#!/usr/bin/env bash
# Makefile 的 VERSION 末位 +1:  v0.9.0 -> v0.9.1
# macOS sed 需要 -i ''
set -Eeuo pipefail
cd ~/Desktop/lt/RTLPlayground

CUR="$(grep -m1 -E '^VERSION[[:space:]]*=' Makefile \
      | sed -E 's/^VERSION[[:space:]]*=[[:space:]]*//')"

if [[ ! "$CUR" =~ ^(v?)([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
  echo "✗ 无法解析版本号: $CUR"
  exit 1
fi

P="${BASH_REMATCH[1]}"; MAJ="${BASH_REMATCH[2]}"
MI="${BASH_REMATCH[3]}";  PA="${BASH_REMATCH[4]}"
NEW="${P}${MAJ}.${MI}.$((PA + 1))"

sed -i '' -E "s|^VERSION[[:space:]]*=.*|VERSION = ${NEW}|" Makefile
echo "✓ 版本号: ${CUR} -> ${NEW}"
grep -n '^VERSION' Makefile
