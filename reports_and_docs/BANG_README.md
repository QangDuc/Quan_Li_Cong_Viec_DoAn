| Mô hình | Backend | AUC test [KTC 95% theo giảng viên] | PR-AUC | Brier | ECE | Ngưỡng |
|---|---|---|---|---|---|---|
| Tĩnh | TabPFN 9.2.0 (4 túi, cuda) | 0.8090 [0.796; 0.821] | 0.5972 | 0.1266 | 0.0075 | [0.23, 0.52] |
| Động | TabPFN 9.2.0 (4 túi, cuda) | 0.8356 [0.825; 0.846] | 0.6754 | 0.1249 | 0.0051 | [0.26, 0.42] |

Ghi chú: mục tiêu nhóm Thấp (tỉ lệ trễ <= 10%) KHÔNG đạt trên tập test (tĩnh 10,04%; động 10,26%); mục tiêu nhóm Cao (độ chính xác >= 60%) đạt (69,3%; 67,5%). Dữ liệu mô phỏng.
Mô hình duy nhất được báo cáo là TabPFN; mô hình nhẹ HistGradientBoosting (`--fast-cpu`) đã được gỡ khỏi gói.
