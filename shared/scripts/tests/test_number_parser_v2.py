#!/usr/bin/env python3
"""Regression tests for the number parser v2 (plugin v0.2.4), the mixed-language sources of v0.2.5, the
parser v3 / carry-over dedupe of v0.2.6 and the parser v4 / reference-list boundary / bidi fixes of v0.2.7 (part E).

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


# ------------------------------------------------------------------------------------------------------------
# Part E — v0.2.7 (D10-P01, 2026-10-06): the reference-list boundary (SD-1), bidi controls in Arabic citations
# (SD-2), one citation-count basis, Word content controls and text boxes, ordinals, list numbering, Arabic clitics,
# the glossary check without the reference list, the parser-version gate (v3 accepted, v2 refused).
# ------------------------------------------------------------------------------------------------------------
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
WPS_NS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
V_NS = "urn:schemas-microsoft-com:vml"


def _w(tag):
    return "{%s}%s" % (W_NS, tag)


def _add_textbox(paragraph, box_text: str) -> None:
    """Anchor a text box in a paragraph the way Word does: a DrawingML choice and a VML fallback, both carrying
    the same w:txbxContent (the reader must count it once)."""
    from lxml import etree
    run = paragraph.add_run()._r
    alt = etree.SubElement(run, "{%s}AlternateContent" % MC_NS)
    choice = etree.SubElement(alt, "{%s}Choice" % MC_NS, Requires="wps")
    txbx = etree.SubElement(etree.SubElement(choice, _w("drawing")), "{%s}txbx" % WPS_NS)
    content = etree.SubElement(txbx, _w("txbxContent"))
    p = etree.SubElement(content, _w("p"))
    etree.SubElement(etree.SubElement(p, _w("r")), _w("t")).text = box_text
    fallback = etree.SubElement(alt, "{%s}Fallback" % MC_NS)
    vt = etree.SubElement(etree.SubElement(etree.SubElement(fallback, _w("pict")), "{%s}shape" % V_NS), "{%s}textbox" % V_NS)
    content2 = etree.SubElement(vt, _w("txbxContent"))
    p2 = etree.SubElement(content2, _w("p"))
    etree.SubElement(etree.SubElement(p2, _w("r")), _w("t")).text = box_text


def _wrap_in_sdt(doc, paragraphs) -> None:
    """Move paragraphs into a body-level content control (Word's bibliography block)."""
    from lxml import etree
    body = doc.element.body
    first = paragraphs[0]._p
    sdt = etree.Element(_w("sdt"))
    etree.SubElement(sdt, _w("sdtPr"))
    content = etree.SubElement(sdt, _w("sdtContent"))
    first.addprevious(sdt)
    for par in paragraphs:
        content.append(par._p)


E_FR = [
    ("h", "3. Résultats"),
    ("p", "Au total, 150 patients ont répondu le 1er octobre 2025 (taux 78,8 %) [1,2] ; le vosiège Box est cité [3]."),
    ("p", "1. Première priorité : renforcer l’accueil (24 items)."),
    ("p", "2. Deuxième priorité : réduire l’attente."),
    ("p", "Le score moyen était de 4,2 ; voir le Tableau 1."),
    ("table", [["Item", "Score", "Source"], ["Accueil", "4,2", "[3]"], ["Attente", "3,1", "[2]"]]),
    ("p", "Tableau 1. Scores par item."),
    ("h", "7. Références"),
    ("p", "1. Ajam A, et al. Patient satisfaction in radiology. J Radiol. 2017;12(3):441-9."),
    ("p", "2. Soufi G, et al. Determinants of satisfaction among patients: a cross-sectional study. BMC Health Serv Res."),
    ("p", "2010;10:149. doi:10.1186/1472-6963-10-149"),
    ("p", "3. Box GEP, Jenkins GM. Time series analysis. San Francisco: Holden-Day; 1970."),
    ("p", "Annexe A. Questionnaire QEPIM (version française)"),
    ("p", "Le questionnaire comporte 24 items répartis en 5 domaines ; chaque item est coté de 1 à 5."),
    ("table", [["Domaine", "Items"], ["Accueil", "6"], ["Information", "5"]]),
    ("p", "Annexe B. Autorisation de collecte des données"),
]

E_EN_MD = """# Results

In total, 150 patients responded on 1 October 2025 (rate 78.8%) [1,2]; the Box seat is cited [3].

1. First priority: strengthen reception (24 items).
2. Second priority: reduce waiting time.

The mean score was 4.2; see Table 1.

Box 1. Participant flow: 180 invited, 150 respondents.

| Item | Score | Source |
|---|---|---|
| Reception | 4.2 | [3] |
| Waiting | 3.1 | [2] |

Table 1. Scores by item.

## 7. References

1. Ajam A, et al. Patient satisfaction in radiology. J Radiol. 2017;12(3):441-9.
2. Soufi G, et al. Determinants of satisfaction among patients: a cross-sectional study. BMC Health Serv Res. 2010;10:149. doi:10.1186/1472-6963-10-149
3. Box GEP, Jenkins GM. Time series analysis. San Francisco: Holden-Day; 1970.

## Appendix A. QEPIM questionnaire (French version)

The questionnaire has 24 items in 5 domains; each item is scored from 1 to 5.

| Domain | Items |
|---|---|
| Reception | 6 |
| Information | 5 |

## Appendix B. Data collection authorisation
"""

E_AR_MD = """# النتائج

أجاب 150 مريضاً في 1 أكتوبر 2025 (بنسبة و78.8%) [1,2]؛ كما يُستشهد بمقعد Box [3].

1. الأولوية الأولى: تعزيز الاستقبال (24 بنداً).
2. الأولوية الثانية: تقليص الانتظار.

بلغ متوسط الدرجة 4.2؛ انظر الجدول 1.

الإطار 1. تدفق المشاركين: 180 مدعواً و150 مجيباً.

| البند | الدرجة | المصدر |
|---|---|---|
| الاستقبال | 4.2 | [3] |
| الانتظار | 3.1 | [2] |

الجدول 1. الدرجات حسب البند.

## 7. المراجع

1. Ajam A, et al. Patient satisfaction in radiology. J Radiol. 2017;12(3):441-9.
2. Soufi G, et al. Determinants of satisfaction among patients: a cross-sectional study. BMC Health Serv Res. 2010;10:149. doi:10.1186/1472-6963-10-149
3. Box GEP, Jenkins GM. Time series analysis. San Francisco: Holden-Day; 1970.

## الملحق أ. استبيان QEPIM (النسخة الفرنسية)

يتضمن الاستبيان 24 بنداً موزعة على 5 مجالات؛ ويُقيَّم كل بند من 1 إلى 5.

| المجال | البنود |
|---|---|
| الاستقبال | 6 |
| المعلومات | 5 |

## الملحق ب. ترخيص جمع البيانات
"""


def part_e(work: str) -> None:
    import docx
    s = lambda n: os.path.join(SCRIPTS, n)  # noqa: E731
    os.chdir(work)
    print("E. v0.2.7 — reference-list boundary, bidi controls, one citation basis, content controls, text boxes")
    # --- E.1 unit checks on the parser ---------------------------------------------------------------------------
    check("bidi controls stripped: [\\u202a29–33] is a citation", L.find_citations("كما أظهرت [\u202a29–33] \u202cأن"),
          {"[29]": 1, "[30]": 1, "[31]": 1, "[32]": 1, "[33]": 1})
    check("bidi controls stripped: no number read from the citation", nums("كما أظهرت [\u202a29–33] \u202cأن النسبة 78.8%", "ar"), ["78.8"])
    check("ar clitic و78.8%", nums("بلغت النسبة و78.8% و210 مريضاً والـ210 منهم ب2 سنة", "ar"), ["78.8", "210", "210", "2"])
    check("ar وسيط without article is a statistical cue", nums("بلغ وسيط العمر 28 سنة [24–33]", "ar"), ["28", "24", "33"])
    check("fr ordinal 1er", nums("le 1er groupe comptait 12 patients", "fr"), ["1", "12"])
    check("fr date in words is one date item", [(h.normalized, h.role_hint) for h in L.find_numbers("le 1er octobre 2026", "fr")], [("1-10-2026", "date")])
    check("en date in words is the same item", [(h.normalized, h.role_hint) for h in L.find_numbers("on October 1, 2026", "en")], [("1-10-2026", "date")])
    check("ar date with a Moroccan month name", [(h.normalized, h.role_hint) for h in L.find_numbers("في 1 نونبر 2026", "ar")], [("1-11-2026", "date")])
    check("month + year alone is a year", [(h.normalized, h.role_hint) for h in L.find_numbers("en octobre 2026", "fr")], [("2026", "year")])
    check("en ordinal 3rd", nums("on the 3rd day, 2 patients", "en"), ["3", "2"])
    check("fr list numbering role", [(h.normalized, h.role_hint) for h in L.find_numbers("1. Première priorité : 12 items", "fr")],
          [("1", "numbering"), ("12", None)])
    check("fr year at paragraph start is not numbering", [h.role_hint for h in L.find_numbers("2023 fut une année", "fr")], ["year"])
    check("heading '7. Références'", bool(L.HEADING_REFS.match("7. Références")), True)
    check("heading 'Bibliography'", bool(L.HEADING_REFS.match("Bibliography")), True)
    check("heading 'قائمة المراجع'", bool(L.HEADING_REFS.match("قائمة المراجع")), True)
    check("'Annexe A' paragraph is not a reference", L.looks_like_reference("Annexe A. Questionnaire QEPIM (version française)"), False)
    check("'Box GEP … 1970.' is a reference", L.looks_like_reference("Box GEP, Jenkins GM. Time series analysis. San Francisco: Holden-Day; 1970."), True)
    # --- E.2 French source with a numbered heading, a wrapped entry, annexes without heading style, a content
    #         control around the reference list and a text box ---------------------------------------------------
    d = docx.Document()
    ref_pars = []
    for kind, content in E_FR:
        if kind == "h":
            d.add_heading(content, level=1)
        elif kind == "p":
            par = d.add_paragraph(content)
            if content.startswith(("1. Ajam", "2. Soufi", "2010;", "3. Box")):
                ref_pars.append(par)
            if content.startswith("Le score moyen"):
                _add_textbox(par, "Encadré 1. Flux des participants : 180 invités, 150 répondants.")
        else:
            t = d.add_table(rows=len(content), cols=len(content[0]))
            for i, row in enumerate(content):
                for j, c in enumerate(row):
                    t.cell(i, j).text = c
    _wrap_in_sdt(d, ref_pars)
    d.save("e_source.docx")
    check("extract", run(s("extract_ledger.py"), "--project", "D99-T07", "--empirical", "e_source.docx", "--out", "e_ledger.json"), 0)
    led = L.load_json("e_ledger.json")
    refs = [it for it in led["items"] if it["kind"] == "reference"]
    check("3 reference entries (a wrapped entry merged), the annexes excluded (SD-1)", len(refs), 3)
    check("wrapped entry merged", refs[1]["text"].endswith("doi:10.1186/1472-6963-10-149"), True)
    check("DOI read from the merged entry", refs[1]["doi"], "10.1186/1472-6963-10-149")
    check("reference list read inside the content control", refs[0]["text"].startswith("Ajam A"), True)
    led_nums = [it["normalized"] for it in led["items"] if it["kind"] == "number"]
    check("annex numbers are in the ledger (SD-1)", all(n in led_nums for n in ("24", "5", "1", "5")), True)
    check("text-box numbers are in the ledger, once", (led_nums.count("180"), led_nums.count("150")), (1, 2))
    check("ordinal 1er read in the source", "1" in led_nums, True)
    roles = {it["normalized"]: it.get("role_hint") for it in led["items"] if it["kind"] == "number" and it.get("role_hint") == "numbering"}
    check("list numbers tagged 'numbering'", sorted(roles), ["1", "2"])
    cits = {it["key"]: it["occurrences"] for it in led["items"] if it["kind"] == "citation"}
    check("citations counted in text and tables", cits, {"[1]": 1, "[2]": 2, "[3]": 2})
    tables = [it for it in led["items"] if it["kind"] == "table"]
    check("two tables, the annex table included", len(tables), 2)
    # --- E.3 the English and Arabic targets reconcile with zero finding (SD-1, SD-2, numbering, ordinals) -------
    open("e_EN.md", "w", encoding="utf-8").write(E_EN_MD)
    open("e_AR.md", "w", encoding="utf-8").write(E_AR_MD)
    for lang in ("en", "ar"):
        check(f"build {lang}", run(s("build_docx_from_md.py"), "--md", f"e_{lang.upper()}.md", "--lang", lang, "--out", f"e_{lang.upper()}.docx"), 0)
        rc = run(s("reconcile_ledger.py"), "translation", "--ledger", "e_ledger.json", "--paper", "empirical",
                 "--target", f"e_{lang.upper()}.docx", "--locale", lang, "--out", f"e_recon_{lang}.json")
        rep = L.load_json(f"e_recon_{lang}.json")
        check(f"reconcile {lang}: exit 0", rc, 0)
        check(f"reconcile {lang}: nothing missing", rep["ledger"]["missing"], [])
        check(f"reconcile {lang}: nothing introduced", rep["ledger"]["introduced"], [])
        check(f"reconcile {lang}: tables ok", rep["tables"]["mismatches"], [])
        check(f"reconcile {lang}: references 3/3 verbatim", rep["references"]["verbatim"], 3)
        check(f"reconcile {lang}: citations ok", rep["citations"]["mismatches"], [])
    open("e_cit.md", "w", encoding="utf-8").write("# النتائج\n\nكما أظهرت دراسات سابقة [29–33] أن النسبة بلغت 78.8%.\n")
    check("build ar citation", run(s("build_docx_from_md.py"), "--md", "e_cit.md", "--lang", "ar", "--out", "e_cit.docx"), 0)
    ar_runs = [r.text for p in docx.Document("e_cit.docx").paragraphs for r in p.runs]
    check("Arabic citation with a range typeset as one LTR unit (SD-2)", any(r.strip() == "\u202a[29–33]\u202c" for r in ar_runs), True)
    check("… and read back as a citation", L.find_citations(L.docx_plain_text("e_cit.docx")),
          {"[29]": 1, "[30]": 1, "[31]": 1, "[32]": 1, "[33]": 1})
    # --- E.4 glossary: a French term kept verbatim in a reference title is not an inconsistency -------------------
    gloss = {"entries": [{"id": "G-1", "term_fr": "accueil", "term_en": "reception", "term_ar": "استقبال", "category": "concept"},
                         {"id": "G-2", "term_fr": "cross-sectional study", "term_en": "cross-sectional study", "term_ar": "دراسة مقطعية", "category": "design"}]}
    L.save_json(gloss, "e_gloss.json")
    check("glossary check runs", run(s("check_glossary.py"), "--glossary", "e_gloss.json", "--source", "e_source.docx",
                                     "--target", "e_AR.docx", "--lang", "ar", "--out", "e_gloss_ar.json"), 0)
    g = L.load_json("e_gloss_ar.json")
    check("term present only in a reference title is not checked; body term checked and consistent",
          ([e["id"] for e in g["all"]], g["flagged"]), (["G-1"], 0))
    # --- E.5 parser gate: a v3 ledger is accepted with a note, a v2 ledger is refused ----------------------------
    v3 = dict(led); v3["parser_version"] = "3"; L.save_json(v3, "e_ledger_v3.json")
    check("v3 ledger accepted (exit 0)", run(s("reconcile_ledger.py"), "translation", "--ledger", "e_ledger_v3.json", "--paper", "empirical",
                                            "--target", "e_EN.docx", "--locale", "en", "--out", "e_recon_v3.json"), 0)
    v2 = dict(led); v2["parser_version"] = "2"; L.save_json(v2, "e_ledger_v2.json")
    check("v2 ledger refused (exit 2)", run(s("reconcile_ledger.py"), "translation", "--ledger", "e_ledger_v2.json", "--paper", "empirical",
                                           "--target", "e_EN.docx", "--locale", "en", "--out", "e_recon_v2.json"), 2)
    # --- E.6 a reference list that ends with an acknowledgement typed as a plain paragraph ------------------------
    blocks = [{"kind": "heading", "text": "Références"},
              {"kind": "paragraph", "text": "1. Cox JL. Detection of postnatal depression. Br J Psychiatry. 1987;150:782-6."},
              {"kind": "paragraph", "text": "Remerciements"},
              {"kind": "paragraph", "text": "Nous remercions les 150 participants."}]
    check("acknowledgement ends the reference list", [r for _, r in L.walk_blocks(blocks)], [False, True, False, False])
    blocks = [{"kind": "heading", "text": "Références"},
              {"kind": "paragraph", "text": "1. Soufi G, et al. Determinants of satisfaction. BMC Health Serv Res."},
              {"kind": "paragraph", "text": "2010;10:149."},
              {"kind": "paragraph", "text": "2. Cox JL. Detection of postnatal depression. Br J Psychiatry. 1987;150:782-6."}]
    check("a wrapped entry stays in the reference list", [r for _, r in L.walk_blocks(blocks)], [False, True, True, True])


def _add_inline_sdt(paragraph, text: str) -> None:
    """An in-text citation inserted by Word's citation manager: an inline content control around a run."""
    from lxml import etree
    sdt = etree.SubElement(paragraph._p, _w("sdt"))
    etree.SubElement(sdt, _w("sdtPr"))
    content = etree.SubElement(sdt, _w("sdtContent"))
    etree.SubElement(etree.SubElement(content, _w("r")), _w("t")).text = text


def _add_tracked(paragraph, inserted: str, deleted: str) -> None:
    from lxml import etree
    ins = etree.SubElement(paragraph._p, _w("ins"), {_w("id"): "901", _w("author"): "x", _w("date"): "2026-10-06T00:00:00Z"})
    etree.SubElement(etree.SubElement(ins, _w("r")), _w("t")).text = inserted
    dl = etree.SubElement(paragraph._p, _w("del"), {_w("id"): "902", _w("author"): "x", _w("date"): "2026-10-06T00:00:00Z"})
    etree.SubElement(etree.SubElement(dl, _w("r")), _w("delText")).text = deleted


F_EN_MD = """# Results

Data were collected from 6 October 2025 to 30 November 2025 among 150 patients [1]. The response rate was 78.8% [2].

## 2.3 Statistical analysis

Scores are given as mean ± SD; the 95% CI is given in brackets.

| Variable | OR | 95% CI | p |
|---|---|---|---|
| Reception | 1.85 | [1.20–2.86] | 0.004 |

Table 1. Associated factors.

## References

1. Ajam A, et al. Patient satisfaction in radiology. J Radiol. 2017;12(3):441-9.
2. Soufi G, et al. Determinants of satisfaction. BMC Health Serv Res. 2010;10:149.
"""


def part_f(work: str) -> None:
    """v0.2.7 — Word features of real student files: merged cells, tracked insertions, inline citation fields,
    numeric dates, numbered headings typed as plain text, and --ignore for the title block."""
    import docx
    s = lambda n: os.path.join(SCRIPTS, n)  # noqa: E731
    os.chdir(work)
    print("F. v0.2.7 — merged cells, tracked changes, citation fields, dates, plain-text numbered headings, --ignore")
    d = docx.Document()
    d.add_paragraph("Année universitaire 2025/2026")  # title block, to be ignored
    d.add_heading("3. Résultats", level=1)
    par = d.add_paragraph("Les données ont été collectées du 06/10/2025 au 30/11/2025 auprès de 150 patients ")
    _add_inline_sdt(par, "[1]")
    par.add_run(". Le taux de réponse était de 78,8 % ")
    _add_inline_sdt(par, "[2]")
    par.add_run(".")
    _add_tracked(par, "", " ancienne phrase avec 999 patients")
    d.add_paragraph("2.3 Analyse statistique")  # plain-text numbered heading (no style, not bold)
    par2 = d.add_paragraph("Les scores sont donnés en moyenne ± ")
    _add_tracked(par2, "ET ; l’IC 95 % est donné entre crochets.", "écart-type.")
    t = d.add_table(rows=2, cols=4)
    hdr = t.cell(0, 1).merge(t.cell(0, 2))
    t.cell(0, 0).text = "Variable"; hdr.text = "OR [IC 95 %]"; t.cell(0, 3).text = "p"
    t.cell(1, 0).text = "Accueil"; t.cell(1, 1).text = "1,85"; t.cell(1, 2).text = "[1,20–2,86]"; t.cell(1, 3).text = "0,004"
    d.add_paragraph("Tableau 1. Facteurs associés.")
    d.add_heading("Références", level=1)
    d.add_paragraph("1. Ajam A, et al. Patient satisfaction in radiology. J Radiol. 2017;12(3):441-9.")
    d.add_paragraph("2. Soufi G, et al. Determinants of satisfaction. BMC Health Serv Res. 2010;10:149.")
    d.save("f_source.docx")
    blocks = L.docx_text_blocks("f_source.docx")
    check("plain-text '2.3 Analyse statistique' is a heading", [b["text"] for b in blocks if b["kind"] == "heading"],
          ["3. Résultats", "2.3 Analyse statistique", "Références"])
    tbl = next(b for b in blocks if b["kind"] == "table")
    check("merged header cell read once", tbl["cells"][0], ["Variable", "OR [IC 95 %]", "", "p"])
    check("extract", run(s("extract_ledger.py"), "--project", "D99-T08", "--empirical", "f_source.docx", "--out", "f_ledger.json"), 0)
    led = L.load_json("f_ledger.json")
    cits = {it["key"]: it["occurrences"] for it in led["items"] if it["kind"] == "citation"}
    check("citations inside Word citation fields are read", cits, {"[1]": 1, "[2]": 1})
    nums = {it["normalized"]: it for it in led["items"] if it["kind"] == "number"}
    check("tracked deletion ignored, tracked insertion read", ("999" in nums, "95" in nums), (False, True))
    check("numeric dates read as dates", sorted(k for k, it in nums.items() if it.get("role_hint") == "date"), ["30-11-2025", "6-10-2025"])
    check("date components are not loose numbers", any(k in nums for k in ("6", "10", "11", "30")), False)
    tnum = next(it for it in led["items"] if it["kind"] == "table")["numbers_normalized"]
    check("table numbers: 95 counted once despite the merge", tnum.count("95"), 1)
    open("f_EN.md", "w", encoding="utf-8").write(F_EN_MD)
    check("build en", run(s("build_docx_from_md.py"), "--md", "f_EN.md", "--lang", "en", "--out", "f_EN.docx"), 0)
    rc = run(s("reconcile_ledger.py"), "translation", "--ledger", "f_ledger.json", "--paper", "empirical", "--target", "f_EN.docx",
             "--locale", "en", "--ignore", "2025/2026", "--out", "f_recon.json")
    rep = L.load_json("f_recon.json")
    check("reconcile en: exit 0", rc, 0)
    check("reconcile en: nothing missing (dates in words are not missing numbers)", rep["ledger"]["missing"], [])
    check("reconcile en: nothing introduced", rep["ledger"]["introduced"], [])
    check("reconcile en: table ok despite the merged header", rep["tables"]["mismatches"], [])
    check("reconcile en: citations ok", rep["citations"]["mismatches"], [])
    check("dates listed for the eye", sorted(d["normalized"] for d in rep["ledger"]["dates_to_verify_by_hand"]), ["30-11-2025", "6-10-2025"])
    check("--ignore recorded", rep["ledger"]["ignored"], ["2025", "2026"])
    rc2 = run(s("reconcile_ledger.py"), "translation", "--ledger", "f_ledger.json", "--paper", "empirical", "--target", "f_EN.docx",
              "--locale", "en", "--out", "f_recon2.json")
    rep2 = L.load_json("f_recon2.json")
    check("without --ignore the title-block year is reported missing", [m["normalized"] for m in rep2["ledger"]["missing"]], ["2025", "2026"])


def part_g(work: str) -> None:
    """v0.2.7 — reference entries typed with hand bullets (a Symbol-font glyph, "•", "-"), sub-indexed entries
    ("[5b]"), four-letter initials, and the carry-over of a reference link by text when the entries are re-split."""
    import docx
    s = lambda n: os.path.join(SCRIPTS, n)  # noqa: E731
    os.chdir(work)
    print("G. v0.2.7 — hand bullets, [5b], four initials, reference carry-over by text")
    d = docx.Document()
    d.add_heading("Résultats", level=1)
    d.add_paragraph("Le taux était de 45 % [1], [5].")
    d.add_heading("Références", level=1)
    d.add_paragraph("\uf0b7  Jang, J., Yu, S. H., & Kim, S. (2013). The effects of an electronic record. Int J Med Inform, 82(8), 702-707.")
    d.add_paragraph("\uf0b7  Dusse, F., Pütz, J., & Wappler, F. (2021). Completeness of the handover. BMC Anesthesiol, 21, 15.")
    d.add_paragraph("• de Freitas BHBM, et al. Brazilian version of the school health survey. Rev Saude Publica. 2022;56:1-9.")
    d.add_paragraph("[5] El Mansouri N, Moujabber M, et al. Awareness of HPV among students in Morocco. PLoS ONE. 2022.")
    d.add_paragraph("[5b] Yacouti A, Elkhoudri N, et al. Acceptability of the HPV vaccine. PLoS ONE. 2022;17(4):e0266081.")
    d.add_paragraph("- Chu TCC, et al. International consensus on school health literacy. Health Promot Int. 2024;39(1):daad170.")
    d.save("g_source.docx")
    check("extract", run(s("extract_ledger.py"), "--project", "D99-T09", "--empirical", "g_source.docx", "--out", "g_ledger.json"), 0)
    led = L.load_json("g_ledger.json")
    refs = [it for it in led["items"] if it["kind"] == "reference"]
    check("six entries, none merged into its neighbour", len(refs), 6)
    check("bullets and glyphs dropped from the entry text", [r["text"][:8] for r in refs],
          ["Jang, J.", "Dusse, F", "de Freit", "El Manso", "Yacouti ", "Chu TCC,"])
    check("[5] and [5b] both read with index 5", [r["index"] for r in refs], [1, 2, 3, 5, 5, 6])
    check("no private-use glyph survives in the ledger", any("\uf0b7" in r["text"] for r in refs), False)
    # carry-over: an old ledger whose parser had merged Dusse into Jang and lost the bullets — the claim linked to
    # "Dusse" must follow the Dusse entry by its text, not land on another entry by position
    old = dict(led)
    old["parser_version"] = "3"
    old_refs = [dict(r) for r in refs]
    jang = next(r for r in old_refs if r["text"].startswith("Jang"))
    dusse = next(r for r in old_refs if r["text"].startswith("Dusse"))
    jang["text"] = jang["text"] + " " + dusse["text"]        # the old parser merged the two entries
    old_refs = [r for r in old_refs if r is not dusse]
    for i, r in enumerate(old_refs, 1):                        # and numbered them by position
        r["index"] = i
    claim = {"id": "E-CL-0001", "paper": "empirical", "kind": "claim", "section": "Résultats", "text_fr": "Handover incomplet.",
             "direction": "positive", "strength": "confirmatory", "hedge": "", "linked_items": [jang["id"], old_refs[-1]["id"]],
             "extracted_by": "assistant", "student_confirmed": True}
    old["items"] = [it for it in led["items"] if it["kind"] != "reference"] + old_refs + [claim]
    L.save_json(old, "g_ledger_old.json")
    check("rebuild with --carry-over", run(s("extract_ledger.py"), "--project", "D99-T09", "--empirical", "g_source.docx",
                                           "--out", "g_ledger_new.json", "--carry-over", "g_ledger_old.json"), 0)
    new = L.load_json("g_ledger_new.json")
    ids = {it["id"]: it for it in new["items"]}
    kept = next(it for it in new["items"] if it["kind"] == "claim")
    linked = sorted(ids[x]["text"][:8] for x in kept["linked_items"])
    check("links follow the entries by text (merged head → Jang, last → Chu)", linked, ["Chu TCC,", "Jang, J."])
    check("no link lost", kept.get("carry_over_unmapped_links"), None)

    # superscript (Vancouver) citations, narrative author–date citations, a heading style carrying a result, a
    # reference list typed in one paragraph with soft line breaks, annotation lines inside an APA list
    d = docx.Document()
    d.add_heading("Résultats", level=1)
    par = d.add_paragraph("Le burnout touche 33 % des infirmiers.")
    r = par.add_run("4,5"); r.font.superscript = True
    par.add_run(" Williams et al. (2023) et Aiken & Clarke (2002) le confirment (Shoman, 2021). Un IMC > 30 kg/m")
    r = par.add_run("2"); r.font.superscript = True
    par.add_run(" était noté chez 12 patients.")
    r = par.add_run("7"); r.font.superscript = True
    par.add_run(" Voir aussi la synthèse.")
    r = par.add_run("12"); r.font.superscript = True
    d.add_heading("Cinq dimensions présentent un α < 0,70 : Gouvernance (0,621)", level=2)
    h = d.add_heading("2. PROBLEMATIQUE", level=1)
    h.add_run().add_break(); h.add_run("Un dossier incomplet concerne 30 % des cas.")
    d.add_heading("Références", level=1)
    one = d.add_paragraph("1. Pottie K, et al. Evidence-based guidelines. CMAJ. 2011;183(12):E824.")
    one.add_run().add_break(); one.add_run("2. Tugwell P; Canadian Collaboration for Immigrant Health.")
    one.add_run().add_break(); one.add_run("Evaluation of evidence. CMAJ. 2011;183(12):E933.")
    one.add_run().add_break(); one.add_run("3. Vo V et al. (2023). Multi-stakeholder preferences. BMJ Open. 2023;13:e1.")
    d.save("g2_source.docx")
    blocks = L.docx_text_blocks("g2_source.docx")
    heads = [b["text"] for b in blocks if b["kind"] == "heading"]
    check("a result typed in a heading style is a paragraph; the heading split from its body text",
          heads, ["Résultats", "2. PROBLEMATIQUE", "Références"])
    check("extract", run(s("extract_ledger.py"), "--project", "D99-T10", "--empirical", "g2_source.docx", "--out", "g2_ledger.json"), 0)
    led = L.load_json("g2_ledger.json")
    cits = {it["key"]: it["occurrences"] for it in led["items"] if it["kind"] == "citation"}
    check("superscript keys read as citations, the unit superscript left alone", cits,
          {"[4]": 1, "[5]": 1, "[7]": 1, "[12]": 1, "(Williams et al., 2023)": 1, "(Aiken & Clarke, 2002)": 1, "(Shoman, 2021)": 1})
    nums = [it["normalized"] for it in led["items"] if it["kind"] == "number"]
    check("the result in heading style and the body text after the soft break reach the ledger",
          all(n in nums for n in ("0.70", "0.621", "30", "33", "12")), True)
    check("superscript citation numbers are not statistics", any(n in nums for n in ("4", "5", "7")), False)
    check("kg/m² is not the citation [2]", "[2]" in cits, False)
    refs = [it for it in led["items"] if it["kind"] == "reference"]
    check("a list typed with soft line breaks is three entries", [r["index"] for r in refs], [1, 2, 3])
    check("the wrapped line stays with entry 2", refs[1]["text"].endswith("E933."), True)
    apa = ["González-Sanz, A., & López, J. (2023). Title. J, 1, 2-3.", "20 études, 12 pays.",
           "Harrison, J. (2021). Title two. J, 2, 3-4.", "Résumé de congrès ; retiré.", "Høegh-Larsen, A. M. (2023). Title three."]
    check("annotation lines in an APA list are not entries", len(L.merge_reference_fragments(apa)), 3)
    idx = ["1. Soufi G. Title. 2020.", "20 études, 12 pays.", "2. Tazi M. Title. 2021."]
    check("… nor in an indexed list (index out of sequence)", len(L.merge_reference_fragments(idx)), 2)


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
        part_e(work)
        part_f(work)
        part_g(work)
    finally:
        os.chdir(HERE)
        if not keep:
            shutil.rmtree(work, ignore_errors=True)
    print(f"\n{'ALL TESTS PASSED' if not FAILS else str(len(FAILS)) + ' TEST(S) FAILED: ' + ', '.join(FAILS)}")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
