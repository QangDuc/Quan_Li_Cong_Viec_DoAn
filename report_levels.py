#!/usr/bin/env python3
"""
BÁO CÁO MỨC CẢNH BÁO TỪ MÔ HÌNH ĐÃ LƯU (không huấn luyện lại).
Nạp model/risk_model.joblib, dự đoán trên TẬP TEST (cùng cách chia theo thời gian 60/15/25 như train_model.py),
rồi in và lưu: bảng mức cảnh báo, kiểm tra mục tiêu (đạt/không đạt), hiệu chuẩn theo decile, hiệu quả theo nhóm,
và dự đoán từng việc để phân tích tiếp (không phải chạy lại GPU).

  python report_levels.py --data ./data/ml_training_set_with_matrix.csv --model ./model/risk_model.joblib --out ./model_report

Chi phí chủ yếu là suy luận trên ~25.000 dòng test x số túi (xem 'n_bags' của mô hình); nên dùng GPU.
Cho phép dừng giữa chừng và chạy tiếp (lô đã xong được lưu trong <out>/checkpoint_report).
"""
import argparse, json, os, shutil
import numpy as np, pandas as pd, joblib
from sklearn.metrics import roc_auc_score
import train_model as T

ap = argparse.ArgumentParser()
ap.add_argument("--data", required=True)
ap.add_argument("--model", required=True)
ap.add_argument("--out", default="./model_report")
ap.add_argument("--max-late-low", type=float, default=0.10)
ap.add_argument("--min-prec-high", type=float, default=0.60)
ap.add_argument("--keep-checkpoint", action="store_true")
T.add_tabpfn_args(ap)
a = ap.parse_args()
T.configure(a)
os.makedirs(a.out, exist_ok=True)

m = joblib.load(a.model)
if not a.tabpfn_version:
    T.TABPFN_VERSION = m.get("tabpfn_version", T.TABPFN_VERSION)
df = T.engineer(pd.read_csv(a.data, parse_dates=["assigned_date"])).sort_values("assigned_date").reset_index(drop=True)
y = df[T.LABEL].astype(int).values
X = df.drop(columns=[c for c in T.ID_COLS + T.TARGETS if c in df.columns])
t1, t2 = df.assigned_date.quantile(0.60), df.assigned_date.quantile(0.75)
te = (df.assigned_date > t2).values
meta = m.get("meta") or {}
if meta.get("data_end") and str(t2.date()) != meta["data_end"]:
    print(f"[CẢNH BÁO] Mốc test ({t2.date()}) khác mốc dữ liệu huấn luyện của mô hình ({meta['data_end']}): file dữ liệu có thể khác lúc huấn luyện.")
Xt = X.loc[te].reindex(columns=m["features"])
print(f"Mô hình: {m.get('model_name')} {m.get('tabpfn_version', '')} | {len(m['contexts'])} túi | ngưỡng {m['thresholds']} | "
      f"test: {int(te.sum()):,} việc (> {t2.date()}), tỉ lệ trễ {y[te].mean():.3f}")
ck = os.path.join(a.out, "checkpoint_report")
os.makedirs(ck, exist_ok=True)
p, sd = T.prob_detail(m, Xt, ckpt=ck, tag="te")
yt = y[te]

res = T.metrics(yt, p)
grp = df.loc[te, "lecturer_id"].values if "lecturer_id" in df.columns else None
ci = T.boot_auc(yt, p, groups=grp)
print(f"\nAUC {res['roc_auc']:.4f} (KTC 95% theo giảng viên {ci[0]:.3f}-{ci[1]:.3f}) | PR-AUC {res['pr_auc']:.3f} | Brier {res['brier']:.4f} | ECE {res['ece']:.4f}")

levels = m["levels"]
lv = pd.DataFrame({"level": [T.level_of(v, levels) for v in p], "y": yt}).groupby("level").y.agg(["count", "mean"]).reindex(T.LEVEL_NAMES)
lv.columns = ["so_viec", "ti_le_tre_thuc_te"]
lv["so_viec"] = lv["so_viec"].fillna(0)
lv["ti_le_viec"] = lv.so_viec / lv.so_viec.sum()
lv["dự_đoán_TB"] = pd.Series(p).groupby([T.level_of(v, levels) for v in p]).mean().reindex(T.LEVEL_NAMES)
print(f"\n=== MỨC CẢNH BÁO (ngưỡng {m['thresholds']}) ===\n" + lv.round(3).to_string())
low, high = lv.loc["Thấp", "ti_le_tre_thuc_te"], lv.loc["Cao", "ti_le_tre_thuc_te"]
ok_low, ok_high = bool(low <= a.max_late_low), bool(high >= a.min_prec_high)
print(f"Mục tiêu: nhóm Thấp trễ <= {a.max_late_low:.0%} -> thực tế {low:.1%} ({'đạt' if ok_low else 'KHÔNG đạt'}); "
      f"nhóm Cao chính xác >= {a.min_prec_high:.0%} -> thực tế {high:.1%} ({'đạt' if ok_high else 'KHÔNG đạt'})")

dec = pd.DataFrame({"p": p, "y": yt})
dec["nhom"] = pd.qcut(dec.p, 10, duplicates="drop")
dtab = dec.groupby("nhom", observed=True).agg(du_doan_TB=("p", "mean"), ti_le_tre_thuc=("y", "mean"), n=("y", "size"))
print("\n=== HIỆU CHUẨN THEO DECILE ===\n" + dtab.round(3).to_string(index=False))
print(f"Dự đoán TB {p.mean():.3f} so với tỉ lệ trễ thực {yt.mean():.3f} (lệch {yt.mean() - p.mean():+.3f})")

seg = {}
for sname, mask in [
    ("giảng viên mới (lịch sử < 5 việc)", (Xt.get("hist_count", pd.Series(99, index=Xt.index)) < 5).values),
    ("giảng viên có lịch sử >= 5 việc", (Xt.get("hist_count", pd.Series(0, index=Xt.index)) >= 5).values),
    ("mùa cao điểm", (Xt.get("peak_season", pd.Series(0, index=Xt.index)) == 1).values),
    ("độ phức tạp cao", (Xt.get("complexity", pd.Series("", index=Xt.index)) == "Cao").values),
]:
    yy, pp = yt[mask], p[mask]
    seg[sname] = dict(n=int(mask.sum()), late_rate=round(float(yy.mean()), 3) if mask.sum() else None,
                      mean_pred=round(float(pp.mean()), 3) if mask.sum() else None,
                      auc=round(float(roc_auc_score(yy, pp)), 3) if mask.sum() >= 50 and 15 <= yy.sum() < len(yy) else None)
print("\n=== HIỆU QUẢ THEO NHÓM ===\n" + pd.DataFrame(seg).T.to_string())

ids = df.loc[te, [c for c in T.ID_COLS if c in df.columns]].reset_index(drop=True)
out = ids.assign(risk_probability=p.round(4), risk_level=[T.level_of(v, levels) for v in p], thuc_te_tre_han=yt)
if len(m["contexts"]) > 1:
    out["risk_uncertainty"] = sd.round(4)
out.to_csv(os.path.join(a.out, "du_doan_tap_test.csv"), index=False, encoding="utf-8-sig")
json.dump(dict(model=a.model, n_bags=len(m["contexts"]), thresholds=m["thresholds"], test=dict((k, round(float(v), 4)) for k, v in res.items()),
               test_auc_ci95_by_lecturer=[round(c, 4) for c in ci],
               alert_levels={k: dict(n=int(r.so_viec), late_rate=T._nn(r.ti_le_tre_thuc_te), share=round(float(r.ti_le_viec), 4)) for k, r in lv.iterrows()},
               target_check=dict(max_late_low=a.max_late_low, actual_low=T._nn(low), ok_low=ok_low, min_prec_high=a.min_prec_high, actual_high=T._nn(high), ok_high=ok_high),
               mean_pred=round(float(p.mean()), 4), late_rate=round(float(yt.mean()), 4), segments=seg,
               calibration_deciles=[dict(mean_pred=round(float(r.du_doan_TB), 4), late_rate=round(float(r.ti_le_tre_thuc), 4), n=int(r.n)) for r in dtab.itertuples()]),
          open(os.path.join(a.out, "bao_cao_muc_canh_bao.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
if not a.keep_checkpoint:
    shutil.rmtree(ck, ignore_errors=True)
print(f"\nĐã lưu bao_cao_muc_canh_bao.json và du_doan_tap_test.csv vào {os.path.abspath(a.out)}")
