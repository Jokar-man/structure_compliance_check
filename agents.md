# AGENTS.md — Structure Compliance Check

Developer and AI agent reference for contributing to or extending this project.

---

## Project Overview

This project checks BIM/IFC building models for structural and regulatory compliance.
It has two interfaces:
- **Gradio web app** — `reinforcement_check/app.py`
- **Standalone CLI tools** — `tools/checker_*.py`

---

## Repository Structure

```
structure_compliance_check/
│
├── reinforcement_check/          ← Gradio web application (main app)
│   ├── app.py                    ← Entry point: run with `py reinforcement_check/app.py`
│   ├── requirements.txt
│   └── src/
│       ├── ifc_analyzer.py       ← IFCAnalyzer class (property extraction)
│       └── report_generator.py   ← ReportGenerator class (HTML/text output)
│
├── tools/                        ← Standalone IFCore-compliant checker modules
│   ├── checker_foundation.py     ← Art. 69, Art. 128, DB SE-AE (foundation)
│   ├── checker_beams.py          ← EHE / DB SE (beam depth + width)
│   ├── checker_columns.py        ← EHE (column min dimension)
│   ├── checker_slabs.py          ← EHE / DB SE (slab thickness)
│   ├── checker_walls.py          ← DB SE-F, EHE, CTE DB HE (walls)
│   ├── checker_reinforcement.py  ← Reinforcement checks
│   └── checker_accessibility.py  ← DB SUA (doors, windows, corridors)
│
├── data/                         ← Sample IFC files for testing
│
├── beam_check/                   ← Legacy source (do not import from tools/)
├── walls_check/                  ← Legacy source (do not import from tools/)
└── reinforcement_check/src/      ← Legacy source (do not import from tools/)
```

---

## IFCore Contract

Every check function in `tools/` must follow this contract:

### Function signature

```python
def check_<topic>(model: ifcopenshell.file, **kwargs) -> list[dict]:
    ...
```

- Accepts an `ifcopenshell.file` object
- Returns a `list[dict]` — one dict per element checked

### Required dict keys (9 fields)

```python
{
    "element_id":        str | None,   # GlobalId of the IFC element
    "element_type":      str,          # e.g. "IfcFooting", "IfcWall"
    "element_name":      str,          # Short display name
    "element_name_long": str | None,   # Long name with context/regulation
    "check_status":      str,          # "pass" | "fail" | "warning" | "blocked" | "log"
    "actual_value":      str | None,   # Measured value (e.g. "250 mm", "0.75 W/(m²·K)")
    "required_value":    str | None,   # Required value (e.g. "≥ 300 mm")
    "comment":           str | None,   # Human-readable explanation
    "log":               str | None,   # Debug info (key=value pairs)
}
```

### Status values

| Status | When to use |
|--------|------------|
| `pass` | Element meets the regulation |
| `fail` | Element does not meet the regulation |
| `warning` | Marginal / borderline case — review recommended |
| `blocked` | Required data not found in IFC model |
| `log` | Informational row (not a compliance result) |

---

## Adding a New Checker

1. Create `tools/checker_<topic>.py`
2. Import only `ifcopenshell` and stdlib — **no imports from other project folders**
3. Write private helpers prefixed with `_`
4. Write public `check_*` functions following the IFCore contract above
5. Add a `__main__` block for CLI use:

```python
if __name__ == "__main__":
    import sys
    ifc_path = sys.argv[1] if len(sys.argv) > 1 else "data/01_Duplex_Apartment.ifc"
    print("Loading:", ifc_path)
    _model = ifcopenshell.open(ifc_path)

    _ICON = {"pass": "PASS", "fail": "FAIL", "warning": "WARN", "blocked": "BLKD", "log": "LOG "}
    for _fn in [check_my_function]:
        print("\n" + "=" * 60)
        print(" ", _fn.__name__)
        print("=" * 60)
        for _row in _fn(_model):
            print(" ", "[" + _ICON.get(_row["check_status"], "?") + "]", _row["element_name"])
            if _row["actual_value"]:
                print("         actual   :", _row["actual_value"])
            if _row["required_value"]:
                print("         required :", _row["required_value"])
            print("         comment  :", _row["comment"])
```

6. Run from the project root:

```bash
py tools/checker_<topic>.py data/01_Duplex_Apartment.ifc
```

---

## Dimension Extraction Priority

When extracting dimensions from IFC elements, use this fallback chain:

| Priority | Source | Example |
|----------|--------|---------|
| 1 | Quantity sets | `Qto_FootingBaseQuantities.Width` |
| 2 | Extruded geometry | `IfcExtrudedAreaSolid → IfcRectangleProfileDef` |
| 3 | Property sets | `PSet_Revit_Type_Dimensions.d`, `Pset_WallCommon.Width` |
| 4 | Element name parsing | `"Bearing Footing - 900 x 300"` → width=900mm, depth=300mm |
| 5 | Material layers | Sum of `IfcMaterialLayerSet` thicknesses |

If all paths fail → return `check_status: "blocked"` with a comment listing what was searched.

---

## Unit Handling

- Use `_get_length_scale(model)` to read `IfcUnitAssignment` and get a metre conversion factor
- Multiply all geometry/quantity values by `scale` to convert to metres
- Do **not** scale pressure/load values (kN/m²) — these are unit-independent

---

## Gradio App Integration

To add a new checker to the Gradio app (`reinforcement_check/app.py`):

1. Import the checker at the top of `app.py`:
   ```python
   sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
   from checker_<topic> import check_<function>
   ```
2. Call it inside a tab's button handler
3. Pass results to `_build_*_html()` or add a new rendering function
4. Return an `gr.HTML` component with the results

---

## Regulations Reference

| Regulation | Topic | Requirement |
|-----------|-------|------------|
| Art. 69 (Met. Building Ord.) | Foundation slab thickness | ≥ 300 mm (150 mm concrete + 150 mm drainage) |
| Art. 128 (Met. Building Ord.) | Floor capacity | max floors = bearing capacity / floor load |
| DB SE-AE | Bearing beam section | ≥ 300 × 300 mm |
| EHE | Beam depth | ≥ 200 mm |
| EHE | Beam width | ≥ 150 mm |
| EHE | Column min side | ≥ 250 mm |
| EHE / DB SE | Slab thickness | 100 – 200 mm |
| DB SE-F / EHE | Wall thickness | ≥ 100 mm |
| CTE DB HE | Wall U-value | ≤ 0.80 W/(m²·K) |
| DB SUA | Door width | ≥ 800 mm |

---

## Running the App

```bash
py reinforcement_check/app.py
```

Gradio auto-selects an available port. The browser opens automatically.

## Running Individual Checkers

```bash
py tools/checker_foundation.py  data/01_Duplex_Apartment.ifc
py tools/checker_beams.py       data/01_Duplex_Apartment.ifc
py tools/checker_columns.py     data/01_Duplex_Apartment.ifc
py tools/checker_slabs.py       data/01_Duplex_Apartment.ifc
py tools/checker_walls.py       data/01_Duplex_Apartment.ifc
```
