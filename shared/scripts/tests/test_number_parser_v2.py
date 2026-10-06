#!/usr/bin/env python3
"""Regression tests for the number parser v2 (plugin v0.2.4), the mixed-language sources of v0.2.5 and the
parser v3 / carry-over dedupe of v0.2.6.

    python shared/scripts/tests/test_number_parser_v2.py [--keep DIR]

Part A checks p4lib.find_numbers / find_citations on the five patterns reported on 2026-10-04 (D15-P04) and on
the cases that must NOT change (true citation keys). Part B builds a small French source (.docx written directly
with python-docx, as a student's Word file), its English and Arabic translations, extracts the ledger and
reconciles the two targets: both must report zero Major finding. Part C checks the parser-version gate and the
--carry-over rebuild (claims kept, links remapped). Exit code 0 = all tests passed.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
import p4lib as L  # noqa: E402

PY = sys.executable
FAILS: list[str] = []


def check(name: str, got, want) -> None:
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ("" if ok else f"\n         got  {got!r}\n         want {want!r}"))
    if not ok:
        FAILS.append(name)


def nums(text: str, loc: str) -> list[str]:
    return [h.normalized for h in L.find_numbers(text, loc)]


def part_a() -> None:
    print("A. parser")
    # 1. thousands separators
    check("fr 1 248", nums("1 248 femmes", "fr"), ["1248"])
    check("en 1,248", nums("1,248 women", "en"), ["1248"])
    check("en 1 248 (no-break space)", nums("1 248 women", "en"), ["1248"])
    check("ar 1٬248 (U+066C)", nums("1٬248 امرأة", "ar"), ["1248"])
    check("ar ١٢٫٥٪ (Arabic-Indic, U+066B)", nums("بنسبة ١٢٫٥٪", "ar"), ["12.5"])
    check("fr label split 'tableau 3 120'", [(h.normalized, h.role_hint) for h in L.find_numbers("le tableau 3 120 femmes", "fr")],
          [("3", "label_ref"), ("120", None)])
    # 2. bracketed intervals
    check("fr CI [1,3 ; 3,4]", nums("OR 2,1 [1,3 ; 3,4]", "fr"), ["2.1", "1.3", "3.4"])
    check("en CI [1.3; 3.4]", nums("OR 2.1 [1.3; 3.4]", "en"), ["2.1", "1.3", "3.4"])
    check("fr cell [0,8–1,9]", nums("2,1 [0,8–1,9]", "fr"), ["2.1", "0.8", "1.9"])
    check("fr median [24–33]", nums("médiane 28 [24–33]", "fr"), ["28", "24", "33"])
    check("en median [24–33]", nums("median 28 [24–33]", "en"), ["28", "24", "33"])
    check("fr CI not a citation", L.find_citations("OR 2,1 [1,3 ; 3,4]"), {})
    # unchanged: real citation keys
    check("fr citation [1,3]", L.find_citations("comme rapporté [1,3]"), {"[1]": 1, "[3]": 1})
    check("fr citation [12–15]", L.find_citations("plusieurs études [12–15]"), {"[12]": 1, "[13]": 1, "[14]": 1, "[15]": 1})
    check("fr citation after a year", L.find_citations("en 2019 [12–15]"), {"[12]": 1, "[13]": 1, "[14]": 1, "[15]": 1})
    check("fr citation not a number", nums("plusieurs études [12–15]", "fr"), [])
    # 2b. parser v3 (v0.2.6, D15-P03): decimal-comma intervals alone in a table cell, and intervals whose
    #     citation reading is not a well-formed list; true citation lists with ranges are unchanged
    check("fr cell [52,5–79,5] alone", nums("[52,5–79,5]", "fr"), ["52.5", "79.5"])
    check("fr cell [2,6–51,3] alone", nums("[2,6–51,3]", "fr"), ["2.6", "51.3"])
    check("fr cell [1,2–3,4] alone", nums("[1,2–3,4]", "fr"), ["1.2", "3.4"])
    check("fr [30,1–49,5] after plain words", nums("continuité adéquate [30,1–49,5]", "fr"), ["30.1", "49.5"])
    check("fr [52,5–79,5] is not a citation", L.find_citations("[52,5–79,5]"), {})
    check("fr [30,1–49,5] is not a citation", L.find_citations("continuité adéquate [30,1–49,5]"), {})
    check("fr citation list with a range [1,3-5,7]", L.find_citations("comme rapporté [1,3-5,7]"),
          {"[1]": 1, "[3]": 1, "[4]": 1, "[5]": 1, "[7]": 1})
    check("fr citation [1,3-5,7] not a number", nums("comme rapporté [1,3-5,7]", "fr"), [])
    check("plausible list 1,3-5,7", L.plausible_citation_list("1,3-5,7"), True)
    check("not plausible 52,5–79,5", L.plausible_citation_list("52,5–79,5"), False)
    check("not plausible 2,6–51,3 (span 45)", L.plausible_citation_list("2,6–51,3"), False)
    # 3. DOIs and URLs
    check("fr DOI url", nums("(https://doi.org/10.1186/s12884-021-03456-7)", "fr"), [])
    check("en DOI url", nums("(https://doi.org/10.1186/s12884-021-03456-7)", "en"), [])
    check("fr doi:", nums("doi: 10.1016/j.midw.2020.102345", "fr"), [])
    # 4. section cross-references
    check("fr (voir 2.3)", nums("(voir 2.3)", "fr"), ["2.3"])
    check("en (see 2.3)", nums("(see 2.3)", "en"), ["2.3"])
    check("ar القسم 2.3 is a label", [h.role_hint for h in L.find_numbers("انظر القسم 2.3", "ar")], ["label_ref"])
    check("fr § 2.3 is a label", [h.role_hint for h in L.find_numbers("cf. § 2.3", "fr")], ["label_ref"])
    check("fr 2.3.1 ignored", nums("la sous-partie 2.3.1 décrit", "fr"), [])
    check("en 2.3.1 ignored", nums("subsection 2.3.1 describes", "en"), [])
    # unchanged statistics
    check("fr p = 0,03", nums("p = 0,03", "fr"), ["0.03"])
    check("fr IC 95 % : 1,10–1,83", nums("IC 95 % : 1,10–1,83", "fr"), ["95", "1.10", "1.83"])
    # 5. empty table rows
    check("md empty row is not a rule", L.is_md_rule_row(["", "", ""]), False)
    check("md rule row", L.is_md_rule_row(["---", ":--:", "---"]), True)
    check("non-empty rows", L.nonempty_rows([["a", "1"], ["", ""], ["b", "2"]]), 2)


FR_PARAS = [
    ("h", "Résultats"),
    ("p", "Au total, 1 248 femmes ont été invitées et 1 012 ont répondu (81,1 %)."),
    ("p", "Le score EPDS ≥ 12 était associé au faible soutien (OR ajusté 2,10 ; IC 95 % [1,30 ; 3,40] ; p = 0,002)."),
    ("p", "La médiane d’âge était de 28 ans [24–33] ; la méthode est décrite plus haut (voir 2.3) et en section 2.3.1."),
    ("p", "Les données sont disponibles (https://doi.org/10.5281/zenodo.1234567) ; voir aussi [1,3]."),
    ("table", [["Variable", "n (%)", "OR [IC 95 %]"], ["Primipare", "412 (40,7)", "1,85 [1,20–2,86]"], ["", "", ""],
               ["Multipare", "600 (59,3)", "1"]]),
    ("table", [["Quartier", "Continuité adéquate (%)", "IC 95 %"], ["Nord", "66,0", "[52,5–79,5]"],
               ["Sud", "39,8", "[30,1–49,5]"], ["Est", "26,9", "[2,6–51,3]"]]),
    ("p", "Tableau 2. Continuité adéquate par quartier."),
    ("p", "Tableau 1. Facteurs associés (n = 1 012)."),
    ("h", "Références"),
    ("p", "1. Cox JL, Holden JM, Sagovsky R. Detection of postnatal depression. Br J Psychiatry. 1987;150:782-6."),
    ("p", "3. Gibson J, et al. A systematic review of the EPDS. Acta Psychiatr Scand. 2009;119:350-64."),
]

EN_MD = """# Results

In total, 1,248 women were invited and 1,012 responded (81.1%).

An EPDS score ≥ 12 was associated with low support (adjusted OR 2.10; 95% CI [1.30; 3.40]; p = 0.002).

The median age was 28 years [24–33]; the method is described above (see 2.3) and in section 2.3.1.

Data are available (https://doi.org/10.5281/zenodo.1234567); see also [1,3].

| Variable | n (%) | OR [95% CI] |
|---|---|---|
| Primiparous | 412 (40.7) | 1.85 [1.20–2.86] |
|  |  |  |
| Multiparous | 600 (59.3) | 1 |

Table 1. Associated factors (n = 1,012).

| District | Adequate continuity (%) | 95% CI |
|---|---|---|
| North | 66.0 | [52.5–79.5] |
| South | 39.8 | [30.1–49.5] |
| East | 26.9 | [2.6–51.3] |

Table 2. Adequate continuity by district.

# References

1. Cox JL, Holden JM, Sagovsky R. Detection of postnatal depression. Br J Psychiatry. 1987;150:782-6.

3. Gibson J, et al. A systematic review of the EPDS. Acta Psychiatr Scand. 2009;119:350-64.
"""

AR_MD = """# النتائج

دُعيت 1٬248 امرأة وأجابت 1٬012 منهن (81٫1٪).

ارتبطت درجة EPDS ≥ 12 بضعف الدعم (OR المعدَّلة 2.10؛ IC 95% [1.30; 3.40]؛ p = 0.002).

بلغ وسيط العمر 28 سنة [24–33]؛ وتُعرض الطريقة أعلاه (انظر القسم 2.3) وفي القسم 2.3.1.

البيانات متاحة (https://doi.org/10.5281/zenodo.1234567)؛ انظر أيضًا [1,3].

| المتغير | n (%) | OR [IC 95%] |
|---|---|---|
| بكرية | 412 (40.7) | 1.85 [1.20–2.86] |
|  |  |  |
| متعددة الولادات | 600 (59.3) | 1 |

الجدول 1. العوامل المرتبطة (n = 1٬012).

| الحي | الاستمرارية الملائمة (%) | IC 95% |
|---|---|---|
| الشمال | 66.0 | [52.5–79.5] |
| الجنوب | 39.8 | [30.1–49.5] |
| الشرق | 26.9 | [2.6–51.3] |

الجدول 2. الاستمرارية الملائمة حسب الحي.

# المراجع

1. Cox JL, Holden JM, Sagovsky R. Detection of postnatal depression. Br J Psychiatry. 1987;150:782-6.

3. Gibson J, et al. A systematic review of the EPDS. Acta Psychiatr Scand. 2009;119:350-64.
"""


def write_fr_docx(path: str) -> None:
    import docx
    d = docx.Document()
    for kind, content in FR_PARAS:
        if kind == "h":
            d.add_heading(content, level=1)
        elif kind == "p":
            d.add_paragraph(content)
        else:
            t = d.add_table(rows=len(content), cols=len(content[0]))
            for i, row in enumerate(content):
                for j, c in enumerate(row):
                    t.cell(i, j).text = c
    d.save(path)


def run(*args) -> int:
    return subprocess.call([PY, *args], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def part_b_c(work: str) -> None:
    s = lambda n: os.path.join(SCRIPTS, n)  # noqa: E731
    os.chdir(work)
    write_fr_docx("article_FR.docx")
    open("article_EN.md", "w", encoding="utf-8").write(EN_MD)
    open("article_AR.md", "w", encoding="utf-8").write(AR_MD)
    print("B. end to end (French Word source → English and Arabic targets)")
    check("extract_ledger", run(s("extract_ledger.py"), "--project", "D99-T01", "--empirical", "article_FR.docx",
                                "--out", "ledger.json"), 0)
    led = L.load_json("ledger.json")
    check("ledger carries parser_version", led.get("parser_version"), L.PARSER_VERSION)
    led_nums = {it["normalized"] for it in led["items"] if it["kind"] == "number"}
    check("CI bounds are in the ledger", {"1.30", "3.40"} <= led_nums, True)
    tbl_nums = {n for it in led["items"] if it["kind"] == "table" for n in it["numbers_normalized"]}
    check("cell intervals [52,5–79,5] … are in the ledger (v3)", {"52.5", "79.5", "30.1", "49.5", "2.6", "51.3"} <= tbl_nums, True)
    check("no phantom citation from a cell interval", any(it["kind"] == "citation" and it["key"] in ("[52]", "[79]", "[30]") for it in led["items"]), False)
    check("DOI digits are not in the ledger", "5281" in led_nums or "1234567" in led_nums, False)
    for lang in ("en", "ar"):
        check(f"build {lang}", run(s("build_docx_from_md.py"), "--md", f"article_{lang.upper()}.md", "--lang", lang,
                                   "--out", f"article_{lang.upper()}.docx"), 0)
        rc = run(s("reconcile_ledger.py"), "translation", "--ledger", "ledger.json", "--paper", "empirical",
                 "--target", f"article_{lang.upper()}.docx", "--locale", lang, "--out", f"recon_{lang}.json")
        rep = L.load_json(f"recon_{lang}.json")
        check(f"reconcile {lang}: exit 0", rc, 0)
        check(f"reconcile {lang}: no missing number", rep["ledger"]["missing"], [])
        check(f"reconcile {lang}: tables ok", rep["tables"]["mismatches"], [])
        check(f"reconcile {lang}: citations ok", rep["citations"]["mismatches"], [])

    print("C. parser gate and --carry-over")
    old = dict(led)
    old["parser_version"] = "1"
    num_ci = next(it["id"] for it in led["items"] if it["kind"] == "number" and it["normalized"] == "1.30")
    num_2_3 = next(it["id"] for it in led["items"] if it["kind"] == "number" and it["normalized"] == "2.3")
    claim = {"id": "E-CL-0001", "paper": "empirical", "kind": "claim", "section": "Résultats",
             "text_fr": "Le faible soutien est associé à un score EPDS ≥ 12.", "direction": "positive",
             "strength": "confirmatory", "hedge": "est associé à", "linked_items": [num_ci, num_2_3],
             "extracted_by": "assistant", "student_confirmed": True}
    # v0.2.6: a CI bound added by hand under the old parser (same occurrence as the script item of 3.40) and a
    # number written in words — the first must be dropped on rebuild, the second kept
    ci_340 = next(it for it in led["items"] if it["kind"] == "number" and it["normalized"] == "3.40")
    hand = {"id": "E-N-9001", "paper": "empirical", "kind": "number", "section": ci_340.get("section"), "raw": "3,40",
            "normalized": "3.40", "unit": None, "role_hint": None, "context": ci_340.get("context"),
            "extracted_by": "assistant (ledger 1.1 correction)"}
    words = {"id": "E-N-9002", "paper": "empirical", "kind": "number", "section": "Résultats", "raw": "douze",
             "normalized": "12", "unit": None, "role_hint": "spelled_out", "context": "score EPDS ≥ douze",
             "extracted_by": "assistant"}
    claim["linked_items"] = [num_ci, num_2_3, "E-N-9001"]
    old["items"] = led["items"] + [claim, hand, words]
    L.save_json(old, "ledger_old.json")
    rc = run(s("reconcile_ledger.py"), "translation", "--ledger", "ledger_old.json", "--paper", "empirical",
             "--target", "article_EN.docx", "--locale", "en", "--out", "recon_old.json")
    check("old ledger refused (exit 2)", rc, 2)
    check("rebuild with --carry-over", run(s("extract_ledger.py"), "--project", "D99-T01", "--empirical", "article_FR.docx",
                                           "--out", "ledger_new.json", "--carry-over", "ledger_old.json"), 0)
    new = L.load_json("ledger_new.json")
    kept = [it for it in new["items"] if it["kind"] == "claim"]
    check("claim kept", [it["id"] for it in kept], ["E-CL-0001"])
    ids = {it["id"]: it for it in new["items"]}
    check("claim links resolve to the same values", sorted(ids[x]["normalized"] for x in kept[0]["linked_items"]), ["1.30", "2.3", "3.40"])
    check("summary counts the claim", new["summary"]["empirical"]["claims"], 1)
    check("hand-added duplicate dropped (v0.2.6)", "E-N-9001" in ids, False)
    check("dropped duplicate reported", [(d["item"], d["replaced_by"]) for d in new["carry_over"]["dropped_duplicates"]],
          [("E-N-9001", ci_340["id"])])
    check("claim link follows the script item", ci_340["id"] in kept[0]["linked_items"], True)
    check("spelled-out number kept", "E-N-9002" in ids and ids["E-N-9002"]["role_hint"] == "spelled_out", True)
    check("3.40 expected once, not twice", sum(1 for it in new["items"] if it["kind"] == "number" and it["normalized"] == "3.40"), 1)


EN_FR_SRC = [
    ("h", "Results"),
    ("p", "In total, 1,248 women were invited and 1,012 responded (81.1%); the adjusted OR was 2.10 (95% CI [1.30; 3.40])."),
]


def part_d(work: str) -> None:
    """v0.2.5 — a French review and an English empirical article read each with its own locale."""
    import docx
    s = lambda n: os.path.join(SCRIPTS, n)  # noqa: E731
    os.chdir(work)
    d = docx.Document()
    for kind, content in EN_FR_SRC:
        (d.add_heading if kind == "h" else d.add_paragraph)(content, **({"level": 1} if kind == "h" else {}))
    d.save("article_EN_source.docx")
    print("D. mixed-language sources (--review-locale / --empirical-locale)")
    check("extract fr review + en empirical", run(s("extract_ledger.py"), "--project", "D99-T02", "--review", "article_FR.docx",
                                                   "--empirical", "article_EN_source.docx", "--review-locale", "fr",
                                                   "--empirical-locale", "en", "--out", "ledger_mixed.json"), 0)
    led = L.load_json("ledger_mixed.json")
    check("source locales recorded", (led["sources"]["review"]["locale"], led["sources"]["empirical"]["locale"]), ("fr", "en"))
    emp = {it["normalized"] for it in led["items"] if it["kind"] == "number" and it["paper"] == "empirical"}
    check("English thousands read as one number", "1248" in emp and "1012" in emp, True)
    check("English decimals kept", {"81.1", "2.10", "1.30", "3.40"} <= emp, True)
    rev = {it["normalized"] for it in led["items"] if it["kind"] == "number" and it["paper"] == "review"}
    check("French review still read in French", "1248" in rev, True)
    # the English source registered unchanged as its own English version reconciles with zero finding
    rc = run(s("reconcile_ledger.py"), "translation", "--ledger", "ledger_mixed.json", "--paper", "empirical",
             "--target", "article_EN_source.docx", "--locale", "en", "--out", "recon_self.json")
    rep = L.load_json("recon_self.json")
    check("English source reconciles with itself: exit 0", rc, 0)
    check("English source reconciles with itself: nothing missing or introduced", (rep["ledger"]["missing"], rep["ledger"]["introduced"]), ([], []))


def main() -> int:
    keep = None
    if "--keep" in sys.argv:
        keep = sys.argv[sys.argv.index("--keep") + 1]
    part_a()
    work = keep or tempfile.mkdtemp(prefix="p4_v2_")
    os.makedirs(work, exist_ok=True)
    try:
        part_b_c(work)
        part_d(work)
    finally:
        os.chdir(HERE)
        if not keep:
            shutil.rmtree(work, ignore_errors=True)
    print(f"\n{'ALL TESTS PASSED' if not FAILS else str(len(FAILS)) + ' TEST(S) FAILED: ' + ', '.join(FAILS)}")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
