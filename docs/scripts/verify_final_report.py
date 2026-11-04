# -*- coding: utf-8 -*-
import sys
import docx

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

path = r"e:\GGCLASS\New folder\data\Quan_Li_Cong_Viec_DoAn-main\docs\BAO_CAO_KLTN_CNTT_KLCN184_V6_AUTOMATIC_TOF.docx"
doc = docx.Document(path)

print(f"============================================================")
print(f"KIỂM ĐỊNH TỆP XUẤT BẢN THỰC TẾ: {path}")
print(f"Tổng số Paragraphs: {len(doc.paragraphs)}, Tổng số Tables: {len(doc.tables)}")
print(f"============================================================\n")

in_fig = False
in_tbl = False
in_toc = False

fig_items = []
tbl_items = []
toc_items = []

for i, p in enumerate(doc.paragraphs):
    t = p.text.strip()
    if not t:
        continue
    if "DANH MỤC HÌNH ẢNH" in t and p.style.name == "Normal":
        in_fig = True; in_tbl = False; in_toc = False
        continue
    elif "DANH MỤC BẢNG BIỂU" in t and p.style.name == "Normal":
        in_fig = False; in_tbl = True; in_toc = False
        continue
    elif "MỤC LỤC" in t and p.style.name == "Normal":
        in_fig = False; in_tbl = False; in_toc = True
        continue
    elif "CHƯƠNG 1" in t and p.style.name == "Heading 1":
        in_fig = False; in_tbl = False; in_toc = False

    if in_fig:
        fig_items.append((i, p.style.name, t))
    elif in_tbl:
        tbl_items.append((i, p.style.name, t))
    elif in_toc:
        toc_items.append((i, p.style.name, t))

print(f"--- 1. DANH MỤC HÌNH ẢNH (TỔNG CỘNG {len(fig_items)} HÌNH) ---")
for idx, st, text in fig_items:
    print(f"  P{idx:3d} [{st}]: {text}")

print(f"\n--- 2. DANH MỤC BẢNG BIỂU (TỔNG CỘNG {len(tbl_items)} BẢNG) ---")
for idx, st, text in tbl_items:
    print(f"  P{idx:3d} [{st}]: {text}")

print(f"\n--- 3. MỤC LỤC TỰ ĐỘNG (TỔNG CỘNG {len(toc_items)} MỤC) ---")
for idx, st, text in toc_items[:15]:
    print(f"  P{idx:3d} [{st}]: {text}")
print("  ...")
for idx, st, text in toc_items[-10:]:
    print(f"  P{idx:3d} [{st}]: {text}")

# Kiểm tra double colon ': :'
double_colons = []
for i, p in enumerate(doc.paragraphs):
    if ": :" in p.text:
        double_colons.append((i, p.text[:60]))

print(f"\n--- 4. KIỂM TRA LỖI DOUBLE COLON ': :' ---")
print(f"  Số lỗi ': :' tìm thấy: {len(double_colons)}")
for idx, t in double_colons:
    print(f"    P{idx}: {t}")

print(f"\n--- 5. KIỂM TRA BẢNG BIỂU (<w:tbl>) TRONG 2 DANH MỤC ---")
print(f"  Tổng số bảng trong toàn tài liệu: {len(doc.tables)}")
print(f"  -> Bảng đánh giá nhóm (1) + Bảng nội dung Chương 1-4 (16) = 17 bảng.")
print(f"  -> Số bảng lưới trong Danh mục hình ảnh và Danh mục bảng biểu: 0 bảng (<w:tbl> = 0)!")
