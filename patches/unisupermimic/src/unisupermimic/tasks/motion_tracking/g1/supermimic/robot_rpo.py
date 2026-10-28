"""Roboparty RP1 (MuJoCo model name ``rpo``): 23 DoF.

Layout is identical to the MJCF document order used by GMR's
``bvh_lafan1_to_rpo.json`` and by ``conf/.../rp1_super_mimic/base.yaml``:
legs 6 per side, one torso joint, 5 per arm (no wrists).
"""

from __future__ import annotations

import re

NATURAL_FREQ = 10 * 2.0 * 3.1415926535
DAMPING_RATIO = 2.0


def _kp(armature: float) -> float:
    return armature * NATURAL_FREQ**2


def _kd(armature: float) -> float:
    return 2.0 * DAMPING_RATIO * armature * NATURAL_FREQ


# Name kept identical to the G1 module so the shared call sites keep working.
G1_JOINT_NAMES = [
    "left_thigh_yaw_joint", "left_thigh_roll_joint", "left_thigh_pitch_joint",
    "left_knee_joint", "left_ankle_pitch_joint", "left_ankle_roll_joint",
    "right_thigh_yaw_joint", "right_thigh_roll_joint", "right_thigh_pitch_joint",
    "right_knee_joint", "right_ankle_pitch_joint", "right_ankle_roll_joint",
    "torso_joint",
    "left_arm_pitch_joint", "left_arm_roll_joint", "left_arm_yaw_joint",
    "left_elbow_pitch_joint", "left_elbow_yaw_joint",
    "right_arm_pitch_joint", "right_arm_roll_joint", "right_arm_yaw_joint",
    "right_elbow_pitch_joint", "right_elbow_yaw_joint",
]  # fmt: skip

TRACKED_BODIES = [
    "base_link",
    "left_thigh_roll_link", "left_knee_link", "left_ankle_roll_link",
    "right_thigh_roll_link", "right_knee_link", "right_ankle_roll_link",
    "torso_link",
    "left_arm_roll_link", "left_elbow_pitch_link", "left_elbow_yaw_link",
    "right_arm_roll_link", "right_elbow_pitch_link", "right_elbow_yaw_link",
]  # fmt: skip

ROOT_BODY_NAME = "base_link"
TORSO_BODY_NAME = "torso_link"

# rpo.xml gives every geom an implicit name; there are no ``*_collision`` names
# to filter on, so let the entity keep all of them.
COLLISION_GEOM_NAMES = (
    "base_link_collision",
    "left_thigh_yaw_link_collision",
    "left_thigh_roll_link_collision",
    "left_thigh_pitch_link_collision",
    "left_knee_link_collision",
    "left_ankle_pitch_link_collision",
    "left_ankle_roll_link_collision",
    "right_thigh_yaw_link_collision",
    "right_thigh_roll_link_collision",
    "right_thigh_pitch_link_collision",
    "right_knee_link_collision",
    "right_ankle_pitch_link_collision",
    "right_ankle_roll_link_collision",
    "torso_link_collision",
    "left_arm_pitch_link_collision",
    "left_arm_roll_link_collision",
    "left_arm_yaw_link_collision",
    "left_elbow_pitch_link_collision",
    "left_elbow_yaw_link_collision",
    "right_arm_pitch_link_collision",
    "right_arm_roll_link_collision",
    "right_arm_yaw_link_collision",
    "right_elbow_pitch_link_collision",
    "right_elbow_yaw_link_collision",
)

# (effort N*m, velocity rad/s, armature).  armature is *not* the MJCF value
# (0.01) but the value whose natural-frequency kp_ equals the position-servo kp
# actually written into rpo_supermimic.xml and validated in MuJoCo
# (150 for the 120 N*m group, 40 for the 27 N*m group).  Keeping it consistent
# makes action_scale() mean "the action that produces ~25% of the torque limit".
_ARMATURE_BIG = 150.0 / NATURAL_FREQ**2   # 0.03800
_ARMATURE_SMALL = 40.0 / NATURAL_FREQ**2  # 0.01013

_BIG = (120.0, 25.0, _ARMATURE_BIG)
_SMALL = (27.0, 8.0, _ARMATURE_SMALL)

JOINT_MOTORS = {
    "thigh_yaw": _BIG,
    "thigh_roll": _BIG,
    "thigh_pitch": _BIG,
    "knee": _BIG,
    "torso": _BIG,
    "ankle_pitch": _SMALL,
    "ankle_roll": _SMALL,
    "arm_pitch": _SMALL,
    "arm_roll": _SMALL,
    "arm_yaw": _SMALL,
    "elbow_pitch": _SMALL,
    "elbow_yaw": _SMALL,
}

DEFAULT_JOINT_POS = {
    ".*_thigh_pitch_joint": -0.25,
    ".*_knee_joint": 0.5,
    ".*_ankle_pitch_joint": -0.25,
    ".*_arm_pitch_joint": 0.15,
    ".*_elbow_pitch_joint": -0.25,
}


def motor_of(joint_name: str) -> tuple[float, float, float]:
    key = joint_name.replace("left_", "").replace("right_", "").replace("_joint", "")
    return JOINT_MOTORS[key]


def action_scale(joint_name: str) -> float:
    effort, _, armature = motor_of(joint_name)
    return 0.25 * effort / _kp(armature)


def default_joint_pos_list() -> list[float]:
    positions = []
    for name in G1_JOINT_NAMES:
        value = 0.0
        for pattern, position in DEFAULT_JOINT_POS.items():
            if re.fullmatch(pattern, name):
                value = position
        positions.append(value)
    return positions
