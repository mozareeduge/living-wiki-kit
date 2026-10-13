---
id: wiki-handoff-2026-10-13-independence-and-1-3-x
type: handoff
title: "Kit independence + ladder 1.3.x (lenses, profiles, six practices, setup polish, fresh-wiki CI)"
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
python -m pytest tests scripts/tests scripts/capture/tests -q   # 476 passed, 2 xfailed
python scripts/check_against_baseline.py                        # OK: validators clean
python scripts/wiki_validate.py --repo . --format json          # exit 0
python scripts/wiki_state.py --repo . check                     # exit 0
python scripts/wiki_evidence.py --repo . check                  # exit 0
python scripts/wiki_profiles.py check                           # 0 active (profile-neutral kit)
python scripts/release_smoke.py                                 # RELEASE SMOKE PASS (9 steps)
```

The repo's git hooks are not executable in this checkout (`core.hooksPath`
set, files lack `+x`), so `check_against_baseline.py` was run by hand
before every commit.

## 5. Unresolved

- **F21** (owner): instance benchmark reports under `_audits/` hold machine
  paths and private filenames in this public repo.
- **F22** (owner): a new wiki inherits the kit's own history (`.maws/`,
  `Plans.md`, kit handoffs, kit audits, `openspec/`).
- **F24** (minor): other tools still leave sqlite connections open.
- Owner decisions D-a … D-d (see `Plans.md`).
- `setup-after-clone.ps1` was fixed and checked statically only; no
  PowerShell was available here.

## 6. Negative constraints

- Do not add instance data or instance-specific names to shipped files; the
  independence guard test will fail.
- Do not let a profile or lens add, drop or reorder pack records, or touch
  authority; tests in O9–O11 pin this.
- Do not reintroduce a name-rewrite table in `instantiate.py`.

## 7. Next exact operation

Watch the PR's first CI run: both jobs `validate` and `fresh-wiki` must be
green, which completes Q6. Then merge, tag `v1.3.0` on `e492df9` (or cut
1.3.1 from the merge, owner's call), and take the owner's answers on F21,
F22 and D-a … D-d.
