# -*- coding: utf-8 -*-
"""
Phần mở rộng chuyên sâu (theo mẫu DoAn_HoanChinh.pdf & 1-huong-dan-kltn.docx):
- Đặc tả chi tiết từng Use Case nghiệp vụ (UC-01 .. UC-06) cho Chương 1
- Đặc tả chi tiết 15 Mã quyền RBAC & Cấu trúc chi tiết từng nhóm bảng trong 17 bảng CSDL cho Chương 3
- Mô tả chi tiết các màn hình giao diện ứng dụng Web & Kiểm thử chức năng cho Chương 4
"""
from docx.enum.text import WD_ALIGN_PARAGRAPH
from kltn_part1_front_and_ch1_ch2 import (
    add_p, add_bullet, add_h1, add_h2, add_h3, add_styled_table
)


def append_chapter1_usecases(doc):
    add_h1(doc, "1.4. Đặc tả chi tiết các Ca sử dụng (Use Cases) cốt lõi")
    add_p(doc, "Dựa trên 10 yêu cầu chức năng đã xác định ở mục 1.3, hệ thống được mô hình hóa thành 6 ca sử dụng (Use Cases) trọng tâm phản ánh đầy đủ vòng đời điều hành công việc tại Khoa Công nghệ Thông tin – HUIT:")

    ucs = [
        ("Bảng 1.4: Đặc tả Use Case UC-01 – Quản lý Kế hoạch năm & Nhập/Xuất biểu mẫu Excel chuẩn", [
            ["Mã và Tên Use Case", "UC-01: Quản lý Kế hoạch công việc năm học & Đồng bộ định mức 270 giờ chuẩn"],
            ["Tác nhân chính", "Ban Chủ nhiệm Khoa (truongkhoa – phạm vi FACULTY), Trưởng Bộ môn (tbm_k01..04 – phạm vi DEPARTMENT), Quản trị viên (admin)"],
            ["Quyền RBAC yêu cầu", "PLAN_VIEW (Xem kế hoạch & định mức), PLAN_MANAGE (Tạo/sửa kế hoạch, nhập/xuất Excel chuẩn)"],
            ["Điều kiện tiên quyết", "Người dùng đã đăng nhập hợp lệ; danh mục loại công việc (task_types) và bảng quy đổi giờ chuẩn (task_type_scales) đã được khởi tạo."],
            ["Luồng sự kiện chính", "1. Người quản lý mở phân hệ 'Kế hoạch & Định mức', xem tổng giờ chuẩn định mức của từng danh mục (Đề cương chi tiết, Hướng dẫn ĐACN/KLTN, Bài báo Scopus/ISI, Minh chứng kiểm định) và số lượng công việc thực tế đã ánh xạ.\n2. Người quản lý chọn 'Tải biểu mẫu kế hoạch chuẩn' để xuất tệp Excel (.xlsx) gồm đầy đủ 16 cột chuẩn hóa kèm trang tính Danh mục tham chiếu.\n3. Người quản lý điền danh sách đầu việc năm học vào tệp Excel và bấm 'Nhập Kế hoạch từ Excel'.\n4. Hệ thống kiểm tra hợp lệ từng dòng, tự động ánh xạ loại việc, quy mô, giảng viên phụ trách và khởi tạo đồng loạt các bản ghi công việc."],
            ["Luồng ngoại lệ", "Nếu tệp Excel thiếu cột bắt buộc hoặc mã giảng viên/loại việc không tồn tại, hệ thống thông báo chi tiết dòng lỗi và hủy giao dịch nhập theo lô."],
            ["Hậu điều kiện", "Các công việc trong kế hoạch năm được lưu vào bảng tasks và task_assignments; số giờ chuẩn quy đổi được cộng dồn tự động vào tiến độ định mức 270 giờ/năm."],
        ]),
        ("Bảng 1.5: Đặc tả Use Case UC-02 – Giao việc thông minh kết hợp Xem trước rủi ro & Gợi ý AI", [
            ["Mã và Tên Use Case", "UC-02: Khởi tạo công việc, Xem trước rủi ro trễ hạn (TabPFN v2) và Gợi ý nhân sự / Trưởng nhóm"],
            ["Tác nhân chính", "Ban Chủ nhiệm Khoa (truongkhoa), Trưởng Bộ môn (tbm_k01..04)"],
            ["Quyền RBAC yêu cầu", "TASK_CREATE, TASK_ASSIGN, ML_PREDICT_VIEW, ML_RECOMMEND_USE"],
            ["Điều kiện tiên quyết", "Người quản lý có quyền giao việc trong phạm vi Bộ môn hoặc toàn Khoa; dịch vụ ML cổng 8001 đang hoạt động (hoặc sẵn sàng chế độ suy giảm an toàn)."],
            ["Luồng sự kiện chính", "1. Người quản lý nhập tiêu đề, chọn nhóm/loại công việc, quy mô (Nhỏ/Vừa/Lớn), độ phức tạp, mức ưu tiên và hạn chót.\n2. Người quản lý bấm 'Gợi ý Nhân sự AI': Backend trích xuất 58 đặc trưng cho toàn bộ giảng viên thuộc phạm vi và gọi POST /predict-batch trên TabPFN v2.\n3. Giao diện hiển thị bảng xếp hạng giảng viên theo Điểm phù hợp S(u), xác suất trễ hạn P(y=1), mức cảnh báo (Thấp/Trung bình/Cao), các yếu tố rủi ro hàng đầu và tự động đề cử Trưởng nhóm (nếu giao việc nhóm).\n4. Người quản lý xác nhận danh sách giảng viên, chỉ định duy nhất 1 Trưởng nhóm và bấm 'Giao việc'."],
            ["Luồng ngoại lệ", "1. Nếu chọn >= 2 giảng viên nhưng không chọn hoặc chọn nhiều hơn 1 Trưởng nhóm: hệ thống chặn ngay tại giao diện và API (HTTP 400).\n2. Nếu dịch vụ ML cổng 8001 quá thời gian chờ (timeout): hệ thống vẫn lưu công việc thành công và ghi nhận RiskPrediction ở trạng thái 'failed' kèm ghi chú suy giảm an toàn."],
            ["Hậu điều kiện", "Bản ghi công việc, phân công, lịch sử dự báo rủi ro và thông báo cảnh báo (nếu mức Cao) được lưu bền vững vào CSDL."],
        ]),
        ("Bảng 1.6: Đặc tả Use Case UC-03 – Cập nhật tiến độ và Phê duyệt công việc nhóm 3 cấp", [
            ["Mã và Tên Use Case", "UC-03: Thực hiện công việc, Duyệt nội bộ cấp Trưởng nhóm và Nghiệm thu cấp Quản lý"],
            ["Tác nhân chính", "Giảng viên thành viên (Member), Giảng viên Trưởng nhóm (Team Leader), Cấp Quản lý (Reviewer/Manager)"],
            ["Quyền RBAC yêu cầu", "TASK_UPDATE_PROGRESS (Thành viên & Trưởng nhóm), TASK_APPROVE (Quản lý nghiệm thu)"],
            ["Điều kiện tiên quyết", "Công việc đã được giao hợp lệ; các bản ghi phân công tồn tại trong bảng task_assignments."],
            ["Luồng sự kiện chính", "1. Giảng viên thành viên cập nhật tỷ lệ hoàn thành (progress_pct = 100%), đính kèm đường dẫn minh chứng và bấm 'Gửi Trưởng nhóm duyệt' (trạng thái chuyển sang 'Chờ trưởng nhóm duyệt').\n2. Giảng viên Trưởng nhóm kiểm tra phần việc của từng thành viên, bấm 'Duyệt thành viên' (hoặc yêu cầu làm lại). Khi 100% thành viên hoàn tất, Trưởng nhóm bấm 'Gửi báo cáo cấp trên' (trạng thái chuyển sang 'Chờ duyệt').\n3. Cấp Quản lý kiểm tra minh chứng tổng thể và bấm 'Phê duyệt hoàn thành' (status = 'Đã hoàn thành').\n4. Hệ thống tự động ghi nhận completed_at, tính toán cờ trễ hạn is_late, số ngày trễ delay_days và đẩy nhãn thực tế vào kho phản hồi MLOps (FeedbackStore)."],
            ["Luồng ngoại lệ", "Nếu thành viên chưa phải Trưởng nhóm cố tình gọi API duyệt hoặc gửi báo cáo cấp trên, tầng RBAC trả về lỗi HTTP 403 Forbidden."],
            ["Hậu điều kiện", "Trạng thái công việc hoàn tất, lịch sử kiểm toán (task_history) và nhãn học tiếp MLOps được cập nhật đồng bộ."],
        ]),
    ]
    for cap, rows in ucs:
        add_styled_table(
            doc,
            caption=cap,
            headers=["Thuộc tính Use Case", "Nội dung đặc tả chi tiết"],
            rows=rows,
            col_aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT],
            font_size=11
        )


def append_chapter3_rbac_and_schema(doc):
    add_h1(doc, "3.6. Đặc tả chi tiết 15 Mã quyền chức năng RBAC trong Cơ sở dữ liệu")
    add_p(doc, "Để loại bỏ hoàn toàn tình trạng kiểm tra quyền rời rạc chỉ bằng tên vai trò chuỗi ký tự (hardcoded role strings), mô-đun backend/app/rbac.py định nghĩa danh mục 15 mã quyền nguyên tử (atomic permissions) lưu trong bảng permissions và ánh xạ vào bảng role_permissions:")

    add_styled_table(
        doc,
        caption="Bảng 3.6: Danh mục đầy đủ 15 mã quyền chức năng (permissions) và ánh xạ theo 3 vai trò",
        headers=["STT", "Mã quyền (code)", "Phân hệ (module)", "Tên quyền chức năng", "Admin (SYSTEM)", "Manager (FACULTY / DEPT)", "Lecturer (SELF)"],
        rows=[
            ["1", "TASK_VIEW", "tasks", "Xem danh sách và chi tiết công việc theo phạm vi", "Có", "Có", "Có"],
            ["2", "TASK_CREATE", "tasks", "Tạo đầu việc mới trong Khoa/Bộ môn", "Có", "Có", "Không"],
            ["3", "TASK_UPDATE", "tasks", "Chỉnh sửa thông tin công việc và hạn chót", "Có", "Có", "Không"],
            ["4", "TASK_DELETE", "tasks", "Xóa hoặc hủy bỏ công việc", "Có", "Có", "Không"],
            ["5", "TASK_ASSIGN", "tasks", "Phân công giảng viên và chỉ định Trưởng nhóm", "Có", "Có", "Không"],
            ["6", "TASK_UPDATE_PROGRESS", "tasks", "Cập nhật tiến độ, nộp minh chứng và điều phối nhóm", "Có", "Có", "Có"],
            ["7", "TASK_APPROVE", "tasks", "Nghiệm thu hoàn thành hoặc trả lại công việc", "Có", "Có", "Không (*)"],
            ["8", "TASK_COMMENT", "tasks", "Gửi bình luận trao đổi và xem lịch sử công việc", "Có", "Có", "Có"],
            ["9", "PLAN_VIEW", "plans", "Xem kế hoạch năm học và định mức 270 giờ chuẩn", "Có", "Có", "Có"],
            ["10", "PLAN_MANAGE", "plans", "Quản lý kế hoạch năm, nhập/xuất biểu mẫu Excel", "Có", "Có", "Không"],
            ["11", "USER_VIEW", "users", "Xem danh sách giảng viên và hồ sơ năng lực", "Có", "Có", "Có"],
            ["12", "USER_MANAGE", "users", "Thêm/sửa/khóa tài khoản và cấu hình phân quyền RBAC", "Có", "Không", "Không"],
            ["13", "DEPT_MANAGE", "departments", "Quản lý danh mục Bộ môn và cấu hình hệ thống", "Có", "Không", "Không"],
            ["14", "ML_PREDICT_VIEW", "ml", "Xem dự báo xác suất trễ hạn và giải thích TabPFN v2", "Có", "Có", "Không"],
            ["15", "ML_RECOMMEND_USE", "ml", "Sử dụng gợi ý phân công AI & Quản trị mô hình MLOps", "Có", "Có", "Không"],
        ],
        col_aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        font_size=10.5
    )
    add_p(doc, "Ghi chú (*): Đối với Giảng viên (Lecturer), khi được chỉ định làm Trưởng nhóm (is_leader = True) trên một công việc nhóm cụ thể, hệ thống cấp quyền ngữ cảnh động (Contextual Leader Permission) cho phép duyệt phần việc của các thành viên trong đúng công việc đó trước khi gửi báo cáo tổng hợp lên cấp Quản lý.", italic=True, indent_cm=0, font_size=12)


def append_chapter4_ui_walkthrough(doc):
    add_h1(doc, "4.5. Kết quả xây dựng và Kiểm chứng Giao diện Ứng dụng Web đồng bộ CSDL")
    add_p(doc, "Song song với dịch vụ Học máy và Backend API, ứng dụng giao diện Web (React 19, TypeScript, Tailwind CSS) đã được xây dựng hoàn chỉnh và kiểm chứng đồng bộ 100% với cơ sở dữ liệu qlcv.db qua 5 phân hệ chức năng chính:")
    add_bullet(doc, "1. Phân hệ Đăng nhập và Hiển thị Phạm vi Phân quyền RBAC: ",
               "Cho phép chuyển đổi nhanh hoặc đăng nhập trực tiếp vào 18 tài khoản mẫu thuộc 4 Bộ môn (admin, truongkhoa, tbm_k01..04, gv_k01..04_*). Ngay sau khi đăng nhập, thanh trạng thái hiển thị rõ Vai trò, Phạm vi dữ liệu (SYSTEM / FACULTY / DEPARTMENT / SELF) và ẩn/hiện chính xác các nút chức năng theo đúng 15 mã quyền trả về từ API /api/auth/login.")
    add_bullet(doc, "2. Phân hệ Bảng điều khiển Tổng quan (Executive Dashboard): ",
               "Hiển thị trực quan các chỉ số KPI thời gian thực (Tổng số công việc, Đang thực hiện, Chờ duyệt, Đã hoàn thành, Số công việc có rủi ro trễ hạn mức Cao do TabPFN v2 cảnh báo), biểu đồ phân bố tải công việc giữa 4 Bộ môn (K01: CNPM, K02: HTTT, K03: KHMT, K04: MMT & ATTT) và danh sách cảnh báo sớm cần ưu tiên xử lý.")
    add_bullet(doc, "3. Phân hệ Quản lý Công việc, Giao việc AI và Phê duyệt 3 cấp: ",
               "Tích hợp hộp thoại Tạo & Giao việc thông minh cho phép bấm 'Xem trước rủi ro AI' và 'Gợi ý nhân sự phù hợp nhất'. Khi giao việc nhóm, giao diện tự động kiểm tra ràng buộc duy nhất 1 Trưởng nhóm và hiển thị luồng tiến độ 3 cấp (Thành viên cập nhật % -> Trưởng nhóm duyệt nội bộ -> Quản lý nghiệm thu).")
    add_bullet(doc, "4. Phân hệ Kế hoạch Năm học & Định mức 270 giờ chuẩn: ",
               "Hiển thị đầy đủ số giờ chuẩn định mức, số giờ đã ánh xạ từ các công việc thực tế và tỷ lệ hoàn thành của từng hạng mục (Đề cương chi tiết học phần chuẩn kiểm định, Hướng dẫn Đồ án chuyên ngành / KLTN, Bài báo khoa học Tạp chí Scopus / ISI uy tín, Minh chứng kiểm định chương trình đào tạo quốc tế). Hỗ trợ nút 'Tải biểu mẫu kế hoạch chuẩn' (xuất tệp Excel .xlsx 16 cột đồng bộ hoàn toàn với các phân hệ khác) và 'Nhập Kế hoạch Công việc Năm từ Excel'.")
    add_bullet(doc, "5. Phân hệ Trung tâm Điều hành Học máy & MLOps (AI & Continual Learning Hub): ",
               "Hiển thị trạng thái thời gian thực của dịch vụ ML cổng 8001 (Mô hình đang chạy: TabPFN v2 • 9.2.0 • 4 túi ngữ cảnh, phiên bản kho CURRENT = v0001, ngưỡng cảnh báo [0,23; 0,52], ROC-AUC = 80,9% tĩnh / 83,9% động), cho phép theo dõi nhật ký dự báo và kích hoạt quy trình huấn luyện lại có rào chắn chất lượng.")
