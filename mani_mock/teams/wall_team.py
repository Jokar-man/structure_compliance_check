"""
Wall Team Adapter — wraps walls_check/ (extractor → rules → report)

Provides wall compliance checks: thickness, U-value, external wall validation.
"""

import sys
from pathlib import Path

# Add walls_check to path
_WALLS_DIR = str(Path(__file__).resolve().parent.parent.parent / "walls_check")
if _WALLS_DIR not in sys.path:
    sys.path.insert(0, _WALLS_DIR)

from extractor import extract_walls
import rules as wall_rules


def _parse_result_line(line: str, required_value: str = None) -> dict:
    """Parse a '[PASS]/[FAIL]/[???] IfcWall GID Name: detail' line."""
    if line.startswith("[PASS]"):
        check_status = "pass"
    elif line.startswith("[FAIL]"):
        check_status = "fail"
    else:
        check_status = "blocked"

    body = line.split("] ", 1)[-1] if "] " in line else line
    parts = body.split(":", 1)
    element_desc = parts[0].strip()
    actual = parts[1].strip() if len(parts) > 1 else ""

    # Extract from "IfcWall GID Name" format
    tokens = element_desc.split(" ", 2)
    element_type = tokens[0] if len(tokens) > 0 else None
    element_id = tokens[1] if len(tokens) > 1 else None
    element_name = tokens[2] if len(tokens) > 2 else element_desc

    comment = None
    if check_status == "fail":
        comment = actual
    elif check_status == "blocked":
        comment = actual or "Property missing"

    return {
        "element_id":        element_id,
        "element_type":      element_type,
        "element_name":      element_name,
        "element_name_long": f"{element_name} ({element_id})" if element_id else element_name,
        "check_status":      check_status,
        "actual_value":      actual,
        "required_value":    required_value,
        "comment":           comment,
        "log":               None,
    }


def check_wall_thickness(model):
    """Minimum wall thickness >= 100 mm."""
    walls = extract_walls(model)
    lines = wall_rules.rule_min_thickness(walls, min_mm=100)
    return [_parse_result_line(l, ">= 100 mm") for l in lines]


def check_wall_uvalue(model):
    """Maximum U-value <= 0.80."""
    walls = extract_walls(model)
    lines = wall_rules.rule_max_uvalue(walls, max_u=0.80)
    return [_parse_result_line(l, "<= 0.80") for l in lines]


def check_wall_external_uvalue(model):
    """External walls must have a U-value defined."""
    walls = extract_walls(model)
    lines = wall_rules.rule_external_walls_must_have_uvalue(walls)
    return [_parse_result_line(l, "U-value required for external walls") for l in lines]


# ── Team registration ────────────────────────────────────────

TEAM_NAME = "walls"

TEAM_CHECKS = [
    {"name": "Wall Thickness >= 100 mm",           "fn": check_wall_thickness},
    {"name": "Wall U-value <= 0.80",               "fn": check_wall_uvalue},
    {"name": "External Walls Must Have U-value",   "fn": check_wall_external_uvalue},
]
