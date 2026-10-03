# Speaker notes and timing

The notes are the student's **script**, in French, and the student must be able to say every sentence as their
own. I coach: I draft from the sentences of their papers, read the draft back, and ask them to rephrase what
does not sound like them. I do not write a speech they will recite without understanding.

## Format of a note (per timed slide)
```
[⏱ 50 s]
<What to say — 3 to 6 short sentences, present tense, first person plural ("nous"), the numbers exactly as on the slide.>
→ Transition : « Voyons maintenant comment nous avons … »
Si le jury demande : Q12 (taille de l'échantillon), Q15 (biais de réponse)
```
- Title slide: who I am, the title, the two components in one sentence, the encadrant(s) — 30 s.
- Section slides: one sentence of transition — 10 s.
- Content slides: 45–60 s; a primary-result slide may take 90 s; the "Et alors ?" slide 60 s.
- Closing slide: 10 s.

## Timing rules
- Total of the timed slides = target duration ± 10 % (`timing_V1.json` → `within_target`). If over, cut
  slides, not speaking speed; if under, give the primary results more air, do not add content.
- 130–150 French words per minute is a calm speaking pace; a 50 s note holds ~110–125 words.
- Annex slides have no timing and no script; they have a one-line note saying which question they answer.

## Register and delivery
- Formal French, "nous" for the work, "je" only for personal reflection at the end if the student wishes.
- Say the numbers as written: "soixante-deux virgule zéro pour cent", "un intervalle de confiance à
  quatre-vingt-quinze pour cent de un virgule dix à un virgule quatre-vingt-trois".
- Name the design and the reporting guideline once each ("revue systématique selon PRISMA", "étude
  transversale analytique rapportée selon STROBE").
- Every limitation is said aloud, in the student's words, before the discussion of results.
- The last sentence of the deck is the contribution of the PFE, not "merci".

## The printable script
`build_deck.py --notes-docx` writes `soutenance_notes_V1.docx`: each slide's notes with the cumulative time,
and a timing table at the end. The student rehearses from this document (see `rehearsal-guide.md`).
