"""合成游戏音效（纯标准库，无需外部素材）。

音色以 Karplus–Strong 拨弦 + 正弦/噪声为基础，做出木子、石质、古琴、闷响等质感。
输出到 assets/audio/*.wav。想换音色改这里的参数即可。

关键处理（针对「刺耳 / 爆音」的老问题）：
  1. 每个音效自带增益（gain），UI 点击远小于胜利号角——不再一律拉满。
  2. write() 一律做首尾淡出，消除硬切产生的 click/pop。
  3. noise() 带 attack 包络，避免全幅起音的爆点。
  4. 统一过一阶低通，削掉噪声与高音正弦的毛刺。

音效清单：
  落子      place（木子/象棋）· place_stone（石子/围棋·五子棋）
  吃子      capture（木）· capture_stone（石子碰撞）
  围棋      atari（打吃）· ko（打劫）· pass（停一手）
  象棋      check（将军）
  终局      win · lose · draw
  五子棋    forbidden（禁手）
  界面      click · select · undo · newgame · error · drawer · panel_open · panel_close
"""

import math
import random
import struct
import wave
from pathlib import Path

SR = 44100
OUT = Path(__file__).resolve().parent.parent / "assets" / "audio"


# ---------------------------------------------------------------- 基础 DSP
def soft_clip(x):
    return math.tanh(x * 1.2)


def lowpass(buf, cutoff):
    """一阶低通（就地），削高频毛刺。"""
    a = math.exp(-2.0 * math.pi * cutoff / SR)
    y = 0.0
    for i in range(len(buf)):
        y = (1.0 - a) * buf[i] + a * y
        buf[i] = y


def fade_edges(buf, head=0.0015, tail=0.012):
    """首尾淡出，消除硬切爆音。"""
    n = len(buf)
    h = min(int(head * SR), n // 2)
    t = min(int(tail * SR), n // 2)
    for i in range(h):
        buf[i] *= i / h
    for i in range(t):
        buf[n - 1 - i] *= i / t


def pluck(freq, dur, damping=0.996, bright=0.5, seed=None):
    """Karplus–Strong 拨弦：返回一段浮点样本（用局部 RNG，不污染全局）。"""
    rng = random.Random(seed) if seed is not None else random
    n = int(SR * dur)
    line = max(2, int(round(SR / freq)))
    buf = [rng.uniform(-1.0, 1.0) * (0.5 + 0.5 * bright) for _ in range(line)]
    out = [0.0] * n
    idx = 0
    prev = 0.0
    for i in range(n):
        cur = buf[idx]
        out[i] = cur
        buf[idx] = (0.5 * (cur + prev)) * damping
        prev = cur
        idx += 1
        if idx >= line:
            idx = 0
    return out


def add(buf, wave_, offset, amp=1.0, atk=0.003):
    off = int(offset * SR)
    a = max(1, int(atk * SR))
    for i, v in enumerate(wave_):
        j = off + i
        if j >= len(buf):
            break
        env = i / a if i < a else 1.0
        buf[j] += v * amp * env


def tone(buf, freq, dur, offset=0.0, amp=0.4, decay=0.25, attack=0.004):
    off = int(offset * SR)
    n = int(SR * dur)
    a = max(1, int(attack * SR))
    for i in range(n):
        j = off + i
        if j >= len(buf):
            break
        t = i / SR
        env = math.exp(-t / decay)
        if i < a:
            env *= i / a
        buf[j] += math.sin(2 * math.pi * freq * t) * env * amp


def noise(buf, dur, offset=0.0, amp=0.3, decay=0.03, attack=0.0012):
    off = int(offset * SR)
    n = int(SR * dur)
    a = max(1, int(attack * SR))
    for i in range(n):
        j = off + i
        if j >= len(buf):
            break
        env = math.exp(-(i / SR) / decay)
        if i < a:
            env *= i / a
        buf[j] += random.uniform(-1, 1) * env * amp


def empty(dur):
    return [0.0] * int(SR * dur)


def impact(buf, offset=0.0, freq=900.0, amp=0.8, decay=0.035, thud=180.0, thud_amp=0.5):
    """一次敲击：宽频瞬态 + 几个快速衰减的泛音 + 低频闷击。

    比拨弦更像「石头/木子敲盘」——短促、干脆，没有弦振的拖尾。
    """
    noise(buf, 0.012, offset, amp=0.55 * amp, decay=0.0022, attack=0.0004)
    for k, ratio in enumerate((1.0, 1.61, 2.34, 3.15)):
        tone(buf, freq * ratio, min(0.13, decay * 3.2), offset,
             amp=amp * (0.55 ** k), decay=decay * (1.0 - 0.12 * k), attack=0.0007)
    tone(buf, thud, 0.10, offset, amp=thud_amp * amp, decay=0.03, attack=0.0010)


def write(name, buf, gain=0.6):
    fade_edges(buf)
    peak = max(1e-6, max(abs(v) for v in buf))
    scale = gain / peak
    data = [int(max(-1.0, min(1.0, soft_clip(v * scale))) * 32767) for v in buf]
    OUT.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT / name), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", s) for s in data))
    print("wrote", name, len(data), "samples")


# ---------------------------------------------------------------- 落子
def s_place():                 # 象棋：木子落盘（低沉「笃」）
    b = empty(0.22)
    impact(b, 0.0, freq=780, amp=0.9, decay=0.042, thud=150, thud_amp=0.55)
    lowpass(b, 3600)
    return b


def s_place_stone():           # 围棋 / 五子棋：石子落盘（清脆「嗒」）
    b = empty(0.20)
    impact(b, 0.0, freq=1500, amp=0.85, decay=0.026, thud=230, thud_amp=0.4)
    lowpass(b, 6500)
    return b


# ---------------------------------------------------------------- 吃子
def s_capture():               # 象棋吃子：两记干脆的木子相击 + 低闷（比落子更脆、更重）
    b = empty(0.38)
    impact(b, 0.000, freq=980, amp=0.95, decay=0.030, thud=150, thud_amp=0.45)
    impact(b, 0.052, freq=700, amp=0.78, decay=0.045, thud=120, thud_amp=0.55)
    lowpass(b, 4200)
    return b


def s_capture_stone():         # 围棋 / 五子棋：几颗石子连撞
    b = empty(0.36)
    for k, f in enumerate((1500, 1880, 1240, 2150)):
        impact(b, 0.032 * k, freq=f, amp=0.5, decay=0.028, thud=240, thud_amp=0.35)
    lowpass(b, 7000)
    return b


# ---------------------------------------------------------------- 围棋 / 象棋术语
def s_atari():
    b = empty(0.55)
    tone(b, 330, 0.50, 0.0, amp=0.50, decay=0.30, attack=0.006)
    tone(b, 494, 0.40, 0.02, amp=0.20, decay=0.22, attack=0.006)
    lowpass(b, 3000)
    return b


def s_ko():
    b = empty(0.60)
    add(b, pluck(294, 0.30, damping=0.995, seed=20), 0.0, 0.70, atk=0.003)
    add(b, pluck(440, 0.30, damping=0.995, seed=21), 0.16, 0.65, atk=0.003)
    lowpass(b, 3200)
    return b


def s_check():
    # 温和的上行三音，取代原来 1.1k–2.3k 的刺耳高音
    b = empty(0.60)
    tone(b, 392.00, 0.45, 0.00, amp=0.42, decay=0.22, attack=0.006)
    tone(b, 523.25, 0.45, 0.09, amp=0.34, decay=0.22, attack=0.006)
    tone(b, 659.25, 0.40, 0.18, amp=0.26, decay=0.20, attack=0.006)
    lowpass(b, 3800)
    return b


def s_forbidden():
    # 低沉警示闷响 + 轻微拍频，不再是嗡嗡爆麦
    b = empty(0.42)
    tone(b, 138, 0.32, 0.0, amp=0.50, decay=0.14, attack=0.004)
    tone(b, 131, 0.32, 0.0, amp=0.40, decay=0.14, attack=0.004)   # 拍频 ≈ 7Hz
    noise(b, 0.10, 0.0, amp=0.14, decay=0.04, attack=0.003)
    lowpass(b, 1400)
    return b


# ---------------------------------------------------------------- 终局
def s_win():
    b = empty(1.50)
    for k, f in enumerate((261.63, 329.63, 392.00, 523.25, 659.25)):
        add(b, pluck(f, 1.0, damping=0.9975, seed=30 + k), 0.13 * k, 0.6, atk=0.004)
    lowpass(b, 4200)
    return b


def s_lose():
    b = empty(1.20)
    for k, f in enumerate((349.23, 277.18, 207.65)):
        add(b, pluck(f, 0.85, damping=0.9955, seed=40 + k), 0.18 * k, 0.62, atk=0.004)
    lowpass(b, 2600)
    return b


def s_draw():
    b = empty(0.90)
    add(b, pluck(261.63, 0.65, damping=0.996, seed=50), 0.0, 0.55, atk=0.004)
    add(b, pluck(392.00, 0.65, damping=0.996, seed=51), 0.18, 0.55, atk=0.004)
    lowpass(b, 3400)
    return b


# ---------------------------------------------------------------- 界面
def s_click():
    b = empty(0.05)
    tone(b, 620, 0.035, 0.0, amp=0.50, decay=0.012, attack=0.0008)
    noise(b, 0.008, 0.0, amp=0.12, decay=0.002, attack=0.0005)
    lowpass(b, 3000)
    return b


def s_select():
    b = empty(0.08)
    tone(b, 784, 0.06, 0.0, amp=0.40, decay=0.020, attack=0.0012)
    lowpass(b, 3600)
    return b


def s_pass():
    b = empty(0.42)
    tone(b, 330, 0.35, 0.0, amp=0.40, decay=0.18, attack=0.006)
    lowpass(b, 2600)
    return b


def s_undo():
    # 两声下行的柔和木击，取代原来的扫频 beep
    b = empty(0.32)
    add(b, pluck(300, 0.14, damping=0.994, seed=60), 0.0, 0.55, atk=0.002)
    add(b, pluck(240, 0.16, damping=0.994, seed=61), 0.09, 0.50, atk=0.002)
    lowpass(b, 2800)
    return b


def s_newgame():
    b = empty(1.00)
    tone(b, 98, 0.90, 0.0, amp=0.50, decay=0.42, attack=0.006)
    tone(b, 147, 0.70, 0.0, amp=0.26, decay=0.30, attack=0.006)
    noise(b, 0.16, 0.0, amp=0.12, decay=0.05, attack=0.003)
    lowpass(b, 1600)
    return b


def s_error():
    b = empty(0.36)
    tone(b, 196, 0.13, 0.00, amp=0.45, decay=0.045, attack=0.002)
    tone(b, 165, 0.18, 0.13, amp=0.45, decay=0.055, attack=0.002)
    lowpass(b, 2000)
    return b


def s_drawer():
    # 柔和的开合"呼"声
    b = empty(0.26)
    noise(b, 0.13, 0.00, amp=0.22, decay=0.045, attack=0.004)
    tone(b, 160, 0.10, 0.01, amp=0.28, decay=0.050, attack=0.004)
    lowpass(b, 2200)
    return b


def s_panel_open():
    b = empty(0.30)
    add(b, pluck(330, 0.18, damping=0.994, bright=0.30, seed=70), 0.0, 0.40, atk=0.003)
    noise(b, 0.12, 0.0, amp=0.10, decay=0.05, attack=0.004)
    lowpass(b, 2600)
    return b


def s_panel_close():
    b = empty(0.30)
    add(b, pluck(247, 0.18, damping=0.994, bright=0.30, seed=71), 0.0, 0.40, atk=0.003)
    noise(b, 0.12, 0.0, amp=0.10, decay=0.05, attack=0.004)
    lowpass(b, 2400)
    return b


# ---------------------------------------------------------------- 汇总
# name -> (生成函数, 增益)。增益做出层次：UI 轻点 < 落子 < 术语 < 终局号角。
SOUNDS = {
    "place.wav":         (s_place, 0.62),
    "place_stone.wav":   (s_place_stone, 0.60),
    "capture.wav":       (s_capture, 0.80),
    "capture_stone.wav": (s_capture_stone, 0.70),
    "atari.wav":         (s_atari, 0.78),
    "ko.wav":            (s_ko, 0.72),
    "check.wav":         (s_check, 0.82),
    "forbidden.wav":     (s_forbidden, 0.80),
    "win.wav":           (s_win, 0.95),
    "lose.wav":          (s_lose, 0.90),
    "draw.wav":          (s_draw, 0.85),
    "click.wav":         (s_click, 0.30),
    "select.wav":        (s_select, 0.38),
    "pass.wav":          (s_pass, 0.60),
    "undo.wav":          (s_undo, 0.55),
    "newgame.wav":       (s_newgame, 0.88),
    "error.wav":         (s_error, 0.62),
    "drawer.wav":        (s_drawer, 0.50),
    "panel_open.wav":    (s_panel_open, 0.42),
    "panel_close.wav":   (s_panel_close, 0.42),
}


def main():
    random.seed(7)
    for name, (fn, gain) in SOUNDS.items():
        write(name, fn(), gain)


if __name__ == "__main__":
    main()
