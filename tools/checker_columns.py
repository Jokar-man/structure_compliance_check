"""
checker_columns — Column compliance checks (IFCore contract).

Checks:
  check_column_min_dimension — EHE — smallest cross-section ≥ 250 mm
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


def _to_mm(value):
    if value is None:
        return None
    return round(value) if value > 100 else round(value * 1000)


# ── Check functions (IFCore contract) ─────────────────────────────────────────

def check_column_min_dimension(model, min_dim_mm=250):
    """EHE — smallest cross-section side of a column ≥ 250 mm."""
    results = []
    for col in model.by_type("IfcColumn"):
        name = col.Name or f"IfcColumn #{col.id()}"
        w = (
            _get_pset_value(col, "PSet_Revit_Type_Dimensions", "b")
            or _get_pset_value(col, "PSet_Revit_Type_Dimensions", "bf")
            or _get_pset_value(col, "Qto_ColumnBaseQuantities", "Width")
        )
        d = (
            _get_pset_value(col, "PSet_Revit_Type_Dimensions", "d")
            or _get_pset_value(col, "PSet_Revit_Type_Dimensions", "h")
            or _get_pset_value(col, "Qto_ColumnBaseQuantities", "Depth")
        )

        smallest = None
        if w is not None and d is not None:
            smallest = min(_to_mm(w), _to_mm(d))
        elif w is not None:
            smallest = _to_mm(w)
        elif d is not None:
            smallest = _to_mm(d)

        if smallest is not None:
            status = "pass" if smallest >= min_dim_mm else "fail"
            comment = (f"EHE satisfied: {smallest} mm ≥ {min_dim_mm} mm"
                       if status == "pass"
                       else f"Column too narrow: {smallest} mm < minimum {min_dim_mm} mm")
            actual = f"{smallest} mm"
        else:
            status = "blocked"
            comment = "Dimensions not found in PSet_Revit_Type_Dimensions or Qto_ColumnBaseQuantities"
            actual = None

        results.append({
            "element_id":        col.GlobalId,
            "element_type":      "IfcColumn",
            "element_name":      name,
            "element_name_long": f"{name} — EHE Column Min Dimension",
            "check_status":      status,
            "actual_value":      actual,
            "required_value":    f"≥ {min_dim_mm} mm",
            "comment":           comment,
            "log":               None,
        })
    return results


if __name__ == "__main__":
    ifc_path = sys.argv[1] if len(sys.argv) > 1 else "data/01_Duplex_Apartment.ifc"
    print("Loading:", ifc_path)
    _model = ifcopenshell.open(ifc_path)
    print("Columns:", len(list(_model.by_type("IfcColumn"))))

    _ICON = {"pass": "PASS", "fail": "FAIL", "warning": "WARN", "blocked": "BLKD", "log": "LOG "}
    for _fn in [check_column_min_dimension]:
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
