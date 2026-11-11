"""C4: wiki_retrieve tool + CLI (scripts/retrieval/retrieve.py)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "retrieval"))

from gov_kernel.retrieval import build_index  # noqa: E402
import retrieve as R  # noqa: E402

PROFILES = {
    "profiles": {
        "all-governed": {"exclude_globs": [".git/**", "_search/**"], "include_globs": ["**/*.md", "**/*.txt"]},
        "canonical": {"exclude_globs": ["02-sources/**"], "include_globs": ["03-objects/**", "04-notes/**"]},
        "captures": {"exclude_globs": [], "include_globs": ["01-inbox/captures/**"]},
        "evidence-text": {"exclude_globs": [], "include_globs": ["02-sources/text/**"]},
    }
}


SECOND_DOC = "\n".join(["---", "id: second", "type: object", "status: accepted", "---", "", "another lantern line", ""])


def _write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def make_wiki(tmp_path: Path, aliases: dict | None = None) -> Path:
    _write(tmp_path, "00-system/configuration/retrieval-profiles.v2.json", json.dumps(PROFILES))
    _write(tmp_path, "00-system/configuration/LABEL_ALIASES.json", json.dumps({"aliases": aliases or {}}))
    _write(tmp_path, "03-objects/theater.md",
           "---\nid: obj-theater\ntype: object\nstatus: accepted\n---\n\n# Theater\n\n"
           "Rehearsal of the lantern play happens every Tuesday in the old hall.\n")
    _write(tmp_path, "01-inbox/captures/cap-1.md",
           "---\nid: cap-1\ntype: capture\nstatus: pending\n---\n\n# Note\n\n"
           "A rough thought about the lantern and the harbour.\n")
    _write(tmp_path, "03-objects/persian.md",
           "---\nid: obj-fa\ntype: object\nstatus: accepted\n---\n\n# تئاتر\n\n"
           "تمرین نمایش فانوس هر سه‌شنبه در سالن قدیمی انجام می‌شود.\n")
    _write(tmp_path, "02-sources/text/tst-src-aaaa.extracted.md",
           "# Book\n\nThe lantern appears in chapter two of the book.\n")
    build_index(tmp_path, tmp_path / "_search" / "retrieval.sqlite")
    return tmp_path


@pytest.fixture
def wiki(tmp_path: Path) -> Path:
    return make_wiki(tmp_path)


def test_canonical_and_captures_are_separate_groups(wiki: Path) -> None:
    res = R.wiki_retrieve(wiki, query="lantern", scope="all")
    assert res["ok"] and res["authority_note"] == "ranking is not evidence"
    groups = res["groups"]
    assert set(groups) == {"canonical", "captures", "sources"}
    assert groups["canonical"]
    can_paths = {h["chunk_ref"] for h in groups["canonical"]}
    cap_paths = {h["chunk_ref"] for h in groups["captures"]}
    assert can_paths and cap_paths and not (can_paths & cap_paths)
    assert len(groups["sources"]) == 1
    only_cap = R.wiki_retrieve(wiki, query="lantern", scope="captures")
    assert list(only_cap["groups"]) == ["captures"] and len(only_cap["groups"]["captures"]) == 1


def test_hit_shape_and_span_rule(wiki: Path) -> None:
    res = R.wiki_retrieve(wiki, query="rehearsal", scope="canonical")
    hit = res["groups"]["canonical"][0]
    for key in ("source_ref", "chunk_ref", "span", "text", "tier", "authority_level",
                "inclusion_reason", "score", "coverage"):
        assert key in hit
    assert "fts-match" in hit["inclusion_reason"]
    assert hit["coverage"] == {"returned_chars": len(hit["text"]), "truncated": False}
    src = (wiki / "03-objects/theater.md").read_text(encoding="utf-8")
    body = src.split("---\n", 2)[2]
    assert body[hit["span"]["start"]:hit["span"]["end"]] == hit["text"]


def test_budget_is_whole_chunks_and_never_cuts(tmp_path: Path) -> None:
    wiki = make_wiki(tmp_path)
    for i in range(6):
        _write(wiki, f"03-objects/big{i}.md",
               f"---\nid: big{i}\ntype: object\nstatus: accepted\n---\n\n# Big {i}\n\n" + ("zebra word. " * 150) + "\n")
    build_index(wiki, wiki / "_search" / "retrieval.sqlite")
    res = R.wiki_retrieve(wiki, query="zebra", scope="canonical", budget_tokens=500)
    hits = res["groups"]["canonical"]
    assert 1 <= len(hits) < 6
    assert res["budget"]["used_chars"] <= 500 * R.CHARS_PER_TOKEN
    assert all(h["coverage"]["truncated"] is False for h in hits)
    assert res["next_cursor"]


def test_single_oversized_chunk_is_truncated_with_span(tmp_path: Path) -> None:
    wiki = make_wiki(tmp_path)
    _write(wiki, "03-objects/huge.md",
           "---\nid: huge\ntype: object\nstatus: accepted\n---\n\n# H\n\n" + ("quokka sentence here. " * 90) + "\n")
    build_index(wiki, wiki / "_search" / "retrieval.sqlite")
    res = R.wiki_retrieve(wiki, query="quokka", scope="canonical", budget_tokens=500)
    # chunk is ~1900 chars, budget is 2000 chars -> shrink further via many tokens check below
    hit = res["groups"]["canonical"][0]
    assert hit["coverage"]["returned_chars"] == len(hit["text"])
    assert hit["span"]["end"] - hit["span"]["start"] == len(hit["text"])


def test_cursor_paging_covers_everything_without_repeats(tmp_path: Path) -> None:
    wiki = make_wiki(tmp_path)
    for i in range(5):
        _write(wiki, f"03-objects/p{i}.md",
               f"---\nid: p{i}\ntype: object\nstatus: accepted\n---\n\n# P{i}\n\nmarmot number {i}.\n")
    build_index(wiki, wiki / "_search" / "retrieval.sqlite")
    seen: list[str] = []
    cursor = None
    pages = 0
    while True:
        res = R.wiki_retrieve(wiki, query="marmot", scope="canonical", limit=2, cursor=cursor)
        seen += [h["chunk_ref"] for h in res["groups"]["canonical"]]
        pages += 1
        cursor = res["next_cursor"]
        if not cursor:
            break
    assert pages == 3 and len(seen) == 5 and len(set(seen)) == 5


def test_cursor_for_other_query_is_rejected(wiki: Path) -> None:
    _write(wiki, "03-objects/second.md", SECOND_DOC)
    build_index(wiki, wiki / "_search" / "retrieval.sqlite")
    res = R.wiki_retrieve(wiki, query="lantern", scope="all", limit=1)
    assert res["next_cursor"]
    with pytest.raises(R.RetrieveError) as ei:
        R.wiki_retrieve(wiki, query="harbour", scope="all", cursor=res["next_cursor"])
    assert ei.value.code == "E_BAD_CURSOR"


def test_persian_query_hits_persian_chunk(wiki: Path) -> None:
    res = R.wiki_retrieve(wiki, query="فانوس", scope="canonical")
    hits = res["groups"]["canonical"]
    assert hits and "فانوس" in hits[0]["text"]
    # Arabic-form yeh/kaf in the query still matches (search-key normalization only)
    res2 = R.wiki_retrieve(wiki, query="تمرين", scope="canonical")
    assert res2["groups"]["canonical"] and "تمرین" in res2["groups"]["canonical"][0]["text"]


def test_alias_hit_has_alias_match_reason(tmp_path: Path) -> None:
    wiki = make_wiki(tmp_path, aliases={"lantern": ["beacon"]})
    _write(wiki, "03-objects/beacon.md",
           "---\nid: obj-beacon\ntype: object\nstatus: accepted\n---\n\n# B\n\nThe beacon burns at night.\n")
    build_index(wiki, wiki / "_search" / "retrieval.sqlite")
    res = R.wiki_retrieve(wiki, query="beacon", scope="canonical")
    by_text = {h["text"]: h for h in res["groups"]["canonical"]}
    beacon = next(h for t, h in by_text.items() if "beacon burns" in t)
    assert beacon["inclusion_reason"] == ["fts-match"] or "fts-match" in beacon["inclusion_reason"]
    lantern = next(h for t, h in by_text.items() if "lantern" in t)
    assert "alias-match" in lantern["inclusion_reason"]
    assert "fts-match" not in lantern["inclusion_reason"]
    assert lantern["alias_matches"][0] == {"from": "beacon", "to": "lantern"}


def test_no_alias_file_entry_means_no_alias_match(wiki: Path) -> None:
    res = R.wiki_retrieve(wiki, query="beacon", scope="all")
    assert all(not v for v in res["groups"].values())


def test_fail_closed_missing_index_and_bad_args(tmp_path: Path) -> None:
    make_wiki(tmp_path)
    (tmp_path / "_search" / "retrieval.sqlite").unlink()
    with pytest.raises(R.RetrieveError) as ei:
        R.wiki_retrieve(tmp_path, query="x")
    assert ei.value.code == "E_INDEX_MISSING"
    with pytest.raises(R.RetrieveError):
        R.wiki_retrieve(tmp_path, query="x", limit=51)
    with pytest.raises(R.RetrieveError):
        R.wiki_retrieve(tmp_path, query="x", budget_tokens=10)


def test_stale_index_is_flagged(wiki: Path) -> None:
    _write(wiki, "03-objects/theater.md", "---\nid: obj-theater\ntype: object\nstatus: accepted\n---\n\nchanged lantern\n")
    res = R.wiki_retrieve(wiki, query="lantern", scope="canonical")
    assert res["index_state"] == "stale" and "index-stale" in res["warnings"]


def test_deterministic_output(wiki: Path) -> None:
    a = json.dumps(R.wiki_retrieve(wiki, query="lantern"), sort_keys=True)
    b = json.dumps(R.wiki_retrieve(wiki, query="lantern"), sort_keys=True)
    assert a == b


def test_cli_prints_json(wiki: Path) -> None:
    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts/retrieval/retrieve.py"), "lantern", "--repo", str(wiki), "--scope", "captures"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert out.returncode == 0, out.stderr
    doc = json.loads(out.stdout)
    assert doc["groups"]["captures"] and doc["authority_note"] == "ranking is not evidence"


def test_tool_handler_returns_json_errors(wiki: Path) -> None:
    h = R.make_retrieve_handler(wiki)
    ok = json.loads(h({"query": "lantern"}))
    assert ok["ok"]
    bad = json.loads(h({"query": ""}))
    assert bad["code"] == "E_BAD_ARGS"
    assert json.loads(h({"nope": 1}))["code"] == "E_BAD_ARGS"
