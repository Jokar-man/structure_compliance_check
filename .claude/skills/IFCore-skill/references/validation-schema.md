# Validation Schema

## Team Output (locked — Board Meeting #1)

Each `check_*` function returns `list[dict]`. Each dict maps to one `element_results` row.

```python
def check_door_width(model, min_width_mm=800):
    results = []
    for door in model.by_type("IfcDoor"):
        width_mm = round(door.OverallWidth * 1000) if door.OverallWidth else None
        results.append({
            "element_id":        door.GlobalId,
            "element_type":      "IfcDoor",
            "element_name":      door.Name or f"Door #{door.id()}",
            "element_name_long": f"{door.Name} (Level 1, Zone A)",
            "check_status":      "blocked" if width_mm is None
                                 else "pass" if width_mm >= min_width_mm
                                 else "fail",
            "actual_value":      f"{width_mm} mm" if width_mm else None,
            "required_value":    f"{min_width_mm} mm",
            "comment":           None if width_mm and width_mm >= min_width_mm
                                 else f"Door is {min_width_mm - width_mm} mm too narrow"
                                 if width_mm else "Width property missing",
            "log":               None,
        })
    return results
```

**Required dict fields:**

| Field | Type | Description |
|-------|------|-------------|
| `element_id` | string / null | IFC GlobalId |
| `element_type` | string / null | e.g. "IfcDoor" |
| `element_name` | string / null | Short name |
| `element_name_long` | string / null | Detailed name with context |
| `check_status` | string | pass / fail / warning / blocked / log |
| `actual_value` | string / null | What was found |
| `required_value` | string / null | What regulation requires |
| `comment` | string / null | Human-readable explanation |
| `log` | string / null | Debug/trace info |

## Platform DB Schema (D1) — 4 tables

users → projects → check_results → element_results

### check_results row (one per check_* function run)
- check_name, team, status (running|pass|fail|unknown|error), summary, has_elements

### element_results row (one per element checked, orchestrator adds id + check_result_id)
- element_id, element_type, element_name, element_name_long
- check_status (pass|fail|warning|blocked|log)
- actual_value, required_value, comment, log

## End-to-End Example

```
Team returns:
  [{"element_name": "Door #42", "check_status": "pass", "actual_value": "850 mm", ...},
   {"element_name": "Door #17", "check_status": "fail", "actual_value": "750 mm",
    "comment": "Door is 50 mm too narrow", ...}]

Orchestrator writes:
  check_results:  check_name="check_door_width", status="fail", summary="2 doors: 1 pass, 1 fail"
  element_results: two rows, one pass, one fail
```
