---
name: wiki-file-to-md
description: Use when a content task arrives as a non-md file. Convert to clean md before ingest/evaluate/summarize; never process raw binaries.
---

# File-to-MD (wiki intake pre-step)

Content tasks (ingest, evaluate, summarize a source) run on clean md,
never on raw binaries. Convert first with `scripts/file-to-md/to_md.py`,
then process the md. This strips format garbage (PDF operators, docx XML,
HTML tags) that wastes tokens and pollutes quotes. The provenance header the
tool writes is evidence metadata: keep it intact through intake.

## When to Use

- A pdf/docx/pptx/xlsx/html/epub/txt arrives for a CONTENT task (intake,
  source record creation, derivative extraction).
- Don't use for: format tasks (fill a form, restyle a deck, fix layout).
- Don't use for: files already clean md/txt.

## How to Run

From the wiki repo root:

```
python scripts/file-to-md/to_md.py "C:/path/file.pdf" -o "C:/path/file.extracted.md"
```

It prints a JSON summary (method, chars, token estimate, needs_ocr flag).
Done = exit 0 + md exists.

In the archive flow, the extracted md becomes the **searchable derivative**
under `02-sources/text/`, linked from the source record's
`extracted_text_path`. The untouched file in `_originals/` remains
authoritative.

## Procedure

1. Run `to_md.py` on the source.
2. If `needs_ocr` is true (scanned PDF), do NOT invent text. Route:
   small (<10 pp) = render pages via pymupdf + `vision_analyze` each;
   large = ask user before any heavy install (marker-pdf ~5GB).
   If the vision backend fails, RapidOCR is the verified local fallback:
   `pip install rapidocr-onnxruntime` (~60MB), then per page:
   `pixmap(dpi=200)` -> `ocr(str(png))` -> join `item[1]` lines; add an
   OCR note to the provenance header.
3. If quality note says `fa-spacing`, Persian glyphs may be
   fragmented — verify quotes against the source before ingesting.
   Mark the source record `extraction_quality: partial` when uncertain.
4. Process the md. Keep the provenance header intact on any file you
   hand onward (evidence governance).

## Pitfalls

- Legacy `.doc/.xls/.ppt`, `.odt/.rtf`, zips: converter refuses cleanly
  (no LibreOffice/pandoc). Ask user for a modern export.
- xlsx sheets cap at 200 rows per sheet (noted in md). Ask for a slice
  if the content you need is past the cap.
- Windows MAX_PATH (260): if a source path or name pushes total length
  over ~255, `iterdir()`/`stat()` silently drop or fail on it
  (LongPathsEnabled=0). Fix: `shutil.copyfile("\\\\?\\ " + path, short_tmp)`,
  convert the temp copy, then restore the ORIGINAL name in the md's
  provenance header. Truncate only the output .md filename (keep header
  + manifest authoritative).
- Batch conversion of a folder: iterate with explicit file list + output
  existence check (idempotent re-runs pick up stragglers); verify the
  converted count against the actual disk file count before reporting
  done — silent skips are usually MAX_PATH victims.

## Verification

- md exists, non-empty, starts with `# Extracted from`.
- Spot-check one known string from the source appears in the md.
- Before claiming intake success: `python scripts/validate_repo.py --full`.
