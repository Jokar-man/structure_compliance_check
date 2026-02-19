"""
Shared IFC utility functions used by team adapters.
"""

import ifcopenshell
import ifcopenshell.util.element


# ── Property extraction ──────────────────────────────────────

def get_pset_value(element, pset_name: str, prop_name: str):
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


def search_psets(element, prop_name: str):
    """Search ALL property sets for a property by name. Returns first numeric match."""
    try:
        psets = ifcopenshell.util.element.get_psets(element)
        for _pset_name, props in psets.items():
            if isinstance(props, dict) and prop_name in props:
                v = props[prop_name]
                if v is not None and v != "" and isinstance(v, (int, float)):
                    return v
    except Exception:
        pass
    return None


# ── Unit helpers ─────────────────────────────────────────────

def to_mm(value_m):
    """Convert a value (assumed metres) to millimetres.

    Heuristic: if value > 100 it's probably already in mm.
    """
    if value_m is None:
        return None
    if value_m > 100:
        return round(value_m)
    return round(value_m * 1000)


def safe_float(x):
    """Try to convert x to float, return None on failure."""
    try:
        return float(x) if x is not None else None
    except (ValueError, TypeError):
        return None


# ── Material helpers ─────────────────────────────────────────

def get_material_total_thickness(element):
    """Sum the thicknesses of all material layers (in model units), or None."""
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


# ── Element label ────────────────────────────────────────────

def label(element) -> str:
    """Return a readable label for an IFC element."""
    name = element.Name or element.GlobalId
    return f"{element.is_a()} '{name}'"
