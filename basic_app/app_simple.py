"""IFC Compliance Checker — one button per check."""

import sys
from pathlib import Path

import gradio as gr
import ifcopenshell

sys.path.insert(0, str(Path(__file__).parent / "src"))
from ifc_checker import check_door_width  # add your imports here


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

    # ─── Add your buttons below (copy these 2 lines per check) ──
    btn_door = gr.Button("Check Door Width")
    btn_door.click(fn=lambda f: run_check(check_door_width, f), inputs=[ifc_input], outputs=[output])

    # btn_room = gr.Button("Check Room Area")
    # btn_room.click(fn=lambda f: run_check(check_room_area, f), inputs=[ifc_input], outputs=[output])


if __name__ == "__main__":
    app.launch()
