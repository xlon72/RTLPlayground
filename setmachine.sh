#!/bin/bash
#
# setmachine.sh — 一键切换 RTLPlayground 编译机型
#
# 用法:
#   ./setmachine.sh FG_4GT_2SX_V2_0      # 切换到完全匹配本板的机型
#   ./setmachine.sh HI_K0402WS           # 切回当前能跑的机型
#   ./setmachine.sh                      # 不带参数 = 只列出所有合法机型
#
# 流程: 校验机型名 -> 改 build.yml -> 提交推送 -> 轮询 Actions -> 下载固件 -> 填充 2MB
#
set -u

REPO="$HOME/Desktop/lt/RTLPlayground"
YML="$REPO/.github/workflows/build.yml"
FLASH_MB=2
FLASH_BYTES=$((FLASH_MB * 1024 * 1024))

cd "$REPO" 2>/dev/null || { echo "找不到仓库: $REPO"; exit 1; }
[ -f "$YML" ] || { echo "找不到工作流: $YML"; exit 1; }

# 从 machine.c 提取全部合法机型。
# 注意: 必须扫 machine.c 而不是 machine.h —— machine.c 里既有
#   #ifdef MACHINE_XXX / #elif defined MACHINE_XXX
# 也有
#   #elif defined(MACHINE_XXX) || defined(MACHINE_YYY)
# 后者里的 YYY 是别名（如 HI_K0402WS 是 PCB_K0402WS_V3 的别名），
# machine.h 中并不存在，但完全可以正常编译。
list_machines() {
    grep -oE '(ifdef[[:space:]]+MACHINE_[A-Za-z0-9_]+|defined[[:space:]]*\(?[[:space:]]*MACHINE_[A-Za-z0-9_]+)' machine.c \
        | sed -E 's/^(ifdef[[:space:]]+|defined[[:space:]]*\(?[[:space:]]*)MACHINE_//' \
        | sort -u
}

# ---- 无参数: 只列出合法机型 ----
if [ $# -lt 1 ]; then
    echo "machine.c 中的合法机型:"
    echo
    list_machines
    echo
    echo "当前 build.yml 使用:"
    grep -o 'MACHINE="[^"]*"' "$YML"
    exit 0
fi

MACHINE="$1"

# ---- 1. 校验机型名是否合法 ----
if ! list_machines | grep -qx "$MACHINE"; then
    echo "错误: machine.c 中没有 MACHINE_${MACHINE}"
    echo
    echo "合法机型:"
    list_machines
    exit 1
fi
echo "==> 机型校验通过: MACHINE_${MACHINE}"

# ---- 2. 改 build.yml ----
sed -i.bak "s/MACHINE=\"[^\"]*\"/MACHINE=\"${MACHINE}\"/g" "$YML"
rm -f "$YML.bak"
echo "==> build.yml 已更新:"
grep -o 'MACHINE="[^"]*"' "$YML"

# ---- 3. 提交推送（无改动则跳过）----
if git diff --quiet -- "$YML"; then
    echo "==> build.yml 无变化，跳过提交推送"
else
    git add "$YML"
    git commit -q -m "build ${MACHINE}"
    echo "==> 已提交，推送中..."
    git push origin main || { echo "推送失败"; exit 1; }
fi

# ---- 4. 轮询 Actions ----
echo
echo "==> 等待 GitHub Actions 编译（最多 3 分钟）..."
sleep 15

DBID=""
RESULT=""
for i in $(seq 1 34); do
    LINE=$(gh run list --limit 1 --json databaseId,status,conclusion 2>/dev/null | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)[0]
    print('%s|%s|%s' % (d['databaseId'], d['status'], d['conclusion'] or '?'))
except Exception:
    print('')
" 2>/dev/null)

    STATUS=$(echo "$LINE" | cut -d'|' -f2)
    RESULT=$(echo "$LINE" | cut -d'|' -f3)
    DBID=$(echo "$LINE" | cut -d'|' -f1)

    if [ "$STATUS" = "completed" ] && [ -n "$DBID" ]; then
        break
    fi
    printf "."
    sleep 5
done

echo
if [ "$RESULT" != "success" ]; then
    echo "=========================================="
    echo " 编译失败 (${RESULT:-超时})"
    echo "=========================================="
    echo
    [ -n "$DBID" ] && gh run view "$DBID" --log-failed 2>&1 | grep -E "Error|error:" | head -15
    exit 1
fi

echo "=========================================="
echo " 编译成功"
echo "=========================================="
echo

# ---- 5. 下载固件 ----
OUTDIR="$HOME/Downloads/firmware-${MACHINE}"
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

if ! (cd "$OUTDIR" && gh run download "$DBID" 2>/dev/null); then
    echo "下载失败，手动执行: gh run download $DBID"
    exit 1
fi

# 找到下载的 bin
BIN=$(find "$OUTDIR" -name '*.bin' -type f | head -1)
[ -n "$BIN" ] || { echo "在 $OUTDIR 中没找到 .bin 文件"; exit 1; }

echo "==> 固件: $BIN ($(wc -c < "$BIN" | tr -d ' ') 字节)"

# ---- 6. 填充到 2MB (0xFF) ----
python3 - "$BIN" "$OUTDIR/flash2m.bin" "$FLASH_BYTES" <<'PY'
import sys
src, dst, total = sys.argv[1], sys.argv[2], int(sys.argv[3])
data = open(src, 'rb').read()
if len(data) > total:
    print("错误: 固件 %d 字节超过 flash 容量 %d" % (len(data), total))
    sys.exit(1)
img = bytearray(b'\xff' * total)
img[:len(data)] = data
open(dst, 'wb').write(bytes(img))
print("==> 已填充: %d -> %d 字节 (填充 0xFF)" % (len(data), total))
PY

echo
echo "=========================================="
echo " 就绪，刷写命令:"
echo
echo "   sudo flashrom -p ch341a_spi -w $OUTDIR/flash2m.bin"
echo
echo " 刷完: 拔掉 CH341A -> 交换机上电 -> 串口 115200"
echo "=========================================="
