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

1. Run the governance gate first: `python scripts/wiki_validate.py --format json` and `python scripts/wiki_state.py --repo . check`. Stop if either fails. (Raw `validate_repo.py --full` also reports reviewed baseline debt in `.githooks/known-baseline-errors.txt`; it is diagnostic, not the gate.)
2. Create branch `intake/YYYY-MM-DD--short-name`.
3. Inventory every inbox file: filename, format, bytes, SHA-256, extraction feasibility, visible title, language, and supplied status.
4. Compare checksums and normalized text against the manifest.
5. Copy each new exact artifact into `_originals/`. Never overwrite an existing path.
6. Create a content-derived source ID `<prefix>-src-<first-12-sha256>` (prefix set at instantiation).
7. Create its source record and searchable derivative. For a non-md source
   (pdf/docx/pptx/xlsx/html/epub), extract the derivative with
   `python scripts/file-to-md/to_md.py "<original>" -o "02-sources/text/<record-id>--<slug>.md"`
   (OCR routing: `.claude/skills/wiki-file-to-md/SKILL.md`).
8. Assign provisional family, authority scope, version role, extraction quality, and validation status. Do not infer sent/published status from filename.
9. Invoke `/wiki-reconcile` before altering canonical object, lineage, relation, claim, or system pages.
10. Set `updated` in `CORPUS_STATE.json` to the intake date, then update the material register, source index, reconciliation audit, and system design prose when the intake changes the system (registers marked `per-intake` must carry an `updated` date no older than the corpus). Whenever registered corpus state changes (snapshot id or source count in CORPUS_STATE.json), refresh the labelled markers — `Current corpus snapshot:`, `Registered source artifacts:`, `Artifacts held:` — plus any layer-count prose on all four entry pages (HOME.md, README.md, SYSTEM_DESIGN.md, CLAUDE.md) from the registers in the same change; the entry-page freshness gate in `validate_repo.py` fails the commit otherwise. An unregistered governed capture (resting in `01-inbox/captures/`) changes no register and triggers no refresh.
11. Regenerate the derived registers, then sync the numbers the intake changed:
    - `python scripts/wiki_state.py --repo . rebuild` (manifest rows, corpus snapshot/counts, system state, evidence index; generated from source records with `status: registered`)
    - `python scripts/sync_intake_registers.py --accept-corpus-change` (dry run), then add `--apply` (holdings counts, entry-page markers, content-release corpus pin)
12. Rebuild search: `python scripts/retrieval/build_index.py --repo .` and `qmd embed`.
13. Run full validation: `python scripts/wiki_validate.py --format json`, `python scripts/wiki_state.py --repo . check`, `python scripts/wiki_evidence.py --repo . check`. All must exit 0.
14. Write an intake report with unchanged areas and unresolved decisions.
15. Commit only after the user reviews the report.

## Registering an item already held (`status: pending-registration`)

Its original and source record already exist. Instead of steps 3-7:

1. Confirm the original is exact: SHA-256 of `original_path` equals the record's `sha256`.
2. Repair a filename cut at the first space: `python scripts/repair_truncated_filenames.py --status pending-registration` (dry run), then `--apply`. Anything listed under `needs_review` is fixed by hand or left for the user.
3. Set `status: registered` and remove `holdings_tier` in the source record; complete family, authority scope, version role, and extraction quality.
4. Continue with steps 8-15.
