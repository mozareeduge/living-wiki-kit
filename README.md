# Living Wiki Kit

A starter package for building **living genetic archives** — private,
Git-versioned, Obsidian-readable wikis that preserve sources immutably and
record how works, concepts, claims, and relations change over time, under a
strict evidence-authority governance model.

Extracted and generalized from the operational mozare-wiki system (v1.2.1),
so new wikis can be instantiated in minutes with the same guarantees.

## Start here

1. `SYSTEM_DESIGN.md` — what the system is and why (read first)
2. `INSTANTIATE.md` — create a new wiki from this kit
3. `HOME.md` — the instance entry page (edit per instance)
4. `SETUP_GUIDE_WINDOWS.md` — Windows install: Git, Obsidian, Python, QMD
5. `SEARCH_GUIDE.md` — authority-aware retrieval
6. `GPT_WORKFLOW.md` — using a cloud LLM as content author, safely
7. `CLAUDE.md` / `AGENTS.md` — rules any AI harness inherits

## The one non-negotiable rule

Files under `_originals/` are never edited, renamed, moved, or replaced.
A correction enters as a new artifact. Every artifact is checksummed; the
checksum detects alteration, never truth.

Current corpus snapshot: `wiki-corpus-empty`
Registered source artifacts: 0
Artifacts held: 0

Live truth: `00-system/registers/CORPUS_STATE.json` and
`MATERIALS_INDEX.jsonl` — this page restates register values only as
verified-at-instantiation anchors, refreshed in the same change as the
registers.

## Kit version

`1.3.0` — governance kernel + adaptive semantics. The kernel port (fail-closed
`wiki_validate` gate, `SYSTEM_STATE.json`, accepted-evidence index, durable
proposal/adjudication records, intake sync, profile-scoped MCP server) and the
adaptive semantic layer (open objects with labels instead of a closed kind
enum, composable profiles, persona lenses, candidate projections visible by
default) land in the kit. Proposals validate at the door against a 17-kind
vocabulary with mandatory evidence passages; reconciliation runs staged
(RC-0…RC-4) with class-carrying receipts. See `CHANGELOG.md` for the full
release history.

## The authority rule

Everything an AI produces is candidate material. Fluency never upgrades it.
Retrieval scores organize attention; they are never evidence. Content changes
reach the wiki only through a reviewed, validated, human-approved path.

## Validate

```bash
python scripts/validate_repo.py --full
python scripts/validate_content_release.py   # once the wiki layer is populated
```

## License / reuse

Personal research instrument of Mohammad Zare, extracted for reuse. If you
instantiate a wiki from this kit, keep the governance invariants
(`SYSTEM_DESIGN.md` §5) intact — they are the system.
