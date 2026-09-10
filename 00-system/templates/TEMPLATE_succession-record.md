---
id:
type: succession-record
title:
object_family:
status: active-note
visibility: private
created:
updated:
schema_version: 1.0.0
---

# {title}

Succession record (VMQ-inspired; T6 backlog item 1). One per major object
family. Answers what must survive the loss of current stewardship or software.
Fill one block per question; keep answers concrete and testable. A succession
record is governance documentation — it never upgrades any record's authority.

## Q1 — Behaviors to preserve

Which behaviors of this family matter, independent of current software?
(e.g., "checksum verification possible from Git alone"; "relation grammar stays
human-readable in Markdown")

## Q2 — Loss scenarios considered

Steward unavailable · tool/CLI removed · format obsolete · host lost ·
collaborator hostile. Which are realistic for this family?

## Q3 — Carriers of continuity

What carries the family forward in each scenario? (Git history, plain-text
derivatives under 02-sources/text/, this record itself, exports under
_exports/interchange/…)

## Q4 — Acceptable degradation

What may degrade without breaking identity? What must never degrade?

## Q5 — Revival procedure

Exact steps a successor would follow to resume work. Name files, scripts,
and validation commands (e.g., `python scripts/validate_repo.py --full`).

## Q6 — Review cadence

When was this last exercised, and when must it be re-tested?
