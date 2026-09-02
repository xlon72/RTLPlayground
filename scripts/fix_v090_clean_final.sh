#!/usr/bin/env bash
set -Eeuo pipefail
cd ~/Desktop/lt/RTLPlayground

# 1. 解除 Makefile 锁定并恢复干净状态
git update-index --no-skip-worktree Makefile 2>/dev/null || true
git checkout --force HEAD -- Makefile html/update.html

# 2. 彻底清理 update.html 中的残留提示文本与空行
python3 -c '
from pathlib import Path
p = Path("html/update.html")
if p.exists():
    content = p.read_text(encoding="utf-8")
    # 移除 update_auto_reboot 及其所在的整行 div 或标签
    content = content.replace("update_auto_reboot", "")
    # 移除英文提示长句
    content = content.replace("Once the upload finishes the switch verifies the image and reboots into it automatically. Do not power it off during that time.", "")
    p.write_text(content, encoding="utf-8")
    print("  ✓ update.html 已彻底清理干净")
'

# 3. 直接修改 Makefile，将版本写死为纯净的 v0.9.0（彻底解决 vv 前缀和 dirty 后缀）
python3 -c '
from pathlib import Path
mf = Path("Makefile")
lines = mf.read_text(encoding="utf-8").splitlines()
new_lines = []
for line in lines:
    if line.startswith("VERSION"):
        new_lines.append("VERSION = v0.9.0")
    elif "v$(VERSION)" in line:
        new_lines.append(line.replace("v$(VERSION)", "$(VERSION)"))
    else:
        new_lines.append(line)
mf.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
print("  ✓ Makefile 版本已硬编码为 v0.9.0")
'

# 4. 重新适配 macOS objcopy 路径并加锁 Makefile
python3 -c '
content = open("Makefile").read()
if "gobjcopy" not in content:
    content = "OBJCOPY ?= /opt/homebrew/opt/binutils/bin/gobjcopy\n" + content.replace("\tobjcopy", "\t$(OBJCOPY)")
    open("Makefile", "w").write(content)
'
git update-index --skip-worktree Makefile

# 5. 清理旧产物并重新编译
rm -rf output/FG_4GT_2SX_V2_0/*.bin
make MACHINE=FG_4GT_2SX_V2_0

if ls output/FG_4GT_2SX_V2_0/rtlplayground-v0.9.0-FG_4GT_2SX_V2_0.bin >/dev/null 2>&1; then
    echo "✅ 完美版 v0.9.0 固件构建成功！"
    echo "产物路径: output/FG_4GT_2SX_V2_0/rtlplayground-v0.9.0-FG_4GT_2SX_V2_0.bin"
else
    echo "✗ 构建产物未找到，现有的 bin 文件："
    ls -l output/FG_4GT_2SX_V2_0/*.bin
fi
