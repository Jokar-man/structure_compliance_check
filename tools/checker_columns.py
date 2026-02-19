"""
checker_columns — Column compliance checks (IFCore contract).

Checks:
  check_column_min_dimension — EHE — smallest cross-section ≥ 250 mm
"""

import sys
from pathlib import Path

_BEAM_SRC = str(Path(__file__).resolve().parent.parent / "beam_check" / "src")
if _BEAM_SRC not in sys.path:
    sys.path.insert(0, _BEAM_SRC)

from ifc_checker import check_column_min_dimension as _raw_column_check


def _parse_line(line: str, required_value: str) -> dict:
    """Parse a '[PASS]/[FAIL]/[???] IfcColumn 'Name': detail' line → IFCore dict."""
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
        comment = f"Column too narrow — {actual}" if actual else "Check failed"
    elif check_status == "blocked":
        comment = actual or "Dimension data missing"

    return {
        "element_id":        None,
        "element_type":      "IfcColumn",
        "element_name":      element_name,
        "element_name_long": f"{element_name} (IfcColumn)" if element_name else None,
        "check_status":      check_status,
        "actual_value":      actual,
        "required_value":    required_value,
        "comment":           comment,
        "log":               None,
    }


def check_column_min_dimension(model, min_dim_mm=250):
    """EHE — smallest cross-section side of a column ≥ 250 mm."""
    lines = _raw_column_check(model, min_dim_mm=min_dim_mm)
    return [_parse_line(l, f"≥ {min_dim_mm} mm") for l in lines]
