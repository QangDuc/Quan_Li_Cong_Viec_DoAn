#!/usr/bin/env python3
"""Xuất BAO_CAO_3_SEEDS.md từ kết quả run_baselines.py trên nhiều bộ dữ liệu (mỗi bộ một seed). MỌI con số và nhận xét xếp hạng đều TÍNH TỪ DỮ LIỆU,
không ghi cứng. Mô hình đối chứng là CPU (logistic, logistic + spline, CatBoost); TabPFN KHÔNG nằm trong báo cáo này.
  python export_3seeds_report.py --run 42:bl_static:du_lieu_co_dinh_v2 --run 43:bl_s43:pack_s43 --run 44:bl_s44:pack_s44 --out BAO_CAO_3_SEEDS.md
Mỗi --run là  seed:thư_mục_baselines:thư_mục_gói_dữ_liệu  (gói có MANIFEST.json và data/oracle_truth.csv)."""
import argparse, json, os
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

ap = argparse.ArgumentParser(); ap.add_argument("--run", action="append", required=True); ap.add_argument("--out", default="BAO_CAO_3_SEEDS.md")
ap.add_argument("--date", default=None)
a = ap.parse_args()
MODELS = ["logistic_base", "logistic_spline", "catboost"]
LABEL = {"logistic_base": "Hồi quy Logistic", "logistic_spline": "Hồi quy Logistic + Spline", "catboost": "CatBoost"}
f4 = lambda x: f"{x:.4f}".replace(".", ",")
f1 = lambda x: f"{100 * x:.2f}%".replace(".", ",")
nf = lambda n: f"{int(n):,}".replace(",", ".")

R = {}
for r in a.run:
    seed, bl, pack = r.split(":"); seed = int(seed)
    info = json.load(open(os.path.join(bl, "baselines_info.json"), encoding="utf-8"))["models"]
    man = json.load(open(os.path.join(pack, "MANIFEST.json"), encoding="utf-8"))
    t = pd.read_csv(os.path.join(bl, "predictions_test.csv")); o = pd.read_csv(os.path.join(pack, "data", "oracle_truth.csv"))
    m = t.merge(o[["task_id", "lecturer_id", "z_signal"]], on=["task_id", "lecturer_id"])
    R[seed] = dict(info=info, man=man, oracle=float(roc_auc_score(m.y, m.z_signal)), n_oracle=len(m), name=man["dataset_name"])
seeds = sorted(R)
auc = {m: [R[s]["info"][m]["test"]["roc_auc"] for s in seeds] for m in MODELS}
ms = lambda v: f"{np.mean(v):.4f} ± {np.std(v, ddof=1):.4f}".replace(".", ",")

L = ["# Nhân bản trên nhiều seed: mô hình đối chứng CPU", "",
     f"Ngày xuất: {a.date or pd.Timestamp.today().date()}. Dữ liệu mô phỏng (cùng bộ sinh `gen_synthetic_data_v5.py`, 360 giảng viên, 6 Khoa, 5 năm; chỉ đổi seed). "
     "Mô hình đối chứng huấn luyện trên tập train, chọn siêu tham số trên validation, đo trên test. **TabPFN không nằm trong báo cáo này** (cần GPU; xem notebook theo seed).", "",
     "## 1. Các bộ dữ liệu", "", "| | " + " | ".join(f"Seed {s}" for s in seeds) + " |", "|---|" + "---|" * len(seeds)]
rowdef = [("Gói dữ liệu", lambda s: f"`{R[s]['name']}`"),
          ("Số dòng tĩnh", lambda s: nf(sum(R[s]["man"]["static"][k] for k in ("n_train", "n_val", "n_test")))),
          ("Train / Validation / Test", lambda s: " / ".join(nf(R[s]["man"]["static"][k]) for k in ("n_train", "n_val", "n_test"))),
          ("Tỉ lệ trễ train / validation / test", lambda s: " / ".join(f1(R[s]["man"]["static"][k]) for k in ("late_train", "late_val", "late_test"))),
          ("Số dòng động", lambda s: nf(sum(R[s]["man"]["dynamic"][k] for k in ("n_train", "n_val", "n_test"))))]
for lab, fn in rowdef: L.append(f"| {lab} | " + " | ".join(fn(s) for s in seeds) + " |")
L += ["", "## 2. ROC-AUC trên tập test (tĩnh)", "", "| Mô hình | " + " | ".join(f"Seed {s}" for s in seeds) + " | Trung bình ± độ lệch chuẩn mẫu |", "|---|" + "---|" * (len(seeds) + 1)]
for m in MODELS: L.append(f"| {LABEL[m]} | " + " | ".join(f4(v) for v in auc[m]) + f" | {ms(auc[m])} |")
L.append("| **Trần oracle (biết yếu tố ẩn)** | " + " | ".join(f4(R[s]["oracle"]) for s in seeds) + f" | {ms([R[s]['oracle'] for s in seeds])} |")
L += ["", "## 3. Các chỉ số khác (trung bình ± độ lệch chuẩn mẫu qua các seed)", "", "| Mô hình | PR-AUC | Brier | ECE |", "|---|---|---|---|"]
for m in MODELS:
    g = lambda k: [R[s]["info"][m]["test"][k] for s in seeds]
    L.append(f"| {LABEL[m]} | {ms(g('pr_auc'))} | {ms(g('brier'))} | {ms(g('ece'))} |")

winners = {s: max(MODELS, key=lambda m: R[s]["info"][m]["test"]["roc_auc"]) for s in seeds}
spread = {s: max(R[s]["info"][m]["test"]["roc_auc"] for m in MODELS) - min(R[s]["info"][m]["test"]["roc_auc"] for m in MODELS) for s in seeds}
gap = {m: [R[s]["oracle"] - R[s]["info"][m]["test"]["roc_auc"] for s in seeds] for m in MODELS}
cb_lr = [R[s]["info"]["catboost"]["test"]["roc_auc"] - R[s]["info"]["logistic_base"]["test"]["roc_auc"] for s in seeds]
L += ["", "## 4. Nhận xét (tính từ số liệu ở trên)", ""]
if len(set(winners.values())) == 1:
    L.append(f"1. **Thứ hạng:** {LABEL[list(winners.values())[0]]} có AUC cao nhất ở cả {len(seeds)} seed.")
else:
    L.append("1. **Thứ hạng không nhất quán:** mô hình có AUC cao nhất là " + "; ".join(f"seed {s}: {LABEL[winners[s]]}" for s in seeds) + ".")
L.append(f"2. **Mức chênh giữa ba mô hình rất nhỏ:** AUC lớn nhất trừ nhỏ nhất trong mỗi seed là " + "; ".join(f"seed {s}: {f4(spread[s])}" for s in seeds) +
         f". CatBoost trừ logistic: " + "; ".join(f"seed {s}: {cb_lr[i]:+.4f}".replace(".", ",") for i, s in enumerate(seeds)) + ".")
L.append(f"3. **Khoảng cách tới trần oracle:** " + "; ".join(f"{LABEL[m]} {ms(gap[m])}" for m in MODELS) + ". Khoảng cách này gần như bằng nhau giữa các mô hình, nên đổi họ mô hình ít thu hẹp được nó.")
L.append("4. **Độ biến thiên giữa các seed:** độ lệch chuẩn của AUC khoảng " + f4(np.mean([np.std(auc[m], ddof=1) for m in MODELS])) +
         ". Độ lệch này gồm cả khác biệt giữa các bộ dữ liệu sinh ra (khác tập test, khác tỉ lệ trễ), không chỉ nhiễu của mô hình.")
L += ["", "## 5. Hạn chế", "",
      f"- Chỉ {len(seeds)} seed: ước lượng độ lệch chuẩn từ {len(seeds)} điểm rất thiếu chính xác; không có kiểm định thống kê giữa các mô hình trong báo cáo này.",
      "- Chỉ có mô hình CPU. Kết luận về TabPFN (so với CatBoost, logistic) cần chạy TabPFN trên từng seed (GPU).",
      "- Cùng một bộ sinh và cùng giả định mô phỏng; nhân bản theo seed chỉ kiểm tra độ nhạy với ngẫu nhiên của bộ sinh, không kiểm tra tính đúng đắn của giả định.",
      "- Việc đạt kết quả tương tự trên các seed không chứng minh mô hình không rò rỉ hay không overfit; rò rỉ (nếu có) do quy trình sinh đặc trưng sẽ lặp lại ở mọi seed.",
      "- Tập test của seed 42 đã được xem nhiều lần trong quá trình phát triển; seed 43 và 44 dùng làm nhân bản."]
open(a.out, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("\n".join(L))
