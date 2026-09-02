#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""首页右上角加"自动刷新"开关, 控制四个 tile(端口/最大速率/TX/RX)是否轮询。

设计
----
index.html 原本无条件 setInterval(update, 2000)。update() 是四个 tile 的
数据来源(updateTiles() 读的 pState/txBytes/rxBytes 都由它填充), 所以它一停,
tile 数字静止, 且 /status.json 请求归零。

状态
  OFF(默认): 灰色按钮, 文字"刷新", 不轮询。初次加载仍取一次数据填充 tile。
  ON       : accent 色按钮, 文字"自动刷新", 恢复 2s 轮询。
由 ON 切回 OFF 时会立即再取一次数据, 避免停在旧值。

语言切换: span 带 data-i18n, 切换时改属性值并重调 translateAll(), 保证
按钮文字跟随当前语言。

纯前端改动(html/ + style.css), 无 C 代码增量, 零 OSEG 风险。
幂等。在仓库根目录或 html/ 目录运行均可。
"""
import io, os, re, sys

log = []


def load(p):
    return io.open(p, encoding="utf-8").read()


def save(p, s):
    io.open(p, "w", encoding="utf-8").write(s)


def sub(s, old, new, label):
    if new in s:
        log.append("  = 跳过(已改): " + label)
        return s, False
    if old not in s:
        log.append("  ! 未找到锚点 <<< " + label)
        return s, False
    log.append("  + 修改: " + label)
    return s.replace(old, new, 1), True


if os.path.basename(os.getcwd()) != "html" and os.path.isdir("html"):
    os.chdir("html")
elif not os.path.exists("index.html"):
    sys.exit("✗ 请在仓库根目录或 html/ 目录运行")

OLD_HEAD = '      <h1 data-i18n="index_heading">Switch Configuration</h1>\n'

NEW_HEAD = '''      <div class="page-head">
        <h1 data-i18n="index_heading">Switch Configuration</h1>
        <button type="button" id="auto-refresh-btn" class="refresh-toggle" aria-pressed="false">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v6h-6"/></svg>
          <span id="auto-refresh-label" data-i18n="dash_refresh">刷新</span>
        </button>
      </div>
'''

OLD_SCRIPT = '''    <script>
    window.addEventListener("load", function() {
      update( () => {
        const interval = setInterval(update, 2000);
      });
    });
    </script>
'''

NEW_SCRIPT = '''    <script>
    window.addEventListener("load", function() {
      var AUTO_MS = 2000;
      var timer = null;
      var btn = document.getElementById("auto-refresh-btn");
      var label = document.getElementById("auto-refresh-label");

      function setAuto(on) {
        if (on && !timer) {
          timer = setInterval(function () { update(); }, AUTO_MS);
        } else if (!on && timer) {
          clearInterval(timer);
          timer = null;
        }
        if (!btn) return;
        btn.classList.toggle("on", !!timer);
        btn.setAttribute("aria-pressed", timer ? "true" : "false");
        if (label) {
          label.setAttribute("data-i18n", timer ? "dash_auto_refresh" : "dash_refresh");
          if (typeof translateAll === "function") translateAll();
        }
      }

      if (btn) {
        btn.addEventListener("click", function () {
          var wasOn = !!timer;
          setAuto(!wasOn);
          if (wasOn) {
            update(function () {
              if (typeof updateTiles === "function") updateTiles();
            });
          }
        });
      }

      update(function () {
        if (typeof updateTiles === "function") updateTiles();
        setAuto(false);
      });
    });
    </script>
'''

s = load("index.html")
s, _ = sub(s, OLD_HEAD, NEW_HEAD, "index.html: h1 包进 .page-head 并加按钮")
s, _ = sub(s, OLD_SCRIPT, NEW_SCRIPT, "index.html: 轮询改由按钮控制, 默认关闭")
save("index.html", s)

CSS = '''
/* 首页自动刷新开关(右上角) */
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.page-head h1 { margin: 0; }

button.refresh-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #f3f4f6;
  color: #6b7280;
  border: 1px solid #d2d2d7;
  border-radius: 10px;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 400;
  cursor: pointer;
  white-space: nowrap;
}
button.refresh-toggle svg { width: 14px; height: 14px; }
button.refresh-toggle:hover { background: #e9eaee; }
button.refresh-toggle.on {
  background: var(--accent, #6d28d9);
  color: #fff;
  border-color: var(--accent, #6d28d9);
}
button.refresh-toggle.on:hover { filter: brightness(1.08); }
'''

cs = load("style.css")
if ".refresh-toggle" in cs:
    log.append("  = 跳过(已改): style.css 已有 .refresh-toggle")
else:
    if not cs.endswith("\n"):
        cs += "\n"
    save("style.css", cs + CSS)
    log.append("  + 追加: style.css 刷新开关样式")

ADD = {
    "dash_refresh":      ("Refresh",      "更新",     "刷新"),
    "dash_auto_refresh": ("Auto Refresh", "自動更新", "自动刷新"),
}

ip = "i18n.js"
s = load(ip)
lines = s.splitlines(keepends=True)
bounds = {}
cur = None
for i, ln in enumerate(lines):
    m = re.match(r"^  (en|ja|zh): \{", ln)
    if m:
        cur = m.group(1)
        bounds[cur] = [i, None]
    elif cur and re.match(r"^  \},?\s*$", ln):
        bounds[cur][1] = i
        cur = None

missing = [k for k in ("en", "ja", "zh") if k not in bounds or bounds[k][1] is None]
if missing:
    log.append("  ! i18n.js 语言包定位失败, 跳过词条补充 <<<")
else:
    n = 0
    for lang, idx in (("zh", 2), ("ja", 1), ("en", 0)):
        end = bounds[lang][1]
        block = ""
        for k, v in ADD.items():
            if re.search(r"^    %s:" % re.escape(k), s, re.M):
                continue
            block += "    %s: '%s',\n" % (k, v[idx])
            n += 1
        if block:
            lines[end:end] = [block]
    if n:
        save(ip, "".join(lines))
        log.append("  + 补入: i18n.js %d 条翻译" % n)
    else:
        log.append("  = 跳过: i18n.js 词条已齐")

print("\n".join(log))

print("\n自检:")
h = load("index.html")
cs = load("style.css")
ij = load("i18n.js")

checks = [
    ("index.html 按钮元素",     'id="auto-refresh-btn"' in h),
    ("index.html label 元素",   'id="auto-refresh-label"' in h),
    ("index.html 默认关闭轮询", "setAuto(false)" in h),
    ("index.html 已移除旧轮询", "const interval = setInterval" not in h),
    ("style.css 开关样式",      ".refresh-toggle" in cs),
    ("style.css 优先级正确",    "button.refresh-toggle" in cs),
    ("i18n dash_refresh",       "dash_refresh:" in ij),
    ("i18n dash_auto_refresh",  "dash_auto_refresh:" in ij),
    ("index.html div 平衡",     h.count("<div") == h.count("</div>")),
    ("index.html button 平衡",  h.count("<button") == h.count("</button>")),
]

ok = True
for name, res in checks:
    print("  %-26s %s" % (name, "OK" if res else "失败 <<<"))
    ok = ok and res

print("")
if ok:
    print("✓ 全部通过")
else:
    print("✗ 存在问题")
