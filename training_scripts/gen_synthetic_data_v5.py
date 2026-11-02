#!/usr/bin/env python3
"""
Sinh dữ liệu giả lập công việc giảng viên -> huấn luyện mô hình dự đoán rủi ro trễ hạn.
Mọi tham số lấy từ khảo sát nghiệp vụ; mục [giả định] cần hiệu chỉnh bằng dữ liệu/phỏng vấn thật.

Phiên bản 5 (bộ dữ liệu v2) - căn cứ bảng định mức "Công tác khác" (file Cong-tac-khac-nam-hoc.xlsx, năm học 2023-2024):
  * Giờ quy đổi (converted_workload) của các loại việc có trong bảng định mức = định mức thật x số đơn vị (xem NORMS), không còn là khoảng giả định
  * Thêm 16 loại việc có trong bảng định mức (dự giờ, trực đề thi, trực phòng thí nghiệm, ngân hàng câu hỏi, ban tổ chức/giám khảo cuộc thi...)
  * Tách "Tham gia họp" thành 5 loại theo Sheet1 (Trực khoa, Họp khoa, Họp bộ môn, Họp giao ban, Tập huấn); chỉ tỉ lệ 7:4:7:4:2 lấy từ file, tổng tần suất là giả định
  * Hiệu chuẩn offset persona trên toàn bộ dữ liệu (v4 dùng mẫu thử 30% giảng viên)
  * CƠ CHẾ SINH NHÃN KHÔNG ĐỔI: converted_workload không đi vào điểm số trễ hạn; khác biệt so với v1b đến từ cơ cấu loại việc
  * Xuất thêm task_catalog_norm.csv: loại việc nào có căn cứ từ file định mức, loại nào vẫn là giả định
Phiên bản 4 - sát thực tế hơn và quy mô ~100.000 dòng (mặc định 360 giảng viên x 6 Khoa x 5 năm, bỏ 180 ngày khởi động):
  * Phân cấp Trường -> Khoa -> Bộ môn: mỗi Khoa/Bộ môn có mức trễ nền riêng + cú sốc theo năm
  * Hành vi giảng viên thay đổi theo thời gian (random walk) + hiệu ứng "kiệt sức" (trễ gần đây -> dễ trễ tiếp)
  * Công việc nhóm có cú sốc chung (trễ tương quan trong nhóm)
  * Hạn chót tập trung vào cuối tháng; thêm đặc trưng hist_late_last5, late_last_30d, deadline_month_end
  * Nhãn nhiễu (ghi nhận sai), độ trễ đuôi dài, thiếu tiến độ không ngẫu nhiên (người hay trễ ít cập nhật)
  * Độ lệch phân bố theo năm (drift): thay đổi hệ số tải việc và mức trễ nền
  * Hiệu chuẩn persona trên mẫu thử (pilot) để chạy nhanh ở quy mô lớn
  * Xuất oracle_truth.csv: xác suất trễ "thật" của từng dòng để kiểm chứng mô hình (evaluate_vs_truth.py)
Ghi chú: tất cả vẫn là [giả định]; dùng audit_realism.py để đối chiếu với số liệu tổng hợp thực của Khoa.

Phiên bản 3 - bổ sung so với v2 (ở cuối docstring):
  * Giảng viên gia nhập/nghỉ giữa chừng (cold-start thực sự) + tenure_days
  * Nhãn có quan hệ PHI TUYẾN (ngưỡng quá tải, bùng nổ deadline, tương tác) -> GBM có cơ hội vượt logistic
  * Tập theo tiến độ mô phỏng nhịp làm việc (pace) có "khởi đầu tốt rồi trễ" / "chậm rồi bắt kịp", không còn sinh từ nhãn
  * Mặc định 80 giảng viên x 4 năm học

Phiên bản 2 - cải tiến so với v1:
  * Trọng số mô hình logistic ẩn nằm trong CFG["weights"] (dễ chỉnh, có thể ghi đè bằng --config file.json)
  * Hiệu chỉnh offset THEO TỪNG PERSONA để tỉ lệ trễ từng nhóm bám khảo sát (tỉ lệ chung tự hình thành)
  * Nhãn tính riêng cho từng giảng viên (công việc nhóm không dùng chung nhãn)
  * Đặc trưng lịch sử tính tuần tự theo thời gian (không rò rỉ), thêm overdue_open_tasks
  * Báo cáo: AUC trần (biết cả yếu tố ẩn) và AUC thực tế (GBM, tách theo thời gian), Brier, hiệu chuẩn theo decile
  * Tùy chọn --snapshot: công việc chưa xong tại ngày chụp có trạng thái "Đang thực hiện/Quá hạn", loại khỏi tập huấn luyện
  * Xuất data_dictionary.csv và generation_report.json

Chạy:  python gen_synthetic_data_v4.py --n_lecturers 360 --years 5 --n_faculties 6 --seed 42 --out ./data
       python gen_synthetic_data.py --snapshot 2026-06-30 --config my_config.json
"""
import argparse, os, json, time
import numpy as np, pandas as pd

# ============================== CẤU HÌNH ==============================
CFG = dict(
    start_year=2023,              # năm học đầu: 15/08/2023 -> 14/08/2024
    tasks_per_lect_year=38,       # [giả định] số công việc chủ trì / GV / năm học
    overall_late_range=(0.15, 0.25),   # khoảng hợp lý theo khảo sát; chỉ dùng để cảnh báo
    noise_sd=1.4,                 # nhiễu ẩn của logit -> không tách được hoàn hảo
    pressure_median=0.75,         # median(expected_duration / available_days) [giả định]
    pressure_sigma=0.45,
    outlier_rate=0.03,            # tỉ lệ giao gấp bất thường
    missing_rate=0.025,
    late_join_rate=0.45, leave_rate=0.12, onboarding_ramp_days=90,   # [giả định] biến động nhân sự
    # --- v4: phân cấp, thay đổi theo thời gian, nhóm, nhãn nhiễu, drift [giả định] ---
    n_faculties=6, fac_sd=0.25, fac_year_sd=0.20, dept_sd=0.15,      # độ lệch chuẩn hiệu ứng Khoa / Khoa x năm / Bộ môn
    lect_year_sd=0.15,                                               # bước ngẫu nhiên hành vi giảng viên theo năm
    task_shock_sd=0.50,                                              # cú sốc chung của công việc nhóm
    label_noise_fn=0.02, label_noise_fp=0.03,                        # trễ bị ghi nhận đúng hạn / đúng hạn bị ghi nhận trễ
    drift_intercept=[0.0, 0.0, 0.20, -0.10, 0.15],                   # mức trễ nền theo năm học (drift)
    drift_active_mult=[1.0, 1.0, 1.15, 1.30, 1.30],                  # hệ số tác động của số việc đang mở theo năm
    snap_prob_hard=0.55, snap_prob_admin=0.35, snap_prob_other=0.15, # xác suất hạn chót rơi vào cuối tháng
    hist_prior_rate=0.20, hist_prior_strength=3,   # làm mượt tỉ lệ trễ lịch sử (cold start)
    accreditation_windows=[("2024-09-01", "2024-12-15"), ("2026-09-01", "2026-12-15")],  # [giả định] đợt kiểm định
    departments=["Công nghệ phần mềm", "Hệ thống thông tin", "Khoa học máy tính", "Mạng máy tính"],
)

# Trọng số logit của mô hình ẩn sinh nhãn [giả định] - mỗi hệ số gắn với một nhận định trong khảo sát phần 5
CFG["weights"] = dict(
    complexity=0.55,        # mỗi bậc độ phức tạp
    log_pressure=1.3,       # log(expected_duration / available_days)
    subtask=0.07, dependency=0.14, ext_input=0.45,
    holiday=0.25, hard_deadline=-0.25, formal_channel=-0.15, accreditation=0.30,
    manager_urgent=0.40, experience=-0.02,
    active=0.09, d7=0.15, overdue=0.15, workload14=0.005, teaching=0.004,
    hist_late=0.8,          # tác động trực tiếp của hành vi lịch sử (so với 0.2)
    interaction=0.20,       # complexity x áp lực x tải
    burnout=0.25,           # mỗi việc trễ trong 30 ngày qua (tối đa 3) làm tăng rủi ro
    # --- v3: quan hệ phi tuyến [giả định] ---
    overload_over=8, overload_slope=0.30,   # vượt 8 việc đang mở: rủi ro tăng nhanh (hiệu ứng ngưỡng)
    crunch=0.80,                            # >=3 hạn trong 7 ngày + việc phức tạp cao
    mgr_peak=0.50,                          # quản lý trong mùa cao điểm
    junior=0.40, senior=0.15,               # <2 năm hoặc >25 năm kinh nghiệm (không đơn điệu)
    newjoin=0.30,                           # <90 ngày kể từ khi vào Khoa
    hist_x_pressure=0.60,                   # người hay trễ + áp lực cao
)

# Persona: (tỉ lệ, tỉ lệ trễ cơ bản, hệ số tải việc, giờ giảng/kỳ, số SV hướng dẫn TB)  -- khảo sát phần 6
PERSONAS = {
    "P1_on_dinh":      (0.25, 0.075, 1.00, 190, 3.0),
    "P2_tre_tai_cao":  (0.20, 0.230, 1.25, 240, 4.0),
    "P3_nghien_cuu":   (0.15, 0.170, 1.10, 150, 3.0),
    "P4_kiem_nhiem":   (0.15, 0.250, 1.30, 120, 2.0),
    "P5_giang_day":    (0.15, 0.180, 1.15, 270, 6.0),
    "P6_tai_nhe":      (0.05, 0.070, 0.70, 140, 1.5),
    "P7_de_qua_tai":   (0.05, 0.370, 1.30, 230, 5.0),
}

SS, NT, MT, FE, GS, GP, SU = ("semester_start", "normal_teaching", "midterm", "final_exam",
                              "grade_submission", "graduation_project", "summer")
PERIOD_W = {SS: 1.2, NT: 0.9, MT: 1.0, FE: 1.6, GS: 1.4, GP: 1.5, SU: 0.5}     # mật độ giao việc
PERIOD_Z = {SS: .15, NT: 0, MT: .25, FE: .55, GS: .35, GP: .5, SU: -.15}       # tác động lên logit trễ
PRIORITIES = ["Thấp", "Trung bình", "Cao", "Khẩn cấp"]
ADMIN_GROUPS = {"Hành chính", "Đào tạo", "Đảm bảo chất lượng", "Hội đồng", "Đoàn thể"}
PRIORITY_Z = [0.20, 0.0, -0.20, -0.35]   # hiệu ứng "tập trung xử lý" (ngược với áp lực giao gấp)
CHANNELS = ["Hệ thống", "Email", "Họp", "Zalo/Teams", "Trực tiếp"]


# ============== ĐỊNH MỨC GIỜ (từ file Cong-tac-khac-nam-hoc.xlsx, sheet KL_CT#) ==============
# khóa: (STT mục trong bảng, định mức nguyên văn, hàm tính giờ(rng, độ phức tạp, quy mô nhóm))
# Số đơn vị (số tín chỉ, số bài, số buổi, số ca...) là GIẢ ĐỊNH của bộ sinh; chỉ đơn giá giờ lấy từ file.
def _u(r, lo, hi): return int(r.integers(lo, hi + 1))
NORMS = {
 "hop":       (9,  "04 giờ/buổi họp",                       lambda r, cx, t: 4.0),
 "truc_khoa": (11, "04 giờ/buổi (trực đơn vị)",             lambda r, cx, t: 4.0),
 "tap_huan":  (45, "04 giờ/buổi học (bồi dưỡng do Trường tổ chức)", lambda r, cx, t: 4.0 * _u(r, 1, 2)),
 "boi_duong": (43, "04 giờ/buổi học",                       lambda r, cx, t: 4.0 * _u(r, 1, 5)),
 "du_gio":    (7,  "02 giờ/tiết dự giờ",                    lambda r, cx, t: 2.0 * _u(r, 1, 4)),
 "cai_tien":  (8,  "30 giờ/nội dung cải tiến/học phần",     lambda r, cx, t: 30.0 * _u(r, 1, 2)),
 "truc_ptn":  (11, "04 giờ/buổi",                           lambda r, cx, t: 4.0 * _u(r, 1, 3)),
 "thuc_te":   (12, "04 giờ/buổi",                           lambda r, cx, t: 4.0 * _u(r, 1, 3)),
 "truc_de":   (20, "04 giờ/ca thi",                         lambda r, cx, t: 4.0 * _u(r, 1, 3)),
 "coi_thi":   (19, "01 giờ/ca thi",                         lambda r, cx, t: 1.0 * _u(r, 1, 3)),
 "de_thi":    (15, "24 (trắc nghiệm) | 08 (tự luận) | 08 (bán trắc nghiệm) | 16 (vấn đáp) giờ/đề/đợt thi",
                   lambda r, cx, t: float(r.choice([24, 8, 8, 16], p=[.15, .55, .20, .10]))),
 "cham_thi":  (22, "0,6 giờ/10 bài/GV",                     lambda r, cx, t: round(0.6 * _u(r, 40, 200) / 10, 2)),
 "cham_klt":  (24, "0,75 giờ/bài/GV",                       lambda r, cx, t: round(0.75 * _u(r, 2, 6), 2)),
 "nhch":      (26, "0,15 giờ/câu hỏi",                      lambda r, cx, t: round(0.15 * _u(r, 100, 400), 2)),
 "du_tru":    (27, "16 giờ/tín chỉ/học phần",               lambda r, cx, t: 16.0 * _u(r, 1, 4)),
 "tu_van_ts": (28, "04 giờ/buổi",                           lambda r, cx, t: 4.0 * _u(r, 1, 2)),
 "ho_tro_le": (29, "04 giờ/buổi",                           lambda r, cx, t: 4.0),
 "dc_hp":     (3,  "15 giờ/tín chỉ (đề cương mới) | 05 giờ/tín chỉ (chỉnh sửa), đại học",
                   lambda r, cx, t: (15.0 if r.random() < .4 else 5.0) * _u(r, 2, 4)),
 "hp_moi":    (3,  "15 giờ/tín chỉ (đại học) | 30 giờ/tín chỉ (thạc sĩ)",
                   lambda r, cx, t: (30.0 if r.random() < .2 else 15.0) * _u(r, 2, 4)),
 "ctdt":      (2,  "396 giờ/chương trình/tổng số người tham gia", lambda r, cx, t: round(396.0 / max(1, t), 1)),
 "minh_chung":(30, "40 giờ/năm học (thành viên tổ đảm bảo chất lượng)", lambda r, cx, t: 40.0),
 "tu_danh_gia":(31, "220 giờ/năm học (hội đồng tự đánh giá/nhóm chuyên trách)", lambda r, cx, t: 220.0),
 "dang_doan": (38, "04 giờ/buổi tham gia",                  lambda r, cx, t: 4.0 * _u(r, 1, 3)),
 "ket_noi_dn":(51, "40 giờ/năm học",                        lambda r, cx, t: 40.0),
 "hoi_thao":  (10, "04 giờ/buổi",                           lambda r, cx, t: 4.0 * _u(r, 1, 3)),
 "btc_thi":   (34, "30 giờ/cuộc thi",                       lambda r, cx, t: 30.0),
 "gk_thi":    (35, "04 giờ/buổi tham dự",                   lambda r, cx, t: 4.0 * _u(r, 1, 3)),
 "dua_doan":  (32, "04 giờ/buổi",                           lambda r, cx, t: 4.0 * _u(r, 1, 3)),
 "tro_giang": (47, "15 giờ/giảng viên/môn học",             lambda r, cx, t: 15.0),
 "van_ban":   (50, "25 giờ/văn bản",                        lambda r, cx, t: 25.0 * _u(r, 1, 2)),
 "website":   (46, "220 giờ/năm học",                       lambda r, cx, t: 220.0),
 "clb":       (52, "100 giờ/năm học",                       lambda r, cx, t: 100.0),
}

def norm_hours(key, r, cx, team):
    return round(float(NORMS[key][2](r, cx, team)), 2)

# (tên, nhóm, cấp giao, I/G/IG, tần suất, (min,typ,max) ngày, xác suất độ phức tạp L/M/H,
#  giai đoạn cao điểm, (giờ quy đổi min,max)|None, giờ công/ngày, deadline cứng)
TYPES = [
 ("Chuẩn bị bài giảng/cập nhật slide","Giảng dạy",["Bộ môn","Khoa"],"I",3.0,(1,3,10),(.25,.55,.2),[SS,SU],(3,8),3,0),
 ("Giảng dạy học phần","Giảng dạy",["Bộ môn","Khoa"],"I",2.0,(56,105,140),(.2,.6,.2),[SS],(30,60),2,0),
 ("Chuẩn bị bài thực hành/lab CNTT","Giảng dạy",["Bộ môn"],"IG",2.0,(1,3,7),(.1,.5,.4),[SS,NT],(3,10),4,0),
 ("Chấm bài tập/đồ án môn học","Giảng dạy",["Bộ môn"],"I",3.0,(1,4,10),(.2,.6,.2),[MT,NT],(4,10),3,0),
 ("Hướng dẫn đồ án môn học","Hướng dẫn SV",["Bộ môn"],"I",1.5,(30,90,120),(.2,.6,.2),[NT,MT],(4,8),1.5,0),
 ("Hướng dẫn khóa luận/đồ án tốt nghiệp","Hướng dẫn SV",["Khoa","Bộ môn"],"I",1.2,(60,120,180),(0,.25,.75),[SS,NT,GP],(15,30),1.5,0),
 ("Hướng dẫn luận văn cao học","Hướng dẫn SV",["Khoa","Trường"],"I",0.3,(90,180,365),(0,.2,.8),[SS],(20,40),1.2,0),
 ("Đề xuất/đăng ký đề tài NCKH","Nghiên cứu khoa học",["Khoa","Trường"],"IG",0.7,(5,14,30),(0,.3,.7),[SS,SU],(5,15),3,0),
 ("Thực hiện đề tài NCKH","Nghiên cứu khoa học",["Khoa","Trường"],"G",0.5,(90,270,730),(0,.2,.8),[SS,NT],None,2,0),
 ("Viết bài báo khoa học","Nghiên cứu khoa học",["Khoa"],"IG",0.8,(14,60,180),(0,.3,.7),[SU,NT],None,2.5,0),
 ("Sửa bài theo phản biện","Nghiên cứu khoa học",["Khoa"],"G",0.4,(3,14,45),(0,.3,.7),[SU,NT],None,4,0),
 ("Ra đề thi","Khảo thí",["Bộ môn","Khoa"],"IG",2.0,(2,5,14),(.1,.6,.3),[MT,FE],"de_thi",4,1),
 ("Phản biện/duyệt đề thi","Khảo thí",["Bộ môn"],"G",1.5,(1,3,7),(.3,.6,.1),[MT,FE],(1,2),3,1),
 ("Coi thi","Khảo thí",["Khoa","Trường"],"IG",2.5,(1,1,1),(.9,.1,0),[MT,FE],"coi_thi",4,1),
 ("Chấm thi cuối kỳ","Khảo thí",["Bộ môn","Khoa"],"IG",2.0,(2,5,14),(.15,.6,.25),[FE,GS],"cham_thi",4,1),
 ("Chấm/phản biện khóa luận","Khảo thí",["Khoa"],"I",0.9,(2,5,10),(0,.35,.65),[GP],"cham_klt",4,1),
 ("Nhập/nộp điểm","Đào tạo",["Khoa","Trường"],"I",2.0,(1,2,5),(.8,.2,0),[GS],(0.5,1),2,1),
 ("Cố vấn học tập","Cố vấn học tập",["Khoa"],"I",0.6,(120,180,270),(.2,.6,.2),[SS],(10,20),0.4,0),
 ("Xử lý cảnh báo học vụ của SV","Cố vấn học tập",["Khoa","Trường"],"I",1.0,(1,3,7),(.2,.6,.2),[GS,SS],(1,3),2,0),
 ("Họp lớp/CVHT định kỳ","Cố vấn học tập",["Khoa"],"I",1.0,(1,1,2),(.9,.1,0),[SS,MT],(1,2),4,0),
 ("Họp Bộ môn","Hành chính",["Bộ môn"],"G",1.75,(1,1,2),(.9,.1,0),[],"hop",3,0),
 ("Họp Khoa","Hành chính",["Khoa"],"G",1.0,(1,1,2),(.9,.1,0),[],"hop",3,0),
 ("Họp giao ban","Hành chính",["Khoa"],"G",1.0,(1,1,2),(.9,.1,0),[],"hop",3,0),
 ("Tập huấn của Trường","Hành chính",["Trường"],"G",0.5,(1,1,3),(.8,.2,0),[SU],"tap_huan",3,0),
 ("Trực khoa","Hành chính",["Khoa"],"I",1.75,(1,1,2),(.9,.1,0),[],"truc_khoa",3,0),
 ("Soạn báo cáo/tổng hợp số liệu","Hành chính",["Khoa","Trường"],"IG",2.0,(1,5,14),(.15,.6,.25),[GS,SU],(3,8),3,0),
 ("Tham gia hội đồng chuyên môn","Hội đồng",["Khoa","Trường"],"G",1.2,(1,3,10),(.1,.55,.35),[GP,FE],(2,4),3,0),
 ("Công tác Đảng/đoàn thể/công đoàn","Đoàn thể",["Khoa","Trường"],"G",1.0,(1,3,10),(.5,.4,.1),[],"dang_doan",2,0),
 ("Thu thập minh chứng kiểm định","Đảm bảo chất lượng",["Khoa","Trường"],"G",0.8,(7,30,90),(0,.3,.7),[],"minh_chung",2,0),
 ("Viết báo cáo tự đánh giá","Đảm bảo chất lượng",["Khoa","Trường"],"G",0.5,(30,90,180),(0,.2,.8),[],"tu_danh_gia",2,0),
 ("Chuẩn bị tiếp đoàn đánh giá","Đảm bảo chất lượng",["Khoa","Trường"],"G",0.4,(7,21,60),(0,.3,.7),[],(5,20),3,1),
 ("Xây dựng/cập nhật đề cương học phần","CTĐT",["Bộ môn","Khoa"],"IG",1.0,(5,15,30),(0,.55,.45),[SU,SS],"dc_hp",2.5,0),
 ("Rà soát chương trình đào tạo","CTĐT",["Khoa","Trường"],"G",0.4,(30,90,180),(0,.3,.7),[SU],"ctdt",1.5,0),
 ("Xây dựng học phần mới","CTĐT",["Bộ môn","Khoa"],"G",0.4,(14,45,90),(0,.3,.7),[SU],"hp_moi",2,0),
 ("Ngày hội tư vấn tuyển sinh","Tuyển sinh",["Trường","Khoa"],"G",0.8,(1,3,7),(.5,.4,.1),[GP,SU],"tu_van_ts",3,1),
 ("Tư vấn/hướng nghiệp sinh viên","Hướng nghiệp",["Khoa","Trường"],"IG",0.8,(1,5,14),(.2,.6,.2),[GP],(2,6),2,0),
 ("Kết nối doanh nghiệp/thực tập","Hướng nghiệp",["Khoa"],"IG",0.8,(3,14,30),(.1,.6,.3),[SS,NT],"ket_noi_dn",2,0),
 ("Hội thảo/chuyên đề cho cộng đồng","Phục vụ cộng đồng",["Khoa","Trường"],"IG",0.6,(3,10,30),(.1,.6,.3),[SU],"hoi_thao",3,0),
 ("Hoạt động chuyển giao/tư vấn CNTT","Phục vụ cộng đồng",["Khoa","Trường"],"G",0.3,(14,60,180),(0,.3,.7),[],None,2,0),
 # --- Loại việc bổ sung theo bảng định mức "Công tác khác" (khóa trong NORMS; STT mục xem task_catalog_norm.csv) ---
 ("Dự giờ đồng nghiệp","Giảng dạy",["Bộ môn"],"I",0.8,(3,10,30),(.7,.3,0),[MT,NT],"du_gio",1.5,0),
 ("Cải tiến đổi mới phương pháp giảng dạy","Giảng dạy",["Bộ môn","Khoa"],"I",0.3,(30,75,120),(0,.4,.6),[SS],"cai_tien",2,0),
 ("Trực đề thi cuối kỳ","Khảo thí",["Khoa"],"I",1.0,(1,1,1),(.9,.1,0),[FE],"truc_de",4,1),
 ("Trực phòng thí nghiệm/bảo trì thiết bị","Giảng dạy",["Bộ môn"],"I",0.8,(1,2,5),(.6,.35,.05),[NT],"truc_ptn",4,0),
 ("Đi thực tế tại cơ sở/doanh nghiệp","Hướng nghiệp",["Khoa","Bộ môn"],"IG",0.5,(1,3,14),(.4,.5,.1),[NT,GP],"thuc_te",4,0),
 ("Xây dựng ngân hàng câu hỏi thi","Khảo thí",["Bộ môn","Khoa"],"IG",0.6,(7,21,60),(.1,.5,.4),[SU,SS],"nhch",3,0),
 ("Dự trù dụng cụ, vật tư, thiết bị","Hành chính",["Bộ môn"],"I",0.5,(3,10,30),(.3,.6,.1),[SS],"du_tru",3,0),
 ("Hỗ trợ lễ do Trường/Khoa tổ chức","Hành chính",["Khoa","Trường"],"G",0.7,(1,2,5),(.8,.2,0),[],"ho_tro_le",4,1),
 ("Ban tổ chức cuộc thi sinh viên","Hướng dẫn SV",["Khoa","Trường"],"G",0.4,(14,30,60),(.1,.5,.4),[NT],"btc_thi",2,1),
 ("Ban giám khảo/trọng tài cuộc thi sinh viên","Hướng dẫn SV",["Khoa","Trường"],"G",0.4,(1,2,5),(.8,.2,0),[NT],"gk_thi",4,1),
 ("Đưa đoàn sinh viên đi tham quan/thực tập/thi","Hướng dẫn SV",["Khoa"],"IG",0.4,(1,3,10),(.4,.5,.1),[NT],"dua_doan",4,0),
 ("Tham gia bồi dưỡng chuyên môn/nghiệp vụ","Hành chính",["Bộ môn","Khoa","Trường"],"I",0.8,(1,5,30),(.5,.4,.1),[SU],"boi_duong",4,0),
 ("Hướng dẫn, đánh giá giảng viên trợ giảng","Giảng dạy",["Bộ môn"],"I",0.3,(30,90,120),(.2,.6,.2),[SS],"tro_giang",1.5,0),
 ("Soạn văn bản/báo cáo góp ý theo yêu cầu của Trường","Hành chính",["Khoa","Trường"],"IG",0.5,(3,10,30),(.1,.6,.3),[],"van_ban",3,0),
 ("Phụ trách website đơn vị","Hành chính",["Khoa"],"I",0.1,(180,300,365),(0,.6,.4),[SS],"website",0.5,0),
 ("Phụ trách CLB học thuật/NCKH sinh viên","Hướng dẫn SV",["Khoa"],"I",0.12,(180,300,365),(0,.6,.4),[SS],"clb",0.5,0),
]

# Ngày nghỉ [giả định]: lễ cố định + Tết âm lịch xấp xỉ
HOLIDAYS = []
for y in range(2023, 2029):
    HOLIDAYS += [f"{y}-01-01", f"{y}-04-30", f"{y}-05-01", f"{y}-09-02"]
for a, b in [("2024-02-08", "2024-02-14"), ("2025-01-25", "2025-02-02"), ("2026-02-14", "2026-02-22"), ("2027-02-04", "2027-02-10"), ("2028-01-24", "2028-01-30")]:
    HOLIDAYS += [str(d.date()) for d in pd.date_range(a, b)]
HOL = np.array(HOLIDAYS, dtype="datetime64[D]")


# ============================== TIỆN ÍCH ==============================
def logit(p): return np.log(p / (1 - p))
def sigmoid(x): return 1 / (1 + np.exp(-x))

def academic_period(d):
    k = d.month * 100 + d.day
    if 815 <= k <= 930: return SS
    if 1001 <= k <= 1031: return NT
    if 1101 <= k <= 1130: return MT
    if k >= 1201 or k <= 115: return FE
    if 116 <= k <= 131: return GS
    if 201 <= k <= 315: return SS
    if 316 <= k <= 405: return NT
    if 406 <= k <= 430: return MT
    if 501 <= k <= 531: return GP
    if 601 <= k <= 630: return FE
    if 701 <= k <= 715: return GS
    return SU

def semester(d):
    k = d.month * 100 + d.day
    if k >= 815 or k <= 131: return "HK1"
    if 201 <= k <= 715: return "HK2"
    return "Summer"

def ay_start(d):
    y = d.year if (d.month, d.day) >= (8, 15) else d.year - 1
    return pd.Timestamp(y, 8, 15)

def in_accreditation(d):
    return any(pd.Timestamp(a) <= d <= pd.Timestamp(b) for a, b in CFG["accreditation_windows"])

def tri(rng, lo, mode, hi):
    return lo if hi <= lo else rng.triangular(lo, mode, hi)


# ============================== GIẢNG VIÊN ==============================
def make_lecturers(n, years, rng):
    names = list(PERSONAS)
    probs = np.array([PERSONAS[k][0] for k in names])
    counts = np.floor(probs * n).astype(int)
    for i in np.argsort(-(probs * n - counts))[: n - counts.sum()]:
        counts[i] += 1
    personas = rng.permutation(np.repeat(names, counts))
    rows, loads = [], []
    nf = max(1, min(CFG["n_faculties"], n)); fac_codes = [f"K{k + 1:02d}" for k in range(nf)]
    facs = rng.permutation(np.resize(fac_codes, n))
    fo = {f: float(rng.normal(0, CFG["fac_sd"])) for f in fac_codes}
    fy = {(f, y): float(rng.normal(0, CFG["fac_year_sd"])) for f in fac_codes for y in range(years)}
    do = {}
    for i, p in enumerate(personas, 1):
        fac = facs[i - 1]; dep_name = f"{fac} - {rng.choice(CFG['departments'])}"
        if dep_name not in do: do[dep_name] = float(rng.normal(0, CFG["dept_sd"]))
        rank = rng.choice(["Giảng viên", "Giảng viên chính", "Phó giáo sư"], p=[.65, .28, .07])
        degree = {"Giảng viên": rng.choice(["Thạc sĩ", "Tiến sĩ"], p=[.6, .4]),
                  "Giảng viên chính": rng.choice(["Thạc sĩ", "Tiến sĩ"], p=[.1, .9]),
                  "Phó giáo sư": "Tiến sĩ"}[rank]
        exp = rng.integers(0, 7) if p == "P2_tre_tai_cao" else rng.integers(3, 31)
        if p == "P4_kiem_nhiem":
            mgr = rng.choice(["Trưởng bộ môn", "Phó trưởng bộ môn", "Phó trưởng khoa"], p=[.3, .45, .25])
        else:
            mgr = "Phó trưởng bộ môn" if rng.random() < .04 else "Không"
        total = 365 * years
        t0 = pd.Timestamp(CFG["start_year"], 8, 15)
        join_off = int(rng.integers(60, max(61, int(total * 0.93)))) if rng.random() < CFG["late_join_rate"] else 0
        leave_off = total - 1
        lo = max(join_off + 120, total // 2)
        if years >= 2 and lo < total - 1 and rng.random() < CFG["leave_rate"]:
            leave_off = int(rng.integers(lo, total))
        tenure_offset = -join_off if join_off > 0 else int(exp * 365 * rng.uniform(.3, 1.0))
        rows.append(dict(lecturer_id=f"GV{i:03d}", full_name=f"Giảng viên giả lập {i:03d}",
                         join_date=t0 + pd.Timedelta(days=join_off), leave_date=t0 + pd.Timedelta(days=leave_off),
                         tenure_offset=tenure_offset,
                         faculty=fac, department=dep_name, fac_offset=fo[fac], dept_offset=do[dep_name], academic_rank=rank, degree=degree,
                         years_experience_at_start=int(exp), management_role=mgr, persona_latent=p,
                         random_effect=float(rng.normal(0, 0.35))))
        ye = 0.0
        for y in range(years):
            ye += rng.normal(0, CFG["lect_year_sd"])
            th = max(60, rng.normal(PERSONAS[p][3], 25))
            cc = int(np.clip(round(th / 45 + rng.normal(0, .5)), 1, 8))
            loads.append(dict(lecturer_id=f"GV{i:03d}", academic_year=f"{CFG['start_year']+y}-{CFG['start_year']+y+1}",
                              year_idx=y, year_effect=round(ye, 4), fac_year_shock=fy[(fac, y)], teaching_hours_semester=round(th, 1), course_count=cc,
                              student_count=int(cc * rng.uniform(35, 75)),
                              supervised_student_count=int(rng.poisson(PERSONAS[p][4]))))
    return pd.DataFrame(rows), pd.DataFrame(loads)


# ============================== KHUNG CÔNG VIỆC (độc lập nhãn) ==============================
def make_skeleton(lect, loads, years, rng):
    freq = np.array([t[4] for t in TYPES])
    tprob = {}
    for per in PERIOD_W:
        for acc in (0, 1):
            w = freq.copy()
            for k, t in enumerate(TYPES):
                if per in t[7]: w[k] *= 4
                if acc and t[1] == "Đảm bảo chất lượng": w[k] *= 4
            tprob[(per, acc)] = w / w.sum()

    ids = lect.lecturer_id.tolist()
    dept = dict(zip(lect.lecturer_id, lect.department))
    jdate, ldate = dict(zip(lect.lecturer_id, lect.join_date)), dict(zip(lect.lecturer_id, lect.leave_date))
    t0 = pd.Timestamp(CFG["start_year"], 8, 15)
    ycache = {}
    for y in range(years):                                   # tính trước lịch từng năm học (nhanh hơn khi quy mô lớn)
        dys = pd.date_range(pd.Timestamp(CFG["start_year"] + y, 8, 15), periods=365)
        pr = [academic_period(d) for d in dys]
        w0 = np.array([PERIOD_W[p] for p in pr]) * np.where(dys.dayofweek >= 5, 0.1, 1.0)
        w0 = w0 * np.where(np.isin(dys.values.astype("datetime64[D]"), HOL), 0.1, 1.0)
        ycache[y] = (dys, pr, w0, [int(in_accreditation(d)) for d in dys])
    rows, tid = [], 0
    for _, L in lect.iterrows():
        mult = PERSONAS[L.persona_latent][2]
        for y in range(years):
            days, per, w0, accs = ycache[y]; w = w0.copy()
            jd, ld = L.join_date, L.leave_date
            active = ((days >= jd) & (days <= ld)).astype(float)
            if active.sum() == 0: continue
            if jd > t0:
                active = active * np.clip(0.3 + 0.7 * np.asarray((days - jd).days) / CFG["onboarding_ramp_days"], 0.3, 1.0)
            w = w * active
            if w.sum() == 0: continue
            frac = float((active > 0).sum()) / 365
            w /= w.sum()
            for di in rng.choice(365, size=rng.poisson(CFG["tasks_per_lect_year"] * mult * frac), p=w):
                d, p = days[di], per[di]
                acc = accs[di]
                k = rng.choice(len(TYPES), p=tprob[(p, acc)])
                (name, grp, levels, mode, _, (dmin, dtyp, dmax), cxp, _, hrs, inten, hard) = TYPES[k]
                cx = rng.choice(3, p=cxp)
                dur = tri(rng, dmin, dtyp, dmax) * (0.85, 1.0, 1.2)[cx]
                pr = np.exp(rng.normal(np.log(CFG["pressure_median"]), CFG["pressure_sigma"]))
                if rng.random() < CFG["outlier_rate"]: pr *= rng.uniform(2, 4)
                avail = max(1, int(round(dur / pr)))
                pressure = dur / avail
                orig = d + pd.Timedelta(days=avail)
                snap_p = CFG["snap_prob_hard"] if hard else (CFG["snap_prob_admin"] if grp in ADMIN_GROUPS else CFG["snap_prob_other"])
                me_flag = 0
                if rng.random() < snap_p:                      # hạn chót tập trung vào cuối tháng (ngày làm việc gần nhất)
                    cand = d + pd.offsets.MonthEnd(0)
                    while (cand - d).days < max(1, int(round(0.6 * avail))): cand = cand + pd.offsets.MonthEnd(1)
                    if (cand - d).days <= 1.8 * avail + 2:
                        while cand.dayofweek >= 5: cand -= pd.Timedelta(days=1)
                        if cand > d:
                            orig = cand; avail = (cand - d).days; pressure = dur / avail; me_flag = 1
                wd = int(np.busday_count(d.date(), orig.date(), holidays=HOL))
                hol_in = int(np.isin(pd.date_range(d, orig).values.astype("datetime64[D]"), HOL).any())
                pri_p = [.08, .45, .33, .14] if pressure > 1.2 else [.15, .55, .25, .05]
                prio = rng.choice(4, p=pri_p)
                if hard and prio < 2: prio += 1
                group = mode == "G" or (mode == "IG" and rng.random() < .3)
                team = int(np.clip(2 + rng.poisson(1.5), 2, 8)) if group else 1
                dep = int(np.clip(rng.poisson(0.5 + 1.2 * cx + (0.8 if group else 0)), 0, 10))
                sub = int(np.clip(1 + rng.poisson(1.5 + 3 * cx), 1, 20))
                ext_in = int(rng.random() < min(.85, .1 + .12 * dep))
                level = rng.choice(levels)
                conv = norm_hours(hrs, rng, cx, team) if isinstance(hrs, str) else (np.nan if hrs is None else round(rng.uniform(*hrs) * (0.8 + 0.2 * cx), 2))
                tid += 1
                scale = "quy mô nhỏ" if dur < 0.8 * dtyp else ("quy mô lớn" if dur > 1.3 * dtyp else "quy mô chuẩn")
                base = dict(task_id=f"T{tid:06d}", assigned_date=d, task_group=grp, task_type=name,
                            task_subtype=f"{name} - {scale}", assignment_level=level,
                            assignment_mode="Group" if group else "Individual", team_size=team,
                            priority=PRIORITIES[prio], priority_idx=prio, complexity=["Thấp", "Trung bình", "Cao"][cx],
                            complexity_idx=cx, subtask_count=sub, dependency_count=dep,
                            require_external_input=ext_in, require_approval=int(rng.random() < (.3 + .2 * (level != "Bộ môn"))),
                            is_urgent_assignment=int(pressure > 1.25), hard_deadline=hard,
                            assignment_channel=rng.choice(CHANNELS, p=[.25, .3, .15, .2, .1]),
                            expected_duration_days=round(dur, 2), available_days=avail,
                            working_days_available=wd, holiday_in_window=hol_in,
                            deadline_pressure=round(pressure, 3), original_deadline=orig,
                            estimated_effort_hours=round(inten * dur ** 0.8 * rng.uniform(.8, 1.2), 1),
                            converted_workload=conv, academic_period=p, semester=semester(d),
                            academic_week=int((d - ay_start(d)).days // 7 + 1),
                            peak_season=int(p in (FE, GP, GS)), accreditation_flag=acc, year_idx=y,
                            deadline_month_end=me_flag, task_shock=float(rng.normal(0, CFG["task_shock_sd"])) if group else 0.0)
                members = [L.lecturer_id]
                if group:
                    pool = [x for x in ids if x != L.lecturer_id and jdate[x] <= d <= ldate[x]]
                    same = [x for x in pool if dept[x] == dept[L.lecturer_id]]
                    pick = same if (len(same) >= team - 1 and rng.random() < .8) else pool
                    if pick:
                        members += list(rng.choice(pick, size=min(team - 1, len(pick)), replace=False))
                for m, lid in enumerate(members):
                    rows.append(dict(base, lecturer_id=lid, role="Chủ trì" if m == 0 else "Thành viên"))
    sk = pd.DataFrame(rows)
    sk = sk.merge(lect[["lecturer_id", "join_date", "tenure_offset", "faculty", "fac_offset", "dept_offset", "department", "academic_rank", "degree", "management_role",
                        "years_experience_at_start", "random_effect", "persona_latent"]], on="lecturer_id")
    sk = sk.merge(loads.drop(columns="academic_year"), on=["lecturer_id", "year_idx"])
    sk["years_experience"] = (sk.years_experience_at_start +
                              (sk.assigned_date - pd.Timestamp(CFG["start_year"], 8, 15)).dt.days / 365).round(1)
    sk["is_manager"] = (sk.management_role != "Không").astype(int)
    sk["tenure_days"] = ((sk.assigned_date - pd.Timestamp(CFG["start_year"], 8, 15)).dt.days + sk.tenure_offset).clip(lower=0)
    return sk.sort_values(["lecturer_id", "assigned_date", "task_id"]).reset_index(drop=True)


# ============================== MÔ PHỎNG NHÃN ==============================
def simulate(sk, persona_off, seed):
    rng = np.random.default_rng(seed)
    N = len(sk)
    o = {k: np.full(N, np.nan) for k in ["hist_count", "hist_late_rate", "hist_avg_delay", "hist_early_rate",
         "active_tasks", "active_high_priority_tasks", "overdue_open_tasks", "deadlines_next_7d",
         "deadlines_next_14d", "workload_next_14d", "z", "z_signal", "late", "comp", "delay", "ext_req", "ext_days",
         "ext_appr", "ext_req_ord", "ext_dec_ord", "late_true", "hist_late_last5", "late_last_30d"]}
    ordn = lambda s: s.map(pd.Timestamp.toordinal).to_numpy()
    A, OD = ordn(sk.assigned_date), ordn(sk.original_deadline)
    prio, eff = sk.priority_idx.to_numpy(), sk.estimated_effort_hours.to_numpy()
    W = CFG["weights"]
    rows = list(sk.itertuples(index=False))
    DI, DA = CFG["drift_intercept"], CFG["drift_active_mult"]

    for _, idx in sk.groupby("lecturer_id").indices.items():
        n = len(idx); comp = np.full(n, 10**9); late = np.zeros(n); dly = np.zeros(n)
        early = np.zeros(n, bool)
        for j in range(n):
            i = idx[j]; aj = A[i]
            if j:
                done = comp[:j] < aj; cnt = int(done.sum()); opn = ~done
                ls = late[:j][done].sum()
                o["hist_late_rate"][i] = (ls + CFG["hist_prior_rate"] * CFG["hist_prior_strength"]) / (cnt + CFG["hist_prior_strength"])
                o["hist_avg_delay"][i] = dly[:j][done & (late[:j] > 0)].mean() if (ls > 0) else (0.0 if cnt else np.nan)
                o["hist_early_rate"][i] = early[:j][done].mean() if cnt else np.nan
                od_o = OD[idx[:j]][opn]
                o["active_tasks"][i] = opn.sum()
                o["active_high_priority_tasks"][i] = (prio[idx[:j]][opn] >= 2).sum()
                o["overdue_open_tasks"][i] = (od_o < aj).sum()
                o["deadlines_next_7d"][i] = ((od_o >= aj) & (od_o <= aj + 7)).sum()
                o["deadlines_next_14d"][i] = ((od_o >= aj) & (od_o <= aj + 14)).sum()
                o["workload_next_14d"][i] = eff[idx[:j]][opn][od_o <= aj + 14].sum()
                o["hist_count"][i] = cnt
                dn = np.flatnonzero(done)
                o["hist_late_last5"][i] = late[:j][dn[-5:]].mean() if len(dn) else np.nan
                o["late_last_30d"][i] = float(((comp[:j] >= aj - 30) & done & (late[:j] > 0)).sum())
            else:
                cnt = 0
                o["hist_late_rate"][i] = CFG["hist_prior_rate"]
                for c in ["late_last_30d", "hist_count", "active_tasks", "active_high_priority_tasks", "overdue_open_tasks",
                          "deadlines_next_7d", "deadlines_next_14d", "workload_next_14d"]:
                    o[c][i] = 0
            r = rows[i]
            yi = min(int(r.year_idx), len(DI) - 1)
            act, d7, w14 = o["active_tasks"][i], o["deadlines_next_7d"][i], o["workload_next_14d"][i]
            lp = np.log(r.deadline_pressure)
            hl = o["hist_late_rate"][i]
            ov = o["overdue_open_tasks"][i]
            zs = (persona_off[r.persona_latent] + r.random_effect + r.fac_offset + r.dept_offset + r.fac_year_shock + r.year_effect + r.task_shock + DI[yi]
                  + W["complexity"] * (r.complexity_idx - 1) + W["log_pressure"] * lp
                  + W["subtask"] * (r.subtask_count - 4) + W["dependency"] * r.dependency_count
                  + W["ext_input"] * r.require_external_input + W["holiday"] * r.holiday_in_window
                  + PRIORITY_Z[r.priority_idx] + W["formal_channel"] * (r.assignment_channel == "Hệ thống")
                  + W["hard_deadline"] * r.hard_deadline + PERIOD_Z[r.academic_period]
                  + W["accreditation"] * r.accreditation_flag
                  + W["manager_urgent"] * r.is_manager * r.is_urgent_assignment
                  + W["experience"] * (r.years_experience - 10)
                  + W["active"] * DA[yi] * (act - 5) + W["burnout"] * min(o["late_last_30d"][i], 3) + W["d7"] * (d7 - 1) + W["overdue"] * ov
                  + W["workload14"] * np.clip(w14 - 40, -40, 200)
                  + W["teaching"] * (r.teaching_hours_semester - 180)
                  + W["hist_late"] * (hl - CFG["hist_prior_rate"])
                  + W["interaction"] * r.complexity_idx * max(lp, 0) * max(act - 5, 0) / 3
                  + W["overload_slope"] * max(0, act - W["overload_over"])
                  + W["crunch"] * float(d7 >= 3 and r.complexity_idx == 2)
                  + W["mgr_peak"] * r.is_manager * r.peak_season
                  + W["junior"] * float(r.years_experience < 2) + W["senior"] * float(r.years_experience > 25)
                  + W["newjoin"] * float(r.tenure_days < 90)
                  + W["hist_x_pressure"] * (hl - CFG["hist_prior_rate"]) * max(lp, 0))
            z = zs + rng.normal(0, CFG["noise_sd"])
            late_true = rng.random() < sigmoid(z)
            flip = rng.random() < (CFG["label_noise_fn"] if late_true else CFG["label_noise_fp"])
            is_late = bool(late_true != flip)                     # nhãn QUAN SÁT (có thể ghi nhận sai); late_true là sự thật ẩn
            if is_late:
                if rng.random() < 0.85: dl = int(np.clip(max(1, round(r.expected_duration_days * rng.lognormal(-1.6, .7))), 1, 90))
                else: dl = int(np.clip(max(2, round(r.expected_duration_days * rng.lognormal(-0.6, .9))), 2, 180))   # đuôi dài
                c = OD[i] + dl
            else:
                dl = 0
                c = A[i] + int(round(r.available_days * rng.beta(5, 1.5)))
                c = min(c, OD[i])
            comp[j], late[j], dly[j] = c, float(is_late), dl
            early[j] = c <= OD[i] - 2
            o["z"][i], o["z_signal"][i], o["late"][i], o["comp"][i] = z, zs, float(is_late), c
            o["delay"][i] = c - OD[i]; o["late_true"][i] = float(late_true)
            # gia hạn
            req = rng.random() < ((0.35 + 0.1 * r.require_external_input) if is_late else 0.03)
            appr = req and rng.random() < (0.4 if r.hard_deadline else 0.7)
            o["ext_req"][i], o["ext_appr"][i] = float(req), float(appr)
            if req:
                ed = int(np.clip(np.ceil(dl * rng.uniform(.7, 1.6)), 2, 45)) if is_late else int(rng.integers(3, 11))
                o["ext_days"][i] = ed if appr else np.nan
                rq = max(A[i], OD[i] - int(rng.integers(1, 6)))
                o["ext_req_ord"][i], o["ext_dec_ord"][i] = rq, rq + int(rng.integers(1, 4))
    out = sk.copy()
    for k, v in o.items(): out[k] = v
    return out

def finalize(df):
    f = lambda c: df[c].map(lambda x: pd.Timestamp.fromordinal(int(x)) if x == x else pd.NaT)
    df["completed_date"] = f("comp")
    df["extension_requested"] = df.ext_req.astype(int)
    df["extension_approved"] = df.ext_appr.astype(int)
    df["extension_days"] = df.ext_days.fillna(0).astype(int)
    df["current_deadline"] = df.original_deadline + pd.to_timedelta(df.extension_days, unit="D")
    df["extension_requested_at"] = f("ext_req_ord"); df["extension_decided_at"] = f("ext_dec_ord")
    df["late_vs_original_deadline"] = df.late.astype(int)
    df["late_vs_current_deadline"] = (df.completed_date > df.current_deadline).astype(int)
    df["delay_days"] = df.delay.astype(int)
    df["delay_days_vs_current"] = (df.completed_date - df.current_deadline).dt.days
    df["is_late"] = df.late_vs_original_deadline
    return df



def calibrate_personas(sk, seed, tol=0.03, max_iter=6, pilot_frac=0.3, pilot_cap=40000):
    """Điều chỉnh offset từng persona để tỉ lệ trễ quan sát bám tỉ lệ cơ bản trong khảo sát.
       Khi dữ liệu lớn, hiệu chuẩn trên mẫu thử (pilot) gồm một phần giảng viên rồi mô phỏng lại toàn bộ một lần."""
    off = {p: logit(v[1]) - logit(0.17) for p, v in PERSONAS.items()}
    pil = sk
    if len(sk) > pilot_cap:
        rg = np.random.default_rng(seed); per = sk.drop_duplicates("lecturer_id").set_index("lecturer_id").persona_latent; pick = []
        for p, g in per.groupby(per):
            pick += list(rg.choice(g.index.values, size=min(len(g), max(2, int(round(len(g) * pilot_frac)))), replace=False))
        pil = sk[sk.lecturer_id.isin(pick)].reset_index(drop=True)
        print(f"[calib] dùng mẫu thử {len(pick)} giảng viên ({len(pil)} dòng) để hiệu chuẩn")
    for it in range(max_iter):
        df = simulate(pil, off, seed)
        rate = df.groupby("persona_latent").late.mean()
        present = [p for p in PERSONAS if p in rate.index]      # quy mô nhỏ có thể thiếu một vài persona
        gap = {p: PERSONAS[p][1] - rate[p] for p in present}
        print(f"[calib {it}] overall={df.late.mean():.3f} max_gap={max(abs(g) for g in gap.values()):.3f}", flush=True)
        if max(abs(g) for g in gap.values()) < tol: break
        for p in present:
            off[p] += 0.8 * (logit(np.clip(PERSONAS[p][1], .01, .99)) - logit(np.clip(rate[p], .005, .995)))
    if pil is not sk:
        df = simulate(sk, off, seed); print(f"[calib] mô phỏng toàn bộ: overall={df.late.mean():.3f}")
    return df, off

# ============================== XUẤT DỮ LIỆU ==============================
FEATS_STATIC = ["task_group", "task_type", "task_subtype", "assignment_level", "assignment_mode", "assignment_channel",
    "priority", "complexity", "subtask_count", "dependency_count", "team_size", "is_urgent_assignment",
    "require_external_input", "require_approval", "available_days", "working_days_available", "holiday_in_window",
    "expected_duration_days", "deadline_pressure", "estimated_effort_hours", "converted_workload",
    "academic_period", "semester", "academic_week", "peak_season", "accreditation_flag",
    "academic_rank", "degree", "years_experience", "tenure_days", "management_role", "department",
    "teaching_hours_semester", "course_count", "student_count", "supervised_student_count",
    "hist_count", "hist_late_rate", "hist_avg_delay", "hist_early_rate", "active_tasks",
    "active_high_priority_tasks", "overdue_open_tasks", "deadlines_next_7d", "deadlines_next_14d", "workload_next_14d",
    "hist_late_last5", "late_last_30d", "deadline_month_end"]
TARGETS = ["is_late", "late_vs_original_deadline", "late_vs_current_deadline"]


DESCR = {
 "task_group": "Nhóm công việc (10 nhóm khảo sát)", "task_type": "Loại công việc cụ thể",
 "task_subtype": "Loại + quy mô (nhỏ/chuẩn/lớn)", "assignment_level": "Cấp giao: Bộ môn/Khoa/Trường",
 "assignment_mode": "Individual/Group", "assignment_channel": "Kênh giao việc", "priority": "Mức ưu tiên",
 "complexity": "Độ phức tạp", "subtask_count": "Số đầu việc con", "dependency_count": "Số đơn vị/bên phụ thuộc",
 "team_size": "Số người thực hiện", "is_urgent_assignment": "1 nếu deadline_pressure > 1.25",
 "require_external_input": "Cần dữ liệu/minh chứng từ bên ngoài", "require_approval": "Cần phê duyệt",
 "available_days": "Số ngày từ lúc giao đến hạn gốc", "working_days_available": "Số ngày làm việc (trừ cuối tuần, lễ, Tết)",
 "holiday_in_window": "Có nghỉ lễ/Tết trong khoảng thực hiện", "expected_duration_days": "Thời lượng điển hình của công việc",
 "deadline_pressure": "expected_duration / available_days", "estimated_effort_hours": "Giờ công ước lượng",
 "converted_workload": "Giờ chuẩn quy đổi: định mức thật (file Cong-tac-khac-nam-hoc.xlsx) x số đơn vị giả định; loại việc không có trong bảng định mức: khoảng giả định hoặc trống (xem task_catalog_norm.csv)",
 "academic_period": "Giai đoạn trong năm học", "semester": "HK1/HK2/Summer", "academic_week": "Tuần của năm học (1-52)",
 "peak_season": "1 nếu thi/chấm/nộp điểm/bảo vệ", "accreditation_flag": "1 nếu trong đợt kiểm định",
 "academic_rank": "Chức danh", "degree": "Học vị", "years_experience": "Thâm niên tại thời điểm giao",
 "hist_late_last5": "Tỉ lệ trễ của 5 việc hoàn thành gần nhất (xu hướng gần đây)", "late_last_30d": "Số việc hoàn thành TRỄ trong 30 ngày qua (kiệt sức)", "deadline_month_end": "Hạn chót rơi vào cuối tháng", "faculty": "Mã Khoa (dùng để chia nhóm đánh giá, không phải đặc trưng)", "progress_missing": "[dynamic] 1 nếu chưa cập nhật tiến độ", "tenure_days": "Số ngày kể từ khi vào Khoa (nhỏ = giảng viên mới)", "management_role": "Vai trò quản lý", "department": "Bộ môn", "teaching_hours_semester": "Giờ giảng học kỳ/năm",
 "course_count": "Số học phần", "student_count": "Số sinh viên phụ trách", "supervised_student_count": "Số SV hướng dẫn",
 "hist_count": "Số công việc đã xong TRƯỚC ngày giao", "hist_late_rate": "Tỉ lệ trễ lịch sử (làm mượt, prior 0.2)",
 "hist_avg_delay": "Số ngày trễ TB của các lần trễ trước đó", "hist_early_rate": "Tỉ lệ hoàn thành sớm >=2 ngày trước đây",
 "active_tasks": "Số việc đang mở lúc giao", "active_high_priority_tasks": "Số việc đang mở mức Cao/Khẩn cấp",
 "overdue_open_tasks": "Số việc đang mở đã quá hạn gốc", "deadlines_next_7d": "Số hạn gốc rơi vào 7 ngày tới",
 "deadlines_next_14d": "Số hạn gốc rơi vào 14 ngày tới", "workload_next_14d": "Tổng giờ công của việc đến hạn trong 14 ngày",
 "is_late": "NHÃN CHÍNH = late_vs_original_deadline", "late_vs_original_deadline": "Hoàn thành sau hạn gốc",
 "late_vs_current_deadline": "Vẫn trễ sau khi đã gia hạn (nếu được duyệt)",
 "checkpoint_fraction": "[dynamic] mốc thời gian 0.25/0.5", "days_elapsed": "[dynamic] số ngày đã trôi",
 "days_remaining": "[dynamic] số ngày còn lại", "progress_pct": "[dynamic] % tiến độ tại mốc",
 "expected_progress_pct": "[dynamic] % tiến độ kỳ vọng tuyến tính", "progress_gap": "[dynamic] progress - expected",
}

def export(df, lect, loads, out, rng, snapshot=None):
    os.makedirs(out, exist_ok=True)
    df = df.copy()
    snap_ord = pd.Timestamp(snapshot).toordinal() if snapshot else None
    df["is_open"] = (df.comp > snap_ord).astype(int) if snap_ord else 0
    lab = df[df.is_open == 0].copy()          # chỉ công việc đã có nhãn mới vào tập ML

    lect.drop(columns=["random_effect", "fac_offset", "dept_offset"]).to_csv(f"{out}/lecturers.csv", index=False, encoding="utf-8-sig")
    loads.drop(columns=["year_idx", "year_effect", "fac_year_shock"]).to_csv(f"{out}/lecturer_load.csv", index=False, encoding="utf-8-sig")

    ta = df[["task_id", "lecturer_id", "role", "assigned_date", "original_deadline", "current_deadline", "completed_date",
             "late_vs_original_deadline", "late_vs_current_deadline", "delay_days", "is_open"]].copy()
    ta["status"] = np.where(ta.late_vs_original_deadline == 1, "Hoàn thành trễ hạn", "Hoàn thành đúng hạn")
    ta["progress_pct"] = 100.0
    o = ta.is_open == 1
    if o.any():
        sn = pd.Timestamp(snapshot)
        total = (df.loc[o, "completed_date"] - df.loc[o, "assigned_date"]).dt.days.clip(lower=1)
        done = (sn - df.loc[o, "assigned_date"]).dt.days.clip(lower=0)
        ta.loc[o, "progress_pct"] = np.clip(100 * done / total * rng.uniform(.8, 1.0, o.sum()), 5, 95).round(1)
        ta.loc[o, "status"] = np.where(df.loc[o, "current_deadline"] < sn, "Quá hạn (đang thực hiện)", "Đang thực hiện")
        for c in ["completed_date", "late_vs_original_deadline", "late_vs_current_deadline", "delay_days"]:
            ta.loc[o, c] = pd.NA
    ta.drop(columns="is_open").to_csv(f"{out}/task_assignments.csv", index=False, encoding="utf-8-sig")

    g = df.groupby("task_id")
    tasks = g.first()[["task_group", "task_type", "task_subtype", "assignment_level", "assignment_mode", "team_size",
                       "priority", "complexity", "subtask_count", "dependency_count", "assigned_date",
                       "original_deadline", "expected_duration_days", "available_days", "converted_workload",
                       "academic_period", "semester"]].copy()
    tasks["final_deadline"] = g.current_deadline.max()
    tk_open = g.is_open.max() == 1
    tasks["completed_date"] = g.completed_date.max().where(~tk_open)
    tasks["is_late"] = g.late_vs_original_deadline.max().where(~tk_open)
    tasks["progress_pct"] = ta.assign(t=df.task_id).groupby("t").progress_pct.mean().round(1)
    tasks["status"] = np.where(tk_open, "Đang thực hiện", np.where(tasks.is_late == 1, "Hoàn thành trễ hạn", "Hoàn thành đúng hạn"))
    tasks.reset_index().to_csv(f"{out}/tasks.csv", index=False, encoding="utf-8-sig")

    er = df[df.extension_requested == 1]
    er = pd.DataFrame(dict(task_id=er.task_id, lecturer_id=er.lecturer_id, requested_at=er.extension_requested_at,
        original_deadline=er.original_deadline, proposed_deadline=er.original_deadline +
        pd.to_timedelta(np.where(er.extension_approved == 1, er.extension_days, 5), unit="D"),
        reason=rng.choice(["Quá nhiều nhiệm vụ song song", "Chờ dữ liệu/minh chứng từ đơn vị khác", "Yêu cầu thay đổi",
                           "Khối lượng sinh viên lớn", "Nhiệm vụ đột xuất"], size=len(er)),
        status=np.where(er.extension_approved == 1, "Đã duyệt", "Từ chối"), decided_at=er.extension_decided_at,
        new_deadline=np.where(er.extension_approved == 1, er.current_deadline.astype(str), "")))
    er.to_csv(f"{out}/extension_requests.csv", index=False, encoding="utf-8-sig")

    # Xác suất "thật" (oracle): xác suất trễ khi biết cả yếu tố ẩn (persona, hiệu ứng giảng viên/Khoa/nhóm...), lấy trung bình theo nhiễu ẩn.
    # Lưu RIÊNG, không phải đặc trưng — chỉ để kiểm chứng mô hình bằng evaluate_vs_truth.py.
    nodes, wts = np.polynomial.hermite_e.hermegauss(40); wts = wts / np.sqrt(2 * np.pi)
    zs_ = lab.z_signal.values; p_true = (sigmoid(zs_[:, None] + CFG["noise_sd"] * nodes[None, :]) * wts[None, :]).sum(axis=1)
    p_obs = p_true * (1 - CFG["label_noise_fn"]) + (1 - p_true) * CFG["label_noise_fp"]
    pd.DataFrame(dict(task_id=lab.task_id.values, lecturer_id=lab.lecturer_id.values, assigned_date=lab.assigned_date.values,
                      z_signal=np.round(zs_, 5), p_true=np.round(p_true, 5), p_true_observed=np.round(p_obs, 5),
                      late_true=lab.late_true.astype(int).values)).to_csv(f"{out}/oracle_truth.csv", index=False, encoding="utf-8-sig")
    ml = lab[["task_id", "lecturer_id", "faculty", "assigned_date"] + FEATS_STATIC + TARGETS].copy()
    for c in ["student_count", "dependency_count", "subtask_count", "years_experience", "require_external_input"]:
        m = rng.random(len(ml)) < CFG["missing_rate"]
        if c != "years_experience": ml[c] = ml[c].astype("Float64")
        ml.loc[m, c] = pd.NA if c != "years_experience" else np.nan
    ml.to_csv(f"{out}/ml_training_set.csv", index=False, encoding="utf-8-sig")

    dyn = []
    # Nhịp làm việc phi = tốc độ thực / tốc độ kỳ vọng. Việc trễ có phi thấp hơn NHƯNG phân bố chồng lấn;
    # 30% việc trễ khởi đầu tốt rồi chậm lại, 20% việc đúng hạn khởi đầu chậm rồi bắt kịp.
    lv = lab.late_true.values; nn = len(lab)
    phi_end = np.where(lv == 1, rng.lognormal(np.log(0.72), 0.30, nn), rng.lognormal(np.log(1.0), 0.28, nn))
    phi_start, shock = phi_end.copy(), rng.random(nn)
    m1 = (lv == 1) & (shock < 0.30); phi_start[m1] = rng.lognormal(np.log(1.0), 0.28, m1.sum())
    m2 = (lv == 0) & (shock < 0.20); phi_start[m2] = rng.lognormal(np.log(0.75), 0.30, m2.sum())
    lab = lab.assign(_phi_end=phi_end, _phi_start=phi_start)
    for fr in (0.25, 0.5):
        s = lab[lab.available_days >= 4].copy()
        el = np.maximum(1, np.round(fr * s.available_days)).astype(int)
        s = s[(s.comp - s.assigned_date.map(pd.Timestamp.toordinal)) > el[s.index]]
        el = el[s.index]
        exp = 100 * el / s.available_days
        phi = s._phi_start if fr == 0.25 else np.sqrt(s._phi_start * s._phi_end)
        prog = np.clip(exp * phi * rng.lognormal(0, 0.15, len(s)) + rng.normal(0, 3, len(s)), 0, 100).round(1)
        miss = rng.random(len(s)) < np.where(s.late_true.values == 1, 0.18, 0.04)    # thiếu không ngẫu nhiên: người hay trễ ít cập nhật
        prog = np.where(miss, np.nan, prog)
        s = s[["task_id", "lecturer_id", "faculty", "assigned_date"] + FEATS_STATIC + TARGETS].assign(
            checkpoint_fraction=fr, days_elapsed=el, days_remaining=s.available_days - el,
            progress_pct=prog, expected_progress_pct=exp.round(1), progress_gap=(prog - exp).round(1), progress_missing=miss.astype(int))
        dyn.append(s)
    pd.concat(dyn).to_csv(f"{out}/ml_dynamic_set.csv", index=False, encoding="utf-8-sig")

    dd = [(c, "ID/thời gian (không dùng làm đặc trưng)" if c in ("task_id", "lecturer_id", "faculty", "assigned_date")
           else "Nhãn" if c in TARGETS else "Đặc trưng", DESCR.get(c, "")) for c in
          ["task_id", "lecturer_id", "faculty", "assigned_date"] + FEATS_STATIC + TARGETS +
          ["checkpoint_fraction", "days_elapsed", "days_remaining", "progress_pct", "expected_progress_pct", "progress_gap", "progress_missing"]]
    pd.DataFrame(dd, columns=["column", "role", "description"]).to_csv(f"{out}/data_dictionary.csv", index=False, encoding="utf-8-sig")
    return lab


def export_catalog(out):
    rows = []
    for t in TYPES:
        name, grp, hrs = t[0], t[1], t[8]
        if isinstance(hrs, str):
            stt, txt, _ = NORMS[hrs]; src, ref = "định mức từ file Cong-tac-khac-nam-hoc.xlsx", f"mục {stt}: {txt}"
        elif hrs is None:
            src, ref = "không quy đổi (trống)", ""
        else:
            src, ref = "giả định của bộ sinh", f"khoảng {hrs[0]}-{hrs[1]} giờ"
        rows.append(dict(task_type=name, task_group=grp, nguon_gio_quy_doi=src, dinh_muc=ref, tan_suat_tuong_doi=t[4]))
    pd.DataFrame(rows).to_csv(f"{out}/task_catalog_norm.csv", index=False, encoding="utf-8-sig")


def checks(lab, out, report):
    print("\n===== KIỂM TRA CHẤT LƯỢNG =====")
    rate = lab.is_late.mean()
    lo, hi = CFG["overall_late_range"]
    print(f"Số dòng có nhãn: {len(lab)} | số task: {lab.task_id.nunique()} | số GV: {lab.lecturer_id.nunique()}")
    print(f"Tỉ lệ trễ (hạn gốc): {rate:.3f} {'OK' if lo <= rate <= hi else 'CẢNH BÁO: ngoài khoảng khảo sát'} | "
          f"(hạn hiện tại): {lab.late_vs_current_deadline.mean():.3f} | gia hạn: {lab.extension_requested.mean():.3f}")
    pr = lab.groupby("persona_latent").is_late.mean().round(3)
    tgt = pd.Series({p: v[1] for p, v in PERSONAS.items()})
    print("\nTỉ lệ trễ theo persona (quan sát vs mục tiêu khảo sát):")
    print(pd.DataFrame({"quan_sat": pr, "muc_tieu": tgt}).to_string())
    for c in ["complexity", "priority", "academic_period"]:
        print(f"\nTỉ lệ trễ theo {c}:\n{lab.groupby(c).is_late.mean().round(3).to_string()}")
    print("\nTỉ lệ trễ theo tháng giao:\n" + lab.groupby(lab.assigned_date.dt.month).is_late.mean().round(3).to_string())
    print(f"\nCold-start: hist_count = 0: {(lab.hist_count == 0).mean():.2%} | hist_count < 5: {(lab.hist_count < 5).mean():.2%} | tenure < 90 ngày: {(lab.tenure_days < 90).mean():.2%}")

    assert (lab.assigned_date < lab.original_deadline).all()
    assert (lab.completed_date >= lab.assigned_date).all()
    assert (lab.current_deadline >= lab.original_deadline).all()
    assert (lab.extension_approved <= lab.extension_requested).all()
    assert not ((lab.hist_count > 0) & (lab.tenure_days <= 0)).any()      # chưa vào Khoa thì không thể có lịch sử
    assert (lab.hist_late_rate.between(0, 1)).all()
    print("Ràng buộc nghiệp vụ & cold-start: OK")
    report.update(n_rows=len(lab), late_rate=round(float(rate), 4), persona_rates=pr.to_dict())

    try:
        from sklearn.metrics import roc_auc_score
        auc_ceiling = roc_auc_score(lab.is_late, lab.z_signal)          # AUC tối đa khi biết cả yếu tố ẩn (không phải một mô hình học máy)
        print(f"\nAUC trần (biết cả yếu tố ẩn: persona, random effect): {auc_ceiling:.3f}")
        report.update(auc_ceiling=round(float(auc_ceiling), 4))
    except Exception as e:
        print("Bỏ qua AUC trần (cần scikit-learn):", e)
    print("(Đánh giá mô hình: chạy train_model.py / evaluate_vs_truth.py)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_lecturers", type=int, default=360)
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--n_faculties", type=int, default=6)
    ap.add_argument("--burn_in_days", type=int, default=180, help="mô phỏng nhưng bỏ N ngày đầu khỏi dữ liệu xuất ra (tránh trạng thái khởi đầu trống)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="./data")
    ap.add_argument("--snapshot", default=None, help="YYYY-MM-DD: việc chưa xong tại ngày này sẽ là 'Đang thực hiện'")
    ap.add_argument("--config", default=None, help="JSON ghi đè CFG (vd: {\"noise_sd\":0.9,\"weights\":{\"active\":0.12}})")
    a = ap.parse_args()
    if a.config:
        ov = json.load(open(a.config, encoding="utf-8"))
        for k, v in ov.items():
            if k == "personas": PERSONAS.update({p: tuple(x) for p, x in v.items()})
            elif isinstance(v, dict) and isinstance(CFG.get(k), dict): CFG[k].update(v)
            else: CFG[k] = v
    CFG["n_faculties"] = a.n_faculties; t_start = time.time()
    rng = np.random.default_rng(a.seed)
    lect, loads = make_lecturers(a.n_lecturers, a.years, rng)
    sk = make_skeleton(lect, loads, a.years, rng)
    print(f"[sinh khung công việc] {len(sk)} dòng, {time.time() - t_start:.0f} giây", flush=True)
    df, off = calibrate_personas(sk, a.seed + 1, pilot_cap=10**9)   # v5: hiệu chuẩn trên TOÀN BỘ dữ liệu (không dùng mẫu thử) để bám tỉ lệ trễ theo persona
    df = finalize(df)
    if a.burn_in_days > 0:       # giai đoạn khởi động: lịch sử/tải việc vẫn được tính từ các dòng này nhưng không xuất ra
        first = df.sort_values("assigned_date").groupby("lecturer_id").head(1)
        assert (first[first.tenure_days < 30].hist_count == 0).all()      # giảng viên mới vào Khoa phải bắt đầu với lịch sử trống
        cut = pd.Timestamp(CFG["start_year"], 8, 15) + pd.Timedelta(days=a.burn_in_days); n0 = len(df)
        df = df[df.assigned_date >= cut].reset_index(drop=True)
        print(f"[burn-in] bỏ {n0 - len(df)} dòng đầu (trước {cut.date()}), còn {len(df)} dòng", flush=True)
    lab = export(df, lect, loads, a.out, rng, a.snapshot)
    export_catalog(a.out)
    report = dict(norm_source_file="Cong-tac-khac-nam-hoc.xlsx (KL_CT#, Sheet1)", seed=a.seed, n_lecturers=a.n_lecturers, years=a.years, n_faculties=a.n_faculties, burn_in_days=a.burn_in_days, snapshot=a.snapshot,
                  persona_offsets={k: round(float(v), 3) for k, v in off.items()}, weights=CFG["weights"])
    checks(lab, a.out, report)
    json.dump(report, open(f"{a.out}/generation_report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nĐã ghi CSV vào {os.path.abspath(a.out)} (tổng {time.time() - t_start:.0f} giây)")

if __name__ == "__main__":
    main()
