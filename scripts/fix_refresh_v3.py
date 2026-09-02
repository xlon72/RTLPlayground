#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""首页刷新开关 v3: 极简重写内联 script + 初次加载重试取数。

v2 的两个症状其实是同一个原因
----------------------------
内联 script 块没执行成功(语法错误)或初次 update() 未取到数据:
  - update() 未成功 -> pState/txBytes/rxBytes/numPorts 全为空
  - updateTiles() 读到 numPorts == 0 -> 四个 tile 显示 "–"
  - btn 的 click 监听未绑定 -> 点按钮没反应

v3 的改动
---------
1. 最保守写法: 不用箭头函数/不用 classList.toggle/不用嵌套三元,
   全部 if-else, 把语法出错概率降到最低。
2. 初次加载"重试直到拿到数据再停": numPorts > 0 才算成功, 最多
   重试 10 次(约 5 秒), 之后无论成败都停止轮询。这样保证第一次
   进网页四个 tile 有数字, 而不是一直 "–"。
3. 内置 JS 括号平衡自检, 生成后立刻校验, 不等刷进去才发现。

幂等: 已含 v3 标记则跳过。
"""
import io, os, re, sys

log = []


def load(p):
    return io.open(p, encoding="utf-8", newline="").read()


def save(p, s):
    io.open(p, "w", encoding="utf-8", newline="").write(s)


def check_balance(js):
    """粗略检查 JS 括号平衡(跳过字符串与注释)。返回 (ok, msg)"""
    stack = []
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
            stack.append((c, line))
            i += 1
            continue
        if c in ")]}":
            if not stack:
                return False, "第 %d 行: 多余的 %s" % (line, c)
            o, ol = stack.pop()
            if "([{".index(o) != ")]}".index(c):
                return False, "第 %d 行 %s 与第 %d 行 %s 不匹配" % (line, c, ol, o)
            i += 1
            continue
        i += 1
    if stack:
        o, ol = stack[-1]
        return False, "第 %d 行的 %s 未闭合" % (ol, o)
    return True, "OK"


if os.path.basename(os.getcwd()) != "html" and os.path.isdir("html"):
    os.chdir("html")
elif not os.path.exists("index.html"):
    sys.exit("✗ 请在仓库根目录或 html/ 目录运行")

MARKER = "v3-initial-load-retry"
h = load("index.html")

if MARKER in h:
    log.append("  = 跳过: 已是 v3")
else:
    JS = '''window.addEventListener("load", function () {
  /* v3-initial-load-retry */
  var AUTO_MS = 2000;
  var timer = null;
  var tries = 0;
  var btn = document.getElementById("auto-refresh-btn");
  var label = document.getElementById("auto-refresh-label");

  function setAuto(on) {
    if (on && !timer) {
      timer = setInterval(update, AUTO_MS);
    } else if (!on && timer) {
      clearInterval(timer);
      timer = null;
    }
    if (btn) {
      if (timer) {
        btn.classList.add("on");
      } else {
        btn.classList.remove("on");
      }
    }
    if (label) {
      if (timer) {
        label.setAttribute("data-i18n", "dash_auto_refresh");
      } else {
        label.setAttribute("data-i18n", "dash_refresh");
      }
      if (typeof translateAll === "function") {
        translateAll();
      }
    }
  }

  function haveData() {
    if (typeof numPorts === "undefined") {
      return false;
    }
    return numPorts > 0;
  }

  function initialLoad() {
    update(function () {
      if (typeof updateTiles === "function") {
        updateTiles();
      }
      if (haveData()) {
        setAuto(false);
        return;
      }
      tries = tries + 1;
      if (tries < 10) {
        setTimeout(initialLoad, 500);
      } else {
        setAuto(false);
      }
    });
  }

  if (btn) {
    btn.onclick = function () {
      var wasOn = (timer !== null);
      setAuto(!wasOn);
      if (wasOn) {
        update(function () {
          if (typeof updateTiles === "function") {
            updateTiles();
          }
        });
      }
    };
  }

  setAuto(false);
  initialLoad();
});
'''

    ok, msg = check_balance(JS)
    if not ok:
        sys.exit("✗ 生成的 JS 括号不平衡: " + msg)
    log.append("  ✓ 生成的 JS 括号平衡检查通过")

    pat = re.compile(r"(<script(?![^>]*\bsrc=)[^>]*>)(.*?)(</script>)", re.S)
    m = None
    for cand in pat.finditer(h):
        if "auto-refresh-btn" in cand.group(2) or \
           'window.addEventListener("load"' in cand.group(2):
            m = cand
            break

    if m is None:
        sys.exit("✗ 未定位 index.html 的内联 script 块")
    h = h[:m.start(2)] + JS + h[m.end(2):]
    save("index.html", h)
    log.append("  + 替换: index.html 内联 script 块 -> v3")

print("\n".join(log))

print("\n自检:")
h = load("index.html")
js = ""
for cand in re.finditer(r"(<script(?![^>]*\bsrc=)[^>]*>)(.*?)(</script>)", h, re.S):
    if "auto-refresh-btn" in cand.group(2):
        js = cand.group(2)
        break

ok, msg = check_balance(js) if js else (False, "未提取到 script 块")
ij = load("i18n.js")
iok, imsg = check_balance(ij)

checks = [
    ("index.html 含 v3 标记",     MARKER in h),
    ("index.html 按钮元素",       'id="auto-refresh-btn"' in h),
    ("script 块 JS 括号平衡",     ok),
    ("i18n.js JS 括号平衡",       iok),
    ("i18n 有 dash_refresh",      "dash_refresh:" in ij),
    ("i18n 有 dash_auto_refresh", "dash_auto_refresh:" in ij),
    ("index.html div 平衡",       h.count("<div") == h.count("</div>")),
    ("index.html script 平衡",    h.count("<script") == h.count("</script>")),
]
allok = True
for name, res in checks:
    print("  %-26s %s" % (name, "OK" if res else "失败 <<<"))
    allok = allok and res

print("")
print("  script 块检查: " + msg)
print("  i18n.js 检查: " + imsg)
print("")
print("✓ 全部通过" if allok else "✗ 存在问题")
