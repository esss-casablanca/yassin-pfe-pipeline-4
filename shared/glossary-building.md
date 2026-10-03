# Building and using glossary_fr_en_ar.json

The glossary is built **before** the first sentence is translated (p4-03), extended in p4-04, and checked in
p4-05. It makes terminology consistent across both papers and both target languages, and it makes every
non-obvious choice visible to the student and the supervisor.

## 1. Collect the candidates (from the sources, not from memory)
Read `_p4_text/<paper>.txt` and `fidelity_ledger.json` and list:
- **instruments** and scales (MSQ, Maslach Burnout Inventory, échelle de Likert…) — their *original* name,
  usually English, is the English term; the Arabic form is the authorised Arabic translation's name when one
  exists, otherwise the Arabic expansion + the Latin acronym;
- **clinical and professional terms** (soins infirmiers, intention de rester, épuisement professionnel,
  rétention, filière, soutenance…);
- **methodological terms** (revue systématique, étude transversale analytique, biais de sélection, méthode
  commune, variable d'exposition, taille de l'échantillon, consentement éclairé…);
- **statistical terms** (odds ratio, intervalle de confiance, écart-type, médiane, test du χ², régression
  logistique, alpha de Cronbach…);
- **reporting guidelines and tools** (PRISMA, STROBE, JBI, AMSTAR, GRADE…) — kept in Latin letters;
- **institutions and places** (ESSS, CHU, ministère de la Santé, Casablanca, the host institution…);
- **acronyms** of the papers (IC, OR, DS, n…) with the decision keep-Latin / translate.

## 2. Decide each equivalent, with a source
Priority of sources for Arabic: (1) the instrument's authorised Arabic version if one is cited in the paper;
(2) the WHO/EMRO **Unified Medical Dictionary** (المعجم الطبي الموحد); (3) usage in indexed Arabic-language
health-science journals (Eastern Mediterranean Health Journal Arabic abstracts, Moroccan and Tunisian nursing
journals); (4) a reasoned decision, marked `status: provisional` with a `decision_note`. For English: the
instrument's original name; MeSH headings for concepts; standard epidemiological vocabulary (Porta's
dictionary; STROBE/PRISMA wording). Use live web search when the environment offers it; otherwise state that
the equivalent comes from my knowledge and mark it provisional.

## 3. Validate with the student
Show the glossary in a table (FR / EN / AR / note); ask the student, who practises in Morocco, whether the
Arabic terms are the ones used in their setting; adopt their usage when it is correct and current; record
`status: validated`. Fix the spelling convention (British English default) and the transliteration of proper
nouns once.

## 4. Use it
- Same term → same equivalent everywhere (both papers, abstract and body, tables and captions).
- First mention rule: Arabic expansion + (Latin acronym); then the acronym alone, as in the French.
- p4-05 checks consistency by searching each `term_en` / `term_ar` in the targets and each `term_fr` in the
  source; a term translated two ways is a Minor issue (Major if it is an outcome or exposure name).

## 5. Shape
See `shared/schemas.md` → `glossary_fr_en_ar.json`. Typically 60–150 entries per PFE.
