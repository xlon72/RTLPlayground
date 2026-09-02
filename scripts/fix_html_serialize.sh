#!/usr/bin/env bash
set -Eeuo pipefail
cd ~/Desktop/lt/RTLPlayground

# 1. 顺应硬件物理定律：强行锁死 UIP_CONNS 为 1
sed -i '' 's/#define UIP_CONF_MAX_CONNECTIONS.*/#define UIP_CONF_MAX_CONNECTIONS 1/g' uip/uip-conf.h
echo "  ✓ 底层连接已硬性锁死为 1"

# 2. 恢复之前被变成二进制 GZIP 的 HTML 文件
git checkout -- html/
echo "  ✓ 静态源码已恢复为文本"

# 3. 注入纯前端串行加载器
python3 -c '
import os, re
from pathlib import Path

html_dir = Path(os.path.expanduser("~/Desktop/lt/RTLPlayground/html"))
for p in html_dir.rglob("*.html"):
    html = p.read_text(encoding="utf-8")

    # 提取所有外链 CSS 和 JS
    css = re.findall(r"<link[^>]*href=\"([^\"]+\.css)\"[^>]*>", html)
    js = re.findall(r"<script[^>]*src=\"([^\"]+\.js)\"[^>]*></script>", html)
    assets = css + js
    if not assets: continue

    # 移除原生并发标签
    html = re.sub(r"<link[^>]*href=\"[^\"]+\.css\"[^>]*>", "", html)
    html = re.sub(r"<script[^>]*src=\"[^\"]+\.js\"[^>]*></script>", "", html)

    # 保护内联 Script，等待外链加载完毕再执行
    def wrap_inline(m):
        tag, inner = m.group(1), m.group(2)
        if "src=" in tag: return m.group(0)
        return f"<script{tag}>\nwindow.addEventListener(\"assetsLoaded\", function(){{\n{inner}\n}});\n</script>"
    html = re.sub(r"<script([^>]*)>(.*?)</script>", wrap_inline, html, flags=re.DOTALL)

    # 注入串行加载器 (完美适配 UIP_CONNS=1)
    assets_str = "[" + ", ".join(f"\"{u}\"" for u in assets) + "]"
    loader = f"""<script>
(async function(){{
    var urls = {assets_str};
    for(var i=0; i<urls.length; i++){{
        await new Promise(function(resolve){{
            var el = document.createElement(urls[i].indexOf(".css") > -1 ? "link" : "script");
            if(el.tagName === "LINK") {{ el.rel = "stylesheet"; el.href = urls[i]; }}
            else {{ el.src = urls[i]; }}
            el.onload = el.onerror = resolve;
            document.head.appendChild(el);
        }});
    }}
    window.dispatchEvent(new Event("assetsLoaded"));
}})();
</script>"""

    if "</title>" in html:
        html = html.replace("</title>", "</title>\n" + loader)
    else:
        html = loader + "\n" + html

    p.write_text(html, encoding="utf-8")
    print(f"  ✓ {p.name}: 注入串行加载器 (排队 {len(assets)} 个资源)")
'

# 4. 重新进行 GZIP 极限压缩
python3 ~/gzip_assets.py

# 5. 编译固件
echo "== 重新构建单线串行版固件 =="
rm -rf output/FG_4GT_2SX_V2_0/*.bin
make MACHINE=FG_4GT_2SX_V2_0 > /tmp/build_serial_ui.log 2>&1

if ls output/FG_4GT_2SX_V2_0/*.bin >/dev/null 2>&1; then
    echo "✅ 极致优化版编译成功！请执行 bash ~/flash_local.sh 刷入。"
else
    echo "✗ 编译失败，请检查 /tmp/build_serial_ui.log"
fi
