#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连接池: UIP_CONNS 1 -> 8, 并把跨事件的续传状态搬进每连接 appstate。

背景
----
UIP_CONF_MAX_CONNECTIONS=1 时, 浏览器开的 6 条并行连接里 5 条被丢弃,
请求要等 SYN 重传超时(秒级)才重试 —— 这是页面卡顿、导航条加载不出来的根因。

但直接把 UIP_CONNS 改大不行: outbuf / slen / o_idx / cont_len / cont_addr
全是全局量, 且 do_send 在响应超过一个 MSS 时会把剩余字节留在 outbuf 里
跨事件等 ACK。另一个连接一进 handle_input() 就覆盖 outbuf, 发出去的是
别人的数据。outbuf 有 2500 字节, 做不成每连接一份。

解法
----
首块只发「响应头 + 填满一个 MSS」, 剩余数据一律按 (cont_addr, cont_len)
从 flash 重读。于是:
  * outbuf 只在单次 appcall 内使用, 不再跨事件;
  * slen / o_idx 退化成单次调用的临时量, 无需搬进 appstate;
  * 真正需要每连接保存的只有 cont_len / cont_addr (+ 重传用的 tx_*)。

顺带修两个既有 bug:
  * page_impl.c send_config(): cont_addr = valid_len 写的是字节数而非
    flash 地址, config 一旦超阈值, 续传就会从错误地址读数据。
  * send_l2() / send_vlanlist() 的截断上限用 TCP_OUTBUF_SIZE(2500),
    大于 MSS(约 1946), 会触发 outbuf 续传。改成按 uip_mss() 截断。

不新增任何函数局部变量: 内部 RAM 已满, 新增局部量会触发
?ASlink-Error ... area OSEG。appstate 位于 xdata(uip_conns 是 __xdata)。

幂等: 重复运行打印"跳过"。在仓库根目录运行。
"""
import io, os, re, sys

log = []
def load(p): return io.open(p, encoding="utf-8").read()
def save(p, s): io.open(p, "w", encoding="utf-8").write(s)

def sub(s, old, new, label):
    """替换一次。new 为空串(删除场景)时不能用 `new in s` 判断,
       否则空串恒真会误判成"已改过"而跳过。"""
    if new == "":
        if old not in s:
            log.append("  = 跳过(已删): " + label); return s, False
        log.append("  + 删除: " + label)
        return s.replace(old, new, 1), True
    if new in s:
        log.append("  = 跳过(已改): " + label); return s, False
    if old not in s:
        log.append("  ! 未找到锚点 <<< " + label); return s, False
    log.append("  + 修改: " + label)
    return s.replace(old, new, 1), True

T1 = "\t"
T2 = "\t\t"
T3 = "\t\t\t"
T4 = "\t\t\t\t"


def fix_httpd_h():
    p = "httpd/httpd.h"
    if not os.path.exists(p):
        log.append("  ! 未找到 %s <<<" % p); return
    s = load(p)
    old = "typedef struct httpd_state {\n   uint8_t tstate;\n} uip_tcp_appstate_t;"
    new = (
        "typedef struct httpd_state {\n"
        "   uint8_t tstate;\n"
        "   /* Continuation state: everything after the first packet is re-read\n"
        "    * from flash, so outbuf never has to survive across events. */\n"
        "   uint16_t cont_len;    /* bytes still to send, 0 = none */\n"
        "   uint32_t cont_addr;   /* next flash address to read from */\n"
        "   uint32_t tx_addr;     /* start of the chunk last transmitted */\n"
        "   uint16_t tx_len;      /* its length; 0 = no chunk sent yet */\n"
        "} uip_tcp_appstate_t;")
    s2, _ = sub(s, old, new, p + ": appstate 增加 cont_*/tx_* 字段")
    if s2 != s: save(p, s2)


def fix_httpd_c():
    p = "httpd/httpd.c"
    if not os.path.exists(p):
        log.append("  ! 未找到 %s <<<" % p); return
    s = load(p)

    # 1) 删除全局 cont_len / cont_addr
    s, _ = sub(s, "__xdata uint16_t cont_len;\n__xdata uint32_t cont_addr;\n", "",
               p + ": 删除全局 cont_len/cont_addr")

    # 2) 新建连接时清零续传状态
    s, _ = sub(s,
        T1 + "if(uip_connected() && s->tstate == TSTATE_CLOSED) {\n"
        + T2 + 'dbg_string("Connected...\\n");\n'
        + T2 + "s->tstate = TSTATE_NONE;\n"
        + T1 + "}",
        T1 + "if(uip_connected() && s->tstate == TSTATE_CLOSED) {\n"
        + T2 + 'dbg_string("Connected...\\n");\n'
        + T2 + "s->tstate = TSTATE_NONE;\n"
        + T2 + "s->cont_len = 0;\n"
        + T2 + "s->cont_addr = 0;\n"
        + T2 + "s->tx_len = 0;\n"
        + T1 + "}",
        p + ": 新建连接清零 cont_*/tx_*")

    # 3) ACK 续传: 改为纯 flash 续传
    old_e = (
        T1 + "} else if (uip_acked() && s->tstate == TSTATE_TX) {\n"
        + T2 + 'dbg_string("ACK\\n");\n'
        + T2 + "if (slen > uip_mss()) {\n"
        + T3 + "slen -= uip_mss();\n"
        + T3 + "o_idx += uip_mss();\n"
        + T2 + "} else {\n"
        + T3 + "slen = 0;\n"
        + T3 + "o_idx += slen;\n"
        + T2 + "}\n"
        + "\n"
        + T2 + "s->tstate = TSTATE_ACKED;\n"
        + "\n"
        + T2 + "if (slen > uip_mss()) {\n"
        + T3 + 'dbg_string("Sending A: "); dbg_short(slen); dbg_char(\'\\n\');\n'
        + T3 + "uip_send(outbuf + o_idx, uip_mss());\n"
        + T3 + "s->tstate = TSTATE_TX;\n"
        + T2 + "} else if (slen > 0) {\n"
        + T3 + 'dbg_string("Sending B: "); dbg_short(slen); dbg_char(\'\\n\');\n'
        + T3 + "uip_send(outbuf + o_idx, slen);\n"
        + T3 + "s->tstate = TSTATE_TX;\n"
        + T2 + "} else if (cont_len) {\n"
        + T3 + 'dbg_string("CONT cont_len: "); dbg_short(cont_len);\n'
        + T3 + "slen = cont_len > uip_mss() ? uip_mss() : cont_len;\n"
        + T3 + "if (slen > TCP_OUTBUF_SIZE)\n"
        + T4 + "slen = TCP_OUTBUF_SIZE;\n"
        + T3 + "flash_region.addr = cont_addr;\n"
        + T3 + "flash_region.len = slen;\n"
        + T3 + "flash_read_bulk(outbuf);\n"
        + T3 + "uip_send(outbuf, slen);\n"
        + T3 + "cont_len -= slen;\n"
        + T3 + "cont_addr += slen;\n"
        + T3 + "s->tstate = TSTATE_TX;\n"
        + T2 + "}")
    new_e = (
        T1 + "} else if (uip_acked() && s->tstate == TSTATE_TX) {\n"
        + T2 + 'dbg_string("ACK\\n");\n'
        + T2 + "s->tstate = TSTATE_ACKED;\n"
        + T2 + "/* Everything past the first packet is re-read from flash using\n"
        + T2 + " * this connection's own cont_*, so outbuf is only ever a\n"
        + T2 + " * scratch buffer within one call: another connection may\n"
        + T2 + " * overwrite it before this one is polled again. */\n"
        + T2 + "if (s->cont_len) {\n"
        + T3 + "slen = s->cont_len > uip_mss() ? uip_mss() : s->cont_len;\n"
        + T3 + "if (slen > TCP_OUTBUF_SIZE)\n"
        + T4 + "slen = TCP_OUTBUF_SIZE;\n"
        + T3 + "s->tx_addr = s->cont_addr;\n"
        + T3 + "s->tx_len = slen;\n"
        + T3 + "flash_region.addr = s->cont_addr;\n"
        + T3 + "flash_region.len = slen;\n"
        + T3 + "flash_read_bulk(outbuf);\n"
        + T3 + "uip_send(outbuf, slen);\n"
        + T3 + "s->cont_len -= slen;\n"
        + T3 + "s->cont_addr += slen;\n"
        + T3 + "s->tstate = TSTATE_TX;\n"
        + T2 + "}")
    s, _ = sub(s, old_e, new_e, p + ": ACK 续传改为纯 flash 续传")

    # 4) 新请求清零。锚点带上下一行, 否则步骤 2 新增的同名行会让
    #    这里的 new 命中而误判为"已改过", 真正的那行就漏改了。
    s, _ = sub(s,
        T2 + "cont_len = 0;\n"
        + T2 + "dbg_char('<'); dbg_short(uip_len); dbg_char('\\n');\n",
        T2 + "s->cont_len = 0;\n"
        + T2 + "dbg_char('<'); dbg_short(uip_len); dbg_char('\\n');\n",
        p + ": 新请求清零 s->cont_len")

    # 5) 文件响应: 首块只发一个 MSS, 其余走 flash 续传
    old_f = (
        T3 + "len_left = f_data[entry].len;\n"
        + T3 + "if (len_left > (TCP_OUTBUF_SIZE - slen)) {\n"
        + T4 + "cont_len = len_left - (TCP_OUTBUF_SIZE - slen);\n"
        + T4 + "len_left = TCP_OUTBUF_SIZE - slen;\n"
        + T4 + "cont_addr = f_data[entry].start + len_left;\n"
        + T3 + "}")
    new_f = (
        T3 + "len_left = f_data[entry].len;\n"
        + T3 + "/* Send at most one MSS in the first packet; the rest is\n"
        + T3 + " * re-read from flash per connection. This keeps outbuf\n"
        + T3 + " * from having to survive across events. */\n"
        + T3 + "if (uip_mss() > slen && len_left > uip_mss() - slen)\n"
        + T4 + "len_left = uip_mss() - slen;\n"
        + T3 + "if (len_left > TCP_OUTBUF_SIZE - slen)\n"
        + T4 + "len_left = TCP_OUTBUF_SIZE - slen;\n"
        + T3 + "s->cont_len = f_data[entry].len - len_left;\n"
        + T3 + "s->cont_addr = f_data[entry].start + len_left;")
    s, _ = sub(s, old_f, new_f, p + ": 文件响应首块限制在一个 MSS")

    # 6) 重传: 优先用 tx_* 从 flash 重发上一段
    old_h = (
        T1 + "} else if (uip_rexmit()) { // Connection established, need to rexmit?\n"
        + T2 + 'dbg_string("RETRANSMIT requested\\n");\n'
        + T2 + "if (slen > uip_mss()) {\n")
    new_h = (
        T1 + "} else if (uip_rexmit()) { // Connection established, need to rexmit?\n"
        + T2 + 'dbg_string("RETRANSMIT requested\\n");\n'
        + T2 + "/* outbuf may hold another connection's data by now, so\n"
        + T2 + " * resend the last chunk from flash instead. */\n"
        + T2 + "if (s->tx_len) {\n"
        + T3 + "flash_region.addr = s->tx_addr;\n"
        + T3 + "flash_region.len = s->tx_len;\n"
        + T3 + "flash_read_bulk(outbuf);\n"
        + T3 + "uip_send(outbuf, s->tx_len);\n"
        + T2 + "} else if (slen > uip_mss()) {\n")
    s, _ = sub(s, old_h, new_h, p + ": 重传改用 flash 上的 tx_*")

    save(p, s)


def fix_page_impl():
    p = "httpd/page_impl.c"
    if not os.path.exists(p):
        log.append("  ! 未找到 %s <<<" % p); return
    s = load(p)

    s, _ = sub(s, "extern __xdata uint16_t cont_len;\nextern __xdata uint32_t cont_addr;\n",
               "", p + ": 删除 extern cont_len/cont_addr")

    s, _ = sub(s, "if (slen + 76 > TCP_OUTBUF_SIZE)",
               "if (slen + 76 > uip_mss())", p + ": send_l2 按 MSS 截断")

    s, _ = sub(s, "if (slen + 141 > TCP_OUTBUF_SIZE)",
               "if (slen + 141 > uip_mss())", p + ": send_vlanlist 按 MSS 截断")

    old_c = (
        T1 + "if (valid_len > (TCP_OUTBUF_SIZE - slen)) {\n"
        + T2 + "cont_len = valid_len - (TCP_OUTBUF_SIZE - slen);\n"
        + T2 + "valid_len = TCP_OUTBUF_SIZE - slen;\n"
        + T2 + "cont_addr = valid_len;\n"
        + T1 + "}")
    new_c = (
        T1 + "/* The config lives in flash, so the tail can be re-read per\n"
        + T1 + " * connection instead of being left in the shared outbuf.\n"
        + T1 + " * (cont_addr used to be set to valid_len here, which is a byte\n"
        + T1 + " * count rather than a flash address.) */\n"
        + T1 + "if (uip_mss() > slen && valid_len > (uip_mss() - slen)) {\n"
        + T2 + "uip_conn->appstate.cont_len = valid_len - (uip_mss() - slen);\n"
        + T2 + "valid_len = uip_mss() - slen;\n"
        + T2 + "uip_conn->appstate.cont_addr = CONFIG_START + valid_len;\n"
        + T1 + "}")
    s, _ = sub(s, old_c, new_c, p + ": send_config 续传改 flash 地址 + 按 MSS 截断")

    save(p, s)


def fix_uipconf():
    p = "uip/uip-conf.h"
    if not os.path.exists(p):
        log.append("  ! 未找到 %s <<<" % p); return
    s = load(p)
    s, _ = sub(s, "#define UIP_CONF_MAX_CONNECTIONS 1",
               "#define UIP_CONF_MAX_CONNECTIONS 8", p + ": UIP_CONNS 1 -> 8")
    save(p, s)


# ---------------------------------------------------------------- 主流程
if os.path.basename(os.getcwd()) == "httpd":
    os.chdir("..")
if not os.path.isdir("httpd") or not os.path.isdir("uip"):
    print("✗ 请在仓库根目录运行"); sys.exit(1)

fix_httpd_h()
fix_httpd_c()
fix_page_impl()
fix_uipconf()

print("\n".join(log))

# ---------------------------------------------------------------- 自检
print("\n自检:")
h = load("httpd/httpd.h")
print("  %-32s %s" % ("httpd.h appstate 字段",
      "OK" if all(k in h for k in ("cont_len", "cont_addr", "tx_addr", "tx_len")) else "缺失 <<<"))

def bare_refs(txt):
    """裸露的 cont_* 引用, 排除注释行。"""
    out = []
    for l in txt.splitlines():
        t = l.strip()
        if t.startswith("*") or t.startswith("/*") or t.startswith("//"):
            continue
        if re.search(r"(?<![->.\w])cont_(len|addr)\b", t):
            out.append(t)
    return out

c = load("httpd/httpd.c")
bare = bare_refs(c)
print("  %-32s %s" % ("httpd.c 无裸露 cont_*",
      "OK" if not bare else ("残留 %d 处 <<<" % len(bare))))
for l in bare[:6]:
    print("        " + l)

p2 = load("httpd/page_impl.c")
bare2 = bare_refs(p2)
print("  %-32s %s" % ("page_impl.c 无裸露 cont_*",
      "OK" if not bare2 else ("残留 %d 处 <<<" % len(bare2))))
for l in bare2[:6]:
    print("        " + l)

print("  %-32s %s" % ("uip-conf.h UIP_CONNS = 8",
      "OK" if "#define UIP_CONF_MAX_CONNECTIONS 8" in load("uip/uip-conf.h") else "未改 <<<"))
print("  %-32s %s" % ("httpd.c 花括号", "平衡" if c.count("{") == c.count("}") else "不平衡 <<<"))
print("  %-32s %s" % ("page_impl.c 花括号", "平衡" if p2.count("{") == p2.count("}") else "不平衡 <<<"))
