<!-- Folded in from change harden-kit-against-state-drift on
     2026-09-17 (kit 1.1.0, PR #2). -->

# Capability: entry-consistency

### Requirement: Entry pages expose labelled register anchors

Every wiki instantiated from the kit SHALL keep README.md, HOME.md,
SYSTEM_DESIGN.md, and CLAUDE.md consistent with
00-system/registers/CORPUS_STATE.json. Each page SHALL contain these literal
label/value forms, using the current `id` and `source_material_count`:

```text
Current corpus snapshot: `<id>`
Registered source artifacts: <count>
```

Each page SHALL also identify CORPUS_STATE.json and MATERIALS_INDEX.jsonl as
live truth.

#### Scenario: fresh populated markers pass

- **WHEN** all four pages contain the exact labelled values from a state with
  id `snap-1` and source count `103`
- **THEN** the entry-page check emits no snapshot or source-count error

#### Scenario: a coincidental numeral does not satisfy the marker

- **WHEN** the live source count is `0` and a page contains an unrelated zero
  but lacks `Registered source artifacts: 0`
- **THEN** the check reports that page's missing source-count marker

#### Scenario: every state-bearing page is enforced

- **WHEN** any one of README.md, HOME.md, SYSTEM_DESIGN.md, or CLAUDE.md has a
  stale snapshot id or labelled source count
- **THEN** the check emits an error naming that page, the expected value and
  CORPUS_STATE.json, and instructs the operator to refresh the entry page from
  the registers in the same change

#### Scenario: absent state id skips only its own check

- **WHEN** the state mapping has no non-empty `id` but does have
  `source_material_count`
- **THEN** the snapshot-marker check is skipped while source-count and
  layer-count checks still run

### Requirement: The validator rejects visible layer-count contradictions

`check_entry_pages(root, state, errors)` SHALL derive recursive Markdown-file
counts for objects, relations, claims, and indexes from 03-objects,
06-relations, 05-claims, and 09-indexes. It SHALL inspect every visible-prose
singular or plural numeric declaration for those layers in all four entry
pages, case-insensitively. It SHALL ignore declarations inside fenced or
inline code and SHALL emit one actionable error for every contradictory
occurrence.

#### Scenario: a later contradiction cannot hide behind an earlier match

- **WHEN** an entry page says `2 objects` and later says `3 objects`, while
  the recursive directory count is `2`
- **THEN** the first declaration passes and the second produces a
  contradiction error naming the page, observed value, and actual value

#### Scenario: empty layer directories pass at birth

- **WHEN** the four layer directories contain no Markdown files and an entry
  page declares `0 objects`, `0 relations`, `0 claims`, and `0 indexes`
- **THEN** the layer-count check emits no contradiction

#### Scenario: code examples are not corpus claims

- **WHEN** a fenced or inline code example contains `99 objects`
- **THEN** that example does not produce a layer-count error

### Requirement: Normal validation, the hook, and CI enforce the same gate

`validate_repo.py` SHALL call `check_entry_pages(ROOT, state, errors)` exactly
once in its normal `validate()` path after loading the state and manifest.
The pre-commit hook and CI SHALL continue to invoke that path through
`scripts/check_against_baseline.py`. Entry-drift errors SHALL NOT be accepted
in `.githooks/known-baseline-errors.txt`.

#### Scenario: registered intake without refresh is blocked

- **WHEN** an internally consistent registered-corpus change alters the live
  snapshot id or source count but leaves one or more entry markers stale
- **THEN** direct validation exits nonzero, a local commit is blocked, and CI
  reports the same new validator error through the shared baseline script

#### Scenario: governed capture alone does not create entry drift

- **WHEN** a governed capture remains under `01-inbox/captures/` and does not
  change CORPUS_STATE.json, MATERIALS_INDEX.jsonl, or a counted record layer
- **THEN** the entry-page check requires no marker refresh

### Requirement: The mutation suite runs without pytest

`python tests/test_validator_mutations.py` SHALL discover and execute its
`test_*` functions, print per-test results, and exit nonzero when any test
fails. It SHALL use no new runtime dependency.

#### Scenario: RED is observable

- **WHEN** an entry-consistency assertion is deliberately unsatisfied
- **THEN** the direct Python command names the failing test and exits nonzero

### Requirement: Intake and reconciliation skills carry the consistency duty

`.claude/skills/wiki-intake/SKILL.md` SHALL require all four entry markers to
be refreshed from the registers in the same change whenever registered corpus
state changes. `.claude/skills/wiki-reconcile/SKILL.md` SHALL read and validate
the live source count and snapshot id from CORPUS_STATE.json at run start and
SHALL NOT carry an instance-specific baseline value.

#### Scenario: reconciliation starts from live state

- **WHEN** reconciliation starts with a valid CORPUS_STATE.json
- **THEN** its expected source count and snapshot id come from that file, not
  from skill prose

#### Scenario: no hardcoded corpus id survives in skills

- **WHEN** `.claude/skills/*/SKILL.md` is searched for `mw-corpus-`
- **THEN** the search returns no instance-specific baseline value

### Requirement: Templates match the validator contract

TEMPLATE_source-record.md SHALL include the `filename:` frontmatter field
required by `validate_repo.py` and a one-line description of the field.

#### Scenario: a filled template supplies filename

- **WHEN** an operator creates a source record by filling every placeholder in
  TEMPLATE_source-record.md, including `filename`
- **THEN** `validate_live_record_schema` reports no missing-field error for
  `filename`

### Requirement: Instantiation creates and preserves a gate-clean empty state

On a fresh kit with an empty manifest and source count `0`,
`scripts/instantiate.py --name X --prefix pxx` SHALL set the corpus-state id to
`pxx-corpus-empty` and render that id and count into the exact markers on all
four entry pages. The same invocation SHALL be idempotent. The command SHALL
refuse before writing when the manifest is non-empty, the source count is
nonzero, state and manifest disagree, or an existing INSTANCE.json identifies
a different instance.

#### Scenario: fresh instantiator output passes both validators

- **WHEN** the instantiator runs in a temporary copy as
  `--name "Smoke Wiki" --prefix swk`
- **THEN** CORPUS_STATE.json and all four pages contain
  `swk-corpus-empty` / `0`, no page retains the `wiki-corpus-empty` marker,
  and both validators exit zero before first intake

#### Scenario: same-instance rerun is idempotent

- **WHEN** the successful fresh invocation is repeated with the same name and
  prefix
- **THEN** tracked file content does not change

#### Scenario: populated instance is not reseeded

- **WHEN** the instantiator is invoked after the manifest or source count is
  non-empty
- **THEN** it exits nonzero before changing the register, entry pages, or
  INSTANCE.json

### Requirement: Documentation teaches pointer-true state and adoption

INSTANTIATE.md SHALL define the two labelled markers, the four-page refresh
duty, the capture-only exception, and the manual adoption sequence for an
existing instance. SYSTEM_DESIGN.md §1 SHALL carry the empty-kit markers and
§6 SHALL document the validator gate. Documentation SHALL state that the
registers remain live truth and that a populated instance must not rerun the
instantiator.

#### Scenario: a new operator follows one unambiguous rule

- **WHEN** an operator instantiates a wiki and later registers source intake
- **THEN** the initial pages are seeded automatically and the intake workflow
  directs the operator to refresh all four markers from the registers in the
  same change

#### Scenario: an existing instance adopts without reseeding

- **WHEN** an existing instance takes the new validator
- **THEN** its documented path is to add markers from its current registers in
  the same change, run both validators, and not run `instantiate.py`
