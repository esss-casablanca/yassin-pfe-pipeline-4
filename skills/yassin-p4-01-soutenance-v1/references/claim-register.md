# Authoring the claim register (ledger items of kind "claim")

The scripts extract numbers, tables, figures, citations and references. **Claims are authored by me with the
student**, because a claim is a sentence whose *direction*, *strength* and *hedge* carry evidential weight that
no regex can read. The register is what p4-02 uses to check that the deck has not strengthened anything, and
what p4-05 uses to check that no translation has shifted a finding.

## What counts as a claim (one item each, per paper)
1. The **title** as deposited (it is itself a claim about scope and design).
2. Each **objective** (primary, secondary) exactly as formulated.
3. Each **primary finding** — the sentence of the Results that answers the primary objective, with its
   estimate and 95 % CI linked (`linked_items`).
4. Each **secondary finding** and each **exploratory finding** (strength = `exploratory`; these must stay
   labelled as such on every slide and in every translation).
5. For the review: the **PRISMA flow sentence** (identified → screened → included), the **synthesis
   statement** of each theme or outcome, the **certainty statement** if the review graded evidence, and the
   **gap handed to Component 2**.
6. Each **limitation** (they qualify the findings; dropping one on a slide is a Major issue).
7. Each **conclusion** and each **implication / recommendation**, with its hedge.

## Fields
```json
{"id": "E-CL-0003", "paper": "empirical", "kind": "claim", "section": "Résultats",
 "text_fr": "La satisfaction globale était associée à l’intention de rester (OR = 1,42 ; IC 95 % : 1,10–1,83).",
 "direction": "positive", "strength": "confirmatory", "hedge": "était associée à",
 "linked_items": ["E-N-0018", "E-N-0020", "E-N-0021"], "extracted_by": "assistant", "student_confirmed": true}
```
- `direction`: positive / negative / null / mixed — the sense of the finding, not its desirability.
- `strength`: confirmatory (pre-specified and reported as such) / exploratory / descriptive / hypothesis
  (Discussion or Conclusion wording that proposes rather than reports).
- `hedge`: the verb phrase or modal that carries the strength, copied verbatim from the paper
  ("suggère", "est associé à", "pourrait", "démontre" — the last is rare and must be in the paper to be used).

## Procedure with the student
Read each section from `_p4_text/<paper>.txt`. Propose the candidate claims one section at a time; ask the
student to confirm, in their own words, what each claim says and what it does *not* say ("Cette phrase
dit qu'il existe une association, pas que la satisfaction cause la rétention — d'accord ?"). Record
`student_confirmed: true` only after that exchange. Typical size: 10–18 claims per paper. Append the items
to `fidelity_ledger.json` and update `summary.<paper>.claims`.

## Numbers written in words
The script reads digits only. A number the paper writes in words ("Vingt et une études", "deux études",
"trois hôpitaux") that the deck or a translation will show as digits is added to the ledger by hand as a
`number` item with `raw` = the words, `normalized` = the digits, `role_hint: "spelled_out"`,
`extracted_by: "assistant"` (see `examples/benali-yasmine/claim_register.json`). The deck reconciliation
then accepts the digits; the translation reconciliation lists these items separately for a hand check.

## Red lines
- Never add a claim the paper does not make, and never "clarify" a claim into a stronger one.
- If the student disagrees with how their own paper phrases a finding, the paper is locked: the deck and the
  translations follow the paper; a change of substance goes back to the originating track.
