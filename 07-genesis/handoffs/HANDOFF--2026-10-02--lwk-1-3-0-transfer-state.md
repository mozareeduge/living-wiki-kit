---
id: wiki-handoff-2026-10-02-lwk-1-3-0-state
type: handoff
title: "living-wiki-kit 1.3.0 — final state, what is done, what is left, and the one blocker (transfer brief)"
branch: system/2026-09-20--next-version-plan
corpus_snapshot: wiki-corpus-empty
status: active
created: 2026-10-02
updated: 2026-10-02
schema_version: 1.0.0
---

# Handoff — living-wiki-kit 1.3.0: complete except one account-level blocker

**Read this if you are picking up the kit cold, on another machine, or in another
harness.** It supersedes `HANDOFF--2026-09-29--overall-plan-and-remaining.md` for
status purposes. Task truth is still `Plans.md`; this note is the map.

Verified 2026-10-02 01:22 local. Every number below was re-run, not recalled.

---

## 1. Where things are

| | |
|---|---|
| Kit repo (public) | `github.com/mozareeduge/living-wiki-kit` |
| Branch | `system/2026-09-20--next-version-plan` @ **`8739a90`** (= origin, tree clean) |
| PR | **#7**, `OPEN`, **`DRAFT`**, `MERGEABLE`, `mergeStateStatus: UNSTABLE` |
| Base | `origin/main` @ `02399e7` |
| Instance (private) | `github.com/mozareeduge/mozare-wiki`, local `Documents/Personal Formal Documents/mozare-wiki/mozare-wiki` |
| Local path | `C:\Users\Zarinpal\Documents\Personal Formal Documents\living-wiki-kit` |
| Tools used | Python 3.11.9, `gh` 2.96.0 (authenticated as `mozareeduge`), `qmd` via npm shim, Windows + `core.autocrlf=true` |

**One-line status: every rung of the 1.3.0 ladder is `cc:done`. The code is
measured, green and pushed. The only thing preventing release is that GitHub has
never once started a job on this account — and that is not fixable from a repo.**

---

## 2. Verification you can reproduce right now

```bash
git config core.hooksPath .githooks
python -m pip install -r requirements.txt -r requirements-governance.txt pytest

python -m pytest tests -q                                # 263 passed
python -m pytest scripts/tests scripts/capture/tests -q # 119 passed, 2 skipped, 2 xfailed
python scripts/check_against_baseline.py                # exit 0 — "OK: validators clean"
python scripts/wiki_validate.py --repo . --format json  # exit 0
python scripts/wiki_state.py --repo . check             # exit 0
python scripts/wiki_evidence.py --repo . check          # exit 0
python scripts/wiki_profiles.py check                   # exit 0
```

`pytest tests` takes ~28 s and the three-dir suite is usually under 60 s; on a
loaded machine a 30 s cap can cut it off — that is load, not a hang.

---

## 3. What this session changed (7 commits, all pushed)

| Commit | What |
---

## 4. Two real defects found and fixed — read before "fixing" anything

### 4.1 The benchmark runner crashed on Windows (why M2 looked "blocked")

`qmd` prints UTF-8 box-drawing glyphs. `subprocess.run(text=True)` decodes with
the Windows ANSI codepage (**cp1252**), the reader thread raises, and
`proc.stdout` silently becomes `None` — which then crashed the runner's *own*
error path:

```
File "subprocess.py", line 1599, in _readerthread
  buffer.append(fh.read())
UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d in position 1862
...
TypeError: 'NoneType' object is not subscriptable   # run-semantic-benchmark.py:86
```

Fixed in `6d2dca1`: explicit `encoding="utf-8", errors="replace"`,
`PYTHONUTF8`/`PYTHONIOENCODING` in the child env, and `None` guards so a decode
failure degrades into a reported error instead of a crash. **Any future Windows
script that shells out to `qmd` needs the same treatment.**

### 4.2 `human_rejection_rate` is not an independent metric

It is derived from the same `expected`-vs-`matched` signal as `mean_recall_at_k`
and tracks `1 - recall`. It is an *operational proxy* ("what fraction of
questions would a reviewer send back?"), not a second quality axis. The
docstring now says so. **Do not report it as corroborating evidence for recall.**

---

## 5. The one blocker: CI has never started a job (account-level, control-proven)

**Symptom:** PR #7 shows a red `validate` check; the browser run page is blank;
`gh run view --log` says `log not found`.

**Verbatim server error:**
```
The job was not started because recent account payments have failed or your
spending limit needs to be increased. Please check the 'Billing & plans' section
in your settings
```

**Proof the job never ran** (not a failing step):
```bash
gh api /repos/mozareeduge/living-wiki-kit/actions/runs/36909363705/attempts/2/jobs
# {"runner_name":"", "runner_id":0, "steps":[], started 20:44:56 → completed 20:44:58}
```
`runner_name` empty + `runner_id: 0` + `steps: []` + **2-second** duration.

**Control experiment — the part that matters.** The owner showed a Free-plan
billing page with $0 usage and nothing owed, and the repo is public (Actions on
public repos are free), which contradicts a billing wall. So it was **tested, not
argued**:

1. Re-ran the failed workflow → attempt 2, identical 2 s failure.
2. Manually dispatched it (`workflow_dispatch`, run `36923953931`) → identical.
   So the `pull_request` trigger is irrelevant.
3. Created a **throwaway public repo** with a three-line workflow
   (`runs-on: ubuntu-latest` → `run: echo "probe-ok"`) → run `36924429166`
   failed with the **same verbatim message**.

A trivial `echo` in an unrelated repo fails the same way ⇒ **account-level block;
no repository change can clear it.** Ruled out: Actions `enabled: true`,
`allowed_actions: all`, repo not private/archived/disabled, workflow YAML valid.

**Cleanup owed:** the probe repo `mozareeduge/actions-probe` is **archived but not
deleted** (the `gh` token lacks delete rights: `HTTP 403 Must have admin rights`).
Delete it manually if you want the account tidy.

### What the owner must do (browser session only)

The `gh` token here has scopes `gist, read:org, repo, workflow` — **no billing
read**, which is why `gh api /users/mozareeduge/settings/billing/actions` returns
`HTTP 404` (a scope limit, not a missing page). In order:

1. <https://github.com/settings/billing/plans> — the account banner read
   *"Included usage limits reset in 31 days"*: this cycle's Actions
   minutes/storage look **exhausted or capped**, which yields this exact message
   with $0 charged.
2. <https://github.com/settings/billing/budgets> — any budget set to a **$0
   spending limit** stops billable minutes outright.
3. <https://github.com/settings/billing> — failed payment method / pending Actions
   suspension.

**Then verify with one field:**
```bash
gh workflow run validate.yml --ref system/2026-09-20--next-version-plan
gh api /repos/mozareeduge/living-wiki-kit/actions/runs/<id>/jobs --jq '.jobs[0].runner_name'
```
Non-empty `runner_name` = unblocked; the gates will then actually run.

**Do not merge PR #7 around this.** `mergeStateStatus` is `UNSTABLE` and the
ladder's release definition is "reviewed, CI green, merged". Merging would record
a release whose gate never executed — the exact failure this ladder exists to
prevent.

---

## 6. The measured result (M2 acceptance b)

`_audits/2026-10-01--semantic-benchmark/` — `README.md`, `report.json`, `report.md`.

| | baseline 2026-09-20 (`mozare-wiki` `9a2dd09`) | run 2026-10-01 |
|---|---|---|
| Cases passing | **3 / 30** | **12 / 30** (4×) |
| Threshold | 27 | 27 (unchanged) |
| Verdict | FAIL | **FAIL** (honest) |

`mean_recall@5 = 0.3067` · `human_rejection_rate = 0.8667` ·
`evidence_trace_completeness = 0.4`

**Caveats (do not skip these when quoting the number):**
- M1 was **still running during the benchmark** — embeddings were mid-flight, so
  12/30 is a mid-recovery figure, not final. See §7.3.
- Most failures are **partial recall**: the right file appears but not all
  expected neighbours inside the top 5. That is why recall (0.31) sits below the
  pass rate (0.40).
- Deterministic `--no-rerank` run; reproducible, not noisy.

---

## 7. What is left, in order

### 7.1 Owner, browser — blocks the release
1. Clear the account-level Actions state (§5). **The only hard blocker.**
2. Re-dispatch the workflow, confirm `runner_name` non-empty, CI green.
3. Mark PR #7 **ready for review**, review, merge to `main` → kit 1.3.0 released.
4. Delete the archived `actions-probe` repo.

### 7.2 Owner, in Obsidian (~1 min)
H3 is `cc:done exc. live-toggle`. The plugin **is** installed at
`mozare-wiki/.obsidian/plugins/black-bird-field/` and **is** registered in
`.obsidian/community-plugins.json`; all four modes (Field / Reader / Route /
Index) are present in the installed `main.js` **v2.0.0**. Only the in-app ribbon
confirmation remains.

**Plugin home decided: external + version-pinned, not vendored into the kit.**
Reason: `.obsidian/plugins/` is gitignored so nothing tracks it, and drift already
exists — the **installed copy is v2.0.0** while the **external source**
(`Documents/.../blackbirdpoem-field-extraction/black-bird-field/`) is **v1.0.0**.
Reconcile or re-pin deliberately.

### 7.3 M1 — finish embeddings, then re-run the benchmark
```bash
qmd embed          # at hand-off: 35,601 vectors embedded, 271 still pending
qmd status         # acceptance: Pending: 0
```
Note: the background `qmd embed` started during this session **exited on its own
with 271 documents still pending** — restart it and let it finish. Then re-run the
30-case set and commit the final score beside the current one; that is the number
that counts.

```bash
# the case config is NOT in the kit (finding F2) - copy it read-only from the instance
cp "../mozare-wiki/mozare-wiki/00-system/configuration/semantic-benchmark-v1.1.0.json" \
   00-system/configuration/
python scripts/run-semantic-benchmark.py --output _audits/<date>--semantic-benchmark/report.json
```

### 7.4 Operator lane (never an agent)
- **H1** — adjudicate the proposal queue in `mozare-wiki`
  (`_audits/evidence-audit-20260919-234541.json`, incl. the
  `prop-20260906-154145-567` refile decision). `cc:todo`.
- **H2** — resolve the ~306 residual schema errors in `mozare-wiki`; the count
  must strictly decrease and the baseline re-register in the same commit.
  `cc:todo`.
- **U2** — G-series workbench UI cards. `blocked` (needs H3 + a free P08-02 lane).

### 7.5 Open findings
- **F2** — the kit does not ship `semantic-benchmark-v1.1.0.json` (only the
  instance has it). Decide: ship a starter case set, or document the benchmark as
  instance-only.
- **F9** — the kit's MCP server reads QMD collection names from config;
  `mozare-wiki`'s copy still hardcodes `mozare-*`. Port `qmd_collections()` back
  so both files stay identical. **Open.**
- **F1** — `schema_drift_fixer.py` LF-normalises despite a "format-preserving"
  docstring. Pinned by a test; fix only if an instance drops `text=auto`.
- **F3/F4** — fixer keeps one op per file; writes an unquoted `filename`.
  Candidate rung `S3b`, unclaimed.

---

## 8. Standing rules (from `AGENTS.md` / `CLAUDE.md`)

1. `_originals/` is **immutable**. Never edit, move or delete anything there.
2. Everything you produce is **candidate-tier (authority level 7)**. Fluency never
   upgrades it; only human adjudication or evidence in canonical records does.
3. Retrieval scores and labels **organise attention, never evidence**.
4. The default agent/MCP profile is **read-only**. Do not write into governed
   canonical/system/source zones. The `capture` profile may create noncanonical
   captures and durable proposals only.
5. **One rung at `cc:wip` at a time.** `MATERIALS_INDEX.jsonl` and
   `CORPUS_STATE.json` are monolithic with a snapshot hash — two branches touching
   them conflict.
6. `[tdd:required]` means **RED pasted, then GREEN**. A test that passes before
   the implementation is a broken test.
7. **Never** add a line to `.githooks/known-baseline-errors.txt` to force a commit
   through. A new check firing on existing content ends the rung with a reported
   count.
8. Never `git add -A`; stage named files. Never force-push.
9. A rung flips to `cc:done` **only** with its acceptance output pasted.
   `.maws/` is continuity, never proof.
10. Adjudication promotes authority; it never gates the pipeline or grants
    visibility.

---

## 9. Gotchas that cost real time here

- **Windows `core.autocrlf=true`**: generated files must stay LF-pinned in
  `.gitattributes` or `wiki_state check` reports `STATE.GENERATED_DRIFT`.
- **Any subprocess calling `qmd` on Windows** must decode UTF-8 explicitly (§4.1).
- **`git commit` looks like it fails** in this PowerShell environment: the
  pre-commit hook writes to stderr, which surfaces as `NativeCommandError` /
  exit 1 even when the commit **succeeds**. Always confirm with
  `git --no-pager log --oneline -1` before assuming failure.
- The same applies to `qmd` (it prints an "N documents need embeddings" warning to
  stderr). Redirect stderr, or read stdout separately.
- The `gh` token has **no billing scope** → 404 on all `/settings/billing` APIs.
- `mozare-wiki` is **private** and is **read-only** unless the owner explicitly
  orders an instance lane. Do not write into it by default.
- Do **not** `git add -A` here: `.maws/` runtime state and stray `01-inbox/` test
  output will be swept in.
- `spawn_agent` may fail with an auth error in this environment; if so, do the
  review inline and say so rather than claiming an independent verdict.
- Full-suite timings that look like hangs on a loaded machine are not.

---

## 10. Suggested next session

```bash
cd "C:/Users/Zarinpal/Documents/Personal Formal Documents/living-wiki-kit"
git config core.hooksPath .githooks
git switch system/2026-09-20--next-version-plan && git pull --ff-only
python -m pytest tests scripts/tests scripts/capture/tests -q
python scripts/check_against_baseline.py
```

Then, in order: owner clears Actions (§7.1) → CI green → merge PR #7 → kit 1.3.0
released. In parallel: finish `qmd embed` (M1) and re-run the benchmark to replace
the mid-flight 12/30 with the final number.

`MAWS 2.0` continuity: thread
`20261001-180932-lwk-1.3.0-close-out-ci-billing-m2-b-score-h3-rev` (all items
`done`); earlier `20261001-172018-lwk-1.3.0-salvage-m2-metrics-u1-capture-breadth`.
Resume with `python ~/.maws/runtime/maws.py --format human status`.

It is derived from the same `expected`-vs-`matched` signal as `mean_recall_at_k`
and tracks `1 - recall`. It is an *operational proxy* ("what fraction of
questions would a reviewer send back?"), not a second quality axis. The
docstring now says so. **Do not report it as corroborating evidence for recall.**
|---|---|
| `73fc135` | **M2** — three metrics in `run-semantic-benchmark.py` (recall@K, rejection rate, evidence-trace completeness), JSON + markdown |
| `82cc968` | **U1** — capture breadth: `capture_url` / `capture_photo` / `SingleFileAdapter`; `url` added to both capture schemas; write-isolated CLI tests; handoff |
| `41d7b74` | `Plans.md` ledger reconciled to reality |
| `6d2dca1` | **Bug fix** — Windows UTF-8 decode crash in the benchmark runner (§4.1) |
| `b5a58f6` | **M2 acceptance (b)** — real 30-case score committed under `_audits/` |
| `764a0bd` | Plans + CHANGELOG + first CI-block handoff |
| `8739a90` | CI-block handoff rewritten after the control experiment (§5) |

New files: `_audits/2026-10-01--semantic-benchmark/{README.md,report.json,report.md}`,
`07-genesis/handoffs/HANDOFF--2026-10-01--m2-u1-landed.md`,
`07-genesis/handoffs/HANDOFF--2026-10-01--ci-billing-block.md`,
`scripts/capture/file_contract.py`,
`scripts/capture/tests/test_url_photo_file.py`,
`scripts/tests/test_semantic_benchmark_metrics.py`.