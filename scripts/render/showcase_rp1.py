"""Render one showcase reel: several motion clips from a single RP1 checkpoint.

Builds the eval env once, rolls out each clip, renders it with the reference
ghost, then stitches all segments into one labelled video plus a contact sheet.

    python showcase_rp1.py --ckpt <ckpt.pt> --clips walk1_subject1,run1_subject2 \
        --seconds 12 --out /root/.../rp1_showcase.mp4 --sheet /root/.../rp1_showcase.png
"""
import os as _os
_ROOT = _os.environ.get("UNI_SUPERMIMIC_ROOT")
if not _ROOT:
    raise SystemExit("请先 export UNI_SUPERMIMIC_ROOT=<Uni-SuperMimic 根目录>")
import argparse
import os
import pathlib
import sys

import numpy as np

ROOT = _ROOT + ""
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--clips", required=True)
    ap.add_argument("--seconds", type=str, default="12",
                    help="one value for all clips, or a comma list per clip")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--backend", default="mjwarp")
    ap.add_argument("--scene", default=None, help="MJCF scene; defaults to the RP1 one")
    args = ap.parse_args()

    import imageio
    import torch
    from PIL import Image, ImageDraw, ImageFont

    from unisupermimic.tasks.motion_tracking.g1.supermimic.evaluate import make_eval_env
    from unisupermimic.tasks.motion_tracking.g1.supermimic.render import (
        render_comparison,
        rollout_qpos,
    )

    clips = [c.strip() for c in args.clips.split(",") if c.strip()]
    ckpt_path = pathlib.Path(args.ckpt).resolve()
    scene = pathlib.Path(args.scene) if args.scene else (
        pathlib.Path(ROOT) / "src/unisupermimic/assets/robots/rp1/scene_supermimic.xml")

    env = make_eval_env(ckpt_path.parent, backend=args.backend)
    # per-clip seconds: "20" applies to all, "30,30,200" maps to clips in order
    secs = [float(s) for s in str(args.seconds).split(",") if s.strip()]
    if len(secs) == 1:
        secs = secs * len(clips)
    if len(secs) != len(clips):
        raise SystemExit("--seconds must be one value or one per clip")
    segments = []
    try:
        device = torch.device(env.device)
        checkpoint = torch.load(ckpt_path, map_location=device, weights_only=True)
        for i, (clip, seconds) in enumerate(zip(clips, secs), 1):
            seg = pathlib.Path(f"/tmp/showcase_{i:02d}_{clip}.mp4")
            print(f"[{i}/{len(clips)}] {clip} ({seconds:g}s) ...", flush=True)
            reference, policy = rollout_qpos(env, checkpoint, clip, seconds)
            written = render_comparison(
                reference,
                policy,
                seg,
                scene,
                clip_name=clip,
                width=args.width,
                height=args.height,
                fps=25,
            )
            print(f"    {written} frames", flush=True)
            segments.append((clip, str(seg)))
    finally:
        env.close()
        env.backend.close()

    # ---- stitch ----
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 30)
    except OSError:
        font = ImageFont.load_default()

    def tag(frame, text, sub):
        pil = Image.fromarray(frame)
        draw = ImageDraw.Draw(pil)
        draw.rectangle([0, 0, 1000, 44], fill=(0, 0, 0))
        draw.text((10, 6), text, fill=(240, 240, 240), font=font)
        draw.rectangle([0, frame.shape[0] - 34, 460, frame.shape[0]], fill=(0, 0, 0))
        draw.text((10, frame.shape[0] - 32), sub, fill=(160, 190, 250), font=font)
        return np.asarray(pil)

    sheet_frames = []
    with imageio.get_writer(
        args.out, fps=25, codec="libx264", quality=8, macro_block_size=None,
        ffmpeg_params=["-pix_fmt", "yuv420p"],
    ) as writer:
        for i, (clip, seg) in enumerate(segments, 1):
            frames = imageio.v3.imread(seg, plugin="pyav")
            for k, frame in enumerate(frames):
                writer.append_data(
                    tag(frame, f"{clip}", f"{i}/{len(segments)}  t={k / 25:4.1f}s")
                )
            pick = int(len(frames) * 0.6)
            sheet_frames.append((clip, frames[pick]))
            print(f"stitched {clip} ({len(frames)} frames)", flush=True)
    print("wrote", args.out)

    if args.sheet:
        cols, rows = 4, (len(sheet_frames) + 3) // 4
        h, w = sheet_frames[0][1].shape[:2]
        scale = 0.42
        tw, th = int(w * scale), int(h * scale)
        sheet = Image.new("RGB", (cols * tw, rows * (th + 26)), (16, 16, 16))
        draw = ImageDraw.Draw(sheet)
        for idx, (clip, frame) in enumerate(sheet_frames):
            img = Image.fromarray(frame).resize((tw, th))
            x, y = (idx % cols) * tw, (idx // cols) * (th + 26)
            sheet.paste(img, (x, y + 26))
            draw.text((x + 6, y + 2), clip, fill=(230, 230, 230), font=font)
        sheet.save(args.sheet)
        print("wrote", args.sheet, sheet.size)


if __name__ == "__main__":
    main()
