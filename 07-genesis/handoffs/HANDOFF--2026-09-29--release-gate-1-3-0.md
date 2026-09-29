---
id: wiki-handoff-2026-09-29-release-gate-1-3-0
type: handoff
title: "Release gate 1.3.0 (R2): smoke + CENSUS CLEAN both repos"
branch: system/2026-09-20--next-version-plan
corpus_snapshot: wiki-corpus-empty
status: active
created: 2026-09-29
updated: 2026-09-29
schema_version: 1.0.0
---

# Handoff — R2 release gate for kit 1.3.0

## (a) Instantiate transcript (true fresh clone)

Cloned `origin/system/2026-09-20--next-version-plan` at `b6112d0` into a
temp dir (no working-tree artifacts), then:

```bash
git config core.hooksPath .githooks
python scripts/instantiate.py --name Smoke --prefix sm
python scripts/validate_repo.py --full          # PASS
python scripts/validate_content_release.py      # PASS (0 orphans)
python scripts/report_holdings.py               # CENSUS CLEAN (0/0 empty kit)
```

Instantiate rewrote 31 files; both validators PASS on the Smoke instance.

## (b) CENSUS CLEAN lines

- kit (fresh clone above, empty Smoke instance): `7. Verdict: CENSUS CLEAN`
- mozare-wiki @ `8e71ee3` (shallow read-only clone, tree left untouched):
  `7. Verdict: CENSUS CLEAN` (mojibake: none; per-intake registers fresh
  at 2026-09-28; 1 blocked claim intact)

## (c) What this gate does NOT do

- Does not merge PR #7 (owner review).
- Does not run CI (GitHub billing block stands; all workflow commands were
  reproduced locally: kernel gates + `pytest tests scripts/tests
  scripts/capture/tests` → 322 passed).
- Does not touch mozare-wiki (read-only clone, deleted after the check).

## Remaining after R2

W3, W4, R1-code, R2-gate are done on the branch. Left: owner review +
billing fix → CI green → merge (R1 c/d) → kit 1.3.0 released. Then the
instance/operator lane on its own schedule: H1, H2, H3, M1 (+M2 after M1),
U1 (needs H3), U2 (blocked).
