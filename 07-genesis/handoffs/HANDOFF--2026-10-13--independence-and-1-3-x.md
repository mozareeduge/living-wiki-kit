---
id: wiki-handoff-2026-10-13-independence-and-1-3-x
type: handoff
title: "Kit 1.4.0: independence, ladder 1.3.x, owner decisions (privacy, tightening, aliases, setup profiles)"
branch: ccr-f635c748-jbckhg
corpus_snapshot: wiki-corpus-empty
status: active
created: 2026-10-13
updated: 2026-10-13
schema_version: 1.0.0
---

# Handoff — kit independence and ladder 1.3.x

Supersedes `HANDOFF--2026-10-02--lwk-1-3-0-transfer-state.md` for status.
Task truth stays `Plans.md`.

## 1. State at hand-off

- 1.3.0 is released into `main`: PR #7 merged 2026-10-03 as `e492df9`;
  CI run #69 green. The account-level Actions block in the 10-02 handoff
  is resolved. No `v1.3.0` tag or GitHub release exists yet.
- Owner decision 2026-10-13: **the kit is an independent project.** See the
  decision block at the top of `Plans.md`. Instance-lane rungs (M1, H1–H3,
  U2, D-e) are `moved-to-instance`.
- This branch carries ladder 1.3.x, all `cc:done` except Q6's CI log,
  which the PR's first run supplies.

## 2. Changed (one commit per rung)

| Commit | What |
|---|---|
| `7f67af7` | F19: graph index resolves record ids in any instance prefix |
| `9cd6584` | O9: lenses foreground relation language (`relation_type`) and section order |
| `e7231a2` | O10: active profiles add seed-label reasons; suggested lenses offered |
| `8ea8cf0` | Independence: object/claim schemas accept any prefix; no foreign names |
| `2307ad4` | O11: six practices on one unchanged kernel; four example lenses added |
| `cc69d22` | O12 + independence naming across shipped files; `build_pack` closes its DB |
| `383a080` | Q1–Q3: prefix everywhere, current-year run ids, review-first commit, setup script fixed |
| `03fc25c` | Q6: `scripts/release_smoke.py` + CI job `fresh-wiki` |
| `7127c00` | Privacy: instance benchmark reports removed, history neutralised, `author_actors` replaces a built-in name, guard scans every file |
| `6a7c52e` | D-d: `instantiate.py --profile` |
| `0e89eb2` | D-c: optional label aliases (retrieval only) |
| `16d0447` | D-b: profile `tighten` rules enforced by `wiki_profiles.py check` |
| `7b9b46d` | F24: tests close every sqlite handle; pre-commit hook executable |
| (release) | Kit 1.4.0: version declarations, CHANGELOG, Plans, this handoff |

## 3. Decisions taken in this session

- `relation_type` is an **optional** relation-object field (string or list).
  Relation before type still holds. It is indexed in a non-evidence table,
  never as an edge.
- Profiles **annotate only**: they never pull a record into a pack, drop it,
  or reorder it. Lens offers carry `available: true|false`.
- The MCP server is registered as `wiki-governance` (was the old project's
  name). Harness configs that pinned the old server name need the new one.
- Retrieval DB default is `_search/retrieval.sqlite`; release receipts
  default to `.git/wiki-governance/evidence`.
- The first commit of a new wiki stages `.` after `git status --short`;
  every later change stages named paths.

## 4. Validation (re-run before hand-off)

```bash
python -m pytest tests scripts/tests scripts/capture/tests -q   # 498 passed, 2 xfailed
python scripts/check_against_baseline.py                        # OK: validators clean
python scripts/wiki_validate.py --repo . --format json          # exit 0
python scripts/wiki_state.py --repo . check                     # exit 0
python scripts/wiki_evidence.py --repo . check                  # exit 0
python scripts/wiki_profiles.py check                           # 0 active (profile-neutral kit)
python scripts/release_smoke.py                                 # RELEASE SMOKE PASS (9 steps)
```

Until `7b9b46d` the pre-commit hook was not executable, so
`check_against_baseline.py` was run by hand before each commit; since then
the hook runs it.

## 5. Owner decisions taken (second batch, 2026-10-13)

- "No trace of my personal wikis" → F21 done (see `7127c00`).
- "Leave out more profiles" → D-a: no new example profiles.
- "Don't remove histories" → F22: a new wiki keeps the kit's history.
- "Close the old PR" → PR #8 closed with a pointer to #9.
- "Do everything else and finish the new version" → D-b, D-c, D-d, F24
  built; kit declared 1.4.0.

## 6. Unresolved

- CI on PR #9 waits for the self-hosted runner `owner-pc` (repo variable
  `CI_RUNNER`); start it, or point `CI_RUNNER` at `ubuntu-latest`.
- Tags `v1.3.0` (on `e492df9`) and `v1.4.0` (on the merge of #9) must be
  pushed by the owner; this session's git proxy refuses tag pushes.
- Git history before `7127c00` and the GitHub repo description still carry
  the old names; changing history needs a force-push (not done).
- `setup-after-clone.ps1` was fixed and checked statically only.

## 7. Negative constraints

- Do not add instance data or instance-specific names to shipped files; the
  independence guard test will fail.
- Do not let a profile or lens add, drop or reorder pack records, or touch
  authority; tests in O9–O11 pin this.
- Do not reintroduce a name-rewrite table in `instantiate.py`.

## 8. Next exact operation

Bring the runner online so PR #9's two jobs (`validate`, `fresh-wiki`) run;
when green, mark the PR ready, merge, and tag `v1.4.0` on the merge commit
(plus `v1.3.0` on `e492df9`).
