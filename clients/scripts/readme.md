# clients/scripts/ 脚本说明

多端客户端（Tauri 2 薄壳）的构建与安装脚本。风格与约定参照 Coby-AI-Learning 项目的 scripts/：操作系统自适应（Windows Git Bash / macOS / Linux）、用户已设的环境变量优先于脚本默认值、构建前 pre-flight 检查、产物统一归位到 `clients/dist/`。

**图标单一来源**：所有端的图标一律来自 `libry/static/icon.png` 一处——改动图标后只需重跑 `build-icons.sh`，各端重新打包即生效。

---

## 一、图标

### `build-icons.sh` — 全端图标再生成（单一来源分发）

**职责**：以 `libry/static/icon.png`（1024 正方形）为唯一源，生成：壳首启页 `shell/ui/icon.png`（原图直拷）、PWA manifest 图标 `libry/static/icons/icon-192|512.png`（重采样）、Tauri 全平台图标集 `shell/src-tauri/icons/`（`cargo tauri icon`，含 icns/ico/Android mipmap/iOS AppIcon）。**额外修正**：Android 自适应图标的前景层默认被 `cargo tauri icon` 铺满 108dp 画布，启动器只显示中央 72dp 会把原瓷砖裁掉约 1/3——本脚本把原图缩放到画布 66.7% 居中重排前景层（需要 Pillow），启动器完整呈现原始瓷砖。

**运行位置**：任一装有 tauri-cli 的机器（Windows Git Bash / macOS / Linux）。

**调用方式**：`./scripts/build-icons.sh`

**依赖**：tauri-cli（`cargo install tauri-cli --version 2.12.4 --locked`）；重采样工具三选一：sips（macOS 自带）/ ImageMagick / Pillow。

---

## 二、桌面端构建

### `build-macos.sh` — macOS 构建（本地运行）

**职责**：`cargo tauri build` 出 .app + .dmg，产物复制到 `clients/dist/`。

**调用方式**：`./scripts/build-macos.sh [--target x86_64-apple-darwin] [--debug]`

**依赖**：Rust、tauri-cli、Xcode Command Line Tools。未签名，首次打开右键 → 打开绕过 Gatekeeper。

### `build-windows.sh` — Windows 构建（Windows 本机运行）

**职责**：`cargo tauri build` 出 NSIS .exe + MSI，产物复制到 `clients/dist/`。

**运行位置**：Windows 的 Git Bash。

**调用方式**：`./scripts/build-windows.sh [--debug]`

**依赖**：Rust（MSVC）、tauri-cli、WebView2（Win10/11 自带）。未签名，SmartScreen 会提示放行。

---

## 三、Android

### `build-android.sh` — APK 构建 + 签名 + 可选自动安装

**职责**：pre-flight（JDK17+/SDK/NDK/Rust 交叉目标/图标/密钥）→ 缺 `gen/` 时 `cargo tauri android init` → **覆盖安装安全区补丁**（`android-custom/MainActivity.kt`，见下）→ `cargo tauri android build --apk` → zipalign + apksigner 签名 → 产物 `clients/dist/Libry_<version>_universal.apk` → 默认自动安装到第一个已连接设备（签名不匹配时自动卸载重装）。

**调用方式**：`./scripts/build-android.sh [--no-install] [--device <serial>]`

**运行位置**：装有 Android SDK + NDK 的机器（Windows Git Bash / macOS / Linux）。

**环境变量**（均可覆盖）：`JAVA_HOME`（Windows 默认 `C:\Softwares\Android\jdk-21.0.5+11`）、`ANDROID_HOME`（Windows 默认 `C:\Softwares\Android`，macOS 默认 `~/Library/Android/sdk`）、`NDK_HOME`（默认取 SDK 下最新 NDK）、`LIBRY_KEYSTORE` / `LIBRY_KEY_ALIAS` / `LIBRY_KEYSTORE_PASS`（签名密钥，缺失时自动生成新密钥并提示备份——**升级覆盖安装必须同一密钥**）。

**内部要点**：`gen/` 与 `keystore/` 都是本机生成物（gitignored）。`gen/` 重新 init 后 MainActivity 会回到模板默认（只 enableEdgeToEdge 不打 insets），本脚本每次构建前自动重新覆盖补丁。

### `install-apk.sh` — APK 安装（独立安装入口）

**职责**：把 `clients/dist/` 最新已签名 APK 装到 adb 设备；`--launch` 装完直接启动；签名不匹配自动卸载重装（会清除应用本地数据，如已连接的服务器地址）。

**调用方式**：`./scripts/install-apk.sh [--device <serial>] [--apk <path>] [--launch]`

**依赖**：adb（`ANDROID_HOME/platform-tools`）。

---

## 四、安全区（显示区域）适配

Android 模板的 `MainActivity` 显式调用 `enableEdgeToEdge()`（内容画进系统栏下面）。本项目的适配在 `android-custom/MainActivity.kt`：保留 edge-to-edge，但在 content 视图按「系统栏 + 刘海 + 键盘」的 WindowInsets 给 WebView 打 padding，被让出的区域用站点底色（#f6f7f9）填充——远端 Web 应用零改动即与浏览器行为一致。壳首启页另带 `env(safe-area-inset-*)` 兜底（`viewport-fit=cover` 已开）。
