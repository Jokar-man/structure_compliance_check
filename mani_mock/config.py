"""
Central configuration for the IFCore compliance platform.
"""

# ── Application ───────────────────────────────────────────────
APP_TITLE = "IFCore — Integrated Compliance Platform"
APP_VERSION = "0.1.0"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 7860

# ── Default thresholds (Spanish DB SUA & Catalan Decree 141/2012) ──
THRESHOLDS = {
    "door_width_mm":          800,
    "window_height_mm":      1200,
    "wall_thickness_mm":      100,
    "wall_height_mm":        2500,
    "slab_thickness_mm":      150,
    "slab_max_thickness_mm":  200,
    "column_min_dim_mm":      250,
    "beam_depth_mm":          200,
    "beam_width_mm":          150,
    "opening_height_mm":     2000,
    "corridor_width_mm":     1100,
    "room_area_m2":           5.0,
    "ceiling_height_mm":     2200,
    "stair_riser_min_mm":     130,
    "stair_riser_max_mm":     185,
    "stair_tread_mm":         280,
    "railing_height_mm":      900,
    "wall_max_u_value":       0.80,
    "foundation_min_mm":      200,
}

# ── Region codes ──────────────────────────────────────────────
REGIONS = {
    "ES": "Spain (DB SUA / EHE / CTE)",
    "CAT": "Catalonia (Decree 141/2012)",
}
DEFAULT_REGION = "ES"
