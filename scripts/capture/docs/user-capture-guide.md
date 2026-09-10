---
id: mw-doc-capture-guide
type: system-document
title: "Capture user guide (1.2.0)"
status: candidate
---
# Capture in one page

## Three routes (pick one per note)

1. **Telegram voice (archive-grade).** Send a voice message in the `Wiki Inbox`
   chat. You get a receipt: capture ID, duration, language, status.
   The audio is preserved; transcription runs only after review or a passing
   benchmark. Zero chat replies are generated.
2. **Obsidian.** New note from template `Capture – rough text`, or record
   audio / attach a photo, then run the `capture` command. Nothing becomes
   canonical by being edited.
3. **Claude mobile dictation.** Say the exact-text instruction
   (see `mobile-capture-instruction.md`). Text-only: no audio is kept.

## After capture

- `wiki_list_captures` / `list` — find by state, kind, channel, date.
- `wiki_read_capture` / `read` — inspect raw text, transcript, description,
  review notes, provenance.
- Correct a transcript: `commit-transcript` (manual) or edit then
  `set-state … reviewed --actor <you> --note <what you fixed>`.
- Want it in the wiki? `wiki_propose_from_capture` — a human approves first.
  Captures never promote themselves.

## What never happens automatically

No summaries, titles, tags, replies, or canonical publication.
Remote transcription only if you explicitly choose a provider per operation.
