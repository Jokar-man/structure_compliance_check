"""Slab compliance checks per Eurocode 2 / Codigo Estructural.

Pure Python module -- no web framework dependencies.
Import and call individual check functions or use run_all_checks().

Each check function has the signature:
    check_*(params: dict) -> tuple[bool, dict]
    Returns (compliant: bool, details: dict)
"""

import math

import numpy as np
import ifcopenshell
import ifcopenshell.util.element


# ══════════════════════════════════════════════════════════════════
# CONSTANTS -- EC2 / Codigo Estructural (Anejo 19)
# ══════════════════════════════════════════════════════════════════

# -- Material partial safety factors (EC2 Table 2.1N) --
GAMMA_C = 1.5       # Concrete
GAMMA_S = 1.15      # Reinforcing steel

# -- Punching / shear design constant --
C_RD_C = 0.18 / GAMMA_C   # = 0.12

# -- Slab thickness limits (mm) --
MIN_THICKNESS_MM = 100
MAX_THICKNESS_MM = 200

# -- K-factors for span/depth calculation (EC2 Table 7.4N) --
K_FACTORS: dict[str, float] = {
    "simply_supported": 1.0,
    "one_way_end_span": 1.3,
    "one_way_continuous": 1.5,
    "two_way_continuous": 1.5,
    "flat_slab": 1.2,
    "cantilever": 0.4,
}

# -- Basic span/depth ratio limits (EC2 Table 7.4N, rho = 0.5%, concrete C30) --
SPAN_DEPTH_RATIOS: dict[str, float] = {
    "simply_supported": 20.0,
    "one_way_end_span": 26.0,
    "one_way_continuous": 30.0,
    "two_way_continuous": 30.0,
    "flat_slab": 24.0,
    "cantilever": 8.0,
}

# -- Minimum durability cover c_min,dur (mm) -- EC2 Table 4.4N (class S4) --
MIN_COVER_BY_EXPOSURE: dict[str, int] = {
    "X0": 10, "XC1": 15, "XC2": 25, "XC3": 25, "XC4": 30,
    "XD1": 35, "XD2": 40, "XD3": 45,
    "XS1": 35, "XS2": 40, "XS3": 45,
}

# -- Maximum crack width limits w_max (mm) -- EC2 Table 7.1N --
CRACK_LIMITS: dict[str, float] = {
    "X0": 0.4, "XC1": 0.4,
    "XC2": 0.3, "XC3": 0.3, "XC4": 0.3,
    "XD1": 0.3, "XD2": 0.3, "XD3": 0.2,
    "XS1": 0.3, "XS2": 0.3, "XS3": 0.2,
}


# ══════════════════════════════════════════════════════════════════
# INPUT PARAMETERS & GEOMETRY HELPERS
# ══════════════════════════════════════════════════════════════════

def input_params(
    slab_type: str = "one_way_continuous",
    L: float = 6.0,
    h: float = 250.0,
    cover: float = 30.0,
    phi: float = 12.0,
    f_ck: float = 30.0,
    f_yk: float = 500.0,
    exposure: str = "XC3",
    q_k: float = 3.0,
    g_k: float = 5.0,
    rho_l: float = 0.005,
    beta: float = 1.5,
    u_1: float = 2000.0,
) -> dict:
    """Return a default parameter dict for slab design checks.

    All values can be overridden via keyword arguments.
    Derived values (d, f_cd, f_yd, V_Ed, c_nom, etc.) are computed
    automatically so the dict is ready for every check function.
    """
    d = calculate_effective_depth(h, cover, phi)

    # Design material strengths
    f_cd = f_ck / GAMMA_C        # MPa
    f_yd = f_yk / GAMMA_S        # MPa

    # ULS load combination (EC0 Eq. 6.10): 1.35*g_k + 1.5*q_k (kN/m2)
    q_uls = np.float64(1.35 * g_k + 1.5 * q_k)

    # Approximate punching shear force for a 1 m strip
    V_Ed = float(q_uls * L)      # kN per metre width (simplified)

    return {
        # Geometry
        "slab_type": slab_type,
        "type": slab_type,
        "L": L,
        "h": h,
        "cover": cover,
        "phi": phi,
        "d": float(d),
        # Materials
        "f_ck": f_ck,
        "f_yk": f_yk,
        "f_cd": round(float(f_cd), 2),
        "f_yd": round(float(f_yd), 2),
        # Exposure & cracking
        "exposure": exposure,
        "exposure_class": exposure,
        "c_nom": cover,
        "w_max": CRACK_LIMITS.get(exposure, 0.3),
        # Loading
        "g_k": g_k,
        "q_k": q_k,
        "q_uls": round(float(q_uls), 2),
        # Reinforcement
        "rho_l": rho_l,
        "rho": rho_l * 100.0,     # percentage for deflection check
        # Punching shear
        "beta": beta,
        "u_1": u_1,
        "V_Ed": round(float(V_Ed), 2),
    }


def calculate_effective_depth(
    h: float, cover: float, phi: float
) -> float:
    """Effective depth: d = h - cover - phi/2 (all in mm).

    Uses numpy for consistency with array-based calcs.
    """
    h = np.float64(h)
    cover = np.float64(cover)
    phi = np.float64(phi)
    d = h - cover - phi / 2.0
    if d <= 0:
        raise ValueError(
            f"Effective depth must be > 0: h={h}, cover={cover}, phi={phi} -> d={d}"
        )
    return round(float(d), 2)


# ── IFC helpers ──────────────────────────────────────────────────

def get_slab_thickness(slab) -> float | None:
    """Extract total thickness (mm) of an IfcSlab from material layers."""
    material = ifcopenshell.util.element.get_material(slab)
    if material is not None:
        layer_set = None
        if material.is_a("IfcMaterialLayerSetUsage"):
            layer_set = material.ForLayerSet
        elif material.is_a("IfcMaterialLayerSet"):
            layer_set = material
        if layer_set is not None:
            return round(sum(l.LayerThickness for l in layer_set.MaterialLayers), 2)

    for rel in slab.IsDefinedBy:
        if rel.is_a("IfcRelDefinesByProperties"):
            pset = rel.RelatingPropertyDefinition
            if pset.is_a("IfcElementQuantity") and "Slab" in (pset.Name or ""):
                for q in pset.Quantities:
                    if q.is_a("IfcQuantityLength") and q.Name in ("Width", "Depth", "Height"):
                        return round(q.LengthValue, 2)
    return None


def get_storey_name(slab) -> str:
    """Return the building storey name for a slab element."""
    storey = ifcopenshell.util.element.get_container(slab)
    if storey is not None and storey.is_a("IfcBuildingStorey"):
        return storey.Name or f"Storey (#{storey.id()})"
    return "Unknown Storey"


# ── 1. Slab Thickness Check (IFC-based) ─────────────────────────

def check_slab_thickness(ifc_path: str) -> tuple[bool, list[dict]]:
    """Check every IfcSlab thickness is within MIN/MAX range.

    Parameters:
        ifc_path – Path to an IFC file.

    Returns:
        (all_pass, results)
        all_pass – True if every slab with a measurable thickness passes.
        results  – List of per-slab dicts with keys:
                   name, storey, thickness_mm, status ('PASS'|'FAIL'|'N/A')
    """
    model = ifcopenshell.open(ifc_path)
    slabs = model.by_type("IfcSlab")
    if not slabs:
        return True, []

    results = []
    all_pass = True

    for slab in slabs:
        name = slab.Name or f"Slab #{slab.id()}"
        storey = get_storey_name(slab)
        thickness = get_slab_thickness(slab)

        if thickness is None:
            status = "N/A"
        elif MIN_THICKNESS_MM <= thickness <= MAX_THICKNESS_MM:
            status = "PASS"
        else:
            status = "FAIL"
            all_pass = False

        results.append({
            "name": name,
            "storey": storey,
            "thickness_mm": thickness,
            "status": status,
        })

    return all_pass, results


# ── 2. Punching Shear Check (EC2 Sec.6.4) ──────────────────────────

def check_punching_shear(params: dict) -> tuple[bool, dict]:
    """Punching shear resistance without shear reinforcement.

    Params:
        V_Ed  – Design shear force (kN)
        u_1   – Control perimeter (mm)
        d     – Effective depth (mm)
        f_ck  – Concrete strength (MPa)
        rho_l – Reinforcement ratio (dimensionless, capped at 0.02)
        beta  – Load factor (default 1.15)
    """
    V_Ed = params["V_Ed"]
    u_1 = params["u_1"]
    d = params["d"]
    f_ck = params["f_ck"]
    rho_l = min(params["rho_l"], 0.02)
    beta = params.get("beta", 1.15)

    k = min(1.0 + math.sqrt(200.0 / d), 2.0)
    v_Rd_c = C_RD_C * k * (100.0 * rho_l * f_ck) ** (1.0 / 3.0)
    v_min = 0.035 * k ** 1.5 * f_ck ** 0.5
    v_Rd_c = max(v_Rd_c, v_min)

    V_Rd_c = v_Rd_c * u_1 * d / 1000.0
    v_Ed = beta * V_Ed * 1000.0 / (u_1 * d)
    compliant = (beta * V_Ed) <= V_Rd_c

    return compliant, {
        "k": round(k, 4),
        "C_Rd_c": round(C_RD_C, 4),
        "v_Rd_c_MPa": round(v_Rd_c, 4),
        "v_min_MPa": round(v_min, 4),
        "V_Rd_c_kN": round(V_Rd_c, 2),
        "v_Ed_MPa": round(v_Ed, 4),
        "beta_V_Ed_kN": round(beta * V_Ed, 2),
        "utilisation": round((beta * V_Ed) / V_Rd_c, 4) if V_Rd_c > 0 else None,
    }


# ── 3. SLS Deflection Check (EC2 Sec.7.4.2) ────────────────────────

def check_sls_deflection(params: dict) -> tuple[bool, dict]:
    """Span/depth ratio check.

    Params:
        L         – Span (m)
        d         – Effective depth (mm)
        rho       – Tension reinforcement ratio (%)
        f_ck      – Concrete strength (MPa)
        type      – Slab type key from K_FACTORS (default 'one_way_continuous')
        rho_prime – Compression reinforcement ratio (%, default 0)
    """
    L = params["L"]
    d = params["d"]
    rho_pct = params["rho"]
    f_ck = params["f_ck"]
    slab_type = params.get("type", "one_way_continuous")
    rho_prime_pct = params.get("rho_prime", 0.0)

    if d <= 0:
        raise ValueError(f"d must be > 0, got {d}")
    if L <= 0:
        raise ValueError(f"L must be > 0, got {L}")
    if rho_pct <= 0:
        raise ValueError(f"rho must be > 0, got {rho_pct}")
    if f_ck <= 0:
        raise ValueError(f"f_ck must be > 0, got {f_ck}")
    if slab_type not in K_FACTORS:
        raise ValueError(f"Unknown type '{slab_type}'. Valid: {', '.join(K_FACTORS)}")

    K = K_FACTORS[slab_type]
    rho = rho_pct / 100.0
    rho_prime = rho_prime_pct / 100.0
    rho_0 = 1e-3 * math.sqrt(f_ck)

    if rho <= rho_0:
        ld_limit = K * (
            11.0
            + 1.5 * math.sqrt(f_ck) * rho_0 / rho
            + 3.2 * math.sqrt(f_ck) * (rho_0 / rho - 1.0) ** 1.5
        )
    else:
        ld_limit = K * (
            11.0
            + 1.5 * math.sqrt(f_ck) * rho_0 / (rho - rho_prime)
            + (1.0 / 12.0) * math.sqrt(f_ck) * math.sqrt(rho_prime / rho_0)
        )

    ld_actual = L / (d / 1000.0)
    compliant = ld_actual <= ld_limit

    return compliant, {
        "K": K,
        "slab_type": slab_type,
        "rho_0": round(rho_0, 6),
        "rho": round(rho, 6),
        "ld_limit": round(ld_limit, 2),
        "ld_actual": round(ld_actual, 2),
        "utilisation": round(ld_actual / ld_limit, 4) if ld_limit > 0 else None,
    }


# ── 4. Concrete Cover Check (EC2 Sec.4.4) ──────────────────────────

def check_concrete_cover(params: dict) -> tuple[bool, dict]:
    """Validate nominal cover against exposure class.

    Params:
        c_nom          – Nominal cover (mm)
        exposure_class – e.g. 'XC1', 'XD2'
        delta_c_dev    – Deviation allowance (mm, default 10)
    """
    c_nom = params["c_nom"]
    exposure = params["exposure_class"].upper().strip()
    delta_c_dev = params.get("delta_c_dev", 10)

    if exposure not in MIN_COVER_BY_EXPOSURE:
        raise ValueError(
            f"Unknown exposure '{exposure}'. Valid: {', '.join(sorted(MIN_COVER_BY_EXPOSURE))}"
        )
    if c_nom < 0:
        raise ValueError(f"c_nom must be >= 0, got {c_nom}")

    c_min_dur = MIN_COVER_BY_EXPOSURE[exposure]
    c_nom_required = c_min_dur + delta_c_dev
    compliant = c_nom >= c_nom_required

    return compliant, {
        "exposure_class": exposure,
        "c_min_dur_mm": c_min_dur,
        "delta_c_dev_mm": delta_c_dev,
        "c_nom_required_mm": c_nom_required,
        "c_nom_provided_mm": c_nom,
        "margin_mm": round(c_nom - c_nom_required, 2),
    }


# ── 5. ULS Bending Check (EC2 Sec.6.1) ──────────────────────────

def uls_bending_check(params: dict) -> tuple[bool, dict]:
    """ULS bending moment check for a simply-supported 1 m slab strip.

    Params:
        g_k  -- Permanent load (kN/m2)
        q_k  -- Variable load (kN/m2)
        L    -- Span (m)
        d    -- Effective depth (mm), or h/cover/phi to compute it
        f_ck -- Concrete characteristic strength (MPa)
        b    -- Slab width (mm, default 1000 for per-metre check)

    Formulas (EC2 Sec.6.1, simplified rectangular stress block):
        M_Ed  = (1.35*g_k + 1.5*q_k) * L^2 / 8   [kNm/m]
        f_cd  = f_ck / gamma_c
        M_Rd  = 0.167 * f_cd * b_m * d_m^2 * 1000  [kNm]
        (0.167 = mu_lim for x/d <= 0.45, ductility class B/C)
    """
    g_k = params["g_k"]
    q_k = params["q_k"]
    L = params["L"]
    f_ck = params["f_ck"]
    b = params.get("b", 1000.0)   # mm

    # Effective depth -- use 'd' directly, or compute from h/cover/phi
    if "d" in params:
        d = params["d"]
    else:
        d = calculate_effective_depth(params["h"], params["cover"], params["phi"])

    if d <= 0:
        raise ValueError(f"d must be > 0, got {d}")
    if L <= 0:
        raise ValueError(f"L must be > 0, got {L}")

    # Convert units
    d_m = d / 1000.0              # mm -> m
    b_m = b / 1000.0              # mm -> m  (1.0 for 1 m strip)

    # Design concrete strength
    f_cd = f_ck / GAMMA_C         # MPa

    # Design bending moment (simply-supported UDL)
    q_uls = 1.35 * g_k + 1.5 * q_k   # kN/m2
    M_Ed = q_uls * L ** 2 / 8.0      # kNm per metre width

    # Moment resistance (simplified rectangular block, mu_lim = 0.167)
    # M_Rd = mu_lim * f_cd * b_m * d_m^2  (units: MPa * m * m^2 = MN*m = 1000 kNm)
    M_Rd = 0.167 * f_cd * b_m * d_m ** 2 * 1000.0   # kNm

    compliant = M_Ed <= M_Rd

    return compliant, {
        "g_k_kN_m2": g_k,
        "q_k_kN_m2": q_k,
        "q_uls_kN_m2": round(q_uls, 2),
        "L_m": L,
        "d_mm": round(d, 1),
        "b_mm": b,
        "f_cd_MPa": round(f_cd, 2),
        "M_Ed_kNm": round(M_Ed, 2),
        "M_Rd_kNm": round(M_Rd, 2),
        "utilisation": round(M_Ed / M_Rd, 4) if M_Rd > 0 else None,
    }


# ── 6. ULS Punching Shear Check (EC2 Sec.6.3/6.4) ───────────────

def uls_punching_check(params: dict) -> tuple[bool, dict]:
    """ULS punching shear for flat slabs -- auto-computes V_Ed from loads.

    Params:
        g_k   -- Permanent load (kN/m2)
        q_k   -- Variable load (kN/m2)
        L     -- Column spacing / span (m)
        d     -- Effective depth (mm)
        f_ck  -- Concrete strength (MPa)
        rho_l -- Reinforcement ratio (dimensionless, capped at 0.02)
        u_1   -- Control perimeter at 2d from column face (mm)
        beta  -- Eccentricity factor (default 1.15 interior)

    V_Ed is estimated as the reaction on an interior column with
    tributary area (L/2)^2 on each side:
        V_Ed = beta * q_uls * (L/2)^2   [kN]

    Resistance per EC2 Sec.6.4:
        k     = min(1 + sqrt(200/d), 2)
        v_Rd_c = max(C_RD_C*k*(100*rho_l*f_ck)^(1/3), v_min)  [MPa]
        V_Rd_c = v_Rd_c * u_1 * d / 1000                       [kN]
    """
    g_k = params["g_k"]
    q_k = params["q_k"]
    L = params["L"]
    d = params["d"]
    f_ck = params["f_ck"]
    rho_l = min(params.get("rho_l", 0.005), 0.02)
    u_1 = params["u_1"]
    beta = params.get("beta", 1.15)

    if d <= 0:
        raise ValueError(f"d must be > 0, got {d}")

    # -- ULS load & design shear force --
    q_uls = 1.35 * g_k + 1.5 * q_k           # kN/m2
    A_trib = (L / 2.0) ** 2                   # m2, quarter-panel tributary area
    V_Ed = beta * q_uls * A_trib              # kN

    # -- Size effect factor --
    k = min(1.0 + math.sqrt(200.0 / d), 2.0)

    # -- Concrete shear resistance (stress) --
    v_Rd_c = C_RD_C * k * (100.0 * rho_l * f_ck) ** (1.0 / 3.0)   # MPa
    v_min = 0.035 * k ** 1.5 * f_ck ** 0.5                         # MPa
    v_Rd_c = max(v_Rd_c, v_min)

    # -- Resistance force --
    # v_Rd_c [N/mm2] * u_1 [mm] * d [mm] = N;  / 1000 = kN
    V_Rd_c = v_Rd_c * u_1 * d / 1000.0       # kN

    # -- Applied shear stress for reporting --
    v_Ed = V_Ed * 1000.0 / (u_1 * d)         # MPa

    compliant = V_Ed <= V_Rd_c

    return compliant, {
        "q_uls_kN_m2": round(q_uls, 2),
        "A_trib_m2": round(A_trib, 2),
        "V_Ed_kN": round(V_Ed, 2),
        "k": round(k, 4),
        "v_Rd_c_MPa": round(v_Rd_c, 4),
        "v_min_MPa": round(v_min, 4),
        "V_Rd_c_kN": round(V_Rd_c, 2),
        "v_Ed_MPa": round(v_Ed, 4),
        "utilisation": round(V_Ed / V_Rd_c, 4) if V_Rd_c > 0 else None,
    }


# ── 7. SLS Deflection -- Tabulated (Table 7.2.2.a) ──────────────

def sls_deflection_check(params: dict) -> tuple[bool, dict]:
    """Simplified SLS deflection check using tabulated span/depth limits.

    Uses SPAN_DEPTH_RATIOS (EC2 Table 7.4N / Codigo Estructural Table 7.2.2.a)
    directly, without the detailed rho-based formula.

    Params:
        L         -- Span (m)
        d         -- Effective depth (mm), or h/cover/phi to compute it
        slab_type -- Key from SPAN_DEPTH_RATIOS (default 'simply_supported')

    Formulas:
        limit_L_d  = SPAN_DEPTH_RATIOS[slab_type]
        actual_L_d = L * 1000 / d        (L in m -> mm, d in mm)
        Check: actual_L_d <= limit_L_d
    """
    L = params["L"]
    slab_type = params.get("slab_type", params.get("type", "simply_supported"))

    # Effective depth -- use 'd' directly, or compute from h/cover/phi
    if "d" in params:
        d = params["d"]
    else:
        d = calculate_effective_depth(params["h"], params["cover"], params["phi"])

    if d <= 0:
        raise ValueError(f"d must be > 0, got {d}")
    if L <= 0:
        raise ValueError(f"L must be > 0, got {L}")
    if slab_type not in SPAN_DEPTH_RATIOS:
        raise ValueError(
            f"Unknown slab_type '{slab_type}'. "
            f"Valid: {', '.join(SPAN_DEPTH_RATIOS)}"
        )

    limit_L_d = SPAN_DEPTH_RATIOS[slab_type]
    actual_L_d = L * 1000.0 / d       # both in mm

    compliant = actual_L_d <= limit_L_d

    return compliant, {
        "slab_type": slab_type,
        "L_m": L,
        "d_mm": round(d, 1),
        "limit_L_d": limit_L_d,
        "actual_L_d": round(actual_L_d, 2),
        "utilisation": round(actual_L_d / limit_L_d, 4) if limit_L_d > 0 else None,
    }


# ── Check Registry ──────────────────────────────────────────────

_CHECKS: list[tuple[str, callable, set[str]]] = [
    ("ULS Bending (EC2 Sec.6.1)",           uls_bending_check,       {"g_k", "q_k", "L", "f_ck"}),
    ("ULS Punching (EC2 Sec.6.3)",          uls_punching_check,      {"g_k", "q_k", "L", "d", "f_ck", "u_1"}),
    ("Punching Shear Direct (EC2 Sec.6.4)", check_punching_shear,    {"V_Ed", "u_1", "d", "f_ck", "rho_l"}),
    ("SLS Deflection Table (7.2.2.a)",      sls_deflection_check,    {"L"}),
    ("SLS Deflection Full (EC2 Sec.7.4.2)", check_sls_deflection,    {"L", "d", "rho", "f_ck"}),
    ("Concrete Cover (EC2 Sec.4.4)",        check_concrete_cover,    {"c_nom", "exposure_class"}),
]


# ── Main Runner ──────────────────────────────────────────────────

def run_all_checks(params: dict, ifc_path: str | None = None) -> list[dict]:
    """Run all slab compliance checks and return a report.

    Parameters:
        params   – Dict with input values for parametric checks.
        ifc_path – Optional path to an IFC file for thickness check.

    Returns:
        List of dicts, each with keys: 'check', 'status', 'details'.
        Status is one of: 'PASS', 'FAIL', 'SKIPPED', 'ERROR'.
    """
    report: list[dict] = []

    # IFC thickness check
    if ifc_path:
        try:
            ok, slab_results = check_slab_thickness(ifc_path)
            report.append({
                "check": "Slab Thickness (100-200 mm)",
                "status": "PASS" if ok else "FAIL",
                "details": slab_results,
            })
        except Exception as e:
            report.append({
                "check": "Slab Thickness (100-200 mm)",
                "status": "ERROR",
                "details": str(e),
            })
    else:
        report.append({
            "check": "Slab Thickness (100-200 mm)",
            "status": "SKIPPED",
            "details": "No IFC file provided",
        })

    # Parametric checks
    for name, fn, required_keys in _CHECKS:
        if not required_keys.issubset(params):
            missing = required_keys - params.keys()
            report.append({
                "check": name,
                "status": "SKIPPED",
                "details": f"Missing: {', '.join(sorted(missing))}",
            })
            continue
        try:
            compliant, details = fn(params)
            report.append({
                "check": name,
                "status": "PASS" if compliant else "FAIL",
                "details": details,
            })
        except Exception as e:
            report.append({
                "check": name,
                "status": "ERROR",
                "details": str(e),
            })

    return report


def print_report(report: list[dict]) -> None:
    """Pretty-print a compliance report to the console."""
    print("\n" + "=" * 60)
    print("  SLAB COMPLIANCE REPORT -- EC2 / Codigo Estructural")
    print("=" * 60)

    for entry in report:
        status = entry["status"]
        icon = {"PASS": "[OK]", "FAIL": "[!!]", "SKIPPED": "[--]", "ERROR": "[XX]"}.get(status, "[??]")
        print(f"\n{icon} {entry['check']}  ->  {status}")

        details = entry["details"]
        if isinstance(details, list):
            for item in details:
                t = item.get("thickness_mm", "N/A")
                print(f"     {item['storey']} / {item['name']}: {t} mm -> {item['status']}")
        elif isinstance(details, dict):
            for k, v in details.items():
                print(f"     {k}: {v}")
        else:
            print(f"     {details}")

    print("\n" + "=" * 60)
    passed = sum(1 for e in report if e["status"] == "PASS")
    failed = sum(1 for e in report if e["status"] == "FAIL")
    print(f"  Summary: {passed} PASS, {failed} FAIL, "
          f"{len(report) - passed - failed} SKIPPED/ERROR")
    print("=" * 60 + "\n")


# ── CLI entry point ──────────────────────────────────────────────

if __name__ == "__main__":
    # Example usage -- run with: python slab_check/slab.py
    params = input_params()   # defaults: C30, 250mm slab, XC3, 6m span

    print("Input parameters:")
    for k, v in params.items():
        print(f"  {k}: {v}")

    print(f"\nEffective depth d = {params['d']} mm")
    print(f"Design strengths: f_cd = {params['f_cd']} MPa, "
          f"f_yd = {params['f_yd']} MPa")
    print(f"ULS load: q_uls = {params['q_uls']} kN/m2")
    print(f"Crack limit w_max = {params['w_max']} mm")

    report = run_all_checks(params)
    print_report(report)
