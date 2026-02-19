"""
IFC Reinforcement & Structural Analysis Application
Analyzes IFC models for ground floor slab, foundation properties, and regulatory compliance.
"""

import sys
import os
from pathlib import Path
import gradio as gr

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
# Add tools to path (for checker_foundation following IFCore contract)
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from ifc_analyzer import IFCAnalyzer
from report_generator import ReportGenerator

import ifcopenshell
from checker_foundation import (
    check_foundation_slab_thickness,
    check_foundation_dimensions,
    check_bearing_beam_section,
    check_floor_capacity,
)


# ── Foundation compliance rendering helpers ───────────────────────────────────

_BADGE = {
    "pass":    ("#d1fae5", "#065f46", "#10b981"),
    "fail":    ("#fee2e2", "#991b1b", "#ef4444"),
    "warning": ("#fef3c7", "#92400e", "#f59e0b"),
    "blocked": ("#f3f4f6", "#374151", "#9ca3af"),
}
_ICONS = {"pass": "&#10003;", "fail": "&#10007;", "warning": "&#9888;", "blocked": "&#8212;"}

_CHECKS_META = [
    (check_foundation_slab_thickness, "Art. 69",    "Slab Thickness"),
    (check_foundation_dimensions,     "Load Check", "Dimensions"),
    (check_bearing_beam_section,      "DB SE-AE",   "Bearing Beam"),
    (check_floor_capacity,            "Art. 128",   "Floor Capacity"),
]


def _build_floor_banner(floor_rows: list) -> str:
    """Build a prominent floor-capacity banner from Art. 128 results."""
    if not floor_rows:
        return ""

    # Aggregate across all footings: use the most conservative (lowest addable)
    addable_values, max_floors_values, existing_values = [], [], []
    for r in floor_rows:
        log = r.get("log") or ""
        try:
            parts = dict(kv.split("=") for kv in log.split() if "=" in kv)
            addable_values.append(int(parts.get("addable", 0)))
            max_floors_values.append(int(parts.get("max", 0)))
            existing_values.append(int(parts.get("existing", 1)))
        except Exception:
            pass

    if not addable_values:
        # Fall back to parsing comment
        for r in floor_rows:
            comment = r.get("comment", "")
            actual  = r.get("actual_value", "")
            return (f"<div style='background:#f3f4f6;border-radius:8px;"
                    f"padding:12px 16px;margin-bottom:12px;font-size:13px;'>"
                    f"<strong>Art. 128:</strong> {comment or actual}</div>")

    addable  = min(addable_values)
    max_fl   = min(max_floors_values)
    existing = existing_values[0] if existing_values else 1

    if addable > 0:
        bg, border, icon, msg_color = "#d1fae5", "#10b981", "&#10003;", "#065f46"
        msg = f"{addable} floor{'s' if addable != 1 else ''} can be added"
    elif addable == 0:
        bg, border, icon, msg_color = "#fef3c7", "#f59e0b", "&#9888;", "#92400e"
        msg = "No additional floors — foundation is at capacity"
    else:
        bg, border, icon, msg_color = "#fee2e2", "#ef4444", "&#10007;", "#991b1b"
        msg = f"{abs(addable)} floor{'s' if abs(addable) != 1 else ''} over capacity — underpinning required"

    return f"""
    <div style='background:{bg};border:2px solid {border};border-radius:10px;
                padding:14px 20px;margin-bottom:14px;
                display:flex;align-items:center;gap:16px;'>
      <div style='font-size:36px;color:{msg_color};flex-shrink:0;'>{icon}</div>
      <div style='flex:1;'>
        <div style='font-size:18px;font-weight:700;color:{msg_color};'>{msg}</div>
        <div style='font-size:12px;color:#4b5563;margin-top:4px;'>
          Art.&nbsp;128 &nbsp;|&nbsp;
          <strong>Existing:</strong> {existing} floors &nbsp;&nbsp;
          <strong>Max capacity:</strong> {max_fl} floors &nbsp;&nbsp;
          <strong>Addable:</strong>
          <span style='font-weight:700;color:{msg_color};'>
            {"+" if addable >= 0 else ""}{addable}
          </span>
        </div>
      </div>
    </div>"""


def _build_foundation_html(card_data: list, all_rows: list, floor_rows: list) -> str:
    """Build floor banner + 4 summary cards + scrollable detail table."""

    banner = _build_floor_banner(floor_rows)

    # ── Summary cards ──
    cards = "<div style='display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px;'>"
    for label, detail, counts, overall, total in card_data:
        bg, txt, bdr = _BADGE[overall]
        badge_label = overall.upper()
        cards += f"""
        <div style='background:{bg};border:2px solid {bdr};border-radius:8px;
                    padding:12px 8px;text-align:center;'>
          <div style='font-size:10px;color:#6b7280;text-transform:uppercase;
                      letter-spacing:.5px;margin-bottom:3px;'>{label}</div>
          <div style='font-size:12px;font-weight:600;color:#1f2937;
                      margin-bottom:7px;line-height:1.3;'>{detail}</div>
          <div style='display:inline-block;background:white;color:{txt};
                      border:1px solid {bdr};border-radius:4px;
                      padding:2px 10px;font-weight:700;font-size:12px;'>
            {badge_label}
          </div>
          <div style='font-size:10px;color:#6b7280;margin-top:5px;'>
            {counts.get("pass",0)} pass / {counts.get("fail",0)} fail
          </div>
        </div>"""
    cards += "</div>"

    # ── Detail table ──
    table = """
    <div style='border:1px solid #e5e7eb;border-radius:6px;overflow:hidden;
                max-height:400px;overflow-y:auto;font-size:12px;'>
      <table style='width:100%;border-collapse:collapse;'>
        <thead>
          <tr style='background:#f9fafb;border-bottom:2px solid #e5e7eb;position:sticky;top:0;'>
            <th style='padding:8px 10px;text-align:left;color:#6b7280;
                       font-size:11px;text-transform:uppercase;'>Regulation</th>
            <th style='padding:8px 10px;text-align:left;color:#6b7280;
                       font-size:11px;text-transform:uppercase;'>Element</th>
            <th style='padding:8px 10px;text-align:right;color:#6b7280;
                       font-size:11px;text-transform:uppercase;'>Actual</th>
            <th style='padding:8px 10px;text-align:right;color:#6b7280;
                       font-size:11px;text-transform:uppercase;'>Required</th>
            <th style='padding:8px 10px;text-align:center;color:#6b7280;
                       font-size:11px;text-transform:uppercase;'>Result</th>
          </tr>
        </thead><tbody>"""

    row_bg_map = {
        "pass":    "rgba(16,185,129,.05)",
        "fail":    "rgba(239,68,68,.07)",
        "warning": "rgba(245,158,11,.07)",
        "blocked": "white",
    }

    for reg_label, r in all_rows:
        s = r.get("check_status", "blocked")
        bg, txt, bdr = _BADGE.get(s, _BADGE["blocked"])
        icon = _ICONS.get(s, "&#8212;")
        row_bg = row_bg_map.get(s, "white")
        elem_name = (r.get("element_name") or "—")[:40]
        actual   = r.get("actual_value")   or "—"
        required = r.get("required_value") or "—"
        comment  = r.get("comment") or ""
        title    = f'title="{comment}"' if comment else ""

        table += f"""
          <tr style='background:{row_bg};border-bottom:1px solid #f3f4f6;' {title}>
            <td style='padding:6px 10px;color:#4b5563;white-space:nowrap;'>{reg_label}</td>
            <td style='padding:6px 10px;color:#1f2937;font-weight:500;max-width:180px;
                       overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'>{elem_name}</td>
            <td style='padding:6px 10px;text-align:right;font-family:monospace;
                       color:#374151;white-space:nowrap;'>{actual}</td>
            <td style='padding:6px 10px;text-align:right;font-family:monospace;
                       color:#374151;white-space:nowrap;'>{required}</td>
            <td style='padding:6px 10px;text-align:center;'>
              <span style='background:{bg};color:{txt};border:1px solid {bdr};
                           border-radius:4px;padding:2px 7px;font-size:11px;
                           font-weight:700;white-space:nowrap;'>{icon} {s.upper()}</span>
            </td>
          </tr>"""

    table += "</tbody></table></div>"

    disclaimer = """
    <div style='margin-top:10px;padding:8px 12px;background:#fef9c3;border-left:3px solid #fbbf24;
                border-radius:4px;font-size:11px;color:#78350f;'>
      <strong>Note:</strong> Where bearing capacity is missing from the IFC model, a conservative
      default of 150 kN/m2 is used. Actual geotechnical values must be provided by a qualified
      engineer per the Metropolitan Building Ordinances.
    </div>"""

    return banner + cards + table + disclaimer


def run_foundation_checks(ifc_file):
    """Run the 4 regulatory foundation checks and return HTML results + status string."""
    if ifc_file is None:
        placeholder = ("<p style='color:#999;text-align:center;padding:40px;'>"
                       "Upload an IFC file and click Foundation Compliance Check.</p>")
        return placeholder, "No file uploaded"

    ifc_path = ifc_file if isinstance(ifc_file, str) else ifc_file.name
    try:
        model = ifcopenshell.open(ifc_path)
    except Exception as e:
        err = (f"<div style='color:#dc2626;padding:20px;background:#fee2e2;"
               f"border-radius:8px;'><strong>Error opening IFC:</strong> {e}</div>")
        return err, f"Error: {e}"

    card_data  = []
    all_rows   = []
    floor_rows = []   # Art. 128 rows kept separately for the banner

    for fn, reg_label, detail_label in _CHECKS_META:
        try:
            rows = fn(model)
        except Exception as e:
            rows = [{
                "element_id": None, "element_type": "—",
                "element_name": "Check error",
                "element_name_long": str(e),
                "check_status": "blocked",
                "actual_value": None, "required_value": None,
                "comment": str(e), "log": None,
            }]

        if fn is check_floor_capacity:
            floor_rows = rows

        all_rows.extend((reg_label, r) for r in rows)

        counts = {}
        for r in rows:
            s = r.get("check_status", "blocked")
            counts[s] = counts.get(s, 0) + 1

        overall = ("fail"    if counts.get("fail", 0) > 0 else
                   "warning" if counts.get("warning", 0) > 0 else
                   "blocked" if counts.get("pass", 0) == 0 else
                   "pass")
        card_data.append((reg_label, detail_label, counts, overall, len(rows)))

    html = _build_foundation_html(card_data, all_rows, floor_rows)

    n_pass = sum(1 for _, r in all_rows if r.get("check_status") == "pass")
    n_fail = sum(1 for _, r in all_rows if r.get("check_status") == "fail")
    n_warn = sum(1 for _, r in all_rows if r.get("check_status") == "warning")
    status = (f"Foundation compliance: {n_pass} pass, {n_fail} fail, "
              f"{n_warn} warning across {len(all_rows)} checks")
    return html, status


# ── Existing property-level analysis ─────────────────────────────────────────

def analyze_ifc_model(ifc_file):
    """Property analysis: thickness, area, material, load capacity estimates."""
    if ifc_file is None:
        return (
            "Please upload an IFC file to begin analysis.",
            "<p style='color:#ff9800;padding:20px;'>Please upload an IFC file.</p>",
            "No file uploaded",
        )
    try:
        ifc_path = ifc_file if isinstance(ifc_file, str) else ifc_file.name
        filename = os.path.basename(ifc_path)
        analyzer = IFCAnalyzer(ifc_path)
        all_slabs    = analyzer.get_slabs()
        ground_slabs = analyzer.get_ground_floor_slabs()
        foundations  = analyzer.get_foundations()

        text_report = ReportGenerator.generate_slab_foundation_report(
            slabs=all_slabs, foundations=foundations,
            ground_slabs=ground_slabs, ifc_filename=filename,
        )
        html_report = ReportGenerator.generate_html_report(
            slabs=all_slabs, foundations=foundations,
            ground_slabs=ground_slabs, ifc_filename=filename,
        )
        status = (f"Analysis complete: {len(all_slabs)} slabs, "
                  f"{len(ground_slabs)} ground floor, {len(foundations)} foundations")
        return text_report, html_report, status

    except Exception as e:
        err_html = (f"<div style='color:#f44336;padding:20px;background:#ffebee;"
                    f"border-radius:8px;'><strong>Error:</strong> {e}</div>")
        return f"Error: {e}", err_html, "Analysis failed"


# ── Gradio UI ─────────────────────────────────────────────────────────────────

PLACEHOLDER_FOUNDATION = (
    "<p style='color:#999;text-align:center;padding:40px;'>"
    "Upload an IFC file and click <strong>Foundation Compliance Check</strong> to run "
    "Art.&nbsp;69, Load Check, DB&nbsp;SE-AE, and Art.&nbsp;128 checks.</p>"
)
PLACEHOLDER_VISUAL = (
    "<p style='color:#999;text-align:center;padding:40px;'>"
    "Upload an IFC file and click <strong>Analyze Properties</strong> to see results.</p>"
)

with gr.Blocks(title="IFC Structural Compliance") as app:

    gr.HTML("""
    <div style='background:linear-gradient(135deg,#1e3a5f 0%,#2d6a9f 100%);
                color:white;padding:28px 30px;border-radius:10px;margin-bottom:18px;'>
      <h1 style='margin:0;font-size:28px;font-family:Segoe UI,Arial,sans-serif;'>
        IFC Structural Compliance
      </h1>
      <p style='margin:8px 0 0 0;opacity:.85;font-size:14px;'>
        Foundation compliance (Art.&nbsp;69 &middot; Load Check &middot;
        DB&nbsp;SE-AE &middot; Art.&nbsp;128) &nbsp;+&nbsp; Property analysis
      </p>
    </div>
    """)

    with gr.Row():

        # ── Left column: upload + buttons ────────────────────────────────────
        with gr.Column(scale=1, min_width=280):

            ifc_input = gr.File(
                label="Upload IFC File",
                file_types=[".ifc"],
                file_count="single",
            )

            foundation_btn = gr.Button(
                "Foundation Compliance Check",
                variant="primary",
                size="lg",
            )
            foundation_status = gr.Textbox(
                label="Compliance Status",
                value="Ready",
                interactive=False,
            )

            gr.HTML("<hr style='margin:12px 0;border-color:#e5e7eb;'>")

            analyze_btn = gr.Button(
                "Analyze Properties",
                variant="secondary",
                size="lg",
            )
            status_text = gr.Textbox(
                label="Property Analysis Status",
                value="Ready",
                interactive=False,
            )

            gr.Markdown("""
**Compliance checks** verify your model against:
- **Art. 69** — Slab thickness ≥ 300 mm
- **Load Check** — Footing area vs required area
- **DB SE-AE** — Bearing beam ≥ 300×300 mm
- **Art. 128** — Max floors + addable floors

**Property analysis** extracts thickness, area, material, and load estimates.
            """)

        # ── Right column: results tabs ────────────────────────────────────────
        with gr.Column(scale=2, min_width=480):

            with gr.Tabs():

                with gr.Tab("Foundation Compliance"):
                    foundation_html = gr.HTML(value=PLACEHOLDER_FOUNDATION)

                with gr.Tab("Visual Report"):
                    html_output = gr.HTML(value=PLACEHOLDER_VISUAL)

                with gr.Tab("Text Report"):
                    text_output = gr.Textbox(
                        label="Detailed Property Report",
                        lines=28,
                        value="Click 'Analyze Properties' to generate a text report.",
                    )

    # ── Button connections ────────────────────────────────────────────────────
    foundation_btn.click(
        fn=run_foundation_checks,
        inputs=[ifc_input],
        outputs=[foundation_html, foundation_status],
    )

    analyze_btn.click(
        fn=analyze_ifc_model,
        inputs=[ifc_input],
        outputs=[text_output, html_output, status_text],
    )

    gr.HTML("""
    <div style='margin-top:14px;padding:10px 14px;background:#f1f5f9;
                border-radius:6px;font-size:11px;color:#64748b;'>
      <strong>Disclaimer:</strong> Automated preliminary analysis only.
      All structural results must be verified by a licensed structural engineer.
      Default soil bearing capacity 150&nbsp;kN/m&sup2; is used when not present in the IFC model.
    </div>
    """)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 70)
    print("IFC Structural Compliance — Foundation + Property Analysis")
    print("=" * 70)
    print("Press Ctrl+C to stop.")
    print("=" * 70)

    app.launch(
        server_name="127.0.0.1",
        server_port=None,   # auto-select next free port
        share=False,
        show_error=True,
        inbrowser=True,
    )
