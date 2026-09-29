#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from gov_kernel.retrieval import exact_resolve,search_fts

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('query'); ap.add_argument('--repo',default='.'); ap.add_argument('--profile',default='canonical'); ap.add_argument('--db',default='_search/mozare-retrieval.sqlite'); ap.add_argument('--limit',type=int,default=10); a=ap.parse_args(); root=pathlib.Path(a.repo).resolve()
 exact=exact_resolve(root,a.query,a.profile); lexical=search_fts(root,root/a.db,a.query,a.profile,a.limit)
 print(json.dumps({'retrieval_mode':'portable-core','profile':a.profile,'exact':exact,'lexical':lexical},ensure_ascii=False,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
