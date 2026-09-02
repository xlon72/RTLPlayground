#!/usr/bin/env bash
set -Eeuo pipefail
cd ~/Desktop/lt/RTLPlayground

# 1. 恢复纯净的源码，清空残余
git checkout -- html/ httpd/httpd.c
echo "  ✓ 源码已重置为干净状态"

# 2. 生成并执行 httpd.c 的补丁脚本
cat > patch_httpd.py <<'EOF'
import re
from pathlib import Path
httpd_path = Path("httpd/httpd.c")
httpd = httpd_path.read_text(encoding="utf-8")

# 解除静态资源鉴权，且符合 SDCC 的变量声明规范
old_pattern = r"if \(!authenticated && !\(f_data\[entry\]\.start == FDATA_START_login_html.*?goto do_send;\s*\}"
new_code = """if (!authenticated) {
            uint8_t qlen = 0;
            uint8_t is_html = 0;
            while(q[qlen]) qlen++;
            if (qlen > 5 && q[qlen-5] == '.' && q[qlen-4] == 'h' && q[qlen-3] == 't' && q[qlen-2] == 'm' && q[qlen-1] == 'l') {
                is_html = 1;
            }
            if (is_html && f_data[entry].start != FDATA_START_login_html) {
                send_to_login();
                goto do_send;
            }
        }"""

httpd = re.sub(old_pattern, new_code, httpd, flags=re.DOTALL)

# 注入 Content-Encoding: gzip 响应头
httpd = httpd.replace("Connection: close\\r\\nAccess-Control", "Connection: close\\r\\nContent-Encoding: gzip\\r\\nAccess-Control")

httpd_path.write_text(httpd, encoding="utf-8")
print("  ✓ httpd.c: 鉴权白名单解除，GZIP 头注入完毕")
EOF
python3 patch_httpd.py

# 3. 生成并执行前端 DOM 加载器注入脚本
cat > patch_html.py <<'EOF'
import os, re, json
from pathlib import Path
for p in Path("html").rglob("*.html"):
    html = p.read_text(encoding="utf-8")
    
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
        await new Promise(function(resolve){{
            var el = document.createElement(urls[i].indexOf(".css") > -1 ? "link" : "script");
            if(el.tagName === "LINK") {{ el.rel = "stylesheet"; el.href = urls[i]; }}
            else {{ el.src = urls[i]; }}
            el.onload = el.onerror = resolve;
            document.head.appendChild(el);
        }});
    }}
    var inlines = {json.dumps(inline_js)};
    for(var j=0; j<inlines.length; j++){{
        var s = document.createElement("script");
        s.innerHTML = inlines[j];
        document.body.appendChild(s);
    }}
    window.dispatchEvent(new Event("assetsLoaded"));
}})();
</script>"""

    if "</body>" in html:
        html = html.replace("</body>", loader + "\n</body>")
    else:
        html += "\n" + loader
        
    p.write_text(html, encoding="utf-8")
    print(f"  ✓ {p.name}: 增强型串行加载器已注入")
EOF
python3 patch_html.py

# 4. 重新进行 GZIP 极限压缩
python3 ~/gzip_assets.py >/dev/null

# 5. 编译固件
echo "== 重新构建完美终极版固件 =="
rm -rf output/FG_4GT_2SX_V2_0/*.bin
make MACHINE=FG_4GT_2SX_V2_0 > /tmp/build_perfect.log 2>&1

if ls output/FG_4GT_2SX_V2_0/*.bin >/dev/null 2>&1; then
    echo "✅ 完美版编译成功！请执行 bash ~/flash_local.sh 刷入。"
else
    echo "✗ 编译失败，请检查 /tmp/build_perfect.log"
fi
