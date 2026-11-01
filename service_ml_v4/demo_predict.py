#!/usr/bin/env python3
"""Demo không cần GPU/TabPFN: gọi dịch vụ ML (động cơ surrogate_hgb) với 3 ca mẫu thật (thấp / trung bình / cao).
  cd service && python demo_predict.py            # mặc định surrogate_hgb
  ML_ENGINE=tabpfn python demo_predict.py        # chỉ khi máy đã cài tabpfn==9.2.0 + trọng số (+ GPU)
Kết quả in ra chính là nội dung JSON mà web nhận được từ POST /predict."""
import json, os, sys, time
os.environ.setdefault("ML_ENGINE", "surrogate_hgb")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from fastapi.testclient import TestClient
import ml_service

c = TestClient(ml_service.app)
h = c.get("/health").json()
print(f"/health: status={h['status']} | engine={h['engine_type']} | validated={h['engine_validated']} | ngưỡng={h['thresholds']}")
if h["status"] != "ok":
    sys.exit(f"Dịch vụ chưa sẵn sàng: {h['load_error']}")
for r in json.load(open(os.path.join(HERE, "sample_requests.json"), encoding="utf-8")):
    t = time.time(); resp = c.post("/predict", json={"features": r["features"]}); ms = (time.time() - t) * 1000
    d = resp.json()
    print(f"\n--- ca '{r['nhan']}' (HTTP {resp.status_code}, {ms:.0f} ms)")
    print(f"P(trễ) = {d['probability']:.1%} -> mức {d['level']} | low_confidence={d['low_confidence']} | engine_validated={d['engine_validated']}")
    print("Yếu tố:", " | ".join(d["top_factors"]))
    print("Khuyến nghị:", d["recommendation"])
