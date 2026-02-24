# Podcast Transcript TXT Skill

A lightweight, deterministic CLI to export podcast transcripts as clean `.txt` files.
Turn any podcast source into clean TXT — YouTube, episode webpages, Xiaoyuzhou, Apple Podcasts, X links, or just a title.

This project is designed for practical reliability:
- Prefer official transcript sources when available.
- Fallback to YouTube subtitles when needed.
- If no transcript/captions are available, fallback to local ASR (`faster-whisper`, fixed model: `medium`).
- Emit machine-readable diagnostics for every run.

## TL;DR

```bash
git clone https://github.com/KingJing1/podcast-transcript-txt-skill.git
cd podcast-transcript-txt-skill
python3 scripts/podcast_transcript_txt.py \
  --input "https://www.youtube.com/watch?v=aR20FWCCjAs" \
  --out-dir "/tmp/transcripts"
```

Output:
- `<title> [<id>].txt`
- `<title> [<id>].meta.json`

## Features

- Deterministic source strategy (official first, subtitles second, ASR third).
- Multiple input types:
  - YouTube URL / ID
  - Episode webpages (e.g. Xiaoyuzhou)
  - Direct audio URLs
  - Apple Podcasts episode discovery from plain title
  - Episode title keywords
  - X/Twitter status URL (best-effort)
  - Official transcript page / JSON URL
  - Scripod episode URL
- Readability guardrails (quality checks + line splitting repair).
- ASR fallback with fixed `medium` model for non-YouTube podcast episodes.
- Structured run metadata (`resolver`, `quality`, `attempts`).

## Requirements

- Python 3.10+
- `yt-dlp`
- For ASR fallback: `faster-whisper` (and system ffmpeg runtime available to PyAV)

Quick check:

```bash
python3 --version
yt-dlp --version
python3 -c "import faster_whisper; print('faster-whisper ok')"
```

## Installation

### Option A: Use as a normal CLI (recommended)

```bash
git clone https://github.com/KingJing1/podcast-transcript-txt-skill.git
cd podcast-transcript-txt-skill
```

### Option B: Install as a Codex skill

```bash
mkdir -p ~/.codex/skills
cp -R podcast-transcript-txt-skill ~/.codex/skills/podcast-transcript-txt
```

## Usage

Single input:

```bash
python3 scripts/podcast_transcript_txt.py \
  --input "https://www.youtube.com/watch?v=aR20FWCCjAs" \
  --out-dir "/tmp/transcripts"
```

Batch input:

```bash
python3 scripts/podcast_transcript_txt.py \
  --input "https://www.youtube.com/watch?v=aR20FWCCjAs" \
  --input "https://www.youtube.com/watch?v=0-LAT4HjWPo" \
  --input "Naval podcast On Artificial Intelligence" \
  --out-dir "/tmp/transcripts"
```

## Output Contract

For each successful input:
- `*.txt`: cleaned transcript text
- `*.meta.json`: execution metadata and diagnostics

Important `meta.json` fields:
- `resolver`: which path produced the final result
- `source`: final source URL
- `status`: `ok` or `warn`
- `quality`: line-level quality metrics
- `attempts[]`: step-by-step attempts and failures

Exit code:
- `0`: all inputs succeeded
- `1`: at least one input failed

## How Resolution Works

Priority order:
1. Official transcript sources (including links found in YouTube descriptions).
2. YouTube subtitles via `yt-dlp`.
3. Local ASR (`faster-whisper`, model fixed to `medium`) from audio URL / episode page / Apple podcastEpisode search.

Notes:
- X/Twitter is a resolver path, not a guaranteed transcript source.
- Official transcript URL input is supported directly.
- ASR outputs are intentionally marked as draft in `meta.json`.

## Resolution Matrix

| Input Type | First Attempt | Fallback Chain | Final Resolver (example) |
|---|---|---|---|
| YouTube URL / ID | Official links in video description | YouTube subtitles (if unavailable, fail with stage detail) | `official-link` / `youtube-id` |
| Official transcript URL | Parse transcript page / JSON directly | None | `official-link-direct` |
| Episode webpage (e.g. Xiaoyuzhou) | Try official transcript parse | Extract `og:audio` / JSON-LD audio -> Local ASR | `episode-page-asr` |
| Direct audio URL (`.m4a/.mp3/...`) | Local ASR | None | `audio-url-asr` |
| Plain title | YouTube title search | Apple Podcasts `podcastEpisode` search -> episode audio -> Local ASR | `title->ytsearch1` / `title->itunes-episode-asr` |
| X/Twitter link | Resolve outbound links | Title hint search -> normal title flow | `x_*` + downstream resolver |

## Boundaries And Guarantees

Guaranteed:
- Deterministic order: A official -> B subtitle -> C ASR.
- One `.txt` + one `.meta.json` per successful input.
- Full attempt trace in `meta.json.attempts[]` for debugging.

Not guaranteed:
- 100% source availability (paywalls, geo/IP blocks, deleted media).
- Perfect Chinese proper nouns in ASR draft.
- Speaker diarization accuracy (current output is timestamped text-first).

Out of scope:
- Bypassing login/paywall/DRM restrictions.
- Uploading private audio to third-party transcription services.

## Priority And Escalation Rules

1. If official transcript exists and parses cleanly, always use it.
2. If official transcript is missing or low quality, use platform subtitles.
3. If subtitles are missing/unreadable and an audio source is available, run local ASR (`medium`).
4. If all routes fail, surface exact failed stage and unblock action in CLI error + `meta.json`.

## ASR Runtime And Quality Expectation

- Model is fixed: `medium` (`faster-whisper`), optimized for practical balance.
- Typical CPU runtime:
  - 30 min audio: around 15-35 min
  - 60 min audio: around 30-70 min
- Output expectation:
  - Usually good structure and semantic continuity.
  - Name/term homophone errors are expected; run one LLM proofreading pass before publishing.

## Post-process (recommended)

When output comes from ASR, do a quick proofreading pass with any LLM.
This usually fixes names/terms fast without re-running heavy transcription.

Suggested one-line instruction:

```text
Proofread this transcript with minimal edits: fix obvious homophone errors and punctuation, keep meaning unchanged, keep paragraph order unchanged.
```

## Agent Integration

This is a CLI-first tool, so any agent that can execute shell commands can use it.

Typical integrations:
- Codex
- OpenClaw
- Claude Code
- Cursor Agent / Cline / custom agent runners

For non-terminal clients (for example Claude App/Web), run the CLI locally first, then upload the generated `.txt`.

## Limitations

- No tool can guarantee 100% transcript availability.
- Failures can still happen due to missing captions, rate limits, or broken outbound links.
- ASR draft quality depends on audio quality and domain terms; expect occasional name/term mistakes.

## Troubleshooting

See:
- [`INSTALL.md`](./INSTALL.md)
- [`TROUBLESHOOTING.md`](./TROUBLESHOOTING.md)

## Project Docs

- [`SKILL.md`](./SKILL.md)
- [`CHANGELOG.md`](./CHANGELOG.md)
- [`CONTRIBUTING.md`](./CONTRIBUTING.md)
- [`references/sources.md`](./references/sources.md)

## License

MIT. See [`LICENSE`](./LICENSE).
