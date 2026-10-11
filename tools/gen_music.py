"""合成国风背景音乐（纯标准库）。

用 Karplus–Strong 拨弦合成三段风格不同的循环，输出到 assets/audio/：
  bgm_guqin.wav    五子棋：清雅古琴（原有曲调，保持不变）
  bgm_martial.wav  象棋：低音区、羽调式、略快、带低沉鼓点
  bgm_void.wav     围棋：高音区、稀疏、长余韵

想换曲调改各段的 NOTES / DRONE 即可。
"""

import math
import random
import struct
import wave
from pathlib import Path

SR = 44100
OUT = Path(__file__).resolve().parent.parent / "assets" / "audio"

N = {
    "A2": 110.00, "C3": 130.81, "D3": 146.83, "E3": 164.81, "G3": 196.00, "A3": 220.00,
    "C4": 261.63, "D4": 293.66, "E4": 329.63, "G4": 392.00, "A4": 440.00,
    "C5": 523.25, "D5": 587.33, "E5": 659.25, "G5": 783.99, "A5": 880.00,
}


def karplus(freq, dur, damp=0.9965, seed=None):
    rng = random.Random(seed) if seed is not None else random
    n = int(SR * dur)
    line = max(2, int(round(SR / freq)))
    buf = [rng.uniform(-1.0, 1.0) * 0.6 for _ in range(line)]
    out = [0.0] * n
    idx = 0
    prev = 0.0
    for i in range(n):
        cur = buf[idx]
        out[i] = cur
        buf[idx] = 0.5 * (cur + prev) * damp
        prev = cur
        idx += 1
        if idx >= line:
            idx = 0
    return out


def _mix(master, voice, start, amp, attack=0.012):
    off = int(start * SR)
    a = max(1, int(attack * SR))
    for i, v in enumerate(voice):
        j = off + i
        if j >= len(master):
            break
        env = i / a if i < a else 1.0
        master[j] += v * amp * env


def _thump(master, start, freq, dur, amp, decay):
    off = int(start * SR)
    n = int(SR * dur)
    for i in range(n):
        j = off + i
        if j >= len(master):
            break
        t = i / SR
        master[j] += math.sin(2 * math.pi * freq * t) * math.exp(-t / decay) * amp


def render(name, notes, dur, gain, drones=(), thumps=(), seed=961006, tail=2.5, damp=0.9965):
    random.seed(seed)
    total = int(SR * dur)
    master = [0.0] * total
    for start, key, amp in drones:
        _mix(master, karplus(N[key], min(dur - start + tail, 4.0), damp), start, amp)
    for start, key, amp in notes:
        _mix(master, karplus(N[key], min(dur - start + tail, 3.2), damp), start, amp)
    for start, freq, t_dur, amp, decay in thumps:
        _thump(master, start, freq, t_dur, amp, decay)
    peak = max(1e-6, max(abs(v) for v in master))
    scale = gain / peak
    # 首尾交叉淡化，便于无缝循环
    fade = int(0.35 * SR)
    for i in range(min(fade, total // 2)):
        f = i / fade
        master[i] *= f
        master[total - 1 - i] *= f
    samples = [int(max(-1.0, min(1.0, v * scale)) * 32767) for v in master]
    OUT.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT / name), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", s) for s in samples))
    print("wrote", name, len(samples), "samples")


# ---------------------------------------------------------------- 五子棋：清雅古琴
GUQIN = [
    (0.0, "C4", 0.55), (1.4, "G4", 0.42), (2.6, "A4", 0.40), (3.8, "E4", 0.44),
    (5.2, "D4", 0.50), (6.4, "C4", 0.40), (7.6, "A3", 0.46), (9.0, "C4", 0.52),
    (10.4, "E4", 0.42), (11.6, "G4", 0.40), (12.8, "C5", 0.46), (14.2, "A4", 0.50),
    (15.4, "G4", 0.38), (16.6, "D4", 0.48), (18.0, "C4", 0.52), (19.2, "G3", 0.44),
]
GUQIN_DRONE = [(0.0, "C3", 0.22), (0.0, "G3", 0.16)]

# ---------------------------------------------------------------- 象棋：羽调式、略快、带鼓点
MARTIAL = [
    (0.0, "A3", 0.50), (0.72, "E4", 0.42), (1.44, "A3", 0.40), (2.16, "C4", 0.46),
    (2.88, "D4", 0.44), (3.60, "E4", 0.50), (4.32, "G4", 0.40), (5.04, "E4", 0.44),
    (5.76, "D4", 0.42), (6.48, "C4", 0.50), (7.20, "A3", 0.44), (7.92, "G3", 0.40),
    (8.64, "A3", 0.50), (9.36, "C4", 0.44), (10.08, "E4", 0.46), (10.80, "G4", 0.42),
    (11.52, "A4", 0.50), (12.24, "G4", 0.40), (12.96, "E4", 0.44), (13.68, "D4", 0.42),
    (14.40, "C4", 0.46), (15.12, "A3", 0.44), (15.84, "G3", 0.40), (16.56, "A3", 0.50),
    (17.28, "C4", 0.44),
]
MARTIAL_DRONE = [(0.0, "A2", 0.24), (0.0, "E3", 0.14)]
MARTIAL_THUMPS = [(t, 82.0, 0.55, 0.5, 0.22) for t in (0.0, 3.6, 7.2, 10.8, 14.4, 18.0)]

# ---------------------------------------------------------------- 围棋：高音区、稀疏、长余韵
VOID = [
    (0.0, "A4", 0.40), (3.2, "E5", 0.36), (6.0, "C5", 0.40), (9.0, "G4", 0.34),
    (11.6, "A4", 0.38), (14.4, "D5", 0.36), (17.2, "C5", 0.40), (20.0, "E5", 0.34),
    (22.8, "G5", 0.36), (25.6, "A4", 0.40), (28.4, "C5", 0.34),
]
VOID_DRONE = [(0.0, "A3", 0.14), (0.0, "E4", 0.10)]


def main():
    render("bgm_guqin.wav", GUQIN, 22.0, 0.62, drones=GUQIN_DRONE, seed=961006)
    render("bgm_martial.wav", MARTIAL, 19.2, 0.60, drones=MARTIAL_DRONE,
           thumps=MARTIAL_THUMPS, seed=77213, tail=2.0, damp=0.9960)
    render("bgm_void.wav", VOID, 30.0, 0.52, drones=VOID_DRONE, seed=20311,
           tail=4.5, damp=0.9975)


if __name__ == "__main__":
    main()
