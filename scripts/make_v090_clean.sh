#!/usr/bin/env bash
set -Eeuo pipefail
cd ~/Desktop/lt/RTLPlayground

# 1. 回退到干净状态
git reset --hard origin/main
git clean -fd

# 2. 清除 update.html 中的残留占位符
python3 -c '
from pathlib import Path
p = Path("html/update.html")
p.write_text(p.read_text(encoding="utf-8").replace("update_auto_reboot", ""), encoding="utf-8")
print("  ✓ 已从 update.html 彻底清除 update_auto_reboot")
'

# 3. 将版本号干净地设定为 v0.9.0
python3 -c '
from pathlib import Path
mf = Path("Makefile")
content = mf.read_text(encoding="utf-8")
content = content.replace("v0.1.0", "v0.9.0")
import re
content = re.sub(r"^VERSION\s*=.*", "VERSION = v0.9.0", content, flags=re.MULTILINE)
mf.write_text(content, encoding="utf-8")
print("  ✓ Makefile 版本已设定为 v0.9.0")
'

# 4. 适配 macOS objcopy 路径并重新锁定
python3 -c '
content = open("Makefile").read()
if "gobjcopy" not in content:
    content = "OBJCOPY ?= /opt/homebrew/opt/binutils/bin/gobjcopy\n" + content.replace("\tobjcopy", "\t$(OBJCOPY)")
    open("Makefile", "w").write(content)
'
git update-index --skip-worktree Makefile

# 5. 编译固件
rm -rf output/FG_4GT_2SX_V2_0/*.bin
make MACHINE=FG_4GT_2SX_V2_0

if ls output/FG_4GT_2SX_V2_0/rtlplayground-v0.9.0-FG_4GT_2SX_V2_0.bin >/dev/null 2>&1; then
    echo "✅ v0.9.0 固件构建成功！"
    echo "产物路径: output/FG_4GT_2SX_V2_0/rtlplayground-v0.9.0-FG_4GT_2SX_V2_0.bin"
else
    echo "✗ 构建产物未找到，现有的 bin 文件："
    ls -l output/FG_4GT_2SX_V2_0/*.bin
fi
