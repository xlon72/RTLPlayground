#!/usr/bin/env bash
# 本地构建固件(不依赖 CI)。
# 版本号: 构建前自动 +1。不要再手动跑 bump_version.sh, 否则会 +2。
#
# 关键: 必须先删 html_data.* 与 output/$MACHINE。
#   HTML 经 fileadder/injector 打包进固件, 跨构建保留的 html_data.c 是
#   元数据索引(仅 3KB), 真正的 HTML 由 injector 写入最终 .bin。
#   曾因此连续三次刷写界面改动无效(版本号却正常递增, 具迷惑性)。
#
# macOS: tools/ 缺 glibc 的 argp.h, 且 Makefile 用裸 gcc(不带 -I/-l),
#   故手工构建后 touch, 让 make 认为已是最新从而跳过重建。
set -Eeuo pipefail
export PATH="/opt/homebrew/opt/binutils/bin:$PATH"
REPO="$HOME/Desktop/lt/RTLPlayground"
MACHINE="FG_4GT_2SX_V2_0"

cd "$REPO" || { echo "✗ 仓库不存在: $REPO"; exit 1; }

echo "== 递增版本号 =="
bash "$HOME/bump_version.sh"

echo "== 强制重新打包 HTML =="
rm -f html_data.c html_data.h
rm -rf output/$MACHINE
echo "  ✓ 已清除 html_data.* 与 output/$MACHINE"

if [ ! -x "$REPO/tools/output/fileadder" ] || [ ! -x "$REPO/tools/output/imagebuilder" ]; then
  echo "== tools 未就绪, 先构建 =="
  bash "$HOME/build_tools_local.sh" || exit 1
fi

cd "$REPO/tools"
touch output/*
echo "  ✓ tools 已置为最新 (跳过 make -C tools)"

cd "$REPO"
echo "== 构建 $MACHINE =="
make MACHINE="$MACHINE" 2>&1 | tail -25

echo ""
echo "== 校验固件内容 =="
BIN="$(ls -t output/$MACHINE/*.bin 2>/dev/null | head -1)"
[ -n "$BIN" ] || { echo "✗ 没找到固件"; exit 1; }
echo "  固件: $(basename "$BIN")"

chk() { # chk "说明" "期望值" "实际值"
  if [ "$3" = "$2" ]; then echo "  ✓ $1: $3"
  else echo "  ✗ $1: 实际 $3 (期望 $2) <<<"; fi
}

# 当前有效的验证项(v5 之后 v3-svg-ready 已被替换, 勿再检查它)
n() { grep -c "$1" "$BIN" 2>/dev/null || echo 0; }
printf "  %-30s %s\n" "v5-direct-refresh(应>0)"  "$(n 'v5-direct-refresh')"
printf "  %-30s %s\n" "refreshInfoTable(应>0)"   "$(n 'refreshInfoTable')"
printf "  %-30s %s\n" "tab-bar padding归零(应>0)" "$(n 'margin-bottom: 0; padding: 0;')"
printf "  %-30s %s\n" "旧损坏path m611(应=0)"     "$(n 'm611')"
printf "  %-30s %s\n" "硬编码中文提示(应=0)"       "$(n '固件上传完成后，交换机将自动校验')"
printf "  %-30s %s\n" "-dirty 后缀(应=0)"         "$(basename "$BIN" | grep -c dirty || true)"
