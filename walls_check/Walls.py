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


def _collect_rule_results(
    walls,
    min_mm=100,
    max_u=0.80,
    min_height_mm=2500,
    min_service_height_mm=2200,
    climate_zone=None,
    use_space_aware_height=True,
):
    results = []
    results += rules.rule_min_thickness(walls, min_mm=min_mm)
    if use_space_aware_height:
        results += rules.rule_min_height_by_space_use(
            walls,
            min_general_mm=min_height_mm,
            min_service_mm=min_service_height_mm,
        )
    else:
        results += rules.rule_min_height(walls, min_height_mm=min_height_mm)
    if climate_zone:
        results += rules.rule_external_uvalue_by_climate_zone(walls, climate_zone=climate_zone)
    else:
        results += rules.rule_max_uvalue(walls, max_u=max_u)
    results += rules.rule_external_walls_must_have_uvalue(walls)
    results += rules.rule_loadbearing_requires_fire_rating(walls)
    results += rules.rule_space_boundary_linkage(walls)
    return results


def run_wall_checks(
    ifc_path,
    min_mm=100,
    max_u=0.80,
    include_summary=True,
    min_height_mm=2500,
    min_service_height_mm=2200,
    climate_zone=None,
    use_space_aware_height=True,
):
    model = ifcopenshell.open(ifc_path)
    walls = extract_walls(model)
    results = _collect_rule_results(
        walls,
        min_mm=min_mm,
        max_u=max_u,
        min_height_mm=min_height_mm,
        min_service_height_mm=min_service_height_mm,
        climate_zone=climate_zone,
        use_space_aware_height=use_space_aware_height,
    )

    lines = make_report(walls, results)
    if include_summary:
        lines.append("")
        lines.extend(summarize(results))
    return lines


def run(
    ifc_path,
    min_mm=100,
    max_u=0.80,
    include_summary=True,
    min_height_mm=2500,
    min_service_height_mm=2200,
    climate_zone=None,
    use_space_aware_height=True,
):
    return run_wall_checks(
        ifc_path,
        min_mm=min_mm,
        max_u=max_u,
        min_height_mm=min_height_mm,
        min_service_height_mm=min_service_height_mm,
        climate_zone=climate_zone,
        use_space_aware_height=use_space_aware_height,
        include_summary=include_summary,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run IFC wall compliance checks.")
    parser.add_argument("ifc_path", help="Path to IFC file")
    parser.add_argument("--min-mm", type=float, default=100, help="Minimum wall thickness in mm")
    parser.add_argument("--max-u", type=float, default=0.80, help="Maximum wall U-value (W/m2K) for custom mode")
    parser.add_argument("--min-height-mm", type=float, default=2500, help="General minimum wall height in mm")
    parser.add_argument(
        "--min-service-height-mm",
        type=float,
        default=2200,
        help="Minimum wall height in service spaces (kitchen/bath/corridor) in mm",
    )
    parser.add_argument(
        "--climate-zone",
        default=None,
        help="Optional CTE climate zone for external walls (A, B, C, D, E). If set, overrides --max-u.",
    )
    parser.add_argument(
        "--disable-space-aware-height",
        action="store_true",
        help="Disable room-type-aware height logic and use only --min-height-mm.",
    )
    parser.add_argument("--no-summary", action="store_true", help="Disable summary counts at end of report")
    args = parser.parse_args()

    for line in run_wall_checks(
        args.ifc_path,
        min_mm=args.min_mm,
        max_u=args.max_u,
        min_height_mm=args.min_height_mm,
        min_service_height_mm=args.min_service_height_mm,
        climate_zone=args.climate_zone,
        use_space_aware_height=not args.disable_space_aware_height,
        include_summary=not args.no_summary,
    ):
        print(line)
