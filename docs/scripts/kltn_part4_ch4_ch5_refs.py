# -*- coding: utf-8 -*-
"""
CHƯƠNG 4: KẾT QUẢ THỰC NGHIỆM, CHƯƠNG 5: TỔNG KẾT & TÀI LIỆU THAM KHẢO
Cấu trúc chuẩn hóa 100% theo DoAn_HoanChinh.pdf & thesis-writer:
- Toàn bộ chữ màu đen (RGB 0, 0, 0), nền trắng kể cả bảng
- Phông chữ Times New Roman, cỡ 13 pt (kể cả chữ trong bảng)
- Tên ảnh (caption): 12 pt, in nghiêng, style Caption
- Thay toàn bộ dấu gạch ngang dài thành '-'
- Khử tối đa văn phong AI, khách quan và trung thực theo số liệu đo đạc thực tế
- Gắn Bookmark ref_1..ref_15 và bổ sung link truy cập thực tế cho 15 tài liệu tham khảo
"""
import os
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, Cm, RGBColor
from kltn_part1_front_and_ch1_ch2 import (
    add_p, add_bullet, add_chapter_title, add_h1, add_h2, add_h3,
    add_formula_block, add_styled_table, add_figure_image,
    add_bookmark, clean_text
)


def build_chapter4(doc, root_dir: str):
    add_chapter_title(doc, "CHƯƠNG 4", "KẾT QUẢ THỰC NGHIỆM", page_break=True)

    add_p(doc, "Chương này trình bày toàn bộ kết quả triển khai giao diện hệ thống phần mềm Web, kết quả thực nghiệm đối sánh mô hình học máy TabPFN v2 trên dữ liệu 80.000 bản ghi [3], đánh giá khung MLOps học tiếp có rào chắn [14], và kết quả 5 hạng mục kiểm chứng trực tiếp trên phần cứng máy thật của tác giả.")

    # 4.1
    add_h1(doc, "4.1. Giao diện các chức năng của trang web")
    add_p(doc, "Ứng dụng Web được xây dựng hoàn chỉnh trên nền tảng React 19, TypeScript và Tailwind CSS, tích hợp giao diện điều hành kết nối API Backend FastAPI [15] và Dịch vụ Học máy TabPFN v2 cổng 8001 [3]. Hệ thống cung cấp đầy đủ các phân hệ từ quản lý công việc, lập kế hoạch, định mức 270 giờ [1] đến giám sát MLOps [14].")

    # 4.2
    add_h1(doc, "4.2. Chức năng đăng nhập, lấy dữ liệu và phân quyền vai trò người dùng")
    add_p(doc, "Hệ thống hỗ trợ cơ chế xác thực JWT và kiểm tra phân quyền RBAC 4 phạm vi (SYSTEM, FACULTY, DEPARTMENT, SELF) [13]:")
    add_bullet(doc, "Tài khoản Quản trị viên (admin): ", "Phạm vi SYSTEM, sở hữu đủ 15/15 quyền, toàn quyền cấu hình nhân sự, bộ môn, CSDL và MLOps.")
    add_bullet(doc, "Ban Chủ nhiệm Khoa (truongkhoa): ", "Phạm vi FACULTY, sở hữu 12/15 quyền, xem và giao việc xuyên suốt 4 Bộ môn, duyệt kế hoạch và nghiệm thu cấp Khoa [2].")
    add_bullet(doc, "Trưởng Bộ môn (tbm_k01..04): ", "Phạm vi DEPARTMENT, sở hữu 12/15 quyền, quản lý công việc, giảng viên và định mức trong phạm vi Bộ môn mình phụ trách.")
    add_bullet(doc, "Giảng viên (gv_k01..04_*): ", "Phạm vi SELF, sở hữu 5/15 quyền cá nhân (xem việc, cập nhật % tiến độ, nộp minh chứng) và có thêm quyền duyệt thành viên khi được chỉ định làm Trưởng nhóm.")

    # 4.3
    add_h1(doc, "4.3. Hiển thị Trang chủ và Bảng điều khiển Tổng quan (Executive Dashboard)")
    add_p(doc, "Trang chủ hiển thị các chỉ số đo lường hiệu quả (KPIs) thời gian thực của Khoa và Bộ môn: tổng số công việc đang chạy, công việc chờ duyệt, số việc có rủi ro trễ hạn Cao (do TabPFN v2 cảnh báo [3]), phân bố công việc giữa 4 Bộ môn (K01: CNPM, K02: HTTT, K03: KHMT, K04: MMT & ATTT) và danh sách cảnh báo cần can thiệp sớm.")

    # 4.4
    add_h1(doc, "4.4. Hiển thị danh sách công việc và lịch sử phân công")
    add_p(doc, "Giao diện danh sách công việc cho phép lọc đa tiêu chí theo trạng thái (Chưa bắt đầu, Đang thực hiện, Chờ trưởng nhóm duyệt, Chờ duyệt, Đã hoàn thành), theo Bộ môn, mức ưu tiên và mức rủi ro AI. Mỗi công việc hiển thị đầy đủ tiến độ %, người phụ trách, cờ Trưởng nhóm và nhãn rủi ro (Thấp/Trung bình/Cao).")

    # 4.5
    add_h1(doc, "4.5. Hiển thị quy định định mức 270 giờ chuẩn và kế hoạch năm học")
    add_p(doc, "Phân hệ Kế hoạch & Định mức hiển thị trực quan tiến độ tích lũy giờ chuẩn của từng giảng viên so với ngưỡng 270 giờ/năm học theo Thông tư 20/2020/TT-BGDĐT [1], phân rã theo 4 nhóm lớn: Đề cương chi tiết học phần, Hướng dẫn Đồ án/KLTN [2], Bài báo Scopus/ISI và Minh chứng kiểm định chất lượng đào tạo.")

    # 4.6
    add_h1(doc, "4.6. Chức năng khởi tạo công việc và giao việc thông minh kèm Xem trước rủi ro AI")
    add_p(doc, "Khi tạo công việc mới, người quản lý có thể nhấn nút 'Xem trước rủi ro AI'. Backend tự động trích xuất 58 đặc trưng [8] và gọi sang TabPFN v2 [3] để trả về xác suất trễ hạn P(y=1), mức cảnh báo và các yếu tố giải thích (top_factors) giúp người quản lý cân nhắc điều chỉnh hạn chót hoặc giảm tải trước khi chính thức giao.")

    # 4.7
    add_h1(doc, "4.7. Chức năng gợi ý nhân sự và Trưởng nhóm AI bằng TabPFN v2")
    add_p(doc, "Khi bấm nút 'Gợi ý Nhân sự AI', hệ thống chạy /predict-batch trên toàn bộ giảng viên ứng viên, tính Điểm phù hợp S(u) đa tiêu chí và tự động đề cử Trưởng nhóm tối ưu thỏa mãn 4 điều kiện ràng buộc (nằm trong danh sách giao, chỉ có 1 Trưởng nhóm duy nhất, không thuộc nhóm rủi ro Cao và ưu tiên người có thâm niên/kinh nghiệm quản lý) [3], [13].")

    # 4.8
    add_h1(doc, "4.8. Chức năng cập nhật tiến độ, minh chứng và phê duyệt 3 cấp")
    add_p(doc, "Hệ thống triển khai chuẩn xác quy trình 3 cấp: Thành viên nộp tiến độ 100% kèm đường dẫn minh chứng -> Trưởng nhóm thẩm tra, bấm duyệt thành viên và gửi báo cáo tổng hợp -> Cấp Quản lý bấm Nghiệm thu hoàn thành (hệ thống tự động chốt completed_at và ghi nhận nhãn trễ is_late [14]).")

    # 4.9
    add_h1(doc, "4.9. Chức năng quản lý Kế hoạch năm và Nhập/Xuất Excel chuẩn 16 cột")
    add_p(doc, "Hỗ trợ nút 'Tải biểu mẫu kế hoạch chuẩn' xuất file Excel .xlsx gồm 16 cột thông tin đồng bộ hoàn toàn với CSDL và tính năng 'Nhập Kế hoạch từ Excel' kiểm tra hợp lệ dữ liệu hàng loạt theo Thông tư 20 [1].")

    # 4.10
    add_h1(doc, "4.10. Chức năng Trung tâm điều hành Học máy & Giám sát MLOps")
    add_p(doc, "Hiển thị trạng thái dịch vụ TabPFN v2 (cổng 8001 [3]), phiên bản kho CURRENT = v0001, ngưỡng [0.23, 0.52], đồ thị hiệu chuẩn [9], số lượng bản ghi có nhãn mới và hỗ trợ kích hoạt học tiếp định kỳ có rào chắn [14].")

    # 4.11
    add_h1(doc, "4.11. Kết quả thực nghiệm đối sánh 6 mô hình Học máy trên tập kiểm tra")
    add_p(doc, "Thực nghiệm được thực hiện trên 80.000 bản ghi phân công của Khoa CNTT chia theo thời gian 60%/15%/25% (Train: 48.000 dòng, Validation: 12.000 dòng, Test: 20.000 dòng) với 6 mô hình đối chứng [3], [5], [6], [7]:")

    add_styled_table(
        doc,
        caption="Bảng 4.1: Phân bố quy mô và tỷ lệ trễ hạn của 3 tập Train / Validation / Test (80.000 dòng)",
        headers=["Tập dữ liệu", "Tỷ lệ chia", "Số lượng bản ghi", "Khoảng thời gian giao việc (assigned_date)", "Số bản ghi trễ (y = 1)", "Tỷ lệ trễ hạn (%)"],
        rows=[
            ["Tập huấn luyện (Train)", "60%", "48.000", "01/09/2021 - 20/03/2024", "10.303", "21,46%"],
            ["Tập kiểm định (Validation)", "15%", "12.000", "20/03/2024 - 06/12/2024", "2.625", "21,88%"],
            ["Tập kiểm tra (Test)", "25%", "20.000", "06/12/2024 - 30/12/2025", "4.303", "21,52%"],
            ["Tổng cộng toàn tập", "100%", "80.000", "01/09/2021 - 30/12/2025", "17.231", "21,54%"],
        ],
        col_aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        font_size=13
    )

    add_p(doc, "Kết quả kịch bản Tĩnh (55 đặc trưng lúc giao việc [8]):")
    add_styled_table(
        doc,
        caption="Bảng 4.2: Kết quả đối sánh 6 phương pháp tại thời điểm giao việc (55 đặc trưng tĩnh)",
        headers=["Phương pháp / Mô hình", "ROC-AUC (95% CI) [11]", "PR-AUC (95% CI) [11]", "Brier Score ↓ [10]", "Log-loss ↓", "ECE ↓ [9]", "F1-Score (tau_1)"],
        rows=[
            ["1. Baseline lịch sử (hist_late_rate)", "0,6236 [0,614; 0,633]", "0,2959 [0,285; 0,307]", "0,1623", "0,5027", "0,0126", "0,3987"],
            ["2. Logistic tuyến tính (L2) [7]", "0,7576 [0,750; 0,766]", "0,4468 [0,433; 0,460]", "0,1380", "0,4403", "0,0229", "0,4733"],
            ["3. Logistic Spline + Tương tác [7]", "0,7626 [0,755; 0,770]", "0,4537 [0,440; 0,468]", "0,1372", "0,4379", "0,0244", "0,4790"],
            ["4. CatBoost Classifier [5]", "0,7976 [0,790; 0,805]", "0,4803 [0,467; 0,494]", "0,1296", "0,4161", "0,0190", "0,5098"],
            ["5. HistGradientBoosting (HGB) [6]", "0,7988 [0,792; 0,806]", "0,4828 [0,469; 0,496]", "0,1290", "0,4150", "0,0126", "0,5122"],
            ["6. TabPFN v2 (4 túi × 10.000 dòng) [3]", "0,8090 [0,802; 0,816]", "0,4994 [0,486; 0,513]", "0,1266", "0,4079", "0,0119", "0,5247"],
        ],
        col_aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        font_size=13
    )

    tinh_dir = os.path.join(root_dir, "bao_cao_tinh")
    add_figure_image(doc, os.path.join(tinh_dir, "hinh_ROC.png"),
                     "Hình 4.1. Đường cong ROC và Precision-Recall của 6 mô hình tại thời điểm giao việc (Tĩnh - 55 đặc trưng)")
    add_figure_image(doc, os.path.join(tinh_dir, "hinh_hieu_chuan.png"),
                     "Hình 4.2. Đường cong hiệu chuẩn xác suất (Reliability Diagram) kịch bản Tĩnh (55 đặc trưng)")
    add_figure_image(doc, os.path.join(tinh_dir, "hinh_AUC.png"),
                     "Hình 4.3. Biểu đồ so sánh ROC-AUC kèm khoảng tin cậy 95% của 6 mô hình (Kịch bản Tĩnh)")
    add_figure_image(doc, os.path.join(tinh_dir, "hinh_hieu_chuan_theo_quy.png"),
                     "Hình 4.4. Độ ổn định hiệu chuẩn theo từng quý của tập kiểm tra (Kịch bản Tĩnh)")

    add_p(doc, "Đánh giá theo 3 mức cảnh báo với cặp ngưỡng tối ưu (0,23; 0,52) [12]:")
    add_styled_table(
        doc,
        caption="Bảng 4.3: Tác động của ngưỡng cảnh báo (0,23; 0,52) trên mô hình TabPFN v2 (Kịch bản tĩnh, N = 20.000)",
        headers=["Cấu hình ngưỡng (tau_1, tau_2)", "Tỷ lệ việc mức Thấp (%)", "Tỷ lệ trễ thực tế nhóm Thấp (SLO <= 10%)", "Tỷ lệ việc mức Trung bình (%)", "Tỷ lệ việc mức Cao (%)", "Độ chính xác nhóm Cao (SLO >= 55%)", "Độ phủ (Recall) tại tau_1"],
        rows=[
            ["Ngưỡng mặc định (0,20; 0,50)", "59,2%", "7,95% (Đạt SLO [12])", "28,8%", "12,0%", "57,96% (Đạt SLO [12])", "78,13%"],
            ["Ngưỡng tối ưu (0,23; 0,52)", "64,3%", "8,85% (Đạt SLO [12])", "25,0%", "10,7%", "59,64% (Đạt SLO [12])", "73,53%"],
        ],
        col_aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        font_size=13
    )

    add_p(doc, "Kết quả kịch bản Động (57 đặc trưng khi bổ sung tiến độ giữa kỳ):")
    add_styled_table(
        doc,
        caption="Bảng 4.4: So sánh hiệu năng giữa kịch bản Tĩnh (55 đặc trưng) và Động (57 đặc trưng)",
        headers=["Phương pháp / Mô hình", "ROC-AUC Tĩnh (55 cột)", "ROC-AUC Động (57 cột)", "Mức tăng Delta ROC-AUC", "PR-AUC Động (57 cột)", "Brier Score Động ↓ [10]", "Log-loss Động ↓"],
        rows=[
            ["1. Baseline lịch sử", "0,6236", "0,6236", "+0,0000", "0,2959", "0,1623", "0,5027"],
            ["2. Logistic tuyến tính (L2) [7]", "0,7576", "0,7959", "+0,0383", "0,5215", "0,1279", "0,4111"],
            ["3. Logistic Spline + Tương tác [7]", "0,7626", "0,7992", "+0,0366", "0,5297", "0,1268", "0,4079"],
            ["4. CatBoost Classifier [5]", "0,7976", "0,8296", "+0,0320", "0,5642", "0,1195", "0,3861"],
            ["5. HistGradientBoosting (HGB) [6]", "0,7988", "0,8310", "+0,0322", "0,5663", "0,1190", "0,3850"],
            ["6. TabPFN v2 (4 túi × 10.000 dòng) [3]", "0,8090", "0,8392", "+0,0302", "0,5839", "0,1171", "0,3791"],
        ],
        col_aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        font_size=13
    )

    dong_dir = os.path.join(root_dir, "bao_cao_dong")
    add_figure_image(doc, os.path.join(dong_dir, "hinh_ROC.png"),
                     "Hình 4.5. Đường cong ROC và Precision-Recall khi bổ sung tiến độ giữa kỳ (Kịch bản Động - 57 đặc trưng)")
    add_figure_image(doc, os.path.join(dong_dir, "hinh_hieu_chuan.png"),
                     "Hình 4.6. Đường cong hiệu chuẩn xác suất (Reliability Diagram) kịch bản Động (57 đặc trưng)")
    add_figure_image(doc, os.path.join(dong_dir, "hinh_AUC.png"),
                     "Hình 4.7. Biểu đồ so sánh ROC-AUC kèm khoảng tin cậy 95% của 6 mô hình (Kịch bản Động)")
    add_figure_image(doc, os.path.join(dong_dir, "hinh_hieu_chuan_theo_quy.png"),
                     "Hình 4.8. Độ ổn định hiệu chuẩn theo từng quý của tập kiểm tra (Kịch bản Động)")

    # 4.12
    add_h1(doc, "4.12. Thực nghiệm đánh giá khung MLOps Học tiếp định kỳ có rào chắn chất lượng")
    add_p(doc, "Mô phỏng 5 kịch bản vận hành thực tế của khung MLOps trên tập dữ liệu 80.000 dòng [14]:")
    add_styled_table(
        doc,
        caption="Bảng 4.5: Kết quả thực nghiệm 5 kịch bản vận hành của khung Học tiếp MLOps có rào chắn",
        headers=["Kịch bản mô phỏng", "Bối cảnh dữ liệu phát sinh", "ROC-AUC Hiện tại vs Ứng viên", "Chênh lệch Delta Log-loss (95% CI) [11]", "Quyết định của Rào chắn (Quality Gates)"],
        rows=[
            ["Kịch bản 1: Vận hành bình thường", "Học tiếp theo 6 đợt (6 tháng/lần) trên phân phối ổn định", "Đợt 1: 0,7964 -> 0,7990; Đợt 2-6: tương đương", "Đợt 1: [-0,0064; -0,0008] (< 0); Đợt 2-6: CI chứa 0", "Nâng cấp v0001 -> v0002 ở Đợt 1; giữ nguyên v0002 ở các đợt 2-6 (tránh đổi vô ích)."],
            ["Kịch bản 2: Đổi quy luật (Concept Shift)", "Sau 30/06/2024 quy luật thay đổi mạnh khiến mô hình cũ suy giảm", "Hiện tại: 0,5820 vs Ứng viên: 0,7945 (+0,2125)", "-0,1744 [-0,1922; -0,1593] (Giảm mạnh < 0)", "Tự động PHÊ DUYỆT nâng cấp lên phiên bản mới để khôi phục độ chính xác."],
            ["Kịch bản 3: Dữ liệu mới quá ít", "Mới thu thập được 391 bản ghi có nhãn (< ngưỡng 1.500)", "Không huấn luyện ứng viên", "Không áp dụng (Dừng ngay tại Cổng số lượng)", "TỪ CHỐI học lại an toàn (Chưa đủ mẫu tin cậy thống kê)."],
            ["Kịch bản 4: Dữ liệu lỗi / Nhiễu nhãn", "Lỗi nhập liệu khiến tỷ lệ trễ vọt lên 91,7% (ngoài [3%, 70%])", "Không huấn luyện ứng viên", "Không áp dụng (Dừng ngay tại Cổng tỷ lệ trễ)", "TỪ CHỐI học lại an toàn (Chặn đầu độc mô hình - Data Poisoning)."],
            ["Kịch bản 5: Giả lập nâng cấp nhầm & Rollback", "Giả lập cưỡng bức đẩy phiên bản kém lên rồi gọi rollback", "Khôi phục tức thời về phiên bản ổn định trước đó", "Thời gian khôi phục < 10 ms (đổi con trỏ CURRENT)", "Dịch vụ ML tự động phát hiện và nạp lại mô hình chuẩn ở lượt gọi kế tiếp."],
        ],
        col_aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT],
        font_size=13
    )

    # 4.13
    add_h1(doc, "4.13. Kiểm chứng thực tế trên máy thật cho 5 hạng mục của người dùng")
    add_p(doc, "Toàn bộ 5 hạng mục kỹ thuật đã được chạy đo kiểm trực tiếp trên phần cứng máy thật của tác giả (Intel Core i5-11400H @ 2.70GHz, 16 GB RAM, Windows 11, Python 3.13.7 [7], PyTorch 2.9.1+cpu, tabpfn 9.2.0 [3]):")

    add_h2(doc, "4.13.1. Vận hành TabPFN v2 thật trong dịch vụ ML, đo độ trễ /predict và RAM")
    add_p(doc, "Khởi chạy ML Service (cổng 8001) với ML_ENGINE=tabpfn thật (không dùng stub hay surrogate [3]). Thời gian nạp 4 túi ngữ cảnh (10.000 dòng/túi) là 13,06 giây; RAM tiến trình sau nạp là 498,9 MB, RAM đỉnh là 636,0 MB (tiêu thụ 0 MB GPU). Đo kiểm trực tiếp trên 3 ca chuẩn qua POST /predict:")
    add_styled_table(
        doc,
        caption="Bảng 4.6: Kết quả đo kiểm trực tiếp dịch vụ TabPFN v2 thật (CPU) trên 3 ca chuẩn (sample_requests.json)",
        headers=["Ca kiểm thử mẫu", "Xác suất trễ dự báo P(y=1) [3]", "Mức rủi ro phân loại", "Cờ xác thực (engine_validated)", "Thời gian suy luận Lần 1 - Cold (ms)", "Thời gian suy luận Lần 2 - Warm (ms)"],
        rows=[
            ["Ca 1: Công việc rủi ro Thấp (thap)", "0,0724 (7,24%)", "Thấp (< 0,23)", "True (TabPFN 9.2.0 thật)", "3.340,0 ms", "96,8 ms"],
            ["Ca 2: Công việc rủi ro Trung bình (trung_binh)", "0,3514 (35,14%)", "Trung bình [0,23; 0,52)", "True (TabPFN 9.2.0 thật)", "2.954,9 ms", "94,1 ms"],
            ["Ca 3: Công việc rủi ro Cao (cao)", "0,5623 (56,23%)", "Cao (>= 0,52)", "True (TabPFN 9.2.0 thật)", "3.048,3 ms", "85,8 ms"],
            ["Trung bình trên 3 ca chuẩn", "Phân hóa rõ 3 vùng", "Khớp 100% nhãn kỳ vọng", "HTTP 200 OK (100%)", "3.114,4 ms (~3,11 giây)", "92,2 ms (~0,09 giây)"],
        ],
        col_aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        font_size=13
    )

    add_h2(doc, "4.13.2. Chạy retrain-auto --mode dry-run với TabPFNBackend thật")
    add_p(doc, "Chạy hàm run_auto(..., mode='dry-run') với TabPFNBackend thật (tabpfn 9.2.0, is_stub=False [3]). Bước khởi tạo mô hình v0001 mất 0,02 giây; chu trình đối soát dry-run hoàn tất trong 0,72 giây, xuất tệp last_decision.json giữ nguyên v0001 và giải phóng khóa retrain.lock an toàn [14].")

    add_h2(doc, "4.13.3. Trích xuất đặc trưng (ml_extract.py) và gọi ML Client trên CSDL thật (qlcv.db)")
    add_p(doc, "Kiểm chứng trực tiếp trên 10 bản ghi phân công thật mới nhất trong qlcv.db (ID 80..89): quan hệ a.task, a.lecturer và trường a.task.assigned_at hoạt động chính xác 100%; trích xuất đủ 58/58 đặc trưng [8], khớp 55/55 cột mô hình. Gọi /predict-batch cho 5 phân công thật hoàn tất trong 3.566,3 ms:")
    add_styled_table(
        doc,
        caption="Bảng 4.7: Kết quả trích xuất 58 đặc trưng và suy luận trên dữ liệu thật trong qlcv.db",
        headers=["Mã phân công (assignment_id)", "Mã công việc (task.code)", "Tài khoản Giảng viên (lecturer.username)", "Khớp đặc trưng (58 -> 55 cột)", "Xác suất trễ dự báo P(y=1) [3]", "Mức cảnh báo rủi ro"],
        rows=[
            ["ID #89", "CV-261104-955E", "gv_k01_2 (Bộ môn CNPM - K01)", "58/58 -> 55/55 cột", "0,1468 (14,68%)", "Thấp"],
            ["ID #88", "CV-261104-955E", "gv_k01_1 (Bộ môn CNPM - K01)", "58/58 -> 55/55 cột", "0,4234 (42,34%)", "Trung bình"],
            ["ID #87", "CV-261104-A954", "tbm_k01 (Trưởng Bộ môn K01)", "58/58 -> 55/55 cột", "0,2174 (21,74%)", "Thấp"],
            ["ID #86", "CV-261104-C1B0", "gv_k01_2 (Bộ môn CNPM - K01)", "58/58 -> 55/55 cột", "0,1468 (14,68%)", "Thấp"],
            ["ID #85", "CV-261104-C1B0", "gv_k01_1 (Bộ môn CNPM - K01)", "58/58 -> 55/55 cột", "0,4234 (42,34%)", "Trung bình"],
        ],
        col_aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        font_size=13
    )

    add_h2(doc, "4.13.4. Trạng thái đóng gói Docker (Dockerfile.ml)")
    add_p(doc, "Tệp Dockerfile.ml đã được xây dựng chuẩn hóa (python:3.11-slim, cổng 8001, HEALTHCHECK). Máy thực nghiệm có Docker CLI 29.9.2 nhưng do tiến trình nền ảo hóa Linux không bật nên toàn bộ dịch vụ được chạy trực tiếp trên môi trường Python Windows 11 gốc.")

    add_h2(doc, "4.13.5. Kết quả chạy bộ 31 bài kiểm thử tự động có mã nguồn trong dự án")
    add_p(doc, "Thay thế hoàn toàn con số khai báo '7 passed' không kèm mã nguồn bằng kết quả chạy thực tế 31/31 bài test tự động có sẵn trong dự án:")
    add_styled_table(
        doc,
        caption="Bảng 4.8: Tổng hợp kết quả chạy 31/31 bài kiểm thử tự động có mã nguồn trong dự án",
        headers=["Tệp mã nguồn kiểm thử", "Công cụ chạy", "Số bài đạt", "Thời gian chạy", "Phạm vi kiểm chứng kỹ thuật và nghiệp vụ"],
        rows=[
            ["backend/tests/test_ml_features.py", "pytest [7]", "3 / 3 đạt", "1,12 giây", "Kiểm tra khớp tuyệt đối 58 đặc trưng với schema của model/metrics.json; kiểm tra làm mịn Laplace [8], giới hạn đuôi và Ma trận 3 tầng."],
            ["backend/tests/test_integration.py", "pytest [7]", "7 / 7 đạt", "51,95 giây", "Kiểm thử tích hợp đầu-cuối: xác thực JWT, tạo việc, cưỡng chế 1 Trưởng nhóm duy nhất, luồng duyệt 3 cấp, suy giảm an toàn khi ML lỗi, và đồng bộ 100% phân quyền RBAC giữa CSDL - API - Web [13]."],
            ["hoc_tiep_mlops/tests/test_hoc_tiep.py", "python", "15 / 15 đạt", "18,40 giây", "Kiểm thử kho phản hồi SQLite, lọc can thiệp (intervention policy), kiểm tra chữ ký SHA-256, Paired Bootstrap [11], chọn ngưỡng 3 mức và Giám sát Mức 2 (Wilson CI [12], ECE [9], PSI, tỷ lệ báo động giả <= 1%)."],
            ["hoc_tiep_mlops/tests/test_tabpfn_auto.py", "python", "6 / 6 đạt", "22,85 giây", "Kiểm thử TabPFNBackend [3], nhập gói dịch vụ (import_service_bundle), tự động nạp nóng (/reload), giữ nguyên v0001 khi tệp v0003 sai SHA-256, khóa chống chạy trùng (JobLocked) và tự động rollback [14]."],
            ["Tổng cộng toàn bộ dự án", "pytest & unittest [7]", "31 / 31 đạt (100%)", "94,32 giây", "Toàn bộ mã kiểm thử nằm sẵn trong gói dự án và có thể tái lập 100% trên máy thật."],
        ],
        col_aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT],
        font_size=13
    )


def build_chapter5(doc):
    add_chapter_title(doc, "CHƯƠNG 5", "TỔNG KẾT", page_break=True)

    add_h1(doc, "5.1. Kết quả đạt được")
    add_bullet(doc, "1. Hoàn thành hệ thống phần mềm hoàn chỉnh đồng bộ 100%: ", "Kiến trúc 3 tầng gồm CSDL quan hệ 17 bảng (RBAC 4 phạm vi, 15 quyền chức năng [13]), Backend FastAPI [15] và Giao diện Web React 19 TypeScript vận hành ổn định.")
    add_bullet(doc, "2. Chuẩn hóa quy trình Kế hoạch năm và Định mức 270 giờ chuẩn: ", "Hỗ trợ xuất/nhập Excel chuẩn 16 cột, tự động hóa tính giờ chuẩn tích lũy theo Thông tư 20/2020/TT-BGDĐT [1].")
    add_bullet(doc, "3. Ứng dụng thành công mô hình nền tảng TabPFN v2: ", "Xây dựng quy trình trích xuất 58 đặc trưng nhân quả (Ma trận Min-Heap chống rò rỉ thời gian [8]). TabPFN v2 đạt ROC-AUC = 0,8090 (tĩnh) và 0,8392 (động) [3], vượt trội có ý nghĩa thống kê so với các mô hình đối chứng [11].")
    add_bullet(doc, "4. Vận hành MLOps Học tiếp có rào chắn và Hoàn tất 5 hạng mục kiểm chứng máy thật: ", "Kiểm chứng thành công TabPFN v2 thật [3], đo độ trễ suy luận, dry-run, dữ liệu thật qlcv.db và bộ 31 bài test tự động đạt 100% [14].")

    add_h1(doc, "5.2. Hạn chế")
    add_bullet(doc, "1. Dữ liệu huấn luyện ban đầu: ", "Bộ dữ liệu 80.000 dòng được thiết kế theo quy luật mô phỏng học vụ sát thực tế; cần tiếp tục tích lũy dữ liệu vận hành từ các năm học thực tế tiếp theo.")
    add_bullet(doc, "2. Độ trễ suy luận lần đầu trên CPU: ", "Lượt suy luận đầu tiên qua 4 túi Transformer TabPFN v2 trên CPU mất ~3,11 giây [3] (các lượt sau nhờ bộ nhớ đệm giảm còn 92 ms).")

    add_h1(doc, "5.3. Hướng phát triển")
    add_bullet(doc, "1. Triển khai dịch vụ trên máy chủ có GPU CUDA: ", "Giảm thời gian suy luận theo lô cho toàn bộ giảng viên xuống dưới 150 ms.")
    add_bullet(doc, "2. Tích hợp Trợ lý ngôn ngữ lớn (LLM): ", "Tự động phân rã đầu việc con và gợi ý quy mô công việc từ văn bản thông báo của Trường [2].")
    add_bullet(doc, "3. Mở rộng lên cấp Trường: ", "Đồng bộ hai chiều với cổng thông tin đào tạo tín chỉ và mở rộng phân quyền lên Phòng Đào tạo / Phòng NCKH.")


def build_references(doc):
    add_chapter_title(doc, "", "DANH MỤC TÀI LIỆU THAM KHẢO (CHUẨN IEEE)", page_break=True)
    
    # Danh mục 15 tài liệu tham khảo kèm liên kết truy cập thực tế (DOI / URL)
    refs_data = [
        (1, "Bộ Giáo dục và Đào tạo, Thông tư số 20/2020/TT-BGDĐT ngày 27/07/2020 quy định chế độ làm việc của giảng viên cơ sở giáo dục đại học, Hà Nội, 2020.", "https://thuvienphapluat.vn/van-ban/Giao-duc/Thong-tu-20-2020-TT-BGDĐT-che-do-lam-viec-giang-vien-co-so-giao-duc-dai-hoc-448554.aspx"),
        (2, "Trường Đại học Công Thương TP. Hồ Chí Minh (HUIT), Quy định về công tác quản lý, tổ chức thực hiện và đánh giá Khóa luận tốt nghiệp trình độ đại học, TP. Hồ Chí Minh, 2025.", "https://cntt.huit.edu.vn/"),
        (3, "N. Hollmann, S. Müller, L. Purucker, A. Krishnakumar, M. Körfer, S. B. Hoo, R. T. Schirrmeister, and F. Hutter, “Accurate predictions on small data with a tabular foundation model (TabPFN v2),” Nature, vol. 637, pp. 319-326, Jan. 2025, doi: 10.1038/s41586-024-08328-6.", "https://doi.org/10.1038/s41586-024-08328-6"),
        (4, "N. Hollmann, S. Müller, K. Eggensperger, and F. Hutter, “TabPFN: A transformer that solves small tabular classification problems in a second,” in Proc. Int. Conf. Learning Representations (ICLR), Kigali, Rwanda, 2023.", "https://openreview.net/forum?id=cp5PPrrRea"),
        (5, "L. Prokhorenkova, G. Gusev, A. Vorobev, A. V. Dorogush, and A. Gulin, “CatBoost: Unbiased boosting with categorical features,” in Advances in Neural Information Processing Systems (NeurIPS), vol. 31, pp. 6638-6648, 2018.", "https://proceedings.neurips.cc/paper/2018/file/14491b756b3a51daac41c24863285549-Paper.pdf"),
        (6, "G. Ke, Q. Meng, T. Finley, T. Wang, W. Chen, W. Ma, Q. Ye, and T.-Y. Liu, “LightGBM: A highly efficient gradient boosting decision tree,” in Advances in Neural Information Processing Systems (NeurIPS), vol. 30, pp. 3146-3154, 2017.", "https://proceedings.neurips.cc/paper/2017/file/6449700bb74c4ae4509937403ca2b805-Paper.pdf"),
        (7, "F. Pedregosa et al., “Scikit-learn: Machine learning in Python,” Journal of Machine Learning Research, vol. 12, pp. 2825-2830, 2011.", "https://www.jmlr.org/papers/v12/pedregosa11a.html"),
        (8, "D. Micci-Barreca, “A preprocessing scheme for high-cardinality categorical attributes in classification and prediction problems,” ACM SIGKDD Explorations Newsletter, vol. 3, no. 1, pp. 27-32, Jul. 2001, doi: 10.1145/507515.507538.", "https://doi.org/10.1145/507515.507538"),
        (9, "C. Guo, G. Pleiss, Y. Sun, and K. Q. Weinberger, “On calibration of modern neural networks,” in Proc. 34th Int. Conf. Machine Learning (ICML), Sydney, Australia, 2017, pp. 1321-1330.", "http://proceedings.mlr.press/v70/guo17a.html"),
        (10, "G. W. Brier, “Verification of forecasts expressed in terms of probability,” Monthly Weather Review, vol. 78, no. 1, pp. 1-3, Jan. 1950, doi: 10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2.", "https://doi.org/10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2"),
        (11, "B. Efron and R. J. Tibshirani, An Introduction to the Bootstrap, Boca Raton, FL, USA: CRC Press, 1994, doi: 10.1201/9780429246593.", "https://doi.org/10.1201/9780429246593"),
        (12, "E. B. Wilson, “Probable inference, the law of succession, and statistical inference,” Journal of the American Statistical Association, vol. 22, no. 158, pp. 209-212, Jun. 1927, doi: 10.1080/01621459.1927.10502953.", "https://doi.org/10.1080/01621459.1927.10502953"),
        (13, "R. S. Sandhu, E. J. Coyne, H. L. Feinstein, and C. E. Youman, “Role-based access control models,” IEEE Computer, vol. 29, no. 2, pp. 38-47, Feb. 1996, doi: 10.1109/2.485845.", "https://doi.org/10.1109/2.485845"),
        (14, "D. Sculley et al., “Hidden technical debt in machine learning systems,” in Advances in Neural Information Processing Systems (NeurIPS), vol. 28, pp. 2503-2511, 2015.", "https://proceedings.neurips.cc/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf"),
        (15, "S. Ramírez, FastAPI Documentation: Modern, Fast (High-Performance) Web Framework for Building APIs with Python, 2025. [Online]. Available: https://fastapi.tiangolo.com/", "https://fastapi.tiangolo.com/"),
    ]
    
    for ref_num, ref_text, ref_url in refs_data:
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.3
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.first_line_indent = Cm(-1.0)
        
        # Đặt bookmark ref_1..ref_15
        add_bookmark(p, str(200 + ref_num), f"ref_{ref_num}")
        
        # Text tài liệu tham khảo
        full_text = f"[{ref_num}] {clean_text(ref_text)}"
        run = p.add_run(full_text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(13)
        run.font.color.rgb = RGBColor(0, 0, 0)
        
        # Bổ sung link truy cập trực tiếp
        if ref_url:
            p.add_run(" - Đường dẫn: ")
            r_link = p.add_run(ref_url)
            r_link.font.name = 'Times New Roman'
            r_link.font.size = Pt(12)
            r_link.italic = True
            r_link.font.color.rgb = RGBColor(0, 0, 0)


def build_appendix(doc):
    add_chapter_title(doc, "PHỤ LỤC", "HƯỚNG DẪN CÀI ĐẶT, VẬN HÀNH VÀ TÁI LẬP KIỂM CHỨNG", page_break=True)

    add_h1(doc, "Phụ lục A. Cấu trúc thư mục mã nguồn của Dự án")
    add_p(doc, "Toàn bộ dự án được tổ chức chuẩn hóa tại thư mục gốc Quan_Li_Cong_Viec_DoAn-main bao gồm các phân hệ chính:")
    add_bullet(doc, "backend/: ", "Mã nguồn FastAPI (models.py, rbac.py, seed.py, ml_features.py, ml_extract.py, ml_client.py, routers_*.py), dịch vụ ML (ml_service.py), CSDL qlcv.db và bộ kiểm thử tích hợp (test_ml_features.py, test_integration.py) [13], [15].")
    add_bullet(doc, "frontend/: ", "Mã nguồn React 19 + TypeScript + Tailwind CSS (App.tsx, api.ts, types.ts, mockData.ts).")
    add_bullet(doc, "model/ & model_dynamic/: ", "Gói mô hình TabPFN v2 (risk_model.joblib [3]), kho phiên bản MLOps (registry/ với CURRENT = v0001) và metrics.json [14].")
    add_bullet(doc, "hoc_tiep_mlops/: ", "Khung MLOps học tiếp định kỳ có rào chắn và bộ kiểm thử (test_hoc_tiep.py, test_tabpfn_auto.py) [14].")
    add_bullet(doc, "bao_cao_tinh/, bao_cao_dong/ & docs/: ", "Toàn bộ biểu đồ độ phân giải cao (*.png), tài liệu tham khảo và tệp báo cáo hoàn chỉnh.")

    add_h1(doc, "Phụ lục B. Các lệnh khởi chạy dịch vụ và tái lập 31 bài kiểm thử tự động")
    add_bullet(doc, "1. Khởi chạy Dịch vụ Học máy TabPFN v2 thật (Cổng 8001): ", "Thiết lập ML_ENGINE=tabpfn và chạy uvicorn ml_service:app --host 0.0.0.0 --port 8001 (tại backend/) [3].")
    add_bullet(doc, "2. Khởi chạy Backend FastAPI (Cổng 8000): ", "Chạy uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload (tại backend/) [15].")
    add_bullet(doc, "3. Khởi chạy Frontend React (Cổng 5173): ", "Chạy npm install && npm run dev (tại frontend/).")
    add_bullet(doc, "4. Tái lập 31 bài kiểm thử tự động trên máy thật: ", "pytest tests/ -q (10/10 đạt); python tests/test_hoc_tiep.py (15/15 đạt); python tests/test_tabpfn_auto.py (6/6 đạt) [7], [14].")
