# Nhân bản trên nhiều seed: mô hình đối chứng CPU

Ngày xuất: 2026-10-31. Dữ liệu mô phỏng (cùng bộ sinh `gen_synthetic_data_v5.py`, 360 giảng viên, 6 Khoa, 5 năm; chỉ đổi seed). Mô hình đối chứng huấn luyện trên tập train, chọn siêu tham số trên validation, đo trên test. **TabPFN không nằm trong báo cáo này** (cần GPU; xem notebook theo seed).

## 1. Các bộ dữ liệu

| | Seed 42 | Seed 43 | Seed 44 |
|---|---|---|---|
| Gói dữ liệu | `du_lieu_co_dinh_v2` | `du_lieu_co_dinh_v2_seed43` | `du_lieu_co_dinh_v2_seed44` |
| Số dòng tĩnh | 99.765 | 96.570 | 100.260 |
| Train / Validation / Test | 59.966 / 14.891 / 24.908 | 57.973 / 14.521 / 24.076 | 60.210 / 15.016 / 25.034 |
| Tỉ lệ trễ train / validation / test | 18,86% / 19,17% / 21,72% | 19,49% / 21,83% / 21,53% | 19,15% / 19,55% / 20,36% |
| Số dòng động | 129.116 | 126.328 | 130.864 |

## 2. ROC-AUC trên tập test (tĩnh)

| Mô hình | Seed 42 | Seed 43 | Seed 44 | Trung bình ± độ lệch chuẩn mẫu |
|---|---|---|---|---|
| Hồi quy Logistic | 0,8072 | 0,8145 | 0,8158 | 0,8125 ± 0,0046 |
| Hồi quy Logistic + Spline | 0,8083 | 0,8165 | 0,8134 | 0,8127 ± 0,0041 |
| CatBoost | 0,8095 | 0,8167 | 0,8154 | 0,8139 ± 0,0038 |
| **Trần oracle (biết yếu tố ẩn)** | 0,8261 | 0,8337 | 0,8295 | 0,8298 ± 0,0038 |

## 3. Các chỉ số khác (trung bình ± độ lệch chuẩn mẫu qua các seed)

| Mô hình | PR-AUC | Brier | ECE |
|---|---|---|---|
| Hồi quy Logistic | 0,6005 ± 0,0133 | 0,1234 ± 0,0039 | 0,0113 ± 0,0011 |
| Hồi quy Logistic + Spline | 0,6025 ± 0,0159 | 0,1238 ± 0,0035 | 0,0219 ± 0,0123 |
| CatBoost | 0,6033 ± 0,0130 | 0,1230 ± 0,0035 | 0,0125 ± 0,0067 |

## 4. Nhận xét (tính từ số liệu ở trên)

1. **Thứ hạng không nhất quán:** mô hình có AUC cao nhất là seed 42: CatBoost; seed 43: CatBoost; seed 44: Hồi quy Logistic.
2. **Mức chênh giữa ba mô hình rất nhỏ:** AUC lớn nhất trừ nhỏ nhất trong mỗi seed là seed 42: 0,0023; seed 43: 0,0022; seed 44: 0,0024. CatBoost trừ logistic: seed 42: +0,0023; seed 43: +0,0022; seed 44: -0,0004.
3. **Khoảng cách tới trần oracle:** Hồi quy Logistic 0,0173 ± 0,0031; Hồi quy Logistic + Spline 0,0170 ± 0,0009; CatBoost 0,0159 ± 0,0015. Khoảng cách này gần như bằng nhau giữa các mô hình, nên đổi họ mô hình ít thu hẹp được nó.
4. **Độ biến thiên giữa các seed:** độ lệch chuẩn của AUC khoảng 0,0042. Độ lệch này gồm cả khác biệt giữa các bộ dữ liệu sinh ra (khác tập test, khác tỉ lệ trễ), không chỉ nhiễu của mô hình.

## 5. Hạn chế

- Chỉ 3 seed: ước lượng độ lệch chuẩn từ 3 điểm rất thiếu chính xác; không có kiểm định thống kê giữa các mô hình trong báo cáo này.
- Chỉ có mô hình CPU. Kết luận về TabPFN (so với CatBoost, logistic) cần chạy TabPFN trên từng seed (GPU).
- Cùng một bộ sinh và cùng giả định mô phỏng; nhân bản theo seed chỉ kiểm tra độ nhạy với ngẫu nhiên của bộ sinh, không kiểm tra tính đúng đắn của giả định.
- Việc đạt kết quả tương tự trên các seed không chứng minh mô hình không rò rỉ hay không overfit; rò rỉ (nếu có) do quy trình sinh đặc trưng sẽ lặp lại ở mọi seed.
- Tập test của seed 42 đã được xem nhiều lần trong quá trình phát triển; seed 43 và 44 dùng làm nhân bản.
