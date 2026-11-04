# -*- coding: utf-8 -*-
"""
Phần 1: Các hàm định dạng chuẩn HUIT (theo thesis-writer, 1-huong-dan-kltn.docx & DoAn_HoanChinh.pdf):
- Phân chia Section chuyên nghiệp:
  * Section 1: Trang bìa (không hiện số trang)
  * Section 2: Từ Lời mở đầu đến Mục lục (đánh số trang La Mã i, ii, iii, iv, ...)
  * Section 3: Từ Chương 1 đến hết (đánh số trang Ả Rập 1, 2, 3, 4, ... bắt đầu lại từ 1)
- Phông chữ Times New Roman, cỡ 13 pt, toàn bộ chữ màu đen (RGB 0, 0, 0)
- Nền trắng 100% kể cả bảng biểu (không đổ màu)
- Cỡ chữ trong bảng: 13 pt
- Tên ảnh (caption): 12 pt, in nghiêng
- Thay toàn bộ dấu gạch ngang dài en-dash/em-dash thành dấu gạch nối ngắn '-'
- Tích hợp Hyperlink nội bộ cho các trích dẫn tài liệu tham khảo [1]..[15]
- Mục lục tự động Word TOC
"""
import os
import re
import docx
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls


def clean_text(text: str) -> str:
    """Thay thế dấu gạch ngang dài en-dash và em-dash thành dấu gạch nối ngắn '-'."""
    if not text:
        return ""
    # Thay en-dash (\u2013) và em-dash (\u2014) thành hyphen-minus (-)
    return text.replace("–", "-").replace("—", "-")


def set_cell_bg_white(cell):
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="FFFFFF"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def set_cell_margins(cell, top=80, bottom=80, left=100, right=100):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def set_repeat_table_header(row):
    trPr = row._tr.get_or_add_trPr()
    tblHeader = OxmlElement('w:tblHeader')
    trPr.append(tblHeader)


def add_page_number_to_section(section, fmt="decimal", start_num=1):
    """
    Thiết lập số trang cho Section:
    - fmt='lowerRoman' hoặc 'roman': đánh số La Mã thường (i, ii, iii...)
    - fmt='decimal': đánh số Ả Rập (1, 2, 3...)
    - start_num: số bắt đầu của section
    Sử dụng trường chuẩn w:fldSimple w:instr="PAGE" tương thích 100% với mọi phiên bản Word.
    """
    section.header.is_linked_to_previous = False
    section.footer.is_linked_to_previous = False

    # Xóa các thẻ pgNumType cũ nếu có để tránh bị thừa
    for old_pg in section._sectPr.xpath('./w:pgNumType'):
        section._sectPr.remove(old_pg)

    xml_fmt = "lowerRoman" if fmt in ["lowerRoman", "roman"] else "decimal"

    # Thêm cấu hình pgNumType mới duy nhất vào sectPr
    pg_num_type = parse_xml(f'<w:pgNumType {nsdecls("w")} w:fmt="{xml_fmt}" w:start="{start_num}"/>')
    section._sectPr.append(pg_num_type)

    footer = section.footer
    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    
    # Xóa các run cũ nếu có
    p.text = ""
    cached_val = "i" if xml_fmt == "lowerRoman" else str(start_num)
    fld_xml = parse_xml(
        f'<w:fldSimple {nsdecls("w")} w:instr="PAGE">'
        f'<w:r>'
        f'<w:rPr>'
        f'<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'
        f'<w:sz w:val="26"/>'
        f'<w:color w:val="000000"/>'
        f'</w:rPr>'
        f'<w:t>{cached_val}</w:t>'
        f'</w:r>'
        f'</w:fldSimple>'
    )
    p._p.append(fld_xml)


def set_outline_level(paragraph, level: int):
    pPr = paragraph._p.get_or_add_pPr()
    outlineLvl = parse_xml(f'<w:outlineLvl {nsdecls("w")} w:val="{level}"/>')
    pPr.append(outlineLvl)


def setup_huit_document() -> Document:
    doc = Document()

    # Section 1: Từ Trang bìa đến Mục lục (đánh số trang theo ký tự La Mã i, ii, iii, iv, ...)
    sec1 = doc.sections[0]
    sec1.page_width = Cm(21.0)
    sec1.page_height = Cm(29.7)
    sec1.top_margin = Cm(2.0)
    sec1.bottom_margin = Cm(2.0)
    sec1.left_margin = Cm(3.0)
    sec1.right_margin = Cm(2.0)
    add_page_number_to_section(sec1, fmt="lowerRoman", start_num=1)

    normal = doc.styles['Normal']
    normal.font.name = 'Times New Roman'
    normal.font.size = Pt(13)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    normal.paragraph_format.line_spacing = 1.3
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for h_name, size, is_bold in [('Heading 1', 15, True), ('Heading 2', 14, True), ('Heading 3', 13, True)]:
        if h_name in doc.styles:
            h_style = doc.styles[h_name]
            h_style.font.name = 'Times New Roman'
            h_style.font.size = Pt(size)
            h_style.font.bold = is_bold
            h_style.font.color.rgb = RGBColor(0, 0, 0)
            h_style._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
            h_style.paragraph_format.line_spacing = 1.3
            h_style.paragraph_format.space_before = Pt(8)
            h_style.paragraph_format.space_after = Pt(4)

    # Style CaptionFigure cho Chú thích Hình (Times New Roman 12pt, nghiêng, căn giữa)
    if 'CaptionFigure' not in doc.styles:
        s_fig = doc.styles.add_style('CaptionFigure', docx.enum.style.WD_STYLE_TYPE.PARAGRAPH)
        s_fig.font.name = 'Times New Roman'
        s_fig.font.size = Pt(12)
        s_fig.font.italic = True
        s_fig.font.color.rgb = RGBColor(0, 0, 0)
        s_fig._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
        s_fig.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        s_fig.paragraph_format.space_before = Pt(2)
        s_fig.paragraph_format.space_after = Pt(10)
        s_fig.paragraph_format.first_line_indent = Cm(0)

    # Style CaptionTable cho Chú thích Bảng (Times New Roman 13pt, đậm, căn giữa)
    if 'CaptionTable' not in doc.styles:
        s_tbl = doc.styles.add_style('CaptionTable', docx.enum.style.WD_STYLE_TYPE.PARAGRAPH)
        s_tbl.font.name = 'Times New Roman'
        s_tbl.font.size = Pt(13)
        s_tbl.font.bold = True
        s_tbl.font.color.rgb = RGBColor(0, 0, 0)
        s_tbl._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
        s_tbl.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        s_tbl.paragraph_format.space_before = Pt(8)
        s_tbl.paragraph_format.space_after = Pt(4)
        s_tbl.paragraph_format.first_line_indent = Cm(0)

    # Cấu hình styles cho Mục lục TOC 1, TOC 2, TOC 3 (Times New Roman 13pt, chữ đen, giãn dòng 1.3)
    for toc_name in ['toc 1', 'toc 2', 'toc 3', 'TOC 1', 'TOC 2', 'TOC 3']:
        if toc_name in doc.styles:
            t_style = doc.styles[toc_name]
            t_style.font.name = 'Times New Roman'
            t_style.font.size = Pt(13)
            t_style.font.color.rgb = RGBColor(0, 0, 0)
            t_style._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
            t_style.paragraph_format.line_spacing = 1.3
            t_style.paragraph_format.space_before = Pt(2)
            t_style.paragraph_format.space_after = Pt(2)

    return doc


def add_p_with_links(doc, text="", bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                     indent_cm=1.0, space_after=6, space_before=0, font_size=13, color=(0, 0, 0)):
    """
    Thêm đoạn văn bản tự động nhận diện các mã trích dẫn [1]..[15]
    và gắn Hyperlink nội bộ trỏ tới bookmark ref_1..ref_15.
    Đồng thời tự động chuyển các ký tự en-dash/em-dash thành '-'.
    """
    cleaned = clean_text(text)
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    p.paragraph_format.line_spacing = 1.3
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(space_before)
    if indent_cm and align == WD_ALIGN_PARAGRAPH.JUSTIFY:
        p.paragraph_format.first_line_indent = Cm(indent_cm)

    if not cleaned:
        return p

    # Tách các thẻ trích dẫn [1] đến [15]
    parts = re.split(r'(\[(?:1[0-5]|[1-9])\])', cleaned)
    for part in parts:
        m = re.match(r'^\[(1[0-5]|[1-9])\]$', part)
        if m:
            ref_idx = m.group(1)
            # Chèn link nội bộ
            link_xml = parse_xml(
                f'<w:hyperlink {nsdecls("w")} w:anchor="ref_{ref_idx}">'
                f'<w:r>'
                f'<w:rPr>'
                f'<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'
                f'<w:sz w:val="{int(font_size * 2)}"/>'
                f'<w:color w:val="000000"/>'
                f'</w:rPr>'
                f'<w:t>[{ref_idx}]</w:t>'
                f'</w:r>'
                f'</w:hyperlink>'
            )
            p._p.append(link_xml)
        else:
            if part:
                r = p.add_run(part)
                r.bold = bold
                r.italic = italic
                r.font.name = 'Times New Roman'
                r.font.size = Pt(font_size)
                r.font.color.rgb = RGBColor(*(color or (0, 0, 0)))
                r._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    return p


# Giữ add_p đồng nghĩa với add_p_with_links
add_p = add_p_with_links


def add_bullet(doc, lead_bold: str, rest_text: str):
    cleaned_lead = clean_text(lead_bold)
    cleaned_rest = clean_text(rest_text)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    p.paragraph_format.line_spacing = 1.3
    p.paragraph_format.left_indent = Cm(0.8)
    p.paragraph_format.first_line_indent = Cm(-0.4)
    p.paragraph_format.space_after = Pt(4)
    
    r0 = p.add_run("• ")
    r0.font.name = 'Times New Roman'
    r0.font.size = Pt(13)
    r0.font.color.rgb = RGBColor(0, 0, 0)
    
    if cleaned_lead:
        r1 = p.add_run(cleaned_lead)
        r1.bold = True
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(13)
        r1.font.color.rgb = RGBColor(0, 0, 0)
        r1._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
        
    if cleaned_rest:
        parts = re.split(r'(\[(?:1[0-5]|[1-9])\])', cleaned_rest)
        for part in parts:
            m = re.match(r'^\[(1[0-5]|[1-9])\]$', part)
            if m:
                ref_idx = m.group(1)
                link_xml = parse_xml(
                    f'<w:hyperlink {nsdecls("w")} w:anchor="ref_{ref_idx}">'
                    f'<w:r>'
                    f'<w:rPr>'
                    f'<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'
                    f'<w:sz w:val="26"/>'
                    f'<w:color w:val="000000"/>'
                    f'</w:rPr>'
                    f'<w:t>[{ref_idx}]</w:t>'
                    f'</w:r>'
                    f'</w:hyperlink>'
                )
                p._p.append(link_xml)
            else:
                if part:
                    r2 = p.add_run(part)
                    r2.font.name = 'Times New Roman'
                    r2.font.size = Pt(13)
                    r2.font.color.rgb = RGBColor(0, 0, 0)
                    r2._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    return p


def add_chapter_title(doc, chapter_label: str, title_upper: str, page_break=False):
    if page_break:
        doc.add_page_break()
    lbl = clean_text(chapter_label)
    ttl = clean_text(title_upper)
    combined = f"{lbl}. {ttl}".strip(". ") if lbl else ttl
    
    p = doc.add_paragraph(style='Heading 1')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(14)
    p.paragraph_format.first_line_indent = Cm(0)
    set_outline_level(p, 0)
    
    r = p.add_run(combined.upper())
    r.bold = True
    r.font.name = 'Times New Roman'
    r.font.size = Pt(15)
    r.font.color.rgb = RGBColor(0, 0, 0)
    r._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    return p


def add_h1(doc, text: str):
    cleaned = clean_text(text)
    p = doc.add_paragraph(style='Heading 2')
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.first_line_indent = Cm(0)
    set_outline_level(p, 1)
    
    r = p.add_run(cleaned)
    r.bold = True
    r.font.name = 'Times New Roman'
    r.font.size = Pt(14)
    r.font.color.rgb = RGBColor(0, 0, 0)
    r._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    return p


def add_h2(doc, text: str):
    cleaned = clean_text(text)
    p = doc.add_paragraph(style='Heading 3')
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.first_line_indent = Cm(0)
    set_outline_level(p, 2)
    
    r = p.add_run(cleaned)
    r.bold = True
    r.font.name = 'Times New Roman'
    r.font.size = Pt(13)
    r.font.color.rgb = RGBColor(0, 0, 0)
    r._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    return p


def add_h3(doc, text: str):
    cleaned = clean_text(text)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.first_line_indent = Cm(0)
    
    r = p.add_run(cleaned)
    r.bold = True
    r.italic = True
    r.font.name = 'Times New Roman'
    r.font.size = Pt(13)
    r.font.color.rgb = RGBColor(0, 0, 0)
    r._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    return p


NS_M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

FORMULA_2_1_XML = f'''<m:oMathPara xmlns:m="{NS_M}" xmlns:w="{NS_W}"><m:oMath>
    <m:sSub><m:e><m:r><m:t>r</m:t></m:r></m:e><m:sub><m:r><m:t>smooth</m:t></m:r></m:sub></m:sSub>
    <m:r><m:t>(k, n) = </m:t></m:r>
    <m:f><m:num><m:r><m:t>k + 3.0 · 0.20</m:t></m:r></m:num><m:den><m:r><m:t>n + 3.0</m:t></m:r></m:den></m:f>
    <m:r><m:t>;    Lift(u, c) = </m:t></m:r>
    <m:sSub><m:e><m:r><m:t>r</m:t></m:r></m:e><m:sub><m:r><m:t>u,c</m:t></m:r></m:sub></m:sSub>
    <m:r><m:t> - </m:t></m:r>
    <m:sSub><m:e><m:r><m:t>r</m:t></m:r></m:e><m:sub><m:r><m:t>d,c</m:t></m:r></m:sub></m:sSub>
    <m:r><m:t>      (2.1)</m:t></m:r>
</m:oMath></m:oMathPara>'''

FORMULA_2_2_XML = f'''<m:oMathPara xmlns:m="{NS_M}" xmlns:w="{NS_W}"><m:oMath>
    <m:acc><m:accPr><m:chr m:val="̂"/></m:accPr><m:e><m:r><m:t>p</m:t></m:r></m:e></m:acc>
    <m:r><m:t>(x) = </m:t></m:r>
    <m:f><m:num><m:r><m:t>1</m:t></m:r></m:num><m:den><m:r><m:t>4</m:t></m:r></m:den></m:f>
    <m:nary>
      <m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="undOvr"/></m:naryPr>
      <m:sub><m:r><m:t>b=1</m:t></m:r></m:sub>
      <m:sup><m:r><m:t>4</m:t></m:r></m:sup>
      <m:e>
        <m:sSub><m:e><m:r><m:t>p</m:t></m:r></m:e><m:sub><m:r><m:t>θ</m:t></m:r></m:sub></m:sSub>
        <m:r><m:t>(y = 1 | x, </m:t></m:r>
        <m:sSubSup><m:e><m:r><m:t>D</m:t></m:r></m:e><m:sub><m:r><m:t>context</m:t></m:r></m:sub><m:sup><m:r><m:t>(b)</m:t></m:r></m:sup></m:sSubSup>
        <m:r><m:t>)</m:t></m:r>
      </m:e>
    </m:nary>
    <m:r><m:t>;    </m:t></m:r>
    <m:acc><m:accPr><m:chr m:val="̂"/></m:accPr><m:e><m:r><m:t>σ</m:t></m:r></m:e></m:acc>
    <m:r><m:t>(x) = </m:t></m:r>
    <m:rad>
      <m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/>
      <m:e>
        <m:f><m:num><m:r><m:t>1</m:t></m:r></m:num><m:den><m:r><m:t>3</m:t></m:r></m:den></m:f>
        <m:nary>
          <m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="undOvr"/></m:naryPr>
          <m:sub><m:r><m:t>b=1</m:t></m:r></m:sub>
          <m:sup><m:r><m:t>4</m:t></m:r></m:sup>
          <m:e>
            <m:r><m:t>(</m:t></m:r>
            <m:sSub><m:e><m:r><m:t>p</m:t></m:r></m:e><m:sub><m:r><m:t>θ</m:t></m:r></m:sub></m:sSub>
            <m:r><m:t>(y = 1 | x, </m:t></m:r>
            <m:sSubSup><m:e><m:r><m:t>D</m:t></m:r></m:e><m:sub><m:r><m:t>context</m:t></m:r></m:sub><m:sup><m:r><m:t>(b)</m:t></m:r></m:sup></m:sSubSup>
            <m:r><m:t>) - </m:t></m:r>
            <m:acc><m:accPr><m:chr m:val="̂"/></m:accPr><m:e><m:r><m:t>p</m:t></m:r></m:e></m:acc>
            <m:r><m:t>(x)</m:t></m:r>
            <m:sSup><m:e><m:r><m:t>)</m:t></m:r></m:e><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup>
          </m:e>
        </m:nary>
      </m:e>
    </m:rad>
    <m:r><m:t>      (2.2)</m:t></m:r>
</m:oMath></m:oMathPara>'''

FORMULA_2_3_XML = f'''<m:oMathPara xmlns:m="{NS_M}" xmlns:w="{NS_W}"><m:oMath>
    <m:r><m:t>S(u) = </m:t></m:r>
    <m:sSub><m:e><m:r><m:t>S</m:t></m:r></m:e><m:sub><m:r><m:t>risk</m:t></m:r></m:sub></m:sSub>
    <m:r><m:t>(u) + </m:t></m:r>
    <m:sSub><m:e><m:r><m:t>S</m:t></m:r></m:e><m:sub><m:r><m:t>exp</m:t></m:r></m:sub></m:sSub>
    <m:r><m:t>(u) + </m:t></m:r>
    <m:sSub><m:e><m:r><m:t>S</m:t></m:r></m:e><m:sub><m:r><m:t>rank</m:t></m:r></m:sub></m:sSub>
    <m:r><m:t>(u) + </m:t></m:r>
    <m:sSub><m:e><m:r><m:t>S</m:t></m:r></m:e><m:sub><m:r><m:t>load</m:t></m:r></m:sub></m:sSub>
    <m:r><m:t>(u)      (2.3)</m:t></m:r>
</m:oMath></m:oMathPara>'''

FORMULA_2_4_XML = f'''<m:oMathPara xmlns:m="{NS_M}" xmlns:w="{NS_W}"><m:oMath>
    <m:sSub><m:e><m:r><m:t>CI</m:t></m:r></m:e><m:sub><m:r><m:t>Wilson</m:t></m:r></m:sub></m:sSub>
    <m:r><m:t> = </m:t></m:r>
    <m:f>
      <m:num>
        <m:acc><m:accPr><m:chr m:val="̂"/></m:accPr><m:e><m:r><m:t>p</m:t></m:r></m:e></m:acc>
        <m:r><m:t> + </m:t></m:r>
        <m:f><m:num><m:sSup><m:e><m:r><m:t>z</m:t></m:r></m:e><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup></m:num><m:den><m:r><m:t>2n</m:t></m:r></m:den></m:f>
        <m:r><m:t> ± z </m:t></m:r>
        <m:rad>
          <m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/>
          <m:e>
            <m:f>
              <m:num>
                <m:acc><m:accPr><m:chr m:val="̂"/></m:accPr><m:e><m:r><m:t>p</m:t></m:r></m:e></m:acc>
                <m:r><m:t>(1 - </m:t></m:r>
                <m:acc><m:accPr><m:chr m:val="̂"/></m:accPr><m:e><m:r><m:t>p</m:t></m:r></m:e></m:acc>
                <m:r><m:t>)</m:t></m:r>
              </m:num>
              <m:den><m:r><m:t>n</m:t></m:r></m:den>
            </m:f>
            <m:r><m:t> + </m:t></m:r>
            <m:f>
              <m:num><m:sSup><m:e><m:r><m:t>z</m:t></m:r></m:e><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup></m:num>
              <m:den><m:r><m:t>4</m:t></m:r><m:sSup><m:e><m:r><m:t>n</m:t></m:r></m:e><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup></m:den>
            </m:f>
          </m:e>
        </m:rad>
      </m:num>
      <m:den>
        <m:r><m:t>1 + </m:t></m:r>
        <m:f><m:num><m:sSup><m:e><m:r><m:t>z</m:t></m:r></m:e><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup></m:num><m:den><m:r><m:t>n</m:t></m:r></m:den></m:f>
      </m:den>
    </m:f>
    <m:r><m:t>      (2.4)</m:t></m:r>
</m:oMath></m:oMathPara>'''

FORMULA_2_5_XML = f'''<m:oMathPara xmlns:m="{NS_M}" xmlns:w="{NS_W}"><m:oMath>
    <m:r><m:t>ECE = </m:t></m:r>
    <m:nary>
      <m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="undOvr"/></m:naryPr>
      <m:sub><m:r><m:t>m=1</m:t></m:r></m:sub>
      <m:sup><m:r><m:t>M</m:t></m:r></m:sup>
      <m:e>
        <m:f>
          <m:num><m:r><m:t>|B</m:t></m:r><m:sSub><m:e><m:r><m:t></m:t></m:r></m:e><m:sub><m:r><m:t>m</m:t></m:r></m:sub></m:sSub><m:r><m:t>|</m:t></m:r></m:num>
          <m:den><m:r><m:t>N</m:t></m:r></m:den>
        </m:f>
        <m:r><m:t> · |acc(B</m:t></m:r><m:sSub><m:e><m:r><m:t></m:t></m:r></m:e><m:sub><m:r><m:t>m</m:t></m:r></m:sub></m:sSub><m:r><m:t>) - conf(B</m:t></m:r><m:sSub><m:e><m:r><m:t></m:t></m:r></m:e><m:sub><m:r><m:t>m</m:t></m:r></m:sub></m:sSub><m:r><m:t>)|</m:t></m:r>
      </m:e>
    </m:nary>
    <m:r><m:t>      (2.5)</m:t></m:r>
</m:oMath></m:oMathPara>'''

FORMULA_2_6_XML = f'''<m:oMathPara xmlns:m="{NS_M}" xmlns:w="{NS_W}"><m:oMath>
    <m:r><m:t>PSI = </m:t></m:r>
    <m:nary>
      <m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="undOvr"/></m:naryPr>
      <m:sub><m:r><m:t>i=1</m:t></m:r></m:sub>
      <m:sup><m:r><m:t>K</m:t></m:r></m:sup>
      <m:e>
        <m:r><m:t>(</m:t></m:r><m:sSub><m:e><m:r><m:t>P</m:t></m:r></m:e><m:sub><m:r><m:t>i</m:t></m:r></m:sub></m:sSub><m:r><m:t> - </m:t></m:r><m:sSub><m:e><m:r><m:t>Q</m:t></m:r></m:e><m:sub><m:r><m:t>i</m:t></m:r></m:sub></m:sSub><m:r><m:t>) · ln</m:t></m:r>
        <m:f>
          <m:num><m:sSub><m:e><m:r><m:t>P</m:t></m:r></m:e><m:sub><m:r><m:t>i</m:t></m:r></m:sub></m:sSub></m:num>
          <m:den><m:sSub><m:e><m:r><m:t>Q</m:t></m:r></m:e><m:sub><m:r><m:t>i</m:t></m:r></m:sub></m:sSub></m:den>
        </m:f>
      </m:e>
    </m:nary>
    <m:r><m:t>      (2.6)</m:t></m:r>
</m:oMath></m:oMathPara>'''


def add_omml_formula(doc, omml_xml: str):
    """Chèn công thức toán học chuẩn Word Equation (OMML m:oMathPara)."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.first_line_indent = Cm(0)
    elem = parse_xml(omml_xml.strip())
    p._p.append(elem)
    return p


def add_formula_block(doc, formula_text: str, eq_num: str):
    if formula_text.strip().startswith("<m:oMath"):
        return add_omml_formula(doc, formula_text)
    cleaned_f = clean_text(formula_text)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.first_line_indent = Cm(0)
    
    r1 = p.add_run(cleaned_f)
    r1.italic = True
    r1.font.name = 'Times New Roman'
    r1.font.size = Pt(13)
    r1.font.color.rgb = RGBColor(0, 0, 0)
    if eq_num:
        r2 = p.add_run(f"    ({eq_num})")
        r2.bold = True
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(13)
        r2.font.color.rgb = RGBColor(0, 0, 0)
    return p


def add_styled_table(doc, caption: str, headers: list, rows: list, col_aligns=None, font_size=13):
    """
    Tạo bảng chuẩn theo quy định:
    - Tiêu đề bảng nằm PHÍA TRÊN bảng, in đậm 13 pt, căn giữa
    - Gán style 'CaptionTable' để trường TOC \t "CaptionTable,1" tự động thu thập chuẩn xác 100%
    - Nền mặc định là màu trắng 100%
    - Toàn bộ chữ màu đen (RGB 0, 0, 0)
    - Phông chữ Times New Roman, cỡ 13 pt
    - Thay thế dấu gạch ngang dài thành '-'
    """
    if caption:
        p_cap = doc.add_paragraph(style='CaptionTable')
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_before = Pt(8)
        p_cap.paragraph_format.space_after = Pt(4)
        p_cap.paragraph_format.first_line_indent = Cm(0)

        cleaned = clean_text(caption)
        # Chuẩn hóa format: Bảng <Chương>.<Thứ tự>: <Tên bảng> (tránh lỗi double colon)
        cleaned = re.sub(r'^(Bảng\s+[0-9]+\.[0-9]+)[:\.\s]+\s*', r'\1: ', cleaned)
        
        r_cap = p_cap.add_run(cleaned)
        r_cap.bold = True
        r_cap.font.name = 'Times New Roman'
        r_cap.font.size = Pt(13)
        r_cap.font.color.rgb = RGBColor(0, 0, 0)
        r_cap._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')

    tbl = doc.add_table(rows=1 + len(rows), cols=len(headers))
    tbl.style = 'Table Grid'
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER

    hdr_row = tbl.rows[0]
    set_repeat_table_header(hdr_row)
    for j, h in enumerate(headers):
        cell = hdr_row.cells[j]
        set_cell_bg_white(cell)
        set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        r = p.add_run(clean_text(str(h)))
        r.bold = True
        r.font.name = 'Times New Roman'
        r.font.size = Pt(font_size)
        r.font.color.rgb = RGBColor(0, 0, 0)
        r._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')

    for i, row_data in enumerate(rows):
        row = tbl.rows[i + 1]
        for j, val in enumerate(row_data):
            cell = row.cells[j]
            set_cell_bg_white(cell)
            set_cell_margins(cell, top=70, bottom=70, left=100, right=100)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            if col_aligns and j < len(col_aligns):
                p.alignment = col_aligns[j]
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            
            cleaned_val = clean_text(str(val))
            # Hỗ trợ trích dẫn trong ô bảng
            parts = re.split(r'(\[(?:1[0-5]|[1-9])\])', cleaned_val)
            for part in parts:
                m = re.match(r'^\[(1[0-5]|[1-9])\]$', part)
                if m:
                    ref_idx = m.group(1)
                    link_xml = parse_xml(
                        f'<w:hyperlink {nsdecls("w")} w:anchor="ref_{ref_idx}">'
                        f'<w:r>'
                        f'<w:rPr>'
                        f'<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'
                        f'<w:sz w:val="{int(font_size * 2)}"/>'
                        f'<w:color w:val="000000"/>'
                        f'</w:rPr>'
                        f'<w:t>[{ref_idx}]</w:t>'
                        f'</w:r>'
                        f'</w:hyperlink>'
                    )
                    p._p.append(link_xml)
                else:
                    if part:
                        r = p.add_run(part)
                        r.font.name = 'Times New Roman'
                        r.font.size = Pt(font_size)
                        r.font.color.rgb = RGBColor(0, 0, 0)
                        r._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')

    add_p(doc, "", indent_cm=0, space_after=4)
    return tbl


def add_figure_image(doc, img_path: str, caption: str, width_cm=14.5):
    """
    Chèn ảnh và tên ảnh (caption):
    - Tiêu đề hình nằm PHÍA DƯỚI hình, Times New Roman 12 pt, in nghiêng, chữ đen, căn giữa
    - Gán style 'CaptionFigure' để trường TOC \t "CaptionFigure,1" tự động thu thập chuẩn xác 100%
    """
    if os.path.exists(img_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(8)
        p_img.paragraph_format.space_after = Pt(3)
        run = p_img.add_run()
        run.add_picture(img_path, width=Cm(width_cm))
        
    p_cap = doc.add_paragraph(style='CaptionFigure')
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(2)
    p_cap.paragraph_format.space_after = Pt(10)
    p_cap.paragraph_format.first_line_indent = Cm(0)
    
    cleaned = clean_text(caption)
    # Chuẩn hóa format: Hình <Chương>.<Thứ tự>: <Tên hình> (tránh lỗi double colon)
    cleaned = re.sub(r'^(Hình\s+[0-9]+\.[0-9]+)[:\.\s]+\s*', r'\1: ', cleaned)
    
    r_cap = p_cap.add_run(cleaned)
    r_cap.italic = True
    r_cap.font.name = 'Times New Roman'
    r_cap.font.size = Pt(12)
    r_cap.font.color.rgb = RGBColor(0, 0, 0)
    r_cap._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    return p_cap


def add_toc_field(doc):
    """Chèn trường Mục lục tự động Word TOC chuẩn OpenXML."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.first_line_indent = Cm(0)
    
    r_b = p.add_run()
    r_b._r.append(parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="begin"/>'))
    r_i = p.add_run()
    r_i._r.append(parse_xml(f'<w:instrText {nsdecls("w")} xml:space="preserve"> TOC \\o "1-3" \\h \\z \\u </w:instrText>'))
    r_s = p.add_run()
    r_s._r.append(parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="separate"/>'))
    r_e = p.add_run()
    r_e._r.append(parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="end"/>'))


FIGURE_ITEMS = [
    ("Hình 1.1", "Sơ đồ UseCase nghiệp vụ tổng thể của hệ thống trên 4 nhóm tác nhân RBAC", "1"),
    ("Hình 1.2", "Sơ đồ hoạt động (Activity Diagram) quy trình giao việc AI và phê duyệt 3 cấp", "3"),
    ("Hình 1.3", "Sơ đồ tuần tự (Sequence Diagram) nghiệp vụ giao việc, trích xuất 58 đặc trưng và dự báo TabPFN v2", "4"),
    ("Hình 1.4", "Sơ đồ Use Case hệ thống: Phân hệ Quản lý người dùng, Xác thực JWT và Phân quyền RBAC 4 phạm vi", "5"),
    ("Hình 1.5", "Sơ đồ Use Case hệ thống: Phân hệ Kế hoạch năm và Định mức 270 giờ chuẩn Excel", "6"),
    ("Hình 1.6", "Sơ đồ Use Case hệ thống: Phân hệ Khởi tạo công việc và Phân công nhóm (Cưỡng chế 1 Trưởng nhóm)", "7"),
    ("Hình 1.7", "Sơ đồ Use Case hệ thống: Phân hệ Dự báo rủi ro trễ hạn và Gợi ý nhân sự AI (TabPFN v2)", "8"),
    ("Hình 1.8", "Sơ đồ Use Case hệ thống: Phân hệ Cập nhật tiến độ, Nộp minh chứng và Phê duyệt 3 cấp", "9"),
    ("Hình 1.9", "Sơ đồ Use Case hệ thống: Phân hệ Giám sát MLOps Mức 2 và Học tiếp định kỳ có rào chắn", "10"),
    ("Hình 1.10", "Sơ đồ lớp ở mức phân tích (Boundary - Control - Entity)", "11"),
    ("Hình 1.11", "Sơ đồ lớp mức thiết kế - Lược đồ 17 bảng cơ sở dữ liệu quan hệ (qlcv.db)", "12"),
    ("Hình 4.1", "Đường cong ROC và Precision-Recall của 6 mô hình tại thời điểm giao việc (Tĩnh - 55 đặc trưng)", "36"),
    ("Hình 4.2", "Đường cong hiệu chuẩn xác suất (Reliability Diagram) kịch bản Tĩnh (55 đặc trưng)", "37"),
    ("Hình 4.3", "Biểu đồ so sánh ROC-AUC kèm khoảng tin cậy 95% của 6 mô hình (Kịch bản Tĩnh)", "37"),
    ("Hình 4.4", "Độ ổn định hiệu chuẩn theo từng quý của tập kiểm tra (Kịch bản Tĩnh)", "38"),
    ("Hình 4.5", "Đường cong ROC và Precision-Recall khi bổ sung tiến độ giữa kỳ (Kịch bản Động - 57 đặc trưng)", "41"),
    ("Hình 4.6", "Đường cong hiệu chuẩn xác suất (Reliability Diagram) kịch bản Động (57 đặc trưng)", "41"),
    ("Hình 4.7", "Biểu đồ so sánh ROC-AUC kèm khoảng tin cậy 95% của 6 mô hình (Kịch bản Động)", "42"),
    ("Hình 4.8", "Độ ổn định hiệu chuẩn theo từng quý của tập kiểm tra (Kịch bản Động)", "42"),
]

TABLE_ITEMS = [
    ("Bảng 1.1", "Cấu trúc 16 cột của Biểu mẫu Kế hoạch công việc năm và Phiếu giao việc chuẩn", "13"),
    ("Bảng 1.2", "Cơ cấu 4 Bộ môn và danh mục quy đổi 270 giờ chuẩn tại Khoa CNTT - HUIT", "15"),
    ("Bảng 2.1", "So sánh quản lý dữ liệu công việc trên Hệ QTCSDL quan hệ (SQL) và Excel", "19"),
    ("Bảng 2.2", "So sánh đặc tính kỹ thuật của 6 phương pháp học máy dự báo rủi ro trễ hạn", "22"),
    ("Bảng 2.3", "Các ngưỡng thống kê của hệ thống Giám sát Mức 2 (Wilson CI, ECE, PSI)", "24"),
    ("Bảng 3.1", "Danh mục đầy đủ 58 trường đặc trưng nhân quả (FEATURE_SCHEMA) và 3 cột lọc trùng", "27"),
    ("Bảng 3.2", "Cấu trúc chi tiết 17 bảng dữ liệu trong CSDL quan hệ (qlcv.db)", "29"),
    ("Bảng 3.3", "Dữ liệu mẫu các bảng Tổ chức, 18 Tài khoản và Ma trận Phân quyền RBAC (4 phạm vi)", "32"),
    ("Bảng 4.1", "Phân bố quy mô và tỷ lệ trễ hạn của 3 tập Train / Validation / Test (80.000 dòng)", "35"),
    ("Bảng 4.2", "Kết quả đối sánh 6 phương pháp tại thời điểm giao việc (55 đặc trưng tĩnh)", "35"),
    ("Bảng 4.3", "Tác động của ngưỡng cảnh báo (0,23; 0,52) trên mô hình TabPFN v2 (Kịch bản tĩnh)", "39"),
    ("Bảng 4.4", "So sánh hiệu năng giữa kịch bản Tĩnh (55 đặc trưng) và Động (57 đặc trưng)", "40"),
    ("Bảng 4.5", "Kết quả thực nghiệm 5 kịch bản vận hành của khung Học tiếp MLOps có rào chắn", "44"),
    ("Bảng 4.6", "Kết quả đo kiểm trực tiếp dịch vụ TabPFN v2 thật (CPU) trên 3 ca chuẩn", "46"),
    ("Bảng 4.7", "Kết quả trích xuất 58 đặc trưng và suy luận trên dữ liệu thật trong qlcv.db", "48"),
    ("Bảng 4.8", "Tổng hợp kết quả chạy 31/31 bài kiểm thử tự động có mã nguồn trong dự án", "49"),
]


def add_figure_list(doc, figure_items=None):
    """
    Tạo Danh mục hình ảnh tự động chuẩn Microsoft Word qua Style Mapping:
    - Lệnh trường: TOC \\h \\z \\t "CaptionFigure,1" \\* MERGEFORMAT
    - KHÔNG dùng bảng (<w:tbl>)
    - Căn chỉnh lề phải 16 cm với dấu chấm dẫn (dot leader)
    - Phông chữ Times New Roman, cỡ 13 pt, toàn bộ chữ màu đen
    - Đảm bảo 100% không bao giờ bị lỗi encoding tiếng Việt và không bị xóa trắng khi cập nhật
    """
    items = figure_items if figure_items is not None else FIGURE_ITEMS
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(6)
    p_title.paragraph_format.space_after = Pt(14)
    p_title.paragraph_format.first_line_indent = Cm(0)
    r_title = p_title.add_run("DANH MỤC HÌNH ẢNH")
    r_title.bold = True
    r_title.font.name = "Times New Roman"
    r_title.font.size = Pt(15)
    r_title.font.color.rgb = RGBColor(0, 0, 0)
    set_outline_level(p_title, 0)

    # Thẻ mở trường tự động TOC \h \z \t "CaptionFigure,1" chuẩn Word
    p_start = doc.add_paragraph()
    p_start.paragraph_format.space_before = Pt(0)
    p_start.paragraph_format.space_after = Pt(0)
    p_start.paragraph_format.first_line_indent = Cm(0)
    
    r_b = p_start.add_run()
    r_b._r.append(parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="begin"/>'))
    r_i = p_start.add_run()
    r_i._r.append(parse_xml(f'<w:instrText {nsdecls("w")} xml:space="preserve"> TOC \\h \\z \\t "CaptionFigure,1" \\* MERGEFORMAT </w:instrText>'))
    r_s = p_start.add_run()
    r_s._r.append(parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="separate"/>'))

    for code, caption, page_num in items:
        p_item = doc.add_paragraph()
        p_item.paragraph_format.tab_stops.add_tab_stop(Cm(16.0), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        p_item.paragraph_format.space_before = Pt(2)
        p_item.paragraph_format.space_after = Pt(2)
        p_item.paragraph_format.first_line_indent = Cm(0)

        cleaned_title = clean_text(caption)
        # Chuẩn hóa format: Hình <Chương>.<Thứ tự>: <Tên hình> (tránh lỗi double colon)
        if not cleaned_title.startswith("Hình"):
            full_title = f"{code}: {cleaned_title}"
        else:
            full_title = re.sub(r'^(Hình\s+[0-9]+\.[0-9]+)[:\.\s]+\s*', r'\1: ', cleaned_title)

        r_code = p_item.add_run(full_title)
        r_code.font.name = "Times New Roman"
        r_code.font.size = Pt(13)
        r_code.font.color.rgb = RGBColor(0, 0, 0)

        r_tab = p_item.add_run(f"\t{page_num}")
        r_tab.font.name = "Times New Roman"
        r_tab.font.size = Pt(13)
        r_tab.font.color.rgb = RGBColor(0, 0, 0)

    # Thẻ đóng trường tự động
    p_end = doc.add_paragraph()
    p_end.paragraph_format.space_before = Pt(0)
    p_end.paragraph_format.space_after = Pt(6)
    p_end.paragraph_format.first_line_indent = Cm(0)
    r_end = p_end.add_run()
    r_end._r.append(parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="end"/>'))


def add_table_list(doc, table_items=None):
    """
    Tạo Danh mục bảng biểu tự động chuẩn Microsoft Word qua Style Mapping:
    - Lệnh trường: TOC \\h \\z \\t "CaptionTable,1" \\* MERGEFORMAT
    - KHÔNG dùng bảng (<w:tbl>)
    - Căn chỉnh lề phải 16 cm với dấu chấm dẫn (dot leader)
    - Phông chữ Times New Roman, cỡ 13 pt, toàn bộ chữ màu đen
    - Đảm bảo 100% không bao giờ bị lỗi encoding tiếng Việt và không bị xóa trắng khi cập nhật
    """
    items = table_items if table_items is not None else TABLE_ITEMS
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(6)
    p_title.paragraph_format.space_after = Pt(14)
    p_title.paragraph_format.first_line_indent = Cm(0)
    r_title = p_title.add_run("DANH MỤC BẢNG BIỂU")
    r_title.bold = True
    r_title.font.name = "Times New Roman"
    r_title.font.size = Pt(15)
    r_title.font.color.rgb = RGBColor(0, 0, 0)
    set_outline_level(p_title, 0)

    # Thẻ mở trường tự động TOC \h \z \t "CaptionTable,1" chuẩn Word
    p_start = doc.add_paragraph()
    p_start.paragraph_format.space_before = Pt(0)
    p_start.paragraph_format.space_after = Pt(0)
    p_start.paragraph_format.first_line_indent = Cm(0)
    
    r_b = p_start.add_run()
    r_b._r.append(parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="begin"/>'))
    r_i = p_start.add_run()
    r_i._r.append(parse_xml(f'<w:instrText {nsdecls("w")} xml:space="preserve"> TOC \\h \\z \\t "CaptionTable,1" \\* MERGEFORMAT </w:instrText>'))
    r_s = p_start.add_run()
    r_s._r.append(parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="separate"/>'))

    for code, caption, page_num in items:
        p_item = doc.add_paragraph()
        p_item.paragraph_format.tab_stops.add_tab_stop(Cm(16.0), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        p_item.paragraph_format.space_before = Pt(2)
        p_item.paragraph_format.space_after = Pt(2)
        p_item.paragraph_format.first_line_indent = Cm(0)

        cleaned_title = clean_text(caption)
        # Chuẩn hóa format: Bảng <Chương>.<Thứ tự>: <Tên bảng> (tránh lỗi double colon)
        if not cleaned_title.startswith("Bảng"):
            full_title = f"{code}: {cleaned_title}"
        else:
            full_title = re.sub(r'^(Bảng\s+[0-9]+\.[0-9]+)[:\.\s]+\s*', r'\1: ', cleaned_title)

        r_code = p_item.add_run(full_title)
        r_code.font.name = "Times New Roman"
        r_code.font.size = Pt(13)
        r_code.font.color.rgb = RGBColor(0, 0, 0)

        r_tab = p_item.add_run(f"\t{page_num}")
        r_tab.font.name = "Times New Roman"
        r_tab.font.size = Pt(13)
        r_tab.font.color.rgb = RGBColor(0, 0, 0)

    # Thẻ đóng trường tự động
    p_end = doc.add_paragraph()
    p_end.paragraph_format.space_before = Pt(0)
    p_end.paragraph_format.space_after = Pt(6)
    p_end.paragraph_format.first_line_indent = Cm(0)
    r_end = p_end.add_run()
    r_end._r.append(parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="end"/>'))


def add_bookmark(p, bm_id, bm_name):
    """Thêm Bookmark nội bộ vào paragraph."""
    bm_start = parse_xml(f'<w:bookmarkStart {nsdecls("w")} w:id="{bm_id}" w:name="{bm_name}"/>')
    bm_end = parse_xml(f'<w:bookmarkEnd {nsdecls("w")} w:id="{bm_id}"/>')
    p._p.insert(0, bm_start)
    p._p.append(bm_end)
