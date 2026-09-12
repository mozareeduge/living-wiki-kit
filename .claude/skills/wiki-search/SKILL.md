---
name: wiki-search
description: Search the Mozare Wiki read-only using QMD, exact text, properties, and source records. Use for bounded questions and retrieval. Do not change files.
---

# Wiki Search

## Terms

- **bounded question**: a question whose answer can be responsibly developed from a selected set of relevant records.
- **semantic result**: a ranked candidate returned by meaning similarity; it is not evidence until its source is opened.
- **source record**: the provenance page that points to the immutable original and searchable derivative.

## Procedure

1. Restate the query in one precise sentence.
2. Run a hybrid QMD query:
   `qmd query "<question>" --json -n 12`
3. When exact wording, names, filenames, or identifiers matter, also run:
   `qmd search "<exact terms>" --json -n 20`
4. Inspect the top results. Prefer source records, canonical object pages, and current lineage pages over isolated machine-extracted passages.
5. Open the source record for each load-bearing result.
6. Open the immutable original when wording, layout, page sequence, images, tracked changes, or version identity matters.
7. Return:
   - answer;
   - source paths;
   - evidence status;
   - unresolved points;
   - whether the question requires full-corpus reconciliation.

Do not edit files. Do not call search ranking proof.
