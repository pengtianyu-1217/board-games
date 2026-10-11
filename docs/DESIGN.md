# 设计说明（DESIGN）

## 1. 分层与职责

| 层 | 文件 | 职责 | 依赖 |
|---|---|---|---|
| 规则层 | `core/games/*` | 局面、合法性、胜负、记谱、序列化 | 无（纯 Python） |
| 引擎层 | `engines/*` | 子进程、协议收发、难度、异常回退 | PySide6(QProcess) + 规则层 |
| 控制器 | `controller.py` | 时间线/轮次/选择/棋谱/计时/难度/存读/调度 | 规则层 + 引擎层 + Qt 模型 |
| 界面 | `qml/*` | 渲染、交互、动效、音效、折叠面板 | 只认 `controller` / `Theme` / `Settings` |

依赖单向：`qml → controller → {engines, core}`，规则层不反向依赖任何东西。

## 2. 规则层契约

三种棋的状态对象都是 **frozen dataclass**，对外提供同一组能力：

| 成员 | 含义 |
|---|---|
| `board` | 扁平序列（象棋 90 字符 / 围棋·五子棋 size² 整数） |
| `to_move` | 1=先手，2=后手 |
| `winner` | 0=未决，1/2=胜方，3=和棋（`DRAW`） |
| `is_over` / `move_count` / `last_move` / `moves` | 常用查询 |
| `play(move)` | 返回**新**状态；非法抛 `ValueError` |
| `legal_moves()` / `is_legal(move)` | 合法着法 |

着法表示：五子棋/围棋 = `(x, y)`；象棋 = `((fx, fy), (tx, ty))`；围棋 `play(None)` 停一手。

各棋特有：

- `GomokuState.win_line`：连五坐标；`forbidden=True` 时**黑棋长连（≥6）判负**。
- `XiangqiState.positions` / `givers`：局面指纹序列与「每一着的将军方」，
  用于**三次重复**判定；`_repetition_result()` 裁定一方长将判负、双方重复判和。
  `to_fen()`。
- `GoState.captures` / `ko` / `passes` / `score` / `to_sgf()`；**停一手会写进 `moves`（None）**，
  这样引擎回放与存档都不会丢 pass。

**性能**：`xiangqi.py` 里 `_pseudo_moves/_legal_moves/king_pos/kings_face/is_attacked`
都用 `functools.lru_cache`（键是 `(board, …)`，board 为 tuple 可哈希）；对外仍返回 `list` 语义。

## 3. 记谱（`core/games/notation.py`）

| 棋种 | 形式 | 例 |
|---|---|---|
| 象棋 | 中文纵线记谱（前/后、进/退/平，红汉字/黑阿拉伯数字） | `炮八平五`、`马8进7`、`前车进一` |
| 围棋 | GTP 坐标（跳字母 I，行号自下而上） | `D16`、`停一手` |
| 五子棋 | 字母 + 行号（自上而下，1 起） | `H8` |

## 4. 坐标与编码约定

| 棋种 | 本项目的 (x, y) | 与引擎的转换 |
|---|---|---|
| 象棋 | x=0..8 左→右，y=0..9 上→下（红在下） | ICCS：`file=chr(97+x)`，`rank=9-y` |
| 围棋 | 同上，y=0 在上 | GTP：列字母（**跳过 I**），`行号=size-y` |
| 五子棋 | 同上 | Piskvork：`x,y`，**整体上下翻转** |

> 关键结论：**收发用同一个变换**即可；反射后棋局等价，着法映射回来仍正确。
> 五子棋自检特意用非中线行证明这一点。

## 5. 引擎层

- `EngineBase`：`QProcess` 起子进程，`readyReadStandardOutput → on_line`。
  GTP 用回调队列 `_resolve`；UCI/Piskvork 看关键字/正则。
- **难度**：基类 `set_difficulty(level)`，子类覆盖——
  Gtp 改 `maxVisits` + `maxTime`（每步下发 `kata-set-param`），Uci 改 `Skill Level`+movetime，
  Piskvork 下发 `INFO timeout_turn`。
- **网络选择（关键）**：CPU（eigen）后端必须用**卷积网**。`manager.KATAGO_NET` 指向
  `nets/g170-b10c128-...bin.gz`（katagoarchive.org 的 g170 档案）；变压器网 `b10c384h6nbt`
  在 eigen 上每访问约 1s，卷积网约 25ms——**差约 50 倍**，换网后围棋每步 1–3s 且能搜几十倍节点。
- **预热**：`EngineManager.prewarm(game)` 在切棋种时把引擎进程与模型加载提前做掉。
- **非落子哨兵**：`MOVE_PASS` / `MOVE_RESIGN`（`engines/base.py`），与 `None`（失败）区分。
- **失败分级**（`manager.py`）：`_build` 返回 None = 硬失败（文件缺失，会话内不再试）；
  `request` 返回 False 或 `failed` 信号 = 软失败（**允许重试一次**），超过才停用。
- `stop()`：先断三个信号，再写退出命令、kill、`deleteLater`。

## 6. 控制器（`controller.py`）

- **`BoardModel`**：角色 `owner/glyph/mark`；只在变化时 `dataChanged`（保住落子动画）。
- **`MoveListModel`**：角色 `moveNo/side/text/current`，驱动棋谱列表。
- **时间线**：`_timeline = [(state, time1, time2, move), …]`，`_viewIndex` 指向当前查看位置。
  - 落子 `_push()`；悔棋 `pop()`（AI 模式下退到该人走）；换棋种 `newGame()` 重建。
  - **复盘**：`gotoMove(i)` 只改 `_viewIndex` 并重建显示；`exitReview()` 回最新；
    复盘态禁止落子与 AI。
- **计时**：`QTimer` 每秒给行棋方累加；随 `_timeline` 快照回滚；复盘时显示快照时间。
- **难度 / 选边**：`difficulty`(0/1/2)、`humanSide`(1/2)；改边即重开。
- **提子**：象棋按初始局面差分出双方被吃子；围棋用 `state.captures`。
- **存读**：`saveGame/loadGame`。JSON 棋谱 `{game,size,komi,humanSide,difficulty,moves[]}`，
  载入 = 新建后**重放**；`.fen` / `.sgf` 走各自导出。
- `_maybe_ai()`：有重入保护；记录 `_engine_asked`。
  `_on_engine_move()`：校验应答新鲜度；`MOVE_PASS → play(None)`、`MOVE_RESIGN → 判负`、
  `None`/非法 → 回退占位 AI。`_do_ai()` 用 try/except 兜底。
- **术语与动画数据**：`_announce()` 计算术语（将军 / 吃子 / 提子 / 打吃 / 打劫 / 连五 /
  禁手 / 将死 / 困毙 / 和棋），**先 `_emit_event(term)` 再 `moveMade(kind)`**；
  `_captured_diff()` 给出被吃/被提棋子的坐标与外观，经 `captureAnimChanged` 推给 QML 做飞离；
  `checkPoint` / `koPoint` 供棋盘画将军环与劫点。

## 7. 界面（QML，无侧栏）

```
┌ 顶栏：印章 + 三棋对弈 · [五子棋][象棋][围棋] · [棋谱][设置] ┐
│                                                              │
│                    BoardArea（居中吃满 + 坐标）              │
│                                                              │
└ 底栏：行棋方/手数 · 双方计时 · [新局][悔棋][停一手][认输][AI] ┘
```

- **`BoardArea`**：Canvas 画棋盘（浅木底 + 木纹叠加 + 高对比线 + 九宫/楚河汉界/星位 +
  坐标）；`Repeater` 按 `controller.board` 铺格子（落子弹入、投影、**落子涟漪**、
  最后一手环、选中环、可走点、**将军环**、**打劫点**、连五呼吸、空位幽灵子）；
  另有一层 `ghostModel`：监听 `captureAnimChanged`，把被吃/被提的棋子做**飞离动画**。
- **折叠浮层**：`MoveDrawer`（右侧滑入：对局信息 / 棋谱 / 提子 / 存读）、
  `SettingsPopover`（顶栏弹出：难度/选边/坐标/声音）、`EndOverlay`（终局印章落印）、
  `ConfirmPopup`（新局/换边/认输确认）、`TermBanner`（术语浮字：将军/打吃/提子/打劫/连五/禁手…）。
- **单例**：`Theme`（国风色板 + `pick()` 从 `Qt.fontFamilies()` 选字体 + 尺寸/动效）、
  `Settings`（坐标、音效、音乐、音量）。
- **硬性约束**：不用任何表情/符号字符；图形用 Canvas 自绘。

## 8. 美术与音频管线

- **贴图**：`tools/gen_textures.py` 纯标准库（zlib 手写 PNG）合成 `paper.png`（宣纸）与
  `wood_light.png`（浅木）。`BoardArea` 用木纹做棋盘底，`Main` 用宣纸做窗口底。
- **音乐**：`tools/gen_music.py` 用 Karplus–Strong 拨弦合成五声音阶古琴循环
  `bgm_guqin.wav`，`MediaPlayer` 循环播放。
- **音效**：`tools/gen_sfx.py` 纯标准库合成 **20 个** wav（Karplus–Strong 拨弦做木子/石子/古琴质感）：
  落子（木·石）、吃子（木·石）、将军、打吃、打劫、禁手、胜、负、和、停着、选中、按钮、
  悔棋、开局、错误、抽屉、面板开合。

## 9. 生命周期

- 启动：`main.py` 建 `QGuiApplication` → `GameController` → `QQmlApplicationEngine`
  → 注入 `controller` → 加载 `Main.qml`。
- 退出：`app.aboutToQuit → controller.shutdown() → EngineManager.shutdown() → 各引擎 stop()`。
- 先断信号再 kill，避免已析构对象上的信号触发。
