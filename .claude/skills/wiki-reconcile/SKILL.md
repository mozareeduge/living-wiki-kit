---
name: wiki-reconcile
description: Run the manifest-accounted full-corpus reconciliation required before accepted corpus-wide changes. Has side effects and must be invoked manually.
disable-model-invocation: true
---

# Full-Corpus Reconciliation

Current baseline: 94 artifacts, snapshot `ref-corpus-a33b260403015901`.

## Completion criterion

The run is complete only when every manifest row appears in exactly one batch receipt or named exception. Semantic search, prior summaries, and the materials index do not count as rereading.

## Procedure

1. Validate the current manifest and checksums.
2. Freeze the expected manifest in `_audits/<run-id>/expected.jsonl`.
3. Divide source records and derivatives into batches small enough for isolated contexts. Use 8–12 artifacts per batch unless a single artifact is unusually large.
4. Delegate each batch to the `corpus-reader` subagent.
5. Each receipt must contain:
   - every source ID and path read;
   - relevant objects, terms, versions, relations, claims, and system effects;
   - contradictions or corrections;
   - what remained unchanged;
   - extraction/access limits;
   - candidate updates;
   - no prose presented as verified beyond its evidence.
6. Use `evidence-auditor` on claims or external facts that would be strengthened, weakened, or exported.
7. Merge receipts into one impact matrix covering:
   - sources and versions;
   - works and projects;
   - chronology;
   - terminology;
   - relations and claims;
   - public/official texts;
   - system architecture;
   - indexes and search.
8. Compare receipt IDs against the expected manifest. Stop on any gap or duplicate coverage.
9. Propose changes. Do not apply them until the user approves the impact report, unless the user explicitly authorized direct implementation.
10. After approved changes, run full validation, rebuild QMD, and create a reconciliation event and handoff.
