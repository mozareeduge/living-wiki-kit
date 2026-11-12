import pathlib
W = pathlib.Path(__file__).resolve().parent
H = (W.parent / "HANDOFF--2026-11-09--remote-ingest-chunks-enrichment.md").read_text(encoding="utf-8")
C = (W / "COMMON.md").read_text(encoding="utf-8")
lanes = {
 "L1-chunks": ("Rungs C1, C2, C3, H5 in that order.",
   "Owns: 00-system/policies/RETRIEVAL_MODEL.md, 00-system/schemas/chunk.schema.json, scripts/gov_kernel/chunking.py, "
   "scripts/gov_kernel/retrieval.py (chunk tables + status/stale semantics for H5), a link line in SYSTEM_DESIGN.md, "
   "new tests named tests/test_c1_*.py, test_c2_*.py, test_c3_*.py, test_h5_*.py. The Persian fixture must contain mixed fa/en text, a ZWNJ and the end marks ؟ and ۔"),
 "L2-ingest": ("Rungs I1, I2, I3 in that order (I1 may write a doc:<sha> derivative and a pending source record; it does NOT build chunks. Leave a clearly named hook `on_ingested(receipt)` for the chunk index, which lane L1 will wire later).",
   "Owns: scripts/gov_kernel/ingest.py, scripts/ingest_file.py, scripts/capture/wiki_capture.py (request_id idempotency only), "
   "_intake/ layout helpers, small test fixtures under tests/fixtures/ingest/ (make tiny Persian PDF and DOCX fixtures with python libs already in requirements, or skip with a written reason), "
   "tests/test_i1_*.py, test_i2_*.py, test_i3_*.py. Reuse scripts/file-to-md/to_md.py; do not rewrite it."),
 "L3-transport": ("Rung H1 only: split scripts/wiki_mcp_server.py into one tool registry plus two transports (stdio as today, and MCP Streamable HTTP with /mcp and /healthz). No auth yet (H3 is blocked on an owner decision). HTTP binds 127.0.0.1 by default. The HTTP server is read-profile only unless a flag says otherwise, and even then write tools refuse with E_AUTH_REQUIRED until auth exists.",
   "Owns: scripts/wiki_mcp_server.py, new scripts/mcp_transport/ package, tests/test_h1_*.py (golden test: same tools/list and same results over stdio and HTTP; /healthz returns no corpus data). Prefer the standard library (http.server + threading) or a dependency already in requirements; any new dependency needs a written reason in RESULT."),
}
for k, (scope, owns) in lanes.items():
    t = C + f"\n\n# YOUR LANE: {k}\n**Scope:** {scope}\n\n**Files you own:** {owns}\n\nResult file name: RESULT-{k}.md\n\n---\n# HANDOFF (authority)\n\n" + H
    (W / f"brief-{k}.md").write_text(t, encoding="utf-8")
    print(k, len(t))
