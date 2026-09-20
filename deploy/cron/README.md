# 定时任务模板（crontab / systemd timer / launchd）

把 `<ENGINE>` 替换为引擎仓库路径、`<VAULT>` 替换为知识库路径。

## crontab（两端通用，`crontab -e`）

```cron
# 副本端：每 10 分钟兜底拉取（webhook 之外的第二条同步链路）
*/10 * * * * KB_ROOT=<VAULT> bash <ENGINE>/deploy/sync.sh >> <VAULT>/.libry/kb-sync.log 2>&1

# 两端：每天 06:00 用户数据双向同步（多机模式；先在 vault .gitignore 放开五个数据文件）
0 6 * * * KB_ROOT=<VAULT> bash <ENGINE>/deploy/sync-data.sh >> <VAULT>/.libry/kb-sync-data.log 2>&1

# 权威端：每周三 04:00 定时入库（需 vault .env 配置 KB_AGENT_CMD 与可选 LIBRY_NOTIFY_WEBHOOK）
0 4 * * 3 cd <VAULT> && bash <ENGINE>/scripts/run-ingest.sh >> <VAULT>/.libry/kb-ingest.log 2>&1

# 权威端：每周日 05:00 定时 lint
0 5 * * 0 cd <VAULT> && bash <ENGINE>/scripts/run-lint.sh >> <VAULT>/.libry/kb-lint.log 2>&1
```

## systemd timer（Linux，可选替代 cron）

```ini
# /etc/systemd/system/libry-ingest.timer
[Unit]
Description=Libry weekly ingest

[Timer]
OnCalendar=Wed *-*-* 04:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/libry-ingest.service
[Unit]
Description=Libry weekly ingest

[Service]
Type=oneshot
User=<你>
WorkingDirectory=<VAULT>
Environment=KB_ROOT=<VAULT>
ExecStart=bash <ENGINE>/scripts/run-ingest.sh
```

启用：`sudo systemctl enable --now libry-ingest.timer`

## launchd（macOS，可选替代 cron）

参见 `deploy/launchd/` 目录样式；`StartCalendarInterval` 配置参考：

```xml
<key>StartCalendarInterval</key>
<dict>
  <key>Weekday</key><integer>3</integer>
  <key>Hour</key><integer>4</integer>
  <key>Minute</key><integer>0</integer>
</dict>
```
