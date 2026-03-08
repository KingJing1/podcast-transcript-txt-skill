# Changelog

## v0.3.1 - 2026-03-08

- Episode page 优化：
  - 小宇宙页面新增 structured page text 回退，优先复用 `shownotes` / 可见文本，不再默认直接进入 ASR。
  - `meta.json` 新增 `episode-page-text` 解析结果与 `page_text` 元数据。
  - 保留 `transcriptMediaId` 作为后续官方 transcript 线索，不再忽略。
- 现成 transcript 复用：
  - 新增本地 transcript 文件直读，支持 `.ttml` 和受支持的 `.json`。
  - 远端 TTML transcript URL 也可直接解析，不再重复转 ASR。
- 稳定性与验证：
  - 启动时增加 Python 3.10+ 前置检查。
  - 新增解析测试，覆盖 TTML 和小宇宙页面结构化文本。

## v0.3.0 - 2026-03-05

- 核心解析链更新（纯标题输入）：
  - 新增 `Scripod search -> channel -> transcript` 解析路径，命中时直接输出官方 transcript，不进入 ASR。
  - 仅在 Scripod 未命中时，继续回退 Apple `podcastEpisode` -> episode audio -> local ASR。
  - `meta.json.resolver` 新增/强化 `title->scripod-api` 诊断标识，`attempts[]` 增加 `title_scripod` 轨迹。
- 规则与文档同步：
  - `SKILL.md` 的 plain-title 决策树已与脚本一致。
  - `README.md` 更新了解析顺序说明与 Resolution Matrix（Plain title 行）。

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
