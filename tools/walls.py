"""Standalone IFC wall compliance checker (single-file version)."""

import argparse
import re
import unicodedata

import ifcopenshell
import ifcopenshell.util.element as element

try:
    import ifcopenshell.util.pset as pset
except ImportError:
    pset = None


QSET_CANDIDATES = ["Qto_WallBaseQuantities", "BaseQuantities", "Dimensions"]

CLIMATE_ZONE_U_LIMITS = {
    "A": 0.80,
    "B": 0.65,
    "C": 0.57,
    "D": 0.49,
    "E": 0.37,
}

SERVICE_SPACE_KEYWORDS = {
    "kitchen",
    "cocina",
    "bath",
    "bathroom",
    "toilet",
    "wc",
    "lavatory",
    "restroom",
    "aseo",
    "bano",
    "corridor",
    "hallway",
    "circulation",
    "pasillo",
    "pasadizo",
    "distribuidor",
}

GENERAL_SPACE_KEYWORDS = {
    "living",
    "salon",
    "sala",
    "comedor",
    "dining",
    "bedroom",
    "dormitorio",
    "habitacion",
    "room",
    "office",
    "study",
    "classroom",
}


# ----------------------------
# Extraction helpers
# ----------------------------

def safe_float(value):
    try:
        return float(value) if value is not None else None
    except:
        return None


def get_wall_type(wall):
    for rel in getattr(wall, "IsDefinedBy", []) or []:
        if rel.is_a("IfcRelDefinesByType"):
            return rel.RelatingType
    return None


def get_container_storey(wall):
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
        if isinstance(pset_name, str) and pset_name.strip():
            hints.append(pset_name.strip())

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

            if hasattr(mat, "Name") and mat.Name:
                out["MaterialName"] = mat.Name
                return out

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


def pick_thickness_mm(qset_name, q, psets_inst, psets_type, mat_inst, mat_type):
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
        mat_type = (
            extract_material_info(wtype)
            if wtype
            else {"MaterialName": None, "LayerNames": [], "LayerThicknesses": [], "TotalLayerThickness": None}
        )

        thickness_mm, thickness_src = pick_thickness_mm(qset_name, q, psets_inst, psets_type, mat_inst, mat_type)
        wc = psets_inst.get("Pset_WallCommon") or {}
        storey = get_container_storey(w)

        row = {
            "GlobalId": getattr(w, "GlobalId", None),
            "Name": getattr(w, "Name", None) or "Unnamed Wall",
            "IfcType": w.is_a(),
            "ObjectType": getattr(w, "ObjectType", None),
            "Tag": getattr(w, "Tag", None),
            "WallTypeName": getattr(wtype, "Name", None) if wtype else None,
            "WallTypeId": getattr(wtype, "GlobalId", None) if wtype and hasattr(wtype, "GlobalId") else None,
            **storey,
            "QSet": qset_name,
            "Length_mm": safe_float(q.get("Length")) if q else None,
            "Height_mm": safe_float(q.get("Height")) if q else None,
            "Area_m2": safe_float((q.get("GrossArea") or q.get("NetArea"))) if q else None,
            "Volume_m3": safe_float((q.get("GrossVolume") or q.get("NetVolume"))) if q else None,
            "Thickness_mm": thickness_mm,
            "ThicknessSource": thickness_src,
            "IsExternal": wc.get("IsExternal"),
            "LoadBearing": wc.get("LoadBearing"),
            "FireRating": wc.get("FireRating"),
            "ThermalTransmittance": wc.get("ThermalTransmittance"),
            "Material_Instance": mat_inst.get("MaterialName"),
            "Material_Type": mat_type.get("MaterialName"),
            "Layers_Instance": mat_inst.get("LayerNames"),
            "LayerThicknesses_Instance": mat_inst.get("LayerThicknesses"),
            "TotalLayerThickness_Instance": mat_inst.get("TotalLayerThickness"),
            "Layers_Type": mat_type.get("LayerNames"),
            "LayerThicknesses_Type": mat_type.get("LayerThicknesses"),
            "TotalLayerThickness_Type": mat_type.get("TotalLayerThickness"),
            "Psets_Instance": psets_inst,
            "Psets_Type": psets_type,
            "Qtos_All": get_qtos(w),
            "SpaceBoundaryCount": sb_count,
            "HasSpaceBoundary": sb_count > 0,
            "AdjacentSpaceNames": sb_space_names,
            "AdjacentSpaceIds": sb_space_ids,
            "AdjacentSpaceHints": sb_space_hints,
        }
        out.append(row)

    return out


# ----------------------------
# Rules
# ----------------------------

def _coerce_float(value):
    try:
        return float(value) if value is not None else None
    except:
        return None


def _is_true(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "t", "1", "yes"}
    return False


def _wall_label(w):
    gid = w.get("GlobalId", "NO_ID")
    name = w.get("Name", "Unnamed")
    return gid, name


def _normalize_text(value):
    if not isinstance(value, str):
        return ""
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _space_text_bucket(wall):
    texts = []
    for key in ("AdjacentSpaceNames", "AdjacentSpaceHints"):
        values = wall.get(key) or []
        for value in values:
            norm = _normalize_text(value)
            if norm:
                texts.append(norm)
    return list(dict.fromkeys(texts))


def _contains_keyword(text, keyword):
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def _classify_wall_space_context(wall):
    texts = _space_text_bucket(wall)
    has_service = False
    has_general = False
    for text in texts:
        if any(_contains_keyword(text, kw) for kw in SERVICE_SPACE_KEYWORDS):
            has_service = True
        if any(_contains_keyword(text, kw) for kw in GENERAL_SPACE_KEYWORDS):
            has_general = True
    return {
        "has_space_links": bool(wall.get("HasSpaceBoundary")),
        "has_service": has_service,
        "has_general": has_general,
    }


def rule_min_thickness(walls, min_mm=100):
    out = []
    for w in walls:
        t = _coerce_float(w.get("Thickness_mm"))
        gid, name = _wall_label(w)
        if t is None:
            out.append(f"[???] IfcWall {gid} {name}: thickness unknown (need Thickness_mm)")
        elif t < float(min_mm):
            out.append(f"[FAIL] IfcWall {gid} {name}: thickness={t:.1f}mm < {float(min_mm):.1f}mm")
        else:
            out.append(f"[PASS] IfcWall {gid} {name}: thickness={t:.1f}mm >= {float(min_mm):.1f}mm")
    return out


def rule_min_height(walls, min_height_mm=2500):
    out = []
    for w in walls:
        h = _coerce_float(w.get("Height_mm"))
        gid, name = _wall_label(w)
        if h is None:
            out.append(f"[???] IfcWall {gid} {name}: height unknown (need Height_mm)")
        elif h < float(min_height_mm):
            out.append(f"[FAIL] IfcWall {gid} {name}: height={h:.1f}mm < {float(min_height_mm):.1f}mm")
        else:
            out.append(f"[PASS] IfcWall {gid} {name}: height={h:.1f}mm >= {float(min_height_mm):.1f}mm")
    return out


def rule_min_height_by_space_use(walls, min_general_mm=2500, min_service_mm=2200):
    out = []
    for w in walls:
        h = _coerce_float(w.get("Height_mm"))
        gid, name = _wall_label(w)
        ctx = _classify_wall_space_context(w)

        if h is None:
            out.append(f"[???] IfcWall {gid} {name}: height unknown (need Height_mm)")
            continue

        if ctx["has_general"]:
            threshold = float(min_general_mm)
            reason = "general-space context"
        elif ctx["has_service"]:
            threshold = float(min_service_mm)
            reason = "service-space context (kitchen/bath/corridor)"
        else:
            if not ctx["has_space_links"]:
                if h >= float(min_general_mm):
                    out.append(
                        f"[PASS] IfcWall {gid} {name}: height={h:.1f}mm >= {float(min_general_mm):.1f}mm "
                        "(no IfcSpace link; used general limit)"
                    )
                elif h >= float(min_service_mm):
                    out.append(
                        f"[???] IfcWall {gid} {name}: height={h:.1f}mm between {float(min_service_mm):.1f}mm "
                        f"and {float(min_general_mm):.1f}mm (no IfcSpace link to infer room type)"
                    )
                else:
                    out.append(
                        f"[FAIL] IfcWall {gid} {name}: height={h:.1f}mm < {float(min_service_mm):.1f}mm "
                        "(below minimum even for service spaces)"
                    )
                continue

            threshold = float(min_general_mm)
            reason = "space linked but room type unclear"

        if h < threshold:
            out.append(f"[FAIL] IfcWall {gid} {name}: height={h:.1f}mm < {threshold:.1f}mm ({reason})")
        else:
            out.append(f"[PASS] IfcWall {gid} {name}: height={h:.1f}mm >= {threshold:.1f}mm ({reason})")
    return out


def rule_max_uvalue(walls, max_u=0.80):
    out = []
    for w in walls:
        u = _coerce_float(w.get("ThermalTransmittance"))
        gid, name = _wall_label(w)
        if u is None:
            out.append(f"[???] IfcWall {gid} {name}: U-value unknown")
        elif u > float(max_u):
            out.append(f"[FAIL] IfcWall {gid} {name}: U={u:.3f} > {float(max_u):.3f}")
        else:
            out.append(f"[PASS] IfcWall {gid} {name}: U={u:.3f} <= {float(max_u):.3f}")
    return out


def rule_external_uvalue_by_climate_zone(walls, climate_zone="A"):
    out = []
    zone = str(climate_zone).strip().upper()
    if zone not in CLIMATE_ZONE_U_LIMITS:
        return [f"[???] Invalid climate zone '{climate_zone}'. Expected one of: A, B, C, D, E."]

    limit = CLIMATE_ZONE_U_LIMITS[zone]
    for w in walls:
        gid, name = _wall_label(w)
        ext = _is_true(w.get("IsExternal"))
        u = _coerce_float(w.get("ThermalTransmittance"))

        if not ext:
            out.append(f"[PASS] IfcWall {gid} {name}: climate U-limit not applicable (IsExternal=False)")
            continue
        if u is None:
            out.append(f"[???] IfcWall {gid} {name}: external wall with unknown U-value for climate zone {zone}")
            continue
        if u > limit:
            out.append(f"[FAIL] IfcWall {gid} {name}: U={u:.3f} > U_lim({zone})={limit:.3f}")
        else:
            out.append(f"[PASS] IfcWall {gid} {name}: U={u:.3f} <= U_lim({zone})={limit:.3f}")
    return out


def rule_external_walls_must_have_uvalue(walls):
    out = []
    for w in walls:
        ext = _is_true(w.get("IsExternal"))
        u = _coerce_float(w.get("ThermalTransmittance"))
        gid, name = _wall_label(w)
        if ext and u is None:
            out.append(f"[FAIL] IfcWall {gid} {name}: IsExternal=True but U-value missing")
        else:
            out.append(f"[PASS] IfcWall {gid} {name}: external/U-value OK")
    return out


def rule_loadbearing_requires_fire_rating(walls):
    out = []
    for w in walls:
        lb = _is_true(w.get("LoadBearing"))
        fr = w.get("FireRating")
        gid, name = _wall_label(w)
        if not lb:
            out.append(f"[PASS] IfcWall {gid} {name}: fire rating check not applicable (LoadBearing=False)")
            continue
        if fr in (None, "", "Unknown"):
            out.append(f"[FAIL] IfcWall {gid} {name}: LoadBearing=True but FireRating missing")
        else:
            out.append(f"[PASS] IfcWall {gid} {name}: LoadBearing=True with FireRating={fr}")
    return out


def rule_space_boundary_linkage(walls):
    out = []
    for w in walls:
        has_boundary = bool(w.get("HasSpaceBoundary"))
        count = int(w.get("SpaceBoundaryCount") or 0)
        gid, name = _wall_label(w)
        if has_boundary:
            out.append(f"[PASS] IfcWall {gid} {name}: linked to spaces (IfcRelSpaceBoundary count={count})")
        else:
            out.append(f"[FAIL] IfcWall {gid} {name}: no IfcRelSpaceBoundary link")
    return out


# ----------------------------
# Report + orchestration
# ----------------------------

def make_report(walls, rule_results):
    lines = [f"Total walls: {len(walls)}", ""]
    lines.extend(rule_results)
    return lines


def summarize(lines):
    p_count = sum(1 for s in lines if s.startswith("[PASS]"))
    f_count = sum(1 for s in lines if s.startswith("[FAIL]"))
    u_count = sum(1 for s in lines if s.startswith("[???]"))
    return [f"[PASS] count={p_count}", f"[FAIL] count={f_count}", f"[???] count={u_count}"]


def _collect_rule_results(
    walls,
    min_mm=100,
    max_u=0.80,
    min_height_mm=2500,
    min_service_height_mm=2200,
    climate_zone=None,
    use_space_aware_height=True,
):
    results = []
    results += rule_min_thickness(walls, min_mm=min_mm)
    if use_space_aware_height:
        results += rule_min_height_by_space_use(
            walls,
            min_general_mm=min_height_mm,
            min_service_mm=min_service_height_mm,
        )
    else:
        results += rule_min_height(walls, min_height_mm=min_height_mm)

    if climate_zone:
        results += rule_external_uvalue_by_climate_zone(walls, climate_zone=climate_zone)
    else:
        results += rule_max_uvalue(walls, max_u=max_u)

    results += rule_external_walls_must_have_uvalue(walls)
    results += rule_loadbearing_requires_fire_rating(walls)
    results += rule_space_boundary_linkage(walls)
    return results


def run_wall_checks(
    ifc_path,
    min_mm=100,
    max_u=0.80,
    include_summary=True,
    min_height_mm=2500,
    min_service_height_mm=2200,
    climate_zone=None,
    use_space_aware_height=True,
):
    model = ifcopenshell.open(ifc_path)
    walls = extract_walls(model)
    results = _collect_rule_results(
        walls,
        min_mm=min_mm,
        max_u=max_u,
        min_height_mm=min_height_mm,
        min_service_height_mm=min_service_height_mm,
        climate_zone=climate_zone,
        use_space_aware_height=use_space_aware_height,
    )

    lines = make_report(walls, results)
    if include_summary:
        lines.append("")
        lines.extend(summarize(results))
    return lines


def run(
    ifc_path,
    min_mm=100,
    max_u=0.80,
    include_summary=True,
    min_height_mm=2500,
    min_service_height_mm=2200,
    climate_zone=None,
    use_space_aware_height=True,
):
    return run_wall_checks(
        ifc_path,
        min_mm=min_mm,
        max_u=max_u,
        include_summary=include_summary,
        min_height_mm=min_height_mm,
        min_service_height_mm=min_service_height_mm,
        climate_zone=climate_zone,
        use_space_aware_height=use_space_aware_height,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run IFC wall compliance checks (single-file tool).")
    parser.add_argument("ifc_path", help="Path to IFC file")
    parser.add_argument("--min-mm", type=float, default=100, help="Minimum wall thickness in mm")
    parser.add_argument("--max-u", type=float, default=0.80, help="Maximum wall U-value (W/m2K) for custom mode")
    parser.add_argument("--min-height-mm", type=float, default=2500, help="General minimum wall height in mm")
    parser.add_argument(
        "--min-service-height-mm",
        type=float,
        default=2200,
        help="Minimum wall height in service spaces (kitchen/bath/corridor) in mm",
    )
    parser.add_argument(
        "--climate-zone",
        default=None,
        help="Optional CTE climate zone for external walls (A, B, C, D, E). If set, overrides --max-u.",
    )
    parser.add_argument(
        "--disable-space-aware-height",
        action="store_true",
        help="Disable room-type-aware height logic and use only --min-height-mm.",
    )
    parser.add_argument("--no-summary", action="store_true", help="Disable summary counts at end of report")
    args = parser.parse_args()

    for line in run_wall_checks(
        args.ifc_path,
        min_mm=args.min_mm,
        max_u=args.max_u,
        include_summary=not args.no_summary,
        min_height_mm=args.min_height_mm,
        min_service_height_mm=args.min_service_height_mm,
        climate_zone=args.climate_zone,
        use_space_aware_height=not args.disable_space_aware_height,
    ):
        print(line)
