"""Register the G1 SuperMimic task with UniLab."""

from unilab.base import registry
from unilab.envs import ManagerBasedRlEnvCfg

from unisupermimic.tasks.motion_tracking.g1.supermimic.env import (
    SUPPORTED_BACKENDS,
    make_supermimic_env,
)

TASK_NAME = "G1SuperMimic"
# The RP1 port runs the same MDP under its own task name so both profiles can
# coexist (selected with SUPERMIMIC_ROBOT=rpo on the Python side).
TASK_NAMES = ["G1SuperMimic", "RP1SuperMimic", "RPOSuperMimic"]

for _task in TASK_NAMES:
    registry.register_env_config(_task, ManagerBasedRlEnvCfg)
    for _backend in SUPPORTED_BACKENDS:
        registry.register_env(_task, make_supermimic_env, sim_backend=_backend)

__all__ = ["TASK_NAME", "TASK_NAMES"]
