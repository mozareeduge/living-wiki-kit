# Lenses

Retrieval/presentation configurations for a persona, task, question, or
output — over one shared corpus, never separate copies of it.

A lens foregrounds (prioritizes, groups, formats); it does not change
authority and never silently filters. Defaults keep candidates visible and
annotated. An accepted-only view is always explicit.

What each field does in a context pack:

- `foreground_labels` — a record matched through one of these labels gets the
  reason `(foregrounded by lens <id>)`.
- `foreground_relations` — a relation whose `relation_type` is listed, and
  every record it joins, gets ``(lens <id> foregrounds relation `<type>`)``.
- `foreground_sections` — each record carries `section_order` (these
  headings first, then the rest as written); its content is unchanged.

None of them adds, removes or re-ranks a record.

Files here with `status: example` are **inactive illustrations**.

## Inactive examples

- [[lens-dramaturg]] — theatre-making foregrounding
- [[lens-scholar]] — research foregrounding
- [[lens-operator]] — product discovery: signals and decisions
- [[lens-investigator]] — investigation: allegations and corroboration
- [[lens-experimenter]] — experimental work: runs and replication
- [[lens-archivist]] — community archive: memories and accounts
