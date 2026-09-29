# Plans.md — living-wiki-kit

> **Project**: living-wiki-kit (kit 1.2.0)
> **Last updated**: 2026-09-29
> **Active ladder**: K — cloud workload (below). Source: `REMAINED` and
> "Kit human-readiness gaps" in `_captures/HANDOFF--2026-09-20--kit-rollout-state.md`,
> re-verified against this tree on 2026-09-29.
> **Handoff**: `07-genesis/handoffs/HANDOFF--2026-09-29--cloud-workload.md`

---

# Active ladder K — cloud workload (kit 1.2.x hardening)

Every K rung can be finished inside a Claude Code cloud session holding only
`living-wiki-kit`: no `qmd`, no Obsidian, no Windows machine, no populated
instance. Same operating rules as the census ladder below (one `cc:wip`,
RED-then-GREEN for `[tdd:required]`, never extend
`.githooks/known-baseline-errors.txt`, paste the decisive command output).

Baseline measured 2026-09-29 on `02399e7`:
`validate_repo.py --full` PASS · `validate_content_release.py` PASS ·
`check_against_baseline.py` `OK: validators clean.` ·
`tests/test_validator_mutations.py` `102/102 passed` ·
`python -m pytest -q` `126 passed` (only after `pip install pytest`; not in
`requirements.txt`, not run by CI) · throwaway-clone
`instantiate.py --name "Smoke Wiki" --prefix smk` → validate PASS +
`report_holdings.py` `CENSUS CLEAN`.

| ID | Task | Acceptance (all must be pasted, from commands actually run) | Depends | Status |
|---|---|---|---|---|
| K1 | `[lane:gate] [size:S]` CI runs the whole suite. The 24 pytest tests added in P1–P3 (`test_context_compiler`, `test_reconcile_runner`, `test_evidence_audit`) are never run by `.github/workflows/`, and `pytest` is in no requirements file. Add `requirements-dev.txt` (`-r requirements.txt` + `pytest`), install it in CI, add a `python -m pytest -q` step; keep the existing two steps | (a) fresh venv: `pip install -r requirements-dev.txt && python -m pytest -q` → `126 passed`, (b) CI run on the PR shows the pytest step green, (c) `python -m unittest discover -s tests` no longer the documented entry point anywhere (or documented as mutations-only), (d) both validators PASS | — | cc:todo |
| K2 | `[lane:doc] [tdd:required] [size:M]` SYSTEM_DESIGN §6 completeness. D1's test only checks rows that exist, so 9 scripts slipped in untabled: `build_graph_index.py`, `context_pack.py`, `evidence_audit.py`, `reconcile_runner.py`, `report_holdings.py`, `retier_holdings.py`, `run_faithfulness_benchmark.py`, `schema_drift_fixer.py`, `setup-after-clone.ps1` (and `instantiate.py` is named only in prose). Add a test: every top-level `scripts/*.py`/`*.ps1` appears in the table. Then add the rows and fix stale cells: `validate_repo.py` still says the census helper is "not yet wired into `validate()`" (A4 wired it); `wiki_mcp_server.py` lacks `wiki_exact` | (a) RED pasted, one named failure per missing script, (b) GREEN `N/N passed`, (c) negative check: deleting one row fails by name, (d) no status re-tier here: any row whose honest status changed (e.g. `run-semantic-benchmark.py`, exercised in mozare-wiki `9a2dd09`) is listed for **K9**, not edited, so the D1 "exactly five unexercised" assertion is untouched, (e) kit PASS | — | cc:todo |
| K3 | `[lane:gate] [tdd:required] [size:S]` `schema_drift_fixer.py` emits patch IDs as `mw-patch-<run_id>` (line 174), but `instantiate.py`'s `MW_ID` rewrites only `mw-(src-|cap-|corpus-)`, so an instance with prefix `smk` still writes `mw-patch-…`. Extend the rewrite (or derive the prefix at runtime) and cover it in the instantiator smoke test | (a) RED: throwaway-clone instantiate with `--prefix smk`, `grep -n "mw-patch" scripts/schema_drift_fixer.py` hits, (b) GREEN: no hit, `smk-patch` present, (c) idempotent rerun byte-identical, (d) suite `N/N passed`, (e) kit PASS | — | cc:todo |
| K4 | `[lane:gate] [tdd:required] [size:S]` Tests for the two untested scripts: `schema_drift_fixer.py` (path-derivable fix proposed, semantic field left alone, output only via PATCH_MANIFEST, `_originals/` untouched) and `wiki_mcp_server.py` `wiki_exact` + BM25 fallback when `qmd` is absent (the cloud case) | (a) RED pasted per new test against a deliberately broken copy, (b) GREEN `N/N passed`, (c) no test needs `qmd`, network, or a model | K1 | cc:todo |
| K5 | `[lane:gate] [size:S]` Fresh-instantiate smoke in CI (handoff gap "never ran on a clean machine"): clone → `instantiate.py --name "CI Wiki" --prefix ciw` → `validate_repo.py --full` PASS → `report_holdings.py` `CENSUS CLEAN` → second run byte-identical. Linux runner; add a `windows-latest` matrix leg only if `setup-after-clone.ps1`/`verify-install.ps1` can run without `qmd` (record which) | (a) CI log with all four results, (b) the job fails when a validator error is injected (negative run pasted), (c) Windows leg: pasted result or pasted reason it is deferred | K1, K3 | cc:todo |
| K6 | `[lane:doc] [size:S]` `instantiate.py`'s closing hint says `git add -A && git commit …` (line 161), contradicting the house rule "never `git add -A`". Replace with explicit staging (`git add .` scoped by `.gitignore` is still bulk — prefer `git status` then named paths, matching `INSTANTIATE.md`) and align `INSTANTIATE.md` | (a) `grep -rn "add -A" scripts/ INSTANTIATE.md README.md` empty, (b) suite passes, (c) kit PASS | — | cc:todo |
| K7 | `[lane:doc] [size:S]` `CHANGELOG.md`: 1.0.0 → 1.1.0 (entry-page freshness gate, `openspec/changes/archive/2026-09-17-*`) → 1.2.0 (census gate, `…/2026-09-19-*`) → Unreleased (P1–P5, schema_drift_fixer, K rungs). Sourced from `git log` and the openspec archive only | (a) every version heading matches a real commit/tag range (pasted `git log --oneline` ranges), (b) no claim absent from those sources, (c) kit PASS (entry-page gate unaffected) | — | cc:todo |
| K8 | `[lane:doc] [size:M]` `QUICKSTART.md` — the one-page first hour: prerequisites (git, python ≥3.x, `pip install -r requirements.txt`; `qmd`/Obsidian optional), instantiate, validate, first intake via `/wiki-intake`, where the rules live. Fold in the instance runbooks now only in the rollout handoff: QMD embed recipe (`qmd embed --max-docs-per-batch 2 --max-batch-mb 1` until `Pending: 0`) → `SEARCH_GUIDE.md`; drift-fixer and benchmark usage → SYSTEM_DESIGN §6 rows. Link QUICKSTART from README start-here | (a) every command in QUICKSTART run verbatim in a throwaway clone (except `qmd`/Obsidian lines, marked optional), output pasted, (b) wikilinks/links resolve (kit PASS), (c) README links it | K6 | cc:todo |
| K9 | `[lane:doc] [size:S]` **operator-gated** Re-tier §6 statuses whose truth changed (from K2's list) and update D1's "exactly N unexercised" assertion in the same change; decide whether 1.2.x docs/CI work ships as 1.2.1 or folds into a 1.3.0 with P1–P5 (B3's atomic bump procedure). `pyproject.toml` decision rides here | (a) operator decision quoted, (b) if bumped: no stray old version outside `schema_version`/openspec, (c) both validators PASS, (d) baseline `OK: validators clean.` | K2, K7 | cc:todo |

### Not finishable in this cloud session (carried, not dropped)

From the rollout handoff `REMAINED` list, re-checked 2026-09-29:

| # | Item | Why not here | Where it gets done |
|---|---|---|---|
| R1 | Finish QMD embeddings (1,062 chunks pending) | Instance corpus + `qmd` + local embedding model; `qmd` absent in this container | owner machine, `mozare-wiki` |
| R2 | Real semantic benchmark (beat 3/30 lexical-only) | needs R1 | owner machine, `mozare-wiki` |
| R3 | 318 residual schema errors | content adjudication (reading sources) in the instance; not auto-fixable by design | `mozare-wiki`, human-led; could run in cloud only if `mozare-wiki` is attached to the session |
| R4 | Proposal-queue adjudication (incl. `prop-20260906-154145-567`) | owner's judgment; queue is inert by design | owner |
| R5 | Enable black-bird-field plugin in Obsidian, check four modes | Obsidian GUI | owner machine |
| R6 | G-series workbench UI cards | blocked on P08-02 lane (session `20260919_140225_2b37f5`) | after lane frees |

---

# Completed ladder — corpus-census-truth (kit 1.1.0 → 1.2.0)

> **Spec** (archived): `openspec/changes/archive/2026-09-19-corpus-census-truth/`

## North Star

**No unchecked number, no undeclared document, no stale register presented as
current.**

The archive already refuses to let a source be altered. It does not yet refuse
to let a *count* be wrong. `mozare-wiki` holds 544 artifacts, registers 97, and
447 source records claim `status: registered` while absent from the register
that every document calls live truth — and `validate_repo.py --full` prints
`PASS`. This ladder closes that, and stops the 1.1.0 entry-page gate from
stamping validator authority on a minority figure.

Measured 2026-09-17. Full evidence in `proposal.md`.

---

## Operating rules for this ladder

1. **One rung at `cc:wip` at a time.** `MATERIALS_INDEX.jsonl` and
   `CORPUS_STATE.json` are monolithic with a snapshot hash; concurrent branches
   conflict (`AGENTS.md`, "Shared-register serialization").
2. **Read `EXECUTOR_BRIEF.md` before each rung.** It carries the prohibitions,
   the four decisive commands, the stop conditions, and the model routing.
3. **`[tdd:required]` means RED pasted, then GREEN pasted.** A test that passes
   before the implementation is a broken test.
4. **Never add a line to `.githooks/known-baseline-errors.txt`.** A new check
   firing on existing content ends the rung with a reported count, not a
   tolerated error.
5. **B4 and C3 are operator-gated.** They touch a populated archive and carry
   corpus-semantics decisions. A lighter model does the read-only half, pastes
   the numbers, and hands back.

---

## Ladder

| ID | Task | Acceptance (all must be pasted, from commands actually run) | Depends | Status |
|---|---|---|---|---|
| A1 | `[lane:gate] [size:S]` Holdings tier vocabulary: `00-system/policies/HOLDINGS_POLICY.json` (3 tiers, `default_tier_for_unregistered`, empty `family_tier_overrides`) + a `## Holdings tier` section in `CONTROLLED_VOCABULARY.md` + `load_holdings_policy(root)` in the validator, unwired | (a) suite `N/N passed` with 4 new names, (b) tier list prints `['pending-registration','reference-shelf','registered']`, (c) **test asserts JSON tier set equals vocabulary tier set**, (d) `validate_repo.py --full` PASS | — | cc:done |
| A2 | `[lane:gate] [tdd:required] [size:M]` `check_holdings_census(root, state, errors)`: the biconditional (`status: registered` iff manifest row), `_originals/` tier coverage, tier legality, count agreement, absent-key skip. Not wired | (a) RED pasted, every new test a named FAIL, (b) GREEN `N/N passed`, (c) `grep` shows definition and **no** call in `validate()`, (d) a test asserts every error names a path *and* the disagreeing register | A1 | cc:done |
| A3 | `[lane:gate] [size:S]` `CORPUS_STATE.json` gains `held_artifact_count: 0` + `holdings_by_tier`; SYSTEM_DESIGN pins the vocabulary (`source_material_count` = manifest rows, never redefined) | (a) `0 0` printed for held + tier sum, (b) `validate_repo.py --full` PASS, (c) suite `N/N passed`, (d) the distinguishing sentence present | A2 | cc:done |
| A4 | `[lane:gate] [tdd:required] [size:M]` Wire the census gate into `validate()` after `check_entry_pages` — hook and CI both enforce it | (a) 2 RED tests pasted (in-process call-once + subprocess undeclared file), (b) `N/N passed`, (c) all four brief commands green, (d) baseline file diff empty, (e) **test-wiring-auditor verdict pasted** | A3 | cc:done |
| A5 | `[lane:gate] [size:M]` `scripts/retier_holdings.py`: dry-run default, `--apply` refuses a dirty tree, refuses on manifest/state disagreement before any write, tier from `family_tier_overrides` else default | (a) `0 records to retier` + `git status` unchanged, (b) fixture flips exactly 1 record then PASS, (c) dirty-tree `--apply` exits nonzero saying `dirty`, (d) broken-base fixture: tree hash identical after refusal, (e) suite `N/N passed` | A4 | cc:done |
| B1 | `[lane:gate] [tdd:required] [size:S]` `check_entry_pages` learns the exact marker `Artifacts held: <held_artifact_count>`; skipped when the key is absent | (a) RED pasted, one named failure per entry page, (b) `N/N passed`, (c) test proves the error quotes the value observed in **raw** page text, (d) local PASS only after B2 — state that, do not work around it | A4 | cc:done |
| B2 | `[lane:gate] [size:M]` Add `Artifacts held: 0` to the four entry pages; `instantiate.py` seeds all three markers; `INSTANTIATE.md` §3.5 documents the third | (a) `grep -c` prints 1 on each of the four pages, (b) suite `N/N passed` incl. extended instantiator smoke, (c) `validate_repo.py --full` PASS, (d) idempotent rerun still byte-identical | B1 | cc:done |
| B3 | `[lane:doc] [size:S]` Kit 1.2.0: bump SYSTEM_DESIGN `system_version`, `content-release.json`, `instantiate.py` `created_from`, CLAUDE.md bullet, README note — atomically; no `schema_version` touched | (a) no stray `1.1.0` outside `schema_version`/openspec, (b) both validators PASS, (c) baseline `OK: validators clean.`, (d) PR + CI green + local main SHA == remote main SHA (both pasted) | B2 | cc:done |
| B4 | `[lane:instance] [size:M]` **operator-gated** Adopt in `mozare-wiki`: copy shipped validator + retier tool + policy, dry-run (expect 447), operator tier decision, `--apply`, set `544`, rewrite the four pages to the three labelled markers, delete `Source artifacts: 94`, handoff | (a) `validate_repo.py --full` PASS with gate active, (b) `grep -l "^status: registered" \| wc -l` == `97`, (c) state prints `97 544 544`, (d) all three markers on four pages, no `Source artifacts: 94` anywhere, (e) diff of `_originals/` + manifest empty, (f) handoff exists | B3 | cc:done (instance-side: mozare-wiki `e892fae` per `_captures/HANDOFF--2026-09-20--kit-rollout-state.md`; not re-verifiable from the kit) |
| C1 | `[lane:gate] [tdd:required] [size:S]` Mojibake guard extended from manifest rows to `aliases`/`original_path`/`filename`/`title` of every source record | (a) RED pasted, one named failure per offending field, (b) `N/N passed`, (c) kit PASS, (d) review note states the exact hit count in a throwaway `mozare-wiki` clone, clone deleted | A1 | cc:done |
| C2 | `[lane:gate] [tdd:required] [size:M]` `check_register_policies`: every `00-system/registers/*.md` declares `refresh_policy` ∈ {per-intake, per-release, static} + ISO `updated`; per-intake fails when older than `CORPUS_STATE.updated`; `archive/` exempt; string comparison only | (a) RED pasted, ≥6 named failures (one per rule), (b) `N/N passed`, (c) subprocess test: stale per-intake → nonzero, both dates quoted, (d) kit PASS, (e) test-wiring-auditor verdict pasted | A1 | cc:done |
| C3 | `[lane:instance] [size:M]` **operator-gated** Apply in `mozare-wiki`: table of 13 registers (current `updated`, proposed policy, tag/refresh/archive), stop for the decision, then tag / refresh / move to `registers/archive/` with a one-line reason each | (a) `grep -L refresh_policy` returns nothing, (b) `validate_repo.py --full` PASS, (c) every archived register has a first-line reason and is in the handoff, (d) a `tag`-only register's diff is exactly one added line | C2, B4 | cc:done (instance-side: mozare-wiki `e892fae` per `_captures/HANDOFF--2026-09-20--kit-rollout-state.md`; not re-verifiable from the kit) |
| D1 | `[lane:doc] [size:S]` Tier the SYSTEM_DESIGN §6 script table: every row `operational` or `available (unexercised)`; reword README/§1 bullets that oversell the export layer; add a test that fails on an untagged row | (a) suite `N/N passed` incl. table-completeness test, (b) negative check pasted (deleting a status cell fails by name), (c) kit PASS, (d) exactly five `available (unexercised)` rows | A1 | cc:done |
| E1 | `[lane:gate] [size:M]` `scripts/report_holdings.py`: read-only 7-section audit (counts, contradictions, proposals by status, claims by permission, register staleness, mojibake, verdict), writes only to `_audits/runtime/` | (a) empty kit prints 7 sections + `CENSUS CLEAN`, exit 0, (b) `git status --porcelain` byte-identical before/after, (c) `--json` parses, prints `0 0`, (d) throwaway `mozare-wiki` clone reproduces `97`/`544`/`32` proposals (`20` new)/`24` claims (`1` blocked), clone deleted, (e) suite `N/N passed` | A4 | cc:done |
| Z1 | `[lane:doc] [size:S]` Archive the change: fold `specs/holdings-census/spec.md` into `openspec/specs/`, move to `openspec/changes/archive/2026-09-XX-corpus-census-truth/`, check every box | (a) change dir gone, (b) standing spec exists, (c) no unchecked `- [ ]` remains, (d) PASS | all above cc:done | cc:done |
| Z2 | `[lane:doc] [size:S]` Horizon check: `report_holdings.py` in both repos must print `CENSUS CLEAN`; handoff in each recording the output | (a) both print `CENSUS CLEAN`, (b) two handoffs exist, (c) on `CENSUS DRIFT` the ladder is **not** finished — open follow-up rows instead of declaring completion | Z1 | cc:done |

---

## Loop contract

`/harness-loop` dynamic mode owns the long tail. Per wake-up:

1. `/harness-sync` — pick the lowest-ID `cc:todo` whose `Depends` are all
   `cc:done` or `pm:approved`;
2. run exactly that rung under `/harness-work <ID>`;
3. `ScheduleWakeup` — `noop: false` if something landed, `noop: true` if
   blocked, `reason` naming the rung.

Cadence **1200–1800s**. Nothing here changes faster than a human reading a
diff, so minute-scale polling is waste. Stop the loop when every row is
`cc:done`/`pm:approved`, or when two consecutive wake-ups end in the same
`advisor-request.v1` — a repeated block is an operator question, not a retry.

---

## Out of scope for this ladder

- Adjudicating the 20 `new` proposals in `mozare-wiki`. That backlog is the
  archive's real rate limiter and it is human judgment work; no rung touches
  it.
- Registering any of the 447 held artifacts. This ladder makes their status
  *declared*, not *decided*.
- Building the export layer, `08-outputs/`, or the semantic benchmark. D1
  relabels them honestly; it does not implement them.
- Any content, claim, relation or object edit in any instance.

---

## Status marker legend

| Marker | Meaning |
|--------|---------|
| `pm:requested` | Operator requested work |
| `cc:todo` | Not started |
| `cc:wip` | In progress (one at a time) |
| `cc:done` | Complete, every criterion pasted; awaiting operator confirmation |
| `pm:approved` | Operator confirmed |
| `cc:withdrawn` | Terminal; superseded or absorbed elsewhere |
| `blocked` | Blocked; the reason sits next to the row |
