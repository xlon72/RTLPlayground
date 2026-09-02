#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""整份重写 index.html: 加入自动刷新开关 + v3 加载逻辑。

为什么不用补丁
--------------
v2 先替换了内联 script 块, v3 又替换一次, 两次替换累积出一个孤立的
</script>(第 82 行), 导致 script 开闭标签不平衡(开 7 / 闭 8)。
补丁套补丁已不可靠, 改为整份生成。

内容来源
--------
HEAD 版 index.html(56 行), 两处改动:
  1) <h1> 包进 .page-head, 右侧加 #auto-refresh-btn 按钮
  2) 内联 script 换成 v3 逻辑

v3 的关键行为
-------------
  OFF(默认): 灰色按钮, 文字"刷新"。
  ON       : accent 色, 文字"自动刷新", 2s 轮询。
  初次加载: update() 回调里检查 numPorts > 0, 未拿到数据则最多
            重试 10 次(约 5 秒)。保证第一次进网页 tile 有数字,
            而不是一直显示 "–"。
  由 ON 切 OFF 时立即补取一次, 避免停在旧值。

style.css 与 i18n.js 已在之前的步骤改好, 本脚本不动它们, 但会检查。
"""
import io, os, re, sys

if os.path.basename(os.getcwd()) != "html" and os.path.isdir("html"):
    os.chdir("html")
elif not os.path.exists("index.html"):
    sys.exit("✗ 请在仓库根目录或 html/ 目录运行")

HTML = '''<!DOCTYPE html>
<html>
  <script src="/main.js"></script>
  <script src="/main_info.js"></script>
  <script src="/i18n.js"></script>
  <script>
  window.addEventListener("load", function () {
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
  </script>
  <link rel="stylesheet" href="style.css">
  <title data-i18n="index_title">FreeSwitchOS Main Page</title>
</head>

<body>
  <nav id="sidebar"></nav>
  <div style="margin-left:16%;padding:1px 16px;height:1000px;">
    <div class="page-head">
      <h1 data-i18n="index_heading">Switch Configuration</h1>
      <button type="button" id="auto-refresh-btn" class="refresh-toggle">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v6h-6"/></svg>
        <span id="auto-refresh-label" data-i18n="dash_refresh">\u5237\u65b0</span>
      </button>
    </div>
    <div class="tiles">
      <div class="tile">
        <div class="tile-icon tile-accent-a"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg></div>
        <div class="tile-value" id="tile-ports">\u2013</div>
        <div class="tile-label" data-i18n="dash_ports">Ports</div>
      </div>
      <div class="tile">
        <div class="tile-icon tile-accent-b"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 18a8 8 0 1 1 16 0"/><path d="M12 18l3.5-5"/></svg></div>
        <div class="tile-value" id="tile-speed">\u2013</div>
        <div class="tile-label" data-i18n="dash_speed">Max Link Speed</div>
      </div>
      <div class="tile">
        <div class="tile-icon tile-accent-c"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20V5"/><path d="m611 6-6 6 6"/></svg></div>
        <div class="tile-value" id="tile-tx">\u2013</div>
        <div class="tile-label" data-i18n="dash_tx">TX Total</div>
      </div>
      <div class="tile">
        <div class="tile-icon tile-accent-d"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4v15"/><path d="m613 6 6 6-6"/></svg></div>
        <div class="tile-value" id="tile-rx">\u2013</div>
        <div class="tile-label" data-i18n="dash_rx">RX Total</div>
      </div>
    </div>
    <div id="ports"></div>
    <table id="infoTable">
      <tr>
        <th colspan="2" data-i18n="index_settings">Settings</th>
      </tr>
      <tbody>
      </tbody>
    </table>
  </div>
  <script src="/dashboard.js"></script>
  <script src="/navigation.js"></script>
  <script>if (typeof translateAll === "function") translateAll();</script>
</body>
</html>
'''

io.open("index.html", "w", encoding="utf-8", newline="").write(HTML)
print("  + 重写: index.html")


def check_balance(js):
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
                return False, "第 %d 行多余的 %s" % (line, c)
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


h = io.open("index.html", encoding="utf-8", newline="").read()
cs = io.open("style.css", encoding="utf-8", newline="").read()
ij = io.open("i18n.js", encoding="utf-8", newline="").read()

opens = re.findall(r"<script\b[^>]*>", h)
closes = re.findall(r"</script\s*>", h)

js = ""
for m in re.finditer(r"<script\b[^>]*>(.*?)</script\s*>", h, re.S):
    if "auto-refresh-btn" in m.group(1):
        js = m.group(1)
        break

ok, msg = check_balance(js) if js else (False, "未提取到 script 块")
iok, imsg = check_balance(ij)

checks = [
    ("script 开闭标签数量一致", len(opens) == len(closes)),
    ("script 开标签数 = 4",     len(opens) == 4),
    ("index.html 含 v3 标记",   "v3-initial-load-retry" in h),
    ("index.html 按钮元素",     'id="auto-refresh-btn"' in h),
    ("index.html label 元素",   'id="auto-refresh-label"' in h),
    ("index.html 默认关闭轮询", "setAuto(false)" in h),
    ("index.html 已移除旧轮询", "const interval = setInterval" not in h),
    ("内联 script JS 括号平衡", ok),
    ("i18n.js JS 括号平衡",     iok),
    ("style.css 有开关样式",    "button.refresh-toggle" in cs),
    ("i18n 有 dash_refresh",    "dash_refresh:" in ij),
    ("i18n 有 dash_auto_refresh", "dash_auto_refresh:" in ij),
    ("index.html div 平衡",     h.count("<div") == h.count("</div>")),
    ("index.html button 平衡",  h.count("<button") == h.count("</button>")),
]

print("\n自检:")
allok = True
for name, res in checks:
    print("  %-28s %s" % (name, "OK" if res else "失败 <<<"))
    allok = allok and res

print("")
print("  script 开标签 %d / 闭标签 %d" % (len(opens), len(closes)))
print("  内联 JS 检查: " + msg)
print("  i18n.js 检查: " + imsg)
print("")
print("✓ 全部通过" if allok else "✗ 存在问题")
