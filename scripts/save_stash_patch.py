#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 stash@{0} 归档成带说明的 patch, 放进 scripts/ 一起备份。

原因: 该 stash 是 UIP_CONNS=8 的试验性改动, 已验证不可行(设备内部 RAM
仅 256 字节, 撑不住 8 个连接), 故不应用回代码; 但作为"此路不通"的记录
有保留价值, 免得日后重复尝试。

生成的 patch 文件开头会写入结论说明。
"""
import io, os, subprocess, sys

REPO = os.path.expanduser("~/Desktop/lt/RTLPlayground")
if os.path.basename(os.getcwd()) != "RTLPlayground" and os.path.isdir(REPO):
    os.chdir(REPO)

DEST = os.path.join(REPO, "scripts")
os.makedirs(DEST, exist_ok=True)
OUT = os.path.join(DEST, "uip_conns_8_experiment.patch")

r = subprocess.run(["git", "stash", "show", "-p", "stash@{0}"],
                   capture_output=True, text=True)
if r.returncode != 0 or not r.stdout.strip():
    sys.exit("✗ 读取 stash 失败: %s" % (r.stderr or "内容为空"))

body = r.stdout
stat = subprocess.run(["git", "stash", "show", "--stat", "stash@{0}"],
                      capture_output=True, text=True).stdout.strip()

HEADER = """# UIP_CONNS=8 试验性改动 —— 已验证不可行, 勿应用
#
# 结论: 该改动会让设备内部 RAM 溢出(OSEG)。这台设备的内部 RAM 只有
#       256 字节, 即便把 UIP_CONNS 从 8 降到 2 也腾不出足够空间, 更
#       不用说 8 个连接所需的连接结构体。
#
# 历史: 曾尝试多种手段(栈自动变量、覆盖段调整、连接数下调等)均无法
#       满足; 相关 commit 已被 revert。此处仅作记录, 避免日后重复尝试。
#
# 用法(仅供查阅):  git apply scripts/uip_conns_8_experiment.patch
# 警告:            应用后固件大概率无法正常运行
#
# 原始 stat:
# %s
#
# ---------------------------------------------------------------

""" % stat.replace("\n", "\n# ")

io.open(OUT, "w", encoding="utf-8", newline="\n").write(HEADER + body)
print("  ✓ 已归档: scripts/uip_conns_8_experiment.patch")
print("  原始 stat:")
for ln in stat.splitlines():
    print("    " + ln)
print("\n  该 stash 未应用, 仍保留在 git stash 中。")
