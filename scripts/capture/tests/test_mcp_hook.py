#!/usr/bin/env python3
"""Task 8/7 gate: MCP capture tools + Telegram hook. Stdlib unittest only.

Run: python scripts/capture/tests/test_mcp_hook.py
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "scripts" / "capture"))
import wiki_capture as wc
import telegram_capture_hook as hook
import wiki_mcp_server as mcp


def call(name: str, args: dict) -> dict:
    resp = mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": name, "arguments": args}})
    return json.loads(resp["result"]["content"][0]["text"])


class HookTest(unittest.TestCase):
    def setUp(self):
        os.environ["MW_WIKI_ALLOW_USER"] = "u1"
        os.environ["MW_WIKI_INBOX_CHAT"] = "c1"

    def test_unauthorized_sender_keeps_normal_dispatch(self):
        r = hook.handle_voice("intruder", "c1", b"OggS" + b"\x00" * 64)
        self.assertFalse(r["ok"])
        self.assertEqual(r["dispatch"], "normal")

    def test_wrong_chat_keeps_normal_dispatch(self):
        r = hook.handle_text("u1", "other", "hello")
        self.assertFalse(r["ok"])
        self.assertEqual(r["dispatch"], "normal")

    def test_commands(self):
        self.assertEqual(hook.parse_command("/capture hi")["op"], "capture_text")
        d = hook.parse_command("/discuss cap-1 what?")
        self.assertEqual((d["op"], d["dispatch"]), ("discuss", "normal"))
        self.assertEqual(hook.parse_command("plain talk")["dispatch"], "normal")

    def test_zero_llm_imports(self):
        src = (REPO / "scripts" / "capture" / "telegram_capture_hook.py").read_text()
        core = (REPO / "scripts" / "capture" / "wiki_capture.py").read_text()
        for mod in ("openai", "anthropic", "transformers", "requests", "httpx", "urllib"):
            self.assertNotIn(f"import {mod}", src)
            self.assertNotIn(f"import {mod}", core)


CAPTURE_SURFACE = ("wiki_capture_text", "wiki_list_captures", "wiki_read_capture",
                   "wiki_get_capture_media", "wiki_search_captures",
                   "wiki_propose_from_capture", "wiki_mark_capture_reviewed",
                   "wiki_transcribe_capture")


def listed_tools() -> set:
    resp = mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    return {t["name"] for t in resp["result"]["tools"]}


class ReadProfileTest(unittest.TestCase):
    """The default profile is read-only: no capture/proposal tool is listed or callable."""

    def test_read_profile_hides_capture_surface(self):
        self.assertEqual(mcp.ACTIVE_PROFILE, "read")
        names = listed_tools()
        for tool in CAPTURE_SURFACE + ("wiki_propose",):
            self.assertNotIn(tool, names)

    def test_read_profile_refuses_capture_calls(self):
        resp = mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                           "params": {"name": "wiki_capture_text",
                                      "arguments": {"text": "x"}}})
        self.assertIn("not enabled in 'read' profile", resp["error"]["message"])


class MCPTest(unittest.TestCase):
    """Capture profile, isolated: captures and proposals land in a temp root,
    never in the real 01-inbox/ or _proposals/."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mcptest-"))
        shutil.copytree(REPO / "00-system" / "schemas", self.tmp / "00-system" / "schemas")
        self._saved = (mcp.ACTIVE_PROFILE, mcp.ROOT, wc.CAPTURES_ROOT, wc.ORPHAN_QUARANTINE)
        mcp.ACTIVE_PROFILE = "capture"
        mcp.ROOT = self.tmp
        wc.CAPTURES_ROOT = self.tmp / "01-inbox" / "captures"
        wc.ORPHAN_QUARANTINE = wc.CAPTURES_ROOT / ".quarantine"
        wc.CAPTURES_ROOT.mkdir(parents=True)

    def tearDown(self):
        mcp.ACTIVE_PROFILE, mcp.ROOT, wc.CAPTURES_ROOT, wc.ORPHAN_QUARANTINE = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_tools_list_has_capture_surface(self):
        names = listed_tools()
        for want in CAPTURE_SURFACE:
            self.assertIn(want, names)

    def test_mark_reviewed_requires_a_named_actor(self):
        cid = call("wiki_capture_text", {"text": "review probe", "channel": "mcp"})["id"]
        bad = call("wiki_mark_capture_reviewed", {"id": cid, "actor": " "})
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["code"], "E_NO_ACTOR")
        # The capture core's state machine still applies: a fresh capture
        # cannot jump straight to reviewed.
        early = call("wiki_mark_capture_reviewed", {"id": cid, "actor": "owner"})
        self.assertEqual(early["code"], "E_BAD_TRANSITION")
        wc.set_state(cid, "processing", "owner")
        wc.set_state(cid, "needs-review", "owner")
        ok = call("wiki_mark_capture_reviewed", {"id": cid, "actor": "owner", "note": "t"})
        self.assertTrue(ok["ok"], ok)
        self.assertEqual(call("wiki_read_capture", {"id": cid})["front_matter"]["status"],
                         "reviewed")

    def test_transcribe_unknown_capture_is_a_json_error(self):
        r = call("wiki_transcribe_capture", {"id": "cap-20000101-000000-dead",
                                             "adapter": "manual", "text": "t"})
        self.assertFalse(r["ok"])

    def test_capture_roundtrip(self):
        r = call("wiki_capture_text", {"text": "mcp hook probe", "channel": "mcp"})
        self.assertTrue(r["ok"])
        cid = r["id"]
        self.assertIn("noncanonical", r["authority_note"].lower())
        lst = call("wiki_list_captures", {"channel": "mcp"})
        self.assertTrue(any(c["id"] == cid for c in lst["captures"]))
        one = call("wiki_read_capture", {"id": cid})
        self.assertEqual(one["front_matter"]["id"], cid)
        media = call("wiki_get_capture_media", {"id": cid})
        self.assertEqual(media["code"], "E_NO_MEDIA")
        bad = call("wiki_read_capture", {"id": "../x"})
        self.assertFalse(bad["ok"])

    def test_search_stays_in_captures(self):
        call("wiki_capture_text", {"text": "mcp hook probe", "channel": "mcp"})
        r = call("wiki_search_captures", {"query": "mcp hook probe"})
        self.assertTrue(r["count"] >= 1)
        self.assertTrue(all(h["id"].startswith("cap-") for h in r["hits"]))
        self.assertIn("noncanonical", r["authority_note"].lower())

    def test_propose_cites_hash(self):
        r = call("wiki_capture_text", {"text": "promotion candidate xyz", "channel": "mcp"})
        p = call("wiki_propose_from_capture", {"ids": [r["id"]], "note": "test proposal"})
        self.assertTrue(p.get("accepted"))
        self.assertEqual(p["authority_tier"], "candidate")
        rec = json.loads((self.tmp / p["proposal_path"]).read_text(encoding="utf-8"))
        sha = call("wiki_read_capture", {"id": r["id"]})["front_matter"]["sha256"]
        self.assertIn(f"capture:{r['id']}:{sha}", rec["evidence_refs"])

    def test_unknown_tool(self):
        resp = mcp.handle({"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                           "params": {"name": "wiki_rm_rf", "arguments": {}}})
        self.assertEqual(resp["error"]["code"], -32602)
        self.assertIn("wiki_rm_rf", resp["error"]["message"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
