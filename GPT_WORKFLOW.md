# GPT Workflow (Cloud-LLM Content Authoring)

How to use a cloud LLM (GPT, Claude, Gemini — any conversation-capable model)
as content author for this archive without breaking governance.

## 1. Division of labour

**Cloud LLM (content author):** whole-corpus rereading and reconciliation;
substantial writing and revision; relation, claim, lineage decisions;
external web verification; content audits; patch manifests with acceptance
tests.

**Local operator (Claude Code / Codex / Hermes / human):** local inspection;
exact patch application; diff review; validation; search configuration; Git
branches, commits, pushes, CI; local handoffs.

The local operator does not reread the full corpus or rewrite an
author-authored patch — it applies, validates, and reports.

## 2. Read-only repository access

ChatGPT's GitHub connection is remote and read-only. It follows the authority
order through file paths: canonical page → source record → derivative →
original. It does not call local QMD.

## 3. A conversational answer never modifies the wiki

For a consequential change, the cloud author delivers a bounded patch:

```text
PATCH_MANIFEST.json
CONTENT_REPORT.md
ACCEPTANCE_TESTS.md
CLAUDE_APPLICATION_PROMPT.md
files/<repository-relative paths>
```

The manifest states: base commit; files to create/replace; source records
and originals used; protected paths; expected counts and links; validation
commands; semantic questions; rollback.

The local operator applies the patch and returns the local diff and tests.
The author then accepts, issues a corrective micro-patch, or revises.

## 4. New source intake

1. Place the file in `01-inbox/`.
2. The local operator preserves and registers it through `/wiki-intake`.
3. The cloud author receives the artifact, current register, corpus snapshot.
4. The cloud author rereads the complete registered corpus (full-corpus
   gate) before corpus-wide changes.
5. A reviewed intake/reconciliation patch updates source memory, canonical
   records, relations, claims, indexes, and system design where justified.

Semantic search and old summaries cannot substitute for the complete-corpus
gate.

## 5. Writing governance

A wiki page should: characterize its object before contrast; articulate
relations rather than list terms; ground abstraction in material, mechanism,
or procedure; distinguish evidence from interpretation and proposal; preserve
older formulations when vocabulary changes; state what it cannot yet claim.

## 6. Future work enters as

new intake · verification · focused research · content correction · system
migration · public output — never as another general completion loop.
