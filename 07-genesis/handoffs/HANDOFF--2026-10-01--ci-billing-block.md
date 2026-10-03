---
id: wiki-handoff-2026-10-01-ci-billing-block
type: handoff
title: "CI never starts: account-level Actions block (control-proven), not a code failure"
branch: system/2026-09-20--next-version-plan
corpus_snapshot: wiki-corpus-empty
status: active
created: 2026-10-01
updated: 2026-10-01
schema_version: 1.0.0
---

# Handoff — CI job never starts; the block is account-wide, not repo- or code-specific

Owner question: "on GitHub in the browser I saw nothing — where is the error?"
and, after seeing a Free-plan billing page: "everything we need is free."

**Answer: the billing page is not wrong, and neither is the error message.**
GitHub reports Free / $0 metered usage / nothing owed — and still refuses to start
the job. The message describes the account's Actions state, not a charge for this
repo. Proven by a control experiment below, not inferred.

## The verbatim server-side error

```json
{
  "path": ".github",
  "annotation_level": "failure",
  "message": "The job was not started because recent account payments have failed or your spending limit needs to be increased. Please check the 'Billing & plans' section in your settings"
}
```

Source (reproducible, paste-able):

```bash
gh api /repos/mozareeduge/living-wiki-kit/check-runs/110511116124/annotations
```

- Runs: **36904376988** / job 110511116124 (head `41d7b74`), **36909363705** /
  job 110527881861 (head `764a0bd`), **36923953931** (manual dispatch) — all
  identical, on this branch and on `main`-era heads.

## Why the browser page is empty

```bash
gh api /repos/mozareeduge/living-wiki-kit/actions/runs/36909363705/attempts/2/jobs
```

```json
{"id":110576157604,"name":"validate","conclusion":"failure",
 "runner_name":"","runner_id":0,"steps":[],
 "started_at":"2026-10-01T20:44:56Z","completed_at":"2026-10-01T20:44:58Z"}
```

- `runner_name` empty and `runner_id: 0` → **no runner was ever assigned**.
- `steps: []` → **no step ever executed**.
- 2-second duration → it failed the instant it was created.
- `gh run view <id> --log` → `log not found`, because there is no execution to log.
  That is why the UI has nothing to show.

## Control experiment — the decisive evidence

A Free plan with $0 usage and a **public** repo should never hit a billing wall
(Actions on public repos are free), so this was tested, not argued:

1. **Re-ran** the failed workflow → attempt 2, same 2-second failure, same message.
2. **Manually dispatched** it (`workflow_dispatch`, run `36923953931`) → also 2 s,
   `runner_name=""`, `steps=0`. So the `pull_request` trigger is irrelevant.
3. **Built a control repo** `mozareeduge/actions-probe` — public, brand new, one
   three-line workflow (`runs-on: ubuntu-latest` → `run: echo "probe-ok"`).
   Run `36924429166` → **same failure, same verbatim message** (job `110578127960`).

A trivial `echo` in an unrelated repo fails identically ⇒ **the block is
account-level; no repository change can clear it.** The probe repo has been
archived (the token cannot delete it: `HTTP 403 Must have admin rights`).

Ruled out as causes: Actions `enabled: true`, `allowed_actions: all`, repo
`private:false archived:false disabled:false`, workflow YAML valid,
`permissions: contents: read`.

## What remains (owner-side, browser-session only)

The token in use (`gho_…`, scopes `gist, read:org, repo, workflow`) carries no
billing read, which is why `gh api /users/mozareeduge/settings/billing/actions`
returns HTTP 404 — a scope limit, not an absent page.

The account-level Actions states that produce this exact message, each readable
only by the owner in a session:

- <https://github.com/settings/billing/plans> — the banner read *"Included usage
  limits reset in 31 days"*: the current cycle's Actions minutes/storage are
  exhausted or capped. That yields this message with **$0 charged**.
- <https://github.com/settings/billing/budgets> — a budget set to a **$0 spending
  limit** stops billable minutes outright.
- <https://github.com/settings/billing> — no failed payment method / no pending
  Actions suspension.

Fastest decisive check after touching any of those — re-dispatch and watch the one
field that matters:

```bash
gh workflow run validate.yml --ref system/2026-09-20--next-version-plan
gh api /repos/mozareeduge/living-wiki-kit/actions/runs/<new-id>/jobs --jq '.jobs[0].runner_name'
```

A non-empty `runner_name` means CI is unblocked and the gates will actually run.

## Do not merge around it

`mergeStateStatus: UNSTABLE`; the `validate` check is red. The ladder's release
definition is "PR #7 reviewed, CI green, merged". Merging now would record a
release whose gate never ran — the exact failure this ladder exists to prevent.
Local gates are green (`check_against_baseline.py` → `OK: validators clean`), so
the code is ready the moment CI can start.