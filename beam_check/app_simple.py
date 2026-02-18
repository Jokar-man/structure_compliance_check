"""IFC Compliance Checker — one button per check."""

import sys
from pathlib import Path

import gradio as gr
import ifcopenshell

sys.path.insert(0, str(Path(__file__).parent / "src"))
from ifc_checker import (
    check_door_width,
    check_window_height,
    check_wall_thickness,
    check_wall_height,
    check_slab_thickness,
    check_column_min_dimension,
    check_beam_depth,
    check_beam_width,
    check_opening_height,
    check_corridor_width,
    check_room_area,
    check_room_ceiling_height,
    check_stair_riser_tread,
    check_railing_height,
)


def run_check(check_fn, ifc_file):
    if ifc_file is None:
        return "Upload an IFC file first."
    path = ifc_file if isinstance(ifc_file, str) else ifc_file.name
    model = ifcopenshell.open(path)
    results = check_fn(model)
    return "\n".join(results) if results else "No elements found."


with gr.Blocks(title="IFC Compliance Checker") as app:
    gr.Markdown("# IFC Compliance Checker")
    gr.Markdown("Upload a building model. Click a check to run it.")

    ifc_input = gr.File(label="Upload IFC File", file_types=[".ifc"])
    output = gr.Textbox(label="Results", lines=15)

    # ─── Row 1: Door, Window, Wall Thickness ─────────────────
    with gr.Row():
        btn_door = gr.Button("Door Width (≥ 800 mm)")
        btn_window = gr.Button("Window Height (≥ 1200 mm)")
        btn_wall_thick = gr.Button("Wall Thickness (≥ 100 mm)")
    btn_door.click(fn=lambda f: run_check(check_door_width, f), inputs=[ifc_input], outputs=[output])
    btn_window.click(fn=lambda f: run_check(check_window_height, f), inputs=[ifc_input], outputs=[output])
    btn_wall_thick.click(fn=lambda f: run_check(check_wall_thickness, f), inputs=[ifc_input], outputs=[output])

    # ─── Row 2: Wall Height, Slab, Column ──────────────────
    with gr.Row():
        btn_wall_height = gr.Button("Wall Height (≥ 2500 mm)")
        btn_slab = gr.Button("Slab Thickness (≥ 150 mm)")
        btn_col = gr.Button("Column Min Dim (≥ 250 mm)")
    btn_wall_height.click(fn=lambda f: run_check(check_wall_height, f), inputs=[ifc_input], outputs=[output])
    btn_slab.click(fn=lambda f: run_check(check_slab_thickness, f), inputs=[ifc_input], outputs=[output])
    btn_col.click(fn=lambda f: run_check(check_column_min_dimension, f), inputs=[ifc_input], outputs=[output])

    # ─── Row 3: Beam Depth, Beam Width, Opening ────────────
    with gr.Row():
        btn_beam_depth = gr.Button("Beam Depth (≥ 200 mm)")
        btn_beam_width = gr.Button("Beam Width (≥ 150 mm)")
        btn_opening = gr.Button("Opening Height (≥ 2000 mm)")
    btn_beam_depth.click(fn=lambda f: run_check(check_beam_depth, f), inputs=[ifc_input], outputs=[output])
    btn_beam_width.click(fn=lambda f: run_check(check_beam_width, f), inputs=[ifc_input], outputs=[output])
    btn_opening.click(fn=lambda f: run_check(check_opening_height, f), inputs=[ifc_input], outputs=[output])

    # ─── Row 4: Corridor, Room Area, Ceiling Height ────────
    with gr.Row():
        btn_corridor = gr.Button("Corridor Width (≥ 1100 mm)")
        btn_room_area = gr.Button("Room Area (≥ 5 m²)")
        btn_ceiling = gr.Button("Ceiling Height (≥ 2200 mm)")
    btn_corridor.click(fn=lambda f: run_check(check_corridor_width, f), inputs=[ifc_input], outputs=[output])
    btn_room_area.click(fn=lambda f: run_check(check_room_area, f), inputs=[ifc_input], outputs=[output])
    btn_ceiling.click(fn=lambda f: run_check(check_room_ceiling_height, f), inputs=[ifc_input], outputs=[output])

    # ─── Row 5: Stair, Railing ─────────────────────────────
    with gr.Row():
        btn_stair = gr.Button("Stair Riser/Tread (130-185 / ≥ 280 mm)")
        btn_railing = gr.Button("Railing Height (≥ 900 mm)")
    btn_stair.click(fn=lambda f: run_check(check_stair_riser_tread, f), inputs=[ifc_input], outputs=[output])
    btn_railing.click(fn=lambda f: run_check(check_railing_height, f), inputs=[ifc_input], outputs=[output])


if __name__ == "__main__":
    app.launch()
