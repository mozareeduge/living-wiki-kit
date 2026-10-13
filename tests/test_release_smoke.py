"""Q6: the fresh-wiki release check passes on the kit and fails, naming the
step, when a gate would fail in the new wiki."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import release_smoke  # noqa: E402


def test_fresh_wiki_passes_every_gate(tmp_path: Path) -> None:
    ok, log = release_smoke.run(ROOT, tmp_path, echo=lambda s: None)
    assert ok, "\n".join(log)
    assert log[-1] == "PASS  instantiate rerun byte-identical"
    assert any(line.startswith("PASS  report_holdings") for line in log)


def test_injected_validator_error_fails_and_names_the_step(tmp_path: Path) -> None:
    def break_it(wiki: Path) -> None:
        bad = wiki / "02-sources" / "records" / "ciw-src-0123456789ab--broken.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text("---\nid: ciw-src-0123456789ab\ntype: source-record\n---\n\nNo fields.\n",
                       encoding="utf-8")

    ok, log = release_smoke.run(ROOT, tmp_path, after_instantiate=break_it,
                                echo=lambda s: None)
    assert not ok
    assert log[-1].startswith("FAIL  validate_repo --full"), log
    # the kit itself is untouched by the run
    assert not (ROOT / "02-sources" / "records" / "ciw-src-0123456789ab--broken.md").exists()
