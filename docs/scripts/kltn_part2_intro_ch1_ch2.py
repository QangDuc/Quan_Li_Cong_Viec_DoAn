# -*- coding: utf-8 -*-
"""
CHƯƠNG 1 & CHƯƠNG 2 chuẩn hóa 100% theo DoAn_HoanChinh.pdf & thesis-writer:
- Section 3: Bắt đầu từ Chương 1, đánh số trang Ả Rập (1, 2, 3...) bắt đầu lại từ 1
- Toàn bộ chữ màu đen (RGB 0, 0, 0), nền trắng kể cả bảng
- Phông chữ Times New Roman, cỡ 13 pt (kể cả chữ trong bảng)
- Tên ảnh (caption): 12 pt, in nghiêng
- Thay toàn bộ dấu gạch ngang dài thành '-'
- Khử tối đa văn phong AI, sử dụng câu văn kỹ thuật mực thước, chuẩn mực
- Tích hợp liên kết nội bộ cho các trích dẫn tài liệu tham khảo
"""
import os
from docx.enum.text import WD_ALIGN_PARAGRAPH
from kltn_part1_front_and_ch1_ch2 import (
    add_p, add_bullet, add_chapter_title, add_h1, add_h2, add_h3,
    add_formula_block, add_styled_table, add_figure_image,
    add_page_number_to_section, clean_text,
    add_omml_formula,
    FORMULA_2_1_XML, FORMULA_2_2_XML, FORMULA_2_3_XML,
    FORMULA_2_4_XML, FORMULA_2_5_XML, FORMULA_2_6_XML
)


def build_chapter1(doc, diagrams_dir: str):
    # ===== SECTION 2: BẮT ĐẦU NỘI DUNG CHÍNH - ĐÁNH SỐ TRANG Ả RẬP (1, 2, 3, 4, ...) BẮT ĐẦU LẠI TỪ 1 =====
    sec2 = doc.add_section()
    add_page_number_to_section(sec2, fmt="decimal", start_num=1)

    add_chapter_title(doc, "CHƯƠNG 1", "TỔNG QUAN ĐỀ TÀI", page_break=False)

    # 1.1
    add_h1(doc, "1.1. Lý do chọn đề tài")
    add_p(doc, "Trong công tác quản lý đào tạo đại học, việc phân công và theo dõi khối lượng công việc chuyên môn của đội ngũ giảng viên là nhiệm vụ thường trực và quan trọng tại các cơ sở giáo dục. Tại Khoa Công nghệ Thông tin - Trường Đại học Công Thương TP. Hồ Chí Minh (HUIT) [2], gần 60 giảng viên thuộc 4 Bộ môn chuyên môn (Công nghệ phần mềm - K01, Hệ thống thông tin - K02, Khoa học máy tính - K03, Mạng máy tính & An toàn thông tin - K04) hàng năm phải thực hiện khối lượng công việc chuyên môn rất lớn:")
    add_bullet(doc, "Công tác giảng dạy và học phần: ",
               "Biên soạn đề cương chi tiết học phần, ra đề thi, đáp án, chấm thi và xây dựng ngân hàng câu hỏi trắc nghiệm theo quy chế đào tạo hiện hành [1].")
    add_bullet(doc, "Công tác hướng dẫn sinh viên: ",
               "Hướng dẫn đồ án chuyên ngành, khóa luận tốt nghiệp [2], kiến tập nghề nghiệp và thực tập doanh nghiệp.")
    add_bullet(doc, "Nghiên cứu khoa học và bài báo: ",
               "Thực hiện đề tài nghiên cứu khoa học các cấp, công bố bài báo khoa học trên các tạp chí quốc tế Scopus/ISI và tạp chí chuyên ngành trong nước.")
    add_bullet(doc, "Kiểm định chất lượng đào tạo: ",
               "Viết báo cáo tự đánh giá, thu thập và mã hóa minh chứng kiểm định chất lượng theo chuẩn Bộ Giáo dục và Đào tạo (MOET) [1] và chuẩn quốc tế AUN-QA.")
    add_p(doc, "Hiện nay, tại Khoa Công nghệ Thông tin - HUIT, công tác quản lý và phân công các nhiệm vụ nêu trên vẫn chủ yếu dựa trên các bảng tính Excel rời rạc, ghi chép cá nhân hoặc trao đổi qua thư điện tử và tin nhắn. Phương thức quản lý thủ công này bộc lộ ba vấn đề kỹ thuật và vận hành chính:")
    add_bullet(doc, "Thứ nhất - Khó khăn trong việc theo dõi lũy kế định mức 270 giờ chuẩn: ",
               "Theo quy định tại Thông tư 20/2020/TT-BGDĐT [1], mỗi giảng viên phải hoàn thành định mức giờ chuẩn giảng dạy và nghiên cứu khoa học trong năm học. Tuy nhiên, do dữ liệu phân tán trên nhiều tệp bảng tính, Ban Chủ nhiệm Khoa và các Trưởng Bộ môn không có công cụ tự động quy đổi và theo dõi tổng số giờ chuẩn tích lũy theo thời gian thực, dẫn đến tình trạng mất cân đối khối lượng công việc giữa các giảng viên.")
    add_bullet(doc, "Thứ hai - Thiếu công cụ định lượng hỗ trợ phân công và cảnh báo sớm nguy cơ trễ hạn: ",
               "Khi giao việc, cấp quản lý chưa có số liệu thống kê đầy đủ về lịch sử hoàn thành của giảng viên trên đúng loại việc đó, số lượng công việc đang mở đồng thời và khối lượng giờ chuẩn dồn vào các mốc thời gian cao điểm, dẫn đến nguy cơ công việc bị quá hạn ngoài dự kiến.")
    add_bullet(doc, "Thứ ba - Thiếu quy trình phê duyệt công việc nhóm 3 cấp chặt chẽ và phân quyền bảo mật: ",
               "Các công việc nhóm lớn chưa có cơ chế kiểm soát phân quyền dựa trên vai trò (RBAC [13]) để phân định trách nhiệm rõ ràng giữa Thành viên thực hiện, Trưởng nhóm thẩm tra và Quản lý nghiệm thu.")
    add_p(doc, "Để giải quyết các vấn đề thực tiễn nêu trên, đề tài “Xây dựng hệ thống quản lý công việc và tối ưu hóa phân công bằng học máy tại Khoa Công nghệ Thông tin” (Mã đề tài: CNTT-KLCN184) được triển khai nhằm xây dựng một phần mềm quản lý trực tuyến hiện đại, tích hợp mô hình nền tảng dữ liệu bảng TabPFN v2 [3], [4] để dự báo xác suất trễ hạn và hỗ trợ gợi ý phân công nhân sự tối ưu.")

    # 1.2
    add_h1(doc, "1.2. Mục tiêu đề tài")
    add_p(doc, "Đề tài tập trung giải quyết các mục tiêu kỹ thuật cụ thể sau:")
    add_bullet(doc, "Xây dựng hệ thống quản lý công việc trực tuyến: ",
               "Cho phép Ban Chủ nhiệm Khoa và Trưởng Bộ môn khởi tạo công việc, phân công cá nhân hoặc nhóm, theo dõi tiến độ thực hiện và phê duyệt nghiệm thu trên nền tảng Web.")
    add_bullet(doc, "Quản lý định mức 270 giờ chuẩn theo năm học: ",
               "Chuẩn hóa biểu mẫu kế hoạch 16 cột (hỗ trợ nhập và xuất tệp Excel chuẩn), tự động ánh xạ công việc vào bảng quy đổi giờ chuẩn theo Thông tư 20/2020/TT-BGDĐT [1].")
    add_bullet(doc, "Ứng dụng mô hình học máy TabPFN v2 dự báo rủi ro trễ hạn: ",
               "Tích hợp mô hình TabPFN v2 (sử dụng kỹ thuật Context Bagging với 4 túi ngữ cảnh × 10.000 dòng [3]) vào dịch vụ suy luận cổng 8001 để dự báo xác suất trễ hạn, phân loại 3 mức cảnh báo (Thấp / Trung bình / Cao), giải thích nguyên nhân và gợi ý phân công nhân sự tối ưu.")
    add_bullet(doc, "Triển khai mô hình phân quyền RBAC 4 phạm vi: ",
               "Cưỡng chế kiểm soát truy cập theo vai trò và phạm vi dữ liệu (SYSTEM - FACULTY - DEPARTMENT - SELF [13]) gồm 3 vai trò và 15 mã quyền chức năng đồng bộ giữa CSDL, API và Giao diện.")
    add_bullet(doc, "Xây dựng quy trình phê duyệt công việc nhóm 3 cấp: ",
               "Cưỡng chế ràng buộc duy nhất 1 Trưởng nhóm cho công việc nhóm: Thành viên cập nhật tiến độ [0..100%] -> Trưởng nhóm duyệt nội bộ -> Quản lý nghiệm thu hoàn thành.")
    add_bullet(doc, "Thiết lập khung MLOps học tiếp định kỳ có kiểm soát: ",
               "Tự động thu thập phản hồi, giám sát suy giảm hiệu chuẩn Mức 2 (Wilson CI [12], ECE [9], PSI) và huấn luyện lại định kỳ qua 6 rào chắn chất lượng (Paired Bootstrap [11]) kèm cơ chế tự động rollback [14].")

    # 1.3
    add_h1(doc, "1.3. Quy trình mô tả nghiệp vụ")
    add_p(doc, "Hệ thống hỗ trợ quản lý toàn diện quy trình giao việc, theo dõi và nghiệm thu hoạt động chuyên môn của giảng viên thuộc 4 Bộ môn tại Khoa Công nghệ Thông tin:")
    add_p(doc, "1) Các đối tượng sử dụng hệ thống:", bold=True, indent_cm=0.5)
    add_bullet(doc, "Quản trị viên hệ thống (Admin): ", "Thuộc phạm vi SYSTEM [13], nắm giữ 15 quyền chức năng, quản lý tài khoản người dùng, cấu hình tổ chức và giám sát hệ thống.")
    add_bullet(doc, "Ban Chủ nhiệm Khoa (Trưởng khoa, Phó Trưởng khoa): ", "Thuộc vai trò Manager với phạm vi FACULTY, có quyền xem, giao việc, duyệt kế hoạch và nghiệm thu công việc trên toàn bộ 4 Bộ môn.")
    add_bullet(doc, "Trưởng Bộ môn (K01: CNPM, K02: HTTT, K03: KHMT, K04: MMT & ATTT): ", "Thuộc vai trò Manager với phạm vi DEPARTMENT, quản lý kế hoạch, giao việc và duyệt công việc trong phạm vi Bộ môn mình phụ trách.")
    add_bullet(doc, "Giảng viên (Lecturer / Team Leader): ", "Thuộc vai trò Lecturer với phạm vi SELF, nhận việc, cập nhật tiến độ cá nhân, nộp minh chứng; khi được chỉ định làm Trưởng nhóm sẽ có thêm quyền duyệt phần việc thành viên.")

    add_p(doc, "2) Chức năng nghiệp vụ chính:", bold=True, indent_cm=0.5)
    add_bullet(doc, "Quản lý Kế hoạch năm và Định mức 270 giờ: ", "Thiết lập chỉ tiêu kế hoạch năm học, tự động tính giờ chuẩn tích lũy theo Thông tư 20 [1], hỗ trợ nhập và xuất file Excel kế hoạch chuẩn 16 cột.")
    add_bullet(doc, "Giao việc và Dự báo rủi ro AI: ", "Khởi tạo công việc, trích xuất 58 đặc trưng thời gian thực [8], gọi dịch vụ TabPFN v2 [3] để dự báo xác suất trễ hạn, xếp hạng ứng viên và đề cử Trưởng nhóm.")
    add_bullet(doc, "Quy trình thực hiện và Phê duyệt 3 cấp: ", "Thành viên nộp tiến độ và đường dẫn minh chứng -> Trưởng nhóm duyệt nội bộ -> Quản lý nghiệm thu hoàn thành.")
    add_bullet(doc, "Cảnh báo chủ động và Bảng điều khiển (Dashboard): ", "Phát thông báo cho Quản lý khi phát hiện công việc rủi ro Cao; trực quan hóa biểu đồ tiến độ theo Bộ môn.")
    add_bullet(doc, "Giám sát MLOps và Học tiếp định kỳ: ", "Tự động ghi nhận nhãn thực tế khi hoàn thành, giám sát trôi dạt dữ liệu và nâng cấp mô hình định kỳ có rào chắn [14].")

    add_p(doc, "3) Luồng nghiệp vụ cơ bản:", bold=True, indent_cm=0.5)
    add_bullet(doc, "Bước 1: ", "Người dùng đăng nhập bằng tài khoản và mật khẩu, hệ thống xác thực và cấp mã JWT Token chứa thông tin vai trò, phạm vi dữ liệu và 15 quyền chức năng [13].")
    add_bullet(doc, "Bước 2: ", "Người quản lý tra cứu kế hoạch năm học và số giờ chuẩn lũy kế của các giảng viên theo quy định [1].")
    add_bullet(doc, "Bước 3: ", "Khởi tạo công việc mới (tiêu đề, nhóm việc, loại việc, quy mô, độ phức tạp, mức ưu tiên, hạn chót).")
    add_bullet(doc, "Bước 4: ", "Hệ thống trích xuất 58 đặc trưng nhân quả [8], gửi tới dịch vụ TabPFN v2 [3] để tính xác suất trễ P(y=1), điểm phù hợp S(u) và đề cử Trưởng nhóm.")
    add_bullet(doc, "Bước 5: ", "Người quản lý xác nhận phân công, chọn duy nhất 1 Trưởng nhóm (nếu giao việc nhóm) và phát hành công việc.")
    add_bullet(doc, "Bước 6: ", "Giảng viên thực hiện công việc, định kỳ cập nhật tỷ lệ hoàn thành [0..100%] và đính kèm đường dẫn minh chứng.")
    add_bullet(doc, "Bước 7: ", "Trưởng nhóm kiểm tra minh chứng, duyệt các thành viên và gửi báo cáo tổng hợp lên cấp quản lý.")
    add_bullet(doc, "Bước 8: ", "Quản lý nghiệm thu công việc; hệ thống ghi nhận thời điểm hoàn thành, tính toán cờ trễ is_late và lưu vào kho phản hồi MLOps [14].")

    add_p(doc, "4) Lợi ích của hệ thống:", bold=True, indent_cm=0.5)
    add_bullet(doc, "Tiết kiệm thời gian xử lý: ", "Giảm hơn 70% thời gian tổng hợp số liệu và theo dõi tiến độ so với phương pháp thủ công bằng Excel.")
    add_bullet(doc, "Chủ động ngăn ngừa trễ hạn: ", "Nhận diện sớm các công việc có nguy cơ trễ hạn Cao với độ chính xác xấp xỉ 60% để kịp thời điều phối.")
    add_bullet(doc, "Minh bạch định mức giảng viên: ", "Tự động hóa việc cộng dồn giờ chuẩn, giúp giảng viên và người quản lý theo dõi sát sao định mức 270 giờ/năm theo Thông tư 20 [1].")
    add_bullet(doc, "Hỗ trợ công tác kiểm định: ", "Lưu trữ minh chứng tập trung, phục vụ nhanh chóng các đợt kiểm định chương trình đào tạo MOET và AUN-QA [2].")

    # 1.4 -> 1.10: Diagrams
    add_h1(doc, "1.4. UseCase nghiệp vụ")
    add_p(doc, "Sơ đồ UseCase nghiệp vụ mô tả toàn bộ tương tác giữa 4 nhóm tác nhân (Quản trị viên, Ban Chủ nhiệm Khoa, Trưởng Bộ môn, Giảng viên) với các chức năng cốt lõi của hệ thống:")
    add_figure_image(doc, os.path.join(diagrams_dir, "hinh_1_1_usecase_nghiep_vu.png"),
                     "Hình 1.1. Sơ đồ UseCase nghiệp vụ hệ thống", width_cm=14.5)

    add_h1(doc, "1.5. Sơ đồ hoạt động (Activity Diagram)")
    add_p(doc, "Sơ đồ hoạt động thể hiện luồng xử lý nghiệp vụ từ lúc khởi tạo công việc, trích xuất 58 đặc trưng, gọi dịch vụ TabPFN v2 [3], phân công nhân sự đến quy trình phê duyệt 3 cấp và ghi nhận phản hồi MLOps [14]:")
    add_figure_image(doc, os.path.join(diagrams_dir, "hinh_1_2_so_do_hoat_dong.png"),
                     "Hình 1.2. Sơ đồ hoạt động quy trình giao việc và phê duyệt 3 cấp", width_cm=14.5)

    add_h1(doc, "1.6. Sơ đồ tuần tự use-case giao việc và dự báo rủi ro trễ hạn")
    add_p(doc, "Sơ đồ tuần tự mô tả chi tiết các bước giao tiếp giữa Giao diện Web (React 19), Máy chủ Backend (FastAPI [15]), Cơ sở dữ liệu quan hệ (qlcv.db 17 bảng) và Dịch vụ Học máy (TabPFN v2 [3]):")
    add_figure_image(doc, os.path.join(diagrams_dir, "hinh_1_3_so_do_tuan_tu.png"),
                     "Hình 1.3. Sơ đồ tuần tự use-case giao việc và dự báo rủi ro trễ hạn", width_cm=14.5)
    add_p(doc, "Giải thích các bước thực hiện trong Sơ đồ tuần tự:")
    add_bullet(doc, "1. ", "Người quản lý gửi yêu cầu xem gợi ý nhân sự hoặc xem trước rủi ro qua POST /api/tasks/recommend-assignees.")
    add_bullet(doc, "2. ", "Backend FastAPI truy vấn CSDL để lấy lịch sử hoàn thành nhân quả (completed_at < t), tải công việc đang mở và Ma trận Tác vụ - Nhân sự 3 tầng [8].")
    add_bullet(doc, "3. ", "CSDL trả về dữ liệu thô; Backend dựng đủ 58 trường đặc trưng chuẩn hóa (FEATURE_SCHEMA).")
    add_bullet(doc, "4. ", "Backend gọi HTTP POST sang Dịch vụ TabPFN v2 (cổng 8001) với lô 55 đặc trưng đầu vào [3].")
    add_bullet(doc, "5. ", "TabPFN v2 thực hiện suy luận trên 4 túi ngữ cảnh và trả về xác suất trễ hạn P(y=1), mức cảnh báo và độ bất định [3].")
    add_bullet(doc, "6. ", "Backend tính Điểm phù hợp S(u), sắp xếp bảng ứng viên và tự động đề cử Trưởng nhóm hiển thị lên Web.")
    add_bullet(doc, "7. ", "Người quản lý xác nhận giao việc và chỉ định duy nhất 1 Trưởng nhóm qua POST /api/tasks.")
    add_bullet(doc, "8. ", "Backend ghi đồng thời vào bảng tasks, task_assignments, risk_predictions và notifications.")
    add_bullet(doc, "9. ", "Hệ thống trả về thông báo giao việc thành công kèm mã công việc.")

    add_h1(doc, "1.7. Sơ đồ cộng tác của nghiệp vụ giao việc và phê duyệt 3 cấp")
    add_p(doc, "Sơ đồ cộng tác (Collaboration Diagram) thể hiện mối liên kết giữa các đối tượng phần mềm: Quản lý (Reviewer) gửi phân công tới đối tượng Task và TaskAssignment; đối tượng TaskAssignment kích hoạt MLClient để giao tiếp với TabPFN Service [3]; khi Thành viên hoàn tất phần việc, thông điệp cập nhật được gửi tới TeamLeader; Trưởng nhóm thẩm tra và chuyển thông điệp duyệt lên Reviewer; khi Reviewer nghiệm thu, thông điệp phản hồi được chuyển tới FeedbackStore để phục vụ học tiếp MLOps [14].")

    add_h1(doc, "1.8. Use Case hệ thống")
    add_p(doc, "Hệ thống Quản lý công việc và Dự báo rủi ro trễ hạn tích hợp AI được phân rã thành 6 phân hệ Use Case kỹ thuật chuyên biệt. Để thể hiện rõ ràng và trực quan từng phân hệ chức năng, mỗi phân hệ được biểu diễn bằng một sơ đồ Use Case độc lập dưới đây:")

    add_h2(doc, "1.8.1. Phân hệ Quản lý người dùng, Xác thực JWT và Phân quyền RBAC 4 phạm vi")
    add_p(doc, "Phân hệ đảm nhiệm xác thực định danh và kiểm soát quyền truy cập tài nguyên CSDL của 4 nhóm tác nhân (Quản trị viên, Ban Chủ nhiệm Khoa, Trưởng Bộ môn, Giảng viên) theo mô hình RBAC 4 phạm vi dữ liệu (SYSTEM - FACULTY - DEPARTMENT - SELF) [13]:")
    add_figure_image(doc, os.path.join(diagrams_dir, "hinh_1_4_uc_auth_rbac.png"),
                     "Hình 1.4. Sơ đồ Use Case hệ thống: Phân hệ Quản lý người dùng, Xác thực JWT và Phân quyền RBAC 4 phạm vi", width_cm=14.5)
    add_p(doc, "Mô tả chi tiết các Use Case cốt lõi:")
    add_bullet(doc, "UC-01 (Đăng nhập & Cấp phát JWT): ", "Xác thực tên đăng nhập/mật khẩu, sinh JSON Web Token (JWT) có thời hạn 24 giờ chứa thông tin user_id, vai trò và department_id.")
    add_bullet(doc, "UC-02 (Quản lý tài khoản & Hồ sơ giảng viên): ", "Quản trị viên hoặc cá nhân cập nhật thông tin học hàm, học vị, ngạch giảng viên, số điện thoại, email phục vụ định mức và gợi ý AI.")
    add_bullet(doc, "UC-03 (Phân quyền RBAC 4 phạm vi): ", "Cưỡng chế 32 ánh xạ quyền qua rbac.py [13], đảm bảo Trưởng Bộ môn chỉ xem/giao việc trong phạm vi Bộ môn, Giảng viên chỉ xem công việc của chính mình.")
    add_bullet(doc, "UC-04 (Kiểm tra quyền hạn qua Dependency): ", "FastAPI tự động giải mã JWT và kiểm tra quyền hạn trước khi chuyển tiếp yêu cầu đến các hàm xử lý API nghiệp vụ.")

    add_h2(doc, "1.8.2. Phân hệ Kế hoạch năm và Định mức 270 giờ chuẩn Excel")
    add_p(doc, "Phân hệ hỗ trợ nhập liệu kế hoạch công tác hàng loạt từ tệp bảng tính Excel chuẩn 16 cột và tự động quy đổi, theo dõi định mức 270 giờ chuẩn của từng giảng viên [1]:")
    add_figure_image(doc, os.path.join(diagrams_dir, "hinh_1_5_uc_ke_hoach_dinh_muc.png"),
                     "Hình 1.5. Sơ đồ Use Case hệ thống: Phân hệ Kế hoạch năm và Định mức 270 giờ chuẩn Excel", width_cm=14.5)
    add_p(doc, "Mô tả chi tiết các Use Case cốt lõi:")
    add_bullet(doc, "UC-05 (Tải biểu mẫu kế hoạch chuẩn): ", "Cung cấp file mẫu Excel 16 cột có cấu trúc chuẩn hóa cho Ban Chủ nhiệm Khoa và Trưởng Bộ môn.")
    add_bullet(doc, "UC-06 (Nhập kế hoạch hàng loạt): ", "Tải tệp Excel lên hệ thống, tự động kiểm tra định dạng dữ liệu, ràng buộc trùng lặp và lưu đồng thời vào CSDL.")
    add_bullet(doc, "UC-07 (Quy đổi giờ chuẩn chuyên môn): ", "Tự động tra cứu hệ số quy đổi theo 4 bảng định mức của Nhà trường để tính số giờ chuẩn tương ứng cho từng đầu việc.")
    add_bullet(doc, "UC-08 (Theo dõi lũy kế định mức 270 giờ): ", "Tổng hợp và hiển thị tiến độ hoàn thành định mức 270 giờ/năm theo Thông tư 20/2020/TT-BGDĐT [1] cho từng cá nhân và đơn vị.")

    add_h2(doc, "1.8.3. Phân hệ Khởi tạo công việc và Phân công nhóm")
    add_p(doc, "Phân hệ cho phép tạo lập công việc đơn lẻ hoặc phân công theo nhóm giảng viên, đồng thời bắt buộc chỉ định duy nhất một Trưởng nhóm phụ trách [13]:")
    add_figure_image(doc, os.path.join(diagrams_dir, "hinh_1_6_uc_phan_cong_cong_viec.png"),
                     "Hình 1.6. Sơ đồ Use Case hệ thống: Phân hệ Khởi tạo công việc và Phân công nhóm (Cưỡng chế 1 Trưởng nhóm)", width_cm=14.5)
    add_p(doc, "Mô tả chi tiết các Use Case cốt lõi:")
    add_bullet(doc, "UC-09 (Khởi tạo công việc mới): ", "Nhập tiêu đề, phân loại việc, xác định hạn chót, quy mô (Nhỏ/Vừa/Lớn), độ phức tạp và mức độ ưu tiên.")
    add_bullet(doc, "UC-10 (Phân công cá nhân hoặc nhóm): ", "Lựa chọn danh sách giảng viên tham gia thực hiện công việc từ danh mục nhân sự thuộc thẩm quyền quản lý.")
    add_bullet(doc, "UC-11 (Cưỡng chế duy nhất 1 Trưởng nhóm): ", "Khi phân công từ 2 giảng viên trở lên, hệ thống bắt buộc chọn đúng 1 người làm Trưởng nhóm (Leader Constraint) qua Trigger CSDL.")
    add_bullet(doc, "UC-12 (Tạo bản ghi & gửi thông báo): ", "Ghi nhận phân công vào task_assignments và tự động sinh bản ghi thông báo nhắc việc trong bảng notifications.")

    add_h2(doc, "1.8.4. Phân hệ Dự báo rủi ro trễ hạn và Gợi ý nhân sự AI")
    add_p(doc, "Phân hệ trích xuất 58 đặc trưng nhân quả từ CSDL và kết nối dịch vụ TabPFN v2 [3] nhằm dự báo nguy cơ trễ hạn và tự động xếp hạng, gợi ý Trưởng nhóm tối ưu:")
    add_figure_image(doc, os.path.join(diagrams_dir, "hinh_1_7_uc_du_bao_tabpfn.png"),
                     "Hình 1.7. Sơ đồ Use Case hệ thống: Phân hệ Dự báo rủi ro trễ hạn và Gợi ý nhân sự AI (TabPFN v2)", width_cm=14.5)
    add_p(doc, "Mô tả chi tiết các Use Case cốt lõi:")
    add_bullet(doc, "UC-13 (Trích xuất 58 đặc trưng nhân quả): ", "Truy vấn lịch sử quá khứ (completed_at < t), tải ma trận tác vụ - nhân sự 3 tầng và chuẩn hóa 58 trường dữ liệu [8].")
    add_bullet(doc, "UC-14 (Dự báo xác suất trễ qua API TabPFN v2): ", "Gửi gói tin HTTP POST sang cổng 8001 của dịch vụ Học máy, nhận về xác suất P(y=1), mức cảnh báo và độ bất định [3].")
    add_bullet(doc, "UC-15 (Xếp hạng Điểm phù hợp S(u) & Gợi ý Trưởng nhóm): ", "Tổng hợp đa tiêu chí (độ trễ thấp, kinh nghiệm, học hàm/học vị, tải công việc) để đề cử Trưởng nhóm tối ưu.")
    add_bullet(doc, "UC-16 (Phân tích yếu tố rủi ro & Khuyến nghị): ", "Hiển thị trực quan 3 mức rủi ro (Thấp/Trung bình/Cao) kèm các nguyên nhân chính giúp cấp quản lý chủ động điều phối.")

    add_h2(doc, "1.8.5. Phân hệ Cập nhật tiến độ, Nộp minh chứng và Phê duyệt 3 cấp")
    add_p(doc, "Phân hệ quản lý toàn bộ vòng đời thực hiện công việc từ cập nhật tiến độ hàng ngày, nộp hồ sơ minh chứng đến quy trình nghiệm thu qua 3 cấp quản lý:")
    add_figure_image(doc, os.path.join(diagrams_dir, "hinh_1_8_uc_phe_duyet_3_cap.png"),
                     "Hình 1.8. Sơ đồ Use Case hệ thống: Phân hệ Cập nhật tiến độ, Nộp minh chứng và Phê duyệt 3 cấp", width_cm=14.5)
    add_p(doc, "Mô tả chi tiết các Use Case cốt lõi:")
    add_bullet(doc, "UC-17 (Cập nhật tiến độ & nộp minh chứng): ", "Giảng viên cập nhật tỷ lệ hoàn thành (0 - 100%) và dán đường link liên kết hồ sơ sản phẩm (Google Drive, One Drive, Cổng đào tạo).")
    add_bullet(doc, "UC-18 (Phê duyệt nội bộ cấp Trưởng nhóm - Cấp 1): ", "Trưởng nhóm kiểm tra sản phẩm của từng thành viên; khi 100% thành viên đạt yêu cầu thì chuyển trạng thái lên cấp quản lý.")
    add_bullet(doc, "UC-19 (Thẩm định cấp Bộ môn - Cấp 2): ", "Trưởng Bộ môn rà soát chuyên môn và xác nhận chất lượng hồ sơ công việc trước khi trình Ban Chủ nhiệm Khoa.")
    add_bullet(doc, "UC-20 (Nghiệm thu hoàn thành cấp Khoa - Cấp 3): ", "Ban Chủ nhiệm Khoa phê duyệt nghiệm thu cuối cùng, tự động so sánh thời điểm hoàn tất với hạn chót để ghi nhận trễ hạn.")

    add_h2(doc, "1.8.6. Phân hệ Giám sát MLOps Mức 2 và Tái huấn luyện định kỳ")
    add_p(doc, "Phân hệ duy trì độ tin cậy của mô hình AI theo thời gian thông qua việc thu thập nhãn thực tế, giám sát sai số hiệu chuẩn và tái huấn luyện an toàn [14]:")
    add_figure_image(doc, os.path.join(diagrams_dir, "hinh_1_9_uc_mlops_monitoring.png"),
                     "Hình 1.9. Sơ đồ Use Case hệ thống: Phân hệ Giám sát MLOps Mức 2 và Học tiếp định kỳ có rào chắn", width_cm=14.5)
    add_p(doc, "Mô tả chi tiết các Use Case cốt lõi:")
    add_bullet(doc, "UC-21 (Thu thập nhãn nghiệm thu thực tế): ", "Khi công việc được nghiệm thu, hệ thống tự động ghi nhãn kết quả (is_late, delay_days) vào kho phản hồi FeedbackStore.")
    add_bullet(doc, "UC-22 (Giám sát MLOps Mức 2): ", "Đo lường định kỳ các chỉ số độ trôi dạt PSI, sai số hiệu chuẩn ECE [9] và khoảng tin cậy Wilson 95% [12].")
    add_bullet(doc, "UC-23 (Tái huấn luyện định kỳ có rào chắn): ", "Tự động kích hoạt chu trình học tiếp qua 6 rào chắn an toàn (kích thước mẫu, cân bằng nhãn, kiểm định suy giảm AUC) [14].")
    add_bullet(doc, "UC-24 (Nạp lại mô hình nóng - Hot Reload): ", "Cập nhật trọng số mô hình mới vào bộ nhớ tiến trình suy luận mà không cần khởi động lại dịch vụ backend.")

    add_h1(doc, "1.9. Sơ đồ lớp ở mức phân tích")
    add_p(doc, "Ở mức phân tích, hệ thống phân chia các lớp đối tượng theo mẫu kiến trúc phân tích BCE (Boundary - Control - Entity) nhằm phân tách rõ ràng trách nhiệm giữa giao diện, luồng xử lý và dữ liệu lưu trữ:")
    add_figure_image(doc, os.path.join(diagrams_dir, "hinh_1_10_so_do_lop_phan_tich.png"),
                     "Hình 1.10. Sơ đồ lớp ở mức phân tích (Boundary - Control - Entity)", width_cm=14.5)
    add_p(doc, "Các nhóm lớp trong mô hình phân tích:")
    add_bullet(doc, "Lớp Biên (Boundary): ", "Bao gồm LoginPage, TaskManagementUI, PersonnelUI, PlanImportUI và MonitoringDashboardUI đảm nhiệm nhận tương tác và hiển thị phản hồi người dùng.")
    add_bullet(doc, "Lớp Điều khiển (Control): ", "Bao gồm AuthController, TaskController, AllocationAIController, ApprovalController và MLOpsController phụ trách thực thi quy tắc nghiệp vụ và điều phối dữ liệu.")
    add_bullet(doc, "Lớp Thực thể (Entity): ", "Bao gồm User, LecturerProfile, Department, Task, TaskAssignment, RiskPrediction, TaskHistory, Notification biểu diễn các đối tượng dữ liệu cốt lõi.")

    add_h1(doc, "1.10. Sơ đồ lớp ở mức thiết kế")
    add_p(doc, "Sơ đồ lớp ở mức thiết kế đặc tả chi tiết 17 bảng dữ liệu quan hệ được triển khai trong backend/app/models.py và backend/app/rbac.py [13], phân chia thành 4 cụm chuyên biệt kết hợp các quan hệ khóa ngoại (1-1, 1-N, N-N) và ràng buộc toàn vẹn:")
    add_figure_image(doc, os.path.join(diagrams_dir, "hinh_1_11_so_do_lop_csdl.png"),
                     "Hình 1.11. Sơ đồ lớp mức thiết kế - Lược đồ 17 bảng cơ sở dữ liệu quan hệ (qlcv.db)", width_cm=14.5)

    # 1.11 -> 1.15
    add_h1(doc, "1.11. Biểu mẫu Kế hoạch công việc năm và Phiếu giao việc chuẩn")
    add_p(doc, "Để đảm bảo tính đồng bộ tuyệt đối giữa việc nhập liệu hàng loạt từ Excel và giao diện Web, hệ thống chuẩn hóa cấu trúc 16 cột thông tin của Biểu mẫu Kế hoạch công việc năm (tải về qua nút 'Tải biểu mẫu kế hoạch chuẩn' trên giao diện):")
    add_styled_table(
        doc,
        caption="Bảng 1.1: Cấu trúc 16 cột của Biểu mẫu Kế hoạch công việc năm và Phiếu giao việc chuẩn",
        headers=["STT Cột", "Tên cột dữ liệu trong Excel", "Kiểu dữ liệu", "Bắt buộc", "Mô tả nghiệp vụ và quy tắc kiểm tra hợp lệ"],
        rows=[
            ["1", "Mã công việc (Task Code)", "Chuỗi (VARCHAR)", "Tự sinh / Có", "Mã định danh duy nhất của công việc (VD: CV-261104-955E)."],
            ["2", "Tiêu đề công việc", "Chuỗi (VARCHAR)", "Bắt buộc", "Tên mô tả rõ ràng nội dung công việc cần thực hiện."],
            ["3", "Nhóm công việc", "Danh mục chọn", "Bắt buộc", "Giảng dạy / Hướng dẫn SV / NCKH / Kiểm định / Hành chính."],
            ["4", "Loại công việc", "Danh mục chọn", "Bắt buộc", "Khớp chính xác với tên trong bảng task_types (tra cứu từ trang tính Tham chiếu)."],
            ["5", "Quy mô (Scale)", "Danh mục chọn", "Bắt buộc", "Nhỏ / Vừa / Lớn (ảnh hưởng đến giờ quy đổi và thời lượng)."],
            ["6", "Độ phức tạp", "Danh mục chọn", "Bắt buộc", "Thấp / Trung bình / Cao (complexity_num: 0, 1, 2)."],
            ["7", "Mức ưu tiên", "Danh mục chọn", "Bắt buộc", "Thấp / Trung bình / Cao / Khẩn cấp (priority_num: 0, 1, 2, 3)."],
            ["8", "Cấp giao việc", "Danh mục chọn", "Mặc định Khoa", "Khoa / Bộ môn / Trường."],
            ["9", "Hình thức giao", "Danh mục chọn", "Bắt buộc", "Individual (Cá nhân) / Group (Nhóm)."],
            ["10", "Số lượng nhân sự", "Số nguyên (INT)", "Bắt buộc", ">= 1 (nếu >= 2 thì kích hoạt quy trình Trưởng nhóm)."],
            ["11", "Tài khoản Giảng viên phụ trách", "Chuỗi (Username)", "Bắt buộc", "Mã đăng nhập của giảng viên chính (hoặc danh sách phân cách bằng dấu phẩy)."],
            ["12", "Chỉ định Trưởng nhóm (Leader)", "Chuỗi (Username)", "Có điều kiện", "Bắt buộc chọn đúng 1 người trong danh sách nếu giao việc nhóm."],
            ["13", "Hạn chót thực hiện (Deadline)", "Ngày (YYYY-MM-DD)", "Bắt buộc", "Hạn chót hoàn thành; hệ thống kiểm tra số ngày available_days."],
            ["14", "Giờ chuẩn quy đổi kỳ vọng", "Số thực (FLOAT)", "Tự động tra", "Tự động điền theo bảng task_type_scales (Thông tư 20 [1])."],
            ["15", "Học kỳ áp dụng", "Danh mục chọn", "Bắt buộc", "HK1 / HK2 / HK Hè của năm học tương ứng."],
            ["16", "Ghi chú & Yêu cầu minh chứng", "Chuỗi văn bản", "Tùy chọn", "Yêu cầu chi tiết về hồ sơ nghiệm thu cần nộp."],
        ],
        col_aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT],
        font_size=13
    )

    add_h1(doc, "1.12. Mô tả hiện trạng tại Khoa Công nghệ Thông tin - HUIT")
    add_p(doc, "Khoa Công nghệ Thông tin - Trường Đại học Công Thương TP. Hồ Chí Minh hiện quản lý đào tạo hơn 4.000 sinh viên đại học chính quy với đội ngũ gần 60 giảng viên cơ hữu và thỉnh giảng phân bổ đều tại 4 Bộ môn chuyên môn [2]. Mỗi năm học, Khoa thực hiện hàng ngàn lượt phân công công việc chuyên môn:")
    add_styled_table(
        doc,
        caption="Bảng 1.2: Cơ cấu 4 Bộ môn và danh mục quy đổi 270 giờ chuẩn tại Khoa CNTT - HUIT",
        headers=["Bộ môn chuyên môn", "Mã BM", "Mã ML", "Số lượng GV", "Định mức 270 giờ chuẩn theo Thông tư 20/2020/TT-BGDĐT [1]"],
        rows=[
            ["Bộ môn Công nghệ phần mềm (K01)", "K01", "Cong nghe phan mem", "~16 GV", "Đề cương CT: 10-35h; Ra đề thi: 8-25h; Hướng dẫn KLTN: 15-45h; Bài báo Scopus/ISI: 45-150h; Tự đánh giá: 15-50h."],
            ["Bộ môn Hệ thống thông tin (K02)", "K02", "He thong thong tin", "~14 GV", "Đề cương CT: 10-35h; Ra đề thi: 8-25h; Hướng dẫn KLTN: 15-45h; Bài báo Scopus/ISI: 45-150h; Tự đánh giá: 15-50h."],
            ["Bộ môn Khoa học máy tính (K03)", "K03", "Khoa hoc may tinh", "~15 GV", "Đề cương CT: 10-35h; Ra đề thi: 8-25h; Hướng dẫn KLTN: 15-45h; Bài báo Scopus/ISI: 45-150h; Tự đánh giá: 15-50h."],
            ["Bộ môn Mạng máy tính & ATTT (K04)", "K04", "Mang may tinh va ATTT", "~15 GV", "Đề cương CT: 10-35h; Ra đề thi: 8-25h; Hướng dẫn KLTN: 15-45h; Bài báo Scopus/ISI: 45-150h; Tự đánh giá: 15-50h."],
        ],
        col_aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT],
        font_size=13
    )

    add_h1(doc, "1.13. Khai thác cơ sở dữ liệu công việc và kho lịch sử học máy")
    add_p(doc, "Song hành với cơ sở dữ liệu giao dịch chính qlcv.db, hệ thống xây dựng kho lưu trữ phản hồi MLOps (FeedbackStore dựa trên SQLite) [14] để tự động ghi lại toàn bộ lịch sử suy luận AI và nhãn kết quả thực tế:")
    add_bullet(doc, "Ghi nhận dự đoán: ", "Mỗi lượt gọi AI được lưu vết đầy đủ trong bảng risk_predictions gồm: JSON 58 đặc trưng [8], xác suất trễ P(y=1) [3], mức cảnh báo, độ bất định, top_factors và model_version.")
    add_bullet(doc, "Ghi nhận nhãn thực tế: ", "Khi công việc được nghiệm thu, hệ thống tự động ghi nhận completed_at, cờ is_late (True nếu completed_at > deadline) và số ngày trễ delay_days để phục vụ tái huấn luyện định kỳ [14].")

    add_h1(doc, "1.14. Quy trình giao việc, cập nhật tiến độ và nghiệm thu chức năng")
    add_p(doc, "Quy trình phân công và kiểm soát công việc trên phần mềm diễn ra qua 4 bước chuẩn mực:")
    add_bullet(doc, "1. ", "Người quản lý truy cập phân hệ 'Quản lý Công việc' hoặc 'Kế hoạch & Định mức', chọn tạo việc mới hoặc nhập từ Excel.")
    add_bullet(doc, "2. ", "Bấm 'Xem trước rủi ro AI' hoặc 'Gợi ý Nhân sự AI' để tham khảo khuyến nghị từ mô hình TabPFN v2 [3] trước khi quyết định giao.")
    add_bullet(doc, "3. ", "Giảng viên nhận việc, cập nhật % tiến độ định kỳ và đính kèm đường dẫn minh chứng (evidence_url).")
    add_bullet(doc, "4. ", "Trưởng nhóm duyệt nội bộ (đối với việc nhóm) và gửi cấp trên; Ban Chủ nhiệm Khoa hoặc Trưởng Bộ môn bấm 'Nghiệm thu' để hoàn tất.")

    add_h1(doc, "1.15. Dịch vụ hỗ trợ người dùng và Cảnh báo sớm bằng AI")
    add_bullet(doc, "Dịch vụ cảnh báo chủ động (Notification): ", "Tự động gửi thông báo cảnh báo nguy cơ trễ hạn Cao cho Trưởng Bộ môn ngay khi việc được giao có P(y=1) >= 0.52.")
    add_bullet(doc, "Dịch vụ gợi ý nhân sự thông minh: ", "Tự động xếp hạng ứng viên theo Điểm phù hợp S(u) kết hợp năng lực lịch sử, tải công việc và xác suất AI [3].")
    add_bullet(doc, "Dịch vụ hỗ trợ trực tuyến: ", "Tích hợp tài liệu hướng dẫn sử dụng, giải thích nguyên nhân rủi ro và các khuyến nghị can thiệp cụ thể.")


def build_chapter2(doc):
    add_chapter_title(doc, "CHƯƠNG 2", "CƠ SỞ LÝ THUYẾT VÀ NỀN TẢNG NGHIÊN CỨU", page_break=True)

    # 2.1
    add_h1(doc, "2.1. Môi trường phát triển Visual Studio Code và Ngôn ngữ Python / TypeScript")
    add_h2(doc, "2.1.1. Lịch sử và giới thiệu môi trường phát triển")
    add_p(doc, "Visual Studio Code (VS Code) là một môi trường phát triển mã nguồn mở hiện đại do Microsoft phát triển, được giới thiệu lần đầu vào năm 2015. Khác với các IDE cồng kềnh truyền thống, VS Code được xây dựng trên nền tảng Electron và Node.js, mang lại tốc độ khởi động nhanh, hiệu năng cao và khả năng mở rộng không giới hạn thông qua kho phần mở rộng (Extensions Marketplace). Trong dự án này, VS Code đóng vai trò là môi trường lập trình hợp nhất cho cả Backend Python, Dịch vụ Học máy và Frontend TypeScript.")
    add_h2(doc, "2.1.2. Cấu trúc và kiến trúc ngôn ngữ")
    add_p(doc, "Hệ thống sử dụng hai ngôn ngữ chủ lực: (1) Python 3.13 cho tầng xử lý dữ liệu, máy chủ nghiệp vụ và dịch vụ học máy [7]; (2) TypeScript 5.8 cho tầng giao diện người dùng React 19, đảm bảo kiểm tra kiểu tĩnh nghiêm ngặt và giảm thiểu tối đa lỗi lúc chạy (runtime errors).")

    # 2.2
    add_h1(doc, "2.2. Các chức năng hệ thống phát triển, FastAPI và React 19 + Tailwind CSS")
    add_h2(doc, "2.2.1. Backend API: FastAPI, Pydantic v2 và SQLAlchemy ORM")
    add_p(doc, "FastAPI [15] là framework phát triển web API bất đồng bộ (Asynchronous) hiện đại có tốc độ xử lý hàng đầu trong hệ sinh thái Python nhờ thư viện Starlette và Pydantic v2. Kết hợp với SQLAlchemy ORM 2.0, hệ thống ánh xạ 17 bảng cơ sở dữ liệu thành các lớp thực thể trong Python, tự động thực thi các ràng buộc toàn vẹn và tạo tài liệu API tương tác tự động chuẩn OpenAPI / Swagger UI tại đường dẫn /docs.")
    add_h2(doc, "2.2.2. Frontend Web: React 19, TypeScript và Tailwind CSS")
    add_p(doc, "Giao diện người dùng được xây dựng theo kiến trúc Single Page Application (SPA) trên nền tảng React 19 và công cụ đóng gói Vite 6. Toàn bộ thiết kế giao diện tuân theo tiêu chuẩn Enterprise SaaS Dashboard với Tailwind CSS, tối ưu hóa hiển thị trên cả máy tính để bàn lẫn máy tính bảng.")
    add_h2(doc, "2.2.3. Trình gỡ lỗi và bộ kiểm thử tự động")
    add_p(doc, "Hệ thống tích hợp bộ kiểm thử tự động toàn diện sử dụng pytest và unittest [7], bao gồm 4 bộ test độc lập với 31 bài kiểm thử tự động bao phủ trọn vẹn từ trích xuất đặc trưng, phân quyền RBAC [13] đến chu trình học tiếp MLOps [14].")

    # 2.3
    add_h1(doc, "2.3. Hệ quản trị Cơ sở dữ liệu quan hệ (SQLite / SQL Server) và So sánh với Excel")
    add_h2(doc, "2.3.1. Thành phần chính của CSDL quan hệ")
    add_p(doc, "Cơ sở dữ liệu quan hệ (RDBMS) gồm hai thành phần trung tâm: Bộ máy lưu trữ (Storage Engine) quản lý việc lưu trữ tệp, bảng, chỉ mục; và Bộ máy xử lý truy vấn (Relation Engine) phân tích cú pháp SQL, tối ưu hóa kế hoạch thực thi và cưỡng chế tính toàn vẹn (ACID).")
    add_h2(doc, "2.3.2. Sử dụng CSDL quan hệ để làm gì")
    add_p(doc, "Trong đề tài này, CSDL quan hệ (qlcv.db) đảm nhận nhiệm vụ lưu trữ bền vững 17 bảng dữ liệu, quản lý lịch sử công việc, kiểm soát phân quyền RBAC [13] và thực thi các Trigger tự động kiểm tra tính duy nhất của Trưởng nhóm.")
    add_h2(doc, "2.3.3. Các tính năng nổi bật")
    add_p(doc, "Tính năng nổi bật bao gồm: thực thi khóa ngoại nghiêm ngặt (FOREIGN KEY), kiểm tra miền giá trị (CheckConstraint), chỉ mục phân phần (Partial Unique Index) và các thủ tục kích hoạt (Triggers) tự động đồng bộ.")
    add_h2(doc, "2.3.4. Các phiên bản và khả năng mở rộng")
    add_p(doc, "Hệ thống phát triển trên SQLite 3 cho giai đoạn kiểm chứng cục bộ và thiết kế trừu tượng qua SQLAlchemy ORM để dễ dàng chuyển đổi sang Microsoft SQL Server hoặc PostgreSQL khi triển khai thực tế tại Trung tâm dữ liệu của Trường [2].")
    add_h2(doc, "2.3.5. So sánh CSDL quan hệ (SQL) và Excel")
    add_styled_table(
        doc,
        caption="Bảng 2.1: So sánh quản lý dữ liệu công việc trên Hệ QTCSDL quan hệ (SQL) và Excel",
        headers=["Thuộc tính so sánh", "Hệ quản trị CSDL quan hệ (SQL)", "Bảng tính Excel truyền thống"],
        rows=[
            ["Vị trí lưu trữ dữ liệu", "Cơ sở dữ liệu tập trung trên máy chủ, kiểm soát kết nối", "Tệp tin rời rạc (.xlsx) lưu trên máy tính cá nhân"],
            ["Đối tượng phù hợp", "Doanh nghiệp, đơn vị quản lý, hệ thống đa người dùng", "Công việc cá nhân, thống kê số liệu nhỏ"],
            ["Quy mô dữ liệu hỗ trợ", "Lớn, hàng triệu bản ghi, tối ưu hóa bằng chỉ mục Index", "Hạn chế, chậm khi dữ liệu lớn vượt 50.000 dòng"],
            ["Tính tương tác đồng thời", "Hỗ trợ hàng trăm người dùng truy cập và ghi đồng thời", "Dễ xung đột khi nhiều người cùng mở tệp"],
            ["Toàn vẹn và ràng buộc", "Cưỡng chế chặt chẽ qua Foreign Key, Unique, Check, Trigger", "Dễ bị nhập sai định dạng, gõ đè hoặc xóa nhầm công thức"],
            ["Bảo mật và phân quyền", "Phân quyền chi tiết theo vai trò và phạm vi dữ liệu (RBAC [13])", "Khó phân quyền, ai có tệp đều có thể xem toàn bộ"],
            ["Tích hợp Học máy (AI/ML)", "Truy vấn thời gian thực qua API [15], hỗ trợ MLOps tự động [14]", "Phải xuất file thủ công, không hỗ trợ API thời gian thực"],
        ],
        col_aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT],
        font_size=13
    )

    # 2.4
    add_h1(doc, "2.4. Cơ sở lý thuyết Học máy dự báo rủi ro trễ hạn (TabPFN v2) và MLOps Học tiếp")
    add_h2(doc, "2.4.1. Bài toán dự báo rủi ro trễ hạn và Ma trận Tác vụ - Nhân sự nhân quả")
    add_p(doc, "Mục tiêu là học hàm ánh xạ xác suất p_i = f(x_i) dự báo trạng thái trễ hạn y_i thuộc {0, 1} của lượt phân công thứ i phát sinh tại thời điểm giao t_i. Để chống rò rỉ thông tin tương lai, tập lịch sử chỉ được lấy từ các công việc đã hoàn thành trước t_i (T_j < t_i). Đối với Ma trận Tác vụ - Nhân sự, hệ thống áp dụng ước lượng Bayes thực nghiệm làm mịn Laplace phân cấp 3 tầng (Cá nhân -> Bộ môn -> Toàn Khoa) theo nghiên cứu của Micci-Barreca [8]:")
    add_omml_formula(doc, FORMULA_2_1_XML)

    add_h2(doc, "2.4.2. Mô hình nền tảng dữ liệu bảng TabPFN v2 và cơ chế Context Bagging")
    add_p(doc, "TabPFN v2 (Tabular Prior-Data Fitted Network thế hệ thứ 2 [3], [4]) là mạng Transformer hai chiều đã được huấn luyện trước trên hàng triệu tập dữ liệu tổng hợp. Mô hình thực hiện suy luận Bayes trong một lượt truyền xuôi (In-Context Learning). Để khai thác dữ liệu lớn và định lượng độ bất định, khóa luận áp dụng Context Bagging với 4 túi ngữ cảnh độc lập (4 × 10.000 dòng [3]):")
    add_omml_formula(doc, FORMULA_2_2_XML)
    add_p(doc, "Trên cơ sở xác suất trễ hạn dự báo, hệ thống tính toán Điểm phù hợp S(u) theo thang 100 điểm để tự động xếp hạng nhân sự và đề xuất giảng viên Trưởng nhóm tối ưu thỏa mãn 4 điều kiện ràng buộc nghiệp vụ:")
    add_omml_formula(doc, FORMULA_2_3_XML)

    add_h2(doc, "2.4.3. Các mô hình đối chứng (Baseline, Logistic, Spline, CatBoost, HGB)")
    add_styled_table(
        doc,
        caption="Bảng 2.2: So sánh đặc tính kỹ thuật của 6 phương pháp học máy dự báo rủi ro trễ hạn",
        headers=["Phương pháp / Mô hình", "Bản chất toán học", "Xử lý tương tác phi tuyến", "Cơ chế học trên tập dữ liệu", "Định lượng độ bất định"],
        rows=[
            ["1. Baseline lịch sử", "Trung bình Bayes làm mịn 1 biến [8]", "Không", "Công thức đóng (Closed-form)", "Không"],
            ["2. Logistic tuyến tính (L2)", "Tổ hợp tuyến tính + hàm Sigmoid [7]", "Không (chỉ cộng tính)", "Tối ưu lồi L-BFGS (cập nhật trọng số)", "Không"],
            ["3. Logistic Spline + Tương tác", "Đa thức từng khúc B-Spline + tương tác [7]", "Có (cục bộ theo nút đặt trước)", "Tối ưu lồi L-BFGS (cập nhật trọng số)", "Không"],
            ["4. CatBoost Classifier", "Cây quyết định đối xứng tăng cường [5]", "Có (chia nhánh theo độ sâu cây)", "Học tăng cường tuần tự (Boosting)", "Hạn chế"],
            ["5. HistGradientBoosting (HGB)", "Cây tăng cường chia giỏ Histogram [6], [7]", "Có (chia nhánh không đối xứng)", "Học tăng cường + Isotonic Calibration [9]", "Hạn chế"],
            ["6. TabPFN v2 (Đề xuất)", "Mạng Transformer PFN hai chiều [3], [4]", "Rất mạnh (Self-Attention mọi cặp)", "Học trong ngữ cảnh (4 túi × 10.000 dòng)", "Có (Độ lệch chuẩn giữa các túi)"],
        ],
        col_aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER],
        font_size=13
    )

    add_h2(doc, "2.4.4. Lý thuyết MLOps Học tiếp có kiểm soát qua 6 rào chắn và Giám sát Mức 2")
    add_p(doc, "Hệ thống MLOps định kỳ vận hành theo cơ chế Học tiếp có kiểm soát kết hợp Giám sát Mức 2 (Wilson CI [12], ECE [9], PSI) nhằm bảo vệ mô hình khỏi hiện tượng quên thảm khốc và dữ liệu nhiễu [14]. Các chỉ số giám sát cốt lõi được định lượng theo các công thức toán học chuẩn:")
    add_p(doc, "1) Khoảng tin cậy Wilson 95% (Wilson Score Interval) dùng để kiểm soát vi phạm SLO tỷ lệ trễ thực tế của nhóm Thấp và độ chính xác của nhóm Cao [12]:", bold=True)
    add_omml_formula(doc, FORMULA_2_4_XML)
    add_p(doc, "2) Sai số hiệu chuẩn kỳ vọng ECE (Expected Calibration Error) đo lường khoảng cách trung bình có trọng số giữa xác suất dự báo và độ chính xác thực tế qua M giỏ phân vị [9]:", bold=True)
    add_omml_formula(doc, FORMULA_2_5_XML)
    add_p(doc, "3) Chỉ số ổn định quần thể PSI (Population Stability Index) định lượng mức độ trôi dạt phân phối xác suất giữa phân phối gốc P và phân phối thực tế gần nhất Q [14]:", bold=True)
    add_omml_formula(doc, FORMULA_2_6_XML)
    add_p(doc, "Bảng 2.3 tổng hợp các ngưỡng kiểm soát thống kê áp dụng trong khung Giám sát Mức 2:")
    add_styled_table(
        doc,
        caption="Bảng 2.3: Các ngưỡng thống kê của hệ thống Giám sát Mức 2 (Wilson CI, ECE, PSI)",
        headers=["Chỉ số giám sát", "Công thức / Tiêu chí kiểm định", "Ngưỡng HEALTHY (Bình thường)", "Ngưỡng WARNING (Theo dõi)", "Ngưỡng ALERT (Kích hoạt học lại)"],
        rows=[
            ["Độ lệch hiệu chuẩn (Gap & Z)", "|y_bar - p_bar| kết hợp kiểm định Z-score", "|Gap| < 3% hoặc Z <= 2,5", "|Gap| >= 3% và Z > 2,5", "|Gap| >= 5% và Z > 3,0"],
            ["Sai số hiệu chuẩn kỳ vọng (ECE)", "Sai số trung bình có trọng số qua 10 giỏ [9]", "ECE < 0,050", "0,050 <= ECE < 0,080", "ECE >= 0,080"],
            ["Vi phạm SLO nhóm Thấp", "Cận dưới khoảng tin cậy Wilson 95% (low_ci [12])", "low_ci <= 0,10", "0,10 < low_ci <= 0,12", "low_ci > 0,12 (Thực tế trễ > 12%)"],
            ["Vi phạm SLO nhóm Cao", "Cận trên khoảng tin cậy Wilson 95% (high_ci [12])", "high_ci >= 0,55", "0,45 <= high_ci < 0,55", "high_ci < 0,45 (Độ chính xác < 45%)"],
            ["Độ trôi dạt phân phối (PSI)", "PSI = Sum (P_i - Q_i) * ln(P_i / Q_i)", "PSI < 0,10 (STABLE)", "0,10 <= PSI < 0,25 (MODERATE)", "PSI >= 0,25 (SIGNIFICANT_DRIFT)"],
        ],
        col_aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        font_size=13
    )
