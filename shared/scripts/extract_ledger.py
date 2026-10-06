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
The reference list is the run of entries after a "Références"-type heading; it ends at the next heading, at a table
or at the first paragraph that is not an entry (an "Annexe A" title typed without a heading style, v0.2.7).
Citation keys are counted in the body paragraphs and in the table cells — the same basis as reconcile_ledger.py.

--text-dump writes <paper>_blocks.json and <paper>.txt so the assistant can read the papers section by section.

--review-locale / --empirical-locale (v0.2.5) override --locale for one paper: a review written in French and an
empirical article deposited in English are read each with their own number conventions (decimal comma vs point,
thousands separators). The locale of each source is recorded in the ledger's `sources` block.

--carry-over OLD_LEDGER (v0.2.4) rebuilds a ledger made with an older number parser without losing the work done
with the student: every item of the old ledger that was not extracted by the script (the confirmed claim register,
numbers written in words) is kept, and its links to script items are remapped to the new ids. Links that cannot be
remapped are listed in the item (carry_over_unmapped_links) and in the ledger's carry_over report: re-link them by
hand with the student before going on.
Since v0.2.6 a number the assistant had added by hand because the old parser missed it (e.g. a CI bound inside
brackets) is dropped when the new parser reads that same occurrence itself: the ledger would otherwise expect the
value twice. Dropped items and the script id that replaces them are listed in carry_over.dropped_duplicates; links
that pointed to them follow. Numbers written in words (role_hint "spelled_out") are never dropped.
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

    ref_index = 0
    ref_paragraphs: list[str] = []
    citation_counts: dict[str, int] = {}
    pending_table_label: str | None = None
    pending_table_caption: str | None = None
    para_index = 0

    for i, (b, in_refs) in enumerate(L.walk_blocks(blocks)):
        if b["kind"] == "heading":
            continue

        if b["kind"] == "paragraph":
            para_index += 1
            text = b["text"]
            if in_refs:
                ref_paragraphs.append(text)
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
                    for k, c in L.find_citations(cell).items():  # v0.2.7: citations in tables count on both sides
                        citation_counts[k] = citation_counts.get(k, 0) + c
            items.append({"id": nid("T"), "paper": paper, "kind": "table", "label": label or f"(table sans légende #{counters['T'] + 1})",
                          "caption": caption, "section": b["section"], "n_rows": len(cells),
                          "n_cols": max((len(r) for r in cells), default=0),
                          "header": cells[0] if cells else [], "cells": cells, "numbers_normalized": nums,
                          "extracted_by": "script"})
            pending_table_label = None
            pending_table_caption = None

    # reference entries — an entry wrapped over two paragraphs is one entry (v0.2.7)
    for text in L.merge_reference_fragments(ref_paragraphs):
        ref_index += 1
        typed, body = L.split_ref_index(text)
        idx = typed if typed is not None else ref_index
        doi = None
        dm = re.search(r"10\.\d{4,9}/[^\s\"<>]+", body)
        if dm:
            doi = dm.group(0).rstrip(".;,")
        items.append({"id": nid("REF"), "paper": paper, "kind": "reference", "index": idx,
                      "text": body, "doi": doi, "extracted_by": "script"})

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
    refs_new: dict[str, list[dict]] = defaultdict(list)
    simple_new: dict[tuple, str] = {}
    ref_taken: set[str] = set()
    ref_cache: dict[str, str | None] = {}

    def ref_key(t: str) -> str:
        return re.sub(r"\s+", " ", L.split_ref_index(t)[1]).strip().lower()
    by_raw: dict[tuple, list[dict]] = defaultdict(list)
    num_taken: set[str] = set()
    for it in new_items:
        if it["kind"] == "number":
            by_para_raw[(it["paper"], it.get("paragraph_index"), it["raw"])].append(it["id"])
            by_para[(it["paper"], it.get("paragraph_index"))].append(it)
            by_raw[(it["paper"], it["normalized"])].append(it)
        elif it["kind"] == "table":
            tables_new[it["paper"]].append(it)
        elif it["kind"] == "figure":
            simple_new[(it["paper"], "figure", it["label"])] = it["id"]
        elif it["kind"] == "citation":
            simple_new[(it["paper"], "citation", it["key"])] = it["id"]
        elif it["kind"] == "reference":
            simple_new.setdefault((it["paper"], "reference", it["index"]), it["id"])
            refs_new[it["paper"]].append(it)

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
            if cands:  # e.g. "2" read from "2.3" by the old parser (never "2" → "25.8", v0.2.7)
                best = max(cands, key=lambda c: difflib.SequenceMatcher(None, c.get("context", ""), o.get("context", "")).ratio()
                           + (0.5 if c["normalized"].startswith(o["normalized"] + ".") else 0))
                if best["normalized"].startswith(o["normalized"] + "."):
                    return best["id"]
            # v0.2.7 — the paragraph numbering shifts when the parser reads a document differently (a table of
            # contents skipped, a heading split from its body text): the same value at the same place in the
            # text, found by its context window, is the same item
            for c in by_raw.get((o["paper"], o["normalized"]), []):
                if c["id"] not in num_taken and same_occurrence(c.get("context", ""), o.get("context", "")):
                    num_taken.add(c["id"])
                    return c["id"]
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
            # v0.2.7 — by text first: the parser now splits, merges and indexes entries differently from v0.2.6
            # (wrapped entries joined, "[5b]" read, hand bullets dropped), so the position alone could hand a
            # verified status to the wrong entry. The typed index is only a tie-breaker between close texts.
            if oid in ref_cache:              # several links may point at the same entry
                return ref_cache[oid]
            ok_ = ref_key(o.get("text", ""))
            cands = [c for c in refs_new.get(o["paper"], []) if c["id"] not in ref_taken]
            best, score = None, 0.0
            for c in cands:
                ck = ref_key(c.get("text", ""))
                s = 1.0 if ck == ok_ else difflib.SequenceMatcher(None, ok_, ck).ratio()
                if ck.startswith(ok_[:80]) or ok_.startswith(ck[:80]):
                    s = max(s, 0.9)           # the old entry is the head of a now-merged entry, or the reverse
                if s > score or (s == score and best is not None and c["index"] == o["index"]):
                    best, score = c, s
            if best is not None and score >= 0.8:
                ref_taken.add(best["id"])
                ref_cache[oid] = best["id"]
                return best["id"]
            ref_cache[oid] = None
            return None
        return None

    # v0.2.6 — an assistant-added number that the new parser now reads itself is a duplicate: the same occurrence
    # (same paragraph, or the same context window) with the same normalised value. It is dropped and the links
    # that pointed to it follow the script item. Numbers written in words stay: they are extra by design.
    by_value: dict[tuple, list[dict]] = defaultdict(list)
    for it in new_items:
        if it["kind"] == "number":
            by_value[(it["paper"], it["normalized"])].append(it)
    dup_map: dict[str, str] = {}
    dropped: list[dict] = []
    survivors: list[dict] = []
    for it in keep:
        if it["kind"] != "number" or it.get("role_hint") == "spelled_out":
            survivors.append(it)
            continue
        twin = None
        for c in by_value.get((it["paper"], it.get("normalized")), []):
            if c["id"] in dup_map.values():
                continue
            if it.get("paragraph_index") is not None and c.get("paragraph_index") == it["paragraph_index"]:
                twin = c
                break
            if same_occurrence(it.get("context", ""), c.get("context", "")):
                twin = c
                break
        if twin is None:
            survivors.append(it)
        else:
            dup_map[it["id"]] = twin["id"]
            dropped.append({"item": it["id"], "replaced_by": twin["id"], "raw": it.get("raw"),
                            "section": it.get("section"), "extracted_by": it.get("extracted_by")})
    keep = survivors

    remapped, unmapped = 0, []
    for it in keep:
        links = it.get("linked_items") or []
        new_links, lost = [], []
        for ln in links:
            nid = dup_map.get(ln) or map_id(ln)
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
              "carried_items": len(keep), "links_remapped": remapped, "unmapped": unmapped, "renamed_ids": renamed,
              "dropped_duplicates": dropped}
    return keep, report


def same_occurrence(ctx_a: str, ctx_b: str, min_common: int = 24) -> bool:
    """Two context windows describe the same place in the paper when they share a long run of text."""
    a = re.sub(r"\s+", " ", ctx_a or "").strip()
    b = re.sub(r"\s+", " ", ctx_b or "").strip()
    if not a or not b:
        return False
    m = difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b))
    return m.size >= min_common


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
                for b, in_refs in L.walk_blocks(blocks):
                    if b["kind"] == "heading":
                        f.write(f"\n## {b['text']}\n\n")
                    elif in_refs and "\n" in b["text"]:
                        # a list typed in one paragraph with soft line breaks: one entry per paragraph in the dump,
                        # so the translation carries one entry per paragraph too (v0.2.7)
                        for entry in L.merge_reference_fragments([b["text"]]):
                            f.write(entry + "\n\n")
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
              f"{sum(len(u['lost_links']) for u in report['unmapped'])} links to re-link by hand, "
              f"{len(report['dropped_duplicates'])} hand-added numbers now read by the parser (dropped)")
        for d in report["dropped_duplicates"]:
            print(f"   dropped {d['item']} ({d['raw']}, {d['section']}) → {d['replaced_by']}")
        for u in report["unmapped"]:
            print(f"   {u['item']}: {', '.join(u['lost_links'])}  — {u['text']}")
    L.save_json(ledger, a.out)
    print(f"ledger written: {a.out} ({len(ledger['items'])} items, number parser v{L.PARSER_VERSION})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
