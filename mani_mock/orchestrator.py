"""
IFCore Orchestrator — central engine that runs all team checks.

Usage:
    from orchestrator import run_compliance_check
    project = run_compliance_check("path/to/model.ifc")
    print(json.dumps(project.to_dict(), indent=2))
"""

import uuid
import os
import ifcopenshell

from models import Project, CheckResult, ElementResult
from teams import discover_teams


def run_compliance_check(
    ifc_path: str,
    project_name: str = None,
    user_id: str = "local-user",
    region: str = None,
) -> Project:
    """Run every registered team check against an IFC model.

    Args:
        ifc_path: Path to the .ifc file.
        project_name: Human-friendly project name (defaults to filename).
        user_id: ID of the uploading user.
        region: Optional region code (e.g. 'ES', 'CAT').

    Returns:
        A fully populated Project with CheckResults and ElementResults.
    """
    # ── 1. Open the model ────────────────────────────────────
    model = ifcopenshell.open(ifc_path)
    filename = os.path.basename(ifc_path)

    # Detect IFC schema version
    ifc_schema = None
    try:
        ifc_schema = model.schema
    except Exception:
        pass

    project = Project(
        name=project_name or filename,
        file_url=ifc_path,
        user_id=user_id,
        ifc_schema=ifc_schema,
        region=region,
    )

    job_id = str(uuid.uuid4())

    # ── 2. Discover and run all teams ────────────────────────
    teams = discover_teams()

    for team_name, checks in teams.items():
        for check_info in checks:
            check_name = check_info["name"]
            check_fn = check_info["fn"]

            cr = CheckResult(
                project_id=project.id,
                job_id=job_id,
                check_name=check_name,
                team=team_name,
            )

            try:
                raw_results = check_fn(model)

                if not raw_results:
                    cr.status = "unknown"
                    cr.summary = "No elements found for this check."
                else:
                    # Convert raw dicts to ElementResult objects
                    pass_count = 0
                    fail_count = 0
                    other_count = 0

                    for r in raw_results:
                        # Support both IFCore field names and legacy names
                        check_status = (
                            r.get("check_status")
                            or r.get("status", "blocked")
                        )
                        # Map legacy "unknown" → IFCore "blocked"
                        if check_status == "unknown":
                            check_status = "blocked"

                        er = ElementResult(
                            check_result_id=cr.id,
                            element_id=r.get("element_id"),
                            element_type=r.get("element_type"),
                            element_name=r.get("element_name"),
                            element_name_long=r.get("element_name_long"),
                            check_status=check_status,
                            actual_value=r.get("actual_value"),
                            required_value=r.get("required_value"),
                            comment=r.get("comment") or r.get("raw"),
                            log=r.get("log"),
                        )
                        cr.elements.append(er)

                        if er.check_status == "pass":
                            pass_count += 1
                        elif er.check_status == "fail":
                            fail_count += 1
                        else:
                            other_count += 1

                    cr.has_elements = True
                    total = len(raw_results)

                    if fail_count > 0:
                        cr.status = "fail"
                    elif other_count == total:
                        cr.status = "unknown"
                    else:
                        cr.status = "pass"

                    cr.summary = f"{pass_count} pass, {fail_count} fail, {other_count} other (of {total})"

            except Exception as e:
                cr.status = "error"
                cr.summary = f"Error: {e}"

            project.check_results.append(cr)

    return project


# ── CLI usage ────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py <path_to.ifc>")
        sys.exit(1)

    project = run_compliance_check(sys.argv[1])
    print(json.dumps(project.to_dict(), indent=2, default=str))
