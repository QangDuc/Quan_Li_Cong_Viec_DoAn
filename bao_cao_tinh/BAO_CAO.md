# Báo cáo cuối: Mô hình tĩnh

Tập test: **24,994** dòng, tỉ lệ trễ **19.84%**. Khoảng tin cậy 95% bootstrap theo cụm giảng viên (400 lần).

## 1. Chỉ số trên tập test

| Mô hình | AUC [KTC 95%] | PR-AUC | Brier | Log-loss | ECE |
|---|---|---|---|---|---|
| TabPFN v2 | 0.8195 [0.806; 0.830] | 0.6046 | 0.1148 | 0.3752 | 0.0054 |
| Baseline lịch sử | 0.6838 [0.659; 0.702] | 0.3532 | 0.1490 | 0.4702 | 0.0372 |
| Logistic (tuyến tính) | 0.8160 [0.803; 0.826] | 0.5947 | 0.1164 | 0.3796 | 0.0100 |
| Logistic (spline) | 0.8170 [0.805; 0.827] | 0.6009 | 0.1158 | 0.3785 | 0.0166 |
| CatBoost | 0.8189 [0.806; 0.829] | 0.6044 | 0.1147 | 0.3751 | 0.0050 |

## 2. So sánh cặp: TabPFN trừ mô hình khác

| So với | ΔAUC [KTC 95%] | ΔBrier | Δlog-loss |
|---|---|---|---|
| Baseline lịch sử | +0.1368 [+0.1226; +0.1534] | -0.03428 | -0.09531 |
| Logistic (tuyến tính) | +0.0035 [+0.0019; +0.0054] | -0.00161 | -0.00443 |
| Logistic (spline) | +0.0025 [+0.0004; +0.0049] | -0.00092 | -0.00327 |
| CatBoost | +0.0006 [-0.0009; +0.0023] | +0.00010 | +0.00013 |

(ΔAUC > 0: TabPFN tốt hơn; ΔBrier, Δlog-loss < 0: TabPFN tốt hơn. Khoảng tin cậy chứa 0: chưa đủ bằng chứng về khác biệt.)

## 3. Mức cảnh báo của TabPFN (ngưỡng chọn trên validation)

Ngưỡng: [0.23, 0.45] | mục tiêu: {'max_late_low': 0.1, 'actual_low': 0.0916, 'ok_low': True, 'min_prec_high': 0.6, 'actual_high': 0.6698, 'ok_high': True}

| Mức | Số việc | % số việc | Tỉ lệ trễ thực tế |
|---|---|---|---|
| Thấp | 18,305 | 73.2% | 9.2% |
| Trung bình | 3,506 | 14.0% | 32.8% |
| Cao | 3,183 | 12.7% | 67.0% |

## 4. Mô hình nhẹ `--fast-cpu` (HistGradientBoosting, KHÔNG phải TabPFN)

AUC 0.8150 | PR-AUC 0.5968 | Brier 0.1162 | ECE 0.0101 | Spearman với TabPFN 0.952

Với ngưỡng của TabPFN: Thấp: 18,471 việc, trễ 9.5%; Trung bình: 3,593 việc, trễ 33.4%; Cao: 2,930 việc, trễ 68.5%

## 5. Hiệu chuẩn theo quý (tỉ lệ trễ thực tế và dự đoán trung bình)

| quy    |    n |   ti_le_tre_that |   tabpfn_dd_TB |   hist_baseline_dd_TB |   logistic_base_dd_TB |   logistic_spline_dd_TB |   catboost_dd_TB |
|:-------|-----:|-----------------:|---------------:|----------------------:|----------------------:|------------------------:|-----------------:|
| 2027Q3 | 2794 |           0.17   |         0.1779 |                0.1653 |                0.1669 |                  0.1646 |           0.1736 |
| 2027Q4 | 6473 |           0.1829 |         0.1843 |                0.1579 |                0.1873 |                  0.1811 |           0.1871 |
| 2028Q1 | 5772 |           0.1862 |         0.1833 |                0.1608 |                0.179  |                  0.1667 |           0.1884 |
| 2028Q2 | 7904 |           0.2252 |         0.2076 |                0.1625 |                0.2108 |                  0.1985 |           0.2158 |
| 2028Q3 | 2051 |           0.2175 |         0.2142 |                0.1628 |                0.202  |                  0.1909 |           0.2165 |

## 6. AUC theo nhóm

|                             |     n |   tabpfn |   hist_baseline |   logistic_base |   logistic_spline |   catboost |
|:----------------------------|------:|---------:|----------------:|----------------:|------------------:|-----------:|
| giảng viên mới (<5 việc)    |   225 |    0.672 |           0.439 |           0.679 |             0.738 |      0.686 |
| giảng viên có lịch sử (>=5) | 24769 |    0.819 |           0.685 |           0.816 |             0.817 |      0.819 |
| mùa cao điểm                | 13148 |    0.827 |           0.687 |           0.822 |             0.823 |      0.826 |
| độ phức tạp cao             |  7103 |    0.809 |           0.685 |           0.804 |             0.804 |      0.808 |
| Khoa K01                    |  4308 |    0.796 |           0.647 |           0.79  |             0.788 |      0.791 |
| Khoa K02                    |  4036 |    0.832 |           0.677 |           0.832 |             0.832 |      0.834 |
| Khoa K03                    |  3767 |    0.821 |           0.703 |           0.816 |             0.818 |      0.82  |
| Khoa K04                    |  4530 |    0.845 |           0.713 |           0.842 |             0.843 |      0.843 |
| Khoa K05                    |  4142 |    0.801 |           0.703 |           0.8   |             0.802 |      0.801 |
| Khoa K06                    |  4211 |    0.807 |           0.648 |           0.803 |             0.805 |      0.808 |

## 7. So với xác suất 'thật' của bộ sinh dữ liệu (oracle AUC 0.8322, TB 0.201)

                    auc  khoang_cach_toi_oracle  pearson   dd_TB
model                                                           
tabpfn           0.8195                  0.0127   0.9550  0.1931
hist_baseline    0.6838                  0.1484   0.4942  0.1613
logistic_base    0.8160                  0.0162   0.9394  0.1918
logistic_spline  0.8170                  0.0151   0.9504  0.1822
catboost         0.8189                  0.0133   0.9562  0.1974

## Lưu ý
- Dữ liệu mô phỏng: chỉ số phản ánh khả năng học lại quy luật đã mô phỏng, không phải hiệu quả trên dữ liệu thật.
- Mọi lựa chọn (cấu hình, ngưỡng) chốt trên validation; tập test chỉ dùng để báo cáo.