# Profiles

Composable advisory bundles (see `00-system/policies/SEMANTIC_MODEL.md`).
A profile suggests vocabulary, relation language, lenses, and outputs for a
practice or context. Profiles configure attention, never truth: they cannot
weaken kernel invariants, and unknown labels always remain allowed.

Files here with `status: example` are **inactive illustrations** that ship
with the kit so a new instance can see the shape. Activate by listing ids in
`active_profiles` in `00-system/registers/INSTANCE.json` (created by
`scripts/instantiate.py`; empty by default). The empty kit stays
profile-neutral and fully functional.

## Inactive examples

- [[practice-research]] — long-horizon inquiry
- [[practice-creative]] — artistic work and unrealized possibilities
- [[practice-product-discovery]] — revisable decisions
- [[practice-investigation]] — hypotheses kept apart from facts
- [[practice-experimental]] — repeatability and provenance
- [[practice-community-archive]] — coexisting perspectives

