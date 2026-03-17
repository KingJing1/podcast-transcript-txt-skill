# Troubleshooting

## 1) 运行后没有产出文件

先看标准输出是否有 `FAIL <input> <error>`，再检查：

```bash
ls -lh /你的输出目录
```

正式转写前，先跑一遍：

```bash
python3 scripts/podcast_transcript_txt.py --doctor
```

如果 `--doctor` 不是退出码 `0`，先把缺的依赖装齐。

## 2) YouTube 报 `PO token` / `429` / 网络失败

已内置 `youtube:player_client=android`。仍失败时建议：

1. 间隔几分钟重试。  
2. 换成同内容的官方频道视频链接。  
3. 降低并发，一次只跑 1-2 个输入。  

## 3) 文本可读性很差（超长行、像一堵墙）

脚本已加入质量门禁和二次切分。请先看 `meta.json` 的：

- `status` 是否为 `warn`
- `quality` 指标（`avg_line_len`、`max_line_len`）
- `attempts` 是否出现 `B_quality_repair`

## 4) X/Twitter 链接失败

这是 best-effort 路径。常见情况是帖子只有外链平台（如 Spotify）而无可抓字幕来源。  
建议直接改成：

- YouTube 链接
- 或“节目名 + 嘉宾名”标题输入

## 5) 报错 `local ASR requires faster-whisper`

说明当前环境缺少 ASR 依赖。安装后重试：

```bash
python3 -m pip install -r requirements.txt
python3 scripts/podcast_transcript_txt.py --doctor
```

## 6) 转写耗时太久（这是正常的吗）

当前 ASR 支持 `small` 和 `medium`。`small` 更快，`medium` 更稳。  
CPU 机器上常见范围：

- 30 分钟音频：`small` 约 8-20 分钟，`medium` 约 15-35 分钟
- 60 分钟音频：`small` 约 16-40 分钟，`medium` 约 30-70 分钟

如果你只要极速初稿，建议先改用可用字幕来源（YouTube）而不是纯 ASR。

## 7) 错字较多（人名、书名、术语）

这是 ASR 常见边界，尤其在中文专有名词上。推荐做法：

1. 保留原时间轴和段落顺序。
2. 用任意大模型做“最小改动订正”。
3. 只改明显同音错字和标点，不改原意。

示例提示词：

```text
Proofread this transcript with minimal edits: fix obvious homophone errors and punctuation, keep meaning unchanged, keep paragraph order unchanged.
```

## 8) 如何快速判断走了哪条路径

打开同名 `*.meta.json`：

- `resolver=official-link`：已走官方 transcript 外链  
- `resolver=official-file-direct`：直接解析本地 transcript 文件  
- `resolver=youtube-id` / `title->ytsearch1`：走字幕回退  
- `resolver=episode-page-text`：走页面可见文字 / shownotes，不是时间轴 transcript  
- `resolver=episode-page-asr` / `resolver=audio-url-asr`：已进入 ASR  
- `attempts[]`：每一步的成功/失败原因

如果是小宇宙这类页面，还可以看：

- `page_text.kind`：是 `shownotes` 还是 `description`
- `page_text.transcript_media_id`：页面里是否出现 transcript 线索

## 9) 标题输入没有命中正确节目

标题搜索路径是：

1. `ytsearch1`（YouTube）
2. Apple `podcastEpisode`（标题匹配）

建议输入格式：

- `节目名 + 期数 + 嘉宾名`
- 避免只给单词或过短关键词

并用 `meta.json.attempts[]` 检查命中来源。

## 10) CLI 一启动就报 Python 版本错误

当前版本会显式要求 Python 3.9+。如果你看到类似：

```text
Python 3.9+ is required
```

说明脚本没有坏，是解释器太旧。先换到 3.9+ 再跑。

## 11) `--doctor` 失败是什么意思

常见输出：

- `DOCTOR FAIL yt-dlp`：先执行 `python3 -m pip install -r requirements.txt`
- `DOCTOR FAIL faster-whisper`：同样先安装 `requirements.txt`
- `DOCTOR FAIL model-root`：说明模型缓存目录不可写，换个有权限的用户目录再跑

只有当 `--doctor` 退出码是 `0`，我才建议把仓库直接交给别人的 agent 做正式转写。

## 12) Git 推送常见问题

`Repository not found`：

```bash
git remote -v
```

确认远端仓库已创建且名称一致后再推送。

`Host key verification failed`：

```bash
ssh-keyscan -t ed25519 github.com >> ~/.ssh/known_hosts
ssh -T git@github.com
```
