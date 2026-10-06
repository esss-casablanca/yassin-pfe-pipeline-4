#!/usr/bin/env python3
"""p4lib — shared helpers for the Pipeline-4 scripts (Python 3.10+, python-docx 1.2, python-pptx 1.0).

Number normalisation is locale-aware:
  fr : thousands separated by (narrow/no-break) spaces, decimal comma   -> "1 248" "12,5"
  en : thousands separated by commas, decimal point                      -> "1,248" "12.5"
  ar : ASCII digits by Pipeline-4 contract, decimal point; Arabic-Indic digits are mapped to ASCII first
A normalised number is a plain string such as "1248", "12.5", "-0.03".

Parser version 2 (plugin v0.2.4) — fixes reported on 2026-10-04 (D15-P04):
  * thousands separators: en/ar also accept no-break / narrow / thin spaces and the Arabic separator U+066C;
    the Arabic decimal separator U+066B is read as a decimal point;
  * bracketed intervals ("IC 95 % [1,3 ; 3,4]", "28 [24–33]") are read as numbers, no longer as citation keys;
  * DOIs and URLs in the running text are ignored;
  * section cross-references ("2.3", "§ 2.3", "القسم 2.3", "2.3.1") are read identically in every locale
    (French accepts a decimal point as a fallback, multi-level numbers are ignored, Arabic section words are labels);
  * a French label followed by a grouped number ("tableau 3 120 femmes") is split into the label and the value.
A ledger built with an older parser must be rebuilt (extract_ledger.py --carry-over) before reconciliation.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field, asdict
from typing import Iterable

PARSER_VERSION = "3"  # bump whenever find_numbers / find_citations change what they return

GROUP_SPACES = "\u00a0\u202f\u2009\u2007 "  # nbsp, narrow nbsp, thin space, figure space, space
EN_GROUP = ",\u00a0\u202f\u2009\u2007\u066c"  # comma, no-break spaces, Arabic thousands separator (not the plain space)
AR_DECIMAL = "\u066b"  # Arabic decimal separator
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
    # decimal comma (French) or, as a fallback, decimal point: "2.3" must read the same in every locale
    return re.compile(
        rf"(?<![\w.,])[-−]?(?:\d{{1,3}}(?:{sp}\d{{3}})+|\d+)(?:[,.]\d+)?(?![\w])"
    )


def _en_pattern() -> re.Pattern:
    g = f"[{EN_GROUP}]"
    return re.compile(rf"(?<![\w.,])[-−]?(?:\d{{1,3}}(?:{g}\d{{3}})+|\d+)(?:[.{AR_DECIMAL}]\d+)?(?![\w])")


def normalize_number(raw: str, locale: str) -> str:
    s = raw.translate(ARABIC_INDIC).replace("−", "-")
    if locale == "fr":
        for ch in GROUP_SPACES:
            s = s.replace(ch, "")
        s = s.replace(",", ".")
    else:  # en / ar
        for ch in EN_GROUP:
            s = s.replace(ch, "")
        s = s.replace(AR_DECIMAL, ".")
    # canonical string: no leading zeros on the integer part; written precision kept (12.50 stays 12.50)
    neg = s.startswith("-")
    s = s.lstrip("-")
    if "." in s:
        ip, fp = s.split(".", 1)
        s = (ip.lstrip("0") or "0") + "." + fp
    else:
        s = s.lstrip("0") or "0"
    return ("-" if neg else "") + s


# ---- things that look like numbers but are not values of the paper -----------------------------------------
URL_DOI = re.compile(r"(?i)(?:https?://|www\.)\S+|\bdoi\s*:\s*\S+|\b10\.\d{4,9}/[^\s\"<>]+")
MULTI_DOT = re.compile(r"(?<![\w.,])\d+(?:\.\d+){2,}(?![\w])")  # 2.3.1 — section / item numbering
LABEL_BEFORE = re.compile(
    r"(?i)(tableau|table|figure|fig\.|الجدول|الشكل|جدول|شكل|composante|component|étape|step|phase|partie|part|"
    r"section|chapitre|chapter|annexe|appendix|objectif|objective|hypoth[èe]se|hypothesis|paragraphe|paragraph|§|"
    r"المكو[نّ]+|الملحق|المرحلة|القسم|الفصل|الجزء|الفقرة|البند|الباب)\s*$")

# ---- bracketed intervals versus numeric citation keys ---------------------------------------------------------
_STAT_ACRONYMS = re.compile(r"(?:\b(?:IC|CI|OR|aOR|ORa|ORaj|RR|aRR|RRa|HR|aHR|RP|PR|IRR|EIQ|IIQ|IQR)\b|95\s*%|±)")
_STAT_WORDS = re.compile(r"(?i)(?:intervalle|interval|interquartile|étendue|\brange\b|m[ée]diane?\b|\bmin(?:imum)?\b|"
                         r"\bmax(?:imum)?\b|فترة\s+الثقة|فاصل\s+الثقة|مجال\s+الثقة|المدى|الوسيط|نسبة\s+الأرجحية)")
_NUMBER_JUST_BEFORE = re.compile(r"(?<![\w.,])(\d+(?:[,.]\d+)?)\s*%?\s*$")


def _stat_context(before: str) -> bool:
    """Statistical vocabulary in the 40 characters before a bracket, within the same clause."""
    w = before[-40:]
    for stop in ("]", ". ", "\n"):
        k = w.rfind(stop)
        if k >= 0:
            w = w[k + len(stop):]
    return bool(_STAT_ACRONYMS.search(w) or _STAT_WORDS.search(w))


def plausible_citation_list(inner: str) -> bool:
    """True when the bracket content reads as a well-formed numeric citation list: integer keys and ranges a–b
    (a < b, span ≤ 20), strictly ascending, never repeated — "1,3-5,7" and "12–15" yes; "52,5–79,5" (52 then 5),
    "2,6–51,3" (span 45) and "30,1–49,5" (30 then 1) no: those are decimal-comma intervals."""
    last = 0
    for part in re.split(r"\s*[,;]\s*", inner.strip()):
        if not part:
            return False
        m = re.fullmatch(r"(\d{1,3})\s*[–—-]\s*(\d{1,3})", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a >= b or b - a > 20:
                return False
        elif re.fullmatch(r"\d{1,3}", part):
            a = b = int(part)
        else:
            return False
        if a <= last:
            return False
        last = b
    return True


def bracket_is_interval(inner: str, before: str) -> bool:
    """True when a bracket matched by CITATION_NUMERIC is a numeric interval (CI, IQR, range), not citation keys.

    Citation keys are positive integers without leading zeros. An interval has two bounds: two decimal-comma
    numbers ("1,3 ; 3,4", "0,8–1,9", "52,5–79,5") or two integers in a statistical context ("médiane 28 [24–33]").
    Parser v3: a decimal-comma pair is an interval when it stands alone (a table cell, the start of a line) or
    when its citation reading is not a well-formed list (see plausible_citation_list); the stat-context, value-
    before and two-decimal cues of v2 still apply."""
    tokens = re.findall(r"\d+", inner)
    if any(t.startswith("0") for t in tokens):          # [0,8–1,9] · [05] : never citation keys
        return True
    parts = [p for p in re.split(r"\s*[;–—-]\s*", inner.strip()) if p]
    if len(parts) != 2:
        return False
    stat = _stat_context(before)
    m = _NUMBER_JUST_BEFORE.search(before)
    after_value = bool(m) and not re.fullmatch(r"(19|20)\d{2}", m.group(1))
    standalone = not before.strip()                      # the bracket is the whole cell or opens the line
    dec = [re.fullmatch(r"\d+,\d+", p) for p in parts]
    if all(dec):
        sep = inner.strip()[len(parts[0]):].strip()[:1]
        if sep == ";":                                    # [1,3 ; 3,4] : French CI typography
            return True
        if stat or after_value or standalone or not plausible_citation_list(inner):
            return True
        return any(len(p.split(",")[1]) >= 2 for p in parts)
    if all(re.fullmatch(r"\d+", p) for p in parts):     # [24–33] : interval only with a statistical cue
        return stat or after_value or not plausible_citation_list(inner)
    return False


def _citation_brackets(text: str):
    """Yield the CITATION_NUMERIC matches that are citation keys (bracketed intervals are skipped)."""
    for m in CITATION_NUMERIC.finditer(text):
        if not bracket_is_interval(m.group(1), text[:m.start()]):
            yield m


def _blank(rx: re.Pattern, s: str) -> str:
    return rx.sub(lambda m: " " * len(m.group(0)), s)


def find_numbers(text: str, locale: str, strip_citations: bool = True) -> list[NumberHit]:
    """Return number hits in display order. Citation keys like [12] are blanked before extraction
    when strip_citations is True so that reference indices are not mistaken for statistics; bracketed
    intervals ([1,3 ; 3,4]) are kept. DOIs, URLs and multi-level section numbers (2.3.1) are ignored."""
    text = nfc(text).translate(ARABIC_INDIC)
    work = _blank(URL_DOI, text)
    work = _blank(MULTI_DOT, work)
    if strip_citations:
        spans = [(m.start(), m.end()) for m in _citation_brackets(work)]
        for a, b in reversed(spans):
            work = work[:a] + " " * (b - a) + work[b:]
    pat = _fr_pattern() if locale == "fr" else _en_pattern()
    hits: list[NumberHit] = []
    pos = 0
    while True:
        m = pat.search(work, pos)
        if not m:
            break
        start, end, raw = m.start(), m.end(), m.group(0)
        before = work[max(0, start - 14): start]
        if locale == "fr" and LABEL_BEFORE.search(before) and re.search(f"[{GROUP_SPACES}]", raw):
            # "tableau 3 120 femmes": the label number is 3, the value 120 is read on the next pass
            raw = re.match(r"[-−]?\d+", raw).group(0)
            end = start + len(raw)
        pos = end
        norm = normalize_number(raw, locale)
        after = work[end: end + 4]
        unit = None
        if re.match(rf"[{GROUP_SPACES}]?[%٪]", after):
            unit = "%"
        role = None
        if re.fullmatch(r"(19|20)\d{2}", norm) and unit is None:
            role = "year"
        if LABEL_BEFORE.search(before):
            role = "label_ref"
        elif re.search(r"(?i)\bp\s*[=<>≤≥]\s*$", before):
            role = "p_value"
        elif re.search(r"(?i)\bn\s*=\s*$", before):
            role = "n"
        ctx = text[max(0, start - 60): end + 60].replace("\n", " ")
        hits.append(NumberHit(raw=raw, normalized=norm, start=start, end=end, unit=unit, role_hint=role, context=ctx))
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
    for m in _citation_brackets(text):
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


def is_md_rule_row(row: list[str]) -> bool:
    """True for a Markdown table rule line (|---|:--:|); an all-empty row is a real (empty) row."""
    cells = [c for c in row if c]
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c) for c in cells)


def nonempty_rows(rows: list[list[str]]) -> int:
    """Number of table rows that carry at least one non-blank cell (spacer rows are not compared)."""
    return sum(1 for r in rows if any(str(c).strip() for c in r))


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
