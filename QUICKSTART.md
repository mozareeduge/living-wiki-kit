# Quickstart — living-wiki-kit

From empty kit to first validated intake in about ten minutes. Full detail
in `INSTANTIATE.md` (instances), `SETUP_GUIDE_WINDOWS.md` (Windows), and
`SEARCH_GUIDE.md` (retrieval).

## 1. Create your wiki

```bash
cp -r living-wiki-kit/ my-wiki/ && cd my-wiki/
rm -rf .git && git init && git config core.hooksPath .githooks
python scripts/instantiate.py --name "My Wiki" --prefix pmw
python scripts/validate_repo.py --full   # must PASS
git add -A && git commit -m "bootstrap: instantiate My Wiki"
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

## 5. Propose, don't edit (agents)

All AI output is candidate-tier. File proposals through the MCP `capture`
profile (`wiki_propose`); each needs a resolvable evidence passage.
Adjudication is yours: it promotes authority, never grants visibility —
candidates stay visible and marked until you decide.
