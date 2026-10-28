"""Chạy: python tests/test_hoc_tiep.py   (không cần pytest). Dữ liệu tổng hợp nhỏ, không dùng dữ liệu đồ án."""
import os, sys, tempfile, warnings, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from hoc_tiep import Config, FeedbackStore, ModelRegistry, RiskService, retrain_job, paired_bootstrap, pick_thresholds
from hoc_tiep.model_backend import HGBBackend, prepare_features

TYPES = ["A", "B", "C", "D", "E"]


def make(n, start, days, seed, shift=False, late_boost=0.0):
    r = np.random.default_rng(seed)
    d = pd.DataFrame({
        "task_id": [f"T{seed}_{i}" for i in range(n)], "lecturer_id": [f"L{i}" for i in r.integers(0, 80, n)],
        "faculty": r.choice(["K1", "K2", "K3"], n),
        "assigned_date": pd.Timestamp(start) + pd.to_timedelta(np.sort(r.integers(0, days, n)), "D"),
        "x1": r.normal(size=n), "x2": r.normal(size=n), "task_type": r.choice(TYPES, n)})
    eff = d.task_type.map(dict(zip(TYPES, [-.6, -.2, 0, .3, .7]))).values
    z = -1.6 + 1.2 * d.x1 + (0.2 * d.x2 if not shift else -1.0 * d.x2 + 0.8 * d.x1 * d.x2) + eff + late_boost
    d["is_late"] = (r.random(n) < 1 / (1 + np.exp(-z))).astype(int)
    return d


def fresh(base, cfg=None):
    tmp = tempfile.mkdtemp()
    reg = ModelRegistry(os.path.join(tmp, "reg")); st = FeedbackStore(os.path.join(tmp, "fb.db"))
    v = retrain_job.init_model(base, reg, cfg or Config())
    return reg, st, v


def feed(st, reg, df, complete_after_days=5):
    """Mô phỏng dịch vụ: dự đoán rồi ghi kết quả sau complete_after_days ngày."""
    svc = RiskService(reg, st)
    svc.predict(df.drop(columns=["is_late"]), now="2020-01-01")
    o = pd.DataFrame({"task_id": df.task_id, "lecturer_id": df.lecturer_id, "is_late": df.is_late,
                      "completed_date": df.assigned_date + pd.Timedelta(days=complete_after_days)})
    st.record_outcomes(o, recorded_at=o.completed_date)


def t_store_basic():
    st = FeedbackStore(); d = make(300, "2026-01-01", 100, 1)
    st.log_predictions(d, np.full(300, .2), ["Thấp"] * 300, "v1", predicted_at="2026-01-01")
    assert st.log_predictions(d, np.full(300, .9), ["Cao"] * 300, "v2", predicted_at="2026-02-01") == 0   # giữ dự đoán đầu
    o = pd.DataFrame({"task_id": d.task_id, "lecturer_id": d.lecturer_id, "is_late": d.is_late,
                      "completed_date": d.assigned_date + pd.Timedelta(days=10)})
    st.record_outcomes(o, recorded_at="2026-06-01")
    lf = st.labeled_frame("2026-03-01")
    assert (lf.completed_date < "2026-03-01").all() and len(lf) < 300
    assert len(st.labeled_frame("2026-05-31")) == len(st.labeled_frame("2026-05-31").drop_duplicates("task_id"))
    assert len(st.labeled_frame("2026-06-01")) == 0          # chưa ghi nhận trước as_of
    full = st.labeled_frame("2026-06-02"); assert len(full) == 300 and (full.model_version_logged == "v1").all()
    assert "is_late" in full and full.is_late.isin([0, 1]).all()
    raw = st.con.execute("select features from predictions limit 1").fetchone()[0]
    import zlib, json; assert "is_late" not in json.loads(zlib.decompress(raw))          # không lưu nhãn trong đặc trưng


def t_store_intervention():
    st = FeedbackStore(); d = make(100, "2026-01-01", 50, 2)
    st.log_predictions(d, np.full(100, .5), None, "v1", predicted_at="2026-01-01")
    st.record_outcomes(pd.DataFrame({"task_id": d.task_id, "lecturer_id": d.lecturer_id, "is_late": d.is_late,
                                     "completed_date": d.assigned_date + pd.Timedelta(days=3)}), recorded_at="2026-03-01")
    for i in range(10): st.record_intervention(d.task_id[i], d.lecturer_id[i], "2026-01-02", "nhắc việc")
    assert len(st.labeled_frame("2026-04-01", intervention_policy="exclude")) == 90
    assert len(st.labeled_frame("2026-04-01", intervention_policy="include")) == 100


def t_registry():
    base = make(3000, "2024-01-01", 700, 3); reg, st, v1 = fresh(base)
    assert reg.current() == v1 == "v0001"
    b = reg.load(v1)
    v2 = reg.register(b, {"kind": "test"}); assert v2 == "v0002" and reg.current() == v1      # đăng ký chưa chạy
    reg.promote(v2, "thử"); assert reg.current() == v2
    assert reg.rollback("hỏng") == v1 and reg.current() == v1
    try: reg.rollback(); raise SystemExit("phải lỗi")
    except RuntimeError: pass
    f = os.path.join(reg.root, "versions", v2, "model.joblib"); open(f, "ab").write(b"x")
    try: reg.load(v2); raise SystemExit("phải phát hiện file bị sửa")
    except RuntimeError: pass


def t_bootstrap_and_thresholds():
    r = np.random.default_rng(0); y = r.integers(0, 2, 2000); p = np.clip(0.3 * y + r.random(2000) * .6, 0, 1); g = r.integers(0, 40, 2000)
    same = paired_bootstrap(y, p, p, g, 100)
    assert all(same[k][0] == 0 and same[k][1] == 0 and same[k][2] == 0 for k in ("auc", "logloss", "brier"))
    better = paired_bootstrap(y, r.random(2000), p, g, 100); assert better["auc"][1] > 0 and better["logloss"][2] < 0
    try:
        import train_model as T
    except ImportError:
        print("   (bỏ qua so khớp với train_model: không import được)"); return
    yy = (r.random(5000) < .2).astype(int); pp = np.clip(yy * .25 + r.random(5000) * .5, 0, 1)
    assert pick_thresholds(yy, pp) == T.pick_thresholds(yy, pp)                                     # bản sao khớp train_model


def t_unseen_category():
    base = make(3000, "2024-01-01", 700, 4); reg, st, v = fresh(base)
    new = make(50, "2026-01-01", 30, 5); new["task_type"] = "KHÔNG_CÓ"; new.loc[0, "x1"] = np.nan
    out = RiskService(reg, st).predict(new.drop(columns=["is_late"]), now="2026-01-01")
    assert out.risk_probability.between(0, 1).all() and out.risk_probability.notna().all()


CFG = Config(maturity_days=30, holdout_days=120, val_days=120, min_new_labeled=1500, min_new_late=150, min_holdout_rows=1000,
             min_holdout_late=100, min_holdout_lecturers=20, n_boot=150)


def t_reject_small():
    base = make(6000, "2022-01-01", 900, 6); reg, st, v = fresh(base, CFG)
    feed(st, reg, make(300, "2025-01-01", 200, 7))
    d = retrain_job.run(st, reg, base, "2025-12-01", CFG)
    assert not d["promoted"] and any("chưa đủ việc mới" in x for x in d["reasons"]) and reg.current() == v


def t_reject_bad_data():
    base = make(6000, "2022-01-01", 900, 8); reg, st, v = fresh(base, CFG)
    feed(st, reg, make(4000, "2025-01-01", 400, 9, late_boost=6.0))                                  # 90%+ trễ: nghi lỗi dữ liệu
    d = retrain_job.run(st, reg, base, "2026-03-01", CFG)
    assert not d["promoted"] and any("ngoài khoảng cho phép" in x for x in d["reasons"])


def t_promote_on_concept_shift_then_rollback():
    base = make(7000, "2022-01-01", 900, 10); reg, st, v1 = fresh(base, CFG)
    svc = RiskService(reg, st)
    feed(st, reg, make(9000, "2025-01-01", 500, 11, shift=True))                                       # quy luật đổi
    d = retrain_job.run(st, reg, base, "2026-06-01", CFG)
    assert d["promoted"], d["reasons"]
    assert reg.current() != v1 and d["details"]["delta"]["logloss"][2] < 0
    assert svc.predict(make(5, "2026-06-02", 3, 12).drop(columns=["is_late"]), log=False).model_version.iloc[0] == reg.current()
    reg.rollback("kiểm thử"); assert reg.current() == v1
    assert svc.predict(make(5, "2026-06-02", 3, 12).drop(columns=["is_late"]), log=False).model_version.iloc[0] == v1   # dịch vụ tự nạp lại


def t_no_promotion_when_equal():
    """Hai mô hình cho dự đoán gần như giống nhau (khác nhiễu rất nhỏ) -> KHÔNG nâng cấp, tránh đổi phiên bản vô ích."""
    r = np.random.default_rng(1); n = 4000
    y = (r.random(n) < .2).astype(int); p = np.clip(.15 + .25 * y * r.random(n) + .1 * r.random(n), .01, .99); g = r.integers(0, 60, n)
    ok, checks, det = retrain_job.gate(y, p, np.clip(p + r.normal(0, .002, n), .01, .99), g, [.2, .5], [.2, .5], CFG)
    assert not ok and not checks["tot_hon_co_y_nghia"][0] and checks["auc_khong_kem"][0]


def t_more_data_can_promote_same_concept():
    """Cùng quy luật nhưng ứng viên có nhiều dữ liệu hơn: được nâng cấp CHỈ KHI tốt hơn có ý nghĩa (ghi lại để người dùng hiểu hành vi)."""
    base = make(3000, "2022-01-01", 900, 13); reg, st, v1 = fresh(base, CFG)
    feed(st, reg, make(12000, "2025-01-01", 500, 14))
    d = retrain_job.run(st, reg, base, "2026-06-01", CFG, dry_run=True)
    assert d["checks"]["tot_hon_co_y_nghia"]["ok"] == (d["details"]["delta"]["logloss"][2] < 0)


def t_dry_run():
    base = make(7000, "2022-01-01", 900, 15); reg, st, v1 = fresh(base, CFG)
    feed(st, reg, make(9000, "2025-01-01", 500, 16, shift=True))
    d = retrain_job.run(st, reg, base, "2026-06-01", CFG, dry_run=True)
    assert not d["promoted"] and reg.current() == v1 and len(reg.versions()) == 1 and "details" in d


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    tests = [v for k, v in sorted(globals().items()) if k.startswith("t_")]
    bad = 0
    for f in tests:
        try:
            f(); print("ĐẠT     ", f.__name__)
        except BaseException:
            bad += 1; print("KHÔNG ĐẠT", f.__name__); traceback.print_exc()
    print(f"\n{len(tests) - bad}/{len(tests)} đạt"); sys.exit(1 if bad else 0)
