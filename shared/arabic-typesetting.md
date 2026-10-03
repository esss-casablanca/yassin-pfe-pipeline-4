# Arabic typesetting rules (p4-04) — what the typesetter does and what the author must do

`shared/scripts/build_docx_from_md.py --lang ar` produces a true right-to-left Word document: RTL section,
`bidi` paragraphs **right-aligned throughout (never justified)** — the only centred elements are the title block
(title, author, affiliation) and the figure captions; Arabic runs flagged `rtl` with a complex-script font
(Noto Naskh Arabic; Word substitutes Arial/Traditional Arabic if absent); Latin and digit runs left-to-right
inside the Arabic line; RTL tables (`bidiVisual`) with the first column on the right and every cell right-aligned;
Latin reference entries keep left-to-right reading order (otherwise their punctuation is garbled) but are
right-aligned like the rest; headings right-aligned; A4 with 2.5 cm margins; Arabic-Indic digits converted to ASCII.

**Alignment rule (Dr Yassin's instruction):** the Arabic article is RTL and right-aligned, except the text that
should be centred. Do not justify, do not left-align, and do not centre anything beyond the title block and the
figure captions without his agreement.

## What the author of the .md must do
1. **Register**: الفصحى scientific prose as in Arabic-language health-science journals; third person or
   authorial "نحن" matching the French "nous"; no colloquial Moroccan forms.
2. **Digits**: ASCII 0–9, decimal point, no spaces inside numbers (1248 or 1,248; never 1 248).
3. **Punctuation**: Arabic comma "،", semicolon "؛" and question mark "؟" inside Arabic sentences; Latin
   parentheses and the Latin semicolon inside statistical formulae. Write a formula as one Latin block:
   `(OR = 1.42; 95% CI: 1.10–1.83; p = 0.008)` and put the Arabic label outside it; mixing Arabic words
   inside the parentheses produces bidi reordering that readers find confusing.
4. **Acronyms**: Latin, unchanged (PRISMA, STROBE, MSQ, OR, CI, SD, n, p); Arabic expansion at first
   mention as the glossary fixes it. Never transliterate an acronym.
5. **Proper nouns**: one transliteration per name, from the glossary; author names in citations stay Latin.
6. **Headings**: `## الملخص`, `## المقدمة`, `## المنهجية` (or `الطرق`), `## النتائج`, `## المناقشة`,
   `## الخلاصة`, `## الإقرارات`, `## المراجع` — the typesetter recognises `المراجع` as the reference list.
7. **Title block** (front matter): `title:` Arabic title; `authors:` the student's name in Arabic as they
   write it officially (ask; do not guess the spelling); `affiliation:` المدرسة العليا لعلوم الصحة (ESSS)،
   الدار البيضاء. Add, as the first paragraph, the original French title: *العنوان الأصلي بالفرنسية:* ….
8. **Tables**: pipe tables with the header row first; the typesetter reverses the visual column order, so
   write the columns in the same logical order as the French (first column = row labels); cells with only
   Latin/digits stay LTR automatically.
9. **Figures**: `![الشكل 1. …](figure1.png)`; the image is the French paper's image, unchanged.
10. **Reference list**: pasted verbatim, one numbered line per entry; the typesetter sets each Latin entry LTR.

## Known rendering limits
- Bidi punctuation next to Latin blocks can look mirrored in some viewers; check once in Word (not only in a
  PDF preview) before sign-off and, if needed, move the Arabic label outside the parentheses.
- Word must have an Arabic-capable font; Noto Naskh Arabic is free (fonts.google.com); Arial renders
  acceptably.
- Line numbering, footnotes and tracked changes are not produced; journals that need them get them from
  the submission step of the earlier tracks.
