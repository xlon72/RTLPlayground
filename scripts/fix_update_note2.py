#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""update.html: 给 .fw-note 补 data-i18n(用正则, 不匹配固定缩进)。

上一版用整段字符串做锚点, 因缩进/换行差异匹配失败。本版用正则
按 class 名定位, 忽略具体空白。

已完成: 硬编码中文提示已删; i18n.js 三语词条已补。
本脚本只做一件事: 把 <div class="fw-note" data-i18n="">...</div>
替换为 <div class="fw-note" data-i18n="update_auto_reboot"></div>
"""
import io, os, re, sys

if os.path.basename(os.getcwd()) != "html" and os.path.isdir("html"):
    os.chdir("html")
elif not os.path.exists("update.html"):
    sys.exit("✗ 请在仓库根目录或 html/ 目录运行")

p = "update.html"
s = io.open(p, encoding="utf-8", newline="").read()

# 匹配 <div class="fw-note" ...> 到其后的第一个 </div>, 跨行, 忽略空白细节
pat = re.compile(
    r'<div\s+class="fw-note"[^>]*>\s*.*?\s*</div>',
    re.S)

m = pat.search(s)
if not m:
    sys.exit("✗ 未定位到 .fw-note 块 <<<")

old = m.group(0)
new = '<div class="fw-note" data-i18n="update_auto_reboot"></div>'

if 'data-i18n="update_auto_reboot"' in old:
    print("  = 跳过: data-i18n 已正确")
else:
    s = s[:m.start()] + new + s[m.end():]
    io.open(p, "w", encoding="utf-8", newline="").write(s)
    print("  + 替换: .fw-note -> data-i18n=\"update_auto_reboot\"")
    print("    原内容: %r" % old[:90])

# ------------------------------------------------------------ 自检
print("\n自检:")
s = io.open(p, encoding="utf-8", newline="").read()
ij = io.open("i18n.js", encoding="utf-8", newline="").read()

dups, seen, cur = [], {}, None
for ln in ij.splitlines():
    mm = re.match(r"^  (en|ja|zh): \{", ln)
    if mm:
        cur = mm.group(1); seen[cur] = {}; continue
    if cur and re.match(r"^  \},?\s*$", ln):
        cur = None; continue
    if cur:
        km = re.match(r"^    ([A-Za-z_]\w*):", ln)
        if km:
            k = km.group(1)
            if k in seen[cur]:
                dups.append("%s.%s" % (cur, k))
            seen[cur][k] = True

checks = [
    ("已删硬编码中文提示",   u"固件上传完成后" not in s),
    ("fw-note 有 i18n 键名", 'data-i18n="update_auto_reboot"' in s),
    ("fw-note 无英文残留",   "Once the upload finishes" not in s),
    ("i18n en 词条",         "update_auto_reboot:" in ij),
    ("i18n 有中文翻译",      u"固件上传完成后" in ij),
    ("i18n 无重复键",        len(dups) == 0),
    ("update.html div 平衡", s.count("<div") == s.count("</div>")),
]
ok = True
for name, res in checks:
    print("  %-24s %s" % (name, "OK" if res else "失败 <<<"))
    ok = ok and res

print("")
if dups:
    print("  重复键: %s" % ", ".join(dups[:10]))
print("✓ 全部通过" if ok else "✗ 存在问题")
