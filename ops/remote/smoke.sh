#!/usr/bin/env bash
# Scripted smoke for a running wiki MCP server (H4):
#   healthz -> status -> capture -> search -> ingest fixture -> retrieve
# Usage: smoke.sh [--read-only] [BASE_URL]      (default http://127.0.0.1:8787)
#   --read-only          skip the write steps (capture, ingest) with a message
# Env:   PYTHON (default python3), SMOKE_FIXTURE, SMOKE_REQUIRE_HITS=1 (retrieve must return a hit)
# Exit:  0 when no step FAILed (SKIP is not a failure), 1 otherwise.
set -uo pipefail

READ_ONLY=0
BASE=""
for a in "$@"; do
  case "$a" in
    --read-only) READ_ONLY=1 ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) BASE="$a" ;;
  esac
done
BASE="${BASE:-http://127.0.0.1:8787}"
BASE="${BASE%/}"
PY="${PYTHON:-python3}"
HERE="$(cd "$(dirname "$0")" && pwd)"
FIXTURE="${SMOKE_FIXTURE:-$HERE/fixtures/smoke-note.txt}"
FAILS=0
TOOLS=""

pass() { echo "PASS $1${2:+: $2}"; }
skip() { echo "SKIP $1: $2"; }
fail() { echo "FAIL $1: $2"; FAILS=$((FAILS + 1)); }

# rpc TOOL [ARGS_JSON]: call a tool over /mcp, print its text result, exit 1 on any error.
rpc() {
  TOOL="$1" ARGS="${2:-}" "$PY" - "$BASE/mcp" <<'PYEOF'
import json, os, sys, urllib.request
args = json.loads(os.environ.get("ARGS") or "{}")
body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": os.environ["TOOL"], "arguments": args}}
req = urllib.request.Request(sys.argv[1], data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json", "Accept": "application/json"})
try:
    reply = json.load(urllib.request.urlopen(req, timeout=60))
except Exception as exc:
    print(f"request failed: {exc}"); sys.exit(1)
if "error" in reply:
    print(json.dumps(reply["error"])); sys.exit(1)
text = reply["result"]["content"][0]["text"]
print(text)
if reply["result"].get("isError"):
    sys.exit(1)
try:
    if json.loads(text).get("ok") is False or "error" in json.loads(text):
        sys.exit(1)
except (ValueError, AttributeError):
    pass
PYEOF
}

jget() { "$PY" -c 'import json,sys; d=json.load(sys.stdin); print(d.get(sys.argv[1], ""))' "$1"; }

step() { "do_$1"; }

do_healthz() {
  local out
  if out="$(curl -fsS -m 10 "$BASE/healthz" 2>&1)" && echo "$out" | grep -q '"ok"'; then
    pass healthz "$out"
  else
    fail healthz "no healthy reply from $BASE/healthz: $out"
  fi
}

do_status() {
  TOOLS="$("$PY" - "$BASE/mcp" <<'PYEOF'
import json, sys, urllib.request
req = urllib.request.Request(sys.argv[1], data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode(),
                             headers={"Content-Type": "application/json", "Accept": "application/json"})
print(" ".join(t["name"] for t in json.load(urllib.request.urlopen(req, timeout=30))["result"]["tools"]))
PYEOF
)"
  local tool=wiki_state
  case " $TOOLS " in *" wiki_status "*) tool=wiki_status ;; esac
  if out="$(rpc "$tool" '{}')"; then pass status "$tool answered"; else fail status "$tool: $out"; fi
}

do_capture() {
  if [ "$READ_ONLY" = 1 ]; then skip capture "--read-only"; return; fi
  local out
  if out="$(rpc wiki_capture_text "{\"text\": \"smoke capture $(date -u +%FT%TZ)\", \"channel\": \"mcp\"}")"; then
    pass capture
  else
    fail capture "$out"
  fi
}

do_search() {
  local out
  if out="$(rpc wiki_search '{"query": "smoke", "n": 3}')"; then pass search; else fail search "$out"; fi
}

do_ingest() {
  if [ "$READ_ONLY" = 1 ]; then skip ingest "--read-only"; return; fi
  local up ref out
  up="$(curl -sS -m 60 -F "file=@$FIXTURE" "$BASE/upload" 2>&1)"
  ref="$(echo "$up" | jget upload_ref 2>/dev/null)"
  if [ -z "$ref" ]; then fail ingest "upload refused: $up"; return; fi
  if out="$(rpc wiki_ingest_file "{\"upload_ref\": \"$ref\", \"title\": \"Smoke note\", \"request_id\": \"smoke-$(date +%s)-$RANDOM\"}")"; then
    pass ingest "$(echo "$out" | jget source_ref)"
  else
    fail ingest "$out"
  fi
}

do_retrieve() {
  case " $TOOLS " in
    *" wiki_retrieve "*) ;;
    *) skip retrieve "tool wiki_retrieve not advertised on this server"; return ;;
  esac
  local out
  if out="$(rpc wiki_retrieve '{"query": "lwk-smoke-fixture-heron-7731", "limit": 3, "budget_tokens": 2000}')"; then
    if [ "${SMOKE_REQUIRE_HITS:-0}" = 1 ] && ! echo "$out" | grep -q 'lwk-smoke-fixture-heron-7731'; then
      fail retrieve "no hit for the fixture phrase (index not refreshed?)"
    else
      pass retrieve
    fi
  else
    fail retrieve "$out"
  fi
}

echo "smoke against $BASE (read-only=$READ_ONLY)"
step healthz
step status
step capture
step search
step ingest
step retrieve

if [ "$FAILS" -gt 0 ]; then echo "smoke: $FAILS step(s) FAILED"; exit 1; fi
echo "smoke: ok"
