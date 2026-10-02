# Search Guide

## 1. Search is a route, not evidence

The wiki contains several descriptions of the same material:

- a canonical page;
- a claim or relation record;
- a source record;
- a machine-extracted derivative;
- an immutable original;
- an index or semantic result.

They are not interchangeable. For an interpretive question:

```text
canonical record → claim/relation → source record → extracted passage → immutable original
```

A search score does not increase a statement's certainty.

## 2. Obsidian search

- **Exact:** `Ctrl+Shift+F` for a known phrase, ID, property, or filename.
- **Backlinks/Outgoing links:** a backlink is navigational, not evidence of
  influence.
- **Properties:** YAML frontmatter stores `type`, `status`, `certainty`,
  `current_claim_permission`, `relation_status`, `updated`. Do not rename a
  property globally without a system decision and migration.
- **Bases:** saved views over properties. A Base is a view, not a database
  and not an authority layer.

## 3. QMD collections

Per-instance collections (see
`00-system/configuration/qmd-collections.json`):

- canonical: root, system, objects, notes, claims, relations, genesis, indexes
- evidence (excluded from default queries): source-records, derivatives

```powershell
qmd collection list
qmd status
powershell -ExecutionPolicy Bypass -File scripts/configure-search.ps1
powershell -ExecutionPolicy Bypass -File scripts/refresh-search.ps1
```

## 4. Search modes

```powershell
# lexical (exact terms, IDs, filenames)
qmd search '"exact phrase"' --files -n 10
# vector (nearby meaning)
qmd vsearch "meaning-like question" --files -n 10
# hybrid (default for open questions)
qmd query "open question" --files -n 10
```

## 5. Boundaries

- `_originals/` is not indexed directly.
- Exact form, images, handwriting, tracked changes → the original.
- A catalogue entry is not a manuscript; a source list is not proof of
  reading; a canonical page is not a primary source; an index, Base, graph,
  or QMD result is not a claim.

## 6. Validation

```powershell
python scripts/validate_repo.py --full
python scripts/validate_content_release.py
powershell -ExecutionPolicy Bypass -File scripts/verify-install.ps1
python scripts/run-semantic-benchmark.py
```

## 7. Benchmark case sets are instance data

The kit ships the benchmark runners but **no case set**: an empty kit has no
corpus to ask questions about, and a starter set would measure nothing. Each
instance writes its own `00-system/configuration/semantic-benchmark-v1.1.0.json`
(or passes `--config <file>` to `run-semantic-benchmark.py` /
`run_faithfulness_benchmark.py retrieve`). Without one, both runners exit with a
one-line explanation instead of a traceback. Minimal shape:

```json
{
  "id": "my-wiki-semantic-benchmark-1.1.0",
  "top_k": 5,
  "threshold": 27,
  "cases": [
    {"id": "q01",
     "question": "Who founded the institution behind the 1998 survey?",
     "expected_suffixes": ["people/some-person.md"]}
  ]
}
```

Each case needs `id`, `question` and `expected_suffixes` (path suffixes that
count as a hit in the top `top_k`); an optional `collection` restricts the
query to one QMD collection.
