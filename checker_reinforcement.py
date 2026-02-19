"""
checker_reinforcement — Reinforcement & foundation checks (IFCore contract).

Checks:
  check_ground_slab_thickness — ground floor slabs ≥ 150 mm
  check_foundations — foundation elements ≥ 200 mm
"""

import sys
from pathlib import Path

_REINF_SRC = str(Path(__file__).resolve().parent.parent / "reinforcement_check" / "src")
if _REINF_SRC not in sys.path:
    sys.path.insert(0, _REINF_SRC)

from ifc_analyzer import IFCAnalyzer


def check_ground_slab_thickness(model, min_thickness_mm=150):
    """Ground floor slabs must have adequate thickness (≥ 150 mm)."""
    results = []
    try:
        analyzer = IFCAnalyzer.__new__(IFCAnalyzer)
        analyzer.model = model
        analyzer.length_scale = analyzer._get_length_scale()

        ground_slabs = analyzer.get_ground_floor_slabs()
        for slab_info in ground_slabs:
            thickness = slab_info.get("thickness_mm")
            name = slab_info.get("name", "Unknown Slab")
            storey = slab_info.get("storey", "Unknown")

            if thickness is None:
                check_status = "blocked"
                actual = None
                comment = "Thickness property not found"
            elif thickness >= min_thickness_mm:
                check_status = "pass"
                actual = f"{thickness:.0f} mm"
                comment = None
            else:
                check_status = "fail"
                actual = f"{thickness:.0f} mm"
                comment = f"Ground slab is {min_thickness_mm - thickness:.0f} mm too thin"

            results.append({
                "element_id":        slab_info.get("global_id"),
                "element_type":      "IfcSlab",
                "element_name":      f"{storey} / {name}",
                "element_name_long": f"{name} ({storey})",
                "check_status":      check_status,
                "actual_value":      actual,
                "required_value":    f"≥ {min_thickness_mm} mm",
                "comment":           comment,
                "log":               None,
            })
    except Exception as e:
        results.append({
            "element_id":        None,
            "element_type":      "IfcSlab",
            "element_name":      "Analysis Error",
            "element_name_long": None,
            "check_status":      "blocked",
            "actual_value":      None,
            "required_value":    f"≥ {min_thickness_mm} mm",
            "comment":           f"Error during analysis: {e}",
            "log":               str(e),
        })
    return results


def check_foundations(model, min_thickness_mm=200):
    """Foundation elements should have thickness ≥ 200 mm."""
    results = []
    try:
        analyzer = IFCAnalyzer.__new__(IFCAnalyzer)
        analyzer.model = model
        analyzer.length_scale = analyzer._get_length_scale()

        foundations = analyzer.get_foundations()
        for fnd in foundations:
            thickness = fnd.get("thickness_mm")
            name = fnd.get("name", "Unknown Foundation")
            ifc_type = fnd.get("ifc_type", "IfcFooting")

            if thickness is None:
                check_status = "blocked"
                actual = None
                comment = "Thickness property not found"
            elif thickness >= min_thickness_mm:
                check_status = "pass"
                actual = f"{thickness:.0f} mm"
                comment = None
            else:
                check_status = "fail"
                actual = f"{thickness:.0f} mm"
                comment = f"Foundation is {min_thickness_mm - thickness:.0f} mm too thin"

            results.append({
                "element_id":        fnd.get("global_id"),
                "element_type":      ifc_type,
                "element_name":      name,
                "element_name_long": f"{name} ({ifc_type})",
                "check_status":      check_status,
                "actual_value":      actual,
                "required_value":    f"≥ {min_thickness_mm} mm",
                "comment":           comment,
                "log":               None,
            })
    except Exception as e:
        results.append({
            "element_id":        None,
            "element_type":      "IfcFooting",
            "element_name":      "Analysis Error",
            "element_name_long": None,
            "check_status":      "blocked",
            "actual_value":      None,
            "required_value":    f"≥ {min_thickness_mm} mm",
            "comment":           f"Error during analysis: {e}",
            "log":               str(e),
        })
    return results
