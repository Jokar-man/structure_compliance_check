"""Wall compliance rules producing [PASS]/[FAIL]/[???] result lines."""
import re
import unicodedata

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
        for v in values:
            norm = _normalize_text(v)
            if norm:
                texts.append(norm)
    # Preserve order, remove duplicates.
    return list(dict.fromkeys(texts))


def _contains_keyword(text, keyword):
    # Word boundary matching to avoid partial matches.
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
        "texts": texts,
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
            # No reliable room-type signal: apply conservative interpretation.
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
