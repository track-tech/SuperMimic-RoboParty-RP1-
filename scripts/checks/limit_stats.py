"""How often does a retargeted motion sit ON a joint limit, and how fast are the joints?

GMR's mink.ConfigurationLimit makes out-of-range *values* impossible, so the only
failure mode in the CSV is saturation: the joint parks exactly at its boundary.
That still matters, because SuperMimic's reward penalises the outer 10% of each
range (soft_limit_factor=0.9) and the reset pose then starts on the limit.

    python limit_stats.py <motions_dir> <robot_mjcf> [src_fps=30]
"""
import glob
import os
import sys

import mujoco
import numpy as np

src = sys.argv[1] if len(sys.argv) > 1 else "."
xml = sys.argv[2] if len(sys.argv) > 2 else None
src_fps = float(sys.argv[3]) if len(sys.argv) > 3 else 30.0
if xml is None:
    raise SystemExit("用法: limit_stats.py <motions_dir> <robot_mjcf> [src_fps]")

model = mujoco.MjModel.from_xml_path(xml)
names = [model.actuator(i).name for i in range(model.nu)]
lo = np.array([model.jnt_range[model.joint(n).id][0] for n in names])
hi = np.array([model.jnt_range[model.joint(n).id][1] for n in names])

rows = [np.loadtxt(f, delimiter=",")[:, 7:7 + len(names)]
        for f in sorted(glob.glob(os.path.join(src, "*.csv")))]
q = np.concatenate(rows)
print(f"{len(rows)} clips, {q.shape[0]} frames, {q.shape[1]} joints, source {src_fps:g} fps")

tol = 1e-3
at_lim = (np.abs(q - lo) < tol) | (np.abs(q - hi) < tol)
sat = at_lim.mean(0)
print(f"\n{'joint':28} {'at limit':>9}   {'range':>18}")
for i in np.argsort(-sat):
    if sat[i] < 0.001:
        continue
    print(f"{names[i]:28} {sat[i]:8.1%}   [{lo[i]:+.2f},{hi[i]:+.2f}]")
print(f"\n有任意关节顶在硬限位上的帧：{at_lim.any(1).mean():.1%}")

# joint speed on the 50 Hz control grid SuperMimic actually uses
ctrl_fps = 50.0
idx = np.round(np.linspace(0, q.shape[0] - 1, int(q.shape[0] * ctrl_fps / src_fps))).astype(int)
qd = np.diff(q[idx], axis=0) * ctrl_fps
peak = np.abs(qd).max(0)
print(f"\n{'joint':28} {'peak |dq| rad/s':>16}")
for i in np.argsort(-peak)[:8]:
    print(f"{names[i]:28} {peak[i]:16.2f}")
print(f"\n全局峰值关节速度：{peak.max():.2f} rad/s（{ctrl_fps:g} Hz 差分）")
