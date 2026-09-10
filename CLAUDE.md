# Living Wiki Kit

This repository is a living genetic archive instrument, not an ordinary
software codebase. These rules apply to every Claude Code session here and
to every wiki instantiated from this kit.

## Always-on rules

1. Treat `_originals/` as immutable. Never edit, overwrite, move, rename, or
   delete an existing original.
2. Read `SYSTEM_DESIGN.md` before changing records, schemas, workflows,
   search, or agent configuration.
3. Distinguish original artifact, source record, derivative, canonical
   object, relation, claim, event, lineage, residue, index, and search result.
4. Do not upgrade evidence because language is fluent, repeated, similar, or
   AI-generated.
5. Use QMD collections according to authority: canonical collections first
   for an interpretive question; source-records collection for provenance;
   derivatives collection for candidate passages; original files for exact
   form.
6. QMD scores organize attention and are never evidence.
7. Side-effect workflows are manually invoked: `/wiki-intake`,
   `/wiki-reconcile`, `/wiki-write`, `/wiki-validate`, `/wiki-handoff`.
8. Apply a supplied content change only through its `PATCH_MANIFEST.json`.
   Do not broaden its scope.
9. Work on a branch. Do not force-push. Do not commit credentials, models,
   caches, local indexes, backups, or machine-specific paths.
10. Before claiming success, show exact commands and decisive results. At
    minimum run:
    - `python scripts/validate_repo.py --full`
    - `python scripts/validate_content_release.py` (once populated)
11. End consequential work with a handoff containing changed files,
    decisions, validation output, unresolved findings, negative constraints,
    and the next exact operation.

## Context discipline

- Keep the main session bounded.
- Use a subagent only for an exact file set or verification task.
- Preserve a handoff before restart, compaction, or context change.
- Do not load all derivatives into one context.
- Report an intellectual concern instead of silently rewriting
  another-author content.

## Current state

- kit version: `1.0.0`
- source artifacts: `0` (empty kit — instance registries start empty)
- entry page: `HOME.md`
- instantiation guide: `INSTANTIATE.md`
