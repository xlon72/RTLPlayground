#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修正 SFP 插槽编号与丝印顺序相反的问题。

现象(实测确认)
--------------
插丝印 5 口(第 1 个 SFP)的模块 -> 网页显示成 "SFP 插槽2"
插丝印 6 口(第 2 个 SFP)的模块 -> 网页显示成 "SFP 插槽1"

根因
----
page_impl.c 里:
    send_sfp_info(0);   // -> sfp_slot_0 -> "SFP 插槽1"
    send_sfp_info(1);   // -> sfp_slot_1 -> "SFP 插槽2"
send_sfp_info() 把参数原样传给 sfp_read_reg(slot, reg), 不做端口换算,
所以"插槽1"的内容取决于 machine.sfp_port[0] 实际接的是哪个物理笼。
FG_4GT_2SX_V2_0 机型里 sfp_port[] 的顺序与机身丝印 5/6 相反。

修法
----
用编译期宏对调索引。纯常量对调, 不新增任何变量, 无 OSEG 风险。
只对 FG_4GT_2SX_V2_0 生效 —— 我们只在这台设备上验证过, 其他机型保持原样。

注意: 本改动是编译期常量, 预处理后宏名即消失, 无法用 grep 二进制验证,
只能上机行为验证(插 SFP1 应显示在"插槽1")。

幂等。在仓库根目录运行。
"""
import io, os, re, sys

REPO = os.path.expanduser("~/Desktop/lt/RTLPlayground")
if os.path.basename(os.getcwd()) != "RTLPlayground" and os.path.isdir(REPO):
    os.chdir(REPO)
if not os.path.exists("httpd/page_impl.c"):
    sys.exit("✗ 请在仓库根目录运行")

p = "httpd/page_impl.c"
s = io.open(p, encoding="utf-8", newline="").read()

MARK = "#define SFP_SLOT_0"
if MARK in s:
    print("  = 跳过: 已改")
else:
    # 1) 在 send_sfp_info 定义之前插入映射宏
    anchor = "void send_sfp_info(uint8_t sfp)"
    if anchor not in s:
        sys.exit("✗ 未定位 send_sfp_info 定义 <<<")

    MACRO = """/* SFP 插槽索引 -> sfp_port[] 索引。
 * FG_4GT_2SX_V2_0: 机身丝印 5/6 两个 SFP 笼的顺序与 machine.sfp_port[]
 * 的索引顺序相反, 导致插第 1 个 SFP 显示成"插槽2"。这里对调。
 * 纯编译期常量, 不增加任何 RAM 占用。 */
#if defined(MACHINE_FG_4GT_2SX_V2_0)
#define SFP_SLOT_0 1
#define SFP_SLOT_1 0
#else
#define SFP_SLOT_0 0
#define SFP_SLOT_1 1
#endif

"""
    s = s.replace(anchor, MACRO + anchor, 1)
    print("  + 插入: SFP_SLOT_0/1 映射宏")

    # 2) 把调用点的字面量换成宏(保留原有缩进)
    n = 0
    out = []
    for ln in s.splitlines(keepends=True):
        body = ln.lstrip()
        ind = ln[:len(ln) - len(body)]
        if body.startswith("send_sfp_info(0);"):
            out.append(ind + "send_sfp_info(SFP_SLOT_0);" + body[len("send_sfp_info(0);"):])
            n += 1
        elif body.startswith("send_sfp_info(1);"):
            out.append(ind + "send_sfp_info(SFP_SLOT_1);" + body[len("send_sfp_info(1);"):])
            n += 1
        else:
            out.append(ln)
    s = "".join(out)
    if n != 2:
        sys.exit("✗ 期望替换 2 处调用, 实际 %d 处 <<<" % n)
    print("  + 替换: send_sfp_info 调用 %d 处 -> 使用映射宏" % n)

    io.open(p, "w", encoding="utf-8", newline="").write(s)

# ------------------------------------------------------------ 自检
print("\n自检:")
s = io.open(p, encoding="utf-8", newline="").read()
checks = [
    ("已插入 SFP_SLOT_0 宏",   "#define SFP_SLOT_0" in s),
    ("已插入 SFP_SLOT_1 宏",   "#define SFP_SLOT_1" in s),
    ("有 FG_4GT_2SX 分支",     "defined(MACHINE_FG_4GT_2SX_V2_0)" in s),
    ("其他机型保持 0/1",       "#else" in s),
    ("调用已用宏",             "send_sfp_info(SFP_SLOT_0);" in s and
                               "send_sfp_info(SFP_SLOT_1);" in s),
    ("无残留字面量调用",       "send_sfp_info(0);" not in s and
                               "send_sfp_info(1);" not in s),
    ("大括号平衡",             s.count("{") == s.count("}")),
]
ok = True
for name, res in checks:
    print("  %-24s %s" % (name, "OK" if res else "失败 <<<"))
    ok = ok and res
print("")
print("✓ 全部通过" if ok else "✗ 存在问题")
