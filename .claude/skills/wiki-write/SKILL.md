---
name: wiki-write
description: Create or revise canonical wiki pages from approved evidence and an explicit change plan. Has side effects and must be invoked manually.
disable-model-invocation: true
---

# Wiki Write

## Preconditions

- The target, genre, audience, and authority level are explicit.
- Load-bearing sources have been opened.
- A corpus-wide change has a completed reconciliation report.
- The user has approved ambiguous biographical, artistic, strategic, or interpretive decisions.

## Procedure

1. Read the Adaptive Writing Protocol and the relevant source records.
2. Characterize the object positively before contrasting it — and
   characterize before labeling: decide whether a persistent identity is
   useful, describe it in ordinary language, link evidence, and only then
   add a small number of minimum useful labels (each must earn its place
   for retrieval, grouping, navigation, or understanding; never label every
   noun, never invent a category just because a field seems to expect one).
3. Separate documentary statement, author confirmation, interpretation, speculation, and machine proposal.
4. Preserve exact project terms and note when terminology changed.
5. Link consequential claims to source or claim records.
6. Record counter-evidence and responsible claim permission.
7. Put roles in relations when context matters (a person may be professor,
   translator, director in different contexts — that statement belongs in a
   relation with sources, not in a label); never merge object identities
   from matching labels, similar titles, or close embeddings — identity
   reconciliation requires evidence.
8. Revise connected indexes and lineages when needed.
8. Run `python scripts/validate_repo.py --full`.
9. Show the exact diff, validation output, and unresolved points.
10. Write a handoff.
