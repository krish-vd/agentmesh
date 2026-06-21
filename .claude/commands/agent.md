---
description: Run a single AgentMesh lens (bull, bear, macro, or devils_advocate) on its own. No API key needed. Usage: /agent bull NVDA
---

The user wants just one lens of the rule-based analysis, not the full
four-lens report.

`$ARGUMENTS` contains the lens name followed by the ticker/question, e.g.
`bull NVDA` or `devils_advocate Is Nifty valuation even the question?`.

Parse out the first word as the lens name (must be one of: `bull`, `bear`,
`macro`, `devils_advocate`) and the rest as the question. If the lens name
isn't one of those four, or the question is missing, ask the user to clarify
before running anything.

Run from the `agentmesh/` project directory (the one containing `mesh.py`
and `.venv/`), substituting the parsed lens name and question:

```bash
source .venv/bin/activate && python mesh.py --agent <lens_name> "<question>"
```
