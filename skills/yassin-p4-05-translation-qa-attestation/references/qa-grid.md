# QA grid for the translated versions

Applied to each of the four targets (review EN, empirical EN, review AR, empirical AR). Severity: **Major**
(blocks the attestation for that target) · **Minor** (closed or accepted with a note) · **Suggestion**.

| # | Check | Tool | Major when |
|---|-------|------|------------|
| 1 | Numbers of the running text | `reconcile_ledger.py translation` | any missing or introduced number; an under-represented number not explained by a legitimate merge |
| 2 | Tables | same | any value, row or column differing; a table absent; a footnote dropped |
| 3 | Figures | assistant | image replaced or re-drawn; caption values differing; a relabel note unresolved without the supervisor's deferral |
| 4 | Citations | same script | a key missing, moved to another sentence, or counts differing |
| 5 | Reference list | same script (≥ 98.5 % similarity) | an entry translated, re-styled, dropped or re-ordered |
| 6 | Claims | assistant, claim register | direction, strength or hedge shifted; "exploratory" label lost; a limitation dropped |
| 7 | Section integrity | assistant | a heading, paragraph or declaration missing or added; order changed |
| 8 | Terminology | `check_glossary.py` + assistant | an outcome/exposure/instrument term rendered two ways; a Latin acronym transliterated |
| 9 | Back-translation spot checks | assistant (blind) | the back-translated abstract, primary result, limitations or conclusion differs in meaning from the French |
| 10 | Typesetting | assistant + student in Word | AR not RTL, a justified or left-aligned paragraph, a centred element other than the title block / figure captions, Arabic-Indic digits; EN spelling mixed (Minor) |

## Back-translation procedure
1. Choose the passages: abstract (whole), the paragraph carrying the primary result, the limitations paragraph,
   the conclusion — for each target.
2. Translate each back into French **without** re-reading the French source (work from the target only).
3. Compare with the source paragraph: same facts, same numbers, same hedges, same scope? Record
   `verdict: faithful` or `shifted` with one sentence describing the shift and the fix.
4. A shift in a claim is a Major issue (dimension 6); a stylistic difference is not an issue.

## Register entries
```json
{"id": "T-004", "severity": "Major", "location": "empirical_AR · Results ¶3",
 "finding": "تُظهر (demonstrates) used where the French says « suggère » — claim E-CL-0006 strengthened.",
 "required_action": "Use تشير إلى; rebuild; re-run reconciliation.", "status": "closed",
 "closure_note": "fixed in empirical_article_AR.md v3; recon clean"}
```
