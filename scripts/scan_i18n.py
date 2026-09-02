#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
找出 i18n.js 里未被任何页面引用的词条。默认 dry-run, 加 --apply 才删除。

安全设计
--------
* 动态 key 保护: 若代码里出现 t('port_' + x) 这类拼接, 则所有以该前缀
  开头的词条一律保留(无法静态确定实际用到哪些)。
* 只删三个语言包都存在的 key。
"""
import io, os, re, sys

I18N = "i18n.js"
USE_PATTERNS = [
    re.compile(r"""data-i18n(?:-placeholder)?\s*=\s*["']([\w.\-]+)["']"""),
    re.compile(r"""\bt\s*\(\s*["']([\w.\-]+)["']"""),
]
DYN = re.compile(r"""\bt\s*\(\s*["']([\w.\-]*)["']\s*\+""")

def read(p):
    return io.open(p, encoding="utf-8", errors="replace").read()

def lang_blocks(src):
    out = {}
    for m in re.finditer(r"^([ \t]*)(en|ja|zh):[ \t]*\{", src, re.M):
        lang = m.group(2)
        start = m.end() - 1
        depth, j = 0, start
        while j < len(src):
            if src[j] == '{': depth += 1
            elif src[j] == '}':
                depth -= 1
                if depth == 0: break
            j += 1
        body = src[start:j]
        keys = {}
        for km in re.finditer(r"^([ \t]*)([\w.\-]+)\s*:", body, re.M):
            ls = km.start()
            le = body.find("\n", ls)
            le = len(body) if le < 0 else le + 1
            keys[km.group(2)] = (ls, le)
        out[lang] = (start, j, keys)
    return out

def main():
    apply_changes = "--apply" in sys.argv
    if os.path.basename(os.getcwd()) != "html" and os.path.isdir("html"):
        os.chdir("html")
    if not os.path.exists(I18N):
        sys.exit("✗ 未找到 i18n.js，请在仓库根目录或 html/ 目录运行")

    src = read(I18N)
    langs = lang_blocks(src)
    if "en" not in langs:
        sys.exit("✗ i18n.js 里没找到 en 包")

    used, prefixes = set(), set()
    for f in sorted(os.listdir(".")):
        if not (f.endswith(".html") or f.endswith(".js")) or f == I18N:
            continue
        s = read(f)
        for pat in USE_PATTERNS:
            used.update(pat.findall(s))
        prefixes.update(m.group(1) for m in DYN.finditer(s))

    en_keys = set(langs["en"][2])
    unused = sorted(k for k in en_keys - used
                    if not any(k.startswith(p) for p in prefixes if p))

    save_bytes = 0
    for k in unused:
        for l in ("en", "ja", "zh"):
            if l in langs and k in langs[l][2]:
                ls, le = langs[l][2][k]
                save_bytes += (le - ls)

    print("i18n 词条统计")
    print("  词条总数 (en 包): %d" % len(en_keys))
    print("  被引用:           %d" % (len(en_keys) - len(unused)))
    print("  未被引用:         %d" % len(unused))
    if prefixes:
        print("  动态前缀(保护中): %s" % (", ".join(sorted(p for p in prefixes if p)) or "(无)"))
    print("  预计可省:         %d 字节 (%.1f KB)" % (save_bytes, save_bytes / 1024.0))
    if unused:
        print("\n未使用词条清单:")
        for k in unused:
            print("    " + k)

    if not apply_changes:
        print("\n(dry-run: 未修改任何文件。确认后加 --apply 执行删除)")
        return
    if not unused:
        print("\n没有可删除的词条。")
        return

    new_src = src
    for l in ("en", "ja", "zh"):
        if l not in langs:
            continue
        start, end, kmap = langs[l]
        body = src[start:end]
        keep = []
        for km in re.finditer(r"^([ \t]*)([\w.\-]+)\s*:", body, re.M):
            if km.group(2) in set(unused):
                ls = km.start()
                le = body.find("\n", ls)
                le = len(body) if le < 0 else le + 1
                keep.append((ls, le))
        for ls, le in reversed(keep):
            body = body[:ls] + body[le:]
        new_src = new_src[:start] + body + new_src[end:]
        src = new_src
        langs = lang_blocks(src)
    io.open(I18N, "w", encoding="utf-8").write(new_src)
    print("\n✓ 已删除 %d 个未使用词条 (3 个语言包)" % len(unused))

main()
