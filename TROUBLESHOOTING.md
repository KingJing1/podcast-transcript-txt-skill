# Troubleshooting

## 1) 运行后没有产出文件

先看标准输出是否有 `FAIL <input> <error>`，再检查：

```bash
ls -lh /你的输出目录
```

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

## 5) 如何快速判断走了哪条路径

打开同名 `*.meta.json`：

- `resolver=official-link`：已走官方 transcript 外链  
- `resolver=youtube-id` / `title->ytsearch1`：走字幕回退  
- `attempts[]`：每一步的成功/失败原因  

## 6) Git 推送常见问题

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
