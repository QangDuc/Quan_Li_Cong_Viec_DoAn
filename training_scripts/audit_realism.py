#!/usr/bin/env python3
"""
KIỂM TRA ĐỘ THỰC TẾ của dữ liệu giả lập bằng cách đối chiếu thống kê tổng hợp với các khoảng kỳ vọng do nhóm nghiên cứu đặt ra (dict DEFAULT, đều là [giả định]).

  python audit_realism.py --data ./data      # so với khoảng kỳ vọng do nhóm nghiên cứu đặt ra (sửa dict DEFAULT nếu cần)

Gồm: thống kê biên (tỉ lệ trễ, khối lượng việc, tỉ lệ nhóm, gia hạn, độ trễ), kiểm tra hướng quan hệ (độ phức tạp, số việc đang mở, áp lực deadline),
ổn định theo năm/Khoa/tháng. KẾT QUẢ "ĐẠT" chỉ có nghĩa là nằm trong khoảng kỳ vọng — không chứng minh dữ liệu giống thực tế.
"""
import argparse, json, os
import numpy as np, pandas as pd

DEFAULT = {   # [giả định] khoảng kỳ vọng mặc định (lo, hi)
    "late_rate": (0.12, 0.28), "tasks_per_lecturer_year": (35, 110), "group_task_share": (0.20, 0.55),
    "extension_request_rate": (0.03, 0.15), "extension_approval_rate": (0.50, 0.85),
    "median_delay_days_when_late": (1, 8), "p90_delay_days_when_late": (7, 60),
    "month_end_deadline_share": (0.10, 0.35), "cold_start_share_hist_lt5": (0.008, 0.15),
}
LABEL = {"late_rate": "tỉ lệ trễ hạn", "tasks_per_lecturer_year": "số phân công / giảng viên / năm (trung vị)", "group_task_share": "tỉ lệ công việc nhóm",
         "extension_request_rate": "tỉ lệ yêu cầu gia hạn", "extension_approval_rate": "tỉ lệ gia hạn được duyệt",
         "median_delay_days_when_late": "số ngày trễ trung vị (khi trễ)", "p90_delay_days_when_late": "số ngày trễ phân vị 90 (khi trễ)",
         "month_end_deadline_share": "tỉ lệ hạn chót cuối tháng", "cold_start_share_hist_lt5": "tỉ lệ dòng lịch sử < 5 việc"}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--data", required=True); a = ap.parse_args()
    ml = pd.read_csv(f"{a.data}/ml_training_set.csv", parse_dates=["assigned_date"])
    ta = pd.read_csv(f"{a.data}/task_assignments.csv", parse_dates=["assigned_date"])
    tk = pd.read_csv(f"{a.data}/tasks.csv"); er = pd.read_csv(f"{a.data}/extension_requests.csv")
    ay = np.where(ml.assigned_date.dt.month >= 8, ml.assigned_date.dt.year, ml.assigned_date.dt.year - 1)
    ml["ay"] = ay; ta["ay"] = np.where(ta.assigned_date.dt.month >= 8, ta.assigned_date.dt.year, ta.assigned_date.dt.year - 1)
    late = ta[ta.late_vs_original_deadline == 1]
    m = {"late_rate": ml.is_late.mean(), "tasks_per_lecturer_year": ta.groupby(["lecturer_id", "ay"]).size().median(),
         "group_task_share": (tk.assignment_mode == "Group").mean(), "extension_request_rate": len(er) / len(ta),
         "extension_approval_rate": (er.status == "Đã duyệt").mean(), "median_delay_days_when_late": late.delay_days.median(),
         "p90_delay_days_when_late": late.delay_days.quantile(0.9),
         "month_end_deadline_share": ml.deadline_month_end.mean() if "deadline_month_end" in ml else np.nan,
         "cold_start_share_hist_lt5": (ml.hist_count < 5).mean()}
    tg = dict(DEFAULT); src = {k: "giả định" for k in DEFAULT}
    rows, n_ok = [], 0
    for k, v in m.items():
        lo, hi = tg[k]; ok = (not np.isnan(v)) and lo <= v <= hi; n_ok += ok
        rows.append(dict(chỉ_số=LABEL[k], giá_trị=round(float(v), 3) if v == v else None, khoảng_kỳ_vọng=f"{lo:.3g} - {hi:.3g}", nguồn=src[k], kết_quả="ĐẠT" if ok else "LỆCH"))
    print("=== A. THỐNG KÊ BIÊN ===\n" + pd.DataFrame(rows).to_string(index=False))

    chk = []
    def mono(name, s, up=True):
        v = s.values; ok = bool(np.all(np.diff(v) > -0.005)) if up else bool(np.all(np.diff(v) < 0.005))
        chk.append(dict(kiểm_tra=name, giá_trị=" -> ".join(f"{x:.2f}" for x in v), kết_quả="ĐẠT" if ok else "LỆCH"))
    mono("tỉ lệ trễ tăng theo độ phức tạp (Thấp->TB->Cao)", ml.groupby("complexity").is_late.mean().reindex(["Thấp", "Trung bình", "Cao"]))
    mono("tỉ lệ trễ tăng theo số việc đang mở (tứ phân vị)", ml.groupby(pd.qcut(ml.active_tasks.rank(method="first"), 4)).is_late.mean())
    mono("tỉ lệ trễ tăng theo áp lực deadline (tứ phân vị)", ml.groupby(pd.qcut(ml.deadline_pressure.rank(method="first"), 4)).is_late.mean())
    mono("tỉ lệ trễ tăng theo tỉ lệ trễ lịch sử (tứ phân vị)", ml.groupby(pd.qcut(ml.hist_late_rate.rank(method="first"), 4)).is_late.mean())
    cnt = ml.groupby("ay").size(); byy = ml.groupby("ay").is_late.mean()[cnt >= 0.5 * cnt.max()]; spread = byy.max() - byy.min()   # bỏ năm học chỉ có một phần dữ liệu
    chk.append(dict(kiểm_tra="ổn định theo năm học (chênh lệch tối đa <= 8 điểm %)", giá_trị=" / ".join(f"{x:.3f}" for x in byy.values), kết_quả="ĐẠT" if spread <= 0.08 else "LỆCH"))
    if "faculty" in ml:
        byf = ml.groupby("faculty").is_late.mean(); sp = byf.max() - byf.min()
        chk.append(dict(kiểm_tra="khác biệt giữa các Khoa (có khác nhau nhưng <= 12 điểm %)", giá_trị=" / ".join(f"{x:.3f}" for x in byf.values), kết_quả="ĐẠT" if 0.01 <= sp <= 0.12 else "LỆCH"))
    bym = ml.groupby(ml.assigned_date.dt.month).is_late.mean(); ratio = bym.max() / bym.min()
    chk.append(dict(kiểm_tra="có tính mùa vụ theo tháng (tỉ số cao nhất/thấp nhất trong 1.15-3.0)", giá_trị=f"{ratio:.2f}", kết_quả="ĐẠT" if 1.15 <= ratio <= 3.0 else "LỆCH"))
    per_lect = ml.groupby("lecturer_id").is_late.mean(); chk.append(dict(kiểm_tra="khác biệt giữa giảng viên (độ lệch chuẩn tỉ lệ trễ 0.05-0.20)", giá_trị=f"{per_lect.std():.3f}", kết_quả="ĐẠT" if 0.05 <= per_lect.std() <= 0.20 else "LỆCH"))
    miss = ml.isna().mean(); chk.append(dict(kiểm_tra="có giá trị thiếu (1-8% ở một số cột)", giá_trị=f"{(miss[miss > 0].max() if (miss > 0).any() else 0):.3f}", kết_quả="ĐẠT" if (miss > 0).any() and miss.max() <= 0.08 else "LỆCH"))
    print("\n=== B. KIỂM TRA HƯỚNG QUAN HỆ VÀ ĐỘ ỔN ĐỊNH ===\n" + pd.DataFrame(chk).to_string(index=False))
    tot = n_ok + sum(c["kết_quả"] == "ĐẠT" for c in chk); allc = len(rows) + len(chk)
    print(f"\nTổng: {tot}/{allc} mục ĐẠT. Lưu ý: ĐẠT chỉ nghĩa là nằm trong khoảng kỳ vọng GIẢ ĐỊNH của nhóm nghiên cứu, không chứng minh dữ liệu giống thực tế.")
    json.dump(dict(marginals={k: (None if v != v else float(v)) for k, v in m.items()}, checks=chk, passed=int(tot), total=int(allc)),
              open(f"{a.data}/audit_report.json", "w"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
