# -*- coding: utf-8 -*-
"""
CHƯƠNG 3: PHƯƠNG PHÁP VÀ QUY TRÌNH THỰC HIỆN
Cấu trúc chuẩn hóa 100% theo DoAn_HoanChinh.pdf & thesis-writer:
- Toàn bộ chữ màu đen (RGB 0, 0, 0), nền trắng kể cả bảng
- Phông chữ Times New Roman, cỡ 13 pt (kể cả chữ trong bảng)
- Thay toàn bộ dấu gạch ngang dài thành '-'
- Khử tối đa văn phong AI, trình bày logic theo từng bước thủ tục kỹ thuật
- Tích hợp liên kết nội bộ cho các trích dẫn tài liệu tham khảo
"""
from docx.enum.text import WD_ALIGN_PARAGRAPH
from kltn_part1_front_and_ch1_ch2 import (
    add_p, add_bullet, add_chapter_title, add_h1, add_h2, add_h3,
    add_styled_table
)


def build_chapter3(doc):
    add_chapter_title(doc, "CHƯƠNG 3", "PHƯƠNG PHÁP VÀ QUY TRÌNH THỰC HIỆN", page_break=True)

    # 3.1
    add_h1(doc, "3.1. Hàm thủ tục quản lý công việc và phê duyệt 3 cấp")

    add_h2(doc, "3.1.1. Thủ tục thêm công việc mới và kiểm tra Trưởng nhóm (sp_ThemCongViec)")
    add_p(doc, "Mô tả: Thủ tục sp_ThemCongViec được gọi khi Ban Chủ nhiệm Khoa hoặc Trưởng Bộ môn khởi tạo một đầu việc mới trên hệ thống, thực hiện kiểm tra tính hợp lệ của loại việc, thời hạn và cưỡng chế tính duy nhất của Trưởng nhóm khi giao việc nhóm [13].")
    add_bullet(doc, "Bước 1: ", "Nhận vào các tham số: mã loại việc, tiêu đề, quy mô (Nhỏ/Vừa/Lớn), độ phức tạp, mức ưu tiên, hạn chót, danh sách mã giảng viên được giao (@LecturerIDs) và cờ chỉ định Trưởng nhóm (@LeaderID).")
    add_bullet(doc, "Bước 2: ", "Bắt đầu giao dịch (BEGIN TRANSACTION) để đảm bảo tính toàn vẹn dữ liệu.")
    add_bullet(doc, "Bước 3: ", "Kiểm tra ràng buộc Trưởng nhóm: nếu số lượng giảng viên >= 2 (Group Assignment) thì bắt buộc @LeaderID phải thuộc danh sách @LecturerIDs và chỉ có duy nhất 1 người được gắn cờ is_leader = True.")
    add_bullet(doc, "Bước 4: ", "Chèn bản ghi vào bảng tasks với mã công việc tự sinh (code định dạng CV-YYMMDD-XXXX), ngày giao assigned_at = thời điểm hiện tại, trạng thái 'Chưa bắt đầu'.")
    add_bullet(doc, "Bước 5: ", "Chèn các bản ghi phân công vào bảng task_assignments cho từng giảng viên, gắn cờ is_leader tương ứng.")
    add_bullet(doc, "Bước 6: ", "Nếu thành công thì COMMIT và trả về mã công việc mới; nếu lỗi thì ROLLBACK và ném thông báo lỗi.")

    add_h2(doc, "3.1.2. Thủ tục duyệt tiến độ thành viên cấp Trưởng nhóm (sp_TruongNhomDuyet)")
    add_p(doc, "Mô tả: Thủ tục này cho phép Giảng viên Trưởng nhóm (Team Leader) kiểm tra và duyệt phần việc của từng thành viên trong nhóm trước khi báo cáo lên cấp quản lý.")
    add_bullet(doc, "Bước 1: ", "Nhận vào mã phân công (@AssignmentID) và mã người thực hiện duyệt (@CurrentUserID).")
    add_bullet(doc, "Bước 2: ", "Kiểm tra quyền hạn: người gọi thủ tục phải là Trưởng nhóm (is_leader = True) của đúng công việc liên quan theo mô hình RBAC [13].")
    add_bullet(doc, "Bước 3: ", "Kiểm tra trạng thái bản ghi phân công: phải đang ở trạng thái 'Chờ trưởng nhóm duyệt' và progress_pct = 100%.")
    add_bullet(doc, "Bước 4: ", "Cập nhật trạng thái bản ghi của thành viên thành 'Đã duyệt nội bộ'.")
    add_bullet(doc, "Bước 5: ", "Kiểm tra nếu 100% thành viên trong nhóm đều đã được duyệt nội bộ thì tự động chuyển trạng thái công việc chung sang 'Chờ duyệt' để sẵn sàng cho cấp Quản lý nghiệm thu.")

    add_h2(doc, "3.1.3. Thủ tục từ chối hoặc yêu cầu chỉnh sửa công việc (sp_TuChoiCongViec)")
    add_p(doc, "Mô tả: Dùng khi Trưởng nhóm hoặc Cấp Quản lý không chấp nhận báo cáo hoàn thành do minh chứng chưa đạt yêu cầu.")
    add_bullet(doc, "Bước 1: ", "Nhận vào mã công việc (@TaskID), mã người từ chối (@UserID) và lý do từ chối (@RejectReason).")
    add_bullet(doc, "Bước 2: ", "Chuyển trạng thái công việc từ 'Chờ duyệt' quay trở lại 'Đang thực hiện'.")
    add_bullet(doc, "Bước 3: ", "Ghi nhận lý do vào bảng task_comments và lưu vết vào bảng task_history (Audit Log).")
    add_bullet(doc, "Bước 4: ", "Gửi thông báo (Notification) đến các giảng viên liên quan để yêu cầu bổ sung hồ sơ minh chứng.")

    add_h2(doc, "3.1.4. Thủ tục hủy phân công công việc (sp_HuyCongViec)")
    add_p(doc, "Mô tả: Cho phép người có thẩm quyền hủy bỏ một công việc đã giao khi có thay đổi kế hoạch từ Nhà trường.")
    add_bullet(doc, "Bước 1: ", "Nhận vào mã công việc (@TaskID).")
    add_bullet(doc, "Bước 2: ", "Kiểm tra công việc không ở trạng thái 'Đã hoàn thành'.")
    add_bullet(doc, "Bước 3: ", "Cập nhật trạng thái trong tasks và task_assignments thành 'Đã hủy'.")
    add_bullet(doc, "Bước 4: ", "Xóa các cảnh báo rủi ro chưa xử lý liên quan đến công việc này trong bảng notifications.")

    add_h2(doc, "3.1.5. Thủ tục cập nhật tiến độ công việc và nộp minh chứng (sp_CapNhatTienDo)")
    add_p(doc, "Mô tả: Giảng viên cập nhật tỷ lệ hoàn thành định kỳ và đính kèm đường dẫn minh chứng.")
    add_bullet(doc, "Bước 1: ", "Nhận vào @AssignmentID, @ProgressPct (từ 0 đến 100) và @EvidenceURL.")
    add_bullet(doc, "Bước 2: ", "Cập nhật trường progress_pct và evidence_url trong bảng task_assignments.")
    add_bullet(doc, "Bước 3: ", "Nếu @ProgressPct = 100% và công việc có Trưởng nhóm -> chuyển trạng thái sang 'Chờ trưởng nhóm duyệt'; nếu là việc cá nhân -> chuyển sang 'Chờ duyệt'.")
    add_bullet(doc, "Bước 4: ", "Ghi vết vào task_history với nhãn tiến độ mới.")

    add_h2(doc, "3.1.6. Thủ tục nghiệm thu hoàn thành và ghi nhận trễ hạn (sp_NghiemThuCongViec)")
    add_p(doc, "Mô tả: Ban Chủ nhiệm Khoa hoặc Trưởng Bộ môn phê duyệt hoàn thành cuối cùng, tự động tính toán trễ hạn và kích hoạt MLOps [14].")
    add_bullet(doc, "Bước 1: ", "Nhận vào mã công việc (@TaskID) và mã người nghiệm thu (@ManagerID).")
    add_bullet(doc, "Bước 2: ", "Xác định thời điểm hiện tại: @CompletedAt = NOW().")
    add_bullet(doc, "Bước 3: ", "So sánh @CompletedAt với original_deadline của công việc:")
    add_bullet(doc, "", "• Nếu @CompletedAt > original_deadline: @IsLate = True, @DelayDays = số ngày trễ thực tế.")
    add_bullet(doc, "", "• Nếu @CompletedAt <= original_deadline: @IsLate = False, @DelayDays = 0.")
    add_bullet(doc, "Bước 4: ", "Cập nhật trạng thái công việc thành 'Đã hoàn thành', ghi completed_at, is_late, delay_days vào task_assignments.")
    add_bullet(doc, "Bước 5: ", "Ghi nhận nhãn thực tế vào kho phản hồi FeedbackStore để phục vụ tái huấn luyện học máy [14].")

    add_h2(doc, "3.1.7. Thủ tục kiểm tra định mức giờ chuẩn 270 giờ (sp_KiemTraDinhMuc)")
    add_p(doc, "Mô tả: Tính tổng số giờ chuẩn tích lũy của giảng viên trong năm học và so sánh với định mức 270 giờ theo Thông tư 20/2020/TT-BGDĐT [1].")
    add_bullet(doc, "Bước 1: ", "Nhận vào @LecturerID và @AcademicYear.")
    add_bullet(doc, "Bước 2: ", "Truy vấn các công việc đã hoàn thành hoặc đang thực hiện của giảng viên trong năm học.")
    add_bullet(doc, "Bước 3: ", "Nối (JOIN) với bảng task_type_scales để lấy conversion_hours.")
    add_bullet(doc, "Bước 4: ", "Tính tổng giờ chuẩn đạt được, tỷ lệ hoàn thành định mức (%) và số giờ còn thiếu.")

    add_h2(doc, "3.1.8. Thủ tục duyệt công việc và tạo phiếu giao việc (sp_DuyetCongViec)")
    add_p(doc, "Mô tả: Phê duyệt đề xuất công việc từ cấp Bộ môn và tạo phiếu giao việc chính thức.")
    add_bullet(doc, "Bước 1: ", "Nhận mã công việc @TaskID.")
    add_bullet(doc, "Bước 2: ", "Kiểm tra tính hợp lệ của nguồn kinh phí hoặc giờ chuẩn quy đổi theo quy chế [1].")
    add_bullet(doc, "Bước 3: ", "Cập nhật trạng thái duyệt và sinh phiếu giao việc điện tử lưu vào hệ thống.")

    add_h2(doc, "3.1.9. Thủ tục quản lý nội quy và xử lý vi phạm tiến độ (sp_XuLyViPham)")
    add_p(doc, "Mô tả: Ghi nhận và xử lý các trường hợp chậm trễ tiến độ hoặc không nộp minh chứng đúng hạn.")
    add_bullet(doc, "Bước 1: ", "Tự động quét định kỳ các công việc có hạn chót < ngày hiện tại mà chưa hoàn thành.")
    add_bullet(doc, "Bước 2: ", "Cập nhật cờ overdue_open_tasks trong thống kê giảng viên và gửi thông báo nhắc nhở.")

    # 3.2
    add_h1(doc, "3.2. Hàm thủ tục giảng viên và phân quyền RBAC")

    add_h2(doc, "3.2.1. Thủ tục lấy tất cả thông tin giảng viên kèm tiến độ công việc trong ngày")
    add_p(doc, "Mô tả: Truy vấn danh sách giảng viên thuộc Bộ môn/Khoa kèm theo số lượng công việc đang mở, công việc ưu tiên cao và tiến độ trung bình.")
    add_bullet(doc, "Bước 1: ", "Nhận vào @DepartmentID (hoặc NULL nếu là cấp Khoa).")
    add_bullet(doc, "Bước 2: ", "Nối các bảng users, lecturer_profiles, departments và task_assignments.")
    add_bullet(doc, "Bước 3: ", "Tính toán các biến đếm: active_tasks, active_high_priority_tasks, overdue_open_tasks.")
    add_bullet(doc, "Bước 4: ", "Trả về danh sách phục vụ hiển thị trên giao diện Quản trị Nhân sự.")

    add_h2(doc, "3.2.2. Thủ tục kiểm tra đăng nhập và cấp quyền RBAC 4 phạm vi (sp_KiemTraQuyen)")
    add_p(doc, "Mô tả: Xác thực tài khoản người dùng và trả về danh sách 15 mã quyền chức năng cùng phạm vi dữ liệu theo kiến trúc RBAC [13].")
    add_bullet(doc, "Bước 1: ", "Nhận @Username và @PasswordHash.")
    add_bullet(doc, "Bước 2: ", "Kiểm tra trong bảng users: xác thực mật khẩu băm bcrypt và cờ is_active = True.")
    add_bullet(doc, "Bước 3: ", "Truy vấn bảng user_permission_scopes để lấy vai trò (role_code) và phạm vi dữ liệu (scope: SYSTEM / FACULTY / DEPARTMENT / SELF [13]).")
    add_bullet(doc, "Bước 4: ", "Nối với role_permissions để lấy toàn bộ danh sách mã quyền chức năng (15 mã quyền).")
    add_bullet(doc, "Bước 5: ", "Đóng gói Payload và ký cấp JWT Access Token.")

    add_h2(doc, "3.2.3. Thủ tục tự động đồng bộ phạm vi quyền hạn bằng Triggers (trg_users_sync_scope)")
    add_p(doc, "Mô tả: SQLite Trigger tự động tạo hoặc cập nhật bản ghi trong user_permission_scopes mỗi khi có thay đổi trong bảng users.")
    add_bullet(doc, "Bước 1: ", "Kích hoạt sau khi chèn (AFTER INSERT) hoặc sau khi sửa (AFTER UPDATE) trên bảng users.")
    add_bullet(doc, "Bước 2: ", "Xác định scope mặc định theo role: admin -> SYSTEM; manager (trưởng khoa) -> FACULTY; manager (trưởng bộ môn) -> DEPARTMENT; lecturer -> SELF.")
    add_bullet(doc, "Bước 3: ", "Cập nhật bảng user_permission_scopes đảm bảo đồng bộ 100%.")

    add_h2(doc, "3.2.4. Thủ tục lấy danh sách công việc của giảng viên trong khoảng thời gian")
    add_p(doc, "Mô tả: Lọc danh sách công việc được giao của một giảng viên theo khoảng ngày bắt đầu và kết thúc.")
    add_bullet(doc, "Bước 1: ", "Nhận @LecturerID, @StartDate, @EndDate.")
    add_bullet(doc, "Bước 2: ", "Truy vấn bảng task_assignments JOIN tasks theo điều kiện assigned_at nằm trong khoảng.")
    add_bullet(doc, "Bước 3: ", "Trả về danh sách kèm trạng thái và liên kết minh chứng.")

    add_h2(doc, "3.2.5. Thủ tục ghi nhận lịch sử kiểm toán Audit Log (sp_GhiNhanLichSu)")
    add_p(doc, "Mô tả: Lưu vết mọi thay đổi trạng thái, phân công và phê duyệt vào bảng task_history.")
    add_bullet(doc, "Bước 1: ", "Nhận @TaskID, @UserID, @Action, @OldStatus, @NewStatus, @Notes.")
    add_bullet(doc, "Bước 2: ", "Chèn dòng mới vào task_history với created_at = NOW().")

    add_h2(doc, "3.2.6. Thủ tục tìm kiếm công việc và nhân sự (sp_TimKiemCongViec)")
    add_p(doc, "Mô tả: Hỗ trợ tìm kiếm nhanh công việc theo từ khóa tiêu đề, mã công việc, tên giảng viên hoặc loại việc.")
    add_bullet(doc, "Bước 1: ", "Nhận vào chuỗi @Keyword và phạm vi quyền của người gọi.")
    add_bullet(doc, "Bước 2: ", "Thực hiện tìm kiếm LIKE trên code, title và username có kiểm soát phạm vi RBAC [13].")

    # 3.3
    add_h1(doc, "3.3. Thủ tục hàm của Học máy và Tài nguyên")

    add_h2(doc, "3.3.1. Thủ tục trích xuất 58 trường đặc trưng nhân quả (ml_extract.py)")
    add_p(doc, "Mô tả: Truy vấn CSDL và dựng đủ 58 trường đặc trưng thời gian thực tại thời điểm giao việc t (chỉ sử dụng dữ liệu đã hoàn thành trước t) theo cơ chế Bayes làm mịn [8]:")
    add_styled_table(
        doc,
        caption="Bảng 3.1: Danh mục đầy đủ 58 trường đặc trưng nhân quả (FEATURE_SCHEMA) và 3 cột lọc trùng",
        headers=["Nhóm đặc trưng", "Số lượng", "Danh sách tên trường đặc trưng (FEATURE_SCHEMA)", "Quy tắc tính toán và xử lý giá trị thiếu"],
        rows=[
            ["1. Thuộc tính Công việc", "15 trường", "task_group, task_type, task_subtype (*), assignment_level, assignment_mode, assignment_channel, priority, complexity, subtask_count, dependency_count, team_size, is_urgent_assignment, require_external_input, require_approval, converted_workload", "Tra bảng task_type_scales [1]; mã hóa complexity_num (0..2) và priority_num (0..3). Cột task_subtype (*) được lọc trùng khi đưa vào 55 cột."],
            ["2. Áp lực & Lịch học vụ", "9 trường", "available_days, holiday_in_window, expected_duration_days, deadline_pressure, academic_period, semester, academic_week, peak_season, accreditation_flag", "deadline_pressure = min(5.0, expected / max(1, available)); kiểm tra giao cắt calendar_events."],
            ["3. Hồ sơ Giảng viên", "9 trường", "academic_rank, degree, years_experience, tenure_days, management_role, department, teaching_hours_semester, student_count, supervised_student_count", "Tính thâm niên đến mốc t; chuẩn hóa tên bộ môn sang ml_name."],
            ["4. Lịch sử Nhân quả", "6 trường", "hist_count, hist_late_rate, hist_avg_delay, hist_early_rate, hist_late_last5, late_last_30d", "Chỉ tính việc ĐÃ HOÀN THÀNH trước t (completed_at < t). Làm mịn Laplace (prior 0,20; m = 3,0 [8])."],
            ["5. Tải Công việc Đang mở", "6 trường", "active_tasks, active_high_priority_tasks, overdue_open_tasks, deadlines_next_7d, deadlines_next_14d, workload_next_14d", "Đếm các việc chưa hoàn thành tại mốc t; giới hạn đuôi: active_tasks <= 20, workload <= 500h."],
            ["6. Cờ Báo thiếu", "6 trường", "deadline_month_end, converted_workload_missing (*), hist_avg_delay_missing, hist_early_rate_missing, hist_late_last5_missing, is_cold_start (*)", "Bật = 1 khi giảng viên chưa có lịch sử (hist_count == 0). Hai cột (*) bị lọc trùng trong 55 cột mô hình."],
            ["7. Ma trận Tác vụ - Nhân sự", "7 trường", "lecturer_task_count, lecturer_task_late_rate, dept_task_late_rate, task_matrix_source, lecturer_task_late_lift, complexity_num, priority_num", "Ước lượng Bayes 3 tầng (personal -> department -> global [8]); Lift = lecturer_rate - dept_rate."],
        ],
        col_aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT],
        font_size=13
    )

    add_h2(doc, "3.3.2. Kiểu dữ liệu tham số đặc trưng (FEATURE_SCHEMA)")
    add_p(doc, "Mô tả: Danh sách 58 trường chuẩn hóa trong FEATURE_SCHEMA được đóng gói thành từ điển JSON chuẩn để chuyển sang mô hình TabPFN v2 [3] (loại bỏ 3 cột trùng để đưa đúng 55 đặc trưng vào mạng nơ-ron).")

    add_h2(doc, "3.3.3. Thủ tục dự báo rủi ro trễ hạn đơn lẻ (/predict trên TabPFN v2)")
    add_p(doc, "Mô tả: Điểm cuối POST /predict trên ML Service cổng 8001 nhận vector đặc trưng, áp dụng bộ mã hóa, tính xác suất qua 4 túi ngữ cảnh TabPFN v2 [3] và trả về xác suất, mức rủi ro kèm các yếu tố giải thích top_factors.")

    add_h2(doc, "3.3.4. Thủ tục dự báo theo lô và gợi ý phân công AI (/predict-batch)")
    add_p(doc, "Mô tả: Điểm cuối POST /predict-batch tính song song cho toàn bộ giảng viên trong Bộ môn/Khoa, tính Điểm phù hợp S(u) và tự động đề cử Trưởng nhóm AI.")

    add_h2(doc, "3.3.5. Thủ tục nạp nóng và kiểm tra SHA-256 từ kho MLOps (/reload)")
    add_p(doc, "Mô tả: Điểm cuối POST /reload có bảo vệ bằng X-Admin-Token kiểm tra mã băm SHA-256 của tệp model.joblib trong kho phiên bản trước khi nạp nóng vào bộ nhớ [14].")

    add_h2(doc, "3.3.6. Thủ tục học tiếp định kỳ có rào chắn (retrain-auto)")
    add_p(doc, "Mô tả: Lệnh chạy tự động retrain-auto đối soát dữ liệu mới qua 6 rào chắn chất lượng (Paired Bootstrap theo giảng viên [11]) trước khi nâng cấp phiên bản trong kho [14].")

    # 3.4
    add_h1(doc, "3.4. Các loại bảng trong cơ sở dữ liệu")

    add_h2(doc, "3.4.1. Tạo cấu trúc 17 bảng trong cơ sở dữ liệu quan hệ")
    add_p(doc, "Lược đồ cơ sở dữ liệu qlcv.db bao gồm 17 bảng quan hệ được đặc tả chi tiết trong Bảng 3.2:")
    add_styled_table(
        doc,
        caption="Bảng 3.2: Cấu trúc chi tiết 17 bảng dữ liệu trong CSDL quan hệ (qlcv.db)",
        headers=["STT", "Tên bảng", "Khóa chính (PK)", "Khóa ngoại (FK)", "Các trường dữ liệu chính và Ràng buộc toàn vẹn"],
        rows=[
            ["1", "departments", "id", "Không", "code (VARCHAR, UNIQUE), name (VARCHAR), ml_name (VARCHAR)"],
            ["2", "users", "id", "department_id -> departments.id", "username (VARCHAR, UNIQUE), password_hash, full_name, role (CHECK in admin/manager/lecturer), is_active"],
            ["3", "lecturer_profiles", "id", "user_id -> users.id", "academic_rank, degree, management_role, years_experience, tenure_days, teaching_hours_semester, student_count"],
            ["4", "roles", "code", "Không", "code (admin/manager/lecturer), name, default_scope, priority [13]"],
            ["5", "permissions", "code", "Không", "code (15 mã quyền: TASK_VIEW, TASK_CREATE,...), name, module [13]"],
            ["6", "role_permissions", "id", "role_code -> roles.code, permission_code -> permissions.code", "UNIQUE (role_code, permission_code) - Gồm 32 bản ghi ánh xạ [13]"],
            ["7", "user_permission_scopes", "id", "user_id -> users.id, role_code -> roles.code", "scope (CHECK in SYSTEM/FACULTY/DEPARTMENT/SELF), UNIQUE (user_id) [13]"],
            ["8", "task_types", "id", "Không", "code, name, task_group (CHECK in Giảng dạy/Hướng dẫn/NCKH/Kiểm định/Hành chính [1])"],
            ["9", "task_type_scales", "id", "task_type_id -> task_types.id", "scale (CHECK in Nhỏ/Vừa/Lớn), expected_duration_days, conversion_hours [1]"],
            ["10", "calendar_events", "id", "Không", "kind (holiday/accreditation), title, start_date, end_date"],
            ["11", "tasks", "id", "task_type_id -> task_types.id", "code (UNIQUE), title, scale, priority, complexity, assigned_at, original_deadline, current_deadline"],
            ["12", "task_assignments", "id", "task_id -> tasks.id, lecturer_id -> users.id", "is_leader (BOOLEAN, tối đa 1 True/task), progress_pct (CHECK 0..100), status, completed_at, is_late, delay_days"],
            ["13", "task_checklists", "id", "task_id -> tasks.id", "title, is_completed (BOOLEAN), sort_order"],
            ["14", "task_comments", "id", "task_id -> tasks.id, user_id -> users.id", "content, created_at"],
            ["15", "task_history", "id", "task_id -> tasks.id, user_id -> users.id", "action, old_status, new_status, notes, created_at (Audit Log)"],
            ["16", "risk_predictions", "id", "task_id -> tasks.id, assignment_id -> task_assignments.id", "features_json, probability (CHECK 0..1), level (Thấp/Trung bình/Cao), uncertainty, model_version, latency_ms [3]"],
            ["17", "notifications", "id", "user_id -> users.id, task_id -> tasks.id", "kind, title, content, is_read, dedupe_key (UNIQUE)"],
        ],
        col_aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT],
        font_size=13
    )

    add_h2(doc, "3.4.2. Nhập dữ liệu các bảng (Dữ liệu mẫu 4 Bộ môn, 18 Tài khoản và Phân quyền RBAC)")
    add_p(doc, "Hệ thống đã nạp sẵn bộ dữ liệu mẫu chuẩn hóa đồng bộ 100% giữa Database, Backend API và Web UI trong tệp backend/app/seed.py:")
    add_styled_table(
        doc,
        caption="Bảng 3.3: Dữ liệu mẫu các bảng Tổ chức, 18 Tài khoản và Ma trận Phân quyền RBAC (4 phạm vi)",
        headers=["Tài khoản (Username)", "Họ và tên", "Bộ môn phụ trách", "Vai trò (Role)", "Phạm vi RBAC (Scope)", "Số quyền chức năng"],
        rows=[
            ["admin", "Quản trị viên Hệ thống", "Khoa CNTT (Chung)", "admin", "SYSTEM", "15 / 15 quyền hệ thống [13]"],
            ["truongkhoa", "TS. Nguyễn Văn Lễ (Trưởng khoa)", "Khoa CNTT (Chung)", "manager", "FACULTY", "12 / 15 quyền cấp Khoa [13]"],
            ["tbm_k01", "Trưởng Bộ môn CNPM", "Bộ môn Công nghệ phần mềm (K01)", "manager", "DEPARTMENT", "12 / 15 quyền cấp Bộ môn [13]"],
            ["tbm_k02", "Trưởng Bộ môn HTTT", "Bộ môn Hệ thống thông tin (K02)", "manager", "DEPARTMENT", "12 / 15 quyền cấp Bộ môn [13]"],
            ["tbm_k03", "Trưởng Bộ môn KHMT", "Bộ môn Khoa học máy tính (K03)", "manager", "DEPARTMENT", "12 / 15 quyền cấp Bộ môn [13]"],
            ["tbm_k04", "Trưởng Bộ môn MMT & ATTT", "Bộ môn Mạng máy tính & ATTT (K04)", "manager", "DEPARTMENT", "12 / 15 quyền cấp Bộ môn [13]"],
            ["gv_k01_1 .. gv_k01_3", "Giảng viên CNPM 1..3", "Bộ môn Công nghệ phần mềm (K01)", "lecturer", "SELF", "5 / 15 quyền cá nhân/leader [13]"],
            ["gv_k02_1 .. gv_k02_3", "Giảng viên HTTT 1..3", "Bộ môn Hệ thống thông tin (K02)", "lecturer", "SELF", "5 / 15 quyền cá nhân/leader [13]"],
            ["gv_k03_1 .. gv_k03_3", "Giảng viên KHMT 1..3", "Bộ môn Khoa học máy tính (K03)", "lecturer", "SELF", "5 / 15 quyền cá nhân/leader [13]"],
            ["gv_k04_1 .. gv_k04_3", "Giảng viên MMT 1..3", "Bộ môn Mạng máy tính & ATTT (K04)", "lecturer", "SELF", "5 / 15 quyền cá nhân/leader [13]"],
        ],
        col_aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        font_size=13
    )
