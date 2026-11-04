# -*- coding: utf-8 -*-
r"""
Script tổng hợp và xuất bản Báo cáo Khóa luận Tốt nghiệp Hoàn chỉnh (.docx)
chuẩn cấu trúc 100% theo DoAn_HoanChinh.pdf và 1-huong-dan-kltn.docx:
- Chữ màu đen, nền trắng kể cả bảng
- Phông chữ Times New Roman cỡ 13 (kể cả chữ trong bảng)
- Tên ảnh (caption) 12 pt in nghiêng
- Mục lục tự động (TOC), Mục lục hình ảnh tự động (TOF)
- Đánh dấu tài liệu tham khảo [1] -> [15]
"""
import os
import sys
import shutil

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from kltn_part1_front_and_ch1_ch2 import setup_huit_document
from kltn_part1_builders import build_front_matter
from kltn_part2_intro_ch1_ch2 import build_chapter1, build_chapter2
from kltn_part3_ch3 import build_chapter3
from kltn_part4_ch4_ch5_refs import build_chapter4, build_chapter5, build_references, build_appendix

ROOT_DIR = r"e:\GGCLASS\New folder\data\Quan_Li_Cong_Viec_DoAn-main"
DOCS_DIR = os.path.join(ROOT_DIR, "docs")
DATA_DIR = r"e:\GGCLASS\New folder\data"
DIAGRAMS_DIR = os.path.join(HERE, "diagrams")
os.makedirs(DOCS_DIR, exist_ok=True)

TARGET_PATHS = [
    os.path.join(DOCS_DIR, "BAO_CAO_KLTN_CNTT_KLCN184_V6_AUTOMATIC_TOF.docx"),
    os.path.join(DATA_DIR, "BAO_CAO_KLTN_CNTT_KLCN184_V6_AUTOMATIC_TOF.docx"),
    os.path.join(DOCS_DIR, "BAO_CAO_KLTN_CNTT_KLCN184_V5_EQUATION_UML.docx"),
    os.path.join(DATA_DIR, "BAO_CAO_KLTN_CNTT_KLCN184_V5_EQUATION_UML.docx"),
    os.path.join(DOCS_DIR, "BAO_CAO_KLTN_CNTT_KLCN184_HOAN_CHINH.docx"),
    os.path.join(DOCS_DIR, "BAO_CAO_KLTN_CNTT_KLCN184_CHUAN_MAU_HUIT.docx"),
    os.path.join(DATA_DIR, "BAO_CAO_KLTN_CNTT_KLCN184_CHUAN_MAU_HUIT.docx"),
    os.path.join(DOCS_DIR, "BAO_CAO_KLTN_CNTT_KLCN184_MOI_NHAT.docx"),
    os.path.join(DATA_DIR, "BAO_CAO_KLTN_CNTT_KLCN184_MOI_NHAT.docx"),
]
OUT_CH4_DOCX = os.path.join(DATA_DIR, "CHUONG_4_THUC_NGHIEM_VA_DANH_GIA_KET_QUA.docx")


def save_doc_safely(doc, path):
    try:
        doc.save(path)
        print(f"SUCCESS: Da luu thanh cong -> {path}")
        return True
    except PermissionError:
        print(f"LOCKED (Word dang mo): {path}")
        return False
    except Exception as e:
        print(f"ERROR khi luu {path}: {e}")
        return False


def generate_all():
    print("[1/3] Khoi tao va xay dung toan bo Bao cao KLTN chuan DoAn_HoanChinh.pdf...")
    doc = setup_huit_document()
    
    print("  -> Phan dau (Bia chinh DoAn_HoanChinh chu den, Bia phu, Loi mo dau, Cam doan, Cam on, Danh gia nhom, Danh muc hinh/bang tu dong, Muc luc tu dong)...")
    build_front_matter(doc)
    
    print("  -> Chuong 1 (Tong quan de tai, 4 so do UML, 16 cot Excel, hien trang HUIT, nen trang, chu den)...")
    build_chapter1(doc, DIAGRAMS_DIR)
    
    print("  -> Chuong 2 (Co so ly thuyet, VS Code, Python, React 19, SQL vs Excel, TabPFN v2, MLOps, trich dan [1]-[15])...")
    build_chapter2(doc)
    
    print("  -> Chuong 3 (Ham thu tuc 3 cap, RBAC 4 pham vi, 58 dac trung, CSDL 17 bang, Seed data, co 13 nen trang)...")
    build_chapter3(doc)
    
    print("  -> Chuong 4 (Giao dien Web, Doi sanh 6 mo hinh, 8 do thi PNG, MLOps, 5 muc kiem chung may that)...")
    build_chapter4(doc, ROOT_DIR)
    
    print("  -> Chuong 5, Tai lieu tham khao IEEE va Phu luc...")
    build_chapter5(doc)
    build_references(doc)
    build_appendix(doc)
    
    print(f"  -> Tong so doan van (paragraphs): {len(doc.paragraphs)}")
    print(f"  -> Tong so bang bieu (tables): {len(doc.tables)}")

    # [1b] Luu ban goc vao primary target
    primary_target = TARGET_PATHS[0]
    print(f"\n[1b] Luu ban goc vao: {primary_target}")
    save_doc_safely(doc, primary_target)

    # [1c] Cap nhat toan bo truong (TOC, TOF, Page Numbers) bang chinh Word Automation
    vbs_path = os.path.join(HERE, "word_update_fields.vbs")
    if os.path.exists(vbs_path):
        print(f"\n[1c] Goi Microsoft Word COM de cap nhat Danh muc Hinh, Bang, Muc luc va So trang...")
        import subprocess
        # Force kill bat ky tien trinh winword treo truoc do
        subprocess.run(["powershell", "-Command", "Stop-Process -Name winword -Force -ErrorAction SilentlyContinue"], capture_output=True)
        res = subprocess.run(["cscript", "//Nologo", vbs_path, primary_target], capture_output=True, text=True, encoding="utf-8", errors="ignore")
        print(res.stdout)
        if res.returncode != 0:
            print("WARNING khi chay word_update_fields.vbs:", res.stderr)

    # [1d] Dong bo tep da duoc Word cap nhat sang tat ca cac vi tri con lai
    print(f"\n[1d] Dong bo tep da cap nhat hoan chinh sang tat ca {len(TARGET_PATHS)-1} duong dan con lai...")
    for target in TARGET_PATHS[1:]:
        try:
            shutil.copy2(primary_target, target)
            print(f"  -> Da dong bo: {target}")
        except Exception as e:
            print(f"  -> Loi khi copy sang {target}: {e}")

    # [2/3] Xây dựng tệp Chương 4 độc lập
    print("\n[2/3] Dang cap nhat tep Chuong 4 doc lap...")
    doc_ch4 = setup_huit_document()
    build_chapter4(doc_ch4, ROOT_DIR)
    save_doc_safely(doc_ch4, OUT_CH4_DOCX)
    print(f"  -> So doan van Ch4: {len(doc_ch4.paragraphs)}, So bang Ch4: {len(doc_ch4.tables)}")

    # [3/3] Báo cáo kích thước
    print("\n[3/3] TONG KET XUAT BAN THANH CONG:")
    for p in TARGET_PATHS + [OUT_CH4_DOCX]:
        if os.path.exists(p):
            size_kb = round(os.path.getsize(p) / 1024, 1)
            print(f"  - {p} ({size_kb} KB)")


if __name__ == "__main__":
    generate_all()
