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
4. The default agent/MCP profile is **read-only**. Do not write into governed
   canonical/system/source zones or `_originals/`. The explicit `capture` MCP
   profile may create noncanonical captures and durable proposals only; it does
   not grant canonical-write authority.
5. Content changes travel only through approved patch manifests
   (`PATCH_MANIFEST.json`) or accepted durable proposal/adjudication records;
   do not broaden their scope.

## Roles (authority comes from the role and its evidence, never from the model)

- **OWNER** — decides vocabulary, adjudications, releases; the only authority
  that promotes candidate material.
- **RESEARCH_SYNTHESIS_AGENT** — drafts candidate synthesis from accepted
  evidence; never self-accepts.
- **REPOSITORY_OPERATOR** — runs intake, gates, and merges; follows the skills
  exactly and stops on gate failure.
- **INDEPENDENT_REVIEWER** — verifies a rung from a fresh context against
  pasted evidence; model or vendor identity confers no authority.
- **RETRIEVAL_CLIENT** — read-only consumer of search and context packs.
- **CAPTURE_CLIENT** — may create noncanonical captures and proposals through
  the `capture` profile only.

## What you MAY do without further permission

- **Read** any file in the repository.
- **Search** via qmd (`qmd search`, deterministic BM25) for orientation.
- **Context**: MCP tool `wiki_context_pack` (seed record id) returns a
  read-only neighbourhood pack (<= 30 records, <= 16k tokens, a reason per
  record). Needs `_search/graph.db` from `python scripts/build_graph_index.py`.
  A navigation aid, never evidence.
- **Propose** through the explicit MCP `capture` profile. `wiki_propose` and
  `wiki_propose_from_capture` create immutable durable proposal records under
  `_proposals/records/`; adjudications are separate immutable records under
  `_proposals/adjudications/`. Proposals are candidate-tier and inert until
  accepted by an authorized adjudicator. Do not append new proposals to the
  legacy `_proposals/proposals.jsonl` runtime log (read-only history).

## Machine contract

- **MCP server:** `scripts/wiki_mcp_server.py` (stdio JSON-RPC). `.mcp.json`
  registers it in the safe default `--profile read`. Enable
  `--profile capture` only for a task that explicitly requires noncanonical
  capture/proposal writes. No profile exposes canonical writes. Each machine
  registers its own interpreter path in its local harness config; never
  commit machine-specific interpreter paths.
- **Authoritative governance gate:** `python scripts/wiki_validate.py --format json`
  followed by `python scripts/wiki_state.py --repo . check`. Raw
  validators (`validate_repo.py`, `validate_content_release.py`) remain
  diagnostic tools; they are not a replacement for this gate.
- **Intake (new files or held `pending-registration` items):** follow
  `.claude/skills/wiki-intake/SKILL.md` step by step; it is plain Markdown and
  harness-neutral. After registering, run `python scripts/wiki_state.py --repo . rebuild`
  then `python scripts/sync_intake_registers.py --accept-corpus-change --apply`.
- **Pre-commit gate (once per clone):** `git config core.hooksPath .githooks`.
  `git commit` then refuses any commit introducing a validator error not
  already listed in `.githooks/known-baseline-errors.txt`. To defer a
  genuinely new issue, add its exact line there in its own reviewed commit
  with a reason; never edit that file just to get a commit through.
- **CI:** `.github/workflows/validate.yml` runs the kernel gates plus the full
  suite (`tests`, `scripts/tests`, `scripts/capture/tests`) on every push/PR,
  so local pass and CI pass mean the same thing.

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
- **All write paths converge the same way:** branch → bounded change /
  PATCH_MANIFEST.json / durable proposal adjudication → `python scripts/wiki_validate.py --format json` →
  `python scripts/wiki_state.py --repo . check` → reviewable diff → merge to `main` → CI green. A candidate never promotes
  itself to authority.

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
