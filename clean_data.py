#!/usr/bin/env python3
"""
Làm sạch + kiểm định tập dữ liệu huấn luyện/dự đoán rủi ro trễ hạn (chạy MỘT lần trước khi train).

  python clean_data.py --input ./data/ml_training_set.csv --output ./data/ml_training_set_clean.csv
  python clean_data.py --input ./data/ml_dynamic_set.csv  --output ./data/ml_dynamic_set_clean.csv
  python clean_data.py --input viec_moi.csv --output viec_moi_clean.csv --inference     # dữ liệu cần dự đoán (không có nhãn)

Nguyên tắc: KHÔNG điền giá trị thiếu và KHÔNG xóa giá trị cực đoan hợp lệ (đó là tín hiệu cho mô hình);
chỉ loại bản ghi sai/trùng, chuẩn hóa văn bản, giới hạn đuôi dài, bỏ cột trùng thông tin và kiểm tra rò rỉ.
Dữ liệu cần dự đoán PHẢI đi qua cùng script này (với --inference) để có cùng các cột như lúc huấn luyện.
"""
import argparse, json, os, unicodedata
import numpy as np, pandas as pd

CFG = dict(
    id_cols=["task_id", "lecturer_id", "faculty", "assigned_date"],
    targets=["is_late", "late_vs_original_deadline", "late_vs_current_deadline"],
    core_required=["task_type", "complexity", "priority", "available_days", "expected_duration_days",
                   "deadline_pressure", "hist_count", "hist_late_rate", "active_tasks",
                   "workload_next_14d", "deadlines_next_7d"],
    caps={"deadline_pressure": 5.0, "workload_next_14d": 500.0, "active_tasks": 20, "active_high_priority_tasks": 15},
    log_cols=["available_days", "expected_duration_days"],            # thêm log1p, giữ nguyên cột gốc
    drop_pairs=[("working_days_available", "available_days"),         # (cột bỏ, cột giữ) nếu |r| > corr_thr
                ("estimated_effort_hours", "expected_duration_days"),
                ("course_count", "teaching_hours_semester")],
    corr_thr=0.90,
    missing_flag_cols=["converted_workload", "hist_avg_delay", "hist_early_rate", "hist_late_last5"],
    nonneg_cols=["available_days", "expected_duration_days", "hist_count", "active_tasks", "workload_next_14d",
                 "deadlines_next_7d", "deadlines_next_14d", "subtask_count", "dependency_count", "team_size", "tenure_days"],
    late_rate_range=(0.10, 0.35),
)


def norm_text(s):
    s2 = s.astype("object")
    f = lambda x: x if (x is None or (isinstance(x, float) and np.isnan(x)) or x is pd.NA) else \
        " ".join(unicodedata.normalize("NFC", str(x)).split())
    return s2.map(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default=None)
    ap.add_argument("--inference", action="store_true", help="dữ liệu không có cột nhãn")
    ap.add_argument("--add-log", action="store_true", help="thêm log1p của available_days, expected_duration_days (mặc định tắt)")
    a = ap.parse_args()
    out = a.output or os.path.splitext(a.input)[0] + "_clean.csv"
    rep = dict(input=a.input, output=out, steps={}, warnings=[])
    warn = lambda m: (rep["warnings"].append(m), print("  [CẢNH BÁO]", m))

    df = pd.read_csv(a.input)
    n0 = len(df); rep["rows_in"] = n0
    print(f"Đọc {n0} dòng, {df.shape[1]} cột từ {a.input}")

    # 1. Kiểm tra schema
    need = CFG["core_required"] + ([] if a.inference else ["is_late"])
    miss = [c for c in need if c not in df.columns]
    if miss:
        raise SystemExit(f"LỖI: thiếu cột bắt buộc: {miss}")
    if "assigned_date" in df.columns:
        df["assigned_date"] = pd.to_datetime(df["assigned_date"], errors="coerce")
    print("1. Schema: OK")

    # 2. Chuẩn hóa văn bản (NFC, bỏ khoảng trắng thừa)
    txt = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c]) and c not in ("assigned_date",)]
    for c in txt: df[c] = norm_text(df[c])
    print(f"2. Chuẩn hóa văn bản: {len(txt)} cột")

    # 3. Loại bản ghi trùng
    key = [c for c in ["task_id", "lecturer_id", "checkpoint_fraction"] if c in df.columns]
    d_full = int(df.duplicated().sum()); df = df.drop_duplicates()
    d_key = int(df.duplicated(key).sum()) if key else 0
    if key: df = df.drop_duplicates(key)
    rep["steps"]["duplicates_removed"] = dict(full_row=d_full, by_key=d_key, key=key)
    print(f"3. Trùng lặp: bỏ {d_full} dòng trùng hoàn toàn, {d_key} dòng trùng khóa {key}")

    # 4. Loại bản ghi sai nghiệp vụ
    bad = pd.Series(False, index=df.index); reasons = {}
    def flag(mask, name):
        nonlocal bad
        mask = mask.fillna(False); reasons[name] = int(mask.sum()); bad |= mask
    if "assigned_date" in df: flag(df.assigned_date.isna(), "assigned_date_khong_hop_le")
    flag(df.available_days < 1, "available_days_<1")
    flag(~df.hist_late_rate.between(0, 1) & df.hist_late_rate.notna(), "hist_late_rate_ngoai_[0,1]")
    for c in CFG["nonneg_cols"]:
        if c in df: flag(df[c] < 0, f"{c}_am")
    if not a.inference:
        for t in CFG["targets"]:
            if t in df: flag(~df[t].isin([0, 1]) & df[t].notna(), f"{t}_khong_phai_0/1")
        flag(df.is_late.isna(), "thieu_nhan")
    df = df[~bad].copy()
    rep["steps"]["invalid_rows_removed"] = dict(total=int(bad.sum()), reasons={k: v for k, v in reasons.items() if v})
    print(f"4. Sai nghiệp vụ: bỏ {int(bad.sum())} dòng {({k: v for k, v in reasons.items() if v}) or ''}")

    # 5. Giá trị thiếu: chỉ báo cáo + thêm cờ cho nhóm thiếu có ý nghĩa nghiệp vụ (KHÔNG điền)
    na = (df.isna().mean() * 100).round(2); na = na[na > 0]
    flags = []
    for c in CFG["missing_flag_cols"]:
        if c in df: df[f"{c}_missing"] = df[c].isna().astype(int); flags.append(f"{c}_missing")
    df["is_cold_start"] = (df.hist_count == 0).astype(int)
    rep["steps"]["missing_pct"] = na.to_dict(); rep["steps"]["flags_added"] = flags + ["is_cold_start"]
    print(f"5. Giá trị thiếu ở {len(na)} cột (giữ nguyên, thêm cờ: {flags + ['is_cold_start']})")

    # 6. Giới hạn đuôi dài + thêm cột log
    clipped = {}
    for c, cap in CFG["caps"].items():
        if c in df:
            n = int((df[c] > cap).sum()); clipped[c] = n
            df[c] = df[c].clip(upper=cap)
    if a.add_log:
        for c in CFG["log_cols"]:
            if c in df: df[f"log_{c}"] = np.log1p(df[c])
    rep["steps"]["clipped"] = clipped
    print(f"6. Giới hạn đuôi dài: {clipped} | cột log: {'bật' if a.add_log else 'tắt'}")

    # 7. Bỏ cột trùng thông tin
    dropped = []
    for drop, keep in CFG["drop_pairs"]:
        if drop in df and keep in df:
            r = df[drop].corr(df[keep])
            if abs(r) > CFG["corr_thr"]:
                df = df.drop(columns=drop); dropped.append(dict(drop=drop, keep=keep, corr=round(float(r), 3)))
    rep["steps"]["dropped_redundant"] = dropped
    print(f"7. Bỏ cột trùng thông tin: {[d['drop'] for d in dropped]}")

    # 8. Kiểm tra rò rỉ & tính nhất quán thời gian
    if {"lecturer_id", "assigned_date", "hist_count"} <= set(df.columns):
        s = df.sort_values(["lecturer_id", "assigned_date"])
        viol = int((s.groupby("lecturer_id").hist_count.diff() < 0).sum())
        first = s.groupby("lecturer_id").head(1)
        if viol: warn(f"hist_count giảm theo thời gian ở {viol} dòng -> nghi ngờ tính lịch sử sai")
        if "tenure_days" in df and ((df.hist_count > 0) & (df.tenure_days <= 0)).any():
            warn("Có dòng thâm niên 0 ngày nhưng đã có lịch sử công việc -> kiểm tra cách tính đặc trưng lịch sử")
        rep["steps"]["temporal_violations"] = viol
    banned = [c for c in ["status", "progress_pct_final", "actual_completion_date", "completed_date",
                          "delay_days", "delay_days_vs_original", "extension_requested", "extension_days"] if c in df.columns]
    if banned: warn(f"Cột có thể gây rò rỉ nhãn: {banned}")
    cold = float(df.is_cold_start.mean()); low = float((df.hist_count < 5).mean())
    n_low = int((df.hist_count < 5).sum())
    if n_low < 500: warn(f"Chỉ {n_low} dòng có lịch sử < 5 việc ({low:.1%}) -> chưa đủ để đánh giá giảng viên mới")
    rep["steps"]["cold_start"] = dict(hist0=round(cold, 4), hist_lt5=round(low, 4))
    print(f"8. Rò rỉ/thời gian: {len(rep['warnings'])} cảnh báo | cold-start {cold:.1%} | lịch sử<5: {low:.1%}")

    # 9. Nhãn
    if not a.inference:
        r = float(df.is_late.mean()); lo, hi = CFG["late_rate_range"]
        rep["late_rate"] = round(r, 4)
        if not lo <= r <= hi: warn(f"Tỉ lệ trễ {r:.1%} ngoài khoảng {lo:.0%}-{hi:.0%}")
        print(f"9. Nhãn: tỉ lệ trễ {r:.1%}")

    df.to_csv(out, index=False, encoding="utf-8-sig")
    rep["rows_out"] = len(df); rep["cols_out"] = df.shape[1]
    jp = os.path.splitext(out)[0] + "_report.json"
    json.dump(rep, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
    print(f"\nKết quả: {n0} -> {len(df)} dòng, {df.shape[1]} cột. Đã ghi {out} và {jp}")


if __name__ == "__main__":
    main()
