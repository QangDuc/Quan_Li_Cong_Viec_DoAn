#!/usr/bin/env python3
"""
SO SÁNH MÔ HÌNH CHÍNH (TabPFN) VỚI CÁC MÔ HÌNH ĐỐI CHỨNG (gồm CatBoost) — huấn luyện RIÊNG, không lưu để triển khai.

  python compare_models.py --data ./data/ml_training_set_with_matrix.csv --out ./compare

Ứng viên:
  - tabpfn (CHÍNH)       — giống train_model.py (tabular foundation model, in-context learning)
  - catboost             — gradient boosting, mô hình chính của bộ công cụ CatBoost (chỉ chạy nếu đã cài catboost; --no-catboost để bỏ)
  - logistic_base        — logistic tuyến tính (mô hình truyền thống / đơn giản)
  - hist_baseline        — chỉ dùng hist_late_rate

Giao thức: chia theo thời gian 60/15/25, chọn siêu tham số trên validation, đánh giá trên test + ΔAUC bootstrap theo cụm giảng viên.
"""
import argparse, json, os, warnings
import numpy as np, pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, log_loss
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import train_model as T

try:
    from catboost import CatBoostClassifier
except ImportError:
    CatBoostClassifier = None
CB_GRID = [
    dict(depth=6, learning_rate=0.05, l2_leaf_reg=3.0, iterations=400),
    dict(depth=4, learning_rate=0.03, l2_leaf_reg=5.0, iterations=500),
    dict(depth=8, learning_rate=0.05, l2_leaf_reg=1.0, iterations=300),
    dict(depth=6, learning_rate=0.08, l2_leaf_reg=3.0, iterations=250),
]


def cb_prep(X):
    X = X.copy()
    cat, num = T.split_cols(X)
    for c in cat:
        X[c] = X[c].astype(object).where(X[c].notna(), None).map(lambda v: str(v) if v is not None and v == v else None)
    for c in num:
        X[c] = pd.to_numeric(X[c], errors="coerce")
    return X, cat


def cb_fit(X, y, params):
    Xp, cat = cb_prep(X)
    m = CatBoostClassifier(loss_function="Logloss", random_seed=0, verbose=False, allow_writing_files=False, cat_features=cat, **params)
    m.fit(Xp, y)
    return m


def cb_prob(m, X):
    return np.clip(m.predict_proba(cb_prep(X)[0])[:, 1], 1e-4, 1 - 1e-4)
warnings.filterwarnings("ignore")


def make_lr_base(X, C):
    cat, num = T.split_cols(X)
    parts = [
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
        ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), num),
    ]
    return Pipeline([("pre", ColumnTransformer(parts)), ("m", LogisticRegression(C=C, max_iter=3000))])


MAIN = "tabpfn (CHÍNH)"


def run_one(path, use_cb=True):
    df = T.engineer(pd.read_csv(path, parse_dates=["assigned_date"])).sort_values("assigned_date").reset_index(drop=True)
    y = df[T.LABEL].astype(int).values
    X = df.drop(columns=[c for c in T.ID_COLS + T.TARGETS if c in df.columns])
    if "task_matrix_source" in X.columns:
        X = X.drop(columns=["task_matrix_source"])
    t1, t2 = df.assigned_date.quantile(0.60), df.assigned_date.quantile(0.75)
    tr = (df.assigned_date <= t1).values
    va = ((df.assigned_date > t1) & (df.assigned_date <= t2)).values
    te = (df.assigned_date > t2).values
    trva = tr | va

    res, preds = {}, {}

    # --- TabPFN (CHÍNH) ---
    best = None
    for params in T.PARAM_GRID:
        m = T.fit_model(X.loc[tr], y[tr], params=params)
        ll = log_loss(y[va], T.prob(m, X.loc[va]))
        if best is None or ll < best[0]:
            best = (ll, params)
    m = T.fit_model(X.loc[trva], y[trva], params=best[1])
    preds[MAIN] = T.prob(m, X.loc[te])
    res[MAIN] = dict(T.metrics(y[te], preds[MAIN]), val_logloss=float(best[0]), hyperparams=str(best[1]))

    # --- CatBoost (đối chứng: mô hình chính của bộ CatBoost) ---
    if use_cb and CatBoostClassifier is not None:
        best = None
        for params in CB_GRID:
            m = cb_fit(X.loc[tr], y[tr], params)
            ll = log_loss(y[va], cb_prob(m, X.loc[va]))
            if best is None or ll < best[0]:
                best = (ll, params)
        m = cb_fit(X.loc[trva], y[trva], best[1])
        preds["catboost"] = cb_prob(m, X.loc[te])
        res["catboost"] = dict(T.metrics(y[te], preds["catboost"]), val_logloss=float(best[0]), hyperparams=str(best[1]))
    elif use_cb:
        print("(bỏ qua catboost: chưa cài — pip install catboost)")

    # --- logistic base ---
    best = None
    for C in [0.01, 0.05, 0.1, 0.3, 1.0]:
        m = make_lr_base(X, C).fit(X.loc[tr], y[tr])
        ll = log_loss(y[va], np.clip(m.predict_proba(X.loc[va])[:, 1], 1e-4, 1 - 1e-4))
        if best is None or ll < best[0]:
            best = (ll, C)
    m = make_lr_base(X, best[1]).fit(X.loc[trva], y[trva])
    preds["logistic_base"] = np.clip(m.predict_proba(X.loc[te])[:, 1], 1e-4, 1 - 1e-4)
    res["logistic_base"] = dict(T.metrics(y[te], preds["logistic_base"]), val_logloss=float(best[0]), hyperparams=str(best[1]))

    # --- hist baseline ---
    base = df.loc[te, "hist_late_rate"].fillna(0.2).values
    preds["hist_baseline"] = base
    res["hist_baseline"] = dict(T.metrics(y[te], base), val_logloss=float("nan"), hyperparams="-")

    rng = np.random.default_rng(0)
    main = preds[MAIN]
    for k in list(preds):
        if k == MAIN:
            continue
        diffs = []
        # bootstrap THEO CỤM GIẢNG VIÊN (các dòng của cùng một người không độc lập; lấy mẫu theo dòng làm khoảng tin cậy quá hẹp)
        grp = df.loc[te, "lecturer_id"].values if "lecturer_id" in df.columns else np.arange(te.sum())
        order = np.argsort(grp, kind="stable")
        ug, st = np.unique(grp[order], return_index=True)
        bnd = list(st) + [len(grp)]
        members = [order[bnd[j]:bnd[j + 1]] for j in range(len(ug))]
        for _ in range(300):
            pick = rng.integers(0, len(ug), len(ug))
            i = np.concatenate([members[j] for j in pick])
            yy = y[te][i]
            if yy.min() == yy.max():
                continue
            diffs.append(roc_auc_score(yy, main[i]) - roc_auc_score(yy, preds[k][i]))
        res[k]["delta_auc_main_minus_this"] = float(np.mean(diffs))
        res[k]["delta_auc_ci95"] = [float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))]

    res["_info"] = dict(
        n_train=int(trva.sum()), n_test=int(te.sum()), late_rate_test=float(y[te].mean()),
        note="Chỉ TabPFN được lưu bởi train_model.py để triển khai; CatBoost, logistic và baseline chỉ để báo cáo so sánh.",
    )
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", nargs="+", required=True)
    ap.add_argument("--out", default="./compare")
    ap.add_argument("--no-catboost", action="store_true", help="không chạy CatBoost đối chứng")
    T.add_tabpfn_args(ap)
    a = ap.parse_args(); T.configure(a)
    os.makedirs(a.out, exist_ok=True)
    allres = {}
    for p in a.data:
        print("đang so sánh trên", p, flush=True)
        allres[p] = run_one(p, use_cb=not a.no_catboost)

    names = [k for k in allres[a.data[0]] if not k.startswith("_")]
    keys = ["roc_auc", "pr_auc", "brier", "ece", "recall_at_top20pct"]
    rows = []
    for n in names:
        row = {"mô hình": n}
        for k in keys:
            v = [allres[p][n][k] for p in a.data]
            row[k] = f"{np.mean(v):.3f}" + (f" ± {np.std(v):.3f}" if len(v) > 1 else "")
        d = [allres[p][n].get("delta_auc_main_minus_this") for p in a.data]
        if d[0] is None:
            row["ΔAUC (chính − mô hình này)"] = "-"
        else:
            lo = np.mean([allres[p][n]["delta_auc_ci95"][0] for p in a.data])
            hi = np.mean([allres[p][n]["delta_auc_ci95"][1] for p in a.data])
            row["ΔAUC (chính − mô hình này)"] = f"{np.mean(d):+.3f} [CI: {lo:+.3f}, {hi:+.3f}]"
        rows.append(row)
    tab = pd.DataFrame(rows)
    print(f"\n=== SO SÁNH TRÊN {len(a.data)} TẬP (test theo thời gian) ===\n" + tab.to_string(index=False))
    print("\nGhi chú: ΔAUC > 0 và CI không chứa 0 → TabPFN tốt hơn đối chứng (trên dữ liệu này).")
    tab.to_csv(f"{a.out}/compare_table.csv", index=False, encoding="utf-8-sig")
    json.dump(allres, open(f"{a.out}/compare_results.json", "w"), ensure_ascii=False, indent=2, default=float)
    print(f"Đã lưu vào {os.path.abspath(a.out)}")


if __name__ == "__main__":
    main()
