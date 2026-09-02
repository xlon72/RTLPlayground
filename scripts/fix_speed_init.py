#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修正首次加载判定: 由 numPorts > 0 改为"端口 SVG 全部就绪"。

根因
----
main.js 的 update() 里:
    var psvg = document.getElementById("port" + n);
    if (psvg == null || !psvg.contentDocument) continue;   // 整轮跳过
    ...
    pState[n] = p.link;                                    // 只有 SVG 就绪才赋值

首次 update() 时 drawPorts() 刚插入 <object data="/port.svg">, SVG 尚未
加载完, contentDocument 为 null, 于是所有端口被 continue 跳过, pState 全 0。
而 numPorts 在 drawPorts() 时就已赋值, 所以旧判定 numPorts > 0 第一次就
误认为数据齐了并停止轮询 -> 速率永远显示 "–"。
点一次刷新能出数据, 是因为那时 SVG 早已加载完。

修法
----
haveData() 改为检查 port1..portN 的 contentDocument 是否全部就绪,
并把重试放宽到 15 次 x 400ms(约 6 秒)。

幂等: 已含 v3-svg-ready 标记则跳过。
"""
import io, os, re, sys

if os.path.basename(os.getcwd()) != "html" and os.path.isdir("html"):
    os.chdir("html")
elif not os.path.exists("index.html"):
    sys.exit("✗ 请在仓库根目录或 html/ 目录运行")

MARK = "v3-svg-ready"
h = io.open("index.html", encoding="utf-8", newline="").read()

if MARK in h:
    print("  = 跳过: 已是 svg-ready 版")
else:
    OLD = '''    function haveData() {
      if (typeof numPorts === "undefined") {
        return false;
      }
      return numPorts > 0;
    }
'''
    NEW = '''    /* v3-svg-ready */
    function haveData() {
      if (typeof numPorts === "undefined" || numPorts <= 0) {
        return false;
      }
      var found = 0;
      var ready = 0;
      for (var i = 1; i <= numPorts; i++) {
        var el = document.getElementById("port" + i);
        if (el) {
          found = found + 1;
          if (el.contentDocument) {
            ready = ready + 1;
          }
        }
      }
      return found > 0 && ready === found;
    }
'''
    if OLD not in h:
        sys.exit("✗ 未定位 haveData() <<<")
    h = h.replace(OLD, NEW, 1)

    OLD2 = '''        tries = tries + 1;
        if (tries < 10) {
          setTimeout(initialLoad, 500);
        } else {
          setAuto(false);
        }
'''
    NEW2 = '''        tries = tries + 1;
        if (tries < 15) {
          setTimeout(initialLoad, 400);
        } else {
          setAuto(false);
        }
'''
    if OLD2 in h:
        h = h.replace(OLD2, NEW2, 1)

    io.open("index.html", "w", encoding="utf-8", newline="").write(h)
    print("  + 修改: index.html haveData() -> 检查 SVG 就绪")

# ------------------------------------------------------------ system.html
sp = "system.html"
s = io.open(sp, encoding="utf-8", newline="").read()

pat = re.compile(
    r'[ \t]*<span data-i18n="sys_ip_note">[^<]*</span><br/>[ \t]*\n')
if "sys_ip_note" not in s:
    print("  = 跳过: system.html 已无 sys_ip_note")
else:
    s2 = pat.sub("", s, count=1)
    if s2 == s:
        print("  ! 正则未匹配 sys_ip_note <<<")
    else:
        io.open(sp, "w", encoding="utf-8", newline="").write(s2)
        print("  + 删除: system.html sys_ip_note 提示(上面那个)")

# ------------------------------------------------------------ 自检
print("\n自检:")
h = io.open("index.html", encoding="utf-8", newline="").read()
s = io.open(sp, encoding="utf-8", newline="").read()
ij = io.open("i18n.js", encoding="utf-8", newline="").read()

# 重复键检查: JS 对象字面量里后出现的同名键会覆盖前面的
dups = []
cur = None
seen = {}
for ln in ij.splitlines():
    m = re.match(r"^  (en|ja|zh): \{", ln)
    if m:
        cur = m.group(1); seen[cur] = {}
        continue
    if cur and re.match(r"^  \},?\s*$", ln):
        cur = None; continue
    if cur:
        km = re.match(r"^    ([A-Za-z_][\w]*):", ln)
        if km:
            k = km.group(1)
            if k in seen[cur]:
                dups.append("%s.%s" % (cur, k))
            seen[cur][k] = True

opens = len(re.findall(r"<script\b[^>]*>", h))
closes = len(re.findall(r"</script\s*>", h))

checks = [
    ("index.html 含 svg-ready 标记",   MARK in h),
    ("index.html 已移除旧判定",        "return numPorts > 0;" not in h),
    ("index.html script 开闭一致",     opens == closes),
    ("system.html 已删 sys_ip_note",   "sys_ip_note" not in s),
    ("system.html 保留 sys_save_label", "sys_save_label" in s),
    ("i18n 有 sys_save_label(en)",     "sys_save_label: 'Save all" in ij),
    ("i18n 无重复键",                  len(dups) == 0),
    ("system.html span 平衡",          s.count("<span") == s.count("</span>")),
]
ok = True
for name, res in checks:
    print("  %-30s %s" % (name, "OK" if res else "失败 <<<"))
    ok = ok and res

print("")
print("  script 开 %d / 闭 %d" % (opens, closes))
if dups:
    print("  重复键(%d): %s" % (len(dups), ", ".join(dups[:10])))
print("")
print("✓ 全部通过" if ok else "✗ 存在问题")
