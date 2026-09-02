#!/usr/bin/env bash
set -Eeuo pipefail
cd ~/Desktop/lt/RTLPlayground

# 1. 补全剩余静态文件的 GZIP 压缩 (.svg, .ico)
python3 -c '
import gzip
import os
from pathlib import Path
html_dir = Path(os.path.expanduser("~/Desktop/lt/RTLPlayground/html"))
for p in html_dir.rglob("*"):
    if p.is_file() and p.suffix in [".svg", ".ico"]:
        with open(p, "rb") as f_in: data = f_in.read()
        # 避免重复压缩
        if data[:2] == b"\x1f\x8b": continue
        with gzip.open(p, "wb") as f_out: f_out.write(data)
        print(f"  ✓ {p.name} -> 压缩完成")
'

# 2. 精准修改 httpd.c 的 strtox 字符串
sed -i '' 's/Connection: close\\r\\nAccess-Control/Connection: close\\r\\nContent-Encoding: gzip\\r\\nAccess-Control/g' httpd/httpd.c
echo "  ✓ HTTP 响应头已精准注入 Content-Encoding: gzip"

# 3. 清理旧产物并重新编译
echo "== 重新构建固件 =="
rm -rf output/FG_4GT_2SX_V2_0/*.bin
make MACHINE=FG_4GT_2SX_V2_0 > /tmp/build_gzip_final.log 2>&1

if ls output/FG_4GT_2SX_V2_0/*.bin >/dev/null 2>&1; then
    echo "✅ 编译成功！"
else
    echo "✗ 编译失败，请检查 /tmp/build_gzip_final.log"
fi
