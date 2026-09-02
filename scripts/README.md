# 辅助脚本备份

本目录备份了构建 / 刷写 / 调试 RTLPlayground 固件时用到的全部辅助脚本。
它们原本位于用户主目录 `~/` 下，不在 git 仓库范围内。

## 恢复

双击 **`第一步点我.command`**（或终端执行 `bash 第一步点我.command`）。

它按 `restore_manifest.txt` 把脚本复制回各自原位置。若目标已存在同名
文件，会先改名为 `xxx.bak.<时间戳>` 再覆盖，不会丢失已有内容。

## 主要脚本

| 脚本 | 用途 |
|---|---|
| `build_local.sh` | 本地构建固件。**必须先删 `html_data.*` 与 `output/$MACHINE`**，否则 HTML 改动不会进固件 |
| `build_tools_local.sh` | macOS 下构建 `tools/`。系统缺 glibc 的 `argp.h`，需手工构建后 `touch` 让 make 跳过 |
| `flash_local.sh` | CH341A 刷写固件，含读回校验 |
| `bump_version.sh` | 递增 Makefile 里的版本号 |
| `scan_scripts.py` | 扫描主目录下待备份的脚本 |
| `fix_*.py` / `fix_*.sh` | 历次调试的补丁脚本（幂等，可重复运行） |

## 注意

- 构建产物 `html_data.c`、`html_data.h`、`version.h`、`output/`、`tools/output/`
  均被 `.gitignore` 忽略，重新构建会自动生成，不在备份范围内。
- `Makefile` 在本地被打上了 `skip-worktree` 标记，工作区改动不被 git 追踪。
  恢复追踪：`git update-index --no-skip-worktree Makefile`
