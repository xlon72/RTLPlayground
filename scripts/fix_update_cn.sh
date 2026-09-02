#!/usr/bin/env bash
set -Eeuo pipefail
cd ~/Desktop/lt/RTLPlayground

python3 -c '
from pathlib import Path
p = Path("html/update.html")
if p.exists():
    content = p.read_text(encoding="utf-8")
    old_text = "Once the upload finishes the switch verifies the image and reboots into it automatically. Do not power it off during that time."
    new_text = "固件上传完成后，交换机将自动校验镜像并重启。在此期间请勿断电。"
    if old_text in content:
        content = content.replace(old_text, new_text)
    else:
        # 如果英文已被翻译或移除，尝试在合适位置直接追加中文提示
        content = content.replace("</div>", f"<div style=\"color:#666;margin-top:10px;\">{new_text}</div>\n</div>", 1)
    p.write_text(content, encoding="utf-8")
    print("  ✓ update.html 提示已修改为中文")
'

# 重新编译并刷写
rm -rf output/FG_4GT_2SX_V2_0/*.bin
make MACHINE=FG_4GT_2SX_V2_0
rm -f output/rtlplayground.bin
ln -sf FG_4GT_2SX_V2_0/rtlplayground-v0.9.0-FG_4GT_2SX_V2_0.bin output/rtlplayground.bin
