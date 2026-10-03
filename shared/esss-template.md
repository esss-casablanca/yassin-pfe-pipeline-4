# The ESSS soutenance deck — template conventions and the storyline Pipeline 4 derives from it

Source: `shared/templates/esss_soutenance_template.pptx` (the ESSS guidance deck "Soutenance Projet de fin
d'études", 2021/2022, 28 slides, supplied by Dr Yassin as guidance only). `build_deck.py` uses this file as the
base so that the ESSS branding is inherited rather than re-drawn.

## Visual identity (inherited from the template's master and layouts)
- 16:9 (12 192 000 × 6 858 000 EMU). White background.
- Header: three horizontal bars at the top (navy `#1A3260`, blue `#4590B8`, grey `#969FA7`); on content layouts
  a navy title banner with white upper-case title text; the round ESSS logo (Arabic + French name, caduceus and
  book) at the top right of every content layout; the title layout carries the logo inside a navy panel with the
  caption "PROJET DE FIN D'ÉTUDES — ANNÉE UNIVERSITAIRE 20xx/20xx" (the builder rewrites the year; it also
  corrects the template's typo "FINE").
- Theme colours: dk1 `#3D3D3D` text, accent1 `#1A3260`, accent2 `#4590B8`, accent3 `#45CBE8`, accent4
  `#969FA7`, accent5 `#A2C777`, accent6 `#42955F`. Charts default to accent1/2/3 series colours.
- Fonts: Gill Sans MT (titles), Corbel (body). Both are Windows fonts; the builder does not override them.
- Footer placeholders (date, footer, slide number) exist on every layout; the builder shows the slide number
  and the footer "Soutenance PFE · ESSS · <promotion>".

## Layouts the builder may use (index → name → placeholders)
| idx | name | use in Pipeline 4 |
|-----|------|-------------------|
| 0 | Diapositive de titre | slide 1 only (title + student + year panel) |
| 1 | Titre et contenu | standard text slide (title idx 0, body idx 1) — the workhorse |
| 2 | Titre de section | one per section (title idx 0, subtitle idx 1) |
| 3 | Deux contenus | two columns (idx 1 and 2) |
| 4 | Comparaison | two labelled columns (labels idx 1/3, bodies idx 2/4) — Component 1 vs Component 2, forces vs limites |
| 5 | Titre seul | title + a free-placed table, chart or picture |
| 6 | Vide | full-bleed figure (PRISMA flow diagram, large table) |
| 7 | Contenu avec légende | figure with a caption box |
| 8 | Image avec légende | picture placeholder + caption |

Layouts 9–10 (vertical text) are never used.

## The guidance storyline (what the 2021/22 deck teaches)
The ESSS deck walks a single empirical study through: *exact study question* → *rationale and relevance* (why
the subject matters, with national figures and a chart) → *methodology* (design, operational definitions of
the variables, risk factors, data processing and analysis, calendar) → *results* (four chart/table slides) →
*discussion* (limits of the study, scope of generalisation, then each main result discussed) → *conclusions* →
*"Et alors ?"* (what the study adds to the body of knowledge). Its lessons, which Pipeline 4 keeps:
one question per slide title, phrased as the jury would ask it; the study question restated before the methods;
figures carry the numbers, the voice carries the interpretation; limits come **before** the discussion of the
results; the deck ends on the contribution, not on a "Merci" slide.

## The Pipeline-4 storyline (two components, one PFE)
The student defends **one PFE made of two linked papers**, so the deck is built as a single argument and not as
two mini-decks. Default allocation for a 20-minute presentation (≈ 22–26 slides, ~45–60 s per content slide):

| # | Section (section-title slide where marked ▸) | Slides | Content rules |
|---|---|---|---|
| 1 | Titre | 1 | Title of the PFE as deposited; student; filière; promotion; encadrant(s); year. |
| 2 | Plan | 1 | The five sections below in one glance. |
| 3 | ▸ Problématique et question de recherche | 2–3 | Context in three facts max (from the papers' introductions); the review question (PICO/PCC) and the empirical objective on one slide, side by side (layout 4). |
| 4 | ▸ Composante 1 — Revue (PRISMA) | 4–5 | Methods in one slide (sources, dates, eligibility, appraisal tool); the PRISMA flow as a figure (counts from the ledger); the synthesis in one or two slides (evidence table condensed, or the main themes); what the review concluded and the gap it handed to Component 2. |
| 5 | ▸ Composante 2 — Étude empirique (STROBE) | 6–7 | Design, setting, population and sample on one slide; instrument and variables; analysis plan in one line per objective; participant flow and descriptives (table/figure); the primary result (estimate + 95 % CI) on its own slide; secondary results; exploratory findings clearly labelled "exploratoire". |
| 6 | ▸ Discussion | 3–4 | Limits first (both components); then each main result against the review and the literature **as already written in the papers**; implications for practice/retention/policy exactly as hedged in the papers. |
| 7 | ▸ Conclusion et apport | 1–2 | Conclusions as in the papers; "Et alors ?" — what the PFE adds; perspectives. |
| 8 | Remerciements / Questions | 1 | Closing slide with the student's name and the invitation to questions (no new content). |
| — | Annexes (after the closing slide, not counted in the timing) | 0–6 | Full evidence table, full descriptive tables, questionnaire, ethics attestation reference, STROBE/PRISMA checklists — ready for the Q&A. |

Rules the appraisal (p4-02) enforces: ≤ 6 bullets per slide and ≤ 12 words per bullet; every number on a slide
exists in the ledger with the same value and the same hedge; one figure per slide; no text below 18 pt in the
body (tables may go to 12 pt in the annexes only); titles are questions or statements, never generic labels
("Résultats 1"); the deck never introduces a claim, a comparison or a citation absent from the papers.

## Speaker notes and timing
Every slide carries speaker notes in French: what to say (the student's own words, coached), in sentences the
student can learn, with the target duration in seconds at the top of the note (`[⏱ 50 s]`) and a one-line
"si le jury demande…" pointer to the relevant jury-bank question. The builder writes the notes into the notes
slide; `soutenance_notes_V1.docx` is the same text as a printable script with a running total.
