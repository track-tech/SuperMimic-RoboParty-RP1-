"""Search a statically balanced standing pose for RP1 (foot flat, CoM over feet).

For each (thigh_pitch, knee) we set ankle_pitch = -(thigh_pitch + knee) so the
foot stays flat, drop the base onto the ground, then measure the CoM offset from
the feet and simulate 2 s at the current actuator gains.

    python search_stand_pose.py --xml <path> [--seconds 2]
"""
import argparse
import itertools
import os

import mujoco
import numpy as np

JOINTS = [
    "left_thigh_yaw_joint", "left_thigh_roll_joint", "left_thigh_pitch_joint",
    "left_knee_joint", "left_ankle_pitch_joint", "left_ankle_roll_joint",
    "right_thigh_yaw_joint", "right_thigh_roll_joint", "right_thigh_pitch_joint",
    "right_knee_joint", "right_ankle_pitch_joint", "right_ankle_roll_joint",
    "torso_joint",
]


def build_qpos(model, data, thigh, knee, ankle):
    data.qpos[:] = 0.0
    data.qpos[3] = 1.0
    idx = {mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j): j for j in range(model.njnt)}
    qadr = {n: model.jnt_qposadr[idx[n]] for n in JOINTS if n in idx}
    for side in ("left", "right"):
        qadr_f = f"{side}_thigh_pitch_joint"
        if qadr_f in qadr:
            data.qpos[qadr[qadr_f]] = thigh
            data.qpos[qadr[f"{side}_knee_joint"]] = knee
            data.qpos[qadr[f"{side}_ankle_pitch_joint"]] = ankle
    # arms slightly out so they do not hit the body
    for side in ("left", "right"):
        s = 1.0 if side == "left" else -1.0
        for name, val in (
            (f"{side}_arm_pitch_joint", 0.15),
            (f"{side}_arm_roll_joint", 0.12 * s),
            (f"{side}_elbow_pitch_joint", -0.25),
        ):
            if name in qadr:
                data.qpos[qadr[name]] = val
    return data.qpos.copy()


def set_ctrl_to_pose(model, data):
    """Position actuators must be commanded to hold the pose, not to 0."""
    data.ctrl[:] = data.qpos[7:7 + model.nu]


def place(model, data):
    mujoco.mj_forward(model, data)
    floor = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "ground")
    if floor < 0:
        floor = 0
    best = np.inf
    for g in range(model.ngeom):
        if g == floor:
            continue
        try:
            d = mujoco.mj_geomDistance(model, data, g, floor, 5.0, None)
        except Exception:  # noqa: BLE001
            d = data.geom_xpos[g, 2] - model.geom_rbound[g]
        best = min(best, d)
    data.qpos[2] -= best - 0.001
    mujoco.mj_forward(model, data)


def measure(model, data):
    place(model, data)
    com = data.subtree_com[0]
    lf = data.body("left_ankle_roll_link").xpos
    rf = data.body("right_ankle_roll_link").xpos
    foot_mid = 0.5 * (lf + rf)
    return dict(
        z0=float(data.qpos[2]),
        com_dx=float(com[0] - foot_mid[0]),
        com_dy=float(com[1] - foot_mid[1]),
        foot_z=float(min(lf[2], rf[2])),
    )


def simulate(model, data, seconds):
    qpos0 = data.qpos.copy()
    n = int(seconds / model.opt.timestep)
    ups = []
    for k in range(n):
        mujoco.mj_step(model, data)
        if k % int(0.05 / model.opt.timestep) == 0:
            ups.append(float(data.body("torso_link").xmat.reshape(3, 3)[2, 2]))
    return dict(up_min=min(ups), up_end=ups[-1], z_end=float(data.qpos[2]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", required=True)
    ap.add_argument("--seconds", type=float, default=2.0)
    ap.add_argument("--write-keyframe", action="store_true")
    args = ap.parse_args()

    xml_path = os.path.abspath(args.xml)
    model = mujoco.MjModel.from_xml_path(xml_path)
    data = mujoco.MjData(model)

    rows = []
    for thigh, knee in itertools.product(
        [-0.35, -0.30, -0.25, -0.20, -0.15, -0.10], [0.15, 0.25, 0.35, 0.45, 0.55]
    ):
        ankle = -(thigh + knee)
        if abs(ankle) > 0.55:
            continue
        build_qpos(model, data, thigh, knee, ankle)
        set_ctrl_to_pose(model, data)
        m = measure(model, data)
        s = simulate(model, data, args.seconds)
        rows.append((thigh, knee, ankle, m, s))

    rows.sort(key=lambda r: (r[4]["up_end"] < 0.9, abs(r[3]["com_dx"])))
    print(f"{'thigh':>6} {'knee':>6} {'ankle':>6} {'z0':>6} {'com_dx':>7} "
          f"{'com_dy':>7} {'up_min':>7} {'up_end':>7} {'z_end':>6}")
    for thigh, knee, ankle, m, s in rows:
        flag = "" if s["up_end"] > 0.9 else "  FELL"
        print(f"{thigh:6.2f} {knee:6.2f} {ankle:6.2f} {m['z0']:6.3f} "
              f"{m['com_dx']:+7.3f} {m['com_dy']:+7.3f} {s['up_min']:+7.3f} "
              f"{s['up_end']:+7.3f} {s['z_end']:6.3f}{flag}")

    best = rows[0]
    print(f"\nbest: thigh={best[0]:.2f} knee={best[1]:.2f} ankle={best[2]:.2f} "
          f"z0={best[3]['z0']:.4f} com_dx={best[3]['com_dx']:+.3f}")

    if args.write_keyframe:
        import re
        txt = open(xml_path, encoding="utf-8").read()
        thigh, knee, ankle = best[0], best[1], best[2]
        joints = [0.0] * 23
        # leg joints in document order: L(6) R(6) torso, then arms
        vals = {"left_thigh_pitch_joint": thigh, "left_knee_joint": knee,
                "left_ankle_pitch_joint": ankle,
                "right_thigh_pitch_joint": thigh, "right_knee_joint": knee,
                "right_ankle_pitch_joint": ankle,
                "left_arm_pitch_joint": 0.15, "left_arm_roll_joint": 0.12,
                "left_elbow_pitch_joint": -0.25,
                "right_arm_pitch_joint": 0.15, "right_arm_roll_joint": -0.12,
                "right_elbow_pitch_joint": -0.25}
        order = [
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
        for i, name in enumerate(order):
            joints[i] = vals.get(name, 0.0)
        z = best[3]["z0"]
        qpos = f"0 0 {z:.4f} 1 0 0 0 " + " ".join(f"{v:g}" for v in joints)
        ctrl = " ".join(f"{v:g}" for v in joints)
        new = (f'<keyframe><key name="stand" qpos="{qpos}" ctrl="{ctrl}" /></keyframe>')
        txt2, n = re.subn(r"<keyframe>.*?</keyframe>", new, txt, flags=re.S)
        if n != 1:
            raise SystemExit(f"expected one keyframe block, found {n}")
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(txt2)
        print(f"wrote keyframe stand: z={z:.4f}")


if __name__ == "__main__":
    main()
