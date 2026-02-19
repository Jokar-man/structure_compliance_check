"""
Reinforcement Team Adapter — wraps reinforcement_check/src/ifc_analyzer.py

Provides ground-floor slab and foundation analysis checks.
"""

import sys
from pathlib import Path

_REINF_SRC = str(Path(__file__).resolve().parent.parent.parent / "reinforcement_check" / "src")
if _REINF_SRC not in sys.path:
    sys.path.insert(0, _REINF_SRC)

from ifc_analyzer import IFCAnalyzer


def check_ground_slab_thickness(model):
    """Ground floor slabs must have adequate thickness (>= 150 mm)."""
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
                comment = "Thickness not found in model data"
            elif thickness >= 150:
                check_status = "pass"
                actual = f"{thickness:.0f} mm"
                comment = None
            else:
                check_status = "fail"
                actual = f"{thickness:.0f} mm"
                comment = f"Slab is {150 - thickness:.0f} mm too thin"

            results.append({
                "element_id":        slab_info.get("global_id"),
                "element_type":      "IfcSlab",
                "element_name":      f"{storey} / {name}",
                "element_name_long": f"{name} ({storey})",
                "check_status":      check_status,
                "actual_value":      actual,
                "required_value":    ">= 150 mm",
                "comment":           comment,
                "log":               None,
            })
    except Exception as e:
        results.append({
            "element_id":        None,
            "element_type":      "IfcSlab",
            "element_name":      "Analysis Error",
            "element_name_long": "Analysis Error (ground slab)",
            "check_status":      "blocked",
            "actual_value":      None,
            "required_value":    ">= 150 mm",
            "comment":           str(e),
            "log":               None,
        })
    return results


def check_foundations(model):
    """Foundation elements should have thickness >= 200 mm."""
    results = []
    try:
        analyzer = IFCAnalyzer.__new__(IFCAnalyzer)
        analyzer.model = model
        analyzer.length_scale = analyzer._get_length_scale()

        foundations = analyzer.get_foundations()
        for fnd in foundations:
            thickness = fnd.get("thickness_mm")
            name = fnd.get("name", "Unknown Foundation")

            if thickness is None:
                check_status = "blocked"
                actual = None
                comment = "Thickness not found in model data"
            elif thickness >= 200:
                check_status = "pass"
                actual = f"{thickness:.0f} mm"
                comment = None
            else:
                check_status = "fail"
                actual = f"{thickness:.0f} mm"
                comment = f"Foundation is {200 - thickness:.0f} mm too thin"

            results.append({
                "element_id":        fnd.get("global_id"),
                "element_type":      fnd.get("ifc_type", "IfcFooting"),
                "element_name":      name,
                "element_name_long": name,
                "check_status":      check_status,
                "actual_value":      actual,
                "required_value":    ">= 200 mm",
                "comment":           comment,
                "log":               None,
            })
    except Exception as e:
        results.append({
            "element_id":        None,
            "element_type":      "IfcFooting",
            "element_name":      "Analysis Error",
            "element_name_long": "Analysis Error (foundations)",
            "check_status":      "blocked",
            "actual_value":      None,
            "required_value":    ">= 200 mm",
            "comment":           str(e),
            "log":               None,
        })
    return results


# ── Team registration ────────────────────────────────────────

TEAM_NAME = "reinforcement"

TEAM_CHECKS = [
    {"name": "Ground Floor Slab Thickness >= 150 mm", "fn": check_ground_slab_thickness},
    {"name": "Foundation Thickness >= 200 mm",         "fn": check_foundations},
]
