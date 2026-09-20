# 裸机部署指南

覆盖三种场景：本地体验（5 分钟）、macOS 常驻、Ubuntu VPS 公网服务。Docker 支持在 v0.2 路线图上。

## 0. 前置要求

- Python **3.11+**（`python3 --version` 确认）
- git
- 公网场景：一台 VPS + 一个域名（DNS A 记录指向 VPS）

## 1. 本地体验（5 分钟）

```bash
git clone https://github.com/CobyLee66/Libry.git ~/Libry
cd ~/Libry
python3.11 -m venv .venv && .venv/bin/pip install .

.venv/bin/libry init ~/my-kb          # 交互式设置 admin 密码
cd ~/my-kb && ~/Libry/.venv/bin/libry serve
# 浏览器打开 http://127.0.0.1:8000
```

局域网访问（手机/平板阅读）：`libry serve --host 0.0.0.0`，然后访问 `http://<本机IP>:8000`。注意 HTTP 明文传输密码，仅限家庭局域网。

## 2. macOS 常驻（launchd）

```bash
# 在引擎仓库执行；--vault 指向你的知识库
bash deploy/install.sh --vault ~/my-kb
```

安装器自动：建 venv、装依赖、写 `~/Library/LaunchAgents/com.libry.web.plist`、加载并启动（RunAtLoad + KeepAlive）。日志在 `<vault>/.libry/libry-web.log`。

管理：

```bash
launchctl kickstart -k gui/$(id -u)/com.libry.web    # 重启
launchctl unload ~/Library/LaunchAgents/com.libry.web.plist && \
launchctl load   ~/Library/LaunchAgents/com.libry.web.plist
```

## 3. Ubuntu VPS（systemd + Caddy，公网 HTTPS）

```bash
# 3.1 引擎与 vault
sudo mkdir -p /opt/libry && sudo chown "$USER" /opt/libry
git clone https://github.com/CobyLee66/Libry.git /opt/libry/engine
cd /opt/libry/engine && python3.11 -m venv .venv && .venv/bin/pip install .
.venv/bin/libry init /opt/libry/vault        # 设置 admin 密码

# 3.2 安装服务（systemd 单元自动生成并启动）
bash deploy/install.sh --vault /opt/libry/vault

# 3.3 公网入口（Caddy 自动 HTTPS）
sudo apt-get install -y caddy
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
sudo sed -i 's/kb.example.com/你的域名/' /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

HTTPS 后建议在 `<vault>/.env` 加 `KB_COOKIE_SECURE='true'` 并重启服务。

防火墙：服务只监听 127.0.0.1:8000，公网只开 80/443（Caddy）。

### 3.4 定时任务（可选）

```bash
crontab -e
# 每周日 05:00 定时 lint（需 vault .env 配置 KB_AGENT_CMD，见 docs/agent-integration.md）
0 5 * * 0 cd /opt/libry/vault && bash /opt/libry/engine/scripts/run-lint.sh >> /opt/libry/vault/.libry/kb-lint.log 2>&1
```

更多模板（ingest / 数据同步 / systemd timer）：`deploy/cron/README.md`。

## 4. 引擎升级

```bash
cd <引擎仓库> && bash deploy/update.sh    # pull + 按需重装依赖 + 重启服务
cd <vault> && libry skills update         # 同步最新 agent skills（AGENTS.md 契约变更时手动 review）
```

## 5. 常见问题

- **忘了 admin 密码**：`cd <vault> && libry passwd admin`
- **关联图入口不显示**：Web 端检测不到 graph.json 时自动隐藏——在装了 graph 组件的机器上跑 `libry graph`
- **服务起不来**：看 `<vault>/.libry/libry-web.log`；常见原因是 `.env` 缺 `SESSION_SECRET`（`libry init` 已自动生成）
- **改了 wiki 页面但列表没变**：索引是缓存——跑 `libry index`，或 Web 管理端触发 reindex；多机场景由 publish/sync 链路自动处理
