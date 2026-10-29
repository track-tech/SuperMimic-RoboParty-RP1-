"""How far is the retargeted reference from the floor? (catches ground-alignment bugs)

    python check_ground_clearance.py <motions_dir> <scene_or_robot_mjcf> <num_joints> <clip>

Reports the signed distance between the lowest colliding geom and the ground
plane over sampled frames.  A large negative median means the whole clip sits
inside the floor - the classic symptom of aligning by body origins instead of by
the real lowest geometry (foot soles hang below their link origin).
"""
import os
import sys

import mujoco
import numpy as np


def main():
    motions, xml, nj, clip = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    n_samples = int(sys.argv[5]) if len(sys.argv) > 5 else 200

    model = mujoco.MjModel.from_xml_path(xml)
    data = mujoco.MjData(model)
    joints = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, int(model.dof_jntid[i]))
              for i in range(6, 6 + nj)]
    adr = {n: model.jnt_qposadr[model.joint(n).id] for n in joints}
    plane = next(g for g in range(model.ngeom)
                 if model.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE)

    q = np.loadtxt(os.path.join(motions, clip + ".csv"), delimiter=",")
    idx = np.linspace(0, q.shape[0] - 1, min(n_samples, q.shape[0])).astype(int)
    mins = []
    for k in idx:
        data.qpos[:] = 0.0
        data.qpos[0:3] = q[k, :3]
        data.qpos[3] = q[k, 6]          # CSV stores xyzw, MuJoCo wants wxyz
        data.qpos[4:7] = q[k, 3:6]
        for i, name in enumerate(joints):
            data.qpos[adr[name]] = q[k, 7 + i]
        mujoco.mj_forward(model, data)
        best = np.inf
        for g in range(model.ngeom):
            if g == plane:
                continue
            if model.geom_contype[g] == 0 and model.geom_conaffinity[g] == 0:
                continue
            best = min(best, mujoco.mj_geomDistance(model, data, g, plane, 2.0, None))
        mins.append(best)
    m = np.array(mins)
    print(f"{clip}: 最低几何到地面 min {m.min():+.4f}  p05 {np.percentile(m,5):+.4f}  "
          f"p50 {np.percentile(m,50):+.4f}  穿地帧 {(m < -0.002).mean():5.1%}")


if __name__ == "__main__":
    main()
