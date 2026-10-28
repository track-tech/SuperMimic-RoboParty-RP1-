"""Pick a crouch stand pose + PD gains for the real RP1 (28 DoF)."""
import os as _os
_ROOT = _os.environ.get("UNI_SUPERMIMIC_ROOT")
if not _ROOT:
    raise SystemExit("请先 export UNI_SUPERMIMIC_ROOT=<Uni-SuperMimic 根目录>")
import numpy as np
import mujoco

D = (_ROOT + "/src/unisupermimic/assets/"
     "robots/rp1_real")
SCENE = f"{D}/scene_supermimic.xml"

model = mujoco.MjModel.from_xml_path(SCENE)
adr = {mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j): model.jnt_qposadr[j]
       for j in range(model.njnt)}


def pose_q(knee, hip, ankle):
    q = {n: 0.0 for n in adr}
    q["left_knee_joint"] = -knee
    q["right_knee_joint"] = knee
    q["left_hip_pitch_joint"] = hip
    q["right_hip_pitch_joint"] = -hip
    q["left_ankle_pitch_joint"] = ankle
    q["right_ankle_pitch_joint"] = -ankle
    return q


def foot_state(q, z=0.78):
    data = mujoco.MjData(model)
    data.qpos[:] = 0.0
    data.qpos[2] = z
    data.qpos[3] = 1.0
    for n, v in q.items():
        data.qpos[adr[n]] = v
    mujoco.mj_kinematics(model, data)
    lf = data.body("left_ankle_roll_link")
    return lf.xpos.copy(), lf.xmat.reshape(3, 3)[:, 2].copy()


print("knee  hip    ankle  foot_dx   foot_z_axis")
for knee in (0.2, 0.3, 0.4, 0.5):
    # flatness: hip + (-knee) + ankle = 0  ->  ankle = knee - hip
    for hip in (-0.5 * knee, -0.4 * knee, -0.6 * knee):
        ankle = knee - hip
        if abs(ankle) > 0.6:
            continue
        p, up = foot_state(pose_q(knee, hip, ankle))
        print(f"{knee:4.2f} {hip:+5.2f} {ankle:+6.2f}  {p[0]:+7.3f}   {up.round(3)}")
