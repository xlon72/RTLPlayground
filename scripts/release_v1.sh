#!/usr/bin/env bash
set -Eeuo pipefail
cd ~/Desktop/lt/RTLPlayground

# 1. 恢复 main.js (剥离局部补丁) 并将全局补丁注入 i18n.js
python3 -c '
import os
from pathlib import Path
repo_dir = Path(os.path.expanduser("~/Desktop/lt/RTLPlayground"))

queue_code = """(function() {
    if (window._netPatched) return;
    window._netPatched = true;
    var chain = Promise.resolve();
    
    var originalFetch = window.fetch;
    window.fetch = function() {
        var args = arguments;
        return new Promise(function(resolve, reject) {
            chain = chain.then(function() {
                return originalFetch.apply(window, args).then(resolve).catch(reject);
            }).catch(function(){});
        });
    };

    var originalSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function() {
        var xhr = this;
        var args = arguments;
        chain = chain.then(function() {
            return new Promise(function(resolve) {
                xhr.addEventListener("loadend", function() { resolve(); });
                originalSend.apply(xhr, args);
            });
        }).catch(function(){});
    };
})();\n"""

for p in repo_dir.rglob("main.js"):
    if "tools" in str(p) or "output" in str(p): continue
    os.system(f"git checkout -- {p}")
    print(f"  ✓ {p.name}: 已还原")

for p in repo_dir.rglob("i18n.js"):
    if "tools" in str(p) or "output" in str(p): continue
    content = p.read_text(encoding="utf-8")
    if "_netPatched" not in content:
        p.write_text(queue_code + content, encoding="utf-8")
        print(f"  ✓ {p.name}: 已注入全站网络队列")
'

# 2. 净化 Makefile 并硬编码版本号为 v1.0.0
find . -type f \( -name "Makefile" -o -name "*.c" -o -name "*.h" \) -exec sed -i '' 's/v0.1.0/v1.0.0/g' {} +
sed -i '' 's/-$(GIT_REV)//g' Makefile 2>/dev/null || true
sed -i '' 's/-$(GIT_VERSION)//g' Makefile 2>/dev/null || true
sed -i '' 's/-dirty//g' Makefile 2>/dev/null || true
echo "  ✓ 版本号已锁定为纯净版 v1.0.0"

# 3. 提交至正式版并开始构建
git add .
git commit -m "release: v1.0.0 with global network queue in i18n.js" || true

echo "== 开始构建正式版固件 =="
bash ~/build_local.sh > /tmp/build_release.log 2>&1
if ls output/FG_4GT_2SX_V2_0/*.bin >/dev/null 2>&1; then
    echo "✅ v1.0.0 编译成功！请执行 bash ~/flash_local.sh 刷入，并用无痕窗口验证。"
else
    echo "✗ 编译失败，请检查 /tmp/build_release.log"
fi
