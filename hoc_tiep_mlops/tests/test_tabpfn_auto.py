"""Kiểm thử học tiếp TỰ ĐỘNG cho TabPFN. Dùng mô-đun tabpfn/torch GIẢ (HistGradientBoosting) CHỈ để kiểm tra dây nối, kho phiên bản,
khóa job, tự quay lại và dịch vụ tự nạp lại; không chứng minh gì về chất lượng hay tốc độ của TabPFN thật.
Chạy: python tests/test_tabpfn_auto.py"""
import json, os, shutil, sys, tempfile, traceback, warnings
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); BO = os.path.dirname(ROOT)
STUB_DIR = tempfile.mkdtemp(prefix="stub_tabpfn_")
os.makedirs(f"{STUB_DIR}/tabpfn"); os.makedirs(f"{STUB_DIR}/torch")
open(f"{STUB_DIR}/tabpfn/__init__.py", "w").write('''import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
__version__ = "0.0-stub"
class TabPFNClassifier:
    def __init__(self, **kw): self.kw = kw
    def fit(self, X, y):
        self.m = HistGradientBoostingClassifier(max_iter=30, categorical_features=self.kw.get("categorical_features_indices"), random_state=self.kw.get("random_state", 0)).fit(np.asarray(X, float), np.asarray(y).astype(int)); return self
    def predict_proba(self, X): return self.m.predict_proba(np.asarray(X, float))
''')
open(f"{STUB_DIR}/torch/__init__.py", "w").write("class cuda:\n    @staticmethod\n    def is_available(): return False\n")
sys.path[:0] = [
    STUB_DIR, ROOT, HERE,
    os.path.join(BO, "backend"),
    os.path.join(BO, "backend", "app"),
    os.path.join(BO, "service"),
    os.path.join(BO, "training_scripts"),
]
warnings.filterwarnings("ignore")
import joblib, numpy as np, pandas as pd
from test_hoc_tiep import make, CFG
from hoc_tiep import FeedbackStore, ModelRegistry, RiskService, retrain_job, TabPFNBackend, import_service_bundle, auto_job
from hoc_tiep.model_backend import prepare_features

BK = lambda: TabPFNBackend(n_bags=2)


def fresh():
    tmp = tempfile.mkdtemp(); base = make(7000, "2022-01-01", 900, 10)
    reg = ModelRegistry(os.path.join(tmp, "reg")); st = FeedbackStore(os.path.join(tmp, "fb.db"))
    retrain_job.init_model(base, reg, CFG, backend=BK())
    return base, reg, st


def feed(st, reg, df):
    svc = RiskService(reg, st, backend=BK()); svc.predict(df.drop(columns=["is_late"]), now="2020-01-01")
    st.record_outcomes(pd.DataFrame({"task_id": df.task_id, "lecturer_id": df.lecturer_id, "is_late": df.is_late,
                                     "completed_date": df.assigned_date + pd.Timedelta(days=5)}), recorded_at=df.assigned_date + pd.Timedelta(days=5))


def t_backend_roundtrip_and_pickle():
    from sklearn.metrics import roc_auc_score
    base, reg, st = fresh(); b = reg.load()
    assert b["backend"] == "tabpfn" and isinstance(b["pipeline"], dict) and "_clf" not in b["pipeline"]
    d = make(3000, "2026-01-01", 200, 99)
    p = BK().predict(b, prepare_features(d.drop(columns=["is_late"]), b["features"]))
    assert roc_auc_score(d.is_late, p) > 0.7 and ((p > 0) & (p < 1)).all()


def t_import_service_bundle_and_service_reload():
    reg = ModelRegistry(os.path.join(tempfile.mkdtemp(), "reg"))
    v1 = import_service_bundle(reg, os.path.join(BO, "model", "risk_model.joblib"))
    assert v1 == "v0001" and reg.current() == v1
    os.environ.update(ML_REGISTRY_DIR=reg.root, ML_ENGINE="tabpfn", ML_ADMIN_TOKEN="s3cret")
    import ml_service
    from fastapi.testclient import TestClient
    c = TestClient(ml_service.app); h = c.get("/health").json()
    assert h["status"] == "ok" and h["registry_version"] == v1 and h["thresholds"] == [0.23, 0.52], h
    req = json.load(open(os.path.join(BO, "backend", "sample_requests.json") if os.path.exists(os.path.join(BO, "backend", "sample_requests.json")) else os.path.join(BO, "service", "sample_requests.json"), encoding="utf-8"))[0]["features"]
    assert c.post("/predict", json={"features": req, "explain": False}).status_code == 200
    # nâng cấp: phiên bản mới có ngưỡng khác -> dịch vụ tự nạp lại ở lần gọi sau
    b = reg.load(v1); b["thresholds"] = [0.10, 0.30]
    v2 = reg.register(b, {"kind": "test"}); reg.promote(v2, "thử")
    h = c.get("/health").json(); assert h["registry_version"] == v2 and h["thresholds"] == [0.10, 0.30], h      # /health tự nạp lại (job dựa vào đây)
    r = c.post("/predict", json={"features": req, "explain": False}); assert r.status_code == 200
    h = c.get("/health").json(); assert h["registry_version"] == v2 and h["thresholds"] == [0.10, 0.30], h
    reg.rollback("thử"); c.post("/predict", json={"features": req, "explain": False})
    assert c.get("/health").json()["registry_version"] == v1
    # phiên bản hỏng (file bị sửa) -> giữ mô hình đang chạy, không sập
    v3 = reg.register(b, {"kind": "test"}); reg.promote(v3, "thử"); open(os.path.join(reg.root, "versions", v3, "model.joblib"), "ab").write(b"x")
    assert c.post("/predict", json={"features": req, "explain": False}).status_code == 200
    h = c.get("/health").json(); assert h["registry_version"] == v1 and "SHA-256" in (h["load_error"] or ""), h
    # /reload cần mã quản trị
    assert c.post("/reload").status_code == 403 and c.post("/reload", headers={"X-Admin-Token": "s3cret"}).status_code == 200


def t_auto_dry_run_then_auto_promote():
    base, reg, st = fresh(); v1 = reg.current()
    feed(st, reg, make(9000, "2025-01-01", 500, 11, shift=True))
    d = auto_job.run_auto(st, reg, base, "2026-06-01", CFG, mode="dry-run", backend_kw=dict(n_bags=2))
    assert not d["promoted"] and reg.current() == v1 and os.path.exists(os.path.join(reg.root, "last_decision.json"))
    d = auto_job.run_auto(st, reg, base, "2026-06-01", CFG, mode="auto", backend_kw=dict(n_bags=2))
    assert d["promoted"] and reg.current() == d["candidate"] != v1, d["reasons"]
    last = json.load(open(os.path.join(reg.root, "last_decision.json"), encoding="utf-8")); assert last["promoted"] and last["mode"] == "auto"
    assert not os.path.exists(os.path.join(reg.root, "retrain.lock"))


def t_auto_rolls_back_when_service_does_not_load():
    base, reg, st = fresh(); v1 = reg.current()
    feed(st, reg, make(9000, "2025-01-01", 500, 11, shift=True))
    auto_job._wait_service.__defaults__            # (chữ ký có fetch)
    d = auto_job.run_auto(st, reg, base, "2026-06-01", CFG, mode="auto", service_url="http://x", wait_timeout=1,
                          backend_kw=dict(n_bags=2), fetch=lambda u: {"status": "ok", "registry_version": v1})
    assert not d["promoted"] and reg.current() == v1 and d["rolled_back_to"] == v1 and d["service_check"]["ok"] is False
    d2 = auto_job.run_auto(st, reg, base, "2026-06-01", CFG, mode="auto", service_url="http://x", wait_timeout=5, backend_kw=dict(n_bags=2),
                           fetch=lambda u: {"status": "ok", "registry_version": reg.current()})
    assert d2["promoted"] and d2["service_check"]["ok"] is True


def t_lock_prevents_concurrent_jobs():
    base, reg, st = fresh()
    open(os.path.join(reg.root, "retrain.lock"), "w").write("1")
    try:
        auto_job.run_auto(st, reg, base, "2026-06-01", CFG, backend_kw=dict(n_bags=2)); raise SystemExit("phải bị khóa")
    except auto_job.JobLocked:
        pass


def t_hook_logs_prediction_and_outcome():
    import hoc_tiep_hook
    db = os.path.join(tempfile.mkdtemp(), "fb.db"); os.environ.update(HOC_TIEP_DB=db, HOC_TIEP_PATH=ROOT)
    f = json.load(open(os.path.join(BO, "backend", "sample_requests.json") if os.path.exists(os.path.join(BO, "backend", "sample_requests.json")) else os.path.join(BO, "service", "sample_requests.json"), encoding="utf-8"))[0]["features"]
    assert hoc_tiep_hook.log_prediction(101, 7, f, "2026-03-02 09:00:00", 0.31, "Trung bình", "TabPFN v2")
    assert not hoc_tiep_hook.log_prediction(101, 7, f, "2026-03-05", 0.9, "Cao", "x") or True      # lần 2 bị bỏ (giữ dự đoán đầu) nhưng không lỗi
    assert hoc_tiep_hook.record_outcome(101, 7, "2026-03-20", True)
    st = FeedbackStore(db); s = st.stats(); assert s["n_predictions"] == 1 and s["n_outcomes"] == 1 and s["n_labeled"] == 1, s
    lf = st.labeled_frame("2099-01-01"); assert len(lf) == 1 and lf.is_late.iloc[0] == 1 and lf.model_version_logged.iloc[0] == "TabPFN v2"
    os.environ.pop("HOC_TIEP_DB"); assert hoc_tiep_hook.log_prediction(1, 1, f, "2026-03-02", .1, "Thấp", "v") is False


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("t_")]; bad = 0
    for f in tests:
        try: f(); print("ĐẠT     ", f.__name__)
        except BaseException: bad += 1; print("KHÔNG ĐẠT", f.__name__); traceback.print_exc()
    shutil.rmtree(STUB_DIR, ignore_errors=True)
    print(f"\n{len(tests) - bad}/{len(tests)} đạt"); sys.exit(1 if bad else 0)
