| Mô hình | Backend | AUC test [KTC 95% theo giảng viên] | PR-AUC | Brier | ECE | Ngưỡng |
|---|---|---|---|---|---|---|
| Tĩnh | TabPFN 9.2.0 (4 túi, cuda) | 0.8090 [0.796; 0.821] | 0.5972 | 0.1266 | 0.0075 | [0.23, 0.52] |
| Tĩnh (--fast-cpu) | HistGradientBoosting 4 túi | 0.8047 | 0.5917 | 0.1282 | 0.0192 | cùng ngưỡng |
| Động | TabPFN 9.2.0 (4 túi, cuda) | 0.8356 [0.825; 0.846] | 0.6754 | 0.1249 | 0.0051 | [0.26, 0.42] |
| Động (--fast-cpu) | HistGradientBoosting 4 túi | 0.8297 | 0.6673 | 0.1276 | 0.0251 | cùng ngưỡng |