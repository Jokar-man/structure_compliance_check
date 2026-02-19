"""
checker_walls - Wall compliance checks (IFCore contract).

Checks:
  check_wall_thickness       - DB SE-F / EHE - >= 100 mm
  check_wall_uvalue          - CTE DB HE - external wall U-value <= 0.80 W/(m2.K)
  check_wall_external_uvalue - external walls must have U-value
"""

import sys
import ifcopenshell
import ifcopenshell.util.element


def _safe_float(value):
    try:
        return float(value) if value is not None else None
    except Exception:
        return None


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        low = value.strip().lower()
        if low in {"true", "t", "1", "yes", "y"}:
            return True
        if low in {"false", "f", "0", "no", "n"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return None


def _get_length_scale(model):
    """Returns factor to convert model length units to metres."""
    try:
        for assignment in model.by_type("IfcUnitAssignment"):
            for unit in assignment.Units:
                if getattr(unit, "UnitType", None) != "LENGTHUNIT":
                    continue
                prefix_map = {"MILLI": 0.001, "CENTI": 0.01, "DECI": 0.1, "KILO": 1000.0}
                prefix = getattr(unit, "Prefix", None)
                return prefix_map.get(prefix, 1.0)
    except Exception:
        pass
    return 1.0


def _get_wall_type(wall):
    for rel in getattr(wall, "IsDefinedBy", []) or []:
        if rel.is_a("IfcRelDefinesByType"):
            return rel.RelatingType
    return None


def _get_instance_and_type_psets(wall):
    wtype = _get_wall_type(wall)
    psets_inst = ifcopenshell.util.element.get_psets(wall) or {}
    psets_type = ifcopenshell.util.element.get_psets(wtype) or {} if wtype else {}
    return psets_inst, psets_type, wtype


def _get_container_storey(wall):
    try:
        container = ifcopenshell.util.element.get_container(wall)
        if container and container.is_a("IfcBuildingStorey"):
            return container.Name or f"Storey #{container.id()}"
    except Exception:
        pass
    return "Unknown Storey"


def _length_to_mm(value, scale):
    """Convert model/unit value to mm with fallback for already-mm custom properties."""
    raw = _safe_float(value)
    if raw is None:
        return None
    mm_from_model_units = raw * scale * 1000.0

    # Some authoring tools export custom pset values directly in mm.
    if mm_from_model_units > 5000.0 and 1.0 <= raw <= 5000.0:
        return raw
    if mm_from_model_units < 1.0 and 1.0 <= raw <= 5000.0:
        return raw
    return mm_from_model_units


def _extract_material_thickness_m(obj, scale):
    try:
        for rel in getattr(obj, "HasAssociations", []) or []:
            if not rel.is_a("IfcRelAssociatesMaterial"):
                continue
            mat = rel.RelatingMaterial
            if mat and mat.is_a("IfcMaterialLayerSetUsage"):
                layers = mat.ForLayerSet.MaterialLayers or []
                total = sum((_safe_float(layer.LayerThickness) or 0.0) for layer in layers)
                return (total * scale) if total > 0 else None
            if mat and mat.is_a("IfcMaterialLayerSet"):
                layers = mat.MaterialLayers or []
                total = sum((_safe_float(layer.LayerThickness) or 0.0) for layer in layers)
                return (total * scale) if total > 0 else None
    except Exception:
        pass
    return None


def _get_wall_thickness_mm(wall, scale):
    psets_inst, psets_type, wtype = _get_instance_and_type_psets(wall)
    qtos = ifcopenshell.util.element.get_psets(wall, qtos_only=True) or {}

    # Priority chain:
    # 1) quantity sets
    # 2) instance psets
    # 3) type psets
    # 4) material layers (instance, then type)
    qset = {}
    qset_name = None
    for name in ["Qto_WallBaseQuantities", "BaseQuantities", "Dimensions"]:
        if name in qtos:
            qset = qtos[name] or {}
            qset_name = name
            break

    for key in ["Width", "Thickness"]:
        value = _length_to_mm(qset.get(key), scale)
        if value is not None:
            return value, f"QTO:{qset_name}.{key}"

    for pset_name in ["Pset_WallCommon", "Construction", "Dimensions"]:
        pset = psets_inst.get(pset_name) or {}
        for key in ["Width", "Thickness"]:
            value = _length_to_mm(pset.get(key), scale)
            if value is not None:
                return value, f"PSET:{pset_name}.{key}"

    for pset_name in ["Pset_WallCommon", "Construction", "Dimensions"]:
        pset = psets_type.get(pset_name) or {}
        for key in ["Width", "Thickness"]:
            value = _length_to_mm(pset.get(key), scale)
            if value is not None:
                return value, f"TYPE_PSET:{pset_name}.{key}"

    value_m = _extract_material_thickness_m(wall, scale)
    if value_m is not None:
        return value_m * 1000.0, "MAT:instance_layers"

    if wtype:
        value_m = _extract_material_thickness_m(wtype, scale)
        if value_m is not None:
            return value_m * 1000.0, "MAT:type_layers"

    return None, "NOT_FOUND"


def _extract_uvalue_from_psets(psets):
    # Prioritize the standard property location, then scan all psets.
    wc = psets.get("Pset_WallCommon") or {}
    for key in ["ThermalTransmittance", "UValue", "U-value"]:
        value = _safe_float(wc.get(key))
        if value is not None:
            return value, f"Pset_WallCommon.{key}"

    for pset_name, props in psets.items():
        if not isinstance(props, dict):
            continue
        for key in ["ThermalTransmittance", "UValue", "U-value"]:
            value = _safe_float(props.get(key))
            if value is not None:
                return value, f"{pset_name}.{key}"
    return None, "NOT_FOUND"


def _get_wall_uvalue(wall):
    psets_inst, psets_type, _ = _get_instance_and_type_psets(wall)
    value, source = _extract_uvalue_from_psets(psets_inst)
    if value is not None:
        return value, f"instance:{source}"
    value, source = _extract_uvalue_from_psets(psets_type)
    if value is not None:
        return value, f"type:{source}"
    return None, "NOT_FOUND"


def _is_external(wall):
    psets_inst, psets_type, _ = _get_instance_and_type_psets(wall)

    for psets, source in ((psets_inst, "instance"), (psets_type, "type")):
        wc = psets.get("Pset_WallCommon") or {}
        value = _as_bool(wc.get("IsExternal"))
        if value is not None:
            return value, f"{source}:Pset_WallCommon.IsExternal"

    for psets, source in ((psets_inst, "instance"), (psets_type, "type")):
        for pset_name, props in psets.items():
            if not isinstance(props, dict):
                continue
            value = _as_bool(props.get("IsExternal"))
            if value is not None:
                return value, f"{source}:{pset_name}.IsExternal"

    return None, "NOT_FOUND"


def _all_walls(model):
    walls = []
    seen = set()
    for wall in list(model.by_type("IfcWall")) + list(model.by_type("IfcWallStandardCase")):
        wall_id = wall.id() if hasattr(wall, "id") else id(wall)
        if wall_id in seen:
            continue
        seen.add(wall_id)
        walls.append(wall)
    return walls


def check_wall_thickness(model, min_mm=100):
    """DB SE-F / EHE - load-bearing wall thickness >= 100 mm."""
    scale = _get_length_scale(model)
    results = []
    for wall in _all_walls(model):
        name = wall.Name or f"IfcWall #{wall.id()}"
        storey = _get_container_storey(wall)
        thickness_mm, source = _get_wall_thickness_mm(wall, scale)

        if thickness_mm is None:
            status = "blocked"
            comment = (
                "Thickness not found in Qto_WallBaseQuantities, Pset_WallCommon/Construction/Dimensions, "
                "or material layers"
            )
            actual = None
        elif thickness_mm < float(min_mm):
            status = "fail"
            comment = f"Wall {thickness_mm:.1f} mm < minimum {min_mm} mm"
            actual = f"{thickness_mm:.1f} mm"
        else:
            status = "pass"
            comment = f"DB SE-F satisfied: {thickness_mm:.1f} mm >= {min_mm} mm"
            actual = f"{thickness_mm:.1f} mm"

        results.append(
            {
                "element_id": wall.GlobalId,
                "element_type": wall.is_a(),
                "element_name": f"{storey} / {name}",
                "element_name_long": f"{name} ({storey}) - DB SE-F Wall Thickness",
                "check_status": status,
                "actual_value": actual,
                "required_value": f">= {min_mm} mm",
                "comment": comment,
                "log": f"scale_to_m={scale} thickness_source={source}",
            }
        )
    return results


def check_wall_uvalue(model, max_u=0.80):
    """CTE DB HE - external wall U-value must be <= 0.80 W/(m2.K)."""
    results = []
    for wall in _all_walls(model):
        name = wall.Name or f"IfcWall #{wall.id()}"
        storey = _get_container_storey(wall)
        is_external, ext_source = _is_external(wall)
        u_value, u_source = _get_wall_uvalue(wall)

        if is_external is False:
            status = "pass"
            comment = "Not an external wall; CTE DB HE U-value limit not applicable"
            actual = f"U={u_value:.3f} W/(m2.K)" if u_value is not None else None
        elif is_external is None and u_value is None:
            status = "blocked"
            comment = "Cannot determine IsExternal and no U-value found in wall property sets"
            actual = None
        elif is_external is None and u_value is not None:
            status = "warning"
            comment = "U-value found but IsExternal is unknown; verify whether CTE DB HE applies"
            actual = f"U={u_value:.3f} W/(m2.K)"
        elif u_value is None:
            status = "fail"
            comment = "External wall has no U-value; CTE DB HE requirement is not met"
            actual = None
        elif u_value > float(max_u):
            status = "fail"
            comment = f"U={u_value:.3f} W/(m2.K) exceeds maximum {max_u}"
            actual = f"U={u_value:.3f} W/(m2.K)"
        else:
            status = "pass"
            comment = f"CTE DB HE satisfied: U={u_value:.3f} <= {max_u} W/(m2.K)"
            actual = f"U={u_value:.3f} W/(m2.K)"

        results.append(
            {
                "element_id": wall.GlobalId,
                "element_type": wall.is_a(),
                "element_name": f"{storey} / {name}",
                "element_name_long": f"{name} ({storey}) - CTE DB HE U-value",
                "check_status": status,
                "actual_value": actual,
                "required_value": f"<= {max_u} W/(m2.K) for external walls",
                "comment": comment,
                "log": f"is_external={is_external} is_external_source={ext_source} u_source={u_source}",
            }
        )
    return results


def check_wall_external_uvalue(model):
    """External walls must have a U-value defined."""
    results = []
    for wall in _all_walls(model):
        name = wall.Name or f"IfcWall #{wall.id()}"
        storey = _get_container_storey(wall)
        is_external, ext_source = _is_external(wall)
        u_value, u_source = _get_wall_uvalue(wall)

        if is_external is True and u_value is None:
            status = "fail"
            comment = "External wall has no U-value (ThermalTransmittance/UValue)"
        elif is_external is True:
            status = "pass"
            comment = "External wall has a U-value"
        elif is_external is False:
            status = "pass"
            comment = "Not an external wall; U-value not required"
        else:
            status = "blocked"
            comment = "IsExternal flag not found; cannot determine whether U-value is required"

        results.append(
            {
                "element_id": wall.GlobalId,
                "element_type": wall.is_a(),
                "element_name": f"{storey} / {name}",
                "element_name_long": f"{name} ({storey}) - External U-value",
                "check_status": status,
                "actual_value": f"U={u_value:.3f} W/(m2.K)" if u_value is not None else None,
                "required_value": "U-value required for external walls",
                "comment": comment,
                "log": f"is_external={is_external} is_external_source={ext_source} u_source={u_source}",
            }
        )
    return results


if __name__ == "__main__":
    ifc_path = sys.argv[1] if len(sys.argv) > 1 else "data/01_Duplex_Apartment.ifc"
    print("Loading:", ifc_path)
    _model = ifcopenshell.open(ifc_path)
    print("Walls:", len(_all_walls(_model)))

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
