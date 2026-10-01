# Handoff — CI billing block: the exact proof, 2026-10-01

Owner question: "on GitHub in the browser I saw nothing — where is the error?"

There is **nothing to see on the run page, and that is the symptom**. The job is
never scheduled, so GitHub never renders steps or a log.

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

- Run: **36904376988** — job **110511116124** — head **`41d7b74`** (this branch, today).
- Same message on the previous run, job 109362934799 / head `2df7db2`.

## Why the browser looks empty

```bash
gh api /repos/mozareeduge/living-wiki-kit/actions/runs/36904376988/jobs
```

```json
{"id":110511116124,"name":"validate","status":"completed","conclusion":"failure",
 "runner_name":"","steps":[],"started_at":"2026-10-01T18:06:40Z",
 "completed_at":"2026-10-01T18:06:43Z"}
```

- `runner_name` empty and `runner_id: 0` → **no runner was ever assigned**.
- `steps: []` → **no step ever executed**.
- 3-second duration → it failed the instant it was created.
- `gh run view <id> --log` → `log not found: 110511116124`, because there is no job
  execution to log. That is why the UI has nothing to show.

## Scope

- Every run since ~2026-09-29 fails identically (10 consecutive `Validate Wiki`
  runs, all 3–4 s, all `failure`).
- This is **account billing**, not code: the kit has no failing CI step, and the
  local gates are green (`check_against_baseline.py` → `OK: validators clean`).
- `gh api /users/mozareeduge/settings/billing/actions` returns **HTTP 404** for
  this token — the billing API needs the owner's own session; the annotation
  above is the authoritative statement.

## The fix (owner-side, ~2 minutes)

1. <https://github.com/settings/billing> → fix the failed payment method, or
2. <https://github.com/settings/billing/plans> → confirm the Actions minutes /
   spending limit, or set spending to $0 if you want Actions hard-capped.
3. Re-run the workflow on PR #7 ("Re-run all jobs"). No code change is needed.

Until then the ladder's own rule stands: `mergeStateStatus: UNSTABLE`, and the
kit's release definition ("PR #7 reviewed, CI green, merged") is not met. Do not
merge around a red check — the check is red for a billing reason, and merging
would record a release whose gate never ran.