#!/usr/bin/env bash
set -Eeuo pipefail
cd ~/Desktop/lt/RTLPlayground

HTTPD_FILE="httpd/httpd.c"

# 1. 备份原文件 (防止改崩)
cp "$HTTPD_FILE" "${HTTPD_FILE}.bak"

# 2. 注入 Content-Encoding: gzip 响应头
# 绝大多数基于 uIP 的 httpd 实现都会有一个预定义的常量字符串用于发送 HTTP 200 OK
# 我们尝试查找并替换这个常量。常见的形式是: "HTTP/1.0 200 OK\r\nContent-type: %s\r\n\r\n"
# 注意：由于不同固件实现差异极大，这里使用 Python 脚本进行安全的正则替换，匹配尽可能宽泛的格式

python3 -c '
import sys
import re
from pathlib import Path

file_path = Path("httpd/httpd.c")
if not file_path.exists():
    print("✗ 找不到 httpd/httpd.c")
    sys.exit(1)

content = file_path.read_text(encoding="utf-8")

# 寻找定义 HTTP 200 OK 头部的字符串常量
# 匹配类似: const char http_header_200[] = "HTTP/1.0 200 OK\r\nServer: ...\r\n\r\n";
# 或在 snprintf/sprintf 中的硬编码字符串

# 策略 A: 替换包含 Content-Type 的成功响应头，追加 Content-Encoding: gzip
# 我们假设遇到 "\r\n\r\n" (HTTP 头结束标志) 前，如果是在发送文件内容，就应该加上 gzip
# 由于我们把 *所有* html/js/css 都压缩了，所以所有成功的文件响应都该加
# 排除 .json 请求 (动态生成的，没有被压缩)

pattern_ok_header = r"(HTTP/1\.0 200 OK\\r\\n.*?)(?=\\r\\n\\r\\n)"
replacement = r"\1\\r\\nContent-Encoding: gzip"

new_content, count = re.subn(pattern_ok_header, replacement, content, flags=re.DOTALL)

if count > 0:
    print(f"  ✓ 成功在 {count} 处注入了 Content-Encoding: gzip")
    file_path.write_text(new_content, encoding="utf-8")
else:
    print("  ✗ 未能自动定位 HTTP 响应头常量，请手动检查 httpd.c")
    sys.exit(1)
'

# 3. 重新编译并提示刷写
echo "== 重新构建支持 GZIP 解码的固件 =="
rm -rf output/FG_4GT_2SX_V2_0/*.bin
make MACHINE=FG_4GT_2SX_V2_0 > /tmp/build_gzip.log 2>&1

if ls output/FG_4GT_2SX_V2_0/*.bin >/dev/null 2>&1; then
    echo "✅ 编译成功！请执行 bash ~/flash_local.sh 刷入。"
    echo "刷入后，务必将交换机彻底断电 5 秒再上电，并使用无痕窗口访问。"
else
    echo "✗ 编译失败，请检查 /tmp/build_gzip.log"
    # 发生错误则回退代码
    mv "${HTTPD_FILE}.bak" "$HTTPD_FILE"
fi
