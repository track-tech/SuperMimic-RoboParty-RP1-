"""How often do the reference motions violate the soft joint limits?

soft_lo/hi = mid -/+ half_range * soft_limit_factor (0.9), i.e. the reward's
joint_limit penalty term fires whenever a reference joint sits in the outer 10%
of its range.  If the retargeted motion lives at the limits, the policy is
punished for tracking it.

    python check_soft_limits.py <robot>   # robot: rp1 | g1
"""
import os as _os
_ROOT = _os.environ.get("UNI_SUPERMIMIC_ROOT")
if not _ROOT:
    raise SystemExit("请先 export UNI_SUPERMIMIC_ROOT=<Uni-SuperMimic 根目录>")
import os
import sys

import mujoco
import numpy as np

ROOT = _ROOT + "/src/unisupermimic/assets"
CASES = {
    "rp1": (f"{ROOT}/robots/rp1/rpo_supermimic.xml",
            f"{ROOT}/motions/rp1/lafan1_supermimic",
            ["left_thigh_yaw_joint", "left_thigh_roll_joint", "left_thigh_pitch_joint",
             "left_knee_joint", "left_ankle_pitch_joint", "left_ankle_roll_joint",
             "right_thigh_yaw_joint", "right_thigh_roll_joint", "right_thigh_pitch_joint",
             "right_knee_joint", "right_ankle_pitch_joint", "right_ankle_roll_joint",
             "torso_joint", "left_arm_pitch_joint", "left_arm_roll_joint",
             "left_arm_yaw_joint", "left_elbow_pitch_joint", "left_elbow_yaw_joint",
             "right_arm_pitch_joint", "right_arm_roll_joint", "right_arm_yaw_joint",
             "right_elbow_pitch_joint", "right_elbow_yaw_joint"]),
    "g1": (f"{ROOT}/robots/g1/supermimic.xml",
           f"{ROOT}/motions/g1/lafan1_supermimic",
           None),
}

SOFT = 0.9


def main():
    robot = sys.argv[1] if len(sys.argv) > 1 else "rp1"
    xml, motion_dir, joint_names = CASES[robot]
    model = mujoco.MjModel.from_xml_path(xml)
    if joint_names is None:
        joint_names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
                       for i in range(model.nu)]

    lo = np.zeros(len(joint_names))
    hi = np.zeros(len(joint_names))
    for i, name in enumerate(joint_names):
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        lo[i], hi[i] = model.jnt_range[jid]
    mid = (lo + hi) / 2
    half = (hi - lo) / 2
    soft_lo = mid - half * SOFT
    soft_hi = mid + half * SOFT

    files = sorted(f for f in os.listdir(motion_dir) if f.endswith(".csv"))
    per_joint = np.zeros(len(joint_names))
    total_frames = 0
    any_violation = 0
    frac_violations = []
    for f in files:
        data = np.loadtxt(os.path.join(motion_dir, f), delimiter=",")
        q = data[:, 7:]
        if q.shape[1] != len(joint_names):
            print(f"skip {f}: {q.shape[1]} joints")
            continue
        bad = (q < soft_lo) | (q > soft_hi)
        per_joint += bad.sum(0)
        any_violation += int(bad.any(1).sum())
        total_frames += q.shape[0]
        frac_violations.append(bad.any(1).mean())

    print(f"robot={robot}  clips={len(files)}  frames={total_frames}")
    print(f"frames with >=1 joint outside the soft range: "
          f"{any_violation}/{total_frames} = {any_violation/total_frames:.1%}")
    print(f"per-clip average: {np.mean(frac_violations):.1%}  max: {np.max(frac_violations):.1%}")
    print("\nper joint share of frames outside soft range:")
    order = np.argsort(-per_joint)
    for i in order:
        if per_joint[i] == 0:
            continue
        span = hi[i] - lo[i]
        print(f"  {joint_names[i]:26} range [{lo[i]:+.2f},{hi[i]:+.2f}] "
              f"soft [{soft_lo[i]:+.2f},{soft_hi[i]:+.2f}]  {per_joint[i]/total_frames:6.1%}")


if __name__ == "__main__":
    main()
