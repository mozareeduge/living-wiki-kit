---
id: mw-doc-capture-privacy
type: system-document
title: "Capture privacy and remote-processing policy (1.2.0)"
status: candidate
---
# Privacy and remote processing

1. **Local by default.** Transcription runs on the Hermes host or another
   user-controlled machine. Audio never leaves the host without a decision.
2. **Per-operation consent.** Any paid/remote provider needs an explicit
   choice naming the provider BEFORE bytes are sent. No background cloud
   processing exists in 1.2.0.
3. **Uncertain audio stays home.** If local transcription is unsure, the
   recording is preserved, uncertain spans are flagged, review is requested.
4. **Logs are redacted.** Provenance events store timestamps, actions,
   tool/version, outcome, input hash. Never prompts, secrets, Telegram
   tokens, phone numbers, or full chat payloads.
5. **Deletion is deliberate.** Record deletion needs a recorded human decision
   with reason and is recoverable for 30 days. Nothing deletes `_originals/`,
   canonical areas, or history.
6. **No public surface.** The MCP server binds locally in 1.2.0.
