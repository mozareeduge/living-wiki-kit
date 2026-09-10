---
name: wiki-voice-capture
description: "Use when a voice/text needs archiving in the instantiated wiki."
---

# Wiki voice capture (living-wiki-kit)

Route spoken or typed material into the governed capture inbox. Nothing here
promotes anything to canonical — capture is always noncanonical until human
review.

## When to fire

1. User says a trigger phrase: "wiki capture", "ingest in wiki",
   "capture this in the wiki", "archive this".
2. A VOICE transcript whose content is clearly archive material (literature,
   research, sources, genetic criticism, project notes) — SUGGEST capture in
   one line; do not capture unbidden: "Want me to capture this in the wiki
   inbox? (say: wiki capture)"
3. Plain voice/text with no wiki relevance → behave normally.

## How to capture

Run the deterministic CLI from the repo root
(`<wiki-repo-root>`):

```bash
# text (a transcript, a note):
python scripts/capture/wiki_capture.py capture-text --channel mcp --lang fa --text "<exact text>"

# an audio/image file the user attached:
python scripts/capture/wiki_capture.py capture-media --src "<path-to-file>" --kind voice --channel mcp --lang fa
```

- channel: `mcp` when Hermes/agent does it; kind is `voice` for audio,
  `handwriting` for photos of writing, `image`/`file` otherwise.
- `--lang` is the language hint: fa | en | mixed | unknown.
- If the audio file itself is available (Telegram voice saves to the
  gateway media dir; Obsidian saves where configured), capture the MEDIA too
  — raw audio is evidence. Then commit the transcript onto it:

```bash
python scripts/capture/wiki_capture.py commit-transcript --id <capture-id> --text "<transcript>" --adapter hermes-local-whisper-small --version 1.2.1
```

## Rules (non-negotiable, mirror AGENTS.md)

- Capture the user's words VERBATIM. No summaries, titles, or tags.
- Report back only: capture ID, status, path. The ID is the receipt.
- Never write into 00-07 dirs or _originals/; promotion is proposal-only
  (`wiki_propose` / PATCH_MANIFEST after human review).
- Duplicate delivery is safe — the core dedups by content hash.
- Validation before claiming success: `python scripts/capture/wiki_capture.py --json validate`.
