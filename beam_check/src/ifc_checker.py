"""IFC Compliance Checker — Spanish DB SUA & Catalan Decree 141/2012

Property extraction is tuned for Revit IFC exports, with fallbacks for
standard IFC property sets (Qto_*, Pset_*) and material layers.
"""

import ifcopenshell
import ifcopenshell.util.element


# ─── Utility ────────────────────────────────────────────────────

def _get_pset_value(element, pset_name, prop_name):
    """Return a property value from a named property set, or None."""
    try:
        psets = ifcopenshell.util.element.get_psets(element)
        if pset_name in psets and prop_name in psets[pset_name]:
            v = psets[pset_name][prop_name]
            if v is not None and v != "":
                return v
    except Exception:
        pass
    return None


def _search_psets(element, prop_name):
    """Search ALL property sets for a property by name. Returns first match."""
    try:
        psets = ifcopenshell.util.element.get_psets(element)
        for pset_name, props in psets.items():
            if isinstance(props, dict) and prop_name in props:
                v = props[prop_name]
                if v is not None and v != "" and isinstance(v, (int, float)):
                    return v
    except Exception:
        pass
    return None


def _to_mm(value_m):
    """Convert a value assumed to be in meters to millimeters."""
    if value_m is None:
        return None
    # Heuristic: if value > 100 it's probably already in mm
    if value_m > 100:
        return round(value_m)
    return round(value_m * 1000)


def _get_material_total_thickness(element):
    """Sum the thicknesses of all material layers (meters), or None."""
    try:
        for rel in getattr(element, "HasAssociations", []):
            if rel.is_a("IfcRelAssociatesMaterial"):
                mat = rel.RelatingMaterial
                layers = None
                if mat.is_a("IfcMaterialLayerSetUsage"):
                    layers = mat.ForLayerSet.MaterialLayers
                elif mat.is_a("IfcMaterialLayerSet"):
                    layers = mat.MaterialLayers
                if layers:
                    total = sum(l.LayerThickness for l in layers)
                    if total > 0:
                        return total
    except Exception:
        pass
    return None


def _label(element):
    """Return a readable label for an IFC element."""
    name = element.Name or element.GlobalId
    return f"{element.is_a()} '{name}'"


# ═══════════════════════════════════════════════════════════════
#  EXISTING CHECKS (Door & Window)
# ═══════════════════════════════════════════════════════════════

def check_door_width(model, min_width_mm=800):
    """DB SUA Annex A — doors on accessible routes ≥ 800 mm wide."""
    results = []
    for door in model.by_type("IfcDoor"):
        width_m = door.OverallWidth  # IFC stores in meters
        width_mm = round(width_m * 1000) if width_m else None
        if width_mm is None:
            results.append(f"[???] {door.Name}: width unknown")
        elif width_mm >= min_width_mm:
            results.append(f"[PASS] {door.Name}: {width_mm} mm (min {min_width_mm} mm)")
        else:
            results.append(f"[FAIL] {door.Name}: {width_mm} mm (min {min_width_mm} mm)")
    return results


def check_window_height(model, min_height_mm=1200):
    """Catalan Decree 141/2012 — window opening height ≥ 1200 mm."""
    results = []
    for window in model.by_type("IfcWindow"):
        height_m = window.OverallHeight  # IFC stores in meters
        height_mm = round(height_m * 1000) if height_m else None
        if height_mm is None:
            results.append(f"[???] {_label(window)}: height unknown")
        elif height_mm >= min_height_mm:
            results.append(f"[PASS] {_label(window)}: {height_mm} mm (min {min_height_mm} mm)")
        else:
            results.append(f"[FAIL] {_label(window)}: {height_mm} mm (min {min_height_mm} mm)")
    return results


# ═══════════════════════════════════════════════════════════════
#  WALL CHECKS
# ═══════════════════════════════════════════════════════════════

def check_wall_thickness(model, min_thickness_mm=100):
    """DB SE-F / EHE — load-bearing wall thickness ≥ 100 mm.

    Revit: PSet_Revit_Type_Construction.Width  (meters)
    Fallback: sum of IfcMaterialLayerSet thicknesses
    Standard: Qto_WallBaseQuantities.Width
    """
    results = []
    for wall in model.by_type("IfcWall"):
        thickness = (
            _get_pset_value(wall, "PSet_Revit_Type_Construction", "Width")
            or _get_material_total_thickness(wall)
            or _get_pset_value(wall, "Qto_WallBaseQuantities", "Width")
            or _get_pset_value(wall, "Pset_WallCommon", "Width")
        )
        if thickness is not None:
            thickness_mm = _to_mm(thickness)
            if thickness_mm >= min_thickness_mm:
                results.append(
                    f"[PASS] {_label(wall)}: {thickness_mm} mm (min {min_thickness_mm} mm)"
                )
            else:
                results.append(
                    f"[FAIL] {_label(wall)}: {thickness_mm} mm (min {min_thickness_mm} mm)"
                )
        else:
            results.append(f"[???] {_label(wall)}: thickness unknown")
    return results


def check_wall_height(model, min_height_mm=2500):
    """Catalan Decree 141/2012 §3.3 — free height between floors ≥ 2500 mm.

    Revit: PSet_Revit_Constraints.Unconnected Height  (meters)
    Standard: Qto_WallBaseQuantities.Height
    """
    results = []
    for wall in model.by_type("IfcWall"):
        height = (
            _get_pset_value(wall, "PSet_Revit_Constraints", "Unconnected Height")
            or _get_pset_value(wall, "Qto_WallBaseQuantities", "Height")
            or _search_psets(wall, "Height")
        )
        if height is not None:
            height_mm = _to_mm(height)
            if height_mm >= min_height_mm:
                results.append(
                    f"[PASS] {_label(wall)}: {height_mm} mm (min {min_height_mm} mm)"
                )
            else:
                results.append(
                    f"[FAIL] {_label(wall)}: {height_mm} mm (min {min_height_mm} mm)"
                )
        else:
            results.append(f"[???] {_label(wall)}: height unknown")
    return results


# ═══════════════════════════════════════════════════════════════
#  SLAB CHECKS
# ═══════════════════════════════════════════════════════════════

def check_slab_thickness(model, min_thickness_mm=150):
    """EHE / DB SE — floor slab thickness ≥ 150 mm.

    Revit: PSet_Revit_Dimensions.Thickness  (meters)
    Revit type: PSet_Revit_Type_Construction.Default Thickness
    Fallback: sum of material layers
    Standard: Qto_SlabBaseQuantities.Depth
    """
    results = []
    for slab in model.by_type("IfcSlab"):
        depth = (
            _get_pset_value(slab, "PSet_Revit_Dimensions", "Thickness")
            or _get_pset_value(slab, "PSet_Revit_Type_Construction", "Default Thickness")
            or _get_material_total_thickness(slab)
            or _get_pset_value(slab, "Qto_SlabBaseQuantities", "Depth")
            or _get_pset_value(slab, "Qto_SlabBaseQuantities", "Width")
        )
        if depth is not None:
            depth_mm = _to_mm(depth)
            if depth_mm >= min_thickness_mm:
                results.append(
                    f"[PASS] {_label(slab)}: {depth_mm} mm (min {min_thickness_mm} mm)"
                )
            else:
                results.append(
                    f"[FAIL] {_label(slab)}: {depth_mm} mm (min {min_thickness_mm} mm)"
                )
        else:
            results.append(f"[???] {_label(slab)}: thickness unknown")
    return results


# ═══════════════════════════════════════════════════════════════
#  COLUMN CHECKS
# ═══════════════════════════════════════════════════════════════

def check_column_min_dimension(model, min_dim_mm=250):
    """EHE — smallest cross-section side of a column ≥ 250 mm.

    Revit: PSet_Revit_Type_Dimensions (b, h, d, bf, etc.)
    Profile: IfcMaterialProfileSetUsage profile dimensions
    Standard: Qto_ColumnBaseQuantities Width/Depth
    """
    results = []
    for col in model.by_type("IfcColumn"):
        # Try Revit type dimensions
        w = (_get_pset_value(col, "PSet_Revit_Type_Dimensions", "b")
             or _get_pset_value(col, "PSet_Revit_Type_Dimensions", "bf")
             or _get_pset_value(col, "Qto_ColumnBaseQuantities", "Width"))
        d = (_get_pset_value(col, "PSet_Revit_Type_Dimensions", "d")
             or _get_pset_value(col, "PSet_Revit_Type_Dimensions", "h")
             or _get_pset_value(col, "Qto_ColumnBaseQuantities", "Depth"))

        smallest = None
        if w is not None and d is not None:
            smallest = min(_to_mm(w), _to_mm(d))
        elif w is not None:
            smallest = _to_mm(w)
        elif d is not None:
            smallest = _to_mm(d)

        if smallest is not None:
            if smallest >= min_dim_mm:
                results.append(
                    f"[PASS] {_label(col)}: {smallest} mm (min {min_dim_mm} mm)"
                )
            else:
                results.append(
                    f"[FAIL] {_label(col)}: {smallest} mm (min {min_dim_mm} mm)"
                )
        else:
            results.append(f"[???] {_label(col)}: dimensions unknown")
    return results


# ═══════════════════════════════════════════════════════════════
#  BEAM CHECKS
# ═══════════════════════════════════════════════════════════════

def check_beam_depth(model, min_depth_mm=200):
    """EHE / DB SE — beam depth ≥ 200 mm.

    Revit: PSet_Revit_Type_Dimensions.d  (overall depth, meters)
    Standard: Qto_BeamBaseQuantities.Depth
    """
    results = []
    for beam in model.by_type("IfcBeam"):
        depth = (
            _get_pset_value(beam, "PSet_Revit_Type_Dimensions", "d")
            or _get_pset_value(beam, "Qto_BeamBaseQuantities", "Depth")
            or _get_pset_value(beam, "Pset_BeamCommon", "Depth")
            or _search_psets(beam, "d")
        )
        if depth is not None:
            depth_mm = _to_mm(depth)
            if depth_mm >= min_depth_mm:
                results.append(
                    f"[PASS] {_label(beam)}: depth {depth_mm} mm (min {min_depth_mm} mm)"
                )
            else:
                results.append(
                    f"[FAIL] {_label(beam)}: depth {depth_mm} mm (min {min_depth_mm} mm)"
                )
        else:
            results.append(f"[???] {_label(beam)}: depth unknown")
    return results


def check_beam_width(model, min_width_mm=150):
    """EHE / DB SE — beam width (flange width) ≥ 150 mm.

    Revit: PSet_Revit_Type_Dimensions.bf  (flange width, meters)
    Standard: Qto_BeamBaseQuantities.Width
    """
    results = []
    for beam in model.by_type("IfcBeam"):
        width = (
            _get_pset_value(beam, "PSet_Revit_Type_Dimensions", "bf")
            or _get_pset_value(beam, "PSet_Revit_Type_Dimensions", "tw")
            or _get_pset_value(beam, "Qto_BeamBaseQuantities", "Width")
            or _get_pset_value(beam, "Pset_BeamCommon", "Width")
        )
        if width is not None:
            width_mm = _to_mm(width)
            if width_mm >= min_width_mm:
                results.append(
                    f"[PASS] {_label(beam)}: width {width_mm} mm (min {min_width_mm} mm)"
                )
            else:
                results.append(
                    f"[FAIL] {_label(beam)}: width {width_mm} mm (min {min_width_mm} mm)"
                )
        else:
            results.append(f"[???] {_label(beam)}: width unknown")
    return results


# ═══════════════════════════════════════════════════════════════
#  OPENING ELEMENT CHECKS
# ═══════════════════════════════════════════════════════════════

def check_opening_height(model, min_height_mm=2000):
    """DB SUA 2 §1.1 — clear height of openings (doorways etc.) ≥ 2000 mm.

    Opening elements themselves rarely carry dimensions; we read them
    from the filling element (IfcDoor / IfcWindow) via HasFillings.
    """
    results = []
    for opening in model.by_type("IfcOpeningElement"):
        height = None

        # Try filling element (door/window) first — most reliable
        try:
            for rel in opening.HasFillings:
                filling = rel.RelatedBuildingElement
                if hasattr(filling, "OverallHeight") and filling.OverallHeight:
                    height = filling.OverallHeight
                    break
        except Exception:
            pass

        # Fallback to pset
        if height is None:
            height = (
                _get_pset_value(opening, "Qto_OpeningElementBaseQuantities", "Height")
                or _search_psets(opening, "Height")
            )

        if height is not None:
            height_mm = _to_mm(height)
            if height_mm >= min_height_mm:
                results.append(
                    f"[PASS] {_label(opening)}: {height_mm} mm (min {min_height_mm} mm)"
                )
            else:
                results.append(
                    f"[FAIL] {_label(opening)}: {height_mm} mm (min {min_height_mm} mm)"
                )
        else:
            results.append(f"[???] {_label(opening)}: height unknown")
    return results


# ═══════════════════════════════════════════════════════════════
#  SPACE / ROOM CHECKS
# ═══════════════════════════════════════════════════════════════

def check_corridor_width(model, min_width_mm=1100):
    """DB SUA Annex A — corridors / circulation ≥ 1100 mm wide.

    Identifies corridors by LongName/Name keywords,
    then estimates width as Area / longest-side (Perimeter / 2 - W ≈ L).
    Simplification: width ≈ Area / (Perimeter / 4) for narrow rooms.
    """
    CORRIDOR_KEYWORDS = {"corridor", "hall", "hallway", "passage",
                         "circulation", "pasillo", "distribuidor"}
    results = []
    for space in model.by_type("IfcSpace"):
        space_name = (space.LongName or space.Name or "").lower()
        if not any(kw in space_name for kw in CORRIDOR_KEYWORDS):
            continue

        area = (
            _get_pset_value(space, "PSet_Revit_Dimensions", "Area")
            or _get_pset_value(space, "GSA Space Areas", "GSA BIM Area")
            or _get_pset_value(space, "Qto_SpaceBaseQuantities", "NetFloorArea")
        )
        perimeter = _get_pset_value(space, "PSet_Revit_Dimensions", "Perimeter")

        if area is not None and perimeter is not None and perimeter > 0:
            # For a rectangle: P = 2(L+W), A = L*W
            # L + W = P/2  →  L*W = A  →  quadratic: x² - (P/2)x + A = 0
            half_p = perimeter / 2.0
            disc = half_p * half_p - 4 * area
            if disc >= 0:
                import math
                short_side = (half_p - math.sqrt(disc)) / 2.0
            else:
                short_side = area / (perimeter / 4.0)
            width_mm = _to_mm(short_side)
            if width_mm >= min_width_mm:
                results.append(
                    f"[PASS] {_label(space)}: ~{width_mm} mm (min {min_width_mm} mm)"
                )
            else:
                results.append(
                    f"[FAIL] {_label(space)}: ~{width_mm} mm (min {min_width_mm} mm)"
                )
        else:
            results.append(f"[???] {_label(space)}: width unknown")
    return results


def check_room_area(model, min_area_m2=5.0):
    """Catalan Decree 141/2012 — habitable room ≥ 5 m² (single bedroom).

    Revit: PSet_Revit_Dimensions.Area  (m²)
    Also: GSA Space Areas.GSA BIM Area
    Standard: Qto_SpaceBaseQuantities.NetFloorArea
    """
    results = []
    for space in model.by_type("IfcSpace"):
        area = (
            _get_pset_value(space, "PSet_Revit_Dimensions", "Area")
            or _get_pset_value(space, "GSA Space Areas", "GSA BIM Area")
            or _get_pset_value(space, "Qto_SpaceBaseQuantities", "NetFloorArea")
            or _get_pset_value(space, "Qto_SpaceBaseQuantities", "GrossFloorArea")
        )
        if area is not None:
            area_val = round(area, 2)
            if area_val >= min_area_m2:
                results.append(
                    f"[PASS] {_label(space)}: {area_val} m² (min {min_area_m2} m²)"
                )
            else:
                results.append(
                    f"[FAIL] {_label(space)}: {area_val} m² (min {min_area_m2} m²)"
                )
        else:
            results.append(f"[???] {_label(space)}: area unknown")
    return results


def check_room_ceiling_height(model, min_height_mm=2200):
    """DB SUA 2 §1.1 / Decree 141/2012 — general ceiling clearance ≥ 2200 mm.

    Revit: PSet_Revit_Dimensions.Unbounded Height  (meters)
    Also: PSet_Revit_Constraints.Limit Offset  (meters)
    Standard: Qto_SpaceBaseQuantities.Height
    """
    results = []
    for space in model.by_type("IfcSpace"):
        height = (
            _get_pset_value(space, "PSet_Revit_Dimensions", "Unbounded Height")
            or _get_pset_value(space, "PSet_Revit_Constraints", "Limit Offset")
            or _get_pset_value(space, "Qto_SpaceBaseQuantities", "Height")
            or _get_pset_value(space, "Qto_SpaceBaseQuantities", "FinishCeilingHeight")
        )
        # Skip zero values from Limit Offset
        if height is not None and height > 0:
            height_mm = _to_mm(height)
            if height_mm >= min_height_mm:
                results.append(
                    f"[PASS] {_label(space)}: {height_mm} mm (min {min_height_mm} mm)"
                )
            else:
                results.append(
                    f"[FAIL] {_label(space)}: {height_mm} mm (min {min_height_mm} mm)"
                )
        else:
            results.append(f"[???] {_label(space)}: ceiling height unknown")
    return results


# ═══════════════════════════════════════════════════════════════
#  STAIR CHECKS
# ═══════════════════════════════════════════════════════════════

def check_stair_riser_tread(model, min_riser_mm=130, max_riser_mm=185, min_tread_mm=280):
    """DB SUA 1 §4.2.1 — riser 130-185 mm, tread ≥ 280 mm.

    Revit exports direct attrs in FEET; Pset_StairFlightCommon in METERS.
    Prefer the pset values which are reliable metric.
    """
    results = []
    for flight in model.by_type("IfcStairFlight"):
        # Prefer Pset values (meters) — Revit direct attrs are often in feet
        riser = (
            _get_pset_value(flight, "Pset_StairFlightCommon", "RiserHeight")
            or _get_pset_value(flight, "Qto_StairFlightBaseQuantities", "RiserHeight")
        )
        tread = (
            _get_pset_value(flight, "Pset_StairFlightCommon", "TreadLength")
            or _get_pset_value(flight, "Qto_StairFlightBaseQuantities", "TreadLength")
        )

        lbl = _label(flight)
        if riser is not None:
            riser_mm = _to_mm(riser)
            if min_riser_mm <= riser_mm <= max_riser_mm:
                results.append(
                    f"[PASS] {lbl}: riser {riser_mm} mm ({min_riser_mm}-{max_riser_mm} mm)"
                )
            else:
                results.append(
                    f"[FAIL] {lbl}: riser {riser_mm} mm ({min_riser_mm}-{max_riser_mm} mm)"
                )
        else:
            results.append(f"[???] {lbl}: riser height unknown")

        if tread is not None:
            tread_mm = _to_mm(tread)
            if tread_mm >= min_tread_mm:
                results.append(
                    f"[PASS] {lbl}: tread {tread_mm} mm (min {min_tread_mm} mm)"
                )
            else:
                results.append(
                    f"[FAIL] {lbl}: tread {tread_mm} mm (min {min_tread_mm} mm)"
                )
        else:
            results.append(f"[???] {lbl}: tread depth unknown")
    return results


# ═══════════════════════════════════════════════════════════════
#  RAILING / GUARDRAIL CHECKS
# ═══════════════════════════════════════════════════════════════

def check_railing_height(model, min_height_mm=900):
    """DB SUA 1 §3.2.1 — guardrail height ≥ 900 mm (drops < 6 m).

    Revit: Pset_RailingCommon.Height (meters)
    Also: PSet_Revit_Type_Construction.Railing Height
    """
    results = []
    for railing in model.by_type("IfcRailing"):
        height = (
            _get_pset_value(railing, "Pset_RailingCommon", "Height")
            or _get_pset_value(railing, "PSet_Revit_Type_Construction", "Railing Height")
            or _get_pset_value(railing, "Qto_RailingBaseQuantities", "Height")
        )
        if height is not None:
            height_mm = _to_mm(height)
            if height_mm >= min_height_mm:
                results.append(
                    f"[PASS] {_label(railing)}: {height_mm} mm (min {min_height_mm} mm)"
                )
            else:
                results.append(
                    f"[FAIL] {_label(railing)}: {height_mm} mm (min {min_height_mm} mm)"
                )
        else:
            results.append(f"[???] {_label(railing)}: height unknown")
    return results


# ═══════════════════════════════════════════════════════════════
#  AGGREGATE RUNNER  (used by app.py's advanced interface)
# ═══════════════════════════════════════════════════════════════

ALL_CHECKS = [
    ("Door Width ≥ 800 mm",         check_door_width),
    ("Window Height ≥ 1200 mm",     check_window_height),
    ("Wall Thickness ≥ 100 mm",     check_wall_thickness),
    ("Wall Height ≥ 2500 mm",       check_wall_height),
    ("Slab Thickness ≥ 150 mm",     check_slab_thickness),
    ("Column Min Dim ≥ 250 mm",     check_column_min_dimension),
    ("Beam Depth ≥ 200 mm",         check_beam_depth),
    ("Beam Width ≥ 150 mm",         check_beam_width),
    ("Opening Height ≥ 2000 mm",    check_opening_height),
    ("Corridor Width ≥ 1100 mm",    check_corridor_width),
    ("Room Area ≥ 5 m²",           check_room_area),
    ("Room Ceiling ≥ 2200 mm",      check_room_ceiling_height),
    ("Stair Riser/Tread",           check_stair_riser_tread),
    ("Railing Height ≥ 900 mm",     check_railing_height),
]


def run_all_checks(ifc_path):
    """Run every registered check.  Returns dict consumed by app.py."""
    model = ifcopenshell.open(ifc_path)
    all_results = []
    failed_ids = set()

    for rule_name, check_fn in ALL_CHECKS:
        lines = check_fn(model)
        for line in lines:
            passed = None
            if line.startswith("[PASS]"):
                passed = True
            elif line.startswith("[FAIL]"):
                passed = False
            all_results.append({
                "rule": rule_name,
                "element_name": line.split("] ", 1)[-1].split(":")[0].strip(),
                "actual": line.split(":")[-1].strip() if ":" in line else "",
                "passed": passed,
            })

        # Collect GlobalIds of failed elements for 3-D highlighting
        if any(l.startswith("[FAIL]") for l in lines):
            type_map = {
                check_door_width: "IfcDoor",
                check_window_height: "IfcWindow",
                check_wall_thickness: "IfcWall",
                check_wall_height: "IfcWall",
                check_slab_thickness: "IfcSlab",
                check_column_min_dimension: "IfcColumn",
                check_beam_depth: "IfcBeam",
                check_beam_width: "IfcBeam",
                check_opening_height: "IfcOpeningElement",
                check_corridor_width: "IfcSpace",
                check_room_area: "IfcSpace",
                check_room_ceiling_height: "IfcSpace",
                check_stair_riser_tread: "IfcStairFlight",
                check_railing_height: "IfcRailing",
            }
            ifc_type = type_map.get(check_fn)
            if ifc_type:
                for elem in model.by_type(ifc_type):
                    failed_ids.add(elem.GlobalId)

    total = len(all_results)
    passed = sum(1 for r in all_results if r["passed"] is True)
    failed = sum(1 for r in all_results if r["passed"] is False)
    unknown = total - passed - failed

    return {
        "results": all_results,
        "failed_ids": failed_ids,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "unknown": unknown,
        },
    }
