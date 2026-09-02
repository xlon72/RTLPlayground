#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修正 Makefile 的 OBJCOPY 探测: Homebrew binutils 是 keg-only,
   不在 PATH 里, command -v 找不到, 必须探测显式路径。幂等。"""
import io, re

p = "Makefile"
s = io.open(p, encoding="utf-8").read()

NEW = (
    "# macOS has no GNU objcopy. Homebrew's binutils is keg-only, i.e. NOT\n"
    "# symlinked into the prefix bin/, so `command -v gobjcopy` fails; probe\n"
    "# the known keg locations explicitly before falling back to PATH.\n"
    "OBJCOPY_CANDIDATES := \\\n"
    "  /opt/homebrew/opt/binutils/bin/gobjcopy \\\n"
    "  /usr/local/opt/binutils/bin/gobjcopy \\\n"
    "  $(shell command -v gobjcopy 2>/dev/null) \\\n"
    "  $(shell command -v objcopy 2>/dev/null) \\\n"
    "  $(shell command -v llvm-objcopy 2>/dev/null)\n"
    "OBJCOPY ?= $(firstword $(foreach c,$(OBJCOPY_CANDIDATES),"
    "$(if $(wildcard $(c)),$(c))) objcopy)\n")

pat = re.compile(r"# macOS has no GNU objcopy.*?\nOBJCOPY \?=.*?\n", re.S)
if "OBJCOPY_CANDIDATES" in s:
    print("  = 跳过: 已是新版探测")
elif pat.search(s):
    io.open(p, "w", encoding="utf-8").write(pat.sub(lambda m: NEW, s, count=1))
    print("  ✓ 已替换为显式路径探测")
else:
    print("  ! 未找到旧 OBJCOPY 块, 请确认 Makefile 内容")

# 打印探测结果, 便于确认
s2 = io.open(p, encoding="utf-8").read()
print("\n当前 OBJCOPY 定义:")
for ln in s2.splitlines():
    if "OBJCOPY" in ln or "gobjcopy" in ln:
        print("  " + ln)
