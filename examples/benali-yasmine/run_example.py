#!/usr/bin/env python3
"""Regenerate the whole fictional example (BENALI Yasmine, D99-P01) from its text sources.

    python run_example.py [--out OUTPUT_DIR]

Runs, in order: approval gate on the bundled fictional approval PDF → French .docx from the Markdown sources → fidelity ledger (+ the claim register and the
spelled-out number the assistant adds by hand) → deck V1 + notes + timing → deck reconciliation → four
translated versions (.docx) → four reconciliations → glossary checks → issue register, soutenance lock,
QA register → attestation. Every step must end with exit code 0; the last line prints the verdict.
Output goes to --out (default: ./_generated next to this file) so the plugin folder stays small.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "..", "shared", "scripts"))
TEMPLATE = os.path.normpath(os.path.join(HERE, "..", "..", "shared", "templates", "esss_soutenance_template.pptx"))
PY = sys.executable


def run(*args, check=True) -> int:
    print("$", " ".join(os.path.basename(a) if i == 1 else a for i, a in enumerate(args)))
    rc = subprocess.call(args)
    if check and rc != 0:
        raise SystemExit(f"step failed with exit code {rc}")
    return rc


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "_generated"))
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(os.path.join(out, "sources"), exist_ok=True)
    for f in ("deck_spec.json", "glossary_fr_en_ar.json", "review_article_EN.md", "empirical_article_EN.md",
              "review_article_AR.md", "empirical_article_AR.md", "claim_register.json"):
        shutil.copy(os.path.join(HERE, f), out)
    os.chdir(out)
    s = lambda name: os.path.join(SCRIPTS, name)  # noqa: E731

    # 0. approval gate (fictional signed approval bundled with the example)
    json.dump({"first_name": "Yasmine", "family_name": "BENALI", "project_code": "D99-P01",
               "project_title": "Satisfaction au travail et intention de rester chez les infirmiers : revue systématique régionale et étude transversale à Casablanca",
               "interaction_language": "fr", "pipeline_progress": []},
              open("student_project_profile.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    shutil.copy(os.path.join(HERE, "APP4-BENALI-Yasmine-SPECIMEN.pdf"), out)
    run(PY, s("verify_approval.py"), "--pdf", "APP4-BENALI-Yasmine-SPECIMEN.pdf", "--profile", "student_project_profile.json",
        "--out", "approval_check.json")
    approval = json.load(open("approval_check.json", encoding="utf-8"))["approval"]
    approval.update({"verdict": "valid", "visual_check": "letterhead and signature seen (fictional example)",
                     "verified_at": "2026-06-15T09:00:00+00:00", "verified_by_step": "Yassin_P4_01_Soutenance_V1"})
    prof = json.load(open("student_project_profile.json", encoding="utf-8"))
    prof["p4_approval_reference"] = approval["reference"]
    json.dump(prof, open("student_project_profile.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 1. French sources
    run(PY, s("build_docx_from_md.py"), "--md", os.path.join(HERE, "sources", "revue_FINAL_FR.md"), "--lang", "fr", "--out", "sources/revue_FINAL_FR.docx")
    run(PY, s("build_docx_from_md.py"), "--md", os.path.join(HERE, "sources", "article_FINAL_FR.md"), "--lang", "fr", "--out", "sources/article_FINAL_FR.docx")
    # 2. ledger + assistant items
    run(PY, s("extract_ledger.py"), "--project", "D99-P01", "--review", "sources/revue_FINAL_FR.docx",
        "--empirical", "sources/article_FINAL_FR.docx", "--out", "fidelity_ledger.json", "--text-dump", "_p4_text")
    ledger = json.load(open("fidelity_ledger.json", encoding="utf-8"))
    extra = json.load(open("claim_register.json", encoding="utf-8"))
    ledger["items"].extend(extra["items"])
    for p in ("review", "empirical"):
        ledger["summary"][p]["claims"] = sum(1 for it in extra["items"] if it["paper"] == p and it["kind"] == "claim")
        ledger["summary"][p]["numbers"] += sum(1 for it in extra["items"] if it["paper"] == p and it["kind"] == "number")
    json.dump(ledger, open("fidelity_ledger.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    # 3. deck
    run(PY, s("build_deck.py"), "--spec", "deck_spec.json", "--template", TEMPLATE, "--out", "soutenance_deck_V1.pptx",
        "--notes-docx", "soutenance_notes_V1.docx", "--timing", "timing_V1.json")
    run(PY, s("reconcile_ledger.py"), "deck", "--ledger", "fidelity_ledger.json", "--target", "soutenance_deck_V1.pptx",
        "--locale", "fr", "--ignore", "2025/2026", "--out", "recon_deck_V1.json")
    # 4. translations
    for paper in ("review", "empirical"):
        for lang in ("en", "ar"):
            md = f"{paper}_article_{lang.upper()}.md"
            docx = f"{paper}_article_{lang.upper()}.docx"
            run(PY, s("build_docx_from_md.py"), "--md", md, "--lang", lang, "--out", docx)
            run(PY, s("reconcile_ledger.py"), "translation", "--ledger", "fidelity_ledger.json", "--paper", paper,
                "--target", docx, "--locale", lang, "--out", f"recon_{paper}_{lang.upper()}.json")
            run(PY, s("check_glossary.py"), "--glossary", "glossary_fr_en_ar.json", "--source", f"_p4_text/{paper}.txt",
                "--target", docx, "--lang", lang, "--out", f"gloss_{paper}_{lang.upper()}.json")
    # 5. lock + registers (as p4-02 / p4-05 would write them after closure and sign-off)
    shutil.copy("soutenance_deck_V1.pptx", "soutenance_deck_FINAL.pptx")
    shutil.copy("soutenance_notes_V1.docx", "soutenance_notes_FINAL.docx")
    timing = json.load(open("timing_V1.json", encoding="utf-8"))
    recon = json.load(open("recon_deck_V1.json", encoding="utf-8"))
    lock = {"lock": {"locked": True, "locked_at": "2026-06-15T11:00:00+00:00", "locked_by_step": "Yassin_P4_02_Soutenance_CA_Lock"},
            "project_id": "D99-P01", "approval_reference": approval["reference"],
            "deck": {"file": "soutenance_deck_FINAL.pptx", "sha256": sha("soutenance_deck_FINAL.pptx"), "slides": timing["slides"]},
            "notes": {"file": "soutenance_notes_FINAL.docx", "sha256": sha("soutenance_notes_FINAL.docx")},
            "timing": {"presentation_minutes": timing["target_minutes"], "estimated_minutes": timing["estimated_minutes"]},
            "ledger_reconciliation": {"items_on_slides": recon["covered_distinct"], "matched": recon["covered_distinct"], "unmatched": 0},
            "issues_closed": {"major": 0, "minor": 1, "suggestion": 1, "open": 0},
            "frozen": ["slide content", "speaker notes content", "figures and tables shown", "claims and their hedges"],
            "editable_after_lock": ["oral delivery", "rehearsal timing", "cosmetic fixes that change no word or value"],
            "student_signoff": {"name": "Yasmine BENALI", "date": "2026-06-15",
                                "statement": "Je confirme que ce diaporama reflète fidèlement mes deux articles et que je suis en mesure de défendre chaque diapositive."}}
    json.dump(lock, open("soutenance_lock.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    qa = {"project_id": "D99-P01", "approval_reference": approval["reference"], "appraised_at": "2026-06-15T11:30:00+00:00", "targets": {}}
    for paper in ("review", "empirical"):
        for lang in ("EN", "AR"):
            r = json.load(open(f"recon_{paper}_{lang}.json", encoding="utf-8"))
            qa["targets"][f"{paper}_{lang}"] = {"file": r["target"], "sha256": r["target_sha256"],
                                               "ledger": {"expected": r["ledger"]["expected_distinct"], "matched": r["ledger"]["matched"]},
                                               "issues": [], "verdict": "attestable"}
    json.dump(qa, open("translation_qa_register.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump({"project_id": "D99-P01", "student": {"first_name": "Yasmine", "family_name": "BENALI", "name_ar": "ياسمين بنعلي"},
               "approval": approval,
               "sources": {k: {"file": v["file"], "sha256": v["sha256"], "language": "fr"} for k, v in ledger["sources"].items()},
               "conventions": {"english_spelling": "british", "arabic_digits": "ascii", "citation_style": "numeric"},
               "soutenance": {"language": "fr", "presentation_minutes": 15, "questions_minutes": 15, "rules_source": "ESSS default (fictional example)"}},
              open("p4_source_manifest.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    # 6. attestation
    rc = run(PY, s("issue_attestation.py"), "--project", "D99-P01", "--manifest", "p4_source_manifest.json", "--ledger", "fidelity_ledger.json",
             "--lock", "soutenance_lock.json", "--qa", "translation_qa_register.json",
             "--deliverable", "review_article_EN.docx=recon_review_EN.json",
             "--deliverable", "empirical_article_EN.docx=recon_empirical_EN.json",
             "--deliverable", "review_article_AR.docx=recon_review_AR.json",
             "--deliverable", "empirical_article_AR.docx=recon_empirical_AR.json",
             "--student", "Yasmine BENALI", "--date", "2026-06-15", "--out", "p4_attestation.json")
    print("\nEXAMPLE COMPLETE —", "attestation issued" if rc == 0 else "attestation refused", "→", out)
    return rc


if __name__ == "__main__":
    sys.exit(main())
