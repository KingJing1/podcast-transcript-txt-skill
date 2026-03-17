import importlib.util
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "podcast_transcript_txt.py"
SPEC = importlib.util.spec_from_file_location("podcast_transcript_txt", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ParserTests(unittest.TestCase):
    def test_parse_ttml_transcript_text(self) -> None:
        payload = """<?xml version="1.0" encoding="UTF-8"?>
<tt xmlns="http://www.w3.org/ns/ttml">
  <body>
    <div>
      <p begin="00:00:01.000">Hello world</p>
      <p begin="00:00:03.500" speaker="Host">Second line</p>
    </div>
  </body>
</tt>
"""
        lines = MODULE.parse_ttml_transcript_text(payload)
        self.assertEqual(lines[0], "[00:00:01] Hello world")
        self.assertEqual(lines[1], "[00:00:03] Host: Second line")

    def test_extract_structured_page_text_from_html_xiaoyuzhou(self) -> None:
        page_html = """
<html>
  <head>
    <meta property="og:title" content="测试节目" />
    <script id="__NEXT_DATA__" type="application/json">
      {"props":{"pageProps":{"episode":{
        "title":"测试节目",
        "description":"一句很短的简介",
        "shownotes":"<p>第一段内容很长，足够作为页面文字回退，而且明确不是空洞简介，能够代表主持人在页面上给出的完整结构化说明。</p><p>第二段继续补充上下文，增加更多文字，确保这个页面文本在测试里超过最小阈值，不会误判为过短。</p>",
        "transcript":{"mediaId":"abc123.m4a"},
        "transcriptMediaId":"abc123.m4a"
      }}}}
    </script>
  </head>
  <body></body>
</html>
"""
        title, lines, meta = MODULE.extract_structured_page_text_from_html(
            "https://www.xiaoyuzhoufm.com/episode/test-id",
            page_html,
        )
        self.assertEqual(title, "测试节目")
        self.assertTrue(any("第一段内容很长" in line for line in lines))
        self.assertEqual(meta["kind"], "shownotes")
        self.assertEqual(meta["transcript_media_id"], "abc123.m4a")
        self.assertTrue(meta["has_transcript_marker"])

    def test_process_item_surfaces_local_transcript_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bad_ttml = Path(td) / "bad.ttml"
            bad_ttml.write_text(
                '<tt><body><div><p begin="00:00:01.000">Only one line</p></div></body></tt>',
                encoding="utf-8",
            )
            out_dir = Path(td) / "out"
            with self.assertRaisesRegex(RuntimeError, "TTML transcript parsed too few lines"):
                MODULE.process_item(str(bad_ttml), out_dir, ytdlp=None, asr_model="small", page_text_fallback="auto")

    def test_build_doctor_checks_reports_missing_dependencies(self) -> None:
        checks, exit_code = MODULE.build_doctor_checks(
            python_version=(3, 9),
            ytdlp_path="",
            faster_whisper_status=(False, "missing faster-whisper"),
            model_root_status=(True, "model root ready"),
        )
        self.assertEqual(exit_code, 1)
        by_name = {item["name"]: item for item in checks}
        self.assertEqual(by_name["python"]["status"], "OK")
        self.assertEqual(by_name["yt-dlp"]["status"], "FAIL")
        self.assertEqual(by_name["faster-whisper"]["status"], "FAIL")

    def test_build_doctor_checks_reports_ready(self) -> None:
        checks, exit_code = MODULE.build_doctor_checks(
            python_version=(3, 11),
            ytdlp_path="/usr/local/bin/yt-dlp",
            faster_whisper_status=(True, "faster-whisper ok"),
            model_root_status=(True, "model root ready"),
        )
        self.assertEqual(exit_code, 0)
        self.assertTrue(all(item["status"] == "OK" for item in checks))

    def test_process_youtube_target_falls_back_to_asr_when_subtitles_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "out"
            out_dir.mkdir()
            fake_audio = Path(td) / "audio.m4a"
            fake_audio.write_text("stub", encoding="utf-8")
            meta = {
                "input": "https://www.youtube.com/watch?v=abcdefghijk",
                "resolver": None,
                "source": None,
                "status": "ok",
                "notes": [],
                "attempts": [],
            }
            with mock.patch.object(
                MODULE,
                "youtube_metadata",
                return_value={
                    "id": "abcdefghijk",
                    "title": "YouTube Test",
                    "webpage_url": "https://www.youtube.com/watch?v=abcdefghijk",
                    "description": "",
                },
            ), mock.patch.object(MODULE, "official_links_from_description", return_value=[]), mock.patch.object(
                MODULE, "run_subtitle_pipeline", side_effect=RuntimeError("no subtitle file downloaded")
            ), mock.patch.object(MODULE, "download_youtube_audio", return_value=fake_audio) as download_mock, mock.patch.object(
                MODULE,
                "run_local_asr",
                return_value=(["[00:00:01] Hello from ASR"], {"model": "small"}),
            ):
                txt_path, meta_path = MODULE.process_youtube_target(
                    "yt-dlp",
                    "https://www.youtube.com/watch?v=abcdefghijk",
                    out_dir,
                    meta,
                    resolver_name="youtube-id",
                    asr_model="small",
                )

            self.assertTrue(download_mock.called)
            self.assertEqual(txt_path.read_text(encoding="utf-8").strip(), "[00:00:01] Hello from ASR")
            meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
            self.assertEqual(meta_data["resolver"], "youtube-id-asr")
            self.assertEqual(meta_data["asr"]["model"], "small")

    def test_process_item_direct_audio_url_skips_official_transcript_parser(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "out"
            out_dir.mkdir()
            meta_txt = out_dir / "episode [id].txt"
            meta_json = out_dir / "episode [id].meta.json"
            meta_txt.write_text("ok\n", encoding="utf-8")
            meta_json.write_text("{}\n", encoding="utf-8")
            with mock.patch.object(MODULE, "parse_official_transcript_url") as parse_official_mock, mock.patch.object(
                MODULE,
                "process_audio_url_target",
                return_value=(meta_txt, meta_json),
            ) as audio_mock:
                txt_path, meta_path = MODULE.process_item(
                    "https://example.com/audio.mp3",
                    out_dir,
                    ytdlp="yt-dlp",
                    asr_model="small",
                    page_text_fallback="auto",
                )
            parse_official_mock.assert_not_called()
            self.assertTrue(audio_mock.called)
            self.assertEqual(txt_path, meta_txt)
            self.assertEqual(meta_path, meta_json)

    def test_process_item_plain_title_prefers_scripod_before_youtube(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "out"
            out_dir.mkdir()
            with mock.patch.object(
                MODULE,
                "resolve_title_to_scripod_episode",
                return_value={
                    "episode_id": "sp123",
                    "track_name": "Best Episode",
                    "collection_name": "Best Show",
                    "feed_url": "https://feed.example.com",
                    "episode_guid": "guid123",
                },
            ) as scripod_resolve_mock, mock.patch.object(
                MODULE,
                "parse_scripod_transcript",
                return_value=("sp123", "Best Episode", ["[00:00:01] Official transcript"]),
            ), mock.patch.object(MODULE, "resolve_title_to_youtube") as youtube_mock:
                txt_path, meta_path = MODULE.process_item(
                    "Best Episode",
                    out_dir,
                    ytdlp="yt-dlp",
                    asr_model="small",
                    page_text_fallback="auto",
                )
            self.assertTrue(scripod_resolve_mock.called)
            youtube_mock.assert_not_called()
            self.assertTrue(txt_path.exists())
            self.assertTrue(meta_path.exists())


if __name__ == "__main__":
    unittest.main()
