# Worked example — BENALI Yasmine (fictional, project D99-P01)

A complete, fictional Pipeline-4 run used to test the scripts and to show every artifact's expected shape.
Nothing in it is real: the student, the hospitals, the numbers and the references are invented for the
demonstration (the "BENALI Yasmine" convention used across the ESSS pipelines).

`benali-yasmine/` holds only the **text sources** so that the plugin stays small:

| File | Role |
|------|------|
| `APP4-BENALI-Yasmine-SPECIMEN.pdf` | an UNSIGNED, watermarked SPÉCIMEN of the *Autorisation d'accès au Pipeline 4* (real approvals carry Dr Yassin's signature; this one deliberately does not) (reference APP-P4-KY-2026/000, verification code C93BD-101F5) that the runner verifies first, exactly as p4-01 does for a real student |
| `sources/revue_FINAL_FR.md`, `sources/article_FINAL_FR.md` | the two "final French papers" (Markdown; the runner typesets them to .docx first) |
| `claim_register.json` | what the assistant adds to the ledger by hand in p4-01: 16 claims with direction / strength / hedge, and one number written in words ("Vingt et une" → 21) |
| `deck_spec.json` | the soutenance deck: 27 slides (24 timed + 3 annexes), French speaker notes with `[⏱]` timing, 15-minute target |
| `glossary_fr_en_ar.json` | 24 validated FR/EN/AR entries |
| `review_article_EN.md`, `empirical_article_EN.md` | the English versions (British spelling, decimal point, references verbatim) |
| `review_article_AR.md`, `empirical_article_AR.md` | the Arabic versions (MSA, ASCII digits, Latin acronyms, references verbatim) |
| `run_example.py` | regenerates everything into `_generated/` (or `--out DIR`) and ends with the attestation |

Run it from anywhere:

```
python examples/benali-yasmine/run_example.py --out <some folder>
```

Expected end state: the approval verifies as **VALID**; the deck reconciliation reports **0 numbers introduced**; the four translations report
**every ledger number matched, every table ok, every reference verbatim, 0 citation mismatches**; the glossary
checks report **0 flagged**; `issue_attestation.py` prints **attestation issued (5 deliverables)**.

Two findings the scripts raised while this example was built, kept here because they are instructive:
- the paper wrote "Vingt et une études" in words — the deck's "21" was flagged as *introduced* until the
  spelled-out number was added to the ledger by hand (`claim_register.json`, `R-N-0901`);
- "Composante 2" was flagged as *missing* in the Arabic version, where it is correctly "المكوّن الثاني" —
  structural labels are now tagged `label_ref` and excluded from the translation check.
