# Podcast Transcript TXT Skill

A lightweight, deterministic CLI to export podcast transcripts as clean `.txt` files.

This project is designed for practical reliability:
- Prefer official transcript sources when available.
- Fallback to YouTube subtitles when needed.
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

- Deterministic source strategy (official first, subtitles second).
- Multiple input types:
  - YouTube URL / ID
  - Episode title keywords
  - X/Twitter status URL (best-effort)
  - Official transcript page / JSON URL
  - Scripod episode URL
- Readability guardrails (quality checks + line splitting repair).
- Structured run metadata (`resolver`, `quality`, `attempts`).

## Requirements

- Python 3.10+
- `yt-dlp`

Quick check:

```bash
python3 --version
yt-dlp --version
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

Notes:
- X/Twitter is a resolver path, not a guaranteed transcript source.
- Official transcript URL input is supported directly.

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
- Local ASR is not bundled in this release (kept dependency-light by design).

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
