"""Headless LAFAN1 BVH -> RP1 (rpo) retargeting using GMR.

Mirrors scripts/bvh_to_robot.py but without the MuJoCo viewer / tty
interaction, so it runs over ssh.  Output CSV matches the format of
Uni-SuperMimic's G1 set: 3 pos + 4 quat (xyzw) + N dof, 30 fps.

Run on the server:
    /root/gpufree-data/mars/gmr-env/bin/python retarget_rp1.py \
        --bvh_dir /root/gpufree-data/mars/ext/lafan1_bvh \
        --out_dir /root/gpufree-data/mars/ext/rp1_motions \
        --robot rpo --limit 1
"""
import argparse
import os
import sys
import time
import traceback

import numpy as np

GMR_ROOT = os.environ.get("GMR_ROOT", "/root/gpufree-data/mars/ext/GMR")
sys.path.insert(0, GMR_ROOT)

import mujoco as mj  # noqa: E402

from general_motion_retargeting import GeneralMotionRetargeting as GMR  # noqa: E402
from general_motion_retargeting.params import ROBOT_XML_DICT  # noqa: E402
from general_motion_retargeting.utils.lafan1 import load_bvh_file  # noqa: E402


def retarget_one(bvh_file, robot, out_dir, fmt="lafan1", verbose=False):
    name = os.path.splitext(os.path.basename(bvh_file))[0]
    out_csv = os.path.join(out_dir, name + ".csv")
    out_npz = os.path.join(out_dir, name + ".npz")
    if os.path.exists(out_npz):
        return name, "cached", 0, None

    frames, human_height = load_bvh_file(bvh_file, format=fmt)
    rt = GMR(
        src_human="bvh_lafan1",
        tgt_robot=robot,
        actual_human_height=human_height,
        verbose=verbose,
    )
    t0 = time.time()
    qpos = np.array([rt.retarget(f) for f in frames], dtype=np.float64)
    n = qpos.shape[0]

    model = mj.MjModel.from_xml_path(str(ROBOT_XML_DICT[robot]))
    data = mj.MjData(model)

    # lowest body point across the whole clip -> plant the motion on z=0
    lo = np.inf
    for k in range(n):
        data.qpos[:] = qpos[k]
        mj.mj_kinematics(model, data)
        lo = min(lo, float(np.min(data.xpos[1:, 2])))
    qpos[:, 2] -= lo
    # start at the origin in xy
    qpos[:, :2] -= qpos[0, :2]

    root_pos = qpos[:, :3]
    root_quat_wxyz = qpos[:, 3:7]
    root_quat_xyzw = root_quat_wxyz[:, [1, 2, 3, 0]]
    dof_pos = qpos[:, 7:]

    dof_names = [
        mj.mj_id2name(model, mj.mjtObj.mjOBJ_JOINT, int(model.dof_jntid[i]))
        for i in range(6, model.nv)
    ]
    body_names = [mj.mj_id2name(model, mj.mjtObj.mjOBJ_BODY, i) for i in range(model.nbody)]

    os.makedirs(out_dir, exist_ok=True)
    with open(out_csv, "w") as f:
        for k in range(n):
            row = [f"{root_pos[k, j]:.6f}" for j in range(3)]
            row += [f"{root_quat_xyzw[k, j]:.6f}" for j in range(4)]
            row += [f"{dof_pos[k, j]:.6f}" for j in range(dof_pos.shape[1])]
            f.write(",".join(row) + "\n")

    np.savez_compressed(
        out_npz,
        fps=np.array(30),
        root_pos=root_pos,
        root_rot=root_quat_wxyz,          # wxyz, mujoco convention
        dof_pos=dof_pos,
        dof_names=np.array(dof_names, dtype=object),
        body_names=np.array(body_names, dtype=object),
        ground_offset=np.array(lo),
    )
    dt = time.time() - t0
    dof_range = dof_pos.max(axis=0) - dof_pos.min(axis=0)
    info = dict(
        seconds=dt,
        fps=n / dt,
        ground_offset=lo,
        base_z_mean=float(root_pos[:, 2].mean()),
        base_z_min=float(root_pos[:, 2].min()),
        dof_range=dof_range,
    )
    return name, "ok", n, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bvh_dir", default="/root/gpufree-data/mars/ext/lafan1_bvh")
    ap.add_argument("--out_dir", default="/root/gpufree-data/mars/ext/rp1_motions")
    ap.add_argument("--robot", default="rpo")
    ap.add_argument("--format", default="lafan1", choices=["lafan1", "nokov"])
    ap.add_argument("--limit", type=int, default=0, help="only first N clips (0 = all)")
    ap.add_argument("--only", default=None, help="comma separated clip names")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    files = sorted(f for f in os.listdir(args.bvh_dir) if f.endswith(".bvh"))
    if args.only:
        want = set(args.only.split(","))
        files = [f for f in files if os.path.splitext(f)[0] in want]
    if args.limit:
        files = files[: args.limit]
    print(f"[retarget] {len(files)} clips -> {args.out_dir} "
          f"(robot={args.robot}, fmt={args.format})", flush=True)

    ok, failed = 0, []
    for i, f in enumerate(files, 1):
        path = os.path.join(args.bvh_dir, f)
        try:
            name, status, n, info = retarget_one(
                path, args.robot, args.out_dir, args.format, args.verbose
            )
            if status == "ok":
                ok += 1
                rng = info["dof_range"]
                print(f"[{i}/{len(files)}] {name:28} {n:5d} frames  "
                      f"{info['fps']:5.1f} fps  base_z={info['base_z_mean']:.3f}  "
                      f"dof_range(max)={rng.max():.2f} rad", flush=True)
            else:
                print(f"[{i}/{len(files)}] {name:28} {status}", flush=True)
        except Exception as exc:  # noqa: BLE001
            failed.append((f, str(exc)))
            print(f"[{i}/{len(files)}] {f} FAILED: {exc}", flush=True)
            traceback.print_exc()

    print(f"\n[retarget] done: {ok} ok, {len(failed)} failed", flush=True)
    for f, e in failed:
        print(f"  FAIL {f}: {e}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
