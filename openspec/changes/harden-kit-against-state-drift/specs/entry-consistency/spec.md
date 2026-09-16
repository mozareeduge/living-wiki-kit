# Spec Delta: entry-consistency

## ADDED Requirements

### Requirement: Entry pages mirror the registers

Every wiki instantiated from the kit SHALL keep its entry-level documents
(HOME.md, README.md, SYSTEM_DESIGN.md) consistent with the machine registers
(00-system/registers/CORPUS_STATE.json, MATERIALS_INDEX.jsonl) at every
commit, enforced by the deterministic validator.

**Enforcement (validator):** `validate_repo.py` SHALL run
`check_entry_pages(root, state, errors)` inside its main `validate()` path
(so the pre-commit hook and CI enforce it identically). For each entry page
the check SHALL:

- emit an error when the current snapshot id from CORPUS_STATE.json is
  absent from the page text (message names the missing id and says to
  "refresh the entry page from the registers in the same change");
- emit an error when the current `source_material_count` is absent;
- emit an error when any `\d+ objects|relations|claims|indexes` phrasing in
  the page contradicts the count derived from the corresponding record
  directory (03-objects, 06-relations, 05-claims, 09-indexes);
- tolerate a state dict without a snapshot id (empty-kit edge).

The empty kit SHALL pass at birth: `wiki-corpus-empty` / `0` must appear in
the seeded entry pages (instantiator writes them; kit's own pages carry them
natively).

#### Scenario: fresh instance passes

- WHEN a new instance is instantiated and validated before first intake
- THEN both validators pass with no entry-page errors

#### Scenario: intake without entry-page refresh is blocked

- WHEN a commit registers a new source (snapshot id and/or count change in
  CORPUS_STATE.json) but no entry page is updated in the same change
- THEN `git commit` fails via the pre-commit gate with the refresh
  instruction, and CI fails identically on push

#### Scenario: contradicted layer count is blocked

- WHEN an entry page states "N objects" where N differs from the number of
  .md files under 03-objects/
- THEN the validator emits the contradiction error

### Requirement: Intake and reconciliation skills carry the consistency duty

- `.claude/skills/wiki-intake/SKILL.md` step 10 SHALL instruct refreshing
  the current-state blocks of HOME.md, README.md, and SYSTEM_DESIGN.md §1
  from the registers in the same change as the manifest update.
- `.claude/skills/wiki-reconcile/SKILL.md` SHALL NOT hardcode a baseline;
  it SHALL read the live source count and snapshot id from
  CORPUS_STATE.json at run start.

#### Scenario: no hardcoded baseline survives

- Grep of `.claude/skills/*/SKILL.md` for `mw-corpus-` returns nothing.

### Requirement: Templates match the validator contract

TEMPLATE_source-record.md SHALL include the `filename:` frontmatter field
required by validate_repo.py's source-record schema, so a record created
from the template passes without template-drift debugging.

#### Scenario: template-created record passes schema

- WHEN a source record is created by filling TEMPLATE_source-record.md
- THEN validate_repo.py reports no missing-field error for `filename`

### Requirement: Instantiation seeds gate-clean entry pages

`scripts/instantiate.py` SHALL update the entry pages' snapshot anchor and
count to the fresh instance values (id `<prefix>-corpus-empty`, count 0) so
the empty instance passes `check_entry_pages` at birth.

#### Scenario: instantiator output passes the gate

- WHEN instantiate.py runs with `--name X --prefix pxx`
- THEN the entry pages reference `pxx-corpus-empty` and contain the count 0

### Requirement: Docs teach pointer-true state, not hardcoded state

INSTANTIATE.md SHALL include an explicit rule: entry docs restate register
values only as verified-at-instantiation anchors plus live-truth pointers to
the registers; the gate fails commits that drift. SYSTEM_DESIGN.md §6 SHALL
document the entry-page freshness gate in the validate_repo.py role, and
§1 SHALL carry the snapshot anchor (id + count) required by the gate.

#### Scenario: newcomer follows the documented rule

- WHEN an operator follows INSTANTIATE.md's pointer-true rule at
  instantiation and on later intake rounds
- THEN no entry doc hardcodes a count without its register anchor, and the
  gate passes each commit; a doc that restates counts without the anchor is
  rejected by the same gate
