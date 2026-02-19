"""
╔══════════════════════════════════════════════════════════════════╗
║               TEMPLATE — Add Your Team's Checks                ║
╚══════════════════════════════════════════════════════════════════╝

HOW TO ADD YOUR OWN TEAM:

  1. Copy this file → teams/my_team.py  (any name, no underscore prefix)
  2. Change TEAM_NAME to your team's identifier (e.g. "fire_safety")
  3. Implement your check functions
  4. Add them to TEAM_CHECKS
  5. Done — the orchestrator will auto-discover your module

Each check function receives an ifcopenshell model and returns a
list of result dicts matching the IFCore element_results schema:

    def my_check(model) -> list[dict]:
        return [
            {
                "element_id":        "2O2Fr$t4X7Zf8NOew3FLOH",  # IFC GlobalId or None
                "element_type":      "IfcDoor",                  # IFC class
                "element_name":      "Main Entrance Door",       # short name
                "element_name_long": "Main Entrance Door (Level 1, Zone A)",  # detailed
                "check_status":      "pass",                     # pass | fail | warning | blocked | log
                "actual_value":      "920 mm",                   # what was measured
                "required_value":    ">= 800 mm",               # the rule
                "comment":           None,                       # human-readable explanation (failures)
                "log":               None,                       # debug/trace info
            },
            ...
        ]
"""


def example_check(model):
    """Example: check that the model contains at least one IfcWall."""
    walls = model.by_type("IfcWall")
    if walls:
        return [{
            "element_id":        None,
            "element_type":      "IfcWall",
            "element_name":      "Model",
            "element_name_long": "Model (wall presence check)",
            "check_status":      "pass",
            "actual_value":      f"{len(walls)} walls found",
            "required_value":    ">= 1 wall",
            "comment":           None,
            "log":               None,
        }]
    else:
        return [{
            "element_id":        None,
            "element_type":      "IfcWall",
            "element_name":      "Model",
            "element_name_long": "Model (wall presence check)",
            "check_status":      "fail",
            "actual_value":      "0 walls found",
            "required_value":    ">= 1 wall",
            "comment":           "Model contains no IfcWall elements",
            "log":               None,
        }]


# ── Change these ─────────────────────────────────────────────

TEAM_NAME = "_template"  # ← change to your team name

TEAM_CHECKS = [
    # {"name": "My Check Name", "fn": my_check_function},
]
