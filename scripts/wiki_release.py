#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,pathlib,sys
from gov_kernel.release import verify_release,make_manifest,manifest_bytes
from gov_kernel.common import atomic_write

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo',default='.'); sub=ap.add_subparsers(dest='cmd',required=True)
 for name in ['verify','manifest']:
  p=sub.add_parser(name); p.add_argument('--profile',required=True); p.add_argument('--receipts',default='.git/mozare-governance-hardening/evidence')
 a=ap.parse_args(); root=pathlib.Path(a.repo).resolve(); profile=root/a.profile; receipts=root/a.receipts
 v=verify_release(root,profile,receipts); print(json.dumps(v,ensure_ascii=False,indent=2))
 if not v['ok']: return 1
 if a.cmd=='manifest':
  m=make_manifest(root,profile,v,sorted(p.stem for p in receipts.glob('*.json')) if receipts.exists() else []); out=root/'00-system/releases/manifests'/f"{m['release']}.json"
  if out.exists():
   if out.read_bytes()!=manifest_bytes(m): print(f'historical/existing manifest differs: {out}',file=sys.stderr); return 2
  else: atomic_write(out,manifest_bytes(m)); print(out)
 return 0
if __name__=='__main__': raise SystemExit(main())
