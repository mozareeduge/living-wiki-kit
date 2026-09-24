#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, pathlib, sys
from gov_kernel.common import write_if_changed
from gov_kernel.evidence import build_accepted_evidence, expected_evidence_bytes
from gov_kernel.provenance import build_provenance, expected_generated_bytes
from gov_kernel.state import rebuild_state, set_axis, state_bytes


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--repo",default="."); sub=ap.add_subparsers(dest="cmd",required=True)
    sub.add_parser("rebuild"); sub.add_parser("check"); s=sub.add_parser("set-axis"); s.add_argument("axis"); s.add_argument("value")
    a=ap.parse_args(); root=pathlib.Path(a.repo).resolve()
    if a.cmd in {"rebuild","check"}:
        prov=build_provenance(root); erows,_,ef=build_accepted_evidence(root,prov); st,sf=rebuild_state(root); findings=[*prov.findings,*ef,*sf]
        expected={**expected_generated_bytes(prov),"00-system/registers/ACCEPTED_EVIDENCE_INDEX.jsonl":expected_evidence_bytes(erows),"00-system/registers/SYSTEM_STATE.json":state_bytes(st)}
        drift=[]
        for rel,data in expected.items():
            p=root/rel
            if not p.exists() or p.read_bytes()!=data: drift.append(rel)
            if a.cmd=="rebuild": write_if_changed(p,data)
        if findings:
            for f in findings: print(f"ERROR {f.check_id}: {f.message}",file=sys.stderr)
        if a.cmd=="check" and drift: print("STATE.GENERATED_DRIFT: "+", ".join(drift),file=sys.stderr)
        return 1 if findings or (a.cmd=="check" and drift) else 0
    if a.cmd=="set-axis":
        state=set_axis(root,a.axis,a.value); (root/"00-system/registers/SYSTEM_STATE.json").write_bytes(state_bytes(state)); return 0
    return 2
if __name__=="__main__": raise SystemExit(main())
