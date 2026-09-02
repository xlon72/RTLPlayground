#!/usr/bin/env bash
#
# 第一步点我 —— 把备份的辅助脚本恢复到它们原来的位置
#
# 用法: 从 GitHub 拉取本项目后, 双击本文件(或终端执行 bash 本文件)。
# 按 restore_manifest.txt 把 scripts/ 下的脚本复制回 ~/ 各自原位置。
# 若目标已存在同名文件, 先改名为 xxx.bak.<时间戳> 再覆盖, 不会丢失。

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="$SCRIPT_DIR/restore_manifest.txt"

if [ ! -f "$MANIFEST" ]; then
  echo "✗ 找不到清单文件: $MANIFEST"
  echo "  本文件应与 restore_manifest.txt 及备份脚本同在 scripts/ 目录下。"
  exit 1
fi

TS="$(date +%Y%m%d-%H%M%S)"
ok=0; failed=0

echo "=============================================="
echo "  恢复辅助脚本"
echo "  源目录: $SCRIPT_DIR"
echo "  目标:   $HOME"
echo "=============================================="
echo ""

while IFS=$'\t' read -r rel name; do
  [ -z "${rel:-}" ] && continue
  case "$rel" in \#*) continue;; esac
  dest="${rel/#\~/$HOME}"
  src="$SCRIPT_DIR/$name"

  if [ ! -f "$src" ]; then
    echo "  ! 备份缺失: $name"
    failed=$((failed+1))
    continue
  fi

  if [ -f "$dest" ]; then
    mv "$dest" "$dest.bak.$TS"
    echo "  ~ 旧文件留存: $(basename "$dest").bak.$TS"
  fi

  if cp "$src" "$dest" 2>/dev/null; then
    chmod +x "$dest" 2>/dev/null
    echo "  ✓ $(basename "$dest")"
    ok=$((ok+1))
  else
    echo "  ✗ 恢复失败: $name"
    failed=$((failed+1))
  fi
done < "$MANIFEST"

echo ""
echo "=============================================="
echo "  完成: 成功 $ok 个, 失败 $failed 个"
echo "=============================================="
echo ""
echo "  接下来可运行:"
echo "    bash ~/build_local.sh     # 构建固件"
echo "    bash ~/flash_local.sh     # 刷写(CH341A)"
echo ""
echo "  旧文件已改名留存为 *.bak.$TS, 确认无误后可自行删除。"
echo ""
read -r -p "按回车键关闭本窗口..." _

LP_REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LP_MK="$LP_REPO_DIR/Makefile"
if [ -f "$LP_MK" ]; then
    cp -p "$LP_MK" "/tmp/Makefile.bak.$(date +%Y%m%d-%H%M%S)"
    if grep -q '^VERSION=0\.1\.0$' "$LP_MK"; then
        LP_TMP="$(mktemp)"
        sed 's|^VERSION=0\.1\.0$|VERSION = v0.9.7|' "$LP_MK" > "$LP_TMP" && mv "$LP_TMP" "$LP_MK"
        echo "[+] Makefile: VERSION -> v0.9.7"
    fi
    if grep -q '^VERSION_EXTENSION = v[$](VERSION)-[$](GIT_VERSION)$' "$LP_MK"; then
        LP_TMP="$(mktemp)"
        sed 's|^VERSION_EXTENSION = v[$](VERSION)-[$](GIT_VERSION)$|VERSION_EXTENSION = $(VERSION)-$(GIT_VERSION)|' "$LP_MK" > "$LP_TMP" && mv "$LP_TMP" "$LP_MK"
        echo "[+] Makefile: VERSION_EXTENSION 去掉 v 前缀"
    fi
    if grep -q '^VERSION = v0\.9\.7$' "$LP_MK" && grep -q '^VERSION_EXTENSION = [$](VERSION)-[$](GIT_VERSION)$' "$LP_MK"; then
        echo "[OK] Makefile 本地版本改动已就位"
    else
        echo "[!] Makefile 未达预期状态，请手工检查"
    fi
    if git -C "$LP_REPO_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        LP_FLAG="$(git -C "$LP_REPO_DIR" ls-files -v Makefile | grep -v '^H ' || true)"
        if [ -z "$LP_FLAG" ]; then
            git -C "$LP_REPO_DIR" update-index --skip-worktree Makefile
            echo "[+] 已设置 skip-worktree (Makefile)"
        else
            echo "[=] skip-worktree 已存在: $LP_FLAG"
        fi
    fi
else
    echo "[!] 未找到 Makefile: $LP_MK"
fi
