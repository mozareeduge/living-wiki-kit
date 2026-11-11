"""Upload staging for the HTTP transport (rung H2).

The store hands out opaque single-use refs; nothing here ever resolves a
caller-supplied filesystem path.
"""
from .store import UploadError, UploadStore, default_store  # noqa: F401
