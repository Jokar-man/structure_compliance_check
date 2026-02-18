# Architecture & Conventions

## Project Structure

```
your-team-repo/
├── tools/
│   ├── checker_doors.py
│   ├── checker_fire_safety.py
│   └── checker_rooms.py
├── requirements.txt
└── README.md
```

- Max 300 lines per file
- One function per check
- File names: `checker_<topic>.py`
- Function names: `check_<what>`
- First arg is always `model` (an `ifcopenshell.file` object)
- Return `list[str]` — each string prefixed `[PASS]`, `[FAIL]`, or `[???]`
- No bare try/except

## AGENTS.md / CLAUDE.md Template

Every team MUST have this file in their repo root.

```markdown
# <Project Name>

Always read the IFCore skill before developing on this project.

## Structure
<paste your app/ directory tree here>

## Conventions
- Max 300 lines per file
- One function per regulation check
- Files: tools/checker_<topic>.py
- Functions: check_*(model, ...) -> list[str] with [PASS]/[FAIL]/[???] prefix

## Issue Reporting
gh issue create --repo SerjoschDuering/iaac-bimwise-skills --label "<label>" --title "<title>"
Labels: contract-gap, skill-drift, learning, schema-change, integration-bug

## Learnings
<!-- Add here after every debugging session -->
```
