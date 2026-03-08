# Transcript Source Priority

## Priority A: Official transcript host

Use official transcript pages/APIs when available.

- `scripod.com/episode/<id>`
  - API: `https://scripod.com/api/transcript/<id>`
  - Reliability: high
- YouTube description outbound links (auto-detected)
  - Typical hosts:
    - `dwarkesh.com` / Substack-backed transcript pages
    - `lexfridman.com/*-transcript`
    - Direct `substackcdn.com/.../transcription.json`
  - Reliability: medium-high (depends on host availability / paywall)
- Direct transcript files
  - Typical formats:
    - `.ttml`
    - supported `.json`
  - Reliability: high when the file is first-party or exported from Apple/host platform

Why first:
- Highest semantic accuracy
- Usually has speaker segmentation

## Priority B: Platform subtitles

Primary method:
- `yt-dlp --extractor-args 'youtube:player_client=android'`

Preferred language order:
1. `zh-Hans`
2. `zh-CN`
3. `zh-Hant`
4. `zh`
5. `en-orig`
6. `en`

Common errors and deterministic handling:
- `PO token` limits: keep `android` client path
- `429 Too Many Requests`: back off, then retry with narrower language list
- Missing zh subtitles: fallback to `en-orig/en` and continue

## Priority C: Structured page text

Use visible page text or show notes when the host exposes meaningful text but not a clean transcript endpoint.

- Example:
  - Xiaoyuzhou episode page `shownotes`
- Reliability: medium
- Important:
  - This is useful text, but it is not the same thing as a time-aligned transcript
  - Mark this clearly in `meta.json` and user-facing delivery

## Priority D: Local ASR fallback

Use local ASR only when A/B/C are unavailable and an audio source is available.

- Current implementation:
  - `faster-whisper`
  - selectable `small|medium`
- Reliability: medium
- Tradeoff:
  - broadest coverage
  - highest compute cost
  - most likely to introduce term/name mistakes

## Security Guardrails

- Avoid browser cookie extraction by default.
- If cookies are required, use temporary local scope only and avoid logging secrets.
- Keep transcript processing local when user privacy matters.
