# Proposal: corpus-census-truth

## The defect

`00-system/registers/MATERIALS_INDEX.jsonl` is named "live truth" in README.md,
HOME.md, SYSTEM_DESIGN.md, CLAUDE.md, AGENTS.md, and INSTANTIATE.md. In the
production instance `mozare-wiki` it holds **97 rows** while `_originals/`
holds **544 files** and `02-sources/records/` holds **556 records**.

447 of those source records declare `status: registered` in their own
frontmatter while being absent from the register. Two contradictory truths
inside one archive.

`python scripts/validate_repo.py --full` reports:

```
PASS: repository structure, metadata, manifest, checksums, and links are valid
```

It passes because `validate()` walks **manifest to disk** ("every row's
original and source record exist") and never **disk to manifest** ("every held
artifact is accounted for"). The validator performs referential integrity
while its output sentence, and every document that cites it, implies a census.

Measured 2026-09-17 against `mozare-wiki` at branch
`audit/2026-09-16--mw-read-0008-full`.

## Why it must be fixed before anything else is built on it

Kit 1.1.0 (this repo, PR #2, 2026-09-17) shipped an entry-page freshness gate
that forces README/HOME/SYSTEM_DESIGN/CLAUDE to display
`Registered source artifacts: <count>` and refuses any commit where the pages
lag `CORPUS_STATE.json`.

That gate is correct and it makes the defect worse. Adopted in `mozare-wiki`
as-is, it stamps validator authority on `Registered source artifacts: 97` at
the top of an archive holding 544 documents. A reader — the operator in six
months, a collaborator, a model routing through the authority hierarchy —
reads 97 as the corpus. The kit would then enforce the prominence of a
minority figure.

Fixing the census question is therefore a precondition of adopting 1.1.0 in
any populated instance, not a follow-up to it.

## The invariant this change introduces

> A source record declares `status: registered` **if and only if** its path
> appears as a `source_record_path` in `MATERIALS_INDEX.jsonl`.

Everything else in the change exists to make that biconditional true,
checkable, and visible:

1. every file in `_originals/` maps to exactly one declared holdings tier;
2. `CORPUS_STATE.json` publishes `held_artifact_count` alongside
   `source_material_count`, and the two are never conflated again;
3. entry pages carry both numbers as separately labelled markers, so
   "registered" cannot be silently read as "held";
4. the tier of held-but-unregistered material is an operator decision recorded
   in one policy file, never inferred by a tool or a model.

## Secondary defects fixed in the same ladder

- **Mojibake reaches only manifest rows.** `looks_double_encoded()` inspects
  manifest fields only. The 447 unregistered records carry strings such as
  `Anna<?>s Archive.pdf` and `Latour <?> Boekenkrant` in `aliases` and
  `original_path`, unchecked.
- **Six of thirteen `.md` registers in `mozare-wiki` were last updated
  2026-07-25 … 2026-07-27** while the corpus moved through 2026-09-16. No
  check governs any of them; they read as current and are not.
- **SYSTEM_DESIGN.md section 6 lists unexercised machinery at the same
  confidence as daily validators.** `08-outputs/` does not exist in
  `mozare-wiki`; `_search/` is absent; `export_interchange.py`,
  `export_public.py` and `run-semantic-benchmark.py` have never run there. The
  kit applies evidence discipline to its content and not to its own
  self-description.

## Explicitly out of scope

- Adjudicating the 20 `new` entries in `mozare-wiki`'s
  `_proposals/proposals.jsonl`. That backlog is the operator's judgment work
  and the archive's actual rate limiter; no task here touches it.
- Registering any of the 447 artifacts. This change makes their status
  *declared*, not *decided*.
- Building out the export layer, the semantic benchmark, or `08-outputs/`.
  Track D relabels them honestly; it does not implement them.
- Any content, claim, relation or object edit in any instance.

## Release

Kit `1.2.0`. `_originals/` untouched. No runtime dependency added; PyYAML
remains the only requirement.
