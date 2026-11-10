---
name: yab
description: >
  在 YAB（原 BAAS，蔚蓝档案自动化脚本，仓库名 blue_archive_auto_script）项目中
  开发、排查、审查、识别回归、打包或修改安装器时使用，涵盖设备、调度、配置、商店与活动提示、
  网页、通知、轻量发行、关窗轻量模式、启动反馈及 Electron（桌面壳）与 NSIS（安装器）发行。不用于其他桌面项目、Alasio 或
  StarRailCopilot 本身的开发，也不用于游戏玩法咨询。
---

# YAB（原 BAAS，blue_archive_auto_script）

蔚蓝档案自动化脚本，现名 YAB，技能名与目录统一为 `yab`。曾用 PyQt5 GUI（`gui/` + `window.py`，已删除），现用 WebUI：
Python 后端 `server/`（starlette/uvicorn）+ Svelte 5 前端 `webapp/`（pnpm + Vite 8）。
主开发分支 `dev`，仅本地提交（禁止 push，除非用户明确要求）。

## Always Read
- 本说明包含仓库结构、常用入口和容易踩到的问题；只读当前任务对应的参考。
- 改启动、配置、设备、通知或网页协议前，读 [架构参考](references/architecture.md)。
- 改桌面构建、运行准备、配置迁移或安装界面前，读 [桌面发行与安装器](references/desktop-packaging.md)。
- 改活动提示识别或离线样本回归前，读 [识别与截图回归](references/offline-regression.md)。
- 维护本技能时，用 [技能核对用例](references/skill-evals.md) 检查范围与行为；静态核对不等于自动触发实测。

## Repo Map
```
core/            # 自动化核心
  Baas_thread.py #   主线程: 信号、调度循环 thread_starter、完成动作 handle_then
  scheduler.py   #   event.json 调度器 (heartbeat/systole/is_wait_long)
  config/        #   config_set.py(ConfigSet), default_config.py(全部默认模板),
                 #   generated_user_config.py(109字段 dataclass), config_init.py(启动迁移)
  device/        #   adb_devices.py(通用设备连接), connection.py, Screenshot.py/Control.py(分发)
  ocr/           #   baas_ocr_client(源码启动可准备 bin/，完整发行内置识别资源；bin/ 禁止提交)
module/          # 游戏任务 (func_dict 在 core/Baas_thread.py 顶部注册, key=task func_name)
server/          # WebUI 后端: hub.py(协议), service.py(任务与配置), app.py(路由), panels.py(面板 schema), frontend.py(构建), security.py(访问保护)
webapp/          # WebUI 前端: Svelte5+Vite, src/lib/ws.ts 协议客户端, src/lib/i18n/(多语言), src/lib/components/fields/(13 种字段控件), build→dist 由后端 serve
desktop/         # Electron 桌面壳、完整与轻量发行：build.cjs/bundle.py/runtime.cjs；NSIS 安装与卸载脚本
src/             # 图像模板/rgb_feature/maatouch_bin 等静态资源
config/          # 运行时生成 (gitignored): <dir>/config.json|event.json|switch.json + static.json
deploy/          # installer(MirrorChyan 启动器)/docker/standalone(webui.whole.spec)
```

Alasio（框架参考）和 StarRailCopilot（设备方法参考）仅供只读参考，按用户提供的检出路径定位，不作为 YAB 的运行依赖。

## 运行环境

- 在 Codex（编程助手）中执行命令，直接使用其 PowerShell（命令行）执行工具与自身审批流程，不通过 PyCharm（开发工具）转发命令。
- Python（运行环境）默认用 3.11，兼容范围为 `>=3.9,<3.13`；当前 `av==12.0.0`（视频解码依赖）不适合直接用 3.13 及更新版本安装。
- Vite 8（前端构建工具）的 Node.js（前端运行环境）要求是 `^20.19.0 || ^22.12.0 || >=24.0.0`。前端工具由开发者自行准备，沿用本机路径、版本和配置；pnpm（前端包管理器）不固定版本，已验证 12 系列可用。
- `server/frontend.py` 复用未过期的网页产物，需要构建时调用本机工具；缺少工具或运行环境过旧会提示准备要求，不自动下载或切换环境。完整发行包直接使用内置网页，缺失时明确报错。

## Common Tasks

| 任务 | 要点 |
|---|---|
| 源码启动 | 项目根目录运行 `uv sync --python 3.11`，再运行 `uv run python -m server --open`；默认本机端口 22267。无网页任务入口仍是 `main.py` |
| 前端开发 | 后端运行 `uv run python -m server --api-only --port 8000`；另一个终端进入 `webapp`，运行 `pnpm install --frozen-lockfile`、`pnpm dev`，网页代理到 8000 端口 |
| 网页构建与打包 | `uv run python -m server.frontend --force` 强制重新构建；完整程序打包前必须已有 `webapp/dist/index.html` |
| 网页监听设置 | 读 [架构参考](references/architecture.md) 与 [桌面网页访问](references/desktop-packaging.md#8-桌面网页访问)；源码与桌面默认共用本机 22267 端口，设置全局保存、重启生效，端口冲突明确报错 |
| 弹窗宽度与网页图标 | 读 [弹窗与网页图标](references/architecture.md#弹窗与网页图标)；输入框撑满内容区并核对宽窄屏，标签与侧栏共用图标，静态目录也参与产物过期判断 |
| 活动提示、公告与截图回归 | 读 [识别与截图回归](references/offline-regression.md)；区分两类弹窗，命中稳定特征后点击关闭位置，回放重复帧与点击未生效，不能用点击代替成功确认 |
| 商店漏识别或购买循环 | 读 [商店识别与有限重试](references/architecture.md#8-商店识别与有限重试)；按固定列编号、补查缺列、限制重试，再用已有截图及模拟缺项回归核对 |
| 配置生效与热更新 | 读 [配置生效时机](references/architecture.md#配置生效时机)；分清文件、网页与任务副本。热更新暂缓，不能把每日刷新或调度重读当成全部配置热更新 |
| 帮助文档配色 | 读 [前端开发](references/architecture.md#6-前端开发)；维护独立文档画布并运行隐藏浏览器渲染检查，不批量改源文档 |
| 通知渠道与旧来源 | 读 [通知入口与来源](references/architecture.md#9-通知入口与来源)；远程推送和本机通知分开追查，测试拦截真实发送，保留安装身份并核对源码与包内版本 |
| 远程访问 | 先通过环境变量设置 `BAAS_WEBUI_TOKEN`（网页访问密码），再监听其他地址；设置后本机访问也需要登录。密码不写入项目文件 |
| 连接安卓设备 | `core/device/adb_devices.py` 提供通用设备发现与连接；真机、模拟器和 redroid（容器安卓设备）共用入口。模拟器自动启动是可选配置，不是设备连接前提 |
| 加配置项 | `core/config/default_config.py` 的 DEFAULT_CONFIG 加键 → 重新生成 dataclass（develop_tools/generate_dataclass_code.py，产物 generated_user_config.py）→ 前端 Settings/Advanced 泛化渲染；下拉枚举再补 server/app.py build_meta() |
| 加结构化面板 | `server/panels.py` 的 PANELS 加面板/字段（options_from 解析器按 server_mode 解析选项）→ 前端 `webapp/src/lib/components/fields/FieldControl.svelte` 分发渲染；值经 ConfigArg topic/set RPC 读写，**类型必须与 config.json 现值一致**（用 coerce 标注转换） |
| 加/改翻译 | 手工词条只改 `webapp/src/lib/i18n/overrides.ts`（三语言尽量同补，不确定的宁缺毋滥）；`locales/*.ts` 是从旧 Qt .ts 自动生成的**勿手改**，上游更新后跑 `python develop_tools/extract_i18n_from_ts.py` 重新生成。UI 中一律 `$t('中文原文')`，脚本代码用 `tNow()`，复合文案用 `'{0}'` 占位 + `.replace('{0}', () => v)` |
| Electron 壳 | 开发运行 `cd desktop && pnpm start`；无头冒烟 `pnpm run smoke`（拉起后端→健康检查→杀进程树，exit 0 为过）；python/端口/根目录用环境变量 BAAS_PYTHON/BAAS_DESKTOP_PORT/BAAS_ROOT 覆盖 |
| 加截图/控制方式 | `core/device/screenshot|control/<name>.py` 实现方法 → Screenshot.py/Control.py 分发 → default_config.py 的方法列表；静态配置每次启动重写，改模板才有效 |
| 加完成动作 | `core/Baas_thread.py: handle_then()` 按中文字符串精确匹配 `config.then`；下拉选项补 server/app.py THEN_OPTIONS |
| 加游戏任务 | module/<task>.py 写 `implement(self)` → core/Baas_thread.py func_dict 注册 → default_config.py EVENT_DEFAULT_CONFIG 加事件 |
| 改网页协议 | server/hub.py、server/app.py 与 webapp/src/lib/ws.ts 保持一致；修改配置或任务状态后推送相应主题，设备查询和连接通过调用回执返回结果 |
| 本地验证 | 按改动选用架构参考中的启动、访问保护和设备离线回归；网页修改运行 `pnpm run check` 与 `pnpm build --emptyOutDir false`。协议修改还需验证实际接口收发 |
| 关窗轻量模式与页面提示 | 读 [窗口与页面提示](references/desktop-packaging.md#12-关窗轻量模式与页面提示)；区分轻量发行与页面释放，保存关窗选择，核对恢复、稳定布局及悬停到期 |
| 桌面预览与表单回归失败 | 读 [主题与原生控件](references/desktop-packaging.md#4-暗黑模式与高分屏) 和 [回归隔离](references/desktop-packaging.md#回归隔离与诊断)；统一主题来源、串行运行原生预览，表单回归独立构建最新网页 |
| 构建目录与缓存整理 | 读 [目录归属](references/desktop-packaging.md#13-构建目录与缓存归属)；中间目录可重建，缓存和正式产物分开，遵守用户不删除文件的约定并核对测试跳过 |
| 桌面发行与批量发包 | 读 [发行变体与工具](references/desktop-packaging.md#轻量发行与工具定位)；默认完整包，轻量包按锁定清单在线准备；三种发包复用共享配置，预览不代表构建成功 |
| 桌面版本、配置与升级 | 读 [版本与配置](references/desktop-packaging.md#2-版本配置与品牌兼容)；二开版本与固定上游基准分开，程序旁保存配置，运行环境在用户数据目录，升级保留原件 |
| 启动进度、日志与过渡 | 读 [启动反馈](references/desktop-packaging.md#10-启动反馈)；按真实阶段和输出更新，主界面加载成功后完成并淡出，失败保留日志，检查减少动态效果和页面访问限制 |
| 安装界面与卸载 | 读 [桌面发行与安装器](references/desktop-packaging.md)；浏览后在原输入框显示最终目录，无二次确认或下方预览；卸载默认勾选保留数据；改脚本后正式编译 |
| 安装器复选框素材 | 读 [复选框素材更新](references/desktop-packaging.md#复选框素材更新)；固定上游与许可，生成多尺寸透明图片后重建插件，验证真实状态并重打两种发行包 |
| 安装总进度 | 读 [进度计算与模板扩展](references/desktop-packaging.md#9-安装总进度与模板扩展)；保留打包器原始计数，按实际阶段显示不回退的估算总进度，成功回调才到 100% |
| 页面返回与弹窗主题 | 读 [安装器易错点](references/desktop-packaging.md#6-nsis安装器工具的易错点) 和 [主题与原生控件](references/desktop-packaging.md#4-暗黑模式与高分屏)；保留提权后恢复和后退、清除共享按钮盾牌；分别检查初始化、界面和安装卸载工作线程、桌面消息及系统选择窗口 |
| 其他 YAB 改动 | 按仓库结构定位；涉及启动和配置先读架构参考，涉及桌面发行先读桌面参考，不套用其他项目的安装方式 |

## Known Gotchas
- **旧通知来源不由远程推送设置决定**：分别检查本机系统通知和远程渠道；旧包与历史消息不会随源码自动更新。见 [通知入口与来源](references/architecture.md#9-通知入口与来源)。
- **原生预览与旧网页会使回归误判**：主窗口和插件共用主题来源，原生测试串行、按真实状态采样；表单测试独立构建当前网页。见 [回归隔离与诊断](references/desktop-packaging.md#回归隔离与诊断)。
- **点击不等于弹窗已关闭**：活动提示检测左下角，公告保留独立特征；用后续画面确认结束，帧耗尽应失败。见 [识别与截图回归](references/offline-regression.md)。
- **包含路径不能覆盖编译当前目录**：复制完整打包模板，切到生成目录后编译，并校验卸载主题模板已加载；保留上游同名文件与检查逻辑。见 [模板扩展](references/desktop-packaging.md#9-安装总进度与模板扩展)。
- **输入框与网页图标要看实际页面**：内容区宽度、窄屏溢出、标签与侧栏分别核对；构建成功或桌面图标正常不能代替。见 [弹窗与网页图标](references/architecture.md#弹窗与网页图标)。
- **漏掉一列不能让商品编号前移**：缺项先补识别，失败必须有限退出；截图能识别不代表复现了实际漏检。见 [商店识别与有限重试](references/architecture.md#8-商店识别与有限重试)。
- **保存不等于运行参数已生效**：任务主要用初始化副本，网页靠服务推送；外部文件修改没有统一热更新。见 [配置生效时机](references/architecture.md#配置生效时机)。
- **桌面发行不是旧冻结方式**：完整包内置独立解释器、离线依赖和识别资源；默认不恢复 PyInstaller（冻结打包工具）。见 [桌面发行流程](references/desktop-packaging.md#1-完整发行流程)。
- **显示名与兼容标识分开**：技能名为 `yab`，对用户显示 YAB；保留安装标识和必要环境变量。默认数据只用新版目录，不自动复用或清理原 BAAS 数据；配置迁移保留原件。见 [版本与配置](references/desktop-packaging.md#2-版本配置与品牌兼容)。
- **安装目录必须所见即所得**：浏览回调立即补目录并回填原输入框；安装阶段不能再追加。当前关闭默认目录页是有意使用自定义页。见 [安装目录约定](references/desktop-packaging.md#3-安装目录的最终约定)。
- **安装器版本与素材**：暂沿用打包器定制版，不因官方有新版本直接替换；先检查真实字体和素材尺寸，再运行原生控件绘制回归与正式编译。见 [暗黑模式与高分屏](references/desktop-packaging.md#4-暗黑模式与高分屏)。
- **进度计数不能直接混用**：安装指令与解压插件共用原控件，但范围不同；不要只把 100% 截成 99%。按实际阶段映射到独立显示条，保留文件占用重试和成功条件。见 [总进度与模板扩展](references/desktop-packaging.md#9-安装总进度与模板扩展)。
- **卸载残留先区分归属**：单独处理安装器自有图标；最终重试按本次打包清单从深到浅处理空目录，不扫描用户安装目录。系统共享备份与用户数据继续保留。见 [卸载数据选择](references/desktop-packaging.md#5-卸载数据选择)。
- **共享按钮与原生消息框**：返回前页清除提权盾牌；界面定时器弹窗不能证明工作线程已适配。各实际线程启用主题，重建插件后验证真实消息框、像素和返回值。见 [暗黑模式与高分屏](references/desktop-packaging.md#4-暗黑模式与高分屏)。
- **验证结果要区分范围**：主窗口深色不代表系统目录窗口也深色；策略日志不代表实际删除；复用已验证应用不代表刚做了离线启动。见 [验证与交付](references/desktop-packaging.md#7-按改动验证并交付)。
- **adbutils 2.2.1 的 list2cmdline 用 shlex.quote**：list 参数里的 `|` 会被引号化破坏 shell 管道——管道命令必须拼成**单个字符串**传 `d.shell(...)`（见 core/device/screenshot/adb_nc.py）。
- **config/static.json 每次启动被 STATIC_DEFAULT_CONFIG 覆盖**（core/config/config_init.py: check_static_config）：改静态配置只能改 default_config.py 模板，手改 json 无效。switch.json 同理每次重置。
- **配置枚举值以中文原文落盘**（then/server/patStyle/event_name），一切匹配用中文字符串精确相等；WebUI 只做显示层翻译。
- **面板值类型以 config.json 现值为准**：CommonShopList/TacticalChallengeShopList 是与价格清单**按下标对齐的 0/1 标志数组**（不是名称列表）；ArenaComponentNumber/cafe_reward_invite*_starred_student_position/create_phase 是 int；createTime/CommonShopRefreshTime/purchase_* 是字符串数字——schema 用 coerce('int'/'int[]') 标注需要转换的字段，其余保持现值类型。
- **任务互斥与停止请求**：每次启动新建 Baas_thread（名字使用纳秒时间），调度和单次任务共用运行锁；工作线程仍存活时不能另起任务或删除配置。初始化期间的停止请求由事件保留，初始化后先检查，再决定是否执行任务。
- **配置路径校验**：服务入口统一使用 `config_path()`，解析后的目录必须直接位于配置根目录下；默认配置的大小写别名也不能删除。不要绕过校验直接拼接用户输入。
- **通用设备判断**：设备列表来自 ADB（安卓调试连接）的实际在线状态；连接返回文字不能代替状态检查。MuMu（模拟器）端口判断只用于本机回环地址，不能据远程端口推断模拟器或改写远程地址。
- **Logger 信号约定 `.emit(level, message)`**（level 1=INFO 2=WARNING 3=ERROR 4=CRITICAL，core/utils.py Logger.__out__）：传普通回调要包一层带 emit 的适配器（server/service.py `_Signal`）。
- **OCR（文字识别）就绪状态**：后台初始化完成后以 `Main.ready` 为准；已有识别客户端对象不代表成功。失败写入 `init_error`，网页保留未就绪状态并显示错误，只有成功后才允许启动及自动运行配置。源码启动可准备识别服务；完整发行使用内置程序和模型，缺失时明确失败。`core/ocr/baas_ocr_client/bin` 是被忽略的嵌入仓库。
- **MaaTouch**：单文件 dex（src/maatouch_bin/maatouch，跨 ABI）push 到 /data/local/tmp 后 `CLASSPATH=... app_process / com.shxyke.MaaTouch.App` 以 `d.shell(..., stream=True)` 拿 socket；握手两行 `^ <contacts> <max_x> <max_y> <pressure>` 与 `$ <pid>`；指令文本同 minitouch（d/m/u/c/r/w + \n）；`recv(0)` 不确认动作完成；发送、重连重发和按动作时长等待都在同一把锁内，长按和滑动须等完设备端等待，再加 50 毫秒余量。
- **adb_nc 截图**：PC 端起 TCP server，设备端 `screencap | nc <host> <port>` 回连（不是 adb exec-out）；raw 格式 = 12 字节头（3×小端 uint32 w/h/format）+ BGRA，取尾部 w*h*4 字节 reshape；设备无 nc 时报错让用户换方式。
- **前端消息顺序不保证**：RPC 回执（有 `i` 字段）与 topic full 推送可能乱序，客户端按字段区分，不要假设顺序。
- **i18n 契约**：中文原文是 key 也是存储值——**落盘/协议值永远是中文原文**（then/server/patStyle/event_name），翻译只发生在前端显示层（`$t()`）；select 渲染 `<option value={原文}>{$t(原文)}</option>`，绝不能把译文存回去。词典缺失自动回退中文。
- **宿主环境可能泄漏 `ELECTRON_RUN_AS_NODE=1`**：会让 electron 退化成普通 Node（`require('electron')` 返回路径字符串、app undefined）。desktop/main.js 顶部有自愈守卫（检测到就用干净 env 重启自己），但直接 require electron 的脚本要小心。
- **新版 starlette StaticFiles 找不到文件是抛 HTTPException 而非返回 404 响应**：SPA 回退必须 try/except 接住再 fallback 到 index.html（见 server/app.py SPAStaticFiles）。
- **素材摘要与换行**：`desktop/.gitattributes`（桌面换行约定）固定原始复选框矢量图和生成头文件为 LF（换行格式）；提交时核对暂存及检出后的摘要，其他文本仍可由版本工具转换。见 [复选框素材更新](references/desktop-packaging.md#复选框素材更新)。

## Commit / Branch 约定
- 分批时读 [提交依赖](references/desktop-packaging.md#11-分批提交)；模块、资源清单与测试夹具按依赖同批，不能只靠最终工作区通过回归。
- 分支 `dev`（主开发），仅本地提交；信息用 `feat:/fix:/refactor!/chore:/docs:` 前缀 + 中文描述。
- 并行特性可开 worktree：`git worktree add <path> -b <branch> dev`，完成后在 dev 上 merge。
- `config/`、`error.log`、`core/ocr/baas_ocr_client/bin/`、`webapp/node_modules|dist`、开发验证环境及工具缓存均已 gitignore，勿提交。

## WebUI 功能路线（持续完善）
面板体系已就绪：前端路由 `#/<dir>/{home,schedule,config,settings,advanced}` + 全局 `#/update`；16 个结构化面板、主页资产条（Assets 2s 轮询）、更新设置（setup.toml/CDK 测试/SHA 测试）、帮助文档（四语言 HTML）、**多语言 i18n**（zh/en/ja/ko，侧栏语言切换器，词典+overrides 双层）与 **Electron 托盘壳及完整离线发行**（desktop/，含安装与卸载定制）均已实现；桌面发行的验证范围见对应参考。待补：全局热键（浏览器形态受限，可后续在 desktop 壳内做全局快捷键）、资产条推消息化（现为轮询）、桌面在线自动更新。
