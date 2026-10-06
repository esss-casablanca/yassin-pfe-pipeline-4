#!/usr/bin/env python3
"""extract_ledger.py — build fidelity_ledger.json from the two final French papers (Pipeline 4, skill p4-01).

Usage:
  python extract_ledger.py --project D03-P01 --review revue_FINAL_FR.docx --empirical article_FINAL_FR.docx \
      --out fidelity_ledger.json [--locale fr] [--review-locale fr] [--empirical-locale en] [--text-dump DIR]

What it extracts, per paper (prefix R- for the review, E- for the empirical article):
  numbers     R-N-0001 … every number in the running text, with locale-aware normalisation, unit, role hint, context
  tables      R-T-0001 … every table: label/caption, header, cells, the multiset of normalised numbers
  figures     R-F-0001 … every "Figure n" caption and the numbers it carries
  citations   R-C-0001 … every in-text citation key ([12] expanded from ranges; (Author, 2020)) with its count
  references  R-REF-0012 … every entry of the reference list, verbatim
Claims (kind = "claim") are NOT extracted here: the assistant authors them with the student (see schemas.md).

--text-dump writes <paper>_blocks.json and <paper>.txt so the assistant can read the papers section by section.

--review-locale / --empirical-locale (v0.2.5) override --locale for one paper: a review written in French and an
empirical article deposited in English are read each with their own number conventions (decimal comma vs point,
thousands separators). The locale of each source is recorded in the ledger's `sources` block.

--carry-over OLD_LEDGER (v0.2.4) rebuilds a ledger made with an older number parser without losing the work done
with the student: every item of the old ledger that was not extracted by the script (the confirmed claim register,
numbers written in words) is kept, and its links to script items are remapped to the new ids. Links that cannot be
remapped are listed in the item (carry_over_unmapped_links) and in the ledger's carry_over report: re-link them by
hand with the student before going on.
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import os
import re
import sys
from collections import defaultdict

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


def carry_over(old: dict, new_items: list[dict]) -> tuple[list[dict], dict]:
    """Keep the assistant-authored items of an older ledger and remap their links to the new script ids."""
    old_items = old.get("items", [])
    old_by_id = {it["id"]: it for it in old_items}
    keep = [dict(it) for it in old_items if it.get("extracted_by") != "script"]

    by_para_raw: dict[tuple, list[str]] = defaultdict(list)
    by_para: dict[tuple, list[dict]] = defaultdict(list)
    tables_new: dict[str, list[dict]] = defaultdict(list)
    simple_new: dict[tuple, str] = {}
    for it in new_items:
        if it["kind"] == "number":
            by_para_raw[(it["paper"], it.get("paragraph_index"), it["raw"])].append(it["id"])
            by_para[(it["paper"], it.get("paragraph_index"))].append(it)
        elif it["kind"] == "table":
            tables_new[it["paper"]].append(it)
        elif it["kind"] == "figure":
            simple_new[(it["paper"], "figure", it["label"])] = it["id"]
        elif it["kind"] == "citation":
            simple_new[(it["paper"], "citation", it["key"])] = it["id"]
        elif it["kind"] == "reference":
            simple_new[(it["paper"], "reference", it["index"])] = it["id"]

    rank: dict[str, int] = {}
    seen: dict[tuple, int] = defaultdict(int)
    old_table_pos: dict[str, int] = {}
    tcount: dict[str, int] = defaultdict(int)
    for it in old_items:
        if it.get("extracted_by") != "script":
            continue
        if it["kind"] == "number":
            key = (it["paper"], it.get("paragraph_index"), it["raw"])
            rank[it["id"]] = seen[key]
            seen[key] += 1
        elif it["kind"] == "table":
            old_table_pos[it["id"]] = tcount[it["paper"]]
            tcount[it["paper"]] += 1

    def map_id(oid: str) -> str | None:
        o = old_by_id.get(oid)
        if o is None:
            return None
        if o.get("extracted_by") != "script":
            return oid
        k = o["kind"]
        if k == "number":
            ids = by_para_raw.get((o["paper"], o.get("paragraph_index"), o["raw"]), [])
            r = rank.get(oid, 0)
            if r < len(ids):
                return ids[r]
            cands = by_para.get((o["paper"], o.get("paragraph_index")), [])
            same = [c for c in cands if c["normalized"] == o["normalized"]]
            if same:
                return same[0]["id"]
            if cands:  # e.g. "2" read from "2.3" by the old parser
                best = max(cands, key=lambda c: difflib.SequenceMatcher(None, c.get("context", ""), o.get("context", "")).ratio()
                           + (0.5 if c["normalized"].startswith(o["normalized"]) else 0))
                if best["normalized"].startswith(o["normalized"]):
                    return best["id"]
            return None
        if k == "table":
            pos = old_table_pos.get(oid)
            lst = tables_new.get(o["paper"], [])
            return lst[pos]["id"] if pos is not None and pos < len(lst) else None
        if k == "figure":
            return simple_new.get((o["paper"], "figure", o["label"]))
        if k == "citation":
            return simple_new.get((o["paper"], "citation", o["key"]))
        if k == "reference":
            return simple_new.get((o["paper"], "reference", o["index"]))
        return None

    remapped, unmapped = 0, []
    for it in keep:
        links = it.get("linked_items") or []
        new_links, lost = [], []
        for ln in links:
            nid = map_id(ln)
            if nid:
                new_links.append(nid)
                remapped += nid != ln
            else:
                lost.append(ln)
        if links:
            it["linked_items"] = new_links
        if lost:
            it["carry_over_unmapped_links"] = lost
            unmapped.append({"item": it["id"], "lost_links": lost, "text": (it.get("text_fr") or it.get("raw") or "")[:120]})

    # an assistant id that now collides with a script id is renamed, and the links that point to it follow
    new_ids = {it["id"] for it in new_items}
    renamed = {}
    for it in keep:
        if it["id"] in new_ids:
            nid = it["id"] + "-H"
            while nid in new_ids:
                nid += "H"
            renamed[it["id"]] = nid
            it["id"] = nid
    if renamed:
        for it in keep:
            if it.get("linked_items"):
                it["linked_items"] = [renamed.get(x, x) for x in it["linked_items"]]

    report = {"from_generated_at": old.get("generated_at"), "from_parser_version": str(old.get("parser_version", "1")),
              "carried_items": len(keep), "links_remapped": remapped, "unmapped": unmapped, "renamed_ids": renamed}
    return keep, report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--review", help=".docx of the final French review article")
    ap.add_argument("--empirical", help=".docx of the final French empirical article")
    ap.add_argument("--locale", default="fr", choices=["fr", "en", "ar"], help="default language of both papers")
    ap.add_argument("--review-locale", default=None, choices=["fr", "en", "ar"], help="language of the review article, if it differs")
    ap.add_argument("--empirical-locale", default=None, choices=["fr", "en", "ar"], help="language of the empirical article, if it differs")
    ap.add_argument("--out", default="fidelity_ledger.json")
    ap.add_argument("--text-dump", help="directory to write <paper>_blocks.json and <paper>.txt")
    ap.add_argument("--carry-over", help="previous fidelity_ledger.json whose claim register (and other assistant items) must be kept")
    a = ap.parse_args()
    if not a.review and not a.empirical:
        ap.error("give --review and/or --empirical")

    old = L.load_json(a.carry_over) if a.carry_over else None
    ledger = {"ledger_version": "1.0", "parser_version": L.PARSER_VERSION, "project_id": a.project,
              "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
              "sources": {}, "items": [], "summary": {}}
    locales = {"review": a.review_locale or a.locale, "empirical": a.empirical_locale or a.locale}
    for paper, prefix, path in (("review", "R", a.review), ("empirical", "E", a.empirical)):
        if not path:
            continue
        loc = locales[paper]
        items, summary, blocks = extract_paper(path, prefix, paper, loc)
        ledger["sources"][paper] = {"file": os.path.basename(path), "sha256": L.sha256_file(path), "locale": loc}
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
        print(f"{paper:9s} [{loc}] {os.path.basename(path)}: " + ", ".join(f"{k}={v}" for k, v in summary.items() if k != 'claims'))
    if old is not None:
        for paper, src in ledger["sources"].items():
            old_sha = (old.get("sources", {}).get(paper) or {}).get("sha256")
            if old_sha and old_sha != src["sha256"]:
                print(f"WARNING: the {paper} source differs from the one of the old ledger (SHA-256 changed) — "
                      f"check that this is the same final, locked paper before going on.")
        keep, report = carry_over(old, ledger["items"])
        ledger["items"].extend(keep)
        for p in ledger["summary"]:
            ledger["summary"][p]["claims"] = sum(1 for it in keep if it.get("paper") == p and it.get("kind") == "claim")
            ledger["summary"][p]["numbers"] += sum(1 for it in keep if it.get("paper") == p and it.get("kind") == "number")
        ledger["carry_over"] = report
        print(f"carried over from the old ledger: {report['carried_items']} items, {report['links_remapped']} links remapped, "
              f"{sum(len(u['lost_links']) for u in report['unmapped'])} links to re-link by hand")
        for u in report["unmapped"]:
            print(f"   {u['item']}: {', '.join(u['lost_links'])}  — {u['text']}")
    L.save_json(ledger, a.out)
    print(f"ledger written: {a.out} ({len(ledger['items'])} items, number parser v{L.PARSER_VERSION})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
