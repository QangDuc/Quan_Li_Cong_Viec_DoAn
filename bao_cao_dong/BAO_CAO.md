# Báo cáo cuối: Mô hình động

Tập test: **34,700** dòng, tỉ lệ trễ **21.50%**. Khoảng tin cậy 95% bootstrap theo cụm giảng viên (400 lần).

## 1. Chỉ số trên tập test

| Mô hình | AUC [KTC 95%] | PR-AUC | Brier | Log-loss | ECE |
|---|---|---|---|---|---|
| TabPFN v2 | 0.8414 [0.829; 0.851] | 0.6663 | 0.1127 | 0.3691 | 0.0054 |
| Baseline lịch sử | 0.6856 [0.661; 0.703] | 0.3759 | 0.1588 | 0.4952 | 0.0534 |
| Logistic (tuyến tính) | 0.8378 [0.826; 0.847] | 0.6544 | 0.1148 | 0.3756 | 0.0131 |
| Logistic (spline) | 0.8387 [0.827; 0.848] | 0.6629 | 0.1138 | 0.3732 | 0.0151 |
| CatBoost | 0.8367 [0.825; 0.847] | 0.6591 | 0.1143 | 0.3738 | 0.0105 |
| CatBoost (bỏ đặc trưng tiến độ) | 0.8109 [0.799; 0.822] | 0.6066 | 0.1238 | 0.3992 | 0.0106 |

## 2. So sánh cặp: TabPFN trừ mô hình khác

| So với | ΔAUC [KTC 95%] | ΔBrier | Δlog-loss |
|---|---|---|---|
| Baseline lịch sử | +0.1571 [+0.1411; +0.1739] | -0.04619 | -0.12646 |
| Logistic (tuyến tính) | +0.0036 [+0.0019; +0.0054] | -0.00215 | -0.00663 |
| Logistic (spline) | +0.0027 [+0.0009; +0.0049] | -0.00111 | -0.00417 |
| CatBoost | +0.0046 [+0.0029; +0.0064] | -0.00160 | -0.00476 |
| CatBoost (bỏ đặc trưng tiến độ) | +0.0304 [+0.0261; +0.0347] | -0.01104 | -0.03007 |

(ΔAUC > 0: TabPFN tốt hơn; ΔBrier, Δlog-loss < 0: TabPFN tốt hơn. Khoảng tin cậy chứa 0: chưa đủ bằng chứng về khác biệt.)

## 3. Mức cảnh báo của TabPFN (ngưỡng chọn trên validation)

Ngưỡng: [0.25, 0.39] | mục tiêu: {'max_late_low': 0.1, 'actual_low': 0.0922, 'ok_low': True, 'min_prec_high': 0.6, 'actual_high': 0.6653, 'ok_high': True}

| Mức | Số việc | % số việc | Tỉ lệ trễ thực tế |
|---|---|---|---|
| Thấp | 25,320 | 73.0% | 9.2% |
| Trung bình | 3,085 | 8.9% | 30.4% |
| Cao | 6,295 | 18.1% | 66.5% |

## 4. Mô hình nhẹ `--fast-cpu` (HistGradientBoosting, KHÔNG phải TabPFN)

AUC 0.8358 | PR-AUC 0.6565 | Brier 0.1146 | ECE 0.0111 | Spearman với TabPFN 0.949

Với ngưỡng của TabPFN: Thấp: 25,570 việc, trễ 9.6%; Trung bình: 3,245 việc, trễ 32.5%; Cao: 5,885 việc, trễ 67.3%

## 5. Hiệu chuẩn theo quý (tỉ lệ trễ thực tế và dự đoán trung bình)

| quy    |     n |   ti_le_tre_that |   tabpfn_dd_TB |   hist_baseline_dd_TB |   logistic_base_dd_TB |   logistic_spline_dd_TB |   catboost_dd_TB |   catboost_khong_tien_do_dd_TB |
|:-------|------:|-----------------:|---------------:|----------------------:|----------------------:|------------------------:|-----------------:|-------------------------------:|
| 2027Q3 |  4245 |           0.1804 |         0.1889 |                0.1665 |                0.1789 |                  0.1758 |           0.184  |                         0.1779 |
| 2027Q4 |  8654 |           0.2027 |         0.2074 |                0.1571 |                0.2098 |                  0.2043 |           0.2062 |                         0.2015 |
| 2028Q1 |  8360 |           0.2048 |         0.2015 |                0.1612 |                0.1958 |                  0.1853 |           0.2029 |                         0.1951 |
| 2028Q2 | 10405 |           0.2443 |         0.2326 |                0.1632 |                0.2352 |                  0.2225 |           0.2328 |                         0.2256 |
| 2028Q3 |  3036 |           0.226  |         0.2353 |                0.1628 |                0.2209 |                  0.2083 |           0.2225 |                         0.2167 |

## 6. AUC theo nhóm

|                             |     n |   tabpfn |   hist_baseline |   logistic_base |   logistic_spline |   catboost |   catboost_khong_tien_do |
|:----------------------------|------:|---------:|----------------:|----------------:|------------------:|-----------:|-------------------------:|
| giảng viên mới (<5 việc)    |   306 |    0.745 |           0.474 |           0.753 |             0.781 |      0.725 |                    0.725 |
| giảng viên có lịch sử (>=5) | 34394 |    0.841 |           0.686 |           0.837 |             0.838 |      0.837 |                    0.811 |
| mùa cao điểm                | 17546 |    0.847 |           0.686 |           0.841 |             0.842 |      0.841 |                    0.815 |
| độ phức tạp cao             | 12825 |    0.841 |           0.687 |           0.837 |             0.838 |      0.837 |                    0.804 |
| Khoa K01                    |  5837 |    0.817 |           0.646 |           0.811 |             0.808 |      0.81  |                    0.783 |
| Khoa K02                    |  5710 |    0.857 |           0.683 |           0.856 |             0.857 |      0.854 |                    0.824 |
| Khoa K03                    |  5165 |    0.832 |           0.699 |           0.828 |             0.829 |      0.827 |                    0.803 |
| Khoa K04                    |  6368 |    0.866 |           0.722 |           0.863 |             0.864 |      0.861 |                    0.84  |
| Khoa K05                    |  5896 |    0.825 |           0.705 |           0.825 |             0.825 |      0.822 |                    0.799 |
| Khoa K06                    |  5724 |    0.837 |           0.643 |           0.833 |             0.835 |      0.834 |                    0.802 |
| mốc tiến độ 25%             | 18014 |    0.834 |           0.685 |           0.831 |             0.832 |      0.83  |                    0.81  |
| mốc tiến độ 50%             | 16686 |    0.848 |           0.686 |           0.845 |             0.845 |      0.844 |                    0.811 |

## Lưu ý
- Dữ liệu mô phỏng: chỉ số phản ánh khả năng học lại quy luật đã mô phỏng, không phải hiệu quả trên dữ liệu thật.
- Mọi lựa chọn (cấu hình, ngưỡng) chốt trên validation; tập test chỉ dùng để báo cáo.