---
id: mw-doc-capture-runbook
type: system-document
title: "Capture incident and recovery runbook (1.2.0)"
status: candidate
---
# Incident / recovery runbook

| Symptom | Action |
|---|---|
| `processing-failed` record | Keep the raw input; fix the cause; `set-state … processing` retries |
| Orphan media (crash between writes) | `wiki_capture.py recover` adopts it as `processing-failed` or quarantines dupes under `.quarantine/` |
| `E_HASH_MISMATCH` on validate | Media bytes changed: investigate, never re-hash to match; restore from backup/LFS |
| `E_STATE_DIVERGED` | Front matter hand-edited: replay the event log, re-apply via `set-state` |
| Oversize / bad MIME rejected | By design: shrink/convert client-side, re-send; rejects are receipts, not data loss |
| Unauthorized sender | Refused before storage; check `MW_WIKI_ALLOW_USER/CHAT` if legit traffic is refused |
| Transcription engine missing | Expected until a benchmark passes: use `commit-transcript` manual path |
| Disk full | Stop intake; free space; `recover`; validate all |
| Log shows secrets | Rotate the secret; note: provenance events must never carry tokens or payloads |

Rollback: captures are additive intake; rolling back the feature = stop the
hook/clients, leave records in place (they validate standalone), remove LFS
patterns only with a recorded decision. No migration of old binaries happens
in 1.2.0.
