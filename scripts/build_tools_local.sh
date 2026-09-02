#!/usr/bin/env bash
# macOS 上构建 tools/。argp-standalone 的库名可能是 argp 或 argp-standalone,
# 逐个试, 找到能解析 _argp_usage 的那个。
set -Eeuo pipefail
cd ~/Desktop/lt/RTLPlayground/tools
mkdir -p output

BREW="$(brew --prefix 2>/dev/null || echo /usr/local)"
echo "brew prefix: $BREW"

# --- 定位 argp 库 ---
ARGP_LIB=""
for cand in argp argp-standalone; do
  if [ -f "$BREW/lib/lib${cand}.a" ] || [ -f "$BREW/lib/lib${cand}.dylib" ]; then
    if printf 'int main(void){return 0;}\n' > /tmp/t.c \
       && gcc /tmp/t.c -L"$BREW/lib" -l"$cand" -o /tmp/t 2>/dev/null; then
      ARGP_LIB="-l$cand"
      echo "  ✓ argp 库: lib${cand}"
      break
    fi
  fi
done

# 还没找到就直接按路径链接
if [ -z "$ARGP_LIB" ]; then
  for f in "$BREW"/lib/libargp*.a "$BREW"/Cellar/argp-standalone/*/lib/libargp*.a; do
    [ -f "$f" ] || continue
    if gcc /tmp/t.c "$f" -o /tmp/t 2>/dev/null; then
      ARGP_LIB="$f"
      echo "  ✓ argp 库(路径): $f"
      break
    fi
  done
fi
[ -n "$ARGP_LIB" ] || { echo "  ✗ 未能定位 argp 库"; exit 1; }

build() {
  local src="$1" out="$2"; shift 2
  if gcc "$src" -Wall -I"$BREW/include" -L"$BREW/lib" "$@" -o "$out" 2>/tmp/gcc_err.log; then
    echo "  ✓ $out"
  else
    echo "  ✗ $out"
    tail -6 /tmp/gcc_err.log
  fi
}

echo "== 构建 =="
build fileadder.c      output/fileadder      $ARGP_LIB
build injector.c       output/injector
build crc_calculator.c output/crc_calculator $ARGP_LIB
build imagebuilder.c   output/imagebuilder   $ARGP_LIB

echo "== httpd_sim (仅模拟用) =="
if gcc httpd_sim.c -Wall -o output/httpd_sim -ljson-c 2>/dev/null; then
  echo "  ✓ output/httpd_sim"
else
  printf '#!/bin/sh\nexit 0\n' > output/httpd_sim
  chmod +x output/httpd_sim
  echo "  ~ 打桩 (json-c 不可用, 不影响固件构建)"
fi

echo "== 结果 =="
ls -l output/
