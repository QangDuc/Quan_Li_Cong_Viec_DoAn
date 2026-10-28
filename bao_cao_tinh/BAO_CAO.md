# Báo cáo cuối: Mô hình tĩnh

Tập test: **24,908** dòng, tỉ lệ trễ **21.72%**. Khoảng tin cậy 95% bootstrap theo cụm giảng viên (400 lần).

## 1. Chỉ số trên tập test

| Mô hình | AUC [KTC 95%] | PR-AUC | Brier | Log-loss | ECE |
|---|---|---|---|---|---|
| TabPFN v2 | 0.8090 [0.797; 0.820] | 0.5972 | 0.1266 | 0.4054 | 0.0075 |
| Baseline lịch sử | 0.6886 [0.666; 0.709] | 0.3722 | 0.1591 | 0.4930 | 0.0453 |
| Logistic (tuyến tính) | 0.8072 [0.795; 0.819] | 0.5936 | 0.1274 | 0.4073 | 0.0113 |
| Logistic (spline) | 0.8083 [0.796; 0.820] | 0.5963 | 0.1278 | 0.4092 | 0.0285 |
| CatBoost | 0.8095 [0.797; 0.821] | 0.5970 | 0.1268 | 0.4056 | 0.0144 |

## 2. So sánh cặp: TabPFN trừ mô hình khác

| So với | ΔAUC [KTC 95%] | ΔBrier | Δlog-loss |
|---|---|---|---|
| Baseline lịch sử | +0.1202 [+0.1064; +0.1358] | -0.03228 | -0.08719 |
| Logistic (tuyến tính) | +0.0018 [-0.0001; +0.0037] | -0.00071 | -0.00192 |
| Logistic (spline) | +0.0007 [-0.0016; +0.0029] | -0.00119 | -0.00380 |
| CatBoost | -0.0004 [-0.0022; +0.0014] | -0.00019 | -0.00031 |

(ΔAUC > 0: TabPFN tốt hơn; ΔBrier, Δlog-loss < 0: TabPFN tốt hơn. Khoảng tin cậy chứa 0: chưa đủ bằng chứng về khác biệt.)

## 3. Mức cảnh báo của TabPFN (ngưỡng chọn trên validation)

Ngưỡng: [0.23, 0.52] | mục tiêu: {'max_late_low': 0.1, 'actual_low': 0.1004, 'ok_low': False, 'min_prec_high': 0.6, 'actual_high': 0.6931, 'ok_high': True}

| Mức | Số việc | % số việc | Tỉ lệ trễ thực tế |
|---|---|---|---|
| Thấp | 17,172 | 68.9% | 10.0% |
| Trung bình | 4,927 | 19.8% | 35.3% |
| Cao | 2,809 | 11.3% | 69.3% |

## 4. Mô hình nhẹ `--fast-cpu` (HistGradientBoosting, KHÔNG phải TabPFN)

AUC 0.8047 | PR-AUC 0.5917 | Brier 0.1282 | ECE 0.0192 | Spearman với TabPFN 0.954

Với ngưỡng của TabPFN: Thấp: 17,809 việc, trễ 10.7%; Trung bình: 4,928 việc, trễ 38.7%; Cao: 2,171 việc, trễ 73.4%

## 5. Hiệu chuẩn theo quý (tỉ lệ trễ thực tế và dự đoán trung bình)

| quy    |    n |   ti_le_tre_that |   tabpfn_dd_TB |   hist_baseline_dd_TB |   logistic_base_dd_TB |   logistic_spline_dd_TB |   catboost_dd_TB |
|:-------|-----:|-----------------:|---------------:|----------------------:|----------------------:|------------------------:|-----------------:|
| 2027Q3 | 2484 |           0.1924 |         0.1786 |                0.1718 |                0.1703 |                  0.1541 |           0.167  |
| 2027Q4 | 6728 |           0.2127 |         0.205  |                0.17   |                0.203  |                  0.1842 |           0.1968 |
| 2028Q1 | 5909 |           0.2166 |         0.2183 |                0.1735 |                0.2082 |                  0.1936 |           0.2089 |
| 2028Q2 | 7743 |           0.2338 |         0.2227 |                0.1707 |                0.2194 |                  0.202  |           0.2146 |
| 2028Q3 | 2044 |           0.2011 |         0.2223 |                0.1778 |                0.2011 |                  0.1815 |           0.2038 |

## 6. AUC theo nhóm

|                             |     n |   tabpfn |   hist_baseline |   logistic_base |   logistic_spline |   catboost |
|:----------------------------|------:|---------:|----------------:|----------------:|------------------:|-----------:|
| giảng viên mới (<5 việc)    |   189 |  nan     |         nan     |         nan     |           nan     |    nan     |
| giảng viên có lịch sử (>=5) | 24719 |    0.809 |           0.689 |           0.807 |             0.808 |      0.809 |
| mùa cao điểm                | 12874 |    0.817 |           0.694 |           0.816 |             0.816 |      0.817 |
| độ phức tạp cao             |  6314 |    0.799 |           0.694 |           0.796 |             0.797 |      0.802 |
| Khoa K01                    |  4294 |    0.821 |           0.708 |           0.818 |             0.823 |      0.822 |
| Khoa K02                    |  4158 |    0.804 |           0.678 |           0.805 |             0.803 |      0.805 |
| Khoa K03                    |  4088 |    0.8   |           0.693 |           0.8   |             0.801 |      0.802 |
| Khoa K04                    |  4355 |    0.813 |           0.708 |           0.814 |             0.811 |      0.813 |
| Khoa K05                    |  3891 |    0.817 |           0.688 |           0.813 |             0.811 |      0.813 |
| Khoa K06                    |  4122 |    0.811 |           0.681 |           0.804 |             0.809 |      0.809 |

## 7. So với xác suất 'thật' của bộ sinh dữ liệu (oracle AUC 0.8261, TB 0.215)

                    auc  khoang_cach_toi_oracle  pearson   dd_TB
model                                                           
tabpfn           0.8090                  0.0171   0.9472  0.2125
hist_baseline    0.6886                  0.1375   0.5263  0.1719
logistic_base    0.8072                  0.0189   0.9380  0.2059
logistic_spline  0.8083                  0.0178   0.9448  0.1887
catboost         0.8095                  0.0167   0.9482  0.2028

## Lưu ý
- Dữ liệu mô phỏng: chỉ số phản ánh khả năng học lại quy luật đã mô phỏng, không phải hiệu quả trên dữ liệu thật.
- Mọi lựa chọn (cấu hình, ngưỡng) chốt trên validation; tập test chỉ dùng để báo cáo.