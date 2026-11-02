#!/usr/bin/env python3
"""
Chạy đánh giá các mô hình CPU (Logistic Base, Logistic Spline, CatBoost)
trên cả 3 bộ dữ liệu (Seed 42, Seed 43, Seed 44) bằng run_baselines.py.
Sau đó tổng hợp bảng chỉ số (Mean ± Std) cho báo cáo.
"""
import os
import sys
import json
import subprocess
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_DIR = os.path.join(BASE_DIR, "task_risk_service")

seeds = [42, 43, 44]
summary = {}

for s in seeds:
    data_path = os.path.join(BASE_DIR, f"du_lieu_seed_{s}", "data", "ml_training_set_with_matrix.csv")
    out_dir = os.path.join(BASE_DIR, f"baselines_seed_{s}")
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"\n{'='*70}")
    print(f"CHẠY BASELINES CPU CHO SEED {s}")
    print(f"Dữ liệu: {data_path}")
    print(f"Đầu ra: {out_dir}")
    print(f"{'='*70}\n")
    
    cmd = [
        sys.executable,
        "run_baselines.py",
        "--data", data_path,
        "--out", out_dir
    ]
    
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    
    res = subprocess.run(cmd, cwd=SERVICE_DIR, env=env)
    if res.returncode != 0:
        print(f"Lỗi khi chạy seed {s}!")
        continue
        
    info_path = os.path.join(out_dir, "baselines_info.json")
    if os.path.exists(info_path):
        with open(info_path, "r", encoding="utf-8") as f:
            summary[s] = json.load(f)

# Xuất bảng tổng hợp
print("\n" + "="*80)
print("BẢNG TỔNG HỢP KẾT QUẢ THỰC NGHIỆM CPU TRÊN 3 SEED (MEAN ± STD)")
print("="*80)

models = ["logistic_base", "logistic_spline", "catboost"]
rows = []

for m in models:
    aucs = []
    briers = []
    eces = []
    for s in seeds:
        if s in summary and m in summary[s]:
            metrics = summary[s][m].get("test", {})
            aucs.append(metrics.get("auc", 0))
            briers.append(metrics.get("brier", 0))
            eces.append(metrics.get("ece", 0))
            
    if aucs:
        rows.append({
            "Mô hình": m,
            "Seed 42 (AUC)": f"{aucs[0]:.4f}" if len(aucs) > 0 else "-",
            "Seed 43 (AUC)": f"{aucs[1]:.4f}" if len(aucs) > 1 else "-",
            "Seed 44 (AUC)": f"{aucs[2]:.4f}" if len(aucs) > 2 else "-",
            "AUC (Mean ± Std)": f"{np.mean(aucs):.4f} ± {np.std(aucs):.4f}",
            "Brier (Mean ± Std)": f"{np.mean(briers):.4f} ± {np.std(briers):.4f}",
            "ECE (Mean ± Std)": f"{np.mean(eces):.4f} ± {np.std(eces):.4f}",
        })

df_res = pd.DataFrame(rows)
print(df_res.to_string(index=False))

# Lưu file json kết quả
out_json = os.path.join(BASE_DIR, "tong_hop_cpu_3seeds.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print(f"\nĐã lưu kết quả chi tiết vào: {out_json}")

