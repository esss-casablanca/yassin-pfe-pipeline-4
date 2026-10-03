#!/usr/bin/env python3
"""extract_ledger.py — build fidelity_ledger.json from the two final French papers (Pipeline 4, skill p4-01).

Usage:
  python extract_ledger.py --project D03-P01 --review revue_FINAL_FR.docx --empirical article_FINAL_FR.docx \
      --out fidelity_ledger.json [--locale fr] [--text-dump DIR]

What it extracts, per paper (prefix R- for the review, E- for the empirical article):
  numbers     R-N-0001 … every number in the running text, with locale-aware normalisation, unit, role hint, context
  tables      R-T-0001 … every table: label/caption, header, cells, the multiset of normalised numbers
  figures     R-F-0001 … every "Figure n" caption and the numbers it carries
  citations   R-C-0001 … every in-text citation key ([12] expanded from ranges; (Author, 2020)) with its count
  references  R-REF-0012 … every entry of the reference list, verbatim
Claims (kind = "claim") are NOT extracted here: the assistant authors them with the student (see schemas.md).

--text-dump writes <paper>_blocks.json and <paper>.txt so the assistant can read the papers section by section.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p4lib as L  # noqa: E402


def extract_paper(path: str, prefix: str, paper: str, locale: str) -> tuple[list[dict], dict, list[dict]]:
    blocks = L.docx_text_blocks(path)
    items: list[dict] = []
    counters = {"N": 0, "T": 0, "F": 0, "C": 0, "REF": 0}

    def nid(kind: str) -> str:
        counters[kind] += 1
        return f"{prefix}-{kind}-{counters[kind]:04d}"

    in_refs = False
    ref_index = 0
    citation_counts: dict[str, int] = {}
    pending_table_label: str | None = None
    pending_table_caption: str | None = None
    para_index = 0

    for i, b in enumerate(blocks):
        if b["kind"] == "heading":
            in_refs = bool(L.HEADING_REFS.match(b["text"]))
            if L.HEADING_ANNEX.match(b["text"]):
                in_refs = False
            continue

        if b["kind"] == "paragraph":
            para_index += 1
            text = b["text"]
            if in_refs:
                ref_index += 1
                m = re.match(r"^\s*(?:\[?(\d{1,3})\]?[.)]?\s+)(.*)$", text, re.S)
                idx = int(m.group(1)) if m else ref_index
                body = (m.group(2) if m else text).strip()
                doi = None
                dm = re.search(r"10\.\d{4,9}/[^\s\"<>]+", body)
                if dm:
                    doi = dm.group(0).rstrip(".;,")
                items.append({"id": nid("REF"), "paper": paper, "kind": "reference", "index": idx,
                              "text": body, "doi": doi, "extracted_by": "script"})
                continue

            # captions
            tm = L.TABLE_LABEL.match(text)
            if tm:
                pending_table_label = f"{tm.group(1).capitalize()} {tm.group(2)}"
                pending_table_caption = text.strip()
            fm = L.FIGURE_LABEL.match(text)
            if fm:
                nums = [h.normalized for h in L.find_numbers(text, locale)]
                # drop the figure's own number
                if nums and nums[0] == L.normalize_number(fm.group(2), locale):
                    nums = nums[1:]
                items.append({"id": nid("F"), "paper": paper, "kind": "figure",
                              "label": f"Figure {fm.group(2)}", "caption": text.strip(),
                              "values_in_caption": nums, "section": b["section"], "extracted_by": "script"})

            # citations
            for k, c in L.find_citations(text).items():
                citation_counts[k] = citation_counts.get(k, 0) + c

            # numbers (skip the caption's own label number)
            hits = L.find_numbers(text, locale)
            skip_first = bool(tm or fm)
            for j, h in enumerate(hits):
                if skip_first and j == 0:
                    continue
                items.append({"id": nid("N"), "paper": paper, "kind": "number", "section": b["section"],
                              "paragraph_index": para_index, "raw": h.raw, "normalized": h.normalized,
                              "unit": h.unit, "role_hint": h.role_hint, "context": h.context.strip(),
                              "extracted_by": "script"})
            continue

        if b["kind"] == "table":
            cells = b["cells"]
            label = pending_table_label
            caption = pending_table_caption
            if label is None:
                # look ahead one block for a caption placed under the table
                nxt = blocks[i + 1] if i + 1 < len(blocks) else None
                if nxt and nxt["kind"] == "paragraph":
                    tm = L.TABLE_LABEL.match(nxt["text"])
                    if tm:
                        label = f"{tm.group(1).capitalize()} {tm.group(2)}"
                        caption = nxt["text"].strip()
            nums: list[str] = []
            for row in cells:
                for cell in row:
                    nums.extend(h.normalized for h in L.find_numbers(cell, locale))
            items.append({"id": nid("T"), "paper": paper, "kind": "table", "label": label or f"(table sans légende #{counters['T'] + 1})",
                          "caption": caption, "section": b["section"], "n_rows": len(cells),
                          "n_cols": max((len(r) for r in cells), default=0),
                          "header": cells[0] if cells else [], "cells": cells, "numbers_normalized": nums,
                          "extracted_by": "script"})
            pending_table_label = None
            pending_table_caption = None

    for k in sorted(citation_counts, key=lambda s: (len(s), s)):
        items.append({"id": nid("C"), "paper": paper, "kind": "citation", "key": k,
                      "occurrences": citation_counts[k], "extracted_by": "script"})

    summary = {"numbers": counters["N"], "tables": counters["T"], "figures": counters["F"],
               "citations": counters["C"], "references": counters["REF"], "claims": 0}
    return items, summary, blocks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--review", help=".docx of the final French review article")
    ap.add_argument("--empirical", help=".docx of the final French empirical article")
    ap.add_argument("--locale", default="fr", choices=["fr", "en", "ar"])
    ap.add_argument("--out", default="fidelity_ledger.json")
    ap.add_argument("--text-dump", help="directory to write <paper>_blocks.json and <paper>.txt")
    a = ap.parse_args()
    if not a.review and not a.empirical:
        ap.error("give --review and/or --empirical")

    ledger = {"ledger_version": "1.0", "project_id": a.project,
              "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
              "sources": {}, "items": [], "summary": {}}
    for paper, prefix, path in (("review", "R", a.review), ("empirical", "E", a.empirical)):
        if not path:
            continue
        items, summary, blocks = extract_paper(path, prefix, paper, a.locale)
        ledger["sources"][paper] = {"file": os.path.basename(path), "sha256": L.sha256_file(path), "locale": a.locale}
        ledger["items"].extend(items)
        ledger["summary"][paper] = summary
        if a.text_dump:
            os.makedirs(a.text_dump, exist_ok=True)
            L.save_json(blocks, os.path.join(a.text_dump, f"{paper}_blocks.json"))
            with open(os.path.join(a.text_dump, f"{paper}.txt"), "w", encoding="utf-8") as f:
                for b in blocks:
                    if b["kind"] == "heading":
                        f.write(f"\n## {b['text']}\n\n")
                    else:
                        f.write(b["text"] + "\n\n")
        print(f"{paper:9s} {os.path.basename(path)}: " + ", ".join(f"{k}={v}" for k, v in summary.items() if k != 'claims'))
    L.save_json(ledger, a.out)
    print(f"ledger written: {a.out} ({len(ledger['items'])} items)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
