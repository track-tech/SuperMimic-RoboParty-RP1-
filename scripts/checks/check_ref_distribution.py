"""Distribution of RP1 reference joint angles: is the retargeted stance sane?"""
import os

import numpy as np

D = "/root/gpufree-data/mars/ext/rp1_motions"
NAMES = [
    "left_thigh_yaw", "left_thigh_roll", "left_thigh_pitch", "left_knee",
    "left_ankle_pitch", "left_ankle_roll",
    "right_thigh_yaw", "right_thigh_roll", "right_thigh_pitch", "right_knee",
    "right_ankle_pitch", "right_ankle_roll", "torso",
    "left_arm_pitch", "left_arm_roll", "left_arm_yaw", "left_elbow_pitch", "left_elbow_yaw",
    "right_arm_pitch", "right_arm_roll", "right_arm_yaw", "right_elbow_pitch", "right_elbow_yaw",
]

files = sorted(f for f in os.listdir(D) if f.endswith(".csv"))
allq = np.concatenate([np.loadtxt(os.path.join(D, f), delimiter=",")[:, 7:] for f in files])

print(f"{len(files)} clips, {allq.shape[0]} frames\n")
print(f"{'joint':20} {'mean':>7} {'std':>6} {'p05':>7} {'p50':>7} {'p95':>7}")
for i, name in enumerate(NAMES):
    q = allq[:, i]
    print(f"{name:20} {q.mean():+7.3f} {q.std():6.3f} {np.percentile(q,5):+7.3f} "
          f"{np.percentile(q,50):+7.3f} {np.percentile(q,95):+7.3f}")

print("\nthigh_roll in degrees (median):")
for side, i in (("left", 1), ("right", 7)):
    print(f"  {side}: {np.degrees(np.median(allq[:, i])):+.1f} deg "
          f"(p95 {np.degrees(np.percentile(allq[:, i], 95)):+.1f})")
