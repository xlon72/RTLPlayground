#!/usr/bin/env bash
set -Eeuo pipefail
export PATH="/opt/homebrew/opt/binutils/bin:$PATH"
cd ~/Desktop/lt/RTLPlayground
cp Makefile /tmp/Makefile.orig

perl -i -pe 's/^(CC_FLAGS\s*=.*)$/$1 --xstack/' Makefile
echo "== CC_FLAGS =="; grep -n '^CC_FLAGS' Makefile

python3 ~/set_conns.py 8
rm -rf output/FG_4GT_2SX_V2_0
bash ~/build_local.sh > /tmp/xs.log 2>&1
echo "退出码: $?"
grep -E "ASlink-Error" /tmp/xs.log | head -3

if ls output/FG_4GT_2SX_V2_0/*.bin >/dev/null 2>&1; then
  echo "✅ --xstack + UIP_CONNS=8 成功"
  ls -l output/FG_4GT_2SX_V2_0/*.bin
else
  tail -8 /tmp/xs.log
  cp /tmp/Makefile.orig Makefile; echo "(已还原)"
fi
