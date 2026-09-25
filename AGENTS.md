# AGENTS.md — Living Wiki Kit (governed agent surface)

This repository (and every wiki instantiated from it) is a living genetic
archive governed by an authority hierarchy. Any AI harness — Claude Code,
Codex, OpenCode, Hermes, MCP clients, or anything else — inherits the rules
below by reading this file. They mirror `CLAUDE.md` and `SYSTEM_DESIGN.md`;
those remain canonical.

## Non-negotiables

1. `_originals/` is immutable. Never edit, overwrite, move, rename, or delete
   anything under it. No exception.
2. Everything you (the model) produce is **candidate-tier material
   (authority level 7)**. Fluency, plausibility, or agreement never upgrades
   it. Only human adjudication or evidence recorded in canonical records does.
3. Retrieval scores (qmd or any search layer) organize attention; they are
   **never evidence**.
4. Do not write into `00-system/`, `01-inbox/`, `02-sources/`, `03-objects/`,
   `04-notes/`, `05-claims/`, `06-relations/`, `07-genesis/`, or `_originals/`.
5. Content changes travel only through approved patch manifests
   (`PATCH_MANIFEST.json`) or the proposal queue
   (`_proposals/proposals.jsonl`); do not broaden their scope.

## What you MAY do without further permission

- **Read** any file in the repository.
- **Search** via qmd (`qmd search`, deterministic BM25) for orientation.
- **Context**: MCP tool `wiki_context_pack` (seed record id) returns a
  read-only neighbourhood pack (<= 30 records, <= 16k tokens, a reason per
  record). Needs `_search/graph.db` from `python scripts/build_graph_index.py`.
  A navigation aid, never evidence.
- **Propose**: append a JSONL record to `_proposals/proposals.jsonl`
  (`{id, received, kind, authority_tier: "candidate", status: "new", body}`),
  or use MCP tool `wiki_propose` (server: `scripts/wiki_mcp_server.py`).
  Proposals are inert until a human moves them. That is the design.

## Machine contract

- **MCP server:** `scripts/wiki_mcp_server.py` (stdio JSON-RPC). Each machine
  registers its own interpreter path in its local harness config; never
  commit machine-specific interpreter paths.
- **Validation gates:** `python scripts/validate_repo.py [--full]` and
  (once populated) `python scripts/validate_content_release.py`.
  Deterministic; no network, no model calls.
- **Pre-commit gate (once per clone):** `git config core.hooksPath .githooks`.
  `git commit` then refuses any commit introducing a validator error not
  already listed in `.githooks/known-baseline-errors.txt`. To defer a
  genuinely new issue, add its exact line there in its own reviewed commit
  with a reason; never edit that file just to get a commit through.
- **CI:** `.github/workflows/validate.yml` runs the same baseline gate on
  every push/PR to main, so local pass and CI pass mean the same thing.

## Harness operation map

- **Claude Code** — loads `CLAUDE.md`; side-effect workflows live in
  `.claude/skills/wiki-*/SKILL.md` (invoke manually; never start them from a
  vague prompt).
- **Codex / OpenCode / other AGENTS.md readers** — read
  `.claude/skills/wiki-*/SKILL.md` directly and follow them; they are
  harness-neutral.
- **Hermes (desktop)** — carries a mirrored operator skill; this file
  remains canonical if they diverge.
- **ChatGPT (GitHub connector)** — read-only; changes reach the archive only
  as a bounded patch package (GPT_WORKFLOW.md) applied locally.
- **All write paths converge the same way:** branch → bounded change or
  PATCH_MANIFEST.json → `python scripts/validate_repo.py --full` green →
  reviewable diff → merge to `main` → CI green.

## Shared-register serialization

`00-system/registers/MATERIALS_INDEX.jsonl` and `CORPUS_STATE.json` are
single monolithic files with a snapshot hash over the whole manifest. Two
branches touching them at once will conflict. Before starting a task that
changes the source count, check for another open branch/PR doing the same
and land it first.

## Reading order for newcomers

1. `SYSTEM_DESIGN.md` (record grammar + authority hierarchy)
2. `CLAUDE.md` (operating rules)
3. This file
4. `HOME.md` (entry page)
5. `RUNBOOK_WEB_CAPTURE.md` (citing live web sources into checksummed derivatives)
