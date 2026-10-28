"""Rewrite the RP1 position actuators and pick PD gains by a standing test.

G1's supermimic MJCF uses kp = armature * NATURAL_FREQ**2 and
kv = 2 * DAMPING_RATIO * armature * NATURAL_FREQ with NATURAL_FREQ = 10*2*pi,
DAMPING_RATIO = 2, i.e. kp = 39.4784, kv = 2.5133 for armature 0.01.
RP1's MJCF also declares armature 0.01 everywhere, but with 33.8 kg and
120 N*m actuators that may be too soft to stand - so measure it.

Run with the gmr-env python (needs mujoco):
    python tune_rp1_gains.py --xml <path> --test
    python tune_rp1_gains.py --xml <path> --write kp_big kv_big kp_small kv_small
"""
import argparse
import os
import re

import mujoco
import numpy as np

BIG = ["left_thigh_yaw_joint", "left_thigh_roll_joint", "left_thigh_pitch_joint",
       "left_knee_joint", "right_thigh_yaw_joint", "right_thigh_roll_joint",
       "right_thigh_pitch_joint", "right_knee_joint", "torso_joint"]
SMALL = ["left_ankle_pitch_joint", "left_ankle_roll_joint",
         "right_ankle_pitch_joint", "right_ankle_roll_joint",
         "left_arm_pitch_joint", "left_arm_roll_joint", "left_arm_yaw_joint",
         "left_elbow_pitch_joint", "left_elbow_yaw_joint",
         "right_arm_pitch_joint", "right_arm_roll_joint", "right_arm_yaw_joint",
         "right_elbow_pitch_joint", "right_elbow_yaw_joint"]
EFFORT = {**{n: 120.0 for n in BIG}, **{n: 27.0 for n in SMALL}}


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


def actuator_block(kp_big, kv_big, kp_small, kv_small):
    lines = ["  <actuator>"]
    for name in JOINT_ORDER:
        if name in BIG:
            kp, kv = kp_big, kv_big
        else:
            kp, kv = kp_small, kv_small
        eff = EFFORT[name]
        lines.append(
            f'    <position name="{name}" joint="{name}" kp="{kp:.6f}" kv="{kv:.6f}" '
            f'ctrllimited="false" forcerange="{-eff:.0f} {eff:.0f}" />'
        )
    lines.append("  </actuator>")
    return "\n".join(lines)


def set_gains(xml_text, kp_big, kv_big, kp_small, kv_small):
    new_block = actuator_block(kp_big, kv_big, kp_small, kv_small)
    out, n = re.subn(r"<actuator>.*?</actuator>", new_block, xml_text, flags=re.S)
    if n != 1:
        raise SystemExit(f"expected 1 actuator block, found {n}")
    return out


def simulate(xml_text, seconds=4.0, tmp=None):
    tmp = tmp or "/tmp/_rp1_gain_test.xml"
    with open(tmp, "w") as f:
        f.write(xml_text)
    model = mujoco.MjModel.from_xml_path(tmp)
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    mujoco.mj_forward(model, data)
    z0 = float(data.qpos[2])
    n = int(seconds / model.opt.timestep)
    zs, ups = [], []
    for k in range(n):
        mujoco.mj_step(model, data)
        if k % int(0.1 / model.opt.timestep) == 0:
            zs.append((k * model.opt.timestep, float(data.qpos[2])))
            # torso up-axis vs world z
            rot = data.body("torso_link").xmat.reshape(3, 3)
            ups.append(float(rot[2, 2]))
    q = data.qpos[7:]
    ctrl = data.ctrl
    rng = [model.actuator_ctrlrange[i] for i in range(model.nu)]
    return dict(
        z0=z0,
        z_end=float(data.qpos[2]),
        z_series=zs[::5],
        up_min=float(np.min(ups)),
        up_end=float(ups[-1]),
        ncon=int(data.ncon),
        q=q.copy(),
        err=float(np.max(np.abs(q - data.ctrl) / np.maximum(np.ptp(rng, axis=1), 1e-9))),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", required=True)
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--write", nargs=4, type=float, default=None,
                    metavar=("KP_BIG", "KV_BIG", "KP_SMALL", "KV_SMALL"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    xml = open(args.xml, encoding="utf-8").read()

    if args.write:
        new = set_gains(xml, *args.write)
        out = args.out or args.xml
        with open(out, "w", encoding="utf-8") as f:
            f.write(new)
        print(f"wrote {out} with kp_big={args.write[0]} kv_big={args.write[1]} "
              f"kp_small={args.write[2]} kv_small={args.write[3]}")
        xml = new

    if args.test:
        # meshdir is relative to the XML, so the scratch copy must live beside it
        tmp = os.path.join(os.path.dirname(os.path.abspath(args.xml)), "_gain_test.xml")
        cands = [
            ("A natural-freq (0.01)", 39.478, 2.513, 39.478, 2.513),
            ("B half G1-ish", 70.0, 4.0, 30.0, 1.8),
            ("C G1-scaled", 85.0, 5.0, 25.0, 1.6),
            ("D current-used", 150.0, 5.0, 40.0, 1.5),
        ]
        print(f"{'candidate':24} {'z0':>6} {'z_end':>6} {'up_min':>7} {'up_end':>7} "
              f"{'ncon':>4} {'maxerr':>7}")
        for label, kb, vb, ks, vs in cands:
            txt = set_gains(xml, kb, vb, ks, vs)
            try:
                r = simulate(txt, tmp=tmp)
            except Exception as exc:  # noqa: BLE001
                print(f"{label:24} FAILED: {exc}")
                continue
            print(f"{label:24} {r['z0']:6.3f} {r['z_end']:6.3f} {r['up_min']:7.3f} "
                  f"{r['up_end']:7.3f} {r['ncon']:4d} {r['err']:7.3f}")


if __name__ == "__main__":
    main()
