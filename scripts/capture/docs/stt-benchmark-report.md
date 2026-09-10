---
id: mw-doc-stt-benchmark
type: system-document
title: "Local STT benchmark report (1.2.0)"
status: candidate
---
# Local speech-to-text: host verdict 2026-09-05

## Tested

- `faster-whisper 1.2.1` (local, `small`, CPU int8): **UNUSABLE** —
  import fails (`av._core` DLL load failure in this Python env).
  No transcript was produced; no audio left the host.
- Host also carries `onnxruntime 1.29.0` + `ctranslate2` (importable),
  but no runnable local transcription configuration exists today.

## Gate outcome (spec §6)

No local configuration passed because none could run. Per the stop
condition, **1.2.0 releases capture WITHOUT automatic transcription**:
`stt-benchmark-pass.json` is absent, `wiki_transcribe_capture` with any
automatic adapter refuses (`E_AUTO_STT_DISABLED`), and voice captures rest
at `transcription_state: pending` for explicit manual action.

## Addendum 2026-09-06 — engine repaired, live transcripts produced

- Root cause of the PyAV failure: broken `av` wheel in the Hermes venv
  (FFmpeg DLLs missing). `pip install --force-reinstall av==18.1.0` +
  missing `huggingface-hub` fixed it; `faster_whisper 1.2.1` imports clean.
- Live verification (Hermes host, CPU int8, `small`): Persian clip detected
  fa (0.97), transcript usable (synthetic TTS voice costs accuracy; real
  voice expected better); English clip verbatim-perfect. fa 9.7 s → 4.6 s,
  en 6.2 s → 3.4 s.
- Hermes-side STT now enabled (`stt.provider: local, model: small`) for
  chat/Telegram transcripts — this is the MANUAL capture path: a transcript
  is committed to the archive only by explicit action (`commit-transcript`,
  adapter `hermes-local-whisper-small`), never automatically.
- The full 25-clip §6 benchmark is still outstanding; `E_AUTO_STT_DISABLED`
  therefore remains in force for the archive's automatic path. The five
  gate clauses must pass before `wiki_transcribe_capture` auto-runs.

## To enable later

1. Fix the host env (PyAV DLLs) or install an alternative local engine.
2. Collect the 25-clip set per `stt-benchmark-manifest.json`
   (10 fa + 10 en + 5 mixed; refs stored outside search).
3. Run, publish measurements, write `stt-benchmark-pass.json`
   (`{passed, date, adapter, metrics}`) only if all five gate clauses hold.
4. Never enable a paid/remote fallback silently (amendment A6).
