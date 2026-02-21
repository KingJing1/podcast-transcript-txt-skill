# Changelog

## v0.1.0 - 2026-02-21

- 初始发布 `podcast-transcript-txt` skill。
- 支持稳定输入路径：
  - YouTube URL/ID
  - 标题关键词（`ytsearch1`）
- 输出：
  - `<title> [<id>].txt`
  - `<title> [<id>].meta.json`
- 文本清洗：
  - 去 HTML/timestamp 噪音
  - rolling captions overlap 合并，降低重复句
- 文档：
  - README
  - INSTALL
  - TROUBLESHOOTING
  - CONTRIBUTING

