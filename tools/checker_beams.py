"""
checker_beams — Beam compliance checks (IFCore contract).

Checks:
  check_beam_depth — EHE / DB SE — beam depth ≥ 200 mm
  check_beam_width — EHE / DB SE — beam width ≥ 150 mm
"""

import sys
import ifcopenshell
import ifcopenshell.util.element


# ── Private helpers ────────────────────────────────────────────────────────────

def _get_pset_value(elem, pset_name, prop_name):
    try:
        psets = ifcopenshell.util.element.get_psets(elem)
        if pset_name in psets and prop_name in psets[pset_name]:
            v = psets[pset_name][prop_name]
            if v is not None and v != "":
                return v
    except Exception:
        pass
    return None


def _search_psets(elem, prop_name):
    try:
        psets = ifcopenshell.util.element.get_psets(elem)
        for props in psets.values():
            if isinstance(props, dict) and prop_name in props:
                v = props[prop_name]
                if v is not None and v != "" and isinstance(v, (int, float)):
                    return v
    except Exception:
        pass
    return None


def _to_mm(value):
    if value is None:
        return None
    return round(value) if value > 100 else round(value * 1000)


# ── Check functions (IFCore contract) ─────────────────────────────────────────

def check_beam_depth(model, min_depth_mm=200):
    """EHE / DB SE — beam depth ≥ 200 mm."""
    results = []
    for beam in model.by_type("IfcBeam"):
        name = beam.Name or f"IfcBeam #{beam.id()}"
        depth = (
            _get_pset_value(beam, "PSet_Revit_Type_Dimensions", "d")
            or _get_pset_value(beam, "Qto_BeamBaseQuantities", "Depth")
            or _get_pset_value(beam, "Pset_BeamCommon", "Depth")
            or _search_psets(beam, "d")
        )
        if depth is not None:
            depth_mm = _to_mm(depth)
            status = "pass" if depth_mm >= min_depth_mm else "fail"
            comment = (f"EHE/DB SE satisfied: {depth_mm} mm ≥ {min_depth_mm} mm"
                       if status == "pass"
                       else f"Depth {depth_mm} mm < minimum {min_depth_mm} mm")
            actual = f"{depth_mm} mm"
        else:
            status = "blocked"
            comment = "Depth not found in PSet_Revit_Type_Dimensions.d, Qto_BeamBaseQuantities.Depth, or Pset_BeamCommon"
            actual = None

        results.append({
            "element_id":        beam.GlobalId,
            "element_type":      "IfcBeam",
            "element_name":      name,
            "element_name_long": f"{name} — EHE Beam Depth",
            "check_status":      status,
            "actual_value":      actual,
            "required_value":    f"≥ {min_depth_mm} mm",
            "comment":           comment,
            "log":               None,
        })
    return results


def check_beam_width(model, min_width_mm=150):
    """EHE / DB SE — beam width (flange) ≥ 150 mm."""
    results = []
    for beam in model.by_type("IfcBeam"):
        name = beam.Name or f"IfcBeam #{beam.id()}"
        width = (
            _get_pset_value(beam, "PSet_Revit_Type_Dimensions", "bf")
            or _get_pset_value(beam, "PSet_Revit_Type_Dimensions", "tw")
            or _get_pset_value(beam, "Qto_BeamBaseQuantities", "Width")
            or _get_pset_value(beam, "Pset_BeamCommon", "Width")
        )
        if width is not None:
            width_mm = _to_mm(width)
            status = "pass" if width_mm >= min_width_mm else "fail"
            comment = (f"EHE/DB SE satisfied: {width_mm} mm ≥ {min_width_mm} mm"
                       if status == "pass"
                       else f"Width {width_mm} mm < minimum {min_width_mm} mm")
            actual = f"{width_mm} mm"
        else:
            status = "blocked"
            comment = "Width not found in PSet_Revit_Type_Dimensions.bf/tw, Qto_BeamBaseQuantities.Width, or Pset_BeamCommon"
            actual = None

        results.append({
            "element_id":        beam.GlobalId,
            "element_type":      "IfcBeam",
            "element_name":      name,
            "element_name_long": f"{name} — EHE Beam Width",
            "check_status":      status,
            "actual_value":      actual,
            "required_value":    f"≥ {min_width_mm} mm",
            "comment":           comment,
            "log":               None,
        })
    return results


if __name__ == "__main__":
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
