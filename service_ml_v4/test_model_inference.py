#!/usr/bin/env python3
"""Chạy thử nhanh dịch vụ với 3 ca mẫu lấy từ dòng THẬT của tập test v2 (sample_requests.json). Mặc định cần TabPFN; thêm ML_ENGINE=surrogate_hgb để chạy bản demo CPU.
  ML_ENGINE=surrogate_hgb python test_model_inference.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ml_service

w = ml_service.model_wrapper
print("=== Trạng thái ===")
print(json.dumps({k: getattr(w, k) for k in ("engine_type", "engine_validated", "model_version", "thresholds", "load_error")}, ensure_ascii=False, indent=1))
if not w.ready():
    sys.exit("Dịch vụ chưa sẵn sàng (xem load_error ở trên).")
for r in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_requests.json"), encoding="utf-8")):
    res = w.predict(r["features"])
    print(f"\n=== Ca {r['nhan']} (TabPFN trên test v2 cho {r['tabpfn_tren_test_v2']:.1%}; thực tế {'trễ' if r['thuc_te_tre'] else 'đúng hạn'}) ===")
    print(f"P = {res['probability']:.1%} | mức {res['level']} | độ lệch giữa các túi {res['uncertainty']:.4f} | tin cậy thấp: {res['low_confidence']}")
    for t in res["top_factors"]:
        print("  •", t)
    print("Khuyến nghị:", res["recommendation"])
