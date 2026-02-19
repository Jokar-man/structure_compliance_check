"""
checker_accessibility — Door, window, opening, corridor, room, stair, railing checks.

All checks follow DB SUA and Catalan Decree 141/2012 accessibility requirements.
Follows the IFCore contract: check_*(model) → list[dict].

Checks:
  check_door_width          — DB SUA Annex A — ≥ 800 mm
  check_window_height       — Decree 141/2012 — ≥ 1200 mm
  check_opening_height      — DB SUA 2 §1.1 — ≥ 2000 mm
  check_corridor_width      — DB SUA Annex A — ≥ 1100 mm
  check_room_area           — Decree 141/2012 — ≥ 5 m²
  check_room_ceiling_height — DB SUA 2 / Decree 141/2012 — ≥ 2200 mm
  check_stair_riser_tread   — DB SUA 1 §4.2.1 — riser 130–185 mm, tread ≥ 280 mm
  check_railing_height      — DB SUA 1 §3.2.1 — ≥ 900 mm
"""

import sys
from pathlib import Path

_BEAM_SRC = str(Path(__file__).resolve().parent.parent / "beam_check" / "src")
if _BEAM_SRC not in sys.path:
    sys.path.insert(0, _BEAM_SRC)

from ifc_checker import (
    check_door_width as _raw_door_width,
    check_window_height as _raw_window_height,
    check_opening_height as _raw_opening_height,
    check_corridor_width as _raw_corridor_width,
    check_room_area as _raw_room_area,
    check_room_ceiling_height as _raw_room_ceiling_height,
    check_stair_riser_tread as _raw_stair_riser_tread,
    check_railing_height as _raw_railing_height,
)


def _parse_line(line: str, element_type: str, required_value: str) -> dict:
    """Parse a '[PASS]/[FAIL]/[???] Element: detail' line → IFCore dict."""
    check_status = "blocked"
    if line.startswith("[PASS]"):
        check_status = "pass"
    elif line.startswith("[FAIL]"):
        check_status = "fail"

    body = line.split("] ", 1)[-1] if "] " in line else line
    parts = body.split(":", 1)
    element_desc = parts[0].strip()
    actual = parts[1].strip() if len(parts) > 1 else None

    element_name = element_desc
    if "'" in element_desc:
        element_name = element_desc.split("'")[1] if len(element_desc.split("'")) > 1 else element_desc

    comment = None
    if check_status == "fail":
        comment = f"Does not meet requirement — {actual}" if actual else "Check failed"
    elif check_status == "blocked":
        comment = actual or "Property data missing"

    return {
        "element_id":        None,
        "element_type":      element_type,
        "element_name":      element_name,
        "element_name_long": f"{element_name} ({element_type})" if element_name else None,
        "check_status":      check_status,
        "actual_value":      actual,
        "required_value":    required_value,
        "comment":           comment,
        "log":               None,
    }


def _wrap(raw_fn, element_type, required_value):
    """Wrap a raw list[str] checker → IFCore list[dict] checker."""
    def wrapped(model):
        lines = raw_fn(model)
        return [_parse_line(l, element_type, required_value) for l in lines]
    wrapped.__name__ = raw_fn.__name__
    wrapped.__doc__ = raw_fn.__doc__
    return wrapped


# ── Exported check_* functions ──────────────────────────────

check_door_width = _wrap(
    _raw_door_width, "IfcDoor", "≥ 800 mm"
)

check_window_height = _wrap(
    _raw_window_height, "IfcWindow", "≥ 1200 mm"
)

check_opening_height = _wrap(
    _raw_opening_height, "IfcOpeningElement", "≥ 2000 mm"
)

check_corridor_width = _wrap(
    _raw_corridor_width, "IfcSpace", "≥ 1100 mm"
)

check_room_area = _wrap(
    _raw_room_area, "IfcSpace", "≥ 5 m²"
)

check_room_ceiling_height = _wrap(
    _raw_room_ceiling_height, "IfcSpace", "≥ 2200 mm"
)

check_stair_riser_tread = _wrap(
    _raw_stair_riser_tread, "IfcStairFlight", "riser 130–185 mm, tread ≥ 280 mm"
)

check_railing_height = _wrap(
    _raw_railing_height, "IfcRailing", "≥ 900 mm"
)
