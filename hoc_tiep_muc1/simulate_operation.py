"""Mô phỏng vận hành 2026Q1-2028Q3 trên bộ du_lieu_co_dinh_v2 (mô hình HistGradientBoosting, CPU).
Mỗi quý: dịch vụ dự đoán việc mới giao bằng phiên bản đang chạy -> ghi nhật ký; việc hoàn thành trong quý được ghi kết quả -> cuối quý chạy huấn luyện lại.
Chiến lược: S0 giữ nguyên | S1 huấn luyện lại mỗi quý, nâng cấp vô điều kiện (ngây thơ) | S2 có kiểm soát (rào chắn mặc định)
            | S3 có kiểm soát nhưng chỉ cần 'không kém' (không đòi tốt hơn có ý nghĩa).
Dữ liệu mô phỏng: kết quả chỉ nói về hành vi của quy trình trên bộ sinh, không phải hiệu quả thực tế."""
import argparse, json, os, sys, tempfile, time, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from hoc_tiep import Config, FeedbackStore, ModelRegistry, RiskService, retrain_job, paired_bootstrap
from hoc_tiep.compare import level_stats, levels_array, metrics
from hoc_tiep.model_backend import HGBBackend, prepare_features

warnings.filterwarnings("ignore")
ap = argparse.ArgumentParser()
ap.add_argument("--data", required=True); ap.add_argument("--completion", required=True); ap.add_argument("--out", default="ket_qua_mo_phong")
ap.add_argument("--start", default="2026-01-01"); ap.add_argument("--strategies", default="S0,S1,S2,S3")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
df = pd.read_csv(a.data, parse_dates=["assigned_date"]).merge(pd.read_csv(a.completion, parse_dates=["completed_date"]), on=["task_id", "lecturer_id"])
t0 = pd.Timestamp(a.start)
base = df[df.completed_date < t0].reset_index(drop=True)
ops = df[df.assigned_date >= t0].sort_values("assigned_date").reset_index(drop=True)
quarters = pd.period_range(t0, ops.assigned_date.max(), freq="Q")
print(f"nền {len(base)} việc (hoàn thành trước {t0.date()}), vận hành {len(ops)} việc, {len(quarters)} quý", flush=True)
CFG = Config()
CFG3 = Config(require_significant_gain=False)


def run(name):
    tmp = tempfile.mkdtemp(); reg = ModelRegistry(tmp); st = FeedbackStore(":memory:")
    cfg = CFG3 if name == "S3" else CFG
    retrain_job.init_model(base, reg, cfg, now=t0 - pd.Timedelta(days=1))
    svc = RiskService(reg, st); backend = HGBBackend()
    preds, decisions = [], []
    for q in quarters:
        q0, q1 = q.start_time.normalize(), q.end_time.normalize()
        rows = ops[(ops.assigned_date >= q0) & (ops.assigned_date <= q1)]
        if len(rows):
            r = svc.predict(rows, now=rows.assigned_date.values)
            preds.append(r)
        o = ops[(ops.completed_date >= q0) & (ops.completed_date <= q1)][["task_id", "lecturer_id", "is_late", "completed_date"]]
        st.record_outcomes(o, recorded_at=o.completed_date)
        as_of = q1 + pd.Timedelta(days=1)
        t = time.time()
        if name in ("S2", "S3"):
            d = retrain_job.run(st, reg, base, as_of, cfg, now=as_of)
            decisions.append({k: v for k, v in d.items() if k != "details"} | ({"delta": d["details"]["delta"]} if "details" in d else {}))
            tag = f"nâng cấp -> {d['candidate']}" if d["promoted"] else "giữ nguyên: " + "; ".join(d["reasons"])[:110]
        elif name == "S1":
            fb = st.labeled_frame(as_of)
            pool = pd.concat([base, fb], ignore_index=True).drop_duplicates(["task_id", "lecturer_id"], keep="last").sort_values("assigned_date").reset_index(drop=True)
            k = int(len(pool) * .85); feats = reg.load()["features"]
            b = retrain_job.build_bundle(backend, feats, pool.iloc[:k], pool.iloc[k:], pool, cfg, None)
            v = reg.register(b, dict(kind="naive", as_of=str(as_of.date())), now=as_of); reg.promote(v, "ngây thơ", now=as_of)
            tag = f"nâng cấp vô điều kiện -> {v} (n={len(pool)})"
        else:
            tag = "-"
        print(f"  [{name}] {q}: {len(rows):5d} việc | đang chạy {reg.current()} | {tag} ({time.time()-t:.0f}s)", flush=True)
    P = pd.concat(preds, ignore_index=True)
    return P, decisions, reg


res, dec = {}, {}
for s in a.strategies.split(","):
    print(f"== {s}", flush=True)
    P, d, reg = run(s)
    res[s] = P; dec[s] = d
    P.to_csv(f"{a.out}/du_doan_{s}.csv", index=False, encoding="utf-8-sig")
    if d: json.dump(d, open(f"{a.out}/quyet_dinh_{s}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    json.dump(reg.history(), open(f"{a.out}/lich_su_{s}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)

truth = ops.set_index(["task_id", "lecturer_id"])
rows = []
ref = None
out = {"quarters": [str(q) for q in quarters], "strategies": {}}
for s, P in res.items():
    P = P.merge(ops[["task_id", "lecturer_id", "is_late", "assigned_date"]], on=["task_id", "lecturer_id"], how="left", validate="one_to_one")   # khóa là (task_id, lecturer_id): việc nhóm có nhiều giảng viên
    P["q"] = P.assigned_date.dt.to_period("Q").astype(str)
    res[s] = P
    m = metrics(P.is_late.values, P.risk_probability.values)
    lv = dict(low=P[P.level == "Thấp"], high=P[P.level == "Cao"])
    m.update(share_low=len(lv["low"]) / len(P), late_low=float(lv["low"].is_late.mean()), share_high=len(lv["high"]) / len(P), prec_high=float(lv["high"].is_late.mean()),
             n_versions=int(P.model_version.nunique()))
    out["strategies"][s] = m
ref = res["S0"] if "S0" in res else None
if ref is not None:
    for s, P in res.items():
        if s == "S0": continue
        mm = P.merge(ref[["task_id", "lecturer_id", "risk_probability"]], on=["task_id", "lecturer_id"], suffixes=("", "_s0"), validate="one_to_one")
        ci = paired_bootstrap(mm.is_late.values, mm.risk_probability_s0.values, mm.risk_probability.values, mm.lecturer_id.values, 300, 0)
        out["strategies"][s]["delta_vs_S0"] = {k: v for k, v in ci.items()}
byq = []
for s, P in res.items():
    for q, g in P.groupby("q"):
        byq.append(dict(strategy=s, quarter=q, n=len(g), actual=g.is_late.mean(), pred=g.risk_probability.mean(),
                        auc=float(__import__("sklearn.metrics", fromlist=["x"]).roc_auc_score(g.is_late, g.risk_probability)) if g.is_late.nunique() > 1 else np.nan, version=g.model_version.mode().iloc[0]))
pd.DataFrame(byq).to_csv(f"{a.out}/theo_quy.csv", index=False, encoding="utf-8-sig")
json.dump(out, open(f"{a.out}/tong_hop.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out["strategies"], ensure_ascii=False, indent=1, default=float))
