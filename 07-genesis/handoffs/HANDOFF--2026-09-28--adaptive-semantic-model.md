---
id: wiki-handoff-2026-09-28-adaptive-semantic-model
type: handoff
title: "Adaptive semantic model implemented (W1, O1-O8)"
branch: system/2026-09-20--next-version-plan
corpus_snapshot: wiki-corpus-empty
status: active
created: 2026-09-28
updated: 2026-09-28
schema_version: 1.0.0
---

# Handoff — adaptive semantic model (dossier v1.0, 2026-09-28)

Design source: `LIVING-WIKI-KIT-ADAPTIVE-SEMANTIC-DESIGN-DOSSIER-v1.0-2026-09-28.md`
(owner machine, Downloads). This record is the in-repo decision summary.

## Decision summary

- object kind closure retired (schema: kind optional/deprecated, no enum)
- labels adopted (mechanical rules only, open-world, never evidence)
- profiles/lenses designed (composable substrate, 6 + 2 inactive examples)
- candidate visibility preserved (projection, not silent canonicalization)
- O1-O8 added to ladder and executed; W3 unblocked

## Commits (oldest first)

- W1 (`cfbefeb`): 17-kind door enum, source_passage check, audit + holdings
  read the durable queue; policy v1.1.0 with 9 new kind specs, tier-enum fix
- O1 (`ab8919a`): open object schema + template labels
- O2 (`dee20d4`): SEMANTIC_MODEL.md + agent guidance (write skill, docs)
- O3 (`5603b57`): label index (raw+norm, non-evidence) + pack label-match
- O4 (`f3deed4`): profile schema/substrate/examples, `wiki_profiles check`,
  instantiate seeds `active_profiles: []`
- O5 (`4cfc0a3`): lens schema/examples, pack foregrounding + accepted-only
- O6 (`fdb0157`): candidate projection into disposable index; pack + search
  visibility; adjudication fate; audit assess extraction
- O7 (`cb8707e`): legacy-kind compat indexing, read-only label audit,
  dry-run migration tool
- O8 (this handoff): end-to-end acceptance green

## Owner constraints honored (binding on later rungs)

- Object vocabulary stays open: no enum enforcement, no template kind
  constraints, no "must carry kind" rules (H0 handoff `a785d56`).
- Adjudication promotes authority; it never gates the pipeline or grants
  visibility. Candidates included by default, relevance and authority
  reported separately, accepted-only always explicit.

## Proof

- `pytest tests scripts/tests scripts/capture/tests` → 316 passed,
  1 skipped, 2 xfailed
- `wiki_validate.py`, `wiki_state.py check`, `wiki_evidence.py check`,
  `wiki_profiles.py check` → exit 0
- `validate_repo.py --full` PASS; `check_against_baseline.py` clean;
  `report_holdings.py` → CENSUS CLEAN
- Fresh smoke instantiate (`Smoke/sm`) passes all of the above

## Deviations from the dossier (small, deliberate)

- O4 profiles and O5 lenses ship 6 + 2 inactive *examples* (dossier's full
  six-domain validation set is represented at practice level; domain/
  collaboration/compliance classes are schema-supported, unshipped).
- `migrate_object_kinds.py` maps to `labels + legacy_kind` exactly as
  specified; runs dry-run by default, operator-gated.
- Flow-style `labels: [a, b]` also indexes (template uses block style).

## Next exact operation

W3 (staged reconciliation) against the new semantic rules. One `cc:wip`
rung at a time; no force-push.
