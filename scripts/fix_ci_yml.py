#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""改进 .github/workflows/build.yml。

三项改动:
1) artifact 名 firmware-nosfp -> firmware-FG_4GT_2SX_V2_0
   原名为上游遗留, 与实际机型(有 2 个 SFP 口)不符。
2) path: output/*.bin -> output/**/*.bin
   单星号不跨 '/', 只匹配到 output/rtlplayground.bin 这个符号链接,
   真正的产物在 output/FG_4GT_2SX_V2_0/ 子目录下。
3) 新增工具链版本打印
   本地 sdcc 4.6.0 与 CI 的 apt sdcc 版本不同, 导致两份二进制有 46%
   字节差异。先打印出来, 才能判断是否需要锁定版本对齐。

不改: 触发条件(保持 branches, 不加 tags, 以免打 tag 时多跑构建)。

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

# ---------------------------------------------------- 1) artifact 名
if "firmware-FG_4GT_2SX_V2_0" in s:
    log.append("  = 跳过: artifact 名已改")
else:
    OLD = "          name: firmware-nosfp\n"
    NEW = "          name: firmware-FG_4GT_2SX_V2_0\n"
    if OLD not in s:
        sys.exit("✗ 未定位 artifact 名 <<<")
    s = s.replace(OLD, NEW, 1)
    log.append("  + 修改: artifact 名 -> firmware-FG_4GT_2SX_V2_0")

# ---------------------------------------------------- 2) 上传路径
if "output/**/*.bin" in s:
    log.append("  = 跳过: 上传路径已改")
else:
    OLD = "          path: output/*.bin\n"
    NEW = "          path: output/**/*.bin\n          retention-days: 90\n"
    if OLD not in s:
        sys.exit("✗ 未定位上传路径 <<<")
    s = s.replace(OLD, NEW, 1)
    log.append("  + 修改: 上传路径 -> output/**/*.bin (+保留 90 天)")

# ---------------------------------------------------- 3) 版本打印
if "Show toolchain versions" in s:
    log.append("  = 跳过: 版本打印已存在")
else:
    OLD = """      - name: Check machine definitions
        run: make machine_check
"""
    NEW = """      - name: Show toolchain versions
        run: |
          echo "sdcc: $(sdcc --version 2>&1 | head -2 | tr '\\n' ' ')"
          echo "gcc:  $(gcc --version | head -1)"
          echo "make: $(make --version | head -1)"

      - name: Check machine definitions
        run: make machine_check
"""
    if OLD not in s:
        sys.exit("✗ 未定位 machine_check 步骤 <<<")
    s = s.replace(OLD, NEW, 1)
    log.append("  + 新增: Show toolchain versions 步骤")

io.open(p, "w", encoding="utf-8", newline="").write(s)
print("\n".join(log))

# ---------------------------------------------------- 自检
print("\n自检:")
s = io.open(p, encoding="utf-8", newline="").read()

checks = [
    ("artifact 名已改",     "name: firmware-FG_4GT_2SX_V2_0" in s),
    ("无旧名 firmware-nosfp", "firmware-nosfp" not in s),
    ("上传路径 output/**",   "path: output/**/*.bin" in s),
    ("无旧路径单一星号",     "path: output/*.bin" not in s),
    ("有版本打印步骤",       "Show toolchain versions" in s),
    ("保留 machine_check",   "make machine_check" in s),
    ("保留 workflow_dispatch", "workflow_dispatch" in s),
    ("未加 tags 触发",       "tags:" not in s),
    ("保留构建机型",         'MACHINE="FG_4GT_2SX_V2_0"' in s),
]

try:
    import yaml
    yaml.safe_load(s)
    checks.append(("YAML 语法有效", True))
except ImportError:
    checks.append(("YAML 语法有效", "跳过(无 pyyaml)"))
except Exception as e:
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
