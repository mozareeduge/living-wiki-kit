# Profiles

Composable advisory bundles (see `00-system/policies/SEMANTIC_MODEL.md`).
A profile suggests vocabulary, relation language, lenses, and outputs for a
practice or context. Profiles configure attention, never truth: they cannot
weaken kernel invariants, and unknown labels always remain allowed.

Files here with `status: example` are **inactive illustrations** that ship
with the kit so a new instance can see the shape. Activate by listing ids in
`active_profiles` in `00-system/registers/INSTANCE.json` (created by
`scripts/instantiate.py`, which takes `--profile <id>` to activate them at
setup; empty by default). The empty kit stays
profile-neutral and fully functional.

## What an active profile changes in a context pack

- A record whose label matches an active profile's `seed_labels` gets the
  reason ``(profile <id> seed label `<label>`)`` and a `profile_attention`
  entry. Matching ignores case and spacing; the label is quoted as written.
- The pack's `meta` lists `active_profiles` and offers the profiles'
  `suggested_lenses` (with whether each lens ships). An offer is never
  applied; a lens applies only when asked for.
- Nothing else: no record is added, removed or reordered, and no authority
  changes. With no active profile the pack is exactly what it was.

## Inactive examples

- [[practice-research]] — long-horizon inquiry
- [[practice-creative]] — artistic work and unrealized possibilities
- [[practice-product-discovery]] — revisable decisions
- [[practice-investigation]] — hypotheses kept apart from facts
- [[practice-experimental]] — repeatability and provenance
- [[practice-community-archive]] — coexisting perspectives

