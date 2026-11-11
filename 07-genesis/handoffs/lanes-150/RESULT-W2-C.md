# RESULT W2-C: upload page, ingest tool, remote runbook

Worktree branch `system/2026-11-09--w2-lane-C`, base `0e94df3`. Commits: `H2` (c8bfa9e), `H4` (22cc32b) and a small H4 follow-up (owner-name literals removed from a test).

## Per rung

| Rung | Status | Proof (tests) |
|---|---|---|
| H2 upload page `GET/POST /upload` | done | `test_get_upload_form_and_post_returns_ref`, `test_post_upload_rejects_oversize_and_bad_type`, `test_upload_rejects_foreign_host_header` |
| H2 ref format, single use, TTL, size cap, allowlist, cleanup | done | `test_ref_format_and_staging_location`, `test_ref_is_single_use`, `test_expired_ref_fails_and_bytes_removed`, `test_size_cap_and_extension_allowlist`, `test_filename_is_sanitized_no_traversal`, `test_cleanup_removes_expired_and_tombstones`, `test_release_after_failed_ingest_allows_retry` |
| H2 `wiki_ingest_file(upload_ref, title?, description?, request_id?)` | done | `test_ingest_tool_happy_path_and_reuse`, `test_ingest_tool_unknown_expired_and_bad_args`, `test_ingest_tool_failure_releases_ref`, `test_tool_registered_capture_write_only` |
| H2 no arbitrary path from MCP side | done | `test_ingest_tool_cannot_read_arbitrary_paths` (schema has exactly 4 properties; paths and traversal refs fail) |
| H2 auth not built; fail-closed gate | done | `test_http_refuses_ingest_without_insecure_flag`, `test_upload_refused_without_flag_or_in_read_profile`, `test_insecure_flag_refuses_non_loopback_bind`, `test_cli_insecure_flag_requires_capture_and_loopback`, `test_end_to_end_upload_then_ingest_over_http` |
| H4 `RUNBOOK_REMOTE_SERVER.md` + `ops/remote/` units, env template, backup script | done | `test_h4_remote_ops.py`: unit lint (parametrized over 6 units), `test_mcp_service_is_loopback_capture_without_insecure_flag`, `test_cloudflared_points_at_loopback_only`, `test_timer_services_run_expected_commands`, `test_env_template_has_no_secrets`, `test_runbook_paths_exist_and_cover_h4` |
| H4 scripted smoke `ops/remote/smoke.sh` | done | `test_smoke_full_run_against_local_insecure_server`, `test_smoke_read_only_skips_writes_with_message`, `test_smoke_fails_when_writes_refused`, `test_smoke_script_syntax_and_step_order` (these start the real server process and run the script against it) |

Not touched: any real VM, Cloudflare or DNS. Paper and templates only.

## How the gate works (document for the owner)

- `/upload` and the write tools over HTTP are refused unless the server runs `--profile capture` AND `--insecure-local-only`. That flag binds 127.0.0.1 only; the CLI and `create_mcp_http_server` both refuse any other host (`ValueError` / argparse error).
- `/upload` additionally checks that the `Host` header is a loopback name (blocks DNS rebinding) and sends no CORS headers.
- Shipped `wiki-mcp.service` does NOT contain the flag. It is an opt-in drop-in example (`wiki-mcp-insecure-local-only.conf.example`) that names D-1/D-2.

## Final test tail

```
$ python -m pytest -q tests scripts/tests -p no:cacheprovider
FAILED tests/test_kit_independence.py::test_no_tracked_file_carries_a_personal_wiki_trace
1 failed, 515 passed, 2 skipped, 2 xfailed in 131.56s (0:02:11)
```

The one failure is not from this lane: `07-genesis/handoffs/HANDOFF--2026-11-09--remote-ingest-chunks-enrichment.md` (placed by base commit `0e94df3`) contains an owner name, and the independence test scans every tracked file. After I removed the owner-name literals from my own test, it is the only remaining hit. Fix belongs to whoever owns that handoff file (neutralise the name or exempt `07-genesis/handoffs/`). The lane brief said the base suite was 478 passed; the handoff file was added after that check.

## Deviations from the HANDOFF / brief

1. **Files outside my list were edited, minimally:** `scripts/wiki_mcp_server.py` (import the upload package, register `wiki_ingest_file`, add the `--insecure-local-only` flag, pass the store to `run_http`) and `scripts/mcp_transport/registry.py` (new `http_writes_allowed` attribute, default False, and the HTTP write gate honours it). Tools are registered in `wiki_mcp_server.py`, not `registry.py`, so the registration lines had to go there. Expect a merge conflict in both; the additions are small and marked `H2`.
2. `scripts/mcp_transport/http.py`: route hooks for `/upload`, two new keyword args on `create_mcp_http_server`/`HttpTransport`/`run_http`. Upload logic lives in `scripts/upload/routes.py`.
3. `wiki-validate.service` runs `scripts/wiki_validate.py --format json`; the HANDOFF says `--full`, but that script has no such flag (only `validate_repo.py` has one).
4. `cloudflared.service` uses token mode (`tunnel run`, token from the env file); the public hostname's service URL (`http://127.0.0.1:8787`) is set in the dashboard. A config-file variant is shipped as an example.
5. H4 acceptance ("fresh VM passes the scripted smoke") can only be fully met after the write drop-in is installed, because D-1/D-2 are open. The runbook therefore has a read-only smoke (`--read-only`) as the default and the write smoke as an explicit opt-in.
6. `ops/remote/.gitattributes` forces LF so scripts and units survive a Windows checkout. `.gitignore` gained `_staging/`.
7. The smoke's retrieve step uses `wiki_retrieve` (another lane). If it is not advertised it prints `SKIP retrieve: tool wiki_retrieve not advertised on this server` and does not fail. `SMOKE_REQUIRE_HITS=1` makes it demand a hit once chunk indexing is wired.

## Open questions

- D-1/D-2 (auth design) still pending; until decided the write path over HTTP stays opt-in and unauthenticated.
- Does `wiki_retrieve` keep the argument names `query`, `limit`, `budget_tokens`? The smoke assumes the HANDOFF C4 names.
- `wiki_ingest_file` with the same `upload_ref` after success returns `E_UPLOAD_USED` even if the same `request_id` is sent; idempotent replay of a receipt by `request_id` is not offered at the tool level (the ingest core does cache it, but the ref is gone first). Decide if replay-by-request_id should bypass the ref check.
- The upload store re-reads env limits on every call (stateless on disk). Cleanup runs on each upload and via `python scripts/upload/store.py <root>`; no separate cleanup timer was added.
