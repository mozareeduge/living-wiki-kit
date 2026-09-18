---
id: wiki-handoff-2026-09-18-census-gate
type: handoff
title: "Census gate (kit 1.2.0) handoff to Hermes"
branch: system/2026-09-18--census-implementation
commit: 218818c
corpus_snapshot: wiki-corpus-empty
status: active
created: 2026-09-18
updated: 2026-09-18
schema_version: 1.0.0
---

# Census gate (kit 1.2.0) handoff to Hermes

## State
- Branch `system/2026-09-18--census-implementation`, pushed; PR #6 open, CI green, NOT merged.
- Ladder: `Plans.md` (root). Spec: `openspec/changes/corpus-census-truth/`. Read `EXECUTOR_BRIEF.md` first.
- Done: A1-A5, B1-B3, C1, C2, D1, E1. Suite 102/102; all validators PASS.

## Remaining (in order)
1. Merge PR #6 after operator review.
2. B4 (operator-gated): adopt the census in mozare-wiki. Needs the tier decision for 447 held
   records; recommended `pending-registration`. They ARE ingested (original + record +
   derivative, ~3.9M words, intake 2026-09-04 commit 3bb89f7); only the frozen release
   manifest omits them.
3. C3 (operator-gated): tag mozare-wiki's 13 registers with refresh_policy; operator decides
   archive vs refresh per register.
4. Z1 archive the openspec change; Z2 run `report_holdings.py` in both repos, expect CENSUS CLEAN.

## Negative constraints
Never edit `_originals/`, `MATERIALS_INDEX.jsonl` or sha256 values; never add baseline lines;
never rerun `instantiate.py` on a populated instance; never skip hooks or force-push.

## Validate
`python tests/test_validator_mutations.py` · `python scripts/validate_repo.py --full` ·
`python scripts/check_against_baseline.py`
