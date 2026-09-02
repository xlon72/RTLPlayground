#!/usr/bin/env bash
# 在不改动 httpd.c 的前提下, 找出能通过链接的最大 UIP_CONNS。
set -Eeuo pipefail
export PATH="/opt/homebrew/opt/binutils/bin:$PATH"
command -v objcopy >/dev/null || { echo "✗ objcopy 不可用"; exit 1; }
cd ~/Desktop/lt/RTLPlayground
for n in 1 2 3 4 6 8; do
  printf "UIP_CONNS = %-2s : " "$n"
  python3 ~/set_conns.py "$n" >/dev/null
  rm -rf output/FG_4GT_2SX_V2_0
  if bash ~/build_local.sh 2>&1 | grep -q "ASlink-Error"; then
    echo "✗ OSEG 溢出"
  elif ls output/FG_4GT_2SX_V2_0/*.bin >/dev/null 2>&1; then
    echo "✅ 编译成功"
  else
    echo "✗ 其他失败"
  fi
done
