| Mô hình | Backend | AUC test [KTC 95% theo giảng viên] | PR-AUC | Brier | ECE | Ngưỡng |
|---|---|---|---|---|---|---|
| Tĩnh | TabPFN 9.2.0 (4 túi, cuda) | 0.8195 [0.806; 0.830] | 0.6046 | 0.1148 | 0.0054 | [0.23, 0.45] |
| Tĩnh (--fast-cpu) | HistGradientBoosting 4 túi | 0.8150 | 0.5968 | 0.1162 | 0.0101 | cùng ngưỡng |
| Động | TabPFN 9.2.0 (4 túi, cuda) | 0.8414 [0.829; 0.851] | 0.6663 | 0.1127 | 0.0054 | [0.25, 0.39] |
| Động (--fast-cpu) | HistGradientBoosting 4 túi | 0.8358 | 0.6565 | 0.1146 | 0.0111 | cùng ngưỡng |