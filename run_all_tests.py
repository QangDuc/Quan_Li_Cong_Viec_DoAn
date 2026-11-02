#!/usr/bin/env python3
"""Chạy toàn bộ kiểm thử của gói (cần: pip install -r service/requirements.txt, trừ torch/tabpfn; pytest).
  python run_all_tests.py"""
import os, subprocess, sys
R = os.path.dirname(os.path.abspath(__file__))
JOBS = [("Dịch vụ ML (3 kịch bản)", ["python", "test_ml_service.py"], "service"),
        ("Tương đương đặc trưng (nhanh)", ["python", "test_feature_parity.py"], "service"),
        ("Tương đương đặc trưng (đầy đủ, sinh dữ liệu mô phỏng nhỏ)", ["python", "-m", "pytest", "-q", "test_feature_parity_full.py"], "service"),
        ("Dựng đặc trưng backend", ["python", "-m", "pytest", "-q", "test_ml_features.py"], "service"),
        ("Học tiếp (15 kiểm thử)", ["python", "tests/test_hoc_tiep.py"], "hoc_tiep_mlops"),
        ("Học tiếp tự động cho TabPFN (6 kiểm thử, TabPFN giả)", ["python", "tests/test_tabpfn_auto.py"], "hoc_tiep_mlops"),
        ("Số liệu chương 4 khớp file kết quả", ["python", "kiem_tra_so_lieu_chuong4.py"], ".")]
bad = 0
for name, cmd, d in JOBS:
    p = subprocess.run([sys.executable if cmd[0] == "python" else cmd[0], *cmd[1:]], cwd=os.path.join(R, d), capture_output=True, text=True)
    ok = p.returncode == 0; bad += not ok
    tail = (p.stdout + p.stderr).strip().splitlines()[-1:] 
    print(f"{'ĐẠT ' if ok else 'LỖI '} {name}: {tail[0] if tail else ''}")
    if not ok: print((p.stdout + p.stderr)[-1500:])
sys.exit(1 if bad else 0)
