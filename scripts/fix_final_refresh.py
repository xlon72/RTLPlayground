#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""index.html: 等页面全部资源加载完(window load)后再刷新一次数据。

根因
----
main.js 的 update() 里:
    var psvg = document.getElementById("port" + n);
    if (psvg == null || !psvg.contentDocument) continue;  // 整轮跳过
    pState[n] = p.link;                                   // SVG 就绪才赋值

只要某个端口的 <object data="/port.svg"> 没加载完, contentDocument 就为
null, 该端口整轮被跳过, pState 不赋值 -> tile 的"最大链路速率"和端口
速率标签一直显示 "–"。

之前的重试(15 次 x 400ms)不够稳, 改为:
  1) 继续保留轮询重试作为兜底
  2) 额外监听 window load 事件(所有图片/SVG/脚本都加载完), 触发一次
     update(), 这时 SVG 必定就绪
  3) 再加一次 load 后 800ms 的延迟刷新, 双保险

幂等: 已含 v4-final-refresh 标记则跳过。
"""
import io, os, re, sys

if os.path.basename(os.getcwd()) != "html" and os.path.isdir("html"):
    os.chdir("html")
elif not os.path.exists("index.html"):
    sys.exit("✗ 请在仓库根目录或 html/ 目录运行")

MARK = "v4-final-refresh"
h = io.open("index.html", encoding="utf-8", newline="").read()

if MARK in h:
    print("  = 跳过: 已是 v4")
else:
    OLD = '''    setAuto(false);
    initialLoad();
  });
'''
    NEW = '''    /* v4-final-refresh: 等全部资源就绪后再刷一次, 确保速率有值 */
    function finalRefresh() {
      update(function () {
        if (typeof updateTiles === "function") {
          updateTiles();
        }
      });
    }

    window.addEventListener("load", finalRefresh);
    window.addEventListener("load", function () {
      setTimeout(finalRefresh, 800);
    });

    setAuto(false);
    initialLoad();
  });
'''
    if OLD not in h:
        sys.exit("✗ 未定位 setAuto(false)/initialLoad() <<<")
    h = h.replace(OLD, NEW, 1)
    io.open("index.html", "w", encoding="utf-8", newline="").write(h)
    print("  + 修改: index.html 加 load 后最终刷新")

# ------------------------------------------------------------- 自检
print("\n自检:")
h = io.open("index.html", encoding="utf-8", newline="").read()


def balance(js):
    st = []
    i, n, line = 0, len(js), 1
    while i < n:
        c = js[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        if c == "/" and i + 1 < n and js[i + 1] == "/":
            while i < n and js[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and js[i + 1] == "*":
            i += 2
            while i + 1 < n and not (js[i] == "*" and js[i + 1] == "/"):
                if js[i] == "\n":
                    line += 1
                i += 1
            i += 2
            continue
        if c in "\"'":
            q = c
            i += 1
            while i < n:
                if js[i] == "\\":
                    i += 2
                    continue
                if js[i] == q:
                    i += 1
                    break
                if js[i] == "\n":
                    line += 1
                i += 1
            continue
        if c in "([{":
            st.append((c, line))
            i += 1
            continue
        if c in ")]}":
            if not st:
                return False, "第 %d 行多余的 %s" % (line, c)
            o, ol = st.pop()
            if "([{".index(o) != ")]}".index(c):
                return False, "第 %d 行 %s 与第 %d 行 %s 不匹配" % (line, c, ol, o)
            i += 1
            continue
        i += 1
    if st:
        o, ol = st[-1]
        return False, "第 %d 行的 %s 未闭合" % (ol, o)
    return True, "OK"


js = ""
for m in re.finditer(r"<script\b[^>]*>(.*?)</script\s*>", h, re.S):
    if "auto-refresh-btn" in m.group(1):
        js = m.group(1)
        break

ok, msg = balance(js) if js else (False, "未提取到 script 块")
opens = len(re.findall(r"<script\b[^>]*>", h))
closes = len(re.findall(r"</script\s*>", h))

checks = [
    ("index.html 含 v4 标记",      MARK in h),
    ("index.html 有 finalRefresh", "function finalRefresh" in h),
    ("index.html 监听 load",       'window.addEventListener("load", finalRefresh)' in h),
    ("index.html 有延迟兜底",      "setTimeout(finalRefresh, 800)" in h),
    ("script 开闭一致",            opens == closes),
    ("内联 JS 括号平衡",           ok),
    ("index.html div 平衡",        h.count("<div") == h.count("</div>")),
]
allok = True
for name, res in checks:
    print("  %-28s %s" % (name, "OK" if res else "失败 <<<"))
    allok = allok and res
print("")
print("  script 开 %d / 闭 %d" % (opens, closes))
print("  JS 检查: " + msg)
print("")
print("✓ 全部通过" if allok else "✗ 存在问题")
