"""
Column Team Adapter — wraps column checks from beam_check/src/ifc_checker.py

Provides column dimension compliance check.
"""

import sys
from pathlib import Path

_BEAM_SRC = str(Path(__file__).resolve().parent.parent.parent / "beam_check" / "src")
if _BEAM_SRC not in sys.path:
    sys.path.insert(0, _BEAM_SRC)

from ifc_checker import check_column_min_dimension


def _parse_result_line(line: str) -> dict:
    """Parse a '[PASS]/[FAIL]/[???] IfcType 'Name': detail' line."""
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

    element_type = "IfcColumn"
    element_name = element_desc
    if "'" in element_desc:
        element_type = element_desc.split("'")[0].strip() or "IfcColumn"
        element_name = element_desc.split("'")[1] if len(element_desc.split("'")) > 1 else element_desc

    comment = None
    if check_status == "fail":
        comment = actual
    elif check_status == "blocked":
        comment = actual or "Dimensions unknown"

    return {
        "element_id":        None,
        "element_type":      element_type,
        "element_name":      element_name,
        "element_name_long": element_name,
        "check_status":      check_status,
        "actual_value":      actual,
        "required_value":    ">= 250 mm",
        "comment":           comment,
        "log":               None,
    }


def check_columns(model):
    """Column smallest cross-section >= 250 mm."""
    lines = check_column_min_dimension(model)
    return [_parse_result_line(l) for l in lines]


# ── Team registration ────────────────────────────────────────

TEAM_NAME = "columns"

TEAM_CHECKS = [
    {"name": "Column Min Dimension >= 250 mm", "fn": check_columns},
]
