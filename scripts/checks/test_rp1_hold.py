"""Static crouch hold for RP1: does the position servo support the robot?

Commands a fixed pose (median reference posture) and reports how much the legs
sag. Isolates servo stiffness from the (unsolvable) open-loop walking replay.
"""
import os as _os
_ROOT = _os.environ.get("UNI_SUPERMIMIC_ROOT")
if not _ROOT:
    raise SystemExit("请先 export UNI_SUPERMIMIC_ROOT=<Uni-SuperMimic 根目录>")
import numpy as np
import mujoco

D = (_ROOT + "/src/unisupermimic/assets/"
     "robots/rp1")
SCENE = f"{D}/scene_supermimic.xml"

base = mujoco.MjModel.from_xml_path(SCENE)
KP0 = base.actuator_gainprm[:, 0].copy()
names = [base.actuator(i).name for i in range(base.nu)]
adr = {mujoco.mj_id2name(base, mujoco.mjtObj.mjOBJ_JOINT, j): base.jnt_qposadr[j]
       for j in range(base.njnt)}

# median reference posture (left/right mirrored), from the retarget statistics
POSE = {
    "hip_pitch": 0.78, "hip_roll": -0.10, "hip_yaw": 0.17, "knee": 0.90,
    "ankle_pitch": -0.22, "ankle_roll": 0.04,
    "waist_roll": 0.0, "waist_yaw": 0.0,
    "shoulder_pitch": 0.05, "shoulder_roll": 0.40, "shoulder_yaw": 0.40,
    "elbow": 0.35, "wrist_roll": 0.30, "wrist_yaw": 0.28, "wrist_pitch": 0.0,
}


def target_q(mirror_signs=True):
    q = {}
    for n in names:
        key = n.replace("left_", "").replace("right_", "").replace("_joint", "")
        v = POSE[key]
        if n.startswith("left_"):
            v = -v if key in ("hip_pitch", "knee", "hip_yaw", "hip_roll") else v
        elif n.startswith("right_"):
            v = v if key in ("hip_pitch", "knee", "hip_yaw", "hip_roll") else -v
        q[n] = v
    return q


def run(kp_scale, seconds=3.0):
    model = mujoco.MjModel.from_xml_path(SCENE)
    kp = KP0 * kp_scale
    kv = kp * 0.0637
    model.actuator_gainprm[:, 0] = kp
    model.actuator_biasprm[:, 1] = -kp
    model.actuator_biasprm[:, 2] = -kv
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    q = target_q()
    ctrl = np.array([q[n] for n in names])
    for i, n in enumerate(names):
        data.qpos[adr[n]] = q[n]
    data.qpos[2] = 0.80
    data.qpos[3] = 1.0
    mujoco.mj_forward(model, data)
    fl = next(g for g in range(model.ngeom)
              if model.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE)
    best = np.inf
    for g in range(model.ngeom):
        if g == fl:
            continue
        best = min(best, mujoco.mj_geomDistance(model, data, g, fl, 5.0, None))
    data.qpos[2] -= best - 0.001
    mujoco.mj_forward(model, data)
    z0 = float(data.qpos[2])
    ups = []
    for k in range(int(seconds / model.opt.timestep)):
        data.ctrl[:] = ctrl
        mujoco.mj_step(model, data)
        if k % int(0.05 / model.opt.timestep) == 0:
            ups.append(float(data.body("waist_yaw_link").xmat.reshape(3, 3)[2, 2]))
    knees = [float(data.qpos[adr["left_knee_joint"]]), float(data.qpos[adr["right_knee_joint"]])]
    return z0, float(data.qpos[2]), min(ups), ups[-1], knees


print(f"{'kp_scale':>8} {'kp_big':>7} {'z0':>6} {'z_end':>6} {'up_min':>7} {'up_end':>7} "
      f"{'knee_actual':>18}")
for s in (1.0, 2.0, 4.0, 8.0):
    z0, z1, um, ue, kn = run(s)
    print(f"{s:8.1f} {KP0[0] * s:7.0f} {z0:6.3f} {z1:6.3f} {um:+7.3f} {ue:+7.3f} "
          f"{np.round(kn, 2)}")
print("\n commanded knee: left -0.90, right +0.90")
