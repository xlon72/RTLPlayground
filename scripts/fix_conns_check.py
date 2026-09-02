#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 UIP_CONF_MAX_CONNECTIONS / UIP_CONNS 的所有数字定义点设为 8。
    上一版只 replace 了第一处, 若文件里有 #ifdef 分支的多个定义就会漏改。
    排除注释行。幂等。改完打印所有生效定义行用于验证。"""
import io, re

def load(p): return io.open(p, encoding="utf-8").read()
def save(p, s): io.open(p, "w", encoding="utf-8").write(s)

TARGETS = ["uip/uip-conf.h", "uip/uipopt.h", "uip/uip.h"]
PAT = re.compile(r"^(\s*#define\s+(?:UIP_CONF_MAX_CONNECTIONS|UIP_CONNS)\s+)(\d+)(\b.*)$")

found = False
for p in TARGETS:
    try:
        s = load(p)
    except IOError:
        print("  跳过(不存在): %s" % p); continue
    out, changed = [], False
    for ln in s.splitlines(keepends=True):
        body = ln.rstrip("\n"); nl = ln[len(body):]
        m = PAT.match(body)
        if m:
            st = body.strip()
            if st.startswith("//") or st.startswith("/*") or st.startswith("*"):
                out.append(ln); continue
            old = int(m.group(2)); found = True
            if old != 8:
                out.append(m.group(1) + "8" + m.group(3) + nl)
                print("  + %-18s %d -> 8   | %s" % (p, old, st)); changed = True
            else:
                out.append(ln); print("  = %-18s 已是 8     | %s" % (p, st))
        else:
            out.append(ln)
    if changed: save(p, "".join(out))

if not found:
    print("  ! 未找到数字形式的 UIP_CONNS 定义 <<<")

print("\n验证(应全部为 8):")
for p in TARGETS:
    try:
        for i, ln in enumerate(load(p).splitlines(), 1):
            if re.search(r"#define\s+(UIP_CONF_MAX_CONNECTIONS|UIP_CONNS)", ln) \
               and not ln.strip().startswith("//"):
                print("  %s:%d  %s" % (p, i, ln.strip()))
    except IOError: pass
