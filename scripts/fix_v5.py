#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复三处前端问题。

1) SVG path 属性损坏(index.html)
   "m611 6-6 6 6" -> "m6 11 6-6 6 6"
   "m613 6 6 6-6" -> "m6 13 6 6 6-6"
   原版文件里就缺空格, Chrome 每次渲染都报 Unexpected end of attribute。

2) finalRefresh 是死代码(index.html)
   v4 把 window.addEventListener("load", finalRefresh) 写在外层
   load 回调内部 —— 按 DOM 规范, 事件派发期间新注册的监听器不会在
   本次派发中被调用, 所以它和它内部的 setTimeout 兜底从未执行。
   改为在 load 回调内直接 setTimeout 调用。

3) pState 赋值太晚(main.js) —— 速率为空的真正根因
   update() 里 pState[n] = p.link 位于 SVG 就绪检查之后:
       if (psvg == null || !psvg.contentDocument) continue;
   首次调用时 port.svg 未加载完, 所有端口被跳过, pState 全 0。
   修法: 在 SVG 检查之前就赋值, 与 SVG 状态解耦。

幂等。
"""
import io, os, re, sys

log = []

if os.path.basename(os.getcwd()) != "html" and os.path.isdir("html"):
    os.chdir("html")
elif not os.path.exists("index.html"):
    sys.exit("✗ 请在仓库根目录或 html/ 目录运行")

# ---------------------------------------------- 1) SVG path
p = "index.html"
s = io.open(p, encoding="utf-8", newline="").read()
ch = False
for old, new, label in [
    ('d="m611 6-6 6 6"', 'd="m6 11 6-6 6 6"', "TX 图标 path"),
    ('d="m613 6 6 6-6"', 'd="m6 13 6 6 6-6"', "RX 图标 path"),
]:
    if new in s:
        log.append("  = 跳过(已修): " + label)
    elif old in s:
        s = s.replace(old, new, 1)
        log.append("  + 修复: " + label)
        ch = True
    else:
        log.append("  ! 未找到 <<< " + label)

# ---------------------------------------------- 2) finalRefresh 死代码
pat_dead = re.compile(
    r'[ \t]*window\.addEventListener\("load", finalRefresh\);[ \t]*\n'
    r'[ \t]*window\.addEventListener\("load", function \(\) \{[ \t]*\n'
    r'[ \t]*setTimeout\(finalRefresh, \d+\);[ \t]*\n'
    r'[ \t]*\}\);[ \t]*\n')
if "v5-direct-refresh" in s:
    log.append("  = 跳过(已修): finalRefresh 直接调用")
else:
    m = pat_dead.search(s)
    if m:
        s = s[:m.start()] + "    setTimeout(finalRefresh, 400);\n    setTimeout(finalRefresh, 1500);\n" + s[m.end():]
        s = s.replace("/* v4-final-refresh", "/* v5-direct-refresh", 1)
        log.append("  + 修复: finalRefresh 改为直接 setTimeout")
        ch = True
    else:
        log.append("  ! 未定位 finalRefresh 死代码 <<<")

if ch:
    io.open(p, "w", encoding="utf-8", newline="").write(s)

# ---------------------------------------------- 3) main.js pState 提前
mp = "main.js"
try:
    mj = io.open(mp, encoding="utf-8", newline="").read()
except IOError:
    log.append("  ! main.js 不存在 <<<")
    mj = None

if mj:
    anchor = re.compile(
        r"^([ \t]*)(txBytes\[n\] = BigInt\(p\.txBytes\);[ \t]*"
        r"rxBytes\[n\] = BigInt\(p\.rxBytes\);)[ \t]*$", re.M)
    ma = anchor.search(mj)
    if not ma:
        log.append("  ! main.js 未定位 txBytes 赋值行 <<<")
    else:
        ind = ma.group(1)
        eol = mj.find("\n", ma.end())
        eol = len(mj) if eol < 0 else eol
        nxt = mj[eol + 1:]
        nxt_line = nxt[:nxt.find("\n")] if "\n" in nxt else nxt
        if "pState[n] = (p.enabled == 0)" in nxt_line:
            log.append("  = 跳过(已修): main.js pState 提前赋值")
        else:
            ins = "\n" + ind + "pState[n] = (p.enabled == 0) ? -1 : p.link;"
            mj = mj[:eol] + ins + mj[eol:]
            io.open(mp, "w", encoding="utf-8", newline="").write(mj)
            log.append("  + 修复: main.js pState 提到 SVG 检查之前")

print("\n".join(log))

# ---------------------------------------------- 自检
print("\n自检:")
s = io.open(p, encoding="utf-8", newline="").read()
mj = io.open(mp, encoding="utf-8", newline="").read() if mj else ""

i_tx = s.find('d="m6 11 6-6 6 6"')
i_rx = s.find('d="m6 13 6 6 6-6"')
i_anchor = mj.find("txBytes[n] = BigInt(p.txBytes)")
i_pstate = mj.find("pState[n] = (p.enabled == 0) ? -1 : p.link;")
i_psvg = mj.find('document.getElementById(pid)')

checks = [
    ("TX path 已修",        i_tx > 0),
    ("RX path 已修",        i_rx > 0),
    ("无旧 m611",           "m611" not in s),
    ("无旧 m613",           "m613" not in s),
    ("已删死代码监听",      'addEventListener("load", finalRefresh)' not in s),
    ("有直接 setTimeout",   "setTimeout(finalRefresh, 400)" in s),
    ("main.js 有 pState",   i_pstate > 0),
    ("pState 在 txBytes 后", i_anchor > 0 and i_pstate > i_anchor),
    ("pState 在 SVG 检查前", i_psvg > 0 and i_pstate < i_psvg),
]
ok = True
for name, res in checks:
    print("  %-24s %s" % (name, "OK" if res else "失败 <<<"))
    ok = ok and res
print("")
print("✓ 全部通过" if ok else "✗ 存在问题")
