---
description: Full rule-based equity analysis (Bull/Bear/Macro/Devil's Advocate lenses + verdict). No API key needed. Usage: /analyze NVDA or a full question.
---

Run the AgentMesh analysis CLI for this question/ticker and report back the
overall verdict plus the path to the saved PDF. This is entirely rule-based
-- every finding is computed from live yfinance/OpenBB data, no LLM call.

If `$ARGUMENTS` is empty, ask the user what stock or question to analyze
before running anything.

Run from the `agentmesh/` project directory (the one containing `mesh.py`
and `.venv/`):

```bash
source .venv/bin/activate && python mesh.py "$ARGUMENTS"
```
