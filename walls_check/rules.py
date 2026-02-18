"""this files converts regulations into rules that take 
the list of wall dicts and return a list of strings with 
the results"""

def rule_min_thickness(walls, min_mm=100):
    out = []
    for w in walls:
        t = w.get("Thickness_mm")
        gid = w.get("GlobalId", "NO_ID")
        name = w.get("Name", "Unnamed")

        if t is None:
            out.append(f"[???] IfcWall {gid} {name}: thickness unknown (need Thickness_mm)")
        elif t < min_mm:
            out.append(f"[FAIL] IfcWall {gid} {name}: thickness={t:.1f}mm < {min_mm}mm")
        else:
            out.append(f"[PASS] IfcWall {gid} {name}: thickness={t:.1f}mm >= {min_mm}mm")
    return out or [f"[???]"]

def rule_max_uvalue(walls, max_u=0.80):
    out = []
    for w in walls:
        u = w.get("ThermalTransmittance")
        gid = w.get("GlobalId","NO_ID")
        name = w.get("Name","Unnamed")

        if u is None:
            out.append(f"[???] IfcWall {gid} {name}: U-value unknown")
        elif float(u) > max_u:
            out.append(f"[FAIL] IfcWall {gid} {name}: U={float(u):.3f} > {max_u}")
        else:
            out.append(f"[PASS] IfcWall {gid} {name}: U={float(u):.3f} <= {max_u}")
    return out

def rule_external_walls_must_have_uvalue(walls):
    out = []
    for w in walls:
        ext = w.get("IsExternal")
        u = w.get("ThermalTransmittance")
        gid = w.get("GlobalId","NO_ID")
        name = w.get("Name","Unnamed")

        if ext is True and u is None:
            out.append(f"[FAIL] IfcWall {gid} {name}: IsExternal=True but U-value missing")
        else:
            out.append(f"[PASS] IfcWall {gid} {name}: external/U-value OK")
    return out
