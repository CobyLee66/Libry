# Security Policy

## 支持版本

| 版本 | 支持状态 |
|---|---|
| 0.1.x | ✅ |

## 报告漏洞

**请不要通过公开 issue 报告安全漏洞。**

请通过 GitHub Security Advisories（仓库 Security 标签页 → Report a vulnerability）私密报告。收到后 72 小时内响应。

## 安全基线（部署自查）

- vault 根 `.env` 含 `SESSION_SECRET` / `SYNC_SECRET`——**绝不提交进 git**（`libry init` 生成的 `.gitignore` 已排除）。
- `users.json` 等 `.libry/` 运行数据默认 gitignored；**只有**启用多机同步时才放开五个用户数据文件（bcrypt 哈希随仓库走，前提是 vault 用私有 git 远端）。
- 公网暴露务必置于 TLS 反代之后（`deploy/Caddyfile`），并在 HTTPS 下设 `KB_COOKIE_SECURE='true'`。
- 渲染输出经 nh3 白名单消毒；不要移除 `server/render.py` 的 `_sanitize`。
- `/api/sync` 等 webhook 端点靠 `X-Sync-Secret`；密钥用 `openssl rand -hex 32` 生成并两端一致。
