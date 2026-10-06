# ESSS PFE — Pipeline 4: Soutenance & Trilingual Papers

The fourth and terminal pipeline of the ESSS Projet de Fin d'Études, downstream of the
`yassin-pfe-review-pipeline` (Component 1, steps 01–10) and the `yassin-pfe-empirical-research` plugin
(Component 2, emp-01 … emp-13). It takes the student's **two final, locked, attested French papers** and
produces everything needed after the science is closed:

```
FINAL FRENCH REVIEW ARTICLE (V5 lineage + content lock)  +  FINAL FRENCH EMPIRICAL ARTICLE (post-ASW-2 + protocol/results locks)
      │
      ▼
Pipeline 4 — Soutenance & Trilingual Papers
   p4-01  Soutenance V1        -> fidelity ledger + ESSS deck + timed notes + jury-question bank + rehearsal guide
   p4-02  Soutenance CA + Lock -> graded issue register -> closure -> student sign-off -> SOUTENANCE LOCK
   p4-03  English versions     -> trilingual glossary + both papers in English (.docx)
   p4-04  Arabic versions      -> both papers in Modern Standard Arabic, true RTL (.docx)
   p4-05  Translation QA       -> ledger reconciliation + terminology + back-translation checks -> PIPELINE-4 ATTESTATION
```

Pipeline 4 is **derivation-only**: nothing is researched or re-analysed. Every number, table value, citation and
claim of the two French sources is extracted into a **fidelity ledger** and every deliverable — the deck and the
four translated papers — is reconciled against it before it can be locked or attested.

| Skill | Role |
|-------|------|
| `yassin-p4-01-soutenance-v1` | Gate, load both papers with their locks and attestations, build `p4_source_manifest.json` and `fidelity_ledger.json`; then build the soutenance deck V1 on the ESSS template with speaker notes timed to the jury's duration, a jury-questions bank and a rehearsal guide. |
| `yassin-p4-02-soutenance-ca-lock` | Appraise the deck (ledger fidelity, storyline, timing, one idea per slide, readability, French register, ESSS format), close every issue, take the student's sign-off and issue the **Soutenance Lock**. |
| `yassin-p4-03-english-versions` | Build the trilingual glossary first, then produce the English version of both papers, reference list untouched. |
| `yassin-p4-04-arabic-versions` | Produce the Arabic version of both papers in a scientific MSA register, typeset RTL, Latin acronyms controlled by the glossary. |
| `yassin-p4-05-translation-qa-attestation` | Reconcile each target against the ledger, check terminology consistency, run back-translation spot checks, close the register, and issue `p4_attestation.json` — the close of the whole PFE. |

Shared material at the plugin root: `cross-cutting-contracts.md` (interaction, fidelity, language/typesetting and
workspace contracts applied by every skill), `shared/schemas.md` (machine-readable shapes), `shared/esss-template.md`
(the ESSS deck conventions), `shared/scripts/` (deck builder, ledger extractor, RTL docx builder, reconciler) and
`shared/templates/` (the ESSS soutenance template deck).

Entry is gated by **Dr Yassin's signed Pipeline-4 approval** (`APP-P4-KY-<year>/<NNN>`, a flattened PDF issued from his
registry once the PFE submission is complete; verified by `shared/scripts/verify_approval.py`, recorded in the manifest, the
profile, the lock and the attestation). All skills run only in Claude Cowork, **only on Claude Opus 5.5 or higher** (included in Claude Pro; Fable 5.1, Mythos and later
releases also accepted; lower models are refused with a bilingual message), and speak as Dr Khaled Yassin.

## Version 0.2.4 — number parser v2 (4 October 2026)

Reported by a student (D15-P04) and reproduced on v0.2.3: `reconcile_ledger.py` raised false **Major** findings on
faithful translations. Fixed in `shared/scripts/` (`p4lib.py`, `extract_ledger.py`, `reconcile_ledger.py`,
`build_docx_from_md.py`):

1. **Thousands separators** — English and Arabic also accept no-break / narrow / thin spaces and the Arabic
   separator `٬`; the Arabic decimal separator `٫` is read as a decimal point.
2. **Bracketed intervals** — `IC 95 % [1,30 ; 3,40]`, `1,85 [1,20–2,86]`, `médiane 28 [24–33]` are read as numbers,
   not as citation keys. In v0.2.3 the French confidence intervals in brackets never entered the ledger (they were
   counted as citations [1], [30]…), so neither the deck check nor the translation check saw them.
3. **DOIs and URLs** in the running text are ignored.
4. **Section cross-references** read the same in every locale (`voir 2.3` = `see 2.3`; `§`, `القسم`, `الفصل` are
   labels; multi-level numbers such as `2.3.1` are ignored).
5. **Empty table rows** are kept by the typesetter and not counted when tables are compared.

Ledgers now carry `parser_version`. `reconcile_ledger.py` stops (exit 2) on a ledger built by an older parser:
rebuild it with `extract_ledger.py … --carry-over <old ledger>`, which keeps the confirmed claim register and the
hand-added numbers and remaps their links. Regression tests: `python shared/scripts/tests/test_number_parser_v2.py`
(the bundled example still runs to an attestation unchanged).

## Version 0.2.5 — a source paper already in English (6 October 2026)

Some empirical articles were accepted by the School in English. `extract_ledger.py` now takes
`--review-locale` / `--empirical-locale` so each paper is read with its own number conventions, and the ledger records
the locale of each source. Rule added to `cross-cutting-contracts.md` (Part C) and to p4-01 / p4-03 / p4-04: the
deposited English paper is the official source of its component; its English version is the file itself, registered
unchanged (same SHA-256); the Arabic version and the French deck are derived from it. Regression test extended.
