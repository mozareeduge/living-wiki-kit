---
id: mw-doc-capture-admin
type: system-document
title: "Capture administrator setup (1.2.0)"
status: candidate
---
# Admin setup

## Telegram / Hermes (Task 7)

1. Create a private chat or topic named `Wiki Inbox`. Note its exact chat/topic ID.
2. On the Hermes host, set (never in Git):
   `MW_WIKI_ALLOW_USER=<exact Telegram user id>`
   `MW_WIKI_INBOX_CHAT=<exact Wiki Inbox chat/topic id>`
3. Register `scripts/capture/telegram_capture_hook.py` as the pre-dispatch
   handler for voice messages and `/capture*` commands in that destination
   only. Capture-only events must stop normal agent dispatch.
4. Test: `python scripts/capture/telegram_capture_hook.py --selftest`
   (expects refusals for intruder/wrong-chat, never a capture).
5. Secrets live in Hermes host env / secret store. No tokens in the repo.

## Obsidian (Task 6)

1. Enable the core **Audio Recorder** plugin (ships disabled).
2. Set attachments to the governed intake: recordings/images land under
   `01-inbox/captures/<YYYY>/<MM>/media/` (or a staging folder consumed by
   the capture CLI — never a canonical area).
3. Copy the five templates from `scripts/capture/obsidian-templates/` into
   the vault templates folder: rough text, voice, handwriting/drawing,
   transcript review, promotion proposal.
4. Mobile + desktop use is identical: template → capture → review.

## MCP clients (Task 8)

Register locally (never commit interpreter paths):
`"wiki-governance": {"command": "<python>", "args": ["scripts/wiki_mcp_server.py"]}`.
Give each client read-only access first (`wiki_list/read/search_captures`);
enable `wiki_capture_text` / `wiki_propose_from_capture` per client after.
No client gets arbitrary filesystem tools for wiki discussion.

## Backups (Task 4)

- LFS patterns for `01-inbox/captures/**` audio+images are in `.gitattributes`.
- Backup must `git lfs fetch --all` (pointers alone are not a backup).
- Restore test: clone elsewhere, `git lfs pull`, re-run
  `wiki_capture.py validate` — every record must resolve byte-identical media.
- Captures over the size cap stay local-only and are referenced, not committed.
