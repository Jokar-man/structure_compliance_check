"""
checker_slabs — Slab compliance checks (IFCore contract).

Checks:
  check_slab_thickness — EHE / Código Estructural — slab thickness:
                         floor slabs  100–200 mm
                         roof slabs   200–350 mm

Notes:
  - Non-structural slabs (finish, wood joist, live roof) are skipped.
  - IFC model lengths are in metres; converted to mm using _get_length_scale.
  - Roof slabs detected by "roof" in the slab name (case-insensitive).
"""

import sys
import ifcopenshell
import ifcopenshell.util.element


# Floor slab limits
MIN_THICKNESS_MM = 100
MAX_THICKNESS_MM = 200

# Roof slab limits
MIN_ROOF_THICKNESS_MM = 200
MAX_ROOF_THICKNESS_MM = 350


def _get_length_scale(model: ifcopenshell.file) -> float:
    """Returns factor to convert model length units → metres."""
    try:
        for assignment in model.by_type("IfcUnitAssignment"):
            for unit in assignment.Units:
                if hasattr(unit, "UnitType") and unit.UnitType == "LENGTHUNIT":
                    prefix_map = {"MILLI": 0.001, "CENTI": 0.01, "DECI": 0.1, "KILO": 1000.0}
                    if hasattr(unit, "Prefix") and unit.Prefix:
                        return prefix_map.get(unit.Prefix, 1.0)
                    return 1.0  # SI base METRE, no prefix
    except Exception:
        pass
    return 1.0


def _get_slab_thickness(slab, scale_to_mm: float):
    """Extract thickness and return value in mm.

    scale_to_mm = _get_length_scale(model) * 1000
    """
    material = ifcopenshell.util.element.get_material(slab)
    if material is not None:
        layer_set = None
        if material.is_a("IfcMaterialLayerSetUsage"):
            layer_set = material.ForLayerSet
        elif material.is_a("IfcMaterialLayerSet"):
            layer_set = material

        if layer_set is not None:
            total = sum(layer.LayerThickness for layer in layer_set.MaterialLayers)
            return round(total * scale_to_mm, 2)

    # Fallback: Qto
    for rel in slab.IsDefinedBy:
        if rel.is_a("IfcRelDefinesByProperties"):
            pset = rel.RelatingPropertyDefinition
            if pset.is_a("IfcElementQuantity") and "Slab" in (pset.Name or ""):
                for q in pset.Quantities:
                    if q.is_a("IfcQuantityLength") and q.Name in ("Width", "Depth", "Height"):
                        return round(q.LengthValue * scale_to_mm, 2)
    return None


def _get_storey_name(slab):
    """Get the building storey name for a slab."""
    storey = ifcopenshell.util.element.get_container(slab)
    if storey is not None and storey.is_a("IfcBuildingStorey"):
        return storey.Name or f"Storey (#{storey.id()})"
    return "Unknown Storey"


def check_slab_thickness(model):
    """EHE / Código Estructural — slab thickness by type:
      floor slabs: 100–200 mm
      roof slabs:  200–350 mm

    Skips non-structural slabs (finish, wood joist, live roof).
    Converts IFC model units to mm via IfcUnitAssignment.
    """
    scale_to_mm = _get_length_scale(model) * 1000
    results = []

    for slab in model.by_type("IfcSlab"):
        name = slab.Name or f"Slab #{slab.id()}"

        # Skip non-structural slab types
        name_lower = name.lower()
        if any(kw in name_lower for kw in ("finish", "wood joist", "live roof")):
            continue

        # Select limits based on slab type
        is_roof = "roof" in name_lower
        t_min = MIN_ROOF_THICKNESS_MM if is_roof else MIN_THICKNESS_MM
        t_max = MAX_ROOF_THICKNESS_MM if is_roof else MAX_THICKNESS_MM
        slab_type_label = "roof slab" if is_roof else "floor slab"

        storey = _get_storey_name(slab)
        thickness = _get_slab_thickness(slab, scale_to_mm)

        if thickness is None:
            check_status = "blocked"
            actual = None
            comment = "Thickness property not found in material layers or Qto"
        elif t_min <= thickness <= t_max:
            check_status = "pass"
            actual = f"{thickness:.0f} mm"
            comment = None
        else:
            check_status = "fail"
            actual = f"{thickness:.0f} mm"
            if thickness < t_min:
                comment = f"{slab_type_label.capitalize()} is {t_min - thickness:.0f} mm too thin"
            else:
                comment = f"{slab_type_label.capitalize()} is {thickness - t_max:.0f} mm too thick"

        results.append({
            "element_id":        getattr(slab, "GlobalId", None),
            "element_type":      "IfcSlab",
            "element_name":      f"{storey} / {name}",
            "element_name_long": f"{name} ({storey})",
            "check_status":      check_status,
            "actual_value":      actual,
            "required_value":    f"{t_min}–{t_max} mm ({slab_type_label})",
            "comment":           comment,
            "log":               None,
        })
    return results


if __name__ == "__main__":
    ifc_path = sys.argv[1] if len(sys.argv) > 1 else "data/01_Duplex_Apartment.ifc"
    print("Loading:", ifc_path)
    _model = ifcopenshell.open(ifc_path)
    print("Slabs:", len(list(_model.by_type("IfcSlab"))))

    _ICON = {"pass": "PASS", "fail": "FAIL", "warning": "WARN", "blocked": "BLKD", "log": "LOG "}
    for _fn in [check_slab_thickness]:
        print("\n" + "=" * 60)
        print(" ", _fn.__name__)
        print("=" * 60)
        for _row in _fn(_model):
            print(" ", "[" + _ICON.get(_row["check_status"], "?") + "]", _row["element_name"])
            if _row["actual_value"]:
                print("         actual   :", _row["actual_value"])
            if _row["required_value"]:
                print("         required :", _row["required_value"])
            if _row["comment"]:
                print("         comment  :", _row["comment"])
