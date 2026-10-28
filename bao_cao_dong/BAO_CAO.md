# Báo cáo cuối: Mô hình động

Tập test: **32,228** dòng, tỉ lệ trễ **24.26%**. Khoảng tin cậy 95% bootstrap theo cụm giảng viên (400 lần).

## 1. Chỉ số trên tập test

| Mô hình | AUC [KTC 95%] | PR-AUC | Brier | Log-loss | ECE |
|---|---|---|---|---|---|
| TabPFN v2 | 0.8356 [0.825; 0.846] | 0.6754 | 0.1249 | 0.4005 | 0.0051 |
| Baseline lịch sử | 0.6912 [0.668; 0.713] | 0.4055 | 0.1735 | 0.5291 | 0.0694 |
| Logistic (tuyến tính) | 0.8331 [0.822; 0.844] | 0.6700 | 0.1264 | 0.4053 | 0.0158 |
| Logistic (spline) | 0.8344 [0.824; 0.844] | 0.6735 | 0.1268 | 0.4065 | 0.0318 |
| CatBoost | 0.8318 [0.821; 0.843] | 0.6682 | 0.1268 | 0.4058 | 0.0154 |
| CatBoost (bỏ đặc trưng tiến độ) | 0.8064 [0.794; 0.818] | 0.6184 | 0.1368 | 0.4313 | 0.0139 |

## 2. So sánh cặp: TabPFN trừ mô hình khác

| So với | ΔAUC [KTC 95%] | ΔBrier | Δlog-loss |
|---|---|---|---|
| Baseline lịch sử | +0.1441 [+0.1273; +0.1612] | -0.04837 | -0.12790 |
| Logistic (tuyến tính) | +0.0025 [+0.0006; +0.0044] | -0.00143 | -0.00472 |
| Logistic (spline) | +0.0013 [-0.0006; +0.0032] | -0.00184 | -0.00595 |
| CatBoost | +0.0038 [+0.0018; +0.0056] | -0.00190 | -0.00524 |
| CatBoost (bỏ đặc trưng tiến độ) | +0.0292 [+0.0252; +0.0335] | -0.01186 | -0.03058 |

(ΔAUC > 0: TabPFN tốt hơn; ΔBrier, Δlog-loss < 0: TabPFN tốt hơn. Khoảng tin cậy chứa 0: chưa đủ bằng chứng về khác biệt.)

## 3. Mức cảnh báo của TabPFN (ngưỡng chọn trên validation)

Ngưỡng: [0.26, 0.42] | mục tiêu: {'max_late_low': 0.1, 'actual_low': 0.1026, 'ok_low': False, 'min_prec_high': 0.6, 'actual_high': 0.6749, 'ok_high': True}

| Mức | Số việc | % số việc | Tỉ lệ trễ thực tế |
|---|---|---|---|
| Thấp | 22,161 | 68.8% | 10.3% |
| Trung bình | 3,672 | 11.4% | 33.5% |
| Cao | 6,395 | 19.8% | 67.5% |

## 4. Mô hình nhẹ `--fast-cpu` (HistGradientBoosting, KHÔNG phải TabPFN)

AUC 0.8297 | PR-AUC 0.6673 | Brier 0.1276 | ECE 0.0251 | Spearman với TabPFN 0.944

Với ngưỡng của TabPFN: Thấp: 23,203 việc, trễ 11.2%; Trung bình: 3,503 việc, trễ 38.2%; Cao: 5,522 việc, trễ 70.2%

## 5. Hiệu chuẩn theo quý (tỉ lệ trễ thực tế và dự đoán trung bình)

| quy    |    n |   ti_le_tre_that |   tabpfn_dd_TB |   hist_baseline_dd_TB |   logistic_base_dd_TB |   logistic_spline_dd_TB |   catboost_dd_TB |   catboost_khong_tien_do_dd_TB |
|:-------|-----:|-----------------:|---------------:|----------------------:|----------------------:|------------------------:|-----------------:|-------------------------------:|
| 2027Q3 | 3942 |           0.2126 |         0.1982 |                0.1722 |                0.1899 |                  0.1749 |           0.1905 |                         0.1909 |
| 2027Q4 | 8288 |           0.2399 |         0.2339 |                0.1713 |                0.2279 |                  0.2057 |           0.2204 |                         0.2222 |
| 2028Q1 | 7827 |           0.2486 |         0.247  |                0.1749 |                0.2344 |                  0.2188 |           0.2365 |                         0.2386 |
| 2028Q2 | 9413 |           0.2594 |         0.2538 |                0.1725 |                0.2444 |                  0.2275 |           0.2432 |                         0.2444 |
| 2028Q3 | 2758 |           0.2197 |         0.2432 |                0.1783 |                0.2176 |                  0.198  |           0.2194 |                         0.223  |

## 6. AUC theo nhóm

|                             |     n |   tabpfn |   hist_baseline |   logistic_base |   logistic_spline |   catboost |   catboost_khong_tien_do |
|:----------------------------|------:|---------:|----------------:|----------------:|------------------:|-----------:|-------------------------:|
| giảng viên mới (<5 việc)    |   249 |  nan     |         nan     |         nan     |           nan     |    nan     |                  nan     |
| giảng viên có lịch sử (>=5) | 31979 |    0.835 |           0.691 |           0.833 |             0.834 |      0.832 |                    0.806 |
| mùa cao điểm                | 15732 |    0.849 |           0.698 |           0.847 |             0.848 |      0.845 |                    0.821 |
| độ phức tạp cao             | 11591 |    0.83  |           0.696 |           0.826 |             0.827 |      0.826 |                    0.795 |
| Khoa K01                    |  5379 |    0.84  |           0.71  |           0.834 |             0.84  |      0.832 |                    0.812 |
| Khoa K02                    |  5563 |    0.831 |           0.688 |           0.831 |             0.831 |      0.827 |                    0.811 |
| Khoa K03                    |  5203 |    0.823 |           0.682 |           0.821 |             0.825 |      0.821 |                    0.788 |
| Khoa K04                    |  5617 |    0.844 |           0.711 |           0.843 |             0.84  |      0.841 |                    0.808 |
| Khoa K05                    |  4980 |    0.853 |           0.706 |           0.851 |             0.848 |      0.848 |                    0.83  |
| Khoa K06                    |  5486 |    0.833 |           0.676 |           0.828 |             0.832 |      0.831 |                    0.803 |
| mốc tiến độ 25%             | 16722 |    0.828 |           0.691 |           0.826 |             0.827 |      0.824 |                    0.806 |
| mốc tiến độ 50%             | 15506 |    0.843 |           0.691 |           0.84  |             0.842 |      0.839 |                    0.807 |

## Lưu ý
- Dữ liệu mô phỏng: chỉ số phản ánh khả năng học lại quy luật đã mô phỏng, không phải hiệu quả trên dữ liệu thật.
- Mọi lựa chọn (cấu hình, ngưỡng) chốt trên validation; tập test chỉ dùng để báo cáo.