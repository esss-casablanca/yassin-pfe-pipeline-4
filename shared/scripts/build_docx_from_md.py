#!/usr/bin/env python3
"""build_docx_from_md.py — typeset a translated paper (English or Arabic) from a Markdown subset into .docx,
with true right-to-left layout for Arabic (Pipeline 4, skills p4-03 / p4-04).

Usage:
  python build_docx_from_md.py --md empirical_article_AR.md --lang ar --out empirical_article_AR.docx
  python build_docx_from_md.py --md review_article_EN.md   --lang en --out review_article_EN.docx

Markdown subset understood
  ---                       front matter (optional): title:, authors:, affiliation:, running_title:, date:
  key: value
  ---
  # Title                   (used if no front-matter title)
  ## Heading / ### Sub-heading
  paragraphs (blank-line separated); **bold**, *italic*
  - bullet / 1. numbered
  | a | b |  pipe tables (first row = header; the |---| rule line is skipped)
  ![Figure 1. Caption](figure1.png)   -> picture (if the file exists) + caption; caption only otherwise
  <<<pagebreak>>>

Arabic typesetting (lang = ar): every paragraph gets w:bidi and is RIGHT-aligned (never justified) — only the
title block and the figure captions are centred; Arabic runs get w:rtl
with the complex-script font (Noto Naskh Arabic, Amiri or Arial — whichever the reader's machine has, Word
substitutes); Latin/digit runs stay LTR; tables get w:bidiVisual; the section is RTL; Arabic-Indic digits are
converted to ASCII (Pipeline-4 contract); reference-list entries that are mostly Latin keep LTR reading order but are
right-aligned like the rest of the article.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

import docx
from docx.enum.section import WD_ORIENT  # noqa: F401
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p4lib as L  # noqa: E402

AR_FONTS = {"ar": "Noto Naskh Arabic", "fallback": "Arial"}
LATIN_FONT = {"en": "Times New Roman", "fr": "Times New Roman", "ar": "Times New Roman"}
ARABIC_RANGE = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
HEADING_WORDS = {"ar": {"refs": "المراجع"}, "en": {"refs": "References"}, "fr": {"refs": "Références"}}


# ------------------------------------------------------------------------------------------------
# low-level XML helpers
# ------------------------------------------------------------------------------------------------
def set_paragraph_bidi(p, rtl: bool) -> None:
    pPr = p._p.get_or_add_pPr()
    for el in pPr.findall(qn("w:bidi")):
        pPr.remove(el)
    if rtl:
        bidi = OxmlElement("w:bidi")
        pPr.append(bidi)


def set_run_props(run, rtl: bool, lang: str, size_pt: float | None = None, bold=None, italic=None) -> None:
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:ascii"), LATIN_FONT[lang])
    rFonts.set(qn("w:hAnsi"), LATIN_FONT[lang])
    rFonts.set(qn("w:cs"), AR_FONTS["ar"] if lang == "ar" else LATIN_FONT[lang])
    if size_pt:
        run.font.size = Pt(size_pt)
        szCs = rPr.find(qn("w:szCs"))
        if szCs is None:
            szCs = OxmlElement("w:szCs")
            rPr.append(szCs)
        szCs.set(qn("w:val"), str(int(size_pt * 2)))
    if bold is not None:
        run.bold = bold
        if bold:
            bCs = OxmlElement("w:bCs")
            rPr.append(bCs)
    if italic is not None:
        run.italic = italic
        if italic:
            iCs = OxmlElement("w:iCs")
            rPr.append(iCs)
    for el in rPr.findall(qn("w:rtl")):
        rPr.remove(el)
    if rtl:
        r = OxmlElement("w:rtl")
        rPr.append(r)
    langEl = rPr.find(qn("w:lang"))
    if langEl is None:
        langEl = OxmlElement("w:lang")
        rPr.append(langEl)
    langEl.set(qn("w:val"), {"en": "en-GB", "fr": "fr-FR", "ar": "en-GB"}[lang])
    if lang == "ar":
        langEl.set(qn("w:bidi"), "ar-MA")


def set_table_bidi(table) -> None:
    tblPr = table._tbl.tblPr
    bv = OxmlElement("w:bidiVisual")
    tblPr.append(bv)


def set_section_rtl(section) -> None:
    sectPr = section._sectPr
    bidi = OxmlElement("w:bidi")
    sectPr.append(bidi)


def is_arabic_text(s: str) -> bool:
    return bool(ARABIC_RANGE.search(s))


def mostly_latin(s: str) -> bool:
    ar = len(ARABIC_RANGE.findall(s))
    lat = len(re.findall(r"[A-Za-zÀ-ÿ]", s))
    return lat > ar


# ------------------------------------------------------------------------------------------------
# inline markdown -> runs, split by script so that Latin stays LTR inside Arabic paragraphs
# ------------------------------------------------------------------------------------------------
INLINE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*)")
RANGE_IN_LATIN = re.compile(r"\d\s*[\u2013\u2014\-/:;]\s*\d")


def script_segments(text: str):
    """Split text into (segment, is_arabic) chunks; neutral characters follow the previous chunk."""
    segs: list[list] = []
    cur_ar = None
    for ch in text:
        if ARABIC_RANGE.match(ch):
            ar = True
        elif re.match(r"[A-Za-zÀ-ÿ0-9]", ch):
            ar = False
        else:
            ar = cur_ar
        if segs and (ar == cur_ar or ar is None):
            segs[-1][0] += ch
        else:
            segs.append([ch, bool(ar)])
            cur_ar = ar
    return [(s, a) for s, a in segs]


def add_inline(p, text: str, lang: str, size_pt: float, base_bold=False, base_italic=False) -> None:
    text = text.translate(L.ARABIC_INDIC) if lang == "ar" else text
    for tok in INLINE.split(text):
        if not tok:
            continue
        bold, italic = base_bold, base_italic
        if tok.startswith("**") and tok.endswith("**"):
            tok, bold = tok[2:-2], True
        elif tok.startswith("*") and tok.endswith("*"):
            tok, italic = tok[1:-1], True
        if lang == "ar":
            segs = [list(x) for x in script_segments(tok)]
            for k, (seg, ar) in enumerate(segs):
                if ar or not RANGE_IN_LATIN.search(seg):
                    continue
                # a numeric range / ratio inside an RTL paragraph flips visually (1.10–1.83 → 1.83–1.10);
                # an explicit left-to-right embedding keeps it readable in Word and LibreOffice.
                # v0.2.7: an opening bracket left on the Arabic side ("دراسات [" + "29–33]") moves into the
                # embedding, so the citation reads "[29–33]" as one unit in Word and in the reconciler; the
                # surrounding spaces stay outside it.
                if k > 0 and segs[k - 1][1]:
                    m = re.search(r"([\[(«{]\s*)$", segs[k - 1][0])
                    if m:
                        segs[k - 1][0] = segs[k - 1][0][: m.start()]
                        seg = m.group(1) + seg
                lead = len(seg) - len(seg.lstrip())
                trail = len(seg) - len(seg.rstrip())
                core = seg[lead: len(seg) - trail] if trail else seg[lead:]
                segs[k][0] = seg[:lead] + "\u202a" + core + "\u202c" + (seg[len(seg) - trail:] if trail else "")
            for seg, ar in segs:
                if not seg:
                    continue
                run = p.add_run(seg)
                set_run_props(run, rtl=ar, lang=lang, size_pt=size_pt, bold=bold, italic=italic)
        else:
            run = p.add_run(tok)
            set_run_props(run, rtl=False, lang=lang, size_pt=size_pt, bold=bold, italic=italic)


# ------------------------------------------------------------------------------------------------
# block parsing
# ------------------------------------------------------------------------------------------------
def parse_md(src: str) -> tuple[dict, list[dict]]:
    meta: dict = {}
    lines = src.splitlines()
    i = 0
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            m = re.match(r"^\s*([A-Za-z_]+)\s*:\s*(.*)$", lines[i])
            if m:
                meta[m.group(1).lower()] = m.group(2).strip()
            i += 1
        i += 1
    blocks: list[dict] = []
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            i += 1
            continue
        if ln.strip() == "<<<pagebreak>>>":
            blocks.append({"kind": "pagebreak"})
            i += 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if m:
            blocks.append({"kind": "heading", "level": len(m.group(1)), "text": m.group(2).strip()})
            i += 1
            continue
        m = re.match(r"^!\[(.*?)\]\((.*?)\)\s*$", ln)
        if m:
            blocks.append({"kind": "figure", "caption": m.group(1), "path": m.group(2)})
            i += 1
            continue
        if ln.lstrip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not L.is_md_rule_row(row):  # empty rows are kept (v0.2.4)
                    rows.append(row)
                i += 1
            blocks.append({"kind": "table", "rows": rows})
            continue
        m = re.match(r"^\s*([-*•]|\d+[.)])\s+(.*)$", ln)
        if m:
            items = []
            numbered = bool(re.match(r"\d", m.group(1)))
            while i < len(lines):
                mm = re.match(r"^\s*([-*•]|\d+[.)])\s+(.*)$", lines[i])
                if not mm:
                    break
                items.append(mm.group(2).strip())
                i += 1
            blocks.append({"kind": "list", "numbered": numbered, "items": items})
            continue
        para = [ln.strip()]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,4}\s|!\[|\s*\||\s*([-*•]|\d+[.)])\s|<<<pagebreak>>>)", lines[i]):
            para.append(lines[i].strip())
            i += 1
        blocks.append({"kind": "paragraph", "text": " ".join(para)})
    return meta, blocks


# ------------------------------------------------------------------------------------------------
def build(md_path: str, lang: str, out: str) -> dict:
    src = open(md_path, encoding="utf-8").read()
    meta, blocks = parse_md(src)
    rtl_doc = lang == "ar"
    d = docx.Document()
    sec = d.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(2.5))
    if rtl_doc:
        set_section_rtl(sec)
    normal = d.styles["Normal"]
    normal.font.name = LATIN_FONT[lang]
    normal.font.size = Pt(12)
    normal.element.rPr.rFonts.set(qn("w:cs"), AR_FONTS["ar"] if rtl_doc else LATIN_FONT[lang])
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    stats = {"headings": 0, "paragraphs": 0, "tables": 0, "figures": 0, "lists": 0, "references": 0}
    in_refs = False

    def para(text: str, size=12.0, bold=False, italic=False, align=None, rtl=None, style=None):
        p = d.add_paragraph(style=style) if style else d.add_paragraph()
        use_rtl = rtl_doc if rtl is None else rtl
        set_paragraph_bidi(p, use_rtl)
        if align is not None:
            p.alignment = align
        elif rtl_doc:
            # Arabic article: right-to-left and RIGHT-aligned throughout (never justified); only the title block
            # and the figure captions are centred
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        else:
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        add_inline(p, text, lang, size, bold, italic)
        return p

    # title block
    title = meta.get("title") or next((b["text"] for b in blocks if b["kind"] == "heading" and b["level"] == 1), "")
    if title:
        para(title, size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    for key, size, italic in (("authors", 12, False), ("affiliation", 11, True), ("date", 11, False)):
        if meta.get(key):
            para(meta[key], size=size, italic=italic, align=WD_ALIGN_PARAGRAPH.CENTER)

    for b in blocks:
        k = b["kind"]
        if k == "heading":
            if b["level"] == 1 and b["text"] == title:
                continue
            txt = b["text"]
            in_refs = L.is_refs_heading(txt) or txt.strip() == HEADING_WORDS[lang]["refs"]
            lvl = max(1, min(b["level"], 3))
            p = d.add_heading("", level=lvl)
            set_paragraph_bidi(p, rtl_doc)
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if rtl_doc else WD_ALIGN_PARAGRAPH.LEFT
            add_inline(p, txt, lang, {1: 14, 2: 13, 3: 12}[lvl], base_bold=True)
            for r in p.runs:
                r.font.color.rgb = RGBColor(0x1A, 0x32, 0x60)  # ESSS navy instead of Word's default theme blue
            stats["headings"] += 1
        elif k == "paragraph":
            if in_refs and rtl_doc and mostly_latin(b["text"]):
                # a Latin reference entry keeps left-to-right reading order (otherwise its punctuation is garbled)
                # but is right-aligned like everything else in the Arabic article
                para(b["text"], size=11, align=WD_ALIGN_PARAGRAPH.RIGHT, rtl=False)
                stats["references"] += 1
            elif in_refs:
                para(b["text"], size=11)
                stats["references"] += 1
            else:
                para(b["text"])
                stats["paragraphs"] += 1
        elif k == "list":
            style = "List Number" if b["numbered"] else "List Bullet"
            for it in b["items"]:
                if in_refs and rtl_doc and mostly_latin(it):
                    para(it, size=11, align=WD_ALIGN_PARAGRAPH.RIGHT, rtl=False, style=style)
                    stats["references"] += 1
                else:
                    para(it, style=style, size=11 if in_refs else 12)
                    stats["references" if in_refs else "lists"] += 1
        elif k == "table":
            rows = b["rows"]
            if not rows:
                continue
            ncols = max(len(r) for r in rows)
            t = d.add_table(rows=len(rows), cols=ncols)
            t.style = "Table Grid"
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            if rtl_doc:
                set_table_bidi(t)
            for ri, row in enumerate(rows):
                for ci in range(ncols):
                    cell = t.cell(ri, ci)
                    cell.text = ""
                    p = cell.paragraphs[0]
                    txt = row[ci] if ci < len(row) else ""
                    use_rtl = rtl_doc and is_arabic_text(txt)  # a cell without Arabic text keeps LTR reading order
                    set_paragraph_bidi(p, use_rtl)
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if rtl_doc else WD_ALIGN_PARAGRAPH.LEFT
                    add_inline(p, txt, lang, 10, base_bold=(ri == 0))
            d.add_paragraph()
            stats["tables"] += 1
        elif k == "figure":
            if b["path"] and os.path.exists(b["path"]):
                d.add_picture(b["path"], width=Cm(15))
                d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            para(b["caption"], size=11, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER)
            stats["figures"] += 1
        elif k == "pagebreak":
            d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    d.save(out)
    stats["file"] = os.path.basename(out)
    stats["sha256"] = L.sha256_file(out)
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--md", required=True)
    ap.add_argument("--lang", required=True, choices=["ar", "en", "fr"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    st = build(a.md, a.lang, a.out)
    print(", ".join(f"{k}={v}" for k, v in st.items() if k != "sha256"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
