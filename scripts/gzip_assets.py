import os
import gzip
import shutil
from pathlib import Path

html_dir = Path(os.path.expanduser("~/Desktop/lt/RTLPlayground/html"))
for p in html_dir.rglob("*"):
    if p.is_file() and p.suffix in [".js", ".css", ".html"]:
        # 读取原文件内容
        with open(p, 'rb') as f_in:
            data = f_in.read()
        # 原地替换为 gzip 压缩后的数据
        with gzip.open(p, 'wb') as f_out:
            f_out.write(data)
        print(f"  ✓ {p.name} -> 压缩完成")
