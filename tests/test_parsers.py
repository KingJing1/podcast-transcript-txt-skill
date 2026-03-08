import importlib.util
import unittest
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


if __name__ == "__main__":
    unittest.main()
