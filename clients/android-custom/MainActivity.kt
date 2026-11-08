package com.libry.shell

import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.os.Bundle
import android.view.ViewGroup
import android.view.WindowInsets
import androidx.activity.enableEdgeToEdge

/* 安全区适配（构建脚本会把本文件覆盖到 gen/android 的 MainActivity.kt）：
   模板默认 enableEdgeToEdge() 让整个窗口画到系统栏下面，WebView 内容（含 Web 端
   sticky 顶栏）会被状态栏/刘海/导航条遮挡。这里在 content 视图上按
   系统栏 + 刘海 + 键盘的 insets 打 padding，把 WebView 限制在安全区内——
   远端 Web 应用零改动即获得正确显示，行为与浏览器一致。 */
class MainActivity : TauriActivity() {
  override fun onCreate(savedInstanceState: Bundle?) {
    enableEdgeToEdge()
    super.onCreate(savedInstanceState)
    // 被让出的状态栏/导航条区域露出窗口背景；用站点底色（--bg #f6f7f9）避免黑条
    window.setBackgroundDrawable(ColorDrawable(Color.rgb(0xF6, 0xF7, 0xF9)))
    val root = findViewById<ViewGroup>(android.R.id.content)
    root.setOnApplyWindowInsetsListener { v, insets ->
      val safe = insets.getInsets(
        WindowInsets.Type.systemBars()
          or WindowInsets.Type.displayCutout()
          or WindowInsets.Type.ime())
      v.setPadding(safe.left, safe.top, safe.right, safe.bottom)
      insets
    }
  }
}
