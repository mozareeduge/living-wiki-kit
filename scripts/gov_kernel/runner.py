from __future__ import annotations

import json
import pathlib
import shlex
import subprocess
from typing import Any

from .findings import Finding


def run_validator_commands(root: pathlib.Path, config_path: pathlib.Path) -> tuple[list[Finding], list[dict[str, Any]]]:
    cfg=json.loads(config_path.read_text(encoding="utf-8"))
    findings: list[Finding]=[]; receipts=[]
    for item in cfg.get("validators",[]):
        check_id=str(item["check_id"]); cmd=item["command"]
        argv=cmd if isinstance(cmd,list) else shlex.split(str(cmd))
        cp=subprocess.run(argv,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        receipt={"check_id":check_id,"command":argv,"returncode":cp.returncode,"stdout":cp.stdout,"stderr":cp.stderr}
        receipts.append(receipt)
        if cp.returncode != 0:
            findings.append(Finding("VALIDATOR.RUNTIME_FAILURE","error",f"validator {check_id} exited {cp.returncode}",details={"command":argv,"stderr":cp.stderr[-4000:]},waivable=False))
            continue
        # Structured output is preferred. If declared json, parse failures fail closed.
        if item.get("output_format") == "json":
            try:
                data=json.loads(cp.stdout or "[]")
                rows=data.get("findings",[]) if isinstance(data,dict) else data
                if not isinstance(rows,list): raise ValueError("findings output is not list")
                for row in rows:
                    if row.get("severity") == "error":
                        findings.append(Finding(str(row.get("check_id") or check_id),"error",str(row.get("message") or "validator error"),path=row.get("path"),record_id=row.get("record_id"),waivable=bool(row.get("waivable",False)),details=row.get("details")))
            except Exception as exc:
                findings.append(Finding("VALIDATOR.RUNTIME_FAILURE","error",f"validator {check_id} emitted invalid structured output: {exc}",details={"stdout":cp.stdout[-4000:]},waivable=False))
    return findings,receipts
