#!/usr/bin/env python3
"""Kiểm thử dịch vụ ml_service.py bằng FastAPI TestClient. Mỗi kịch bản chạy trong một tiến trình riêng vì cấu hình đọc lúc import.
  python test_ml_service.py        (cần: fastapi, httpx, scikit-learn đúng phiên bản của model, numpy, pandas, joblib)
Kịch bản 'tabpfn_gia_lap' dùng mô-đun tabpfn/torch GIẢ trong thư mục tạm CHỈ để kiểm tra dây nối của nhánh TabPFN; nó không chứng minh gì về TabPFN thật."""
import json, os, subprocess, sys, tempfile, textwrap
HERE = os.path.dirname(os.path.abspath(__file__))

STUB = {
    "tabpfn/__init__.py": '''import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
__version__ = "0.0-stub"
class TabPFNClassifier:
    def __init__(self, **kw): self.kw = kw
    def fit(self, X, y):
        self.m = HistGradientBoostingClassifier(max_iter=20, categorical_features=self.kw.get("categorical_features_indices"), random_state=0).fit(np.asarray(X, float), np.asarray(y).astype(int)); return self
    def predict_proba(self, X): return self.m.predict_proba(np.asarray(X, float))
''',
    "torch/__init__.py": "class cuda:\n    @staticmethod\n    def is_available(): return False\n",
}

RUN = textwrap.dedent('''
    import json, sys
    sys.path.insert(0, {here!r})
    from fastapi.testclient import TestClient
    import ml_service
    c = TestClient(ml_service.app)
    reqs = json.load(open({samples!r}, encoding="utf-8"))
    out = {{"health": c.get("/health").json(), "preds": []}}
    for r in reqs:
        resp = c.post("/predict", json={{"features": r["features"]}})
        out["preds"].append({{"nhan": r["nhan"], "status": resp.status_code, "body": resp.json()}})
    partial = {{k: v for k, v in reqs[2]["features"].items() if k in ("task_type", "priority", "complexity", "deadline_pressure", "available_days", "hist_count", "hist_late_rate", "department")}}
    resp = c.post("/predict", json={{"features": partial}})
    out["partial"] = {{"status": resp.status_code, "body": resp.json()}}
    print("@@" + json.dumps(out, ensure_ascii=False))
''')

def scenario(env_extra, stub=False):
    env = dict(os.environ, **env_extra)
    env.pop("ML_ENGINE", None) if "ML_ENGINE" not in env_extra else None
    tmp = None
    if stub:
        tmp = tempfile.mkdtemp()
        for rel, txt in STUB.items():
            p = os.path.join(tmp, rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(txt)
        env["PYTHONPATH"] = tmp
    code = RUN.format(here=HERE, samples=os.path.join(HERE, "sample_requests.json"))
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=900)
    line = [l for l in r.stdout.splitlines() if l.startswith("@@")]
    assert line, "kịch bản không trả kết quả:\\n" + r.stderr[-1500:]
    return json.loads(line[0][2:])

ok = True
def check(cond, msg):
    global ok
    print(("  ĐẠT   " if cond else "  LỖI   ") + msg); ok &= bool(cond)

print("== 1. Mặc định (ML_ENGINE=tabpfn) khi KHÔNG có TabPFN: phải báo degraded và trả 503, không âm thầm đổi mô hình")
o = scenario({})
check(o["health"]["status"] == "degraded" and o["health"]["engine_type"] == "unavailable", f"health: {o['health']['status']} / {o['health']['engine_type']}")
check(all(p["status"] == 503 for p in o["preds"]), "mọi /predict trả 503")
check("tabpfn" in (o["health"]["load_error"] or "").lower(), "thông báo lỗi nêu rõ nguyên nhân")

print("== 2. Động cơ thay thế surrogate_hgb (chọn chủ động)")
o = scenario({"ML_ENGINE": "surrogate_hgb"})
h = o["health"]; thr = h["thresholds"]
sur = json.load(open(os.path.join(HERE, "..", "model", "cpu_surrogate.json"), encoding="utf-8"))
check(h["status"] == "ok" and h["engine_validated"] is False, "health ok nhưng engine_validated = false")
check(thr == sur["thresholds"], f"ngưỡng lấy từ cpu_surrogate.json: {thr}")
for p in o["preds"]:
    b = p["body"]
    check(p["status"] == 200 and b["engine_validated"] is False and "surrogate" in b["engine"], f"[{p['nhan']}] 200, engine={b['engine']}, P={b['probability']}, mức {b['level']}")
    lo, hi = thr
    expect = {"Thấp": f"P < {lo:.0%}", "Trung bình": f"{lo:.0%} ≤ P < {hi:.0%}", "Cao": f"P ≥ {hi:.0%}"}[b["level"]]
    check(expect in b["recommendation"], f"[{p['nhan']}] chữ khuyến nghị khớp ngưỡng thật ({expect})")
    check(not any("= thiếu" in f for f in b["top_factors"]), f"[{p['nhan']}] giải thích không liệt kê trường thiếu như yếu tố rủi ro")
    check(b["low_confidence"] is False and b["missing_features"] == [], f"[{p['nhan']}] đủ trường thì không bị hạ độ tin cậy")
levels = [p["body"]["level"] for p in o["preds"]]
check(levels == ["Thấp", "Trung bình", "Cao"], f"ba ca mẫu (thấp/trung bình/cao) ra đúng ba mức: {levels}")
pb = o["partial"]["body"]
check(o["partial"]["status"] == 200 and pb["low_confidence"] is True and len(pb["missing_features"]) > 0 and "thiếu" in pb["recommendation"], f"yêu cầu thiếu nhiều trường bị hạ độ tin cậy ({len(pb['missing_features'])}+ trường thiếu)")
check(not any("= thiếu" in f for f in pb["top_factors"]), "yêu cầu thiếu trường: giải thích không có '= thiếu'")

print("== 3. Nhánh TabPFN với tabpfn/torch GIẢ LẬP (chỉ kiểm tra dây nối)")
o = scenario({"TABPFN_DEVICE": "cpu"}, stub=True)
h = o["health"]; bt = json.load(open(os.path.join(HERE, "..", "model", "metrics.json"), encoding="utf-8"))["thresholds"]
check(h["status"] == "ok" and h["engine_validated"] is True and h["engine_type"].startswith("tabpfn_"), f"engine {h['engine_type']}, validated={h['engine_validated']}")
check(h["thresholds"] == bt, f"ngưỡng lấy từ bundle: {h['thresholds']}")
check(h["test_roc_auc"] == json.load(open(os.path.join(HERE, "..", "model", "metrics.json"), encoding="utf-8"))["test"]["roc_auc"], f"health đọc đúng AUC test từ metrics.json: {h['test_roc_auc']}")
for p in o["preds"]:
    b = p["body"]; lo, hi = h["thresholds"]
    expect = {"Thấp": f"P < {lo:.0%}", "Trung bình": f"{lo:.0%} ≤ P < {hi:.0%}", "Cao": f"P ≥ {hi:.0%}"}[b["level"]]
    check(p["status"] == 200 and b["engine_validated"] is True and expect in b["recommendation"], f"[{p['nhan']}] 200, mức {b['level']}, chữ khuyến nghị khớp ngưỡng bundle ({expect})")
print("\n" + ("TẤT CẢ ĐẠT" if ok else "CÓ LỖI"))
sys.exit(0 if ok else 1)
