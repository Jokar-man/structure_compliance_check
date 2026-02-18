"""Gradio UI for running wall compliance checks on uploaded IFC files."""

import argparse
import sys
from pathlib import Path

import gradio as gr


ROOT_DIR = Path(__file__).resolve().parent.parent
WALLS_DIR = ROOT_DIR / "walls_check"
if str(WALLS_DIR) not in sys.path:
    sys.path.insert(0, str(WALLS_DIR))

from Walls import run_wall_checks
import rules


def analyze_ifc_walls(
    ifc_file,
    min_mm,
    min_height_mm,
    min_service_height_mm,
    use_space_aware_height,
    max_u,
    climate_zone,
    include_summary,
):
    if ifc_file is None:
        return "", "Please upload an IFC file first."

    ifc_path = ifc_file if isinstance(ifc_file, str) else ifc_file.name
    normalized_zone = None if climate_zone == "Custom (use max U-value)" else climate_zone

    try:
        report_lines = run_wall_checks(
            ifc_path,
            min_mm=float(min_mm),
            min_height_mm=float(min_height_mm),
            min_service_height_mm=float(min_service_height_mm),
            use_space_aware_height=bool(use_space_aware_height),
            max_u=float(max_u),
            climate_zone=normalized_zone,
            include_summary=bool(include_summary),
        )
        report_text = "\n".join(report_lines)
        fail_count = sum(1 for line in report_lines if line.startswith("[FAIL] IfcWall "))
        if normalized_zone:
            u_info = f"U-limit mode: climate zone {normalized_zone} (U_lim={rules.CLIMATE_ZONE_U_LIMITS[normalized_zone]:.2f})"
        else:
            u_info = f"U-limit mode: custom max U={float(max_u):.3f}"
        if use_space_aware_height:
            h_info = f"Height mode: room-aware ({float(min_height_mm):.0f}/{float(min_service_height_mm):.0f}mm)"
        else:
            h_info = f"Height mode: fixed ({float(min_height_mm):.0f}mm)"
        status = f"Analyzed: {Path(ifc_path).name} | Failed checks: {fail_count} | {u_info} | {h_info}"
        return report_text, status
    except Exception as exc:
        return "", f"Error analyzing {Path(ifc_path).name}: {exc}"


def build_app():
    with gr.Blocks(title="IFC Wall Compliance Checker") as app:
        gr.Markdown(
            """
# IFC Wall Compliance Checker
Upload an IFC model and run wall compliance checks.
`U-value` (thermal transmittance) is in W/m2K: lower is better insulation.
If room-aware height is enabled: 2.50m general, 2.20m for kitchen/bath/corridor (based on IfcSpace links).
"""
        )

        with gr.Row():
            with gr.Column(scale=1):
                ifc_input = gr.File(
                    label="Upload IFC file",
                    file_types=[".ifc"],
                    type="filepath",
                )
                min_mm = gr.Number(label="Minimum wall thickness (mm)", value=100, precision=0)
                min_height_mm = gr.Number(label="General minimum wall height (mm)", value=2500, precision=0)
                min_service_height_mm = gr.Number(
                    label="Service-space minimum height (mm)",
                    value=2200,
                    precision=0,
                )
                use_space_aware_height = gr.Checkbox(
                    label="Use room-aware height (kitchen/bath/corridor)",
                    value=True,
                )
                max_u = gr.Number(label="Maximum U-value", value=0.8, precision=3)
                climate_zone = gr.Dropdown(
                    label="Climate zone (CTE external-wall U limit)",
                    choices=["Custom (use max U-value)", "A", "B", "C", "D", "E"],
                    value="Custom (use max U-value)",
                )
                include_summary = gr.Checkbox(label="Include summary section", value=True)
                analyze_btn = gr.Button("Run wall checks", variant="primary")
                clear_btn = gr.Button("Clear")

            with gr.Column(scale=2):
                status = gr.Markdown("Upload a file and click **Run wall checks**.")
                output = gr.Textbox(
                    label="Compliance report",
                    lines=24,
                    max_lines=40,
                )

        analyze_btn.click(
            fn=analyze_ifc_walls,
            inputs=[
                ifc_input,
                min_mm,
                min_height_mm,
                min_service_height_mm,
                use_space_aware_height,
                max_u,
                climate_zone,
                include_summary,
            ],
            outputs=[output, status],
        )

        clear_btn.click(
            fn=lambda: ("", "Upload a file and click **Run wall checks**."),
            inputs=[],
            outputs=[output, status],
        )

    return app


def parse_args():
    parser = argparse.ArgumentParser(description="Run the wall compliance Gradio app.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface for Gradio server.")
    parser.add_argument("--port", type=int, default=7860, help="Port for Gradio server.")
    parser.add_argument(
        "--share",
        action="store_true",
        help="Create a temporary public Gradio link.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_app().launch(server_name=args.host, server_port=args.port, share=args.share)
