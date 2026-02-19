# IFCore — Integrated Compliance Platform (`mani_mock`)

Unified IFC compliance checking platform that integrates all team modules into a single orchestrator + dashboard.

## Quick Start

```bash
cd mani_mock
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:7860 → Upload an IFC file → Results appear across all tabs.

## Architecture

```
mani_mock/
├── app.py                 ← Gradio frontend (7 tabs)
├── orchestrator.py        ← Central engine: discover teams → run checks → collect results
├── models.py              ← Data models (Project → CheckResult → ElementResult)
├── config.py              ← Thresholds & region codes
├── utils.py               ← Shared IFC utilities
├── report_engine.py       ← JSON / HTML / Text report generators
├── requirements.txt
│
└── teams/                 ← Team plugin directory
    ├── __init__.py        ← Auto-discovery registry
    ├── beam_team.py       ← Wraps beam_check/
    ├── wall_team.py       ← Wraps walls_check/
    ├── slab_team.py       ← Wraps slab_check/
    ├── column_team.py     ← Column dimension checks
    ├── reinforcement_team.py  ← Wraps reinforcement_check/
    ├── accessibility_team.py  ← Doors, windows, corridors, stairs, railings
    └── _template_team.py  ← Copy this to add your team!
```

## Data Schema (IFCore)

```
Project
 ├── id, name, file_url, ifc_schema, region, ...
 └── check_results[]
      ├── id, check_name, team, status, summary
      └── elements[]
           ├── element_id, element_type, element_name
           ├── status (pass | fail | unknown)
           ├── actual_value, required_value
           └── raw
```

## Adding Your Team

1. Copy `teams/_template_team.py` → `teams/my_team.py`
2. Set `TEAM_NAME = "my_team"`
3. Implement check functions that return `list[dict]` with keys:
   - `element_id`, `element_type`, `element_name`
   - `status` (pass / fail / unknown)
   - `actual_value`, `required_value`, `raw`
4. Add them to `TEAM_CHECKS`
5. Restart the app — your team is auto-discovered!

## Current Teams

| Team              | Checks                                                       | Source Module                   |
| ----------------- | ------------------------------------------------------------ | ------------------------------- |
| **beams**         | Beam depth, beam width                                       | `beam_check/src/ifc_checker.py` |
| **walls**         | Thickness, U-value, external wall U-value                    | `walls_check/`                  |
| **slabs**         | Thickness range (100–200 mm)                                 | `slab_check/slab.py`            |
| **columns**       | Min cross-section dimension                                  | `beam_check/src/ifc_checker.py` |
| **reinforcement** | Ground slab thickness, foundation thickness                  | `reinforcement_check/src/`      |
| **accessibility** | Doors, windows, openings, corridors, rooms, stairs, railings | `beam_check/src/ifc_checker.py` |

## JSON Output

Run from CLI to get the full JSON report:

```bash
python orchestrator.py path/to/model.ifc > report.json
```

## Integration

This platform is designed to integrate with the IFCore architecture:

- **Backend**: Can be deployed as a HuggingFace Space with FastAPI
- **Frontend**: Dashboard can be served via Cloudflare Pages
- **Storage**: JSON output is compatible with Cloudflare D1 / R2
- **Other teams**: Just drop new team modules into `teams/`
