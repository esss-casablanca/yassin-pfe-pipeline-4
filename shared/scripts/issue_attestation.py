#!/usr/bin/env python3
"""issue_attestation.py — assemble p4_attestation.json from the reconciliation reports and the lock (p4-05).

Usage:
  python issue_attestation.py --project D03-P01 --manifest p4_source_manifest.json --ledger fidelity_ledger.json \
      --lock soutenance_lock.json --qa translation_qa_register.json \
      --deliverable review_article_EN.docx=recon_review_EN.json \
      --deliverable empirical_article_EN.docx=recon_empirical_EN.json \
      --deliverable review_article_AR.docx=recon_review_AR.json \
      --deliverable empirical_article_AR.docx=recon_empirical_AR.json \
      --student "Prénom NOM" --date 2026-06-15 --out p4_attestation.json

Refuses to issue (exit 1) when: the manifest carries no valid Pipeline-4 approval, a reconciliation report has major_findings > 0, a report's target_sha256 differs
from the file on disk (the file changed after its check), the soutenance lock is not locked, or the QA register
has an open issue.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p4lib as L  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--lock", required=True)
    ap.add_argument("--qa", required=True)
    ap.add_argument("--deliverable", action="append", required=True, help="<file>=<recon json>")
    ap.add_argument("--student", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    manifest, ledger, lock, qa = (L.load_json(p) for p in (a.manifest, a.ledger, a.lock, a.qa))
    problems: list[str] = []
    approval = manifest.get("approval") or {}
    if approval.get("verdict") != "valid" or not approval.get("reference"):
        problems.append("no valid Pipeline-4 approval recorded in p4_source_manifest.json (approval.reference / verdict)")
    elif lock.get("approval_reference") and lock["approval_reference"] != approval["reference"]:
        problems.append("the soutenance lock carries a different approval reference than the manifest")
    if not lock.get("lock", {}).get("locked"):
        problems.append("soutenance_lock.json is not locked")
    open_issues = []
    for tname, t in qa.get("targets", {}).items():
        for iss in t.get("issues", []):
            if iss.get("status") != "closed":
                open_issues.append(f"{tname}:{iss.get('id')}")
    if open_issues:
        problems.append("open QA issues: " + ", ".join(open_issues))

    deliverables = {}
    for spec in a.deliverable:
        f, rep_path = spec.split("=", 1)
        rep = L.load_json(rep_path)
        if not os.path.exists(f):
            problems.append(f"missing deliverable {f}")
            continue
        sha = L.sha256_file(f)
        if rep.get("target_sha256") and rep["target_sha256"] != sha:
            problems.append(f"{f} changed after its reconciliation ({rep_path})")
        if rep.get("major_findings", 0) > 0:
            problems.append(f"{f}: {rep['major_findings']} Major finding(s) in {rep_path}")
        lg = rep.get("ledger", {})
        deliverables[os.path.basename(f)] = {
            "sha256": sha, "paper": rep.get("paper"), "locale": rep.get("locale"),
            "ledger_matched": f"{lg.get('matched', 0)}/{lg.get('expected_distinct', 0)}",
            "tables_ok": f"{rep.get('tables', {}).get('expected', 0) - len(rep.get('tables', {}).get('mismatches', []))}/{rep.get('tables', {}).get('expected', 0)}",
            "references_verbatim": f"{rep.get('references', {}).get('verbatim', 0)}/{rep.get('references', {}).get('expected', 0)}",
            "verdict": "attestable" if rep.get("major_findings", 0) == 0 else "not attestable",
        }
    deck = lock.get("deck", {})
    if deck.get("file") and os.path.exists(deck["file"]):
        sha = L.sha256_file(deck["file"])
        if deck.get("sha256") and deck["sha256"] != sha:
            problems.append("the locked deck changed after the lock")
        deliverables[deck["file"]] = {"sha256": sha, "lock": "soutenance_lock.json"}

    att = {
        "attestation": {"issued": not problems,
                        "issued_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                        "issued_by_step": "Yassin_P4_05_Translation_QA_Attestation"},
        "project_id": a.project,
        "approval_reference": approval.get("reference"),
        "approval": {k: approval.get(k) for k in ("reference", "date_iso", "verification_code", "file", "sha256")},
        "sources": {k: {"file": v.get("file"), "sha256": v.get("sha256")} for k, v in ledger.get("sources", {}).items()},
        "ledger_sha256": L.sha256_file(a.ledger),
        "deliverables": deliverables,
        "statement": ("No frozen value, table value, citation, reference or claim of the two French sources was "
                      "altered in the deck or in the four translated versions; terminology is consistent with "
                      "glossary_fr_en_ar.json."),
        "student_signoff": {"name": a.student, "date": a.date},
        "pfe_complete": not problems,
        "refusal_reasons": problems,
    }
    L.save_json(att, a.out)
    if problems:
        print("ATTESTATION REFUSED:")
        for p in problems:
            print("  -", p)
        return 1
    print(f"attestation issued: {a.out} ({len(deliverables)} deliverables)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
