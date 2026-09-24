#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, pathlib, sys
from gov_kernel.runner import run_validator_commands


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--repo",default="."); ap.add_argument("--config",default="00-system/configuration/validators.json"); ap.add_argument("--format",choices=["human","json"],default="human")
    a=ap.parse_args(); root=pathlib.Path(a.repo).resolve(); findings,receipts=run_validator_commands(root,root/a.config)
    if a.format=="json": print(json.dumps({"findings":[f.to_dict() for f in findings],"receipts":receipts},ensure_ascii=False,indent=2))
    else:
        for f in findings: print(f"{f.severity.upper()} {f.check_id}: {f.message}")
        print(f"validators={len(receipts)} errors={sum(f.severity=='error' for f in findings)}")
    return 1 if any(f.severity=="error" for f in findings) else 0
if __name__=="__main__": raise SystemExit(main())
