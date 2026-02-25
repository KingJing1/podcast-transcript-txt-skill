---
name: podcast-transcript-txt
description: Deterministic workflow to find and export full podcast transcripts as cleaned TXT files from YouTube URLs, episode webpages (including Xiaoyuzhou), Apple Podcasts title search, X/Twitter links, direct audio URLs, or plain episode titles. Use when users ask for 逐字稿/文字版/transcript/txt and want minimal trial-and-error.
---

# Podcast Transcript TXT

## Overview
Produce clean TXT transcripts for podcast/video episodes with a fixed decision tree.
Prioritize official transcript sources first, then platform subtitles, then local ASR fallback.
ASR fallback uses `faster-whisper` with selectable `--asr-model small|medium` (default `small`).
All transcript outputs are working drafts; always recommend one strong-LLM proofreading pass.

## Workflow Decision Tree

1. Normalize input.
- Accept one or more `--input` values.
- Support (stable): YouTube URL/ID, episode webpages (including Xiaoyuzhou), direct audio URLs, or plain title.
- X/Twitter status URL: best-effort resolver to outbound sources.

2. Resolve canonical episode source.
- Stable path A: if input is YouTube URL/ID, use it directly.
- Stable path B: if input is direct official transcript URL/JSON, parse it directly.
- Stable path C: if input is direct audio URL, go to local ASR path.
- Stable path D: if input is episode webpage, attempt transcript parse, then extract `og:audio`/JSON-LD audio as ASR source.
- Stable path E: if input is plain title, resolve with `ytsearch1`, then Apple `podcastEpisode` search fallback.
- Optional path: if input is X/Twitter URL, try outbound link resolution or compact title hint fallback, then follow A-E.

3. Fetch transcript in strict priority order.
- Priority A: official transcript/API source from episode host (including YouTube description outbound links).
- Priority B: platform subtitles via `yt-dlp` (`youtube:player_client=android`).
- Priority C: local ASR fallback when A/B unavailable and an audio source is available (`faster-whisper`, `--asr-model small|medium`, default `small`).

4. Error and boundary handling.
- If A/B/C all fail, return exact failed stage and error detail.
- Record every step into `meta.json.attempts[]`.
- Do not bypass login/paywall/DRM protections.

5. Clean and export.
- Remove timestamp markup and HTML tags.
- Collapse rolling-caption duplication.
- Run readability quality checks; if needed, apply aggressive secondary splitting.
- Keep paragraph-level readability.
- Write one TXT file per input item.

## Deterministic Rules

1. Do not jump between random methods.
- Always follow A -> B -> C.
- C requires an audio source (direct audio URL / episode webpage audio / Apple episode audio).
- Record the failure reason before moving to next tier.

2. Default security posture.
- Do not use browser cookies unless explicitly required and approved.
- Do not upload private audio/video to third-party transcript sites.

3. Failure reporting contract.
- Return: failed stage, exact error type, and next action already attempted.
- Persist each attempt in `meta.json` (`attempts[]`).
- If blocked after A/B/C, return one minimal user command to unblock.

4. Delivery quality contract.
- Explicitly state that output TXT is a draft, not final publish-ready text.
- Explicitly recommend one strong-LLM proofreading pass for names/terms/punctuation.
- Keep this notice concise but always present in final user-facing delivery.
- Prompt users to choose ASR model (`small` or `medium`) and explain tradeoff in one sentence.
- Remind users that delivery includes both `*.txt` and `*.meta.json`.

## Quick Start

Run (recommended stable usage):

```bash
python3 /Users/jing/.codex/skills/podcast-transcript-txt/scripts/podcast_transcript_txt.py \
  --input "https://www.youtube.com/watch?v=aR20FWCCjAs" \
  --input "播客标题关键词" \
  --out-dir "/Users/jing/Documents/New project"
```

Outputs:
- `<title> [<id>].txt`
- `<title> [<id>].meta.json`

## Host-Specific Notes

- `scripod.com`: prefer `/api/transcript/<episode_id>`.
- YouTube: use `yt-dlp` with `youtube:player_client=android`; try language set in this order: `zh-*` then `en-orig` then `en`.
- Xiaoyuzhou and similar episode pages: extract `og:audio` / JSON-LD media URL, then run ASR fallback.

## References

- Source strategy and reliability matrix: `references/sources.md`

## Scripts

- Main executor: `scripts/podcast_transcript_txt.py`
