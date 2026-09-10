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
2. Characterize the object positively before contrasting it.
3. Separate documentary statement, author confirmation, interpretation, speculation, and machine proposal.
4. Preserve exact project terms and note when terminology changed.
5. Link consequential claims to source or claim records.
6. Record counter-evidence and responsible claim permission.
7. Revise connected indexes and lineages when needed.
8. Run `python scripts/validate_repo.py --full`.
9. Show the exact diff, validation output, and unresolved points.
10. Write a handoff.
