from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any

FA_CHARS = set("ابپتثجچحخدرزژسشصضطظعغفقکگلمنوهیيىةك")
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")
SENTENCE_SPLIT_RE = re.compile(r"([.!?؟۔]+[\"\'»\)\}\]]*)(?=\s+|$)")


@dataclass(frozen=True)
class Chunk:
    chunk_ref: str
    source_ref: str
    source_version: str
    span: dict[str, int]
    text_sha256: str
    heading_path: list[str]
    language_hint: str
    char_len: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_derivative_text(raw_text: str) -> str:
    """Normalize derivative text to LF line endings and Unicode NFC."""
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFC", text)


def compute_source_version(normalized_text: str) -> str:
    """Compute sha256 (hex, 64) of normalized derivative text."""
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()


def compute_chunk_ref(source_version: str, start: int, end: int) -> str:
    """chk: + first 32 hex of sha256(source_version + ':' + start + ':' + end)."""
    raw = f"{source_version}:{start}:{end}".encode("utf-8")
    return f"chk:{hashlib.sha256(raw).hexdigest()[:32]}"


def detect_language_hint(text: str) -> str:
    """Infer language hint: fa, mixed, en, or unknown."""
    has_fa = any(c in FA_CHARS for c in text)
    has_en = any("a" <= c.lower() <= "z" for c in text)
    if has_fa and has_en:
        return "mixed"
    if has_fa:
        return "fa"
    if has_en:
        return "en"
    return "unknown"


def _split_oversized_block(
    text: str,
    block_start: int,
    block_end: int,
    target_chars: int,
    max_chars: int,
) -> list[tuple[int, int]]:
    block_text = text[block_start:block_end]
    if len(block_text) <= max_chars:
        return [(block_start, block_end)]

    sentences: list[tuple[int, int]] = []
    cursor = 0
    for match in SENTENCE_SPLIT_RE.finditer(block_text):
        punct_end = match.end()
        s_text = block_text[cursor:punct_end]
        s_l = len(s_text) - len(s_text.lstrip())
        s_r = len(s_text.rstrip())
        if s_r > s_l:
            sentences.append((block_start + cursor + s_l, block_start + cursor + s_r))
        cursor = punct_end

    if cursor < len(block_text):
        rem = block_text[cursor:]
        r_l = len(rem) - len(rem.lstrip())
        r_r = len(rem.rstrip())
        if r_r > r_l:
            sentences.append((block_start + cursor + r_l, block_start + cursor + r_r))

    if not sentences:
        return [(block_start, block_end)]

    refined: list[tuple[int, int]] = []
    for s_start, s_end in sentences:
        s_len = s_end - s_start
        if s_len <= max_chars:
            refined.append((s_start, s_end))
        else:
            sub_cur = s_start
            while sub_cur < s_end:
                sub_rem = text[sub_cur:s_end]
                if len(sub_rem) <= max_chars:
                    refined.append((sub_cur, s_end))
                    break
                slice_window = text[sub_cur:sub_cur + max_chars]
                last_space = max(slice_window.rfind(" "), slice_window.rfind("\t"), slice_window.rfind("\n"))
                if last_space > 0:
                    split_pt = sub_cur + last_space
                    refined.append((sub_cur, split_pt))
                    sub_cur = split_pt
                    while sub_cur < s_end and text[sub_cur].isspace():
                        sub_cur += 1
                else:
                    split_pt = sub_cur + max_chars
                    refined.append((sub_cur, split_pt))
                    sub_cur = split_pt

    packed: list[tuple[int, int]] = []
    curr_start: int | None = None
    curr_end: int | None = None

    for sent_start, sent_end in refined:
        if curr_start is None:
            curr_start = sent_start
            curr_end = sent_end
            continue

        proposed_len = sent_end - curr_start
        if proposed_len <= target_chars:
            curr_end = sent_end
        else:
            packed.append((curr_start, curr_end))
            curr_start = sent_start
            curr_end = sent_end

    if curr_start is not None and curr_end is not None:
        packed.append((curr_start, curr_end))

    return packed


@dataclass
class _Block:
    start: int
    end: int
    is_heading: bool
    heading_path: list[str]


def chunk_text(
    text: str,
    *,
    source_ref: str = "",
    source_version: str | None = None,
    target_chars: int = 1200,
    max_chars: int = 2000,
    language_hint: str | None = None,
) -> list[Chunk]:
    """Deterministically segment normalized derivative text into chunks with spans."""
    norm_text = normalize_derivative_text(text)
    if not norm_text or norm_text.isspace():
        return []

    if source_version is None:
        source_version = compute_source_version(norm_text)

    # 1. Parse into lines with character offsets
    lines = norm_text.split("\n")
    line_offsets: list[int] = []
    off = 0
    for line in lines:
        line_offsets.append(off)
        off += len(line) + 1  # 1 for '\n'

    heading_stack: list[tuple[int, str]] = []
    raw_blocks: list[_Block] = []
    active_para_start: int | None = None
    active_para_end: int | None = None

    for i, line in enumerate(lines):
        line_start = line_offsets[i]
        line_end = line_start + len(line)
        stripped = line.strip()

        if not stripped:
            if active_para_start is not None and active_para_end is not None:
                curr_path = [t for _, t in heading_stack]
                raw_blocks.append(_Block(active_para_start, active_para_end, False, curr_path))
                active_para_start = None
                active_para_end = None
            continue

        hm = HEADING_RE.match(line)
        if hm:
            if active_para_start is not None and active_para_end is not None:
                curr_path = [t for _, t in heading_stack]
                raw_blocks.append(_Block(active_para_start, active_para_end, False, curr_path))
                active_para_start = None
                active_para_end = None

            level = len(hm.group(1))
            title = hm.group(2).strip()
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, title))
            curr_path = [t for _, t in heading_stack]

            # Headings point to the stripped non-whitespace boundaries of the line
            l_strip = len(line) - len(line.lstrip())
            r_strip = len(line.rstrip())
            raw_blocks.append(_Block(line_start + l_strip, line_start + r_strip, True, curr_path))
        else:
            l_strip = len(line) - len(line.lstrip())
            r_strip = len(line.rstrip())
            if active_para_start is None:
                active_para_start = line_start + l_strip
            active_para_end = line_start + r_strip

    if active_para_start is not None and active_para_end is not None:
        curr_path = [t for _, t in heading_stack]
        raw_blocks.append(_Block(active_para_start, active_para_end, False, curr_path))

    if not raw_blocks:
        return []

    # 2. Refine oversized paragraph blocks (> max_chars)
    blocks: list[_Block] = []
    for b in raw_blocks:
        if b.is_heading or (b.end - b.start <= max_chars):
            blocks.append(b)
        else:
            sub_spans = _split_oversized_block(norm_text, b.start, b.end, target_chars, max_chars)
            for s_start, s_end in sub_spans:
                blocks.append(_Block(s_start, s_end, False, b.heading_path))

    # 3. Pack blocks into chunks
    chunks: list[Chunk] = []
    curr_group: list[_Block] = []

    def flush_group() -> None:
        if not curr_group:
            return
        c_start = curr_group[0].start
        c_end = curr_group[-1].end
        c_text = norm_text[c_start:c_end]
        c_path = list(curr_group[0].heading_path)
        lang = language_hint or detect_language_hint(c_text)
        txt_sha = hashlib.sha256(c_text.encode("utf-8")).hexdigest()
        chk_ref = compute_chunk_ref(source_version, c_start, c_end)
        chunks.append(
            Chunk(
                chunk_ref=chk_ref,
                source_ref=source_ref,
                source_version=source_version,
                span={"start": c_start, "end": c_end},
                text_sha256=txt_sha,
                heading_path=c_path,
                language_hint=lang,
                char_len=len(c_text),
                text=c_text,
            )
        )
        curr_group.clear()

    for b in blocks:
        if not curr_group:
            curr_group.append(b)
            continue

        if b.is_heading:
            flush_group()
            curr_group.append(b)
            continue

        # Non-heading: check if packing would exceed target_chars
        combined_len = b.end - curr_group[0].start
        if combined_len <= target_chars:
            curr_group.append(b)
        else:
            flush_group()
            curr_group.append(b)

    flush_group()
    return chunks
