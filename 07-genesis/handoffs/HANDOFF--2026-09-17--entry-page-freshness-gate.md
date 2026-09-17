---
id: wiki-handoff-2026-09-17-entry-gate
type: handoff
title: "Entry-page freshness gate and kit 1.1.0"
branch: system/2026-09-16--harden-kit-spec
commit: 62fa873566b50b2e6c193afc46a634fe0b415669
corpus_snapshot: wiki-corpus-empty
status: active
created: 2026-09-17
updated: 2026-09-17
schema_version: 1.0.0
---

# Entry-page freshness gate and kit 1.1.0

## Task and intended result

Close the openspec change `harden-kit-against-state-drift`: entry pages must
stop carrying hand-copied corpus facts that silently drift from the
registers. Result: the four entry pages carry labelled markers, the
validator fails any commit whose pages lag `CORPUS_STATE.json`, the
instantiator seeds those markers and refuses to reseed a live instance, and
the kit ships as 1.1.0.

## Files changed

- `scripts/validate_repo.py` — `check_entry_pages()` helper; called from
  `validate()` after the manifest/state agreement check; stale-marker errors
  now quote the value actually on the page.
- `scripts/instantiate.py` — pre-write preconditions (populated corpus,
  different instance), empty corpus id rename, marker rewrite on four pages,
  `README.md` added to target globs, `created_from` 1.1.0.
- `tests/test_validator_mutations.py` — real `__main__` runner; gate tests;
  instantiator smoke/idempotence/refusal tests; gate-wiring tests.
- `README.md`, `HOME.md`, `SYSTEM_DESIGN.md`, `CLAUDE.md` — markers,
  live-truth pointers, §6 gate documentation, version bullet.
- `INSTANTIATE.md` — §3.5 markers, refresh duty, capture exception, manual
  adoption order for an existing instance.
- `00-system/templates/TEMPLATE_source-record.md` — `filename:` field.
- `00-system/configuration/content-release.json` — `system_version` 1.1.0.
- `.claude/skills/wiki-reconcile/SKILL.md` — reads the baseline from
  `CORPUS_STATE.json` at run start instead of a hardcoded id.
- `.claude/skills/wiki-intake/SKILL.md` — step 10 refreshes the markers in
  the same change as a register change.
- `.github/workflows/validate.yml` — CI runs the mutation suite.
- `openspec/changes/harden-kit-against-state-drift/tasks.md` — 1.1–5.3
  checked.

## Files read

`SYSTEM_DESIGN.md`, `CLAUDE.md`, the openspec proposal/design/spec,
`.githooks/pre-commit`, `.githooks/known-baseline-errors.txt`,
`scripts/check_against_baseline.py`.

## Decisions accepted

- Markers are labelled (`Current corpus snapshot:` / `Registered source
  artifacts:`), so a coincidental numeral or version string cannot satisfy
  the gate.
- The gate runs inside `validate()`, so the pre-commit hook and CI enforce
  it with no separate command.
- Kit version bumped to 1.1.0 atomically across four declarations plus a
  README release note; no `schema_version` changed.
- CI now runs `tests/test_validator_mutations.py` (stdlib only), because
  `check_against_baseline.py` alone never exercised the suite.

## Decisions not made

- Existing instances are NOT migrated automatically. Adoption is manual and
  documented in INSTANTIATE.md §3.5; `instantiate.py` refuses a populated
  corpus rather than reseeding it.
- No automatic marker-refresh writer was added; refreshing stays a human/
  skill step inside the same change as the register update.

## Validation commands and outcomes

```
python tests/test_validator_mutations.py      -> 23/23 passed
python scripts/validate_repo.py --full        -> PASS
python scripts/validate_content_release.py    -> PASS
python scripts/check_against_baseline.py      -> OK: validators clean
```

Hook proof, disposable local clone with `core.hooksPath=.githooks` (never
pushed, since removed): changing only `CORPUS_STATE.json`'s id was BLOCKED
with four errors naming HOME.md, README.md, SYSTEM_DESIGN.md and CLAUDE.md
stale snapshot markers; refreshing the four markers and retrying passed the
same baseline gate CI uses.

PR #2 merged to main with CI green (`validate` job, 23/23 suite + baseline).
Remote main and local main are both
`62fa873566b50b2e6c193afc46a634fe0b415669`.

## Unresolved findings

- The layer-count rule reads visible prose, so an entry page that describes
  layer counts in an unusual phrasing (not `N objects/relations/claims/
  indexes`) is still ungoverned.
- `validate_content_release.py` keeps six pre-existing baseline errors in
  `.githooks/known-baseline-errors.txt` (short person/research notes,
  orphan canonical records). Untouched by this change.
- The openspec change is finalized but not archived under
  `openspec/changes/archive/`.

## Negative constraints

- Do not rerun `scripts/instantiate.py` on a populated instance; it refuses,
  and forcing it would rewrite live register ids.
- Do not add an entry-drift line to `.githooks/known-baseline-errors.txt`;
  drift is a bug, not tolerated debt.
- `_originals/` remains untouched; no runtime dependency was added.

## Next exact operation

Archive the openspec change:
`git mv openspec/changes/harden-kit-against-state-drift openspec/changes/archive/`,
then run `python scripts/validate_repo.py --full` and commit on a branch.

## Rollback

`git revert -m 1 62fa873` on a branch, then rerun both validators. Reverting
restores kit 1.0.0 behaviour; entry pages keep their markers harmlessly
because nothing then reads them.
