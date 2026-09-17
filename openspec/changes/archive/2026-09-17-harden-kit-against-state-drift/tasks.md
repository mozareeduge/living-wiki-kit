# Tasks: harden-kit-against-state-drift

## 1. Make the TDD command real; build the isolated gate

- [x] 1.1 Add a deterministic `__main__` runner to
      `tests/test_validator_mutations.py`; run
      `python tests/test_validator_mutations.py` and confirm the four existing
      tests are reported, not silently skipped.
- [x] 1.2 RED: add table-driven tests for `check_entry_pages(root, state,
      errors)`: all four fresh pages pass; each page fails for a stale snapshot
      and wrong labelled source count; an unrelated `0` does not satisfy the
      zero-count marker; missing/empty `state.id` skips only the snapshot
      check; empty directories count as zero; every one of multiple layer
      declarations is checked; singular/plural and fenced-code behavior match
      the spec; missing pages and errors are self-explanatory. Run the direct
      command, observe named failures and a nonzero exit.
- [x] 1.3 GREEN: implement the extracted helper in
      `scripts/validate_repo.py` without wiring it into `validate()` yet; run
      the direct suite and observe all helper tests pass.

## 2. Establish the contract surfaces before enabling enforcement

- [x] 2.1 Add the exact `Current corpus snapshot:` and
      `Registered source artifacts:` markers for `wiki-corpus-empty` / `0`,
      plus live-register pointers, to README.md, HOME.md, SYSTEM_DESIGN.md §1,
      and CLAUDE.md Current state.
- [x] 2.2 Update SYSTEM_DESIGN.md §6 to document the four-page freshness and
      layer-count gate. Update INSTANTIATE.md to define the same markers,
      refresh duty, capture-only exception, and manual adoption order for an
      existing instance; remove the invitation to rewrite ungoverned “corpus
      facts.”
- [x] 2.3 Add `filename:` and its one-line description to
      `00-system/templates/TEMPLATE_source-record.md`; extend the mutation
      suite with a filled-template schema case that has no `filename` error.
- [x] 2.4 Replace wiki-reconcile's hardcoded baseline with a run-start read of
      CORPUS_STATE.json that stops on missing/malformed id or count. Keep only
      a value-free verification date; prove no `mw-corpus-` value remains in
      any `.claude/skills/*/SKILL.md`.
- [x] 2.5 Update wiki-intake step 10 to refresh the four markers in the same
      change whenever registered corpus state changes. State explicitly that
      an unregistered governed capture does not trigger the refresh.

## 3. RED→GREEN the instantiator

- [x] 3.1 RED: extend the same plain-Python suite with a temporary-copy smoke
      test. Run `instantiate.py --name "Smoke Wiki" --prefix swk`; assert
      CORPUS_STATE.json has id `swk-corpus-empty` and count `0`, all four pages
      have exact markers and no `wiki-corpus-empty` marker, and both validators
      pass. Rerun with the same arguments and assert no content diff. Set up a
      populated-state case and assert refusal occurs before any file changes.
- [x] 3.2 GREEN: update `scripts/instantiate.py` to validate fresh-state
      preconditions, set the empty register id, include/render all four entry
      pages from the register, preserve same-instance idempotence, and refuse
      populated or different-instance reseeding. Run the direct suite green.

## 4. Enable the shared gate

- [x] 4.1 RED: add an integration test proving normal `validate()` calls
      `check_entry_pages()` once with the loaded state, plus a subprocess case
      showing a stale marker makes `validate_repo.py` exit nonzero. Run and
      observe the named failures.
- [x] 4.2 GREEN: call `check_entry_pages(ROOT, state, errors)` from
      `validate()` after state/manifest loading and agreement checks. Run the
      mutation suite and verify all tests pass.
- [x] 4.3 Run `python scripts/validate_repo.py --full`,
      `python scripts/validate_content_release.py`, and
      `python scripts/check_against_baseline.py` on the empty kit; require clean
      exits and add no entry-drift line to
      `.githooks/known-baseline-errors.txt`.

## 5. End-to-end governance and landing

- [x] 5.1 In a disposable local clone, set `core.hooksPath=.githooks`, change
      only CORPUS_STATE.json's id, stage it, and attempt a commit. Assert the
      hook blocks specifically on missing four-page snapshot markers. Refresh
      those markers, retry, and assert the same baseline gate used by CI
      passes. Do not push the clone; retain decisive output in the review
      record, then remove it.
- [x] 5.2 Review `git diff --check`, the bounded file list, and the full diff.
      Confirm `_originals/` is untouched, no runtime dependency was added, no
      baseline error was added, and no unrelated generated or memory file is
      staged.
- [x] 5.3 If releasing as 1.1.0, update SYSTEM_DESIGN.md `system_version`,
      `00-system/configuration/content-release.json` `system_version`,
      `scripts/instantiate.py` `created_from`, and the README release note in
      the same change; rerun both validators after the bump.
- [x] 5.4 Open a reviewable PR from the existing `system/` branch. Require CI
      green; do not use `--no-verify`, force-push, or a baseline exception.
      Merge, verify remote main SHA, and fast-forward the local checkout.
- [x] 5.5 Record the consequential-work handoff required by SYSTEM_DESIGN.md,
      including changed files, decisions, exact validation output, unresolved
      risks, negative constraints, and the next operation.
