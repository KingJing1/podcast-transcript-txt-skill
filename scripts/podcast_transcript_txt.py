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
from typing import Dict, List, Optional, Tuple

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)

YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
URL_RE = re.compile(r"https?://[^\s\"'<>]+")


def run(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:180] if len(name) > 180 else name


def seconds_to_hms(sec: float) -> str:
    t = int(sec)
    h = t // 3600
    m = (t % 3600) // 60
    s = t % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def http_get(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def find_ytdlp() -> Optional[str]:
    candidates = [
        os.getenv("YT_DLP_PATH"),
        str(Path.home() / "Library/Python/3.9/bin/yt-dlp"),
        shutil.which("yt-dlp"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
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


def youtube_info(ytdlp: str, target: str) -> Tuple[str, str, str]:
    cmd = [
        ytdlp,
        "--extractor-args",
        "youtube:player_client=android",
        "--skip-download",
        "--print",
        "%(id)s\t%(title)s\t%(webpage_url)s",
        target,
    ]
    p = run(cmd)
    if p.returncode != 0:
        raise RuntimeError(f"yt-dlp info failed: {p.stderr.strip()}")
    line = (p.stdout or "").strip().splitlines()
    if not line:
        raise RuntimeError("yt-dlp info returned empty output")
    parts = line[0].split("\t")
    if len(parts) < 3:
        raise RuntimeError(f"unexpected yt-dlp info format: {line[0]}")
    return parts[0], parts[1], parts[2]


def resolve_title_to_youtube(ytdlp: str, title: str) -> Tuple[str, str, str]:
    queries = [f"ytsearch1:{title} podcast", f"ytsearch1:{title}"]
    last_err = ""
    for q in queries:
        try:
            return youtube_info(ytdlp, q)
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
        text = re.sub(r"\s+", " ", text).strip()
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
    """Merge rolling captions by suffix-prefix overlap.

    YouTube auto-captions often repeat partial text across cues.
    This function keeps one continuous stream by appending only non-overlap.
    """
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

        need_space = (
            acc
            and tail
            and acc[-1].isalnum()
            and tail[0].isalnum()
            and not acc.endswith(" ")
        )
        if need_space:
            acc += " "
        acc += tail

    acc = re.sub(r"\s+([,.!?;:])", r"\1", acc)
    acc = re.sub(r"([，。！？；：、])\s+", r"\1", acc)
    acc = re.sub(r"\s+", " ", acc).strip()
    return acc


def split_lines(text: str) -> List[str]:
    if not text:
        return []

    text = text.replace(">>", "\n>>")
    parts = [p.strip() for p in text.splitlines() if p.strip()]
    out: List[str] = []
    for part in parts:
        segs = re.split(r"(?<=[.!?。！？])\s+", part)
        for s in segs:
            s = s.strip()
            if s:
                out.append(s)

    dedup: List[str] = []
    for x in out:
        if dedup and x == dedup[-1]:
            continue
        dedup.append(x)
    return dedup


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
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
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

    query = re.sub(r"\s+", " ", " ".join(parts)).strip()
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


def process_item(raw: str, out_dir: Path, ytdlp: Optional[str]) -> Tuple[Path, Path]:
    meta = {
        "input": raw,
        "resolver": None,
        "source": None,
        "status": "ok",
        "notes": [],
    }

    raw = raw.strip()

    # A) Known transcript host
    if is_url(raw) and "scripod.com/episode/" in raw:
        eid, title, lines = parse_scripod_transcript(raw)
        meta["resolver"] = "scripod-api"
        meta["source"] = f"https://scripod.com/api/transcript/{eid}"
        return write_outputs(out_dir, title, eid, lines, meta)

    # B) X/Twitter indirection
    if is_url(raw) and ("x.com/" in raw or "twitter.com/" in raw):
        links = links_from_x(raw)
        meta["resolver"] = "x-outbound-links"

        direct = None
        for u in links:
            if extract_youtube_id(u) or "scripod.com/episode/" in u:
                direct = u
                break

        if direct:
            meta["notes"].append(f"resolved direct transcript/subtitle source: {direct}")
            raw = direct
        else:
            hint = x_text_hint(raw)
            if hint and ytdlp:
                preview = ", ".join(links[:2]) if links else "none"
                meta["notes"].append(f"x outbound links are not directly supported ({preview}); fallback to title search from tweet text")
                raw = hint
            else:
                raise RuntimeError("x status resolved no usable transcript source and no searchable text hint")

    # C) YouTube URL or ID
    vid = extract_youtube_id(raw)
    if vid and ytdlp:
        video_url = youtube_url_from_id(vid)
        real_id, title, page_url = youtube_info(ytdlp, video_url)
        meta["resolver"] = "youtube-id"
        meta["source"] = page_url
        with tempfile.TemporaryDirectory(prefix="podcast_sub_") as td:
            vtt = download_youtube_vtt(ytdlp, page_url, real_id, Path(td))
            cues = parse_vtt_cues(vtt.read_text(encoding="utf-8", errors="ignore"))
            merged_text = merge_cues_with_overlap(cues)
            lines = split_lines(merged_text)
        return write_outputs(out_dir, title, real_id, lines, meta)

    # D) Plain title -> YouTube
    if ytdlp and not is_url(raw):
        real_id, title, page_url = resolve_title_to_youtube(ytdlp, raw)
        meta["resolver"] = "title->ytsearch1"
        meta["source"] = page_url
        with tempfile.TemporaryDirectory(prefix="podcast_sub_") as td:
            vtt = download_youtube_vtt(ytdlp, page_url, real_id, Path(td))
            cues = parse_vtt_cues(vtt.read_text(encoding="utf-8", errors="ignore"))
            merged_text = merge_cues_with_overlap(cues)
            lines = split_lines(merged_text)
        return write_outputs(out_dir, title, real_id, lines, meta)

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

