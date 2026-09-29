from __future__ import annotations

import pathlib
from typing import Any

from .retrieval import open_current_result


def govern_qmd_hits(root: pathlib.Path, hits: list[dict[str, Any]], profile_name: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Convert optional QMD hits into governed current-repo candidates.

    QMD score/snippet can guide attention. The body/hash returned to the caller is
    always reloaded from the current checkout. Deleted/stale paths are rejected.
    """
    accepted=[]; rejected=[]
    for hit in hits:
        try:
            current=open_current_result(root,{**hit,"backend":"qmd"},profile_name)
            accepted.append({**hit,**current})
        except FileNotFoundError as exc:
            rejected.append({"path":hit.get("path"),"reason":"STALE_BACKEND_PATH","detail":str(exc)})
        except PermissionError as exc:
            rejected.append({"path":hit.get("path"),"reason":"AUTHORITY_PROFILE_REJECTED","detail":str(exc)})
    return accepted,rejected
