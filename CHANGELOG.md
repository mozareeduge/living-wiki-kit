# Changelog — living-wiki-kit

Release history. The registers (`CORPUS_STATE.json`) stay live truth for
counts; this file records what each kit version changed and why.

## 1.5.0 — files in, exact passages out, from any device

- **Add a file and keep it exact.** Give the wiki a PDF, Word, PowerPoint,
  Excel, HTML, EPUB, text or Markdown file (`scripts/ingest_file.py`, or the
  `wiki_ingest_file` tool). The original bytes are kept unchanged with their
  fingerprint, a pending source record is created for you to review, and the
  text is extracted. Adding the same file twice does nothing new. Scanned
  PDFs are marked `needs-ocr`; nothing guesses their text.
- **Ask a question, get the exact passage.** `wiki_retrieve` (and
  `scripts/retrieval/retrieve.py`) returns passages ("chunks") from your
  sources, each with where it comes from, its exact position in the text,
  its authority level and why it was returned. Canonical records and
  captures come back as separate groups, never one mixed ranking. Answers
  stay inside a size budget without cutting a passage in half. Persian works,
  and your label aliases find passages too.
- **Open one source or one passage.** `wiki_artifact_read` shows a source
  page by page, or one passage with the ones before and after it. If the
  source text changed since you got a reference, it says so
  (`E_STALE_SOURCE`) instead of showing you a different passage.
- **Cite a passage in a proposal.** Proposals can point at a passage
  (`chk:` reference); the quote must be found word for word in its current
  text.
- **Model notes beside the archive, never inside it.** A model can add a
  summary, topics, people, places and links to a source
  (`wiki_enrichment_submit`; `wiki_enrichment_pending` lists what still
  needs notes). The notes live in a separate store, are always candidate
  material, and each quote they use must exist in the source. Search can
  find a passage through a note, but labels the hit "non-evidence" and still
  shows the passage's own text, never the note. A source shows how much of
  it has notes. Notes made for an old version of a source are ignored.
- **Retries are safe.** Capture and ingest accept a `request_id`; sending the
  same request again returns the first receipt instead of writing twice.
  Receipts also say whether the change is committed to Git yet.
- **Honest status.** A new, empty wiki no longer reports a "stale index".
  Status reads `empty`, `fresh`, `stale` or `missing`.
- **Run it as a server (local first).** The MCP server now also speaks
  HTTP (`--transport http`, `/mcp`, `/healthz`) besides the usual stdio,
  with the same tools. An upload page (`/upload`) gives a one-time code for
  `wiki_ingest_file`. `RUNBOOK_REMOTE_SERVER.md` explains a cloud machine
  behind a tunnel, with a scripted check.
- **Not yet: sign-in for remote writing.** Over HTTP the server is
  read-only by default and refuses every write tool (`E_AUTH_REQUIRED`).
  Writing and uploading over HTTP work only on the same machine
  (`--profile capture --insecure-local-only`, 127.0.0.1 only). Sign-in for
  phones and other devices waits on an owner decision and ships later.
- The fresh-wiki release check now also adds a file, finds it, adds a note
  and checks coverage. Three tests that only checked the shape of new code
  were moved to `07-genesis/test-archive/2026-11-12--om-862/`.

## 1.4.0 — perspectives complete, independent kit

- **No trace of personal wikis.** Instance benchmark reports removed;
  history kept with neutral names; a guard test scans every tracked file.
  Author-confirmation authority is an explicit `author_actors` setting in
  `evidence-sources.json` instead of a name built into the kernel.
- **Profiles at setup.** `instantiate.py --profile <id>` (repeatable).
- **Stricter profiles.** `tighten: [object-labels, relation-type,
  record-visibility]`, enforced by `wiki_profiles.py check`; nothing can
  loosen a rule. No new example profiles (owner decision).
- **Label aliases.** Optional `LABEL_ALIASES.json`; search reaches records
  through an alias and says so; never rewrites or merges.
- The pre-commit gate is executable on macOS/Linux; tests close every
  database handle.

- **Independent project.** The kit no longer names or depends on the archive
  it was extracted from: the MCP server is `wiki-governance`, schemas carry
  the kit's own names, and object/claim ids accept any instance prefix. A
  guard test keeps it that way.
- **Lenses highlight relationships and sections (O9).** Relations may name
  their language in an optional `relation_type`; a lens listing it adds a
  visible reason to the relation and every record it joins. Section
  foregrounding sets reading order only. Membership and authority unchanged.
- **Profiles steer attention (O10).** Active profiles' seed labels add a
  reason naming the profile; their suggested lenses are offered, never
  applied. No active profile, no change.
- **Six practices proven (O11).** Research, creative, product discovery,
  investigation, experimental and a Persian community archive each run on
  the unchanged kernel. Four example lenses added so every profile's
  suggested lens exists.
- **Graph fix (F19).** Relations that name participants by id (`mw-obj-…`,
  `smk-rel-…`) now join them in the graph; before, only links did.
- **New-wiki setup (Q1–Q3).** Your prefix everywhere (incl. repair patch
  ids), a review-first first commit, a complete script catalogue, and a
  Windows setup script that works on a fresh clone.
- **Fresh-wiki release check in CI (Q6).** `scripts/release_smoke.py`
  creates a wiki from each commit and runs every gate in it.
- Docs say what exists: profiles cannot weaken kernel rules and tightening
  is not implemented yet.

## 1.3.0 — governance kernel + adaptive semantics

- **Governance kernel port** (from source-instance v1.2.1): fail-closed
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
