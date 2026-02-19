"""
checker_walls — Wall compliance checks (IFCore contract).

Checks:
  check_wall_thickness       — DB SE-F / EHE — ≥ 100 mm
  check_wall_uvalue          — CTE DB HE — ≤ 0.80 W/(m²·K)
  check_wall_external_uvalue — external walls must have U-value
"""

import sys
import ifcopenshell
import ifcopenshell.util.element


# ── Private helpers ────────────────────────────────────────────────────────────

def _safe_float(x):
    try:
        return float(x) if x is not None else None
    except Exception:
        return None


def _get_wall_type(wall):
    for rel in getattr(wall, "IsDefinedBy", []) or []:
        if rel.is_a("IfcRelDefinesByType"):
            return rel.RelatingType
    return None


def _get_container_storey(wall):
    try:
        container = ifcopenshell.util.element.get_container(wall)
        if container and container.is_a("IfcBuildingStorey"):
            return container.Name or f"Storey #{container.id()}"
    except Exception:
        pass
    return "Unknown Storey"


def _extract_material_thickness(obj):
    try:
        for rel in getattr(obj, "HasAssociations", []) or []:
            if not rel.is_a("IfcRelAssociatesMaterial"):
                continue
            mat = rel.RelatingMaterial
            if mat and mat.is_a("IfcMaterialLayerSetUsage"):
                layers = mat.ForLayerSet.MaterialLayers
                total = sum(_safe_float(l.LayerThickness) or 0.0 for l in layers)
                return total if total > 0 else None
            if mat and mat.is_a("IfcMaterialLayerSet"):
                total = sum(_safe_float(l.LayerThickness) or 0.0 for l in mat.MaterialLayers)
                return total if total > 0 else None
    except Exception:
        pass
    return None


def _get_wall_thickness(wall):
    wtype = _get_wall_type(wall)
    psets_inst = ifcopenshell.util.element.get_psets(wall) or {}
    psets_type = ifcopenshell.util.element.get_psets(wtype) or {} if wtype else {}
    qtos = ifcopenshell.util.element.get_psets(wall, qtos_only=True) or {}

    # Priority: QTO → instance psets → type psets → material layers
    q = {}
    for name in ["Qto_WallBaseQuantities", "BaseQuantities", "Dimensions"]:
        if name in qtos:
            q = qtos[name]
            break

    for key in ["Width", "Thickness"]:
        v = _safe_float(q.get(key))
        if v is not None:
            return v

    for pset_name in ["Pset_WallCommon", "Construction", "Dimensions"]:
        for src in [psets_inst, psets_type]:
            ps = src.get(pset_name) or {}
            for key in ["Width", "Thickness"]:
                v = _safe_float(ps.get(key))
                if v is not None:
                    return v

    v = _extract_material_thickness(wall)
    if v is not None:
        return v
    if wtype:
        v = _extract_material_thickness(wtype)
        if v is not None:
            return v
    return None


def _get_wall_uvalue(wall):
    psets = ifcopenshell.util.element.get_psets(wall) or {}
    wc = psets.get("Pset_WallCommon") or {}
    return _safe_float(wc.get("ThermalTransmittance"))


def _is_external(wall):
    psets = ifcopenshell.util.element.get_psets(wall) or {}
    wc = psets.get("Pset_WallCommon") or {}
    return wc.get("IsExternal")


def _all_walls(model):
    return list(model.by_type("IfcWall")) + list(model.by_type("IfcWallStandardCase"))


# ── Check functions (IFCore contract) ─────────────────────────────────────────

def check_wall_thickness(model, min_mm=100):
    """DB SE-F / EHE — load-bearing wall thickness ≥ 100 mm."""
    results = []
    for wall in _all_walls(model):
        name = wall.Name or f"IfcWall #{wall.id()}"
        storey = _get_container_storey(wall)
        thickness = _get_wall_thickness(wall)

        if thickness is None:
            status = "blocked"
            comment = "Thickness not found in Qto, Pset_WallCommon, or material layers"
            actual = None
        elif thickness < min_mm:
            status = "fail"
            comment = f"Wall {thickness:.1f} mm < minimum {min_mm} mm"
            actual = f"{thickness:.1f} mm"
        else:
            status = "pass"
            comment = f"DB SE-F satisfied: {thickness:.1f} mm ≥ {min_mm} mm"
            actual = f"{thickness:.1f} mm"

        results.append({
            "element_id":        wall.GlobalId,
            "element_type":      wall.is_a(),
            "element_name":      f"{storey} / {name}",
            "element_name_long": f"{name} ({storey}) — DB SE-F Wall Thickness",
            "check_status":      status,
            "actual_value":      actual,
            "required_value":    f"≥ {min_mm} mm",
            "comment":           comment,
            "log":               None,
        })
    return results


def check_wall_uvalue(model, max_u=0.80):
    """CTE DB HE — maximum thermal transmittance ≤ 0.80 W/(m²·K)."""
    results = []
    for wall in _all_walls(model):
        name = wall.Name or f"IfcWall #{wall.id()}"
        storey = _get_container_storey(wall)
        u = _get_wall_uvalue(wall)

        if u is None:
            status = "blocked"
            comment = "U-value (ThermalTransmittance) not set in Pset_WallCommon"
            actual = None
        elif u > max_u:
            status = "fail"
            comment = f"U={u:.3f} W/(m²·K) exceeds maximum {max_u}"
            actual = f"{u:.3f} W/(m²·K)"
        else:
            status = "pass"
            comment = f"CTE DB HE satisfied: U={u:.3f} ≤ {max_u} W/(m²·K)"
            actual = f"{u:.3f} W/(m²·K)"

        results.append({
            "element_id":        wall.GlobalId,
            "element_type":      wall.is_a(),
            "element_name":      f"{storey} / {name}",
            "element_name_long": f"{name} ({storey}) — CTE DB HE U-value",
            "check_status":      status,
            "actual_value":      actual,
            "required_value":    f"≤ {max_u} W/(m²·K)",
            "comment":           comment,
            "log":               None,
        })
    return results


def check_wall_external_uvalue(model):
    """External walls must have a U-value defined."""
    results = []
    for wall in _all_walls(model):
        name = wall.Name or f"IfcWall #{wall.id()}"
        storey = _get_container_storey(wall)
        ext = _is_external(wall)
        u = _get_wall_uvalue(wall)

        if ext is True and u is None:
            status = "fail"
            comment = "External wall has no U-value (ThermalTransmittance) in Pset_WallCommon"
        else:
            status = "pass"
            comment = "External/U-value requirement satisfied"

        results.append({
            "element_id":        wall.GlobalId,
            "element_type":      wall.is_a(),
            "element_name":      f"{storey} / {name}",
            "element_name_long": f"{name} ({storey}) — External U-value",
            "check_status":      status,
            "actual_value":      f"U={u:.3f}" if u is not None else None,
            "required_value":    "U-value required for external walls",
            "comment":           comment,
            "log":               f"IsExternal={ext}",
        })
    return results


if __name__ == "__main__":
    ifc_path = sys.argv[1] if len(sys.argv) > 1 else "data/01_Duplex_Apartment.ifc"
    print("Loading:", ifc_path)
    _model = ifcopenshell.open(ifc_path)
    print("Walls:", len(list(_model.by_type("IfcWall"))))

    _ICON = {"pass": "PASS", "fail": "FAIL", "warning": "WARN", "blocked": "BLKD", "log": "LOG "}
    for _fn in [check_wall_thickness, check_wall_uvalue, check_wall_external_uvalue]:
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
