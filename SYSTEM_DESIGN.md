---
id: kit-system-design
type: system-document
title: "Living Wiki Kit — Operational System Design"
system_version: "1.2.0"
schema_version: "1.0.0"
status: operational-release
created: 2026-09-10
updated: 2026-09-10
source_of_truth: true
---

# Living Wiki Kit — A Starter System for Living Genetic Archives

## 1. What this kit is

This repository is a **generalized extraction** of the mozare-wiki operational
system: a private, Git-versioned, Obsidian-readable archive pattern that
preserves not only current statements but *how works, concepts, claims, and
directions changed* — a "living genetic archive."

It ships everything needed to start a **new wiki instance** for any subject:

- the numbered record-layer layout (`00-system` … `09-indexes`, `_originals`);
- record templates (source-record, object, relation-object, claim-object,
  succession-record, handoff);
- deterministic validators (structure, checksums, manifest, links, content
  release) plus a cross-tool pre-commit/CI gate;
- agent operating rules and manual-invocation skills (search, intake,
  reconcile, write, validate, handoff, voice capture);
- a governed multimodal capture core (text/audio/image → checksummed,
  deduplicated, noncanonical capture records);
- interchange export scripts (PROV-O JSON-LD, SKOS, TEI skeleton) and a
  public export tool that never writes inside the repo — shipped and
  available, not yet exercised against a populated instance (see §6 for
  the per-script status);
- an MCP server exposing read / search / propose to any AI harness;
- a controlled vocabulary so status words mean the same thing everywhere.

**This repo is not itself a populated wiki.** It is the empty, validated
instrument. Instances made from it hold the content.

Current corpus snapshot: `wiki-corpus-empty`
Registered source artifacts: 0
Artifacts held: 0

Live truth: `00-system/registers/CORPUS_STATE.json` and
`MATERIALS_INDEX.jsonl`; entry-level summaries (README/HOME/CLAUDE) are
pointer-true restatements refreshed in the same change as the registers.

## 2. The core idea (carry this, not the tooling)

1. **Preservation contract.** What arrives is frozen. `_originals/` is
   immutable; every artifact is identified by SHA-256; corrections enter as
   new artifacts, never edits.
2. **Authority hierarchy (8 levels).** Immutable original → verified external
   primary → author confirmation → accepted canonical record → derived
   witness → interpretive synthesis → candidate/AI material → generated view.
   Everything a model produces is level 7. Fluency never upgrades evidence;
   only human adjudication or recorded evidence does.
3. **Record grammar.** Markdown + YAML frontmatter. Source records prove
   provenance; objects persist across profiles; relations are recorded
   *before* they are classified ("relation before type"); claims carry
   explicit permission (`may-note` … `blocked`); residue records why a route
   stopped.
4. **Search is a route, never evidence.** Canonical page → claim/relation →
   source record → derivative → original. A retrieval score organizes
   attention; it proves nothing.
5. **Convergence of write paths.** All changes travel: branch → bounded
   change or patch manifest → validator green → reviewable diff → merge → CI
   green. Conversational edits never modify the wiki.

`source_material_count` (rows registered in `MATERIALS_INDEX.jsonl`) and
`held_artifact_count` (files present under `_originals/`) are two different
counts and are not interchangeable — a held artifact need not yet be
registered.

## 3. Repository layout

```text
/
├── README.md  HOME.md  SYSTEM_DESIGN.md  SETUP_GUIDE_WINDOWS.md
├── SEARCH_GUIDE.md  GPT_WORKFLOW.md  CLAUDE.md  AGENTS.md
├── RUNBOOK_WEB_CAPTURE.md
├── .mcp.json  .claude/  .githooks/  .github/workflows/
├── 00-system/          governance: policies, schemas, templates, registers
├── 01-inbox/           raw arrivals (incl. governed captures/)
├── 02-sources/         records/ (provenance) + text/ (derivatives)
├── 03-objects/         works, projects, people, institutions, concepts,
│                       methods, collections, references
├── 04-notes/           research notes
├── 05-claims/          claim-objects with permission levels
├── 06-relations/       relation-objects (before classification)
├── 07-genesis/         lineages, events, handoffs
├── 08-outputs/         public-facing exports (review-gated)
├── 09-indexes/         navigation, Bases, dashboards
├── _originals/         immutable originals (committed)
├── _proposals/         AI proposal queue — inert until human moves it
├── _audits/ _exports/  audit reports; interchange output (git-ignored)
├── _search/            rebuildable local index (git-ignored)
└── scripts/            validators, capture core, MCP, exports, benchmarks
```

## 4. Instantiating a new wiki

See `INSTANTIATE.md` for the full checklist. Summary:

1. Clone this kit, rename the folder, `git init` (or use the template repo).
2. Run `python scripts/instantiate.py --name <wiki-name> --prefix <pfx>`.
   This rewrites the record-ID prefix (`mw-` → your prefix), renames the
   corpus state id pattern, and stamps instance metadata.
3. Register the three immutable decisions: prefix, corpus-state id, and the
   authority hierarchy wording (you may tighten it, never loosen it).
4. Validate, commit, push to a **private** remote.

## 5. Governance invariants (unchanged from the source system)

- `_originals/` is immutable. No exception, no tool privilege.
- Model output is always candidate-tier. Proposals land in
  `_proposals/proposals.jsonl` and stay inert until a human moves them.
- Search scores organize attention; they are never evidence.
- Work on branches (`intake/`, `wiki/`, `system/`, `audit/`, `output/`,
  `migration/`); no force-push; no `--no-verify`; no credentials.
- Before claiming success: `python scripts/validate_repo.py --full` (+ the
  content validator once populated) and show the decisive output.
- End consequential work with a handoff in `07-genesis/handoffs/`.
- `main` is the last accepted state. Static pass ≠ local operational pass.

## 6. What each script does

| Script | Role | Status |
|---|---|---|
| `validate_repo.py` | structure, frontmatter identity, dup IDs, manifest/state, SHA-256 of originals, wikilinks, entry-page freshness gate (labelled snapshot/count markers + layer-count agreement on HOME/README/SYSTEM_DESIGN/CLAUDE vs the registers and record directories), holdings census helper (`held_artifact_count` / `holdings_by_tier` in `CORPUS_STATE.json` against `_originals/` and `HOLDINGS_POLICY.json`, enforced in `validate()`), mojibake guard on every source record, register refresh-policy gate | operational |
| `validate_content_release.py` | populated-layer gate: minimum counts, claim fields, orphan records, Base YAML, benchmark | operational |
| `check_against_baseline.py` | shared local-hook/CI gate: fail only on NEW errors vs `.githooks/known-baseline-errors.txt` | operational |
| `instantiate.py` | stamps a new instance from the kit: record-ID prefix, corpus-state id, the three entry markers; refuses to reseed a populated instance | operational |
| `report_holdings.py` | read-only 7-section census audit (counts, contradictions, proposals, claims, register staleness, mojibake, verdict); prints `CENSUS CLEAN` or `CENSUS DRIFT`; writes only to `_audits/runtime/` | operational |
| `retier_holdings.py` | migration tool for adopting the census: dry-run by default, `--apply` only on a clean tree and refuses on manifest/state disagreement | operational |
| `build_graph_index.py` | deterministic graph index (nodes, edges, resolved aliases) over frontmatter, wikilinks and relation participants into `_search/graph.db` — disposable, rebuildable | operational |
| `context_pack.py` | governed context packer (CLI, also served read-only as the MCP tool `wiki_context_pack`): lexical hits plus graph neighbourhood into ≤ 30 records / ≤ 16k tokens, each with a selection reason; no model in retrieval | operational |
| `reconcile_runner.py` | incremental-reconciliation core: full vs incremental plan (escalates on loss or > 30% drift), exact-once verify, human gate above 3 conflicts; not yet called by the reconcile skills | available (unexercised) |
| `evidence_audit.py` | candidate-layer audit against `proposal_schema.json`: a proposal whose `source_passage` cannot be verified is reported `rejected-audit`; never edits the queue | operational |
| `schema_drift_fixer.py` | derives path-derivable frontmatter fixes (filename, type/kind) as a `PATCH_MANIFEST`; leaves semantic fields for human adjudication | operational |
| `wiki_capture.py` (+ `capture/`) | governed multimodal capture: hash, dedupe, atomic store, state machine | operational |
| `wiki_mcp_server.py` | MCP: `wiki_read`, `wiki_search` (hybrid `qmd query`, lexical fallback), `wiki_exact` (deterministic text match), `wiki_context_pack` (read-only governed neighbourhood pack), `wiki_propose`, plus the capture tools — writes go only to `_proposals/` and the governed capture store | operational |
| `export_interchange.py` | PROV-O JSON-LD, SKOS, TEI skeletons — derived views, never the record | available (unexercised) |
| `export_public.py` | sensitivity-reviewed public export OUTSIDE the repo | available (unexercised) |
| `run-semantic-benchmark.py` | QMD retrieval benchmark against an expected-path set (deterministic `--no-rerank`); baseline 3/30 lexical-only recorded in `mozare-wiki` 2026-09-20 | operational |
| `run_faithfulness_benchmark.py` | faithfulness evaluation loop: answer from retrieved records, then entailment-check each claim against the sources | available (unexercised) |
| `file-to-md/to_md.py` | converts pdf/docx/pptx/xlsx/html/epub to clean md with a provenance header — the derivative-extraction step of intake; OCR routing rules in `.claude/skills/wiki-file-to-md/SKILL.md` | operational |
| `check_research_spans.py` | citation-span audit over an external research quarantine | available (unexercised) |
| `create-backup.ps1` | Windows helper: zip backup of the repo to `_wiki_backups/` | operational |
| `configure-search.ps1` / `refresh-search.ps1` / `search-wiki.ps1` / `verify-install.ps1` | Windows helpers: QMD config/refresh, verify-install, search wrapper | available (unexercised) |

The capture core, MCP server, and validators are instance-agnostic: IDs use
the instance prefix set by `instantiate.py`.

## 7. Closing rule

The archive must remain readable without Obsidian, searchable without one AI
provider, recoverable without chat history, and inspectable without trusting
a generated summary. Its procedures serve the works and sources; the works do
not exist to satisfy the procedures.
