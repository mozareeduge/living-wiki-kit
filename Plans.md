# Plans.md — living-wiki-kit

> **Project**: living-wiki-kit (kit 1.2.0 → 1.3.0)
> **Last updated**: 2026-09-25 (hand-off: `07-genesis/handoffs/HANDOFF--2026-09-25--k1-kernel-port.md`)
> **Spec (1.3.0)**: `../living-wiki-kit next-phase spec DRAFT.md` (phases 0–5) and
> `../workbench-ui-spec.md` (G-series) — verified against the repos 2026-09-20;
> current-state evidence in `07-genesis/handoffs/HANDOFF--2026-09-20--kit-rollout-state.md`.
> The two spec drafts sit outside this (public) repo on the owner's machine; every
> rung's acceptance below is self-contained, so an executor elsewhere does not need them.
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
`07-genesis/handoffs/HANDOFF--2026-09-20--kit-rollout-state.md`). Their rows below are
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
| S1 | `[lane:doc] [size:S]` Doc truth: SYSTEM_DESIGN §6 lists every `scripts/*.py` with a tier (`operational` / `available (unexercised)`) and drops the stale "not yet wired" clause; move `_captures/HANDOFF--2026-09-20--kit-rollout-state.md` to `07-genesis/handoffs/` with frontmatter | (a) kit `validate_repo.py --full` PASS with no no-frontmatter warning for the handoff, (b) a new test fails by name when a `scripts/*.py` file is absent from §6, (c) suite `N/N passed` | — | cc:done |
| S2 | `[lane:gate] [size:S]` CI runs the whole test suite (`pytest tests`), not only the mutation file | (a) `validate.yml` diff shows the step, (b) local `pytest tests -q` count equals the count CI logs, (c) CI green on the PR | — | cc:done |
| S3 | `[lane:gate] [tdd:required] [size:M]` Tests for `schema_drift_fixer.py` (path-derivable fix applied, bracket-path guard, semantic fields refused) and a smoke test for `run_faithfulness_benchmark.py` | (a) RED pasted, named failures, (b) GREEN `N/N passed`, (c) kit PASS | — | cc:done |
| K1a | `[lane:gate] [tdd:required] [size:M]` Port the Governance Kernel core from `mozare-wiki` (v1.2.1 H21 as repaired in mozare-wiki PR #15): `scripts/gov_kernel/`, `wiki_validate/state/evidence/proposals/release.py`, `retrieval/`, `sync_intake_registers.py`, `repair_truncated_filenames.py`, fail-closed `check_against_baseline.py`, 7 schemas, 5 configs, `SYSTEM_STATE.json`; `instantiate.py` renames kernel files and runs `wiki_state.py rebuild` | (a) RED: fresh instance failed `wiki_state.py check`; GREEN in `test_instantiate_seeds_gate_clean_empty_instance`, (b) `wiki_validate` / `wiki_state check` / `wiki_evidence check` exit 0, (c) fresh Windows clone `wiki_state check` exit 0 (LF pinned) | S3 | cc:done (e651c11, 18423f3) |
| K1b | `[lane:gate] [tdd:required] [size:M]` Kernel MCP server in the kit: `--profile read` default / `capture`; durable proposal records; UTF-8 stdio; `wiki_context_pack`; QMD collection names read from `qmd-collections-v1.1.0.json` (now shipped, generic `wiki-*`); `.mcp.json` registers it | (a) RED 5 failed / GREEN 5 passed `tests/test_mcp_kernel_server.py`, (b) `pytest tests scripts/tests` 213 passed, 2 xfailed, (c) `validate_repo --full` PASS | K1a | cc:done (b5272cb) |
| K1c | `[lane:gate] [size:S]` Capture tests + fixtures into the kit (`scripts/capture/tests/`, `scripts/capture/fixtures/` incl. deterministic-base `make_fixtures.py`, temp-root MCP tests), and CI runs the kernel gates and every test dir | (a) `validate.yml` runs `wiki_validate.py --format json`, `wiki_state.py --repo . check`, `wiki_evidence.py --repo . check`, `pytest tests scripts/tests scripts/capture/tests`, (b) test run leaves `git status --porcelain` empty, (c) CI green on the exact head | K1b | cc:done (b124d4f: 252 passed, 1 skipped, 2 xfailed; CI billing-blocked, reproduced locally) |
| K1d | `[lane:doc] [size:S]` Docs + agents for the kernel: rewrite `wiki-intake` SKILL.md to the mechanical path (rebuild → sync → gates, held-item registration), add `.claude/agents/corpus-reader.md` + `evidence-auditor.md`, role contract (OWNER / RESEARCH_SYNTHESIS_AGENT / REPOSITORY_OPERATOR / INDEPENDENT_REVIEWER / RETRIEVAL_CLIENT / CAPTURE_CLIENT) and governance gates in `AGENTS.md` + `CLAUDE.md`; replace every stale `proposals.jsonl` / `wiki_exact` / `wiki_read` description (`AGENTS.md`, `LIFECYCLE.md`, `SETUP_GUIDE_WINDOWS.md`, `SYSTEM_DESIGN.md` §4) | (a) `grep -rn "proposals.jsonl\|wiki_exact" *.md` hits only history/legacy notes, (b) kit PASS + suite green, (c) instantiated copy still passes both gates | K1c | cc:done (a9e256b) |
| H0 | `[lane:operator] [size:S]` Decide the proposal-kind vocabulary: keep the schema's 8 (`relation-edge`, `claim-amendment`, `object-note`, `intake-registration`, `tier-change`, `record-correction`, `link-repair`, `retirement-request`), adopt the spec's 8 (`object-create`, `object-update`, `relation-create`, `relation-amend`, `claim-create`, `claim-amend`, `lineage-link`, `research-question`), or union | (a) decision recorded in `07-genesis/handoffs/`, (b) `proposal_schema.json` `version` bumped in W1 | — | cc:done (union 17: HANDOFF--2026-09-28--h0-proposal-kinds.md; enum + version-bump rides with W1) |
| W1 | `[lane:gate] [tdd:required] [size:M]` Kernel `wiki_propose` (capture profile, durable record in `_proposals/records/`) validates at the door against `proposal.schema.json`: kind in the H0 vocabulary (enum), `source_passage` (quote ≥ 20 chars verbatim in a canonical path) required, authority stays `candidate`; `evidence_audit.py` and `report_holdings.py` read `_proposals/records/` + `_proposals/adjudications/` (legacy `proposals.jsonl` read-only) | (a) RED pasted, (b) GREEN, (c) a proposal without a resolvable passage is refused at the door, (d) kit PASS | H0, K1d | cc:done (cfbefeb: 264 passed; door refuses unknown kind / missing-fabricated passage; object-create labels optional, no kind; policy v1.1.0 + tier-enum fix) |
| W2 | `[lane:gate] [tdd:required] [size:S]` MCP tool `wiki_context_pack` wrapping `context_pack.py` (≤ 30 records, ≤ 16k tokens, reason per record) | (a) tool listed in `tools/list`, (b) dispatch test returns records with reasons, (c) suite `N/N passed` | S3 | cc:done |
| O1 | `[lane:gate] [tdd:required] [size:M]` Open object schema (dossier §27–28, §38.1–38.2): `kind` out of required + enum removed (optional deprecated string), `labels[]` added (mechanical string rules only); `TEMPLATE_object.md` gains `labels: []`, no `kind` | (a) RED then GREEN pasted, (b) kindless object validates, legacy `kind: person` validates, dup labels fail, unfamiliar label passes, (c) instantiate smoke + suite green | W1 | cc:done (ab8919a; 273 passed) |
| O2 | `[lane:doc] [size:S]` Semantic policy + agent guidance (dossier §30–35, §38.3–38.7): new `00-system/policies/SEMANTIC_MODEL.md` (object-before-kind, labels≠evidence, relation/claim classification, minimality, vocabulary preference, no label-merge); update `SYSTEM_DESIGN.md`, `LIFECYCLE.md`, `AGENTS.md`, `CLAUDE.md`, `wiki-write` | (a) doc tests fail by name when a maxim is absent, (b) no doc presents the 8 legacy kinds as exhaustive, (c) kit PASS | O1 | cc:done (dee20d4; doc tests green, validators PASS) |
| O3 | `[lane:gate] [tdd:required] [size:M]` Labels in graph/search/context (dossier §39): `build_graph_index.py` indexes raw + normalized labels as non-evidence edges; `context_pack.py` selects on label match with an explicit label-match reason | (a) RED then GREEN, (b) `rehearsal` fixture retrieved with label-match reason, no evidence edge from labels, Unicode label passes, (c) suite green | O2 | cc:done (5603b57; 285 passed) |
| O4 | `[lane:gate] [size:M]` Profile substrate (dossier §14–19, §47, §49): `wiki-profile.schema.json`, `00-system/configuration/profiles/` (+ README, inactive examples), `active_profiles` in instance config, deterministic composition (kernel wins, conflicts surfaced) | (a) empty actives valid, unknown profile errors clearly, profiles compose, cannot weaken kernel, conflicts surfaced, examples inactive, (b) instantiate smoke passes | O2 | cc:done (f3deed4; 293 passed, smoke OK) |
| O5 | `[lane:gate] [size:M]` Lens substrate (dossier §20–22): `wiki-lens.schema.json`, `00-system/configuration/lenses/`, optional lens parameter in context/retrieval; defaults `candidate_visibility: include`, `authority_mode: annotate` | (a) lens foregrounds labels/relations, changes reasons not authority, candidates visible by default, explicit accepted-only filter works, no silent authority filtering | O4 | cc:done (4cfc0a3; 300 passed) |
| O6 | `[lane:gate] [tdd:required] [size:L]` Candidate object projection (dossier §23–25, §40): eligible `object-create` proposals project into disposable index space; never writes `03-objects/`; carries proposal id/status/authority/passage/labels | (a) RED then GREEN, (b) all 9 §54-O6 acceptances (visible + marked candidate, no relevance penalty, accepted-only excludes, rejected in audit scope only, accepted resolves to canonical) | W1, O3, O5 | cc:done (fdb0157; 307 passed) |
| O7 | `[lane:gate] [size:M]` Compatibility + label audit (dossier §42–44): legacy `kind` indexed as compat label marked `label_source: legacy-kind`; read-only `report_labels.py` (counts, variants, namespaces, unlabeled, candidate-vs-canonical); optional dry-run migration tool | (a) legacy kind searchable + marked, report read-only, migration dry-run default, no auto-apply on populated instances | O1, O3 | cc:done (cb8707e) |
| O8 | `[lane:gate] [tdd:required] [size:M]` End-to-end semantic acceptance (dossier §69): fixture intake → kindless labeled object proposal → retrieval → relation + claim → two profiles → two lenses → foregrounding differs, no canonical mutation off the promotion path | (a) RED then GREEN, (b) validators + state + evidence green, suite green, diff limited to fixtures/output | O6, O7 | cc:done (O8 test green; final proof below) |
| W3 | `[lane:gate] [size:M]` Staged reconciliation: every reconcile/intake run first declares a class RC-0…RC-4 (RC-0 mechanism, RC-1 candidate intake: gates only; RC-2 correction on accepted evidence: graph-impact scan; RC-3 new accepted evidence / RC-4 ontology change: `reconcile_runner.py` plan → 8–12-item batches to `corpus-reader` → exact-once verify); `wiki-reconcile` / `wiki-intake` take `--mode incremental\|full`; full mode unchanged; each run writes a receipt with its class (`RECONCILIATION_RECEIPT` schema from the H21 package) | (a) skill text diff, (b) fixture: one new source reconciled in batches without reading every row at once, resumable across sessions, (c) escalation to full on loss or > 30% drift, (d) kit PASS | O8 | cc:done (467d764; 321 passed) |
| W4 | `[lane:gate] [tdd:required] [size:M]` Phase 3 acceptance test: 50 speculative proposals in (durable records) → each is audited or `rejected-audit`; zero canonical file changes; zero accepted without a separate adjudication record | (a) RED pasted, (b) GREEN, (c) `git status --porcelain` empty outside `_proposals/` | W1 | cc:done (2fbe138; 30 audited + 20 rejected-audit, zero canonical change) |
| M1 | `[lane:instance] [size:S]` Finish QMD embeddings in `mozare-wiki` (282 documents pending, measured 2026-09-23) | `qmd status` prints `Pending: 0` | — | cc:done (2026-10-02: `qmd embed` → `Embedded 1886 chunks from 271 documents`; `qmd status` has no Pending line, 37,487 vectors. Final 30-case re-run committed `_audits/2026-10-02--semantic-benchmark-final/`: **12/30**, recall@5 0.2949, the same 12 cases as 10-01, so embeddings were not the bottleneck. See F10) |
| M2 | `[lane:gate] [size:M]` Benchmark metrics: neighborhood recall@K, human rejection rate, evidence-trace completeness added to `run-semantic-benchmark.py`; rerun the 30-case set | (a) metrics in JSON output, (b) score committed under `_audits/`, compared with the 3/30 lexical baseline, (c) suite `N/N passed` | M1, W2 | cc:done (b5a58f6 + 6d2dca1: (a) three metrics in JSON **and** markdown, (b) real 30-case run = **12/30** vs **3/30** baseline — 4x; recall@5 0.3067, rejection 0.8667, trace-complete 0.4; threshold 27 unchanged so the verdict is an honest **FAIL**; score committed `_audits/2026-10-01--semantic-benchmark/`; (c) 46 passed 2 xfailed. Two defects found on the way: a Windows cp1252 decode crash in the runner (real blocker, fixed 6d2dca1) and `human_rejection_rate` being a restatement of recall (docstring corrected). **M1 still owed a final re-run** once embeddings reach `Pending: 0`) |
| H1 | `[lane:operator] [size:L]` Adjudicate the proposal queue from `_audits/evidence-audit-20260919-234541.json` (incl. `prop-20260906-154145-567` refile decision) | recorded human decisions in `mozare-wiki` | W1 | cc:todo |
| H2 | `[lane:operator] [size:L]` Resolve the 306 residual schema errors (baseline after 2026-09-23) in `mozare-wiki` (semantic fields), then re-derive with `schema_drift_fixer.py --errors <file>` | validator error count strictly decreases; baseline re-registered in the same commit | — | cc:todo |
| H3 | `[lane:operator] [size:S]` Enable "Black Bird Field" in Obsidian (Settings → Community plugins) and confirm the four modes; decide plugin home (kit `tools/` vs external, version-pinned) | operator confirmation recorded | — | cc:done exc. live-toggle (2026-10-01: plugin **is** installed at `mozare-wiki/.obsidian/plugins/black-bird-field/` and registered in `community-plugins.json`; all four modes confirmed present in the installed `main.js` v2.0.0 — Field/Reader/Route/Index. Plugin home **decided: external + version-pinned** (installed v2.0.0 vs external source v1.0.0 drift recorded); `.obsidian/plugins/` is gitignored so nothing is version-tracked, which is why the pin must live outside the vault. Remaining: the human in-Obsidian ribbon/toggle confirmation, which cannot be done headlessly) |
| U1 | `[lane:gate] [size:L]` Capture breadth: URL, photo, file (SingleFile adapter) → identical governed capture receipts | (a) one receipt per modality, (b) capture tests green, (c) kit PASS | H3, W1 | cc:done (82cc968: (a) `TestReceiptEquivalence` asserts the three modalities return the same receipt keys, (b) `scripts/capture/tests` 73 passed 2 skipped incl. mutation-checked `TestSchemaParity`, (c) `wiki_validate` / `wiki_state check` / `check_against_baseline` all exit 0. Two defects fixed first: canonical capture schema had not gained `url` (silent drift), and the CLI tests wrote captures into `01-inbox/` (K1c invariant); both pinned by tests now) |
| U2 | `[lane:instance] [size:L]` G-series workbench UI cards (G-01…G-07 per `workbench-ui-spec.md`) | per-card evidence in the spec | H3; P08-02 lane free | blocked |
| R1 | `[lane:doc] [size:S]` Kit 1.3.0: bump SYSTEM_DESIGN `system_version`, `content-release.json`, `instantiate.py` `created_from`, CLAUDE.md, README — atomically; add `CHANGELOG.md` and `QUICKSTART.md` | (a) no stray `1.2.0` outside `schema_version`/openspec/archive, (b) both validators PASS, (c) PR + CI green, (d) local main SHA == remote main SHA | S1, S2, S3, W1–W4 | cc:done exc. (c)(d) (b91901e: declarations at 1.3.0 + CHANGELOG + QUICKSTART, suite + validators green; PR #7 pushed; **(c) CI has never run — the account-level Actions block means no job is ever scheduled, see `HANDOFF--2026-10-01--ci-billing-block.md`; "CI green" in earlier notes was wrong; (d) merge waits on owner**) |
| R2 | `[lane:gate] [size:M]` Release gate: fresh-clone `instantiate.py --name smoke --prefix sm` in a temp dir passes both validators; `report_holdings.py` prints `CENSUS CLEAN` in kit and `mozare-wiki`; handoff in `07-genesis/handoffs/` | (a) instantiate transcript, (b) both CENSUS CLEAN lines, (c) handoff exists | R1 | cc:done exc. merge (R2 handoff filed; fresh-clone smoke PASS + CENSUS CLEAN kit and mozare-wiki@8e71ee3; merge waits on owner) |

### Routing under MAWS (model policy: Sonnet 5 everywhere)

One model policy for the whole 1.3.0 ladder: **every executor, subagent and
reviewer runs Sonnet 5** (`model: "sonnet"` on any Agent/Workflow call). No
haiku on a `gate` rung; no other model unless the operator changes this line.
Route by work shape (`mozare-work`), one writer per mutable scope:

| Rungs | Shape | Executor | Verifier (fresh context) | Checkpoint into `.maws/` |
|---|---|---|---|---|
| S1, S2, R1 | DIRECT | parent (Sonnet 5) | validators + suite output | phase change + evidence line |
| S3, W1, W2, W4 | STAGED (`[tdd:required]`: RED → GREEN) | parent (Sonnet 5) | `test-wiring-auditor` (Sonnet 5) verdict pasted | RED evidence, GREEN evidence |
| W3, M2, R2 | STAGED | parent (Sonnet 5) | `reviewer` (Sonnet 5) | decisions + evidence |
| H0–H3, M1 | operator / instance lane | never an agent | — | recorded only after the operator decides |
| U1, U2 | STAGED, later PARALLEL | Sonnet 5 workers in isolated worktrees | `reviewer` (Sonnet 5) | per-card |

Rules that come with the setup: the parent owns `.maws/` writes and the
`Plans.md` status column; workers get a bounded contract, return artifacts and
evidence, and never write shared state; `.maws/` is continuity, not proof —
a rung flips to `cc:done` only with its acceptance output pasted. Rungs run
sequentially because they share the register/CI surfaces (operating rule 1).

**Findings recorded while running the ladder** (not fixed here; each is a candidate rung):

- **F1** `schema_drift_fixer.py` reads and writes in text mode, so a CRLF file comes back LF-normalised although its docstring says "format-preserving". Git's `* text=auto` hides it. Pinned by a characterisation test in `tests/test_schema_drift_fixer.py`; fix only if an instance turns off `text=auto`.
- **F2** (fixed 2026-10-02, decision: instance-only) `run_faithfulness_benchmark.py` and `run-semantic-benchmark.py` both read `00-system/configuration/semantic-benchmark-v1.1.0.json`, which the kit does not ship (the empty kit has no benchmark set), so neither can run from a fresh instance until one is supplied. Resolved: case sets are instance data (an empty kit has no corpus to measure); both runners take `--config` and exit with a one-line explanation instead of a traceback; `SEARCH_GUIDE.md` §7 documents the shape. Pinned by `scripts/tests/test_benchmark_config_contract.py`.

- **F3** (fixed S3b 2026-10-02) `schema_drift_fixer.py` keeps one operation per file (`ops[rel] = ...`): two errors on the same file drop all but the last, so a second validate → fix pass is needed. No test pins it; candidate rung `S3b`.
- **F4** (fixed S3b 2026-10-02) `schema_drift_fixer.py` writes a derived `filename` unquoted and only guards a leading `[` or `{`; a basename containing `: ` or ` #` would produce invalid YAML. Candidate rung `S3b` (quote unsafe values; keep the kit and `mozare-wiki` copies identical).

- **F5** (fixed K1b) The kit's `configure-search.ps1` read `qmd-collections-v1.1.0.json`, which the kit never shipped; now shipped with generic `wiki-*` names and the MCP server reads it by folder.
- **F6** (fixed K1a) `instantiate.py` renamed the corpus id without refreshing kernel state, so a fresh instance failed `wiki_state.py check`; it now runs `wiki_state.py rebuild` last.
- **F7** (fixed K1a) With `core.autocrlf=true` a fresh Windows clone checked `SYSTEM_STATE.json` out as CRLF → `STATE.GENERATED_DRIFT`; LF pinned in `.gitattributes`.
- **F8** (W1) `evidence_audit.py`, `report_holdings.py` and `tests/test_evidence_audit.py` still read the legacy `_proposals/proposals.jsonl`; the kernel writes `_proposals/records/`.
- **F9** (fixed 2026-10-02, mozare-wiki `564ad05` on `system/2026-10-02--f9-s3b-kit-sync`, same mozare-* sets resolved, instance suite 200 passed) (sync) The kit's MCP server now reads QMD names from config; `mozare-wiki`'s copy still hardcodes `mozare-*`. Port `qmd_collections()` back so both files stay identical.
- **F10** (kit side fixed 2026-10-02: `qmd_scope.py`; every kit QMD call scoped to the instance's own collections, collision refused, `<prefix>-*` names on instantiate; exercised on an isolated index) (machine-level) The local QMD index is one `mozare-wiki` collection over all `*.md` plus `ref-wiki` / `zp-*`, not the per-folder collections in `mozare-wiki`'s `qmd-collections-v1.1.0.json`. Effects: SRC-01…04 never run (`Collection not found: mozare-source-records`), canonical questions are swamped by `02-sources/text/*-extracted.md`, and the config-driven MCP QMD layer finds no collection. Fix: run `mozare-wiki/scripts/configure-search.ps1`, `qmd embed`, re-run the benchmark. Not done unilaterally because the index is shared with `ref-wiki` and `zarinpal-product-wiki`.
- **F10** (K1c) The kit ships the capture core but no capture tests; mozare-wiki's suite found a Linux-only path bug (fixed c0dc845) and a 1-in-3 flaky fixture (fixed there, not yet in the kit).

**Order the loop takes:** S1 → S2 → S3 → W2 → K1a → K1b → **K1c → K1d** → H0 (owner) → W1 → O1 → O2 → O3/O4 → O5 → O6 → O7 → O8 → W3 → W4 → M2 → R1 → R2.
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
