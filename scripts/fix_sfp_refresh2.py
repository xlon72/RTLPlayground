#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""index.html: 手动刷新时同步更新信息表(含 SFP 插槽)。

背景
----
main_info.js 已抽出 window.refreshInfoTable(), 但只在 DOMContentLoaded
时执行一次。首页刷新按钮只调 update()(/status.json), 管不到
/information.json, 所以 SFP 插槽信息不随刷新更新。

修法
----
在手动点击的回调(第 83-87 行)和 finalRefresh(第 93-99 行)里各加一次
refreshInfoTable() 调用。自动轮询不调用, 避免请求量翻倍。

锚点说明: v5 改过这段, 之前用的旧锚点已失效, 这里按当前实际内容写。

幂等。在仓库根目录或 html/ 目录运行。
"""
import io, os, sys

if os.path.basename(os.getcwd()) != "html" and os.path.isdir("html"):
    os.chdir("html")
elif not os.path.exists("index.html"):
    sys.exit("✗ 请在仓库根目录或 html/ 目录运行")

p = "index.html"
s = io.open(p, encoding="utf-8", newline="").read()

if "refreshInfoTable" in s:
    print("  = 跳过: 已接入")
else:
    # 锚点 1: 手动点击回调里的 update(...) —— 它是唯一带 wasOn 判断的那处
    OLD1 = '''        if (wasOn) {
          update(function () {
            if (typeof updateTiles === "function") {
              updateTiles();
            }
          });
        }'''
    NEW1 = '''        if (wasOn) {
          update(function () {
            if (typeof updateTiles === "function") {
              updateTiles();
            }
            if (typeof window.refreshInfoTable === "function") {
              window.refreshInfoTable();
            }
          });
        }'''
    if OLD1 not in s:
        sys.exit("✗ 未定位手动点击回调 <<<")
    s = s.replace(OLD1, NEW1, 1)
    print("  + 接入: 手动点击回调刷新信息表")

    # 锚点 2: finalRefresh() —— 页面加载完成后的补刷
    OLD2 = '''    function finalRefresh() {
      update(function () {
        if (typeof updateTiles === "function") {
          updateTiles();
        }
      });
    }'''
    NEW2 = '''    function finalRefresh() {
      update(function () {
        if (typeof updateTiles === "function") {
          updateTiles();
        }
        if (typeof window.refreshInfoTable === "function") {
          window.refreshInfoTable();
        }
      });
    }'''
    if OLD2 in s:
        s = s.replace(OLD2, NEW2, 1)
        print("  + 接入: finalRefresh 刷新信息表")
    else:
        print("  ! 未定位 finalRefresh <<< (不影响手动刷新)")

    io.open(p, "w", encoding="utf-8", newline="").write(s)

# ------------------------------------------------------------ 自检
print("\n自检:")
s = io.open(p, encoding="utf-8", newline="").read()
mj = io.open("main_info.js", encoding="utf-8", newline="").read()

opens = s.count("<script")
closes = s.count("</script>")

checks = [
    ("main_info 有 refreshInfoTable", "window.refreshInfoTable" in mj),
    ("index.html 调用了它",           "refreshInfoTable" in s),
    ("调用处 2 处(手动+final)",       s.count("refreshInfoTable") == 2),
    ("script 标签平衡",               opens == closes),
]
ok = True
for name, res in checks:
    print("  %-30s %s" % (name, "OK" if res else "失败 <<<"))
    ok = ok and res
print("")
print("✓ 全部通过" if ok else "✗ 存在问题")
