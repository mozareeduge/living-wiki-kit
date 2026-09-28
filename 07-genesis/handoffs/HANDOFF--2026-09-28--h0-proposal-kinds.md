---
id: wiki-handoff-2026-09-28-h0-proposal-kinds
type: handoff
title: "H0 decision: union proposal-kind vocabulary (16 + capture-promotion)"
branch: system/2026-09-20--next-version-plan
corpus_snapshot: wiki-corpus-empty
status: active
created: 2026-09-28
updated: 2026-09-28
schema_version: 1.0.0
---

# H0 — proposal-kind vocabulary decision (owner, 2026-09-28)

## Decision

**Union: all 16 kinds plus `capture-promotion` (17 total)** as the fixed
vocabulary. W1 turns this list into the `kind` enum in
`00-system/schemas/proposal.schema.json` and specifies required fields for
the 9 kinds missing from `00-system/policies/proposal_schema.json`, then
bumps that file's `version`.

## The 17 kinds

Maintenance (already specified in `proposal_schema.json` v1.0.0):
`relation-edge`, `claim-amendment`, `object-note`, `intake-registration`,
`tier-change`, `record-correction`, `link-repair`, `retirement-request`.

Content (from the next-phase spec; W1 specifies their required fields):
`object-create`, `object-update`, `relation-create`, `relation-amend`,
`claim-create`, `claim-amend`, `lineage-link`, `research-question`.

Capture pipeline (written by `wiki_propose_from_capture` today, in neither
list): `capture-promotion`.

## Why union

- The live queue (`_audits/evidence-audit-20260919-234541.json` in
  mozare-wiki: 32 proposals) uses `object-note` ×27, `relation-edge` ×2,
  `claim-amendment` ×1 — all maintenance. Maintenance-only would still work,
  but the content kinds are the write-path vocabulary for the workbench UI
  (G-series); dropping them now just re-opens the decision later.
- Content-only would invalidate 30 of 32 queued kinds on the eve of human
  adjudication (H1). Rejected.
- Known cost, accepted: near-synonym pairs (`claim-amend` /
  `claim-amendment`, `relation-create` / `relation-edge`, `object-update` /
  `object-note` + `record-correction`). W1 must give each kind a one-line
  `_desc` stating when to use it versus its twin.
- Two queued proposals use kinds in no list (`reconciliation-proposal`,
  `reconciliation-amendment`). They stay kind-invalid; H1 refiles or rejects
  them. Not a reason to expand the list further.
- Noted for W1: `tier-change`'s `to_tier_enum` in `proposal_schema.json`
  lists `held`, but the holdings vocabulary is `registered` /
  `pending-registration` / `reference-shelf`. W1 aligns the enum.

## Next

W1 is unblocked. Do not start it on a second branch; ladder rule is one
`cc:wip` rung at a time.
