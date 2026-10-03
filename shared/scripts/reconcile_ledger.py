#!/usr/bin/env python3
"""reconcile_ledger.py — check a Pipeline-4 deliverable against fidelity_ledger.json.

Two modes:

  translation  (skills p4-03 / p4-04 / p4-05) — a translated paper must carry EVERY ledger item of its paper:
      python reconcile_ledger.py translation --ledger fidelity_ledger.json --paper review \
          --target review_article_EN.docx --locale en --out recon_review_EN.json
      Reports: numbers missing / under-represented / introduced, table-by-table number multisets,
      references verbatim or not, citation keys and counts. Markdown (.md) targets are accepted too.

  deck  (skill p4-02) — a deck may condense but may not INTRODUCE a number absent from the two papers:
      python reconcile_ledger.py deck --ledger fidelity_ledger.json --target soutenance_deck_V1.pptx \
          --locale fr --out recon_deck.json [--ignore 2025/2026]
      Reports: numbers on slides not in the ledger (introduced), per-slide detail, ledger coverage.

Exit code 0 = no Major finding, 1 = Major findings present (missing/altered/introduced), 2 = usage error.
Hedge words and claim strength are NOT checked here — the assistant does that against the claim register.
"""
from __future__ import annotations

import argparse
import difflib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p4lib as L  # noqa: E402

IGNORED_ROLES = {"numbering", "label_ref"}


def load_target_text(path: str, locale: str) -> tuple[str, list[list[list[str]]], list[str]]:
    """Return (plain text, tables, reference paragraphs) of a .docx or .md target."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        blocks = L.docx_text_blocks(path)
    elif ext in (".md", ".txt"):
        blocks = md_blocks(open(path, encoding="utf-8").read())
    else:
        raise SystemExit(f"unsupported target: {path}")
    text_parts, body_parts, tables, refs = [], [], [], []
    in_refs = False
    for b in blocks:
        if b["kind"] == "heading":
            in_refs = bool(L.HEADING_REFS.match(b["text"]))
            if L.HEADING_ANNEX.match(b["text"]):
                in_refs = False
            text_parts.append(b["text"])
        elif b["kind"] == "table":
            tables.append(b["cells"])
            text_parts.append(b["text"])
            body_parts.append(b["text"])
        else:
            text_parts.append(b["text"])
            if in_refs:
                refs.append(b["text"].strip())
            else:
                # blank table/figure labels so "Tableau 1" / "الجدول 1" is not read as a statistic
                t = b["text"]
                t = L.TABLE_LABEL.sub(lambda m: " " * len(m.group(0)), t)
                t = L.FIGURE_LABEL.sub(lambda m: " " * len(m.group(0)), t)
                body_parts.append(t)
    return "\n".join(text_parts), tables, refs, "\n".join(body_parts)


def md_blocks(src: str) -> list[dict]:
    blocks: list[dict] = []
    lines = src.splitlines()
    i = 0
    section = ""
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            i += 1
            continue
        if ln.startswith("#"):
            section = ln.lstrip("#").strip()
            blocks.append({"kind": "heading", "text": section, "section": section})
            i += 1
            continue
        if ln.lstrip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c or "--") for c in row):
                    rows.append(row)
                i += 1
            blocks.append({"kind": "table", "cells": rows, "section": section,
                           "text": "\n".join("\t".join(r) for r in rows)})
            continue
        if re.match(r"^\s*([-*•]|\d+[.)])\s+", ln):  # list item (reference entries are usually numbered)
            blocks.append({"kind": "paragraph", "text": ln.strip(), "section": section})
            i += 1
            continue
        para = [ln]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith("#") and not lines[i].lstrip().startswith("|") \
                and not re.match(r"^\s*([-*•]|\d+[.)])\s+", lines[i]):
            para.append(lines[i].rstrip())
            i += 1
        blocks.append({"kind": "paragraph", "text": "\n".join(para), "section": section})
    return blocks


def ref_similarity(a: str, b: str) -> float:
    na = re.sub(r"\s+", " ", re.sub(r"^\s*\[?\d{1,3}\]?[.)]?\s+", "", a)).strip().lower()
    nb = re.sub(r"\s+", " ", re.sub(r"^\s*\[?\d{1,3}\]?[.)]?\s+", "", b)).strip().lower()
    return difflib.SequenceMatcher(None, na, nb).ratio()


def reconcile_translation(ledger: dict, paper: str, target: str, locale: str) -> dict:
    text, tables, refs, body_text = load_target_text(target, locale)
    items = [it for it in ledger["items"] if it["paper"] == paper]
    tgt_nums = L.number_multiset(body_text, locale)  # body + tables, without the reference list
    # expected multiset from running-text numbers (tables are checked separately)
    expected: dict[str, int] = {}
    examples: dict[str, dict] = {}
    spelled_out: list[dict] = []
    for it in items:
        if it["kind"] != "number" or it.get("role_hint") in IGNORED_ROLES:
            continue
        if it.get("role_hint") == "spelled_out":
            # written in words in the source (e.g. "Vingt et une"): may legitimately be in words in the target too
            spelled_out.append({"id": it["id"], "raw": it["raw"], "normalized": it["normalized"],
                                "found_as_digits": tgt_nums.get(it["normalized"], 0) > 0, "context": it.get("context", "")[:160]})
            continue
        expected[it["normalized"]] = expected.get(it["normalized"], 0) + 1
        examples.setdefault(it["normalized"], it)
    # table numbers also live in the target text (python-docx tables are included in text); count them too
    tbl_expected: dict[str, int] = {}
    for it in items:
        if it["kind"] == "table":
            for n in it["numbers_normalized"]:
                tbl_expected[n] = tbl_expected.get(n, 0) + 1
    total_expected = {k: expected.get(k, 0) + tbl_expected.get(k, 0) for k in set(expected) | set(tbl_expected)}

    missing, under, matched = [], [], 0
    for n, c in sorted(total_expected.items(), key=lambda kv: kv[0]):
        found = tgt_nums.get(n, 0)
        if found == 0:
            ex = examples.get(n, {})
            missing.append({"normalized": n, "expected": c, "found": 0, "example_id": ex.get("id"), "context": ex.get("context", "")[:160]})
        elif found < c:
            ex = examples.get(n, {})
            under.append({"normalized": n, "expected": c, "found": found, "example_id": ex.get("id"), "context": ex.get("context", "")[:160]})
            matched += 1
        else:
            matched += 1
    introduced = []
    ledger_all = {it["normalized"] for it in ledger["items"] if it["kind"] == "number"} | set(tbl_expected) | {
        n for it in ledger["items"] if it["kind"] == "figure" for n in it["values_in_caption"]}
    tgt_hits = L.find_numbers(body_text, locale)  # body only: the reference list is checked verbatim below
    seen = set()
    for h in tgt_hits:
        if h.normalized in ledger_all or h.normalized in seen:
            continue
        seen.add(h.normalized)
        introduced.append({"normalized": h.normalized, "raw": h.raw, "context": h.context.strip()[:160]})

    # tables one-to-one by order
    ledger_tables = [it for it in items if it["kind"] == "table"]
    table_report = []
    for k, lt in enumerate(ledger_tables):
        if k < len(tables):
            tgt_nums_t: dict[str, int] = {}
            for row in tables[k]:
                for cell in row:
                    for h in L.find_numbers(cell, locale):
                        tgt_nums_t[h.normalized] = tgt_nums_t.get(h.normalized, 0) + 1
            src_nums_t: dict[str, int] = {}
            for n in lt["numbers_normalized"]:
                src_nums_t[n] = src_nums_t.get(n, 0) + 1
            miss = {n: c - tgt_nums_t.get(n, 0) for n, c in src_nums_t.items() if tgt_nums_t.get(n, 0) < c}
            extra = {n: c - src_nums_t.get(n, 0) for n, c in tgt_nums_t.items() if src_nums_t.get(n, 0) < c}
            table_report.append({"ledger_id": lt["id"], "label": lt["label"], "target_table_index": k + 1,
                                 "rows_src": lt["n_rows"], "rows_tgt": len(tables[k]),
                                 "missing_numbers": miss, "extra_numbers": extra,
                                 "ok": not miss and not extra and lt["n_rows"] == len(tables[k])})
        else:
            table_report.append({"ledger_id": lt["id"], "label": lt["label"], "target_table_index": None, "ok": False,
                                 "missing_numbers": "table absent", "extra_numbers": {}})

    # references verbatim
    ledger_refs = [it for it in items if it["kind"] == "reference"]
    ref_report = []
    for k, lr in enumerate(ledger_refs):
        best, best_sim = None, 0.0
        for cand in refs:
            s = ref_similarity(lr["text"], cand)
            if s > best_sim:
                best, best_sim = cand, s
        ref_report.append({"ledger_id": lr["id"], "index": lr["index"], "similarity": round(best_sim, 3),
                           "verbatim": best_sim >= 0.985, "target_text": (best or "")[:120]})

    # citations
    tgt_cit = L.find_citations(text)
    cit_report = []
    for it in items:
        if it["kind"] == "citation":
            f = tgt_cit.get(it["key"], 0)
            cit_report.append({"key": it["key"], "expected": it["occurrences"], "found": f, "ok": f == it["occurrences"]})

    majors = len(missing) + sum(1 for t in table_report if not t["ok"]) + sum(1 for r in ref_report if not r["verbatim"])
    return {
        "mode": "translation", "paper": paper, "target": os.path.basename(target),
        "target_sha256": L.sha256_file(target) if os.path.exists(target) else None,
        "locale": locale,
        "ledger": {"expected_distinct": len(total_expected), "matched": matched, "missing": missing,
                   "under_represented": under, "introduced": introduced,
                   "spelled_out_to_verify_by_hand": spelled_out},
        "tables": {"expected": len(ledger_tables), "found_in_target": len(tables), "detail": table_report,
                   "mismatches": [t for t in table_report if not t["ok"]]},
        "references": {"expected": len(ledger_refs), "found_in_target": len(refs),
                       "verbatim": sum(1 for r in ref_report if r["verbatim"]),
                       "mismatches": [r for r in ref_report if not r["verbatim"]]},
        "citations": {"checked": len(cit_report), "mismatches": [c for c in cit_report if not c["ok"]]},
        "major_findings": majors,
        "verdict": "attestable (script level)" if majors == 0 else "NOT attestable — resolve Major findings",
    }


def reconcile_deck(ledger: dict, target: str, locale: str, ignore: list[str]) -> dict:
    slides = L.pptx_slide_texts(target, include_notes=False)
    ledger_nums = {it["normalized"] for it in ledger["items"] if it["kind"] == "number"}
    for it in ledger["items"]:
        if it["kind"] == "table":
            ledger_nums.update(it["numbers_normalized"])
        if it["kind"] == "figure":
            ledger_nums.update(it["values_in_caption"])
    ignore_set = set()
    for ig in ignore:
        for h in L.find_numbers(ig, locale):
            ignore_set.add(h.normalized)
    per_slide, introduced, covered = [], [], set()
    for s in slides:
        hits = L.find_numbers(s["text"], locale)
        intro_here = []
        for h in hits:
            if h.normalized in ignore_set:
                continue
            # tolerate small enumerations (1–9) used as list numbering / plan numbering on slides
            if re.fullmatch(r"[1-9]", h.normalized) and h.unit is None and h.role_hint is None:
                continue
            if h.normalized in ledger_nums:
                covered.add(h.normalized)
            else:
                intro_here.append({"raw": h.raw, "normalized": h.normalized, "context": h.context.strip()[:120]})
        for cv in s.get("chart_values", []):
            if cv["normalized"] in ledger_nums:
                covered.add(cv["normalized"])
            else:
                intro_here.append({"raw": cv["normalized"], "normalized": cv["normalized"],
                                   "context": f"chart value — {cv['series']} / {cv['category']}"})
        per_slide.append({"slide": s["slide"], "layout": s["layout"], "numbers": len(hits) + len(s.get("chart_values", [])), "introduced": intro_here})
        for x in intro_here:
            introduced.append({"slide": s["slide"], **x})
    return {
        "mode": "deck", "target": os.path.basename(target), "target_sha256": L.sha256_file(target), "locale": locale,
        "slides": len(slides), "ledger_numbers_distinct": len(ledger_nums), "covered_distinct": len(covered),
        "introduced": introduced, "per_slide": per_slide,
        "major_findings": len(introduced),
        "verdict": "no number introduced (script level)" if not introduced else "NOT lockable — numbers absent from the papers appear on slides",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    t = sub.add_parser("translation")
    t.add_argument("--ledger", required=True)
    t.add_argument("--paper", required=True, choices=["review", "empirical"])
    t.add_argument("--target", required=True)
    t.add_argument("--locale", required=True, choices=["fr", "en", "ar"])
    t.add_argument("--out", required=True)
    d = sub.add_parser("deck")
    d.add_argument("--ledger", required=True)
    d.add_argument("--target", required=True)
    d.add_argument("--locale", default="fr", choices=["fr", "en", "ar"])
    d.add_argument("--ignore", nargs="*", default=[], help="strings whose numbers are tolerated (e.g. the academic year)")
    d.add_argument("--out", required=True)
    a = ap.parse_args()
    ledger = L.load_json(a.ledger)
    if a.mode == "translation":
        rep = reconcile_translation(ledger, a.paper, a.target, a.locale)
        L.save_json(rep, a.out)
        lg = rep["ledger"]
        print(f"[{rep['paper']} → {rep['target']}] numbers: {lg['matched']}/{lg['expected_distinct']} matched, "
              f"{len(lg['missing'])} missing, {len(lg['under_represented'])} under-represented, {len(lg['introduced'])} introduced | "
              f"tables: {rep['tables']['expected'] - len(rep['tables']['mismatches'])}/{rep['tables']['expected']} ok | "
              f"references: {rep['references']['verbatim']}/{rep['references']['expected']} verbatim | "
              f"citations mismatched: {len(rep['citations']['mismatches'])}")
    else:
        rep = reconcile_deck(ledger, a.target, a.locale, a.ignore)
        L.save_json(rep, a.out)
        print(f"[deck {rep['target']}] {rep['slides']} slides; {rep['covered_distinct']} ledger numbers shown; "
              f"{len(rep['introduced'])} numbers introduced")
        for x in rep["introduced"]:
            print(f"   slide {x['slide']}: {x['raw']}  …{x['context']}…")
    print("verdict:", rep["verdict"])
    return 0 if rep["major_findings"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
