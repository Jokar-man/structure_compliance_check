"""
checker_beams — Beam compliance checks (IFCore contract).

Checks:
  check_beam_depth — EHE / DB SE — beam depth ≥ 200 mm
  check_beam_width — EHE / DB SE — beam width ≥ 150 mm
"""

import sys
from pathlib import Path

_BEAM_SRC = str(Path(__file__).resolve().parent.parent / "beam_check" / "src")
if _BEAM_SRC not in sys.path:
    sys.path.insert(0, _BEAM_SRC)

from ifc_checker import (
    check_beam_depth as _raw_beam_depth,
    check_beam_width as _raw_beam_width,
)


def _parse_line(line: str, element_type: str, required_value: str) -> dict:
    """Parse a '[PASS]/[FAIL]/[???] IfcType 'Name': detail' line → IFCore dict."""
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
        comment = f"Below minimum — {actual}" if actual else "Check failed"
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


def check_beam_depth(model, min_depth_mm=200):
    """EHE / DB SE — beam depth ≥ 200 mm."""
    lines = _raw_beam_depth(model, min_depth_mm=min_depth_mm)
    return [_parse_line(l, "IfcBeam", f"≥ {min_depth_mm} mm") for l in lines]


def check_beam_width(model, min_width_mm=150):
    """EHE / DB SE — beam width (flange) ≥ 150 mm."""
    lines = _raw_beam_width(model, min_width_mm=min_width_mm)
    return [_parse_line(l, "IfcBeam", f"≥ {min_width_mm} mm") for l in lines]


if __name__ == "__main__":
    import ifcopenshell
    ifc_path = sys.argv[1] if len(sys.argv) > 1 else "data/01_Duplex_Apartment.ifc"
    print("Loading:", ifc_path)
    _model = ifcopenshell.open(ifc_path)
    print("Beams:", len(list(_model.by_type("IfcBeam"))))

    _ICON = {"pass": "PASS", "fail": "FAIL", "warning": "WARN", "blocked": "BLKD", "log": "LOG "}
    for _fn in [check_beam_depth, check_beam_width]:
        print("\n" + "=" * 60)
        print(" ", _fn.__name__)
        print("=" * 60)
        for _row in _fn(_model):
            print(" ", "[" + _ICON.get(_row["check_status"], "?") + "]", _row["element_name"])
            if _row["actual_value"]:
                print("         actual   :", _row["actual_value"])
            if _row["required_value"]:
                print("         required :", _row["required_value"])
            print("         comment  :", _row["comment"])
