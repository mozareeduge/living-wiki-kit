from __future__ import annotations

import re
import unicodedata

_ARABIC_DIACRITICS = re.compile(r"[\u064b-\u065f\u0670\u06d6-\u06ed]")
_SPACE_AROUND_ZWNJ = re.compile(r"\s*\u200c\s*")
_MULTI_SPACE = re.compile(r"[\t \u00a0]+")


def normalize_persian_for_search(text: str) -> str:
    """Deterministic search-only normalization; never write back to source text."""
    out = unicodedata.normalize("NFC", text)
    out = out.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    out = _ARABIC_DIACRITICS.sub("", out)
    out = _SPACE_AROUND_ZWNJ.sub("\u200c", out)
    out = _MULTI_SPACE.sub(" ", out)
    return out
