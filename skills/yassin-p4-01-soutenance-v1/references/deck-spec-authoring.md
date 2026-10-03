# Authoring deck_spec.json

`shared/scripts/build_deck.py` turns the spec into the ESSS-branded deck; the spec, not the .pptx, is the
editable master (p4-02 fixes issues in the spec and rebuilds). The storyline and the slide allocation are in
`shared/esss-template.md`; this file is about writing each slide well.

## Slide types and when to use them
| type | use for | notes |
|------|---------|-------|
| `title` | slide 1 | `title` = PFE title as deposited; `subtitle` = "Prénom NOM · Filière · Promotion · Encadrant : …" |
| `bullets` | most text slides | ≤ 6 bullets, ≤ 12 words each; sub-points with `{"text": "...", "level": 1}` |
| `two_columns` | side-by-side content | with `left_label`/`right_label` → Comparaison layout (Composante 1 vs 2, Forces vs Limites); without labels → Deux contenus |
| `section` | one per section of the storyline | `subtitle` = one line saying what the section will show |
| `table` | condensed tables | `header`, `rows`, `font_pt` (≥ 14 in the body of the deck, ≥ 12 in annexes), `caption` = the paper's label ("Tableau 2 …"), `col_widths` relative |
| `chart` | one message per chart | `kind` column/bar/pie/line; `categories`, `series`; values **only** from the ledger; `number_format` "0.0" / "0"; `axis_min` defaults to 0 |
| `image` | PRISMA flow, forest plot, figures copied from the papers | PNG/JPG path; `caption` = the paper's label |
| `closing` | last timed slide | title "Merci de votre attention", subtitle with the student's name |
| `annex_marker` | boundary | everything after it is an annex (timing 0) |

## Writing rules (p4-02 checks them)
1. **Titles are questions or statements**, in French, ≤ 10 words: "Qui sont les participants ?",
   "La satisfaction est associée à l'intention de rester". Never "Résultats 1".
2. **One idea per slide.** If a slide needs a second idea, it is two slides.
3. **Numbers**: write them exactly as in the paper (French typography: "62,0 %", "1 248", "IC 95 % : 1,10–1,83"),
   with the same precision. The reconciler reads them; so does the jury.
4. **Hedges**: copy the paper's verb ("est associé à", "suggère"). A slide may shorten, never strengthen.
5. **Exploratory findings** carry the word "exploratoire" on the slide, not only in the notes.
6. **Limits before discussion** (the ESSS deck's own order), both components covered.
7. **Tables**: ≤ 6 rows × 4 columns in the body; the full table goes to the annexes.
8. **Charts**: a bar or column chart for group comparisons; a forest-style figure is better copied from the
   paper as an image than redrawn; never a 3-D chart; axis from 0.
9. **No "Merci" slide with a picture of a sunset.** The closing slide carries the name and the invitation to
   questions; the real last message is the "Et alors ?" slide before it.
10. Annexes: full tables, questionnaire, PRISMA/STROBE checklists, ethics attestation reference — ready for
    the Q&A, each with a clear title ("Annexe 2 — Tableau 3 complet").

## Minimal example
```json
{"meta": {"academic_year": "2025/2026", "footer": "Soutenance PFE · ESSS · P23", "presentation_minutes": 20},
 "slides": [
  {"type": "title", "title": "…", "subtitle": "…", "notes": "[⏱ 30 s] …", "seconds": 30},
  {"type": "bullets", "title": "Plan", "bullets": ["…"], "notes": "[⏱ 20 s] …", "seconds": 20},
  {"type": "section", "title": "Problématique et question de recherche", "subtitle": "…"},
  {"type": "two_columns", "title": "Que voulons-nous savoir ?", "left_label": "Composante 1 — Revue", "left": ["…"],
   "right_label": "Composante 2 — Étude empirique", "right": ["…"], "notes": "[⏱ 60 s] …", "seconds": 60},
  {"type": "closing", "title": "Merci de votre attention", "subtitle": "Prénom NOM — vos questions"},
  {"type": "annex_marker", "title": "Annexes"},
  {"type": "table", "title": "Annexe 1 — Tableau 2 complet", "header": ["…"], "rows": [["…"]], "font_pt": 12}
 ]}
```
