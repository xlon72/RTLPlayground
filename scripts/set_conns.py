#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 UIP_CONF_MAX_CONNECTIONS / UIP_CONNS 的所有定义点设为 N。
   用法: python3 ~/set_conns.py <N>
   注意 uipopt.h 有两个定义点(:245 硬编码, :247 推导式), 属不同 #if 分支,
   必须都改, 否则改了一个另一个生效。幂等。
"""
import io, re, sys

if len(sys.argv) != 2 or not sys.argv[1].isdigit():
    sys.exit("用法: python3 ~/set_conns.py <N>")
N = int(sys.argv[1])

TARGETS = ["uip/uip-conf.h", "uip/uipopt.h"]
PAT = re.compile(r"^(\s*#define\s+(?:UIP_CONF_MAX_CONNECTIONS|UIP_CONNS)\s+)(\d+)(\b.*)$")

found = False
for p in TARGETS:
    try:
        s = io.open(p, encoding="utf-8").read()
    except IOError:
        continue
    out, changed = [], False
    for ln in s.splitlines(keepends=True):
        body = ln.rstrip("\n"); nl = ln[len(body):]
        m = PAT.match(body)
        if m:
            st = body.strip()
            if st.startswith(("//", "/*", "*")):
                out.append(ln); continue
            found = True
            if int(m.group(2)) != N:
                out.append(m.group(1) + str(N) + m.group(3) + nl)
                print("  + %-16s %s -> %d" % (p, m.group(2), N)); changed = True
            else:
                out.append(ln)
        else:
            out.append(ln)
    if changed:
        io.open(p, "w", encoding="utf-8").write("".join(out))

if not found:
    print("  ! 未找到数字形式的 UIP_CONNS 定义 <<<")
print("  ✓ 已设为 %d" % N)
