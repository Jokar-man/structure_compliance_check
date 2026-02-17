"""
IFC Compliance Checker with 3D Visualization (Day 2+)

Architecture:
- ifc_checker.py: Compliance logic (ADD YOUR CHECKS HERE)
- ifc_visualizer.py: 3D export with color highlighting (DON'T MODIFY)
- app.py: Gradio interface (DON'T MODIFY)
"""

import gradio as gr
import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ifc_checker import run_all_checks
from ifc_visualizer import create_highlighted_glb

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_IFC = os.path.join(
    SCRIPT_DIR, "..", "..", "00_data", "ifc_models", "01_Duplex_Apartment.ifc"
)

OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CSS = """
.summary-bar {
    display: flex; gap: 12px; padding: 10px 14px;
    background: #1a1a2e; border-radius: 8px; margin-bottom: 8px;
}
.summary-bar .stat {
    font-size: 22px; font-weight: 700; font-family: monospace;
}
.summary-bar .label {
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;
    color: #999;
}
.stat-pass { color: #4ade80; }
.stat-fail { color: #f87171; }
.stat-unknown { color: #9ca3af; }

.check-list {
    max-height: 420px; overflow-y: auto; font-size: 12px;
    border: 1px solid #d1d5db; border-radius: 6px;
}
.check-row {
    display: flex; align-items: center; padding: 6px 10px;
    border-bottom: 1px solid #e5e7eb; gap: 8px;
}
.check-row:last-child { border-bottom: none; }
.check-row.pass { background: rgba(74,222,128,0.08); }
.check-row.fail { background: rgba(248,113,113,0.1); }
.check-row.unknown { background: rgba(156,163,175,0.06); }

.check-icon { font-size: 14px; width: 20px; text-align: center; flex-shrink: 0; }
.check-icon.pass { color: #4ade80; }
.check-icon.fail { color: #f87171; }
.check-icon.unknown { color: #6b7280; }

.check-rule { font-weight: 600; min-width: 130px; flex-shrink: 0; color: #1f2937; }
.check-element { flex: 1; color: #4b5563; overflow: hidden;
    text-overflow: ellipsis; white-space: nowrap; }
.check-value { text-align: right; min-width: 80px; flex-shrink: 0;
    font-family: monospace; font-size: 11px; color: #374151; }

.status-bar {
    font-size: 11px; color: #6b7280; padding: 4px 0;
    font-family: monospace;
}
.compact-controls { max-height: 56px !important; min-height: 0 !important; }
.compact-controls .wrap { min-height: 0 !important; padding: 8px !important; }
.compact-controls .upload-text { display: none !important; }
.compact-controls .or { display: none !important; }
.small-btn { max-height: 42px !important; min-height: 42px !important;
    font-size: 13px !important; padding: 0 16px !important; }
"""

PLACEHOLDER_HTML = """
<div style="color:#6b7280; text-align:center; padding:40px 20px;">
    <div style="font-size:32px; margin-bottom:8px;">&#8593;</div>
    Upload an IFC file or click <b>Load Demo</b> to start.
</div>
"""


def build_results_html(check_data):
    """Build a compact scrollable HTML list from check results."""
    s = check_data["summary"]

    html = f"""
    <div class="summary-bar">
        <div><div class="stat stat-pass">{s['passed']}</div>
             <div class="label">Passed</div></div>
        <div><div class="stat stat-fail">{s['failed']}</div>
             <div class="label">Failed</div></div>
        <div><div class="stat stat-unknown">{s['unknown']}</div>
             <div class="label">N/A</div></div>
    </div>
    <div class="check-list">
    """

    for r in check_data["results"]:
        if r["passed"] is True:
            cls, icon = "pass", "&#10003;"
        elif r["passed"] is False:
            cls, icon = "fail", "&#10007;"
        else:
            cls, icon = "unknown", "&#8212;"

        html += f"""
        <div class="check-row {cls}">
            <span class="check-icon {cls}">{icon}</span>
            <span class="check-rule">{r['rule']}</span>
            <span class="check-element" title="{r['element_name']}">{r['element_name']}</span>
            <span class="check-value">{r['actual']}</span>
        </div>"""

    html += "</div>"
    return html


def run_compliance_check(ifc_file):
    """Run all checks on uploaded IFC file and return 3D model + results."""
    if ifc_file is None:
        return None, "Please upload an IFC file.", ""

    ifc_path = ifc_file if isinstance(ifc_file, str) else ifc_file.name
    start = time.time()

    check_data = run_all_checks(ifc_path)
    check_time = time.time() - start

    glb_path, processed, errors = create_highlighted_glb(
        ifc_path, check_data["failed_ids"], output_dir=OUTPUT_DIR
    )
    viz_time = time.time() - start - check_time

    results_html = build_results_html(check_data)

    status = (
        f"{check_data['summary']['total']} checks  |  "
        f"{processed} meshes  |  "
        f"{check_time:.1f}s + {viz_time:.1f}s"
    )

    return glb_path, results_html, status


# --- Gradio UI ---

with gr.Blocks(
    title="IFC Compliance Checker",
    theme=gr.themes.Base(primary_hue="blue", neutral_hue="slate"),
    css=CSS,
) as app:

    gr.HTML(
        "<h2 style='margin:0 0 2px 0;'>IFC Compliance Checker</h2>"
        "<p style='margin:0 0 8px 0; color:#9ca3af; font-size:13px;'>"
        "Upload a building model, run checks, see failures in "
        "<span style='color:#f87171;font-weight:600;'>red</span></p>"
    )

    with gr.Row(equal_height=True):
        with gr.Column(scale=3, min_width=400):
            model_3d = gr.Model3D(
                label="3D Model", height=480,
                clear_color=[0.94, 0.94, 0.96, 1.0],
            )

        with gr.Column(scale=2, min_width=300):
            results_html = gr.HTML(value=PLACEHOLDER_HTML)
            status_text = gr.HTML(
                value="<div class='status-bar'>Ready</div>"
            )

    with gr.Row():
        ifc_input = gr.File(
            label="IFC File", file_types=[".ifc"], scale=3,
            height=42, elem_classes=["compact-controls"],
        )
        run_btn = gr.Button(
            "Run Checks", variant="primary", scale=0, min_width=110,
            size="sm", elem_classes=["small-btn"],
        )
        default_btn = gr.Button(
            "Load Demo", variant="secondary", scale=0, min_width=110,
            size="sm", elem_classes=["small-btn"],
        )

    def wrap_status(result):
        glb, html, status = result
        return glb, html, f"<div class='status-bar'>{status}</div>"

    run_btn.click(
        fn=lambda f: wrap_status(run_compliance_check(f)),
        inputs=[ifc_input],
        outputs=[model_3d, results_html, status_text],
    )

    def load_default():
        path = os.path.abspath(DEFAULT_IFC)
        if os.path.exists(path):
            return wrap_status(run_compliance_check(path))
        return None, "Default file not found.", ""

    default_btn.click(
        fn=load_default,
        inputs=[],
        outputs=[model_3d, results_html, status_text],
    )

if __name__ == "__main__":
    app.launch()
