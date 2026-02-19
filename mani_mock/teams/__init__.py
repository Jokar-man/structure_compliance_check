"""
Team plugin registry.

Each team module registers its checks via TEAM_CHECKS.
The orchestrator calls discover_teams() to find all available checks.

To add a new team:
  1. Copy _template_team.py → my_team.py
  2. Implement your check functions
  3. Set TEAM_CHECKS in your module
  4. The registry auto-discovers it
"""

import importlib
import pkgutil
from typing import List, Dict, Callable, Any

# Type alias for a team check function:
#   (model: ifcopenshell.file) -> List[dict]
#   Each dict has keys: element_id, element_type, element_name, status, actual_value, required_value, raw
TeamCheckFn = Callable

# ── Registry ─────────────────────────────────────────────────

_REGISTRY: Dict[str, List[Dict[str, Any]]] = {}


def register_team(team_name: str, checks: List[Dict[str, Any]]):
    """Register a team and its check functions.

    Args:
        team_name: Unique team identifier (e.g. 'walls', 'beams').
        checks: List of dicts with keys:
            - name: str  (human-readable check name)
            - fn: Callable  (function(model) → list[dict])
    """
    _REGISTRY[team_name] = checks


def discover_teams() -> Dict[str, List[Dict[str, Any]]]:
    """Auto-import all team modules in this package and return registry."""
    # Import all modules in the teams/ package
    package = importlib.import_module("teams")
    for _importer, modname, _ispkg in pkgutil.iter_modules(package.__path__):
        if modname.startswith("_"):
            continue  # skip _template_team.py and __init__
        try:
            mod = importlib.import_module(f"teams.{modname}")
            # Each module should have TEAM_NAME and TEAM_CHECKS
            if hasattr(mod, "TEAM_NAME") and hasattr(mod, "TEAM_CHECKS"):
                register_team(mod.TEAM_NAME, mod.TEAM_CHECKS)
        except Exception as e:
            print(f"[WARN] Could not load team module 'teams.{modname}': {e}")

    return dict(_REGISTRY)


def get_registry() -> Dict[str, List[Dict[str, Any]]]:
    """Return currently registered teams (without re-discovering)."""
    return dict(_REGISTRY)
