# -*- coding: utf-8 -*-
"""
Builder Phần Đầu Báo Cáo bám sát 100% cấu trúc của DoAn_HoanChinh.pdf:
- Section 1: Trang bìa chính và Bìa phụ (không hiện số trang)
- Section 2: Từ Lời mở đầu đến Mục lục (đánh số trang theo ký tự La Mã i, ii, iii, iv, ...)
- Mục lục: Duy nhất 1 mục lục tự động (TOC field) chuẩn Word
- Phông chữ Times New Roman, chữ màu đen 100%, nền bảng trắng
- Toàn bộ dấu gạch ngang dài đổi thành '-'
- Văn phong học thuật chuẩn mực, giảm thiểu tối đa các lối diễn đạt sáo rỗng
"""
from docx.enum.text import WD_ALIGN_PARAGRAPH
from kltn_part1_front_and_ch1_ch2 import (
    add_p, add_bullet, add_chapter_title, add_h1, add_h2, add_styled_table,
    add_toc_field, add_page_number_to_section,
    add_figure_list, add_table_list, set_outline_level
)


def build_front_matter(doc):
    # ===== SECTION 1: TRANG 1 & TRANG 2 - BÌA CHÍNH VÀ BÌA PHỤ (KHÔNG HIỆN SỐ TRANG) =====
    add_p(doc, "BỘ CÔNG THƯƠNG", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_after=2, font_size=14)
    add_p(doc, "TRƯỜNG ĐẠI HỌC CÔNG THƯƠNG TP. HỒ CHÍ MINH", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_after=2, font_size=14)
    add_p(doc, "KHOA CÔNG NGHỆ THÔNG TIN", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_after=6, font_size=14)
    add_p(doc, "", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_after=28, font_size=14)

    add_p(doc, "KHÓA LUẬN TỐT NGHIỆP", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_before=18, space_after=18, font_size=20)

    add_p(doc, "ĐỀ TÀI: XÂY DỰNG HỆ THỐNG QUẢN LÝ CÔNG VIỆC VÀ TỐI ƯU HÓA PHÂN CÔNG BẰNG HỌC MÁY TẠI KHOA CÔNG NGHỆ THÔNG TIN",
          bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_after=10, font_size=16)
    add_p(doc, "(Mã đề tài: CNTT-KLCN184)", bold=True, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_after=28, font_size=13)

    add_p(doc, "Thành viên nhóm :", bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, indent_cm=1.5, space_after=4, font_size=13)
    add_p(doc, "Mã sinh viên và họ tên:", bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, indent_cm=1.5, space_after=4, font_size=13)
    add_p(doc, "Nhóm sinh viên thực hiện Đề tài CNTT-KLCN184 - Khóa 13ĐH", bold=False, align=WD_ALIGN_PARAGRAPH.LEFT, indent_cm=2.0, space_after=18, font_size=13)
    add_p(doc, "Giáo viên hướng dẫn : TS. Nguyễn Văn Lễ", bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, indent_cm=1.5, space_after=48, font_size=13)

    add_p(doc, "TP. Hồ Chí Minh, tháng 5 năm 2026", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_before=36, space_after=6, font_size=13)

    # TRANG 2: BÌA PHỤ
    doc.add_page_break()
    add_p(doc, "BỘ CÔNG THƯƠNG", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_after=2, font_size=14)
    add_p(doc, "TRƯỜNG ĐẠI HỌC CÔNG THƯƠNG TP. HỒ CHÍ MINH", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_after=2, font_size=14)
    add_p(doc, "KHOA CÔNG NGHỆ THÔNG TIN", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_after=6, font_size=14)
    add_p(doc, "", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_after=28, font_size=14)

    add_p(doc, "Khóa luận tốt nghiệp", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_before=18, space_after=18, font_size=18)
    add_p(doc, "Đề tài: Xây dựng hệ thống quản lý công việc và tối ưu hóa phân công bằng học máy tại Khoa Công nghệ Thông tin - Trường Đại học Công Thương TP. Hồ Chí Minh",
          bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_after=28, font_size=15)

    add_p(doc, "Thành viên nhóm :", bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, indent_cm=1.5, space_after=4, font_size=13)
    add_p(doc, "Mã sinh viên và họ tên:", bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, indent_cm=1.5, space_after=4, font_size=13)
    add_p(doc, "1. Thành viên 1 (Nhóm trưởng) - Phụ trách Backend FastAPI, CSDL 17 bảng và Phân quyền RBAC", bold=False, align=WD_ALIGN_PARAGRAPH.LEFT, indent_cm=2.0, space_after=4, font_size=13)
    add_p(doc, "2. Thành viên 2 - Phụ trách Mô hình Học máy TabPFN v2, Trích xuất 58 đặc trưng và MLOps", bold=False, align=WD_ALIGN_PARAGRAPH.LEFT, indent_cm=2.0, space_after=4, font_size=13)
    add_p(doc, "3. Thành viên 3 - Phụ trách Giao diện Web React 19 TypeScript, Kế hoạch Excel và Bộ kiểm thử", bold=False, align=WD_ALIGN_PARAGRAPH.LEFT, indent_cm=2.0, space_after=18, font_size=13)
    add_p(doc, "Giáo viên hướng dẫn : TS. Nguyễn Văn Lễ", bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, indent_cm=1.5, space_after=48, font_size=13)

    add_p(doc, "TP. Hồ Chí Minh, tháng 5 năm 2026", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_before=36, space_after=6, font_size=13)

    # Chuyển sang Trang 3 (Lời mở đầu) - Section 1 tiếp tục đánh số La Mã liên tục từ Trang bìa
    doc.add_page_break()

    # TRANG 3: LỜI MỞ ĐẦU (Trang iii)
    p_modau = add_p(doc, "LỜI MỞ ĐẦU", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_before=6, space_after=14, font_size=15)
    set_outline_level(p_modau, 0)
    add_p(doc, "Trường Đại học Công Thương Thành phố Hồ Chí Minh (HUIT) là cơ sở giáo dục đại học công lập trực thuộc Bộ Công Thương, có bề dày lịch sử hình thành và phát triển hơn 40 năm qua các giai đoạn chuyển mình quan trọng:")
    add_p(doc, "Ngày 09/09/1982, tiền thân của Trường là Trường Cán bộ Kinh tế Kỹ thuật Công nghiệp Thực phẩm Thành phố Hồ Chí Minh được thành lập, sau đó nâng cấp thành Trường Trung học Công nghiệp Thực phẩm TP.HCM (1986) và Trường Cao đẳng Công nghiệp Thực phẩm TP.HCM (2001).")
    add_p(doc, "Ngày 23/02/2010, Thủ tướng Chính phủ ký Quyết định số 284/QĐ-TTg thành lập Trường Đại học Công nghiệp Thực phẩm Thành phố Hồ Chí Minh (HUFI). Đến ngày 01/07/2023, Thủ tướng Chính phủ ban hành Quyết định số 549/QĐ-TTg chính thức đổi tên Trường thành Trường Đại học Công Thương Thành phố Hồ Chí Minh (Ho Chi Minh City University of Industry and Trade - HUIT), đánh dấu bước phát triển mới trở thành trường đại học đa ngành, đa lĩnh vực theo định hướng ứng dụng và đổi mới sáng tạo.")
    add_p(doc, "Trong cơ cấu các khoa đào tạo chủ lực của Nhà trường, Khoa Công nghệ Thông tin được thành lập từ năm 2004 và không ngừng lớn mạnh với 4 Bộ môn chuyên môn sâu gồm: Bộ môn Công nghệ phần mềm (K01), Bộ môn Hệ thống thông tin (K02), Bộ môn Khoa học máy tính (K03) và Bộ môn Mạng máy tính & An toàn thông tin (K04). Khoa có nhiệm vụ tổ chức đào tạo trình độ đại học và sau đại học các ngành Công nghệ thông tin, An toàn thông tin, Khoa học dữ liệu; triển khai nghiên cứu khoa học, chuyển giao công nghệ và thực hiện kiểm định chất lượng chương trình đào tạo theo chuẩn của Bộ Giáo dục và Đào tạo [1] cũng như quy định của Nhà trường [2]. Trước quy mô công việc ngày càng lớn và đa dạng tại Khoa, việc xây dựng một hệ thống quản lý công việc trực tuyến kết hợp trí tuệ nhân tạo để tối ưu hóa phân công nhân sự và cảnh báo sớm nguy cơ trễ hạn là nhiệm vụ có ý nghĩa thiết thực.")

    # TRANG 4: LỜI CAM ĐOAN (Trang ii)
    doc.add_page_break()
    p_camdoan = add_p(doc, "LỜI CAM ĐOAN", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_before=6, space_after=14, font_size=15)
    set_outline_level(p_camdoan, 0)
    add_p(doc, "Chúng em xin cam đoan đây là công trình nghiên cứu của riêng nhóm em dưới sự hướng dẫn khoa học của thầy TS. Nguyễn Văn Lễ. Các số liệu thực nghiệm, kết quả đo kiểm trên máy thật và toàn bộ mã nguồn hệ thống nêu trong bài báo cáo là trung thực và được thực hiện nghiêm túc.")
    add_p(doc, "Chúng em xin cam đoan rằng mọi sự giúp đỡ cho việc thực hiện bài báo cáo này đã được cảm ơn và các thông tin trích dẫn, tài liệu tham khảo trong báo cáo đều đã được chỉ rõ nguồn gốc theo đúng quy định của Trường Đại học Công Thương TP. Hồ Chí Minh [2].")

    # TRANG 5: LỜI CẢM ƠN (Trang iii)
    doc.add_page_break()
    p_camon = add_p(doc, "LỜI CẢM ƠN", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_before=6, space_after=14, font_size=15)
    set_outline_level(p_camon, 0)
    add_p(doc, "Lời đầu tiên, chúng em xin gửi lời cảm ơn chân thành và sâu sắc nhất đến thầy TS. Nguyễn Văn Lễ. Trong suốt quá trình tìm hiểu, phân tích thiết kế và thực hiện đề tài “Xây dựng hệ thống quản lý công việc và tối ưu hóa phân công bằng học máy tại Khoa Công nghệ Thông tin”, chúng em đã nhận được sự quan tâm giúp đỡ, định hướng phương pháp nghiên cứu rất tận tình và tâm huyết của thầy. Thầy đã giúp chúng em tích lũy thêm nhiều kiến thức chuyên sâu về cả kỹ thuật phần mềm, thiết kế cơ sở dữ liệu phân quyền [13] lẫn phương pháp đánh giá thực nghiệm học máy nghiêm ngặt chống rò rỉ thời gian [3], [11].")
    add_p(doc, "Có lẽ kiến thức là vô hạn mà sự tiếp nhận kiến thức của bản thân mỗi người luôn tồn tại những hạn chế nhất định. Do đó, trong quá trình hoàn thành bài báo cáo Khóa luận tốt nghiệp, chắc chắn không tránh khỏi những thiếu sót. Nhóm chúng em rất mong nhận được những ý kiến đóng góp quý báu từ Quý Thầy Cô trong Hội đồng để đề tài và bài báo cáo của nhóm được hoàn thiện hơn.")
    add_p(doc, "Chúng em kính chúc thầy TS. Nguyễn Văn Lễ và Quý Thầy Cô Khoa Công nghệ Thông tin - Trường Đại học Công Thương TP. Hồ Chí Minh nhiều sức khỏe, hạnh phúc và thành công trên con đường sự nghiệp giảng dạy.")

    # TRANG 6: BẢNG ĐÁNH GIÁ NHÓM & TÓM TẮT (Trang iv)
    doc.add_page_break()
    p_danhgia = add_p(doc, "BẢNG ĐÁNH GIÁ KẾT QUẢ THỰC HIỆN CÔNG VIỆC NHÓM", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_before=6, space_after=12, font_size=15)
    set_outline_level(p_danhgia, 0)
    add_styled_table(
        doc,
        caption="",
        headers=["STT", "Họ và tên / Vai trò", "Công việc đảm nhận", "Cá nhân tự đánh giá mức hoàn thành (%)", "Nhóm đánh giá mức hoàn thành (%)", "GV đánh giá"],
        rows=[
            ["1", "Thành viên 1 (Nhóm trưởng)", "Phân tích nghiệp vụ, thiết kế CSDL 17 bảng, RBAC 4 phạm vi, Backend API FastAPI", "100%", "100%", ""],
            ["2", "Thành viên 2", "Trích xuất 58 đặc trưng nhân quả, huấn luyện TabPFN v2, dịch vụ ML 8001 và MLOps học tiếp", "100%", "100%", ""],
            ["3", "Thành viên 3", "Xây dựng giao diện Web React 19 TypeScript, Kế hoạch năm Excel 16 cột, bộ 31 bài kiểm thử", "100%", "100%", ""],
        ],
        col_aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        font_size=13
    )

    p_tomtat = add_p(doc, "TÓM TẮT", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_before=14, space_after=8, font_size=15)
    set_outline_level(p_tomtat, 0)
    add_p(doc, "Đề tài “Xây dựng hệ thống quản lý công việc và tối ưu hóa phân công bằng học máy tại Khoa Công nghệ Thông tin” (Mã đề tài: CNTT-KLCN184) giải quyết bài toán số hóa toàn diện quy trình lập kế hoạch năm học, theo dõi định mức 270 giờ chuẩn (Thông tư 20/2020/TT-BGDĐT [1]), điều phối công việc nhóm 3 cấp (Thành viên - Trưởng nhóm - Quản lý) và ứng dụng mô hình nền tảng dữ liệu bảng TabPFN v2 [3] để dự báo xác suất trễ hạn cũng như gợi ý nhân sự tối ưu tại Khoa CNTT - Trường Đại học Công Thương TP.HCM (HUIT).")
    add_p(doc, "Hệ thống gồm 3 phân hệ đồng bộ 100%: (1) Cơ sở dữ liệu quan hệ 17 bảng tích hợp phân quyền RBAC 4 phạm vi (SYSTEM - FACULTY - DEPARTMENT - SELF với 3 vai trò, 15 mã quyền và 32 ánh xạ quyền [13]) cùng các Trigger bảo vệ toàn vẹn; (2) Máy chủ Backend FastAPI [15] và Giao diện Web React 19 TypeScript; (3) Dịch vụ suy luận Học máy độc lập (cổng 8001) trích xuất 58 đặc trưng nhân quả (55 đặc trưng đưa vào mô hình [8]) sử dụng Ma trận Tác vụ - Nhân sự cập nhật theo hàng đợi ưu tiên Min-Heap chống rò rỉ thời gian. Trên 80.000 bản ghi phân công chia theo thời gian 60%/15%/25%, TabPFN v2 (4 túi × 10.000 dòng [3]) đạt ROC-AUC = 0,8090, PR-AUC = 0,4994 ở kịch bản tĩnh (lúc giao việc) và ROC-AUC = 0,8392, PR-AUC = 0,5839 ở kịch bản động (giữa kỳ). Toàn bộ dịch vụ TabPFN v2 thật trên CPU, chu trình học tiếp retrain-auto --mode dry-run [14], mô-đun trích xuất đặc trưng trên dữ liệu thật (qlcv.db) và 31/31 bài kiểm thử tự động đã được kiểm chứng thành công trên máy thật.")

    # TRANG 7: DANH MỤC HÌNH ẢNH TỰ ĐỘNG (KHÔNG DÙNG BẢNG - CHUẨN WORD TOC \c "Hình")
    doc.add_page_break()
    add_figure_list(doc)

    # TRANG 8: DANH MỤC BẢNG BIỂU TỰ ĐỘNG (KHÔNG DÙNG BẢNG - CHUẨN WORD TOC \c "Bảng")
    doc.add_page_break()
    add_table_list(doc)

    # TRANG 9: MỤC LỤC TỰ ĐỘNG (CHỈ DUY NHẤT 1 MỤC LỤC TỰ ĐỘNG)
    doc.add_page_break()
    add_p(doc, "MỤC LỤC", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent_cm=0, space_before=6, space_after=12, font_size=15)
    
    # Chỉ chèn 1 trường Mục lục tự động Word TOC duy nhất, KHÔNG lặp lại danh sách đoạn văn tĩnh bên dưới
    add_toc_field(doc)
