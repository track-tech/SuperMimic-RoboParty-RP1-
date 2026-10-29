#!/usr/bin/env python
"""Build a LAFAN1 -> Mars_v3 IK config and register the robot in GMR.

Mars_v3 is a 6-DoF point-foot biped (2.19 kg, ~0.25 m leg): 3 joints per leg
(abad/hip/knee) and **no ankle, no arms**.  So the full-body 14-body template
cannot apply; we track only what exists:

    base_link   <- Hips        (orientation only, like G1's pelvis)
    hip_L/R     <- Left/RightUpLeg
    knee_L/R    <- Left/RightLeg
    foot_L/R    <- Left/RightFootMod   (position only - no ankle to match orientation)

The human skeleton is scaled by ~0.28 so the pelvis lands at ~0.25 m.
"""

import json
import os

GMR = "/root/gpufree-data/mars/ext/GMR"
CFG = os.path.join(GMR, "general_motion_retargeting/ik_configs/bvh_lafan1_to_mars_v3.json")

SCALE = 0.28
# rot offsets copied from the G1 config where the body frame plays the same role
ROT_LEG = [-0.5, 0.5, 0.5, -0.5]
ROT_FOOT = [-0.70710678, 0.70710678, 0.0, 0.0]
ROT_ROOT = [0.5, 0.5, 0.5, 0.5]

table1 = {
    "base_link": ["Hips", 0, 10, [0.0, 0.0, 0.0], ROT_ROOT],
    "hip_L_Link": ["LeftUpLeg", 0, 10, [0.0, 0.0, 0.0], ROT_LEG],
    "knee_L_Link": ["LeftLeg", 0, 10, [0.0, 0.0, 0.0], ROT_LEG],
    "foot_L_Link": ["LeftFootMod", 50, 0, [0.0, 0.0, 0.0], ROT_FOOT],
    "hip_R_Link": ["RightUpLeg", 0, 10, [0.0, 0.0, 0.0], ROT_LEG],
    "knee_R_Link": ["RightLeg", 0, 10, [0.0, 0.0, 0.0], ROT_LEG],
    "foot_R_Link": ["RightFootMod", 50, 0, [0.0, 0.0, 0.0], ROT_FOOT],
}
table2 = {
    "base_link": ["Hips", 100, 10, [0.0, 0.0, 0.0], ROT_ROOT],
    "hip_L_Link": ["LeftUpLeg", 10, 5, [0.0, 0.0, 0.0], ROT_LEG],
    "knee_L_Link": ["LeftLeg", 10, 5, [0.0, 0.0, 0.0], ROT_LEG],
    "foot_L_Link": ["LeftFootMod", 50, 0, [0.0, 0.0, 0.0], ROT_FOOT],
    "hip_R_Link": ["RightUpLeg", 10, 5, [0.0, 0.0, 0.0], ROT_LEG],
    "knee_R_Link": ["RightLeg", 10, 5, [0.0, 0.0, 0.0], ROT_LEG],
    "foot_R_Link": ["RightFootMod", 50, 0, [0.0, 0.0, 0.0], ROT_FOOT],
}

cfg = {
    "robot_root_name": "base_link",
    "human_root_name": "Hips",
    "ground_height": 0.0,
    "human_height_assumption": 1.75,   # matches lafan1.py's hardcoded 1.75 -> ratio 1.0
    "use_ik_match_table1": True,
    "use_ik_match_table2": True,
    "human_scale_table": {
        # NOTE: this table is also the body *filter* - scale_human_data drops every
        # body that is not listed, and offset_human_data then indexes rot_offsets by
        # the surviving names. So only list bodies that are also task targets,
        # otherwise you get KeyError: 'LeftToe'.
        "Hips": SCALE,
        "LeftUpLeg": SCALE, "RightUpLeg": SCALE,
        "LeftLeg": SCALE, "RightLeg": SCALE,
        "LeftFootMod": SCALE, "RightFootMod": SCALE,
    },
    "ik_match_table1": table1,
    "ik_match_table2": table2,
}
with open(CFG, "w") as f:
    json.dump(cfg, f, indent=4)
print("wrote", CFG)

# --- register in params.py ---
p = os.path.join(GMR, "general_motion_retargeting/params.py")
t = open(p, encoding="utf-8").read()
if '"mars_v3"' not in t:
    t = t.replace('    "rp1": ASSET_ROOT / "rp1" / "rp1_supermimic.xml",',
                  '    "rp1": ASSET_ROOT / "rp1" / "rp1_supermimic.xml",\n'
                  '    "mars_v3": ASSET_ROOT / "mars_v3" / "mars_v3.xml",')
    t = t.replace('        "rp1": IK_CONFIG_ROOT / "bvh_lafan1_to_rp1.json",',
                  '        "rp1": IK_CONFIG_ROOT / "bvh_lafan1_to_rp1.json",\n'
                  '        "mars_v3": IK_CONFIG_ROOT / "bvh_lafan1_to_mars_v3.json",')
    t = t.replace('    "rp1": "base_link",',
                  '    "rp1": "base_link",\n    "mars_v3": "base_link",')
    t = t.replace('    "rp1": 2.0,', '    "rp1": 2.0,\n    "mars_v3": 0.8,')
    open(p, "w", encoding="utf-8").write(t)
    print("registered mars_v3 in params.py")
else:
    print("already registered")
