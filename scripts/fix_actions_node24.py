#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""升级 GitHub Actions 到原生支持 Node24 的版本。

背景
----
官方公告: Node 20 于 2026-09-23 从 Actions runners 彻底移除。
当前 build.yml 使用 actions/checkout@v4 与 actions/upload-artifact@v4,
二者 target node20, 目前靠 GitHub 的强制兼容层跑在 Node24 上, CI 日志有:
    Node.js 20 is deprecated. The following actions target Node.js 20 but
    are being forced to run on Node.js 24 ...
官方建议迁移到原生跑 Node24 的版本。

改法
----
v4 -> v7 (已查询确认的最新主版本, latest release = v7.0.1)。
继续沿用浮动主版本标签(@v7)写法, 与仓库原有风格一致。

注: v4 -> v7 跨了三个主版本, 具体变更我不臆测; 本 workflow 只用到
checkout 和 upload-artifact 的基础能力, 风险低, 以 CI 实跑结果为准。

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
log = []

for name in ("checkout", "upload-artifact"):
    old = "actions/%s@v4" % name
    new = "actions/%s@v7" % name
    if new in s:
        log.append("  = 跳过: %s 已是 v7" % name)
    elif old in s:
        s = s.replace(old, new, 1)
        log.append("  + 升级: %s v4 -> v7" % name)
    else:
        log.append("  ! 未找到 %s <<<" % name)

io.open(p, "w", encoding="utf-8", newline="").write(s)
print("\n".join(log))

print("\n自检:")
s = io.open(p, encoding="utf-8", newline="").read()

checks = [
    ("checkout 已升 v7",        "actions/checkout@v7" in s),
    ("upload-artifact 已升 v7", "actions/upload-artifact@v7" in s),
    ("无残留 @v4",              "@v4" not in s),
    ("保留 workflow_dispatch",  "workflow_dispatch" in s),
    ("保留构建机型",            'MACHINE="FG_4GT_2SX_V2_0"' in s),
    ("保留 artifact 名",        "name: firmware-FG_4GT_2SX_V2_0" in s),
    ("保留 output/** 路径",     "path: output/**/*.bin" in s),
    ("保留 machine_check",      "make machine_check" in s),
    ("保留版本打印",            "Show toolchain versions" in s),
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
    print("  %-26s %s" % (name, mark))

print("")
print("✓ 全部通过" if ok else "✗ 存在问题")
