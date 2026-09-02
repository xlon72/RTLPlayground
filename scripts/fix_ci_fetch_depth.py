#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI: 让 git describe 能拿到 tag, 修正产物版本号。

问题
----
上轮 CI 产物名: rtlplayground-v0.1.0--FG_4GT_2SX_V2_0.bin
                ^^^^^^^  ^^
                版本退化   git hash 为空 -> 双横线

根因: actions/checkout 默认 fetch-depth: 1 (浅克隆), clone 下来的仓库
没有 tag 历史, 于是 Makefile 里的 git describe 失败, VERSION 退回默认的
v0.1.0, GIT_VERSION 为空。

这正是 update.html 注释里提到的情况:
  "CI 里 git describe 失败时版本串退化为 v0.1.0-, 故后缀允许为空"

同时也是 CI 产物与本地产物差异巨大的一部分原因(连嵌入的版本串都不同)。

修法
----
给 checkout 加 fetch-depth: 0, 拉取完整历史(含 tag)。

幂等。在仓库根目录运行。
"""
import io, os, sys

REPO = os.path.expanduser("~/Desktop/lt/RTLPlayground")
if os.path.basename(os.getcwd()) != "RTLPlayground" and os.path.isdir(REPO):
    os.chdir(REPO)

p = ".github/workflows/build.yml"
if not os.path.exists(p):
    sys.exit("✗ 未找到 %s <<<" % p)

s = io.open(p, encoding="utf-8", newline="").read()

if "fetch-depth" in s:
    print("  = 跳过: fetch-depth 已配置")
else:
    OLD = "      - uses: actions/checkout@v7\n"
    NEW = ("      - uses: actions/checkout@v7\n"
           "        with:\n"
           "          fetch-depth: 0\n")
    if OLD not in s:
        sys.exit("✗ 未定位 checkout 步骤 <<<")
    s = s.replace(OLD, NEW, 1)
    io.open(p, "w", encoding="utf-8", newline="").write(s)
    print("  + 新增: checkout fetch-depth: 0")

print("\n自检:")
s = io.open(p, encoding="utf-8", newline="").read()

checks = [
    ("已配 fetch-depth",      "fetch-depth: 0" in s),
    ("checkout 仍为 v7",      "actions/checkout@v7" in s),
    ("upload 仍为 v7",        "actions/upload-artifact@v7" in s),
    ("保留 artifact 名",      "name: firmware-FG_4GT_2SX_V2_0" in s),
    ("保留 output/** 路径",   "path: output/**/*.bin" in s),
    ("保留 machine_check",    "make machine_check" in s),
    ("保留版本打印",          "Show toolchain versions" in s),
    ("保留构建机型",          'MACHINE="FG_4GT_2SX_V2_0"' in s),
]

try:
    import yaml
    yaml.safe_load(s)
    checks.append(("YAML 语法有效", True))
except ImportError:
    checks.append(("YAML 语法有效", "跳过(无 pyyaml)"))
except Exception:
    checks.append(("YAML 语法有效", False))

ok = True
for item in checks:
    name, res = item[0], item[1]
    if res is True:
        mark = "OK"
    elif res is False:
        mark = "失败 <<<"
        ok = False
    else:
        mark = res
    print("  %-24s %s" % (name, mark))
print("")
print("✓ 全部通过" if ok else "✗ 存在问题")
