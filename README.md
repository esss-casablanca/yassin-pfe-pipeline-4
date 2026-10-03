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
profile, the lock and the attestation). All skills run only in Claude Cowork, **only on Claude Fable 5.1 or higher** (Mythos 5.1 and later releases included; every
other model is refused with a bilingual message), and speak as Dr Khaled Yassin.
