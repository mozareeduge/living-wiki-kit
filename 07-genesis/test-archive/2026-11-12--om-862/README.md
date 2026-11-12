# Test archive — OM-862, 1.5.0

Owner test rule OM-862: a test must pin something a wiki user or agent relies on
(product, design, tech or data layer). A test that only pins the shape of code
written this week is archival noise. Such tests are moved here, not deleted, and
are not collected or run (the file ends in `.txt`).

| Test (was in) | What it pinned | Why it is noise | Behaviour still covered by |
|---|---|---|---|
| `test_on_ingested_hook_invoked` (`tests/test_i1_ingest.py`) | an internal hook function is called once | internal seam from the I1 lane split; the hook is now wired | `tests/test_a0_ingest_chunks.py::test_ingest_reports_real_chunk_count_and_rows` (ingest really indexes chunks) |
| `test_h1_cli_transport_flags` (`tests/test_h1_transport.py`) | the words `--transport` and `--bind` appear in `--help` | help-text shape | `tests/test_h1_transport.py::test_h1_cli_subprocess_http_mode` (the server really starts over HTTP from the CLI) |
| `test_smoke_script_syntax_and_step_order` (`tests/test_h4_remote_ops.py`) | step labels appear in a given text order in `smoke.sh` | script text shape | `tests/test_h4_remote_ops.py::test_smoke_full_run_against_local_insecure_server` and `test_smoke_fails_when_writes_refused` (the smoke really runs and fails when it should) |

Source of the removed tests: `archived_tests.py.txt` in this folder.
