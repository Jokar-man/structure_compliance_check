"""
Unified data models for the IFCore compliance platform.

Matches the IFCore data schema:
  projects → check_results → element_results
"""

import uuid
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


@dataclass
class ElementResult:
    """One result per IFC element per check."""
    check_result_id: str
    element_id: Optional[str] = None
    element_type: Optional[str] = None
    element_name: Optional[str] = None
    element_name_long: Optional[str] = None
    check_status: str = "blocked"       # pass | fail | warning | blocked | log
    actual_value: Optional[str] = None
    required_value: Optional[str] = None
    comment: Optional[str] = None
    log: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CheckResult:
    """One result per check function per job."""
    project_id: str
    job_id: str
    check_name: str
    team: str
    status: str = "unknown"            # pass | fail | unknown | error
    summary: str = ""
    has_elements: bool = False
    elements: List[ElementResult] = field(default_factory=list)
    created_at: int = field(default_factory=lambda: int(time.time()))
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["elements"] = [e.to_dict() for e in self.elements]
        return d


@dataclass
class Project:
    """Top-level container for an IFC file upload + all its results."""
    name: str
    file_url: str
    user_id: str = "local-user"
    ifc_schema: Optional[str] = None
    region: Optional[str] = None
    building_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    check_results: List[CheckResult] = field(default_factory=list)
    created_at: int = field(default_factory=lambda: int(time.time()))
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["check_results"] = [cr.to_dict() for cr in self.check_results]
        return d

    # ── Convenience aggregations ──────────────────────────────

    @property
    def total_checks(self) -> int:
        return len(self.check_results)

    @property
    def passed_checks(self) -> int:
        return sum(1 for cr in self.check_results if cr.status == "pass")

    @property
    def failed_checks(self) -> int:
        return sum(1 for cr in self.check_results if cr.status == "fail")

    @property
    def total_elements(self) -> int:
        return sum(len(cr.elements) for cr in self.check_results)

    @property
    def passed_elements(self) -> int:
        return sum(
            1 for cr in self.check_results
            for e in cr.elements if e.check_status == "pass"
        )

    @property
    def failed_elements(self) -> int:
        return sum(
            1 for cr in self.check_results
            for e in cr.elements if e.check_status == "fail"
        )

    def summary_by_team(self) -> Dict[str, Dict[str, int]]:
        teams: Dict[str, Dict[str, int]] = {}
        for cr in self.check_results:
            t = teams.setdefault(cr.team, {"pass": 0, "fail": 0, "unknown": 0, "error": 0, "total": 0})
            t[cr.status] = t.get(cr.status, 0) + 1
            t["total"] += 1
        return teams
