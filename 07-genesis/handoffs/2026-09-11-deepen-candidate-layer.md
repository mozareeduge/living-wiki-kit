---
id: ref-handoff-2026-09-11-deepen
type: handoff
title: Deepen pass — research-campaign candidate layer (2026-09-11)
branch: intake/2026-09-10--research-campaign
commit: (this commit)
corpus_snapshot: ref-corpus-2026-09-10
status: active
created: '2026-09-11'
updated: '2026-09-11'
schema_version: 1.0.0
---

# Deepen pass — research-campaign candidate layer

## Task and intended result

Deepen ref-wiki around the eleven registered research-campaign sources: create the
candidate object/relation/claim layer the dossiers support, grounded only in the
registered dossier text. Done in this session after the subagent delegation path
proved unusable (4 failed waves; root cause: upstream 500/503 on streamed
tool-bearing requests without an explicit max_tokens cap — config now pins
`delegation.provider: 9router` + `max_output_tokens: 4096`, verified resolving).

## Files created

- 82 object records under `03-objects/` (23 references, 17 concepts, 15 methods,
  12 people, 14 works, 1 institution) — all candidate-tier
- 40 relation records under `06-relations/` — `relation_status: candidate`,
  `current_claim_permission: may-note`
- 8 claim records under `05-claims/` — governance-stack-original verdict,
  four-recurring-gaps, three cross-track negatives, terminology status
  (speculative-research-poetry distinct from Lahman; mixt attribution BLOCKED),
  OOO uptake shape, artistic-research provenance gap, authority-hierarchy
  anticipation of the RAG frontier
- `_proposals/mine_data.py` — the deterministic generator (re-runnable)

## Files read

All 11 derivatives under `02-sources/text/` (bounded section reads, headings +
key sections); no originals re-opened (md sources, derivatives are verbatim).

## Decisions accepted

- Subagent delegation abandoned after 4 waves; mined directly in-session.
- Wikilinks link by file stem (mozare-wiki convention), not record id —
  id-style links normalized to stem links (the validator resolves stems).
  Examples below are escaped as code so they are not scanned as live links.
- Every record carries `candidate_tier: true` / `relation_status: candidate`
  and cites its dossier sources; nothing canonical was touched.

## Decisions not made (human gates)

- Adjudication of all 130 candidate records (upgrade/merge/correct/delete).
- mixt attribution: BLOCKED on author identification (candidate referent:
  Baetens 2013 'Monomedial Hybridization' — NOT an identification).
- Which backlog methods (15 ADOPT/ADAPT items) to schedule.

## Validation commands and outcomes

- `python scripts/validate_repo.py --full` → PASS (structure, metadata,
  manifest, checksums, links valid; known frontmatter warnings only).
- 95 wikilink errors found and fixed during the pass (id-links → stem-links,
  2 slug typos corrected).