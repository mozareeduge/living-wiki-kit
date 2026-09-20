# Plans.md — living-wiki-kit

> **Project**: living-wiki-kit (kit 1.2.0 → 1.3.0)
> **Last updated**: 2026-09-20
> **Spec (1.3.0)**: `../living-wiki-kit next-phase spec DRAFT.md` (phases 0–5) and
> `../workbench-ui-spec.md` (G-series) — verified against the repos 2026-09-20;
> current-state evidence in `_captures/HANDOFF--2026-09-20--kit-rollout-state.md`
> **Spec (1.2.0, closed)**: `openspec/specs/holdings-census/spec.md`
> (archived change: `openspec/changes/archive/2026-09-19-corpus-census-truth/`)
> **Continuity**: portable MAWS thread `.maws/` (see "Continuity" below)

---

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

## Ladder 1.2.0 — census truth (closed)

B4 and C3 were operator-gated and ran in `mozare-wiki` (instance commits
`13a0175` B4, `140a043` C3, `6102114` Z2; census merged as `e892fae`;
Z2 CENSUS CLEAN 97/447/544 recorded in
`_captures/HANDOFF--2026-09-20--kit-rollout-state.md`). Their rows below are
updated to match; they were not re-run from this repo.

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
| B4 | `[lane:instance] [size:M]` **operator-gated** Adopt in `mozare-wiki`: copy shipped validator + retier tool + policy, dry-run (expect 447), operator tier decision, `--apply`, set `544`, rewrite the four pages to the three labelled markers, delete `Source artifacts: 94`, handoff | (a) `validate_repo.py --full` PASS with gate active, (b) `grep -l "^status: registered" \| wc -l` == `97`, (c) state prints `97 544 544`, (d) all three markers on four pages, no `Source artifacts: 94` anywhere, (e) diff of `_originals/` + manifest empty, (f) handoff exists | B3 | cc:done (in `mozare-wiki`) |
| C1 | `[lane:gate] [tdd:required] [size:S]` Mojibake guard extended from manifest rows to `aliases`/`original_path`/`filename`/`title` of every source record | (a) RED pasted, one named failure per offending field, (b) `N/N passed`, (c) kit PASS, (d) review note states the exact hit count in a throwaway `mozare-wiki` clone, clone deleted | A1 | cc:done |
| C2 | `[lane:gate] [tdd:required] [size:M]` `check_register_policies`: every `00-system/registers/*.md` declares `refresh_policy` ∈ {per-intake, per-release, static} + ISO `updated`; per-intake fails when older than `CORPUS_STATE.updated`; `archive/` exempt; string comparison only | (a) RED pasted, ≥6 named failures (one per rule), (b) `N/N passed`, (c) subprocess test: stale per-intake → nonzero, both dates quoted, (d) kit PASS, (e) test-wiring-auditor verdict pasted | A1 | cc:done |
| C3 | `[lane:instance] [size:M]` **operator-gated** Apply in `mozare-wiki`: table of 13 registers (current `updated`, proposed policy, tag/refresh/archive), stop for the decision, then tag / refresh / move to `registers/archive/` with a one-line reason each | (a) `grep -L refresh_policy` returns nothing, (b) `validate_repo.py --full` PASS, (c) every archived register has a first-line reason and is in the handoff, (d) a `tag`-only register's diff is exactly one added line | C2, B4 | cc:done (in `mozare-wiki`) |
| D1 | `[lane:doc] [size:S]` Tier the SYSTEM_DESIGN §6 script table: every row `operational` or `available (unexercised)`; reword README/§1 bullets that oversell the export layer; add a test that fails on an untagged row | (a) suite `N/N passed` incl. table-completeness test, (b) negative check pasted (deleting a status cell fails by name), (c) kit PASS, (d) exactly five `available (unexercised)` rows | A1 | cc:done |
| E1 | `[lane:gate] [size:M]` `scripts/report_holdings.py`: read-only 7-section audit (counts, contradictions, proposals by status, claims by permission, register staleness, mojibake, verdict), writes only to `_audits/runtime/` | (a) empty kit prints 7 sections + `CENSUS CLEAN`, exit 0, (b) `git status --porcelain` byte-identical before/after, (c) `--json` parses, prints `0 0`, (d) throwaway `mozare-wiki` clone reproduces `97`/`544`/`32` proposals (`20` new)/`24` claims (`1` blocked), clone deleted, (e) suite `N/N passed` | A4 | cc:done |
| Z1 | `[lane:doc] [size:S]` Archive the change: fold `specs/holdings-census/spec.md` into `openspec/specs/`, move to `openspec/changes/archive/2026-09-XX-corpus-census-truth/`, check every box | (a) change dir gone, (b) standing spec exists, (c) no unchecked `- [ ]` remains, (d) PASS | all above cc:done | cc:done |
| Z2 | `[lane:doc] [size:S]` Horizon check: `report_holdings.py` in both repos must print `CENSUS CLEAN`; handoff in each recording the output | (a) both print `CENSUS CLEAN`, (b) two handoffs exist, (c) on `CENSUS DRIFT` the ladder is **not** finished — open follow-up rows instead of declaring completion | Z1 | cc:done |

---

## Ladder 1.3.0 — wire, measure, seal

Goal: the parts built in P1–P5 (context compiler, incremental reconcile,
candidate layer, benchmark) become reachable from the agent front door, CI and
the docs, then the kit is released as 1.3.0. Everything below is `cc:todo`
except where noted. Same operating rules as the 1.2.0 ladder apply; rungs
tagged `[lane:operator]` are never executed by an agent.

| ID | Task | Acceptance (all pasted from commands actually run) | Depends | Status |
|---|---|---|---|---|
| S1 | `[lane:doc] [size:S]` Doc truth: SYSTEM_DESIGN §6 lists every `scripts/*.py` with a tier (`operational` / `available (unexercised)`) and drops the stale "not yet wired" clause; move `_captures/HANDOFF--2026-09-20--kit-rollout-state.md` to `07-genesis/handoffs/` with frontmatter | (a) kit `validate_repo.py --full` PASS with no no-frontmatter warning for the handoff, (b) a new test fails by name when a `scripts/*.py` file is absent from §6, (c) suite `N/N passed` | — | cc:todo |
| S2 | `[lane:gate] [size:S]` CI runs the whole test suite (`pytest tests`), not only the mutation file | (a) `validate.yml` diff shows the step, (b) local `pytest tests -q` count equals the count CI logs, (c) CI green on the PR | — | cc:todo |
| S3 | `[lane:gate] [tdd:required] [size:M]` Tests for `schema_drift_fixer.py` (path-derivable fix applied, bracket-path guard, semantic fields refused) and a smoke test for `run_faithfulness_benchmark.py` | (a) RED pasted, named failures, (b) GREEN `N/N passed`, (c) kit PASS | — | cc:todo |
| H0 | `[lane:operator] [size:S]` Decide the proposal-kind vocabulary: keep the schema's 8 (`relation-edge`, `claim-amendment`, `object-note`, `intake-registration`, `tier-change`, `record-correction`, `link-repair`, `retirement-request`), adopt the spec's 8 (`object-create`, `object-update`, `relation-create`, `relation-amend`, `claim-create`, `claim-amend`, `lineage-link`, `research-question`), or union | (a) decision recorded in `07-genesis/handoffs/`, (b) `proposal_schema.json` `version` bumped in W1 | — | cc:todo |
| W1 | `[lane:gate] [tdd:required] [size:M]` `wiki_propose` validates against `proposal_schema.json`: unknown kind refused, `source_passage` (quote ≥ 20 chars verbatim in a canonical path) required, authority stays `candidate` | (a) RED pasted, (b) GREEN, (c) a proposal without a resolvable passage is refused at the door, (d) kit PASS | H0, S3 | cc:todo |
| W2 | `[lane:gate] [tdd:required] [size:S]` MCP tool `wiki_context_pack` wrapping `context_pack.py` (≤ 30 records, ≤ 16k tokens, reason per record) | (a) tool listed in `tools/list`, (b) dispatch test returns records with reasons, (c) suite `N/N passed` | S3 | cc:todo |
| W3 | `[lane:gate] [size:M]` `wiki-reconcile` and `wiki-intake` skills take `--mode incremental\|full` and call `reconcile_runner.py` (plan → verify); full mode is the existing procedure, untouched | (a) skill text diff, (b) fixture: one new source reconciled without reading every manifest row, (c) escalation to full fires on loss or > 30% drift, (d) kit PASS | W2 | cc:todo |
| W4 | `[lane:gate] [tdd:required] [size:M]` Phase 3 acceptance test: 50 speculative proposals in → each is audited or `rejected-audit`; zero canonical file changes; zero accepted without a recorded human decision | (a) RED pasted, (b) GREEN, (c) `git status --porcelain` empty outside `_proposals/` | W1 | cc:todo |
| M1 | `[lane:instance] [size:S]` Finish QMD embeddings in `mozare-wiki` (1,062 pending) | `qmd status` prints `Pending: 0` | — | cc:todo |
| M2 | `[lane:gate] [size:M]` Benchmark metrics: neighborhood recall@K, human rejection rate, evidence-trace completeness added to `run-semantic-benchmark.py`; rerun the 30-case set | (a) metrics in JSON output, (b) score committed under `_audits/`, compared with the 3/30 lexical baseline, (c) suite `N/N passed` | M1, W2 | cc:todo |
| H1 | `[lane:operator] [size:L]` Adjudicate the proposal queue from `_audits/evidence-audit-20260919-234541.json` (incl. `prop-20260906-154145-567` refile decision) | recorded human decisions in `mozare-wiki` | W1 | cc:todo |
| H2 | `[lane:operator] [size:L]` Resolve the 318 residual schema errors in `mozare-wiki` (semantic fields), then re-derive with `schema_drift_fixer.py --errors <file>` | validator error count strictly decreases; baseline re-registered in the same commit | — | cc:todo |
| H3 | `[lane:operator] [size:S]` Enable "Black Bird Field" in Obsidian (Settings → Community plugins) and confirm the four modes; decide plugin home (kit `tools/` vs external, version-pinned) | operator confirmation recorded | — | cc:todo |
| U1 | `[lane:gate] [size:L]` Capture breadth: URL, photo, file (SingleFile adapter) → identical governed capture receipts | (a) one receipt per modality, (b) capture tests green, (c) kit PASS | H3, W1 | cc:todo |
| U2 | `[lane:instance] [size:L]` G-series workbench UI cards (G-01…G-07 per `workbench-ui-spec.md`) | per-card evidence in the spec | H3; P08-02 lane free | blocked |
| R1 | `[lane:doc] [size:S]` Kit 1.3.0: bump SYSTEM_DESIGN `system_version`, `content-release.json`, `instantiate.py` `created_from`, CLAUDE.md, README — atomically; add `CHANGELOG.md` and `QUICKSTART.md` | (a) no stray `1.2.0` outside `schema_version`/openspec/archive, (b) both validators PASS, (c) PR + CI green, (d) local main SHA == remote main SHA | S1, S2, S3, W1–W4 | cc:todo |
| R2 | `[lane:gate] [size:M]` Release gate: fresh-clone `instantiate.py --name smoke --prefix sm` in a temp dir passes both validators; `report_holdings.py` prints `CENSUS CLEAN` in kit and `mozare-wiki`; handoff in `07-genesis/handoffs/` | (a) instantiate transcript, (b) both CENSUS CLEAN lines, (c) handoff exists | R1 | cc:todo |

**Order the loop takes:** S1 → S2 → S3 → W2 → W1 (after H0) → W3 → W4 → M2 → R1 → R2.
`H*`, `M1`, `U*` are outside the agent loop: they wait for the operator or
another lane and never block the S/W/R chain except where `Depends` says so.

---

## Continuity (MAWS)

Work state for this ladder lives in the portable `.maws/` thread (shared by
Claude Code, Hermes and Codex). `Plans.md` stays the task truth; `.maws/`
records *where we are* (phase, decisions, evidence, next operation). Resume
with `python ~/.maws/runtime/maws.py --format human status`. `.maws/` is
continuity, not completion proof — a rung is done only when its acceptance
evidence has been pasted.

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
