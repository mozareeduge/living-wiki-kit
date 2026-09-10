# The Lifecycle: From Raw Material to Inquiry

The operating loop of a living genetic archive. Each stage has a named
procedure; nothing jumps stages.

## Stage 0 — Arrival (01-inbox/)

Raw material lands in `01-inbox/` (files dropped in, voice/text via the
governed capture system, or web captures per `RUNBOOK_WEB_CAPTURE.md`).
Nothing is canonical here. Capture records are level-7, deduplicated by
content hash, checksummed, and never touch canonical areas.

- Text/voice: `python scripts/capture/wiki_capture.py capture-text --channel mcp --lang fa --text "<exact text>"`
- Media: `python scripts/capture/wiki_capture.py capture-media --src <path> --kind voice --channel mcp`
- Transcription commit: `... commit-transcript --id <id> --text "<transcript>" --adapter <adapter> --version <n>`
- Validate: `python scripts/capture/wiki_capture.py --json validate`

Rules: capture VERBATIM; report only ID, status, path; promotion is
proposal-only after human review.

## Stage 1 — Intake (manual skill: wiki-intake)

Preserve and register: inventory every inbox file (bytes, SHA-256, format,
language, title), dedupe by checksum and normalized text, copy exact
artifacts into `_originals/` (never overwrite), mint content-derived IDs
(`<prefix>-src-<first-12-sha256>`), create source records and searchable
derivatives, assign authority scope and validation status, update
manifest/corpus state, and stop for human review before commit.

Derivative extraction for non-md sources runs through
`scripts/file-to-md/to_md.py` (see `.claude/skills/wiki-file-to-md/SKILL.md`
for OCR routing and Persian-text caveats).

Key discipline: do not infer sent/published status from a filename.

## Stage 2 — Reconciliation (manual skill: wiki-reconcile)

Before any corpus-wide change: every manifest row read exactly once (batched
through context-isolated subagents, 8–12 artifacts each), receipts merged
into an impact matrix, gaps stop the run. Propose; apply only after the
human approves the impact report.

## Stage 3 — Inquiry (manual skill: wiki-search)

Bounded questions answered in authority order: canonical page → claim/relation
→ source record → derivative → original. Answers report source paths,
evidence status, unresolved points. Search scores are never proof.

## Stage 4 — Creation of objects, relations, claims (manual skill: wiki-write)

Canonical pages are created from approved evidence with explicit target,
genre, and authority level. Objects characterize before contrast; relations
are recorded before classification (relation-objects); claims carry
permission levels (`may-note` … `blocked`) with support, counter-evidence,
and responsible language. Every consequential statement links to source or
claim records.

## Stage 5 — Genesis tracking (07-genesis/)

Lineages record how objects changed; events record consequential actions
(intake, extraction, revision, rejection, AI generation); residue records
what was removed without erasure and why; handoffs record session
continuation state. Version history is additive: later drafts never erase
earlier ones.

## Stage 6 — Validation and release

```bash
python scripts/validate_repo.py --full        # structure, checksums, links
python scripts/validate_content_release.py    # populated-layer gate
python scripts/export_interchange.py prov     # PROV-O graph export
python scripts/export_public.py               # sensitivity-reviewed public export (outside repo)
```

A numeric threshold is a defect detector, not a quality certificate. Static
pass ≠ local operational pass; GitHub Actions green + local validation pass
are both required before reporting a release-state change.

## Continuous guardrails

- Pre-commit hook + CI run the same baseline gate (`check_against_baseline.py`).
- QMD scores organize attention, never evidence.
- All AI output stays candidate-tier; promotion runs through
  `_proposals/proposals.jsonl` + human adjudication.
- Backups: local clone + private remote + dated external ZIP
  (`scripts/create-backup.ps1`).
