# Changelog — living-wiki-kit

Release history. The registers (`CORPUS_STATE.json`) stay live truth for
counts; this file records what each kit version changed and why.

## 1.3.0 — governance kernel + adaptive semantics

- **Governance kernel port** (from mozare-wiki v1.2.1): fail-closed
  `wiki_validate` gate, `SYSTEM_STATE.json`, accepted-evidence index,
  durable proposal/adjudication records, `sync_intake_registers.py`,
  `repair_truncated_filenames.py`, profile-scoped MCP server
  (`--profile read` default, `capture` for captures/proposals), config-driven
  QMD collection names.
- **Proposal door (W1)**: 17-kind vocabulary enforced as a schema enum with
  pair-wise usage notes; `source_passage` (quote ≥ 20 chars, verbatim in a
  canonical path) required at creation; `evidence_audit.py` and
  `report_holdings.py` read the durable queue (legacy `proposals.jsonl` is
  read-only history). Policy `proposal_schema.json` v1.1.0.
- **Adaptive semantics (O1–O8)**: mandatory object `kind` retired (optional
  deprecated string); open `labels` with mechanical rules; `SEMANTIC_MODEL.md`
  policy (object-before-kind, labels never evidence); labels indexed raw +
  normalized as non-evidence edges with label-match pack reasons; composable
  profiles (6 inactive examples) with `wiki_profiles check`; persona lenses
  (2 examples, foreground-only, accepted-only explicit); candidate object
  projections into disposable index space; legacy-kind compatibility
  indexing, read-only label audit, dry-run migration tool.
- **Staged reconciliation (W3)**: RC-0…RC-4 classes declared first,
  `--mode incremental|full` in both skills, schema-validated class-carrying
  run receipts, escalation to full on loss/>30% drift and to human above
  3 conflicts.
- **Phase 3 acceptance (W4)**: 50 proposals → 30 audited + 20 rejected-audit,
  zero canonical change.
- **Capture breadth (U1)**: URL, photo and file arrivals are first-class governed
  captures — `capture-url` / `capture-photo` plus a provider-neutral
  `SingleFileAdapter` (extracts `.txt/.md/.csv`, *flags* what it will not guess).
  All three modalities emit the same checksummed, deduplicated candidate receipt.
  A URL's own bytes are its content: no fetch, no model call.
- **Benchmark metrics (M2)**: `run-semantic-benchmark.py` now reports
  neighborhood recall@K, human rejection rate and evidence-trace completeness in
  both JSON and markdown, and runs on Windows (a cp1252 decode crash that made
  the 30-case run impossible is fixed). Measured 12/30 against the 3/30 lexical
  baseline (`_audits/2026-10-01--semantic-benchmark/`).
- **Capture schema parity**: the canonical and client capture schemas are pinned
  to one `capture_kind` vocabulary, and the capture test suite is write-isolated
  so a test run never writes into the repository.
- **Machine-wide QMD index, scoped (F10)**: QMD keeps one index per machine,
  shared by every wiki on it. `refresh-search.ps1` ran bare `qmd update` /
  `qmd embed -f` (re-indexing every wiki, and with `-Force` deleting every
  wiki's vectors), unscoped queries ranked other wikis' files, `context_pack`
  queried a hardcoded `wiki` collection that matched nothing, and every
  instance shipped the same `wiki-*` names. New `scripts/qmd_scope.py` keeps
  every QMD call inside the instance's own configured collections, refuses a
  name another wiki already registered, and `instantiate.py` renames
  collections to `<prefix>-*`. `configure-search.ps1` now creates the empty
  content folders a fresh instance lacks instead of failing.
- **Schema-drift fixer (S3b)**: several derivable errors on one file are fixed
  in one pass; derived values YAML would misread are written quoted.
- **Benchmark case sets are instance data (F2)**: both runners take `--config`
  and explain a missing case set in one line.
- Governance invariants unchanged. Adjudication promotes authority; it never
  gates the pipeline or grants visibility.

## 1.2.0 — holdings census gate

A source record carries `status: registered` if and only if the manifest
names it, and every file under `_originals/` carries a declared holdings
tier — so a file can no longer sit uncounted and undeclared. The four entry
pages carry a third labelled marker, `Artifacts held:`, alongside
`Current corpus snapshot:` / `Registered source artifacts:` (the 1.1.0
entry-page freshness gate). `scripts/retier_holdings.py` migrates existing
instances: dry-run default, `--apply` only on a clean tree.

## 1.1.0 — entry-page freshness gate

The four entry pages carry labelled `Current corpus snapshot:` /
`Registered source artifacts:` markers; `validate_repo.py` fails any commit
whose pages lag `CORPUS_STATE.json`. `instantiate.py` seeds the markers and
refuses to reseed a populated instance.
