# Retrieval Model and Chunk Governance

> **Search is a route, never evidence. Ranking organizes attention; it proves nothing.**

This policy defines the core retrieval concepts, derivation stability guarantees,
and vocabulary for chunk-level retrieval in the Living Wiki Kit.

---

## 1. Core Vocabulary

- **source** — a registered or pending source record (`rec:`), an extracted derivative (`doc:<sha>`), or a capture (`cap:`).
- **source_version** — `sha256` (hex, 64) of the **normalized derivative text** (UTF-8, LF line endings, NFC). Changes whenever the text changes.
- **chunk** — a contiguous piece of one source_version's text.
- **span** — `{start, end}` character offsets (Python `str` indices, end-exclusive) into that exact text. `text[start:end] == chunk.text` must always hold.
- **chunk_ref** — `chk:` + first 32 hex of `sha256(source_version + ":" + start + ":" + end)`. Stable across rebuilds; changes when the source version changes.
- **stale ref** — a `chunk_ref` whose source_version is no longer current → error `E_STALE_SOURCE`, never a remap.
- **inclusion_reason** — why a hit was returned: `fts-match`, `exact-match`, `alias-match`, `graph-neighbor`, `enrichment-topic` (the last is non-evidence and must say so).
- **receipt** — the JSON a write door returns: ids, hashes, `persisted`, `commit_state` (`committed` / `uncommitted`), warnings.

---

## 2. Invariants and Architectural Guarantees

1. **Deterministic derivations:** Chunking and source-version hashing are pure functions of derivative text. The same input yields identical chunk references across platforms and environments (LF line endings and NFC normalized).
2. **Search is a route, never evidence:** Retrieval scores or ranks organize attention; they never constitute evidence for claims or adjudications.
3. **Partitioned ranking:** Canonical corpus and capture records remain separate groups; their retrieval rankings are never merged into a single blended list.
4. **Candidate metadata isolation:** Model-generated metadata, enrichment, or candidate summaries are authority level 7 (candidate tier). Metadata may provide an `inclusion_reason` (e.g. `enrichment-topic`), but is explicitly marked `non_evidence: true` and cannot serve as evidentiary quotes.
5. **Fail closed on staleness:** When a `chunk_ref` is requested whose `source_version` does not match the active derivative version, the system returns `E_STALE_SOURCE` rather than guessing or remapping offsets.
