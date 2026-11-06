#!/usr/bin/env python3
"""Đối chiếu các con số trong chương 4 (Word) với nguồn dữ liệu của gói.

Số trong Word được gõ tay, nên script này lấy số từ file kết quả (metrics.json, so_sanh_cap.json,
bang_chi_so.csv, predictions_test.csv) rồi kiểm tra từng số có xuất hiện trong văn bản hay không.
Đồng thời tìm các chuỗi cũ đã biết là sai (số của bộ dữ liệu trước, câu khẳng định quá mức).

Chạy:  python kiem_tra_so_lieu_chuong4.py            (từ thư mục gốc của gói)
       python kiem_tra_so_lieu_chuong4.py --docx duong_dan/chuong4.docx
Mã thoát 0 nếu mọi kiểm tra đạt, 1 nếu có kiểm tra không đạt.

Giới hạn: script chỉ kiểm tra rằng số kỳ vọng CÓ MẶT trong văn bản, không kiểm tra nó nằm đúng ô bảng
hay đúng câu. Các số không có trong danh sách dưới đây chưa được kiểm tra.
"""
import argparse, csv, html, json, os, re, sys, zipfile
from decimal import Decimal, ROUND_HALF_UP

ROOT = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--docx", default=os.path.join(ROOT, "reports_and_docs", "CHUONG_4_THUC_NGHIEM_VA_DANH_GIA_KET_QUA.docx"))
a = ap.parse_args()


def P(*p):
    return os.path.join(ROOT, *p)


def load_json(*p):
    with open(P(*p), encoding="utf-8") as f:
        return json.load(f)


def docx_text(path):
    x = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    x = re.sub(r"</w:p>", "\n", x)
    return html.unescape(re.sub(r"<[^>]+>", "", x))


def rnd(v, nd):
    """Làm tròn nửa lên theo chuỗi thập phân (tránh sai số nhị phân của float)."""
    q = Decimal(1).scaleb(-nd)
    return str(Decimal(str(v)).quantize(q, rounding=ROUND_HALF_UP))


def rnd_alts(v, nd):
    """Giá trị trong file kết quả chỉ lưu 5 chữ số thập phân. Nếu chữ số thứ 5 đúng bằng 5 (hòa), giá trị
    gốc chưa làm tròn có thể làm tròn lên hoặc xuống, nên chấp nhận cả hai cách ghi."""
    up = Decimal(str(v)).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP)
    down = Decimal(str(v)).quantize(Decimal(1).scaleb(-nd), rounding="ROUND_HALF_DOWN")
    return sorted({str(up), str(down)})


def thousands(n):
    return f"{int(n):,}".replace(",", ".")


def signed(v, nd=4):
    s = rnd(abs(v), nd)
    return ("+" if v >= 0 else "-") + s


text = docx_text(a.docx)
results = []


def need(label, token):
    alts = token if isinstance(token, list) else [token]
    results.append((any(t in text for t in alts), label, " hoặc ".join(alts)))


def forbid(label, token):
    results.append((token not in text, "KHÔNG được có: " + label, token))


# ---------- nguồn ----------
ms = load_json("model", "metrics.json")
md = load_json("model_dynamic", "metrics.json")
cs = load_json("reports_and_docs", "bao_cao_tinh", "so_sanh_cap.json")
cd = load_json("reports_and_docs", "bao_cao_dong", "so_sanh_cap.json")

# ---------- quy mô tập dữ liệu ----------
need("n train (tĩnh)", thousands(ms["n_train"]))
need("n test tĩnh", thousands(ms["n_test"]))
need("n test động", thousands(md["n_test"]))
need("ngày cuối train", ".".join(reversed(ms["meta"]["train_end"].split("-"))).replace(".", "/"))
need("ngày cuối validation", "/".join(reversed(ms["meta"]["test_after"].split("-"))))
need("tỉ lệ trễ test tĩnh", rnd(cs["late_rate"] * 100, 1) + "%")
need("tỉ lệ trễ test động", rnd(cd["late_rate"] * 100, 1) + "%")
need("phiên bản Python", "Python " + ms["meta"]["versions"]["python"])
need("phiên bản TabPFN", "TabPFN " + ms["meta"]["versions"]["tabpfn"])

# ---------- bảng 4.1 (tĩnh) và 4.3 (động) ----------
NAMES_DOC = {
    "tabpfn": "TabPFN", "catboost": "CatBoost", "logistic_spline": "Logistic (Spline",
    "logistic_base": "Logistic (Tuyến", "hist_baseline": "Baseline Lịch sử",
}


def check_metrics_table(tag, cmp_json):
    has_baseline = "Baseline Lịch sử" in text or "Baseline lịch sử" in text
    for model, m in cmp_json["metrics"].items():
        if model == "hist_baseline" and not has_baseline:
            continue
        ci = cmp_json["auc_ci95"].get(model)
        if ci:
            need(f"{tag} {model}: ROC-AUC [KTC]",
                 [f"{a_} [{rnd(ci[0], 3)}; {rnd(ci[1], 3)}]" for a_ in rnd_alts(m["roc_auc"], 4)])
        else:
            need(f"{tag} {model}: ROC-AUC", rnd_alts(m["roc_auc"], 4))
        for key, nd in (("pr_auc", 4), ("brier", 4), ("logloss", 4), ("ece", 4)):
            need(f"{tag} {model}: {key}", rnd_alts(m[key], nd))


check_metrics_table("Bảng 4.1", cs)
check_metrics_table("Bảng 4.3", cd)

# ---------- so sánh cặp ----------
has_baseline = "Baseline Lịch sử" in text or "Baseline lịch sử" in text
for model, d in cs["paired_tabpfn_minus"].items():
    if model == "hist_baseline" and not has_baseline:
        continue
    if model in ("hist_baseline", "logistic_base", "catboost"):
        lo, hi = d["d_auc_ci"]
        need(f"ΔAUC TabPFN − {model}", [f"{signed(d['d_auc'])} [{signed(lo)}; {signed(hi)}]",
                                        f"{signed(d['d_auc'])} [{rnd(lo, 4)}; {rnd(hi, 4)}]"])

# ---------- bảng 4.2: mức cảnh báo ----------
thr = ms["thresholds"]
need("cặp ngưỡng", f"[{rnd(thr[0], 2)}, {rnd(thr[1], 2)}]")
for name, lv in ms["alert_levels"].items():
    need(f"mức {name}: số việc", thousands(lv["n"]))
    need(f"mức {name}: tỉ trọng", rnd(lv["share"] * 100, 1) + "%")
    # nhóm Thấp được ghi 2 chữ số thập phân vì sát mục tiêu 10%
    nd = 2 if name == "Thấp" else 1
    need(f"mức {name}: tỉ lệ trễ", rnd(lv["late_rate"] * 100, nd) + "%")

# kiểm chéo: tính lại bảng mức cảnh báo từ dự đoán, phải khớp metrics.json
rows = list(csv.DictReader(open(P("model", "predictions_test.csv"), encoding="utf-8")))
cnt = {"Thấp": [0, 0], "Trung bình": [0, 0], "Cao": [0, 0]}
for r in rows:
    p = float(r["risk_probability"])
    k = "Thấp" if p < thr[0] else ("Trung bình" if p < thr[1] else "Cao")
    cnt[k][0] += 1
    cnt[k][1] += int(float(r["y"]))
for k, (n, late) in cnt.items():
    lv = ms["alert_levels"][k]
    ok = n == lv["n"] and abs(late / n - lv["late_rate"]) < 5e-5
    results.append((ok, f"metrics.json khớp predictions_test.csv: mức {k}", f"{n} việc, trễ {late / n:.4f}"))

# ---------- chuỗi cũ đã biết là sai ----------
for tok in ("75.017", "18.755", "24.994", "34.700", "3.13.15", "10.0% (Đạt", "--fast-cpu", "HistGBoost",
            "Vượt trội", "Tăng vọt", "triệt tiêu hoàn toàn", "p < 0.001", "p < 0,001", "thấp nhất toàn hệ thống"):
    forbid(f"chuỗi cũ '{tok}'", tok)

# ---------- kiểm chéo file phụ & tính nhất quán mã nguồn ----------
bc = load_json("model", "bao_cao_muc_canh_bao.json")
for k in ("thresholds", "test", "alert_levels", "target_check", "segments"):
    results.append((bc.get(k) == ms.get(k), f"bao_cao_muc_canh_bao.json khớp model/metrics.json [{k}]", k))

ref_tm_path = P("training_scripts", "train_model.py") if os.path.exists(P("training_scripts", "train_model.py")) else P("train_model.py")
ref_tm = open(ref_tm_path, encoding="utf-8").read()
ht_tm = open(P("hoc_tiep_mlops", "train_model.py"), encoding="utf-8").read()
results.append((ref_tm == ht_tm, "hoc_tiep_mlops/train_model.py khớp train_model.py", "train_model.py"))

for nb_name in ("Colab_RETRAIN_v2.ipynb", "Colab_RETRAIN_v2_seed43.ipynb", "Colab_RETRAIN_v2_seed44.ipynb"):
    nb = load_json("colab_notebooks", nb_name)
    nb_tm = None
    for cell in nb.get("cells", []):
        src = "".join(cell.get("source", []))
        if "def pick_thresholds" in src:
            lines = src.splitlines(keepends=True)
            nb_tm = "".join(lines[1:]) if lines and lines[0].startswith("%%writefile") else src
            break
    results.append((nb_tm == ref_tm, f"{nb_name} nhúng đúng training_scripts/train_model.py", nb_name))

# ---------- báo cáo ----------
bad = [r for r in results if not r[0]]
for ok, label, token in results:
    if not ok:
        print(f"[KHÔNG ĐẠT] {label}: {token!r}")
print(f"\n{len(results) - len(bad)}/{len(results)} kiểm tra đạt. "
      f"(chỉ kiểm sự có mặt của số, không kiểm vị trí; số ngoài danh sách chưa được kiểm tra)")
sys.exit(1 if bad else 0)
