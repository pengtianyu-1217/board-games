# 三棋对弈（中国象棋 · 围棋 · 五子棋）

一个 PySide6 + QML 桌面应用：三种棋都能**人机对战**，AI 全部由**外部引擎**驱动
（象棋 Pikafish / 围棋 KataGo / 五子棋 Rapfi）。界面走**古典国风**——宣纸为底、
木纹为盘、朱红为印、楷宋为字；无侧边栏，棋谱与设置按需折叠展开。

## 运行

```bash
python -m pip install -r requirements.txt
python main.py                    # 启动图形界面
python main.py --game xiangqi     # 指定开局棋种（gomoku / xiangqi / go）
python main.py --demo             # 开局后自动走一步，便于观察引擎应招
python main.py --no-engine        # 强制使用内置占位 AI
python main.py --selftest         # 只加载 QML 校验，无头冒烟
```

环境变量：`BOARD_NO_ENGINE=1` 关引擎；`BOARD_ENGINE_LOG=1` 打印引擎日志。

## 玩法与功能

- 顶部切换棋种：**五子棋 / 象棋 / 围棋**；棋盘点击落子；象棋是「先点自己的子 → 再点落点」两步。
- 底部工具条：新局 / 悔棋 / 停一手（围棋）/ **换边** / 认输 / AI 开关；
  行棋方指示 + **双方计时**，状态行会显示「你执红/黑」。
  - **换边**：一键交换先后手并重开（AI 会先手）；也可在设置里直接选执子方。
  - 新局 / 换边 / 认输 在**对局进行中**会先弹确认，避免误触。
  - 快捷键：`Ctrl+N` 新局、`Ctrl+Z` 悔棋、`Esc` 收起浮层。
- 顶栏「**棋谱**」：右侧滑入长卷，含对局信息、可点击跳转的**棋谱列表（复盘）**、
  **提子/俘虏**，以及**保存 / 打开棋谱**（JSON，另可导出象棋 FEN、围棋 SGF、纯文本棋谱）。
- 顶栏「**设置**」：**难度**（简单/普通/困难）、**执子选边**（红/黑 或 黑/白）、
  棋盘**坐标标注**、**音效 / 背景音乐开关与音量**，附**快捷键**说明。
  以上偏好会**记忆到下次启动**。
- **配乐随棋种切换**：五子棋古琴、象棋激越、围棋空灵（`assets/audio/bgm_*.wav`）。
- 状态行显示 **AI 思考耗时与引擎名**（如「对手思考中 · KataGo · 3s」）。
- **棋盘两侧**（宽窗时）显示双方信息栏：侧色、名字、计时、提子/俘虏数。
- 顶栏常显**当前引擎名与状态点**；设置里可「**检测引擎**」自检（可用 / 未找到 / 已停用）。
- 终局常驻「对局结束」浮层（印章落印），可**再来一局**或**复盘**。

> **引擎响应速度**：象棋 Pikafish ≈ 1s、五子棋 Rapfi ≈ 1s、围棋 KataGo ≈ 1–3s。
> 关键经验：CPU（eigen）版**不能用变压器网络**——原来的 `b10c384h6nbt` 每访问约 1 秒；
> 换成 `g170-b10c128` **卷积网络后快约 50 倍**（20 次访问从 26s → 0.5s），
> 同样时间能搜几十倍节点，实际棋力反而更高。难度同时给 `maxVisits` 与 `maxTime` 上限，
> 并在切换棋种时**预热引擎**，把模型加载藏在对局准备阶段。

## 目录结构

```
main.py                 入口（--game / --demo / --no-engine / --selftest）
appsettings.py          用户偏好持久化（QSettings：坐标/音量/难度/执子）
controller.py           QML 与规则层、引擎层之间的桥
                        （BoardModel + MoveListModel + GameController）
ai.py                   占位 AI（引擎缺失时兜底，随难度调整）
core/games/             纯 Python 规则层，零 Qt
  base.py               公共常量
  gomoku.py             五子棋：四方向五连、和棋、黑棋长连禁手
  xiangqi.py            象棋：马腿/象眼/炮架/将帅照面/困毙、重复局面与长将判负、FEN
  go.py                 围棋：提子/劫杀/禁着点/数目/SGF（停一手入历史）
  notation.py           记谱：象棋中文纵线、围棋/五子棋坐标
engines/                外部引擎适配（QProcess + 文本协议，含难度参数）
  base.py               子进程、按行收发、超时与优雅退出、pass/resign 哨兵
  gtp.py                KataGo（围棋，GTP，maxVisits 随难度）
  uci.py                Pikafish（象棋，UCI，Skill Level 随难度）
  piskvork.py           Rapfi（五子棋，Piskvork/Gomocup，timeout 随难度）
  manager.py            按棋种选引擎，软/硬失败区分，异常自动回退占位 AI
  bin/ nets/            引擎可执行文件、配置与 KataGo 网络
qml/
  Main.qml              三段式布局（顶栏 / 棋盘 / 底栏）+ 抽屉 / 设置 / 终局浮层 + 音效音乐
  components/           Theme/Settings 单例、BoardArea、SegButton、TextButton、Toggle、
                        MoveDrawer、MoveList、Clock、CapturedTray、SettingsPopover、
                        EndOverlay、Seal、SectionTitle
assets/
  art/                  paper.png（宣纸）· wood_light.png（浅木）
  audio/                 bgm_guqin / bgm_martial / bgm_void.wav（按棋种循环）+ 成套音效 wav
tools/
  gen_textures.py       纯标准库合成宣纸 / 木纹贴图（zlib 手写 PNG）
  gen_music.py          纯标准库合成按棋种的三段循环（古琴/激越/空灵，Karplus–Strong）
  gen_sfx.py            纯标准库合成音效
  engine_check.py       三引擎 + 控制器端到端自检
  export_canvas_image.py 从浏览器 IndexedDB 导出「无限画布」生成的图片
  shot.ps1              按窗口 PID 截屏
tests/                  111 项单测
shots/                  界面截图
```

## 外部引擎

| 棋种 | 引擎 | 协议 | 难度映射 |
|---|---|---|---|
| 象棋 | Pikafish | UCI | `Skill Level` + movetime |
| 围棋 | KataGo（eigen/CPU 版） | GTP | `maxVisits` |
| 五子棋 | Rapfi | Piskvork | `INFO timeout_turn` |

- 本机无 N 卡，故 KataGo 用 **eigen（纯 CPU）** 构建；网络取 GitHub 托管的
  `b10c384h6nbttflrs`（CPU 友好）。
- 自检：`python tools/engine_check.py` —— 逐个引擎要一步棋（五子棋会验证它是否
  **正确挡四**，用来证明坐标映射没错），最后再用控制器跑一遍完整人机流程。
- 引擎不可用时自动回退到 `ai.py` 的占位 AI，界面不会崩。

> **许可**：三个引擎本体与各自神经网络权重的许可是分开的（KataGo 网络、Pikafish
> NNUE 另有条款），随附分发前需分别确认。

## 美术与音频

- **宣纸 / 浅木纹**：`python tools/gen_textures.py` 纯标准库合成（zlib 手写 PNG），
  确定性、可复现，不依赖外部服务。
- **背景音乐**：`python tools/gen_music.py` 用 **Karplus–Strong** 拨弦合成三段五声音阶
  循环（`bgm_guqin` 五子棋 / `bgm_martial` 象棋 / `bgm_void` 围棋），QML `MediaPlayer`
  随棋种切换并循环播放。
- **音效**：`python tools/gen_sfx.py` 纯标准库合成 **20 种**、以 Karplus–Strong 拨弦做
  木子/石子/古琴质感：落子（木·石）、吃子（木·石）、将军、**打吃**、**打劫**、
  **禁手**、胜利、失败、**和棋**、停一手、选中、按钮、**悔棋**、**开局**、错误、
  抽屉、**面板开 / 关**。
- **动效**：落子弹入 + 投影 + **涟漪**、**被提/被吃棋子飞离**、吃子闪光、最后一手环、
  选中环、可走点、**将军环**、**打劫点**、连五呼吸高亮、**术语浮字（将军 / 打吃 / 提子 /
  打劫 / 连五 / 禁手 / 将死 / 困毙 / 和棋 / 认输 / 停一手）**、AI 思考脉冲、棋谱行淡入、
  抽屉滑入、换棋种淡入、终局印章落印。

## 文档

| 文档 | 内容 |
|---|---|
| [`AGENTS.md`](./AGENTS.md) | **接手先读**：架构、不可破坏的不变量、踩过的坑、下一步 |
| [`docs/DESIGN.md`](./docs/DESIGN.md) | 分层设计、规则层契约、坐标与协议约定、界面与素材管线 |
| [`docs/REVIEW.md`](./docs/REVIEW.md) | 代码审查：已修复问题、待办、性能、许可、测试覆盖 |

## 测试

```bash
python -m unittest discover -s tests      # 111 项
python tools/engine_check.py              # 引擎端到端自检（需引擎在位）
```

## 重新生成美术 / 音频

```bash
python tools/gen_textures.py   # assets/art/paper.png, wood_light.png
python tools/gen_music.py      # assets/audio/bgm_guqin.wav
python tools/gen_sfx.py        # assets/audio/*.wav
```

## 打包（Windows）

```bash
python -m pip install pyinstaller

# ① onedir（推荐）：产物是文件夹，压成 zip 分发，启动快
python -m PyInstaller board-games.spec --noconfirm --clean
#   → dist/三棋对弈/三棋对弈.exe  （连同同级 _internal/ 一起分发）

# ② 单文件（可选）：产物是单个 exe，可直接拷贝，但每次启动要解压 ~300MB，明显更慢
python -m PyInstaller board-games-onefile.spec --noconfirm --clean --distpath dist-single --workpath build-single
#   → dist-single/三棋对弈.exe
```

**分发方式**

| 方式 | 产物 | 体积 | 启动 | 说明 |
|---|---|---|---|---|
| onedir + zip（推荐） | `dist/三棋对弈-win64.zip` | 184MB | ~1s | 解压即用；`三棋对弈.exe` **不能单独拷**，必须连同 `_internal/` |
| 单文件 onefile | `dist-single/三棋对弈.exe` | 183MB | ~5–6s | 一个文件好传，代价是每次启动解压到临时目录 |

> 单文件版运行期会在 `%TEMP%\_MEIxxxxxx` 解压约 316MB，正常退出会清理；
> 被强杀时可能残留（用上面的 Job Object 只会顺带结束子引擎，不会删临时目录）。


`board-games.spec` 已经做好取舍，只装运行需要的东西：

- **引擎**：只带 Windows 二进制；剔除非 Windows 版、Rapfi 未使用的指令集构建、KataGo 运行日志。
- **网络**：只带在用的卷积网 `g170-b10c128`（其余备用网留在源码仓库，不进包）。
- **Qt**：只带 QML 用到的模块（QtQml / QtQuick / QtMultimedia），剔掉 WebEngine（~194MB）、
  Widgets、Quick3D、Pdf 与多余翻译 —— 打包体积约 318MB（未裁剪时约 562MB）。

冒烟自检：

```bash
dist\三棋对弈\三棋对弈.exe --selftest   # 退出码 0 = QML 加载正常
```

> 注意：窗口程序（console=False）下 `sys.stdout/stderr` 为 `None`，代码里输出一律走
> `main._emit()`，别直接 `print`/`sys.stdout.write`，否则打包版会异常退出。

