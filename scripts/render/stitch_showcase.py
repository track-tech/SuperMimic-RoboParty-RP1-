"""Stitch the rendered segments in /tmp/showcase_*.mp4 into one labelled reel.

    python stitch_showcase.py --out rp1_showcase.mp4 --sheet rp1_showcase.png
"""
import argparse
import glob
import os
import re

import numpy as np


def read_frames(path):
    import imageio

    reader = imageio.get_reader(path, "ffmpeg")
    try:
        return [np.asarray(f) for f in reader]
    finally:
        reader.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="/tmp/showcase_*.mp4")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--fps", type=int, default=25)
    args = ap.parse_args()

    import imageio
    from PIL import Image, ImageDraw, ImageFont

    paths = sorted(glob.glob(args.glob))
    if not paths:
        raise SystemExit("no segments found")
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 30)
    except OSError:
        font = ImageFont.load_default()

    def tag(frame, title, sub):
        pil = Image.fromarray(frame)
        draw = ImageDraw.Draw(pil)
        draw.rectangle([0, 0, 1000, 46], fill=(0, 0, 0))
        draw.text((10, 6), title, fill=(240, 240, 240), font=font)
        draw.rectangle([0, frame.shape[0] - 36, 520, frame.shape[0]], fill=(0, 0, 0))
        draw.text((10, frame.shape[0] - 33), sub, fill=(160, 190, 250), font=font)
        return np.asarray(pil)

    sheet = []
    with imageio.get_writer(
        args.out, fps=args.fps, codec="libx264", quality=8,
        macro_block_size=None, ffmpeg_params=["-pix_fmt", "yuv420p"],
    ) as writer:
        for i, path in enumerate(paths, 1):
            clip = re.sub(r"^showcase_\d+_", "", os.path.splitext(os.path.basename(path))[0])
            frames = read_frames(path)
            print(f"[{i}/{len(paths)}] {clip}: {len(frames)} frames", flush=True)
            for k, frame in enumerate(frames):
                writer.append_data(tag(frame, clip, f"{i}/{len(paths)}  t={k / args.fps:4.1f}s"))
            sheet.append((clip, frames[int(len(frames) * 0.62)]))
    print("wrote", args.out)

    if args.sheet:
        cols = 4
        rows = (len(sheet) + cols - 1) // cols
        h, w = sheet[0][1].shape[:2]
        scale = 0.42
        tw, th = int(w * scale), int(h * scale)
        img = Image.new("RGB", (cols * tw, rows * (th + 28)), (16, 16, 16))
        draw = ImageDraw.Draw(img)
        for idx, (clip, frame) in enumerate(sheet):
            tile = Image.fromarray(frame).resize((tw, th))
            x, y = (idx % cols) * tw, (idx // cols) * (th + 28)
            img.paste(tile, (x, y + 28))
            draw.text((x + 6, y + 2), clip, fill=(235, 235, 235), font=font)
        img.save(args.sheet)
        print("wrote", args.sheet, img.size)


if __name__ == "__main__":
    main()
