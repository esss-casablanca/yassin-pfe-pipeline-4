#!/usr/bin/env python3
"""p4lib — shared helpers for the Pipeline-4 scripts (Python 3.10+, python-docx 1.2, python-pptx 1.0).

Number normalisation is locale-aware:
  fr : thousands separated by (narrow/no-break) spaces, decimal comma   -> "1 248" "12,5"
  en : thousands separated by commas, decimal point                      -> "1,248" "12.5"
  ar : ASCII digits by Pipeline-4 contract, decimal point; Arabic-Indic digits are mapped to ASCII first
A normalised number is a plain string such as "1248", "12.5", "-0.03".
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field, asdict
from typing import Iterable

GROUP_SPACES = "     "  # nbsp, narrow nbsp, thin space, figure space, space
ARABIC_INDIC = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
DASHES = "–—−-"  # en dash, em dash, minus, hyphen

CITATION_NUMERIC = re.compile(r"\[(\d{1,3}(?:\s*[,;–—-]\s*\d{1,3})*)\]")
_NAME = r"[A-ZÀ-ÝŒ][\w'’\-À-ÿ]+(?:\s+(?:&|and|et)\s+[A-ZÀ-ÝŒ][\w'’\-À-ÿ]+)*(?:\s+et\s+al\.?)?"
CITATION_AUTHOR_DATE = re.compile(
    rf"\(((?:{_NAME})\s*,?\s*(?:19|20)\d{{2}}[a-z]?(?:\s*;\s*(?:{_NAME})\s*,?\s*(?:19|20)\d{{2}}[a-z]?)*)\)"
)

HEADING_REFS = re.compile(r"^\s*(r[ée]f[ée]rences?(\s+bibliographiques)?|bibliographie|references|liste\s+des\s+r[ée]f[ée]rences|المراجع)\s*:?\s*$", re.I)
HEADING_ANNEX = re.compile(r"^\s*(annexes?|appendix|appendices|الملاحق|supplementary)\b", re.I)
TABLE_LABEL = re.compile(r"^\s*(tableau|table|الجدول|جدول)\s*(\d+[a-z]?)\b", re.I)
FIGURE_LABEL = re.compile(r"^\s*(figure|fig\.|الشكل|شكل)\s*(\d+[a-z]?)\b", re.I)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


# ---------------------------------------------------------------------------------------------
# Number extraction
# ---------------------------------------------------------------------------------------------
@dataclass
class NumberHit:
    raw: str
    normalized: str
    start: int
    end: int
    unit: str | None = None
    role_hint: str | None = None
    context: str = ""


def _fr_pattern() -> re.Pattern:
    sp = f"[{GROUP_SPACES}]"
    return re.compile(
        rf"(?<![\w.,])[-−]?(?:\d{{1,3}}(?:{sp}\d{{3}})+|\d+)(?:,\d+)?(?![\w])"
    )


def _en_pattern() -> re.Pattern:
    return re.compile(r"(?<![\w.,])[-−]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![\w])")


def normalize_number(raw: str, locale: str) -> str:
    s = raw.translate(ARABIC_INDIC).replace("−", "-")
    if locale == "fr":
        for ch in GROUP_SPACES:
            s = s.replace(ch, "")
        s = s.replace(",", ".")
    else:  # en / ar
        s = s.replace(",", "")
    # canonical string: no leading zeros on the integer part; written precision kept (12.50 stays 12.50)
    neg = s.startswith("-")
    s = s.lstrip("-")
    if "." in s:
        ip, fp = s.split(".", 1)
        s = (ip.lstrip("0") or "0") + "." + fp
    else:
        s = s.lstrip("0") or "0"
    return ("-" if neg else "") + s


def find_numbers(text: str, locale: str, strip_citations: bool = True) -> list[NumberHit]:
    """Return number hits in display order. Citation keys like [12] are blanked before extraction
    when strip_citations is True so that reference indices are not mistaken for statistics."""
    text = nfc(text).translate(ARABIC_INDIC)
    work = text
    if strip_citations:
        work = CITATION_NUMERIC.sub(lambda m: " " * len(m.group(0)), work)
    pat = _fr_pattern() if locale == "fr" else _en_pattern()
    hits: list[NumberHit] = []
    for m in pat.finditer(work):
        raw = m.group(0)
        norm = normalize_number(raw, locale)
        after = work[m.end(): m.end() + 4]
        before = work[max(0, m.start() - 12): m.start()]
        unit = None
        if re.match(rf"[{GROUP_SPACES}]?%", after):
            unit = "%"
        role = None
        if re.fullmatch(r"(19|20)\d{2}", norm) and unit is None:
            role = "year"
        if re.search(r"(?i)(tableau|table|figure|fig\.|الجدول|الشكل|جدول|شكل|composante|component|étape|step|phase|partie|part|"
                     r"section|chapitre|chapter|annexe|appendix|objectif|objective|hypoth[èe]se|hypothesis|المكو[نّ]+|الملحق|المرحلة)\s*$", before):
            role = "label_ref"
        elif re.search(r"(?i)\bp\s*[=<>≤≥]\s*$", before):
            role = "p_value"
        elif re.search(r"(?i)\bn\s*=\s*$", before):
            role = "n"
        ctx = text[max(0, m.start() - 60): m.end() + 60].replace("\n", " ")
        hits.append(NumberHit(raw=raw, normalized=norm, start=m.start(), end=m.end(), unit=unit, role_hint=role, context=ctx))
    return hits


def number_multiset(text: str, locale: str, strip_citations: bool = True) -> dict[str, int]:
    out: dict[str, int] = {}
    for h in find_numbers(text, locale, strip_citations):
        out[h.normalized] = out.get(h.normalized, 0) + 1
    return out


# ---------------------------------------------------------------------------------------------
# Citations
# ---------------------------------------------------------------------------------------------
def expand_numeric_keys(inner: str) -> list[str]:
    keys: list[str] = []
    for part in re.split(r"\s*[,;]\s*", inner):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d{1,3})\s*[–—-]\s*(\d{1,3})", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a <= b and b - a < 60:
                keys.extend(str(i) for i in range(a, b + 1))
                continue
        if re.fullmatch(r"\d{1,3}", part):
            keys.append(part)
    return keys


def find_citations(text: str) -> dict[str, int]:
    text = nfc(text)
    counts: dict[str, int] = {}
    for m in CITATION_NUMERIC.finditer(text):
        for k in expand_numeric_keys(m.group(1)):
            key = f"[{k}]"
            counts[key] = counts.get(key, 0) + 1
    for m in CITATION_AUTHOR_DATE.finditer(text):
        for part in re.split(r"\s*;\s*", m.group(1)):
            key = "(" + re.sub(r"\s+", " ", part.strip()) + ")"
            counts[key] = counts.get(key, 0) + 1
    return counts


# ---------------------------------------------------------------------------------------------
# Document walking (python-docx)
# ---------------------------------------------------------------------------------------------
def iter_block_items(doc):
    """Yield ('p', Paragraph) and ('t', Table) in body order."""
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    body = doc.element.body
    for child in body.iterchildren():
        tag = child.tag.rsplit('}', 1)[-1]
        if tag == "p":
            yield "p", Paragraph(child, doc)
        elif tag == "tbl":
            yield "t", Table(child, doc)


def is_heading(par) -> bool:
    name = (par.style.name if par.style is not None else "") or ""
    if name.lower().startswith(("heading", "titre", "title")):
        return True
    txt = par.text.strip()
    if not txt or len(txt) > 90:
        return False
    runs = [r for r in par.runs if r.text.strip()]
    if runs and all(r.bold for r in runs) and not txt.endswith((".", ";", ",")):
        return True
    return False


def docx_text_blocks(path: str) -> list[dict]:
    """Flatten a .docx into ordered blocks: {'kind': 'heading'|'paragraph'|'table', 'text', 'section', 'cells'?}."""
    import docx
    doc = docx.Document(path)
    blocks: list[dict] = []
    section = ""
    for kind, item in iter_block_items(doc):
        if kind == "p":
            txt = nfc(item.text)
            if not txt.strip():
                continue
            if is_heading(item):
                section = txt.strip()
                blocks.append({"kind": "heading", "text": txt.strip(), "section": section, "style": item.style.name if item.style else ""})
            else:
                blocks.append({"kind": "paragraph", "text": txt, "section": section})
        else:
            cells = []
            for row in item.rows:
                cells.append([nfc(c.text).strip() for c in row.cells])
            blocks.append({"kind": "table", "text": "\n".join("\t".join(r) for r in cells), "section": section, "cells": cells})
    return blocks


def docx_plain_text(path: str) -> str:
    return "\n".join(b["text"] for b in docx_text_blocks(path))


# ---------------------------------------------------------------------------------------------
# PPTX reading
# ---------------------------------------------------------------------------------------------
def pptx_slide_texts(path: str, include_notes: bool = False) -> list[dict]:
    from pptx import Presentation
    from pptx.util import Pt  # noqa: F401
    prs = Presentation(path)
    out = []
    for idx, slide in enumerate(prs.slides, 1):
        texts: list[str] = []
        tables: list[list[list[str]]] = []
        chart_values: list[dict] = []
        for shape in slide.shapes:
            if shape.is_placeholder and shape.placeholder_format.type is not None and \
                    str(shape.placeholder_format.type).startswith(("SLIDE_NUMBER", "DATE", "FOOTER")):
                continue
            if shape.has_text_frame:
                t = nfc(shape.text_frame.text)
                if t.strip():
                    texts.append(t)
            if getattr(shape, "has_table", False) and shape.has_table:
                rows = [[nfc(c.text).strip() for c in r.cells] for r in shape.table.rows]
                tables.append(rows)
                texts.append("\n".join("\t".join(r) for r in rows))
            if getattr(shape, "has_chart", False) and shape.has_chart:
                try:
                    ch = shape.chart
                    cats = [str(c) for c in ch.plots[0].categories]
                    for s in ch.plots[0].series:
                        for c, v in zip(cats, s.values):
                            if v is None:
                                continue
                            chart_values.append({"series": s.name or "", "category": c,
                                                 "normalized": normalize_number(repr(float(v)).rstrip("0").rstrip(".") if isinstance(v, float) else str(v), "en")})
                        texts.append("CHART " + (s.name or "") + ": " + ", ".join(cats))
                except Exception:
                    pass
        notes = ""
        if include_notes and slide.has_notes_slide:
            notes = nfc(slide.notes_slide.notes_text_frame.text)
        out.append({"slide": idx, "layout": slide.slide_layout.name, "text": "\n".join(texts), "tables": tables,
                    "chart_values": chart_values, "notes": notes})
    return out


def save_json(obj, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
