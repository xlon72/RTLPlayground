#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""首页右上角加"自动刷新"开关(按行号定位, 不依赖缩进)。

上一版用整段字符串做锚点, 因空白/换行细微差异匹配失败。本版改为:
  第 20 行  <h1 ...>               -> 包进 .page-head 并加按钮
  第 6-11 行 window load 脚本块     -> 轮询改由按钮控制(默认关闭)
按行号从大到小替换, 避免先改的行号变化影响后改的。

状态
  OFF(默认): 灰色, 文字"刷新", 不轮询; 初次加载仍取一次数据填充 tile。
  ON       : accent 色, 文字"自动刷新", 恢复 2s 轮询。
  由 ON 切 OFF 时立即补取一次, 避免停在旧值。

停的是 update()(数据源), 而非 dashboard.js 的 updateTiles()(重绘)——
数据源一停, tile 数字静止且 /status.json 请求归零。

幂等: style.css / i18n.js 已改则跳过; index.html 已含按钮则跳过。
"""
import io, os, re, sys

log = []


def load(p):
    return io.open(p, encoding="utf-8", newline="").read()


def save(p, s):
    io.open(p, "w", encoding="utf-8", newline="").write(s)


if os.path.basename(os.getcwd()) != "html" and os.path.isdir("html"):
    os.chdir("html")
elif not os.path.exists("index.html"):
    sys.exit("✗ 请在仓库根目录或 html/ 目录运行")

# ---------------------------------------------------------------- index.html
h = load("index.html")

if 'id="auto-refresh-btn"' in h:
    log.append("  = 跳过(已改): index.html 已有刷新按钮")
else:
    lines = h.splitlines(keepends=True)

    # --- 定位: 优先按内容, 失败则回退行号 ---
    h1_idx = next((i for i, l in enumerate(lines)
                   if "index_heading" in l and "<h1" in l), None)
    js_start = next((i for i, l in enumerate(lines)
                     if 'window.addEventListener("load"' in l), None)
    js_end = None
    if js_start is not None:
        for i in range(js_start, min(js_start + 10, len(lines))):
            if lines[i].rstrip().endswith("});"):
                js_end = i + 1
                break
        # 再吃掉紧随的 </script>
        if js_end is not None and js_end < len(lines) \
           and lines[js_end].strip() == "</script>":
            js_end += 1

    if h1_idx is None:
        log.append("  ! 未定位 h1 行 <<<")
    elif js_start is None or js_end is None:
        log.append("  ! 未定位 load 脚本块 <<<")
    else:
        h1_line = lines[h1_idx]
        indent = re.match(r"^(\s*)", h1_line).group(1)

        NEW_HEAD = (
            indent + '<div class="page-head">\n'
            + h1_line
            + indent + '  <button type="button" id="auto-refresh-btn"'
              ' class="refresh-toggle" aria-pressed="false">\n'
            + indent + '    <svg viewBox="0 0 24 24" fill="none"'
              ' stroke="currentColor" stroke-width="2" stroke-linecap="round"'
              ' stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-3-6.7"/>'
              '<path d="M21 3v6h-6"/></svg>\n'
            + indent + '    <span id="auto-refresh-label"'
              ' data-i18n="dash_refresh">刷新</span>\n'
            + indent + '  </button>\n'
            + indent + '</div>\n')

        js_indent = re.match(r"^(\s*)", lines[js_start]).group(1)
        NEW_SCRIPT = (
            js_indent + '<script>\n'
            + js_indent + 'window.addEventListener("load", function() {\n'
            + js_indent + '  var AUTO_MS = 2000;\n'
            + js_indent + '  var timer = null;\n'
            + js_indent + '  var btn = document.getElementById("auto-refresh-btn");\n'
            + js_indent + '  var label = document.getElementById("auto-refresh-label");\n'
            + '\n'
            + js_indent + '  function setAuto(on) {\n'
            + js_indent + '    if (on && !timer) {\n'
            + js_indent + '      timer = setInterval(function () { update(); }, AUTO_MS);\n'
            + js_indent + '    } else if (!on && timer) {\n'
            + js_indent + '      clearInterval(timer);\n'
            + js_indent + '      timer = null;\n'
            + js_indent + '    }\n'
            + js_indent + '    if (!btn) return;\n'
            + js_indent + '    btn.classList.toggle("on", !!timer);\n'
            + js_indent + '    btn.setAttribute("aria-pressed", timer ? "true" : "false");\n'
            + js_indent + '    if (label) {\n'
            + js_indent + '      label.setAttribute("data-i18n",'
              ' timer ? "dash_auto_refresh" : "dash_refresh");\n'
            + js_indent + '      if (typeof translateAll === "function") translateAll();\n'
            + js_indent + '    }\n'
            + js_indent + '  }\n'
            + '\n'
            + js_indent + '  if (btn) {\n'
            + js_indent + '    btn.addEventListener("click", function () {\n'
            + js_indent + '      var wasOn = !!timer;\n'
            + js_indent + '      setAuto(!wasOn);\n'
            + js_indent + '      if (wasOn) {\n'
            + js_indent + '        update(function () {\n'
            + js_indent + '          if (typeof updateTiles === "function") updateTiles();\n'
            + js_indent + '        });\n'
            + js_indent + '      }\n'
            + js_indent + '    });\n'
            + js_indent + '  }\n'
            + '\n'
            + js_indent + '  update(function () {\n'
            + js_indent + '    if (typeof updateTiles === "function") updateTiles();\n'
            + js_indent + '    setAuto(false);\n'
            + js_indent + '  });\n'
            + js_indent + '});\n'
            + js_indent + '</script>\n')

        # 从大到小替换, 前面的替换不影响后面的行号
        for start, end, new, what in sorted(
                [(h1_idx, h1_idx + 1, NEW_HEAD, "h1 -> .page-head + 按钮"),
                 (js_start, js_end, NEW_SCRIPT, "load 脚本 -> 按钮控制轮询")],
                key=lambda t: -t[0]):
            lines[start:end] = [new]
            log.append("  + 修改: index.html " + what)

        save("index.html", "".join(lines))

# ---------------------------------------------------------------- style.css
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

# ---------------------------------------------------------------- i18n
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
    log.append("  ! i18n.js 语言包定位失败, 跳过 <<<")
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

# ---------------------------------------------------------------- 自检
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
    ("index.html script 平衡",  h.count("<script") == h.count("</script>")),
]

ok = True
for name, res in checks:
    print("  %-26s %s" % (name, "OK" if res else "失败 <<<"))
    ok = ok and res

print("")
print("✓ 全部通过" if ok else "✗ 存在问题")
