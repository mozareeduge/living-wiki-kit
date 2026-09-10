#!/usr/bin/env python3
"""Provider-neutral speech-to-text contract — This Wiki 1.2.0 (Task 5).

Spec §5: every adapter accepts a local media path + optional language hint
and returns text + segments + detected language + duration + quality flags
+ provider/model/version + cost. No summaries during transcription. Never
manufacture confidence. Raw media always preserved (core does that).

Release gate (spec §6): automatic transcription stays DISABLED until a
benchmark on the actual Hermes host passes and `stt-benchmark-pass.json`
exists. Until then transcription is an explicit manual action via
`record_transcript(..., adapter="manual", ...)` or the `transcribe` CLI
with --manual. Remote adapters are disabled unless --remote-provider is
passed explicitly per operation (amendment A6).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SYS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SYS / "scripts" / "capture"))
import wiki_capture as wc

CAPTURE_DIR = Path(__file__).resolve().parent
BENCHMARK_PASS_FILE = CAPTURE_DIR / "stt-benchmark-pass.json"
BENCHMARK_MANIFEST = CAPTURE_DIR / "stt-benchmark-manifest.json"

QUALITY_FLAGS = {
    "silence", "clipping", "low-volume", "unsupported-format",
    "language-mismatch", "suspicious-repetition", "uncertain-names",
    "uncertain-numbers", "uncertain-dates", "incomplete",
}


class STTResult(dict):
    """Spec §5 result shape. Construct via make_result() for validation."""

    @staticmethod
    def make(provider: str, model: str, version: str, text: str,
             segments: list | None = None, detected_language: str = "unknown",
             duration_ms: int | None = None, quality_flags: list | None = None,
             cost_known: float = 0) -> "STTResult":
        flags = [f for f in (quality_flags or []) if f in QUALITY_FLAGS]
        return STTResult({
            "text": text,
            "segments": segments or [],
            "detected_language": detected_language,
            "duration_ms": duration_ms,
            "quality_flags": flags,
            "provider": provider,
            "model_or_engine": model,
            "engine_version": version,
            "cost_known": cost_known,
        })


class SpeechAdapter:
    name = "base"
    version = "0"
    remote = False

    def available(self) -> tuple[bool, str]:
        return False, "base adapter transcribes nothing"

    def transcribe(self, media_path: str, language_hint: str = "unknown") -> STTResult:
        raise NotImplementedError


class ManualAdapter(SpeechAdapter):
    """Explicit human transcription. Always available; the 1.2.0 default."""
    name = "manual"
    version = "1"

    def available(self):
        return True, "human operator types or pastes the transcript"

    def transcribe(self, media_path, language_hint="unknown"):
        raise wc.CaptureError(
            "E_MANUAL_ONLY",
            "no automatic engine is enabled. Listen to the media and store the "
            "transcript with: wiki_capture.py commit-transcript --id <id> "
            "--adapter manual --version v1 --text-file <txt>")


class FasterWhisperAdapter(SpeechAdapter):
    """Local faster-whisper. Reports honest unavailability when broken."""
    name = "faster-whisper"
    version = "1.2.1"
    MODEL = "small"

    def available(self):
        try:
            import faster_whisper  # noqa: F401
            return True, f"faster-whisper {self.version}, model {self.MODEL}"
        except Exception as exc:  # noqa: BLE001
            return False, f"faster-whisper unusable on this host: {exc}"

    def transcribe(self, media_path, language_hint="unknown"):
        ok, why = self.available()
        if not ok:
            raise wc.CaptureError("E_ENGINE_UNAVAILABLE", why)
        from faster_whisper import WhisperModel
        model = WhisperModel(self.MODEL, device="cpu", compute_type="int8")
        lang = None if language_hint in ("unknown", "mixed") else language_hint
        segments, info = model.transcribe(media_path, language=lang,
                                          word_timestamps=False)
        segs = [{"start_ms": int(s.start * 1000), "end_ms": int(s.end * 1000),
                 "text": s.text, "confidence": None} for s in segments]
        text = "".join(s["text"] for s in segs).strip()
        flags = []
        if not text:
            flags.append("silence")
        return STTResult.make(
            provider="local-faster-whisper", model=f"whisper-{self.MODEL}",
            version=self.version, text=text, segments=segs,
            detected_language=info.language or "unknown",
            duration_ms=int(info.duration * 1000), quality_flags=flags)


ADAPTERS: dict[str, SpeechAdapter] = {
    "manual": ManualAdapter(),
    "faster-whisper": FasterWhisperAdapter(),
}


def auto_transcription_allowed() -> tuple[bool, str]:
    if not BENCHMARK_PASS_FILE.exists():
        return False, ("no passing host benchmark (stt-benchmark-pass.json absent); "
                        "transcription is manual-only per spec §6 stop condition")
    try:
        data = json.loads(BENCHMARK_PASS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return False, f"benchmark pass file unreadable: {exc}"
    if not data.get("passed"):
        return False, "benchmark recorded a FAIL; automatic transcription disabled"
    return True, f"benchmark passed {data.get('date')} ({data.get('adapter')})"


def transcribe_capture(capture_id: str, adapter_name: str = "manual",
                       remote_provider: str | None = None,
                       text: str | None = None) -> dict:
    """Explicit transcription entry point used by CLI/hook/MCP.

    adapter=manual + text => store human transcript immediately.
    any automatic adapter => requires a passing host benchmark, else refuse.
    remote_provider set => requires explicit per-operation opt-in (A6); no
    remote adapters ship in 1.2.0, so this always refuses for now.
    """
    rec = wc.read_capture(capture_id)
    if rec["front_matter"]["capture_kind"] not in ("voice", "mixed"):
        raise wc.CaptureError("E_WRONG_KIND", "transcription is for voice/mixed captures")
    if remote_provider is not None:
        raise wc.CaptureError(
            "E_REMOTE_REFUSED",
            f"remote provider {remote_provider!r} needs explicit per-operation "
            "consent AND a configured remote adapter; none ships in 1.2.0")
    adapter = ADAPTERS.get(adapter_name)
    if adapter is None:
        raise wc.CaptureError("E_UNKNOWN_ADAPTER", f"unknown adapter: {adapter_name}")
    if adapter_name != "manual":
        ok, why = auto_transcription_allowed()
        if not ok:
            raise wc.CaptureError("E_AUTO_STT_DISABLED", why)
        ok, why = adapter.available()
        if not ok:
            raise wc.CaptureError("E_ENGINE_UNAVAILABLE", why)
        media = wc._resolve_media(rec["front_matter"]["raw_media"])
        result = adapter.transcribe(str(media), rec["front_matter"]["language_hint"])
        wc.record_transcript(capture_id, result["text"], adapter.name,
                             adapter.version, segments=result["segments"],
                             quality_flags=result["quality_flags"])
        wc.set_state(capture_id, "transcribed", "stt-pipeline",
                     note=f"{adapter.name} {adapter.version}")
        return {"ok": True, "id": capture_id, "adapter": adapter.name,
                "chars": len(result["text"]), "flags": result["quality_flags"],
                "message": f"transcript stored ({adapter.name})"}
    if not (text or "").strip():
        raise wc.CaptureError("E_EMPTY", "manual transcription needs --text")
    wc.record_transcript(capture_id, text, "manual", "v1")
    return {"ok": True, "id": capture_id, "adapter": "manual",
            "chars": len(text),
            "message": "manual transcript stored; review it with set-state"}


# ------------------------------------------------------------- benchmark set

def benchmark_manifest_template() -> dict:
    return {
        "clips": [],
        "required": {
            "fa": 10, "en": 10, "mixed_or_proper_names": 5,
            "durations_s": [15, 180], "conditions": ["quiet", "noisy"],
            "must_cover": ["dates", "numbers", "names", "wiki-vocabulary"],
        },
        "metrics": ["cer_fa", "wer_en", "omissions_over_2s", "name_date_number_acc",
                    "correction_time_s", "runtime_s", "peak_mem_mb", "cost"],
        "gate": ["no unmarked omission over 2s", "90% usable without full re-transcription",
                 "uncertain names/dates/numbers flaggable by timestamp",
                 "correction faster than manual transcription", "runs on the Hermes host"],
        "note": "reference transcripts live OUTSIDE normal search results",
    }


def ensure_manifest():
    if not BENCHMARK_MANIFEST.exists():
        BENCHMARK_MANIFEST.write_text(
            json.dumps(benchmark_manifest_template(), ensure_ascii=False, indent=1),
            encoding="utf-8")
    return BENCHMARK_MANIFEST


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(prog="stt_contract")
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("transcribe")
    t.add_argument("--id", required=True)
    t.add_argument("--adapter", default="manual")
    t.add_argument("--text", default=None)
    t.add_argument("--remote-provider", default=None)
    sub.add_parser("status").add_argument("--x", nargs="?", default=None)
    sub.add_parser("init-manifest")
    args = ap.parse_args()
    try:
        if args.cmd == "transcribe":
            print(json.dumps(transcribe_capture(
                args.id, args.adapter, args.remote_provider, args.text),
                ensure_ascii=False, indent=1))
        elif args.cmd == "status":
            auto_ok, auto_why = auto_transcription_allowed()
            print(json.dumps({
                "auto_transcription": auto_ok, "reason": auto_why,
                "adapters": {k: {"available": a.available()[0],
                                 "detail": a.available()[1]}
                             for k, a in ADAPTERS.items()}},
                ensure_ascii=False, indent=1))
        elif args.cmd == "init-manifest":
            print(f"manifest: {ensure_manifest()}")
    except wc.CaptureError as e:
        print(json.dumps({"ok": False, "code": e.code, "message": e.message},
                         ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
