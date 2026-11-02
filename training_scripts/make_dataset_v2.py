#!/usr/bin/env python3
"""Dựng bộ dữ liệu cố định du_lieu_co_dinh_v2 từ đầu ra thô của gen_synthetic_data_v5.py.
  python make_dataset_v2.py --raw ./raw --out ./du_lieu_co_dinh_v2
Các bước (cùng quy trình v1b): làm sạch tĩnh -> ma trận tác vụ-nhân sự (chỉ dùng việc ĐÃ HOÀN THÀNH trước ngày giao)
-> làm sạch động -> ghép CÙNG đặc trưng ma trận của bảng tĩnh vào bảng động (theo task_id + lecturer_id)
-> MANIFEST.json (SHA-256) + verify_data.py."""
import argparse, hashlib, json, os, shutil, subprocess, sys
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--raw", default="./raw"); ap.add_argument("--out", default="./du_lieu_co_dinh_v2")
ap.add_argument("--name", default="du_lieu_co_dinh_v2")
a = ap.parse_args()
here = os.path.dirname(os.path.abspath(__file__))
run = lambda *c: subprocess.run([sys.executable, *c], check=True, cwd=here)
raw = os.path.abspath(a.raw)
MC = ["lecturer_task_count", "lecturer_task_late_rate", "dept_task_late_rate", "task_matrix_source", "lecturer_task_late_lift"]

run("clean_data.py", "--input", f"{raw}/ml_training_set.csv", "--output", f"{raw}/ml_training_set_clean.csv")
run("build_task_personnel_matrix.py", "--data", f"{raw}/ml_training_set_clean.csv", "--out", raw)
run("clean_data.py", "--input", f"{raw}/ml_dynamic_set.csv", "--output", f"{raw}/ml_dynamic_set_clean.csv")

st = pd.read_csv(f"{raw}/ml_training_set_with_matrix.csv")
dy = pd.read_csv(f"{raw}/ml_dynamic_set_clean.csv")
dy = dy.drop(columns=[c for c in MC if c in dy.columns]).merge(
    st[["task_id", "lecturer_id"] + MC].drop_duplicates(["task_id", "lecturer_id"]), on=["task_id", "lecturer_id"], how="left")
miss = int(dy.lecturer_task_count.isna().sum())
assert miss == 0, f"{miss} dòng động không khớp ma trận tĩnh"
dy.to_csv(f"{raw}/ml_dynamic_set_clean_with_matrix.csv", index=False, encoding="utf-8-sig")
print(f"[động] {len(dy)} dòng, ghép ma trận khớp 100%")

d = os.path.join(a.out, "data"); shutil.rmtree(a.out, ignore_errors=True); os.makedirs(d)
for f in ["ml_training_set_with_matrix.csv", "ml_dynamic_set_clean_with_matrix.csv", "oracle_truth.csv", "task_personnel_matrix.csv",
          "task_personnel_matrix_wide.csv", "task_personnel_matrix_meta.json", "task_catalog_norm.csv", "data_dictionary.csv", "generation_report.json"]:
    shutil.copy(f"{raw}/{f}", f"{d}/{f}")
mp = f"{d}/task_personnel_matrix_meta.json"          # bỏ đường dẫn tuyệt đối của máy dựng
mj = json.load(open(mp, encoding="utf-8")); mj["output_matrix"] = "data/task_personnel_matrix.csv"; mj["output_enriched"] = "data/ml_training_set_with_matrix.csv"
json.dump(mj, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
shutil.copy(os.path.join(here, "verify_data.py"), a.out)
if os.path.exists(os.path.join(here, "README_DU_LIEU_v2.md")): shutil.copy(os.path.join(here, "README_DU_LIEU_v2.md"), os.path.join(a.out, "README_DU_LIEU.md"))

def split_info(df):
    t = pd.to_datetime(df.assigned_date); t1, t2 = t.quantile(0.60), t.quantile(0.75)
    tr, va, te = df[t <= t1], df[(t > t1) & (t <= t2)], df[t > t2]
    return dict(n_train=len(tr), n_val=len(va), n_test=len(te), train_end=str(t1.date()), val_end=str(t2.date()),
                late_train=round(float(tr.is_late.mean()), 4), late_val=round(float(va.is_late.mean()), 4), late_test=round(float(te.is_late.mean()), 4))
files = []
for root, _, fs in os.walk(a.out):
    for f in sorted(fs):
        p = os.path.join(root, f)
        if f in ("MANIFEST.json",): continue
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for ch in iter(lambda: fh.read(1 << 20), b""): h.update(ch)
        files.append(dict(path=os.path.relpath(p, a.out).replace(os.sep, "/"), sha256=h.hexdigest(), bytes=os.path.getsize(p)))
man = dict(dataset_name=a.name, note="Dữ liệu MÔ PHỎNG (seed 42). Giờ quy đổi lấy từ bảng định mức Cong-tac-khac-nam-hoc.xlsx; nhãn vẫn do bộ sinh quyết định.",
           split_rule="theo assigned_date: train <= phân vị 60%, validation (60%,75%], test > 75%",
           static=split_info(st), dynamic=split_info(dy), files=sorted(files, key=lambda x: x["path"]))
json.dump(man, open(os.path.join(a.out, "MANIFEST.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps({k: man[k] for k in ("static", "dynamic")}, ensure_ascii=False, indent=1))
