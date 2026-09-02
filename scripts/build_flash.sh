#!/usr/bin/env bash
# RTLPlayground 一键: 等 CI -> 自动取 run id -> 校验 -> 下载 -> 防呆 -> 刷写
# 用法: bash ~/build_flash.sh [固件下载目录] [仓库路径]
set -Eeuo pipefail

REPO="xlon72/RTLPlayground"
REPO_DIR="${2:-$HOME/Desktop/lt/RTLPlayground}"
DIR="${1:-$HOME/Downloads/uifw}"
EXPECT=524288
OUT=/tmp/flash2m.bin
MAXWAIT=40          # 40 次 x 10 秒 ≈ 6 分钟

command -v gh >/dev/null 2>&1 || { echo "✗ 未找到 gh"; exit 1; }

cd "$REPO_DIR" 2>/dev/null || { echo "✗ 仓库目录不存在: $REPO_DIR"; exit 1; }
git rev-parse --git-dir >/dev/null 2>&1 || { echo "✗ 不是 git 仓库: $REPO_DIR"; exit 1; }
echo "仓库: $REPO_DIR"

# ---- 1. 等 CI: 轮询本地 HEAD 对应的 run ----
HEAD_SHA="$(git rev-parse HEAD)"
echo "本地 HEAD: ${HEAD_SHA:0:12}"
echo "等待该 commit 的 CI 完成（最多 $((MAXWAIT*10/60)) 分钟）..."

RUN_ID=""; CONC=""
for i in $(seq 1 $MAXWAIT); do
  J="$(gh api "repos/$REPO/actions/runs?head_sha=$HEAD_SHA&per_page=1" 2>/dev/null || echo '{}')"
  read -r ST CC ID < <(printf '%s' "$J" | python3 -c '
import sys, json
try:
    r = (json.load(sys.stdin).get("workflow_runs") or [{}])[0]
    print(r.get("status",""), r.get("conclusion",""), r.get("id",""))
except Exception:
    print("", "", "")' 2>/dev/null)
  if [ -n "$ID" ] && [ "$ST" = "completed" ]; then
    RUN_ID="$ID"; CONC="$CC"; break
  fi
  printf "  [%2d] %s\n" "$i" "${ST:-尚未注册}"
  sleep 10
done

# ---- 2. 校验 ----
if [ -z "$RUN_ID" ]; then
  echo "✗ 超时: 未找到 HEAD ${HEAD_SHA:0:12} 的已完成构建"
  echo "  手动触发: gh workflow run build.yml --ref main"
  exit 1
fi
echo "run id: $RUN_ID   conclusion: ${CONC:-未知}"
if [ "$CONC" != "success" ]; then
  echo "✗ 构建未成功，拒绝刷写"
  echo "  查看日志: gh run view $RUN_ID --log-failed"
  exit 1
fi

# ---- 3. 下载 ----
echo "== 下载 run $RUN_ID -> $DIR =="
rm -rf "$DIR"
gh run download "$RUN_ID" --dir "$DIR"
find "$DIR" -name '*.bin' -exec ls -l {} \;

# ---- 4. 定位真实固件(-type f 排除 symlink) ----
FW="$(find "$DIR" -type f -name 'rtlplayground-*.bin' 2>/dev/null | head -n 1 || true)"
[ -n "$FW" ] || FW="$(find "$DIR" -type f -name 'rtlplayground.bin' 2>/dev/null | head -n 1 || true)"
if [ -z "$FW" ] || [ ! -s "$FW" ]; then
  echo "✗ 没找到真实固件（目录里可能只有断裂 symlink）"; exit 1
fi

# ---- 5. 防呆: 尺寸 + 镜像头 ----
SZ=$(wc -c < "$FW")
[ "$SZ" -eq $EXPECT ] || { echo "✗ 尺寸 $SZ ≠ $EXPECT（Makefile IMAGESIZE）"; exit 1; }
MAGIC="$(head -c 3 "$FW" | xxd -p)"
[ "$MAGIC" = "004002" ] || { echo "✗ 镜像头 $MAGIC ≠ 004002（00 40 前缀 + LJMP 0x02）"; exit 1; }
echo "✓ 源固件: $FW"
echo "         $SZ 字节，头 004002（LJMP → 0x$(head -c 4 "$FW" | xxd -p | cut -c7-8)xx）"

# ---- 6. 合成 2MB ----
perl -e 'print "\xFF" x 2097152' > /tmp/ff.bin
[ "$(wc -c < /tmp/ff.bin)" -eq 2097152 ] || { echo "✗ 填充块生成失败"; exit 1; }
cat "$FW" /tmp/ff.bin > /tmp/padded.bin
head -c 2097152 /tmp/padded.bin > "$OUT"

[ "$(wc -c < "$OUT")" -eq 2097152 ] || { echo "✗ 合成尺寸错误"; exit 1; }
[ "$(head -c 3 "$OUT" | xxd -p)" = "004002" ] || { echo "✗ 合成后镜像头错误"; exit 1; }
echo "✓ 待刷镜像: $OUT  2097152 字节  头 004002  ← 可刷"

# ---- 7. 人工确认后刷写 ----
read -rp "确认 CH341A 8 条线已全部脱开 + 板子未上电，回车开刷（Ctrl-C 取消）: " || { echo "已取消"; exit 1; }
sudo flashrom -p ch341a_spi -w "$OUT"
