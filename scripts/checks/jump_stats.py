"""Where do impossible joint speeds in a retargeted clip come from?

Flags adjacent-frame jumps (IK flips) and ranks the offending joints/clips.

    python jump_stats.py <motions_dir> <robot_mjcf> [fps=30] [threshold_rad_s=20]
"""
import glob
import os
import sys

import mujoco
import numpy as np

src = sys.argv[1] if len(sys.argv) > 1 else "."
xml = sys.argv[2] if len(sys.argv) > 2 else None
fps = float(sys.argv[3]) if len(sys.argv) > 3 else 30.0
thresh = float(sys.argv[4]) if len(sys.argv) > 4 else 20.0
if xml is None:
    raise SystemExit("用法: jump_stats.py <motions_dir> <robot_mjcf> [fps] [threshold]")

model = mujoco.MjModel.from_xml_path(xml)
names = [model.actuator(i).name for i in range(model.nu)]

worst, allq = [], []
for f in sorted(glob.glob(os.path.join(src, "*.csv"))):
    q = np.loadtxt(f, delimiter=",")[:, 7:7 + len(names)]
    allq.append(q)
    d = np.abs(np.diff(q, axis=0)) * fps
    i, j = np.unravel_index(np.argmax(d), d.shape)
    worst.append((float(d[i, j]), os.path.basename(f)[:-4], names[j], int(i),
                  float(q[i, j]), float(q[i + 1, j])))

q = np.concatenate(allq)
qd = np.abs(np.diff(q, axis=0)) * fps
print(f"{len(allq)} clips, {q.shape[0]} frames @ {fps:g} fps\n")
for label, val in (("max", qd.max()), ("p99.9", np.percentile(qd, 99.9)),
                   ("p99", np.percentile(qd, 99)), ("p95", np.percentile(qd, 95))):
    print(f"  |dq| {label:>6} = {val:8.2f} rad/s")

print(f"\n速度最大的 6 段（clip, joint, frame, q[i] -> q[i+1]）：")
for dmax, clip, jn, i, a, b in sorted(worst, reverse=True)[:6]:
    print(f"  {dmax:8.1f} rad/s  {clip:24} {jn:26} f{i:5d}  {a:+.2f} -> {b:+.2f}")

n_bad = int((qd > thresh).sum())
print(f"\n超过 {thresh:g} rad/s 的相邻帧对：{n_bad} / {qd.size} = {n_bad/qd.size:.2%}")
per_joint = (qd > thresh).sum(0)
for i in np.argsort(-per_joint)[:8]:
    if per_joint[i] == 0:
        break
    print(f"  {names[i]:28} {per_joint[i]:5d}")
