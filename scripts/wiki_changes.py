#!/usr/bin/env python3
"""Who changed the wiki, and how to undo a wrong change (OM-888).

  record    stamp a change an agent just made (intake / reconcile / edit / audit / merge)
  feedback  the owner said wrong / outdated / not-needed at a hop -> retract or supersede
  restore   undo a correction (appends; nothing is deleted)
  trace     record id or path -> sources (sha256-checked) -> ledger rows
  check     every ledger row whole, stamped and unedited

Stamp flags are required on every write: --model --provider --effort --host --harness.
Examples:
  python scripts/wiki_changes.py record --action intake --level L2 --target mw-src-... \
      --model claude-opus-5-5 --provider anthropic --effort high --host nanobot --harness wiki-intake
  python scripts/wiki_changes.py feedback --target mw-claim-... --verdict outdated \
      --note "date moved to 2025" --replaced-by mw-claim-...-r2 --model ... (stamp)
  python scripts/wiki_changes.py trace mw-claim-...
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gov_kernel.changes import (ACTIONS, LEVELS, VERDICTS, LedgerError, append_change,  # noqa: E402
                                check_ledger, feedback, trace)
from gov_kernel.common import git  # noqa: E402


def _stamp(a: argparse.Namespace) -> dict[str, str]:
    return {"model": a.model, "provider": a.provider, "effort": a.effort, "host": a.host,
            "harness": a.harness, "skill": a.skill, "session_ref": a.session_ref}


def _add_stamp(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("stamp (who made this change)")
    for name in ("model", "provider", "effort", "host", "harness"):
        g.add_argument(f"--{name}", required=True)
    g.add_argument("--skill"); g.add_argument("--session-ref")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=str(pathlib.Path(__file__).resolve().parents[1]))
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record"); r.add_argument("--action", required=True, choices=sorted(ACTIONS - {"retract", "supersede", "restore"}))
    r.add_argument("--target", action="append", required=True); r.add_argument("--level", choices=sorted(LEVELS))
    r.add_argument("--reason", default=""); r.add_argument("--commit", help="commit sha; 'HEAD' resolves it")
    r.add_argument("--source", action="append", default=[], help="path=sha256 of a verbatim original this change rests on")
    _add_stamp(r)
    f = sub.add_parser("feedback"); f.add_argument("--target", required=True)
    f.add_argument("--verdict", required=True, choices=sorted(VERDICTS)); f.add_argument("--note", default="")
    f.add_argument("--replaced-by"); _add_stamp(f)
    u = sub.add_parser("restore"); u.add_argument("--change-id", action="append", required=True)
    u.add_argument("--reason", required=True); _add_stamp(u)
    t = sub.add_parser("trace"); t.add_argument("ref")
    sub.add_parser("check")
    a = ap.parse_args(argv)
    root = pathlib.Path(a.repo).resolve()
    try:
        if a.cmd == "record":
            commit = git(root, "rev-parse", "HEAD") if a.commit == "HEAD" else a.commit
            sources = [dict(zip(("path", "sha256"), s.split("=", 1))) for s in a.source]
            out = append_change(root, action=a.action, targets=a.target, stamp=_stamp(a), reason=a.reason,
                                level=a.level, sources=sources, commit=commit)
        elif a.cmd == "feedback":
            out = feedback(root, target=a.target, verdict=a.verdict, note=a.note, stamp=_stamp(a),
                           replaced_by=a.replaced_by)
        elif a.cmd == "restore":
            out = append_change(root, action="restore", targets=a.change_id, stamp=_stamp(a), reason=a.reason)
        elif a.cmd == "trace":
            out = trace(root, a.ref)
        else:
            problems = check_ledger(root)
            print(json.dumps({"ok": not problems, "problems": problems}, ensure_ascii=False, indent=2))
            return 1 if problems else 0
    except LedgerError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)); return 2
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
