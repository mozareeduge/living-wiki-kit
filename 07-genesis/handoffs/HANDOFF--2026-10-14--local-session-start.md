---
id: wiki-handoff-2026-10-14-local-session-start
type: handoff
title: "Local session start: finish releasing kit 1.4.0 (CI runner, merge, tags)"
branch: ccr-f635c748-jbckhg
corpus_snapshot: wiki-corpus-empty
status: active
created: 2026-10-14
updated: 2026-10-14
schema_version: 1.0.0
---

# Handoff — start here in a local session

Everything for kit **1.4.0** is built, tested and pushed to PR #9. The only
thing missing is a CI run, and that needs this machine: the CI runner is the
self-hosted runner on the owner's PC. Detail on what was built and why:
`HANDOFF--2026-10-13--independence-and-1-3-x.md`. Task truth: `Plans.md`.

## 1. Get the branch

```bash
cd <your living-wiki-kit checkout>
git fetch origin
git switch ccr-f635c748-jbckhg
git pull --ff-only
git config core.hooksPath .githooks        # pre-commit gate (now executable)
python -m pip install -r requirements.txt -r requirements-governance.txt pytest
```

## 2. Prove it locally (expected results)

```bash
python -m pytest tests scripts/tests scripts/capture/tests -q   # 498 passed, 2 xfailed
python scripts/check_against_baseline.py                        # OK: validators clean
python scripts/wiki_validate.py --repo . --format json          # exit 0
python scripts/wiki_state.py --repo . check                     # exit 0
python scripts/wiki_evidence.py --repo . check                  # exit 0
python scripts/wiki_profiles.py check                           # 0 active (profile-neutral kit)
python scripts/release_smoke.py                                 # RELEASE SMOKE PASS
```

On Windows, the first full run is the first time the new tests run on this
OS. If something fails only here, fix it on this branch before merging.

## 3. Release, in order

1. **Start the GitHub Actions runner** on this PC (the one registered for
   this repository). PR #9's two queued jobs, `validate` and `fresh-wiki`,
   then start by themselves. Alternative: in the repo settings, set the
   variable `CI_RUNNER` to `ubuntu-latest` (or delete it) and re-run.
2. **Check:** both jobs green on PR #9.
3. **Merge:** mark PR #9 ready for review, then merge into `main`.
4. **Tag** (the cloud session could not push tags):
   ```bash
   git switch main && git pull --ff-only
   git tag -a v1.3.0 e492df9 -m "living-wiki-kit 1.3.0"
   git tag -a v1.4.0 HEAD   -m "living-wiki-kit 1.4.0"
   git push origin v1.3.0 v1.4.0
   ```
5. Optional: create a GitHub release for `v1.4.0` from the CHANGELOG 1.4.0
   section, and update the repository description on GitHub (it still names
   the archive the kit came from).

## 4. Things that changed and may touch your local setup

- **MCP server renamed** to `wiki-governance` in `.mcp.json`. Any local
  harness config or allowlist that used the old server name needs the new
  one.
- **Author authority is a setting now.** In any wiki where your own
  promoted captures should count as author confirmation (authority level 3),
  add your actor name to `author_actors` in
  `00-system/configuration/evidence-sources.json`. The kit ships it empty,
  so without it every promotion is level 6.
- **Retrieval index** default is `_search/retrieval.sqlite`, and release
  receipts default to `.git/wiki-governance/evidence`. The old index file
  can be deleted; it is rebuildable.
- New options: `instantiate.py --profile <id>`, optional
  `LABEL_ALIASES.json`, and profile `tighten` rules (see `CHANGELOG.md`
  1.4.0).

## 5. Decisions on record (2026-10-13), do not reopen

- The kit is independent; no trace of the owner's personal wikis in any
  tracked file. A guard test (`tests/test_kit_independence.py`) enforces it.
- No more example profiles.
- New wikis keep the kit's history; nothing is stripped at setup.
- PR #8 is closed; PR #9 replaces it.

## 6. Negative constraints

- Never force-push and never rewrite history to scrub old names. Older
  commits keep them; the owner accepted this.
- Do not add personal wiki names, local paths or personal names to any
  file. The guard test will fail.
- Stage named paths, never `git add -A`.

## 7. Prompt for a local Claude session

> Read `07-genesis/handoffs/HANDOFF--2026-10-14--local-session-start.md`
> and `CLAUDE.md`. Run section 2 and show me the results. If everything
> passes, help me with section 3 step by step and stop before each merge or
> push for my OK.
