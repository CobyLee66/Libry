# Agent 接入指南

Libry 的核心设计：**引擎不内置 agent**——vault 自带契约与技能，任何 coding agent 都能当图书管理员。

## 契约层（agent 读什么）

`libry init` 生成的 vault 里有：

| 文件 | 作用 |
|---|---|
| `AGENTS.md` | 维护手册：入库/查询/lint 全部规则（最高权威） |
| `.agents/skills/kb-ingest/` | 入库流程 skill |
| `.agents/skills/kb-lint/` | 健康检查与修复 skill |
| `.agents/skills/kb-publish/` | 发布同步 skill（多机部署用） |
| `.agents/skills/kb-query/` | 基于 wiki 的问答 skill |
| `.agents/skills/kb-research-ingest/` | 研究→确认→归档管线（示例，按需改造） |

## 交互式使用（人在场）

在 vault 目录下启动你的 agent，直接下指令：

```bash
cd ~/my-kb
claude "把 https://example.com/article 这篇文章入库"
# 或 hermes / codex / 其它支持 AGENTS.md 约定的 CLI
```

agent 会读 `AGENTS.md` 与 skills，执行入库并跑 `libry lint` 验证。

- **Claude Code / ZCode**：原生读取 `AGENTS.md` 与 `.agents/skills/`，开箱即用。
- **hermes 等自管 skills 的 agent**：把 `.agents/skills/kb-*` 复制进你的 profile skills 目录即可（内容无需改动，路径已相对化）。
- **任何 agent**：即便不识别 skill 格式，只要它按 `AGENTS.md` 行事即可——契约是纯 markdown。

## 无人值守（定时任务）

`scripts/run-ingest.sh` 与 `run-lint.sh` 通过 `KB_AGENT_CMD` 无头调用 agent。在 vault 根 `.env` 配置：

```bash
# {prompt} 是占位符，脚本会把任务指令填进去。按你的 agent CLI 写：
KB_AGENT_CMD='claude -p "{prompt}"'
# KB_AGENT_CMD='hermes run --prompt "{prompt}"'
# KB_AGENT_CMD='zcode ...'

# 可选：结果推送（通用 webhook，POST {"text": ...}）
LIBRY_NOTIFY_WEBHOOK='https://your-webhook.example.com/message'
```

调度模板（crontab / systemd timer / launchd）见 `deploy/cron/README.md`，推荐节奏：每周三 04:00 入库、每周日 05:00 lint。

### 通知适配示例

`notify.sh` 只做一件事：向 `LIBRY_NOTIFY_WEBHOOK` POST `{"text": ...}`。接到任何能收 JSON 的入口（企业微信/飞书/Telegram bot/自建转发）。QQ 机器人场景：建议自建一个小转发服务持有 bot 密钥（密钥走环境变量，绝不进仓库），webhook 指向它。

## 定制

- **改入库规则**：编辑 vault 的 `AGENTS.md`（它属于你）；引擎升级带来的契约更新用 `libry skills update` 拉取后自行 diff 合并。
- **改 skills**：直接编辑 `.agents/skills/` 下的 `SKILL.md`。
- **抓取类外部工具**（kb-research-ingest 里提到的站点抓取、PDF 处理）：按你的环境安装/替换，skill 中已标注为可选依赖。
