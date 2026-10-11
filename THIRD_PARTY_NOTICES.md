# 第三方组件许可声明（THIRD PARTY NOTICES）

本项目（**三棋对弈**）自身代码与仓库内的第三方引擎二进制、神经网络权重是**两回事**，
许可条款各不相同。本文件逐项列明 `engines/` 下随仓库分发的每一个第三方组件及其许可，
供使用者核对与追溯。

> 核对时间：2026-10-11
> 核对方式：以各组件**上游仓库/官方站点的许可原文**为准，本地文件仅作为副本随附。
> **如发现本文件与上游最新许可不一致，以上游为准**，并请提 Issue 更正。

---

## 一、本项目自有代码

**MIT License**，Copyright (c) 2026 shaqimadawang (pengtianyu-1217)。全文见 [`LICENSE`](./LICENSE)。

这个许可**只覆盖本项目自己写的部分**：`main.py`、`appsettings.py`、`controller.py`、`ai.py`、
`core/`、`qml/`、`tools/`、`tests/`，以及 `assets/` 下自制的美术与音频。
**不覆盖** `engines/` 下的任何第三方引擎二进制与神经网络权重——那部分见第二节起。

### 为什么自有代码用 MIT 而不用 GPL-3.0

本项目通过 **stdin/stdout 文本协议启动独立子进程**（`QProcess`）的方式调用 Pikafish、
KataGo、Rapfi：各引擎是**独立可执行文件**，既不静态链接进本项目，也不复制其源码到本项目，
二者之间隔着操作系统进程边界。

FSF（GPL 制定方）对这类情形的立场是：通过进程边界交互的独立程序**不构成衍生作品**
（同"编辑器调用 shell 脚本""浏览器请求 Web 服务器"）。因此 GPL-3.0 的 copyleft 传染性
不会传导至本项目自有代码。

**注意**：即便采用 MIT，本项目在**分发**时仍须履行 GPL-3.0 对二进制分发的义务——
附 GPL 全文、保留版权声明、提供源码获取途径。这三项已分别由
`engines/bin/*/Copying.txt`、各引擎目录内的许可文件、以及本文第五节满足。

---

## 二、组件总览

| 组件 | 路径 | 许可 | 可商用 | 随附原文 |
|---|---|---|---|---|
| Pikafish 引擎 | `engines/bin/pikafish/` | **GPL-3.0** | 允许（copyleft） | `Copying.txt` |
| Pikafish NNUE 权重 | `engines/bin/pikafish/pikafish.nnue` | **Pikafish NNUE-License**（专有） | **需单独许可** | `NNUE-License.md` |
| KataGo 引擎 | `engines/bin/katago/` | **MIT** | 允许 | `LICENSE` |
| KataGo 网络 `b10c384` | `engines/nets/b10c384h6nbttflrs.bin.gz` | **KataGo NN License**（MIT 类） | 允许 | 见下链接 |
| KataGo 网络 `g170` ×2 | `engines/nets/g170-*.bin.gz` | **CC0 1.0**（公共领域） | 允许 | 见下链接 |
| Rapfi 引擎 | `engines/bin/rapfi/` | **GPL-3.0** | 允许（copyleft） | `Copying.txt` |
| Rapfi 网络权重 | `engines/bin/rapfi/*.bin.lz4` | **CC0 1.0** | 允许 | 见下链接 |

---

## 三、逐项详述

### 3.1 Pikafish —— 中国象棋引擎

- **作品**：Pikafish（Stockfish 血统的 UCI 中国象棋引擎）
- **版本**：随 `Pikafish-Windows-x86-64-universal.exe` 等发行包分发，具体版本见该包内文件
- **许可**：**GNU General Public License v3.0**
- **作者**：Pikafish 团队 <https://github.com/official-pikafish/Pikafish>
- **源码获取**：<https://github.com/official-pikafish/Pikafish>
- **许可全文副本**：`engines/bin/pikafish/Copying.txt`
- **附带文件**：`AUTHORS`、`CONTRIBUTING.md`、`Top CPU Contributors.txt`、`Wiki/`

**你需要注意的义务**：GPL-3.0 是 copyleft 许可。若你**分发**本项目（含本引擎二进制），
须随附 GPL-3.0 全文（已随附于上述路径）、保留全部版权声明，并提供对应**源码获取途径**
（见第五节）。

### 3.2 Pikafish NNUE 权重 —— ⚠️ 独立于引擎本体的专有许可

- **作品**：`pikafish.nnue`（50,706,378 字节）
- **许可**：**Pikafish NNUE-License** —— 这是**与 GPL-3.0 分开的另一套条款**，不随引擎本体的 GPL 授权
- **许可全文副本**：`engines/bin/pikafish/NNUE-License.md`
- **要点（原文条款）**：
  1. 仅限合法用途；超出合法范围使用（如**在线作弊**）的后果由用户自行承担
  2. **未经许可不得用于商业用途**；许可名单所列个人与组织可商用
- **补充**：Fairy-Stockfish 使用的、基于 Pikafish 数据训练的另一套权重，
  由官方以 **CC0** 发布，不受本许可约束

> **这条是本仓库中限制最强的一项。** 目前的公开仓库属于**非商业分发**，不触发第 2 条。
> 但如果本项目将来用于**商业分发**，`pikafish.nnue` 必须**单独取得许可或替换**，
> 不能沿用 GPL 合规来推断其可商用。

### 3.3 KataGo —— 围棋引擎

- **作品**：KataGo v1.18.1（AlphaZero 风格 MCTS + 深度学习围棋引擎）
- **作者**：David J. Wu ("lightvector")，另见 `CONTRIBUTORS`
- **许可**：**MIT License**
- **源码获取**：<https://github.com/lightvector/KataGo>
- **许可全文副本**：`engines/bin/katago/LICENSE`（本仓库新增，自上游补齐）
- **论文**：Wu, D. J. *Accelerating Self-Play Learning in Go*, arXiv:1902.10565

**MIT 义务很简单**：在所有副本或实质性部分中保留版权声明与许可声明。已随附于上述路径。

#### 3.3.1 KataGo 随附的系统库

`engines/bin/katago/` 下另有若干随官方 Windows 发行版一同分发的运行库，
**各自适用其上游许可**，不适用 MIT：

| 文件 | 组件 | 许可 |
|---|---|---|
| `libcrypto-3-x64.dll`、`libssl-3-x64.dll` | OpenSSL 3.x | Apache License 2.0 |
| `z.dll` | zlib | zlib License |
| `bz2.dll` | bzip2 | bzip2 License |
| `cacert.pem` | Mozilla CA 证书包 | MPL 2.0 |
| `msvcp140*.dll`、`vcruntime140*.dll` | Microsoft Visual C++ 运行时 | Microsoft EULA |

> 这些库由 KataGo 上游打包分发。若你需要完整清单，请查 KataGo 仓库
> `cpp/external/` 下各子目录的 README 与许可文件，或查阅 KataGo 的 `LICENSE` 首段说明。

### 3.4 KataGo 神经网络权重 —— ⚠️ 按训练批次适用不同许可

KataGo 的**代码是 MIT，但神经网络权重另有专门许可**，且**权重之间彼此不同**。

**许可原文**：<https://katagotraining.org/network_license/>

本仓库所含三个权重文件的归属与许可：

| 文件 | 大小 | 训练批次 | 许可 |
|---|---|---|---|
| `b10c384h6nbttflrs.bin.gz` | 38,245,488 | `b10c384` | **KataGo Neural Network License**（MIT 式条款，Copyright 2026 David J Wu） |
| `g170-b10c128-s197428736-d67404019.bin.gz` | 11,138,987 | **`g170`** | **CC0 1.0**，公共领域 |
| `g170-b6c96-s175395328-d26788732.bin.gz` | 3,827,339 | **`g170`** | **CC0 1.0**，公共领域 |

> **关键区分**：官方许可页面明确写明，**`g170` 批次是最早一批网络，不适用上述 MIT 式许可，
> 而是以 CC0 释出（即实质公共领域）**。本项目默认加载的
> `g170-b10c128-s197428736-d67404019.bin.gz` 正属于这一类，**限制最少**。
>
> 若将来换用较新的 `kata1` 批次权重，需回到该页面重新核对条款。

### 3.5 Rapfi —— 五子棋引擎

- **作品**：Rapfi（Renju / Gomocup / Freestyle 五子棋引擎，Piskvork 协议）
- **版本**：配置声明最低要求 0.43.1（`engines/bin/rapfi/config.toml` 的 `min_version`）
- **许可**：**GNU General Public License v3.0**
- **作者**：Haobin Duan (dblue)、HZY (sigmoid)、Joker2770、crsov、
  nguyencongminh090、subarashikihibi —— 完整名单见 `engines/bin/rapfi/AUTHORS`
- **源码获取**：<https://github.com/dhbloo/Rapfi>
- **许可全文副本**：`engines/bin/rapfi/Copying.txt`（本仓库新增，自上游补齐）

Rapfi 采用了一部分 Stockfish 的代码，故继承 GPL-3.0。义务同 3.1。

### 3.6 Rapfi 神经网络权重 —— CC0，最宽松

- **作品**：`mix9svq*.bin.lz4`（4 个）、`model210901.bin`
- **许可**：**CC0 1.0 Universal**（公共领域奉献，作者放弃全部权利）
- **权重仓库**：<https://github.com/dhbloo/rapfi-networks>
- **许可原文**：该仓库根目录 `LICENSE`

> CC0 是最宽松的许可：可用于商业用途、可修改、无署名义务。
> 这是本仓库中**限制最少**的一类资产。

---

## 四、快速结论

- **想商用**，唯一需要额外处理的是 **`pikafish.nnue`**（见 3.2），其余组件
  KataGo 权重、Rapfi 权重、Rapfi 引擎、GPT 代码均为 MIT / GPL / CC0，允许商用
  （GPL 组件需以 GPL 方式一并发布）。
- **想自由使用/学习/二次开发**，本仓库内所有组件均无障碍。
- **`g170` 权重与 Rapfi 权重是 CC0**，可无条件取用。

---

## 五、源码获取途径（GPL-3.0 §6 要求）

GPL-3.0 允许以二进制形式分发，但须附带完整源码或**明确的源码获取途径**。
本项目通过以下方式满足该要求：

| 组件 | 源码地址 |
|---|---|
| Pikafish | <https://github.com/official-pikafish/Pikafish> |
| Rapfi | <https://github.com/dhbloo/Rapfi> |
| KataGo | <https://github.com/lightvector/KataGo> |
| KataGo 网络权重 | <https://katagotraining.org/network_license/> |
| Rapfi 网络权重 | <https://github.com/dhbloo/rapfi-networks> |
| **本项目自身** | 见仓库 <https://github.com/pengtianyu-1217/board-games> |

---

## 六、如何自行复核

本文件不替代原始许可。要确认某一具体组件的义务，请：

1. 打开对应引擎目录内的许可副本（`Copying.txt` / `LICENSE` / `NNUE-License.md`）
2. 或访问第三节给出的上游链接，以**上游最新版本**为准
3. 涉及商业用途或有法律疑问时，请咨询专业法律意见

---

## 七、致谢

- **Pikafish** 团队及其 CPU Contributors、算力提供方
- **David J. Wu (lightvector)** 与 KataGo 分布式训练社区
- **Rapfi** 团队，以及 Stockfish / Fairy-Stockfish 的贡献者

三者的贡献使本项目得以实现"三棋皆可人机对战"。
