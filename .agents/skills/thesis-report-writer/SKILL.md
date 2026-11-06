---
name: thesis-report-writer
description: Chuyên dụng cho việc soạn thảo, chỉnh sửa, đối soát và hoàn thiện báo cáo Khóa luận tốt nghiệp (KLTN CNTT-KLCN184, HUIT) trên file DOCX. Đảm bảo 100% liêm chính dữ liệu học máy (đối chiếu trực tiếp với metrics.json, so_sanh_cap.json, kiem_tra_so_lieu_chuong4.py), tuân thủ định dạng học thuật HUIT, an toàn khi chỉnh sửa Word với cơ chế sao lưu tự động và kiểm thử sau khi sửa.
---

# Kỹ năng Soạn thảo & Chỉnh sửa Báo cáo Khóa luận Tốt nghiệp (HUIT CNTT)

Kỹ năng này cung cấp quy trình và quy tắc chuẩn mực để soạn thảo, chỉnh lý các chương trong báo cáo Khóa luận tốt nghiệp (file Word `.docx`), đặc biệt là file trung tâm: `docs/BAO_CAO_KLTN_CNTT_KLCN184_UNIFIED_UPDATED.docx`.

---

## 1. Nguyên tắc Liêm chính Dữ liệu & Số liệu Học thuật (BẮT BUỘC)

1. **Tuyệt đối không bịa số liệu (Zero Hallucination):**
   - Mọi chỉ số đánh giá mô hình ($\text{ROC-AUC}$, $\text{PR-AUC}$, $\text{Brier}$, $\text{Log-loss}$, $\text{ECE}$), quy mô mẫu ($N$), số giảng viên, số việc, ngày chia tập, tỷ lệ trễ, khoảng tin cậy 95% Bootstrap **phải trích xuất 100% từ các file nguồn**:
     - `model/metrics.json`: Mô hình Tĩnh ($T_0$)
     - `model_dynamic/metrics.json`: Mô hình Động ($T_t$)
     - `reports_and_docs/bao_cao_tinh/so_sanh_cap.json`: Đối chứng cặp Tĩnh
     - `reports_and_docs/bao_cao_dong/so_sanh_cap.json`: Đối chứng cặp Động
     - `reports_and_docs/SO_SANH_MO_HINH.md`: Tổng hợp phân tích
2. **Khẳng định rõ bản chất dữ liệu mô phỏng:**
   - Luôn nêu rõ `du_lieu_co_dinh_v2` là bộ dữ liệu mô phỏng có kiểm soát (360 giảng viên, 6 Khoa, 5 năm, hạt giống seed 42, 43, 44). Các chỉ số phản ánh khả năng học lại quy luật mô phỏng, không phải lịch sử trễ hạn thật của trường.
3. **Bộ từ khóa cũ bị cấm (Forbid list):**
   - Không được dùng các con số cũ hay từ ngữ phóng đại: `"75.017"`, `"18.755"`, `"24.994"`, `"34.700"`, `"3.13.15"`, `"10.0% (Đạt"`, `"--fast-cpu"`, `"HistGBoost"`, `"Vượt trội"`, `"Tăng vọt"`, `"triệt tiêu hoàn toàn"`, `"p < 0.001"`, `"thấp nhất toàn hệ thống"`.
4. **Kiểm tra tự động sau mỗi lần chỉnh sửa Chương 4:**
   - Bắt buộc chạy:
     ```bash
     .venv\Scripts\python kiem_tra_so_lieu_chuong4.py --docx docs/BAO_CAO_KLTN_CNTT_KLCN184_UNIFIED_UPDATED.docx
     ```
   - Kết quả phải đạt **103 / 103 kiểm tra**.

---

## 2. Quy trình Chỉnh sửa File DOCX An toàn (Safe Editing Workflow)

Khi chỉnh sửa file Word `.docx` của đồ án:

### Bước 1: Luôn tạo bản sao lưu (Backup)
Trước khi thực hiện bất kỳ thao tác ghi đè nào:
```python
import shutil, datetime
now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copyfile("docs/BAO_CAO_KLTN_CNTT_KLCN184_UNIFIED_UPDATED.docx", f"docs/backup_BAO_CAO_{now}.docx")
```

### Bước 2: Giữ nguyên định dạng và kiểu dáng (Styles & Formatting)
- Không dùng các công cụ ghi đè toàn bộ tài liệu làm mất Header, Footer, mục lục tự động, định dạng bảng hay footnote.
- Sử dụng thư viện `python-docx` để tìm chính xác đoạn văn (`paragraph`) hoặc ô trong bảng (`table.cell`), chỉ thay thế chuỗi văn bản (`run.text`) cần cập nhật.
- Bảo toàn cấu trúc XML hoặc sử dụng skill `docx` (merge_runs, unzip/zip XML khi cần can thiệp sâu).

### Bước 3: Định dạng Bảng & Hình ảnh chuẩn học thuật HUIT
- **Bảng:** Tên bảng đặt phía TRÊN bảng (ví dụ: *Bảng 4.3: Đối chứng hiệu năng mô hình Động...*), canh giữa, in đậm tên bảng, in nghiêng nội dung mô tả.
- **Hình ảnh:** Tên hình đặt phía DƯỚI hình (ví dụ: *Hình 4.6: Giao diện Hồ sơ công tác 1 năm...*), canh giữa.
- **Số thập phân:** Làm tròn đồng nhất:
  + ROC-AUC, PR-AUC, Brier, Log-loss, ECE: 4 chữ số thập phân (hoặc 3 chữ số cho khoảng tin cậy KTC 95%).
  + Tỷ lệ phần trăm (%): 1 chữ số thập phân (ví dụ: $68.9\%$, $11.3\%$), riêng nhóm Thấp là $10.04\%$ (2 chữ số thập phân để làm rõ so với mục tiêu $10\%$).

---

## 3. Khung Cấu trúc Báo cáo Khóa luận Chuẩn (5 Chương)

- **Chương 1: Tổng quan & Nghiệp vụ Quản lý Công việc Giảng viên**
  - Bối cảnh Chuyển đổi số giáo dục đại học và định mức Thông tư 20/2020/TT-BGDĐT (270 giờ chuẩn).
  - Phân tích hiện trạng, khảo sát nghiệp vụ tại Khoa CNTT - HUIT.
  - Mục tiêu, phạm vi và phương pháp nghiên cứu của đề tài.
- **Chương 2: Cơ sở Lý thuyết & Công nghệ Áp dụng**
  - Tổng quan Học máy trên dữ liệu bảng (Tabular Learning): Logistic Regression, CatBoost, TabPFN v2 (Prior-data Fitted Networks).
  - Lý thuyết Đánh giá & Hiệu chuẩn Xác suất: ROC-AUC, PR-AUC, Brier Score, ECE, Bootstrap Clustered Confidence Interval.
  - Kiến trúc hệ thống: FastAPI, Microsoft SQL Server LocalDB, React 19 TypeScript.
- **Chương 3: Phân tích & Thiết kế Hệ thống**
  - Sơ đồ ca sử dụng (Use Case), luồng phân quyền RBAC đa cấp độ (Admin, Trưởng Khoa, Trưởng Bộ môn, Giảng viên).
  - Thiết kế Cơ sở dữ liệu quan hệ (18 bảng chuẩn hóa).
  - Thiết kế pipeline trích xuất 55 đặc trưng nhân quả không rò rỉ thời gian (Min-Heap, Bayesian Smoothing).
- **Chương 4: Thực nghiệm & Đánh giá Kết quả**
  - Thiết lập thực nghiệm: Môi trường (Python 3.13, TabPFN 9.2.0, CUDA T4), tập chia theo thời gian (assigned_date).
  - Kết quả mô hình Tĩnh ($T_0$) & phân tích cặp ngưỡng `[0.23, 0.52]`.
  - Kết quả mô hình Động ($T_t$) & nghiên cứu bóc tách Ablation Study (CatBoost bỏ 7 cột tiến độ).
  - Phân tích rủi ro trần xác suất Oracle và mô phỏng học tiếp 11 quý (HistGBoost).
- **Chương 5: Kết luận & Hướng phát triển**
  - Tổng kết các kết quả đạt được về khoa học và phần mềm ứng dụng.
  - Hạn chế của đề tài và lộ trình phát triển (tích hợp học tiếp trực tiếp vào giao diện web, thu thập dữ liệu nhật ký trễ hạn thật).

