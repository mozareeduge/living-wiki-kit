# Instantiating a New Wiki from the Kit

This turns the kit into a working, governed wiki instance for a new subject.
Follow in order; do not skip a verification.

## 0. Decide the three instance constants

| Constant | Example | Where it appears |
|---|---|---|
| instance name | `persian-modernism-wiki` | repo/folder name, docs |
| record-ID prefix | `pmw` | every record id: `pmw-src-…`, `pmw-cap-…` |
| corpus-state id | `pm-corpus-<snapshot>` | `CORPUS_STATE.json`, validators |

Keep the prefix short (2–4 lowercase letters), unique among your wikis.

## 1. Create the instance repository

```bash
cp -r living-wiki-kit/ my-wiki/
cd my-wiki/
rm -rf .git
git init
git config core.hooksPath .githooks
```

## 2. Run the instantiator

```bash
python scripts/instantiate.py --name "My Wiki" --prefix pmw
```

This rewrites ID patterns in validators/capture core/docs, renames
`CORPUS_STATE.json` fields, and writes an instance stamp into
`00-system/registers/INSTANCE.json`. Review its diff with `git diff` before
committing.

## 3. Edit the instance-facing pages

- `HOME.md` — subject, routes, entry points (replace mozare examples)
- `SYSTEM_DESIGN.md` — keep §§2–5 (authority, preservation, record grammar)
  verbatim; rewrite §1 and the corpus facts for your subject
- `README.md` — instance name and purpose
- `AGENTS.md` / `CLAUDE.md` — update names, keep the non-negotiables verbatim

## 4. First validation

```bash
python scripts/validate_repo.py --full
```

An empty instance must PASS: no originals registered yet, manifest empty,
corpus state consistent, no broken links.

## 5. First commit

```bash
git add -A
git commit -m "bootstrap: instantiate <name> from living-wiki-kit"
```

(The pre-commit hook runs the validator automatically.)

## 6. Create the private remote and push

```bash
gh repo create <name> --private --source=. --push
```

GitHub Actions ("Validate Wiki") runs the same baseline gate as the local
hook. Both must be green before any content work is reported as done.

## 7. Optional local search (QMD)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/configure-search.ps1
powershell -ExecutionPolicy Bypass -File scripts/refresh-search.ps1
```

Rename collections per instance (edit
`00-system/configuration/qmd-collections.json`). The index is a disposable
local derivative; the Markdown remains authoritative.

## 8. First intake (when material arrives)

1. Drop files in `01-inbox/`.
2. Invoke the intake procedure (`.claude/skills/wiki-intake/SKILL.md`).
3. The intake skill creates a branch, checksums, source records, manifest
   rows — and stops for your review before any commit.

## What you must NOT change when instantiating

- The authority hierarchy (§3 of SYSTEM_DESIGN) — you may tighten, never loosen.
- The immutability of `_originals/`.
- Candidate-tier status of all AI output and the proposal queue's inertia.
- The validator-before-success claim rule.

Everything else (folder names for object types, vocabulary additions,
thresholds) is yours to adapt per instance.
