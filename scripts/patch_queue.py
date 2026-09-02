#!/usr/bin/env python3
import os
import re
from pathlib import Path

repo_dir = Path(os.path.expanduser("~/Desktop/lt/RTLPlayground"))
if not repo_dir.exists():
    print(f"✗ 找不到仓库目录: {repo_dir}")
    exit(1)

# 使用完全兼容原生 fetch API 的队列封装，无需改动后续的 .then(res => res.json())
queue_code = """window.ReqQueue = (function() {
    var chain = Promise.resolve();
    return {
        fetch: function(url, options) {
            return new Promise(function(resolve, reject) {
                chain = chain.then(function() {
                    return fetch(url, options).then(resolve).catch(reject);
                }).catch(function(){});
            });
        }
    };
})();

"""

js_files = []
# 遍历目录找 JS 文件，跳过构建和工具目录
for root, dirs, files in os.walk(repo_dir):
    if any(skip in root for skip in ["tools", "output", ".git"]):
        continue
    for file in files:
        if file.endswith(".js"):
            js_files.append(Path(root) / file)

for js_path in js_files:
    try:
        content = js_path.read_text(encoding="utf-8")
        original_content = content
        modified = False
        
        # 1. 在 main.js 顶部注入队列定义
        if js_path.name == "main.js" and "window.ReqQueue" not in content:
            content = queue_code + content
            print(f"  ✓ {js_path.name}: 注入全局请求队列")
            modified = True
            
        # 2. 将全局所有独立的 fetch( 替换为排队 fetch
        # 使用负向后瞻 (?<!...) 防止重复替换 window.ReqQueue.fetch
        new_content = re.sub(r'(?<!window\.ReqQueue\.)\bfetch\s*\(', 'window.ReqQueue.fetch(', content)
        
        if new_content != content:
            count = len(re.findall(r'window\.ReqQueue\.fetch\(', new_content)) - len(re.findall(r'window\.ReqQueue\.fetch\(', content))
            print(f"  ✓ {js_path.name}: 拦截并替换了 {count} 处 fetch 并发请求")
            content = new_content
            modified = True
            
        if modified:
            js_path.write_text(content, encoding="utf-8")
            
    except Exception as e:
        print(f"  ✗ {js_path.name}: 处理失败 ({e})")

print("\n✅ 队列植入完毕。请执行: bash ~/build_local.sh && bash ~/flash_local.sh")
