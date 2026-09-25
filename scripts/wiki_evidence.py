#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,pathlib
from gov_kernel.evidence import build_accepted_evidence, expected_evidence_bytes
from gov_kernel.provenance import build_provenance
from gov_kernel.common import write_if_changed

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo',default='.'); ap.add_argument('command',choices=['build','check']); a=ap.parse_args(); root=pathlib.Path(a.repo).resolve()
 prov=build_provenance(root); rows,state,findings=build_accepted_evidence(root,prov); data=expected_evidence_bytes(rows); p=root/'00-system/registers/ACCEPTED_EVIDENCE_INDEX.jsonl'
 drift=not p.exists() or p.read_bytes()!=data
 if a.command=='build': write_if_changed(p,data)
 print(json.dumps({'state':state,'findings':[f.to_dict() for f in findings],'drift':drift},ensure_ascii=False,indent=2))
 return 1 if findings or (a.command=='check' and drift) else 0
if __name__=='__main__': raise SystemExit(main())
