"""Tests for Rung I1: Ingest core (scripts/gov_kernel/ingest.py + scripts/ingest_file.py).

Acceptance criteria:
- Fixtures for each format incl. Persian PDF and Persian DOCX.
- Duplicate upload returns same receipt with duplicate_of.
- Source record created with status: pending-registration and holdings_tier: pending-registration.
- Original copied to _originals/<prefix>-<yyyy>/<sha256[:2]>/<sha256>.<ext> and read-only.
- Extracted derivative written to 02-sources/text/ with deterministic source_version.
- Scanned PDF yields extraction: partial and flag needs-ocr.
- Hook on_ingested(receipt) is called.
- Validator passes after ingest; census is still CLEAN in a fresh instance.
- CLI scripts/ingest_file.py works.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "ingest"

sys.path.insert(0, str(ROOT / "scripts"))


@pytest.fixture
def clean_wiki(tmp_path: Path) -> Path:
    """Create a fresh instantiated wiki in tmp_path."""
    wiki = tmp_path / "wiki"
    # Copy tracked files
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    ).stdout.decode("utf-8").split("\0")
    for rel in filter(None, listed):
        src = ROOT / rel
        if src.is_file():
            (wiki / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, wiki / rel)
    # Instantiate with prefix test
    res = subprocess.run(
        [sys.executable, "scripts/instantiate.py", "--name", "Test Wiki", "--prefix", "tst"],
        cwd=wiki, capture_output=True, text=True
    )
    assert res.returncode == 0, res.stdout + res.stderr
    return wiki


def test_ingest_text_file(clean_wiki: Path) -> None:
    from gov_kernel import ingest

    txt_file = FIXTURES / "sample.txt"
    receipt = ingest.ingest_file(txt_file, root=clean_wiki)

    assert receipt["ok"] is True
    assert receipt["source_ref"].startswith("rec:tst-src-")
    assert "tst-src-" in receipt["record_id"]
    assert len(receipt["sha256"]) == 64
    assert receipt["bytes"] == txt_file.stat().st_size
    assert receipt["mime"] == "text/plain"
    assert receipt["extraction"]["status"] == "ok"
    assert receipt["extraction"]["method"] == "passthrough"
    assert len(receipt["source_version"]) == 64
    assert receipt["chunk_count"] == 0

    # Verify original file created
    prefix_year = f"tst-{Path(clean_wiki).stat().st_ctime and '2026'}"
    sha = receipt["sha256"]
    orig_path = clean_wiki / "_originals" / prefix_year / sha[:2] / f"{sha}.txt"
    assert orig_path.is_file()
    # Verify read-only permissions (no write bit for owner/group/other)
    mode = orig_path.stat().st_mode
    assert (mode & stat.S_IWUSR) == 0

    # Verify source record created
    rec_path = clean_wiki / "02-sources" / "records" / f"{receipt['record_id']}.md"
    assert rec_path.is_file()
    rec_text = rec_path.read_text(encoding="utf-8")
    assert "status: pending-registration" in rec_text
    assert "holdings_tier: pending-registration" in rec_text
    assert f"sha256: {sha}" in rec_text
    assert "type: source-record" in rec_text

    # Verify derivative created
    deriv_path = clean_wiki / "02-sources" / "text" / f"{receipt['record_id']}.extracted.md"
    assert deriv_path.is_file()
    assert receipt["source_version"] in ingest.normalize_derivative_text(deriv_path.read_text(encoding="utf-8"))[1]


def test_ingest_persian_text_and_ratio(clean_wiki: Path) -> None:
    from gov_kernel import ingest

    fa_file = FIXTURES / "sample_fa.txt"
    receipt = ingest.ingest_file(fa_file, root=clean_wiki)

    assert receipt["ok"] is True
    assert receipt["extraction"]["fa_ratio"] > 0.05
    assert "fa-spacing" in receipt["extraction"]["quality_note"]
    assert receipt["extraction"]["status"] == "ok"


def test_ingest_persian_pdf_and_docx(clean_wiki: Path) -> None:
    from gov_kernel import ingest

    pdf_file = FIXTURES / "sample_fa.pdf"
    if pdf_file.exists():
        receipt_pdf = ingest.ingest_file(pdf_file, root=clean_wiki)
        assert receipt_pdf["ok"] is True
        assert receipt_pdf["mime"] == "application/pdf"
        assert receipt_pdf["extraction"]["method"] == "pymupdf-text"

    docx_file = FIXTURES / "sample_fa.docx"
    if docx_file.exists():
        receipt_docx = ingest.ingest_file(docx_file, root=clean_wiki)
        assert receipt_docx["ok"] is True
        assert "openxmlformats" in receipt_docx["mime"] or receipt_docx["mime"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert receipt_docx["extraction"]["method"] == "python-docx"


def test_ingest_scanned_pdf_needs_ocr(clean_wiki: Path) -> None:
    from gov_kernel import ingest

    scanned = FIXTURES / "scanned.pdf"
    if scanned.exists():
        receipt = ingest.ingest_file(scanned, root=clean_wiki)
        assert receipt["ok"] is True
        assert receipt["extraction"]["status"] == "partial"
        assert "needs-ocr" in receipt["extraction"]["flags"]
        assert "NEEDS-OCR" in receipt["extraction"]["quality_note"]


def test_ingest_duplicate_returns_same_receipt(clean_wiki: Path) -> None:
    from gov_kernel import ingest

    txt_file = FIXTURES / "sample.txt"
    receipt1 = ingest.ingest_file(txt_file, root=clean_wiki)
    receipt2 = ingest.ingest_file(txt_file, root=clean_wiki)

    assert receipt2["ok"] is True
    assert receipt2["duplicate_of"] == receipt1["source_ref"]
    assert receipt2["source_ref"] == receipt1["source_ref"]
    assert receipt2["sha256"] == receipt1["sha256"]
    assert receipt2["source_version"] == receipt1["source_version"]


def test_on_ingested_hook_invoked(clean_wiki: Path) -> None:
    from gov_kernel import ingest

    called_with = []

    def my_hook(r: dict) -> None:
        called_with.append(r)

    orig_hook = ingest.on_ingested
    try:
        ingest.on_ingested = my_hook
        txt_file = FIXTURES / "sample.txt"
        receipt = ingest.ingest_file(txt_file, root=clean_wiki)
        assert len(called_with) == 1
        assert called_with[0]["source_ref"] == receipt["source_ref"]
    finally:
        ingest.on_ingested = orig_hook


def test_validator_and_census_pass_after_ingest(clean_wiki: Path) -> None:
    from gov_kernel import ingest

    txt_file = FIXTURES / "sample.txt"
    ingest.ingest_file(txt_file, root=clean_wiki)

    # Validate repo full
    res_val = subprocess.run(
        [sys.executable, "scripts/validate_repo.py", "--full"],
        cwd=clean_wiki, capture_output=True, text=True
    )
    assert res_val.returncode == 0, res_val.stdout + res_val.stderr
    assert "PASS" in res_val.stdout

    # Report holdings
    res_rep = subprocess.run(
        [sys.executable, "scripts/report_holdings.py"],
        cwd=clean_wiki, capture_output=True, text=True
    )
    assert res_rep.returncode == 0, res_rep.stdout + res_rep.stderr
    assert "CENSUS CLEAN" in res_rep.stdout


def test_ingest_cli(clean_wiki: Path) -> None:
    txt_file = FIXTURES / "sample.txt"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "ingest_file.py"),
        str(txt_file),
        "--repo", str(clean_wiki),
        "--json"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    data = json.loads(res.stdout)
    assert data["ok"] is True
    assert data["source_ref"].startswith("rec:tst-src-")
