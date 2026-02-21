# Troubleshooting

## 1) `Repository not found`（git push 时）

原因：
- 远端仓库不存在，或仓库名不一致。

处理：
- 先在 GitHub 创建同名仓库，再执行：

```bash
git remote -v
git push -u origin main
```

## 2) `Host key verification failed`

原因：
- 本机未信任 GitHub 主机指纹。

处理：

```bash
ssh-keyscan -t ed25519 github.com >> ~/.ssh/known_hosts
ssh -T git@github.com
```

## 3) YouTube 报 `PO token` / `429` / 无字幕

处理建议：
- 优先使用脚本内置的 `youtube:player_client=android` 路径。
- 更换输入链接，优先官方频道视频源。
- 重试时避免短时间内高频请求。

## 4) 标题检索失败（`ytsearch` 无结果）

处理建议：
- 缩短关键词，只保留“节目名 + 嘉宾名”。
- 直接改用 YouTube 直链。

## 5) 输出文本重复严重

说明：
- 本项目已对 rolling captions 做 overlap 合并。
- 若仍遇到重复，可在 issue 附上原始视频链接与样例片段。

## 6) X/Twitter 链接不稳定

说明：
- X 帖子可能只给 Spotify 等外链，不保证可直达字幕源。
- 这是可选路径，建议回退为 YouTube 链接或标题输入。

