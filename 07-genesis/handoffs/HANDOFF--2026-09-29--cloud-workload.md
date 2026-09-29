---
id: wiki-handoff-2026-09-29-cloud-workload
type: handoff
title: "Remaining work triaged into a cloud-finishable ladder (K1-K9)"
branch: claude/remaining-tasks-workload-w9wft4
commit: 02399e7
corpus_snapshot: wiki-corpus-empty
status: active
created: 2026-09-29
updated: 2026-09-29
schema_version: 1.0.0
---

# Remaining work triaged into a cloud-finishable ladder (K1-K9)

## Task and intended result

Find what is still open after the 2026-09-20 rollout and turn it into a
workload that a Claude Code cloud session (this repo only; no `qmd`, no
Obsidian, no Windows, no instance) can finish. No code or content was changed.

## Files changed

- `Plans.md`: new active ladder K1-K9 plus a carried-items table (R1-R6);
  census ladder retitled "Completed"; B4/C3 marked `cc:done` with their
  instance-side evidence pointer.
- `07-genesis/handoffs/HANDOFF--2026-09-29--cloud-workload.md` (this file).

## Files read

`Plans.md`, `_captures/HANDOFF--2026-09-20--kit-rollout-state.md`,
`SYSTEM_DESIGN.md` §6, `scripts/instantiate.py`, `scripts/schema_drift_fixer.py`,
`.github/workflows/*.yml`, `requirements.txt`, `00-system/templates/TEMPLATE_handoff.md`.

## Decisions accepted

- Only rungs that finish without an instance, `qmd`, Obsidian or Windows go in
  ladder K. Everything else is carried as R1-R6 with its reason.
- K2 adds missing §6 rows without re-tiering any status; re-tiering and the
  version question are operator-gated in K9.

## Decisions not made

- Whether the post-1.2.0 work ships as 1.2.1 or 1.3.0 (K9).
- Whether to add `pyproject.toml` (K9).
- Whether to attach `mozare-wiki` to a cloud session for R3.

## Validation commands and outcomes

Run on `02399e7`, 2026-09-29:

```
python scripts/validate_repo.py --full        -> PASS (only openspec-archive "no frontmatter" warnings)
python scripts/validate_content_release.py    -> PASS
python scripts/check_against_baseline.py      -> OK: validators clean.
python tests/test_validator_mutations.py      -> 102/102 passed
python -m unittest discover -s tests          -> 3 errors: No module named 'pytest'
pip install pytest; python -m pytest -q       -> 126 passed
throwaway clone: instantiate.py --name "Smoke Wiki" --prefix smk
  -> validate_repo.py --full PASS; report_holdings.py "7. Verdict: CENSUS CLEAN"
```

## Unresolved findings

1. CI never runs the 24 pytest tests; `pytest` is in no requirements file (K1).
2. Nine scripts are missing from SYSTEM_DESIGN §6; the D1 test cannot see an
   absent row. Two existing cells are stale (K2).
3. `schema_drift_fixer.py` hardcodes `mw-patch-`, which `instantiate.py` does
   not rewrite (K3).
4. `schema_drift_fixer.py` and `wiki_mcp_server.py` have no tests (K4).
5. `instantiate.py` tells new users to `git add -A` (K6).

## Negative constraints

- Do not touch `_originals/` or any register in a K rung.
- Do not add lines to `.githooks/known-baseline-errors.txt`.
- Do not re-tier §6 statuses or bump the version outside K9.
- Do not claim R1-R6 from a cloud session.

## Next exact operation

Set K1 to `cc:wip` in `Plans.md`, add `requirements-dev.txt`
(`-r requirements.txt`, `pytest`), add `python -m pytest -q` to the CI
workflow, and paste `126 passed` from a fresh venv.

## Rollback

`git revert` the commit that added this file; it touches only `Plans.md` and
this handoff.
