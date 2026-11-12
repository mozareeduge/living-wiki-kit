# Quickstart — living-wiki-kit

From empty kit to first validated intake in about ten minutes. Full detail
in `INSTANTIATE.md` (instances), `SETUP_GUIDE_WINDOWS.md` (Windows), and
`SEARCH_GUIDE.md` (retrieval).

## 1. Create your wiki

```bash
cp -r living-wiki-kit/ my-wiki/ && cd my-wiki/
rm -rf .git && git init && git config core.hooksPath .githooks
python scripts/instantiate.py --name "My Wiki" --prefix pmw   # optional: --profile practice-research
python scripts/validate_repo.py --full   # must PASS
git status --short                      # review: kit files + what instantiate wrote, nothing else
git add -- . && git commit -m "bootstrap: instantiate My Wiki"
```

## 2. Run the governance gates

```bash
python scripts/wiki_validate.py --format json
python scripts/wiki_state.py --repo . check
python scripts/wiki_evidence.py --repo . check
python scripts/wiki_profiles.py check
```

All four must exit 0 before any content work is reported done.

## 3. Optional local search

```powershell
powershell -ExecutionPolicy Bypass -File scripts/configure-search.ps1
powershell -ExecutionPolicy Bypass -File scripts/refresh-search.ps1
python scripts/build_graph_index.py
```

## 4. First intake

1. Drop files in `01-inbox/`.
2. Follow `.claude/skills/wiki-intake/SKILL.md` (manually invoked, step by
   step — it stops for your review before any commit).
3. Refresh the three entry-page markers from the registers in the same
   change; the pre-commit hook enforces it.

## 5. Add a file and ask about it (1.5.0)

```bash
python scripts/ingest_file.py path/to/play.pdf --title "Play, draft 2" --json
python scripts/retrieval/retrieve.py "rehearsal"          # exact passages, with where they come from
python scripts/retrieval/retrieve.py --artifact <source_ref from the receipt>
```

The original file is kept unchanged; a pending source record waits for your
review. Each answer is a passage from your sources, with its place in the
text and why it was returned. Model notes (`wiki_enrichment_*` tools) can
help search, but such hits are marked non-evidence.

## 6. Use it from another program or device

```bash
python scripts/wiki_mcp_server.py                         # stdio, as before
python scripts/wiki_mcp_server.py --transport http        # http://127.0.0.1:8787/mcp, read-only
python scripts/wiki_mcp_server.py --transport http --profile capture --insecure-local-only
                                                          # this machine only: writes + /upload page
```

Over HTTP, write tools stay refused until sign-in exists (planned; not in
1.5.0). For a cloud machine behind a tunnel, follow
`RUNBOOK_REMOTE_SERVER.md` — read-only until then.

## 7. Propose, don't edit (agents)

All AI output is candidate-tier. File proposals through the MCP `capture`
profile (`wiki_propose`); each needs a resolvable evidence passage — a
passage reference (`chk:`) from `wiki_retrieve` works too.
Adjudication is yours: it promotes authority, never grants visibility —
candidates stay visible and marked until you decide.
