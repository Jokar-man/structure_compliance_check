---
name: IFCore
description: Use when developing on the IFCore compliance checker. Covers contracts, check function conventions, issue reporting, app structure, and development patterns.
---

# IFCore — Company Skill

> **Living document.** Sections marked [TBD] are decided in board meetings.
> When a [TBD] is resolved, update this skill and tell your agent to adapt.

## When This Skill Activates

Welcome the user. Introduce yourself as their IFCore development assistant. Explain:

1. **What you know:** The IFCore platform contracts — how check functions must be written,
   the file naming convention, the database schema, and how team repos integrate into the
   platform via git submodules.

2. **What you can do:**
   - Help write `check_*` functions that comply with the platform contracts
   - Review existing code for contract compliance
   - Explain IFC file structure and ifcopenshell patterns
   - Help with feature planning (PRDs, user stories)
   - File issues to the shared skills repo when contracts are unclear

3. **Offer a codebase review.** Ask to scan the current repo and check:
   - Are `checker_*.py` files directly inside `tools/`?
   - Do all `check_*` functions follow the contract (signature, return type)?
   - Is there anything that would block platform integration?

4. **Respect their setup.** Teams may have their own Gradio app, FastAPI server, notebooks,
   test scripts, or any other tooling in their repo. **That's fine.** The platform only cares
   about `tools/checker_*.py` files — everything else is ignored during integration.
   The only hard rule: don't put anything in `tools/` that breaks the `checker_*.py` import
   chain (e.g. conflicting `__init__.py` files or dependencies not in `requirements.txt`).

5. **Offer to explain Agent Skills.** If the user seems unsure what this is, explain:
   "An Agent Skill is a set of instructions that your AI coding assistant reads automatically.
   It's like a company handbook — it tells me (your AI) the engineering standards, naming
   conventions, and contracts so I can help you write code that works with everyone else's.
   You installed it once; now I follow it in every conversation."

6. **How to install & update this skill.**
   Install the skill **globally** so it works in every project on your machine:
   ```
   Install (once):
   1. Clone: git clone https://github.com/SerjoschDuering/iaac-bimwise-skills.git
   2. Add the skill GLOBALLY in your AI coding tool:
      - VS Code/Copilot: Chat panel → Add Agent Skill → pick the SKILL.md file (User scope)
      - Cursor: Settings → Agent Skills → Add → point to the cloned folder.
      - Claude Code: add to ~/.claude/settings.json under agent skills
   3. Start a new chat session — your AI now knows IFCore standards.

   Update (after board meetings):
   1. cd into your cloned skills folder
   2. git pull
   3. Start a fresh chat session
   ```

## Contracts — READ THIS FIRST

### 1. Check Function Contract

```python
# Function naming: check_<what>
# Location: tools/checker_*.py (directly inside tools/, no subdirectories)
# Signature: first arg is always the ifcopenshell model
# Return: list[dict] — one dict per element, maps to element_results DB rows

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

**Rules:**
- Prefix `check_` — discovered by this prefix
- First arg: `model` (an `ifcopenshell.file` object) — always
- Return: `list[dict]` with fields matching `element_results`
- `check_status` values: `"pass"`, `"fail"`, `"warning"`, `"blocked"`, `"log"`
- One function per regulation check
- Files must be directly inside `tools/` (no subdirectories)

### 2. File Structure Contract

```
your-team-repo/
├── tools/
│   ├── checker_doors.py
│   ├── checker_fire_safety.py
│   └── checker_rooms.py
├── requirements.txt
└── README.md
```

### 3. Issue Reporting Contract — MANDATORY

| Trigger | Label |
|---|---|
| Contract unclear or ambiguous | `contract-gap` |
| Skill instructions don't match reality | `skill-drift` |
| Found a workaround for a known limitation | `learning` |
| Schema format needs a new field | `schema-change` |
| Team code works locally but breaks on platform | `integration-bug` |

```bash
gh issue create \
  --repo SerjoschDuering/iaac-bimwise-skills \
  --title "contract-gap: check functions with multiple models" \
  --label "contract-gap" \
  --body "..."
```

## Company Context

IFCore is building an AI-powered building compliance checker. 5 teams each develop in their
own GitHub repo. The platform integrates them automatically via git submodules.

| Component | Deploys to | Who manages |
|-----------|-----------|-------------|
| Team check functions | Own GitHub repo → pulled into platform | Each team |
| Backend + orchestrator | HuggingFace Space (Docker, FastAPI) | Captains |
| Frontend | Cloudflare Pages | Captains |
| API gateway | Cloudflare Worker | Captains |
| File storage | Cloudflare R2 | Captains |
| Results database | Cloudflare D1 (SQLite) | Captains |

## References
- [Validation Schema](./references/validation-schema.md)
- [Architecture](./references/architecture.md)
- [Repo Structure](./references/repo-structure.md)
- [Frontend Architecture](./references/frontend-architecture.md)
- [Development Patterns](./references/development-patterns.md)
