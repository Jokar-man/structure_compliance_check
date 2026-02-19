# AGENTS.md — IFCore Compliance Checker

## Repository Structure

```
structure_compliance_check/
├── tools/                     ← IFCore-compliant checker modules
│   ├── checker_walls.py       ← check_wall_thickness, check_wall_uvalue, check_wall_external_uvalue
│   ├── checker_beams.py       ← check_beam_depth, check_beam_width
│   ├── checker_columns.py     ← check_column_min_dimension
│   ├── checker_slabs.py       ← check_slab_thickness
│   ├── checker_reinforcement.py ← check_ground_slab_thickness, check_foundations
│   └── checker_accessibility.py ← check_door_width, check_window_height, ...
├── mani_mock/                 ← Gradio web application
│   ├── app.py                 ← Main UI
│   ├── orchestrator.py        ← Runs all team checks
│   ├── models.py              ← Data models (IFCore schema)
│   ├── teams/                 ← Team adapters (auto-discovered)
│   └── ...
├── walls_check/               ← Wall extraction + rules (source module)
├── beam_check/src/            ← Beam/column/door/stair checks (source module)
└── reinforcement_check/src/   ← Slab/foundation analysis (source module)
```

## Conventions

- **Checker files**: `tools/checker_<topic>.py`
- **Check functions**: `check_<what>(model, **kwargs) → list[dict]`
- **Required dict keys**: `element_id`, `element_type`, `element_name`, `element_name_long`, `check_status`, `actual_value`, `required_value`, `comment`, `log`
- **Status values**: `pass`, `fail`, `warning`, `blocked`, `log`
- **Max file length**: 300 lines per file
