"""AniBench v2 candidate public API.

The package root deliberately exposes only the non-aggregated v2 mechanics.
Withdrawn v1 scalar/rank APIs remain available only in repository history and
are not imported or distributed by the public v2 package.
"""

from .api import (
    assess_protocol_level1_v2,
    compile_protocol_capacity_v2,
    compile_trial_design_v2,
    optimize_protocol_design_v2,
    score_joint_information_v2,
)

__all__ = [
    "assess_protocol_level1_v2",
    "compile_protocol_capacity_v2",
    "compile_trial_design_v2",
    "optimize_protocol_design_v2",
    "score_joint_information_v2",
]
__version__ = "2.0.0rc1"
