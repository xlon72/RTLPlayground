#!/usr/bin/env bash
set -Eeuo pipefail
cd ~/Desktop/lt/RTLPlayground

# 1. 撤销之前的 JS 修改
git checkout -- $(git ls-files '*.js')
echo "  ✓ 已清理旧补丁"

# 2. 注入 Fetch + XHR 双重队列
python3 -c '
import os
from pathlib import Path

repo_dir = Path(os.path.expanduser("~/Desktop/lt/RTLPlayground"))

hook_code = """(function() {
    if (window._netPatched) return;
    window._netPatched = true;
    
    var chain = Promise.resolve();
    
    // 1. 劫持 Fetch
    var originalFetch = window.fetch;
    window.fetch = function() {
        var args = arguments;
        return new Promise(function(resolve, reject) {
            chain = chain.then(function() {
                return originalFetch.apply(window, args).then(resolve).catch(reject);
            }).catch(function(){});
        });
    };

    // 2. 劫持 XHR
    var originalSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function() {
        var xhr = this;
        var args = arguments;
        
        chain = chain.then(function() {
            return new Promise(function(resolve) {
                // 监听 XHR 结束事件放行队列
                xhr.addEventListener("loadend", function() { resolve(); });
                originalSend.apply(xhr, args);
            });
        }).catch(function(){});
    };
})();\n"""

for p in repo_dir.rglob("main.js"):
    if "tools" in str(p) or "output" in str(p): continue
    content = p.read_text(encoding="utf-8")
    p.write_text(hook_code + content, encoding="utf-8")
    print(f"  ✓ {p.name}: 已注入 Fetch + XHR 全局双重排队机制")
'

# 3. 编译
echo "== 重新构建固件 =="
bash ~/build_local.sh > /tmp/build_fix_univ.log 2>&1
if ls output/FG_4GT_2SX_V2_0/*.bin >/dev/null 2>&1; then
    echo "✅ 编译成功！"
    echo "下一步：执行 bash ~/flash_local.sh 刷入，然后务必 Cmd-Shift-R 硬刷新页面。"
else
    echo "✗ 编译失败，请检查 /tmp/build_fix_univ.log"
fi
