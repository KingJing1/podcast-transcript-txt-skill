# 安装与接入

## 依赖

- `python3`（建议 3.10+）
- `yt-dlp`
- `faster-whisper`（用于 ASR fallback）

校验：

```bash
python3 --version
yt-dlp --version
python3 -c "import faster_whisper; print('faster-whisper ok')"
```

## 持久安装（强烈推荐）

如果你希望“今天能跑、下次也能跑”，请把 ASR 依赖安装到用户环境（`--user`）或项目固定虚拟环境，**不要依赖 `/tmp` 下的临时 venv**。

```bash
python3 -m pip install --user -U faster-whisper
python3 -c "import faster_whisper; print('ASR ready')"
```

说明：

1. `--user` 安装是持久的，重启后仍可用。  
2. `/tmp` 临时 venv 适合应急，不适合长期使用。  
3. 模型文件会缓存在 `~/.cache/huggingface/hub`，首次慢，后续复用。  

## 方式 A：当作普通脚本使用（推荐）

```bash
cd podcast-transcript-txt-skill
python3 scripts/podcast_transcript_txt.py \
  --input "https://www.youtube.com/watch?v=aR20FWCCjAs" \
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

1. 安装 `python3` + `yt-dlp` + `faster-whisper`（持久安装，非临时目录）。  
2. 运行上面的命令并指定 `--input`。  
3. 看输出目录里的 `*.txt` 和同名 `*.meta.json`。  

## 输入建议

- 优先：YouTube 直链
- 可直接：官方 transcript 页/JSON 链接
- 次优：标题关键词
- X/Twitter：best-effort，不保证每条都能直达字幕源
