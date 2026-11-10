# YAB（原 BAAS）架构参考

## 1. 进程与启动链

- 在项目根目录运行 `uv sync --python 3.11`，再运行 `uv run python -m server --open`。读取 config/webui.json（全局网页配置），缺省监听本机 22267 端口，显式 `--host`（地址）与 `--port`（端口）覆盖保存值；`webui.py` 仍转发到相同入口。
- Python（运行环境）默认 3.11，依赖兼容范围是 `>=3.9,<3.13`。前端使用 Vite 8（网页构建工具），所需 Node.js（前端运行环境）范围为 `^20.19.0 || ^22.12.0 || >=24.0.0`。
- `server/frontend.py` 先检查网页产物是否存在且未过期，需要时使用本机 pnpm（前端包管理器）安装锁文件依赖并构建。工具版本、路径和配置由开发者准备，包管理器不固定版本；不会自动下载或替换开发环境。
- `--api-only`（仅后端模式）跳过网页构建及静态网页路由，供分开开发前端使用。`uv run python -m server.frontend --force`（强制构建命令）可手动重建网页。
- 完整发行包使用内置网页，资源缺失会明确报错；完整程序打包前校验 `webapp/dist/index.html` 已存在。容器使用源码时也要自行准备前端工具或先构建网页。
- `server/app.py` 的 lifespan（应用生命周期）依次迁移配置、推送配置列表，再在后台初始化 `Main(ocr_needed)`。只有 `Main.ready` 成功才设置识别就绪状态并执行自动启动；失败通过 `init_error` 和网页元数据保留错误。
- OCR（文字识别）语言推导：任一配置为官服或 B 服时加 `zh-cn`（简体中文），日服加 `ja-jp`（日语），始终包含 `en-us`（英语）。源码启动可由 `check_git` 准备服务文件；完整发行内置识别程序与模型，资源缺失时明确失败，不运行下载。嵌入仓库目录已忽略。
- `main.py` 保留不带网页的任务入口；识别初始化和静态配置都成功后才标记完整就绪。

## 2. 网页协议与访问保护

- `/api/ws`（实时通信接口）由 `server/hub.py` 管理。生产网页由 `SPAStaticFiles` 提供：无扩展名路径找不到时回退首页，资源响应禁用缓存，避免继续使用旧页面。
- 上行协议是 `{"t": topic, "o": "sub"|"unsub"|"rpc", "f", "v", "i"}`；下行数据是 `{"t","o":"full"|"add"|"set","v"}`，调用回执是 `{"t","i","e","r"}`。
- 推送在线程间排队后由事件循环发送，回执与主题推送的先后不保证；客户端按 `i`（调用编号）区分回执。日志按配置保留最近 500 条供首次订阅。
- 全局主题为 `Meta`（元数据）和 `ConfigScan`（配置列表）；配置主题为 `Log:<dir>`（日志）、`State:<dir>`（任务状态）、`ConfigArg:<dir>`（配置项）、`EventConfig:<dir>`（事件配置）、`Panels:<dir>`（面板 schema：panels/groups/fields，options 由后端按 server_mode 解析）。注册入口在 `server/app.py`，面板定义在 `server/panels.py`。
- 设备调用：`Meta.autosearch_adb()`（刷新已连接设备）返回在线设备序列号列表；`Meta.connect_adb({host, port})`（连接手填地址或序列号）返回 `{"serial": "...", "state": "device"}`。二者不扫描模拟器进程。
- 配置列表的 `add/delete/rename`（新建、删除及显示名称修改）、配置项的 `set`（单项写入）与 `set_sweep`（mainPriority/hardPriority 扫荡串，校验并同步 unfinished_*_tasks）、事件的 `set_event/enable_all/refresh_all`（修改、批量启用及刷新时间）、任务的 `start/stop/run_task`（启动、停止及运行单项任务）、资产的 `Assets:<dir>.get`（主页资产条 2s 轮询）。修改后推送相应主题；设备查询和连接只返回调用结果。
- 更新与帮助是全局页：Meta.update_get（读取版本与更新设置）始终返回二开版本及固定上游基准，等待连接成功后加载；只有旧启动器设置的读写与测试依赖 setup.toml（旧启动器配置）。Meta.help_list/help_content（帮助文档）仍从内置文档读取，不因缺少旧配置而隐藏版本来源。
- `Meta.webui_get/webui_save`（网页设置读取与保存）返回已保存值、当前监听值和桌面端口覆盖标记；保存后重启生效，不自动打断任务。源码与桌面读取同一配置结构，配置位置由 `YAB_CONFIG_DIR`（配置根目录）或默认目录决定。
- `server/security.py` 默认只允许本机访问。监听其他地址前需要设置 `BAAS_WEBUI_TOKEN`（网页访问密码环境变量）；设置后本机也要登录，密码不写入源码或项目配置。
- 浏览器通过登录会话访问，并检查实时连接的来源；本机开发代理的来源与实际访问端口需要一致。原生客户端可使用 Bearer（持有者令牌）请求头。会话仅保存在服务进程中，重启后需要重新登录。

## 3. 任务运行与信号

- `BaasService`（任务服务，server/service.py）为每次启动创建新的 `Baas_thread`（任务实例），名字使用配置目录和纳秒时间，避免 `Main.get_thread` 复用停止过的实例。
- 调度和单次任务共用 `_launch()`（启动入口）及运行锁。实际工作线程或运行状态任一仍活跃时，都不能重复启动；单次任务会明确提示先停止当前任务。
- `stop()`（停止入口）先记录停止事件，再通知任务；初始化前后都会检查该事件。停止请求发出后，实际工作线程仍存活时不能新建任务或删除该配置。
- 任务结束后在清理阶段重置运行状态、当前任务和等待队列，并移除任务实例与停止事件。按钮回调不能提前把仍存活的工作线程标成空闲。
- `_Signal(fn).emit(...)`（信号适配器）让核心信号可接普通回调。日志等级为 1 至 4；按钮、任务列表和退出信号转换为网页状态推送。
- `handle_then()`（完成动作）在空闲且预计等待超过 120 秒时精确匹配已保存的字符串：`无动作`、`退出 Baas`、`退出 模拟器`、`退出 Baas 和 模拟器`、`关闭游戏`、`关机`。除`关闭游戏`外均为终止动作（触发 signal_stop）；`关闭游戏`是等待期动作（参考 SRC WhenTaskQueueEmpty=close_game）：只关一次游戏、调度器继续等待，游戏只在任务实际到点时由 thread_starter 先 solve('restart') 拉起——因此启动时若没有到期任务也不会拉起游戏。网页中的退出脚本动作仍只停止相应任务状态；安卓关闭游戏用调试连接停止应用，桌面版关闭窗口失败后结束进程。

## 4. 配置存储契约

- 移除过时展示开关时，先查实际消费者与存量配置读取；当前配置直接按字段构造数据对象，不能只删字段导致旧配置无法加载。bannerVisibility（旧首页头图开关）只为兼容保留，普通设置与高级页均不展示，高级页计数按可见字段计算。

- 以下相对路径指源码布局。桌面发行默认使用 `YAB.exe` 旁的 `config/profiles`（任务配置）和 `config/ocr`（识别设置）；`YAB_CONFIG_DIR` 可覆盖配置根目录，版本目录通过目录联接复用共享配置。
- `config/<dir>/config.json`（用户配置）由数据类全量保存，缩进为 4；`event.json`（事件配置）缩进为 2；`switch.json`（开关配置）每次启动重置。
- `config/static.json`（静态配置）每次从默认模板重写。需要持久生效的枚举或默认值改 `core/config/default_config.py`；用户配置数据类由开发工具生成。
- `ConfigSet.get()`（配置读取）每次读磁盘，无缓存；单项写入后保存文件。
- 服务中的 `config_path()`（目录校验）拒绝非法名称、路径分隔符、父目录跳转及解析后离开配置根目录的路径。需要现有配置的入口还会检查文件及目录名称；默认配置及其大小写别名不可删除。
- 游戏服务器决定游戏版本及资源分派，安卓服务器不限定设备必须为模拟器。`日服PC端`（日服桌面版）与 `Steam国际服`（国际服桌面版）保留原有桌面设备逻辑。
- 服务器模式映射：官服、B服对应 `CN`（国服）；国际服、国际服青少年、韩国ONE（韩国版本）及 Steam国际服（国际服桌面版）对应 `Global`（国际服）；日服及日服PC端（桌面版）对应 `JP`（日服）。
- 事件字段为 `func_name`（任务名）、`event_name`（显示名）、`enabled`（启用状态）、`next_tick`（下次执行时间戳）、`priority`（优先级）、`interval`（间隔）、`daily_reset`（每日刷新时分秒数组）、`disabled_time_range`（禁用时段）、`pre_task`（前置任务）和 `post_task`（后置任务）。调度器按每日刷新和间隔计算下一次执行。

### 配置生效时机

1. 先分清配置文件、网页当前值和工作线程副本。`ConfigSet.get()`（单项读取）每次重读文件；`set()`（单项设置）先重读再保存，`update()`（兼容更新）调用同一逻辑，也会保存。直接访问已持有的配置对象不会自动刷新。
2. 网页保存由 `server/service.py`（任务服务）保存后推送相应主题；配置类本身不更新界面。外部改文件不会主动刷新已打开的网页，需要重新加载页面取值。
3. 工作线程在 `init_config()`（配置初始化）复制普通参数，不能假定每项任务前重读。`daily_config_refresh()`（每日刷新）只重置计数和扫荡待办，不是通用重载。需要确保普通参数生效时，停止该配置，等实际线程退出后重新启动。
4. `event.json`（调度配置）在调度循环中重读，空闲等待约每秒一次；不打断当前任务，结束时仍会写回调度时间。设备、服务器和截图控制方式等初始化参数需重新启动配置；网页监听地址、端口需重启服务。
5. 配置热更新已由用户暂缓，尚未实现。仅讨论过每秒检查目录与文件修改时间、处理半写文件并同步网页、普通参数在下一任务前重读、初始化参数停止并重新启动后生效。不要把建议写成当前能力。对照 ALAS（碧蓝航线自动化脚本）时，本轮核对的是等待时约每 5 秒比较文件修改时间、任务结束清除缓存，并非持续监听整个目录；以后仍按对应版本核对。

项目面向维护者的说明位于 `docs/develop_doc/webui_shop_maintenance.md`（网页与商店维护），配置类文档位于 `docs/develop_doc/script/ConfigSet.md`（配置接口）。修改配置行为时同步这些说明，区分当前实现与暂缓方案。

## 5. 设备与触控

- `core/device/adb_devices.py` 提供通用安卓设备连接。发现只返回实际状态为 `device`（在线）的设备并去重，支持网络地址和 USB（有线连接）序列号，不依赖模拟器进程。
- 手填网络地址先调用连接，再核实设备状态；未授权和连接失败明确报错，返回文字中出现连接字样不作为成功依据。真机序列号端口留空，直接核实在线状态，不发起网络连接。地址支持带方括号的 IPv6（第六版互联网协议），独立端口字段校验 1 至 65535。
- `core/device/connection.py` 保留地址修正和自动选择设备，但写回配置时必须保留真机序列号。MuMu（模拟器）的特殊端口判断只适用于本机回环地址，附近端口选择还要求同一主机；远程设备不能因为使用这些端口就被改写地址。
- 任务中的连接失败最多重试三次后终止初始化，不假设已经连接，也不顺带断开其他离线设备。模拟器自动启动只用于需要自动打开本机模拟器的配置；真机和 redroid（容器安卓设备）可保持关闭，无需模拟器路径。
- 截图和控制分别由 Screenshot.py 与 Control.py 按配置分派。安卓截图支持 adb（调试截图）、adb_nc（网络回传截图）、nemu（模拟器专用截图）、uiautomator2（界面自动化截图）和 scrcpy（投屏截图）；安卓控制支持对应的调试、模拟器、界面自动化、投屏方式及 maatouch（触控服务）。桌面截图用 pyautogui（桌面自动化）或 mss（屏幕捕获），桌面控制用 pyautogui（桌面自动化）。通用安卓设备可先使用调试方式，其他方式按设备实际支持选择。
- 截图归一化为 1280×720，控制按设备宽度与 1280 的比例还原坐标；MaaTouch（触控服务）再按屏幕尺寸与握手范围换算。
- 触控服务的发送、重连重发和动作等待在同一把锁内。`recv(0)`（零长度读取）不确认动作完成；长按按下发的毫秒数等待，滑动按实际下发的每段 10 毫秒等待累计，再统一增加 50 毫秒余量。
- MuMu（模拟器）的 `nemud.app_keep_alive=true`（后台保活开启）会触发 `RequestHumanTakeOver`（需要人工处理）；该检查只用于对应的本机模拟器。

## 6. 前端开发

- 前端为 Vite 8（构建工具）、Svelte 5（界面框架）和 TypeScript（类型语言），无额外界面框架，路由为 `#/<dir>/{home,schedule,config,settings,advanced}`，全局页 `#/update`（仅无第二段时匹配，避免与同名配置目录冲突）。
- `src/lib/ws.ts`（通信客户端）负责重连、重新订阅及调用回执；消息类型在 `src/lib/types.ts`（协议类型文件）。
- 多语言：`src/lib/i18n/`——中文原文为 key；`locale` store（localStorage 'baas.lang' 持久化）+ `t` derived（模板 `{$t('中文')}`、脚本 `tNow()`）；词典 `locales/*.ts` 由 develop_tools/extract_i18n_from_ts.py 从旧 Qt .ts 生成（勿手改），手工补充进 `overrides.ts`。落盘/协议值永远中文原文，翻译只在显示层。
- 帮助文档经 `webapp/src/lib/help-document.ts`（文档样式处理）解析，在真实头部末尾注入深色画布；内嵌文档不会继承外层主题，不要只设置透明背景。保留彩色强调与图片，用受限内嵌页显示，不批量重写源文档。
- 结构化面板：`src/lib/components/fields/FieldControl.svelte` 分发 13 种字段类型（switch/text/number/select/checklist/shop_checklist/ordered_checklist/student_text/slots_select/tag_list/lesson_editor/sweep_editor/actions），`PanelAccordion.svelte` 渲染手风琴卡片，值经 `stores.ts` 的 setConfigValue/setSweep 写回；主页 `AssetBar.svelte` 轮询资产。
- 桌面壳 `desktop/`（Electron）：开发或主动指定源码目录时，从 BAAS_PYTHON → .venv → webui.exe/YAB.exe → python 选择后端；完整发行始终校验并准备内置解释器与离线依赖，用内置源码启动服务。健康检查成功后加载页面；关闭到托盘、退出杀进程树；`pnpm run smoke` 无头冒烟。main.js 保留 ELECTRON_RUN_AS_NODE 泄漏自愈守卫。
- 后端运行 `uv run python -m server --api-only --port 8000`；在 `webapp` 目录运行 `pnpm install --frozen-lockfile`（按锁文件安装）及 `pnpm dev`（开发服务）。代理包含普通接口和实时通信接口。
- `pnpm run check`（前端检查）验证类型与界面代码；`pnpm build --emptyOutDir false`（保留旧产物的构建）生成后端提供的网页。包管理器沿用开发者本机版本，不新增指定版本的绑定。

### 弹窗与网页图标

- 新建、重命名配置共用 `webapp/src/lib/components/Modal.svelte`（弹窗组件）。先检查弹窗和输入框各自的宽度限制，让输入框占满内容区并保留内边距；同时核对窄屏最大宽度与横向溢出。
- 浏览器标签在 `webapp/index.html`（网页入口）引用图标，侧栏在 `webapp/src/App.svelte`（主界面）引用同一个 `/favicon.ico`（网站图标）。文件为 `webapp/public/favicon.ico`（静态图标），源素材为 `assets/logo.ico`（应用图标）；不要用桌面程序图标代替网页图标检查。
- `server/frontend.py`（网页准备入口）的产物过期判断包含 `webapp/public`（静态资源目录）；只改图标也要使旧产物过期。完整发行仍使用内置网页，更新资源需重新打包。
- 前端检查与保留产物构建通过后，用正常安全设置的隐藏浏览器观察宽窄屏输入框边界、图标请求和实际侧栏尺寸。说明观察到的结果，不把类型检查当成布局验证。

## 7. 本地验证

按改动选择已有离线回归，启动、访问保护或设备逻辑一起调整时可在项目根目录运行：

```shell
uv run python -B -m unittest -q develop_tools.test.test_webui_runtime develop_tools.test.test_webui_access develop_tools.test.test_adb_devices develop_tools.test.test_webui_settings
```

这组检查覆盖任务互斥、初始化停止、目录校验、识别失败、触控等待、网页资源准备、访问会话、网页监听持久化及通用设备连接，不需要实际连接游戏设备。

协议调整后，再启动实际服务核实健康检查、主题订阅及调用回执；设备调用可模拟底层设备列表和连接，以隔离识别下载和游戏操作。网页变动再完成前端检查及构建。回归会在 `develop_tools/out`（忽略的验证目录）保留隔离数据，验证后按用户约定处理。

## 8. 商店识别与有限重试

- 入口为 `module/shop/shop_utils.py`（商店工具）。商品编号按固定列位置推进；第六行第二列是第 22 件，缺少该列时，不能把第 23、24 件前移。滑动重叠行不重复计数，末行按配置清单剩余列数处理。
- 单点颜色漏检时，在已识别行中用已有货币模板复查缺列。未匹配到模板就保留缺项，不能仅靠相邻商品推断存在；缺项先重新截图，不推进该行编号。
- 当前实现连续三次缺项、空识别或滑动无进展会报错退出；滑动后无法定位商品也报错，整个检查循环另有次数上限。每件最多点击勾选三次，一组待选商品总等待 15 秒，并响应停止。
- 先跑已有离线回归，覆盖固定截图、模拟缺项及恢复、编号不偏移、重叠行、末行不足四件、停滞、勾选超时和停止请求：

```shell
uv run python -B -m unittest -q develop_tools.test.test_shop_selection develop_tools.test.test_tactical_shop_config develop_tools.test.test_webui_runtime.FrontendTests
```

- 固定样本为 `develop_tools/test/fixtures/global_shop_last_row.png`（国际服商店末行）。本轮用户截图底部两行共八件在当时离线检查中均能识别；不能声称已复现实际第 22 件漏检原因，也不能把模拟购买当实机购买。
- 继续排查时保留原始截图、服务器与语言、目标编号、识别行列和滑动日志，再核对模板与坐标。面向维护者的步骤见项目内 `docs/develop_doc/webui_shop_maintenance.md`（网页与商店维护）。

## 9. 通知入口与来源

| 通知类型 | 排查入口 |
|---|---|
| 任务出错、完成后的远程推送 | core/pushkit.py（触发入口）、core/push_onepush.py（渠道适配）、core/push_config.py（配置与校验）及网页通知设置 |
| 本机“任务已停止”和关机取消交互 | core/notification.py（系统通知），由任务线程调用 |

- 先按实际消息来源定位入口，不能因为接入 OnePush（多渠道推送库）就认为本机通知也已迁移。本机普通及交互通知共用 YAB（应用来源）；保留标题、正文、图标、按钮和返回值。不要顺手改 org.baas.desktop（安装兼容身份）或兼容环境变量。
- 远程渠道以 push_onepush（渠道列表字段）为准，旧字段只迁移一次并保留原值；删除全部渠道后不从旧字段重新启用。新增渠道或改变配置结构时，核对迁移、停用、保存及移除流程。
- 网页“发送测试通知”使用当前表单、不保存且不受任务触发开关限制；用户主动点击会真实发送。正常任务遵守出错和完成开关，已运行的任务需停止并重启后使用新设置。
- 保留网络连接及响应读取超时，包括邮件；失败不阻断其他渠道，日志不输出凭据、完整请求地址或服务响应正文。凭据不写入源码、示例或提交。
- 本机来源修复要完整退出并重启应用；历史消息不会改名，已构建旧包不会因源码变化更新。交付前核对包内版本，不能把旧包当作已包含修复。
- 远程推送回归运行下面已有入口，全部拦截传输，不向真实服务发送；本机来源变化则拦截 core/notification.py（系统通知）的两种发送接口，核对来源与交互参数，不能拿远程回归代替它。网页表单使用桌面参考中的独立前端回归。

```powershell
.venv/Scripts/python.exe -B -m unittest -q develop_tools.test.test_onepush develop_tools.test.test_telegram_push
```

面向用户的配置说明在 docs/usage_doc/notifications.md（推送通知）。实现阶段的历史通过数只记在维护记录，不替代本次验证。
