# 多机同步指南（权威端 + 消费端）

典型拓扑：**Mac 是权威端**（agent 在这里入库、算关联图），**VPS 是消费端**（只读 + 家人手机访问）。传输层是 vault 自己的 **私有 git 远端**（GitHub/Gitea 均可），两条通道：webhook 即时 + cron 兜底。

> 前提：vault 必须用**私有** git 远端（用户数据、个人文档可见性都随它同步）。

## 1. 权威端（Mac）配置

vault 根 `.env`：

```bash
KB_WEB_URL='https://kb.example.com'      # 消费端公网地址
SYNC_SECRET='<openssl rand -hex 32>'     # 两端一致
KB_SSH_HOST='my-server'                  # 可选：graph.json 直传用（免密可登录）
KB_REMOTE_DATA_DIR='/opt/libry/vault/.libry'   # 消费端数据目录绝对路径
```

放开 `.gitignore` 中五个用户数据文件的白名单（多机模式的开关）：

```gitignore
.libry/users.json
.libry/state.json
.libry/bookmarks.json
.libry/visibility.json
.libry/deletions.json
```

角色声明（写进权威端服务环境或 `.env`）：`KB_ROLE='primary'`——设置页「立即执行删除」会走 publish.sh 发布链路而非自行 push。

## 2. 消费端（VPS）配置

```bash
# 引擎 + vault（vault 从同一 git 远端 clone）
git clone <你的私有远端> /opt/libry/vault
bash deploy/install.sh --vault /opt/libry/vault
```

vault 根 `.env`（消费端）：

```bash
SYNC_SECRET='<与权威端一致>'
# KB_ROLE 缺省即副本端：purge 用部署写密钥自行 commit+push
KB_DEPLOY_KEY='/home/<user>/.ssh/id_ed25519_libry'   # 对 git 远端有写权限的部署密钥
```

写权限部署密钥（仅用于用户数据同步与副本端 purge 推送）：

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_libry -N ''
# 公钥添加到 GitHub 仓库 → Settings → Deploy keys（勾选写权限）
```

cron 兜底（每 10 分钟拉取 + 每天 06:00 数据同步）：

```cron
*/10 * * * * KB_ROOT=/opt/libry/vault bash /opt/libry/engine/deploy/sync.sh >> /opt/libry/vault/.libry/kb-sync.log 2>&1
0 6 * * * KB_ROOT=/opt/libry/vault bash /opt/libry/engine/deploy/sync-data.sh >> /opt/libry/vault/.libry/kb-sync-data.log 2>&1
```

权威端也加一行每天 06:05 的 `sync-data.sh`（错峰）。

## 3. 数据流总结

| 数据 | 方向 | 通道 |
|---|---|---|
| 知识内容（wiki/、index.md、tags.md、content_dirs） | 权威端 → 消费端 | `deploy/publish.sh`（agent 入库后调用）：commit+push → webhook `/api/sync`；消费端 cron 兜底 |
| 用户数据（已读/收藏/账户/可见性/删除标记） | 双向 | `libry sync-data`：fetch → CRDT 合并（LWW+墓碑）→ push，每日 cron + Web 端手动 |
| 关联图 graph.json | 权威端 → 消费端 | 不走 git：publish.sh 构建后 SSH 直传 |

## 4. 删除的两端行为

- **权威端执行**（KB_ROLE=primary）：purge 暂存删除 → publish.sh 提交推送 → webhook。
- **消费端执行**：purge 用写密钥自行 `--commit --push`；权威端下次 publish/sync-data 时由内置 reconcile 钩子清掉本地残留（防复活）。

## 5. 故障排查

- **webhook 一直失败**：检查 `KB_WEB_URL`/`SYNC_SECRET` 两端一致；消费端 cron 每 10 分钟兜底，不丢数据只延迟。
- **「本地有未推送的非数据提交，已跳过」**：vault 有手工 commit 未推送——先 `git push` 再跑 sync-data（保护机制，避免 reset --soft 吞掉你的提交）。
- **已删页面复活**：跑 `libry purge --reconcile-only`；这是 reset --soft 对齐后的残留清理钩子，正常链路会自动执行。
