#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""system.html: 修 tab-bar 与侧边栏错位。

根因
----
#sidebar 是 position:fixed(不占文档流, 宽 240px), 内容区靠 margin-left:16%
避让。而 tab-bar 排在 <nav> 之前, 用自己的内联 margin-left:16% 来避让 ——
百分比按视口算, 侧边栏按固定 240px 算, 两者在任意窗口宽度下都对不齐:
    视口 1200px -> 16% = 192px < 240px  (被侧边栏压住)
    视口 1920px -> 16% = 307px > 240px  (多缩进)
所以 tab-bar 与下方内容永远不在同一条左基线上。

修法
----
把 tab-bar 移到 <nav> 之后、内容容器之内, 与 ports.html 等页面的结构一致,
并删掉它自己的 margin-left:16%(外层容器已有)。

幂等。在仓库根目录或 html/ 目录运行。
"""
import io, os, re, sys

if os.path.basename(os.getcwd()) != "html" and os.path.isdir("html"):
    os.chdir("html")
elif not os.path.exists("system.html"):
    sys.exit("✗ 请在仓库根目录或 html/ 目录运行")

p = "system.html"
s = io.open(p, encoding="utf-8", newline="").read()

if s.count('<div class="tab-bar"') == 0:
    sys.exit("✗ 未找到 tab-bar <<<")

m = re.search(r'[ \t]*<div class="tab-bar">.*?</div>[ \t]*\n', s, re.S)
if not m:
    sys.exit("✗ 未定位 tab-bar 块 <<<")

bar = m.group(0)
s = s[:m.start()] + s[m.end():]

# 清掉 tab-bar 自己的 margin-left(外层容器已有), 保留其他内联样式
bar_clean = bar.replace(
    "margin-bottom: 0; margin-left: 16%; padding: 1px 16px; padding-bottom: 0;",
    "margin-bottom: 12px; padding: 0;").replace(
    'class="tab-bar"', 'class="tab-bar" ')

# 缩进改为容器内层级
bar_clean = "\n".join(
    ("  " + ln if ln.strip() else ln) for ln in bar_clean.splitlines())

# 插到内容容器之后
anchor = '<div style="margin-left:16%;padding:1px 16px;height:1000px;">'
if anchor not in s:
    sys.exit("✗ 未定位内容容器 <<<")
idx = s.index(anchor) + len(anchor)
s = s[:idx] + "\n" + bar_clean.rstrip("\n") + "\n" + s[idx:]

io.open(p, "w", encoding="utf-8", newline="").write(s)
print("  + 修复: tab-bar 移入内容容器, 去掉自身 margin-left")

# ------------------------------------------------------------ 自检
print("\n自检:")
s = io.open(p, encoding="utf-8", newline="").read()
i_bar = s.find('<div class="tab-bar"')
i_nav = s.find('<nav id="sidebar">')
i_box = s.find('<div style="margin-left:16%')

checks = [
    ("tab-bar 在 nav 之后",      i_nav > 0 and i_bar > i_nav),
    ("tab-bar 在内容容器内",     i_box > 0 and i_bar > i_box),
    ("tab-bar 无自身 margin-left", 'class="tab-bar" style' not in s),
    ("3 个 tab-btn 都在",        s.count("tab-btn") >= 3),
    ("tab-content 都在",         s.count('class="tab-content') >= 3),
    ("system.html div 平衡",     s.count("<div") == s.count("</div>")),
    ("system.html button 平衡",  s.count("<button") == s.count("</button>")),
]
ok = True
for name, res in checks:
    print("  %-26s %s" % (name, "OK" if res else "失败 <<<"))
    ok = ok and res
print("")
print("✓ 全部通过" if ok else "✗ 存在问题")
