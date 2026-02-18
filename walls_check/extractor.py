"""
Extract all wall info from IFC and return:
list[dict] where each dict contains:
- identity + type
- placement + storey
- quantities + psets (instance + type)
- materials (incl. layers)
- canonical fields (Thickness_mm, Height_mm, Length_mm, U_value, FireRating, etc.) + sources
"""

import ifcopenshell.util.element as element
try:
    import ifcopenshell.util.pset as pset
except ImportError:
    pset = None


QSET_CANDIDATES = ["Qto_WallBaseQuantities", "BaseQuantities", "Dimensions"]


def safe_float(x):
    try:
        return float(x) if x is not None else None
    except:
        return None

def to_mm(value, length_unit_scale_to_mm=1.0):
    if value is None:
        return None
    try:
        return float(value) * length_unit_scale_to_mm
    except:
        return None

def get_length_scale_to_mm(model):
    # default: meters -> mm
    scale = 1000.0

    projects = model.by_type("IfcProject")
    if not projects or not projects[0].UnitsInContext:
        return scale

    units = projects[0].UnitsInContext.Units or []
    for u in units:
        if u.is_a("IfcSIUnit") and u.UnitType == "LENGTHUNIT":
            # If Prefix is MILLI, then base unit is mm already
            if getattr(u, "Prefix", None) == "MILLI":
                return 1.0
            return 1000.0
    return scale

def get_wall_type(wall):
    for rel in getattr(wall, "IsDefinedBy", []) or []:
        if rel.is_a("IfcRelDefinesByType"):
            return rel.RelatingType
    return None


def get_container_storey(wall):
    # IfcRelContainedInSpatialStructure
    try:
        container = element.get_container(wall)
        if container and container.is_a("IfcBuildingStorey"):
            return {
                "StoreyName": getattr(container, "Name", None),
                "StoreyGlobalId": getattr(container, "GlobalId", None),
                "StoreyElevation": getattr(container, "Elevation", None),
            }
    except:
        pass
    return {"StoreyName": None, "StoreyGlobalId": None, "StoreyElevation": None}


def get_psets(obj):
    if not obj:
        return {}

    if hasattr(element, "get_psets"):
        try:
            return element.get_psets(obj, psets_only=True) or {}
        except TypeError:
            # Older signatures may not accept psets_only/qtos_only.
            all_sets = element.get_psets(obj) or {}
            return {name: values for name, values in all_sets.items() if not str(name).startswith("Qto_")}

    if pset and hasattr(pset, "get_psets"):
        return pset.get_psets(obj) or {}

    return {}


def get_qtos(obj):
    if not obj:
        return {}

    if hasattr(element, "get_psets"):
        try:
            return element.get_psets(obj, qtos_only=True) or {}
        except TypeError:
            all_sets = element.get_psets(obj) or {}
            return {
                name: values
                for name, values in all_sets.items()
                if str(name).startswith("Qto_") or str(name) in QSET_CANDIDATES
            }

    if pset and hasattr(pset, "get_quantities"):
        return pset.get_quantities(obj) or {}

    return {}


def get_quantities(wall):
    qtos = get_qtos(wall)
    for name in QSET_CANDIDATES:
        if name in qtos:
            return name, qtos[name]
    return None, {}


def _space_usage_hints(space):
    hints = []
    for attr in ("Name", "LongName", "ObjectType", "Description"):
        value = getattr(space, attr, None)
        if isinstance(value, str) and value.strip():
            hints.append(value.strip())

    psets = get_psets(space)
    for pset_name, props in (psets or {}).items():
        if not isinstance(props, dict):
            continue
        for key in ("Reference", "Category", "OccupancyType", "RoomTag", "Function", "Usage"):
            value = props.get(key)
            if isinstance(value, str) and value.strip():
                hints.append(value.strip())
        # Keep pset name too; many tools encode usage in vendor pset names.
        if isinstance(pset_name, str) and pset_name.strip():
            hints.append(pset_name.strip())

    # Preserve order, remove duplicates.
    return list(dict.fromkeys(hints))


def get_space_boundary_data(model):
    data = {}

    rel_names = [
        "IfcRelSpaceBoundary",
        "IfcRelSpaceBoundary1stLevel",
        "IfcRelSpaceBoundary2ndLevel",
    ]

    for rel_name in rel_names:
        try:
            rels = model.by_type(rel_name) or []
        except:
            rels = []

        for rel in rels:
            wall = getattr(rel, "RelatedBuildingElement", None)
            if not wall:
                continue
            wid = wall.id() if hasattr(wall, "id") else id(wall)
            wall_data = data.setdefault(
                wid,
                {
                    "count": 0,
                    "space_names": [],
                    "space_ids": [],
                    "space_hints": [],
                },
            )
            wall_data["count"] += 1

            space = getattr(rel, "RelatingSpace", None)
            if space:
                sid = getattr(space, "GlobalId", None)
                sname = getattr(space, "Name", None)
                if sid and sid not in wall_data["space_ids"]:
                    wall_data["space_ids"].append(sid)
                if sname and sname not in wall_data["space_names"]:
                    wall_data["space_names"].append(sname)
                for hint in _space_usage_hints(space):
                    if hint not in wall_data["space_hints"]:
                        wall_data["space_hints"].append(hint)

    return data


def extract_material_info(obj):
    """
    Returns:
    {
      "MaterialName": str|None,
      "LayerNames": [..],
      "LayerThicknesses": [..],
      "TotalLayerThickness": float|None
    }
    Works for instance or type (pass wall or walltype).
    """
    out = {
        "MaterialName": None,
        "LayerNames": [],
        "LayerThicknesses": [],
        "TotalLayerThickness": None,
    }

    try:
        for rel in getattr(obj, "HasAssociations", []) or []:
            if not rel.is_a("IfcRelAssociatesMaterial"):
                continue

            mat = rel.RelatingMaterial

            # Simple IfcMaterial
            if hasattr(mat, "Name") and mat.Name:
                out["MaterialName"] = mat.Name
                return out

            # LayerSetUsage (common)
            if mat and mat.is_a("IfcMaterialLayerSetUsage"):
                ls = mat.ForLayerSet
                if ls and hasattr(ls, "MaterialLayers"):
                    total = 0.0
                    for layer in ls.MaterialLayers or []:
                        name = getattr(getattr(layer, "Material", None), "Name", None)
                        th = safe_float(getattr(layer, "LayerThickness", None))
                        if name:
                            out["LayerNames"].append(name)
                        if th is not None:
                            out["LayerThicknesses"].append(th)
                            total += th
                    out["TotalLayerThickness"] = total if out["LayerThicknesses"] else None
                    out["MaterialName"] = ", ".join(out["LayerNames"]) if out["LayerNames"] else None
                    return out

            # LayerSet (less common, but exists)
            if mat and mat.is_a("IfcMaterialLayerSet"):
                total = 0.0
                for layer in mat.MaterialLayers or []:
                    name = getattr(getattr(layer, "Material", None), "Name", None)
                    th = safe_float(getattr(layer, "LayerThickness", None))
                    if name:
                        out["LayerNames"].append(name)
                    if th is not None:
                        out["LayerThicknesses"].append(th)
                        total += th
                out["TotalLayerThickness"] = total if out["LayerThicknesses"] else None
                out["MaterialName"] = ", ".join(out["LayerNames"]) if out["LayerNames"] else None
                return out

    except:
        pass

    return out


def pick_thickness_mm(wall, qset_name, q, psets_inst, psets_type, mat_inst, mat_type):
    # Priority: QTO > instance psets > type psets > material layers (inst > type)
    # Note: In your IFC sample units are mm, and q.Width=95 is already mm.
    if q:
        for key in ["Width", "Thickness"]:
            v = safe_float(q.get(key))
            if v is not None:
                return v, f"QTO:{qset_name}.{key}"

    for pset_name in ["Pset_WallCommon", "Construction", "Dimensions"]:
        ps = psets_inst.get(pset_name) or {}
        for key in ["Width", "Thickness"]:
            v = safe_float(ps.get(key))
            if v is not None:
                return v, f"PSET:{pset_name}.{key}"

    for pset_name in ["Pset_WallCommon", "Construction", "Dimensions"]:
        ps = psets_type.get(pset_name) or {}
        for key in ["Width", "Thickness"]:
            v = safe_float(ps.get(key))
            if v is not None:
                return v, f"TYPE_PSET:{pset_name}.{key}"

    if mat_inst.get("TotalLayerThickness") is not None:
        return mat_inst["TotalLayerThickness"], "MAT:Instance LayerThickness sum"

    if mat_type.get("TotalLayerThickness") is not None:
        return mat_type["TotalLayerThickness"], "MAT:Type LayerThickness sum"

    return None, "NOT_FOUND"


def extract_walls(model):
    # IfcWall may already include IfcWallStandardCase (subtype), so dedupe by STEP id.
    walls = []
    seen_ids = set()
    for w in model.by_type("IfcWall") + model.by_type("IfcWallStandardCase"):
        wid = w.id() if hasattr(w, "id") else id(w)
        if wid in seen_ids:
            continue
        seen_ids.add(wid)
        walls.append(w)
    out = []
    space_boundary_data = get_space_boundary_data(model)

    for w in walls:
        wtype = get_wall_type(w)
        wall_id = w.id() if hasattr(w, "id") else id(w)
        sb_data = space_boundary_data.get(wall_id, {})
        sb_count = int(sb_data.get("count", 0))
        sb_space_names = list(sb_data.get("space_names", []))
        sb_space_ids = list(sb_data.get("space_ids", []))
        sb_space_hints = list(sb_data.get("space_hints", []))

        qset_name, q = get_quantities(w)
        psets_inst = get_psets(w)
        psets_type = get_psets(wtype) if wtype else {}

        mat_inst = extract_material_info(w)
        mat_type = extract_material_info(wtype) if wtype else {"MaterialName": None, "LayerNames": [], "LayerThicknesses": [], "TotalLayerThickness": None}

        thickness_mm, thickness_src = pick_thickness_mm(w, qset_name, q, psets_inst, psets_type, mat_inst, mat_type)

        wc = psets_inst.get("Pset_WallCommon") or {}
        storey = get_container_storey(w)

        row = {
            # identity
            "GlobalId": getattr(w, "GlobalId", None),
            "Name": getattr(w, "Name", None) or "Unnamed Wall",
            "IfcType": w.is_a(),
            "ObjectType": getattr(w, "ObjectType", None),
            "Tag": getattr(w, "Tag", None),

            # type
            "WallTypeName": getattr(wtype, "Name", None) if wtype else None,
            "WallTypeId": getattr(wtype, "GlobalId", None) if wtype and hasattr(wtype, "GlobalId") else None,

            # container/storey
            **storey,

            # quantities (raw + canonical)
            "QSet": qset_name,
            "Length_mm": safe_float(q.get("Length")) if q else None,
            "Height_mm": safe_float(q.get("Height")) if q else None,
            "Area_m2": safe_float((q.get("GrossArea") or q.get("NetArea"))) if q else None,
            "Volume_m3": safe_float((q.get("GrossVolume") or q.get("NetVolume"))) if q else None,

            # canonical thickness
            "Thickness_mm": thickness_mm,
            "ThicknessSource": thickness_src,

            # wall common
            "IsExternal": wc.get("IsExternal"),
            "LoadBearing": wc.get("LoadBearing"),
            "FireRating": wc.get("FireRating"),
            "ThermalTransmittance": wc.get("ThermalTransmittance"),

            # materials (instance + type)
            "Material_Instance": mat_inst.get("MaterialName"),
            "Material_Type": mat_type.get("MaterialName"),
            "Layers_Instance": mat_inst.get("LayerNames"),
            "LayerThicknesses_Instance": mat_inst.get("LayerThicknesses"),
            "TotalLayerThickness_Instance": mat_inst.get("TotalLayerThickness"),
            "Layers_Type": mat_type.get("LayerNames"),
            "LayerThicknesses_Type": mat_type.get("LayerThicknesses"),
            "TotalLayerThickness_Type": mat_type.get("TotalLayerThickness"),

            # raw for any future rules
            "Psets_Instance": psets_inst,
            "Psets_Type": psets_type,
            "Qtos_All": get_qtos(w),

            # IFC relationship quality
            "SpaceBoundaryCount": sb_count,
            "HasSpaceBoundary": sb_count > 0,
            "AdjacentSpaceNames": sb_space_names,
            "AdjacentSpaceIds": sb_space_ids,
            "AdjacentSpaceHints": sb_space_hints,
        }

        out.append(row)

    return out
