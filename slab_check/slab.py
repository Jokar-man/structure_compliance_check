"""Slab thickness compliance check for IFC models — Gradio App.

Rule: Slab thickness must be between 100 mm and 200 mm for each floor.
"""

import gradio as gr
import ifcopenshell
import ifcopenshell.util.element


MIN_THICKNESS_MM = 100
MAX_THICKNESS_MM = 200


def get_slab_thickness(slab):
    """Extract the total thickness (mm) of an IfcSlab from its material layer set."""
    material = ifcopenshell.util.element.get_material(slab)
    if material is not None:
        layer_set = None
        if material.is_a("IfcMaterialLayerSetUsage"):
            layer_set = material.ForLayerSet
        elif material.is_a("IfcMaterialLayerSet"):
            layer_set = material

        if layer_set is not None:
            total = sum(layer.LayerThickness for layer in layer_set.MaterialLayers)
            return round(total, 2)

    # Fallback: check Qto_SlabBaseQuantities
    for rel in slab.IsDefinedBy:
        if rel.is_a("IfcRelDefinesByProperties"):
            pset = rel.RelatingPropertyDefinition
            if pset.is_a("IfcElementQuantity") and "Slab" in (pset.Name or ""):
                for q in pset.Quantities:
                    if q.is_a("IfcQuantityLength") and q.Name in ("Width", "Depth", "Height"):
                        return round(q.LengthValue, 2)

    return None


def get_storey_name(slab):
    """Get the building storey name for a slab."""
    storey = ifcopenshell.util.element.get_container(slab)
    if storey is not None and storey.is_a("IfcBuildingStorey"):
        return storey.Name or f"Storey (#{storey.id()})"
    return "Unknown Storey"


def check_slab_thickness(ifc_file):
    """Run slab thickness check and return an HTML report."""
    if ifc_file is None:
        return "<p>Please upload an IFC file first.</p>"

    path = ifc_file if isinstance(ifc_file, str) else ifc_file.name
    model = ifcopenshell.open(path)
    slabs = model.by_type("IfcSlab")

    if not slabs:
        return "<p>No IfcSlab elements found in the model.</p>"

    passed = 0
    failed = 0
    na = 0
    rows = ""

    for slab in slabs:
        name = slab.Name or f"Slab #{slab.id()}"
        storey = get_storey_name(slab)
        thickness = get_slab_thickness(slab)

        if thickness is None:
            na += 1
            color = "#6b7280"
            icon = "&#8212;"
            detail = "Thickness not found"
        elif MIN_THICKNESS_MM <= thickness <= MAX_THICKNESS_MM:
            passed += 1
            color = "#16a34a"
            icon = "&#10003;"
            detail = f"{thickness} mm"
        else:
            failed += 1
            color = "#dc2626"
            icon = "&#10007;"
            detail = f"{thickness} mm"

        rows += f"""
        <tr style="border-bottom:1px solid #e5e7eb;">
            <td style="padding:8px;text-align:center;color:{color};font-size:18px;">{icon}</td>
            <td style="padding:8px;">{storey}</td>
            <td style="padding:8px;">{name}</td>
            <td style="padding:8px;font-family:monospace;">{detail}</td>
        </tr>"""

    total = passed + failed + na

    html = f"""
    <div style="font-family:sans-serif;">
        <h3 style="margin:0 0 4px 0;">Slab Thickness Report</h3>
        <p style="margin:0 0 12px 0;color:#6b7280;">
            Allowed range: <b>{MIN_THICKNESS_MM} mm – {MAX_THICKNESS_MM} mm</b>
        </p>
        <div style="display:flex;gap:16px;margin-bottom:16px;">
            <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:12px 20px;text-align:center;">
                <div style="font-size:28px;font-weight:700;color:#16a34a;">{passed}</div>
                <div style="font-size:12px;color:#6b7280;">PASSED</div>
            </div>
            <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:12px 20px;text-align:center;">
                <div style="font-size:28px;font-weight:700;color:#dc2626;">{failed}</div>
                <div style="font-size:12px;color:#6b7280;">FAILED</div>
            </div>
            <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:12px 20px;text-align:center;">
                <div style="font-size:28px;font-weight:700;color:#6b7280;">{na}</div>
                <div style="font-size:12px;color:#6b7280;">N/A</div>
            </div>
            <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:12px 20px;text-align:center;">
                <div style="font-size:28px;font-weight:700;color:#1d4ed8;">{total}</div>
                <div style="font-size:12px;color:#6b7280;">TOTAL</div>
            </div>
        </div>
        <table style="width:100%;border-collapse:collapse;border:1px solid #d1d5db;border-radius:8px;">
            <thead>
                <tr style="background:#f3f4f6;">
                    <th style="padding:8px;width:40px;">Status</th>
                    <th style="padding:8px;text-align:left;">Floor</th>
                    <th style="padding:8px;text-align:left;">Slab Name</th>
                    <th style="padding:8px;text-align:left;">Thickness</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """

    return html


# ── Gradio App ───────────────────────────────────────────────────
with gr.Blocks(title="Slab Thickness Checker") as app:
    gr.Markdown("# Slab Thickness Compliance Checker")
    gr.Markdown(
        "Upload an IFC model to check that every slab thickness is "
        f"between **{MIN_THICKNESS_MM} mm** and **{MAX_THICKNESS_MM} mm**."
    )

    with gr.Row():
        ifc_input = gr.File(label="Upload IFC File", file_types=[".ifc"])
        run_btn = gr.Button("Run Check", variant="primary")

    report = gr.HTML(label="Report")

    run_btn.click(fn=check_slab_thickness, inputs=[ifc_input], outputs=[report])

if __name__ == "__main__":
    app.launch(theme=gr.themes.Soft())
