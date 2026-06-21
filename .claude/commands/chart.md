---
description: Render a standalone 12-month price chart for a ticker. No debate. Usage: /chart NVDA
---

`$ARGUMENTS` is a single stock ticker (e.g. `NVDA`, `RELIANCE.NS`, `7203.T`).
If it's empty, ask the user for a ticker before running anything.

Run from the `agentmesh/` project directory (the one containing `mesh.py`
and `.venv/`):

```bash
source .venv/bin/activate && python mesh.py --chart "$ARGUMENTS"
```

Report back the saved PNG path.
