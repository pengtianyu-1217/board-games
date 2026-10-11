# AGENTS.md —— 给下一位开发者 / AI 的项目说明

> 项目：**三棋对弈**（中国象棋 · 围棋 · 五子棋），PySide6 + QML 桌面应用，
> 三种棋都能人机对战，AI 由外部引擎驱动。**古典国风**皮肤，无侧边栏、折叠式布局。
> 位置：`E:\Desktop\GUI测试\board-games\`，入口 `main.py`。

先读这一页，再动代码。深度设计见 `docs/DESIGN.md`，审查结论见 `docs/REVIEW.md`。

---

## 1. 快速命令

```bash
python -m pip install -r requirements.txt
python main.py                  # 启动
python main.py --game go        # 指定开局棋种 gomoku/xiangqi/go
python main.py --demo           # 开局自动走一步，观察引擎应招
python main.py --no-engine      # 关引擎，用内置占位 AI
python main.py --selftest       # 只加载 QML 校验（无头冒烟）

python -m unittest discover -s tests   # 111 项单测
python tools/engine_check.py           # 三引擎 + 控制器端到端自检（会拉起真引擎）
python -m PyInstaller board-games.spec --noconfirm --clean   # 打包 → dist/三棋对弈/
python tools/gen_textures.py           # 重新合成宣纸 / 浅木纹贴图
python tools/gen_music.py              # 重新合成古琴背景音乐
python tools/gen_sfx.py                # 重新合成音效 wav
```

环境变量：`BOARD_NO_ENGINE=1`、`BOARD_ENGINE_LOG=1`（打印引擎日志）。

---

## 2. 架构（四层，单向依赖）

```
QML 界面 ── controller(GameController/BoardModel/MoveListModel) ──┬── core/games/*  规则层（纯 Python，零 Qt）
                                                                  └── engines/*     引擎层（QProcess + 文本协议）
```

- `qml/` 只通过上下文属性 **`controller`**、**`appSettings`** 与 `Theme` 单例交互，不认识任何 Python 模块。
- `controller.py` 收口「时间线 / 轮次 / 选择 / 棋谱 / 计时 / 难度 / 存读 / 引擎调度」。
- `core/games/` 是**纯 Python 规则**，可以脱离 Qt 单测。
- `engines/` 管子进程与协议，失败自动回退到 `ai.py` 的占位 AI。

数据流（人走一步）：`clickCell → _apply → _push(timeline) → _rebuild()(刷新 BoardModel)`
→ `_sync_moves()`（刷新棋谱）→ `_maybe_ai()` → 引擎异步回 `bestMove → _on_engine_move → 落子`。

---

## 3. 不可破坏的不变量（改代码前务必确认）

1. **`core/` 不许 import PySide6 / Qt。** 规则层必须能脱离 GUI 单测，这是分层的地基。
2. **规则状态是不可变的 frozen dataclass。** `play()` 返回**新状态**，不改旧状态。
3. **UCI 语义**：`position fen <起点> moves <着法…>` 里的 `<起点>` 必须是**走这些着法之前**的局面。
   ⚠ 把「走完之后的 FEN」再叠一遍着法会让 Pikafish 判「Illegal move」并**静默不回复**。
4. **引擎坐标映射只要「发送与解析互为逆运算」即可。** 不要把某个引擎的原点当成全局约定。
5. **迟到的引擎应答必须校验后再落子。** `_engine_asked = (棋种, 手数, 行棋方)` 对不上就丢弃。
6. **引擎不可用必须回退占位 AI，不许崩。** 失败分硬（文件缺失，会话内不再试）/软（启动超时，
   允许重试一次）两类。`_do_ai()` 用 try/except 包 `state.play()`，非法着法不冒泡。
7. **棋盘渲染走 `BoardModel` 的角色**：`owner`(0/1/2)、`glyph`(象棋汉字)、
   `mark`(0 无 /1 最后一手 /2 选中 /3 可走点 /4 连五)。QML 不自己推局面。
8. **引擎子进程退出顺序**：先 `disconnect` 再 kill，否则会抛 "Signal source has been deleted"。
9. **控制器「时间线」是唯一历史源。** `_timeline = [(state, t1, t2, move), …]`，`_viewIndex`
   指向当前查看的位置；**复盘只改 `_viewIndex`**，不改时间线；在复盘态禁止落子与 AI。
10. **引擎「非落子」语义用哨兵**：`engines/base.py` 的 `MOVE_PASS` / `MOVE_RESIGN`，
    与 `None`（引擎失败）区分开。围棋 `pass` 要落 `play(None)`，认输要判负，不能当非法着法。
11. **QML 不出现任何表情/符号字符**（`✦ ✶ ↶ ⏸ ⚑ ♟` 等一律禁止）。按钮只用文字；
    必须画图形时用 `Canvas` 自绘。字体一律经 `Theme.pick(list)`（`Qt.fontFamilies()` 命中首个可用）。
12. **界面无侧边栏**：棋谱/提子/对局信息在右侧滑入抽屉，设置在顶栏弹出，底栏可自适应。
13. **术语与被提子走两个信号**：`eventChanged`（术语浮字）与 `captureAnimChanged`（棋子飞离）。
    `_announce()` 里必须**先** `_emit_event(term)` **再** `moveMade(kind)`，否则 QML 的音效分支
    读不到当前术语（如「禁手」「和棋」「打劫」）。

---

## 4. 目录地图

```
main.py            入口与命令行开关
appsettings.py     用户偏好持久化（QSettings；以上下文属性 appSettings 暴露给 QML）
controller.py      BoardModel + MoveListModel + GameController（QML 的唯一后端）
ai.py              占位 AI（引擎缺失时兜底，随难度调整）
core/games/        base / gomoku / xiangqi / go / notation —— 规则与记谱（纯 Python）
engines/           base / gtp / uci / piskvork / manager —— 引擎层
  bin/             katago/ pikafish/ rapfi/（含各自的 DLL、配置、权重）
  nets/            KataGo 网络 g170-b10c128（卷积，CPU 用）+ b10c384h6nbt（变压器，留着备用）
qml/               Main.qml + components/
  components/      Theme（单例）· BoardArea · SegButton/TextButton/Toggle
                   · MoveDrawer（棋谱长卷）· MoveList · Clock · CapturedTray · SettingsPopover
                   · EndOverlay · ConfirmPopup · TermBanner（术语浮字）· Seal · SectionTitle
                   · PlayerCard（宽窗时棋盘两侧的双方信息栏）
assets/art          paper.png（宣纸）· wood_light.png（浅木）
assets/audio        bgm_guqin/bgm_martial/bgm_void.wav（按棋种循环）· 20 个音效 wav（落子/吃子/将军/打吃/打劫/
                    禁手/胜/负/和/停着/选中/按钮/悔棋/开局/错误/抽屉/面板开合 …）
tools/              生成与自检脚本（见下）
tests/              111 项单测
shots/              界面截图（tools/shot.ps1 或离屏 grabWindow 生成）
```

`tools/` 里各脚本的用途：

| 脚本 | 用途 |
|---|---|
| `engine_check.py` | 三引擎各要一步 + 控制器人机整局；五子棋**特意用非中线行**验证坐标映射 |
| `gen_textures.py` | 纯标准库（zlib 手写 PNG）合成宣纸与浅木纹 |
| `gen_music.py` | 纯标准库（Karplus–Strong 拨弦）合成五声音阶古琴循环 |
| `gen_sfx.py` | 纯标准库合成音效 |
| `export_canvas_image.py` | 从浏览器 IndexedDB 导出「无限画布」生成的图片（按 `bytes` 匹配 blob） |
| `shot.ps1` | 按窗口 PID 截屏（Qt 内部 `grabToImage` 在本机不回调，别用） |

---

## 5. 踩过的坑（别再踩）

- **Windows curl 证书吊销检查失败**（`CRYPT_E_NO_REVOCATION_CHECK`）→ 下载加 `--ssl-no-revoke`。
- **katagotraining.org 的存储桶返回 403** → 改用 GitHub releases 托管的网络。
- **`.7z` 用 `tar`（bsdtar）就能解**，不必装 7zip。
- **QML `grabToImage` 在 offscreen/本机都不回调**，静默无产物 → 真机截图走 `tools/shot.ps1`。
- **offscreen 平台没有字体库**（`QFontDatabase.families()` 返回 0），离屏渲染的截图里**所有文字都是方块**，
  这是假象，别据此判断字体或改字体代码。要看布局/配色用离屏截图，要看文字上真机。
- **离屏抓帧**：`QT_QPA_PLATFORM=offscreen` + `QT_QUICK_BACKEND=software`，把 `rootObjects()[0]`
  用 `shiboken6.wrapInstance(getCppPointer(...), QQuickWindow).grabWindow()` 才能抓到位图。
- **PowerShell 5.1 读无 BOM 的 UTF-8 脚本会把中文搞乱** → 截屏脚本按 **PID** 找主窗口，不按标题。
- **`cmd` 里 `&&` 与 `findstr`、`&` 混用会被错误解析**，命令尽量拆开跑。
- **单测不要让引擎真的起来** → 测试里设 `BOARD_NO_ENGINE=1`。
- **KataGo 会写日志到 `gtp_logs/`**（已 gitignore）；重下引擎后要再关 `logAllGTPCommunication`。
- **CPU 版 KataGo 千万别用变压器网络**：`b10c384h6nbt`（transformer）在 eigen 上每访问约 1s，
  20 核加线程也救不动；换 **卷积网** `g170-b10c128` 后快约 50 倍（20 次访问 26s → 0.5s）。
  已把 `manager.KATAGO_NET` 指向 `nets/g170-b10c128-s197428736-d67404019.bin.gz`
  （来自 `katagoarchive.org` 的 g170 档案）。难度同时给 `maxVisits` 与 `maxTime`
  （见 `gtp.py` 的 `_TIME_BY_LEVEL`），并在切换棋种时**预热引擎**。
- **引擎预热**：`newGame()` 会 `EngineManager.prewarm()` 提前拉起引擎（进程 + 模型加载），
  把冷启动藏在对局准备阶段；切棋种时会把其它空闲引擎停掉以省内存。
- **`--selftest` 会设 `BOARD_NO_ENGINE=1`**：它只是 QML 冒烟，不该拉起真引擎——否则退出期
  QProcess 析构会触发 `errorOccurred`，抛 "Signal source has been deleted"（该回调已加防御，
  但仍不要在无事件循环的场景里启动引擎）。
- **丢弃「迟到 / 过期」的引擎应答时，必须顺带清 `_ai_thinking`**：否则玩家在 AI 思考时打开
  棋谱跳回历史手，应答被判过期后会永久卡在「对手思考中」。
- **`undo()` 要先 `del _timeline[_viewIndex+1:]` 再 pop，且必须防空**：终局点「复盘」到第 0 手
  再按悔棋，若直接 pop 会把时间线清空并在 `_timeline[-1]` 崩溃（已加 `len > 1` 守卫）。
- **QML 设置一律走上下文属性 `appSettings`**：原来的 `Settings` QML 单例是内存态、重启即丢，
  现已由 `appsettings.py` 的 `AppSettings`（QSettings）取代；QML 里不要再出现 `Settings.xxx`。
- **BGM 按棋种切换**：`Main.qml` 的 `bgmTrack()` 依 `controller.game` 选 `bgm_*.wav`，
  切棋种时重启播放；新增曲目改 `tools/gen_music.py` 并重生成。
- **兜底 AI 也是「对手」**：引擎不可用时接管的是 `ai.py`；五子棋用形状打分（会挡四/堵活三），
  它决定「引擎挂了」时的下限，别当摆设。回退时会有一次性 toast 提示。
- **Rapfi 构建按 CPU 选**：`manager._pick_rapfi()` 依 `IsProcessorFeaturePresent`
  挑 avx512 / avx2 / sse，别写死 avx2——不支持的机器会崩溃并静默回退到弱 AI。

---

## 6. 当前状态与下一步

**已完成**：三棋规则（象棋 44 步开局校验 / 重复局面与长将判负、围棋劫争与数目、
五子棋五连与黑棋长连禁手）、记谱（象棋中文纵线、围棋/五子棋坐标）、
国风界面（无侧栏、折叠抽屉、宣纸木纹、印章、成套动效）、古琴 BGM + 成套音效、
棋谱/复盘跳转、双方计时、难度选择、执子选边、提子显示、存读（JSON/FEN/SGF）、
三引擎接入并端到端验证、111 项单测、**PyInstaller 打包（Windows onedir，见 `board-games.spec`）**。

**待办（按价值排序）**：

1. **五子棋三三/四四禁手**：长连（overline）已接线（`newGame` 用 `forbidden=True`，黑 ≥6 连判负），
   双三 / 双四待实现（或交给 Rapfi）。
2. **围棋形势判断与死活**：接 KataGo `kata-analyze`，显示胜率/目差。
3. ~~**打包**~~：**已完成** —— `board-games.spec`（Windows onedir），
   剔除非 Windows 引擎、Rapfi 未用指令集、KataGo 日志，网络只带 `g170-b10c128`，
   Qt 只带 QML 用到的模块；产物约 318MB。
4. **棋谱导出多格式 / 局面编辑**：现在只能整局存取。
5. **残局/让子**：`GameController.humanSide` 已在，让子局面待补。

**已知边界**：
- 引擎「认输」会立即判负；`resign` 不进入 `moves`（只进时间线）。
- `EngineManager` 硬失败（文件缺失）会记住并在会话内不再重试；软失败允许重试一次。
