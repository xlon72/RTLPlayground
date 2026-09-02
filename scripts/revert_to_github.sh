#!/usr/bin/env bash
set -Eeuo pipefail
cd ~/Desktop/lt/RTLPlayground

echo "== 1. 清理本地改动，硬回退到 GitHub 版本 =="
# 暂时解除保护，强制与云端同步
git update-index --no-skip-worktree Makefile 2>/dev/null || true
git fetch origin
git reset --hard origin/main
git clean -fd

echo "== 2. 自动适配 macOS 编译环境 =="
python3 -c '
import os
code = open("Makefile").read()
if "gobjcopy" not in code:
    code = "OBJCOPY ?= /opt/homebrew/opt/binutils/bin/gobjcopy\n" + code.replace("\tobjcopy", "\t$(OBJCOPY)")
    open("Makefile", "w").write(code)
    print("  ✓ Makefile 已重新注入 macOS objcopy 路径")
'
# 重新锁定 Makefile 防止推送到云端
git update-index --skip-worktree Makefile

echo "== 3. 重新构建 GitHub 稳定版 =="
rm -rf output/FG_4GT_2SX_V2_0/*.bin
make MACHINE=FG_4GT_2SX_V2_0 > /tmp/build_revert.log 2>&1

if ls output/FG_4GT_2SX_V2_0/*.bin >/dev/null 2>&1; then
    echo "✅ 回退编译成功！请执行 bash ~/flash_local.sh 刷入。"
else
    echo "✗ 编译失败，请检查 /tmp/build_revert.log"
fi
