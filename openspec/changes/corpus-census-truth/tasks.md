# Tasks: corpus-census-truth

15 rungs in five tracks. IDs are stable and are the same IDs used in root
`Plans.md`. Read `EXECUTOR_BRIEF.md` before the first one.

Tags: `[lane:gate]` touches validators; `[lane:doc]` documentation only;
`[lane:instance]` runs in a populated wiki, not in the kit;
`[tdd:required]` RED before GREEN, both pasted; `[size:S]` ~15 tool calls,
`[size:M]` ~40.

Dependency spine: **A1 → A2 → A3 → A4 → A5 → B1 → B2 → B3 → B4**, with
**C1, C2, D1, E1** parallel to track A after A1, and **C3** after C2 + B4.

---

## Track A — census truth (the defect)

### A1 — holdings tier vocabulary `[lane:gate] [size:S]`

Branch: `system/2026-09-17--corpus-census-truth` · Depends: none

**Goal.** Declare the three tiers in one machine-readable file and one human
file, and prove the two agree. No validator wiring.

**Context.** `00-system/policies/CONTROLLED_VOCABULARY.md`,
`design.md` section 3, `tests/test_validator_mutations.py` (read the module
header and `__main__` runner only).

**Steps.**

1. Create `00-system/policies/HOLDINGS_POLICY.json`:
   `schema_version` `"1.0.0"`; `tiers` as an object keyed by the three tier
   names, each with `description`, `manifest_row` (`"required"` or
   `"forbidden"`), and `counted_in` (`"source_material_count"` or
   `"held_artifact_count"`); `default_tier_for_unregistered`:
   `"pending-registration"`; `family_tier_overrides`: `{}` (the operator's
   per-family decision surface, empty in the kit).
2. Add a `## Holdings tier` section to `CONTROLLED_VOCABULARY.md` listing the
   same three values with the same one-line meanings.
3. Add `load_holdings_policy(root)` to `scripts/validate_repo.py` — parse,
   return the dict, raise a self-explanatory error on a missing file or an
   unknown tier key. Not called from `validate()` yet.
4. Add tests: the policy parses; `default_tier_for_unregistered` is one of the
   declared tiers; **the tier set in the JSON equals the tier set parsed out of
   `CONTROLLED_VOCABULARY.md`** (assert set equality — do not eyeball it); an
   unknown tier name in a fixture policy raises.

**Acceptance.**

- (a) `python tests/test_validator_mutations.py` prints `N/N passed` with the
  four new test names visible in the PASS list.
- (b) `python -c "import json;p=json.load(open('00-system/policies/HOLDINGS_POLICY.json'));print(sorted(p['tiers']))"`
  prints `['pending-registration', 'reference-shelf', 'registered']`.
- (c) `grep -n "check_holdings_census\|load_holdings_policy" scripts/validate_repo.py`
  shows `load_holdings_policy` defined and **not** referenced inside
  `def validate(`.
- (d) `python scripts/validate_repo.py --full` prints `PASS`.

**Negative.** No change to `validate()`. No change to any entry page. No new
dependency.

---

### A2 — `check_holdings_census` helper, RED then GREEN `[lane:gate] [tdd:required] [size:M]`

Depends: A1

**Goal.** Implement the biconditional and the coverage/count invariants as a
standalone helper. Still not wired.

**Context.** `scripts/validate_repo.py` (`check_entry_pages` is the shape to
copy — same signature, same error-message style, same `REFRESH_HINT`
discipline), `design.md` sections 3–4, `tests/test_validator_mutations.py`
(the `_gate_root` fixture helpers).

**Signature.** `check_holdings_census(root: Path, state: dict, errors: list[str]) -> None`

**Invariants to enforce, in this order.**

1. **Biconditional.** A source record carries `status: registered` **iff** its
   repo-relative path appears as a `source_record_path` in
   `MATERIALS_INDEX.jsonl`. Both directions are errors, and each names the
   record path and which side is wrong.
2. **Coverage.** Every file under `_originals/` is either a manifest
   `original_path`, or is the `original_path` of a source record whose
   `holdings_tier` is a declared non-`registered` tier. An uncovered file is an
   error naming the file and stating that it is held but undeclared.
3. **Tier legality.** A record with `holdings_tier: registered` must be a
   manifest row; a manifest row's record must not carry a non-`registered`
   tier.
4. **Counts.** `held_artifact_count` equals the number of files under
   `_originals/`; `holdings_by_tier` sums to it; `source_material_count`
   equals the manifest row count and equals `holdings_by_tier["registered"]`.
   Each mismatch is a separate error quoting both numbers.
5. **Absent keys skip, they do not pass.** If `held_artifact_count` is absent
   from state, skip invariant 4 only, and still run 1–3.

**Steps.** Write the table-driven RED tests first, on temp fixture roots:
all-registered-and-consistent passes with zero errors; an unregistered
original with no record fails naming that file; a record claiming `registered`
while absent from the manifest fails naming that record; a manifest row whose
record carries `pending-registration` fails; `held_artifact_count` off by one
fails quoting 544 and 543; `holdings_by_tier` not summing fails; empty
`_originals/` with counts 0 passes; absent `held_artifact_count` runs 1–3 and
skips 4. Then implement.

**Acceptance.**

- (a) RED pasted: the suite exits nonzero and every new test appears as a
  named `FAIL` **before** the helper exists.
- (b) GREEN pasted: `python tests/test_validator_mutations.py` prints
  `N/N passed`.
- (c) `grep -n "check_holdings_census" scripts/validate_repo.py` shows the
  definition and **no** call inside `def validate(`.
- (d) Every error string produced by the helper names a path **and** the
  register that disagrees with it — asserted by a test, not by reading.

**Negative.** Do not wire into `validate()` (that is A4). Do not touch
`check_entry_pages`. Do not read a real instance.

**Stop.** If the fixture work needs a decision about what counts as a "file
under `_originals/`" for a nested directory, choose `rglob` over files only
(matching `check_entry_pages`' layer counting) and note it — do not ask.

---

### A3 — `CORPUS_STATE.json` census keys `[lane:gate] [size:S]`

Depends: A2

**Goal.** Publish the two new numbers in the kit's own state and pin the
meaning of the old one in prose.

**Context.** `00-system/registers/CORPUS_STATE.json`, `SYSTEM_DESIGN.md`
sections 2 and 6, `design.md` section 4.

**Steps.**

1. Add to the kit's `CORPUS_STATE.json`: `"held_artifact_count": 0` and
   `"holdings_by_tier": {"registered": 0, "pending-registration": 0, "reference-shelf": 0}`.
2. In `SYSTEM_DESIGN.md`, add one sentence that fixes the vocabulary:
   `source_material_count` is the manifest row count; `held_artifact_count` is
   the file count under `_originals/`; the two are not interchangeable.
3. Update the `validate_repo.py` row in the section 6 table to mention the
   holdings census.

**Acceptance.**

- (a) `python -c "import json;s=json.load(open('00-system/registers/CORPUS_STATE.json'));print(s['held_artifact_count'], sum(s['holdings_by_tier'].values()))"`
  prints `0 0`.
- (b) `python scripts/validate_repo.py --full` prints `PASS`.
- (c) `python tests/test_validator_mutations.py` still prints `N/N passed`.
- (d) `grep -c "source_material_count" SYSTEM_DESIGN.md` is at least 1 and the
  sentence distinguishing the two counts is present.

**Negative.** Do not touch `MATERIALS_INDEX.jsonl`. Do not change
`corpus_snapshot_sha256`. Do not add a JSON Schema file (design section 4).

---

### A4 — enable the census gate `[lane:gate] [tdd:required] [size:M]`

Depends: A3

**Goal.** The gate runs on every normal validation — hook and CI — and the
kit stays clean.

**Context.** `scripts/validate_repo.py` (`validate()`, and the 1.1.0 wiring of
`check_entry_pages` as the precedent), `tests/test_validator_mutations.py`
(`test_validate_calls_entry_gate_once_with_loaded_state` is the pattern to
copy), `.githooks/pre-commit`, `.github/workflows/validate.yml`.

**Steps.**

1. RED: an in-process test asserting `validate()` calls
   `check_holdings_census` exactly once with the loaded state; a subprocess
   test that plants an undeclared file under `_originals/` in a throwaway copy
   and asserts `validate_repo.py --full` exits nonzero naming that file.
2. GREEN: call `check_holdings_census(ROOT, state, errors)` from `validate()`
   immediately after the existing `check_entry_pages` call.
3. Run all four commands from the brief, section 4.
4. Run `claude-code-harness:test-wiring-auditor` over the diff and paste its
   verdict.

**Acceptance.**

- (a) Both new tests pasted as named `FAIL` before step 2.
- (b) `python tests/test_validator_mutations.py` prints `N/N passed`.
- (c) All four brief commands print their expected verdict lines.
- (d) `git diff -- .githooks/known-baseline-errors.txt` is empty.
- (e) test-wiring-auditor verdict pasted, and any finding it raises is either
  fixed in this rung or written into the review note with a reason.

**Negative.** No baseline line. No `--no-verify`. Do not also adopt anything
in `mozare-wiki`.

---

### A5 — `retier_holdings.py`, read-only by default `[lane:gate] [size:M]`

Depends: A4

**Goal.** The migration instrument for populated instances. Safe by
construction: it reports, and only writes when explicitly told and the tree is
clean.

**Context.** `scripts/instantiate.py` (the precondition-then-write shape, and
its refusal style), `design.md` section 8, `00-system/policies/HOLDINGS_POLICY.json`.

**Behaviour.**

- default `--dry-run`: print a table — records correctly `registered`,
  records to retier, per-family counts, the resulting `holdings_by_tier`, and
  the `held_artifact_count` it would write. Write nothing.
- `--apply`: same plan, then set `status` and `holdings_tier` on each
  record that needs retiering, and update `CORPUS_STATE.json`'s
  `held_artifact_count` / `holdings_by_tier`.
- refuse, before any write, with a nonzero exit and a one-line reason, when:
  the working tree is dirty; the manifest row count and
  `source_material_count` disagree; `HOLDINGS_POLICY.json` is missing or names
  an unknown tier; a `family_tier_overrides` key matches no record family.
- tier selection per record: `family_tier_overrides[family]` if present, else
  `default_tier_for_unregistered`.

**Acceptance.**

- (a) `python scripts/retier_holdings.py` (no args) in the empty kit prints a
  plan with `0 records to retier` and exits 0;
  `git status --porcelain` is unchanged afterwards.
- (b) A temp-copy fixture test: one unregistered original + its record
  claiming `registered` → dry run reports exactly `1 records to retier` and
  changes no file; `--apply` flips it to
  `status: pending-registration` / `holdings_tier: pending-registration`, and a
  following `validate_repo.py --full` prints `PASS`.
- (c) `--apply` on a dirty tree exits nonzero with a message containing
  `dirty` and writes nothing.
- (d) Manifest/state disagreement fixture exits nonzero **before** any write,
  asserted by a tree hash equal to the pre-run hash.
- (e) `python tests/test_validator_mutations.py` prints `N/N passed`.

**Negative.** Never touch `_originals/`, `MATERIALS_INDEX.jsonl`, or any
`sha256`. Never change a record that is correctly `registered`. No `--force`
flag — a dirty tree is refused, full stop.

---

## Track B — honest restatement

### B1 — entry gate learns `Artifacts held:` `[lane:gate] [tdd:required] [size:S]`

Depends: A4

**Goal.** The four entry pages must also carry the held count, checked by
exact string match, skipped cleanly on instances that have not adopted A3.

**Context.** `scripts/validate_repo.py` (`check_entry_pages`),
`tests/test_validator_mutations.py` (the `_fresh_pages` / `_page_text`
fixtures), `design.md` section 5.

**Marker.** `Artifacts held: <held_artifact_count>` — labelled, exact,
code-span-tolerant exactly like the existing two markers.

**Steps.** RED: fresh pages with both markers pass; a page missing
`Artifacts held:` fails naming that page; a page with the wrong held number
fails quoting expected and observed; `held_artifact_count` absent from state
skips only this check and still enforces the other two. Then GREEN.

**Acceptance.**

- (a) RED pasted with named failures, one per entry page.
- (b) `python tests/test_validator_mutations.py` prints `N/N passed`.
- (c) The error message quotes the observed value from the raw page text, not a
  bare label — asserted by a test (the 1.1.0 precedent:
  `_visible_prose()` strips the code span the value lives in).
- (d) `python scripts/validate_repo.py --full` prints `PASS` **only after** B2
  adds the marker; until then a local failure here is expected and must be
  stated in the report rather than worked around.

**Negative.** Do not add the marker to the pages in this rung (that is B2, so
that the RED state is real). Do not make the check a warning.

---

### B2 — seed the marker in the kit and the instantiator `[lane:gate] [size:M]`

Depends: B1

**Goal.** The kit's own four pages carry both markers; a newly instantiated
wiki gets them seeded; the documented adoption order covers the new marker.

**Context.** `README.md`, `HOME.md`, `SYSTEM_DESIGN.md`, `CLAUDE.md`,
`scripts/instantiate.py` (the `entry_pages` marker rewrite), `INSTANTIATE.md`
section 3.5.

**Steps.**

1. Add `Artifacts held: 0` next to the existing two markers on all four pages.
2. Extend `instantiate.py` so the seeded pages carry all three markers with
   the instance's own corpus id.
3. Extend `INSTANTIATE.md` section 3.5: the third marker, what it counts, and
   that `held_artifact_count` must be set from the filesystem, not typed.
4. Extend the instantiator smoke test to assert all three markers appear with
   the instance prefix and that `wiki-corpus-empty` appears nowhere.

**Acceptance.**

- (a) `grep -c "Artifacts held: 0" README.md HOME.md SYSTEM_DESIGN.md CLAUDE.md`
  prints `1` for each of the four.
- (b) `python tests/test_validator_mutations.py` prints `N/N passed`, including
  the extended instantiator smoke and idempotence tests.
- (c) `python scripts/validate_repo.py --full` prints `PASS`.
- (d) Rerunning the instantiator with the same arguments produces no content
  diff (the existing idempotence test still passes).

**Negative.** Do not reword the two existing markers. Do not touch
`_originals/`.

---

### B3 — kit 1.2.0 release `[lane:doc] [size:S]`

Depends: B2

**Goal.** One atomic version bump, no half-bumped declaration.

**Context.** `SYSTEM_DESIGN.md` frontmatter, `00-system/configuration/content-release.json`,
`scripts/instantiate.py` (`created_from`), `CLAUDE.md` kit-version bullet,
`README.md` "Kit version" note.

**Steps.** Bump exactly those five to `1.2.0`; the README note names the
census gate and the third marker, and points at `INSTANTIATE.md` section 3.5
for existing instances. Leave every `schema_version` alone — no schema
changed.

**Acceptance.**

- (a) `grep -rn "1\.1\.0" --include=*.md --include=*.json --include=*.py . | grep -v schema_version | grep -v openspec | grep -v "\.git/"`
  returns nothing.
- (b) `python scripts/validate_repo.py --full` and
  `python scripts/validate_content_release.py` both print `PASS`.
- (c) `python scripts/check_against_baseline.py` prints `OK: validators clean.`
- (d) PR opened, CI `validate` green, merged, local `main` SHA equals remote
  `main` SHA (paste both).

**Negative.** Do not bump any `schema_version`. Do not bump the capture schema
or the MCP server version.

---

### B4 — adopt the census in `mozare-wiki` `[lane:instance] [size:M]` — **operator-gated**

Depends: B3 · Runs in: `Documents/Personal Formal Documents/mozare-wiki/mozare-wiki`

**Goal.** The production instance tells the truth: 97 registered, 544 held,
447 declared, and `HOME.md` no longer says 94.

**Known numbers, measured 2026-09-17** (reconfirm, do not assume): manifest
rows 97; files under `_originals/` 544; source records 556; records claiming
`status: registered` 544; `HOME.md` states `Source artifacts: 94` and
`updated: '2026-07-27'`; `CORPUS_STATE.updated` is `2026-09-16`.

**Steps.**

1. On a new branch `system/2026-09-XX--adopt-census`, confirm the base state:
   `python scripts/validate_repo.py --full` prints `PASS` before any edit.
2. Copy the kit's shipped `scripts/validate_repo.py`, `scripts/retier_holdings.py`,
   `00-system/policies/HOLDINGS_POLICY.json`, the `CONTROLLED_VOCABULARY.md`
   tier section, and `tests/test_validator_mutations.py` into the instance.
   Nothing else from the kit.
3. Run `python scripts/retier_holdings.py` (dry run). Paste the plan. Expect
   447 records to retier.
4. **Operator gate.** If `family_tier_overrides` is empty, everything becomes
   `pending-registration`. If the operator has decided some families are a
   reference shelf, record that mapping in `HOLDINGS_POLICY.json` **in this
   commit** and rerun the dry run. If no decision exists, emit
   `advisor-request.v1` naming the top families by count and stop.
5. `python scripts/retier_holdings.py --apply` on a clean tree.
6. Set `held_artifact_count: 544` and the tier breakdown in
   `CORPUS_STATE.json`; bump its `updated`.
7. Rewrite the four entry pages' state lines to the three labelled markers
   with the real values: snapshot `mw-corpus-a33b260403015901`,
   `Registered source artifacts: 97`, `Artifacts held: 544`. Delete the
   unlabelled `Source artifacts: 94` line and refresh `HOME.md`'s frontmatter
   `updated`.
8. Run the four brief commands. Write a handoff in `07-genesis/handoffs/`.

**Acceptance.**

- (a) `python scripts/validate_repo.py --full` prints `PASS` with the census
  gate active.
- (b) `grep -l "^status: registered" 02-sources/records/*.md | wc -l` prints
  exactly `97`.
- (c) `python -c "import json;s=json.load(open('00-system/registers/CORPUS_STATE.json'));print(s['source_material_count'], s['held_artifact_count'], sum(s['holdings_by_tier'].values()))"`
  prints `97 544 544`.
- (d) Each of the four entry pages contains all three labelled markers, and
  `grep -rn "Source artifacts: 94" .` returns nothing.
- (e) `git diff --stat main...HEAD -- _originals/ 00-system/registers/MATERIALS_INDEX.jsonl`
  is empty.
- (f) A handoff file exists naming changed files, the 447 decision, validation
  output, and the next operation.

**Negative.** Never rerun `instantiate.py` here. Never register an artifact as
part of this rung. Never edit a `sha256`. Never add a baseline line.

**Stop.** Any surprise in the numbers — 447 is not 447, base state is not
`PASS`, a record is `registered` with no original on disk — stops the rung
with an `advisor-request.v1`. A surprise in a production archive is evidence,
not an obstacle.

## Track C — hygiene guards

### C1 — mojibake guard across every source record `[lane:gate] [tdd:required] [size:S]`

Depends: A1 · Parallel to A2–A5

**Goal.** The double-encoding check reaches every source record, not only the
97 in the manifest.

**Context.** `scripts/validate_repo.py` (`looks_double_encoded()` and its
current call site inside the manifest-row loop),
`tests/test_validator_mutations.py`, `design.md` section 6.

**Steps.**

1. RED: a fixture source record whose `aliases` contains
   `Anna�s Archive.pdf` and whose `original_path` contains
   `Latour � Boekenkrant` produces one named error per offending field,
   each naming the record path and the field; a clean record produces none;
   the existing manifest-row mojibake test still passes unchanged.
2. GREEN: apply `looks_double_encoded()` to `aliases` (each element),
   `original_path`, `filename` and `title` of every record under
   `02-sources/records/`, inside the existing frontmatter walk. Reuse the
   existing error wording — the one that tells the operator to re-derive the
   name from the filesystem rather than hand-patch the garbled string.
3. Measure the blast radius without changing anything:
   run `python scripts/validate_repo.py --full` in a **throwaway clone** of
   `mozare-wiki` with the new validator copied in, and record the error count
   in the review note.

**Acceptance.**

- (a) RED pasted with one named failure per offending field.
- (b) `python tests/test_validator_mutations.py` prints `N/N passed`.
- (c) `python scripts/validate_repo.py --full` prints `PASS` in the kit.
- (d) The review note states the exact number of records this would fire on in
  `mozare-wiki`, and the throwaway clone is deleted.

**Negative.** Do **not** add a baseline line anywhere. Do **not** "fix" a
single filename in any instance — renaming an original is forbidden and
rewriting an alias is content work. This rung reports the radius; C3's operator
decides.

---

### C2 — register refresh-policy gate `[lane:gate] [tdd:required] [size:M]`

Depends: A1 · Parallel to A2–A5

**Goal.** A `.md` register either declares how often it must be refreshed, or
fails. A `per-intake` register that lags the corpus fails.

**Context.** `scripts/validate_repo.py`, `00-system/registers/RELEASE_READINESS_REGISTER.md`,
`00-system/configuration/content-release.json`, `design.md` section 7.

**Signature.** `check_register_policies(root: Path, state: dict, errors: list[str]) -> None`

**Rules.**

1. Every `.md` directly under `00-system/registers/` carries
   `refresh_policy` from exactly `{per-intake, per-release, static}` and an
   `updated` date. A missing or unknown value is an error naming the file and
   listing the legal values.
2. `per-intake` fails when its `updated` predates `CORPUS_STATE.updated`; the
   error quotes both dates and names both files.
3. `per-release` fails when its `updated` predates the `updated` of
   `00-system/configuration/content-release.json`.
4. `static` never fails on freshness.
5. Files under `00-system/registers/archive/` are exempt entirely.
6. Dates are compared as ISO `YYYY-MM-DD` strings after validating the shape;
   an unparseable date is its own error, never a silent pass.

**Steps.** RED the six rules on fixture roots, then GREEN, then wire into
`validate()` in the same rung (unlike A2, this helper has no instance-wide
blast radius in the kit: the kit has one register `.md`). Give
`RELEASE_READINESS_REGISTER.md` `refresh_policy: per-release`.

**Acceptance.**

- (a) RED pasted: at least six named failures, one per rule.
- (b) `python tests/test_validator_mutations.py` prints `N/N passed`.
- (c) A subprocess test proves a stale `per-intake` register makes
  `validate_repo.py` exit nonzero and quote both dates.
- (d) `python scripts/validate_repo.py --full` prints `PASS` in the kit.
- (e) `claude-code-harness:test-wiring-auditor` verdict pasted.

**Negative.** No day-count window. No timezone arithmetic. No `datetime`
parsing beyond an ISO-shape check — a string comparison is the contract.

---

### C3 — apply register policy in `mozare-wiki` `[lane:instance] [size:M]` — **operator-gated**

Depends: C2, B4 · Runs in: `mozare-wiki`

**Goal.** All thirteen `.md` registers either declare a policy and are fresh,
or are archived with a reason. The six July registers stop reading as current.

**Known state, measured 2026-09-17.** Fresh (2026-09-16): `BIOGRAPHICAL_CLAIM_REGISTER`,
`CONCEPT_METHOD_DISPOSITION_REGISTER`, `CORPUS_MAP`, `EXTERNAL_VERIFICATION_REGISTER`,
`MATERIALS_REGISTER`. Mid (2026-08-31 / 2026-09-04): `WORK_CANDIDATE_REGISTER`,
`CORRESPONDENCE_STATUS_REGISTER`. **Stale since July**: `AI_RESEARCH_REPORT_AUTHORITY_REGISTER`
(07-26), `FINAL_CONTENT_DISPOSITION_REGISTER` (07-27),
`PROJECT_DOCUMENT_DISPOSITION_REGISTER` (07-25), `PROJECT_ROUTE_REGISTER` (07-25),
`RELEASE_READINESS_REGISTER` (07-27), `RESEARCH_FIELD_DISPOSITION_REGISTER` (07-26).

**Steps.**

1. Copy the shipped `check_register_policies` into the instance's validator.
2. Produce a table: register, current `updated`, proposed `refresh_policy`,
   proposed action (`tag` / `refresh` / `archive`). Propose `per-intake` only
   for registers whose content is a function of the corpus; `static` for
   policy-like registers; `archive` for a register the operator no longer
   consults.
3. **Operator gate.** Present that table and stop. The question "is this
   register still consulted?" is not answerable from the repository.
4. After the decision: tag each register, move archived ones to
   `00-system/registers/archive/` with a one-line reason at the top of each,
   refresh the ones marked `refresh`, and update `CORPUS_MAP.md` if it lists
   moved registers.

**Acceptance.**

- (a) `grep -L "refresh_policy" 00-system/registers/*.md` returns nothing.
- (b) `python scripts/validate_repo.py --full` prints `PASS`.
- (c) Every file under `00-system/registers/archive/` has a first-line reason
  and appears in the handoff.
- (d) No register's *content* was rewritten in this rung except where the
  operator said `refresh`; a diff of any `tag`-only register shows exactly one
  added line.

**Negative.** Do not delete a register. Do not infer from git history that a
register is abandoned — a register can be stable and still consulted.

---

## Track D — self-description honesty

### D1 — tier the SYSTEM_DESIGN script table `[lane:doc] [size:S]`

Depends: A1 · Parallel to everything

**Goal.** A reader can tell which scripts run daily and which have never run
in any instance. The kit stops asserting its unexercised parts at the same
confidence as its validators.

**Context.** `SYSTEM_DESIGN.md` section 6, `README.md` (the "what it ships"
list), `tests/test_validator_mutations.py`.

**Evidence, measured in `mozare-wiki` 2026-09-17.** Never run there:
`export_interchange.py`, `export_public.py`, `run-semantic-benchmark.py`
(`08-outputs/` does not exist; `_search/` is absent). Run routinely:
`validate_repo.py`, `validate_content_release.py`, `check_against_baseline.py`,
`wiki_capture.py`, `file-to-md/to_md.py`, `wiki_mcp_server.py`.

**Steps.**

1. Add a `status` column to the section 6 table with exactly one of
   `operational` or `available (unexercised)` per row.
2. Reword the README and SYSTEM_DESIGN section 1 bullets that currently
   present the export/interchange layer as shipped capability, so they say
   available-and-unexercised.
3. Add a test that reads the section 6 table and fails if any row lacks one of
   the two exact status strings — so a future script added to the table cannot
   arrive untagged.

**Acceptance.**

- (a) `python tests/test_validator_mutations.py` prints `N/N passed`, including
  the new table-completeness test.
- (b) Deleting a status cell in a scratch copy makes that test fail by name
  (paste the negative check).
- (c) `python scripts/validate_repo.py --full` prints `PASS`.
- (d) `grep -n "available (unexercised)" SYSTEM_DESIGN.md` shows exactly three
  rows.

**Negative.** Do not delete or implement any unexercised script. Relabelling
is the whole rung.

---

## Track E — bottleneck visibility

### E1 — `report_holdings.py`, read-only audit `[lane:gate] [size:M]`

Depends: A4 · Parallel to B

**Goal.** One command reproduces the audit that motivated this change, so the
next drift is found by running something rather than by noticing.

**Context.** `scripts/check_against_baseline.py` (the read-only reporting
shape), `.gitignore` (`_audits/runtime/` is ignored — that is the only write
destination allowed), `design.md` section 1.

**Output, in this order.**

1. `registered / held / unregistered` counts and the tier breakdown.
2. Records whose `status` contradicts the manifest — count, and the first five
   paths.
3. Proposals in `_proposals/proposals.jsonl` grouped by `status`, with the
   `new` count called out as the adjudication backlog.
4. Claims grouped by `current_claim_permission`, `blocked` called out.
5. `.md` registers with their `refresh_policy` and a `STALE` flag.
6. Mojibake hits by field.
7. A one-line verdict: `CENSUS CLEAN` or `CENSUS DRIFT: <n> findings`.

**Acceptance.**

- (a) `python scripts/report_holdings.py` on the empty kit prints all seven
  sections with zeros and `CENSUS CLEAN`, exit 0.
- (b) `git status --porcelain` is byte-identical before and after a run.
- (c) `--json` emits one parseable object;
  `python scripts/report_holdings.py --json | python -c "import json,sys;d=json.load(sys.stdin);print(d['held'], d['registered'])"`
  prints `0 0`.
- (d) Run in a throwaway clone of `mozare-wiki`, it reproduces the audit
  numbers `97` registered, `544` held, `32` proposals with `20` at `new`,
  `24` claims with `1` blocked. Paste the output; delete the clone.
- (e) `python tests/test_validator_mutations.py` prints `N/N passed`.

**Negative.** No writes outside `_audits/runtime/`. No network. No model call.
No new dependency. Never a `--fix` flag — this instrument reports and nothing
else.

---

## Closing rungs

### Z1 — archive the change `[lane:doc] [size:S]`

Depends: every row above at `cc:done`

Fold `specs/holdings-census/spec.md` into `openspec/specs/holdings-census/spec.md`
(drop the `## ADDED Requirements` header, add a one-line provenance comment),
move the change to `openspec/changes/archive/2026-09-XX-corpus-census-truth/`,
and check every box in this file.

**Acceptance.** (a) `openspec/changes/corpus-census-truth/` no longer exists;
(b) `openspec/specs/holdings-census/spec.md` exists; (c) no unchecked `- [ ]`
remains in the archived `tasks.md`; (d) `validate_repo.py --full` prints
`PASS`.

### Z2 — horizon check `[lane:doc] [size:S]`

Depends: Z1

Run `python scripts/report_holdings.py` in the kit and in `mozare-wiki`, and
assert the horizon sentence from `design.md` section 1 holds in both:
no unchecked number, no undeclared document, no stale register presented as
current.

**Acceptance.** (a) Both runs print `CENSUS CLEAN`; (b) a handoff in each repo
records the two outputs; (c) if either prints `CENSUS DRIFT`, the ladder is not
finished — open the follow-up rows rather than declaring completion.

---

## Checklist

- [ ] A1 holdings tier vocabulary
- [ ] A2 `check_holdings_census` helper (RED/GREEN)
- [ ] A3 `CORPUS_STATE.json` census keys
- [ ] A4 enable the census gate
- [ ] A5 `retier_holdings.py`
- [ ] B1 entry gate learns `Artifacts held:`
- [ ] B2 seed the marker in kit + instantiator
- [ ] B3 kit 1.2.0 release
- [ ] B4 adopt the census in mozare-wiki (operator-gated)
- [ ] C1 mojibake guard across every source record
- [ ] C2 register refresh-policy gate
- [ ] C3 apply register policy in mozare-wiki (operator-gated)
- [ ] D1 tier the SYSTEM_DESIGN script table
- [ ] E1 `report_holdings.py`
- [ ] Z1 archive the change
- [ ] Z2 horizon check
