"""
Accessibility Team Adapter — wraps door/window/opening/corridor/room/stair/railing
checks from beam_check/src/ifc_checker.py

These checks cover DB SUA and Catalan Decree 141/2012 accessibility requirements.
"""

import sys
from pathlib import Path

_BEAM_SRC = str(Path(__file__).resolve().parent.parent.parent / "beam_check" / "src")
if _BEAM_SRC not in sys.path:
    sys.path.insert(0, _BEAM_SRC)

from ifc_checker import (
    check_door_width,
    check_window_height,
    check_opening_height,
    check_corridor_width,
    check_room_area,
    check_room_ceiling_height,
    check_stair_riser_tread,
    check_railing_height,
)


def _parse_result_line(line: str, required_value: str = None, default_type: str = None) -> dict:
    """Parse a '[PASS]/[FAIL]/[???]' line into an IFCore result dict."""
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

    element_type = default_type
    element_name = element_desc
    if "'" in element_desc:
        element_type = element_desc.split("'")[0].strip() or default_type
        element_name = element_desc.split("'")[1] if len(element_desc.split("'")) > 1 else element_desc

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


def _wrap(fn, name, required_value, default_type=None):
    def wrapped(model):
        return [_parse_result_line(l, required_value, default_type) for l in fn(model)]
    wrapped.__name__ = name
    return wrapped


# ── Team registration ────────────────────────────────────────

TEAM_NAME = "accessibility"

TEAM_CHECKS = [
    {"name": "Door Width >= 800 mm",             "fn": _wrap(check_door_width,         "door_width",        ">= 800 mm",  "IfcDoor")},
    {"name": "Window Height >= 1200 mm",         "fn": _wrap(check_window_height,      "window_height",     ">= 1200 mm", "IfcWindow")},
    {"name": "Opening Height >= 2000 mm",        "fn": _wrap(check_opening_height,     "opening_height",    ">= 2000 mm", "IfcOpeningElement")},
    {"name": "Corridor Width >= 1100 mm",        "fn": _wrap(check_corridor_width,     "corridor_width",    ">= 1100 mm", "IfcSpace")},
    {"name": "Room Area >= 5 m2",                "fn": _wrap(check_room_area,          "room_area",         ">= 5 m2",    "IfcSpace")},
    {"name": "Ceiling Height >= 2200 mm",        "fn": _wrap(check_room_ceiling_height,"ceiling_height",    ">= 2200 mm", "IfcSpace")},
    {"name": "Stair Riser/Tread (130-185/>=280)","fn": _wrap(check_stair_riser_tread,  "stair_riser_tread", "riser 130-185 mm, tread >= 280 mm", "IfcStairFlight")},
    {"name": "Railing Height >= 900 mm",         "fn": _wrap(check_railing_height,     "railing_height",    ">= 900 mm",  "IfcRailing")},
]
