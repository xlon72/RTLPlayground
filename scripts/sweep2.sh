#!/usr/bin/env bash
set -Eeuo pipefail
export PATH="/opt/homebrew/opt/binutils/bin:$PATH"
cd ~/Desktop/lt/RTLPlayground
for n in 2 4 8; do
  printf "UIP_CONNS = %-2s : " "$n"
  python3 ~/set_conns.py "$n" >/dev/null
  rm -rf output/FG_4GT_2SX_V2_0
  bash ~/build_local.sh > /tmp/sw.log 2>&1
  if ls output/FG_4GT_2SX_V2_0/*.bin >/dev/null 2>&1; then
    echo "✅ 编译成功"
  else
    e=$(grep -m1 -E "ASlink-Error" /tmp/sw.log)
    echo "✗ ${e:-其他失败}"
  fi
done
