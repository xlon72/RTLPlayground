#!/usr/bin/env bash
set -Eeuo pipefail
cd ~/Desktop/lt/RTLPlayground

# 1. 恢复基线，放弃所有破坏体积的修改
git checkout -- html/ httpd/httpd.c uip/uip-conf.h
echo "  ✓ 源码已重置"

# 2. 修改 httpd.c 放开静态资源鉴权 (解决 302 死循环)
cat > patch_httpd.py <<'EOF'
import re
code = open("httpd/httpd.c").read()
code = re.sub(r'if \(!authenticated && !\(f_data\[entry\]\.start == FDATA_START_login_html.*?goto do_send;\n\s*\}', 
r'''
uint8_t is_html = 0;
{
    uint8_t qlen = 0;
    while(q[qlen]) qlen++;
    if (qlen > 5 && q[qlen-5] == '.' && q[qlen-4] == 'h' && q[qlen-3] == 't' && q[qlen-2] == 'm' && q[qlen-1] == 'l') is_html = 1;
}
if (!authenticated && is_html && f_data[entry].start != FDATA_START_login_html) {
    send_to_login();
    goto do_send;
}
''', code, flags=re.DOTALL)
open("httpd/httpd.c", "w").write(code)
print("  ✓ HTTP 鉴权白名单已修正")
EOF
python3 patch_httpd.py

# 3. 注入带 100ms 物理延迟的串行加载器
cat > patch_html.py <<'EOF'
import re, json
from pathlib import Path
for p in Path("html").rglob("*.html"):
    html = p.read_text(encoding="utf-8")
    
    # 物理掐断浏览器偷偷并发请求 favicon 的行为
    html = html.replace('</head>', '<link rel="icon" href="data:;base64,=">\n</head>')
    
    css = re.findall(r'<link[^>]*href="([^"]+\.css)"[^>]*>', html)
    js = re.findall(r'<script[^>]*src="([^"]+\.js)"[^>]*></script>', html)
    html = re.sub(r'<link[^>]*href="[^\"]+\.css"[^>]*>', '', html)
    html = re.sub(r'<script[^>]*src="[^\"]+\.js"[^>]*></script>', '', html)
    
    inline_js = []
    def ext(m):
        if 'src=' not in m.group(1):
            inline_js.append(m.group(2))
            return ''
        return m.group(0)
    html = re.sub(r'<script([^>]*)>(.*?)</script>', ext, html, flags=re.DOTALL)
    
    if not css and not js and not inline_js: continue
    
    loader = f"""<script>
(async function(){{
    var urls = {json.dumps(css + js)};
    for(var i=0; i<urls.length; i++){{
        // 核心心法：强制让出 100ms，让 8051 芯片把 TIME_WAIT 插槽腾出来
        await new Promise(r => setTimeout(r, 100)); 
        await new Promise(function(resolve){{
            var el = document.createElement(urls[i].indexOf(".css") > -1 ? "link" : "script");
            if(el.tagName === "LINK") {{ el.rel = "stylesheet"; el.href = urls[i]; }}
            else {{ el.src = urls[i]; }}
            el.onload = el.onerror = resolve;
            document.head.appendChild(el);
        }});
    }}
    var inlines = {json.dumps(inline_js)};
    inlines.forEach(function(c) {{ var s = document.createElement('script'); s.innerHTML=c; document.body.appendChild(s); }});
    window.dispatchEvent(new Event('assetsLoaded'));
}})();
</script>"""
    if "</body>" in html: html = html.replace("</body>", loader + "\n</body>")
    else: html += "\n" + loader
    p.write_text(html, encoding="utf-8")
print("  ✓ 延迟型串行加载器已注入")
EOF
python3 patch_html.py

echo "== 重新构建终极延迟单线版固件 =="
rm -rf output/FG_4GT_2SX_V2_0/*.bin
make MACHINE=FG_4GT_2SX_V2_0 > /tmp/build_delay.log 2>&1
if ls output/FG_4GT_2SX_V2_0/*.bin >/dev/null 2>&1; then
    echo "✅ 延迟版编译成功！请执行 bash ~/flash_local.sh 刷入。"
else
    echo "✗ 编译失败，请检查 /tmp/build_delay.log"
fi
