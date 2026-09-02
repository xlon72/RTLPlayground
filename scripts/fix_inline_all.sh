#!/usr/bin/env bash
set -Eeuo pipefail
cd ~/Desktop/lt/RTLPlayground

# 1. 回退到最初干净的状态
git checkout -- html/ httpd/httpd.c uip/uip-conf.h
echo "  ✓ 源码已彻底重置为基线状态"

# 2. 执行全文件内联打包
python3 -c '
import os, re
from pathlib import Path

html_dir = Path("html")
# 提取全局 CSS 和基础 JS
style_css = (html_dir / "style.css").read_text(encoding="utf-8")
i18n_js = (html_dir / "i18n.js").read_text(encoding="utf-8")
nav_js = (html_dir / "navigation.js").read_text(encoding="utf-8")

for p in html_dir.rglob("*.html"):
    html = p.read_text(encoding="utf-8")
    
    # 替换 style.css 为内联 <style>
    if "<link" in html and "style.css" in html:
        html = re.sub(r"<link[^>]*href=\"[^\"]*style\.css\"[^>]*>", f"<style>\n{style_css}\n</style>", html)
    
    # 将页面引用的所有独立 JS 文件内联
    js_links = re.findall(r"<script[^>]*src=\"([^\"]+)\"[^>]*></script>", html)
    for js_file in js_links:
        js_path = html_dir / js_file
        if js_path.exists():
            js_content = js_path.read_text(encoding="utf-8")
            html = re.sub(f"<script[^>]*src=\"{js_file}\"[^>]*></script>", f"<script>\n{js_content}\n</script>", html)
    
    p.write_text(html, encoding="utf-8")
    print(f"  ✓ {p.name}: 已全内联 ({len(js_links)} 个 JS)")

# 删除已经被内联的独立资源，避免占用 Flash 空间
for f in ["style.css", "i18n.js", "navigation.js", "main.js", "dashboard.js", "vlan.js"]:
    if (html_dir / f).exists():
        (html_dir / f).unlink()
        print(f"  ✓ 已清理独立文件: {f}")
'

# 3. 拦截残留的 favicon 并发请求 (纯前端手段)
# 给所有 html 强行注入一个空的 base64 favicon，彻底掐断浏览器去请求 favicon.ico 的行为
find html -name "*.html" -exec sed -i '' -e 's|</head>|<link rel="icon" href="data:;base64,=">\n</head>|g' {} +

# 4. 保守起见：放弃 GZIP 压缩，保证 C 代码 100% 不出错
# 我们依靠内联带来的零并发来提速，而不是依赖 GZIP。

# 5. 编译固件
echo "== 重新构建全内联零并发版固件 =="
rm -rf output/FG_4GT_2SX_V2_0/*.bin
make MACHINE=FG_4GT_2SX_V2_0 > /tmp/build_inline.log 2>&1

if ls output/FG_4GT_2SX_V2_0/*.bin >/dev/null 2>&1; then
    echo "✅ 零并发版编译成功！请执行 bash ~/flash_local.sh 刷入。"
else
    echo "✗ 编译失败，请检查 /tmp/build_inline.log"
fi
