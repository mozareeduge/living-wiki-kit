# HANDOFF — 2026-11-09 — remote server, file ingest, chunk retrieval, enrichment sidecar

**To:** Jimmy (executing agent)
**From:** the owner, drafted with Claude
**Repo:** `mozareeduge/living-wiki-kit` — baseline `main` @ `ac66be8` (tag `v1.4.1`)
**Target release:** kit **1.5.0**
**Place this file at:** `07-genesis/handoffs/HANDOFF--2026-11-09--remote-ingest-chunks-enrichment.md`
and add the rungs below to `Plans.md` as a new ladder section (same table format as the 1.3.0/1.4.0 ladders).

---

## 0. Why this work exists (read first)

A friend built a hosted connector ("0xbrain") from an early snapshot of this kit
(between `60fabc7` P3, 2026-09-19, and `cfbefeb` W1, 2026-09-29). Testing it from
Claude on mobile showed five capabilities the kit does not have yet:

1. **Remote use** — an HTTPS MCP endpoint a Claude connector can call from any device.
2. **File ingest with exact bytes** — upload a PDF/DOCX/EPUB, keep the original
   immutably with its SHA-256, create a pending source record, extract a text derivative.
3. **Chunk-level retrieval** — every hit carries `source_ref`, `chunk_ref`, `span`,
   the exact text, tier, authority level, and the reason it was included.
4. **Enrichment sidecar** — model-written candidate metadata (summaries, tags,
   entities, links) stored *beside* the corpus, never inside it.
5. **Idempotent writes** — a `request_id` so a retried call never captures twice.

We want these in the kit, built **our way**: on the existing governance kernel,
fail-closed, TDD, instance-prefix-aware, and without breaking any invariant below.

> ⚠️ The 0xbrain repo is private and we have **not** read its code. Section 9 lists
> its *observed public tool contracts* (from tool descriptions only). Use them as an
> interoperability target, not as code to copy. Do not request or copy its source.

---

## 1. Ground truth (verified in the repo at `ac66be8`)

| Capability | What already exists | Gap |
|---|---|---|
| Text extraction | `scripts/file-to-md/to_md.py` — pdf/epub (pymupdf), docx, pptx, xlsx, html, txt; writes a header with method + quality note; `fa_ratio()` Persian check | Not wired to an ingest door; output is a whole-file `.md`, no spans |
| Originals + holdings | `_originals/`, `HOLDINGS_POLICY.json`, census gate (1.2.0), `retier_holdings.py`, `report_holdings.py` | No upload/staging path; no receipt for remote arrivals |
| Content hashing / dedup | `scripts/capture/wiki_capture.py` (`sha256`, `duplicate_of`, `find_by_hash`), `file_contract.py` | Dedup is by content, not by caller `request_id` |
| Lexical index | `scripts/gov_kernel/retrieval.py` — SQLite FTS5, table `docs(path, record_id, record_type, status, authority_level, …)` + `docs_fts`; `exact_resolve`, `search_fts`; profiles from `retrieval-profiles.v2.json` | **File-level only.** No chunks, no spans, no chunk refs |
| MCP server | `scripts/wiki_mcp_server.py` — server name `wiki-governance`, JSON-RPC over **stdio**, `--profile read` (default) / `capture` | No HTTP transport, no auth, no upload |
| Context / reconcile | `context_pack.py`, `reconcile_runner.py`, W3 staged reconciliation | Not chunk-aware |
| Labels / aliases | `LABEL_ALIASES.json`, labels as non-evidence edges (O3, D-c) | Enrichment should reuse this "never evidence" rule |

Tests live in `tests/` (pytest) and `scripts/tests/`. CI runs both plus `release_smoke.py`.

---

## 2. Invariants — do not break (each has, or must get, a test)

1. **Corpus is written only by governed doors.** Nothing in this ladder writes canonical records directly.
2. **Model output is authority level 7 (candidate)** — enrichment, proposals, summaries. Fluency never upgrades evidence.
3. **Labels/metadata are never evidence.** Enrichment can add *reasons* for inclusion; it can never be quoted as support.
4. **Originals are immutable.** Bytes in `_originals/` never change after write; SHA-256 is recorded at arrival and re-verified by the validator.
5. **Fail closed.** If FTS5 is missing, an index is stale, or a span no longer matches its source version → return an explicit error/flag, never a silent best guess.
6. **Read is the default profile.** Any write tool (capture, ingest, propose, enrichment submit) is unavailable unless the server runs with a write-capable profile **and** the request is authenticated.
7. **Instance prefix everywhere** (Q1). New ids, collections, files use the instance prefix, not a hard-coded `wiki`.
8. **Kit independence + privacy guard** (`test_kit_independence.py`, 1.4.0 privacy test) must stay green: no owner names, no personal wiki paths, no 0xbrain names in shipped code.
9. **Deterministic derivations.** Chunking and source-version hashing are pure functions of the derivative text. Same input → same refs, on Windows and Linux (watch CRLF and UTF-8; reuse the LF pinning from K1a).

---

## 3. Vocabulary (define these exactly; put them in `SYSTEM_DESIGN.md` and a new `00-system/policies/RETRIEVAL_MODEL.md`)

- **source** — a registered or pending source record (`rec:`), or an extracted derivative (`doc:<sha>`), or a capture (`cap:`).
- **source_version** — `sha256` (hex, 64) of the **normalized derivative text** (UTF-8, LF line endings, NFC). Changes whenever the text changes.
- **chunk** — a contiguous piece of one source_version's text.
- **span** — `{start, end}` character offsets (Python `str` indices, end-exclusive) into that exact text. `text[start:end] == chunk.text` must always hold.
- **chunk_ref** — `chk:` + first 32 hex of `sha256(source_version + ":" + start + ":" + end)`. Stable across rebuilds; changes when the source version changes.
- **stale ref** — a `chunk_ref` whose source_version is no longer current → error `E_STALE_SOURCE`, never a remap.
- **inclusion_reason** — why a hit was returned: `fts-match`, `exact-match`, `alias-match`, `graph-neighbor`, `enrichment-topic` (the last is non-evidence and must say so).
- **receipt** — the JSON a write door returns: ids, hashes, `persisted`, `commit_state` (`committed` / `uncommitted`), warnings.

---

## 4. Target architecture

```
 Claude (phone / desktop / web)
        │  HTTPS (MCP Streamable HTTP)
        ▼
 Cloudflare edge ── Cloudflare Tunnel (cloudflared, outbound-only from VM)
        │                + auth in front (see D-1)
        ▼
 AWS VM (Ubuntu LTS)
  ├─ wiki-governance server  (same tool registry; transports: stdio | http)
  │    ├─ /mcp       MCP endpoint
  │    ├─ /upload    owner-only upload page → returns upl-<43 chars>
  │    └─ /healthz   liveness (no data)
  ├─ instance repo (git)  ← commits by the server, pushed to a private remote
  │    ├─ _originals/          immutable bytes
  │    ├─ _staging/uploads/    TTL'd, gitignored
  │    ├─ derivatives / source records / captures (existing layout)
  │    └─ _search/
  │         ├─ retrieval.sqlite   docs + chunks + FTS5 (disposable, rebuildable)
  │         └─ enrichment/        sidecar JSONL (candidate tier, versioned)
  └─ systemd units: server, cloudflared, nightly backup + validate
```

**Why not Cloudflare Workers alone:** the kit needs a real filesystem, Git, Python,
SQLite FTS5 and QMD/Node. Workers have none of these without a rewrite onto R2/D1/
Durable Objects. Cloudflare's job here is **ingress + TLS + access control**; the VM
does the work. (Do not open inbound ports on the VM; the tunnel is outbound-only.)

---

## 5. The ladder

Format matches `Plans.md`: id, lane/size, task, acceptance, depends on.
Work in order; each rung is TDD (failing test first), one commit per rung plus a
`plans:` commit marking `cc:done`. Branch: `system/2026-11-09--remote-ingest-chunks`.

### Phase C — chunks, spans, refs (local, no server needed)

**C1** `[lane:kit] [size:S]` **Retrieval model policy + schema.**
Write `RETRIEVAL_MODEL.md` (section 3 vocabulary). Add `00-system/schemas/chunk.schema.json`
(`chunk_ref`, `source_ref`, `source_version`, `span{start,end}`, `text_sha256`, `heading_path[]`, `language_hint`, `char_len`).
*Acceptance:* schema validates fixtures; `SYSTEM_DESIGN.md` links the policy; validator lists the schema.

**C2** `[lane:kit] [size:M]` **Deterministic chunker** — `scripts/gov_kernel/chunking.py`.
- Input: normalized derivative text. Output: list of chunks with spans.
- Split on headings (`#`), then blank-line paragraphs; pack paragraphs up to a target (config `chunk_target_chars`, default 1200, max 2000); never split inside a sentence unless a paragraph exceeds max (then split at the last sentence end — handle `.` `!` `?` `؟` `۔` and Persian `.`).
- Keep `heading_path` (e.g. `["Chapter 2", "Rehearsal"]`).
- No overlap in v1 (keeps spans disjoint and simple).
- Normalization: reuse `gov_kernel/normalize.py` for *search keys only*; spans always point into the **un-normalized-for-search** derivative text.
*Acceptance:* property tests — chunks are disjoint, ordered, cover all non-whitespace text, and `text[start:end] == chunk.text`; identical output on CRLF and LF input after normalization; Persian fixture (mixed fa/en, ZWNJ `‌`) chunks without breaking words; ref stability test (rebuild twice → same refs; edit one paragraph → only nearby refs change).

**C3** `[lane:kit] [size:M]` **Chunk index** — extend `gov_kernel/retrieval.build_index`.
New tables in `retrieval.sqlite`:
```sql
CREATE TABLE sources(source_ref TEXT PRIMARY KEY, source_version TEXT, path TEXT,
  tier TEXT, authority_level INTEGER, language_hint TEXT, indexed_at TEXT);
CREATE TABLE chunks(chunk_ref TEXT PRIMARY KEY, source_ref TEXT, source_version TEXT,
  start INTEGER, end INTEGER, heading_path TEXT, text TEXT, text_sha256 TEXT);
CREATE VIRTUAL TABLE chunks_fts USING fts5(chunk_ref UNINDEXED, text, normalized_text);
```
Keep the existing `docs` tables untouched (back-compat). Profiles from `retrieval-profiles.v2.json` filter which paths get chunked.
*Acceptance:* building on a fresh instance creates the tables; FTS5 missing → `FTS5_UNAVAILABLE` exit 2 (existing behaviour); index is disposable (delete + rebuild = identical rows); every handle closed (F24 rule).

**C4** `[lane:kit] [size:M]` **`wiki_retrieve` tool + CLI** (`scripts/retrieval/retrieve.py`).
Args: `query`, `scope` (`canonical|captures|all`), `limit` (≤50), `budget_tokens` (500–32000, default 6000), `cursor`.
Each hit: `source_ref, chunk_ref, span, text, tier, authority_level, inclusion_reason[], score, coverage{returned_chars,truncated}`.
Rules: canonical and captures are **separate groups, never one merged ranking**; budget is enforced by whole chunks (never cut a chunk mid-text; if one chunk exceeds budget, return it with `truncated:true` and the span of what was returned); include `authority_note: "ranking is not evidence"`.
*Acceptance:* tests for grouping, budget, cursor paging, Persian query hitting Persian chunk, alias query hitting via `LABEL_ALIASES.json` with `alias-match` reason.

**C5** `[lane:kit] [size:S]` **`wiki_artifact_read`** — read one source as layers + paginated chunk list, or one chunk by `chunk_ref` with `prev/next` refs. Stale ref → `E_STALE_SOURCE` (with current `source_version`).
*Acceptance:* stale test (edit derivative, rebuild, old ref fails cleanly).

**C6** `[lane:kit] [size:S]` **Proposal door accepts chunk evidence.**
`evidence_refs` may cite `chk:` refs; the quote must be an exact substring of that chunk's current text (in addition to the existing ≥20-char `source_passage` rule). Stale chunk → reject with reason.
*Acceptance:* extend `test_w1_proposal_door.py`.

### Phase I — ingest door and idempotency

**I1** `[lane:kit] [size:M]` **Ingest core** — `scripts/gov_kernel/ingest.py` + CLI `scripts/ingest_file.py`.
Flow for one staged file:
1. Compute SHA-256 of bytes. If an original with that hash exists → return the existing receipt with `duplicate_of` (no new files).
2. Copy bytes to `_originals/<prefix>-<yyyy>/<sha256[:2]>/<sha256>.<ext>` (read-only after write), declare holdings tier per `HOLDINGS_POLICY.json`.
3. Create a source record with `status: pending-registration` (not `registered` — the census biconditional from 1.2.0 must still hold).
4. Extract the derivative by calling `to_md.py` as a library (refactor its `from_*` functions into an importable module; keep the CLI). Record `extraction: {method, quality_note, fa_ratio, ok|partial|failed}`. Never substitute a model summary for extraction.
5. Chunk + index the derivative (C2/C3).
6. Return the receipt: `source_ref, sha256, bytes, mime, extraction, source_version, chunk_count, commit_state`.
Supported in v1: pdf, docx, pptx, xlsx, html, epub, txt, md. Scanned PDFs → `extraction: partial`, flag `needs-ocr` (reuse `ocr_contract.py` flags; do **not** auto-OCR in this ladder).
*Acceptance:* fixtures for each format incl. a Persian PDF and a Persian DOCX; duplicate upload returns same receipt; validator passes after ingest; census still CLEAN; `release_smoke.py` ingests one fixture in a fresh instance.

**I2** `[lane:kit] [size:S]` **Idempotency.**
`wiki_capture_text` and `wiki_ingest_file` accept optional `request_id` (8–100 chars). Store `request_id → receipt` in `_intake/idempotency.jsonl` (append-only). Same id + same payload → return the stored receipt; same id + different payload → error `E_IDEMPOTENCY_CONFLICT`.
*Acceptance:* retry test, conflict test, concurrency test (two processes, same id → one write).

**I3** `[lane:kit] [size:S]` **Commit state.**
Write doors commit to Git in small batches (config: commit immediately, or every N seconds). Receipts report `commit_state`. Add `wiki_status` fields: `uncommitted.count`, `last_failure`.
*Acceptance:* a failing `git commit` (e.g. hook rejects) yields `commit_state: uncommitted` + `last_failure`, never a false `committed`.

### Phase E — enrichment sidecar

**E1** `[lane:kit] [size:M]` **Sidecar store** — `_search/enrichment/<source_ref>.jsonl`, append-only revisions.
Each revision: `source_ref, source_version, revision, idempotency_key, producer{harness, model, prompt_version}, created_at, annotation{summary, topics[], tags[], categories[], entities[{name,kind,aliases[],mention{chunk_ref,text}}], links[{relation,target,evidence[{chunk_ref,quote}]}], chunk_annotations[], uncertainty[]}`.
Optimistic concurrency: submit must send `expected_annotation_revision`; mismatch → `E_REVISION_CONFLICT`. Wrong `source_version` → `E_STALE_SOURCE`.
Validation: every `mention.text` and evidence `quote` must be an exact substring of the named chunk; relation vocabulary closed (`about, mentions, part_of_project, related_to, supports, contradicts`); limits as in section 9.
Tier: all of it is **level 7**. It never edits a record, capture, or source.
*Acceptance:* schema `00-system/schemas/enrichment-revision.schema.json`; tests for each rejection; sidecar deletion does not change the validator result (proves it is outside the corpus).

**E2** `[lane:kit] [size:S]` **Work queue** — `wiki_enrichment_pending(limit≤5, cursor, retry_failed)`: returns sources whose current version has no revision, with page-sized chunk texts. Read-only.

**E3** `[lane:kit] [size:S]` **Use in retrieval, as non-evidence.** `wiki_retrieve` may add hits whose only reason is `enrichment-topic` / `enrichment-entity`; those reasons are labelled `non_evidence: true`. The returned `text` is still the chunk text, never the summary.
*Acceptance:* a query matching only an enrichment tag returns the chunk with a non-evidence reason; the proposal door refuses a quote taken from a summary.

**E4** `[lane:kit] [size:S]` **Coverage reporting** in `wiki_artifact_read`: `annotated_chunks / total_chunks`.

### Phase H — HTTP server, upload page, deployment

**H1** `[lane:kit] [size:M]` **Transport split.**
Refactor `wiki_mcp_server.py` so the tool registry and handlers are transport-agnostic; keep stdio exactly as is (all `test_mcp_*` stay green). Add an HTTP transport implementing MCP **Streamable HTTP** at `/mcp`. Prefer the official MCP Python SDK if it can wrap our existing handlers without changing tool contracts; otherwise a minimal ASGI app (Starlette/uvicorn). Check the current MCP spec version before choosing.
*Acceptance:* same `tools/list` and same results over stdio and HTTP (golden test); `/healthz` returns no corpus data.

**H2** `[lane:kit] [size:M]` **Upload page.**
`GET /upload` (owner-only HTML form) → `POST /upload` stores bytes in `_staging/uploads/` (gitignored), returns `upl-` + 43 chars URL-safe base64 of 32 random bytes. TTL default 24 h; max size config (default 50 MB); allowlisted extensions; ref is single-use. `wiki_ingest_file(upload_ref, title?, description?)` consumes it.
*Acceptance:* expired / reused / unknown refs fail cleanly; staging cleanup job; no path from the MCP side can read arbitrary files.

**H3** `[lane:kit] [size:M]` **Auth + profiles per caller.** Blocked by **D-1**.
Read tools may be reachable with read-scoped credentials; write tools require write scope. The server must re-check scope on every write call (never trust the edge alone).

**H4** `[lane:ops] [size:M]` **AWS VM + Cloudflare Tunnel runbook** — new `RUNBOOK_REMOTE_SERVER.md`.
- VM: Ubuntu LTS, small instance is enough to start; encrypted EBS volume; security group with **no inbound** except SSH from the owner's IP (or SSM only).
- Install: Python + requirements + `requirements-governance.txt`, Node (for QMD), git, `cloudflared`.
- Service user `wiki` without sudo; repo at `/srv/<prefix>-wiki`.
- systemd: `wiki-mcp.service` (`--transport http --profile capture --bind 127.0.0.1:8787`), `cloudflared.service` (tunnel → `http://127.0.0.1:8787`), `wiki-backup.timer` (git push to a private remote + EBS snapshot), `wiki-validate.timer` (nightly `wiki_validate.py --full`).
- Secrets in `/etc/<prefix>-wiki/env` (0600), never in the repo.
- Hostname e.g. `brain.<owner-domain>` via Cloudflare DNS.
*Acceptance:* a fresh VM following only the runbook serves `/healthz` through the tunnel and passes a scripted smoke (status → capture → search → ingest fixture → retrieve).

**H5** `[lane:kit] [size:S]` **Status semantics fix.**
`wiki_status` must not report `degraded` for an **empty** corpus with no index ("nothing to index" ≠ "stale"). States: `empty`, `fresh`, `stale`, `missing`.
*Acceptance:* fresh instance → `degraded: false`; after ingest without rebuild → `stale` + `degraded: true`.

### Phase R — release

**R1** `[lane:kit] [size:S]` Version 1.5.0, `CHANGELOG.md`, `QUICKSTART.md` (local + remote paths), `SYSTEM_DESIGN.md` §6 script table, Persian/English search guide note. `release_smoke.py` covers ingest + retrieve + enrichment submit in a fresh instance. CI green on ubuntu + windows runners.

---

## 6. Owner decisions needed (ask the owner; do not guess)

- **D-1 Auth model for claude.ai connectors.** Verify against current Anthropic docs (docs.claude.com / support.claude.com: "custom connectors / remote MCP") which auth a claude.ai custom connector supports today. Then choose between: (a) MCP OAuth served by our app (or an OAuth provider in front), (b) Cloudflare Access for the upload page + OAuth for `/mcp`, (c) other. Write the decision to `07-genesis/handoffs/`. **H3 is blocked until then.**
- **D-2 Upload page access.** Cloudflare Access with the owner's email (recommended) vs app-level login.
- **D-3 Where the instance repo's private remote lives** (GitHub private repo vs other) and push cadence.
- **D-4 Who runs enrichment.** A scheduled Claude task calling `pending`/`submit`, a local script with an API key, or manual only. Budget cap if automated.
- **D-5 Chunk target size** (default 1200 chars) — confirm after looking at C2's output on one real Persian play text.

---

## 7. Out of scope for 1.5.0

- OCR / speech-to-text automation (contracts exist; host benchmarks still gate them).
- Vector embeddings for chunks (QMD stays as-is; chunk FTS first, measure with `run-semantic-benchmark.py` before adding vectors).
- Porting W1/O-series features *into 0xbrain* — separate contribution work for the friend's repo.
- Any change to promotion/adjudication authority rules.
- Multi-user / multi-tenant hosting.

---

## 8. Done means

- All rungs `cc:done` in `Plans.md`; owner decisions recorded.
- `pytest tests scripts/tests` green on Linux and Windows; `wiki_validate.py --full` PASS; census CLEAN; kit independence + privacy tests green.
- From Claude on a phone, the owner can: check status → capture text with a `request_id` (retry does not duplicate) → upload a Persian PDF on the upload page → ingest it → ask a question and get chunk hits with refs and spans → open a chunk → see an enrichment summary marked non-evidence.
- A handoff file for the next session, and `.maws/` continuity updated.

---

## 9. Interop reference — observed 0xbrain tool contracts (descriptions only)

Use these names/shapes where they fit our kernel so a Claude client behaves the same
against either server. Our server keeps the `wiki_` prefix; aliases are optional.

| 0xbrain tool | Our equivalent | Key contract details observed |
|---|---|---|
| `brain_status` | `wiki_status` / `wiki_state` | counts, captures pending by stage, proposals, validation, search-index state, git uncommitted, `degraded` + reasons |
| `brain_capture` | `wiki_capture_text` | verbatim text only, `language_hint` (fa/en/mixed/unknown), optional `request_id` 8–100 chars, report `persisted` + `commit_state` |
| `brain_search` | `wiki_search` | `mode` lexical/exact, `scope` canonical/captures/all as **separate groups**, `n` ≤50, `offset` paging, "navigation only" |
| `brain_retrieve` | `wiki_retrieve` (C4) | `budget_tokens` 500–32000, `limit` ≤50, `cursor`; hits carry source_ref, text_ref, chunk_ref, span, exact text, tier, authority_level, inclusion_reason, coverage/truncation; explicit fallback when enrichment index missing; no model at query time |
| `brain_read` | `wiki_get_record` | refs `rec: doc: cap: prop: hist:`; never file paths |
| `brain_artifact_read` | `wiki_artifact_read` (C5) | layers, quality flags, metadata coverage, paginated chunks, `E_STALE_SOURCE` |
| `brain_ingest_file` | `wiki_ingest_file` (I1) | `upload_ref` `upl-[A-Za-z0-9_-]{43}`, optional title ≤200 / description ≤2000; exact bytes, SHA-256, pending source record, deterministic derivative |
| `brain_reconcile_context` | `wiki_context_pack` / reconcile | `focused` vs `deep` (paged), sections incl. claims, relations, superseded, open proposals, chronology; returns evidence, never a verdict |
| `brain_propose` | `wiki_propose` | 7 kinds (pre-W1 set minus intake-registration); evidence quote ≥20 chars verified against read output. **Ours keeps the 17-kind W1 vocabulary.** |
| `brain_enrichment_pending` | `wiki_enrichment_pending` (E2) | `limit` ≤5, cursor, `retry_failed` |
| `brain_enrichment_submit` | `wiki_enrichment_submit` (E1) | `source_version` + `expected_annotation_revision` + `idempotency_key`; summary ≤800, ≤12 tags, ≤5 topics, ≤10 entities, ≤10 links (≤3 evidence each, quote 8–500 chars), ≤20 chunk annotations, ≤8 uncertainty notes; entity kinds concept/person/project/organization/work/place/other |

Observed weakness to **avoid**: their status reports `degraded: search index stale`
on an empty archive (fixed in our H5).

---

## 10. Suggested commit order

`C1 → C2 → C3 → C4 → C5 → H5 → I1 → I2 → I3 → C6 → E1 → E2 → E3 → E4 → H1 → H2 → (D-1) → H3 → H4 → R1`

Phases C and I are fully local and need no decisions. Start there.
