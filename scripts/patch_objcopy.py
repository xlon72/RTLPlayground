#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Makefile: objcopy 改为自动探测 gobjcopy/objcopy(llvm-objcopy)。
   macOS 无 GNU objcopy, Homebrew binutils 提供 gobjcopy。
   幂等。会先备份为 Makefile.bak。"""
import io, os, shutil

p = "Makefile"
s = io.open(p, encoding="utf-8").read()

if "OBJCOPY ?=" in s:
    print("  = 跳过: 已改过")
    raise SystemExit(0)

shutil.copy(p, p + ".bak")
print("  ✓ 已备份 Makefile.bak")

lines = s.splitlines(keepends=True)
out = []
inserted = False
for ln in lines:
    # 在首个非注释非空行前插入探测块
    if not inserted and ln.strip() and not ln.lstrip().startswith("#"):
        out.append(
            "# macOS has no GNU objcopy; Homebrew binutils provides gobjcopy.\n"
            "OBJCOPY ?= $(shell command -v gobjcopy 2>/dev/null \\\n"
            "             || command -v objcopy 2>/dev/null \\\n"
            "             || command -v llvm-objcopy 2>/dev/null \\\n"
            "             || echo objcopy)\n\n")
        inserted = True
    out.append(ln)

s2 = "".join(out)
n = s2.count("\tobjcopy ")
s2 = s2.replace("\tobjcopy ", "\t$(OBJCOPY) ")
if n == 0:
    print("  ! 未找到 objcopy 调用, 请检查 Makefile")
else:
    io.open(p, "w", encoding="utf-8").write(s2)
    print("  ✓ 替换 %d 处 objcopy -> $(OBJCOPY)" % n)
