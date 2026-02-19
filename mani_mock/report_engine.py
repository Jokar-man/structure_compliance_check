"""
Report Engine — generate JSON / HTML / Text reports from a Project.
"""

import json
from datetime import datetime
from typing import Dict, Any
from models import Project


def generate_json_report(project: Project) -> str:
    """Full JSON output matching the IFCore schema."""
    return json.dumps(project.to_dict(), indent=2, default=str)


def generate_text_report(project: Project) -> str:
    """Plain text summary report."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"  IFCore Compliance Report — {project.name}")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  IFC Schema: {project.ifc_schema or 'unknown'}")
    lines.append("=" * 70)
    lines.append("")

    # Summary
    lines.append(f"  Total Checks:    {project.total_checks}")
    lines.append(f"  Passed Checks:   {project.passed_checks}")
    lines.append(f"  Failed Checks:   {project.failed_checks}")
    lines.append(f"  Total Elements:  {project.total_elements}")
    lines.append(f"  Passed Elements: {project.passed_elements}")
    lines.append(f"  Failed Elements: {project.failed_elements}")
    lines.append("")

    # Per-team breakdown
    lines.append("─" * 70)
    lines.append("  TEAM BREAKDOWN")
    lines.append("─" * 70)
    for team, stats in project.summary_by_team().items():
        lines.append(f"  [{team.upper()}]  total={stats['total']}  pass={stats['pass']}  fail={stats['fail']}  unknown={stats.get('unknown',0)}")
    lines.append("")

    # Detailed results
    lines.append("─" * 70)
    lines.append("  DETAILED RESULTS")
    lines.append("─" * 70)

    for cr in project.check_results:
        icon = "✓" if cr.status == "pass" else ("✗" if cr.status == "fail" else "?")
        lines.append(f"\n  {icon}  [{cr.team}] {cr.check_name}  →  {cr.status.upper()}")
        lines.append(f"     {cr.summary}")

        for er in cr.elements:
            s = "✓" if er.check_status == "pass" else ("✗" if er.check_status == "fail" else "?")
            lines.append(f"       {s} {er.element_name or 'unnamed'} — {er.actual_value or ''}")

    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


def generate_html_report(project: Project) -> str:
    """Visual HTML dashboard report with cards and tables."""
    ts = project.summary_by_team()

    # Team cards
    team_cards = ""
    for team, stats in ts.items():
        team_cards += f"""
        <div style="background:#f8f9fa;border-radius:12px;padding:16px 20px;min-width:180px;
                     border-left:4px solid {'#16a34a' if stats['fail']==0 else '#dc2626'};">
            <div style="font-weight:700;font-size:15px;text-transform:uppercase;color:#374151;">{team}</div>
            <div style="display:flex;gap:14px;margin-top:8px;">
                <span style="color:#16a34a;font-weight:600;">✓ {stats['pass']}</span>
                <span style="color:#dc2626;font-weight:600;">✗ {stats['fail']}</span>
                <span style="color:#6b7280;">? {stats.get('unknown',0)}</span>
            </div>
        </div>"""

    # Element rows
    rows = ""
    for cr in project.check_results:
        for er in cr.elements:
            color = "#16a34a" if er.check_status == "pass" else ("#dc2626" if er.check_status == "fail" else "#6b7280")
            icon = "✓" if er.check_status == "pass" else ("✗" if er.check_status == "fail" else "—")
            rows += f"""
            <tr style="border-bottom:1px solid #e5e7eb;">
                <td style="padding:8px;text-align:center;color:{color};font-size:16px;font-weight:700;">{icon}</td>
                <td style="padding:8px;font-size:13px;color:#6b7280;">{cr.team}</td>
                <td style="padding:8px;">{cr.check_name}</td>
                <td style="padding:8px;">{er.element_name or '—'}</td>
                <td style="padding:8px;font-family:monospace;">{er.actual_value or '—'}</td>
                <td style="padding:8px;font-family:monospace;color:#6b7280;">{er.required_value or '—'}</td>
            </tr>"""

    html = f"""
    <div style="font-family:'Segoe UI',system-ui,sans-serif;">
        <h2 style="margin:0 0 4px 0;">IFCore Compliance Report</h2>
        <p style="margin:0 0 20px 0;color:#6b7280;">
            {project.name} &nbsp;·&nbsp; {project.ifc_schema or 'IFC'} &nbsp;·&nbsp;
            {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </p>

        <!-- Summary cards -->
        <div style="display:flex;gap:16px;margin-bottom:24px;flex-wrap:wrap;">
            <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:16px 24px;text-align:center;">
                <div style="font-size:32px;font-weight:700;color:#16a34a;">{project.passed_elements}</div>
                <div style="font-size:12px;color:#6b7280;">ELEMENTS PASSED</div>
            </div>
            <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:12px;padding:16px 24px;text-align:center;">
                <div style="font-size:32px;font-weight:700;color:#dc2626;">{project.failed_elements}</div>
                <div style="font-size:12px;color:#6b7280;">ELEMENTS FAILED</div>
            </div>
            <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:12px;padding:16px 24px;text-align:center;">
                <div style="font-size:32px;font-weight:700;color:#1d4ed8;">{project.total_elements}</div>
                <div style="font-size:12px;color:#6b7280;">TOTAL ELEMENTS</div>
            </div>
            <div style="background:#fefce8;border:1px solid #fde68a;border-radius:12px;padding:16px 24px;text-align:center;">
                <div style="font-size:32px;font-weight:700;color:#d97706;">{project.total_checks}</div>
                <div style="font-size:12px;color:#6b7280;">CHECKS RUN</div>
            </div>
        </div>

        <!-- Team cards -->
        <h3 style="margin:0 0 12px 0;">Team Breakdown</h3>
        <div style="display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap;">
            {team_cards}
        </div>

        <!-- Element table -->
        <h3 style="margin:0 0 12px 0;">Element-Level Results</h3>
        <div style="max-height:500px;overflow-y:auto;border:1px solid #d1d5db;border-radius:12px;">
            <table style="width:100%;border-collapse:collapse;">
                <thead>
                    <tr style="background:#f3f4f6;position:sticky;top:0;">
                        <th style="padding:10px;width:40px;">St</th>
                        <th style="padding:10px;text-align:left;">Team</th>
                        <th style="padding:10px;text-align:left;">Check</th>
                        <th style="padding:10px;text-align:left;">Element</th>
                        <th style="padding:10px;text-align:left;">Actual</th>
                        <th style="padding:10px;text-align:left;">Required</th>
                    </tr>
                </thead>
                <tbody>
                    {rows if rows else '<tr><td colspan="6" style="padding:20px;text-align:center;color:#9ca3af;">No results yet — upload an IFC file and run checks.</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
    """
    return html
