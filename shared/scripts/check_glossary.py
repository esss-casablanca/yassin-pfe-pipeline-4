#!/usr/bin/env python3
"""check_glossary.py — terminology consistency between the French source and a translated version (p4-05).

Usage:
  python check_glossary.py --glossary glossary_fr_en_ar.json --source _p4_text/review.txt \
      --target review_article_EN.docx --lang en --out gloss_review_EN.json

For every glossary entry whose French term occurs in the source, the target must contain the target-language
term (or one of its listed "variants_<lang>") at least once; an entry present in the source but absent from the
target is reported, with the count asymmetry, as a possible inconsistent rendering. Acronyms with
keep_latin_acronym = true must appear in Latin letters in the target. The check is lexical (case-insensitive,
whitespace-normalised, Arabic diacritics stripped); the assistant judges each report. The reference list of both
documents is excluded from the count (v0.2.7).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p4lib as L  # noqa: E402

AR_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ]")


AR_WORD_PREFIX = re.compile(r"(?<![\u0600-\u06FF])(?:و|ف|ب|ل|ك)?(?:ال|لل)(?=[\u0600-\u06FF]{2,})")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "")
    s = AR_DIACRITICS.sub("", s)
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
    s = AR_WORD_PREFIX.sub("", s)  # strip the definite article (and a clitic before it) so المراجعة المنهجية matches مراجعة منهجية
    return re.sub(r"\s+", " ", s).strip().lower()


def count(term: str, text: str) -> int:
    t = norm(term)
    if not t:
        return 0
    if re.search(r"[A-Za-zÀ-ÿ]", t):  # Latin-script term: whole-word match (Maroc must not count marocaine, CI must not count CINAHL)
        pat = r"(?<![A-Za-zÀ-ÿ0-9])" + re.escape(t) + r"(?![A-Za-zÀ-ÿ0-9])"
    else:
        pat = re.escape(t)
    return len(re.findall(pat, text))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--glossary", required=True)
    ap.add_argument("--source", required=True, help="French source text (.txt from the dump, or .docx)")
    ap.add_argument("--target", required=True, help="translated version (.docx or .md)")
    ap.add_argument("--lang", required=True, choices=["en", "ar"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    g = L.load_json(a.glossary)
    # v0.2.7: the reference list is left out on both sides — a French title kept verbatim in a reference is not a
    # rendering of the term (the .txt dump of extract_ledger has "## heading" lines and is read like Markdown)
    src = L.split_body_and_refs(L.text_blocks(a.source))[0]
    tgt = L.split_body_and_refs(L.text_blocks(a.target))[0]
    src_n, tgt_n = norm(src), norm(tgt)
    key = f"term_{a.lang}"
    report, checked, flagged = [], 0, 0
    for e in g.get("entries", []):
        fr = e.get("term_fr", "")
        c_src = count(fr, src_n)
        acr = e.get("acronym")
        if acr:
            c_src += count(acr, src_n)
        if c_src == 0:
            continue
        checked += 1
        variants = [e.get(key, "")] + list(e.get(f"variants_{a.lang}", []))
        c_tgt = sum(count(v, tgt_n) for v in variants if v)
        c_acr_tgt = count(acr, tgt_n) if acr else 0
        entry = {"id": e.get("id"), "category": e.get("category"), "term_fr": fr, key: e.get(key), "acronym": acr,
                 "source_count": c_src, "target_count": c_tgt, "acronym_in_target": c_acr_tgt,
                 "status": e.get("status")}
        problems = []
        if c_tgt == 0 and c_acr_tgt == 0:
            problems.append("target term absent — rendered differently or omitted")
        if acr and e.get("keep_latin_acronym") and c_acr_tgt == 0:
            problems.append("Latin acronym absent from the target")
        if c_tgt + c_acr_tgt < c_src * 0.5:
            problems.append("far fewer occurrences in the target than in the source")
        if problems:
            flagged += 1
            entry["problems"] = problems
        report.append(entry)
    out = {"glossary": os.path.basename(a.glossary), "target": os.path.basename(a.target), "lang": a.lang,
           "entries_checked": checked, "flagged": flagged,
           "inconsistencies": [r for r in report if r.get("problems")], "all": report}
    L.save_json(out, a.out)
    print(f"[{out['target']}] {checked} glossary entries checked, {flagged} flagged")
    for r in out["inconsistencies"]:
        print(f"   {r['id']} {r['term_fr']!r} → {r[key]!r}: {'; '.join(r['problems'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
