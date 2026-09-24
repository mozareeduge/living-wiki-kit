#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from gov_kernel.retrieval import build_index,FTS5Unavailable

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo',default='.'); ap.add_argument('--db',default='_search/mozare-retrieval.sqlite'); a=ap.parse_args(); root=pathlib.Path(a.repo).resolve()
 try: result=build_index(root,root/a.db)
 except FTS5Unavailable: result={'capability':'FTS5_UNAVAILABLE','results':[]}; print(json.dumps(result)); return 2
 print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
