---
id: wiki-handoff-2026-09-25-k1-kernel-port
type: handoff
title: "Kit 1.3.0 hand-off: governance kernel port (K1) half done, finish K1c/K1d, then owner decides H0"
branch: system/2026-09-20--next-version-plan
commit: b5272cb
corpus_snapshot: wiki-corpus-empty
status: active
created: 2026-09-25
updated: 2026-09-25
schema_version: 1.0.0
---

# HANDOFF — 2026-09-25 — living-wiki-kit: kernel port (K1)

Written for any harness or person picking this up, with no access to earlier
conversations or machine memory. Trust the repository over this note: every
claim below names the command that proves it. Task truth is `Plans.md`,
section "Ladder 1.3.0". This note supersedes
`HANDOFF--2026-09-20--kit-rollout-state.md` for the kit.

## 1. The order the owner set

1. **Finish K1** — rungs `K1c` then `K1d` (below). Agent work, about 1 hour.
2. **Stop.** The owner decides **H0** (proposal-kind vocabulary, section 5).
3. Then continue the ladder: `W1 → W3 → W4 → M2 → R1 → R2`.

Do not start W1 before the owner has recorded H0.

## 2. Where things are (verified 2026-09-25)

| Item | Value | Check |
|---|---|---|
| Kit repo | `github.com/mozareeduge/living-wiki-kit` (**public**) | `gh repo view --json visibility` |
| Working branch | `system/2026-09-20--next-version-plan`, = origin | `git status -sb` |
| Open PR | #7 (draft) from that branch to `main` | `gh pr view 7` |
| Last code commit | `b5272cb` K1b | `git log --oneline -6` |
| Kit tests | `pytest tests scripts/tests` → 213 passed, 2 xfailed | run it |
| Gates | `validate_repo.py --full` PASS; `wiki_validate.py --format json`, `wiki_state.py --repo . check`, `wiki_evidence.py --repo . check` all exit 0 | run them |
| Instance repo | `mozareeduge/mozare-wiki` (**private**), `main` = `630a998`, CI green | owner access needed |

Commits on the branch since `main` (oldest first): S1, S2, S3 (docs, CI, tests),
W2 (`wiki_context_pack`), `c0dc845` (three bug fixes ported from mozare-wiki),
`e651c11` + `18423f3` (K1a kernel core, LF pin), `b5272cb` (K1b kernel MCP server).

## 3. What K1 is and why

In September the private instance `mozare-wiki` installed an externally built
"Governance Kernel v1.2.1": a fail-closed validation gate, one generated state
file (`SYSTEM_STATE.json`), an accepted-evidence index, immutable proposal and
adjudication records, portable SQLite FTS search, and an MCP server that is
read-only unless started with `--profile capture`. The kit had none of it.
K1 ports it into the kit in generic form. Instance names stay as `mw-` ids and
the word "mozare" in code; `scripts/instantiate.py` rewrites both when a new
wiki is created (its `TARGET_GLOBS` now include the kernel folders).

Done in K1a/K1b (see `Plans.md` rows for evidence): kernel core, schemas and
configs, seeded empty-kit `SYSTEM_STATE.json`, fail-closed baseline gate,
`instantiate.py` runs `wiki_state.py rebuild` last, LF pinned for generated
state, kernel MCP server with QMD collection names read from
`00-system/configuration/qmd-collections-v1.1.0.json`.

## 4. Exact next work

### K1c — capture tests into the kit, CI runs everything

1. Copy from mozare-wiki `main` (`630a998`), same relative paths:
   - `scripts/capture/tests/test_capture.py`, `test_fixtures.py`, `test_mcp_hook.py`
   - `scripts/capture/fixtures/` (whole folder, incl. `make_fixtures.py`)
   These are generic test code and synthetic fixtures. If you cannot read the
   private repo, ask the owner for these files; do not rewrite them from memory.
2. `test_mcp_hook.py` uses the tool name `wiki_get_capture_media` and sets
   `mcp.ROOT` / `wc.CAPTURES_ROOT` to a temp dir; confirm it passes against the
   kit's `scripts/wiki_mcp_server.py` and `scripts/capture/wiki_capture.py`.
3. `.github/workflows/validate.yml`: keep `check_against_baseline.py`; add
   `pip install -r requirements-governance.txt`, then
   `python scripts/wiki_validate.py --repo . --format json`,
   `python scripts/wiki_state.py --repo . check`,
   `python scripts/wiki_evidence.py --repo . check`, and
   `python -m pytest tests scripts/tests scripts/capture/tests -q`.
4. Acceptance: `git status --porcelain` empty after the test run (tests must
   not write into the repo); CI green on the exact pushed head.
5. No SYSTEM_DESIGN §6 row is needed for test files: the §6 coverage test
   checks top-level `scripts/*.py` only.

### K1d — docs, skill, agents

1. `.claude/skills/wiki-intake/SKILL.md`: adopt mozare-wiki's rewritten
   procedure (gate first; `wiki_state.py --repo . rebuild`;
   `sync_intake_registers.py --accept-corpus-change` dry run then `--apply`;
   `retrieval/build_index.py`; the three gates; the "register a held
   `pending-registration` item" section with `repair_truncated_filenames.py`).
   Keep it generic: no instance counts, no instance ids.
2. Add `.claude/agents/corpus-reader.md` and `.claude/agents/evidence-auditor.md`
   (copy from mozare-wiki, strip instance specifics).
3. `AGENTS.md` and `CLAUDE.md`: governance gates are `wiki_validate.py
   --format json` then `wiki_state.py --repo . check`; MCP is read-only by
   default; proposals go to `_proposals/records/` via the capture profile; add
   the role contract — OWNER, RESEARCH_SYNTHESIS_AGENT, REPOSITORY_OPERATOR,
   INDEPENDENT_REVIEWER, RETRIEVAL_CLIENT, CAPTURE_CLIENT; model or vendor
   identity confers no authority.
4. Replace stale descriptions: `proposals.jsonl` as the write path,
   `wiki_exact` (now an unadvertised alias of `wiki_resolve_id`), `wiki_read`
   (alias of `wiki_read_text`) in `AGENTS.md`, `LIFECYCLE.md`,
   `SETUP_GUIDE_WINDOWS.md`, `SYSTEM_DESIGN.md` §4.
5. Acceptance: kit PASS, suite green, and an instantiated copy
   (`python scripts/instantiate.py --name Smoke --prefix sm` in a temp copy)
   passes `validate_repo.py --full` and `wiki_state.py --repo . check`.
6. Flip `K1c` / `K1d` to `cc:done` in `Plans.md` with the commit hash, and
   refresh PR #7's title/body (it still says "plan + S1, S2, S3").

## 5. H0 — the owner's decision (do not decide it for them)

`proposal.schema.json` currently accepts any non-empty `kind`. Choose:

- **A.** Maintenance kinds (8): `relation-edge`, `claim-amendment`,
  `object-note`, `intake-registration`, `tier-change`, `record-correction`,
  `link-repair`, `retirement-request`.
- **B.** Content kinds (8): `object-create`, `object-update`,
  `relation-create`, `relation-amend`, `claim-create`, `claim-amend`,
  `lineage-link`, `research-question`.
- **C.** Both (16) as one fixed list — recommended by the previous session,
  because existing queued proposals keep a valid kind. `capture-promotion`
  (used by `wiki_propose_from_capture`) must be in whatever list is chosen.

Record the decision in `07-genesis/handoffs/`; W1 turns it into an enum.

## 6. Rules that apply (from `CLAUDE.md` / `AGENTS.md`)

- `_originals/` is immutable. Never `git add -A`; stage named files.
- Once per clone: `git config core.hooksPath .githooks` (pre-commit refuses
  new validator errors). Never add lines to `.githooks/known-baseline-errors.txt`
  to make a commit pass.
- `[tdd:required]` rungs: paste RED (named failures), then GREEN.
- A rung is done only with its acceptance output pasted; `.maws/` is
  continuity, not proof.
- Work on the branch; no force-push.

## 7. Gotchas that cost time

- Windows with `core.autocrlf=true`: byte-compared generated files must be
  LF-pinned in `.gitattributes` (done for the kernel registers).
- Heredocs passed through Git Bash can mangle `\b` and `\n` inside Python
  source; write multi-line patches with an editor tool or a script file.
- The full suite can take 10+ minutes on a loaded machine (normally ~1.5);
  that is load, not a hang.
- Kernel scripts need `jsonschema` (`requirements-governance.txt`).
- `evidence_audit.py` / `report_holdings.py` still read the legacy
  `_proposals/proposals.jsonl` (finding F8) — expected until W1.

## 8. Instance-side items (mozare-wiki, owner's lane)

- Owner: keep or remove 10 test captures written on 2026-09-05 into
  `01-inbox/captures/` by an old test (the fixed tests can no longer do this).
- Owner: intake thread M01–M04 (held items, 6 `.html` originals, 12
  capture-derived records, 2 filenames) — tracked in mozare-wiki `.maws/`.
- Agent, small: port the kit's config-driven `qmd_collections()` into
  mozare-wiki's `scripts/wiki_mcp_server.py` (finding F9).
- M1: `qmd embed` until `qmd status` shows `Pending: 0` (282 docs on 2026-09-23).

## 9. Next exact operation

```bash
git fetch origin && git switch system/2026-09-20--next-version-plan && git pull --ff-only
git config core.hooksPath .githooks
python -m pip install -r requirements.txt -r requirements-governance.txt pytest
python -m pytest tests scripts/tests -q
```

Expect 213 passed, 2 xfailed. Then start K1c step 1.
