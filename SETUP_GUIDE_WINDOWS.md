# Setup Guide (Windows)

Takes a new wiki instance from this kit to a working state: Git + GitHub,
Obsidian, Python validators, optional QMD semantic search, and the
governance gates. Follow phases in order; do not skip a pass condition.

## 0. Prerequisites check

```powershell
git --version          # Git for Windows
python --version       # 3.11+ on PATH as "python"
obsidian --version     # or just confirm Obsidian is installed
```

Missing? `winget install --id Git.Git -e`, install Python from python.org
(check "Add to PATH"), install Obsidian from obsidian.md.

## 1. Get the instance

```powershell
# if instantiated from the kit folder:
cd C:\path\to\my-wiki
git config core.hooksPath .githooks
python -m pip install -r requirements.txt
```

## 2. Validate the empty instance

```powershell
python scripts/validate_repo.py --full
```

**Pass condition:** `PASS: repository structure, metadata, manifest,
checksums, and links are valid`.

## 3. Obsidian

1. Obsidian → Open folder as vault → select the repository root
   (the folder containing `README.md`). Repository root = vault root.
2. Trust the vault. Properties and Bases render from YAML frontmatter.
3. **Pass condition:** `HOME.md` opens and internal links resolve.

## 4. Git remote and CI

```powershell
gh repo create my-wiki --private --source=. --push
```

**Pass condition:** GitHub → Actions → "Validate Wiki" green on the push.

## 5. QMD semantic search (optional but recommended)

Requires Node.js 22+. QMD's index is a disposable local derivative; the
Markdown remains authoritative. First `qmd query` downloads local embedding
models (~2 GB) — allow minutes.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/configure-search.ps1
powershell -ExecutionPolicy Bypass -File scripts/refresh-search.ps1
qmd status
```

**Pass condition:** `qmd status` reports collections present and embedded.

Note: the index can go stale silently. Run `qmd update` then `qmd embed`
when the tip appears; check `qmd status` before benchmark claims.

## 6. MCP registration (optional, per harness)

Register `scripts/wiki_mcp_server.py` in your harness's local config
(`.mcp.json` for Claude Code; per-machine paths — never commit interpreter
paths). The server exposes read/search/propose only; writes exist only into
`_proposals/`.

## 7. Backups

```powershell
powershell -ExecutionPolicy Bypass -File scripts/create-backup.ps1 -Destination D:\Backups
```

Minimum backup set: local clone + private GitHub remote + dated ZIP on a
separate drive. Obsidian File Recovery is a convenience layer only.

## 8. First intake smoke test

1. Put any small text file in `01-inbox/`.
2. Follow `.claude/skills/wiki-intake/SKILL.md` (manually invoked).
3. **Pass condition:** intake branch created, SHA-256 computed, source
   record + derivative proposed, work stops for your review before commit.
