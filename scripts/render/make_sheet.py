"""Extract evenly spaced frames from the render mp4 into one contact-sheet PNG.

    python make_sheet.py <video.mp4> <out.png> [cols] [rows]
"""
import sys

import imageio.v3 as iio
import numpy as np
from PIL import Image

video, out = sys.argv[1], sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 3
rows = int(sys.argv[4]) if len(sys.argv) > 4 else 2
crop = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0

frames = iio.imread(video, plugin="pyav")
n = frames.shape[0]
idx = np.linspace(0, n - 1, cols * rows).astype(int)
print(f"{n} frames, picking {list(idx)}")

if crop < 1.0:
    h0, w0 = frames.shape[1], frames.shape[2]
    ch, cw = int(h0 * crop), int(w0 * crop)
    y0, x0 = (h0 - ch) // 2, (w0 - cw) // 2
    frames = frames[:, y0 : y0 + ch, x0 : x0 + cw]

thumbs = [Image.fromarray(frames[i]) for i in idx]
w, h = thumbs[0].size
scale = 0.5
tw, th = int(w * scale), int(h * scale)
thumbs = [t.resize((tw, th)) for t in thumbs]

sheet = Image.new("RGB", (cols * tw, rows * th), (20, 20, 20))
for k, t in enumerate(thumbs):
    sheet.paste(t, ((k % cols) * tw, (k // cols) * th))
sheet.save(out)
print(f"wrote {out} ({sheet.size[0]}x{sheet.size[1]})")
