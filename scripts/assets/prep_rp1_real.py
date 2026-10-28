"""Prepare the real Roboparty RP1 (28 DoF) for Uni-SuperMimic and test it stands.

Reads rp1_description/mjcf/robot.xml, writes
  assets/robots/rp1_real/rp1_supermimic.xml  (position actuators + stand keyframe)
  assets/robots/rp1_real/scene_supermimic.xml
  assets/robots/rp1_real/meshes/*.STL
and then sweeps PD gains in MuJoCo to pick ones that keep RP1 upright.

    python prep_rp1_real.py --src /tmp/rp1d/rp1_description-master --test
"""
import os as _os
_ROOT = _os.environ.get("UNI_SUPERMIMIC_ROOT")
if not _ROOT:
    raise SystemExit("请先 export UNI_SUPERMIMIC_ROOT=<Uni-SuperMimic 根目录>")
import argparse
import os
import re
import shutil

import mujoco
import numpy as np

NATURAL_FREQ = 10 * 2.0 * 3.1415926535
DAMPING_RATIO = 2.0


def kp_of(armature):
    return armature * NATURAL_FREQ**2


def actuator_block(src_xml, kp_big, kv_big, kp_mid, kv_mid, kp_small, kv_small):
    """Replace <actuator> with position servos; torque limits come from the motors."""
    motors = re.findall(
        r'<motor[^>]*ctrlrange="([-0-9. ]+)"[^>]*name="([^"]+)"[^>]*joint="([^"]+)"', src_xml
    )
    if not motors:
        motors = [
            (m.group(1), m.group(2), m.group(3))
            for m in re.finditer(
                r'<motor[^>]*name="([^"]+)"[^>]*joint="([^"]+)"[^>]*ctrlrange="([-0-9. ]+)"',
                src_xml,
            )
        ]
        motors = [(t, n, j) for n, j, t in motors]
    lines = ["  <actuator>"]
    for rng, name, joint in motors:
        lo, hi = [float(v) for v in rng.split()]
        torque = max(abs(lo), abs(hi))
        if torque >= 100:
            kp, kv = kp_big, kv_big
        elif torque >= 50:
            kp, kv = kp_mid, kv_mid
        else:
            kp, kv = kp_small, kv_small
        lines.append(
            f'    <position name="{name}" joint="{joint}" kp="{kp:.3f}" kv="{kv:.3f}" '
            f'ctrllimited="false" forcerange="{-torque:.0f} {torque:.0f}" />'
        )
    lines.append("  </actuator>")
    return "\n".join(lines), len(motors)


SCENE = """<mujoco model="rp1 supermimic scene">
  <include file="rp1_supermimic.xml"/>

  <statistic center="0 0 0.6" extent="0.5"/>

  <visual>
    <quality shadowsize="4096"/>
    <map znear="0.05"/>
  </visual>

  <asset>
    <texture type="skybox" builtin="gradient" rgb1="0.55 0.55 0.57" rgb2="0.55 0.55 0.57" width="512" height="3072"/>
    <texture type="2d" name="groundplane" builtin="checker" rgb1="0.66 0.66 0.675" rgb2="0.615 0.615 0.63" width="300" height="300"/>
    <material name="groundplane" texture="groundplane" texuniform="true" texrepeat="1.0 1.0" reflectance="0.0"/>
  </asset>

  <worldbody>
    <light pos="0 0 3" dir="0 0 -1" directional="true"/>
    <geom name="floor" size="0 0 0.05" type="plane" material="groundplane"
          condim="4" contype="1" conaffinity="15" friction="0.9 0.2 0.2" solref="0.01 1"/>
  </worldbody>
</mujoco>
"""


def build_model(src_xml, keyframe_qpos, gains):
    xml = src_xml
    # meshes are referenced as meshes/xxx.STL; keep that layout next to the model
    xml = xml.replace('meshdir="../"', 'meshdir="./"')
    block, n = actuator_block(xml, *gains)
    xml, count = re.subn(r"<actuator>.*?</actuator>", block, xml, flags=re.S)
    if count != 1:
        raise SystemExit(f"expected one actuator block, got {count}")
    qpos = " ".join(f"{v:.6g}" for v in keyframe_qpos)
    ctrl = " ".join(f"{v:.6g}" for v in keyframe_qpos[7:])
    key = f'  <keyframe><key name="stand" qpos="{qpos}" ctrl="{ctrl}" /></keyframe>\n'
    xml = xml.replace("</mujoco>", key + "</mujoco>")
    return xml, n


def floor_geom(model):
    for g in range(model.ngeom):
        if model.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE:
            return g
    return 0


def place(model, data):
    mujoco.mj_forward(model, data)
    fl = floor_geom(model)
    best = np.inf
    for g in range(model.ngeom):
        if g == fl:
            continue
        try:
            d = mujoco.mj_geomDistance(model, data, g, fl, 5.0, None)
        except Exception:  # noqa: BLE001
            d = data.geom_xpos[g, 2] - model.geom_rbound[g]
        best = min(best, d)
    data.qpos[2] -= best - 0.001
    mujoco.mj_forward(model, data)


def run(robot_xml, scene_path, tmp, seconds=3.0):
    """Write the candidate robot xml, then simulate the *scene* that includes it."""
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(robot_xml)
    model = mujoco.MjModel.from_xml_path(scene_path)
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    ctrl = data.ctrl.copy()
    place(model, data)
    z0 = float(data.qpos[2])
    n = int(seconds / model.opt.timestep)
    ups, zs = [], []
    for k in range(n):
        data.ctrl[:] = ctrl
        mujoco.mj_step(model, data)
        if k % int(0.05 / model.opt.timestep) == 0:
            ups.append(float(data.body("waist_yaw_link").xmat.reshape(3, 3)[2, 2]))
            zs.append(float(data.qpos[2]))
    return dict(z0=z0, z_end=zs[-1], up_min=min(ups), up_end=ups[-1], ncon=int(data.ncon))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="/tmp/rp1d/rp1_description-master")
    ap.add_argument("--dst", default=_ROOT + "/src/"
                                   "unisupermimic/assets/robots/rp1_real")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--gains", default=None,
                    help="kp_big,kv_big,kp_mid,kv_mid,kp_small,kv_small to write")
    args = ap.parse_args()

    src_xml = open(os.path.join(args.src, "mjcf/robot.xml"), encoding="utf-8").read()
    # keyframe: straight legs at the model's own base height, then placed on the floor
    key = [0.0] * 35
    key[2] = 0.78
    key[3] = 1.0
    default_gains = (kp_of(0.01), 2 * DAMPING_RATIO * 0.01 * NATURAL_FREQ,
                     kp_of(0.01), 2 * DAMPING_RATIO * 0.01 * NATURAL_FREQ,
                     kp_of(0.01), 2 * DAMPING_RATIO * 0.01 * NATURAL_FREQ)

    gains = tuple(float(x) for x in args.gains.split(",")) if args.gains else default_gains
    xml, n_act = build_model(src_xml, key, gains)

    os.makedirs(args.dst, exist_ok=True)
    mesh_dst = os.path.join(args.dst, "meshes")
    if not os.path.isdir(mesh_dst):
        shutil.copytree(os.path.join(args.src, "meshes"), mesh_dst,
                        ignore=shutil.ignore_patterns("hand"))
    with open(os.path.join(args.dst, "rp1_supermimic.xml"), "w", encoding="utf-8") as f:
        f.write(xml)
    with open(os.path.join(args.dst, "scene_supermimic.xml"), "w", encoding="utf-8") as f:
        f.write(SCENE)
    print(f"wrote {args.dst}  ({n_act} position actuators, gains={gains})")

    if not args.test:
        return

    tmp = os.path.join(args.dst, "_stand_test.xml")
    scene_tmp = os.path.join(args.dst, "_scene_test.xml")
    with open(scene_tmp, "w", encoding="utf-8") as f:
        f.write(SCENE.replace('include file="rp1_supermimic.xml"',
                              'include file="_stand_test.xml"'))
    cands = [
        ("A armature 0.01", kp_of(0.01), 2.513, kp_of(0.01), 2.513, kp_of(0.01), 2.513),
        ("B mid 80", 80.0, 4.5, 60.0, 3.5, 30.0, 2.0),
        ("C rpo-like", 150.0, 5.0, 80.0, 4.0, 40.0, 1.5),
        ("D stiff 250", 250.0, 8.0, 150.0, 6.0, 60.0, 2.5),
    ]
    print(f"{'candidate':16} {'z0':>7} {'z_end':>7} {'up_min':>7} {'up_end':>7} {'ncon':>5}")
    for label, *g in cands:
        x, _ = build_model(src_xml, key, tuple(g))
        try:
            r = run(x, scene_tmp, tmp, args.seconds)
        except Exception as exc:  # noqa: BLE001
            print(f"{label:16} FAILED {exc}")
            continue
        print(f"{label:16} {r['z0']:7.3f} {r['z_end']:7.3f} {r['up_min']:+7.3f} "
              f"{r['up_end']:+7.3f} {r['ncon']:5d}")
    for p in (tmp, scene_tmp):
        try:
            os.unlink(p)
        except OSError:
            pass


if __name__ == "__main__":
    main()
