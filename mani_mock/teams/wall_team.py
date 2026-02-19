"""
Wall Team Adapter - delegates to tools/checker_walls.py.

This keeps team-mode execution aligned with the IFCore checker implementation.
"""

import sys
from pathlib import Path

# Add tools/ to path
_TOOLS_DIR = str(Path(__file__).resolve().parent.parent.parent / "tools")
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from checker_walls import (  # noqa: E402
    check_wall_thickness as _check_wall_thickness,
    check_wall_uvalue as _check_wall_uvalue,
    check_wall_external_uvalue as _check_wall_external_uvalue,
)


def check_wall_thickness(model):
    """Minimum wall thickness >= 100 mm."""
    return _check_wall_thickness(model)


def check_wall_uvalue(model):
    """Maximum external-wall U-value <= 0.80 W/(m2.K)."""
    return _check_wall_uvalue(model)


def check_wall_external_uvalue(model):
    """External walls must have a U-value defined."""
    return _check_wall_external_uvalue(model)


TEAM_NAME = "walls"

TEAM_CHECKS = [
    {"name": "Wall Thickness >= 100 mm", "fn": check_wall_thickness},
    {"name": "Wall U-value <= 0.80", "fn": check_wall_uvalue},
    {"name": "External Walls Must Have U-value", "fn": check_wall_external_uvalue},
]
