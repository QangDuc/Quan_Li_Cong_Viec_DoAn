#!/usr/bin/env python3
"""
CÁC MÔ HÌNH ĐỐI CHỨNG (CPU, không cần GPU), cùng quy trình với train_model.py (--pool train):
  huấn luyện trên tập train, chọn siêu tham số trên validation, dự đoán validation và test.
Mô hình: baseline lịch sử, hồi quy logistic, hồi quy logistic có spline, CatBoost
(và với dữ liệu ĐỘNG: thêm CatBoost chỉ dùng đặc trưng tĩnh để đo giá trị của thông tin tiến độ).

  python run_baselines.py --data ./data/ml_training_set_with_matrix.csv --out ./baselines_static
  python run_baselines.py --data ./data/ml_dynamic_set_clean_with_matrix.csv --out ./baselines_dynamic

Ra: predictions_val.csv, predictions_test.csv (mỗi mô hình một cột), baselines_info.json
"""
import argparse, json, os, time, warnings
import numpy as np, pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, SplineTransformer, StandardScaler
warnings.filterwarnings("ignore")
import train_model as T

try:
    from catboost import CatBoostClassifier
except ImportError:
    CatBoostClassifier = None
CB_GRID = [dict(depth=6, learning_rate=0.05, l2_leaf_reg=3.0, iterations=400), dict(depth=4, learning_rate=0.03, l2_leaf_reg=5.0, iterations=500),
           dict(depth=8, learning_rate=0.05, l2_leaf_reg=1.0, iterations=300), dict(depth=6, learning_rate=0.08, l2_leaf_reg=3.0, iterations=250)]
DYN_COLS = ["checkpoint_fraction", "days_elapsed", "days_remaining", "progress_pct", "expected_progress_pct", "progress_gap", "progress_missing"]
clip = lambda p: np.clip(p, 1e-4, 1 - 1e-4)


def make_lr(X, C, spline=False, n_knots=5):
    cat, num = T.split_cols(X)
    if spline:
        cont = [c for c in num if X[c].nunique() > 10]
        low = [c for c in num if c not in cont]
        parts = [("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=30), cat),
                 ("low", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), low),
                 ("cont", make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), SplineTransformer(n_knots=n_knots, degree=3, extrapolation="constant")), cont)]
    else:
        parts = [("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=30), cat),
                 ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), num)]
    return Pipeline([("pre", ColumnTransformer(parts)), ("m", LogisticRegression(C=C, max_iter=3000))])


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
    return clip(m.predict_proba(cb_prep(X)[0])[:, 1])


def tune(name, fits, X, y, tr, va, info):
    """fits: danh sách (tham số, hàm dựng mô hình đã fit, hàm dự đoán). Chọn theo log-loss validation."""
    best = None
    for params, fit, pred in fits:
        t = time.time()
        m = fit(X.loc[tr], y[tr])
        p = pred(m, X.loc[va])
        ll = log_loss(y[va], p)
        print(f"   [{name}] {params} -> log-loss validation {ll:.4f} ({time.time() - t:.0f}s)", flush=True)
        if best is None or ll < best[0]:
            best = (ll, params, m, pred)
    info[name] = dict(val_logloss=round(float(best[0]), 5), params=best[1])
    return best[2], best[3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default="./baselines")
    ap.add_argument("--no-catboost", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    df = T.engineer(pd.read_csv(a.data, parse_dates=["assigned_date"])).sort_values("assigned_date").reset_index(drop=True)
    y = df[T.LABEL].astype(int).values
    X = df.drop(columns=[c for c in T.ID_COLS + T.TARGETS if c in df.columns])
    t1, t2 = df.assigned_date.quantile(0.60), df.assigned_date.quantile(0.75)
    tr = (df.assigned_date <= t1).values
    va = ((df.assigned_date > t1) & (df.assigned_date <= t2)).values
    te = (df.assigned_date > t2).values
    dynamic = "checkpoint_fraction" in df.columns
    print(f"{'ĐỘNG' if dynamic else 'TĨNH'} | train {tr.sum()} | validation {va.sum()} | test {te.sum()} | {X.shape[1]} đặc trưng", flush=True)
    ids = [c for c in ["task_id", "lecturer_id", "faculty", "assigned_date", "checkpoint_fraction"] if c in df.columns]
    out_va = df.loc[va, ids].reset_index(drop=True).assign(y=y[va])
    out_te = df.loc[te, ids].reset_index(drop=True).assign(y=y[te])
    info = {}
    models = {}

    out_va["hist_baseline"] = df.loc[va, "hist_late_rate"].fillna(0.2).values
    out_te["hist_baseline"] = df.loc[te, "hist_late_rate"].fillna(0.2).values
    models["logistic_base"] = (X, [(dict(C=c), (lambda Xa, ya, c=c: make_lr(Xa, c).fit(Xa, ya)), lambda m, Xa: clip(m.predict_proba(Xa)[:, 1])) for c in [0.01, 0.05, 0.1, 0.3, 1.0]])
    models["logistic_spline"] = (X, [(dict(C=c), (lambda Xa, ya, c=c: make_lr(Xa, c, spline=True).fit(Xa, ya)), lambda m, Xa: clip(m.predict_proba(Xa)[:, 1])) for c in [0.03, 0.1, 0.3, 1.0]])
    if CatBoostClassifier is not None and not a.no_catboost:
        models["catboost"] = (X, [(p, (lambda Xa, ya, p=p: cb_fit(Xa, ya, p)), cb_prob) for p in CB_GRID])
        if dynamic:
            Xs = X.drop(columns=[c for c in DYN_COLS if c in X.columns])
            models["catboost_khong_tien_do"] = (Xs, [(p, (lambda Xa, ya, p=p: cb_fit(Xa, ya, p)), cb_prob) for p in CB_GRID])
    else:
        print("(bỏ qua CatBoost: chưa cài hoặc --no-catboost)")
    for name, (XX, fits) in models.items():
        m, pred = tune(name, fits, XX, y, tr, va, info)
        out_va[name] = pred(m, XX.loc[va])
        out_te[name] = pred(m, XX.loc[te])
        r = T.metrics(y[te], out_te[name].values)
        print(f"== {name}: test AUC {r['roc_auc']:.4f} | PR-AUC {r['pr_auc']:.4f} | Brier {r['brier']:.4f} | ECE {r['ece']:.4f}", flush=True)
        info[name]["test"] = {k: round(float(v), 4) for k, v in r.items()}
        out_va.to_csv(f"{a.out}/predictions_val.csv", index=False, encoding="utf-8-sig")
        out_te.to_csv(f"{a.out}/predictions_test.csv", index=False, encoding="utf-8-sig")
    json.dump(dict(dynamic=dynamic, n_train=int(tr.sum()), n_val=int(va.sum()), n_test=int(te.sum()), models=info), open(f"{a.out}/baselines_info.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nĐã lưu vào {os.path.abspath(a.out)}")


if __name__ == "__main__":
    main()
