"""
IFC Wall Compliance Checker

This module analyzes IFC wall elements and generates compliance reports
including dimensions, properties, and requirements.
Functions returning [PASS]/[FAIL]/[???]

"""

import ifcopenshell

try:
    from .extractor import extract_walls
    from . import rules
    from .report import make_report, summarize
except ImportError:
    from extractor import extract_walls
    import rules
    from report import make_report, summarize


def _collect_rule_results(walls, min_mm=100, max_u=0.80):
    results = []
    results += rules.rule_min_thickness(walls, min_mm=min_mm)
    results += rules.rule_max_uvalue(walls, max_u=max_u)
    results += rules.rule_external_walls_must_have_uvalue(walls)
    return results


def run_wall_checks(ifc_path, min_mm=100, max_u=0.80, include_summary=True):
    model = ifcopenshell.open(ifc_path)
    walls = extract_walls(model)
    results = _collect_rule_results(walls, min_mm=min_mm, max_u=max_u)

    lines = make_report(walls, results)
    if include_summary:
        lines.append("")
        lines.extend(summarize(results))
    return lines


def run(ifc_path, min_mm=100, max_u=0.80, include_summary=True):
    return run_wall_checks(ifc_path, min_mm=min_mm, max_u=max_u, include_summary=include_summary)


if __name__ == "__main__":
    import sys
    for line in run_wall_checks(sys.argv[1]):
        print(line)
