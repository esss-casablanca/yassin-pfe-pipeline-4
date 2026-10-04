# Pipeline-4 helper scripts

All scripts run on the student's or supervisor's machine inside Cowork with Python ≥ 3.10, `python-docx` ≥ 1.1,
`python-pptx` ≥ 1.0 and `Pillow`. They never call the network. Paths are passed explicitly; nothing is hard-coded.

| Script | Used by | Purpose |
|--------|---------|---------|
| `p4lib.py` | all | locale-aware number normalisation (fr / en / ar), citation parsing, .docx and .pptx text walking, SHA-256 |
| `verify_approval.py` | p4-01 | checks the uploaded *Autorisation d'accès au Pipeline 4* (reference format, verification code recomputed from reference + project + name + date, match with the profile, SHA-256) and writes `approval_check.json`; exit 2 when the fields must be typed by hand (no text layer) |
| `extract_ledger.py` | p4-01 | build `fidelity_ledger.json` from the two final French papers (numbers, tables, figures, citations, references); `--text-dump` writes the papers as plain text for section-by-section reading |
| `build_deck.py` | p4-01, p4-02 | build the soutenance deck from `deck_spec.json` on the ESSS template; writes speaker notes into the slides, a printable notes script (.docx) and a timing/lint report (.json) |
| `reconcile_ledger.py deck` | p4-02 | every number on a slide must exist in the ledger (introduced numbers = Major) |
| `build_docx_from_md.py` | p4-03, p4-04 | typeset a translated paper from Markdown into .docx; `--lang ar` produces a true RTL document |
| `reconcile_ledger.py translation` | p4-03, p4-04, p4-05 | every ledger number, table value, citation key and reference entry of the paper must be present and unchanged in the translated version; numbers absent from the source are flagged |
| `check_glossary.py` | p4-05 | every glossary term present in the French source must appear in the target with its fixed equivalent (and its Latin acronym when so decided) |
| `issue_attestation.py` | p4-05 | assembles `p4_attestation.json` (carrying the approval reference); refuses when the manifest has no valid approval, a reconciliation has a Major finding, a file changed after its check, a QA issue is open, or the soutenance lock is not locked |

Exit codes of `reconcile_ledger.py`: 0 = no Major finding, 1 = Major findings, 2 = usage error **or a ledger built
with an older number parser** (v0.2.3 or before). The JSON report is the record; the skill reads it and turns each
finding into an issue-register entry.

**Number parser v2 (v0.2.4).** `fidelity_ledger.json` carries `parser_version`. When `reconcile_ledger.py` stops with
exit 2, rebuild the ledger without losing the claim register:
`extract_ledger.py --project <code> --review <fr.docx> --empirical <fr.docx> --out fidelity_ledger.json --text-dump _p4_text --carry-over <copy of the old ledger>`.
The `carry_over` block of the new ledger lists any claim link that could not be remapped: re-link it with the
student before re-running the checks. Regression tests: `python tests/test_number_parser_v2.py`.

What the scripts cannot judge: the **hedge and strength of claims** (the claim register is compared by the
assistant), figure *images* (the assistant compares the figure's values with the ledger figure item), and the
visual rendering in Word/PowerPoint (always open the file once before sign-off — Arabic bidi punctuation can
need a manual nudge).
