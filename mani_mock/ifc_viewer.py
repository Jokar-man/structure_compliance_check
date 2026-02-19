"""
3D IFC Viewer — extract geometry from IFC and render with Plotly.

Uses ifcopenshell.geom (OpenCASCADE) to tessellate elements,
then renders Mesh3d traces coloured by IFC type and compliance status.

Every IFC type is a separately togglable trace in the Plotly legend,
so users can click any element type to show/hide it.
"""

import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import plotly.graph_objects as go
from typing import Set, Optional, List, Dict


# ── Colour palette per IFC type ────────────────────────────

TYPE_COLORS: Dict[str, tuple] = {
    # (R, G, B, opacity)
    "IfcWall":              (180, 190, 205, 0.75),
    "IfcWallStandardCase":  (180, 190, 205, 0.75),
    "IfcSlab":              (200, 200, 185, 0.70),
    "IfcBeam":              (80,  130, 190, 0.85),
    "IfcColumn":            (130, 110, 180, 0.85),
    "IfcDoor":              (170, 120, 75,  0.85),
    "IfcWindow":            (130, 200, 240, 0.35),
    "IfcStairFlight":       (165, 155, 145, 0.75),
    "IfcStair":             (165, 155, 145, 0.75),
    "IfcRailing":           (100, 100, 100, 0.65),
    "IfcPlate":             (190, 190, 190, 0.55),
    "IfcFooting":           (155, 145, 130, 0.75),
    "IfcCovering":          (215, 205, 195, 0.55),
    "IfcRoof":              (190,  95,  70, 0.70),
    "IfcCurtainWall":       (130, 200, 240, 0.35),
    "IfcMember":            (160, 160, 175, 0.75),
    "IfcBuildingElementProxy": (160, 160, 160, 0.50),
    "IfcSpace":             (220, 220, 240, 0.15),
    "IfcFurnishingElement": (185, 150, 110, 0.60),
    "IfcFlowTerminal":      (110, 170, 140, 0.60),
    "IfcFlowSegment":       (110, 170, 140, 0.50),
    "IfcDistributionElement": (110, 170, 140, 0.50),
}

FAIL_COLOR = (220, 38, 38, 0.90)  # vivid red

# Friendly display names
TYPE_LABELS: Dict[str, str] = {
    "IfcWall": "🧱 Walls",
    "IfcWallStandardCase": "🧱 Walls (Std)",
    "IfcSlab": "📐 Slabs",
    "IfcBeam": "🔩 Beams",
    "IfcColumn": "🏛️ Columns",
    "IfcDoor": "🚪 Doors",
    "IfcWindow": "🪟 Windows",
    "IfcStairFlight": "🪜 Stairs",
    "IfcStair": "🪜 Stairs (full)",
    "IfcRailing": "🛡️ Railings",
    "IfcPlate": "📋 Plates",
    "IfcFooting": "🔧 Footings",
    "IfcCovering": "🎨 Coverings",
    "IfcRoof": "🏠 Roof",
    "IfcCurtainWall": "🏢 Curtain Walls",
    "IfcMember": "🔗 Members",
    "IfcBuildingElementProxy": "📦 Proxies",
    "IfcSpace": "🏠 Spaces",
    "IfcFurnishingElement": "🪑 Furniture",
    "IfcFlowTerminal": "🔌 MEP Terminals",
    "IfcFlowSegment": "🔌 MEP Segments",
    "IfcDistributionElement": "⚡ Distribution",
}


# ── Geometry extraction ──────────────────────────────────────

def _get_settings():
    """Create ifcopenshell geometry settings for tessellation."""
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    return settings


def extract_meshes(model, failed_ids: Optional[Set[str]] = None):
    """Extract triangle meshes from ALL renderable IFC elements.

    Auto-discovers every element type in the model so nothing is missed.
    """
    if failed_ids is None:
        failed_ids = set()

    settings = _get_settings()
    meshes = []

    # Auto-discover ALL product types in the model
    # IfcProduct is the base class for all spatial/physical elements
    all_products = model.by_type("IfcProduct")

    for element in all_products:
        ifc_type = element.is_a()

        # Skip non-geometric items
        if ifc_type in ("IfcSite", "IfcBuilding", "IfcBuildingStorey",
                        "IfcProject", "IfcAnnotation", "IfcGrid",
                        "IfcOpeningElement", "IfcVirtualElement"):
            continue

        try:
            shape = ifcopenshell.geom.create_shape(settings, element)
            verts_flat = shape.geometry.verts
            faces_flat = shape.geometry.faces

            if len(verts_flat) == 0 or len(faces_flat) == 0:
                continue

            vertices = np.array(verts_flat).reshape(-1, 3)
            faces = np.array(faces_flat).reshape(-1, 3)

            gid = getattr(element, "GlobalId", None)
            name = element.Name or ifc_type

            # Determine colour
            is_failed = (gid is not None and gid in failed_ids)
            if is_failed:
                rgba = FAIL_COLOR
            else:
                rgba = TYPE_COLORS.get(ifc_type, (170, 170, 170, 0.60))

            # Get storey info if available
            storey = ""
            try:
                container = ifcopenshell.util.element.get_container(element)
                if container and container.is_a("IfcBuildingStorey"):
                    storey = container.Name or ""
            except Exception:
                pass

            meshes.append({
                "vertices": vertices,
                "faces": faces,
                "rgba": rgba,
                "ifc_type": ifc_type,
                "name": name,
                "global_id": gid,
                "storey": storey,
                "is_failed": is_failed,
            })

        except Exception:
            continue

    return meshes


# ── IFC model summary (for deeper analysis) ─────────────────

def get_model_summary(model) -> Dict:
    """Extract a comprehensive summary of all element types in the model."""
    summary = {
        "schema": getattr(model, "schema", "unknown"),
        "element_types": {},
        "total_products": 0,
        "storeys": [],
        "materials": set(),
    }

    # Count elements by type
    for product in model.by_type("IfcProduct"):
        ifc_type = product.is_a()
        if ifc_type not in summary["element_types"]:
            summary["element_types"][ifc_type] = 0
        summary["element_types"][ifc_type] += 1
        summary["total_products"] += 1

    # Get storeys
    for storey in model.by_type("IfcBuildingStorey"):
        elev = getattr(storey, "Elevation", None)
        summary["storeys"].append({
            "name": storey.Name or f"Storey #{storey.id()}",
            "elevation": elev,
        })

    # Get unique materials
    for mat in model.by_type("IfcMaterial"):
        summary["materials"].add(mat.Name or "unnamed")

    summary["materials"] = sorted(summary["materials"])
    return summary


# ── Plotly 3D figure ─────────────────────────────────────────

def build_3d_figure(
    meshes: list,
    title: str = "IFC Model",
    width: int = None,
    height: int = 700,
) -> go.Figure:
    """Build a Plotly figure with Mesh3d traces grouped by IFC type.

    Each element type becomes a separate legend entry that can be
    clicked to show/hide.
    """
    fig = go.Figure()

    if not meshes:
        fig.add_annotation(
            text="No renderable geometry found in the IFC model.<br>Upload an IFC file and run checks.",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=16, color="#9ca3af"),
        )
        fig.update_layout(
            height=height,
            scene=dict(
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                zaxis=dict(visible=False),
            ),
        )
        return fig

    # Group meshes by IFC type for legend grouping
    type_groups: Dict[str, List] = {}
    failed_meshes: List = []

    for mesh in meshes:
        if mesh["is_failed"]:
            failed_meshes.append(mesh)
        ifc_type = mesh["ifc_type"]
        if ifc_type not in type_groups:
            type_groups[ifc_type] = []
        type_groups[ifc_type].append(mesh)

    # Sort by type name to make legend consistent
    sorted_types = sorted(type_groups.keys())

    for ifc_type in sorted_types:
        group = type_groups[ifc_type]
        is_first = True
        legend_label = TYPE_LABELS.get(ifc_type, ifc_type)
        count = len(group)

        for mesh in group:
            v = mesh["vertices"]
            f = mesh["faces"]
            r, g, b, opacity = mesh["rgba"]

            status_text = "❌ FAILED" if mesh["is_failed"] else "✓ OK"
            storey_str = f"<br>Storey: {mesh['storey']}" if mesh["storey"] else ""

            fig.add_trace(go.Mesh3d(
                x=v[:, 0], y=v[:, 1], z=v[:, 2],
                i=f[:, 0], j=f[:, 1], k=f[:, 2],
                color=f"rgb({r},{g},{b})",
                opacity=opacity,
                name=f"{legend_label} ({count})" if is_first else legend_label,
                legendgroup=ifc_type,
                showlegend=is_first,
                hovertemplate=(
                    f"<b>{mesh['name']}</b><br>"
                    f"Type: {ifc_type}<br>"
                    f"ID: {mesh.get('global_id', '—')}"
                    f"{storey_str}<br>"
                    f"Status: {status_text}"
                    "<extra></extra>"
                ),
                flatshading=True,
                lighting=dict(
                    ambient=0.45,
                    diffuse=0.85,
                    specular=0.3,
                    roughness=0.5,
                    fresnel=0.15,
                ),
                lightposition=dict(x=1000, y=1000, z=2000),
            ))
            is_first = False

    # Layout — responsive width
    layout_kwargs = dict(
        title=dict(
            text=f"🏗️ {title} — Click legend items to show/hide element types",
            font=dict(size=16),
        ),
        height=height,
        scene=dict(
            xaxis=dict(title="X (m)", showgrid=True, gridcolor="#e5e7eb",
                       backgroundcolor="#f0f2f5"),
            yaxis=dict(title="Y (m)", showgrid=True, gridcolor="#e5e7eb",
                       backgroundcolor="#f0f2f5"),
            zaxis=dict(title="Z (m)", showgrid=True, gridcolor="#e5e7eb",
                       backgroundcolor="#f0f2f5"),
            aspectmode="data",
            bgcolor="#f0f2f5",
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.0),
                up=dict(x=0, y=0, z=1),
            ),
        ),
        legend=dict(
            title=dict(text="Element Types (click to toggle)"),
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor="#d1d5db",
            borderwidth=1,
            font=dict(size=12),
            itemclick="toggle",
            itemdoubleclick="toggleothers",
        ),
        margin=dict(l=0, r=0, t=50, b=0),
        paper_bgcolor="#ffffff",
    )

    if width is not None:
        layout_kwargs["width"] = width

    fig.update_layout(**layout_kwargs)

    return fig


# ── High-level API ───────────────────────────────────────────

def render_ifc_model(
    ifc_path: str,
    failed_ids: Optional[Set[str]] = None,
    title: str = None,
) -> go.Figure:
    """One-call API: open model → extract meshes → build Plotly figure."""
    import os
    model = ifcopenshell.open(ifc_path)
    if title is None:
        title = os.path.basename(ifc_path)

    meshes = extract_meshes(model, failed_ids)
    return build_3d_figure(meshes, title=title)


def render_from_project(ifc_path: str, project) -> go.Figure:
    """Render the IFC model with failed elements highlighted from a Project."""
    failed_ids = set()
    for cr in project.check_results:
        for er in cr.elements:
            if er.check_status == "fail" and er.element_id:
                failed_ids.add(er.element_id)

    return render_ifc_model(ifc_path, failed_ids, title=project.name)


def get_model_info_html(ifc_path: str) -> str:
    """Generate an HTML summary of all element types in the IFC model."""
    model = ifcopenshell.open(ifc_path)
    info = get_model_summary(model)

    # Build type table rows
    type_rows = ""
    for t, count in sorted(info["element_types"].items(), key=lambda x: -x[1]):
        icon = TYPE_LABELS.get(t, "").split(" ")[0] if t in TYPE_LABELS else "📦"
        type_rows += f"""
        <tr style="border-bottom:1px solid #e5e7eb;">
            <td style="padding:6px 12px;">{icon} {t}</td>
            <td style="padding:6px 12px;text-align:center;font-weight:600;">{count}</td>
        </tr>"""

    # Storey rows
    storey_rows = ""
    for s in info["storeys"]:
        elev = f"{s['elevation']:.2f} m" if s["elevation"] is not None else "—"
        storey_rows += f"<tr><td style='padding:4px 12px;'>{s['name']}</td><td style='padding:4px 12px;'>{elev}</td></tr>"

    # Material list
    mat_items = "".join(f"<li>{m}</li>" for m in info["materials"][:20]) or "<li>No materials found</li>"

    html = f"""
    <div style="font-family:'Segoe UI',system-ui,sans-serif;display:grid;grid-template-columns:1fr 1fr;gap:20px;">
        <div>
            <h4 style="margin:0 0 8px 0;">📊 Element Types ({info['total_products']} total)</h4>
            <div style="max-height:300px;overflow-y:auto;border:1px solid #e5e7eb;border-radius:8px;">
                <table style="width:100%;border-collapse:collapse;font-size:13px;">
                    <thead><tr style="background:#f3f4f6;position:sticky;top:0;">
                        <th style="padding:8px 12px;text-align:left;">Type</th>
                        <th style="padding:8px 12px;text-align:center;">Count</th>
                    </tr></thead>
                    <tbody>{type_rows}</tbody>
                </table>
            </div>
        </div>
        <div>
            <h4 style="margin:0 0 8px 0;">🏢 Storeys</h4>
            <table style="width:100%;border-collapse:collapse;font-size:13px;border:1px solid #e5e7eb;border-radius:8px;">
                <thead><tr style="background:#f3f4f6;">
                    <th style="padding:8px 12px;text-align:left;">Name</th>
                    <th style="padding:8px 12px;">Elevation</th>
                </tr></thead>
                <tbody>{storey_rows or '<tr><td colspan="2" style="padding:8px;color:#9ca3af;">No storeys found</td></tr>'}</tbody>
            </table>
            <h4 style="margin:16px 0 8px 0;">🧱 Materials ({len(info['materials'])})</h4>
            <ul style="font-size:13px;margin:0;padding-left:20px;max-height:150px;overflow-y:auto;">
                {mat_items}
            </ul>
            <p style="margin-top:12px;font-size:12px;color:#6b7280;">Schema: <strong>{info['schema']}</strong></p>
        </div>
    </div>
    """
    return html
