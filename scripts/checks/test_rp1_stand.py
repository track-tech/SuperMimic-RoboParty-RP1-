"""Standing test for the RP1 MJCF: place the feet on the ground, then hold ctrl.

The earlier "200 steps, base_z=0.730" check was 0.2 s of free fall, not
standing - this places the robot exactly on the ground first and runs 3 s.

    python test_rp1_stand.py --xml <path> [--kp-big 85 --kv-big 5 ...]
"""
import argparse
import os
import re

import mujoco
import numpy as np

JOINT_ORDER = [
    "left_thigh_yaw_joint", "left_thigh_roll_joint", "left_thigh_pitch_joint",
    "left_knee_joint", "left_ankle_pitch_joint", "left_ankle_roll_joint",
    "right_thigh_yaw_joint", "right_thigh_roll_joint", "right_thigh_pitch_joint",
    "right_knee_joint", "right_ankle_pitch_joint", "right_ankle_roll_joint",
    "torso_joint",
    "left_arm_pitch_joint", "left_arm_roll_joint", "left_arm_yaw_joint",
    "left_elbow_pitch_joint", "left_elbow_yaw_joint",
    "right_arm_pitch_joint", "right_arm_roll_joint", "right_arm_yaw_joint",
    "right_elbow_pitch_joint", "right_elbow_yaw_joint",
]
BIG = {"left_thigh_yaw_joint", "left_thigh_roll_joint", "left_thigh_pitch_joint",
       "left_knee_joint", "right_thigh_yaw_joint", "right_thigh_roll_joint",
       "right_thigh_pitch_joint", "right_knee_joint", "torso_joint"}
EFFORT = {n: (120.0 if n in BIG else 27.0) for n in JOINT_ORDER}


def set_gains(xml_text, kp_big, kv_big, kp_small, kv_small):
    lines = ["  <actuator>"]
    for name in JOINT_ORDER:
        kp, kv = (kp_big, kv_big) if name in BIG else (kp_small, kv_small)
        g = EFFORT[name]
        lines.append(
            f'    <position name="{name}" joint="{name}" kp="{kp:.4f}" kv="{kv:.4f}" '
            f'ctrllimited="false" forcerange="{-g:.0f} {g:.0f}" />'
        )
    lines.append("  </actuator>")
    block = "\n".join(lines)
    out, n = re.subn(r"<actuator>.*?</actuator>", block, xml_text, flags=re.S)
    if n != 1:
        raise SystemExit(f"expected 1 actuator block, found {n}")
    return out


def load(xml_text, tmp):
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(xml_text)
    return mujoco.MjModel.from_xml_path(tmp)


def place_on_ground(model, data):
    """Lower the base until the lowest robot geom just touches the floor."""
    mujoco.mj_forward(model, data)
    floor = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "ground")
    if floor < 0:
        floor = 0
    best = np.inf
    for g in range(model.ngeom):
        if g == floor:
            continue
        try:
            dist = mujoco.mj_geomDistance(model, data, g, floor, 5.0, None)
        except Exception:  # noqa: BLE001  older mujoco
            dist = data.geom_xpos[g, 2] - model.geom_rbound[g]
        best = min(best, dist)
    data.qpos[2] -= best - 0.001
    mujoco.mj_forward(model, data)
    return float(data.qpos[2])


def run(xml_text, tmp, seconds=3.0):
    model = load(xml_text, tmp)
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    qpos0 = data.qpos.copy()
    ctrl = data.ctrl.copy()
    place_on_ground(model, data)
    z0 = float(data.qpos[2])
    n = int(seconds / model.opt.timestep)
    ups, zs = [], []
    for k in range(n):
        data.ctrl[:] = ctrl
        mujoco.mj_step(model, data)
        if k % int(0.05 / model.opt.timestep) == 0:
            ups.append(float(data.body("torso_link").xmat.reshape(3, 3)[2, 2]))
            zs.append(float(data.qpos[2]))
    return dict(
        z0=z0, z_end=zs[-1], up_min=min(ups), up_end=ups[-1],
        ncon=int(data.ncon), foot_z=float(np.min(data.geom_xpos[[0], 2])),
        q0_joints=qpos0[7:].copy(),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", required=True)
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--gains", default=None,
                    help="kp_big,kv_big,kp_small,kv_small (single test)")
    ap.add_argument("--write", action="store_true",
                    help="write the patched actuator block back to --xml (or --out)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    xml = open(args.xml, encoding="utf-8").read()
    tmp = os.path.join(os.path.dirname(os.path.abspath(args.xml)), "_stand_test.xml")

    if args.gains:
        kb, vb, ks, vs = [float(x) for x in args.gains.split(",")]
        patched = set_gains(xml, kb, vb, ks, vs)
        if args.write:
            out = args.out or args.xml
            with open(out, "w", encoding="utf-8") as f:
                f.write(patched)
            print(f"wrote {out}: kp_big={kb} kv_big={vb} kp_small={ks} kv_small={vs}")
        r = run(patched, tmp, args.seconds)
        print(f"gains {kb}/{vb} {ks}/{vs}: z0={r['z0']:.3f} z_end={r['z_end']:.3f} "
              f"up_end={r['up_end']:+.3f} up_min={r['up_min']:+.3f} ncon={r['ncon']}")
        return

    cands = [
        ("A armature conv", 39.478, 2.513, 39.478, 2.513),
        ("B 2x armature", 78.96, 5.03, 78.96, 5.03),
        ("C G1-scaled", 85.0, 5.0, 19.0, 1.2),
        ("D old phaseA", 150.0, 5.0, 40.0, 1.5),
        ("E stiff", 250.0, 8.0, 60.0, 2.5),
    ]
    print(f"{'candidate':16} {'z0':>7} {'z_end':>7} {'up_min':>7} {'up_end':>7} {'ncon':>5}")
    for label, kb, vb, ks, vs in cands:
        try:
            r = run(set_gains(xml, kb, vb, ks, vs), tmp, args.seconds)
        except Exception as exc:  # noqa: BLE001
            print(f"{label:16} FAILED {exc}")
            continue
        print(f"{label:16} {r['z0']:7.3f} {r['z_end']:7.3f} {r['up_min']:+7.3f} "
              f"{r['up_end']:+7.3f} {r['ncon']:5d}")


if __name__ == "__main__":
    main()
