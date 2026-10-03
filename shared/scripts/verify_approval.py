#!/usr/bin/env python3
"""verify_approval.py — check the signed "Autorisation d'accès au Pipeline 4" the student uploads (p4-01, STEP 0).

Usage:
  python verify_approval.py --pdf APP4-NOM-Prenom-V1-Flat.pdf --profile student_project_profile.json --out approval_check.json
  python verify_approval.py --pdf <file> --ref APP-P4-KY-2026/012 --project D12-P05 --name "NOM Prénom" \
        --date-iso 2026-10-03 --vcode ABCDE-12345 --profile … --out …       (fields typed by hand when the PDF has no text layer)

What it checks (exit 0 = valid, 1 = invalid, 2 = unverifiable without the hand-typed fields):
  - the document is the Pipeline-4 approval (title and signatory present);
  - the reference has the form APP-P4-KY-<year>/<NNN>;
  - the verification code printed on the letter equals SHA-256("ESSS-P4|<ref>|<project>|<NOM PRENOM ascii upper>|<date ISO>")[:10]
    formatted XXXXX-XXXXX — i.e. reference, project code, student name and date were not altered;
  - the project code and the student name match student_project_profile.json (when given);
  - the file's SHA-256 is recorded so later steps can detect a swapped file.
What it cannot check: that the signature is genuine and that the letter was really issued by Dr Yassin — the
assistant looks at the rendered page (signature present, ESSS letterhead) and Dr Yassin's registry is the authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata

REF_RE = re.compile(r"APP-P4-KY-(\d{4})/(\d{3})")
CODE_LINE_RE = re.compile(r"Code de v[ée]rification\s*:\s*([A-Z0-9]{5}-[A-Z0-9]{5})\s*\(\s*(APP-P4-KY-\d{4}/\d{3})\s*[·•\-]\s*([A-Z]\d{2}-P?\d{2})\s*[·•\-]\s*(\d{4}-\d{2}-\d{2})\s*\)")
STUDENT_RE = re.compile(r"[ÉE]tudiant\(e\)\s*:\s*(.+?)\s+—\s+Cycle", re.S)
TITLE_RE = re.compile(r"AUTORISATION D'ACC[ÈE]S AU PIPELINE 4", re.I)
SIGNATORY_RE = re.compile(r"Dr Khaled Yassin")


def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().upper()


def verification_code(ref: str, project: str, name: str, date_iso: str) -> str:
    payload = "ESSS-P4|" + "|".join([ref.strip(), project.strip().upper(), norm_name(name), date_iso.strip()])
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:10].upper()
    return h[:5] + "-" + h[5:]


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pdf_text(path: str) -> tuple[str, int]:
    """Return (text, number of pages). Tries pypdf, then the pdftotext command."""
    try:
        from pypdf import PdfReader
        r = PdfReader(path)
        return "\n".join((pg.extract_text() or "") for pg in r.pages), len(r.pages)
    except Exception:
        pass
    if shutil.which("pdftotext"):
        out = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True)
        if out.returncode == 0:
            return out.stdout, out.stdout.count("\f") + 1
    return "", 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--profile")
    ap.add_argument("--ref"); ap.add_argument("--project"); ap.add_argument("--name"); ap.add_argument("--date-iso"); ap.add_argument("--vcode")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    res = {"file": os.path.basename(a.pdf), "sha256": sha256_file(a.pdf) if os.path.exists(a.pdf) else None,
           "text_layer": False, "pages": 0, "checks": {}, "verdict": "unverifiable"}
    if not os.path.exists(a.pdf):
        res["checks"]["file_exists"] = False
        json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("file not found"); return 1

    text, pages = pdf_text(a.pdf)
    text = unicodedata.normalize("NFC", text)
    res["pages"] = pages
    res["text_layer"] = bool(text.strip())

    fields = {"ref": a.ref, "project": a.project, "name": a.name, "date_iso": a.date_iso, "vcode": a.vcode}
    if res["text_layer"]:
        res["checks"]["title_present"] = bool(TITLE_RE.search(text))
        res["checks"]["signatory_present"] = bool(SIGNATORY_RE.search(text))
        m = CODE_LINE_RE.search(text)
        if m:
            fields.setdefault("vcode", None)
            fields["vcode"] = fields["vcode"] or m.group(1)
            fields["ref"] = fields["ref"] or m.group(2)
            fields["project"] = fields["project"] or m.group(3)
            fields["date_iso"] = fields["date_iso"] or m.group(4)
        sm = STUDENT_RE.search(text)
        if sm:
            fields["name"] = fields["name"] or re.sub(r"\s+", " ", sm.group(1)).strip()
        res["checks"]["code_line_found"] = bool(m)
    missing = [k for k, v in fields.items() if not v]
    res["fields"] = fields
    if missing:
        res["missing_fields"] = missing
        res["verdict"] = "unverifiable"
        json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("unverifiable — missing fields:", ", ".join(missing),
              "(no text layer: read the page image and pass --ref --project --name --date-iso --vcode)" if not res["text_layer"] else "")
        return 2

    res["checks"]["reference_format"] = bool(REF_RE.fullmatch(fields["ref"].strip()))
    recomputed = verification_code(fields["ref"], fields["project"], fields["name"], fields["date_iso"])
    res["recomputed_code"] = recomputed
    res["checks"]["verification_code_valid"] = recomputed == fields["vcode"].strip().upper()
    res["checks"]["date_format"] = bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", fields["date_iso"].strip()))

    if a.profile and os.path.exists(a.profile):
        prof = json.load(open(a.profile, encoding="utf-8"))
        pcode = str(prof.get("project_code", "")).strip().upper()
        pname = norm_name(f"{prof.get('family_name', '')} {prof.get('first_name', '')}")
        pname_rev = norm_name(f"{prof.get('first_name', '')} {prof.get('family_name', '')}")
        lname = norm_name(fields["name"])
        res["checks"]["project_matches_profile"] = (pcode == fields["project"].strip().upper()) if pcode else None
        res["checks"]["name_matches_profile"] = (lname in (pname, pname_rev)) if pname.strip() else None
    hard = [v for k, v in res["checks"].items() if v is not None]
    res["verdict"] = "valid" if all(hard) else "invalid"
    res["approval"] = {"reference": fields["ref"].strip(), "date_iso": fields["date_iso"].strip(),
                       "verification_code": fields["vcode"].strip().upper(), "student_name_on_letter": fields["name"].strip(),
                       "project_code_on_letter": fields["project"].strip().upper(), "file": res["file"], "sha256": res["sha256"]}
    json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"{res['verdict'].upper()} — {fields['ref']} · {fields['project']} · {fields['name']} · {fields['date_iso']} · code {fields['vcode']}"
          f" (recomputed {recomputed})")
    for k, v in res["checks"].items():
        if v is False:
            print("   FAILED:", k)
    return 0 if res["verdict"] == "valid" else 1


if __name__ == "__main__":
    sys.exit(main())
