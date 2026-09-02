RTLPlayground FG-4GT-2SX_V2.0 项目记忆体（修订版）

零、先说我的错（避免重蹈覆辙）

# 我的错误判断 真相 教训

1 分析 SFP 顺序时，直接用了 machine.c 里第一个机型的 .is_sfp = {0,0,0,1,0,0,0,0,2} 本机型实为 {0,0,0,2,0,0,0,0,1}，得出完全相反的结论 machine.c 有多组机型配置，引用前必须先确认属于哪一个

2 判断"顶部子菜单错位"是结构问题，把 tab-bar 移进容器后没同步改 <style> 里的 CSS 移进容器后 margin-left:16% 变成双重缩进（16% + 13.4% + 16px），制造了新 bug 移动元素必须同步改它的定位样式

3 自检统计 refreshInfoTable 出现次数，断言"应等于 2" 每处调用在源码里出现 2 次（typeof 判断 + 调用），2 处 = 4 次，误报失败 统计"调用了几处"应数 xxx() 而非裸名字

4 fix_sfp_refresh.py 沿用旧锚点匹配 index.html v5 已改过该段，锚点失效 给已多次修改的文件写补丁前先 grep 看实际内容

5 猜测 CI 产物名 v0.1.0-- 是 fetch-depth:1 浅克隆导致，加了 fetch-depth: 0 没解决。真凶是 Makefile 被 skip-worktree 屏蔽 + 容器内 git rev-parse 返回空 先诊断再改，别凭直觉下药（这次让你白跑了一轮 CI）

6 判断 CI 产物与本地 md5 不同"是 build_date 时间戳差异" 实际差 46%（8695 个零散区段）—— sdcc 版本差一个完整次版本 要用差异区段数与分布形态判断，不能想当然

7 首次 fix_sfp_refresh.py 的 heredoc 被终端截断，脚本没写成却让你执行 报 No such file 大段 heredoc 后必须先跑语法检查确认文件已生成

8 一开始假设"SFP 顺序错乱是前端按 logPort 排序" 前端完全没有排序逻辑，顺序 100% 由固件决定 先看代码再下结论，别先入为主

我做对的（可继续沿用）：
• pState 赋值位置是速率为空的根治点（提到 SVG 就绪检查之前）

• finalRefresh 注册在 load 回调内部是死代码（DOM 规范下本次派发不调用）

• tile 图标 SVG path 缺空格是原版既有缺陷（非我们引入）

• 侧边栏 fixed 240px 与 16% 混用必然错位

• 控制台报错来自浏览器扩展，与固件无关

• -dirty 应提交代码消除，而非改 Makefile 屏蔽

• 发布应选本地已硬件验证的二进制，而非未验证的 CI 产物

• 256 字节 RAM 约束下，常量对调优于加循环

一、环境

项 值

设备 FG-4GT-2SX_V2.0（4×RJ45 + 2×SFP）

管理 IP 192.168.0.253（网关 192.168.0.1，掩码 255.255.255.0）

认证 --anyauth -u admin:1234

本地仓库 ~/Desktop/lt/RTLPlayground

远程 origin = git@github.com:xlon72/RTLPlayground.git（fork，可写）<br>upstream = logicog/RTLPlayground（需 PR）<br>另有 Gitee 镜像 gitee.com/xlon7/RTLPlayground

相关仓库 xlon72/RY-4GT-2SX-UI-Firmware（8372ncn）

Shell zsh，未开 interactive_comments → 带 # 的注释行会报 command not found，须存文件后 bash 执行

macOS 差异 cat 无 -A（GNU 扩展），用 od -c；双击执行用 .command 后缀（.sh 会被文本编辑器打开）

刷写工具 CH341A + flashrom


1.1 冷启动检查清单（新会话开头跑一遍，输出贴给 AI 即可对齐状态）
bash
cd ~/Desktop/lt/RTLPlayground
git fetch origin
git log --oneline -3
git log origin/main..HEAD --oneline
git ls-files -o --exclude-standard
git ls-files -v | grep -v '^H '
git stash list
git branch -vv
ls ~/Desktop/lt/RTLPlayground/scripts/ | wc -l
预期：
• `origin/main..HEAD` 为空（没有未推送的提交）
• `ls-files -v` 只输出 `S Makefile`（skip-worktree 在位，无其他隐身文件）
• `scripts/ | wc -l` = **63**

⚠️ 因为 Makefile 被 skip-worktree，`git status` 永远 clean，**不能**用它判断有没有东西没交 —— 必须看 `git log origin/main..HEAD`。

二、交换机端口 / IO 对应（核心）

2.1 FG_4GT_2SX_V2.0 的端口映射


.min_port = 3,  .max_port = 8,  .n_sfp = 2,  .isRTL8373 = 0
.log_to_phys_port = {0, 0, 0, 6, 1, 2, 3, 4, 5}
.phys_to_log_port = {4, 5, 6, 7, 8, 3, 0, 0, 0}
.is_sfp           = {0, 0, 0, 2, 0, 0, 0, 0, 1}


phys_to_log_port 下标从 0 开始，代表物理口 N-1：

丝印物理口 index → logPort is_sfp[logPort] 类型

1 0 4 0 RJ45

2 1 5 0 RJ45

3 2 6 0 RJ45

4 3 7 0 RJ45

5 4 8 1 SFP（I2C 口号 1）

6 5 3 2 SFP（I2C 口号 2）

⚠️ 逻辑端口号与物理丝印顺序完全乱序：物理 6 → logPort 3（最小），物理 5 → logPort 8（最大）。这是所有"顺序反了"类 bug 的根源。

⚠️ is_sfp[] 按 logPort 索引，值是 I2C 口号（1 或 2），不是 0/1 槽位号 —— 差 1，别混用。

2.2 SFP 的 GPIO / I2C 引脚


                     sfp_port[0]                    sfp_port[1]
注释标注             "Left SFP port"                "Right SFP port"
pin_detect           GPIO38                         GPIO37
pin_los              GPIO_NA                        GPIO_NA
pin_tx_disable       GPIO_NA                        GPIO_NA
sds                  1                              0
i2c.sda              GPIO47_I2C_SDA0                GPIO49_I2C_SDA1
i2c.scl              GPIO46_I2C_SCL0                GPIO48_I2C_SCL1
reset_pin            GPIO_NA


⚠️ 注释里的 Left/Right 与实际硬件接线不符 —— 这正是"插丝印 5 口显示成插槽 2"的物理原因。已用编译期宏 SFP_SLOT_0/1 对调修正。

2.3 调用链（SFP 信息如何到网页）


page_impl.c:284  send_sfp_info(SFP_SLOT_0)  →  sfp_slot_0  →  网页"SFP 插槽1"
page_impl.c:288  send_sfp_info(SFP_SLOT_1)  →  sfp_slot_1  →  网页"SFP 插槽2"
                      ↓
send_sfp_info(sfp): sfp_read_reg(sfp, i)      ← 参数原样传递，不做端口换算
                      ↓
sfp_read_reg(slot, reg)  @ rtlplayground.c:1048


⚠️ 未解点：is_sfp[] 存 1/2（I2C 口号），send_sfp_info() 传 0/1（槽位索引），两者差 1，但 sfp_read_reg() 内部实现我们从未读过。宏对调已通过实测验证（SFP 编号正确），但底层语义仍不明。若将来要改通用化方案，必须先读 rtlplayground.c:1048。

2.4 LED


Ports 1-4 (RJ45)  → LED set 0
Ports 5-6 (SFP)   → LED set 1
Ports 1-4: Green = 2.5GBit, Amber = 10/100/1000MBit
Ports 5-6: Green = 100MBit–10GBit

（来源：machine.c 中该机型的注释，未经实测验证）

2.5 其他机型的 is_sfp（仅供对照，勿套用）

机型 n_sfp .is_sfp sfp_port[0] I2C sfp_port[1] I2C

FG_4GT_2SX_V2.0 2 {0,0,0,2,0,0,0,0,1} GPIO47/46 (SDA0/SCL0) GPIO49/48 (SDA1/SCL1)

machine.c 第 1 个 2 {0,0,0,1,0,0,0,0,2} GPIO41/40 (SDA3/SCL3) GPIO39/40 (SDA4/SCL3)

machine.c 中 n_sfp=1 的 1 {0,0,0,0,0,0,0,0,1} GPIO39/40 (SDA4/SCL3) —

三、构建与刷写

3.1 构建必须清缓存（血泪教训）

rm -f html_data.c html_data.h
rm -rf output/$MACHINE

不清的话 HTML 改动不会进固件，但版本号照常递增，极具迷惑性，曾连续三次刷写无效。

原因：HTML 经 fileadder/injector 打包进固件，html_data.c 只是 3KB 元数据索引，真正的 HTML 由 injector 写入最终 .bin。

3.2 macOS 构建 tools 的坑

tools/ 缺 glibc 的 argp.h，Makefile 用裸 gcc（不带 -I/-l）。
解法：手工构建后 touch output/*，让 make 认为已是最新从而跳过重建。

3.3 刷写

CH341A + flashrom，镜像标准 2MB（前 512KB 为固件，其余填充 0xFF）。刷前先备份原 flash。flash_local.sh 含读回校验。

3.4 判断两份二进制是否等价

不能只看 md5（构建时间戳会变），也不能只看大小：

差异形态 含义

8695 个零散区段、最大单段 1113 字节、占 46% 编译器版本差异

集中 1–2 个小段 数据 / 时间戳差异

3.5 内部 RAM 只有 256 字节（OSEG 极易溢出）

任何新增局部变量都可能触发溢出。改 C 代码优先选"零新增变量"方案。

UIP_CONNS=8 已验证不可行（折腾七轮，CI 失败后 revert）。改动现存在 stash@{0}，建议归档为 patch 作反面记录，不要应用。

四、已修复的问题（v0.9.7，均已刷写验证）

问题 根因 修法

SFP 插槽编号与丝印相反 machine.sfp_port[] 顺序与物理布局相反 编译期宏 SFP_SLOT_0/1 对调（仅 FG_4GT_2SX_V2_0，零 RAM 开销）

链路速率首次加载为空 main.js 中 pState[n] 赋值在 SVG 就绪检查之后，首次请求 port.svg 未加载完导致整轮 continue 跳过 赋值提前到检查之前

控制台 SVG 报错刷屏 tile 图标 path 缺空格：m611 6-6 6 6 → m6 11 6-6 6 6（原版缺陷） 补空格

"加载后刷新"从未生效 addEventListener("load", finalRefresh) 写在 load 回调内部，按 DOM 规范本次派发不调用 改为直接 setTimeout

系统设置页标签错位 .tab-bar 在 <nav> 之前且自带 margin-left:16%，与 fixed 240px 侧边栏对不齐 移入内容容器 + 去掉冗余 margin/padding

固件升级页重复提示 硬编码中文 + data-i18n 空值导致切语言不生效 接入 i18n，补中/日/英三语

刷新不更新 SFP information.json 只在页面加载时请求一次 抽出 window.refreshInfoTable()，手动点击 + finalRefresh 各调一次（自动轮询不调）

新增：首页右上角"自动刷新"开关，默认关闭。

前端 CSS 布局要点


#sidebar: position:fixed; width:240px; z-index:10;  ← 脱离文档流，不占位
内容容器: margin-left:16%; padding:1px 16px;         ← 靠 margin 手动避让

百分比与固定像素混用必然错位：视口 1200px 时 16%=192px < 240px（被压住），1920px 时 16%=307px > 240px（多缩进）。子菜单等元素应放在容器内，不要自己再写 margin-left:16%。

五、Git / CI

5.1 Makefile 被打上 skip-worktree（重要）


git ls-files -v | grep -v '^H '   →   S Makefile

git 永久忽略它的工作区改动：
• 本地 VERSION = v0.9.7（bump 脚本改的）

• 仓库里永远是 VERSION=0.1.0（上游默认值）

  ⚠️ 修正（2026-09-03 实测 diff）：仓库版 VERSION_EXTENSION **本身带 v**：
     `VERSION=0.1.0` + `VERSION_EXTENSION = v$(VERSION)-$(GIT_VERSION)`
     → CI 实际拿到 `v0.1.0-<hash>`，不是 `0.1.0-<hash>`。
     `v0.1.0--` 的唯一成因是容器内 `git rev-parse --short HEAD` 返回空，与 v 前缀无关。

• git status 永远显示 clean

CI 版本号退化链条：Makefile 硬编码 VERSION 且被屏蔽 → CI 拿到 0.1.0；容器内 git rev-parse --short HEAD 返回空 → hash 为空 → VERSION_EXTENSION = $(VERSION)-$(GIT_VERSION) → 产物名 v0.1.0--。

建议保持现状：CI 定位为"编译验证"。Makefile 硬编码版本号与 git tag 天然无法同步，强求产物名有意义会带来维护负担。发布用本地已硬件验证的二进制。
恢复追踪：git update-index --no-skip-worktree Makefile

诊断同类问题：git ls-files -v | grep -v '^H '（S=skip-worktree，h=assume-unchanged）

5.1.1 本地 Makefile 差异（实测精确值，删本地后可原样重建）

`git show HEAD:Makefile` 与工作区 Makefile 的 diff 只有 2 行，且成对自洽（把 v 从 EXTENSION 移进 VERSION）：
-VERSION=0.1.0 +VERSION = v0.9.7
-VERSION_EXTENSION = v(VERSION)−(GIT_VERSION) +VERSION_EXTENSION = (VERSION)−(GIT_VERSION)
⚠️ `SOURCE_DATE_EPOCH` 确定性构建日期逻辑是**上游自带**的（diff 未涉及），不是本地改动。
这条很关键：它意味着同 commit 构建本应字节一致 → 反推出 CI 与本地 46% 的差异确实来自 sdcc 版本（4.5.0 vs 4.6.0），而非时间戳。

5.1.2 第一步点我.command 内置 Makefile 重建

因为 Makefile 不进 git，它上面的 2 行本地改动会随删本地而丢失。
`第一步点我.command` 已在末尾加入重建段（变量统一 `LP_` 前缀，3473 字节，权限 755）：

• `LP_REPO_DIR` = 脚本所在目录的上一级 = 仓库根（脚本永远在 `scripts/` 下，且 restore_manifest.txt 不含它自己，不会被复制到 `~/`）
• 改动前先 `cp -p Makefile /tmp/Makefile.bak.<时间戳>` —— **备份落 /tmp 不落仓库**，否则会变成未跟踪文件触发 `-dirty`（撞 §6 那条规矩）
• 重建后自动 `git update-index --skip-worktree Makefile`，让 `git status` 保持 clean
• sed 用 `[$]` 字符类而非 `\$`，BSD/GNU 行为一致

已硬验证：仓库版 Makefile 经该脚本改造后，与本地 Makefile **字节一致**（`REBUILD_IDENTICAL`）。

5.2 CI 配置（已现代化）

on: push: branches: ['**'] + workflow_dispatch   # 无 tags 触发 → 打 tag 不会多跑构建
actions/checkout@v7 + fetch-depth: 0            # 原 v4 target node20
actions/upload-artifact@v7                       # 同上
name: firmware-FG_4GT_2SX_V2_0                  # 原 firmware-nosfp（名不副实）
path: output/**/*.bin                            # 原 output/*.bin（单星号不跨 '/'）
含 "Show toolchain versions" 步骤
无 release workflow → Release 需手动创建

• Node20 于 2026-09-23 从 runners 彻底移除；v4 靠强制兼容层跑 Node24，已升级到原生 v7

• CI sdcc 4.5.0（debian:trixie apt）vs 本地 4.6.0（Homebrew）—— 46% 字节差异主因之一。建议不对齐（对齐需从源码编译，CI 从 1.5 分钟涨到十几分钟）

六、发布

v0.9.7 已发布：https://github.com/xlon72/RTLPlayground/releases/tag/v0.9.7
资产 rtlplayground-v0.9.7-0741ae1-FG_4GT_2SX_V2_0.bin（524288 字节，已硬件验证）

git push origin main
→ SHA=$(git rev-parse HEAD); 轮询 gh run list 取 RUN_ID; gh run watch "$RUN_ID"
→ gh run download "$RUN_ID" --name firmware-FG_4GT_2SX_V2_0
→ 验证 524288 字节 / 版本串正确 / 无 -dirty
→ git tag -a v0.9.7; git push origin v0.9.7
→ gh release create v0.9.7 <bin> --title "v0.9.7" --notes-file /tmp/notes.md


build.yml 无 tags 触发 → 打 tag 不产生多余 CI 运行，也不干扰产物下载。

去掉 -dirty 靠提交代码，不是改 Makefile。提交前须清掉未跟踪文件（git status --porcelain 含 ?? 仍判 dirty）。

七、零散但会再踩的坑

• 控制台报错先看来源路径：userscript.html?name=... 是浏览器扩展（Mactype / 夜间模式 / Immersive-Translate / 网盘助手 / 星号密码显示），与固件无关。设备代码路径是 index.html / main.js / i18n.js

• grep 验证不了编译期宏：#define 预处理后消失，只能行为验证

• grep -c 无匹配返回 1，会触发 set -e 退出，脚本里要 || echo 0 兜底

• heredoc 写脚本后必须跑语法检查确认文件生成完整

• YAML 片段不能直接粘终端（- name: / run: 会 command not found）

• 查询 Action 最新版本：gh api repos/<owner>/<repo>/releases/latest --jq '.tag_name'，别猜版本号

• 复制命令别带终端提示符 

• **`.DS_Store` 会污染仓库**：macOS Finder 逛过的目录都会生成。根目录的曾被历史 `git add -A` 误提交进索引（表现为 `git status` 里 ` D .DS_Store`，第一列空格=仍被跟踪，文件本身却已删除）。
  → 清理：`git rm --cached .DS_Store`，并在 `.gitignore` 补 `**/.DS_Store`（不带前导斜杠，否则只对根目录生效）
  → 提交前先 `find . -not -path './.git/*' -name '.DS_Store' -print -delete`，再 `git ls-files -o --exclude-standard` 确认为空

• **zsh 粘贴多行命令时 `# 注释` 会变实参**：未开 `interactive_comments`。`git log --oneline -5` 后跟 `# 注释` 报 `ambiguous argument '#'`；`grep -v '^H ' # 说明` 更危险 —— grep 一旦拿到文件参数就**不再读 stdin**，管道上游输出被丢弃，转而 grep 了那个文件（曾把整个 Makefile 原样吐出，伪装成检查结果）。
  → 贴给 AI 的命令一律去掉行尾注释；`2>/dev/null` 也别乱加，会把"目录不存在"伪装成 0

八、待办（按优先级）

~~第一步点我.command 特性~~ ✅ **已完成并验证**（2026-09-03），不再是待办：

• 用 `${BASH_SOURCE[0]}` 定位自身目录（双击时 cwd 是 `~`）
• 目标已存在则先改名 `.bak.<时间戳>` 再覆盖
• 恢复后 `chmod +x`
• 末尾追加了 Makefile 本地改动重建段（见 §5.1.2）

可选

• 发 PR 给上游 logicog/RTLPlayground

• 读 rtlplayground.c:1048 搞清 sfp_read_reg() 参数语义（当前未解）

• 实测验证 LED 行为（目前只有注释依据）

九、本地脚本归档（2026-09-03 完成）

`scripts/` 共 **63 个文件**，随仓库一同推送；`output/` 下所有固件按 .gitignore 忽略，不入库。

| 类别 | 内容 | 数量 |
|---|---|---|
| 主脚本 | `build_local.sh` `build_tools_local.sh` `build_flash.sh` `flash_local.sh` `serial.sh` | 5 |
| 历史 fix/diag/patch 脚本 | 其余 `.py` / `.sh` | 53 |
| 文档 | `README.md`、`restore_manifest.txt`、`RTLPlayground_记忆体.md` | 3 |
| 归档 | `uip_conns_8_experiment.patch`（已验等于 `stash@{0}`） | 1 |
| 恢复入口 | `第一步点我.command`（755） | 1 |

⚠️ `restore_manifest.txt` **只有 58 条纯 `.py`/`.sh`**，不含 README / manifest / patch / command / 记忆体。
→ 恢复时这 5 个文件**不会被复制到 `~/`**，只留在 `scripts/` 里。这也是 `第一步点我.command` 能用 `..` 定位仓库根的前提。

删除本地后即丢失、且已确认可接受：

| 内容 | 处置 |
|---|---|
| `output/` 所有固件 | 放弃（v0.9.7 已在 GitHub Release） |
| Makefile 两行版本改动 | 放弃，由恢复脚本重建（§5.1.2） |
| `stash@{0}` 条目本身 | 放弃，内容已存 `uip_conns_8_experiment.patch` |
| `.git/` reflog | 无其他分支，无影响 |

三条硬事实（删本地后复用）：
• 已发布：`v0.9.7` @ `0741ae1`，`rtlplayground-v0.9.7-0741ae1-FG_4GT_2SX_V2_0.bin`，524288 字节，硬件验证通过
• `0741ae1..f422c4a` 只改了 `.github/workflows/build.yml` → **当前源码与已发布二进制等价**
• 本地 = `origin/main` @ `f422c4a`，无未推送提交

⚠️ 已公开信息（若仓库为 public）：管理 IP 192.168.0.253、出厂口令 `admin:1234`、Gitee 镜像地址均已随本文件进入仓库。

---

## 附：2026-09-03 补充（第二批）

> 追加式补充，按主题分条编号，供正文交叉引用。

### §A 设备型号对应关系（补充 §1）

整机对外型号是 **NPA AP-7024-2.5G**；`FG_4GT_2SX_V2_0` 只是 `machine.c` 里的编译配置名。

出处：v0.9.7 release notes 首句「面向NPA AP-7024-2.5G,基于上游logicog/RTLPlayground。管理界面192.168.0.253默认密码1234」。

⚠️ 因此 **192.168.0.253 / admin:1234 早已在 Release 页公开**，与记忆体内容一致 —— 本文件进仓库不产生额外暴露。Gitee 镜像地址仅见于本文件，若在意需单独处理。

### §B 错误 #9 / #10（接续正文错误清单）

9 **生成记忆体更新脚本时，把备份写成了 `TARGET + .bak.<时间戳>`（即仓库内 `scripts/` 下），随即被 `git add scripts/` 一并暂存。**
   而同一批 §5.1.2 里刚写下「备份落 /tmp 不落仓库，否则会变成未跟踪文件触发 `-dirty`」—— 写进记忆体的规矩自己第一个违反。
   → **脚本生成的备份一律写死 `/tmp`，不得落在会被 `git add` 覆盖的目录内。**

10 **用 `git status --short | grep -c '^A  scripts/'` 数暂存文件数得 61，实际是 63。**
   git 对非 ASCII 路径加双引号：`A  "scripts/第一步点我.command"`，引号使前缀匹配不上，2 个中文文件名被静默漏掉。
   → 计数用 `git diff --cached --name-only -- <dir> | wc -l`（输出不加引号，无此问题）
   → 需安全处理任意路径用 `git status --porcelain -z`（NUL 分隔）
   → 或 `git -c core.quotepath=false status --short`（但含空格的路径仍会加引号）

### §C 易踩坑（补充 §7）

• **`git status --short` 的输出不能直接做前缀匹配** —— 见 §B 错误 #10。

• **脚本生成的备份文件必须落 `/tmp`** —— 见 §B 错误 #9。

• **给 AI 贴的 Python heredoc 要防截断**：大段中文塞进 `"""..."""` 经终端粘贴易损坏（曾报 `EOF while scanning triple-quoted string literal`）。改用「纯文本 heredoc 落盘 + 短 Python 脚本读取追加」，文本末尾放结束标记，脚本先校验标记存在再写入。

• **`.gitignore` 可能没有换行结尾**：实测尾部 `tools/fileadder` 无尾随换行。追加规则用 `printf '\n**/.DS_Store\n'`，并用 `cat -e` 确认行尾有 `$`。

• **`.DS_Store` 的处理口径（补充 §7）**：根目录的曾被误提交进索引，表现为 `git status` 里 ` D .DS_Store` —— **第一列是空格**表示索引里仍在、工作区已删、删除未暂存。处理：`git rm --cached .DS_Store` + `.gitignore` 追加 `**/.DS_Store`（不带前导斜杠，否则只对根目录生效，挡不住 `doc/` `tools/` `output/` 下的）。

### §D v0.9.7 release notes 原文（补充 §6，下次发布直接改这份）
面向NPA AP-7024-2.5G,基于上游logicog/RTLPlayground。管理界面192.168.0.253默认密码1234
SFP 插槽编号与机身丝印相反 —— 插入丝印 5 口的光模块此前显示为"插槽 2"。send_sfp_info() 将槽位索引原样传给 sfp_read_reg()，而该机型 machine.sfp_port[] 的顺序与丝印 5/6 相反。现以编译期宏对调（仅影响 FG_4GT_2SX_V2_0，不增加 RAM 占用）。
首次进入页面时链路速率为空 —— main.js 中 pState[n] 的赋值位于 SVG 就绪检查之后，首次请求时 port.svg 尚未加载完，导致整轮被 continue 跳过。现改为在检查之前赋值，速率进页面即有值，无需手动刷新。
首页 tile 图标 SVG 报错 —— TX/RX 图标 path 数据缺少空格（m611 6-6 6 6 → m6 11 6-6 6 6），控制台持续报 Unexpected end of attribute。
"加载完成后刷新"从未生效 —— finalRefresh 注册在 load 事件回调内部，按 DOM 规范本次派发不会调用它，属死代码。改为直接 setTimeout 调用。
系统设置页标签栏错位 —— .tab-bar 位于 <nav> 之前且自带 margin-left:16%。（原文档此处被截断，完整表述见 §4）
固件升级页重复提示 —— 删除硬编码中文提示；下方英文提示 data-i18n 为空值导致切语言不生效，现已接入 i18n 并补齐中/日/英三语。
手动刷新不更新 SFP 信息 —— information.json 此前只在页面加载时请求一次。现抽出 refreshInfoTable()，点击右上角刷新时同步更新。
本二进制在 macOS (Apple Silicon) + Homebrew sdcc 4.6.0 下构建，并在 FG_4GT_2SX_V2_0 硬件上实际刷写验证通过。
仓库 CI（debian:trixie + apt sdcc）产出的二进制与本文件存在约 46% 的字节差异，源于编译器版本不同导致的代码布局差异（源码均为 commit 0741ae1）。CI 产物未经硬件验证，故本次发布采用本地验证版。
使用 CH341A 等编程器写入，镜像为标准 2MB（前 512KB 为固件，其余填充 0xFF）。刷写前请先备份原有 flash 内容。
### §E 归档最终口径（修正 §9）

`scripts/` 共 **63** 个文件（含本文件）。冷启动校验用 `git diff --cached --name-only -- scripts/ | wc -l`，应为 **63**；连同 `M .gitignore` 与 `D .DS_Store` 一起计数时为 **65**。

`git rm --cached .DS_Store` 已执行（该文件此前被误提交进索引）。`.gitignore` 已追加 `**/.DS_Store`。

<!-- PATCH2-END -->
