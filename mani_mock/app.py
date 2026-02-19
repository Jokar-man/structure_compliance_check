"""
IFCore — Integrated Compliance Platform

Main Gradio application with tabbed interface:
  Dashboard | Upload & Run | Results | Report | Agent Chat | 3D Viewer
"""

import os
import sys
import json
import tempfile
from pathlib import Path

import gradio as gr

# Ensure mani_mock is on the path
sys.path.insert(0, str(Path(__file__).parent))

from config import APP_TITLE, APP_VERSION, SERVER_HOST, SERVER_PORT
from orchestrator import run_compliance_check
from report_engine import generate_html_report, generate_text_report, generate_json_report
from ifc_viewer import render_from_project, build_3d_figure, get_model_info_html

# ── State ────────────────────────────────────────────────────
_current_project = None
_current_ifc_path = None


# ── Callbacks ────────────────────────────────────────────────

def on_upload_and_run(ifc_file):
    """Handle IFC upload → run all checks → return outputs for every tab."""
    global _current_project, _current_ifc_path

    if ifc_file is None:
        empty_html = "<p style='color:#9ca3af;text-align:center;padding:40px;'>Upload an IFC file to get started.</p>"
        return (
            empty_html,        # dashboard_html
            "No file uploaded", # status
            empty_html,        # results_html
            "",                # text_report
            "{}",              # json_report
            gr.update(),       # json_download
            None,              # viewer_plot
            empty_html,        # model_info_html
        )

    path = ifc_file if isinstance(ifc_file, str) else ifc_file.name
    _current_ifc_path = path

    try:
        project = run_compliance_check(path)
        _current_project = project

        # Generate all outputs
        dashboard_html = _build_dashboard_html(project)
        results_html = generate_html_report(project)
        text_report = generate_text_report(project)
        json_report = generate_json_report(project)

        status = (
            f"✓ Analysis complete — "
            f"{project.total_checks} checks, "
            f"{project.passed_elements} passed, "
            f"{project.failed_elements} failed"
        )

        # Save JSON to temp file for download
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", prefix="ifcore_report_", delete=False
        )
        tmp.write(json_report)
        tmp.close()

        # Build 3D viewer
        try:
            viewer_fig = render_from_project(path, project)
        except Exception as ve:
            print(f"[WARN] 3D viewer error: {ve}")
            viewer_fig = build_3d_figure([], title="Error loading geometry")

        # Build model info
        try:
            model_info = get_model_info_html(path)
        except Exception as mi_err:
            print(f"[WARN] Model info error: {mi_err}")
            model_info = f"<p style='color:#dc2626;'>Error reading model info: {mi_err}</p>"

        return (
            dashboard_html,
            status,
            results_html,
            text_report,
            json_report,
            gr.update(value=tmp.name, visible=True),
            viewer_fig,
            model_info,
        )

    except Exception as e:
        error_html = f"<div style='color:#dc2626;padding:20px;'><strong>Error:</strong> {e}</div>"
        return (error_html, f"\u2717 Error: {e}", error_html, str(e), "{}", gr.update(), None, "")


def _build_dashboard_html(project):
    """Build the dashboard summary cards with per-property breakdowns."""
    ts = project.summary_by_team()

    # Group check results by team
    checks_by_team = {}
    for cr in project.check_results:
        checks_by_team.setdefault(cr.team, []).append(cr)

    team_cards = ""
    for team, stats in ts.items():
        border_color = "#16a34a" if stats["fail"] == 0 else "#dc2626"
        team_checks = checks_by_team.get(team, [])

        # Build per-property rows
        property_rows = ""
        for cr in team_checks:
            # Count element-level statuses for this check
            el_pass = sum(1 for e in cr.elements if e.check_status == "pass")
            el_fail = sum(1 for e in cr.elements if e.check_status == "fail")
            el_unknown = sum(1 for e in cr.elements if e.check_status not in ("pass", "fail"))
            el_total = len(cr.elements)

            # Status pill colour
            if el_fail > 0:
                pill_bg, pill_color, pill_text = "#fef2f2", "#dc2626", "FAIL"
            elif el_pass > 0:
                pill_bg, pill_color, pill_text = "#f0fdf4", "#16a34a", "PASS"
            else:
                pill_bg, pill_color, pill_text = "#fefce8", "#d97706", "N/A"

            # Build element detail rows (collapsed by default)
            detail_id = f"detail_{team}_{cr.check_name}".replace(" ", "_").replace("≥", "ge").replace("≤", "le").replace("/", "_")
            element_rows = ""
            for e in cr.elements:
                st_icon = "✅" if e.check_status == "pass" else ("❌" if e.check_status == "fail" else "⚠️")
                el_name = e.element_name or e.element_type or "—"
                actual = e.actual_value or "—"
                required = e.required_value or "—"
                element_rows += f"""
                    <tr style="border-bottom:1px solid #f1f5f9;font-size:12px;">
                        <td style="padding:4px 8px;">{st_icon}</td>
                        <td style="padding:4px 8px;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
                            title="{el_name}">{el_name}</td>
                        <td style="padding:4px 8px;color:#6b7280;">{actual}</td>
                        <td style="padding:4px 8px;color:#6b7280;">{required}</td>
                    </tr>"""

            # Collapsible section for element details
            has_elements = len(cr.elements) > 0
            toggle_html = ""
            if has_elements:
                toggle_html = f"""
                <div style="margin-top:4px;max-height:160px;overflow-y:auto;border:1px solid #e5e7eb;border-radius:6px;">
                    <table style="width:100%;border-collapse:collapse;">
                        <thead><tr style="background:#f8fafc;font-size:11px;color:#6b7280;">
                            <th style="padding:3px 8px;width:24px;"></th>
                            <th style="padding:3px 8px;text-align:left;">Element</th>
                            <th style="padding:3px 8px;text-align:left;">Actual</th>
                            <th style="padding:3px 8px;text-align:left;">Required</th>
                        </tr></thead>
                        <tbody>{element_rows}</tbody>
                    </table>
                </div>"""

            # Count summary
            count_parts = []
            if el_pass > 0:
                count_parts.append(f"<span style='color:#16a34a;font-weight:600;'>{el_pass}✓</span>")
            if el_fail > 0:
                count_parts.append(f"<span style='color:#dc2626;font-weight:600;'>{el_fail}✗</span>")
            if el_unknown > 0:
                count_parts.append(f"<span style='color:#d97706;font-weight:600;'>{el_unknown}?</span>")
            count_str = " ".join(count_parts) if count_parts else "<span style='color:#9ca3af;'>—</span>"

            property_rows += f"""
            <div style="padding:8px 0;border-bottom:1px solid #f1f5f9;">
                <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
                    <div style="display:flex;align-items:center;gap:8px;flex:1;min-width:0;">
                        <span style="background:{pill_bg};color:{pill_color};font-size:10px;font-weight:700;
                                     padding:2px 6px;border-radius:4px;letter-spacing:0.5px;">{pill_text}</span>
                        <span style="font-size:13px;color:#374151;overflow:hidden;text-overflow:ellipsis;
                                     white-space:nowrap;" title="{cr.check_name}">{cr.check_name}</span>
                    </div>
                    <div style="font-size:12px;white-space:nowrap;">{count_str}</div>
                </div>
                {toggle_html}
            </div>"""

        team_cards += f"""
        <div style="min-width:280px;flex:1;background:linear-gradient(135deg,#f8fafc,#f1f5f9);
                     border-radius:14px;padding:20px;border-left:5px solid {border_color};
                     box-shadow:0 1px 3px rgba(0,0,0,0.08);">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                <div style="font-weight:700;font-size:16px;text-transform:uppercase;
                            letter-spacing:1px;color:#1e293b;">{team}</div>
                <div style="display:flex;gap:12px;font-size:13px;">
                    <span style="color:#16a34a;font-weight:700;">{stats['pass']}P</span>
                    <span style="color:#dc2626;font-weight:700;">{stats['fail']}F</span>
                    <span style="color:#d97706;font-weight:700;">{stats.get('unknown',0)+stats.get('error',0)}O</span>
                </div>
            </div>
            <div>{property_rows}</div>
        </div>"""

    # Score
    total_el = project.total_elements
    passed_el = project.passed_elements
    score = round(passed_el / total_el * 100) if total_el > 0 else 0
    score_color = "#16a34a" if score >= 80 else ("#d97706" if score >= 50 else "#dc2626")

    html = f"""
    <div style="font-family:'Segoe UI',system-ui,-apple-system,sans-serif;">
        <!-- Hero Score -->
        <div style="display:flex;align-items:center;gap:32px;margin-bottom:28px;
                     background:linear-gradient(135deg,#0f172a,#1e293b);border-radius:16px;
                     padding:28px 36px;color:white;">
            <div style="text-align:center;">
                <div style="font-size:56px;font-weight:800;color:{score_color};">{score}%</div>
                <div style="font-size:13px;opacity:0.7;letter-spacing:1px;">COMPLIANCE SCORE</div>
            </div>
            <div style="flex:1;">
                <h2 style="margin:0 0 8px 0;font-size:22px;">{project.name}</h2>
                <div style="display:flex;gap:24px;font-size:14px;opacity:0.85;">
                    <span>Schema: {project.ifc_schema or '—'}</span>
                    <span>Checks: {project.total_checks}</span>
                    <span>Elements: {total_el}</span>
                    <span>Teams: {len(ts)}</span>
                </div>
            </div>
        </div>

        <!-- Summary row -->
        <div style="display:flex;gap:16px;margin-bottom:28px;flex-wrap:wrap;">
            <div style="flex:1;min-width:140px;background:#f0fdf4;border:1px solid #bbf7d0;
                         border-radius:14px;padding:18px;text-align:center;">
                <div style="font-size:36px;font-weight:700;color:#16a34a;">{passed_el}</div>
                <div style="font-size:12px;color:#6b7280;letter-spacing:0.5px;">PASSED</div>
            </div>
            <div style="flex:1;min-width:140px;background:#fef2f2;border:1px solid #fecaca;
                         border-radius:14px;padding:18px;text-align:center;">
                <div style="font-size:36px;font-weight:700;color:#dc2626;">{project.failed_elements}</div>
                <div style="font-size:12px;color:#6b7280;letter-spacing:0.5px;">FAILED</div>
            </div>
            <div style="flex:1;min-width:140px;background:#eff6ff;border:1px solid #bfdbfe;
                         border-radius:14px;padding:18px;text-align:center;">
                <div style="font-size:36px;font-weight:700;color:#2563eb;">{total_el}</div>
                <div style="font-size:12px;color:#6b7280;letter-spacing:0.5px;">TOTAL</div>
            </div>
            <div style="flex:1;min-width:140px;background:#fefce8;border:1px solid #fde68a;
                         border-radius:14px;padding:18px;text-align:center;">
                <div style="font-size:36px;font-weight:700;color:#d97706;">{project.total_checks}</div>
                <div style="font-size:12px;color:#6b7280;letter-spacing:0.5px;">CHECKS</div>
            </div>
        </div>

        <!-- Team breakdown -->
        <h3 style="margin:0 0 14px 0;font-size:17px;color:#1e293b;">Team Breakdown</h3>
        <div style="display:flex;gap:14px;flex-wrap:wrap;">
            {team_cards}
        </div>
    </div>
    """
    return html


def on_chat_message(message, history):
    """Stub chat handler for future AI agent integration (legacy format)."""
    if _current_project is None:
        return history + [[message, "Please upload and run an IFC check first so I have data to reason about."]]

    p = _current_project
    response = (
        f"📊 I can see the compliance results for **{p.name}**.\n\n"
        f"- **Score**: {round(p.passed_elements / max(p.total_elements,1) * 100)}%\n"
        f"- **Passed**: {p.passed_elements} elements\n"
        f"- **Failed**: {p.failed_elements} elements\n"
        f"- **Teams**: {', '.join(p.summary_by_team().keys())}\n\n"
        f"_Full AI agent integration coming soon — this is a preview stub._"
    )
    return history + [[message, response]]


def on_chat_message_v2(message, history):
    """Stub chat handler — Gradio 6.x messages format."""
    if _current_project is None:
        return history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": "Please upload and run an IFC check first so I have data to reason about."},
        ]

    p = _current_project
    response = (
        f"📊 I can see the compliance results for **{p.name}**.\n\n"
        f"- **Score**: {round(p.passed_elements / max(p.total_elements,1) * 100)}%\n"
        f"- **Passed**: {p.passed_elements} elements\n"
        f"- **Failed**: {p.failed_elements} elements\n"
        f"- **Teams**: {', '.join(p.summary_by_team().keys())}\n\n"
        f"_Full AI agent integration coming soon — this is a preview stub._"
    )
    return history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": response},
    ]


# ── Build the Gradio App ─────────────────────────────────────

CSS = """
.gradio-container { max-width: 100% !important; padding: 0 24px !important; }
.main-header { 
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; padding: 24px 32px; border-radius: 14px;
    margin-bottom: 16px; text-align: center;
}
.main-header h1 { margin: 0; font-size: 28px; font-weight: 800; }
.main-header p { margin: 6px 0 0 0; opacity: 0.9; font-size: 14px; }
"""

with gr.Blocks(title=APP_TITLE, css=CSS, theme=gr.themes.Soft()) as app:

    # Header
    gr.HTML(f"""
        <div class="main-header">
            <h1>🏗️ {APP_TITLE}</h1>
            <p>Upload an IFC model · Run compliance checks across all teams · View integrated results</p>
        </div>
    """)

    with gr.Tabs():

        # ─── Tab 1: Dashboard ────────────────────────────────
        with gr.Tab("📊 Dashboard"):
            dashboard_html = gr.HTML(
                value="<p style='color:#9ca3af;text-align:center;padding:60px;font-size:15px;'>Upload an IFC file in the <b>Upload & Run</b> tab to see the compliance dashboard.</p>"
            )

        # ─── Tab 2: Upload & Run ─────────────────────────────
        with gr.Tab("📤 Upload & Run"):
            gr.Markdown("### Upload your IFC model and run all team compliance checks")

            with gr.Row():
                with gr.Column(scale=1):
                    ifc_input = gr.File(
                        label="Upload IFC File",
                        file_types=[".ifc"],
                        type="filepath",
                    )
                    run_btn = gr.Button(
                        "🔍 Run All Checks",
                        variant="primary",
                        size="lg",
                    )
                    status_text = gr.Textbox(
                        label="Status",
                        value="Ready — waiting for IFC file",
                        interactive=False,
                    )

                with gr.Column(scale=2):
                    gr.Markdown("""
                    **What happens when you click Run:**

                    1. The IFC model is opened and parsed
                    2. All registered team checks are discovered automatically
                    3. Each team runs its compliance functions against the model
                    4. Results are unified into the IFCore schema
                    5. Dashboard, reports, and JSON output are generated

                    **Currently registered teams:**
                    - 🧱 **Walls** — thickness, U-value, external wall validation
                    - 🔩 **Beams** — depth, width
                    - 🏗️ **Columns** — minimum cross-section dimension
                    - 📐 **Slabs** — thickness range
                    - 🔧 **Reinforcement** — ground slab & foundation thickness
                    - ♿ **Accessibility** — doors, windows, corridors, stairs, railings, rooms

                    > **Want to add your team?** Copy `teams/_template_team.py` and follow the instructions!
                    """)

        # ─── Tab 3: Results ──────────────────────────────────
        with gr.Tab("📋 Results"):
            results_html = gr.HTML(
                value="<p style='color:#9ca3af;text-align:center;padding:60px;'>Run checks to see element-level results.</p>"
            )

        # ─── Tab 4: Reports ─────────────────────────────────
        with gr.Tab("📝 Reports"):
            with gr.Tabs():
                with gr.Tab("Text Report"):
                    text_output = gr.Textbox(
                        label="Text Report",
                        lines=25,
                        value="Run checks to generate the text report.",
                    )
                with gr.Tab("JSON Report"):
                    json_output = gr.Textbox(
                        label="JSON (IFCore Schema)",
                        lines=25,
                        value="{}",
                    )
                    json_download = gr.File(
                        label="Download JSON",
                        visible=False,
                    )

        # ─── Tab 5: Agent Chat (Stub) ───────────────────────
        with gr.Tab("🤖 Agent Chat"):
            gr.Markdown("""
            ### AI Compliance Agent
            
            Ask questions about the compliance results. 
            _Full LLM integration coming soon — this is a preview with basic data lookup._
            """)
            chatbot = gr.Chatbot(label="Chat", height=400)
            chat_input = gr.Textbox(
                label="Message",
                placeholder="Ask about the compliance results...",
            )
            chat_input.submit(
                fn=on_chat_message,
                inputs=[chat_input, chatbot],
                outputs=[chatbot],
            ).then(lambda: "", outputs=[chat_input])

        # ─── Tab 6: 3D Viewer ────────────────────────────────
        with gr.Tab("🏠 3D Viewer"):
            gr.Markdown("""
            ### Interactive 3D Model Viewer
            Upload an IFC file and run checks — the 3D model renders here with **failed elements in red**.
            
            🖱️ **Controls:** Left-drag to rotate · Right-drag to pan · Scroll to zoom · Hover for details
            
            💡 **Click legend items** to show/hide element types · **Double-click** to isolate one type
            """)
            viewer_plot = gr.Plot(
                label="3D IFC Model",
            )
            gr.Markdown("### 📊 Model Analysis")
            model_info_html = gr.HTML(
                value="<p style='color:#9ca3af;text-align:center;padding:30px;'>Upload an IFC file to see the model breakdown.</p>",
            )

        # ─── Tab 7: User/Login (Stub) ───────────────────────
        with gr.Tab("👤 User"):
            gr.HTML("""
                <div style="text-align:center;padding:80px 40px;color:#9ca3af;">
                    <div style="font-size:64px;margin-bottom:16px;">👤</div>
                    <h3 style="color:#6b7280;">User Management</h3>
                    <p>Login, project history, and team settings will be available here.</p>
                    <p style="font-size:12px;margin-top:24px;color:#d1d5db;">
                        Placeholder for authentication + user dashboard.
                    </p>
                </div>
            """)

    # ── Wire the run button ──────────────────────────────────
    run_btn.click(
        fn=on_upload_and_run,
        inputs=[ifc_input],
        outputs=[
            dashboard_html,
            status_text,
            results_html,
            text_output,
            json_output,
            json_download,
            viewer_plot,
            model_info_html,
        ],
    )

    # Auto-run on file upload
    ifc_input.change(
        fn=on_upload_and_run,
        inputs=[ifc_input],
        outputs=[
            dashboard_html,
            status_text,
            results_html,
            text_output,
            json_output,
            json_download,
            viewer_plot,
            model_info_html,
        ],
    )


# ── Launch ───────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 70)
    print(f"  {APP_TITLE}  v{APP_VERSION}")
    print("=" * 70)
    print(f"\n  Starting Gradio server on http://{SERVER_HOST}:{SERVER_PORT}")
    print("  Press Ctrl+C to stop.\n")
    print("=" * 70)

    app.launch(
        server_name=SERVER_HOST,
        server_port=SERVER_PORT,
        share=False,
        show_error=True,
        inbrowser=True,
    )
