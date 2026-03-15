---
name: podcast-transcript-txt
description: Deterministic workflow to find and export full podcast transcripts as cleaned TXT files from YouTube URLs, episode webpages (including Xiaoyuzhou), Apple Podcasts title search, X/Twitter links, direct audio URLs, or plain episode titles. Use when users ask for 逐字稿/文字版/transcript/txt and want minimal trial-and-error.
---

# Podcast Transcript TXT

## Overview
Use the single persistent local runtime at `/Users/jing/Desktop/podcast_transcripts`.
Do not maintain a second transcription stack inside the skill itself.
Default delivery is one final `.txt`; metadata is opt-in with `--emit-meta`.
Current runtime is audio-first local ASR using the persistent virtualenv and model cache already present on this machine.

## Workflow Decision Tree

1. Normalize input.
- Accept one or more `--input` values.
- Support (stable): YouTube URL/ID, episode webpages (including Xiaoyuzhou), direct audio URLs, or plain title.
- X/Twitter status URL: best-effort resolver to outbound sources.

2. Resolve canonical episode source.
- Stable path A: if input is a Xiaoyuzhou episode URL, resolve the page and extract `og:audio`, using local cached HTML as fallback when needed.
- Stable path B: if input is a direct audio URL, use it directly.
- Stable path C: if input is a local audio file, use it directly.
- Avoid maintaining a separate resolver tree in the skill unless the desktop runtime is updated first.

3. Fetch transcript in strict priority order.
- Priority A: reuse existing local caches and persistent model files.
- Priority B: fetch episode page/audio only if the needed file is not already cached.
- Priority C: run local Whisper ASR with the persistent runtime.

4. Error and boundary handling.
- If A/B/C all fail, return exact failed stage and error detail.
- Record every step into metadata in-memory; only persist `meta.json.attempts[]` when explicitly requested.
- Do not bypass login/paywall/DRM protections.

5. Clean and export.
- Remove timestamp markup and HTML tags.
- Collapse rolling-caption duplication.
- Run readability quality checks; if needed, apply aggressive secondary splitting.
- Keep paragraph-level readability.
- Write one TXT file per input item by default.
- Only write `*.meta.json` when debugging or when the user explicitly asks for metadata.

## Deterministic Rules

1. Do not jump between random methods.
- Always follow A -> B -> C -> D.
- D requires an audio source (direct audio URL / episode webpage audio / Apple episode audio).
- Record the failure reason before moving to next tier.

2. Default security posture.
- Do not use browser cookies unless explicitly required and approved.
- Do not upload private audio/video to third-party transcript sites.

3. Failure reporting contract.
- Return: failed stage, exact error type, and next action already attempted.
- Persist each attempt in `meta.json` (`attempts[]`) only when metadata output is enabled.
- If blocked after A/B/C, return one minimal user command to unblock.

4. Delivery quality contract.
- Explicitly state that output TXT may be transcript, subtitle-derived text, or visible page text depending on resolver.
- Explicitly recommend one strong-LLM proofreading pass for names/terms/punctuation.
- Keep this notice concise but always present in final user-facing delivery.
- Ask for ASR model (`small` or `medium`) only when the run is likely to hit audio fallback, and explain the tradeoff in one sentence.
- Default delivery is only the final `*.txt`.
- Mention `*.meta.json` only when `--emit-meta` is used or the user explicitly asks for debugging traces.

## Quick Start

Run (recommended stable usage):

```bash
python3 /Users/jing/.codex/skills/podcast-transcript-txt/scripts/podcast_transcript_txt.py \
  --input "https://www.xiaoyuzhoufm.com/episode/69b3b675772ac2295bfc01d0" \
  --out-dir "/Users/jing/Documents/New project"
```

Outputs:
- `<title> [<id>].txt`
- optional: `<title> [<id>].meta.json` when `--emit-meta` is passed

Debug mode:

```bash
python3 /Users/jing/.codex/skills/podcast-transcript-txt/scripts/podcast_transcript_txt.py \
  --input "https://www.youtube.com/watch?v=aR20FWCCjAs" \
  --out-dir "/Users/jing/Documents/New project" \
  --emit-meta
```

## Local Runtime Contract

- Source of truth config: `/Users/jing/Desktop/podcast_transcripts/runtime.json`
- Source of truth script: `/Users/jing/Desktop/podcast_transcripts/transcribe_episode.py`
- Persistent environment: `/Users/jing/Desktop/podcast_transcripts/.venv-whisper`
- Persistent model cache: `/Users/jing/Desktop/podcast_transcripts/model-cache`
- Persistent audio cache: `/Users/jing/Desktop/podcast_transcripts/audio-cache`
- Final outputs: `/Users/jing/Desktop/podcast_transcripts/output`

If any of these paths change, update the desktop runtime first, then keep this skill wrapper aligned with it.

## References

- Source strategy and reliability matrix: `references/sources.md`

## Scripts

- Unified wrapper: `scripts/podcast_transcript_txt.py`
- Runtime executor: `/Users/jing/Desktop/podcast_transcripts/transcribe_episode.py`
