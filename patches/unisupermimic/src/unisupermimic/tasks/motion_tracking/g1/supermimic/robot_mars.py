"""Roboparty/small-biped Mars_v3 (MuJoCo model ``mars_v3``): 6 actuated DoF.

A 2.19 kg, ~0.25 m point-foot biped: 3 joints per leg, **no ankle, no arms**.

Layout (MJCF document order, also the order GMR's ``bvh_lafan1_to_mars_v3.json``
writes into):

    abad_L, hip_L, knee_L, abad_R, hip_R, knee_R

``hip_L`` rotates about +y and ``hip_R`` about -y (mirrored), the knees both about
-y, so a positive knee angle flexes both legs the same way.
"""

from __future__ import annotations

import re

NATURAL_FREQ = 10 * 2.0 * 3.1415926535
DAMPING_RATIO = 2.0


def _kp(armature: float) -> float:
    return armature * NATURAL_FREQ**2


def _kd(armature: float) -> float:
    return 2.0 * DAMPING_RATIO * armature * NATURAL_FREQ


# Name kept identical to the G1/RPO/RP1 modules so shared call sites keep working.
G1_JOINT_NAMES = [
    "abad_L_joint", "hip_L_joint", "knee_L_joint",
    "abad_R_joint", "hip_R_joint", "knee_R_joint",
]  # fmt: skip

# MJCF actuator names are "<joint>_motor".
ACTUATOR_NAMES = [f"{n[:-6]}_motor" for n in G1_JOINT_NAMES]

# Only 7 bodies exist.  No ankle, so the foot is tracked by position only in the
# retargeting config; here it is a normal tracked body.
TRACKED_BODIES = [
    "base_link",
    "hip_L_Link", "knee_L_Link", "foot_L_Link",
    "hip_R_Link", "knee_R_Link", "foot_R_Link",
]  # fmt: skip

ROOT_BODY_NAME = "base_link"
# No separate torso: the base box *is* the torso.
TORSO_BODY_NAME = "base_link"

COLLISION_GEOM_NAMES = (
    "base_collision",
    "foot_L_Link_collision_mesh", "foot_R_Link_collision_mesh",
)  # fmt: skip

# 12 N*m / 12 rad/s at every joint.  The MJCF servo gains are kp=40, kv=2.5; the
# armature below is what makes action_scale() agree with them.
_KP = 40.0
_ARM = _KP / NATURAL_FREQ**2
_KD = 2.5

JOINT_MOTORS = {
    "abad_L": (12.0, 12.0, _ARM),
    "hip_L": (12.0, 12.0, _ARM),
    "knee_L": (12.0, 12.0, _ARM),
    "abad_R": (12.0, 12.0, _ARM),
    "hip_R": (12.0, 12.0, _ARM),
    "knee_R": (12.0, 12.0, _ARM),
}

# The stand keyframe is a crouch (hip -+0.3, knee -0.5): with a 0.25 m leg a
# straight-leg pose leaves no room for the servo to push, so start from the
# crouch the CAD team shipped.
DEFAULT_JOINT_POS: dict[str, float] = {
    r"abad_[LR]_joint": 0.0,
    r"hip_L_joint": -0.3,
    r"hip_R_joint": 0.3,
    r"knee_[LR]_joint": -0.5,
}

# A quarter-size robot needs a tighter reward bandwidth, otherwise the position
# Gaussian (std 0.3 m = the whole robot) saturates and stops discriminating.
REWARD_OVERRIDES = {
    "body_pos_std": 0.09,
    "root_pos_std": 0.09,
    "body_linvel_std": 0.4,
    "body_angvel_std": 3.14,
}


def motor_of(joint_name: str) -> tuple[float, float, float]:
    key = joint_name.replace("_joint", "")
    return JOINT_MOTORS[key]


def action_scale(joint_name: str) -> float:
    effort, _, armature = motor_of(joint_name)
    # One action unit asks for the full 12 N*m at zero tracking error
    # (kp * scale == effort).  G1/RP1 use 0.25 because their servos are stiffer
    # relative to their torque limits; Mars needs the authority.
    return 1.0 * effort / _kp(armature)


def default_joint_pos_list() -> list[float]:
    positions = []
    for name in G1_JOINT_NAMES:
        value = 0.0
        for pattern, position in DEFAULT_JOINT_POS.items():
            if re.fullmatch(pattern, name):
                value = position
        positions.append(value)
    return positions
