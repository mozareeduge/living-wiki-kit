---
name: wiki-intake
description: Preserve and register new source artifacts, update corpus memory, and prepare a reviewable intake branch. Has side effects and must be invoked manually.
disable-model-invocation: true
---

# Wiki Intake

Input: one or more files placed in `01-inbox/`.

## Definitions

- **intake**: one bounded arrival of source material.
- **artifact**: the exact received file.
- **exact duplicate**: the same byte checksum.
- **textual duplicate**: different files with identical normalized extracted text.
- **new version**: a distinct artifact that belongs to an existing work or document family.
- **replacement**: a user-confirmed artifact that takes over a specific current function; it does not delete predecessors.

## Procedure

1. Run `python scripts/validate_repo.py --full`. Stop if the existing state fails.
2. Create branch `intake/YYYY-MM-DD--short-name`.
3. Inventory every inbox file: filename, format, bytes, SHA-256, extraction feasibility, visible title, language, and supplied status.
4. Compare checksums and normalized text against the manifest.
5. Copy each new exact artifact into `_originals/`. Never overwrite an existing path.
6. Create a content-derived source ID `<prefix>-src-<first-12-sha256>` (prefix set at instantiation; `mw-` in the source system).
7. Create its source record and searchable derivative. For a non-md source
   (pdf/docx/pptx/xlsx/html/epub), extract the derivative with
   `python scripts/file-to-md/to_md.py "<original>" -o "02-sources/text/<record-id>--<slug>.md"`
   (OCR routing: `.claude/skills/wiki-file-to-md/SKILL.md`).
8. Assign provisional family, authority scope, version role, extraction quality, and validation status. Do not infer sent/published status from filename.
9. Invoke `/wiki-reconcile` before altering canonical object, lineage, relation, claim, or system pages.
10. Update the manifest, corpus state, material register, source index, reconciliation audit, and system design when the intake changes the system.
11. Rebuild QMD: `qmd embed`.
12. Run full validation.
13. Write an intake report with unchanged areas and unresolved decisions.
14. Commit only after the user reviews the report.
