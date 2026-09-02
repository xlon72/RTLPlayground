#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""update.html: 删除硬编码中文提示, 让下方提示跟随语言。

问题
----
1) 第 42 行有一行硬编码中文提示(在 .fw-current 的 <div> 之外, 缩进也错),
   与下面那段英文重复。删除它。
2) 下方 .fw-note 的 data-i18n="" 是空值, 所以 translateAll() 找不到词条,
   永远显示英文原文。补上键名 update_auto_reboot 并写入三语翻译。

注意: i18n.js 里已存在 update_auto_reboot 词条(之前补过), 若已存在则跳过,
避免重复键(JS 对象字面量中后者覆盖前者)。

幂等。
"""
import io, os, re, sys

if os.path.basename(os.getcwd()) != "html" and os.path.isdir("html"):
    os.chdir("html")
elif not os.path.exists("update.html"):
    sys.exit("✗ 请在仓库根目录或 html/ 目录运行")

log = []
p = "update.html"
s = io.open(p, encoding="utf-8", newline="").read()

# ---------------------------------------------------- 1) 删除硬编码中文提示
pat = re.compile(
    r'[ \t]*<div style="color:#666;margin-top:10px;">[^<]*</div>[ \t]*\n')
if u"固件上传完成后" in s:
    s2 = pat.sub("", s, count=1)
    if s2 == s:
        log.append("  ! 正则未匹配硬编码中文提示 <<<")
    else:
        s = s2
        log.append("  + 删除: update.html 硬编码中文提示(上面那个)")
else:
    log.append("  = 跳过: 已无硬编码中文提示")

# ---------------------------------------------------- 2) 补 data-i18n 键名
OLD_NOTE = '''        <div class="fw-note" data-i18n="">
          Once the upload finishes the switch verifies the image and reboots
          into it automatically. Do not power it off during that time.
        </div>
'''
NEW_NOTE = '''        <div class="fw-note" data-i18n="update_auto_reboot"></div>
'''
if OLD_NOTE in s:
    s = s.replace(OLD_NOTE, NEW_NOTE, 1)
    log.append("  + 修改: .fw-note 补 data-i18n=\"update_auto_reboot\"")
elif 'data-i18n="update_auto_reboot"' in s:
    log.append("  = 跳过: data-i18n 已正确")
else:
    log.append("  ! 未定位 .fw-note <<<")

io.open(p, "w", encoding="utf-8", newline="").write(s)

# ---------------------------------------------------- 3) i18n 词条
ADD = {
    "update_auto_reboot": (
        "Once the upload finishes the switch verifies the image and reboots "
        "into it automatically. Do not power it off during that time.",
        "アップロード完了後、スイッチがイメージを検証して自動的に再起動します。"
        "その間は電源を切らないでください。",
        "固件上传完成后，交换机将自动校验镜像并重启。在此期间请勿断电。",
    )
}

ip = "i18n.js"
ij = io.open(ip, encoding="utf-8", newline="").read()
lines = ij.splitlines(keepends=True)
bounds, cur = {}, None
for i, ln in enumerate(lines):
    m = re.match(r"^  (en|ja|zh): \{", ln)
    if m:
        cur = m.group(1)
        bounds[cur] = [i, None]
    elif cur and re.match(r"^  \},?\s*$", ln):
        bounds[cur][1] = i
        cur = None

if [k for k in ("en", "ja", "zh") if k not in bounds or bounds[k][1] is None]:
    log.append("  ! i18n.js 语言包定位失败 <<<")
else:
    n = 0
    for lang, idx in (("zh", 2), ("ja", 1), ("en", 0)):
        end = bounds[lang][1]
        block = ""
        for k, v in ADD.items():
            if re.search(r"^    %s:" % re.escape(k), ij, re.M):
                continue
            block += "    %s:\n      '%s',\n" % (k, v[idx])
            n += 1
        if block:
            lines[end:end] = [block]
    if n:
        io.open(ip, "w", encoding="utf-8", newline="").write("".join(lines))
        log.append("  + 补入: i18n.js %d 条翻译" % n)
    else:
        log.append("  = 跳过: i18n.js 已有 update_auto_reboot")

print("\n".join(log))

# ---------------------------------------------------- 自检
print("\n自检:")
s = io.open(p, encoding="utf-8", newline="").read()
ij = io.open(ip, encoding="utf-8", newline="").read()

dups, seen, cur = [], {}, None
for ln in ij.splitlines():
    m = re.match(r"^  (en|ja|zh): \{", ln)
    if m:
        cur = m.group(1); seen[cur] = {}; continue
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
    ("已删硬编码中文提示",    u"固件上传完成后" not in s),
    ("fw-note 有 i18n 键名",  'data-i18n="update_auto_reboot"' in s),
    ("fw-note 无英文残留",    "Once the upload finishes" not in s),
    ("i18n en 词条",          "update_auto_reboot:" in ij),
    ("i18n 有中文翻译",       u"固件上传完成后" in ij),
    ("i18n 无重复键",         len(dups) == 0),
    ("update.html div 平衡",  s.count("<div") == s.count("</div>")),
]
ok = True
for name, res in checks:
    print("  %-24s %s" % (name, "OK" if res else "失败 <<<"))
    ok = ok and res

print("")
if dups:
    print("  重复键: %s" % ", ".join(dups[:10]))
print("✓ 全部通过" if ok else "✗ 存在问题")
