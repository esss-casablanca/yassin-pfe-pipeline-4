# Translation protocol — French final → English (p4-03) and → Arabic (p4-04)

A translation in Pipeline 4 is a **faithful transfer** of a locked paper: same sections, same sentences in
the same order (a sentence may be split or merged only inside its paragraph), same numbers, same tables,
same citations, same reference list, same hedges. The student's voice is kept; nothing is added, nothing is
dropped, nothing is "improved". Where the French is ambiguous, I ask the student what they meant and keep
the answer *within* what the French says.

## 1. Working files
- Source text: `_p4_text/<paper>.txt` (from `extract_ledger.py --text-dump`) and the French .docx itself for
  tables and figures.
- Target text is authored as **Markdown** (`review_article_EN.md`, `empirical_article_EN.md`,
  `review_article_AR.md`, `empirical_article_AR.md`) in the subset understood by
  `shared/scripts/build_docx_from_md.py`, then typeset into .docx. Markdown is the editable master: fixes
  are made in the .md and the .docx is rebuilt.
- Progress is tracked in `translation_progress.json` (`{"review_EN": {"sections_done": [...], "status": "in progress"}}`)
  so that a session can resume mid-paper.

## 2. Order of work (per paper)
1. **Glossary first** (`shared/glossary-building.md`) — terms, instruments, acronyms, institutions,
   statistical vocabulary, proper nouns; validated with the student before the first sentence is translated.
2. Title · abstract · keywords.
3. Introduction. 4. Methods. 5. Results (text, then tables, then figure captions). 6. Discussion.
7. Conclusion. 8. Declarations (ethics, funding, conflicts, contributions, data availability, acknowledgements).
9. Reference list — **copied verbatim** from the source dump, never translated or re-styled.
10. Build the .docx, run `reconcile_ledger.py translation`, fix every finding in the .md, rebuild, re-run,
    until the script reports no Major finding. Then the assistant's own read-through, section by section,
    against the claim register (direction, strength, hedge of every claim).

## 3. Section-by-section rhythm with the student
Translate one section, show it next to the French, point out the two or three choices that mattered (a term,
a hedge, a sentence split), ask the student to read and confirm. Keep the sessions short; record the
section as done in `translation_progress.json`. Never translate the whole paper silently and present it at
the end.

## 4. Numbers, statistics, units (the reconciler reads these)
| French source | English target | Arabic target |
|---|---|---|
| 62,0 % · 1 248 · 0,008 | 62.0% · 1,248 · 0.008 | 62.0% · 1248 (or 1,248) · 0.008 — **never a space inside a number** |
| IC 95 % : 1,10–1,83 | 95% CI: 1.10–1.83 | فاصل الثقة 95%: 1.10–1.83 (label at first mention, then 95% CI) |
| OR · RR · HR · p · n · DS/ET (écart-type) · Moy. · méd. · EIQ | OR · RR · HR · p · n · SD · mean · median · IQR | OR · RR · HR · p · n · الانحراف المعياري (SD) · المتوسط · الوسيط · المدى الربيعي (IQR) |
| α de Cronbach = 0,89 | Cronbach's α = 0.89 | معامل ألفا كرونباخ = 0.89 |
| 150 infirmiers | 150 nurses | 150 ممرضاً |
Same precision as the source (62,0 → 62.0, never 62). Ranges keep the en dash. Units unchanged. Dates in the
target convention. ASCII digits in Arabic (Pipeline-4 contract) — the typesetter converts Arabic-Indic digits
back to ASCII as a safeguard, but write ASCII from the start.

## 5. Citations and references
In-text keys unchanged ([12], [3–5], (Smith et al., 2020)) in the same places. The reference list is pasted
verbatim from `_p4_text/<paper>.txt` under the heading "References" / "المراجع" as a numbered list, one entry
per line. The reconciler compares each entry to the source at ≥ 98.5 % similarity.

## 6. Claims and hedges
Before translating a Results, Discussion or Conclusion paragraph, open the claim register for that section.
The target sentence carries the same direction and strength: *suggère* → suggests / تشير إلى; *est associé à* →
is associated with / يرتبط بـ; *pourrait* → may / قد; *démontre* (if the paper used it) → demonstrates / يُظهر.
Never upgrade (suggests → shows) and never downgrade (demonstrates → may). Exploratory findings keep the
word exploratory / استكشافي.

## 7. Headings and reporting vocabulary
IMRaD headings in the target language; PRISMA and STROBE vocabulary in its official English form; in Arabic,
the term followed by the English/Latin acronym at first mention ("بيان PRISMA").

## 8. Tables and figures
Tables are re-typed in the target language with the same rows, columns, values and footnotes (Markdown pipe
tables; the header row first). Figures: the figure image from the French paper is reused unchanged (the
numbers are inside the image) with a translated caption; a figure whose labels must be in the target
language is noted as `[FIGURE À RELÉGENDER]` in the progress file for the student/supervisor.

## 9. The earlier English draft (reference only)
If an English draft from the earlier tracks exists, it may be consulted for phrasing. Every sentence is still
checked against the French final; where they differ, the French final wins, and the difference is noted in
`translation_progress.json` so the supervisor sees it.

## 10. Honesty
A translation choice with no settled equivalent is recorded in the glossary (`status: provisional`,
`decision_note`) and shown to the student; it is never hidden in fluent prose.
