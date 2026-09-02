#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Makefile: 把裸 objcopy 换成 $(OBJCOPY), 并加一行默认探测。
   刻意用最简语法(避免 foreach/wildcard 续行陷阱)。OBJCOPY 可用
   命令行覆盖: make OBJCOPY=/path/to/gobjcopy ...
   幂等。"""
import io, shutil

p = "Makefile"
s = io.open(p, encoding="utf-8").read()

# 1) 还原: 若存在旧探测块则整段删除(按标记行定位, 不用正则跨行)
lines = s.splitlines(keepends=True)
keep, skipping = [], False
for ln in lines:
    if ln.startswith("OBJCOPY_CANDIDATES"):
        skipping = True
        continue
    if skipping:
        # 探测块结束于最后一个非空行(即 OBJCOPY ?= 那行)
        if ln.strip() and not ln.startswith(" "):
            skipping = False
        continue
    if ln.startswith("OBJCOPY ?="):
        continue
    if ln.startswith("# macOS has no GNU objcopy"):
        continue
    if ln.startswith("# symlinked into the prefix bin/"):
        continue
    if ln.startswith("# the known keg locations"):
        continue
    keep.append(ln)
s = "".join(keep)

# 2) 插入单行默认值(放在首个非注释非空行之前)
if "OBJCOPY ?=" not in s:
    if not shutil.os.path.exists(p + ".bak"):
        shutil.copy(p, p + ".bak")
        print("  ✓ 已备份 Makefile.bak")
    out, inserted = [], False
    for ln in s.splitlines(keepends=True):
        if not inserted and ln.strip() and not ln.lstrip().startswith("#"):
            out.append("# macOS: no GNU objcopy; Homebrew binutils is keg-only.\n")
            out.append("OBJCOPY ?= /opt/homebrew/opt/binutils/bin/gobjcopy\n\n")
            inserted = True
        out.append(ln)
    s = "".join(out)
    print("  ✓ 插入 OBJCOPY 默认值")

# 3) 调用处替换
n = s.count("\tobjcopy ")
if n:
    s = s.replace("\tobjcopy ", "\t$(OBJCOPY) ")
    print("  ✓ 替换 %d 处 objcopy -> $(OBJCOPY)" % n)
else:
    print("  ? 未发现裸 objcopy 调用(可能已替换)")

io.open(p, "w", encoding="utf-8").write(s)
print("\nOBJCOPY 相关行:")
for ln in s.splitlines():
    if "OBJCOPY" in ln:
        print("  " + ln)
