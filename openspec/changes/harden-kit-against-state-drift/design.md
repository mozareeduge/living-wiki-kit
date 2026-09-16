# Design: harden-kit-against-state-drift

## Context

living-wiki-kit 1.0.0 is the template; ref-wiki (and mozare-wiki,
zarinpal-product-wiki) are production instances. The 2026-09-16 ref-wiki
incident proved a kit-level gap class: entry-level prose hardcodes register
values and drifts silently. The fix was designed and e2e-proven in ref-wiki
(PR #6, merge 63c3636; earlier resolution PRs #3/#4/#5, CLAUDE.md via PR #7).
This change ports the validated design into the kit so every future
instantiation inherits it at birth — per the standing note in the operator
skill (living-wiki-ops): "port ref-wiki hardenings into the kit (validated in
production)".

## Goals / Non-Goals

- Goals: enforce entry/register consistency deterministically at commit time
  (hook + CI); remove every hardcoded instance-state baseline from shipped
  skills; align the source-record template with the validator contract;
  make the instantiator seed gate-clean pages; keep kit empty-state PASS.
- Non-Goals: changing the record grammar, authority hierarchy, intake
  procedure mechanics, capture core, or anything ref-wiki already fixed at
  the instance level beyond the named gaps. No LFS strategy change.

## Decisions

### D1. Port the proven gate verbatim (adapted, not re-designed)
`check_entry_pages()` ships exactly as validated in ref-wiki: presence of
snapshot id + source count per entry page (HOME.md, README.md,
SYSTEM_DESIGN.md), plus layer-count contradiction detection against the
record directories, plus the missing-snapshot-id tolerance. One adaptation:
the function is extracted (as in ref-wiki) so `tests/` can exercise it
against tmp dirs without a populated repo.

### D2. Empty kit must pass at birth (kit-specific constraint)
ref-wiki never runs in empty state; the kit does. `wiki-corpus-empty` and
count 0 must appear in the seeded entry pages, and the layer-count check
must not fire on empty directories (0 == 0). The instantiator seeds the
anchor + count; the kit's own pages carry them natively. This constraint is
covered by a dedicated test.

### D3. Baselines live in registers, not skills
The reconcile skill's baseline line becomes an instruction ("read
CORPUS_STATE.json at run start") with a dated verification note, mirroring
the ref-wiki fix. No skill may hardcode `mw-corpus-*` or any count.

### D4. Template/validator reconciliation is minimal
Add only the `filename:` line to TEMPLATE_source-record.md — no schema
re-design. The validator is the contract; the template meets it.

### D5. TDD in kit's plain-python test mode
Kit tests run as `python tests/test_validator_mutations.py` (no pytest in
the venv; ref-wiki precedent). New tests follow RED→GREEN: write test,
watch it fail against the un-gated validator, then port the gate, watch it
pass. All-or-nothing per commit; mutation suite must end 100% green.

### D6. Verification recipe (inherited from ref-wiki work)
- per-behavior: `python tests/test_validator_mutations.py`
- full gate: `python scripts/validate_repo.py --full` +
  `python scripts/validate_content_release.py` +
  `python scripts/check_against_baseline.py`
- e2e: on a throwaway branch, bump CORPUS_STATE.json without entry-page
  refresh → expect hook BLOCK; refresh pages → expect PASS; revert.
- instantiate smoke: run instantiate.py in a temp copy → both validators
  PASS in the temp instance before first intake.

## Risks / Trade-offs

- Gate strictness: any legit doc restructure of entry pages must keep the
  anchor + count. Accepted: the error message is self-explanatory and the
  fix is one line.
- The empty-kit count anchor ("0") is a bit odd in prose ("0 sources");
  accepted: honesty over polish, and INSTANTIATE.md explains it.
- Regex layer-count check can false-positive on prose mentioning e.g.
  "3 objects" in a examples context. Accepted: rare, error is
  self-explanatory; ref-wiki ran the gate live without false positives.

## Migration Plan

1. Land validator + tests + template + skill fixes (one branch, TDD).
2. Update docs (INSTANTIATE.md, SYSTEM_DESIGN, README/HOME anchors).
3. instantiate.py seeding change lands in the same branch (smoke-tested).
4. Merge via PR with CI green. Existing instances are untouched; they
   already carry the gate (ref-wiki) or can adopt by pulling kit updates
   manually (out of scope here).

## Open Questions

- None blocking. (Kit-version bump to 1.1.0 decided at merge time.)
