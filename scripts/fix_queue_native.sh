#!/usr/bin/env bash
set -Eeuo pipefail
cd ~/Desktop/lt/RTLPlayground

# 1. 撤销之前所有被正则破坏的 JS 文件
git checkout -- $(git ls-files '*.js')
echo "  ✓ 已回退 JS 源码"

# 2. 使用安全的 Monkey-patch 劫持底层原生 fetch
python3 -c '
import os
from pathlib import Path

repo_dir = Path(os.path.expanduser("~/Desktop/lt/RTLPlayground"))

hook_code = """(function() {
    if (window._fetchPatched) return;
    window._fetchPatched = true;
    var originalFetch = window.fetch;
    var chain = Promise.resolve();
    
    window.fetch = function() {
        var args = arguments;
        return new Promise(function(resolve, reject) {
            chain = chain.then(function() {
                return originalFetch.apply(window, args)
                    .then(resolve)
                    .catch(reject);
            }).catch(function(){}); // 吞掉链条错误，防止队列卡死
        });
    };
})();\n"""

# 仅在 main.js 注入一次劫持代码 (基于记忆体知晓 main.js 是核心入口)
for p in repo_dir.rglob("main.js"):
    if "tools" in str(p) or "output" in str(p): continue
    content = p.read_text(encoding="utf-8")
    if "_fetchPatched" not in content:
        p.write_text(hook_code + content, encoding="utf-8")
        print(f"  ✓ {p.name}: 已注入底层 fetch 劫持队列")
'

# 3. 重新编译并提示刷写
echo "== 重新构建固件 =="
bash ~/build_local.sh > /tmp/build_fix.log 2>&1
if ls output/FG_4GT_2SX_V2_0/*.bin >/dev/null 2>&1; then
    echo "✅ 修复版编译成功，请执行: bash ~/flash_local.sh 刷入并使用 Cmd-Shift-R 硬刷新页面"
else
    echo "✗ 编译失败，请检查"
fi
