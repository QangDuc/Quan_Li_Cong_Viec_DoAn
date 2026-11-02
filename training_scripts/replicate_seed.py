#!/usr/bin/env python3
"""
Tự động sinh và chuẩn hóa bộ dữ liệu theo seed được chỉ định (v2 pipeline):
  1. gen_synthetic_data_v5.py: Sinh dữ liệu thô (360 giảng viên x 6 Khoa x 5 năm).
  2. clean_data.py & build_task_personnel_matrix.py: Làm sạch, xây ma trận tác vụ-nhân sự không rò rỉ.
  3. make_dataset_v2.py: Chuẩn hóa bộ dữ liệu tĩnh, động, oracle_truth và tính mã băm MANIFEST.json.
"""
import sys
import os
import time
import argparse
import subprocess
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))

def run_cmd(cmd, desc):
    print(f"\n[RUNNING] {desc}...")
    t0 = time.time()
    res = subprocess.run([sys.executable] + cmd, cwd=HERE, capture_output=True, text=True)
    elapsed = time.time() - t0
    if res.returncode != 0:
        print(f"[ERROR] {desc} thất bại sau {elapsed:.1f}s!")
        print("STDOUT:", res.stdout[-1000:] if res.stdout else "")
        print("STDERR:", res.stderr[-1000:] if res.stderr else "")
        sys.exit(1)
    print(f"[DONE] {desc} hoàn tất trong {elapsed:.1f}s.")
    return res.stdout

def build_seed_dataset(seed: int):
    raw_dir = os.path.join(HERE, f"raw_seed_{seed}")
    out_dir = os.path.join(HERE, f"du_lieu_seed_{seed}")
    
    print("=" * 60)
    print(f"BẮT ĐẦU QUY TRÌNH NHÂN BẢN DỮ LIỆU: SEED {seed}")
    print(f"Thư mục thô: {raw_dir}")
    print(f"Thư mục xuất: {out_dir}")
    print("=" * 60)
    
    os.makedirs(raw_dir, exist_ok=True)
    
    # Bước 1: Sinh dữ liệu thô
    gen_cmd = [
        "gen_synthetic_data_v5.py",
        "--n_lecturers", "360",
        "--years", "5",
        "--n_faculties", "6",
        "--seed", str(seed),
        "--out", raw_dir
    ]
    run_cmd(gen_cmd, f"1. Sinh dữ liệu thô v5 (seed={seed})")
    
    # Bước 2: Chuẩn hóa, ma trận và tạo MANIFEST
    make_cmd = [
        "make_dataset_v2.py",
        "--raw", raw_dir,
        "--out", out_dir,
        "--name", f"du_lieu_seed_{seed}"
    ]
    out_log = run_cmd(make_cmd, f"2. Chuẩn hóa ma trận và đóng gói dataset (seed={seed})")
    print(out_log)
    
    # Dọn dẹp thư mục raw trung gian để tiết kiệm dung lượng đĩa
    print(f"[CLEANUP] Dọn dẹp thư mục thô {raw_dir}...")
    shutil.rmtree(raw_dir, ignore_errors=True)
    
    print("=" * 60)
    print(f"HOÀN THÀNH XUẤT SẮC BỘ DỮ LIỆU SEED {seed}!")
    print(f"Đường dẫn: {out_dir}")
    print("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=43, help="Seed ngẫu nhiên cần sinh")
    args = parser.parse_args()
    
    build_seed_dataset(args.seed)

