# Spec Delta: holdings-census

## ADDED Requirements

### Requirement: Registration status is a biconditional, not a label

A source record SHALL declare `status: registered` if and only if its
repository-relative path appears as a `source_record_path` in
`00-system/registers/MATERIALS_INDEX.jsonl`. The validator SHALL report both
directions of violation, and each error SHALL name the record path and state
which side disagrees.

#### Scenario: a record claiming registration without a manifest row fails

- **WHEN** `02-sources/records/x-src-abc.md` carries `status: registered` and
  no manifest row has that `source_record_path`
- **THEN** the census check reports an error naming that record and
  `MATERIALS_INDEX.jsonl`

#### Scenario: a manifest row whose record omits registration fails

- **WHEN** a manifest row points at a record whose `status` is
  `pending-registration`
- **THEN** the census check reports an error naming the record and the row

#### Scenario: an agreeing pair passes

- **WHEN** every manifest row's record carries `status: registered` and no
  other record does
- **THEN** the census check emits no registration error

### Requirement: Every held artifact carries exactly one declared tier

Every file under `_originals/` SHALL be accounted for as either a manifest
`original_path`, or the `original_path` of a source record whose
`holdings_tier` is a tier declared in
`00-system/policies/HOLDINGS_POLICY.json` other than `registered`. An
unaccounted file SHALL be reported as held but undeclared, naming the file.

The tier vocabulary SHALL be exactly `registered`, `pending-registration`,
`reference-shelf`, declared identically in `HOLDINGS_POLICY.json` and
`00-system/policies/CONTROLLED_VOCABULARY.md`.

#### Scenario: an unregistered original with no record fails

- **WHEN** `_originals/stray.pdf` exists, is absent from the manifest, and no
  source record names it
- **THEN** the census check reports `_originals/stray.pdf` as held but
  undeclared

#### Scenario: a declared backlog artifact passes

- **WHEN** `_originals/stray.pdf` is named by a record carrying
  `holdings_tier: pending-registration` and `status: pending-registration`
- **THEN** the census check emits no coverage error for that file

#### Scenario: an undeclared tier value fails

- **WHEN** a record carries `holdings_tier: someday`
- **THEN** the check reports the record and lists the legal tier values

### Requirement: Held and registered counts are published separately

`00-system/registers/CORPUS_STATE.json` SHALL carry `source_material_count`
(the number of manifest rows), `held_artifact_count` (the number of files
under `_originals/`), and `holdings_by_tier` (a count per declared tier).
`holdings_by_tier` SHALL sum to `held_artifact_count`, and
`holdings_by_tier["registered"]` SHALL equal `source_material_count`.

`source_material_count` SHALL NOT be redefined to mean anything else.

#### Scenario: a count mismatch fails quoting both numbers

- **WHEN** `held_artifact_count` is `543` and `_originals/` holds `544` files
- **THEN** the check reports an error quoting `543` and `544` and naming
  `CORPUS_STATE.json`

#### Scenario: missing census keys skip only the count check

- **WHEN** `held_artifact_count` is absent from state
- **THEN** the count check is skipped and the registration and coverage checks
  still run

### Requirement: Entry pages restate both counts as labelled markers

Every entry page (README.md, HOME.md, SYSTEM_DESIGN.md, CLAUDE.md) SHALL carry
the literal labelled form `Artifacts held: <held_artifact_count>` in addition
to the snapshot and registered-count markers, so that a registered count is
never readable as a holdings count. The check SHALL be skipped when
`held_artifact_count` is absent from state, and SHALL quote the value observed
on the page when it fails.

#### Scenario: a page missing the held marker fails

- **WHEN** `held_artifact_count` is `544` and `HOME.md` carries no
  `Artifacts held:` marker
- **THEN** the entry-page check reports `HOME.md` and the expected marker

#### Scenario: an instance without census keys is not broken by the upgrade

- **WHEN** an instance's state has no `held_artifact_count`
- **THEN** no `Artifacts held:` error is reported for any page

### Requirement: Double-encoding is checked on every source record

The double-encoding (mojibake) check SHALL apply to `aliases`,
`original_path`, `filename` and `title` of every record under
`02-sources/records/`, not only to rows of `MATERIALS_INDEX.jsonl`. Each error
SHALL name the record, the field, and instruct the operator to re-derive the
value from the filesystem rather than hand-patch the garbled string.

#### Scenario: a garbled alias on an unregistered record is reported

- **WHEN** an unregistered record's `aliases` contains a U+FFFD replacement
  character
- **THEN** the check reports that record and that field

### Requirement: Registers declare their refresh obligation

Every `.md` file directly under `00-system/registers/` SHALL carry
`refresh_policy` with exactly one of `per-intake`, `per-release`, `static`,
and an ISO `YYYY-MM-DD` `updated` value. A `per-intake` register whose
`updated` predates `CORPUS_STATE.updated`, or a `per-release` register whose
`updated` predates `00-system/configuration/content-release.json`'s `updated`,
SHALL fail with both dates quoted. Files under
`00-system/registers/archive/` are exempt.

#### Scenario: a stale per-intake register fails

- **WHEN** a register declares `refresh_policy: per-intake` and `updated:
  2026-07-25` while `CORPUS_STATE.updated` is `2026-09-16`
- **THEN** the check reports that register and quotes both dates

#### Scenario: a static register never fails on freshness

- **WHEN** a register declares `refresh_policy: static` and an old `updated`
- **THEN** the check emits no freshness error for it

#### Scenario: a missing policy is an error, not a default

- **WHEN** a register carries no `refresh_policy`
- **THEN** the check reports that register and lists the three legal values

### Requirement: Migration into a populated instance is read-only by default

`scripts/retier_holdings.py` SHALL default to a dry run that writes nothing,
SHALL refuse `--apply` on a dirty working tree, and SHALL refuse before any
write when the manifest row count and `source_material_count` disagree, when
`HOLDINGS_POLICY.json` is missing, or when it declares an unknown tier. It
SHALL never modify `_originals/`, `MATERIALS_INDEX.jsonl`, any `sha256`, or a
record that is correctly registered.

#### Scenario: a dry run changes nothing

- **WHEN** the script runs with no arguments in a populated instance
- **THEN** it prints the planned retiering and the working tree is unchanged

#### Scenario: apply on a dirty tree refuses

- **WHEN** `--apply` runs with uncommitted changes present
- **THEN** it exits nonzero, names the dirty tree, and writes nothing

#### Scenario: a broken base state refuses before writing

- **WHEN** the manifest holds 97 rows and `source_material_count` is 96
- **THEN** the script exits nonzero before any file is modified
