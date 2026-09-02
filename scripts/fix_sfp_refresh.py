#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""main_info.js: 让信息表(含 SFP 插槽)可被手动刷新一次。

现状
----
main_info.js 只在 DOMContentLoaded 时 fetch('/information.json') 一次,
之后不再更新。首页刷新按钮只调 update()(/status.json), 管不到它,
所以点按钮后 SFP 插槽信息不变。

修法
----
把填充逻辑抽成全局函数 window.refreshInfoTable(), 支持重复调用:
每次先清空 tbody 再重建, 避免重复追加行。
刷新按钮仅在"手动点击"时调用它一次(自动轮询不调用, 避免请求量翻倍)。

幂等。在仓库根目录或 html/ 目录运行。
"""
import io, os, sys

if os.path.basename(os.getcwd()) != "html" and os.path.isdir("html"):
    os.chdir("html")
elif not os.path.exists("main_info.js"):
    sys.exit("✗ 请在仓库根目录或 html/ 目录运行")

p = "main_info.js"
s = io.open(p, encoding="utf-8", newline="").read()

if "window.refreshInfoTable" in s:
    print("  = 跳过: main_info.js 已改造")
else:
    OLD = '''document.addEventListener("DOMContentLoaded", function () {
    fetch('/information.json')
        .then(response => response.json())
        .then(data => {
            const tableBody = document.getElementById('infoTable').querySelector('tbody');

            // Create table rows
            for (const [key, value] of Object.entries(data)) {
                const row = document.createElement('tr');
                const cellKey = document.createElement('td');
                const cellValue = document.createElement('td');

                cellKey.textContent = t(infoKeyMap[key] || key);
                cellValue.textContent = value;

                row.appendChild(cellKey);
                row.appendChild(cellValue);
                tableBody.appendChild(row);
            }
        })
        .catch(error => console.error('Error fetching the data:', error));
});
'''
    NEW = '''function fillInfoTable(data) {
    const tbl = document.getElementById('infoTable');
    if (!tbl) return;
    const tableBody = tbl.querySelector('tbody');
    if (!tableBody) return;
    tableBody.innerHTML = '';

    for (const [key, value] of Object.entries(data)) {
        const row = document.createElement('tr');
        const cellKey = document.createElement('td');
        const cellValue = document.createElement('td');

        cellKey.textContent = t(infoKeyMap[key] || key);
        cellValue.textContent = value;

        row.appendChild(cellKey);
        row.appendChild(cellValue);
        tableBody.appendChild(row);
    }
}

window.refreshInfoTable = function () {
    fetch('/information.json')
        .then(function (r) { return r.json(); })
        .then(fillInfoTable)
        .catch(function (e) { console.error('Error fetching the data:', e); });
};

document.addEventListener("DOMContentLoaded", function () {
    window.refreshInfoTable();
});
'''
    if OLD not in s:
        sys.exit("✗ 未定位 main_info.js 的 fetch 块 <<<")
    s = s.replace(OLD, NEW, 1)
    io.open(p, "w", encoding="utf-8", newline="").write(s)
    print("  + 改造: main_info.js 抽出 window.refreshInfoTable()")

ip = "index.html"
h = io.open(ip, encoding="utf-8", newline="").read()

if "refreshInfoTable" in h:
    print("  = 跳过: index.html 已接入")
else:
    OLD2 = '''        update(function () {
          if (typeof updateTiles === "function") {
            updateTiles();
          }
        });
      }'''
    NEW2 = '''        update(function () {
          if (typeof updateTiles === "function") {
            updateTiles();
          }
          if (typeof window.refreshInfoTable === "function") {
            window.refreshInfoTable();
          }
        });
      }'''
    if OLD2 not in h:
        print("  ! index.html 未定位手动刷新回调 <<<")
    else:
        h = h.replace(OLD2, NEW2, 1)
        io.open(ip, "w", encoding="utf-8", newline="").write(h)
        print("  + 接入: index.html 手动点击时刷新信息表(含 SFP)")

print("\n自检:")
s = io.open(p, encoding="utf-8", newline="").read()
h = io.open(ip, encoding="utf-8", newline="").read()

checks = [
    ("main_info 有 refreshInfoTable", "window.refreshInfoTable" in s),
    ("main_info 有 fillInfoTable",    "function fillInfoTable" in s),
    ("main_info 清空 tbody",          "tableBody.innerHTML = ''" in s),
    ("index.html 调用 refreshInfo",   "refreshInfoTable" in h),
    ("index.html 仅手动时刷(1处)",    h.count("refreshInfoTable") == 1),
]
ok = True
for name, res in checks:
    print("  %-30s %s" % (name, "OK" if res else "失败 <<<"))
    ok = ok and res
print("")
print("✓ 全部通过" if ok else "✗ 存在问题")
