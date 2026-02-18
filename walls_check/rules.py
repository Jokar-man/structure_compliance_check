def rule_min_thickness(walls, min_mm=100):
    min_m = min_mm / 1000
    out = []
    for w in walls:
        t = w.get("Thickness_m")
        if t is None:
            out.append(f"[WARN] {w['GlobalId']} thickness missing (source={w['ThicknessSource']})")
        elif t < min_m:
            out.append(f"[FAIL] {w['GlobalId']} {w['Name']} thickness={t:.3f}m < {min_m:.3f}m")
    return out or [f"[PASS] All walls >= {min_mm}mm"]
