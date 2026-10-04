# Machine-Readable Schemas — Pipeline 4

Indicative shapes. Field names must stay stable across p4-01 … p4-05 and the scripts in `shared/scripts/`.
All files are UTF-8 JSON saved in the student's project workspace.

## p4_source_manifest.json (p4-01)
```json
{
  "project_id": "D03-P01",
  "student": {"first_name": "", "family_name": "", "name_ar": null, "filiere": "", "promotion": ""},
  "generated_at": "2026-10-03T10:00:00Z",
  "approval": {"reference": "APP-P4-KY-2026/012", "date_iso": "2026-10-03", "verification_code": "ABCDE-12345",
               "student_name_on_letter": "NOM Prénom", "project_code_on_letter": "D03-P01",
               "file": "APP4-NOM-Prenom-V1-Flat.pdf", "sha256": "", "verdict": "valid",
               "visual_check": "letterhead and signature seen by the assistant", "verified_at": "", "verified_by_step": "Yassin_P4_01_Soutenance_V1"},
  "sources": {
    "review":    {"file": "revue_systematique_FINAL_FR.docx", "sha256": "", "language": "fr",
                  "lineage": "V5", "words": 0, "headings": [], "locks": ["content_lock.json"],
                  "attestations": ["lock_attestation_ASW2.json"], "lock_status": "verified|missing|inconsistent"},
    "empirical": {"file": "article_empirique_FINAL_FR.docx", "sha256": "", "language": "fr",
                  "lineage": "post-ASW-2", "words": 0, "headings": [],
                  "locks": ["protocol_lock.json", "results_lock.json"],
                  "attestations": ["ASW_attestation.json"], "lock_status": "verified"}
  },
  "reference_drafts": [{"paper": "review", "file": "review_V5_EN.docx", "role": "reference only — French final wins"}],
  "conventions": {"english_spelling": "british|american", "arabic_digits": "ascii", "citation_style": "numeric|author-date"},
  "soutenance": {"language": "fr", "presentation_minutes": 20, "questions_minutes": 20,
                 "jury": {"size": null, "composition": null}, "date": null, "rules_source": "student-supplied|ESSS default"},
  "pipeline_progress_ref": "student_project_profile.json"
}
```

## fidelity_ledger.json (p4-01; read by p4-02 and p4-05)
```json
{
  "ledger_version": "1.0",
  "parser_version": "2",
  "project_id": "D03-P01",
  "generated_at": "",
  "sources": {"review": {"file": "", "sha256": ""}, "empirical": {"file": "", "sha256": ""}},
  "items": [
    {"id": "R-N-0001", "paper": "review", "kind": "number", "section": "Résultats", "paragraph_index": 42,
     "raw": "1 248", "normalized": "1248", "unit": null, "context": "… 1 248 références identifiées …",
     "role_hint": "prisma_identified", "extracted_by": "script"},
    {"id": "E-N-0117", "paper": "empirical", "kind": "number", "section": "Résultats", "paragraph_index": 88,
     "raw": "1,42", "normalized": "1.42", "unit": null, "context": "OR = 1,42 ; IC 95 % : 1,10–1,83", "extracted_by": "script"},
    {"id": "E-T-0001", "paper": "empirical", "kind": "table", "label": "Tableau 1", "caption": "", "n_rows": 0, "n_cols": 0,
     "header": [], "cells": [["", ""]], "numbers_normalized": ["150", "62.0"], "extracted_by": "script"},
    {"id": "E-F-0001", "paper": "empirical", "kind": "figure", "label": "Figure 1", "caption": "", "values_in_caption": [], "extracted_by": "script"},
    {"id": "R-C-0001", "paper": "review", "kind": "citation", "key": "[12]", "occurrences": 3, "extracted_by": "script"},
    {"id": "R-REF-0012", "paper": "review", "kind": "reference", "index": 12, "text": "", "doi": null, "extracted_by": "script"},
    {"id": "E-CL-0001", "paper": "empirical", "kind": "claim", "section": "Conclusion", "text_fr": "",
     "direction": "positive|negative|null|mixed", "strength": "confirmatory|exploratory|descriptive|hypothesis",
     "hedge": "est associé à", "linked_items": ["E-N-0117"], "extracted_by": "assistant", "student_confirmed": true}
  ],
  "summary": {"review": {"numbers": 0, "tables": 0, "figures": 0, "citations": 0, "references": 0, "claims": 0},
              "empirical": {"numbers": 0, "tables": 0, "figures": 0, "citations": 0, "references": 0, "claims": 0}}
}
```
Normalisation rules (script): remove thousands separators (space, narrow no-break space, thin space, dot used as
thousands separator in a clearly integer context), convert decimal comma to decimal point, keep sign and
percent as separate fields, keep ranges as two numbers linked by `range_of`. Years, section numbers, reference
indices and citation keys are tagged (`role_hint`: `year`, `numbering`, `citation`) so the reconciler does not
treat them as statistics but still checks their presence.
Parser v2 (plugin v0.2.4): bracketed intervals (`[1,30 ; 3,40]`, `28 [24–33]` after a statistical cue) are numbers,
not citation keys; DOIs/URLs and multi-level section numbers (`2.3.1`) are ignored; a ledger rebuilt with
`--carry-over` adds `"carry_over": {"from_parser_version", "carried_items", "links_remapped", "unmapped": [...],
"renamed_ids": {}}` and marks a claim whose link could not be remapped with `carry_over_unmapped_links`.

## soutenance_issue_register.json (p4-02)
```json
{
  "project_id": "D03-P01", "deck_file": "soutenance_deck_V1.pptx", "deck_sha256": "", "appraised_at": "",
  "dimensions": ["fidelity", "storyline", "timing", "density", "readability", "register", "format", "defence_readiness"],
  "issues": [
    {"id": "S-001", "severity": "Major|Minor|Suggestion", "dimension": "fidelity", "slide": 14,
     "finding": "Slide states 'démontre' where the paper says 'suggère' (claim E-CL-0003 strengthened).",
     "required_action": "Restore the hedge of the paper.", "status": "open|closed", "closure_note": "", "closed_in": "soutenance_deck_V2.pptx"}
  ],
  "ledger_reconciliation": {"items_on_slides": 0, "matched": 0, "missing": [], "altered": [], "introduced": []},
  "timing": {"target_minutes": 20, "estimated_minutes": 0, "per_slide_seconds": []},
  "verdict": "lockable|not lockable"
}
```

## soutenance_lock.json (p4-02)
```json
{
  "lock": {"locked": true, "locked_at": "", "locked_by_step": "Yassin_P4_02_Soutenance_CA_Lock"},
  "project_id": "D03-P01",
  "approval_reference": "APP-P4-KY-2026/012",
  "deck": {"file": "soutenance_deck_FINAL.pptx", "sha256": "", "slides": 0},
  "notes": {"file": "soutenance_notes_FINAL.docx", "sha256": ""},
  "jury_questions_bank": {"file": "jury_questions_bank.docx", "sha256": "", "questions": 0},
  "timing": {"presentation_minutes": 20, "estimated_minutes": 0},
  "ledger_reconciliation": {"items_on_slides": 0, "matched": 0, "unmatched": 0},
  "issues_closed": {"major": 0, "minor": 0, "suggestion": 0, "open": 0},
  "frozen": ["slide content", "speaker notes content", "figures and tables shown", "claims and their hedges"],
  "editable_after_lock": ["oral delivery", "rehearsal timing", "cosmetic fixes that change no word or value (re-lock required otherwise)"],
  "student_signoff": {"name": "", "date": "", "statement": "Je confirme que ce diaporama reflète fidèlement mes deux articles et que je suis en mesure de défendre chaque diapositive."}
}
```

## glossary_fr_en_ar.json (p4-03 creates; p4-04 and p4-05 extend)
```json
{
  "project_id": "D03-P01", "created_by_step": "Yassin_P4_03_English_Versions", "updated_at": "",
  "conventions": {"english_spelling": "british", "arabic_digits": "ascii", "arabic_register": "MSA scientific",
                  "transliteration": "simplified, consistent, as in the Arabic forms below"},
  "entries": [
    {"id": "G-0001", "category": "instrument|clinical|statistical|methodological|institutional|acronym|proper_noun",
     "term_fr": "Questionnaire de satisfaction du Minnesota", "term_en": "Minnesota Satisfaction Questionnaire",
     "term_ar": "مقياس مينيسوتا للرضا الوظيفي", "acronym": "MSQ", "keep_latin_acronym": true,
     "first_mention_rule": "AR: Arabic expansion followed by (MSQ); EN: expansion followed by (MSQ)",
     "source": "authorised translation / WHO terminology / published Arabic article / decision",
     "decision_note": "", "status": "validated|provisional"}
  ]
}
```

## translation_qa_register.json (p4-05)
```json
{
  "project_id": "D03-P01", "approval_reference": "APP-P4-KY-2026/012", "appraised_at": "",
  "targets": {
    "review_EN": {"file": "review_article_EN.docx", "sha256": "",
      "ledger": {"expected": 0, "matched": 0, "missing": [], "altered": [], "introduced": []},
      "tables": {"expected": 0, "matched": 0, "mismatches": []},
      "references": {"expected": 0, "verbatim": 0, "mismatches": []},
      "terminology": {"entries_checked": 0, "inconsistencies": []},
      "back_translation": [{"section": "Abstract", "source_fr": "", "target": "", "back_fr": "", "verdict": "faithful|shifted", "note": ""}],
      "issues": [{"id": "T-001", "severity": "Major|Minor|Suggestion", "location": "", "finding": "", "required_action": "", "status": "open|closed", "closure_note": ""}],
      "verdict": "attestable|not attestable"},
    "empirical_EN": {}, "review_AR": {}, "empirical_AR": {}
  }
}
```

## p4_attestation.json (p4-05 — terminal)
```json
{
  "attestation": {"issued": true, "issued_at": "", "issued_by_step": "Yassin_P4_05_Translation_QA_Attestation"},
  "project_id": "D03-P01",
  "approval_reference": "APP-P4-KY-2026/012",
  "sources": {"review": {"file": "", "sha256": ""}, "empirical": {"file": "", "sha256": ""}},
  "deliverables": {
    "soutenance_deck_FINAL.pptx": {"sha256": "", "lock": "soutenance_lock.json"},
    "review_article_EN.docx": {"sha256": "", "ledger_matched": "n/n", "verdict": "attestable"},
    "empirical_article_EN.docx": {"sha256": ""}, "review_article_AR.docx": {"sha256": ""}, "empirical_article_AR.docx": {"sha256": ""}
  },
  "statement": "No frozen value, table value, citation, reference or claim of the two French sources was altered in the deck or in the four translated versions; terminology is consistent with glossary_fr_en_ar.json.",
  "student_signoff": {"name": "", "date": ""},
  "pfe_complete": true
}
```

## approval_check.json (p4-01, written by `verify_approval.py`)
```json
{"file": "APP4-NOM-Prenom-V1-Flat.pdf", "sha256": "", "text_layer": true, "pages": 1,
 "checks": {"title_present": true, "signatory_present": true, "code_line_found": true, "reference_format": true,
            "verification_code_valid": true, "date_format": true, "project_matches_profile": true, "name_matches_profile": true},
 "fields": {"ref": "APP-P4-KY-2026/012", "project": "D03-P01", "name": "NOM Prénom", "date_iso": "2026-10-03", "vcode": "ABCDE-12345"},
 "recomputed_code": "ABCDE-12345", "verdict": "valid|invalid|unverifiable",
 "approval": {"reference": "", "date_iso": "", "verification_code": "", "student_name_on_letter": "", "project_code_on_letter": "", "file": "", "sha256": ""}}
```
