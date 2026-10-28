"""Compare leg-pose statistics of the G1 and RP1 reference motions."""
import os as _os
_ROOT = _os.environ.get("UNI_SUPERMIMIC_ROOT")
if not _ROOT:
    raise SystemExit("请先 export UNI_SUPERMIMIC_ROOT=<Uni-SuperMimic 根目录>")
import os

import numpy as np

G1 = _ROOT + "/src/unisupermimic/assets/motions/g1/lafan1_supermimic"
R1 = "/root/gpufree-data/mars/ext/rp1_motions"

G1_NAMES = [
    "left_hip_pitch", "left_hip_roll", "left_hip_yaw", "left_knee",
    "left_ankle_pitch", "left_ankle_roll",
    "right_hip_pitch", "right_hip_roll", "right_hip_yaw", "right_knee",
    "right_ankle_pitch", "right_ankle_roll",
]
RP1_NAMES = [
    "left_thigh_pitch", "left_thigh_roll", "left_thigh_yaw", "left_knee",
    "left_ankle_pitch", "left_ankle_roll",
    "right_thigh_pitch", "right_thigh_roll", "right_thigh_yaw", "right_knee",
    "right_ankle_pitch", "right_ankle_roll",
]


def load(d):
    files = sorted(f for f in os.listdir(d) if f.endswith(".csv"))
    return np.concatenate([np.loadtxt(os.path.join(d, f), delimiter=",") for f in files])


g1 = load(G1)
rp1 = load(R1)
print(f"G1 {g1.shape}   RP1 {rp1.shape}")
print(f"\n{'joint':18} {'G1 mean':>8} {'G1 p50':>7} {'G1 p95':>7} | "
      f"{'RP1 mean':>9} {'RP1 p50':>8} {'RP1 p95':>8}   (rad)")
for i, (a, b) in enumerate(zip(G1_NAMES, RP1_NAMES)):
    qa, qb = g1[:, 7 + i], rp1[:, 7 + i]
    print(f"{a:18} {qa.mean():+8.3f} {np.median(qa):+7.3f} {np.percentile(qa,95):+7.3f} | "
          f"{qb.mean():+9.3f} {np.median(qb):+8.3f} {np.percentile(qb,95):+8.3f}   {b}")

print("\nbase height:")
print(f"  G1  mean {g1[:,2].mean():.3f}  p05 {np.percentile(g1[:,2],5):.3f}  "
      f"p95 {np.percentile(g1[:,2],95):.3f}")
print(f"  RP1 mean {rp1[:,2].mean():.3f}  p05 {np.percentile(rp1[:,2],5):.3f}  "
      f"p95 {np.percentile(rp1[:,2],95):.3f}")
