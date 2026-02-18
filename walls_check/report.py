def make_report(walls, rule_results):
    lines = []
    lines.append(f"Total walls: {len(walls)}")
    lines.append("")
    lines.extend(rule_results)
    return lines
