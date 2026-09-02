#!/usr/bin/env bash
set -Eeuo pipefail
cd ~/Desktop/lt/RTLPlayground

# 1. 恢复纯净的源码，清空此前失败的注入
git checkout -- html/ httpd/httpd.c
echo "  ✓ 源码已重置为干净状态"

# 2. 修改 httpd.c：解除静态文件的无脑鉴权拦截，并重新注入 GZIP 头
python3 -c '
import re
from pathlib import Path
httpd_path = Path("httpd/httpd.c")
httpd = httpd_path.read_text(encoding="utf-8")

# 将原本严苛的白名单，改为：仅当请求的是 .html 文件且不是 login.html 时，才重定向
old_pattern = r"if \(!authenticated && !\(f_data\[entry\]\.start == FDATA_START_login_html.*?goto do_send;\n\s*\}"
new_code = """uint8_t is_html = 0;
            {
                uint8_t qlen = 0;
                while(q[qlen]) qlen++;
                if (qlen > 5 && q[qlen-5] == '"'"'."'"' && q[qlen-4] == '"'"'h'"'"' && q[qlen-3] == '"'"'t'"'"' && q[qlen-2] == '"'"'m'"'"' && q[qlen-1] == '"'"'l'"'"') {
                    is_html = 1;
                }
            }
            if (!authenticated && is_html && f_data[entry].start != FDATA_START_login_html) {
                send_to_login();
                goto do_send;
            }"""

httpd = re.sub(old_pattern, new_code, httpd, flags=re.DOTALL)

# 确保 GZIP 响应头正确注入
httpd = httpd.replace(r"Connection: close\r\nAccess-Control", r"Connection: close\r\nContent-Encoding: gzip\r\nAccess-Control")

httpd_path.write_text(httpd, encoding="utf-8")
print("  ✓ httpd.c: 静态文件鉴权已放开，GZIP 头已注入")
'

# 3. 注入完美的 DOM 级串行加载器 (修复作用域丢失)
python3 -c '
import os, re, json
from pathlib import Path
for p in Path("html").rglob("*.html"):
    html = p.read_text(encoding="utf-8")
    
    # 提取并移除外链资源
    css = re.findall(r"<link[^>]*href=\"([^\"]+\.css)\"[^>]*>", html)
    js = re.findall(r"<script[^>]*src=\"([^\"]+\.js)\"[^>]*></script>", html)
    html = re.sub(r"<link[^>]*href=\"[^\"]+\.css\"[^>]*>", "", html)
    html = re.sub(r"<script[^>]*src=\"[^\"]+\.js\"[^>]*></script>", "", html)
    
    # 提取并移除内联资源
    inline_js = []
    def ext(m):
        if "src=" not in m.group(1):
            inline_js.append(m.group(2))
            return ""
        return m.group(0)
    html = re.sub(r"<script([^>]*)>(.*?)</script>", ext, html, flags=re.DOTALL)
    
    if not css and not js and not inline_js: continue
    
    # 构造新的加载器 (内联脚本会通过创建 <script> 标签注入 body，完美保持全局作用域)
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
'

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
