"""
Beam Team Adapter — wraps beam_check/src/ifc_checker.py

Provides all beam-related compliance checks from the existing module.
"""

import sys
from pathlib import Path

# Add beam_check/src to path so we can import ifc_checker
_BEAM_SRC = str(Path(__file__).resolve().parent.parent.parent / "beam_check" / "src")
if _BEAM_SRC not in sys.path:
    sys.path.insert(0, _BEAM_SRC)

from ifc_checker import (
    check_beam_depth,
    check_beam_width,
)


# ── Adapter: convert [PASS]/[FAIL]/[???] text lines → dicts ─

def _parse_result_line(line: str, required_value: str = None) -> dict:
    """Parse a '[PASS] Element: value (min X)' line into an IFCore dict."""
    if line.startswith("[PASS]"):
        check_status = "pass"
    elif line.startswith("[FAIL]"):
        check_status = "fail"
    else:
        check_status = "blocked"

    # Extract element info after '] '
    body = line.split("] ", 1)[-1] if "] " in line else line
    parts = body.split(":", 1)
    element_desc = parts[0].strip()
    actual = parts[1].strip() if len(parts) > 1 else ""

    # Try to extract element type and name from "IfcType 'Name'" format
    element_type = "IfcBeam"
    element_name = element_desc
    if "'" in element_desc:
        type_part = element_desc.split("'")[0].strip()
        name_part = element_desc.split("'")[1] if len(element_desc.split("'")) > 1 else element_desc
        element_type = type_part or "IfcBeam"
        element_name = name_part

    comment = None
    if check_status == "fail":
        comment = actual
    elif check_status == "blocked":
        comment = actual or "Property missing"

    return {
        "element_id":        None,
        "element_type":      element_type,
        "element_name":      element_name,
        "element_name_long": element_name,
        "check_status":      check_status,
        "actual_value":      actual,
        "required_value":    required_value,
        "comment":           comment,
        "log":               None,
    }


def _wrap_check(check_fn, check_name, required_value):
    """Wrap an existing check function to return list[dict] with IFCore fields."""
    def wrapped(model):
        lines = check_fn(model)
        return [_parse_result_line(line, required_value) for line in lines]
    wrapped.__name__ = check_name
    return wrapped


# ── Team registration ────────────────────────────────────────

TEAM_NAME = "beams"

TEAM_CHECKS = [
    {"name": "Beam Depth >= 200 mm",    "fn": _wrap_check(check_beam_depth, "beam_depth", ">= 200 mm")},
    {"name": "Beam Width >= 150 mm",    "fn": _wrap_check(check_beam_width, "beam_width", ">= 150 mm")},
]
