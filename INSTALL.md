# 安装与接入

## 依赖

- `python3`（建议 3.10+）
- `yt-dlp`

校验：

```bash
python3 --version
yt-dlp --version
```

## 方式 A：当作普通脚本使用（推荐）

```bash
cd podcast-transcript-txt-skill
python3 scripts/podcast_transcript_txt.py \
  --input "https://www.youtube.com/watch?v=sXCKgEl9hBo" \
  --out-dir "/tmp/transcripts"
```

## 方式 B：当作 Codex Skill 使用

```bash
mkdir -p ~/.codex/skills
cp -R podcast-transcript-txt-skill ~/.codex/skills/podcast-transcript-txt
```

在对话中触发 `$podcast-transcript-txt`。

## 方式 C：给任何 Agent 直接接入（推荐通用法）

只要该 Agent 能执行 shell 命令，就直接调用：

```bash
python3 scripts/podcast_transcript_txt.py \
  --input "<链接或标题>" \
  --out-dir "<输出目录>"
```

接入时建议按以下契约处理：

1. 读标准输出中的 `OK` / `FAIL` 行作为执行结果。  
2. 成功后从 `--out-dir` 读取对应 `*.txt`。  
3. 同时读取同名 `*.meta.json` 作为可观测日志（`attempts`、`quality`、`resolver`）。  

## 给别人分发时的最小说明

把以下三条发给对方即可：

1. 安装 `python3` + `yt-dlp`。  
2. 运行上面的命令并指定 `--input`。  
3. 看输出目录里的 `*.txt` 和同名 `*.meta.json`。  

## 输入建议

- 优先：YouTube 直链
- 可直接：官方 transcript 页/JSON 链接
- 次优：标题关键词
- X/Twitter：best-effort，不保证每条都能直达字幕源
