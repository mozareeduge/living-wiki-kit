---
id: wiki-handoff-2026-09-29-overall-plan-and-remaining
type: handoff
title: "Overall plan, done, remaining for 1.3.0 (Hermes agent brief)"
branch: system/2026-09-20--next-version-plan
corpus_snapshot: wiki-corpus-empty
status: active
created: 2026-09-29
updated: 2026-09-29
schema_version: 1.0.0
---

# Handoff — living-wiki-kit 1.3.0: overall plan, done, remaining (for a Hermes agent with file access)

Date: 2026-09-29. Author: execution session of 2026-09-28/29 (branch work
in a temp clone; all commits pushed to origin).

## 1. Where things are

- Kit repo (public): `https://github.com/mozareeduge/living-wiki-kit`
- Work branch: `system/2026-09-20--next-version-plan` at
  `6489024c1af0ebe9c7336bf6495fbede96679675` (= origin, tree clean)
- Base: `origin/main` at `02399e7942245748aa1f12d9e8fb890791d994e2`
- Open PR: #7 (draft) branch → main, "needs review + CI + merge"
- Instance repo (private, read-only for you unless the owner says otherwise):
  `https://github.com/mozareeduge/mozare-wiki` (checked 2026-09-29 at
  `8e71ee3`, CENSUS CLEAN, untouched)
- Task truth: `Plans.md`, section "Ladder 1.3.0" (plus closed "Ladder 1.2.0")
- Design docs (owner machine, Downloads folder):
  `LIVING-WIKI-KIT-ADAPTIVE-SEMANTIC-DESIGN-DOSSIER-v1.0-2026-09-28.md`
  (71 sections, the object-kinds decision),
  `living-wiki-kit-session-transcript-2026-09-28.md` (prior session),
  this file.
- In-repo handoff copies: `07-genesis/handoffs/HANDOFF--2026-09-28--h0-proposal-kinds.md`,
  `HANDOFF--2026-09-28--adaptive-semantic-model.md`,
  `HANDOFF--2026-09-29--release-gate-1-3-0.md`.

## 2. The original vision for the new version (what "done" means)

Kit 1.2.0 (released on main) closed the holdings census: no unchecked
number, no undeclared document, no stale register presented as current.
The 1.3.0 vision, set by the owner at the start ("wire, measure, seal"):

1. Parts built earlier (P1 context compiler/graph packer, P2 incremental
   reconcile core, P3 proposal schema + evidence audit, P4/P5 benchmarks)
   become reachable from the agent front door (MCP), CI, and the docs.
2. The Governance Kernel (fail-closed gates, generated state, durable
   proposal/adjudication records) is ported from mozare-wiki v1.2.1 into
   the kit in generic form.
3. The open semantic problem gets decided and built: no mandatory object
   kind; open labels; composable profiles; persona lenses; candidate
   objects visible by default and marked (owner dossier v1.0, §§D01–D30).
4. The kit releases as 1.3.0 with CHANGELOG + QUICKSTART, proven by a
   release gate (fresh-clone smoke + CENSUS CLEAN in kit and instance).

"Done" = PR #7 reviewed, CI green, merged to main (kit 1.3.0 released);
then the instance/operator lane (M1→M2, H1–H3, U1; U2 stays blocked).

## 3. Ladder map and status

Lanes: `gate` = validator/CI-enforced; `doc` = docs only; `operator` =
owner only, never an agent; `instance` = runs against mozare-wiki.

| ID | Rung | Status |
|---|---|---|
| S1 | Doc truth (§6 lists every script) | done |
| S2 | CI runs whole suite | done (code; CI itself billing-blocked, §6) |
| S3 | Tests for schema_drift_fixer + faithfulness benchmark | done |
| W2 | MCP wiki_context_pack | done |
| K1a | Kernel core (state, evidence, fail-closed gate, LF pin) | done |
| K1b | Kernel MCP server (read/capture profiles, config QMD) | done |
| K1c | Capture tests + fixtures; CI runs kernel gates + all test dirs | done (`b124d4f`) |
| K1d | Intake skill, agents, role contract, stale-desc cleanup | done (`a9e256b`) |
| H0 | Proposal-kind vocabulary: UNION 17 (16 + capture-promotion) | decided by owner, done |
| W1 | Proposal door (17-kind enum, passage check, durable audit) | done (`cfbefeb`) |
| O1 | Open object schema (kind optional/deprecated, labels) | done (`ab8919a`) |
| O2 | SEMANTIC_MODEL.md + agent guidance | done (`dee20d4`) |
| O3 | Labels in graph/search/context | done (`5603b57`) |
| O4 | Profile substrate | done (`f3deed4`) |
| O5 | Lens substrate | done (`4cfc0a3`) |
| O6 | Candidate object projection | done (`fdb0157`) |
| O7 | Compat + label audit + dry-run migration | done (`cb8707e`) |
| O8 | End-to-end semantic acceptance | done (`da7e2a5`) |
| W3 | Staged reconciliation (RC-0…RC-4, receipts, escalation) | done (`467d764`) |
| W4 | Phase 3: 50 proposals → 30 audited + 20 rejected, zero canonical change | done (`2fbe138`) |
| R1 | Kit 1.3.0 bump + CHANGELOG + QUICKSTART | code done (`b91901e`); (c)(d) need owner |
| R2 | Release gate (smoke + CENSUS CLEAN both + handoff) | gate done (`6489024`); merge needs owner |
| M1 | QMD embeddings to Pending: 0 in mozare-wiki | OWNER |
| M2 | Benchmark metrics (recall@K, rejection rate, trace completeness) | agent, after M1 |
| H1 | Adjudicate 32 queued proposals in mozare-wiki | OWNER |
| H2 | Resolve ~306 residual schema errors in mozare-wiki | OWNER |
| H3 | Enable Black Bird Field in Obsidian, decide plugin home | OWNER |
| U1 | Capture breadth (URL/photo/file) | agent, after H3 |
| U2 | Workbench UI cards G-01…G-07 | blocked |

## 4. What is done (proof per rung)

- Suite: `pytest tests scripts/tests scripts/capture/tests` → **322 passed,
  1 skipped, 2 xfailed** (last full run 2026-09-29).
- Gates: `wiki_validate.py --format json`, `wiki_state.py check`,
  `wiki_evidence.py check`, `wiki_profiles.py check` → exit 0;
  `validate_repo.py --full` PASS; `check_against_baseline.py` clean;
  `report_holdings.py` → CENSUS CLEAN.
- Fresh-clone smoke (`Smoke/sm`): instantiate rewrote 31 files, both
  validators PASS.
- mozare-wiki @ `8e71ee3`: CENSUS CLEAN, mojibake none, per-intake
  registers fresh 2026-09-28, 1 blocked claim intact; clone was read-only
  and removed afterwards.
- 40 commits branch-vs-main (`git log main..branch`); PR #7 carries
  title/body refreshes at each milestone.

## 5. What remains — owner side (precise)

1. **Pay / raise GitHub spending limit** (Settings → Billing & plans).
   Evidence it is still the blocker (2026-09-29): every Validate-Wiki run
   on the branch fails in 2–4s with "recent account payments have failed
   or your spending limit needs to be increased" — no code runs at all.
2. **Review PR #7** (40 commits, all green locally) and **merge** it.
   That act releases kit 1.3.0 and formally closes R1(c)(d).
3. **M1**: in mozare-wiki, run `qmd embed` until `qmd status` shows
   `Pending: 0` (282 pending measured 2026-09-23).
4. **H1**: adjudicate the 32 queued proposals
   (`_audits/evidence-audit-20260919-234541.json` in mozare-wiki; 30
   kind-valid under the union-17 decision, 2 strays to refile/reject).
5. **H2**: resolve the ~306 residual schema errors, then re-derive with
   `schema_drift_fixer.py --errors <file>`; error count must strictly
   decrease, baseline re-registered in the same commit.
6. **H3**: enable Black Bird Field in Obsidian, confirm four modes, decide
   plugin home (kit `tools/` vs external, version-pinned).

## 6. What remains — agent side (after the owner)

- **M2** (after M1): add neighborhood recall@K, human rejection rate,
  evidence-trace completeness to `run-semantic-benchmark.py`; rerun the
  30-case set; commit score under `_audits/` vs the 3/30 lexical baseline.
- **U1** (after H3 + W1-done): URL/photo/file capture → identical governed
  receipts; one receipt per modality; capture tests green; kit PASS.
- **U2**: blocked (workbench UI spec lane).
- Small port-back (finding F9): kit MCP reads QMD names from config;
  mozare-wiki's copy still hardcodes `mozare-*` — port `qmd_collections()`
  back so both files stay identical.

## 7. Standing rules (from AGENTS.md / CLAUDE.md / ladder)

- One rung at `cc:wip` at a time; `Plans.md` status flips only with pasted
  acceptance evidence. `.maws/` is continuity, never proof.
- `[tdd:required]` = RED pasted, then GREEN. Never weaken a test or a
  validator to make a change pass.
- `_originals/` immutable, always. Never `git add -A`; stage named files.
  `git config core.hooksPath .githooks` once per clone. Never add lines to
  `.githooks/known-baseline-errors.txt` to force a commit through.
- Never force-push. Work on the branch; mozare-wiki is read-only unless
  the owner orders an instance lane explicitly.
- Binding owner decisions (do not relitigate): union-17 proposal kinds;
  object vocabulary stays OPEN (no enum enforcement, no template kind
  rules — W1 was explicitly forbidden and stays forbidden);
  adjudication promotes authority but never gates the pipeline and never
  grants visibility (candidates included by default, relevance and
  authority separate, accepted-only always explicit).
- Superseded: commit `8a49184` ("must carry kind") was retracted by
  `a785d56`. The dossier (§67) governs W1/O-series interpretation.

## 8. Open findings ledger

- F1: `schema_drift_fixer.py` LF-normalises despite "format-preserving"
  docstring (pinned by test; fix only if an instance drops `text=auto`).
- F2: both benchmark runners need `semantic-benchmark-v1.1.0.json`, which
  the empty kit does not ship.
- F3/F4: fixer keeps one op per file; writes unquoted `filename`
  (candidate rung S3b, unclaimed).
- F5–F7: fixed in K1a/K1b. F8: fixed by W1. F10: fixed by K1c.
- F9: open (see §6 small port-back).
- Known wart: `TIER` wording — `tier-change` enum now aligned to
  `reference-shelf`; mechanism/capture versions in generated
  `SYSTEM_STATE.json` intentionally still read 1.2.0 (kernel mechanism
  version, not kit version — do not hand-edit generated state).

## 9. Gotchas that cost time before

- Windows `core.autocrlf=true`: generated files must stay LF-pinned in
  `.gitattributes`.
- Heredocs through Git Bash mangle `\b`/`\n` in Python — write patches
  with file tools, not shell heredocs.
- Full suite ≈ 30s–2min normally; 10+ min on a loaded machine is load,
  not a hang.
- Kernel scripts need `jsonschema` (`requirements-governance.txt`).
- `validate_content_release.py` treats any `id`+`type` .md as curated:
  new config example pages need inbound `[[wikilinks]]` from their
  README (profiles + lenses READMEs already do this).
- mozare-wiki full clone is heavy (timed out twice); `--depth 1`
  suffices for read-only checks.

## 10. Verify right now (exact commands, kit repo, branch head)

```bash
git fetch origin && git switch system/2026-09-20--next-version-plan
git config core.hooksPath .githooks
python -m pip install -r requirements.txt -r requirements-governance.txt pytest
python -m pytest tests scripts/tests scripts/capture/tests -q
python scripts/wiki_validate.py --repo . --format json
python scripts/wiki_state.py --repo . check
python scripts/wiki_evidence.py --repo . check
python scripts/wiki_profiles.py check
python scripts/validate_repo.py --full
python scripts/check_against_baseline.py
python scripts/report_holdings.py
```

Expected: 322 passed / all gates exit 0 / PASS / clean / CENSUS CLEAN.
Then continue the ladder at the lowest-ID `cc:todo` whose Depends are met
(M2 once M1 lands; U1 once H3 lands).
