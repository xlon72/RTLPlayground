#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""system.html: 消除 tab-bar 左侧的过大空隙(双重缩进)。

根因
----
上一轮把 .tab-bar 的 <div> 从 <nav> 之前移进了内容容器, 但 head 里
<style> 的规则没同步改, 仍保留:
    margin-left: 16%;                 <- 容器已有 margin-left:16%
    padding: 1px 16px; padding-bottom: 0;   <- 容器已有 padding:1px 16px
移进容器后, 16% 按容器宽度(视口的 84%)计算, 于是 tab-bar 在容器已缩进
16% 的基础上又右移 16% x 84% = 13.4% 视口宽, 外加 16px 重复内边距,
左侧出现一大块空白。

修法
----
删掉 .tab-bar 自身的 margin-left 与 padding, 继承容器即可, 与正文左对齐。
保留 margin-bottom: 0(原设计: 标签紧贴下方内容)。
只改这一行 CSS, 不动结构。

幂等。在仓库根目录或 html/ 目录运行。
"""
import io, os, sys

if os.path.basename(os.getcwd()) != "html" and os.path.isdir("html"):
    os.chdir("html")
elif not os.path.exists("system.html"):
    sys.exit("✗ 请在仓库根目录或 html/ 目录运行")

p = "system.html"
s = io.open(p, encoding="utf-8", newline="").read()

OLD = "margin-bottom: 0; margin-left: 16%; padding: 1px 16px; padding-bottom: 0;"
NEW = "margin-bottom: 0; padding: 0;"

if NEW in s:
    print("  = 跳过: 已改")
elif OLD not in s:
    sys.exit("✗ 未定位 .tab-bar 的 margin/padding <<<")
else:
    s = s.replace(OLD, NEW, 1)
    io.open(p, "w", encoding="utf-8", newline="").write(s)
    print("  + 修复: .tab-bar 去掉自身 margin-left 与 padding")

# ------------------------------------------------------------ 自检
print("\n自检:")
s = io.open(p, encoding="utf-8", newline="").read()

i_bar_css = s.find(".tab-bar {")
i_bar_div = s.find('<div class="tab-bar"')
i_nav     = s.find('<nav id="sidebar">')
i_box     = s.find('<div style="margin-left:16%')
bar_css   = s[i_bar_css:s.find("}", i_bar_css)] if i_bar_css > 0 else ""

checks = [
    ("tab-bar 无自身 margin-left", "margin-left: 16%" not in bar_css),
    ("tab-bar padding 已归零",     "padding: 0;" in bar_css),
    ("保留 border-bottom",         "border-bottom: 2px solid #226" in bar_css),
    ("tab-bar 在 nav 之后",        i_nav > 0 and i_bar_div > i_nav),
    ("tab-bar 在容器之内",         i_box > 0 and i_bar_div > i_box),
    ("3 个 tab-btn 都在",          s.count("tab-btn") >= 3),
    ("3 个 tab-content 都在",      s.count('class="tab-content') >= 3),
    ("system.html div 平衡",       s.count("<div") == s.count("</div>")),
]
ok = True
for name, res in checks:
    print("  %-28s %s" % (name, "OK" if res else "失败 <<<"))
    ok = ok and res

print("")
print("  .tab-bar 规则: %s" % bar_css.strip())
print("")
print("✓ 全部通过" if ok else "✗ 存在问题")
