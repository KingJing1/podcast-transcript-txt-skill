# 安装与接入

## 方式 A：当作普通脚本使用（最简单）

### 1) 准备依赖

- Python 3.10+
- `yt-dlp`

macOS 示例：

```bash
python3 --version
yt-dlp --version
```

如果没有 `yt-dlp`，可用 `pipx` 或包管理器安装。

### 2) 运行脚本

```bash
cd podcast-transcript-txt-skill
python3 scripts/podcast_transcript_txt.py \
  --input "https://www.youtube.com/watch?v=sXCKgEl9hBo" \
  --out-dir "/tmp/transcripts"
```

## 方式 B：当作 Codex Skill 使用

把本仓库目录放到你的 skills 目录下，例如：

```bash
mkdir -p ~/.codex/skills
cp -R podcast-transcript-txt-skill ~/.codex/skills/podcast-transcript-txt
```

然后在对话里让 agent 使用 `$podcast-transcript-txt`。

## 建议的输入策略

- 第一优先：YouTube 直链
- 第二优先：标题关键词
- X/Twitter 链接仅 best-effort，不作为稳定输入

## 输出约定

- `*.txt`：清洗后的逐字稿
- `*.meta.json`：输入来源、解析路径、状态信息

