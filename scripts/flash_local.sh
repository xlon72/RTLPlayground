#!/usr/bin/env bash
# 刷写本地构建的固件, 并读回逐字节校验。
#
# 两个曾踩过的坑:
#  1) 不要用 `find | head -n 1` 选固件 —— 那是字母序, 会选中旧的。
#     必须按 mtime 取最新(ls -t)。曾因此把 00:37 的旧固件当成 01:44
#     的新构建刷进去。
#  2) 不要用 `cat a b | head -c N` 合成 —— head 提前关管道会让 cat 收到
#     SIGPIPE(141), 在 set -o pipefail 下脚本静默退出。填充块直接生成到
#     精确大小即可。
set -Eeuo pipefail
MACHINE="FG_4GT_2SX_V2_0"
REPO="$HOME/Desktop/lt/RTLPlayground"
EXPECT=524288
TOTAL=2097152
PAD=$((TOTAL - EXPECT))
OUT=/tmp/flash2m_local.bin
READBACK=/tmp/readback_local.bin

cd "$REPO" || { echo "✗ 仓库不存在"; exit 1; }

# 按修改时间取最新的一个固件
FW="$(ls -t output/$MACHINE/*.bin 2>/dev/null | head -n 1 || true)"
[ -n "$FW" ] && [ -s "$FW" ] || { echo "✗ 没找到固件, 先跑 bash ~/build_local.sh"; exit 1; }

SZ=$(wc -c < "$FW")
[ "$SZ" -eq $EXPECT ] || { echo "✗ 尺寸 $SZ ≠ $EXPECT"; exit 1; }
MAGIC="$(head -c 3 "$FW" | xxd -p)"
[ "$MAGIC" = "004002" ] || { echo "✗ 镜像头 $MAGIC ≠ 004002"; exit 1; }
echo "✓ 源固件: $FW"
echo "          ($SZ 字节, 头 004002, $(date -r "$FW" '+%m-%d %H:%M'))"

perl -e "print \"\\xFF\" x $PAD" > /tmp/ff_pad.bin
[ "$(wc -c < /tmp/ff_pad.bin)" -eq $PAD ] || { echo "✗ 填充块大小错误"; exit 1; }
cat "$FW" /tmp/ff_pad.bin > "$OUT"
[ "$(wc -c < "$OUT")" -eq $TOTAL ] || { echo "✗ 合成尺寸错误"; exit 1; }
[ "$(head -c 3 "$OUT" | xxd -p)" = "004002" ] || { echo "✗ 合成后镜像头错误"; exit 1; }
echo "✓ 待刷镜像: $OUT  $TOTAL 字节  头 004002"

read -rp "确认 CH341A 8 条线已全部脱开 + 板子未上电, 回车开刷(Ctrl-C 取消): " || { echo "已取消"; exit 1; }

echo ""
echo "== 写入 =="
sudo flashrom -p ch341a_spi -w "$OUT"

echo ""
echo "== 读回校验 =="
rm -f "$READBACK"
sudo flashrom -p ch341a_spi -r "$READBACK"
[ -s "$READBACK" ] || { echo "✗ 读回失败"; exit 1; }
RSZ=$(wc -c < "$READBACK")
[ "$RSZ" -eq $TOTAL ] || { echo "✗ 读回尺寸 $RSZ ≠ $TOTAL"; exit 1; }

if cmp -s "$OUT" "$READBACK"; then
  echo "✅ 校验通过: 芯片内容与待刷镜像完全一致"
else
  echo "✗ 校验失败: 芯片内容与镜像不一致 <<<"
  echo "  差异位置(前 5 处):"
  cmp -l "$OUT" "$READBACK" 2>/dev/null | head -5 || true
  exit 1
fi
