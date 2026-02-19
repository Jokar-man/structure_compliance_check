# Structure Compliance Check

A Gradio web application and set of standalone Python tools for checking BIM/IFC models against structural and regulatory standards (Spanish Metropolitan Building Ordinances, EHE, DB SE-AE, CTE DB HE).

---

## Quick Start

### 1. Install dependencies

```bash
pip install ifcopenshell numpy gradio python-dotenv
```

### 2. Run the Gradio app

```bash
py reinforcement_check/app.py
```

Open the URL printed in the terminal (e.g. `http://127.0.0.1:7860`), upload an `.ifc` file, and click **Foundation Compliance Check**.

### 3. Run a single checker from the terminal

All checkers in `tools/` are standalone scripts. Run from the **project root**:

```bash
py tools/checker_foundation.py  data/01_Duplex_Apartment.ifc
py tools/checker_beams.py       data/01_Duplex_Apartment.ifc
py tools/checker_columns.py     data/01_Duplex_Apartment.ifc
py tools/checker_slabs.py       data/01_Duplex_Apartment.ifc
py tools/checker_walls.py       data/01_Duplex_Apartment.ifc
```

---

## Project Structure

```
structure_compliance_check/
│
├── reinforcement_check/          ← Gradio web application
│   ├── app.py                    ← Main entry point — run this
│   ├── requirements.txt          ← Python dependencies
│   └── src/
│       ├── ifc_analyzer.py       ← IFC property analysis
│       └── report_generator.py   ← HTML/text report builder
│
├── tools/                        ← Standalone compliance checkers
│   ├── checker_foundation.py     ← Foundation checks (Art. 69, Art. 128, DB SE-AE)
│   ├── checker_beams.py          ← Beam section checks (EHE / DB SE)
│   ├── checker_columns.py        ← Column dimension check (EHE)
│   ├── checker_slabs.py          ← Slab thickness check (EHE / DB SE)
│   ├── checker_walls.py          ← Wall thickness + U-value checks (DB SE-F, CTE DB HE)
│   ├── checker_reinforcement.py  ← Reinforcement checks
│   └── checker_accessibility.py  ← Accessibility checks (DB SUA)
│
├── data/                         ← Sample IFC files for testing
│   ├── 01_Duplex_Apartment.ifc
│   ├── Ifc4_SampleHouse.ifc
│   └── ...
│
├── beam_check/                   ← Legacy source module (beams/columns)
├── walls_check/                  ← Legacy source module (walls)
└── reinforcement_check/src/      ← Legacy source module (slabs/foundations)
```

---

## Gradio App — Foundation Compliance

The app has two tabs:

| Tab | What it does |
|-----|-------------|
| **Foundation Compliance** | Runs 4 automated regulatory checks against uploaded IFC |
| **Analyze Properties** | Extracts raw properties (thickness, area, materials, loads) from IFC |

### Foundation Compliance checks

| Check | Regulation | Requirement |
|-------|-----------|------------|
| Slab Thickness | Art. 69 | ≥ 300 mm (150 mm concrete + 150 mm drainage) |
| Foundation Dimensions | Load Check | Footing area ≥ required area (load / bearing capacity) |
| Bearing Beam Section | DB SE-AE | Width × Depth ≥ 300 × 300 mm |
| Floor Capacity | Art. 128 | Shows max floors and how many can be added |

### Result badges

| Badge | Meaning |
|-------|---------|
| `PASS` | Element meets the requirement |
| `FAIL` | Element does not meet the requirement |
| `WARN` | Marginal — review recommended |
| `BLOCKED` | Data needed for the check is missing from the IFC model |

---

## CLI Checkers — All Tools

Each file in `tools/` is a self-contained script. Run any of them directly:

```bash
py tools/<checker_name>.py <path_to_ifc_file>
```

### checker_foundation.py

Checks foundation elements against Spanish Building Ordinances.

| Function | Regulation | Checks |
|----------|-----------|--------|
| `check_foundation_slab_thickness` | Art. 69 | IfcFooting + on-grade IfcSlab ≥ 300 mm |
| `check_foundation_dimensions` | Load Check | Footing L×W vs required area from bearing capacity |
| `check_bearing_beam_section` | DB SE-AE | Bearing beam ≥ 300×300 mm at lowest storey |
| `check_floor_capacity` | Art. 128 | Max floors = bearing / floor load; addable floors |

### checker_beams.py

| Function | Regulation | Minimum |
|----------|-----------|---------|
| `check_beam_depth` | EHE / DB SE | ≥ 200 mm |
| `check_beam_width` | EHE / DB SE | ≥ 150 mm |

### checker_columns.py

| Function | Regulation | Minimum |
|----------|-----------|---------|
| `check_column_min_dimension` | EHE | ≥ 250 mm (smallest side) |

### checker_slabs.py

| Function | Regulation | Range |
|----------|-----------|-------|
| `check_slab_thickness` | EHE / DB SE | 100 – 200 mm |

### checker_walls.py

| Function | Regulation | Requirement |
|----------|-----------|------------|
| `check_wall_thickness` | DB SE-F / EHE | ≥ 100 mm |
| `check_wall_uvalue` | CTE DB HE | ≤ 0.80 W/(m²·K) |
| `check_wall_external_uvalue` | CTE DB HE | U-value must be defined for external walls |

---

## IFC Dimension Extraction

Checkers look for dimensions in this priority order:

1. **Quantity sets** — `Qto_FootingBaseQuantities`, `Qto_BeamBaseQuantities`, etc.
2. **Geometry** — `IfcExtrudedAreaSolid → IfcRectangleProfileDef`
3. **Property sets** — `Pset_WallCommon`, `PSet_Revit_Type_Dimensions`, etc.
4. **Element name** — parses patterns like `"900 x 300"` or `"150mm Slab on Grade"` (Revit naming convention)
5. **Material layers** — sums `IfcMaterialLayerSet` thicknesses

If none of these yield a value, the result is `BLOCKED` with a description of what was searched.

---

## Sample IFC Files

| File | Description |
|------|-------------|
| `01_Duplex_Apartment.ifc` | Residential duplex — footings, slabs, walls |
| `Ifc4_SampleHouse.ifc` | IFC4 sample house |
| `Ifc4_SampleHouse_1_Roof.ifc` | Roof-only subset |
| `Ifc4_SampleHouse_IfcWallStandardCase.ifc` | Wall-heavy model |
| `Ifc4_Revit_ARC_FireRatingAdded.ifc` | Revit export with fire ratings |

---

## Requirements

```
ifcopenshell>=0.8.4
numpy
gradio>=4.20
python-dotenv>=1.0.0
```

Install with:

```bash
pip install ifcopenshell numpy gradio python-dotenv
```