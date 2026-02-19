def make_report(walls, rule_results):
    lines = []
    lines.append(f"Total walls: {len(walls)}")
    lines.append("")
    lines.extend(rule_results)
    return lines

def summarize(lines):
    p = sum(1 for s in lines if s.startswith("[PASS]"))
    f = sum(1 for s in lines if s.startswith("[FAIL]"))
    u = sum(1 for s in lines if s.startswith("[???]"))
    return [f"[PASS] count={p}", f"[FAIL] count={f}", f"[???] count={u}"]
