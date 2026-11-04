# -*- coding: utf-8 -*-
"""
Sinh toàn bộ 11 sơ đồ UML hệ thống chuẩn 300 DPI cho Chương 1:
1. hinh_1_1_usecase_nghiep_vu.png (UseCase tổng thể 4 tác nhân)
2. hinh_1_2_so_do_hoat_dong.png (Activity Diagram quy trình giao việc & duyệt 3 cấp)
3. hinh_1_3_so_do_tuan_tu.png (Sequence Diagram trích xuất 58 đặc trưng & gọi TabPFN v2)
4. hinh_1_4_uc_auth_rbac.png (Use Case: Quản lý người dùng, Xác thực JWT & Phân quyền RBAC 4 phạm vi)
5. hinh_1_5_uc_ke_hoach_dinh_muc.png (Use Case: Kế hoạch năm & Định mức 270 giờ chuẩn Excel)
6. hinh_1_6_uc_phan_cong_cong_viec.png (Use Case: Khởi tạo & Phân công nhóm, Cưỡng chế 1 Trưởng nhóm)
7. hinh_1_7_uc_du_bao_tabpfn.png (Use Case: Dự báo rủi ro trễ hạn & Gợi ý nhân sự AI TabPFN v2)
8. hinh_1_8_uc_phe_duyet_3_cap.png (Use Case: Cập nhật tiến độ, Nộp minh chứng & Phê duyệt 3 cấp)
9. hinh_1_9_uc_mlops_monitoring.png (Use Case: Giám sát MLOps Mức 2 & Học tiếp định kỳ có rào chắn)
10. hinh_1_10_so_do_lop_phan_tich.png (Sơ đồ lớp ở mức phân tích - Boundary, Control, Entity)
11. hinh_1_11_so_do_lop_csdl.png (Sơ đồ lớp mức thiết kế - Lược đồ 17 bảng CSDL qlcv.db)
"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUT_DIR = r"C:\Users\ADMIN\.gemini\antigravity\brain\37490e21-be68-4229-9703-1fb6bdc12c89\scratch\diagrams"
os.makedirs(OUT_DIR, exist_ok=True)
plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Segoe UI"]
plt.rcParams["axes.unicode_minus"] = False


def draw_box(ax, x, y, w, h, text, bg="#FFFFFF", edge="#000000", fontsize=9, bold=False, color="#000000"):
    rect = patches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.015,rounding_size=0.02",
        facecolor=bg, edgecolor=edge, linewidth=1.2
    )
    ax.add_patch(rect)
    ax.text(
        x + w / 2, y + h / 2, text,
        ha="center", va="center", fontsize=fontsize,
        fontweight="bold" if bold else "normal", color=color
    )


def draw_actor(ax, x, y, name, role="Actor"):
    # Vẽ biểu tượng Actor UML đơn giản
    head = patches.Circle((x, y + 0.05), 0.025, facecolor="#FFFFFF", edgecolor="#000000", lw=1.3)
    ax.add_patch(head)
    ax.plot([x, x], [y + 0.025, y - 0.03], color="#000000", lw=1.3)  # thân
    ax.plot([x - 0.03, x + 0.03], [y + 0.01, y + 0.01], color="#000000", lw=1.3)  # tay
    ax.plot([x, x - 0.025], [y - 0.03, y - 0.07], color="#000000", lw=1.3)  # chân trái
    ax.plot([x, x + 0.025], [y - 0.03, y - 0.07], color="#000000", lw=1.3)  # chân phải
    ax.text(x, y - 0.10, name, ha="center", va="top", fontsize=8.5, fontweight="bold", color="#000000")


def draw_usecase_oval(ax, x, y, w, h, text, fontsize=8.5):
    oval = patches.Ellipse((x + w/2, y + h/2), w, h, facecolor="#FFFFFF", edgecolor="#000000", lw=1.2)
    ax.add_patch(oval)
    ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=fontsize, color="#000000")


def draw_arrow(ax, x1, y1, x2, y2, label="", linestyle="-"):
    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle="->", color="#000000", lw=1.2, linestyle=linestyle)
    )
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.02, label,
                ha="center", va="bottom", fontsize=8, color="#000000", fontstyle="italic")


def make_uc_diagram(filename, title, left_actors, right_actors, ucs, connections):
    fig, ax = plt.subplots(figsize=(10.5, 6.2), dpi=220)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Khung ranh giới hệ thống
    rect = patches.Rectangle((0.26, 0.05), 0.50, 0.86, facecolor="#FFFFFF", edgecolor="#000000", lw=1.4)
    ax.add_patch(rect)
    ax.text(0.51, 0.88, title.upper(), ha="center", va="center", fontsize=9.5, fontweight="bold", color="#000000")

    # Actors trái
    for x, y, name in left_actors:
        draw_actor(ax, x, y, name)

    # Actors phải
    for x, y, name in right_actors:
        draw_actor(ax, x, y, name)

    # Use Cases
    for x, y, w, h, text in ucs:
        draw_usecase_oval(ax, x, y, w, h, text)

    # Nối
    for x1, y1, x2, y2, lbl, ls in connections:
        draw_arrow(ax, x1, y1, x2, y2, label=lbl, linestyle=ls)

    plt.tight_layout()
    p = os.path.join(OUT_DIR, filename)
    plt.savefig(p, dpi=220)
    plt.close(fig)
    return p


def generate_all_diagrams():
    print("Đang vẽ 11 sơ đồ UML hệ thống chất lượng cao...")

    # 1.1 Use Case tổng thể
    fig, ax = plt.subplots(figsize=(11, 6.2), dpi=220)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    sys_rect = patches.Rectangle((0.27, 0.06), 0.69, 0.86, facecolor="#FFFFFF", edgecolor="#000000", lw=1.5)
    ax.add_patch(sys_rect)
    ax.text(0.615, 0.89, "HỆ THỐNG QUẢN LÝ CÔNG VIỆC & TỐI ƯU PHÂN CÔNG BẰNG HỌC MÁY (KHOA CNTT - HUIT)",
            ha="center", va="center", fontsize=9.5, fontweight="bold", color="#000000")
    actors = [
        (0.03, 0.74, "Quản trị viên (Admin)\n[Phạm vi: SYSTEM]"),
        (0.03, 0.53, "Ban Chủ nhiệm Khoa\n[Phạm vi: FACULTY]"),
        (0.03, 0.32, "Trưởng Bộ môn K01..K04\n[Phạm vi: DEPARTMENT]"),
        (0.03, 0.11, "Giảng viên (GV / Leader)\n[Phạm vi: SELF]"),
    ]
    for x, y, lbl in actors:
        draw_box(ax, x, y, 0.20, 0.14, lbl, bg="#FFFFFF", edge="#000000", fontsize=8.5, bold=True)
    ucs = [
        (0.32, 0.75, 0.28, 0.10, "UC-01: Quản lý Tài khoản, Bộ môn\nvà Phân quyền RBAC 4 phạm vi"),
        (0.64, 0.75, 0.29, 0.10, "UC-02: Giám sát MLOps, Cảnh báo sớm\nvà Tái huấn luyện TabPFN v2"),
        (0.32, 0.58, 0.28, 0.10, "UC-03: Kế hoạch công việc năm\nvà Định mức 270 giờ chuẩn"),
        (0.64, 0.58, 0.29, 0.10, "UC-04: Dự báo rủi ro trễ hạn AI\nvà Gợi ý nhân sự tối ưu"),
        (0.32, 0.40, 0.28, 0.10, "UC-05: Khởi tạo & Giao việc nhóm\n(Cưỡng chế duy nhất 1 Trưởng nhóm)"),
        (0.64, 0.40, 0.29, 0.10, "UC-06: Nghiệm thu hoàn thành\nvà Ghi nhận nhãn thực tế MLOps"),
        (0.32, 0.22, 0.28, 0.10, "UC-07: Trưởng nhóm duyệt nội bộ\nvà Báo cáo tổng hợp cấp trên"),
        (0.64, 0.22, 0.29, 0.10, "UC-08: Thành viên cập nhật tiến độ\nvà Nộp đường dẫn minh chứng"),
    ]
    for x, y, w, h, lbl in ucs:
        draw_box(ax, x, y, w, h, lbl, bg="#FFFFFF", edge="#000000", fontsize=8.5, bold=False)
    draw_arrow(ax, 0.23, 0.81, 0.32, 0.80)
    draw_arrow(ax, 0.23, 0.79, 0.64, 0.80)
    draw_arrow(ax, 0.23, 0.60, 0.32, 0.63)
    draw_arrow(ax, 0.23, 0.58, 0.32, 0.45)
    draw_arrow(ax, 0.23, 0.39, 0.32, 0.61)
    draw_arrow(ax, 0.23, 0.38, 0.32, 0.45)
    draw_arrow(ax, 0.23, 0.18, 0.32, 0.27)
    draw_arrow(ax, 0.23, 0.16, 0.64, 0.27)
    draw_arrow(ax, 0.60, 0.45, 0.64, 0.61, "<<include>>", linestyle="--")
    draw_arrow(ax, 0.60, 0.27, 0.64, 0.43, "<<extend>>", linestyle="--")
    plt.tight_layout()
    p1 = os.path.join(OUT_DIR, "hinh_1_1_usecase_nghiep_vu.png")
    plt.savefig(p1, dpi=220)
    plt.close(fig)

    # 1.2 Activity Diagram
    fig, ax = plt.subplots(figsize=(10.5, 6.5), dpi=220)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.96, "SƠ ĐỒ HOẠT ĐỘNG: QUY TRÌNH GIAO VIỆC VÀ PHÊ DUYỆT 3 CẤP",
            ha="center", va="center", fontsize=10.5, fontweight="bold", color="#000000")
    steps = [
        (0.06, 0.80, 0.26, 0.10, "1. Quản lý nhập thông tin việc\nvà thời hạn hoàn thành"),
        (0.37, 0.80, 0.26, 0.10, "2. Trích xuất 58 đặc trưng nhân quả\n(Lịch sử, Tải mở, Ma trận 3 tầng)"),
        (0.68, 0.80, 0.26, 0.10, "3. Gọi TabPFN v2 (/predict-batch)\nxếp hạng GV và gợi ý Trưởng nhóm"),
        (0.68, 0.60, 0.26, 0.10, "4. Kiểm tra ràng buộc Trưởng nhóm\n(Duy nhất 1 Leader nếu giao nhóm)"),
        (0.37, 0.60, 0.26, 0.10, "5. Lưu công việc, phân công vào CSDL\nvà phát cảnh báo nếu Rủi ro Cao"),
        (0.06, 0.60, 0.26, 0.10, "6. Giảng viên cập nhật tiến độ\n[0..100%] và đính kèm minh chứng"),
        (0.06, 0.36, 0.26, 0.10, "7. Trưởng nhóm duyệt nội bộ\nvà gửi báo cáo lên cấp quản lý"),
        (0.37, 0.36, 0.26, 0.10, "8. Cấp Quản lý kiểm tra hồ sơ:\nNghiệm thu hoặc Yêu cầu sửa"),
        (0.68, 0.36, 0.26, 0.10, "9. Ghi nhận completed_at, is_late\nvà đẩy vào kho FeedbackStore"),
        (0.37, 0.12, 0.28, 0.10, "10. Định kỳ chạy MLOps học tiếp\nqua 6 rào chắn (Paired Bootstrap)"),
    ]
    for x, y, w, h, lbl in steps:
        draw_box(ax, x, y, w, h, lbl, bg="#FFFFFF", edge="#000000", fontsize=8.5, bold=False)
    draw_arrow(ax, 0.32, 0.85, 0.37, 0.85)
    draw_arrow(ax, 0.63, 0.85, 0.68, 0.85)
    draw_arrow(ax, 0.81, 0.80, 0.81, 0.70)
    draw_arrow(ax, 0.68, 0.65, 0.63, 0.65)
    draw_arrow(ax, 0.37, 0.65, 0.32, 0.65)
    draw_arrow(ax, 0.19, 0.60, 0.19, 0.46)
    draw_arrow(ax, 0.32, 0.41, 0.37, 0.41)
    draw_arrow(ax, 0.63, 0.41, 0.68, 0.41, "Nghiệm thu")
    draw_arrow(ax, 0.81, 0.36, 0.65, 0.17)
    draw_arrow(ax, 0.50, 0.36, 0.19, 0.60, "Yêu cầu sửa", linestyle="--")
    plt.tight_layout()
    p2 = os.path.join(OUT_DIR, "hinh_1_2_so_do_hoat_dong.png")
    plt.savefig(p2, dpi=220)
    plt.close(fig)

    # 1.3 Sequence Diagram
    fig, ax = plt.subplots(figsize=(11, 6.2), dpi=220)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.96, "SƠ ĐỒ TUẦN TỰ: GIAO VIỆC, TRÍCH XUẤT 58 ĐẶC TRƯNG & DỰ BÁO TABPFN V2",
            ha="center", va="center", fontsize=10, fontweight="bold", color="#000000")
    lifelines = [
        (0.11, "Quản lý\n(Web React 19)"),
        (0.35, "Backend API\n(FastAPI :8000)"),
        (0.61, "CSDL Quan hệ\n(qlcv.db - 17 bảng)"),
        (0.87, "ML Service\n(TabPFN v2 :8001)"),
    ]
    for x, title in lifelines:
        draw_box(ax, x - 0.09, 0.83, 0.18, 0.09, title, bg="#FFFFFF", edge="#000000", fontsize=8.8, bold=True)
        ax.plot([x, x], [0.06, 0.83], linestyle="--", color="#000000", linewidth=1.1)
    msgs = [
        (0.11, 0.35, 0.76, "1. POST /api/tasks/recommend-assignees (Thông tin việc mới)"),
        (0.35, 0.61, 0.69, "2. Truy vấn lịch sử hoàn thành (T_j < t), tải mở & Ma trận 3 tầng"),
        (0.61, 0.35, 0.62, "3. Trả về hồ sơ GV, lịch sử nhân quả -> Dựng 58 đặc trưng"),
        (0.35, 0.87, 0.54, "4. POST /predict-batch (Lô 58->55 đặc trưng ứng viên)"),
        (0.87, 0.35, 0.46, "5. Suy luận 4 túi TabPFN v2 -> Trả về P(trễ), Mức, Giải thích"),
        (0.35, 0.11, 0.38, "6. Hiển thị bảng xếp hạng Điểm phù hợp S(u) & Đề cử Leader"),
        (0.11, 0.35, 0.29, "7. POST /api/tasks (Xác nhận giao việc + Cưỡng chế 1 Leader)"),
        (0.35, 0.61, 0.21, "8. INSERT tasks, task_assignments, risk_predictions"),
        (0.61, 0.11, 0.13, "9. Hoàn tất giao dịch & Thông báo giao việc thành công"),
    ]
    for x1, x2, y, text in msgs:
        draw_arrow(ax, x1, y, x2, y, text)
    plt.tight_layout()
    p3 = os.path.join(OUT_DIR, "hinh_1_3_so_do_tuan_tu.png")
    plt.savefig(p3, dpi=220)
    plt.close(fig)

    # 1.4 Use Case: Xác thực JWT & Phân quyền RBAC 4 phạm vi
    p4 = make_uc_diagram(
        "hinh_1_4_uc_auth_rbac.png",
        "PHÂN HỆ XÁC THỰC VÀ PHÂN QUYỀN RBAC 4 PHẠM VI",
        [(0.12, 0.70, "Quản trị viên\n(Admin)"), (0.12, 0.30, "Người dùng\n(User)")],
        [],
        [
            (0.35, 0.72, 0.32, 0.09, "UC-01: Đăng nhập JWT\n& Cấp mã truy cập"),
            (0.35, 0.56, 0.32, 0.09, "UC-02: Đổi mật khẩu\n& Thông tin cá nhân"),
            (0.35, 0.40, 0.32, 0.09, "UC-03: Quản lý Tài khoản\nvà Hồ sơ Giảng viên"),
            (0.35, 0.24, 0.32, 0.09, "UC-04: Cấu hình Phạm vi RBAC\n(SYSTEM/FACULTY/DEPT/SELF)"),
            (0.35, 0.08, 0.32, 0.09, "UC-05: Kiểm tra quyền truy cập\nvà Đồng bộ Trigger CSDL"),
        ],
        [
            (0.15, 0.65, 0.35, 0.76, "", "-"),
            (0.15, 0.65, 0.35, 0.44, "", "-"),
            (0.15, 0.65, 0.35, 0.28, "", "-"),
            (0.15, 0.65, 0.35, 0.12, "", "-"),
            (0.15, 0.30, 0.35, 0.74, "", "-"),
            (0.15, 0.30, 0.35, 0.60, "", "-"),
            (0.51, 0.40, 0.51, 0.33, "<<include>>", "--"),
            (0.51, 0.24, 0.51, 0.17, "<<include>>", "--"),
        ]
    )

    # 1.5 Use Case: Kế hoạch năm và Định mức 270 giờ chuẩn
    p5 = make_uc_diagram(
        "hinh_1_5_uc_ke_hoach_dinh_muc.png",
        "PHÂN HỆ KẾ HOẠCH NĂM VÀ ĐỊNH MỨC 270 GIỜ CHUẨN",
        [(0.12, 0.65, "Cấp Quản lý\n(Khoa / Bộ môn)")],
        [(0.88, 0.45, "Giảng viên\n(Lecturer)")],
        [
            (0.35, 0.72, 0.32, 0.09, "UC-06: Thiết lập Kế hoạch\nNăm học & Phân bổ chỉ tiêu"),
            (0.35, 0.56, 0.32, 0.09, "UC-07: Tải biểu mẫu chuẩn\nKế hoạch Excel (16 cột)"),
            (0.35, 0.40, 0.32, 0.09, "UC-08: Nhập Kế hoạch từ Excel\nvà Kiểm tra tính hợp lệ"),
            (0.35, 0.24, 0.32, 0.09, "UC-09: Tự động tính Giờ chuẩn\ntheo Thông tư 20/2020"),
            (0.35, 0.08, 0.32, 0.09, "UC-10: Tra cứu tiến độ tích lũy\n& Xuất báo cáo định mức"),
        ],
        [
            (0.15, 0.65, 0.35, 0.76, "", "-"),
            (0.15, 0.65, 0.35, 0.60, "", "-"),
            (0.15, 0.65, 0.35, 0.44, "", "-"),
            (0.15, 0.65, 0.35, 0.28, "", "-"),
            (0.85, 0.45, 0.67, 0.28, "", "-"),
            (0.85, 0.45, 0.67, 0.12, "", "-"),
            (0.51, 0.40, 0.51, 0.33, "<<include>>", "--"),
        ]
    )

    # 1.6 Use Case: Khởi tạo và Phân công công việc (Cưỡng chế 1 Leader)
    p6 = make_uc_diagram(
        "hinh_1_6_uc_phan_cong_cong_viec.png",
        "PHÂN HỆ KHỞI TẠO VÀ PHÂN CÔNG CÔNG VIỆC",
        [(0.12, 0.60, "Cấp Quản lý\n(Khoa / Bộ môn)")],
        [(0.88, 0.40, "Hệ thống CSDL\n(Triggers)")],
        [
            (0.35, 0.72, 0.32, 0.09, "UC-11: Tạo công việc mới\n(Tiêu đề, Loại việc, Deadline)"),
            (0.35, 0.56, 0.32, 0.09, "UC-12: Phân công Cá nhân\nhoặc Phân công Nhóm"),
            (0.35, 0.40, 0.32, 0.09, "UC-13: Cưỡng chế chỉ định\nduy nhất 1 Trưởng nhóm"),
            (0.35, 0.24, 0.32, 0.09, "UC-14: Thiết lập Checklist\nvà Phân rã đầu việc con"),
            (0.35, 0.08, 0.32, 0.09, "UC-15: Phát hành công việc\nvà Gửi thông báo đến GV"),
        ],
        [
            (0.15, 0.60, 0.35, 0.76, "", "-"),
            (0.15, 0.60, 0.35, 0.60, "", "-"),
            (0.15, 0.60, 0.35, 0.28, "", "-"),
            (0.15, 0.60, 0.35, 0.12, "", "-"),
            (0.85, 0.40, 0.67, 0.44, "<<enforce>>", "--"),
            (0.51, 0.56, 0.51, 0.49, "<<include>>", "--"),
            (0.51, 0.24, 0.51, 0.17, "<<include>>", "--"),
        ]
    )

    # 1.7 Use Case: Dự báo rủi ro trễ hạn & Gợi ý nhân sự AI
    p7 = make_uc_diagram(
        "hinh_1_7_uc_du_bao_tabpfn.png",
        "PHÂN HỆ DỰ BÁO RỦI RO VÀ GỢI Ý NHÂN SỰ AI",
        [(0.12, 0.60, "Cấp Quản lý\n(Khoa / Bộ môn)")],
        [(0.88, 0.50, "Dịch vụ Học máy\n(TabPFN v2 :8001)")],
        [
            (0.35, 0.72, 0.32, 0.09, "UC-16: Xem trước Rủi ro AI\n(Xác suất P(y=1) & Top factors)"),
            (0.35, 0.56, 0.32, 0.09, "UC-17: Trích xuất 58 đặc trưng\nnhân quả thời gian thực"),
            (0.35, 0.40, 0.32, 0.09, "UC-18: Dự báo song song theo lô\n(POST /predict-batch)"),
            (0.35, 0.24, 0.32, 0.09, "UC-19: Xếp hạng Điểm phù hợp S(u)\nvà Tự động đề cử Trưởng nhóm"),
            (0.35, 0.08, 0.32, 0.09, "UC-20: Cảnh báo chủ động mức Cao\n(P(y=1) >= 0.52 qua Notification)"),
        ],
        [
            (0.15, 0.60, 0.35, 0.76, "", "-"),
            (0.15, 0.60, 0.35, 0.28, "", "-"),
            (0.51, 0.72, 0.51, 0.65, "<<include>>", "--"),
            (0.51, 0.56, 0.51, 0.49, "<<call>>", "--"),
            (0.85, 0.50, 0.67, 0.44, "", "-"),
            (0.51, 0.40, 0.51, 0.33, "<<include>>", "--"),
            (0.51, 0.24, 0.51, 0.17, "<<extend>>", "--"),
        ]
    )

    # 1.8 Use Case: Cập nhật tiến độ, Nộp minh chứng & Phê duyệt 3 cấp
    p8 = make_uc_diagram(
        "hinh_1_8_uc_phe_duyet_3_cap.png",
        "PHÂN HỆ TIẾN ĐỘ, MINH CHỨNG VÀ PHÊ DUYỆT 3 CẤP",
        [(0.12, 0.75, "Thành viên\n(Member)"), (0.12, 0.40, "Trưởng nhóm\n(Team Leader)")],
        [(0.88, 0.55, "Cấp Quản lý\n(Reviewer)")],
        [
            (0.35, 0.72, 0.32, 0.09, "UC-21: Cập nhật % tiến độ\nvà Đính kèm URL minh chứng"),
            (0.35, 0.56, 0.32, 0.09, "UC-22: Thẩm tra tiến độ thành viên\nvà Duyệt nội bộ cấp Leader"),
            (0.35, 0.40, 0.32, 0.09, "UC-23: Tổng hợp báo cáo nhóm\nvà Gửi thẩm định lên Quản lý"),
            (0.35, 0.24, 0.32, 0.09, "UC-24: Cấp Quản lý Nghiệm thu\nhoàn thành công việc"),
            (0.35, 0.08, 0.32, 0.09, "UC-25: Từ chối / Yêu cầu bổ sung\nhồ sơ minh chứng"),
        ],
        [
            (0.15, 0.75, 0.35, 0.76, "", "-"),
            (0.15, 0.40, 0.35, 0.60, "", "-"),
            (0.15, 0.40, 0.35, 0.44, "", "-"),
            (0.85, 0.55, 0.67, 0.28, "", "-"),
            (0.85, 0.55, 0.67, 0.12, "", "-"),
            (0.51, 0.56, 0.51, 0.49, "<<include>>", "--"),
            (0.51, 0.40, 0.51, 0.33, "<<include>>", "--"),
        ]
    )

    # 1.9 Use Case: Giám sát MLOps và Tái huấn luyện định kỳ
    p9 = make_uc_diagram(
        "hinh_1_9_uc_mlops_monitoring.png",
        "PHÂN HỆ GIÁM SÁT MLOPS VÀ TÁI HUẤN LUYỆN ĐỊNH KỲ",
        [(0.12, 0.65, "Quản trị viên\n(Admin)")],
        [(0.88, 0.45, "Tiến trình nền\n(Cron Worker)")],
        [
            (0.35, 0.72, 0.32, 0.09, "UC-26: Ghi nhận nhãn thực tế\nvào FeedbackStore (completed_at)"),
            (0.35, 0.56, 0.32, 0.09, "UC-27: Giám sát hiệu chuẩn Mức 2\n(Wilson CI, ECE, PSI)"),
            (0.35, 0.40, 0.32, 0.09, "UC-28: Kích hoạt học tiếp tự động\n(retrain-auto qua 6 rào chắn)"),
            (0.35, 0.24, 0.32, 0.09, "UC-29: Kiểm tra mã băm SHA-256\nvà Nạp nóng mô hình (/reload)"),
            (0.35, 0.08, 0.32, 0.09, "UC-30: Tự động Rollback phiên bản\nkhi phát hiện bất thường"),
        ],
        [
            (0.15, 0.65, 0.35, 0.76, "", "-"),
            (0.15, 0.65, 0.35, 0.44, "", "-"),
            (0.15, 0.65, 0.35, 0.28, "", "-"),
            (0.85, 0.45, 0.67, 0.76, "", "-"),
            (0.85, 0.45, 0.67, 0.60, "", "-"),
            (0.85, 0.45, 0.67, 0.44, "", "-"),
            (0.51, 0.40, 0.51, 0.33, "<<include>>", "--"),
            (0.51, 0.24, 0.51, 0.17, "<<extend>>", "--"),
        ]
    )

    # 1.10 Sơ đồ lớp ở mức phân tích (Analysis Class Diagram)
    fig, ax = plt.subplots(figsize=(11, 6.4), dpi=220)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.96, "SƠ ĐỒ LỚP Ở MỨC PHÂN TÍCH (BOUNDARY - CONTROL - ENTITY)",
            ha="center", va="center", fontsize=10, fontweight="bold", color="#000000")
    classes = [
        (0.04, 0.65, 0.26, 0.24, "LỚP BIÊN (BOUNDARY)\n• WebAppUI\n• TaskManagementView\n• WorkloadPlanningView\n• MLMonitoringDashboard\n• LoginForm / JWTHandler"),
        (0.37, 0.65, 0.26, 0.24, "LỚP ĐIỀU KHIỂN (CONTROL)\n• TaskController\n• RBACController\n• WorkloadController\n• MLPredictionClient\n• MLOpsLifecycleManager"),
        (0.70, 0.65, 0.26, 0.24, "THỰC THỂ TỔ CHỨC (ENTITY)\n• User\n• LecturerProfile\n• Department\n• Role & Permission\n• UserPermissionScope"),
        (0.20, 0.12, 0.28, 0.40, "THỰC THỂ CÔNG VIỆC (ENTITY)\n• Task (code, title, deadline)\n• TaskAssignment (is_leader, status)\n• TaskType & TaskTypeScale\n• TaskChecklist\n• TaskComment\n• TaskHistory (Audit Log)"),
        (0.55, 0.12, 0.28, 0.40, "THỰC THỂ HỌC MÁY (ENTITY)\n• RiskPrediction (features, prob)\n• FeedbackStore (SQLite)\n• ModelRegistry (TabPFN v2)\n• Notification (dedupe_key)\n• CalendarEvent (holiday)"),
    ]
    for x, y, w, h, text in classes:
        draw_box(ax, x, y, w, h, text, bg="#FFFFFF", edge="#000000", fontsize=8.5, bold=False)
    draw_arrow(ax, 0.30, 0.77, 0.37, 0.77, "Yêu cầu")
    draw_arrow(ax, 0.63, 0.77, 0.70, 0.77, "Truy vấn")
    draw_arrow(ax, 0.50, 0.65, 0.34, 0.52, "Điều phối")
    draw_arrow(ax, 0.50, 0.65, 0.69, 0.52, "Gọi dự báo")
    draw_arrow(ax, 0.48, 0.32, 0.55, 0.32, "Nạp nhãn", linestyle="--")
    plt.tight_layout()
    p10 = os.path.join(OUT_DIR, "hinh_1_10_so_do_lop_phan_tich.png")
    plt.savefig(p10, dpi=220)
    plt.close(fig)

    # 1.11 Sơ đồ lớp ở mức thiết kế (CSDL 17 bảng)
    fig, ax = plt.subplots(figsize=(11.2, 6.6), dpi=220)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.96, "SƠ ĐỒ LỚP MỨC THIẾT KẾ: LƯỢC ĐỒ 17 BẢNG CƠ SỞ DỮ LIỆU QUAN HỆ (QLCV.DB)",
            ha="center", va="center", fontsize=10, fontweight="bold", color="#000000")
    groups = [
        (0.03, 0.52, 0.44, 0.38, "CỤM 1: TỔ CHỨC & NHÂN SỰ (3 BẢNG)\n"
         "• Department (id, code, name, ml_name)\n"
         "• User (id, username, full_name, role, department_id)\n"
         "• LecturerProfile (user_id, academic_rank, degree,\n"
         "  management_role, teaching_hours_semester, student_count)"),
        (0.53, 0.52, 0.44, 0.38, "CỤM 2: PHÂN QUYỀN RBAC ĐỒNG BỘ (4 BẢNG)\n"
         "• Role (code [admin/manager/lecturer], name, default_scope)\n"
         "• Permission (code [15 mã quyền], name, module)\n"
         "• RolePermission (role_code, permission_code [32 ánh xạ])\n"
         "• UserPermissionScope (user_id, role_code, scope\n"
         "  [SYSTEM / FACULTY / DEPARTMENT / SELF])"),
        (0.03, 0.06, 0.44, 0.38, "CỤM 3: DANH MỤC & CÔNG VIỆC (8 BẢNG)\n"
         "• TaskType & TaskTypeScale (expected_days, conversion_hours)\n"
         "• CalendarEvent (holiday, accreditation)\n"
         "• Task (id, code, title, scale, priority, complexity, deadline)\n"
         "• TaskAssignment (task_id, lecturer_id, is_leader, status, is_late)\n"
         "• TaskChecklist, TaskComment, TaskHistory (Audit Log)"),
        (0.53, 0.06, 0.44, 0.38, "CỤM 4: DỰ BÁO HỌC MÁY & CẢNH BÁO (2 BẢNG + MLOPS)\n"
         "• RiskPrediction (task_id, assignment_id, lecturer_id,\n"
         "  features_json [58 cột], probability, level, uncertainty,\n"
         "  top_factors, model_version [TabPFN v2], latency_ms)\n"
         "• Notification (user_id, kind [risk_high], dedupe_key)\n"
         "• Kho MLOps: FeedbackStore (SQLite) & ModelRegistry (v0001)"),
    ]
    for x, y, w, h, text in groups:
        draw_box(ax, x, y, w, h, text, bg="#FFFFFF", edge="#000000", fontsize=8.7, bold=False)
    draw_arrow(ax, 0.47, 0.71, 0.53, 0.71, "1 - 1 / 1 - N")
    draw_arrow(ax, 0.25, 0.52, 0.25, 0.44, "1 - N")
    draw_arrow(ax, 0.47, 0.25, 0.53, 0.25, "1 - N")
    draw_arrow(ax, 0.75, 0.52, 0.75, 0.44, "Kiểm soát RBAC")
    plt.tight_layout()
    p11 = os.path.join(OUT_DIR, "hinh_1_11_so_do_lop_csdl.png")
    plt.savefig(p11, dpi=220)
    plt.close(fig)

    print("Hoàn thành vẽ 11 sơ đồ UML hệ thống!")


if __name__ == "__main__":
    generate_all_diagrams()
