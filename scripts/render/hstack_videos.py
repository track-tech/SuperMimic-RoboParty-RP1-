"""Put two rendered clips side by side into one comparison video.

    python hstack_videos.py <left.mp4> <right.mp4> <out.mp4> [label_left] [label_right]
"""
import sys

import imageio.v3 as iio
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def label(img, text):
    pil = Image.fromarray(img)
    draw = ImageDraw.Draw(pil)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 26)
    except OSError:
        font = ImageFont.load_default()
    draw.rectangle([0, 0, 360, 34], fill=(0, 0, 0))
    draw.text((8, 4), text, fill=(240, 240, 240), font=font)
    return np.asarray(pil)


def main():
    left_p, right_p, out_p = sys.argv[1:4]
    lname = sys.argv[4] if len(sys.argv) > 4 else "left"
    rname = sys.argv[5] if len(sys.argv) > 5 else "right"

    frames_l = iio.imread(left_p, plugin="pyav")
    frames_r = iio.imread(right_p, plugin="pyav")
    n = min(len(frames_l), len(frames_r))
    h = min(frames_l.shape[1], frames_r.shape[1])
    w = min(frames_l.shape[2], frames_r.shape[2])
    print(f"left {frames_l.shape} right {frames_r.shape} -> {n} frames of {w}x{h}")

    import imageio

    with imageio.get_writer(
        out_p,
        fps=25,
        codec="libx264",
        quality=8,
        macro_block_size=None,
        ffmpeg_params=["-pix_fmt", "yuv420p"],
    ) as writer:
        for i in range(n):
            a = label(frames_l[i, :h, :w], lname)
            b = label(frames_r[i, :h, :w], rname)
            writer.append_data(np.concatenate([a, b], axis=1))
            if i % 100 == 0:
                print(f"  frame {i}/{n}", flush=True)
    print("wrote", out_p)


if __name__ == "__main__":
    main()
