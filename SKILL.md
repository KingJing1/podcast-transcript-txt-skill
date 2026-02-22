---
name: podcast-transcript-txt
description: Deterministic workflow to find and export full podcast transcripts as cleaned TXT files from YouTube URLs, X/Twitter links, podcast episode pages, or plain episode titles. Use when users ask for 逐字稿/文字版/transcript/txt and want minimal trial-and-error.
---

# Podcast Transcript TXT

## Overview
Produce clean TXT transcripts for podcast/video episodes with a fixed decision tree.
Prioritize official transcript sources first, then platform subtitles.
This release does not bundle local ASR dependencies by default.

## Workflow Decision Tree

1. Normalize input.
- Accept one or more `--input` values.
- Support (stable): YouTube URL/ID or plain title.
- X/Twitter status URL: best-effort only, non-blocking fallback.

2. Resolve canonical episode source.
- Stable path A: if input is YouTube URL/ID, use it directly.
- Stable path B: if input is plain title, resolve with `ytsearch1`.
- Optional path: if input is X/Twitter URL, try outbound link resolution or compact title hint fallback.

3. Fetch transcript in strict priority order.
- Priority A: official transcript/API source from episode host (including YouTube description outbound links).
- Priority B: platform subtitles via `yt-dlp` (`youtube:player_client=android`).
- Priority C (optional, not bundled): local ASR fallback when A/B unavailable.

4. Clean and export.
- Remove timestamp markup and HTML tags.
- Collapse rolling-caption duplication.
- Run readability quality checks; if needed, apply aggressive secondary splitting.
- Keep paragraph-level readability.
- Write one TXT file per input item.

## Deterministic Rules

1. Do not jump between random methods.
- Always follow A -> B -> C.
- Record the failure reason before moving to next tier.

2. Default security posture.
- Do not use browser cookies unless explicitly required and approved.
- Do not upload private audio/video to third-party transcript sites.

3. Failure reporting contract.
- Return: failed stage, exact error type, and next action already attempted.
- Persist each attempt in `meta.json` (`attempts[]`).
- If blocked after A/B/C, return one minimal user command to unblock.

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

## References

- Source strategy and reliability matrix: `references/sources.md`

## Scripts

- Main executor: `scripts/podcast_transcript_txt.py`
