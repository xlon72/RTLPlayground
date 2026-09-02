#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 5 个指针变量本身挪进 xdata, 腾出 DSEG(内部 RAM)。

背景
----
UIP_CONNS=1 时内部 RAM 刚好卡满:
    DSEG 0x00-0x7E  126 字节
    OSEG 0x79-0x7E    6 字节 (REL,OVR 叠在 DSEG 尾)
    SSEG 0x7F-0xFF  129 字节 (栈, 已顶到 0xFF 无后退空间)
UIP_CONNS=2 时 OSEG 需增到 8 字节, 挤不进 DSEG 尾与栈起点之间, 报:
    ?ASlink-Error-Could not get 8 consecutive bytes in internal RAM for area OSEG

原理
----
DSEG 里约 76 字节是 _xxx_PARM_n (sdcc small model 非重入函数的参数静态区,
不可动)。能动的只有下面 5 个真实全局变量。把它们自身挪进 xdata 后 DSEG
缩小, OSEG 起点得以前移, 从而给 OSEG 让出空间。

写法必须注意(sdcc 指针存储类型易搞反):
    __xdata uint8_t *p;    指针变量在 data, 数据在 xdata   <- 不省内部 RAM
    uint8_t * __xdata p;   指针变量本身在 xdata            <- 这个才省
extern 声明要与定义同步改, 否则类型不匹配。

幂等。在仓库根目录运行。
"""
import io, re, sys

log = []
def load(p): return io.open(p, encoding="utf-8").read()
def save(p, s): io.open(p, "w", encoding="utf-8").write(s)

def sub(s, old, new, label):
    if new in s:
        log.append("  = 跳过(已改): " + label); return s, False
    if old not in s:
        log.append("  ! 未找到锚点 <<< " + label); return s, False
    log.append("  + 修改: " + label)
    return s.replace(old, new, 1), True

# (文件, 旧写法, 新写法, 说明)
TARGETS = [
 ("httpd/httpd.c", "__xdata uint8_t *content_type = 0;", "uint8_t * __xdata content_type = 0;",
  "httpd.c: content_type 指针移入 xdata"),
 ("httpd/httpd.c", "__xdata uint8_t *session = 0;", "uint8_t * __xdata session = 0;",
  "httpd.c: session 指针移入 xdata"),
 ("httpd/httpd.c", "__xdata uint8_t *timeptr;", "uint8_t * __xdata timeptr;",
  "httpd.c: timeptr 指针移入 xdata"),
 ("uip/uip.c", "__xdata struct uip_conn *uip_conn;", "struct uip_conn * __xdata uip_conn;",
  "uip.c: uip_conn 指针移入 xdata"),
 ("uip/uip.c", "__xdata struct uip_udp_conn *uip_udp_conn;", "struct uip_udp_conn * __xdata uip_udp_conn;",
  "uip.c: uip_udp_conn 指针移入 xdata"),
 ("uip/uip.h", "extern __xdata struct uip_conn *uip_conn;", "extern struct uip_conn * __xdata uip_conn;",
  "uip.h: uip_conn extern 声明同步"),
 ("uip/uip.h", "extern __xdata struct uip_udp_conn *uip_udp_conn;", "extern struct uip_udp_conn * __xdata uip_udp_conn;",
  "uip.h: uip_udp_conn extern 声明同步"),
]

if not (os.path.isdir("httpd") and os.path.isdir("uip")) if False else True:
    pass
import os
if not (os.path.isdir("httpd") and os.path.isdir("uip")):
    sys.exit("✗ 请在仓库根目录运行")

# 按文件分组处理, 减少读写次数
files = {}
for f, old, new, label in TARGETS:
    files.setdefault(f, []).append((old, new, label))

for f, ops in files.items():
    try:
        s = load(f)
    except IOError:
        log.append("  ! 未找到 %s <<<" % f); continue
    changed = False
    for old, new, label in ops:
        s, c = sub(s, old, new, label)
        changed = changed or c
    if changed:
        save(f, s)

print("\n".join(log))

print("\n自检:")
ok = True
for f, old, new, label in TARGETS:
    s = load(f)
    if new in s:
        print("  OK   %s" % label)
    else:
        print("  FAIL %s <<<" % label); ok = False
# 反向确认: 旧写法不应残留
for f, old, new, label in TARGETS:
    if old in load(f):
        print("  残留旧写法: %s (%s) <<<" % (f, old)); ok = False
print("\n%s" % ("✓ 全部通过" if ok else "✗ 存在问题"))
