#!/usr/bin/env bash
# 基线下生成 map, 列出内部 RAM 各区域占用
set -Eeuo pipefail
export PATH="/opt/homebrew/opt/binutils/bin:$PATH"
cd ~/Desktop/lt/RTLPlayground

python3 ~/set_conns.py 1
rm -rf output/FG_4GT_2SX_V2_0
bash ~/build_local.sh > /tmp/base.log 2>&1 \
  || { echo "✗ 基线构建失败"; tail -20 /tmp/base.log; exit 1; }
echo "✓ 基线构建成功"

rm -f /tmp/probe.map /tmp/probe.ihx
sdcc -mmcs51 -I. -Ihttpd -Iuip -DMACHINE_FG_4GT_2SX_V2_0 \
  -Wl-bHOME=0x00000 -Wl-bBANK1=0x14000 -Wl-bBANK2=0x24000 -Wl-r -Wl-m \
  -o /tmp/probe.ihx \
  output/FG_4GT_2SX_V2_0/*.rel \
  output/FG_4GT_2SX_V2_0/httpd/*.rel \
  output/FG_4GT_2SX_V2_0/uip/*.rel > /tmp/probe.log 2>&1 || true

[ -f /tmp/probe.map ] || { echo "✗ map 未生成"; tail -20 /tmp/probe.log; exit 1; }
echo "✓ map: /tmp/probe.map"

python3 - <<'PY'
import io, re
lines = io.open("/tmp/probe.map", encoding="utf-8", errors="replace").read().splitlines()
for i, l in enumerate(lines):
    if re.search(r"\bArea\b", l) and re.search(r"\bSize\b", l):
        print("\n=== 区域表 ===")
        print("\n".join(lines[i:i+40]))
        break
else:
    print("\n(未定位到区域表, 打印前 60 行)")
    print("\n".join(lines[:60]))

print("\n=== 内部 RAM(<0x100)相关行 ===")
pat = re.compile(r"^\s*([A-Za-z_][\w]*)\s+([0-9A-Fa-f]{4})\s+([0-9A-Fa-f]{4})")
for l in lines:
    m = pat.match(l)
    if m:
        addr, size = int(m.group(2), 16), int(m.group(3), 16)
        if addr < 0x100 or (addr & 0xffff) < 0x100:
            print("  %-24s addr=0x%04x size=%d" % (m.group(1), addr, size))
PY
