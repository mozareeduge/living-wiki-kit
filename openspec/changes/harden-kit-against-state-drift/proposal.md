# Proposal: harden-kit-against-state-drift

## Why

The ref-wiki instance suffered a governance incident on 2026-09-16. Its
entry documents (README.md, HOME.md, SYSTEM_DESIGN.md §1, CLAUDE.md, and the
wiki-reconcile skill) still described the 2026-09-10 seed state—11 sources,
intake paused, Horizon C open—six days after the corpus had reached 103
sources across three intake waves. A fully ingested batch therefore appeared
not to have been ingested, and an operator could have resumed it as a first
intake.

The incident exposed five kit-level causes:

1. **No validator binds entry prose to the registers.**
   `CORPUS_STATE.json` and `MATERIALS_INDEX.jsonl` hold the live values, but a
   commit can leave README.md, HOME.md, SYSTEM_DESIGN.md, or CLAUDE.md stale.
2. **Instantiation invites ungoverned corpus facts.** INSTANTIATE.md tells an
   operator to rewrite “the corpus facts” without defining a stable marker,
   refresh duty, or migration rule. The kit's own four entry documents do not
   currently share one current-state contract.
3. **A shipped skill contains an instance-specific baseline.**
   `.claude/skills/wiki-reconcile/SKILL.md` hardcodes “94 artifacts” and
   `mw-corpus-a33b260403015901`, which is false for the empty kit and for every
   new instance.
4. **A shipped template contradicts its validator.**
   TEMPLATE_source-record.md omits the required `filename` field. This caused
   a debugging round in zarinpal-product-wiki on 2026-09-14.
5. **The intake workflow does not carry the refresh duty.** It updates the
   manifest and corpus state without requiring the entry markers to change in
   the same bounded intake.

The validator design was exercised in ref-wiki PRs #3–#7, including an
end-to-end hook rejection, and merged at ref-wiki main db27adf. This change
ports that evidence into the kit while tightening the weak edges found in
review: all four state-bearing entry documents are covered; markers are
labelled rather than accepted as arbitrary numerals; every layer-count
statement is checked; and empty-kit and instantiation behavior are tested by
the repository's plain-Python runner.

## What changes

- **Entry contract:** README.md, HOME.md, SYSTEM_DESIGN.md, and CLAUDE.md each
  carry the same labelled snapshot-id and source-count markers, plus a pointer
  to the registers as live truth.
- **Validator:** `validate_repo.py` checks those four pages from its normal
  `validate()` path. It reports a page, expected value, source register, and
  repair action for each missing/stale marker, and checks every visible
  object/relation/claim/index count against recursive Markdown-file counts.
- **Tests:** `tests/test_validator_mutations.py` gains a working direct-run
  harness and RED→GREEN cases for the helper, its integration into
  `validate()`, the zero-count edge, all-match layer checking, readable
  errors, and instantiation. No pytest or new runtime dependency is added.
- **Skills and template:** wiki-reconcile reads its baseline at run time;
  wiki-intake refreshes all four entry pages whenever registered corpus state
  changes; TEMPLATE_source-record.md gains `filename:`.
- **Instantiation and docs:** the instantiator converts the empty register id
  to `<prefix>-corpus-empty`, renders all four entry markers from that state,
  is idempotent for the same fresh instance, and refuses populated-state
  reseeding. INSTANTIATE.md teaches both new-instance and existing-instance
  adoption.

Governed captures that remain under `01-inbox/captures/` do not change the
registered corpus and therefore do not trigger an entry refresh. Registration
through intake does.

## Impact

- Affected capability: `entry-consistency`.
- Primary implementation surfaces: `scripts/validate_repo.py`,
  `scripts/instantiate.py`, `tests/test_validator_mutations.py`, the two wiki
  skills, TEMPLATE_source-record.md, INSTANTIATE.md, SYSTEM_DESIGN.md,
  README.md, HOME.md, and CLAUDE.md.
- Release metadata must be updated atomically if the kit version becomes
  1.1.0: SYSTEM_DESIGN frontmatter, the content-release contract,
  `instantiate.py`'s `created_from`, and the README release note.
- Existing instances fail closed when they adopt the new validator until
  their four entry markers are populated from their own registers. Automatic
  migration and bulk rollout are out of scope; the manual adoption sequence
  is part of this change, and the instantiator must not be rerun on a populated
  instance.
