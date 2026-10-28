"""Probe RP1 joint sign conventions so a crouch stand pose can be built."""
import os as _os
_ROOT = _os.environ.get("UNI_SUPERMIMIC_ROOT")
if not _ROOT:
    raise SystemExit("请先 export UNI_SUPERMIMIC_ROOT=<Uni-SuperMimic 根目录>")
import numpy as np
import mujoco

XML = (_ROOT + "/src/unisupermimic/assets/"
       "robots/rp1_real/scene_supermimic.xml")

model = mujoco.MjModel.from_xml_path(XML)
data = mujoco.MjData(model)
adr = {mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j): model.jnt_qposadr[j]
       for j in range(model.njnt)}


def fk(q):
    data.qpos[:] = 0.0
    data.qpos[2] = 0.78
    data.qpos[3] = 1.0
    for name, val in q.items():
        data.qpos[adr[name]] = val
    mujoco.mj_kinematics(model, data)
    lf = data.body("left_ankle_roll_link").xpos.copy()
    rf = data.body("right_ankle_roll_link").xpos.copy()
    return lf, rf


base_l, base_r = fk({})
print(f"zero pose: left foot {base_l.round(3)}  right foot {base_r.round(3)}")
print("perturb +0.2 rad, report foot delta (dx forward, dz up):\n")
for joint in ("left_hip_pitch_joint", "left_knee_joint", "left_ankle_pitch_joint",
              "left_hip_roll_joint", "left_ankle_roll_joint",
              "right_hip_pitch_joint", "right_knee_joint", "right_ankle_pitch_joint"):
    l, r = fk({joint: 0.2})
    side = l if joint.startswith("left") else r
    base = base_l if joint.startswith("left") else base_r
    d = side - base
    print(f"  {joint:28} dx={d[0]:+.3f}  dy={d[1]:+.3f}  dz={d[2]:+.3f}")

print("\nfoot orientation at zero (up axis of ankle_roll_link):")
data.qpos[:] = 0.0
data.qpos[2] = 0.78
data.qpos[3] = 1.0
mujoco.mj_kinematics(model, data)
for b in ("left_ankle_roll_link", "right_ankle_roll_link"):
    R = data.body(b).xmat.reshape(3, 3)
    print(f"  {b}: z-axis {R[:, 2].round(3)}  (1 0 0 means foot tilted)")
