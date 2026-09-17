---
id: kit-system-design
type: system-document
title: "Living Wiki Kit — Operational System Design"
system_version: "1.1.0"
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
- interchange exports (PROV-O JSON-LD, SKOS, TEI skeleton) and a public
  export tool that never writes inside the repo;
- an MCP server exposing read / search / propose to any AI harness;
- a controlled vocabulary so status words mean the same thing everywhere.

**This repo is not itself a populated wiki.** It is the empty, validated
instrument. Instances made from it hold the content.

Current corpus snapshot: `wiki-corpus-empty`
Registered source artifacts: 0

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

| Script | Role |
|---|---|
| `validate_repo.py` | structure, frontmatter identity, dup IDs, manifest/state, SHA-256 of originals, wikilinks, entry-page freshness gate (labelled snapshot/count markers + layer-count agreement on HOME/README/SYSTEM_DESIGN/CLAUDE vs the registers and record directories) |
| `validate_content_release.py` | populated-layer gate: minimum counts, claim fields, orphan records, Base YAML, benchmark |
| `check_against_baseline.py` | shared local-hook/CI gate: fail only on NEW errors vs `.githooks/known-baseline-errors.txt` |
| `wiki_capture.py` (+ `capture/`) | governed multimodal capture: hash, dedupe, atomic store, state machine |
| `wiki_mcp_server.py` | MCP: `wiki_read`, `wiki_search`, `wiki_propose` — writes go only to `_proposals/` |
| `export_interchange.py` | PROV-O JSON-LD, SKOS, TEI skeletons — derived views, never the record |
| `export_public.py` | sensitivity-reviewed public export OUTSIDE the repo |
| `run-semantic-benchmark.py` | QMD retrieval benchmark against an expected-path set
| `file-to-md/to_md.py` | converts pdf/docx/pptx/xlsx/html/epub to clean md with a provenance header — the derivative-extraction step of intake; OCR routing rules in `.claude/skills/wiki-file-to-md/SKILL.md` |
| `check_research_spans.py` | citation-span audit over an external research quarantine |
| `*.ps1` | Windows helpers: QMD config/refresh, backup, verify-install, search wrapper |

The capture core, MCP server, and validators are instance-agnostic: IDs use
the instance prefix set by `instantiate.py`.

## 7. Closing rule

The archive must remain readable without Obsidian, searchable without one AI
provider, recoverable without chat history, and inspectable without trusting
a generated summary. Its procedures serve the works and sources; the works do
not exist to satisfy the procedures.
