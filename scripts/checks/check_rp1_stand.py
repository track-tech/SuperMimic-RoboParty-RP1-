"""Hold the written RP1 stand keyframe for N seconds and report stability."""
import os as _os
_ROOT = _os.environ.get("UNI_SUPERMIMIC_ROOT")
if not _ROOT:
    raise SystemExit("请先 export UNI_SUPERMIMIC_ROOT=<Uni-SuperMimic 根目录>")
import sys

import mujoco
import numpy as np

scene = (_ROOT + "/src/unisupermimic/assets/"
         "robots/rp1_real/scene_supermimic.xml")
seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0

model = mujoco.MjModel.from_xml_path(scene)
data = mujoco.MjData(model)
mujoco.mj_resetDataKeyframe(model, data, 0)
ctrl = data.ctrl.copy()
mujoco.mj_forward(model, data)


def place():
    fl = next(g for g in range(model.ngeom)
              if model.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE)
    best = np.inf
    for g in range(model.ngeom):
        if g == fl:
            continue
        d = mujoco.mj_geomDistance(model, data, g, fl, 5.0, None)
        best = min(best, d)
    data.qpos[2] -= best - 0.001
    mujoco.mj_forward(model, data)


place()
z0 = float(data.qpos[2])
ups, zs = [], []
for k in range(int(seconds / model.opt.timestep)):
    data.ctrl[:] = ctrl
    mujoco.mj_step(model, data)
    if k % int(0.05 / model.opt.timestep) == 0:
        ups.append(float(data.body("waist_yaw_link").xmat.reshape(3, 3)[2, 2]))
        zs.append(float(data.qpos[2]))
finite = np.isfinite(data.qpos).all()
print(f"gains kp/fv sample: {model.actuator_gainprm[0, 0]:.1f}/{model.actuator_biasprm[0, 2]:.1f}  "
      f"forcerange[0]={model.actuator_forcerange[0]}")
print(f"z0={z0:.3f} z_end={zs[-1]:.3f} up_end={ups[-1]:+.3f} up_min={min(ups):+.3f} "
      f"ncon={data.ncon} finite={finite}")
print(f"z trace: {[round(v,3) for v in zs[::4]]}")
