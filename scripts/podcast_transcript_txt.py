#!/usr/bin/env python3
"""Deterministic podcast transcript exporter.

Input types:
- YouTube URL / YouTube ID
- X/Twitter status URL (extract outbound links)
- Scripod episode URL
- Plain title (resolve with ytsearch)

Output:
- <title> [<id>].txt
- <title> [<id>].meta.json
"""

from __future__ import annotations

import argparse
import glob
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)

YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
URL_RE = re.compile(r"https?://[^\s\"'<>]+")
TRANSCRIPTION_JSON_RE = re.compile(r"https://[^\"'<> ]*transcription\.json[^\"'<> ]*", re.I)
AUDIO_EXTS = (".m4a", ".mp3", ".wav", ".flac", ".aac", ".ogg", ".opus", ".mp4", ".webm")
ASR_MODEL = "medium"


def run(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def compact_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def append_with_spacing(base: str, piece: str) -> str:
    if not base:
        return piece
    if not piece:
        return base
    if re.match(r"^[,.;:!?，。！？；：、\)\]\"'”’]", piece):
        return base + piece
    if base[-1].isalnum() and piece[0].isalnum():
        return base + " " + piece
    return base + piece


def dedup_consecutive(lines: List[str]) -> List[str]:
    out: List[str] = []
    for x in lines:
        if out and out[-1] == x:
            continue
        out.append(x)
    return out


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:180] if len(name) > 180 else name


def seconds_to_hms(sec: float) -> str:
    t = int(max(0, sec))
    h = t // 3600
    m = (t % 3600) // 60
    s = t % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def log_attempt(meta: Dict[str, Any], stage: str, ok: bool, detail: str, source: Optional[str] = None) -> None:
    attempts = meta.setdefault("attempts", [])
    entry: Dict[str, Any] = {
        "stage": stage,
        "ok": ok,
        "detail": compact_ws(detail)[:260],
    }
    if source:
        entry["source"] = source
    attempts.append(entry)


def http_get(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def looks_like_audio_url(url: str) -> bool:
    try:
        path = urllib.parse.urlparse(url).path.lower()
    except Exception:
        return False
    return any(path.endswith(ext) for ext in AUDIO_EXTS)


def find_ytdlp() -> Optional[str]:
    candidates = [
        os.getenv("YT_DLP_PATH"),
        shutil.which("yt-dlp"),
        str(Path.home() / ".local/bin/yt-dlp"),
        str(Path.home() / "Library/Python/3.12/bin/yt-dlp"),
        str(Path.home() / "Library/Python/3.11/bin/yt-dlp"),
        str(Path.home() / "Library/Python/3.10/bin/yt-dlp"),
        str(Path.home() / "Library/Python/3.9/bin/yt-dlp"),
    ]
    seen = set()
    for c in candidates:
        if not c or c in seen:
            continue
        seen.add(c)
        p = Path(c).expanduser()
        if p.exists() and os.access(p, os.X_OK):
            return str(p)
    return None


def extract_youtube_id(value: str) -> Optional[str]:
    value = value.strip()
    if YOUTUBE_ID_RE.fullmatch(value):
        return value
    if not is_url(value):
        return None

    u = urllib.parse.urlparse(value)
    host = u.netloc.lower()
    path = u.path
    qs = urllib.parse.parse_qs(u.query)

    if "youtube.com" in host:
        if path == "/watch":
            v = qs.get("v", [None])[0]
            if v and YOUTUBE_ID_RE.fullmatch(v):
                return v
        m = re.match(r"^/(shorts|live|embed)/([A-Za-z0-9_-]{11})", path)
        if m:
            return m.group(2)
    if "youtu.be" in host:
        vid = path.strip("/").split("/")[0]
        if YOUTUBE_ID_RE.fullmatch(vid):
            return vid
    return None


def youtube_url_from_id(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def youtube_metadata(ytdlp: str, target: str) -> Dict[str, str]:
    cmd = [
        ytdlp,
        "--extractor-args",
        "youtube:player_client=android",
        "--skip-download",
        "--dump-single-json",
        target,
    ]
    p = run(cmd)
    if p.returncode != 0:
        raise RuntimeError(f"yt-dlp metadata failed: {compact_ws(p.stderr)}")
    try:
        data = json.loads(p.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"invalid yt-dlp json: {e}") from e
    if not isinstance(data, dict):
        raise RuntimeError("unexpected yt-dlp metadata payload type")

    video_id = str(data.get("id") or "").strip()
    title = str(data.get("title") or "").strip()
    page_url = str(data.get("webpage_url") or "").strip()
    description = data.get("description") or ""
    if not (video_id and title and page_url):
        raise RuntimeError("yt-dlp metadata missing id/title/webpage_url")
    if not YOUTUBE_ID_RE.fullmatch(video_id):
        raise RuntimeError(f"yt-dlp metadata returned non-video id: {video_id}")
    if not page_url.startswith("http"):
        raise RuntimeError(f"yt-dlp metadata returned invalid webpage_url: {page_url}")
    return {
        "id": video_id,
        "title": title,
        "webpage_url": page_url,
        "description": str(description),
    }


def resolve_title_to_youtube(ytdlp: str, title: str) -> Dict[str, str]:
    queries = [f"ytsearch1:{title} podcast", f"ytsearch1:{title}"]
    last_err = ""
    for q in queries:
        try:
            return youtube_metadata(ytdlp, q)
        except Exception as e:
            last_err = str(e)
    raise RuntimeError(f"title resolve failed: {last_err}")


def parse_vtt_cues(vtt_text: str) -> List[str]:
    lines = vtt_text.splitlines()
    cues: List[str] = []
    buf: List[str] = []
    in_cue = False

    def flush() -> None:
        nonlocal buf
        if not buf:
            return
        text = " ".join(buf)
        text = re.sub(r"<\d{2}:\d{2}:\d{2}\.\d{3}>", "", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text)
        text = re.sub(r"\[(?:music|Music|applause|Applause)\]", " ", text)
        text = text.replace("\u200b", " ")
        text = compact_ws(text)
        if text:
            cues.append(text)
        buf = []

    for raw in lines:
        s = raw.strip("\ufeff").rstrip()
        if not s.strip():
            flush()
            in_cue = False
            continue
        if s.startswith("WEBVTT") or s.startswith("NOTE") or s.startswith("Kind:") or s.startswith("Language:"):
            continue
        if "-->" in s:
            flush()
            in_cue = True
            continue
        if re.fullmatch(r"\d+", s.strip()):
            continue
        if in_cue or s.strip():
            buf.append(s.strip())

    flush()
    return cues


def merge_cues_with_overlap(cues: List[str]) -> str:
    """Merge rolling captions by suffix-prefix overlap."""
    acc = ""
    for cue in cues:
        cue = cue.strip()
        if not cue:
            continue
        if not acc:
            acc = cue
            continue

        window = acc[-600:]
        if cue in window:
            continue

        max_possible = min(len(window), len(cue))
        overlap = 0
        for k in range(max_possible, 0, -1):
            if window[-k:] == cue[:k]:
                overlap = k
                break

        tail = cue[overlap:]
        if not tail:
            continue
        acc = append_with_spacing(acc, tail)

    acc = re.sub(r"\s+([,.!?;:])", r"\1", acc)
    acc = re.sub(r"([，。！？；：、])\s+", r"\1", acc)
    acc = compact_ws(acc)
    return acc


def hard_wrap(text: str, width: int = 200) -> List[str]:
    out: List[str] = []
    cur = text.strip()
    while len(cur) > width:
        cut = cur.rfind(" ", 0, width + 1)
        if cut <= 0:
            cut = width
        out.append(cur[:cut].strip())
        cur = cur[cut:].strip()
    if cur:
        out.append(cur)
    return out


def split_lines(text: str) -> List[str]:
    if not text:
        return []
    text = text.replace(">>", "\n>>")
    parts = [p.strip() for p in text.splitlines() if p.strip()]
    out: List[str] = []
    for part in parts:
        segs = re.split(r"(?<=[.!?。！？])\s*", part)
        for seg in segs:
            s = seg.strip()
            if not s:
                continue
            if len(s) > 260:
                out.extend(hard_wrap(s, width=220))
            else:
                out.append(s)
    return dedup_consecutive(out)


def aggressive_split_lines(text: str) -> List[str]:
    text = compact_ws(text)
    if not text:
        return []
    primary = re.split(r"(?<=[.!?。！？])", text)
    out: List[str] = []
    for seg in primary:
        seg = seg.strip()
        if not seg:
            continue
        if len(seg) > 260:
            secondary = re.split(r"(?<=[,，;；:：])", seg)
            for s in secondary:
                s = s.strip()
                if not s:
                    continue
                if len(s) > 260:
                    out.extend(hard_wrap(s, width=200))
                else:
                    out.append(s)
        else:
            out.append(seg)
    return dedup_consecutive(out)


def quality_metrics(lines: List[str]) -> Dict[str, float]:
    if not lines:
        return {
            "line_count": 0,
            "total_chars": 0,
            "avg_line_len": 0.0,
            "max_line_len": 0,
            "unique_ratio": 0.0,
            "long_lines_over_260": 0,
        }
    total = sum(len(x) for x in lines)
    return {
        "line_count": len(lines),
        "total_chars": total,
        "avg_line_len": round(total / len(lines), 2),
        "max_line_len": max(len(x) for x in lines),
        "unique_ratio": round(len(set(lines)) / len(lines), 4),
        "long_lines_over_260": sum(1 for x in lines if len(x) > 260),
    }


def is_low_quality(metrics: Dict[str, float]) -> bool:
    return bool(
        (metrics["line_count"] <= 8 and metrics["total_chars"] >= 2000)
        or metrics["max_line_len"] >= 900
        or metrics["avg_line_len"] >= 240
        or (metrics["line_count"] >= 30 and metrics["unique_ratio"] < 0.55)
    )


def quality_score(metrics: Dict[str, float]) -> float:
    return (
        metrics["line_count"] * 3
        - metrics["avg_line_len"]
        - metrics["long_lines_over_260"] * 40
        + metrics["unique_ratio"] * 50
    )


def choose_vtt(video_id: str, workdir: Path) -> Optional[Path]:
    cands = [Path(p) for p in glob.glob(str(workdir / f"{video_id}.*.vtt"))]
    if not cands:
        return None
    priority = ["zh-Hans", "zh-CN", "zh-Hant", "zh", "en-orig", "en"]
    for p in priority:
        for c in cands:
            if c.name.endswith(f".{p}.vtt"):
                return c
    return sorted(cands)[0]


def download_youtube_vtt(ytdlp: str, video_url: str, video_id: str, workdir: Path) -> Path:
    lang_sets = [
        "zh-Hans,zh-CN,zh-Hant,zh,en-orig,en",
        "en-orig,en",
    ]
    for langs in lang_sets:
        cmd = [
            ytdlp,
            "--skip-download",
            "--write-auto-subs",
            "--write-subs",
            "--extractor-args",
            "youtube:player_client=android",
            "--sub-langs",
            langs,
            "--sub-format",
            "vtt",
            "-o",
            str(workdir / "%(id)s.%(ext)s"),
            video_url,
        ]
        run(cmd)
        vtt = choose_vtt(video_id, workdir)
        if vtt is not None:
            return vtt
    raise RuntimeError("no subtitle file downloaded")


def scripod_episode_id(url: str) -> Optional[str]:
    m = re.search(r"scripod\.com/episode/([A-Za-z0-9_-]+)", url)
    return m.group(1) if m else None


def parse_scripod_transcript(url: str) -> Tuple[str, str, List[str]]:
    eid = scripod_episode_id(url)
    if not eid:
        raise RuntimeError("invalid scripod episode url")
    api = f"https://scripod.com/api/transcript/{eid}"
    data = json.loads(http_get(api))
    title = data.get("title") or eid
    speakers: Dict[str, str] = data.get("speakers", {}) or {}
    lines: List[str] = []
    for seg in data.get("segments", []):
        sid = seg.get("speaker")
        spk = speakers.get(str(sid)) if sid is not None else None
        if not spk:
            spk = f"Speaker {sid}" if sid is not None else "Unknown"
        sents = seg.get("sentences", []) or []
        if not sents:
            continue
        start = float(sents[0].get("start", 0.0) or 0.0)
        txt = "".join((s.get("text") or "") for s in sents).strip()
        if not txt:
            continue
        lines.append(f"[{seconds_to_hms(start)}] {spk}: {txt}")
    return eid, title, lines


def extract_urls(text: str) -> List[str]:
    urls = []
    for m in URL_RE.findall(text):
        u = m.rstrip(".,;)]}>")
        urls.append(u)
    out: List[str] = []
    seen = set()
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def normalize_speaker(value: Any) -> str:
    s = str(value).strip() if value is not None else ""
    if not s:
        return ""
    if re.fullmatch(r"\d+", s):
        return f"Speaker {s}"
    return s


def clean_html_fragment(raw: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", raw, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = text.replace("\u200b", " ")
    return compact_ws(text)


def parse_substack_transcription_data(payload: Any) -> List[str]:
    lines: List[str] = []

    if isinstance(payload, list):
        cur_speaker = ""
        cur_start = 0.0
        buf = ""

        def flush() -> None:
            nonlocal cur_speaker, cur_start, buf
            text = compact_ws(buf)
            if text:
                spk = cur_speaker or "Speaker"
                lines.append(f"[{seconds_to_hms(cur_start)}] {spk}: {text}")
            cur_speaker = ""
            cur_start = 0.0
            buf = ""

        for item in payload:
            if not isinstance(item, dict):
                continue
            piece = compact_ws(str(item.get("text") or ""))
            if not piece:
                continue
            start = float(item.get("start") or 0.0)
            spk = normalize_speaker(item.get("speaker"))
            if not spk:
                words = item.get("words")
                if isinstance(words, list):
                    for w in words:
                        if not isinstance(w, dict):
                            continue
                        spk = normalize_speaker(w.get("speaker"))
                        if spk:
                            break
            if not spk:
                spk = cur_speaker or "Speaker"

            if not buf:
                cur_speaker = spk
                cur_start = start
                buf = piece
            elif spk != cur_speaker:
                flush()
                cur_speaker = spk
                cur_start = start
                buf = piece
            else:
                buf = append_with_spacing(buf, piece)

            if re.search(r"[.!?。！？][\"'”’)]?$", piece) or len(buf) >= 260:
                flush()

        flush()
        return dedup_consecutive(lines)

    if isinstance(payload, dict) and isinstance(payload.get("segments"), list):
        speakers = payload.get("speakers", {}) or {}
        for seg in payload.get("segments", []):
            if not isinstance(seg, dict):
                continue
            sid = seg.get("speaker")
            spk = speakers.get(str(sid)) if sid is not None else None
            if not spk:
                spk = normalize_speaker(sid) or "Speaker"
            sents = seg.get("sentences", []) or []
            if not sents:
                continue
            start = float((sents[0] or {}).get("start", 0.0) or 0.0)
            text = compact_ws("".join((s.get("text") or "") for s in sents if isinstance(s, dict)))
            if text:
                lines.append(f"[{seconds_to_hms(start)}] {spk}: {text}")
        return dedup_consecutive(lines)

    raise RuntimeError("unsupported transcription.json payload schema")


def parse_substack_transcription_json(url: str) -> List[str]:
    payload = json.loads(http_get(url))
    lines = parse_substack_transcription_data(payload)
    if not lines:
        raise RuntimeError("substack transcription.json parsed empty")
    return lines


def extract_transcription_json_urls(text: str) -> List[str]:
    out: List[str] = []
    seen = set()
    for m in TRANSCRIPTION_JSON_RE.findall(text or ""):
        u = html.unescape(m).rstrip("\\")
        u = u.rstrip(".,;)]}>")
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def parse_lex_transcript_html(page_html: str) -> List[str]:
    lines: List[str] = []
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", page_html, flags=re.I | re.S)

    for p in paragraphs:
        speaker = ""
        spk_match = re.search(r"<strong[^>]*>\s*([^<]{1,80})\s*</strong>", p, flags=re.I)
        if spk_match:
            candidate = compact_ws(spk_match.group(1))
            if re.fullmatch(r"[A-Za-z][A-Za-z .'\-]{0,70}", candidate):
                speaker = candidate

        ts_match = re.search(r"\b(\d{2}:\d{2}:\d{2})\b", p)
        ts = ts_match.group(1) if ts_match else "00:00:00"

        text = p
        if spk_match:
            text = text.replace(spk_match.group(0), " ", 1)
        text = clean_html_fragment(text)
        text = re.sub(r"^[\-–—:：\s]+", "", text)
        if not text:
            continue

        if speaker:
            lines.append(f"[{ts}] {speaker}: {text}")
            continue

        generic = re.match(r"^([A-Z][A-Za-z .'\-]{1,50}):\s+(.+)$", text)
        if generic:
            lines.append(f"[{ts}] {generic.group(1)}: {generic.group(2)}")

    lines = dedup_consecutive(lines)
    if len(lines) < 20:
        raise RuntimeError("lex transcript parse result too small")
    return lines


def parse_official_transcript_url(url: str) -> Tuple[List[str], str]:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()

    if "scripod.com" in host and "scripod.com/episode/" in url:
        _eid, _title, lines = parse_scripod_transcript(url)
        return lines, f"https://scripod.com/api/transcript/{scripod_episode_id(url)}"

    if "transcription.json" in url:
        return parse_substack_transcription_json(url), url

    page_html = http_get(url)

    for candidate in extract_transcription_json_urls(page_html):
        try:
            return parse_substack_transcription_json(candidate), candidate
        except Exception:
            continue

    if "lexfridman.com" in host and "transcript" in parsed.path:
        return parse_lex_transcript_html(page_html), url

    raise RuntimeError("unsupported official transcript format")


def normalize_for_match(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text)
    return compact_ws(text)


def title_match_score(query: str, track_name: str, collection_name: str) -> float:
    q = normalize_for_match(query)
    t = normalize_for_match(track_name)
    c = normalize_for_match(collection_name)
    if not q or not t:
        return 0.0

    score = 0.0
    if q == t:
        score += 40.0
    if q in t:
        score += 25.0
    if q in c:
        score += 8.0

    for tok in q.split():
        if len(tok) <= 1:
            continue
        if tok in t:
            score += 4.0
        elif tok in c:
            score += 1.5

    return score


def resolve_title_to_itunes_episode(title: str, limit: int = 12) -> Dict[str, str]:
    term = urllib.parse.quote(title)
    api = f"https://itunes.apple.com/search?media=podcast&entity=podcastEpisode&limit={limit}&term={term}"
    payload = json.loads(http_get(api, timeout=30))
    results = payload.get("results") or []
    if not isinstance(results, list) or not results:
        raise RuntimeError("itunes episode search returned no results")

    best: Optional[Dict[str, Any]] = None
    best_score = -1.0
    for item in results:
        if not isinstance(item, dict):
            continue
        episode_url = str(item.get("episodeUrl") or "").strip()
        track_name = str(item.get("trackName") or "").strip()
        collection_name = str(item.get("collectionName") or "").strip()
        if not (episode_url and track_name):
            continue
        s = title_match_score(title, track_name, collection_name)
        if s > best_score:
            best_score = s
            best = item

    if not best:
        raise RuntimeError("itunes episode search returned no usable episodeUrl")

    episode_url = str(best.get("episodeUrl") or "").strip()
    track_name = str(best.get("trackName") or "").strip()
    collection_name = str(best.get("collectionName") or "").strip()
    episode_guid = str(best.get("episodeGuid") or best.get("trackId") or "").strip()
    feed_url = str(best.get("feedUrl") or "").strip()
    track_view_url = str(best.get("trackViewUrl") or "").strip()

    if not episode_guid:
        episode_guid = stable_id_from_url(episode_url)
    if not episode_url:
        raise RuntimeError("itunes result missing episodeUrl")

    return {
        "episode_url": episode_url,
        "track_name": track_name or title,
        "collection_name": collection_name,
        "episode_guid": episode_guid,
        "feed_url": feed_url,
        "track_view_url": track_view_url,
    }


def extract_og_content(page_html: str, prop: str) -> Optional[str]:
    p = re.escape(prop)
    patterns = [
        rf'<meta[^>]+property=["\']{p}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{p}["\']',
        rf'<meta[^>]+name=["\']{p}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']{p}["\']',
    ]
    for pattern in patterns:
        m = re.search(pattern, page_html, flags=re.I)
        if m:
            return html.unescape(m.group(1).strip())
    return None


def extract_audio_from_episode_page(url: str) -> Tuple[str, str]:
    page = http_get(url, timeout=30)
    audio = extract_og_content(page, "og:audio")
    if not audio:
        ld = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', page, flags=re.I | re.S)
        for block in ld:
            try:
                data = json.loads(block)
            except Exception:
                continue
            if isinstance(data, dict):
                media = data.get("associatedMedia") or {}
                if isinstance(media, dict):
                    v = media.get("contentUrl")
                    if isinstance(v, str) and v.startswith("http"):
                        audio = v
                        break
    if not audio:
        raise RuntimeError("episode page has no og:audio or associatedMedia.contentUrl")

    title = extract_og_content(page, "og:title")
    if not title:
        m = re.search(r"<title>(.*?)</title>", page, flags=re.I | re.S)
        title = compact_ws(html.unescape(m.group(1))) if m else "podcast episode"
    return compact_ws(title), compact_ws(audio)


def download_audio_file(audio_url: str, dest: Path) -> None:
    req = urllib.request.Request(audio_url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f, length=1 << 20)


def run_local_asr(audio_path: Path) -> Tuple[List[str], Dict[str, Any]]:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "local ASR requires faster-whisper. Install: pip install faster-whisper"
        ) from e

    model = WhisperModel(ASR_MODEL, device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        str(audio_path),
        beam_size=5,
        vad_filter=True,
        condition_on_previous_text=True,
    )

    lines: List[str] = []
    for seg in segments:
        text = compact_ws(getattr(seg, "text", ""))
        if not text:
            continue
        ts = seconds_to_hms(float(getattr(seg, "start", 0.0) or 0.0))
        lines.append(f"[{ts}] {text}")

    if not lines:
        raise RuntimeError("local ASR returned empty transcript")

    asr_meta = {
        "model": ASR_MODEL,
        "language": str(getattr(info, "language", "")),
        "duration_sec": float(getattr(info, "duration", 0.0) or 0.0),
        "line_count": len(lines),
    }
    return lines, asr_meta


def stable_id_from_url(url: str) -> str:
    p = urllib.parse.urlparse(url)
    slug = Path(p.path).stem or p.netloc or "official"
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", slug).strip("-")
    return slug[:40] or "official"


def official_links_from_description(description: str) -> List[str]:
    urls = extract_urls(description or "")

    def score(u: str) -> int:
        pu = urllib.parse.urlparse(u)
        host = pu.netloc.lower()
        path = pu.path.lower()
        s = 0
        if "transcription.json" in u:
            s += 300
        if "lexfridman.com" in host and "transcript" in path:
            s += 260
        if "dwarkesh.com" in host:
            s += 230
        if "scripod.com" in host and "/episode/" in path:
            s += 220
        if "substack" in host:
            s += 180
        if "transcript" in path:
            s += 120
        if "podcast" in path:
            s += 40
        return s

    ranked = sorted(urls, key=score, reverse=True)
    out: List[str] = []
    seen = set()
    for u in ranked:
        if u in seen:
            continue
        seen.add(u)
        if score(u) > 0:
            out.append(u)
    return out[:12]


def run_subtitle_pipeline(ytdlp: str, page_url: str, real_id: str, meta: Dict[str, Any]) -> Tuple[List[str], Dict[str, float]]:
    with tempfile.TemporaryDirectory(prefix="podcast_sub_") as td:
        vtt = download_youtube_vtt(ytdlp, page_url, real_id, Path(td))
        cues = parse_vtt_cues(vtt.read_text(encoding="utf-8", errors="ignore"))
        merged_text = merge_cues_with_overlap(cues)
        lines = split_lines(merged_text)
        metrics = quality_metrics(lines)
        if is_low_quality(metrics):
            repaired = aggressive_split_lines(merged_text)
            repaired_metrics = quality_metrics(repaired)
            if quality_score(repaired_metrics) > quality_score(metrics):
                log_attempt(meta, "B_quality_repair", True, "applied aggressive splitter to improve readability")
                lines = repaired
                metrics = repaired_metrics
            else:
                log_attempt(meta, "B_quality_repair", False, "aggressive splitter did not improve quality")
    return lines, metrics


def extract_x_status_id(url: str) -> Optional[str]:
    try:
        path = urllib.parse.urlparse(url).path
    except Exception:
        return None
    m = re.search(r"/status/(\d+)", path)
    return m.group(1) if m else None


def x_payload_from_api(url: str) -> Dict:
    sid = extract_x_status_id(url)
    if not sid:
        return {}
    api = f"https://api.fxtwitter.com/status/{sid}"
    try:
        payload = json.loads(http_get(api))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def x_text_hint(url: str) -> str:
    payload = x_payload_from_api(url)
    tweet = payload.get("tweet", {}) if isinstance(payload, dict) else {}
    if not isinstance(tweet, dict):
        return ""

    author = ""
    author_obj = tweet.get("author") or {}
    if isinstance(author_obj, dict):
        author = (author_obj.get("name") or "").strip()

    raw_text_obj = tweet.get("raw_text") or {}
    raw_text = tweet.get("text") or ""
    mentions: List[str] = []

    if isinstance(raw_text_obj, dict):
        if not raw_text:
            raw_text = raw_text_obj.get("text") or ""
        facets = raw_text_obj.get("facets") or []
        if isinstance(facets, list):
            for facet in facets:
                if not isinstance(facet, dict):
                    continue
                if facet.get("type") == "mention":
                    name = (facet.get("original") or "").strip()
                    if name:
                        mentions.append(name)

    cleaned = re.sub(r"https?://\S+", " ", raw_text)
    cleaned = re.sub(r"@\w+", " ", cleaned)
    cleaned = compact_ws(cleaned)
    first_sentence = re.split(r"[.!?。！？]", cleaned)[0].strip()
    if len(first_sentence) > 90:
        first_sentence = first_sentence[:90].rsplit(" ", 1)[0].strip()

    parts: List[str] = []
    if author:
        parts.append(author)
    if mentions:
        parts.append(" ".join(mentions[:2]))
    if first_sentence:
        parts.append(first_sentence)
    parts.append("podcast interview")

    query = compact_ws(" ".join(parts))
    return query[:180]


def links_from_x(url: str) -> List[str]:
    all_urls: List[str] = []

    payload = x_payload_from_api(url)
    tweet = payload.get("tweet", {}) if isinstance(payload, dict) else {}
    if isinstance(tweet, dict):
        for key in ("text", "url"):
            val = tweet.get(key)
            if isinstance(val, str):
                all_urls.extend(extract_urls(val))

        rt = tweet.get("raw_text") or {}
        if isinstance(rt, dict):
            txt = rt.get("text")
            if isinstance(txt, str):
                all_urls.extend(extract_urls(txt))
            facets = rt.get("facets") or []
            if isinstance(facets, list):
                for facet in facets:
                    if not isinstance(facet, dict):
                        continue
                    rep = facet.get("replacement")
                    if isinstance(rep, str) and rep.startswith("http"):
                        all_urls.append(rep)

    variants = [url, url.replace("x.com/", "fxtwitter.com/"), url.replace("twitter.com/", "fxtwitter.com/")]
    for u in variants:
        try:
            page = http_get(u)
            all_urls.extend(extract_urls(page))
        except Exception:
            continue

    out: List[str] = []
    seen = set()
    for u in all_urls:
        host = urllib.parse.urlparse(u).netloc.lower()
        if any(x in host for x in ["x.com", "twitter.com", "fxtwitter.com", "t.co"]):
            continue
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def write_outputs(out_dir: Path, title: str, stable_id: str, lines: List[str], meta: dict) -> Tuple[Path, Path]:
    base = f"{sanitize_filename(title)} [{stable_id}]"
    txt_path = out_dir / f"{base}.txt"
    meta_path = out_dir / f"{base}.meta.json"
    txt_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return txt_path, meta_path


def process_youtube_target(ytdlp: str, target: str, out_dir: Path, meta: Dict[str, Any], resolver_name: str) -> Tuple[Path, Path]:
    info = youtube_metadata(ytdlp, target)
    real_id = info["id"]
    title = info["title"]
    page_url = info["webpage_url"]
    description = info.get("description", "")

    meta["source"] = page_url
    log_attempt(meta, "yt_metadata", True, f"resolved video {real_id}", source=page_url)

    # Priority A: official transcript links in YouTube description.
    links = official_links_from_description(description)
    if not links:
        log_attempt(meta, "A_official", False, "no official transcript links found in description")
    else:
        for link in links:
            try:
                lines, actual_source = parse_official_transcript_url(link)
                m = quality_metrics(lines)
                if not lines:
                    raise RuntimeError("official transcript parsed empty")
                if is_low_quality(m):
                    log_attempt(meta, "A_official", False, "official transcript quality is too low", source=actual_source)
                    continue
                meta["resolver"] = "official-link"
                meta["source"] = actual_source
                meta["quality"] = m
                log_attempt(meta, "A_official", True, f"resolved via {urllib.parse.urlparse(link).netloc}", source=actual_source)
                return write_outputs(out_dir, title, real_id, lines, meta)
            except Exception as e:
                log_attempt(meta, "A_official", False, str(e), source=link)

    # Priority B: platform subtitles.
    lines, metrics = run_subtitle_pipeline(ytdlp, page_url, real_id, meta)
    meta["resolver"] = resolver_name
    meta["quality"] = metrics
    if is_low_quality(metrics):
        meta["status"] = "warn"
        meta["notes"].append("subtitle transcript quality is low; try official transcript links or rerun later")
        log_attempt(meta, "B_subtitle", False, f"low quality output: {metrics}", source=page_url)
    else:
        log_attempt(meta, "B_subtitle", True, f"subtitle extraction ok: {metrics}", source=page_url)
    return write_outputs(out_dir, title, real_id, lines, meta)


def process_audio_url_target(
    audio_url: str,
    title: str,
    stable_id: str,
    out_dir: Path,
    meta: Dict[str, Any],
    resolver_name: str,
) -> Tuple[Path, Path]:
    with tempfile.TemporaryDirectory(prefix="podcast_asr_") as td:
        suffix = Path(urllib.parse.urlparse(audio_url).path).suffix or ".audio"
        audio_path = Path(td) / f"input{suffix}"
        download_audio_file(audio_url, audio_path)
        lines, asr_meta = run_local_asr(audio_path)

    metrics = quality_metrics(lines)
    meta["resolver"] = resolver_name
    meta["source"] = audio_url
    meta["quality"] = metrics
    meta["asr"] = asr_meta
    meta["status"] = "warn"
    meta["notes"].append(
        "ASR transcript is a draft; proofread with any LLM for names/terms before publishing."
    )
    log_attempt(meta, "C_local_asr", True, f"model={ASR_MODEL}, lines={len(lines)}", source=audio_url)
    return write_outputs(out_dir, title, stable_id, lines, meta)


def process_item(raw: str, out_dir: Path, ytdlp: Optional[str]) -> Tuple[Path, Path]:
    meta: Dict[str, Any] = {
        "input": raw,
        "resolver": None,
        "source": None,
        "status": "ok",
        "notes": [],
        "attempts": [],
    }

    raw = raw.strip()

    # A) Direct known transcript host.
    if is_url(raw) and "scripod.com/episode/" in raw:
        try:
            eid, title, lines = parse_scripod_transcript(raw)
            m = quality_metrics(lines)
            meta["resolver"] = "scripod-api"
            meta["source"] = f"https://scripod.com/api/transcript/{eid}"
            meta["quality"] = m
            log_attempt(meta, "A_direct_scripod", True, f"parsed {m['line_count']} lines", source=meta["source"])
            return write_outputs(out_dir, title, eid, lines, meta)
        except Exception as e:
            log_attempt(meta, "A_direct_scripod", False, str(e), source=raw)
            raise

    # A2) Direct official transcript page/json URL.
    if is_url(raw) and not ("x.com/" in raw or "twitter.com/" in raw) and not extract_youtube_id(raw):
        try:
            lines, actual_source = parse_official_transcript_url(raw)
            m = quality_metrics(lines)
            parsed = urllib.parse.urlparse(raw)
            title_guess = Path(parsed.path).stem or parsed.netloc or "official transcript"
            title_guess = compact_ws(title_guess.replace("-", " ").replace("_", " "))
            meta["resolver"] = "official-link-direct"
            meta["source"] = actual_source
            meta["quality"] = m
            if is_low_quality(m):
                meta["status"] = "warn"
                meta["notes"].append("official transcript parsed but readability is below threshold")
                log_attempt(meta, "A_direct_official", False, f"low quality output: {m}", source=actual_source)
            else:
                log_attempt(meta, "A_direct_official", True, f"parsed {m['line_count']} lines", source=actual_source)
            return write_outputs(out_dir, title_guess, stable_id_from_url(raw), lines, meta)
        except Exception as e:
            log_attempt(meta, "A_direct_official", False, str(e), source=raw)

    # B) X/Twitter indirection.
    if is_url(raw) and ("x.com/" in raw or "twitter.com/" in raw):
        links = links_from_x(raw)
        log_attempt(meta, "x_resolve", True, f"discovered outbound links: {len(links)}", source=raw)

        direct = None
        for u in links:
            if extract_youtube_id(u) or "scripod.com/episode/" in u or looks_like_audio_url(u):
                direct = u
                break

        if direct:
            meta["notes"].append(f"resolved direct transcript/subtitle source: {direct}")
            raw = direct
            log_attempt(meta, "x_resolve", True, "resolved to direct source", source=direct)
        else:
            hint = x_text_hint(raw)
            if hint and ytdlp:
                preview = ", ".join(links[:2]) if links else "none"
                meta["notes"].append(f"x outbound links are not directly supported ({preview}); fallback to title search from tweet text")
                raw = hint
                log_attempt(meta, "x_resolve", True, "fallback to title hint", source=raw)
            else:
                log_attempt(meta, "x_resolve", False, "no usable direct source and no title hint", source=raw)
                raise RuntimeError("x status resolved no usable transcript source and no searchable text hint")

    # C) Generic non-YouTube URL: audio URL or episode page -> local ASR.
    if is_url(raw) and not ("x.com/" in raw or "twitter.com/" in raw) and not extract_youtube_id(raw):
        if looks_like_audio_url(raw):
            guessed_title = compact_ws(Path(urllib.parse.urlparse(raw).path).stem.replace("-", " ").replace("_", " "))
            guessed_title = guessed_title or "podcast episode"
            sid = stable_id_from_url(raw)
            try:
                log_attempt(meta, "C_audio_url", True, "detected direct audio url", source=raw)
                return process_audio_url_target(raw, guessed_title, sid, out_dir, meta, resolver_name="audio-url-asr")
            except Exception as e:
                log_attempt(meta, "C_audio_url", False, str(e), source=raw)
                raise

        try:
            page_title, audio_url = extract_audio_from_episode_page(raw)
            sid = stable_id_from_url(raw)
            log_attempt(meta, "C_episode_page", True, "extracted og:audio from episode page", source=raw)
            return process_audio_url_target(audio_url, page_title, sid, out_dir, meta, resolver_name="episode-page-asr")
        except Exception as e:
            log_attempt(meta, "C_episode_page", False, str(e), source=raw)

    # C) YouTube URL or ID.
    vid = extract_youtube_id(raw)
    if vid and ytdlp:
        video_url = youtube_url_from_id(vid)
        return process_youtube_target(ytdlp, video_url, out_dir, meta, resolver_name="youtube-id")

    # D) Plain title: YouTube first, then Apple podcastEpisode -> ASR.
    if not is_url(raw):
        if ytdlp:
            try:
                info = resolve_title_to_youtube(ytdlp, raw)
                log_attempt(meta, "title_search", True, f"matched video {info['id']}", source=info["webpage_url"])
                return process_youtube_target(ytdlp, info["webpage_url"], out_dir, meta, resolver_name="title->ytsearch1")
            except Exception as e:
                log_attempt(meta, "title_search", False, str(e), source=raw)

        try:
            ep = resolve_title_to_itunes_episode(raw)
            src = ep["track_view_url"] or ep["feed_url"] or ep["episode_url"]
            detail = f"matched episode {ep['episode_guid']} from {ep['collection_name'] or 'podcast'}"
            log_attempt(meta, "title_itunes", True, detail, source=src)
            return process_audio_url_target(
                ep["episode_url"],
                ep["track_name"],
                ep["episode_guid"],
                out_dir,
                meta,
                resolver_name="title->itunes-episode-asr",
            )
        except Exception as e:
            log_attempt(meta, "title_itunes", False, str(e), source=raw)

    if not ytdlp:
        raise RuntimeError("yt-dlp not found and local ASR fallback failed; install yt-dlp or provide official transcript URL")
    raise RuntimeError("no deterministic resolver matched this input")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export podcast transcript to TXT with deterministic source priority")
    parser.add_argument("--input", action="append", required=True, help="YouTube URL/ID, X status URL, known episode URL, or plain title")
    parser.add_argument("--out-dir", default=".", help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    ytdlp = find_ytdlp()
    if not ytdlp:
        print("WARN: yt-dlp not found; only official-host transcript paths will work.", file=sys.stderr)

    failures = 0
    for raw in args.input:
        try:
            txt, meta = process_item(raw, out_dir, ytdlp)
            print(f"OK\t{txt}")
            print(f"META\t{meta}")
        except Exception as e:
            failures += 1
            print(f"FAIL\t{raw}\t{e}", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
