---
id: mw-doc-1.2.0-release-notes
type: system-document
title: "Release notes 1.2.0 — governed multimodal capture"
status: candidate
---
# 1.2.0 release notes (candidate)

Voice, text, handwriting, drawing, and file intake with provenance;
Telegram/Hermes capture-only path with zero conversational LLM calls;
Obsidian templates; governed MCP tools; capture search separated from
canonical search; LFS-backed media with restore procedure.

## Known limitations (honest)

1. **No automatic transcription.** No local STT runs on the Hermes host
   (faster-whisper broken: PyAV DLL). Manual transcription only until a
   benchmark passes (see `stt-benchmark-report.md`).
2. **No remote transcription.** No remote adapter ships; per-operation
   consent flow is specified but untested end-to-end.
3. **OCR is literal-only, English-tested.** RapidOCR extracts regions;
   Persian handwriting accuracy is unbenchmarked; interpretation is manual.
4. **Restore proof: executed 2026-09-05.** Clean local clone of the release
   branch: all 8 capture records validate and all 4 media files are real
   bytes (PNG/RIFF magic, zero LFS pointer files) after `git lfs pull`.
   Remote disaster recovery = clone from GitHub + `git lfs fetch origin main`
   + `git lfs checkout` (same object store; LFS objects verified pushed).
5. **Telegram hook is code + simulated tests.** Real voice-message delivery
   needs the Wiki Inbox wiring + one live message from Mohammad.
6. Duplicate voice deliveries store a second media copy (processing is
   deduplicated; bytes are retained per record for provenance independence).
7. QMD `wiki` collection also matches the intake tree; separation is
   enforced in `wiki_search` code (collection scope + path filter), not in
   qmd collection config.

## Costs

Local path: 0 model calls, 0 network. No paid service is configured.
