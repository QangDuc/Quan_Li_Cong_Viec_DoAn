#!/usr/bin/env python3
"""Hiệu chuẩn ngưỡng cho động cơ thay thế `surrogate_hgb` của ml_service.py (chỉ dùng cho demo khi không có TabPFN).
Động cơ này huấn luyện 4 bộ HistGradientBoosting trên các túi ngữ cảnh của risk_model.joblib; xác suất của nó KHÁC TabPFN nên không được dùng
ngưỡng của TabPFN. Ngưỡng được CHỌN TRÊN VALIDATION (ngữ cảnh chỉ từ tập train nên validation chưa được thấy) và chỉ ĐO trên test.
  python calibrate_cpu_surrogate.py --data ../data/ml_training_set_with_matrix.csv --model ../model --out ../model/cpu_surrogate.json
Kết quả nói về động cơ thay thế, KHÔNG phải về TabPFN."""
import argparse, json, os, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, joblib
from sklearn.ensemble import HistGradientBoostingClassifier
import train_model as T

ap = argparse.ArgumentParser()
ap.add_argument("--data", required=True); ap.add_argument("--model", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--safety-margin", type=float, default=0.01); ap.add_argument("--safety-margin-high", type=float, default=0.03)
a = ap.parse_args()
b = joblib.load(os.path.join(a.model, "risk_model.joblib"))
df = T.engineer(pd.read_csv(a.data, parse_dates=["assigned_date"])).sort_values("assigned_date").reset_index(drop=True)
t1, t2 = df.assigned_date.quantile(0.60), df.assigned_date.quantile(0.75)
va, te = (df.assigned_date > t1) & (df.assigned_date <= t2), df.assigned_date > t2
eng = T.restore_dups(df, b["features"]); X = T.apply_encoder(b["encoder"], eng.reindex(columns=b["features"])); y = df[T.LABEL].astype(int).values
clfs = []
for k, (Xc, yc) in enumerate(b["contexts"]):          # đúng cấu hình của ml_service._load_surrogate
    c = HistGradientBoostingClassifier(max_iter=150, learning_rate=0.05, max_depth=6, categorical_features=b.get("cat_idx") or None, random_state=42 + k)
    c.fit(Xc, yc); clfs.append(c)
P = lambda m: np.clip(np.mean([c.predict_proba(X[m].values)[:, 1] for c in clfs], axis=0), 1e-4, 1 - 1e-4)
p_va, p_te = P(va.values), P(te.values)
thr, ok = T.pick_thresholds(y[va.values], p_va, safety_margin=a.safety_margin, safety_margin_high=a.safety_margin_high)
def lv(y_, p_):
    lo, hi = p_ < thr[0], p_ >= thr[1]
    return dict(thap=dict(share=round(float(lo.mean()), 4), late_rate=round(float(y_[lo].mean()), 4)), cao=dict(share=round(float(hi.mean()), 4), precision=round(float(y_[hi].mean()), 4)))
out = dict(
    note="Ngưỡng cho động cơ thay thế surrogate_hgb (KHÔNG phải TabPFN). Chọn trên validation, đo trên test.",
    created=str(datetime.date.today()), thresholds=thr, thresholds_ok=bool(ok), safety_margin=a.safety_margin, safety_margin_high=a.safety_margin_high,
    n_val=int(va.sum()), n_test=int(te.sum()),
    val=T.metrics(y[va.values], p_va) | lv(y[va.values], p_va),
    test=T.metrics(y[te.values], p_te) | lv(y[te.values], p_te),
    test_note="Tập test v2 đã được xem trong các lần đánh giá trước nên số này chỉ để minh họa, không dùng để chọn ngưỡng.")
def clean(o):
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (np.floating,)): return round(float(o), 4)
    return o
json.dump(clean(out), open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(clean(out), ensure_ascii=False, indent=1))
