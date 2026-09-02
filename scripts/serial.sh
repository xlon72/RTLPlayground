#!/usr/bin/env bash
# 自动识别 CH341/WCH 串口并启动 miniterm(自动选择, 不询问)
#
# 用法:
#   ~/serial.sh                # 自动选串口, 波特率 115200
#   ~/serial.sh 9600           # 指定波特率
#   ~/serial.sh /dev/cu.xxx    # 直接指定设备
#   ~/serial.sh /dev/cu.xxx 9600
#
# 退出 miniterm: Ctrl-]
set -Eeuo pipefail

BAUD=115200
DEV=""

for a in "$@"; do
  case "$a" in
    /dev/*) DEV="$a" ;;
    [0-9]*) BAUD="$a" ;;
  esac
done

PATTERNS=(
  "/dev/cu.wchusbserial"*
  "/dev/cu.wch"*
  "/dev/cu.usbserial"*
  "/dev/cu.usbmodem"*
  "/dev/cu.SLAB_USBtoUART"*
  "/dev/cu.FTDI"*
)

pick_device() {
  local matches=() seen=" " p d
  for p in "${PATTERNS[@]}"; do
    for d in $p; do
      [ -e "$d" ] || continue
      case "$d" in
        *Bluetooth*) continue ;;
      esac
      # 去重: 多个通配模式会匹配到同一个设备
      case "$seen" in *" $d "*) continue ;; esac
      seen="$seen$d "
      matches+=("$d")
    done
  done

  [ ${#matches[@]} -eq 0 ] && return 1

  # 多个时按设备号降序取最新的一个(CH341 重插后序号递增)
  if [ ${#matches[@]} -gt 1 ]; then
    local best="${matches[0]}" bn=-1 m n
    for m in "${matches[@]}"; do
      n="${m##*[!0-9]}"
      [ -z "$n" ] && n=0
      [ "$n" -gt "$bn" ] && { bn="$n"; best="$m"; }
    done
    echo "找到 ${#matches[@]} 个串口, 自动选最新: $best" >&2
    echo "$best"
    return 0
  fi

  echo "${matches[0]}"
}

if [ -z "$DEV" ]; then
  if ! DEV="$(pick_device)"; then
    echo "✗ 未找到串口设备" >&2
    echo "" >&2
    echo "当前 /dev/cu.* :" >&2
    ls -1 /dev/cu.* 2>/dev/null >&2 || echo "  (无)" >&2
    echo "" >&2
    echo "排查:" >&2
    echo "  1) CH341A 插好了吗" >&2
    echo "  2) 板子上电了吗" >&2
    echo "  3) ls /dev/cu.* | grep -i wch" >&2
    exit 1
  fi
fi

echo "连接: $DEV @ $BAUD   (退出: Ctrl-])"
exec python3 -m serial.tools.miniterm "$DEV" "$BAUD"
