"""Roboparty RP1 (MuJoCo model ``rp1``): 28 actuated DoF.

Layout is the MJCF document order, which is also the order GMR's
``bvh_lafan1_to_rp1.json`` retargets into:

  6 per leg  (hip pitch / roll / yaw, knee, ankle pitch / roll)
  2 waist    (roll, yaw)
  7 per arm  (shoulder pitch / roll / yaw, elbow, wrist roll / yaw / pitch)

Torque groups taken from the MJCF motor ctrlrange: 140 / 64 / 55 / 32 N*m.
"""

from __future__ import annotations

import re

NATURAL_FREQ = 10 * 2.0 * 3.1415926535
DAMPING_RATIO = 2.0


def _kp(armature: float) -> float:
    return armature * NATURAL_FREQ**2


def _kd(armature: float) -> float:
    return 2.0 * DAMPING_RATIO * armature * NATURAL_FREQ


# Name kept identical to the G1/RPO modules so shared call sites keep working.
G1_JOINT_NAMES = [
    "left_hip_pitch_joint", "left_hip_roll_joint", "left_hip_yaw_joint", "left_knee_joint",
    "left_ankle_pitch_joint", "left_ankle_roll_joint",
    "right_hip_pitch_joint", "right_hip_roll_joint", "right_hip_yaw_joint", "right_knee_joint",
    "right_ankle_pitch_joint", "right_ankle_roll_joint",
    "waist_roll_joint", "waist_yaw_joint",
    "left_shoulder_pitch_joint", "left_shoulder_roll_joint", "left_shoulder_yaw_joint",
    "left_elbow_joint", "left_wrist_roll_joint", "left_wrist_yaw_joint", "left_wrist_pitch_joint",
    "right_shoulder_pitch_joint", "right_shoulder_roll_joint", "right_shoulder_yaw_joint",
    "right_elbow_joint", "right_wrist_roll_joint", "right_wrist_yaw_joint",
    "right_wrist_pitch_joint",
]  # fmt: skip

TRACKED_BODIES = [
    "base_link",
    "left_hip_roll_link", "left_knee_link", "left_ankle_roll_link",
    "right_hip_roll_link", "right_knee_link", "right_ankle_roll_link",
    "waist_yaw_link",
    "left_shoulder_roll_link", "left_elbow_link", "left_wrist_yaw_link",
    "right_shoulder_roll_link", "right_elbow_link", "right_wrist_yaw_link",
]  # fmt: skip

ROOT_BODY_NAME = "base_link"
TORSO_BODY_NAME = "waist_yaw_link"

# The MJCF ships explicit ``*_collision`` geoms, so UniLab can bind the friction
# randomisation directly.
COLLISION_GEOM_NAMES = (
    "left_ankle_pitch_collision", "left_elbow_collision", "left_foot_center_collision",
    "left_foot_inner_neg_collision", "left_foot_inner_pos_collision",
    "left_foot_outer_neg_collision", "left_foot_outer_pos_collision",
    "left_foot_toe_neg_collision", "left_foot_toe_pos_collision",
    "left_hip_pitch_collision", "left_hip_roll_collision", "left_hip_yaw_collision",
    "left_knee_lower_collision", "left_knee_upper_collision",
    "left_shoulder_pitch_collision", "left_shoulder_roll_collision", "left_shoulder_yaw_collision",
    "left_wrist_pitch_collision", "left_wrist_roll_collision", "left_wrist_yaw_collision",
    "right_ankle_pitch_collision", "right_elbow_collision", "right_foot_center_collision",
    "right_foot_inner_neg_collision", "right_foot_inner_pos_collision",
    "right_foot_outer_neg_collision", "right_foot_outer_pos_collision",
    "right_foot_toe_neg_collision", "right_foot_toe_pos_collision",
    "right_hip_pitch_collision", "right_hip_roll_collision", "right_hip_yaw_collision",
    "right_knee_lower_collision", "right_knee_upper_collision",
    "right_shoulder_pitch_collision", "right_shoulder_roll_collision",
    "right_shoulder_yaw_collision",
    "right_wrist_pitch_collision", "right_wrist_roll_collision", "right_wrist_yaw_collision",
    "torso_lower_collision", "torso_middle_collision", "torso_upper_collision",
    "waist_roll_neg_y_collision", "waist_roll_pos_y_collision",
)  # fmt: skip

# Position-servo gains written into rp1_supermimic.xml, scaled from G1 by torque:
# 140 N*m -> kp 90, 64 -> 45, 55 -> 45, 32 -> 25.  armature is defined so that
# _kp(armature) reproduces those gains, which keeps action_scale() meaningful.
_KP_BIG, _KP_MID, _KP_SMALL = 90.0, 45.0, 25.0
_BIG = (140.0, 20.0, _KP_BIG / NATURAL_FREQ**2)
_MID = (55.0, 12.0, _KP_MID / NATURAL_FREQ**2)
_ANKLE = (64.0, 12.0, _KP_MID / NATURAL_FREQ**2)
_SMALL = (32.0, 20.0, _KP_SMALL / NATURAL_FREQ**2)

JOINT_MOTORS = {
    "hip_pitch": _BIG,
    "hip_roll": _BIG,
    "knee": _BIG,
    "waist_roll": _BIG,
    "waist_yaw": _BIG,
    "hip_yaw": _MID,
    "shoulder_pitch": _MID,
    "ankle_pitch": _ANKLE,
    "ankle_roll": _ANKLE,
    "shoulder_roll": _SMALL,
    "shoulder_yaw": _SMALL,
    "elbow": _SMALL,
    "wrist_roll": _SMALL,
    "wrist_yaw": _SMALL,
    "wrist_pitch": _SMALL,
}

# The stand keyframe is all zeros (straight legs, like G1), so the action centre
# is the zero pose.
DEFAULT_JOINT_POS: dict[str, float] = {}


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
