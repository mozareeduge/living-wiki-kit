from __future__ import annotations

import json
import pathlib
from typing import Any

from .common import git, stable_json_bytes
from .schemas import validate_record


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_release(root: pathlib.Path, profile_path: pathlib.Path, receipt_dir: pathlib.Path | None = None) -> dict[str, Any]:
    profile=load_json(profile_path)
    state=load_json(root/"00-system/registers/SYSTEM_STATE.json")
    findings=[]
    for key,state_path in [
        ("system_mechanism_version",("system","mechanism_version")),
        ("content_release",("content","release")),
        ("capture_version",("capture","version")),
        ("schema_version",("system","schema_version")),
    ]:
        expected=profile.get(key)
        if expected is None: continue
        node=state
        for part in state_path: node=node.get(part,{}) if isinstance(node,dict) else None
        if node != expected:
            findings.append({"check_id":"RELEASE.STATE_MISMATCH","severity":"error","message":f"{key}: expected {expected!r}, got {node!r}"})
    pairs=[("required_source_snapshot",state.get("source_corpus",{}).get("snapshot_id")),("required_evidence_snapshot",state.get("accepted_evidence",{}).get("snapshot_id"))]
    for k,actual in pairs:
        expected=profile.get(k)
        if expected is not None and expected != actual:
            findings.append({"check_id":"RELEASE.SNAPSHOT_MISMATCH","severity":"error","message":f"{k}: expected {expected!r}, got {actual!r}"})
    receipts={}
    if receipt_dir and receipt_dir.exists():
        for p in receipt_dir.glob("*.json"):
            try: receipts[p.stem]=load_json(p)
            except Exception: pass
    for check in profile.get("required_checks",[]):
        r=receipts.get(str(check))
        if not r or r.get("status") not in {"PASS","PASS_ENFORCED"}:
            findings.append({"check_id":"RELEASE.REQUIRED_CHECK_MISSING","severity":"error","message":f"required check not passed: {check}"})
    for manual in profile.get("required_manual_receipts",[]):
        if str(manual) not in receipts:
            findings.append({"check_id":"RELEASE.REQUIRED_RECEIPT_MISSING","severity":"error","message":f"manual receipt missing: {manual}"})
    sf=validate_record(profile,root/"00-system/schemas",explicit_schema="release-profile.schema.json")
    findings.extend(f.to_dict() for f in sf)
    return {"ok":not any(f.get("severity")=="error" for f in findings),"profile":str(profile_path),"candidate_sha":git(root,"rev-parse","HEAD"),"source_snapshot":state.get("source_corpus",{}).get("snapshot_id"),"evidence_snapshot":state.get("accepted_evidence",{}).get("snapshot_id"),"findings":findings}


def make_manifest(root: pathlib.Path, profile_path: pathlib.Path, verification: dict[str, Any], receipt_ids: list[str] | None = None) -> dict[str, Any]:
    if not verification.get("ok"):
        raise RuntimeError("release verification failed; manifest generation blocked")
    profile=load_json(profile_path); state=load_json(root/"00-system/registers/SYSTEM_STATE.json")
    manifest={
      "type":"release-manifest",
      "release":profile["release"],
      "commit":git(root,"rev-parse","HEAD"),
      "tree":git(root,"rev-parse","HEAD^{tree}"),
      "system":state.get("system"),"content":state.get("content"),"capture":state.get("capture"),
      "source_corpus":state.get("source_corpus"),"accepted_evidence":state.get("accepted_evidence"),
      "validator_version":profile.get("validator_version"),
      "retrieval_benchmark_receipt":profile.get("retrieval_benchmark_receipt"),
      "receipt_ids":sorted(receipt_ids or []),
      "waivers":profile.get("accepted_waivers",[]),
    }
    sf=validate_record(manifest,root/"00-system/schemas",explicit_schema="release-manifest.schema.json")
    if sf: raise ValueError("; ".join(f.message for f in sf))
    return manifest


def manifest_bytes(manifest: dict[str, Any]) -> bytes:
    return stable_json_bytes(manifest)
