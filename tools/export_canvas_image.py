"""从浏览器 IndexedDB 的 blob 目录按「字节大小」取出画布图片。

无限画布把生成的图片原始 PNG 存在 Edge 的 IndexedDB blob 目录里，文件名是随机
短名，但内容就是纯 PNG。画布元数据里带着每张图的 `bytes`，用它去精确匹配即可。

用法：
    python tools/export_canvas_image.py --list
    python tools/export_canvas_image.py <字节数> <输出路径>

可用环境变量 CANVAS_BLOB_DIR 覆盖目录（默认本机 Edge Default profile）。
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
DEFAULT_BLOB_DIR = Path(
    r"C:\Users\PTY pty\AppData\Local\Microsoft\Edge\User Data\Default"
    r"\IndexedDB\http_localhost_3000.indexeddb.blob"
)


def blob_dir() -> Path:
    return Path(os.environ.get("CANVAS_BLOB_DIR", DEFAULT_BLOB_DIR))


def iter_png_blobs():
    root = blob_dir()
    if not root.exists():
        return
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        try:
            with open(p, "rb") as f:
                if f.read(8) == PNG_MAGIC:
                    yield p, p.stat().st_size
        except OSError:
            continue


def find_by_size(size: int):
    return [p for p, s in iter_png_blobs() if s == size]


def cmd_list():
    sizes = sorted({s for _, s in iter_png_blobs()}, reverse=True)
    print(f"{len(sizes)} distinct PNG sizes in {blob_dir()}")
    for s in sizes:
        print(s)


def cmd_export(size: int, dest: str):
    matches = find_by_size(size)
    if not matches:
        print(f"未找到字节数为 {size} 的 PNG。Edge 可能还没落盘，稍后重试；或用 --list 查看现有尺寸。")
        return 1
    out = Path(dest)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(matches[0], out)
    print(f"saved {out}  <- {matches[0].name}  (matches={len(matches)})")
    return 0


def main(argv):
    args = list(argv)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args[0] == "--list":
        cmd_list()
        return 0
    if len(args) < 2:
        print(__doc__)
        return 1
    return cmd_export(int(args[0]), args[1])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
