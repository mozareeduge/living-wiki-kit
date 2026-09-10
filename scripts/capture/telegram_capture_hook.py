#!/usr/bin/env python3
"""Zero-LLM Telegram/Hermes capture path — 1.2.0 (Task 7).

A pre-dispatch hook: permitted voice/text messages in the Wiki Inbox become
captures with receipts WITHOUT invoking the conversational agent loop.

Transport-agnostic by design: the caller (Hermes hook) downloads the Telegram
bytes and calls handle_voice()/handle_text(). This module validates identity,
bytes, and size, then funnels everything through the deterministic core.
It performs its OWN authorization (spec §9.1: pre-dispatch may run before
normal pairing/auth checks) and never raises — every failure is a receipt.

Config (environment, never in Git):
  MW_WIKI_ALLOW_USER  exact Telegram user id, e.g. 235217824
  MW_WIKI_INBOX_CHAT  exact chat/topic id for Wiki Inbox
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

SYS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SYS / "scripts" / "capture"))
import wiki_capture as wc

MAX_VOICE_BYTES = 25 * 1024 * 1024
MAX_VOICE_SECONDS = 600
VOICE_SUFFIXES = {".ogg", ".oga", ".opus", ".mp3", ".m4a", ".wav"}


def config() -> tuple[str | None, str | None]:
    return os.environ.get("MW_WIKI_ALLOW_USER"), os.environ.get("MW_WIKI_INBOX_CHAT")


def failure(message: str, code: str = "E_CAPTURE_REJECTED") -> dict:
    return {"ok": False, "code": code, "message": message, "dispatch": "normal"}


def _authorized(sender_id: str, chat_id: str) -> tuple[bool, str]:
    allow_user, inbox_chat = config()
    if not allow_user or not inbox_chat:
        return False, "capture route not configured (MW_WIKI_ALLOW_USER/CHAT unset)"
    if str(sender_id) != str(allow_user):
        return False, "sender not allowlisted"
    if str(chat_id) != str(inbox_chat):
        return False, "not the Wiki Inbox destination"
    return True, "ok"


def handle_voice(sender_id: str, chat_id: str, data: bytes,
                 suffix: str = ".ogg", duration_s: int | None = None,
                 language_hint: str = "unknown") -> dict:
    """Capture-only voice path. Returns receipt; dispatch=stop means the
    conversational agent loop must NOT run for this message."""
    ok, why = _authorized(sender_id, chat_id)
    if not ok:
        return failure(f"voice capture refused: {why}", "E_UNAUTHORIZED")
    if len(data) > MAX_VOICE_BYTES:
        return failure(f"voice message {len(data)} bytes exceeds cap")
    if not data:
        return failure("empty voice payload")
    if suffix.lower() not in VOICE_SUFFIXES:
        return failure(f"unsupported voice container: {suffix}")
    if duration_s is not None and duration_s > MAX_VOICE_SECONDS:
        return failure(f"voice duration {duration_s}s exceeds cap")
    digest = hashlib.sha256(data).hexdigest()
    first = wc.find_by_hash(digest)
    if first:
        return {"ok": True, "capture_id": first, "duplicate_of": first,
                "status": "received", "duration_s": duration_s,
                "language": language_hint, "needs_review": False,
                "dispatch": "stop",
                "message": f"duplicate voice; already {first}"}
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=suffix.lower(), delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        receipt = wc.capture_media(tmp_path, "voice", "telegram-hermes", language_hint)
    except wc.CaptureError as e:
        return failure(f"voice capture failed: {e.message}", e.code)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    # Local transcription only if a passing host benchmark exists; else the
    # transcript stays pending for explicit manual action (spec §6).
    auto_ok, _ = _auto_ok()
    return {"ok": True, "capture_id": receipt["id"], "duplicate_of": None,
            "status": receipt["status"], "duration_s": duration_s,
            "language": language_hint,
            "needs_review": not auto_ok,
            "transcription": "attempted" if auto_ok else "pending-manual",
            "dispatch": "stop",
            "message": f"voice captured as {receipt['id']}"}


def _auto_ok():
    from stt_contract import auto_transcription_allowed
    return auto_transcription_allowed()


def handle_text(sender_id: str, chat_id: str, text: str,
                language_hint: str = "unknown") -> dict:
    """/capture <text> path. Plain chat text outside Wiki Inbox keeps normal
    behavior (the caller only routes Wiki Inbox traffic here)."""
    ok, why = _authorized(sender_id, chat_id)
    if not ok:
        return failure(f"text capture refused: {why}", "E_UNAUTHORIZED")
    try:
        receipt = wc.capture_text(text, "telegram-hermes", language_hint)
    except wc.CaptureError as e:
        return failure(f"text capture failed: {e.message}", e.code)
    return {"ok": True, "capture_id": receipt["id"],
            "duplicate_of": receipt["duplicate_of"], "status": "received",
            "dispatch": "stop",
            "message": f"text captured as {receipt['id']}"}


def parse_command(text: str) -> dict:
    """Classify an explicit command. capture* are handled here without an
    agent turn; discuss passes through to normal dispatch WITH the capture
    context attached (explicit discuss, spec §2.1)."""
    t = (text or "").strip()
    if t.startswith("/capture ") and len(t) > 9:
        return {"op": "capture_text", "text": t[9:]}
    if t.startswith("/discuss "):
        rest = t[9:].split(None, 1)
        return {"op": "discuss", "capture_id": rest[0] if rest else None,
                "question": rest[1] if len(rest) > 1 else "",
                "dispatch": "normal"}
    if t.startswith("/retry_transcript "):
        return {"op": "retry_transcript",
                "capture_id": t[18:].strip(), "dispatch": "stop"}
    return {"op": "none", "dispatch": "normal"}


def retry_transcript(capture_id: str, actor: str = "telegram-op") -> dict:
    from stt_contract import transcribe_capture
    try:
        rec = wc.read_capture(capture_id)
        fm = rec["front_matter"]
        if fm["transcription_state"] == "complete":
            return failure("transcript already complete; correct it via review, not retry")
        out = transcribe_capture(capture_id, "manual")
        return {"ok": True, "capture_id": capture_id, "dispatch": "stop",
                "message": "manual transcription requested; send the corrected text"}
    except wc.CaptureError as e:
        return failure(e.message, e.code)


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser(prog="telegram_capture_hook")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        os.environ.setdefault("MW_WIKI_ALLOW_USER", "selftest-user")
        os.environ.setdefault("MW_WIKI_INBOX_CHAT", "selftest-chat")
        print(json.dumps({
            "unauthorized": handle_voice("intruder", "selftest-chat", b"x"),
            "wrong_chat": handle_text("selftest-user", "elsewhere", "hi"),
            "command": parse_command("/discuss cap-x what is this"),
        }, ensure_ascii=False, indent=1))
