# Contributing

## Commit 约定

- 单次提交聚焦一个改动点。
- 提交信息建议格式：`type(scope): summary`
  - 示例：`fix(cleaning): reduce rolling-caption duplication`

## 代码改动原则

- 先保稳定，再扩功能。
- 行为变化必须更新文档（`README.md` 或 `references/sources.md`）。
- 避免引入隐式网络依赖与隐式凭证读取。

## 提交前自检

```bash
python3 scripts/podcast_transcript_txt.py --help
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile scripts/podcast_transcript_txt.py
```

