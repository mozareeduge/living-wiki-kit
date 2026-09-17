# Design: harden-kit-against-state-drift

## Context

living-wiki-kit 1.0.0 is an empty, validated template. ref-wiki,
mozare-wiki, and zarinpal-product-wiki are instances. The 2026-09-16
ref-wiki incident showed that a register can be internally correct while the
documents an operator reads first remain six days stale. ref-wiki PR #6
proved that a deterministic entry-page check can block that drift; PRs
#3–#5 and #7 repaired the surrounding documents and workflow. The kit needs
the whole contract, not only the copied function.

## Adversarial review answers

### 1. Coverage of the five root causes

The original four artifacts did not cover them end to end. They checked only
HOME.md, README.md, and SYSTEM_DESIGN.md even though CLAUDE.md contains a
hardcoded `0`-source Current state block and was stale in the incident. They
also left governed capture behavior implicit. The revised plan covers all
four state-bearing entry documents, keeps capture-only changes outside the
registered-corpus trigger, and retains the reconcile, intake, template, and
instantiation repairs.

### 2. Testability of the enforcement requirement

The original requirement was not precise enough for TDD. Searching for the
bare string `0` can pass because of an unrelated version or date, and a single
`re.search` can miss a later contradictory layer count. The revised spec
defines exact labelled markers, checks every visible layer-count occurrence,
defines missing-state-id behavior, and states the required error contents.
Task rows distinguish helper behavior from integration into `validate()`.

### 3. Empty-kit birth and plain-Python tests

Empty record directories are not a conflict: recursive Markdown counts are
zero. Bare-number matching is a conflict because `0` appears easily in
unrelated prose; labelled matching removes it. A second hidden conflict is
that the kit's current mutation-test file defines tests but has no direct-run
test harness, so `python tests/test_validator_mutations.py` exits successfully
without running them. The first task repairs the runner before the RED step.

### 4. Ordering and instantiation smoke coverage

The original order attempted a full validator pass before making the kit's
entry pages compliant. It also checked only output anchors, not the register
id that should supply them. The revised tracer bullet is: make the test runner
real; RED/GREEN the isolated check; update the four entry surfaces; RED/GREEN
the instantiator in a temporary copy; RED/GREEN the `validate()` integration;
then run the complete gates. The smoke test asserts the register id, exact
markers in all four pages, both validators, same-argument idempotence, and
refusal on a populated state.

### 5. Existing-instance migration

An existing instance that pulls the validator before adding its own markers
will fail validation. An instance with custom wording may also fail even when
its prose is semantically current. Automatic migration is acceptably out of
scope only if this fail-closed behavior and the manual adoption order are
documented: read the instance's registers, add its four markers in the same
change as the validator, run both validators, and do not rerun
`instantiate.py`.

### 6. Governance compatibility

The active `system/2026-09-16--harden-kit-spec` branch follows the allowed
prefix. The implementation plan forbids force-push, `--no-verify`, and adding
entry-drift errors to the accepted-error baseline. It uses the same
`check_against_baseline.py` path for hook and CI, requires a reviewable diff,
and keeps `_originals/` untouched. A 1.1.0 release bump must update every
version declaration together; changing only SYSTEM_DESIGN.md would break the
content validator. Consequential implementation work still ends with the
repository-required handoff.

## Goals / Non-goals

Goals are to make entry/register drift a deterministic commit failure, remove
the instance-specific skill baseline, align the source-record template with
the validator, keep a fresh empty instance green, and give existing instances
an explicit adoption path.

This change does not alter record grammar, authority levels, `_originals/`
immutability, capture-core semantics, intake mechanics beyond the refresh
duty, content-release thresholds, or LFS strategy. It does not bulk-migrate
existing instances.

## Decisions

### D1. Use one labelled entry contract on four pages

Each of README.md, HOME.md, SYSTEM_DESIGN.md, and CLAUDE.md contains these
literal label/value forms, optionally preceded by ordinary Markdown list
syntax:

```text
Current corpus snapshot: `<state.id>`
Registered source artifacts: <state.source_material_count>
```

Each page also points to `00-system/registers/CORPUS_STATE.json` and
`MATERIALS_INDEX.jsonl` as live truth. Labels prevent a version number, date,
or unrelated zero from satisfying the check.

### D2. Port the proven gate structure, with bounded corrections

`check_entry_pages(root, state, errors)` remains an extracted deterministic
function. It checks the four pages, is called once from `validate()` after the
state and manifest are loaded, and appends rather than raises for content
drift.

If `state.id` is a non-empty value, every page must contain the exact labelled
snapshot marker. If the key is absent or empty, only that marker test is
skipped; source-count and layer-count checks still run. If
`source_material_count` is present, every page must contain its exact labelled
marker, including zero.

For objects, relations, claims, and indexes, the function recursively counts
`*.md` files in 03-objects, 06-relations, 05-claims, and 09-indexes. It checks
every singular or plural visible-prose occurrence such as `1 object` or
`3 objects`, case-insensitively. Fenced and inline code are excluded so
documentation examples do not become corpus claims. Every contradiction is
reported, not only the first match.

Each error names the entry page, the expected register or directory value,
the observed or missing marker, and says to refresh the entry page from the
registers in the same change. This makes the failure actionable without
reading validator source.

### D3. The empty register is the source for instantiation

The kit itself carries `wiki-corpus-empty` and count `0` in all four pages.
On a fresh instantiation, `instantiate.py` sets the register id to
`<prefix>-corpus-empty`, then renders the four markers from the resulting
state. It does not rewrite arbitrary numeric prose.

The operation is idempotent when rerun with the same name and prefix on the
same still-empty instance. It refuses before writing if the manifest is
non-empty, the source count is nonzero, state/manifest disagree, or an
existing INSTANCE.json identifies a different instance. This prevents a
bootstrap tool from reseeding a live corpus.

### D4. Skills read or refresh; they do not remember

wiki-reconcile reads and validates the live source count and snapshot id at
run start. Its dated note records that the behavior was verified, not a
historic count or id. wiki-intake refreshes the markers in all four pages in
the same change whenever it changes the registered corpus state. A governed
capture not yet registered as a source has no such duty.

### D5. Template/validator reconciliation stays minimal

TEMPLATE_source-record.md gains the `filename:` frontmatter field and its
description. Record grammar is otherwise unchanged.

### D6. Tests remain executable as plain Python

`tests/test_validator_mutations.py` gets a deterministic `__main__` runner
that discovers its `test_*` functions, prints per-test results, and exits
nonzero on any failure. Tests use `tempfile`, `pathlib`, `shutil`, and
`subprocess` from the standard library. No pytest dependency is introduced.
RED means that this exact command visibly runs tests and exits nonzero:

```text
python tests/test_validator_mutations.py
```

### D7. Hook and CI share one enforcement path

The pre-commit hook and CI continue to call
`scripts/check_against_baseline.py`; the entry check enters both through
`validate_repo.validate()`. Entry-drift errors are defects and must never be
added to `.githooks/known-baseline-errors.txt` to obtain a pass.

## Verification

- Plain-Python mutation suite: `python tests/test_validator_mutations.py`.
- Repository gates: `python scripts/validate_repo.py --full`,
  `python scripts/validate_content_release.py`, and
  `python scripts/check_against_baseline.py`.
- Instantiation: run the CLI inside a temporary copy; assert register and
  four-page markers; run both validators; rerun with the same arguments and
  assert no content diff; assert a populated-state invocation refuses before
  writing.
- End to end: in a disposable local clone with `core.hooksPath=.githooks`,
  change only the corpus-state id and attempt a commit. The hook must reject
  with an entry-page error. Refresh all four snapshot markers and retry; the
  shared baseline gate must pass. Nothing is pushed, and the disposable clone
  is removed after inspection.

## Risks / Trade-offs

- Existing instances fail closed on adoption until their markers are added.
- Fixed labels constrain entry-page wording. This is deliberate: the values
  remain human-readable while the validator avoids coincidental matches.
- A source replacement with unchanged count is caught only if the workflow
  also changes `state.id`. The implementation should not claim that the
  human-readable id is cryptographically derived; the existing
  `corpus_snapshot_sha256` check remains the integrity mechanism.
- Recursive layer counts treat every Markdown file under the four record
  directories as a record. That matches current layout; a later addition of
  explanatory Markdown there would require an explicit counting rule change.

## Migration plan

1. Make the direct test command execute real tests; RED/GREEN the isolated
   entry check.
2. Add the four kit markers and pointer-true documentation; align skills and
   template.
3. RED/GREEN fresh instantiation, idempotence, and populated-state refusal.
4. Wire the helper into `validate()`, prove hook/CI-path enforcement, and run
   every local gate.
5. Land through a reviewable PR without baseline additions or bypasses; make
   any 1.1.0 version bump atomic; record the required handoff.

Existing instances adopt manually in one change: read their live register
values, add the four markers, take the validator and workflow updates, then
run both validators. They must not run the instantiator again.

## Open question for the owner

Should a later change replace the human-managed snapshot id marker with, or
add, a shortened `corpus_snapshot_sha256` marker? The present change retains
the proven id-plus-count scope; it cannot force an entry refresh after a
same-count manifest change if the intake workflow fails to rotate `state.id`.
