#!/usr/bin/env bash
# 试 --stack-auto: 把函数局部变量从 OSEG 搬到栈, 腾出内部 RAM
set -Eeuo pipefail
export PATH="/opt/homebrew/opt/binutils/bin:$PATH"
cd ~/Desktop/lt/RTLPlayground

cp Makefile /tmp/Makefile.orig
grep -n '^CC_FLAGS' Makefile

perl -i -pe 's/^(CC_FLAGS\s*=.*)$/$1 --stack-auto/' Makefile
echo "== 加 --stack-auto 后 =="
grep -n '^CC_FLAGS' Makefile

python3 ~/set_conns.py 8
rm -rf output/FG_4GT_2SX_V2_0
bash ~/build_local.sh > /tmp/sa.log 2>&1
echo "构建退出码: $?"
grep -E "ASlink-Error" /tmp/sa.log | head -5

if ls output/FG_4GT_2SX_V2_0/*.bin >/dev/null 2>&1; then
  echo "✅ --stack-auto + UIP_CONNS=8 编译成功"
  ls -l output/FG_4GT_2SX_V2_0/*.bin
else
  echo "✗ 失败"
  tail -8 /tmp/sa.log
  cp /tmp/Makefile.orig Makefile
  echo "(已还原 Makefile)"
fi
