# MAWS active work thread

- **Thread:** `20260920-174600-living-wiki-kit-1.3.0` — Living Wiki Kit 1.3.0
- **Status:** `active`
- **Shape:** `long-horizon`
- **Phase:** `execute`
- **Last host:** `claude`
- **Handoff target:** `any host (owner's choice)`
- **Updated:** `2026-09-25T11:00:00Z`

## Objective

Take living-wiki-kit from 1.2.0 to 1.3.0: wire the built P1-P5 parts (context pack, incremental reconcile, candidate layer, benchmark) into the agent front door, CI and docs, then release. Task truth: Plans.md 'Ladder 1.3.0'.

## Current state

K1a + K1b done (e651c11, 18423f3, b5272cb): governance kernel core and kernel MCP server ported from mozare-wiki; 213 tests pass; validate_repo, wiki_validate, wiki_state check, wiki_evidence check all green. Hand-off for another host: 07-genesis/handoffs/HANDOFF--2026-09-25--k1-kernel-port.md.

## Decisions

- Owner 2026-09-25: finish K1 (K1c, K1d) first; then the owner decides H0 (proposal kinds); then W1 -> W3 -> W4 -> M2 -> R1 -> R2.
- W3 becomes staged reconciliation (classes RC-0..RC-4, batched reconcile_runner, receipts).

## Blockers

- W1/W4 wait on H0 (owner).

## Next operations

- K1c: capture tests + fixtures into the kit; CI runs kernel gates and all test dirs.
- K1d: intake skill, 2 agents, role contract, stale proposals.jsonl/wiki_exact docs.

## Artifacts

- none

## Evidence references

- test:pass — pytest tests scripts/tests — K1a/K1b: 213 passed, 2 xfailed; RED first for instantiate state drift and 5 kernel-server tests
- validator:pass — validate_repo --full PASS; wiki_validate/wiki_state check/wiki_evidence check exit 0; fresh Windows clone wiki_state check exit 0 after LF pin
- test:pass — pytest tests -q — S1: 129/129 (126 + 3 new section6 tests); RED was 2 named failures (9 scripts missing from s6; stale 'not yet wired')
- validator:pass — validate_repo.py --full; validate_content_release.py; check_against_baseline.py — S1: PASS/PASS/OK; 0 warnings for the moved handoff
- test:pass — pytest tests -q — S3: 172/172; 43 new tests; mutation RED demo 8/8 caught (after adding the pinned dir->kind test)
- ci:pass — PR #7 validate run 35533135212 — S2: ubuntu-latest py3.12 '172 passed' == local 172
- review:pass — test-wiring-auditor (Sonnet 5) on 71807d9,4ddb8c7,77f43b4 — PASS-WITH-GAPS: CI collects all 6 test files, no vacuous S1 coverage test, no CLAUDE.md conflicts; 3 weak assertions tightened; F3/F4 recorded
- test:pass — pytest tests -q — W2: 185/185; RED = 13 named failures before implementation; 7/7 mutations caught; live stdio JSON-RPC tools/list shows wiki_context_pack

## Graph

- Provider: `none`
- Graph: `none`
- Run state: `none`
- Last route: `unknown`

## Continuity rule

This document is coordination memory, not completion proof. Re-check project authority, current files, tests, external facts, and evidence before relying on stale claims after a handoff.
