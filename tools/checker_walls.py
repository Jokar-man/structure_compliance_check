"""
checker_walls — Wall compliance checks (IFCore contract).

Checks:
  check_wall_thickness  — DB SE-F / EHE — ≥ 100 mm
  check_wall_uvalue     — CTE DB HE — ≤ 0.80
  check_wall_external_uvalue — external walls must have U-value
"""

import sys
from pathlib import Path

# Add walls_check to path
_WALLS_DIR = str(Path(__file__).resolve().parent.parent / "walls_check")
if _WALLS_DIR not in sys.path:
    sys.path.insert(0, _WALLS_DIR)

from extractor import extract_walls
import rules as wall_rules


def _parse_wall_line(line: str, required_value: str = None) -> dict:
    """Parse a '[PASS]/[FAIL]/[???] IfcWall GID Name: detail' line → IFCore dict."""
    check_status = "blocked"
    if line.startswith("[PASS]"):
        check_status = "pass"
    elif line.startswith("[FAIL]"):
        check_status = "fail"

    body = line.split("] ", 1)[-1] if "] " in line else line
    parts = body.split(":", 1)
    element_desc = parts[0].strip()
    actual = parts[1].strip() if len(parts) > 1 else None

    # Extract from "IfcWall GID Name" format
    tokens = element_desc.split(" ", 2)
    element_type = tokens[0] if len(tokens) > 0 else None
    element_id = tokens[1] if len(tokens) > 1 else None
    element_name = tokens[2] if len(tokens) > 2 else element_desc

    comment = None
    if check_status == "fail":
        comment = f"Wall does not meet the requirement — {actual}" if actual else "Check failed"
    elif check_status == "blocked":
        comment = actual or "Property data missing"

    return {
        "element_id":        element_id,
        "element_type":      element_type or "IfcWall",
        "element_name":      element_name,
        "element_name_long": f"{element_name} ({element_type or 'IfcWall'})" if element_name else None,
        "check_status":      check_status,
        "actual_value":      actual,
        "required_value":    required_value,
        "comment":           comment,
        "log":               None,
    }


def check_wall_thickness(model, min_mm=100):
    """DB SE-F / EHE — load-bearing wall thickness ≥ 100 mm."""
    walls = extract_walls(model)
    lines = wall_rules.rule_min_thickness(walls, min_mm=min_mm)
    return [_parse_wall_line(l, required_value=f"≥ {min_mm} mm") for l in lines]


def check_wall_uvalue(model, max_u=0.80):
    """CTE DB HE — maximum thermal transmittance ≤ 0.80 W/(m²·K)."""
    walls = extract_walls(model)
    lines = wall_rules.rule_max_uvalue(walls, max_u=max_u)
    return [_parse_wall_line(l, required_value=f"≤ {max_u} W/(m²·K)") for l in lines]


def check_wall_external_uvalue(model):
    """External walls must have a U-value defined."""
    walls = extract_walls(model)
    lines = wall_rules.rule_external_walls_must_have_uvalue(walls)
    return [_parse_wall_line(l, required_value="U-value must be defined for external walls") for l in lines]
