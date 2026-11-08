/* Libry 薄壳 — 壳内没有任何业务逻辑：默认窗口加载 ui/（首启/换服务器页），
   用户填入自家 Libry 服务器地址后由前端 location.replace 跳转，此后 WebView
   即与浏览器访问等价（登录、Service Worker 离线缓存全部由服务端 Web 层承担）。
   不定义任何 Tauri command，远程页面默认无 IPC 权限，天然隔离。 */

/// mobile_entry_point 在 Android/iOS 目标下导出移动端所需的 JNI 入口符号（桌面端为空操作）
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
