"""
Slab Team Adapter — wraps slab_check/slab.py

Provides slab thickness compliance check.
"""

import ifcopenshell.util.element


MIN_THICKNESS_MM = 100
MAX_THICKNESS_MM = 200


def _get_slab_thickness(slab):
    """Extract total thickness (mm) from material layers or Qto."""
    material = ifcopenshell.util.element.get_material(slab)
    if material is not None:
        layer_set = None
        if material.is_a("IfcMaterialLayerSetUsage"):
            layer_set = material.ForLayerSet
        elif material.is_a("IfcMaterialLayerSet"):
            layer_set = material

        if layer_set is not None:
            total = sum(layer.LayerThickness for layer in layer_set.MaterialLayers)
            return round(total, 2)

    # Fallback: Qto
    for rel in slab.IsDefinedBy:
        if rel.is_a("IfcRelDefinesByProperties"):
            pset = rel.RelatingPropertyDefinition
            if pset.is_a("IfcElementQuantity") and "Slab" in (pset.Name or ""):
                for q in pset.Quantities:
                    if q.is_a("IfcQuantityLength") and q.Name in ("Width", "Depth", "Height"):
                        return round(q.LengthValue, 2)
    return None


def _get_storey_name(slab):
    """Get the building storey name for a slab."""
    storey = ifcopenshell.util.element.get_container(slab)
    if storey is not None and storey.is_a("IfcBuildingStorey"):
        return storey.Name or f"Storey (#{storey.id()})"
    return "Unknown Storey"


def check_slab_thickness(model):
    """Slab thickness must be between 100-200 mm."""
    results = []
    for slab in model.by_type("IfcSlab"):
        name = slab.Name or f"Slab #{slab.id()}"
        storey = _get_storey_name(slab)
        thickness = _get_slab_thickness(slab)

        if thickness is None:
            check_status = "blocked"
            actual = None
            comment = "Thickness not found in model data"
        elif MIN_THICKNESS_MM <= thickness <= MAX_THICKNESS_MM:
            check_status = "pass"
            actual = f"{thickness} mm"
            comment = None
        else:
            check_status = "fail"
            actual = f"{thickness} mm"
            if thickness < MIN_THICKNESS_MM:
                comment = f"Slab is {MIN_THICKNESS_MM - thickness:.0f} mm too thin"
            else:
                comment = f"Slab is {thickness - MAX_THICKNESS_MM:.0f} mm too thick"

        results.append({
            "element_id":        getattr(slab, "GlobalId", None),
            "element_type":      "IfcSlab",
            "element_name":      f"{storey} / {name}",
            "element_name_long": f"{name} ({storey})",
            "check_status":      check_status,
            "actual_value":      actual,
            "required_value":    f"{MIN_THICKNESS_MM}-{MAX_THICKNESS_MM} mm",
            "comment":           comment,
            "log":               None,
        })
    return results


# ── Team registration ────────────────────────────────────────

TEAM_NAME = "slabs"

TEAM_CHECKS = [
    {"name": f"Slab Thickness {MIN_THICKNESS_MM}-{MAX_THICKNESS_MM} mm", "fn": check_slab_thickness},
]
