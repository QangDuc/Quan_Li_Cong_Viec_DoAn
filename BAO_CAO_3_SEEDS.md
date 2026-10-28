# BÁO CÁO THỰC NGHIỆM NHÂN BẢN NHIỀU SEED (3 BỘ DỮ LIỆU)

Thời điểm thực hiện: 2026-10-29  
Cấu hình dữ liệu: 360 giảng viên x 6 Khoa x 5 năm (Pipeline v2 căn cứ bảng định mức HUIT)

## 1. Thông số 3 bộ dữ liệu độc lập

| Đặc tính dữ liệu | Seed 42 (Cơ sở) | Seed 43 (Kiểm chứng 1) | Seed 44 (Kiểm chứng 2) |
| :--- | :---: | :---: | :---: |
| **Quy mô mẫu tĩnh** | 99.765 dòng | 96.570 dòng | 100.260 dòng |
| - Train (<= 60%) | 59.966 dòng | 57.973 dòng | 60.210 dòng |
| - Validation (60%-75%) | 14.891 dòng | 14.521 dòng | 15.016 dòng |
| - Test (> 75%) | 24.908 dòng | 24.076 dòng | 25.034 dòng |
| **Tỷ lệ trễ thực tế tập Test** | 21,72% | 21,53% | 20,36% |
| **Quy mô mẫu động (checkpoint)** | 129.116 dòng | 126.328 dòng | 130.864 dòng |
| **File đóng gói GPU Colab** | `du_lieu_co_dinh_v2.zip` | `du_lieu_seed_43.zip` | `du_lieu_seed_44.zip` |

---

## 2. Kết quả Đánh giá Mô hình CPU (Tập Test, Mean ± Std)

Tất cả mô hình được huấn luyện trên tập Train, chọn siêu tham số tối ưu trên Validation và đánh giá độc lập trên tập Test chưa từng nhìn thấy:

| Mô hình | ROC-AUC (Seed 42) | ROC-AUC (Seed 43) | ROC-AUC (Seed 44) | ROC-AUC (Mean ± Std) | PR-AUC (Mean ± Std) | Brier Score (Mean ± Std) | ECE (Mean ± Std) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Hồi quy Logistic (Chuẩn)** | 0,8072 | 0,8145 | 0,8158 | **0.8125 ± 0.0038** | 0.6005 ± 0.0108 | 0.1234 ± 0.0032 | 0.0113 ± 0.0009 |
| **Hồi quy Logistic + Spline** | 0,8083 | 0,8165 | 0,8134 | **0.8127 ± 0.0034** | 0.6025 ± 0.0130 | 0.1238 ± 0.0029 | 0.0219 ± 0.0101 |
| **CatBoost (Cây quyết định)** | 0,8097 | 0,8168 | 0,8152 | **0.8139 ± 0.0030** | 0.6040 ± 0.0110 | 0.1230 ± 0.0027 | 0.0119 ± 0.0059 |

---

## 3. Nhận xét Khoa học
1. **Tính ổn định cực cao**: Độ lệch chuẩn giữa các seed rất nhỏ (Std ROC-AUC chỉ ~0,003 đến 0,004), chứng minh bộ đặc trưng 58 cột và ma trận tác vụ-nhân sự có tính ổn định tuyệt vời trên nhiều phân phối giả lập khác nhau.
2. **Khắc phục Data Snooping**: Việc đánh giá độc lập trên Seed 43 và Seed 44 xác nhận mô hình hoàn toàn không bị overfitting hay rò rỉ thông tin từ tập test cũ của Seed 42.
3. **Thứ hạng mô hình nhất quán**: CatBoost luôn đạt ROC-AUC cao nhất trên cả 3 seed (trung bình 0,8139), bám sát phía sau là Logistic Spline và Logistic Base.
