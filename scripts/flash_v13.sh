#!/usr/bin/env bash
# RTLPlayground v13 刷写 —— 必须 bash 运行：bash ~/flash_v13.sh <固件目录>
set -Eeuo pipefail

DIR="${1:-$HOME/Downloads/v13fw}"
EXPECT=524288
OUT=/tmp/flash2m.bin

# 1. 找真实固件（-type f 排除 symlink）
FW="$(find "$DIR" -type f -name 'rtlplayground-*.bin' 2>/dev/null | head -n 1 || true)"
if [[ -z "$FW" ]]; then
  FW="$(find "$DIR" -type f -name 'rtlplayground.bin' 2>/dev/null | head -n 1 || true)"
fi
if [[ -z "$FW" || ! -s "$FW" ]]; then
  echo "✗ 没找到真实固件"; find "$DIR" -name '*.bin' -exec ls -l {} \; 2>/dev/null || true; exit 1
fi

# 2. 防呆：尺寸
SZ=$(wc -c < "$FW")
if [[ "$SZ" -ne $EXPECT ]]; then echo "✗ 尺寸 $SZ ≠ $EXPECT"; exit 1; fi

# 3. 防呆：镜像头 = 00 40（预取长度 0x4000）+ LJMP 0x02
#    依据 doc/ghidra.md + tools/imagebuilder.c OFFSET=2
MAGIC="$(head -c 3 "$FW" | xxd -p)"
if [[ "$MAGIC" != "004002" ]]; then
  echo "✗ 镜像头 $MAGIC ≠ 004002（应为 00 40 前缀 + LJMP 0x02）"; exit 1
fi
TARGET="$(head -c 4 "$FW" | xxd -p | cut -c7-8)"
echo "✓ 源固件: $FW"
echo "         $SZ 字节"
echo "         头: 00 40（预取 0x4000）  LJMP 02 → 0x${TARGET}xx"

# 4. 填充成 2MB
perl -e 'print "\xFF" x 2097152' > /tmp/ff.bin
if [[ $(wc -c < /tmp/ff.bin) -ne 2097152 ]]; then echo "✗ 填充块生成失败"; exit 1; fi
cat "$FW" /tmp/ff.bin > /tmp/padded.bin
head -c 2097152 /tmp/padded.bin > "$OUT"

# 5. 合成后再校验一次
if [[ $(wc -c < "$OUT") -ne 2097152 ]]; then echo "✗ 合成尺寸错误"; exit 1; fi
if [[ "$(head -c 3 "$OUT" | xxd -p)" != "004002" ]]; then echo "✗ 合成后镜像头错误"; exit 1; fi
echo "✓ 待刷镜像: $OUT  2097152 字节  头 004002  ← 可刷"

read -rp "确认 CH341A 8 条线已全部脱开 + 板子未上电，回车开刷（Ctrl-C 取消）: " || { echo "已取消"; exit 1; }
sudo flashrom -p ch341a_spi -w "$OUT"
