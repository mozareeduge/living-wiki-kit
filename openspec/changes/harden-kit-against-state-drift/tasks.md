# Tasks: harden-kit-against-state-drift

## 1. Validator gate (TDD)

- [ ] 1.1 RED: add `tests/test_validator_mutations.py` tests for the
      entry-page gate (fresh passes; stale snapshot caught; wrong source
      count caught; layer-count drift caught; missing-snapshot tolerated;
      empty-kit birth state passes) — run, watch fail (no check_entry_pages
      in kit validator yet)
- [ ] 1.2 GREEN: port `check_entry_pages()` into `scripts/validate_repo.py`
      (extracted function, called from `validate()` after the
      manifest/state check; entry pages = HOME.md, README.md,
      SYSTEM_DESIGN.md); run suite → green
- [ ] 1.3 Verify full gate: validate_repo --full, validate_content_release,
      check_against_baseline all PASS on the kit tree (empty state)

## 2. Templates & skills (contract alignment)

- [ ] 2.1 Add `filename:` to `00-system/templates/TEMPLATE_source-record.md`
      (field name + one-line description), matching validator requirement
- [ ] 2.2 `.claude/skills/wiki-reconcile/SKILL.md`: replace hardcoded
      "94 artifacts, `mw-corpus-a33b260403015901`" with the read-at-runtime
      instruction (dated verification note 2026-09-16); grep proves no
      `mw-corpus-` remains in any skill
- [ ] 2.3 `.claude/skills/wiki-intake/SKILL.md` step 10: add entry-page
      refresh instruction (same change as manifest update; names the gate)

## 3. Docs (pointer-true rule)

- [ ] 3.1 `SYSTEM_DESIGN.md`: §1 gains snapshot anchor (`wiki-corpus-empty`,
      0 sources, live-truth pointer); §6 validate_repo.py row documents the
      entry-page freshness gate
- [ ] 3.2 `INSTANTIATE.md`: new subsection "Keep entry docs pointer-true"
      (rule + gate reference); adjust step 3 wording to point at registers
- [ ] 3.3 `README.md` / `HOME.md`: verify/refresh anchors so the kit tree
      passes its own gate (fix any hardcoded values found)

## 4. Instantiator (structural seeding)

- [ ] 4.1 TDD-lite: extend the smoke check — run instantiate.py in a temp
      copy (`--name "Smoke Wiki" --prefix swk`), assert seeded anchors
      (`swk-corpus-empty`, count 0) and both validators PASS in the temp
      instance
- [ ] 4.2 Implement seeding in `scripts/instantiate.py` (rewrite snapshot
      id and count occurrences in HOME.md/README.md/SYSTEM_DESIGN.md after
      the prefix pass; idempotent)

## 5. Verification & landing

- [ ] 5.1 Full local gate green; mutation suite green (no regressions)
- [ ] 5.2 e2e drift-rejection demo on throwaway branch (bump register only
      → hook blocks; with refresh → passes; revert)
- [ ] 5.3 PR → CI green → merge to main; bump kit version to 1.1.0 in
      SYSTEM_DESIGN frontmatter (system_version) + note in README
- [ ] 5.4 Post-merge: verify remote main SHA; local ff; repo-state sync
      (skill update + memory)
