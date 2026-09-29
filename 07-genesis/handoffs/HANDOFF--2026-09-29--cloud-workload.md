---
id: wiki-handoff-2026-09-29-cloud-workload
type: handoff
title: "Dossier closure + cloud follow-ups: ladder O9-O12, Q1-Q6, decisions D-a..D-e"
branch: claude/remaining-tasks-workload-w9wft4
commit: 2df7db2
corpus_snapshot: wiki-corpus-empty
status: active
created: 2026-09-29
updated: 2026-09-29
schema_version: 1.0.0
---

# Dossier closure + cloud follow-ups: ladder O9-O12, Q1-Q6, decisions D-a..D-e

## Task and intended result

Shape all remaining work into one sequenced workload a Claude Code cloud
session can finish (this repo only; no `qmd`, Obsidian, Windows, or
instance). Inputs: (1) the adaptive semantic design dossier v1.0
(2026-09-28), audited section by section against this tree, and (2) a
triage of the tree. No code or content was changed.

## Files changed

- `Plans.md` (PR #7's version, merged in): findings F11-F18; the section
  "Ladder 1.3.x — dossier closure + cloud follow-ups" with O9-O12, Q1-Q6
  (Q5 withdrawn), owner decisions D-a..D-e.
- `07-genesis/handoffs/HANDOFF--2026-09-29--cloud-workload.md` (this file).

## Files read

The dossier (uploaded copy); `Plans.md`; handoffs `…2026-09-28--adaptive-semantic-model`,
`…2026-09-29--overall-plan-and-remaining`, `…2026-09-20--kit-rollout-state`;
`00-system/schemas/{object-record,wiki-lens,wiki-profile}.schema.json`;
`00-system/templates/TEMPLATE_object.md`; `00-system/policies/SEMANTIC_MODEL.md`;
`00-system/configuration/{profiles,lenses}/`; `scripts/{context_pack,wiki_profiles,
build_graph_index,wiki_mcp_server,evidence_audit,report_holdings,instantiate,
schema_drift_fixer}.py`; `tests/test_o1..o8_*.py`; SYSTEM_DESIGN, LIFECYCLE,
AGENTS, `wiki-write` skill.

## Dossier audit — what is already done (verified, not assumed)

- §27/§38.1 schema: `kind` optional + deprecated, no enum; `labels` with
  length, uniqueness, control-character guard; `additionalProperties: true`.
- §28/§38.2 template: `labels: []`, no `kind`.
- §38.3-38.7 docs: SEMANTIC_MODEL.md carries all six §52 phrases; the
  SYSTEM_DESIGN core idea, `03-objects/` open, LIFECYCLE stage 4, AGENTS,
  `wiki-write` all updated (pinned by `test_o2_semantic_docs.py`).
- §39 labels raw + normalized, non-evidence (O3 tests); §40/§23-25 candidate
  projection, default-visible, no penalty, accepted-only explicit, rejected
  in audit scope, accepted → canonical (O6 tests); §43 `label_source:
  legacy-kind`; §44 read-only `report_labels.py`; §42.3 dry-run
  `migrate_object_kinds.py`; profiles compose, weakening rejected, conflicts
  surfaced (O4); MCP `wiki_context_pack` exposes `lens` and `accepted_only`.

## Dossier audit — gaps (become rungs)

- F14 → O9: lens `foreground_relations` / `foreground_sections` are inert.
- F15 → O10: active profiles never reach retrieval.
- F16 → O11: no executable proof of the six-context claim (§69.13, D30).
- F17 → O12: "Ref Wiki" schema titles; §29 term distinction missing;
  stale `evidence_audit.py` docstring.
- F18 → D-b: "may tighten" has no mechanism.

## Decisions accepted

- The dossier's gaps continue the O series (O9-O12) and run before the Q
  hygiene rungs.
- Q5 (F8) withdrawn: W1 already moved both readers to `_proposals/records/`;
  my earlier triage misread the legacy fallback as the live path.
- Binding owner decisions are not reopened (open object vocabulary,
  candidates visible by default, relevance ≠ authority, 17 proposal kinds).

## Decisions not made (owner)

D-a domain/collaboration/compliance example profiles; D-b compliance
tightening semantics; D-c `LABEL_ALIASES.json`; D-d `instantiate.py
--profile`; D-e `mozare-wiki` legacy-`kind` path (low-churn compat vs.
migration).

## Validation commands and outcomes

Merged tree on this branch, 2026-09-29:

```
python scripts/check_against_baseline.py                  -> OK: validators clean; validator execution healthy.
python scripts/validate_repo.py --full                    -> PASS
python scripts/wiki_validate.py --repo . --format json    -> exit 0
python scripts/wiki_state.py --repo . check               -> exit 0
python scripts/wiki_evidence.py --repo . check            -> exit 0
python scripts/wiki_profiles.py check                     -> exit 0
python -m pytest tests scripts/tests scripts/capture/tests -q -> 323 passed, 2 xfailed
```

CI: every run on PR #7 and PR #8 ends within seconds before any step
(GitHub billing block, per PR #7). The cause is at the account level, not in
the diff.

## Negative constraints

- No O/Q rung before PR #7 merges; one `cc:wip` at a time.
- O9/O10 never filter, never change authority, and leave the no-lens,
  no-profile pack byte-identical.
- No object-kind enum, template kind rule, or label registry, anywhere.
- No `_originals/`, register, or `mozare-wiki` writes; D-e `--apply` never
  runs before the owner decides.
- No lines added to `.githooks/known-baseline-errors.txt`.

## Next exact operation

Owner: clear the billing block, merge PR #7, then PR #8, and answer D-a..D-e
when convenient (none blocks O9). Agent: set O9 to `cc:wip`, write
`test_lens_foregrounds_relation_language` against a fixture relation typed
`supports` under `lens-scholar`, and paste the RED.

## Rollback

Revert this branch's merge commit (`git revert -m 1`) and the plan commits;
they touch only `Plans.md` and this handoff.
