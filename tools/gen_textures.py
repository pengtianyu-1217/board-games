"""合成棋盘与界面贴图（纯标准库，zlib 手写 PNG，不依赖外部素材服务）。

输出到 assets/art/：
    paper.png       宣纸底纹（暖白 + 纤维噪点）
    wood_light.png  浅黄木板（纵向木纹，棋盘底）

想换色调改这里的参数即可。
"""

import math
import random
import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets" / "art"


def write_png(name, width, height, rows):
    """rows: 每行的 bytes（RGB，长度 = width*3）。"""
    raw = b"".join(b"\x00" + r for r in rows)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

    head = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    blob = (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", head)
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_bytes(blob)
    print("wrote", name, width, "x", height)


def clamp(v):
    return 0 if v < 0 else (255 if v > 255 else int(v))


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


# ---------------------------------------------------------------- 宣纸
def make_paper(width=768, height=768):
    base = (243, 236, 220)
    deep = (232, 223, 201)
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            # 低频斑纹 + 细纤维噪点
            blotch = 0.5 + 0.5 * math.sin(x * 0.013 + 1.7) * math.sin(y * 0.011 + 0.4)
            fiber = random.random()
            t = 0.35 * blotch + 0.12 * (fiber - 0.5)
            r, g, b = mix(base, deep, max(0.0, min(1.0, t)))
            n = random.uniform(-3.5, 3.5)
            row += bytes((clamp(r + n), clamp(g + n), clamp(b + n)))
        rows.append(bytes(row))
    # 稀疏深色纤维
    for _ in range(width * height // 1600):
        fx = random.randrange(width - 24)
        fy = random.randrange(height)
        length = random.randrange(6, 22)
        dark = (206, 196, 172)
        for k in range(length):
            xx = fx + k
            if xx >= width:
                break
            idx = xx * 3
            r, g, b = rows[fy][idx], rows[fy][idx + 1], rows[fy][idx + 2]
            nr, ng, nb = mix((r, g, b), dark, 0.32)
            rows[fy] = (rows[fy][:idx] + bytes((clamp(nr), clamp(ng), clamp(nb)))
                        + rows[fy][idx + 3:])
    return rows


# ---------------------------------------------------------------- 木纹
def make_wood(width=640, height=1024):
    light = (236, 206, 148)
    dark = (214, 178, 112)
    rows = []
    for y in range(height):
        wobble = 1.6 * math.sin(y * 0.012) + 0.9 * math.sin(y * 0.037 + 1.1)
        row = bytearray()
        for x in range(width):
            grain = 0.5 + 0.5 * math.sin(x * 0.18 + wobble)
            grain = grain ** 1.6
            ring = 0.5 + 0.5 * math.sin(x * 0.021 + wobble * 0.5)
            t = 0.55 * grain + 0.30 * ring
            t = max(0.0, min(1.0, t))
            r, g, b = mix(light, dark, t)
            n = random.uniform(-4.0, 4.0)
            row += bytes((clamp(r + n), clamp(g + n), clamp(b + n)))
        rows.append(bytes(row))
    return rows


def main():
    random.seed(20261006)
    write_png("paper.png", 768, 768, make_paper())
    write_png("wood_light.png", 640, 1024, make_wood())


if __name__ == "__main__":
    main()
