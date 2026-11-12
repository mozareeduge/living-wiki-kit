# living-wiki-kit 1.5.0 — wave 2 lane contract (laptop, 11 Nov 2026)

Authority: `07-genesis/handoffs/HANDOFF--2026-11-09--remote-ingest-chunks-enrichment.md` (in your worktree). Read sections 1–5 and 9 first.

## State you start from (verified 11 Nov)
Branch base `0e94df3` already has: C1 chunk policy + schema, C2 `scripts/gov_kernel/chunking.py`, C3 chunk tables in `scripts/gov_kernel/retrieval.py`, H5 status states, I1 `scripts/gov_kernel/ingest.py` + `scripts/ingest_file.py` (hook `on_ingested(receipt)` exists but does NOT index chunks yet; `chunk_count` is always 0), I2 `request_id` idempotency, I3 commit state, H1 `scripts/mcp_transport/{registry,stdio,http}.py`. Full suite: 478 passed, 2 skipped, 2 xfailed.

## Rules
1. Work ONLY in your own worktree (given in your lane). Never touch `lwk-wt-150` or another lane's worktree. No push, no PR, no merge.
2. TDD: write the failing test first. One commit per rung, message `<ID>: <what>`.
3. HANDOFF §2 invariants hold. The kit independence and privacy tests must stay green: no owner names, personal paths or "0xbrain" anywhere in shipped code or tests. Use the instance prefix, never a hard-coded `wiki`. Fail closed. Deterministic output on LF/CRLF and UTF-8 NFC.
4. New MCP tools: put the handlers in your own module and register them in `scripts/mcp_transport/registry.py` with the smallest possible addition (a few lines). Jimmy resolves merge conflicts there.
5. Do not edit `Plans.md`, `CHANGELOG.md` or the version number.
6. Run the WHOLE suite at the end: `python -m pytest -q tests scripts/tests -p no:cacheprovider`. Any new failure must be fixed, or listed with its reason.
7. Write `07-genesis/handoffs/lanes-150/RESULT-W2-<lane>.md`: per rung done/partial/not done, with the names of the tests that prove it; the final test tail; any deviations from the HANDOFF and why; open questions. Commit it.
8. Never invent results. End your reply with the STATUS / CHANGED / CHECKED / OPEN lines.
