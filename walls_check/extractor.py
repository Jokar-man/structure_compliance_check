import ifcopenshell
import ifcopenshell.util.pset as pset

QSET_CANDIDATES = ["Qto_WallBaseQuantities", "BaseQuantities", "Dimensions"]

def safe_float(x):
    try:
        return float(x) if x is not None else None
    except:
        return None

def get_wall_type(wall):
    for rel in getattr(wall, "IsDefinedBy", []) or []:
        if rel.is_a("IfcRelDefinesByType"):
            return rel.RelatingType
    return None

def get_quantities(wall):
    qtos = pset.get_quantities(wall) or {}
    # return the first available qset dict
    for name in QSET_CANDIDATES:
        if name in qtos:
            return name, qtos[name]
    return None, {}

def wall_thickness_m(wall):
    # 1) QTO width
    qname, q = get_quantities(wall)
    w = safe_float(q.get("Width"))
    if w is not None:
        return w, f"QTO:{qname}.Width"

    # 2) Pset common
    psets = pset.get_psets(wall) or {}
    for key in ["Thickness", "Width"]:
        v = safe_float((psets.get("Pset_WallCommon") or {}).get(key))
        if v is not None:
            return v, f"PSET:Pset_WallCommon.{key}"

    # 3) Type layers
    wtype = get_wall_type(wall)
    if wtype:
        for rel in getattr(wtype, "HasAssociations", []) or []:
            if rel.is_a("IfcRelAssociatesMaterial"):
                mat = rel.RelatingMaterial
                if mat and mat.is_a("IfcMaterialLayerSet"):
                    total = 0.0
                    for layer in mat.MaterialLayers or []:
                        if layer.LayerThickness is not None:
                            total += float(layer.LayerThickness)
                    if total > 0:
                        return total, "TYPE:IfcMaterialLayerSet sum(LayerThickness)"

                if mat and mat.is_a("IfcMaterialLayerSetUsage"):
                    ls = mat.ForLayerSet
                    if ls and ls.is_a("IfcMaterialLayerSet"):
                        total = 0.0
                        for layer in ls.MaterialLayers or []:
                            if layer.LayerThickness is not None:
                                total += float(layer.LayerThickness)
                        if total > 0:
                            return total, "TYPE:IfcMaterialLayerSetUsage sum(LayerThickness)"

    return None, "UNKNOWN"

def wall_material(wall):
    # instance associations first
    for rel in getattr(wall, "HasAssociations", []) or []:
        if rel.is_a("IfcRelAssociatesMaterial"):
            mat = rel.RelatingMaterial
            if hasattr(mat, "Name") and mat.Name:
                return mat.Name
            if mat and mat.is_a("IfcMaterialLayerSetUsage"):
                ls = mat.ForLayerSet
                if ls and hasattr(ls, "MaterialLayers"):
                    names = []
                    for layer in ls.MaterialLayers or []:
                        if getattr(layer, "Material", None) and getattr(layer.Material, "Name", None):
                            names.append(layer.Material.Name)
                    return ", ".join(names) if names else None
    # fallback: type associations
    wtype = get_wall_type(wall)
    if wtype:
        for rel in getattr(wtype, "HasAssociations", []) or []:
            if rel.is_a("IfcRelAssociatesMaterial"):
                mat = rel.RelatingMaterial
                if hasattr(mat, "Name") and mat.Name:
                    return mat.Name
    return None

def extract_walls(model):
    walls = model.by_type("IfcWall") + model.by_type("IfcWallStandardCase")
    out = []

    for w in walls:
        wtype = get_wall_type(w)
        qname, q = get_quantities(w)
        thickness, thickness_src = wall_thickness_m(w)

        psets = pset.get_psets(w) or {}
        common = psets.get("Pset_WallCommon") or {}

        out.append({
            "GlobalId": getattr(w, "GlobalId", None),
            "Name": getattr(w, "Name", None) or "Unnamed Wall",
            "IfcType": w.is_a(),
            "ObjectType": getattr(w, "ObjectType", None),
            "Tag": getattr(w, "Tag", None),

            # quantities
            "QSet": qname,
            "Length_m": safe_float(q.get("Length")),
            "Height_m": safe_float(q.get("Height")),
            "Area_m2": safe_float(q.get("GrossArea") or q.get("NetArea")),
            "Volume_m3": safe_float(q.get("GrossVolume") or q.get("NetVolume")),

            # thickness
            "Thickness_m": thickness,
            "ThicknessSource": thickness_src,

            # material + type
            "Material": wall_material(w) or "N/A",
            "WallTypeName": getattr(wtype, "Name", None) if wtype else "N/A",
            "WallTypeId": getattr(wtype, "GlobalId", None) if wtype and hasattr(wtype, "GlobalId") else "N/A",

            # key pset props
            "LoadBearing": common.get("LoadBearing"),
            "IsExternal": common.get("IsExternal"),
            "FireRating": common.get("FireRating"),

            # raw psets for later rules
            "Psets": psets
        })

    return out
