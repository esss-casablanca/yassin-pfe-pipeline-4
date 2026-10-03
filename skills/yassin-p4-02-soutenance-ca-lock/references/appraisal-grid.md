# Appraisal grid for the soutenance deck (eight dimensions)

Severity: **Major** blocks the lock · **Minor** must be closed or explicitly accepted by the student with a note ·
**Suggestion** is advice. Each finding names the slide (or note / bank entry), quotes the problem, and states
the required action.

| # | Dimension | What I check | Typical Major |
|---|-----------|--------------|---------------|
| 1 | **Fidélité** (ledger + claim register) | `reconcile_ledger.py deck` reports no introduced number; every slide number has the paper's value and precision; every claim on a slide keeps its direction, strength and hedge; no limitation of the papers is missing from the limits slide; exploratory findings are labelled; no citation or comparison absent from the papers; tables/figures are condensations of the papers' own tables/figures | a number not in the ledger; "démontre" for "suggère"; an exploratory finding shown as a result; a dropped limitation |
| 2 | **Storyline** | the Pipeline-4 storyline order (`shared/esss-template.md`): question → C1 → C2 → limits → discussion → conclusion → "Et alors ?"; the two components read as one argument; the gap from C1 to C2 is explicit; the "Et alors ?" slide exists | a results slide before the methods; no link between the components |
| 3 | **Chronométrage** | `timing` within ± 10 % of the target; no content slide under 30 s or over 90 s except the primary result; annexes untimed | total outside the tolerance |
| 4 | **Densité** | ≤ 6 bullets × ≤ 12 words; one idea per slide; tables ≤ 6 × 4 in the body; one figure per slide | — (Minor unless it hides a number) |
| 5 | **Lisibilité** | body text ≥ 18 pt (template placeholders), tables ≥ 14 pt in the body / ≥ 12 pt in annexes, figures legible at 2 m, charts with axis from 0 and data labels, no 3-D | a chart whose axis truncation exaggerates a difference |
| 6 | **Registre** | formal French, "nous", French typography (62,0 %; 1 248; IC 95 % : …; « »), no anglicism where a French term exists, no spelling error in a title | — |
| 7 | **Format ESSS** | built on the ESSS template (banner, logo, footer, numbering), title slide with the right academic year, student, filière, promotion, encadrant; closing slide; annexes titled | wrong year or student data |
| 8 | **Prêt à défendre** | the notes can be said by the student in their own words (mini-rehearsal); the jury bank covers the nine categories with ≥ 3 difficult questions; every model answer is supported by the papers (ledger ids) and keeps the hedges; the "si le jury demande" pointers resolve | a model answer the papers do not support |

## Procedure
1. Scripts first: deck reconciliation (dimension 1), timing (3), lint warnings from the build (4, 6).
2. Then the slide-by-slide read with the claim register open (1, 2, 5, 6, 7).
3. Then the notes and the bank (8), reading each model answer against the ledger.
4. Write the register; count Major/Minor/Suggestion; give the verdict `lockable` only at zero open Major.

## Closure record
Each issue: `closure_note` (what changed, in one sentence) and `closed_in` (the spec/deck version). The lock
file carries the counts. An accepted Minor issue is recorded as closed with `closure_note: "accepted by the
student: <reason>"`.
