# Changelog

## v0.2.0 - 2026-02-22

- 核心脚本增强：
  - 新增 YouTube 描述区官方 transcript 外链探测（优先 A 路径）。
  - 支持解析 Substack `transcription.json`（含列表/segments 两种结构）。
  - 增加输出质量门禁（行数、行长、重复率）与自动二次切分修复。
  - `meta.json` 新增 `attempts[]` 诊断轨迹，记录每一步结果与失败原因。
- 稳定性优化：
  - `yt-dlp` 发现逻辑扩展（支持更多常见安装路径）。
  - 标题检索和 YouTube 解析统一 metadata 流程，减少分叉不一致。
- 文档重构：
  - README 改为“可分享、可复现、可排障”导向。
  - INSTALL / TROUBLESHOOTING 更新为最小可执行流程。

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
