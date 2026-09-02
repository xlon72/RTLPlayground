#!/usr/bin/env bash
set -Eeuo pipefail
cd ~/Desktop/lt/RTLPlayground

# 1. 确保工作区基于干净的 main
git update-index --no-skip-worktree Makefile 2>/dev/null || true
git reset --hard origin/main
git clean -fd

# 2. 移除 update.html 中的残留文本 "update_auto_reboot"
python3 -c '
from pathlib import Path
update_html = Path("html/update.html")
if update_html.exists():
    content = update_html.read_text(encoding="utf-8")
    new_content = content.replace("update_auto_reboot", "")
    update_html.write_text(new_content, encoding="utf-8")
    print("  ✓ 已从 update.html 移除 update_auto_reboot")
'

# 3. 将版本号全局变更为 v0.9.0
find . -type f \( -name "Makefile" -o -name "*.c" -o -name "*.h" -o -name "*.json" \) -exec sed -i '' 's/v0.1.0/v0.9.0/g' {} +
python3 -c '
from pathlib import Path
import re
makefile = Path("Makefile")
content = makefile.read_text(encoding="utf-8")
content = re.sub(r"-v0\.9\.0-\$\(GIT_REV\)[^\n]*", "-v0.9.0", content)
content = re.sub(r"VERSION\s*[:?]?=.*", "VERSION = v0.9.0", content)
makefile.write_text(content, encoding="utf-8")
print("  ✓ Makefile 版本已固化为 v0.9.0")
'

# 4. 重新适配 macOS objcopy 路径并锁定 Makefile
python3 -c '
code = open("Makefile").read()
if "gobjcopy" not in code:
    code = "OBJCOPY ?= /opt/homebrew/opt/binutils/bin/gobjcopy\n" + code.replace("\tobjcopy", "\t$(OBJCOPY)")
    open("Makefile", "w").write(code)
'
git update-index --skip-worktree Makefile

# 5. 编译固件
echo "== 构建 v0.9.0 版本固件 =="
rm -rf output/FG_4GT_2SX_V2_0/*.bin
make MACHINE=FG_4GT_2SX_V2_0 > /tmp/build_v090.log 2>&1

if ls output/FG_4GT_2SX_V2_0/*.bin >/dev/null 2>&1; then
    echo "✅ v0.9.0 编译成功！请执行 bash ~/flash_local.sh 刷入。"
else
    echo "✗ 编译失败，请检查 /tmp/build_v090.log"
    tail -n 10 /tmp/build_v090.log
fi
