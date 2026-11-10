# Libry 多端客户端（clients/）

薄壳策略：**壳里没有任何业务逻辑**（壳内离线阅读器、镜像桥与 Web 应用快照是 Web 层
产物/快照的通用承载，由引擎仓库维护、构建时刷新 `ui/lib/offline.js` 与 `ui/webapp/`）。
壳 = 一个 WebView，首次启动让用户填自家 Libry 服务器地址，之后加载的就是线上 Web
应用本体（登录、阅读、离线缓存全部由服务端 Web 层承担）。在线时永远是最新网页——
**网页更新不需要发版客户端**；在线离线能力由 Web 层的 Service Worker + IndexedDB
提供，客户端壳另有一条不依赖 SW 的可靠离线面：断网经离线门户进入**本地模式的完整
Web 应用快照**（fetch 垫片从壳内镜像库应答，页面与在线同款，见 `docs/offline.md`
「壳内离线阅读器与镜像」）。

```
clients/
└── shell/
    ├── ui/index.html          # 首启/换服务器页 + 离线门户（探测可达即连；不可达不裸跳，进离线阅读）
    ├── ui/webapp/             # 构建时拷入的完整 Web 应用快照 + local-mode.js 垫片（断网时的同款 UI）
    ├── ui/reader.html         # 轻量兜底阅读器（webapp 快照缺失时的后备）
    ├── ui/bridge.html         # 镜像桥（远端 Web 应用经 iframe+postMessage 同步离线库到壳 origin）
    └── src-tauri/             # Tauri 2 工程（Rust 侧仅样板代码，无自定义 command）
        ├── src/               #   lib.rs + main.rs（~10 行）
        ├── tauri.conf.json    #   窗口/打包配置；frontendDist 指向 ../ui
        └── icons/             #   各平台图标（由 libry/static/icon.png 生成）
```

设计要点：

- **无 IPC**：壳不定义任何 Tauri command，远程页面默认无 IPC 权限，与浏览器访问同权。
- **连接策略**：连接过的地址存于壳的 localStorage（`libry-server`）。启动显示锁定的
  「连接中」界面并后台探测（icon.png，4s 超时）：可达就**立即自动连接**（在线=远端
  network-first 最新网页）；不可达进**离线门户**——绝不裸跳（跳转会落到 WebView 系统错误页），
  门户展示壳内离线库文档数并提供「进入离线阅读」（本地模式完整 Web 应用，读壳 origin
  镜像库）、「重试连接」「更换服务器」。仅当用户在 Web 设置页「断开连接」后
  （`libry-server-noauto` 置位）启动停留在「上次连接」卡片，由用户手动决定。
- **壳 ↔ Web 跳转标记**（跨 origin，只能靠 URL 传）：壳连接时给目标 URL 追加
  `?_libryHome=<壳首页>`，Web 层存下后供设置页「断开连接并更换服务器」（仅壳内可见）跳回壳页；
  跳回时带 `?_libryDisconnected=1`，壳保留地址记忆（`libry-server-noauto` 置位）但之后启动
  不再自动连接，直到用户再次主动连接。
- **Android 返回键**：默认行为需在真机验证（期望 WebView 内先回退历史、栈底才退出）；
  若与期望不符，在 `src-tauri/gen/android` 的 Activity 中最小化定制。
- **IME 纪律**（源自 Coby 项目踩坑，详见 `docs/frontend-style.md`）：壳内文本输入
  必须 Enter 守卫（`isComposing || keyCode === 229`）；若未来替换为 Capacitor 壳，
  第一天就必须 `android.captureInput: false`（红线）。

## 构建前提

| 平台 | 前提 |
|---|---|
| 通用 | Rust（stable）+ `cargo install tauri-cli --version "^2" --locked` |
| macOS | Xcode Command Line Tools |
| Windows | MSVC Build Tools + WebView2（Win10/11 自带） |
| Android | Android SDK + NDK（`NDK_HOME` 指向 NDK 目录）+ JDK 17 |

## 本地构建（推荐走 scripts/）

各平台的构建/安装统一走 `clients/scripts/`（用法与环境变量详见
[scripts/readme.md](scripts/readme.md)，风格参照 Coby-AI-Learning 项目）：

```bash
./clients/scripts/build-icons.sh                    # 全端图标再生成（唯一来源 libry/static/icon.png）
./clients/scripts/build-macos.sh                    # macOS：.app + .dmg → clients/dist/
./clients/scripts/build-windows.sh                  # Windows（Git Bash）：NSIS + MSI → clients/dist/
./clients/scripts/build-android.sh                  # Android：构建+签名+自动装到手机
./clients/scripts/install-apk.sh --launch           # 单独安装已签名 APK
```

`build-android.sh` 会自动完成：pre-flight（JDK/SDK/NDK/Rust 交叉目标）→ 缺失时
`cargo tauri android init` → **覆盖安全区补丁**（`android-custom/MainActivity.kt`）→
**同步启动图标进工程**（gen/ 只在 init 时拷图标，脚本每次构建前重新覆盖）→ 构建 →
zipalign + apksigner 签名（密钥在 `shell/keystore/`，gitignored，缺失自动生成并提示备份）→
归位 `clients/dist/`。

直接调 tauri-cli 的手动方式（了解原理用）：

```bash
cd clients/shell/src-tauri
cargo tauri build                  # 桌面（当前平台）；--target x86_64-apple-darwin 交叉 Intel
cargo tauri android init           # 生成 src-tauri/gen/android（gitignored）
cargo tauri android build --apk    # 产物在 gen/android/app/build/outputs/apk/
```

开发调试用 `cargo tauri dev`（窗口内先跳首启页）。CI 构建见
`.github/workflows/clients.yml`（macOS arm/intel + Windows + Android APK，含
MainActivity 安全区补丁，产物在 workflow artifacts，未签名——macOS 首次打开需
右键绕过 Gatekeeper）。

## 图标与安全区

- **图标单一来源**：所有端（PWA / macOS / Windows / Android 启动器）的图标一律来自
  `libry/static/icon.png`，由 `scripts/build-icons.sh` 分发——改图标只改这一处。
- **安全区**：Android 模板 `MainActivity` 显式 `enableEdgeToEdge()`（内容画进系统栏），
  `android-custom/MainActivity.kt` 按「系统栏 + 刘海 + 键盘」insets 给 WebView 打 padding，
  被让出的区域填站点底色——远端 Web 应用零改动即与浏览器一致；壳首启页另带
  `env(safe-area-inset-*)` 兜底。

## 版本与发版

- 壳版本号独立于引擎（`src-tauri/tauri.conf.json` 的 `version`），仅在壳行为变化时 bump。
- 离线能力全部在 Web 层演进，正常情况下**网页更新无需重新发壳**。
