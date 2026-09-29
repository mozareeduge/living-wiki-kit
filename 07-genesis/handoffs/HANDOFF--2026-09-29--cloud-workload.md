---
id: wiki-handoff-2026-09-29-cloud-workload
type: handoff
title: "Cloud follow-up ladder Q1-Q6, stacked on PR #7 (1.3.0)"
branch: claude/remaining-tasks-workload-w9wft4
commit: 2df7db2
corpus_snapshot: wiki-corpus-empty
status: active
created: 2026-09-29
updated: 2026-09-29
schema_version: 1.0.0
---

# Cloud follow-up ladder Q1-Q6, stacked on PR #7 (1.3.0)

## Task and intended result

Find what is still open and turn it into a workload that a Claude Code cloud
session can finish. That session has only this repo: no `qmd`, no Obsidian,
no Windows machine, no instance. No code or content was changed.

## Files changed

- `Plans.md` (PR #7's version, merged in): findings F11-F13 added and a new
  "Ladder 1.3.x — cloud follow-ups (Q)" with Q1-Q6.
- `07-genesis/handoffs/HANDOFF--2026-09-29--cloud-workload.md` (this file).

## Files read

`Plans.md` on `main` and on `system/2026-09-20--next-version-plan` (PR #7),
`07-genesis/handoffs/HANDOFF--2026-09-20--kit-rollout-state.md`,
`SYSTEM_DESIGN.md` §6, `scripts/instantiate.py`, `scripts/schema_drift_fixer.py`,
`.github/workflows/validate.yml`, `INSTANTIATE.md`, `QUICKSTART.md`.

## Decisions accepted

- A first draft (ladder K1-K9, built from `main`) duplicated work that is
  already code-complete on PR #7 (S1-S3, R1, R2). It was replaced by a merge
  of PR #7's branch, adding only the residual Q rungs. The first draft remains
  in history, with no force-push.
- Q rungs wait for PR #7 to merge because they touch files it changes.

## Decisions not made

- Whether to attach `mozare-wiki` to a cloud session so F10 (flaky capture
  fixture port) and the F9/Q4 instance sync can become Q rungs.

## Validation commands and outcomes

On this branch after the merge (2026-09-29):

```
python scripts/validate_repo.py --full   -> see PR #8 body for the pasted run
python -m pytest tests scripts/tests scripts/capture/tests -q
```

CI: the `validate` job on PR #8 (run 36572654232) and every PR #7 run since
2026-09-29 08:04 end within seconds, before any step runs. PR #7 attributes
this to a GitHub billing block. The cause is at the account level, not in the
diff.

## Unresolved findings

F11 `mw-patch-` prefix not rewritten by `instantiate.py`; F12 `git add -A`
in the bootstrap path (three places); F13 `setup-after-clone.ps1` missing
from §6. Earlier findings F3/F4/F8/F10 are still open and are routed in `Plans.md`.

## Negative constraints

- Do not start a Q rung before PR #7 merges.
- Do not touch `_originals/` or any register in a Q rung.
- Do not add lines to `.githooks/known-baseline-errors.txt`.
- Do not claim M1, M2, H1-H3, U1, U2 from a cloud session.

## Next exact operation

Owner: clear the GitHub billing block, review and merge PR #7, then PR #8.
Agent, after that: set Q1 to `cc:wip` and paste the RED
`grep -n "mw-patch"` hit from a throwaway `--prefix smk` instantiate.

## Rollback

`git revert -m 1` the merge commit and revert the commit that added this file.
