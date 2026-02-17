# BIMwise - IFC Compliance Checker

Welcome to BIMwise. You're a startup building automated building compliance checking. Upload an IFC model, run checks against regulations, see what fails. By Friday you pitch this to investors.

## Setup

```bash
git clone https://github.com/SerjoschDuering/iaac-bimwise-starter.git
cd iaac-bimwise-starter
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Verify: `python -c "import ifcopenshell, gradio; print('Ready')"`

## What's in the Repo

```
00_data/
  ifc_models/              Duplex Apartment (14 doors, 24 windows, 57 walls)
  regulations/
    sample_regulations_basic.md       6 numeric checks (door width, room area, ...)
    sample_regulations_advanced.md    4 checks that need LLM reasoning

exercises/
  01_explore_ifc.ipynb     Open an IFC, query elements, plot properties
  02_llm_basics.ipynb      Call Gemini, system prompts
  03_structured_output.ipynb   Get JSON from an LLM, parse it
  04_llm_decisions.ipynb   LLM evaluates a regulation, code acts on result
  05_pydantic_ai_agents.ipynb  Agents, tools, chains with PydanticAI

app/
  app_simple.py            Text-only results (Monday)
  app.py                   3D viewer, failures in red (Tuesday+)
  src/
    ifc_checker.py         YOUR CODE GOES HERE
    ifc_visualizer.py      Don't touch
```

## The One File You Edit

`app/src/ifc_checker.py` -- add check functions, wire them into `run_all_checks()`.

Each check returns a list of results:
```python
{
    "element_id": "2O2Fr$t4X7Zf8NOew3FLOH",
    "element_type": "IfcDoor",
    "element_name": "Door #1",
    "rule": "Min Door Width",
    "requirement": ">= 800 mm",
    "actual": "900 mm",
    "passed": True
}
```

Failed elements show up red in the 3D viewer.

## Run the App

```bash
cd app
python app_simple.py    # Monday: text results
python app.py           # Tuesday+: 3D viewer
```

## The Week

**Mon -- Make It Work:** Explore IFC files (notebooks 01), write check functions by hand, see results in Gradio.

**Tue -- Make It Talk:** Add LLM reasoning (notebooks 02-05), agree on a shared data schema across teams. Board meeting #1 drops company standards.

**Wed -- Make It Connect:** Deploy your agent to HuggingFace Spaces, add RAG so agents look up regulations themselves. Board meeting #2: "We need one product by Friday."

**Thu -- Make It Real:** Integration sprint. Frontend + orchestrator + team agents connect. Rehearse the pitch.

**Fri -- Present:** Pitch to investors.

## Resources

- IFC spec: https://standards.buildingsmart.org/IFC/
- ifcopenshell: http://ifcopenshell.org/
- Gradio: https://gradio.app/docs/
- Online IFC viewer: https://ifcviewer.com
