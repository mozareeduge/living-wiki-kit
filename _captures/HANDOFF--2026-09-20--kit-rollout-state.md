# HANDOFF — 2026-09-20 — living-wiki-kit rollout state

Written for whoever picks this up next (human or agent). Everything below is
verified against the repos themselves — commits are pushed, not just local.

## Where the work lives

- **kit (template):** `github.com/mozareeduge/living-wiki-kit` @ `9e4fca4` (main)
  Local: `Documents/Personal Formal Documents/living-wiki-kit`
- **instance (the archive):** `github.com/mozareeduge/mozare-wiki` @ `e171b25` (main)
  Local: `Documents/Personal Formal Documents/mozare-wiki/mozare-wiki`
- **obsidian plugin:** `Documents/Personal Formal Documents/blackbirdpoem-field-extraction/black-bird-field/`
  (packaged: `Downloads/black-bird-field-1.0.0.zip`)

## DONE (all pushed, validator-clean at each step)

| Phase | What | Commits |
|---|---|---|
| 0 census | B4 re-tier 447, C3 policies, Z2 CENSUS CLEAN 97/447/544; **census merged to main** | `e892fae` (merge) |
| 1 | QMD hybrid MCP + context compiler (lex: --no-rerank) + graph index 1359n/4334e | kit `c87a794`, mw `1f3b1a5` |
| 2 | reconcile_runner: full/incremental plan, exact-once verify, >3-conflict human gate | kit `b81ffab`, mw `9b73c58` |
| 2 drift fix | **1,182 → 318 schema errors** via 711 path-derivable fixes through PATCH_MANIFEST + re-registered baseline | mw `4c9e3f2`, merge `d7c9f79`; fixer ported to kit `9e4fca4` |
| 3 | candidate layer: proposal_schema (8 kinds) + evidence_audit (auto-reject, queue inert); live-fired on real queue | kit, mw `b44cc24` |
| 5 | run-semantic-benchmark exercised; baseline recorded: **3/30 lexical-only** (embeddings were 53% missing) | mw `9a2dd09` |
| ops | evidence-audit report `_audits/evidence-audit-20260919-234541.json`; schema-drift audit `_audits/2026-09-20--schema-drift-reconcile/` | mw |
| obsidian | `.obsidian` plugin dirs gitignored + untracked (obsidian-git auto-commit guard) | mw `e171b25` |
| blackbird | black-bird-field plugin built + syntax/mock-load verified + packaged | (external dir, see above) |

QMD embeddings: 16,575 → **25,052 vectors embedded**; 1,062 chunks still pending
(qmd's "LLM session expired" flakiness, not the model — local embeddinggemma
works; recipe: repeat `qmd embed --max-docs-per-batch 2 --max-batch-mb 1`
passes until Pending: 0).

## REMAINED (in order of next action)

1. **Finish embeddings** — 1,062 pending. Loop passes of
   `qmd embed --max-docs-per-batch 2 --max-batch-mb 1` (background+notify) until
   `qmd status` shows Pending: 0.
2. **Real semantic benchmark** — run
   `python scripts/run-semantic-benchmark.py --output _audits/...json`
   after step 1; commit score. Baseline to beat: 3/30 lexical-only.
3. **318 residual schema errors** — all semantic-judgment fields
   (counter_evidence lists, missing titles/creators that need reading the
   source). NOT auto-fixable; needs content adjudication. Use
   `scripts/schema_drift_fixer.py --errors <file>` to re-derive after manual fixes.
4. **Proposal queue adjudication** — queue is INERT by design. Human must
   decide refiles from `_audits/evidence-audit-20260919-234541.json`.
   Note: `prop-20260906-154145-567` (mixt attribution guard) auto-rejected for
   missing source_passage — refile with the mixt source quote is the owner's call.
5. **black-bird-field plugin** — installed in the mozare-wiki vault
   (`.obsidian/plugins/`, registered in community-plugins.json), but the
   **enable-toggle in Obsidian Settings was never confirmed** (Obsidian was
   open during install; ribbon icons unverified). Open Settings → Community
   plugins → enable "Black Bird Field" → check the four modes.
6. **G-series workbench UI cards** — blocked on the P08-02 lane (claimed by
   session `20260919_140225_2b37f5`, active 2026-09-20). After it frees:
   dispatch P08-03, then G-cards per `workbench-ui-spec.md`.

## Kit human-readiness gaps (for "new version usable by a human")

- README's start-here path works; missing polish: no `QUICKSTART.md`
  (one-page first-hour path), no `CHANGELOG.md`, no `pyproject.toml`
  (install is requirements.txt + PATH tools: git, python, qmd, obsidian).
- `instantiate.py --name X` exists; end-to-end fresh-instantiate smoke test
  on a clean machine never ran — do one before calling v1.0.
- Instance-runbooks (embed passes, drift-fixer usage, benchmark) live in this
  file and `Plans.md`/`SYSTEM_DESIGN.md`; consider folding into kit docs.

## Owner's live edits (left untouched on purpose)

`09-indexes/people-index.md` (embeds `Untitled.base`) and `Untitled.base`
(0-byte Bases view) — in-flight Obsidian edits by the owner, not committed.
`Untitled.base` is empty; if unintended, delete it in Obsidian and the diff
resolves.

## House rules that still apply

`_originals/` immutable; content-zone writes via PATCH_MANIFEST or reviewed
commit; never `git add -A`; validator before success claims; obsidian-git
panel must show 0 changes before you trust a clean tree.
