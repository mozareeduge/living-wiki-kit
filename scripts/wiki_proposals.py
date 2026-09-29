#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,pathlib
from gov_kernel.proposals import create_proposal, adjudicate, pending

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo',default='.'); sub=ap.add_subparsers(dest='cmd',required=True)
 c=sub.add_parser('create'); c.add_argument('--kind',required=True); c.add_argument('--body',required=True); c.add_argument('--tool',default='repository-operator')
 d=sub.add_parser('adjudicate'); d.add_argument('proposal_id'); d.add_argument('decision',choices=['accepted','rejected','deferred']); d.add_argument('--by',required=True); d.add_argument('--note',required=True)
 sub.add_parser('pending'); a=ap.parse_args(); root=pathlib.Path(a.repo).resolve()
 if a.cmd=='create': print(create_proposal(root,kind=a.kind,body=a.body,submitted_by={'actor_type':'agent','tool':a.tool})); return 0
 if a.cmd=='adjudicate': print(adjudicate(root,proposal_id=a.proposal_id,decision=a.decision,by=a.by,decision_note=a.note)); return 0
 print(json.dumps(pending(root),ensure_ascii=False,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
