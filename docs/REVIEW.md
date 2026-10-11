# 代码审查（REVIEW）

审查范围：`main.py`、`controller.py`、`ai.py`、`core/games/*`、`engines/*`、`qml/*`、
`tools/*`、`tests/*`；以「能否被下一位开发者安全接手」为标准。

---

## 本轮（打包前质检 + 稳定性加固）

一次针对「打包前」的深度质检：跑真实测试、引擎端到端、真机启动、以及针对性探针。

### 修复
- **另存为错误格式会崩**：保存对话框对三种棋都列出 FEN/SGF 过滤器。选成与当前棋种不匹配的
  扩展名时，`saveGame` 会调 `GomokuState.to_fen()`（不存在）抛 `AttributeError`，而它只 catch
  `OSError`——未捕获异常在 QML 槽里可能直接终止进程。现按棋种校验扩展名，不匹配只提示、
  不写文件、不抛异常。
- **打包版启动即退出**：窗口程序（console=False）下 `sys.stdout/stderr` 为 `None`，
  `main.py` 直接 `sys.stdout.write(...)` 抛 `AttributeError` → 退出码 1。新增 `_emit()` 安全写。
- **载入畸形棋谱会崩**：`loadGame` 原来只 catch `(OSError, ValueError)` 且仅包住 json 解析，
  之后的 `int(size)` / `float(komi)` / `int(humanSide)` 与 `_decode` 解包都在 try 之外。
  现把解析与字段校验整体托管，畸形文件只提示；并对 `size` 加 5–25 护栏，防止畸形尺寸撑爆棋盘。
- **强杀时引擎子进程残留**：`engines/base.py` 接入 Windows Job Object
  （`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`），父进程被强杀时 OS 连带回收 katago/pikafish/rapfi。
  正常退出仍走 `stop()` 优雅结束；非 Windows / 调用失败一律静默降级。
- **启动 QML 告警**：`Shortcut { sequence: StandardKey.Cancel }` 绑定多个键，改为 `sequences: [...]`。

### 打包
- 新增 `board-games.spec`（Windows onedir）。引擎只带 Windows 二进制，网络只带在用的
  `g170-b10c128`；Qt 只带 QML 用到的模块，剔掉 WebEngine（~194MB）/Widgets/Quick3D/Pdf/翻译。
  体积 562MB → **318MB**。`main.py` / `engines/manager.py` 支持冻结路径（`sys._MEIPASS`）。

### 验证（全部实测）
- 单测 **111 项全过**；`tools/engine_check.py` 四项全过（Pikafish / Rapfi / KataGo / 控制器）。
- 探针：存读边界 13 例、三棋整局对弈终止性、随机走子压力、引擎软失败回退、终局生命周期。
- 真机：源码版与打包版均启动成功、窗口标题正确、拉起引擎、优雅关闭回收引擎；
  打包版 `--selftest` 退出码 0，运行时 stderr 无 QML 告警。

---

## 本轮（吃子音效 / 两侧信息栏 / 引擎可见）

- **象棋吃子音效**：之前和落子都是木「嗒」，太像。改为**两记清脆相击 + 低闷**
  （首击 980Hz 更脆、次击 700Hz 更沉），与落子（780Hz 单响）明显区分，增益提到 0.80。
- **减少留白 + 沉浸**：宽窗（>1080px）时棋盘**两侧显示双方信息栏**（`PlayerCard`：
  侧色脉冲、名字、大号计时、提子/俘虏数），中间棋盘居中；窄窗自动隐藏、计时回到底栏。
- **引擎稳定性可见**：顶栏常显**引擎名 + 状态点**（AI 开时金色）。
  设置里新增「**检测**」按钮，调用 `EngineManager.probe()` 自检并 toast 结果
  （可用 / 未找到 / 已停用 / 已禁用），不用再猜引擎稳不稳。

---

## 本轮（落子/吃子音效 + 象棋杀法术语）

### 音效：落子 / 吃子
反馈「落子、吃子不好听」。原因是这四个音用的是 Karplus–Strong 拨弦——听感偏「弦响」，
不像石头/木子敲盘。改为**打击模型** `impact()`：宽频瞬态 + 几个快速衰减的泛音 + 低频闷击。
- `place`（象棋木子·低沉「笃」）、`place_stone`（围棋/五子棋石子·清脆「嗒」）、
  `capture`（木子相击 + 低闷）、`capture_stone`（几颗石子连撞）。
- 复测：首尾边界幅值 ≤0.005（无爆音），时长短促干脆（不再有拨弦拖尾）。

### 象棋杀法术语（`core/games/xiangqi.py`）
`_result_term` 原来只报「将死 / 困毙」。新增 `mate_term()` 识别常见杀法：
- **闷宫**（老将被自己子堵死 + 炮将）、**重炮**（老将线上两门炮）、
  **马后炮**（炮将 + 马控逃路）、**卧槽马**（马将），拿不准则回退「将死」。
- 术语会经 `TermBanner` 浮字显示（配色见上一轮）。

### 动效
- 落子增加**下落**动作（`dropAnim` 微幅下坠 + 回稳），配合新音效更有「放子」感。

### 测试
- 新增杀法识别与兜底 AI 用例；总数 **107 项全过**，`--selftest` 通过。

---

## 本轮（AI 兜底强化 + 更多特效）

反馈两点：兜底 AI 太弱、特效用得少。查证：**Rapfi 本身不弱**（挡四/挡活三/天元开局都正确，
整局能赢占位 AI）——但一旦引擎失败，「内置 AI」接管，而它原来的五子棋几乎是随机下，
看上去就是「棋力突然变弱、没法玩」。所以重点补兜底。

### 兜底 AI（`ai.py`）
- 五子棋重写为**形状打分**（(连子数, 开放端数) 加权 + 进攻×1.2/防守）：
  会成五、挡四、堵活三、自己做活三，不再随机。新增 4 项测试锁定这些战术。
- 引擎失败时**界面可见**：`notice` 提示「引擎不可用，已回退内置 AI」（每局一次），
  不至于让人以为是 AI 变傻了。

### 引擎选择（`engines/manager.py`）
- Rapfi 构建**按 CPU 能力自选**（`IsProcessorFeaturePresent`：avx512 > avx2 > sse）。
  之前硬编码 avx2，在不支持的机器上会崩溃并静默回退到弱 AI。

### 特效（QML）
- **将军暗角**：被将军时棋盘四周朱红呼吸。
- **AI 思考扫光**：思考时棋盘上一道暖金斜光扫过。
- **连五描线加外发光**；**落子涟漪**更大更久；**被吃/被提**的冲击环更明显。
- **术语浮字按类型配色**（吃子/提子/打吃/打劫→金，禁手→墨，和棋→灰，将军/连五→朱红）。

### 测试
- 新增 `tests/test_polish.py` 的兜底 AI 用例；总数 **102 项全过**，`--selftest` 通过。

---

## 本轮（沉浸打磨）

按「氛围音画 / 交互反馈 / 玩法完整度 / 细节与记忆」四个方向各补了一批。

### 细节与记忆
- **设置持久化**：新增 `appsettings.py`（`AppSettings`，QSettings 支撑），坐标 / 音效 / 音乐 /
  音量 / 难度 / 执子下次启动自动恢复；以上下文属性 `appSettings` 暴露。
  **删除了原 `Settings` QML 单例**（内存态、重启即丢）。`GameController(settings)` 把难度 /
  执子的改动落盘（`settings=None` 时保持无副作用，便于单测）。

### 交互反馈与手感
- 状态行显示 **AI 思考耗时 + 引擎名**（`thinkSeconds` / `aiEngine`），慢引擎不再像卡死。
- **看门狗按时长放宽**：围棋 20s、象棋/五子棋 10s（原统一 8s，慢机器上可能误判超时）。
- `TextButton` / `SegButton` 加**按压微动**；设置卡片补 **快捷键说明**。

### 玩法完整度
- **围棋终局目差**：`resultDetail` 给「共 N 手 · 黑 X 目 · 白 Y 目（含贴目）· 差 Z 目」，
  终局浮层与状态行展示。
- **棋谱纯文本导出**：`saveGame` 支持 `.txt`（中文记谱 / 坐标，含难度与结果），对话框加该格式。

### 氛围音画与动效
- **按棋种配乐**：`tools/gen_music.py` 扩为三段循环（`bgm_guqin` 五子棋 / `bgm_martial`
  象棋羽调式带鼓点 / `bgm_void` 围棋空灵），`Main.qml` 随棋种切换。
- **棋盘入场过渡**（换棋种 / 开新局时淡入 + 轻微缩放）。
- **五子棋连五描线**：落定后沿连线画一笔朱红（`controller.winLine` + `Canvas` 动画）。

### 测试
- 新增 `tests/test_polish.py`；总数 **98 项全过**，`--selftest` 通过。

---

## 本轮（运行时 bug 修复 + 音效重制）

对这版做了一次深入审查：单测实为 78 项（文档曾写 73），`--selftest` 通过，
说明缺陷都在测试覆盖不到的运行时/听感层面。本轮修掉的问题：

### 逻辑 / 交互
- **五子棋禁手形同虚设**：`newGame` 调 `gomoku_mod.new_game(15)`，`forbidden` 默认 `False`，
  黑棋长连不判负，「禁手」术语与 `forbidden.wav` 永不触发。改为 `forbidden=True`
  并在存读里持久化 `forbidden` 字段。
- **复盘态悔棋删错棋**：`undo()` 无条件 `pop()` 时间线末尾，不看 `_viewIndex`——
  在复盘时按悔棋会删掉「最新一手」而非正在看的那手。改为先截断到 `_viewIndex` 再撤。
- **引擎无超时看门狗**：引擎卡住/不回复时 `_ai_thinking` 永久为真，界面锁死。
  新增单发 `QTimer`（`ENGINE_TIMEOUT_MS = 8000`），超时记软失败并回退占位 AI。
- **非法点击零反馈**：新增 `pieceSelected` / `illegalMove` 信号，接上此前声明却从未播放的
  `select.wav` / `error.wav`。
- **象棋「最后一手」双标**：`_compute_marks` 同时标起点与终点（双环 + 双涟漪），
  改为只标落点，与五子棋/围棋一致。
- **开局整窗金色闪光**：`Main.qml` 的吃子闪光 `SequentialAnimation on opacity` 是属性值源动画，
  **默认自动运行**，启动即闪一次；加 `running: false`。
- **五子棋长连方向**：`_win_line_at` 取第一个 ≥5 的方向；改为取最长线，
  一手同时成五与长连时以长连（≥6）为准。
- **围棋 `is_legal` 终局守卫**：终局后 `is_legal` / `legal_moves` 返回空。

### 音效（重制 `tools/gen_sfx.py` 并重生成 20 个 wav）
问题根因量化后确认：每个音都归一化到峰值 **0.85**（UI 点击与胜利号角一样响），
且**从不做首尾淡出**，`place_stone` / `capture_stone` 等首尾样本跳变高达 ~1.3（硬切爆音）；
还大量使用 1.1k–2.3k Hz 的正弦 beep，与「国风」定位冲突。改法：
1. 每个音效带独立增益（click 0.30 → win 0.95），做出响度层次；
2. `write()` 一律首尾淡出；`noise()` 加 attack；统一过一阶低通；
3. 把 `click/check/panel/undo` 的高频正弦换成木击、闷响、上行三音等更柔和的音色。
重测：首尾边界幅值从最高 1.3 降到 **≤0.002**（无爆音），各音峰值拉开层次。

### 终局 / 复盘（第二轮复查）
顺着「一局结束以后会怎么样」把所有终局路径走了一遍，又抓到三处：

- **终局 → 复盘 → 悔棋直接崩**：`undo()` 先 `del _timeline[_viewIndex+1:]` 再 `pop()`——
  在第 0 手复盘时会把时间线清空，随后 `_timeline[-1]` 抛 `IndexError`。加 `len > 1` 守卫。
- **AI 思考时跳历史手会永久卡「思考中」**：玩家在引擎思考时打开棋谱点历史手，引擎应答被判
  「过期」丢弃，但丢弃分支没有清 `_ai_thinking`，而看门狗已在应答到达时停掉 → 永久卡死。
  丢弃分支现在会清思考态并 `_maybe_ai()` 重挂；`gotoMove()` 回到最新局面时也会重挂 AI。
- **双人模式认输判错方**：`resign()` 恒判 `opponent(humanSide)` 赢。改为双人模式由**当前行棋方**认输。

### 测试
- 新增 `tests/test_fixes.py`（12 项）锁定上述修复；总数 **90 项全过**。

---

## 一、本轮（国风重构 + 功能补全）做了什么

### 界面：整布局重做，取消侧边栏
- 旧的常驻右栏（306px）改为**三段式布局**：顶栏（品牌 + 棋种 + 棋谱/设置）/ 棋盘（居中吃满）/
  底栏（行棋方 + 双方计时 + 操作）。
- 棋谱、提子、对局信息收进**右侧滑入长卷**；难度/选边/坐标/声音收进**顶栏弹出卡片**；
  终局改为**常驻遮罩**（印章落印 + 再来一局 / 复盘）。
- **古典国风**皮肤：宣纸底、浅木纹棋盘、高对比棋盘线、朱红印章、楷/宋字体自动挑选
  （`Theme.pick()` 从 `Qt.fontFamilies()` 命中首个可用）。删除了所有 `✦ ↶ ⏸ ⚑ ♟`
  之类**表情/符号字符**，按钮只用文字，图形一律 Canvas 自绘。

### 功能补全
- **记谱**：新增 `core/games/notation.py`（象棋中文纵线含前/后、进/退/平；围棋/五子棋坐标）。
- **棋谱 + 复盘**：`MoveListModel` + `gotoMove/exitReview`，点历史手跳转，复盘态禁落子与 AI。
- **计时**：`QTimer` 累计双方用时，随历史回滚，复盘显示快照时间。
- **难度**：简单/普通/困难 → Pikafish `Skill Level`、KataGo `maxVisits`、Rapfi `timeout_turn`、
  占位 AI 深度。
- **选边**：`humanSide`，AI 执先会自动开局。
- **提子/俘虏**：象棋按初始局面差分，围棋用 `captures`。
- **存读**：统一 JSON 棋谱（重放），另可导出象棋 FEN / 围棋 SGF。
- **音乐**：`tools/gen_music.py`（Karplus–Strong 古琴循环）+ 设置里开关与音量。

### 规则 / 引擎健壮性
- **围棋 `pass`**：KataGo 回 `pass` 用哨兵 `MOVE_PASS` 表示 → `play(None)` 停一手，
  不再被当成非法着法；`GoState._pass()` 现在会把 `None` 写进 `moves`（修了回放/存档丢 pass 的老问题）。
- **引擎认输**：`MOVE_RESIGN` → 判负。
- **`_do_ai()` 异常保护**：`try/except` 包 `state.play()`，非法着法不再冒泡崩主线程。
- **引擎软失败重试**：硬失败（文件缺失）会话内停用；软失败（启动超时/协议异常）**允许重试一次**。
- **象棋重复局面 / 长将判负**：`XiangqiState.positions/givers` + `_repetition_result()`。
- **五子棋黑棋长连禁手**：`forbidden=True` 时黑 ≥6 连判负。

### 性能
- 象棋 `pseudo_moves/legal_moves/king_pos/kings_face/is_attacked` 全部 `lru_cache`，
  对外保持 `list` 返回语义。

### 素材管线
- 新增 `tools/gen_textures.py`（宣纸/浅木，zlib 手写 PNG）与 `tools/gen_music.py`；
  `tools/gen_sfx.py` 扩到 20 种音效。全部纯标准库、确定性、可复现。

### 第二轮（体验与性能）
- **围棋换网（最大改善）**：CPU（eigen）下把 `b10c384h6nbt`（变压器网，每次访问约 1s）
  换成 `g170-b10c128`（卷积网，约 25ms）——**快约 50 倍**：20 次访问 26.7s → 0.49s。
  围棋每步从 20–120s 降到 1–3s，同样时间能搜几十倍节点，**棋力反而更高**。
  难度改为 `maxVisits` + `maxTime` 双上限，切棋种时**预热引擎**隐藏模型加载。
- **音效 9 → 20 种**（Karplus–Strong 拨弦做木/石/古琴质感）：落子（木·石）、吃子（木·石）、
  将军、打吃、打劫、禁手、胜、负、和、停着、选中、按钮、悔棋、开局、错误、抽屉、面板开合。
- **术语**：`TermBanner` 术语浮字（将军 / 吃子 / 提子 / 打吃 / 打劫 / 连五 / 禁手 / 将死 /
  困毙 / 和棋 / 认输 / 停一手），由 `_announce()` **先**发 `eventChanged` **再**发 `moveMade`。
- **动画**：落子涟漪、**被吃/被提棋子飞离**、将军环、打劫点、吃子闪光。
- **操作成熟度**：底栏加「**换边**」；状态行显示「你执红/黑」；新局/换边/认输**二次确认**；
  快捷键 `Ctrl+N` / `Ctrl+Z` / `Esc`。

修复后：**单测通过**（当时 107 项），`--selftest` 通过，`tools/engine_check.py` 四项全过。

---

## 二、历史修复（第一轮，仍有效）

| # | 问题 | 位置 | 处理 |
|---|---|---|---|
| 1 | `--shot` 死代码（`grabToImage` 本机不回调） | `main.py`、`Main.qml` | 删除，截图走 `tools/shot.ps1` |
| 2 | 迟到引擎应答落到错误局面 | `controller._on_engine_move` | `_engine_asked` 校验，不匹配丢弃 |
| 3 | `_maybe_ai` 无重入保护 | `controller` | `if self._ai_thinking: return` |
| 4 | `resign()` 后 `_ai_thinking` 未清 | `controller` | 清并 emit |
| 5 | UCI `position fen` 起点用错 → 静默不回复 | `engines/uci.py` | 固定标准初始局面 + 完整着法 |
| 6 | 引擎退出先 kill 后断信号 → 崩溃 | `engines/base.stop` | 先断三个信号再退/kill |
| 7 | 单测真拉起引擎 | `tests/test_controller.py` | 设 `BOARD_NO_ENGINE=1` |

---

## 三、本轮过程中被测试抓到并修复的问题

- **`_compute_marks` 数组长度不匹配**：改用当前局面的格子数，不再引用模型的旧长度。
- **`_apply` 未同步棋谱模型**：普通落子后棋谱列表不刷新（已补 `_sync_moves()`）。
- **象棋两步选择误锁一方**：AI 关闭（双人对下）时只能动固定一方；改为「只能选当前行棋方的子」。
- **提子统计把空位当俘虏**：`Counter(INITIAL)` 把 `.` 也计进去 → 过滤空位。

---

## 四、未修复 / 待处理

### 高
1. **五子棋三三/四四禁手**未实现（长连已接线并有测试）。
2. ~~**打包**~~：**已完成** —— 见 `board-games.spec`（Windows onedir，约 318MB）。

### 中
3. **围棋形势判断/死活**：可接 `kata-analyze` 显示胜率/目差。
4. **棋谱只支持整局存取**：没有单步编辑 / 局面摆子 / 多格式导出（当前 JSON/FEN/SGF）。
5. **让子让先 / 残局**：`humanSide` 已有，让子局面未做。
6. **子进程残留风险**：Windows 上父进程被强杀时子引擎不自动退出，建议 Job Object 兜底。

### 低 / 整洁度
7. ~~`Theme.woodDeep`、`Theme.cinnabarSoft` 等若有未引用可清理。~~ 已清理：`woodDeep` 未引用已删，
   `cinnabarSoft` 仍在使用。
8. `ai.py` 围棋占位走法仍弱（最近邻随机），仅够演示。
9. `tools/export_canvas_image.py` 依赖本机 Edge 路径，换机器需改 `CANVAS_BLOB_DIR`。

---

## 五、性能

- 象棋 `legal_moves()` 已用 `lru_cache` 缓存（键 `(board, player)`）；选中高亮可走点不再重复重算。
  缓存无上限增长的风险由 `maxsize=8192` 约束。
- `BoardModel.set_board` 只在变化格发 `dataChanged`，落子动画不被重置——**别改成 `beginResetModel`**。
- 围棋 `is_legal()` 是常数级洪泛；不要在没有虚拟化的前提下调用 `GoState.legal_moves()`。
- 棋盘 `Repeater` 全量实例化（最多 19×19=361），delegate 很轻，可接受。

---

## 六、许可以与分发（务必知情）

| 组件 | 许可 |
|---|---|
| Pikafish 引擎 | 派生自 Stockfish（GPL-3.0） |
| **Pikafish NNUE 权重** | **独立许可**（商用需授权） |
| KataGo 引擎 | MIT |
| **KataGo 神经网络** | **独立许可** |
| Rapfi | 见其仓库 LICENSE |

随附分发前需逐一确认，尤其两个「权重许可」和 Pikafish 的 GPL 义务。

---

## 七、测试覆盖评估

| 范围 | 现状 | 缺口 |
|---|---|---|
| 规则层 | 好：44 步开局、长将/重复、禁手长连、围棋劫争/数目、五子棋连五 | 三三/四四禁手未实现 |
| 记谱 | 好：象棋开口/兵/前后/黑阿拉伯；围棋/五子棋坐标 | 复杂重子（>2 同线）用例可再补 |
| 控制器 | 好：走子/悔棋/胜负/引擎应答校验/复盘/存读/选边/难度/提子 | 「悔棋与引擎并发」仍偏薄 |
| 引擎 | 中：坐标回环 + 路径；真引擎行为靠 `engine_check.py` | 缺可 skip 的集成测试 |
| QML | 弱：只有 `--selftest` 冒烟 | 无交互/渲染断言（离屏字体库为空，文字验证只能在真机） |

> 建议：把 `tools/engine_check.py` 的四个判定迁到 `tests/` 并在无引擎时 `skipTest`。
