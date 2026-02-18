"""
Foundation Compliance Checker — IFCore Platform Contract
Regulations: Metropolitan Building Ordinances (Art. 69, Art. 128) + DB SE-AE
Returns list[dict] per element; each dict maps to one element_results DB row.
"""
import re
import ifcopenshell
import ifcopenshell.util.element
from typing import Optional, Any

# ── Regulatory Constants ─────────────────────────────────────────────────────
MIN_SLAB_THICKNESS_MM = 300         # Art. 69: 150 mm waterproof concrete + 150 mm drainage
MIN_BEAM_WIDTH_MM = 300             # DB SE-AE minimum bearing beam width
MIN_BEAM_DEPTH_MM = 300             # DB SE-AE minimum bearing beam depth
DEFAULT_BEARING_CAPACITY_KN_M2 = 150.0   # Conservative default (soft-medium soil)
DEFAULT_FLOOR_LOAD_KN_M2 = 7.0      # DB SE-AE residential: 5.0 dead + 2.0 live


# ── Private Helpers ───────────────────────────────────────────────────────────

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


def _get_pset_value(element, *keys) -> Optional[Any]:
    """Search all property sets for the first matching key. Returns None if not found."""
    try:
        psets = ifcopenshell.util.element.get_psets(element)
        for key in keys:
            for pset_props in psets.values():
                if key in pset_props and pset_props[key] is not None:
                    return pset_props[key]
    except Exception:
        pass
    return None


def _get_footing_dimensions(footing, scale: float) -> dict:
    """
    Extract length, width, and thickness from an IfcFooting or IfcSlab.
    Returns: {length_m, width_m, thickness_m} — any may be None.
    Path 1: Quantity sets (Qto_FootingBaseQuantities)
    Path 2: IfcExtrudedAreaSolid → IfcRectangleProfileDef geometry
    """
    dims = {"length_m": None, "width_m": None, "thickness_m": None}

    # Path 1: Quantity sets
    try:
        if hasattr(footing, "IsDefinedBy"):
            for rel in footing.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    prop_def = rel.RelatingPropertyDefinition
                    if prop_def.is_a("IfcElementQuantity"):
                        for qty in prop_def.Quantities:
                            if hasattr(qty, "LengthValue"):
                                if qty.Name in ("Length", "FootingLength") and dims["length_m"] is None:
                                    dims["length_m"] = qty.LengthValue * scale
                                elif qty.Name in ("Width", "FootingWidth") and dims["width_m"] is None:
                                    dims["width_m"] = qty.LengthValue * scale
                                elif qty.Name in ("Depth", "Thickness", "Height") and dims["thickness_m"] is None:
                                    dims["thickness_m"] = qty.LengthValue * scale
    except Exception:
        pass

    # Path 2: Geometry — IfcExtrudedAreaSolid
    if any(v is None for v in dims.values()):
        try:
            if hasattr(footing, "Representation") and footing.Representation:
                for rep in footing.Representation.Representations:
                    for item in rep.Items:
                        if item.is_a("IfcExtrudedAreaSolid"):
                            if dims["thickness_m"] is None:
                                dims["thickness_m"] = item.Depth * scale
                            area = item.SweptArea
                            if area.is_a("IfcRectangleProfileDef"):
                                if dims["length_m"] is None:
                                    dims["length_m"] = area.XDim * scale
                                if dims["width_m"] is None:
                                    dims["width_m"] = area.YDim * scale
        except Exception:
            pass

    # Path 3: Parse dimensions from element name (Revit-style naming conventions)
    # e.g. "Bearing Footing - 900 x 300"  → width=900 mm, thickness=300 mm
    # e.g. "150mm Exterior Slab on Grade"  → thickness=150 mm
    if any(v is None for v in dims.values()):
        try:
            name = getattr(footing, "Name", "") or ""
            # Pattern A: two numbers separated by "x" / "X" / "×"
            match_x = re.search(r'(\d+)\s*[xX×]\s*(\d+)', name)
            if match_x:
                a, b = int(match_x.group(1)), int(match_x.group(2))
                # Larger value is the plan width; smaller is the depth/thickness
                if dims["width_m"] is None:
                    dims["width_m"] = max(a, b) / 1000.0
                if dims["thickness_m"] is None:
                    dims["thickness_m"] = min(a, b) / 1000.0
            else:
                # Pattern B: a standalone "NNNmm" token (e.g. "150mm Slab on Grade")
                if dims["thickness_m"] is None:
                    match_mm = re.search(r'(\d+)\s*mm', name, re.IGNORECASE)
                    if match_mm:
                        dims["thickness_m"] = int(match_mm.group(1)) / 1000.0
        except Exception:
            pass

    return dims


def _get_element_elevation(element, scale: float) -> Optional[float]:
    """Return the Z coordinate of an element's placement in metres."""
    try:
        coords = element.ObjectPlacement.RelativePlacement.Location.Coordinates
        return coords[2] * scale if len(coords) > 2 else 0.0
    except Exception:
        return None


def _get_bearing_beams(model: ifcopenshell.file, scale: float):
    """
    Find IfcBeam (or IfcMember fallback) assigned to the lowest IfcBuildingStorey.
    Returns: (beams: list, blocked_reason: str | None)
    blocked_reason is a human-readable explanation when the list is empty.
    """
    def _storey_elev(s):
        try:
            coords = s.ObjectPlacement.RelativePlacement.Location.Coordinates
            return coords[2] * scale if len(coords) > 2 else 0.0
        except Exception:
            return 0.0

    storeys = model.by_type("IfcBuildingStorey")
    if not storeys:
        return [], (
            "Model has no IfcBuildingStorey elements — cannot determine the foundation level. "
            "Add storeys in your BIM tool and assign structural elements to them."
        )

    lowest_storey = min(storeys, key=_storey_elev)
    storey_name   = lowest_storey.Name or f"Storey #{lowest_storey.id()}"
    storey_elev   = _storey_elev(lowest_storey)

    # Collect beams assigned to the lowest storey
    beams_in_storey = []
    for ifc_type in ("IfcBeam", "IfcMember"):
        if beams_in_storey:
            break
        for elem in model.by_type(ifc_type):
            try:
                for rel in elem.ContainedInStructure:
                    if rel.RelatingStructure == lowest_storey:
                        beams_in_storey.append(elem)
                        break
            except Exception:
                pass

    if not beams_in_storey:
        total_beams = len(list(model.by_type("IfcBeam"))) + len(list(model.by_type("IfcMember")))
        if total_beams > 0:
            reason = (
                f"Model has {total_beams} IfcBeam/IfcMember element(s) but none are spatially "
                f"assigned to the lowest storey '{storey_name}' (elevation {storey_elev:.2f} m). "
                f"In your BIM tool, ensure foundation beams are contained in the correct storey."
            )
        else:
            reason = (
                f"No IfcBeam or IfcMember elements exist in the model. "
                f"Foundation bearing beams must be modelled as IfcBeam and assigned to "
                f"storey '{storey_name}' (elevation {storey_elev:.2f} m)."
            )
        return [], reason

    # Extract cross-section dimensions for each beam
    results = []
    for beam in beams_in_storey:
        width_m, depth_m = None, None
        dim_source = None

        # Path 1: IfcExtrudedAreaSolid → IfcRectangleProfileDef
        try:
            if hasattr(beam, "Representation") and beam.Representation:
                for rep in beam.Representation.Representations:
                    for item in rep.Items:
                        if item.is_a("IfcExtrudedAreaSolid"):
                            swept = item.SweptArea
                            if swept.is_a("IfcRectangleProfileDef"):
                                width_m, depth_m = swept.XDim * scale, swept.YDim * scale
                                dim_source = "geometry"
        except Exception:
            pass

        # Path 2: Property sets
        if width_m is None:
            val = _get_pset_value(beam, "Width", "CrossSectionWidth", "b")
            if val is not None:
                width_m = float(val) * scale
                dim_source = "property set"
        if depth_m is None:
            val = _get_pset_value(beam, "Depth", "Height", "CrossSectionHeight", "h")
            if val is not None:
                depth_m = float(val) * scale
                dim_source = dim_source or "property set"

        results.append({
            "id":          beam.GlobalId,
            "name":        beam.Name or f"{beam.is_a()} #{beam.id()}",
            "ifc_type":    beam.is_a(),
            "storey_name": storey_name,
            "width_mm":    round(width_m * 1000, 1) if width_m is not None else None,
            "depth_mm":    round(depth_m * 1000, 1) if depth_m is not None else None,
            "dim_source":  dim_source,
        })
    return results, None


# ── Check Functions (IFCore Contract) ────────────────────────────────────────

def check_foundation_slab_thickness(model: ifcopenshell.file) -> list:
    """
    Art. 69 — Foundation slab minimum thickness (ground floor only).
    Scope: IfcFooting + IfcSlab[BASESLAB] at the lowest storey only.
    Floor finishes (IfcSlab[FLOOR]) and upper-floor slabs are excluded.
    Required: 150 mm waterproof concrete + 150 mm drainage layer = 300 mm total.
    """
    scale = _get_length_scale(model)
    results = []

    # ── Determine ground-level elevation cut-off ──────────────────────────────
    storeys = model.by_type("IfcBuildingStorey")
    ground_elev_cutoff = None
    if storeys:
        def _selev(s):
            try:
                c = s.ObjectPlacement.RelativePlacement.Location.Coordinates
                return c[2] * scale if len(c) > 2 else 0.0
            except Exception:
                return 0.0
        ground_elev = _selev(min(storeys, key=_selev))
        ground_elev_cutoff = ground_elev + 1.0  # 1 m tolerance above lowest storey

    def _is_at_ground(elem):
        """True when element is at or just above the lowest storey level."""
        if ground_elev_cutoff is None:
            return True  # no storey info — include all
        elev = _get_element_elevation(elem, scale)
        return elev is None or elev <= ground_elev_cutoff

    # ── Candidates: IfcFooting (always foundation elements — no elevation filter needed)
    #               + IfcSlab[BASESLAB or FLOOR-on-grade] at ground level only ──────────
    candidates = list(model.by_type("IfcFooting"))   # IfcFooting is always a foundation type
    for slab in model.by_type("IfcSlab"):
        ptype = getattr(slab, "PredefinedType", None)
        name_lower = (getattr(slab, "Name", "") or "").lower()
        is_base = ptype == "BASESLAB"
        # Include FLOOR-type slabs that are explicitly described as ground/on-grade slabs
        is_on_grade = ptype == "FLOOR" and (
            "on grade" in name_lower or "slab on grade" in name_lower
        )
        if (is_base or is_on_grade) and _is_at_ground(slab):
            candidates.append(slab)

    if not candidates:
        return [{
            "element_id":        None,
            "element_type":      "IfcFooting / IfcSlab",
            "element_name":      "No foundation elements found",
            "element_name_long": "Art. 69 — No IfcFooting or IfcSlab[BASESLAB/on-grade] in model",
            "check_status":      "blocked",
            "actual_value":      None,
            "required_value":    f"{MIN_SLAB_THICKNESS_MM} mm",
            "comment":           "Model contains no IfcFooting or on-grade slab elements to check",
            "log":               None,
        }]

    for elem in candidates:
        name = elem.Name or f"{elem.is_a()} #{elem.id()}"
        dims = _get_footing_dimensions(elem, scale)
        thickness_m = dims["thickness_m"]
        thickness_mm = round(thickness_m * 1000, 1) if thickness_m is not None else None

        if thickness_mm is None:
            status = "blocked"
            comment = "Thickness not found in quantity sets, geometry, or element name"
        elif thickness_mm >= MIN_SLAB_THICKNESS_MM:
            status = "pass"
            comment = f"Art. 69 satisfied: {thickness_mm} mm ≥ {MIN_SLAB_THICKNESS_MM} mm"
        else:
            deficit = MIN_SLAB_THICKNESS_MM - thickness_mm
            status = "fail"
            comment = (f"Art. 69: {deficit:.0f} mm below minimum "
                       f"(requires 150 mm concrete + 150 mm drainage layer)")

        results.append({
            "element_id":        elem.GlobalId,
            "element_type":      elem.is_a(),
            "element_name":      name,
            "element_name_long": f"{name} — Art. 69 Foundation Slab Thickness",
            "check_status":      status,
            "actual_value":      f"{thickness_mm} mm" if thickness_mm is not None else None,
            "required_value":    f"{MIN_SLAB_THICKNESS_MM} mm",
            "comment":           comment,
            "log":               None,
        })
    return results


def check_foundation_dimensions(model: ifcopenshell.file) -> list:
    """
    Load Check — Foundation footing dimensions vs calculated required area.
    Required area = (n_floors × floor_load × provided_area) / bearing_capacity.
    Bearing capacity from IFC property sets; defaults to 150 kN/m².
    """
    scale = _get_length_scale(model)
    n_floors = max(len(model.by_type("IfcBuildingStorey")), 1)

    # Floor load from IfcSpace properties or default
    floor_load = DEFAULT_FLOOR_LOAD_KN_M2
    spaces = model.by_type("IfcSpace")
    if spaces:
        val = _get_pset_value(spaces[0], "DesignLoad", "FloorLoad", "LoadBearingCapacity")
        if val is not None:
            try:
                floor_load = float(val)
            except (TypeError, ValueError):
                pass

    footings = list(model.by_type("IfcFooting"))
    if not footings:
        return [{
            "element_id":        None,
            "element_type":      "IfcFooting",
            "element_name":      "No footings found",
            "element_name_long": "Load Check — No IfcFooting elements in model",
            "check_status":      "blocked",
            "actual_value":      None,
            "required_value":    None,
            "comment":           "Model contains no IfcFooting elements",
            "log":               None,
        }]

    results = []
    for footing in footings:
        name = footing.Name or f"Footing #{footing.id()}"

        # Bearing capacity fallback chain
        bearing_val = _get_pset_value(
            footing,
            "BearingCapacity", "AllowableBearingCapacity",
            "WorkingStress", "FatiguesDeTraball", "SoilBearingCapacity",
        )
        used_default = bearing_val is None
        bearing = float(bearing_val) if not used_default else DEFAULT_BEARING_CAPACITY_KN_M2
        if bearing <= 0:
            bearing = DEFAULT_BEARING_CAPACITY_KN_M2
            used_default = True

        dims = _get_footing_dimensions(footing, scale)
        L, W = dims["length_m"], dims["width_m"]

        if L is None or W is None:
            results.append({
                "element_id":        footing.GlobalId,
                "element_type":      "IfcFooting",
                "element_name":      name,
                "element_name_long": f"{name} — Foundation Dimensions / Load Check",
                "check_status":      "blocked",
                "actual_value":      None,
                "required_value":    None,
                "comment":           "Footing L/W not found in geometry or quantity sets",
                "log":               f"dims={dims}",
            })
            continue

        provided_area = round(L * W, 4)
        total_load = n_floors * floor_load * provided_area       # kN
        required_area = round(total_load / bearing, 4)           # m²

        if provided_area >= required_area:
            status = "pass"
            comment = (f"Provided {provided_area:.2f} m² ≥ required {required_area:.2f} m² "
                       f"({n_floors} floors × {floor_load} kN/m² / {bearing} kN/m²)")
        else:
            deficit = round(required_area - provided_area, 3)
            status = "fail"
            comment = (f"Deficit {deficit:.3f} m²: required {required_area:.2f} m² > "
                       f"provided {provided_area:.2f} m² "
                       f"({n_floors} floors, q={floor_load} kN/m², σ={bearing} kN/m²)"
                       + (" [σ default]" if used_default else ""))

        results.append({
            "element_id":        footing.GlobalId,
            "element_type":      "IfcFooting",
            "element_name":      name,
            "element_name_long": f"{name} — Foundation Dimensions / Load Check",
            "check_status":      status,
            "actual_value":      f"{provided_area:.2f} m²  ({L:.2f} × {W:.2f} m)",
            "required_value":    f"{required_area:.2f} m²",
            "comment":           comment,
            "log":               (f"L={L:.3f}m W={W:.3f}m bearing={bearing}kN/m² "
                                  f"q={floor_load}kN/m² n={n_floors} "
                                  f"{'[default bearing]' if used_default else ''}"),
        })
    return results


def check_bearing_beam_section(model: ifcopenshell.file) -> list:
    """
    DB SE-AE — Foundation bearing beam minimum cross-section.
    Checks beams at the lowest storey only.
    Required: width ≥ 300 mm AND depth ≥ 300 mm.
    """
    scale = _get_length_scale(model)
    beams, blocked_reason = _get_bearing_beams(model, scale)

    if not beams:
        return [{
            "element_id":        None,
            "element_type":      "IfcBeam / IfcMember",
            "element_name":      "Bearing beams not found",
            "element_name_long": "DB SE-AE — Bearing beam check blocked",
            "check_status":      "blocked",
            "actual_value":      None,
            "required_value":    f"{MIN_BEAM_WIDTH_MM}×{MIN_BEAM_DEPTH_MM} mm",
            "comment":           blocked_reason,
            "log":               None,
        }]

    results = []
    for beam in beams:
        w    = beam["width_mm"]
        d    = beam["depth_mm"]
        name = beam["name"]
        src  = beam.get("dim_source")

        if w is None or d is None:
            # Beam was found but its cross-section geometry is missing from IFC
            missing = []
            if w is None:
                missing.append("width")
            if d is None:
                missing.append("depth")
            status = "blocked"
            actual  = (f"w={w:.0f} mm" if w is not None else "w=N/A") + \
                      " / " + (f"d={d:.0f} mm" if d is not None else "d=N/A")
            comment = (
                f"Cross-section {' and '.join(missing)} not found. "
                f"Searched: IfcExtrudedAreaSolid → IfcRectangleProfileDef (geometry), "
                f"and property sets (Width/Depth/Height keys). "
                f"Ensure the beam has a rectangular structural profile assigned in your BIM tool."
            )
        else:
            w_ok = w >= MIN_BEAM_WIDTH_MM
            d_ok = d >= MIN_BEAM_DEPTH_MM
            actual = f"{w:.0f}×{d:.0f} mm"
            if w_ok and d_ok:
                status  = "pass"
                comment = (f"DB SE-AE satisfied: {w:.0f}×{d:.0f} mm ≥ "
                           f"{MIN_BEAM_WIDTH_MM}×{MIN_BEAM_DEPTH_MM} mm"
                           + (f" (from {src})" if src else ""))
            else:
                parts = []
                if not w_ok:
                    parts.append(f"width {w:.0f} mm < min {MIN_BEAM_WIDTH_MM} mm")
                if not d_ok:
                    parts.append(f"depth {d:.0f} mm < min {MIN_BEAM_DEPTH_MM} mm")
                status  = "fail"
                comment = "DB SE-AE violation: " + "; ".join(parts)

        results.append({
            "element_id":        beam["id"],
            "element_type":      beam["ifc_type"],
            "element_name":      name,
            "element_name_long": f"{name} @ {beam['storey_name']} — DB SE-AE Bearing Beam",
            "check_status":      status,
            "actual_value":      actual if (w is not None or d is not None) else None,
            "required_value":    f"{MIN_BEAM_WIDTH_MM}×{MIN_BEAM_DEPTH_MM} mm",
            "comment":           comment,
            "log":               f"dim_source={src}",
        })
    return results


def check_floor_capacity(model: ifcopenshell.file) -> list:
    """
    Art. 128 — Maximum floors the foundation can bear.
    max_floors = floor(bearing_capacity / floor_load_per_m2)
    addable_floors = max_floors - existing_floors
    """
    scale = _get_length_scale(model)
    n_existing = max(len(model.by_type("IfcBuildingStorey")), 1)

    floor_load = DEFAULT_FLOOR_LOAD_KN_M2
    spaces = model.by_type("IfcSpace")
    if spaces:
        val = _get_pset_value(spaces[0], "DesignLoad", "FloorLoad", "LoadBearingCapacity")
        if val is not None:
            try:
                floor_load = float(val)
            except (TypeError, ValueError):
                pass

    footings = list(model.by_type("IfcFooting"))
    if not footings:
        return [{
            "element_id":        None,
            "element_type":      "IfcFooting",
            "element_name":      "No footings found",
            "element_name_long": "Art. 128 — No IfcFooting elements in model",
            "check_status":      "blocked",
            "actual_value":      None,
            "required_value":    None,
            "comment":           "Cannot compute floor capacity without IfcFooting elements",
            "log":               None,
        }]

    if floor_load <= 0:
        floor_load = DEFAULT_FLOOR_LOAD_KN_M2

    results = []
    for footing in footings:
        name = footing.Name or f"Footing #{footing.id()}"

        bearing_val = _get_pset_value(
            footing,
            "BearingCapacity", "AllowableBearingCapacity",
            "WorkingStress", "FatiguesDeTraball", "SoilBearingCapacity",
        )
        used_default = bearing_val is None
        bearing = float(bearing_val) if not used_default else DEFAULT_BEARING_CAPACITY_KN_M2
        if bearing <= 0:
            bearing = DEFAULT_BEARING_CAPACITY_KN_M2
            used_default = True

        max_floors = int(bearing / floor_load)
        addable = max_floors - n_existing

        if addable > 0:
            status = "pass"
            comment = (f"Art. 128: {addable} floor(s) can be added. "
                       f"Current: {n_existing}, capacity: {max_floors}")
        elif addable == 0:
            status = "warning"
            comment = (f"Art. 128: Foundation is at capacity — no additional floors possible. "
                       f"Current: {n_existing} = max: {max_floors}")
        else:
            status = "fail"
            comment = (f"Art. 128: Existing {n_existing} floors exceeds capacity of "
                       f"{max_floors} floors by {abs(addable)}. Underpinning required.")

        default_note = " [bearing: default 150 kN/m²]" if used_default else ""

        results.append({
            "element_id":        footing.GlobalId,
            "element_type":      "IfcFooting",
            "element_name":      name,
            "element_name_long": f"{name} — Art. 128 Floor Capacity",
            "check_status":      status,
            "actual_value":      f"{n_existing} existing floors",
            "required_value":    (f"max {max_floors} floors "
                                  f"(σ={bearing} kN/m², q={floor_load} kN/m²){default_note}"),
            "comment":           comment,
            "log":               (f"bearing={bearing}kN/m² q={floor_load}kN/m² "
                                  f"max={max_floors} existing={n_existing} "
                                  f"addable={addable}"),
        })
    return results
