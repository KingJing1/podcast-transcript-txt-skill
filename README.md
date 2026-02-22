# podcast-transcript-txt-skill

把播客链接快速落地为可读 `txt` 的 Skill。目标是少试错、可复现、可分享。

## 3 分钟上手（给别人分享时直接发这段）

```bash
git clone https://github.com/KingJing1/podcast-transcript-txt-skill.git
cd podcast-transcript-txt-skill
python3 scripts/podcast_transcript_txt.py \
  --input "https://www.youtube.com/watch?v=sXCKgEl9hBo" \
  --out-dir "/tmp/transcripts"
```

输出在 `--out-dir`：

- `<title> [<id>].txt`
- `<title> [<id>].meta.json`

## 这个版本解决了什么

- 固定决策树，减少随机试错。
- 优先官方 transcript 线索（YouTube 描述区外链）。
- 回退 YouTube 字幕（`yt-dlp`）。
- 自动做可读性质量检查，避免“超长文本墙”。
- `meta.json` 增加 `attempts`，失败可追踪。

## 支持矩阵

- `YouTube URL/ID`：稳定支持
- `播客标题关键词`：稳定支持（通过 `ytsearch1`）
- `X/Twitter 状态页`：best-effort（先解外链，失败再用文本 hint 检索）
- `Scripod episode URL`：稳定支持（官方 API）
- `官方 transcript 页/JSON URL`：稳定支持（如 Lex transcript、Substack transcription.json）

## 依赖

- `python3`（建议 3.10+）
- `yt-dlp`

## 快速开始

单个输入：
```bash
python3 scripts/podcast_transcript_txt.py \
  --input "https://www.youtube.com/watch?v=sXCKgEl9hBo" \
  --out-dir "/tmp/transcripts"
```

批量输入：

```bash
python3 scripts/podcast_transcript_txt.py \
  --input "https://www.youtube.com/watch?v=sXCKgEl9hBo" \
  --input "https://www.youtube.com/watch?v=0-LAT4HjWPo" \
  --input "Naval podcast On Artificial Intelligence" \
  --out-dir "/tmp/transcripts"
```

## 任何 Agent 都能用（重点）

本项目本质是一个 CLI 脚本，不绑定任何特定 Agent。  
只要你的 Agent 能执行 shell 命令，就能接入。

通用调用命令：

```bash
python3 scripts/podcast_transcript_txt.py \
  --input "<链接或标题>" \
  --out-dir "<输出目录>"
```

通用返回约定：

- 退出码 `0`：至少一个输入成功。
- 退出码 `1`：有输入失败（错误会打印 `FAIL\t<input>\t<error>`）。
- 每个输入产出一对文件：`*.txt` 和 `*.meta.json`。

## 平台映射（示例）

- `Codex`：可当 Skill 使用，也可直接跑脚本。
- `OpenClaw`：直接跑脚本命令并读取输出目录文件。
- `Claude Code`：直接跑脚本命令并读取输出目录文件。
- 其他 agent（Cursor Agent、Cline、自建 Agent）：同上，按 CLI 契约接入即可。
- `Claude App/Web` 这类非终端产品：先在本地跑脚本，再上传 `txt`。

## 输出说明

`meta.json` 重点字段：

- `resolver`：最终走了哪条路径
- `source`：最终来源 URL
- `status`：`ok` / `warn`
- `quality`：行数、平均行长、重复率等指标
- `attempts[]`：每一步执行日志（stage / ok / detail / source）

## 已知边界

- 不是 100% 成功：视频无字幕、平台限流、外链失效都可能失败。
- X/Twitter 路径是 best-effort，不保证稳定。
- 当前版本不内置本地 ASR（刻意保持轻量依赖）。

## 推荐分发方式

1. GitHub 仓库链接（推荐）。  
2. ZIP（一次性交付）。

## 文档导航

- 安装与接入：[`INSTALL.md`](./INSTALL.md)
- 故障排查：[`TROUBLESHOOTING.md`](./TROUBLESHOOTING.md)
- 变更记录：[`CHANGELOG.md`](./CHANGELOG.md)
- 贡献说明：[`CONTRIBUTING.md`](./CONTRIBUTING.md)
- 来源策略：[`references/sources.md`](./references/sources.md)

## 仓库结构

```text
.
├── SKILL.md
├── README.md
├── INSTALL.md
├── TROUBLESHOOTING.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── references/
│   └── sources.md
└── scripts/
    └── podcast_transcript_txt.py
```

## 许可

MIT License，见 [`LICENSE`](./LICENSE)。
