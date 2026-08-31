#!/bin/bash
# flashver.sh - 一键推送指定版本的固件源码并监视编译
#
# 用法:
#   ./flashver.sh v4        # 推送 v4 并实时看编译日志
#   ./flashver.sh slim      # 推送兜底版
#
# 前置: 把 <版本>_rtl837x_flash.c / .h / _rtlplayground.c 三个文件放进 ~/Downloads/
set -e

VER="$1"
REPO="$HOME/Desktop/lt/RTLPlayground"

if [ -z "$VER" ]; then
    echo "用法: $0 <版本名>    例如: $0 v4"
    exit 1
fi

cd "$REPO" || { echo "找不到仓库 $REPO"; exit 1; }

for suffix in "_rtl837x_flash.c" "_rtl837x_flash.h" "_rtlplayground.c"; do
    src="$HOME/Downloads/${VER}${suffix}"
    [ -f "$src" ] || { echo "缺少文件: $src"; exit 1; }
done

cp "$HOME/Downloads/${VER}_rtl837x_flash.c"    rtl837x_flash.c
cp "$HOME/Downloads/${VER}_rtl837x_flash.h"    rtl837x_flash.h
cp "$HOME/Downloads/${VER}_rtlplayground.c"    rtlplayground.c

echo "=== 覆盖完成，校验和 ==="
shasum -a 256 rtl837x_flash.c rtl837x_flash.h rtlplayground.c

# 没有改动就别浪费一次 Actions
if git diff --quiet; then
    echo "文件内容与上次相同，跳过提交"
else
    git add -A
    git commit -m "flash diagnostics ${VER}"
    git push origin main
fi

echo "=== 开始监视编译 ==="
gh run watch
