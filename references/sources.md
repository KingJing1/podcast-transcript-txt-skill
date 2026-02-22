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

## Priority C: Local ASR fallback (not included in current script)

Current release intentionally keeps dependencies minimal (`python3 + yt-dlp`).
If needed in your fork, add optional local ASR (`faster-whisper` / `whisper`) as an explicit opt-in path.

## Security Guardrails

- Avoid browser cookie extraction by default.
- If cookies are required, use temporary local scope only and avoid logging secrets.
- Keep transcript processing local when user privacy matters.
