#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描 ~/ 下需要备份的辅助脚本(只列出, 不复制)。"""
import os, glob

HOME = os.path.expanduser("~")
EXCLUDE = {
    ".bash_profile", ".bashrc", ".zshrc", ".zprofile", ".profile",
    ".pythonstartup",
}

def scan():
    found = []
    for name in ("bump_version.sh", "build_local.sh",
                 "build_tools_local.sh", "flash_local.sh"):
        p = os.path.join(HOME, name)
        if os.path.isfile(p):
            found.append(p)
    for pat in ("fix_*.py", "scan_scripts.py", "*.sh"):
        for p in sorted(glob.glob(os.path.join(HOME, pat))):
            if not os.path.isfile(p):
                continue
            if os.path.basename(p) in EXCLUDE:
                continue
            if p not in found:
                found.append(p)
    return found

files = scan()
print("候选脚本 %d 个(位于 %s):\n" % (len(files), HOME))
for p in files:
    print("  %-32s %7d 字节" % (os.path.basename(p), os.path.getsize(p)))
print("")
print("其中已知重要的:")
for k in ("build_local.sh", "build_tools_local.sh", "flash_local.sh",
          "bump_version.sh"):
    mark = "有" if os.path.isfile(os.path.join(HOME, k)) else "缺失 <<<"
    print("  %-24s %s" % (k, mark))
print("\nfix_*.py 补丁脚本: %d 个" % len(glob.glob(os.path.join(HOME, "fix_*.py"))))
