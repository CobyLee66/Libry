---
name: kb-publish
description: >
  知识库入库/修改完成后发布同步：commit + push 内容变更，通知远端 Web 立即拉取
  重建索引。当 kb-ingest / kb-lint 完成写入之后调用。
allowed-tools: Bash, Read
---

# kb-publish — 知识库发布同步

## 触发场景

完成一次入库（ingest）或修复（lint）之后：新文档已进入 `wiki/`、`index.md` / `tags.md` / `wiki/log.md` 已更新。调用本 skill 把变更发布到 git 远端并通知 Web 应用同步。**单机部署（无远端 Web）不需要本 skill。**

## 执行步骤

1. 确认写入流程已全部完成（wiki 页面、index.md、wiki/log.md 均已落盘）。
2. 执行发布脚本：

   ```bash
   bash "$(libry config | awk '/engine_root/{print $2}')/deploy/publish.sh"
   ```

   脚本自动完成：
   - 内容有变更时本地重建索引（+ 关联图，若装了 graph 可选依赖）
   - `git add` 内容路径（wiki/、index.md、tags.md/、logs/、content_dirs）并 commit（无变更则跳过）
   - `git push`
   - 调用 `$KB_WEB_URL/api/sync`（带 `X-Sync-Secret`），远端立即 pull + 重建索引
   - graph.json 不入 git：构建成功后经 SSH 直传远端（`KB_SSH_HOST`/`KB_REMOTE_DATA_DIR` 可配）

3. 检查输出：
   - `已推送到 GitHub` + `已通知对端同步` → 完成。
   - `webhook 调用失败` → 不阻断，远端 cron 兜底拉取，提醒用户即可。
   - `git push 失败（可能有冲突）` → **停止重试**，提示用户人工 `git pull --rebase` 处理后重跑。

## 前置配置

vault 根 `.env`（gitignored）需包含（多机部署时）：

```
KB_WEB_URL=https://<远端域名>
SYNC_SECRET=<与远端 .env 相同>
# 可选：KB_SSH_HOST=server-alias（graph.json 直传用，须可免密登录）
```

未配置时脚本只 commit + push，跳过 webhook，属可接受降级。

## 注意

- 不要手动 `git commit/push` 绕过脚本，保持同步链路一致。
- 引擎代码改动不归本 skill 管（引擎仓库自行更新，见 `deploy/update.sh`）。
