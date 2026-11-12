#!/usr/bin/env python3
"""把一批图片拼成一张带文件名的总览图（批量生图后快速通看、发给用户确认用）。

用法：
    python3 contact_sheet.py OUT.png IMG1.png IMG2.png ... [--cols 2] [--width 1100]
    python3 contact_sheet.py OUT.png 输出目录/*.png

需要 Pillow（pip install pillow）。每格按 --width 等比缩小，左上角写文件名。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="拼一张带文件名的图片总览")
    parser.add_argument("out", help="输出的总览图路径（.png / .jpg）")
    parser.add_argument("images", nargs="+", help="要放进总览的图片")
    parser.add_argument("--cols", type=int, default=2, help="每行几张，默认 2")
    parser.add_argument("--width", type=int, default=1100, help="每格宽度（像素），默认 1100")
    args = parser.parse_args()

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("需要 Pillow：python3 -m pip install pillow", file=sys.stderr)
        return 2

    tiles = []
    for path in args.images:
        try:
            image = Image.open(path).convert("RGB")
        except OSError as exc:
            print(f"跳过 {path}：{exc}", file=sys.stderr)
            continue
        image.thumbnail((args.width, args.width * 4))
        tiles.append((Path(path).name, image))
    if not tiles:
        print("没有可用的图片", file=sys.stderr)
        return 1

    cols = max(1, args.cols)
    rows = (len(tiles) + cols - 1) // cols
    label_height = 28
    cell_height = max(image.height for _name, image in tiles) + label_height
    sheet = Image.new("RGB", (cols * args.width, rows * cell_height), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (name, image) in enumerate(tiles):
        x, y = (index % cols) * args.width, (index // cols) * cell_height
        draw.text((x + 8, y + 6), name, fill="red")
        sheet.paste(image, (x, y + label_height))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(f"OK {args.out}（{len(tiles)} 张，{cols} 列）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
