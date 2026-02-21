# podcast-transcript-txt-skill

一个可复用的「播客转文字」Skill：输入 YouTube 链接或播客标题，输出清洗后的逐字稿 `txt`（并附 `meta.json`）。

## 作者与署名

- 作者：一龙小包子（GitHub: [@KingJing1](https://github.com/KingJing1)）
- 说明：本项目由一龙小包子发起与维护。

## 功能范围

- 稳定路径：
  - YouTube URL/ID -> 字幕提取 -> 文本清洗 -> TXT
  - 标题关键词 -> YouTube 检索 -> 字幕提取 -> 文本清洗 -> TXT
- 可选路径（best-effort）：
  - X/Twitter 链接解析（不保证每条都成功）

## 文档导航

- 安装与接入：[`INSTALL.md`](./INSTALL.md)
- 常见问题与故障排查：[`TROUBLESHOOTING.md`](./TROUBLESHOOTING.md)
- 变更记录：[`CHANGELOG.md`](./CHANGELOG.md)
- 贡献说明：[`CONTRIBUTING.md`](./CONTRIBUTING.md)

## 仓库结构

```text
.
├── SKILL.md
├── README.md
├── CONTRIBUTING.md
├── LICENSE
├── .gitignore
├── agents/
│   └── openai.yaml
├── references/
│   └── sources.md
└── scripts/
    └── podcast_transcript_txt.py
```

## 依赖

- `python3` (建议 3.10+)
- `yt-dlp`

## 快速开始

1) 链接模式

```bash
python3 scripts/podcast_transcript_txt.py \
  --input "https://www.youtube.com/watch?v=sXCKgEl9hBo" \
  --out-dir "/path/to/output"
```

2) 标题模式

```bash
python3 scripts/podcast_transcript_txt.py \
  --input "Naval podcast On Artificial Intelligence" \
  --out-dir "/path/to/output"
```

## 输出文件

- `<title> [<id>].txt`
- `<title> [<id>].meta.json`

## 分享给他人的推荐方式

1. 分享仓库链接（推荐）
- 优点：后续更新可直接 `git pull`
- 对方按 `INSTALL.md` 安装即可

2. 分享 ZIP 包
- 适合一次性分发
- 后续更新不方便同步

## 常见问题

- Q: 为什么有时 X 链接不稳定？
  - A: X 帖子本身可能只有 Spotify 等外链，不一定有可直接抓字幕的来源。建议优先给 YouTube 链接或标题。
- Q: 是否需要 cookies？
  - A: 默认不使用 cookies，优先走公开可访问路径。

## 维护建议（规矩）

- 先小改后大改，优先可审阅 diff。
- 保持决策树稳定（A -> B -> C），不要随机切换抓取策略。
- 对行为变更写明原因，并更新 `references/sources.md`。

## 版权与许可

本项目采用 [MIT License](./LICENSE)。
