# AgentMesh

Rule-based, multi-lens equity research tool that runs inside [Claude Code](https://claude.com/claude-code) as a set of slash commands.

No LLM, no API key required. Every finding is computed deterministically from live market data (via [OpenBB](https://openbb.co/) and `yfinance`) across four lenses — **Bull**, **Bear**, **Macro**, **Devil's Advocate** — followed by a rebuttal round and a verdict. Output is an institutional-style PDF research note plus a standalone price chart with technical context (52-week high/low, volatility band, 50-day MA).

Works on any market yfinance covers: US, India (NSE/BSE), UK, Europe, Japan, Hong Kong, and more.

---

## What you get

- `/analyze TICKER` — full four-lens analysis + rebuttal round + verdict, saved as a PDF
- `/agent LENS TICKER` — a single lens in isolation (`bull`, `bear`, `macro`, or `devils_advocate`)
- `/chart TICKER` — a standalone 12-month price chart (PNG)

Everything is computed from real fundamentals and price history — there is no AI-generated text anywhere in this pipeline. The "debate" is a deterministic comparison of cited metrics, not an LLM conversation.

---

## Requirements

- **Python 3.10+** (the code uses `str | None` union syntax, which fails on Python 3.9 and earlier)
- **Claude Code** installed ([instructions here](https://claude.com/claude-code)) — only needed if you want to use the slash commands; the underlying CLI works standalone too
- macOS, Linux, or WSL (no special OS dependencies beyond Python)

Check your Python version:
```bash
python3 --version
```
If it's below 3.10, install a newer version. On macOS with Homebrew:
```bash
brew install python@3.11
```

---

## Setup (from scratch)

### 1. Clone the repo

```bash
git clone <your-repo-url> agentmesh
cd agentmesh
```

### 2. Create a virtual environment

Use whichever Python 3.10+ binary you have. On macOS with Homebrew's Python 3.11:

```bash
/opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate
```

On Linux, swap in your own Python 3.10+ path (e.g. `python3.11 -m venv .venv`).

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs `openbb`, `yfinance`, `reportlab`, `matplotlib`, `pandas`, and a few smaller packages. The first import of `openbb` will take a little while as it builds its local provider registry — that's normal, only happens once.

### 4. (Optional) Set up `.env`

No key is required for the core pipeline. `.env` is only needed if you want the extra India-specific data layer:

```bash
cp .env.example .env
```

Then edit `.env` and add a free key from [indianapi.in](https://indianapi.in) if you want quarterly results, shareholding patterns, and analyst targets for NSE/BSE stocks. Without it, Indian tickers still work fine — they just skip that extra layer and fall back to the standard yfinance/OpenBB data plus BSE/NSE/SEBI filing links.

### 5. Verify it works

```bash
python mesh.py NVDA
```

You should see live price/fundamentals data print to the terminal, followed by the four-lens analysis, a rebuttal round, a verdict, and finally a line like:
```
Report saved: outputs/analysis_report_NVDA_<timestamp>.pdf
```

If that worked, the core pipeline is installed correctly.

---

## Using it inside Claude Code (slash commands)

The slash commands live in `.claude/commands/` and are **project-scoped** — Claude Code only discovers them when its working directory/session root is this `agentmesh/` folder itself, not a parent directory.

### Open Claude Code rooted at this folder

```bash
cd agentmesh
claude
```
(Or in VS Code / another IDE: open `agentmesh/` directly as the workspace folder, then launch Claude Code from there.)

### Then just type the commands as your messages

```
/analyze Should I buy NVDA at current valuation?
/analyze RELIANCE.NS
/agent bear TSLA
/agent devils_advocate Is HDFC Bank overvalued?
/chart 7203.T
```

Claude will activate the virtual environment and run the underlying `mesh.py` command for you, then report back the verdict and the path to the saved PDF/PNG.

**Important:** activate the venv first if you're running things manually outside of Claude Code's slash commands:
```bash
source .venv/bin/activate
```

---

## Using it without Claude Code (plain CLI)

Everything works as a standalone Python CLI too:

```bash
source .venv/bin/activate

# Full four-lens analysis + verdict + PDF
python mesh.py "Should I buy NVDA at current valuation?"
python mesh.py "RELIANCE.NS valuation check"

# Single lens only
python mesh.py --agent bull NVDA
python mesh.py --agent bear AAPL
python mesh.py --agent macro RELIANCE.NS
python mesh.py --agent devils_advocate TSLA

# Chart only, no analysis
python mesh.py --chart NVDA
python mesh.py --chart RELIANCE.NS
python mesh.py --chart 7203.T
```

Run `python mesh.py --help` for the full flag list.

---

## Ticker formats

| Market      | Exchange    | Format    | Examples                          |
|-------------|-------------|-----------|------------------------------------|
| US          | NYSE/NASDAQ | `TICKER`    | `NVDA`, `AAPL`, `TSLA`             |
| India NSE   | NSE         | `TICKER.NS` | `RELIANCE.NS`, `TCS.NS`, `HDFCBANK.NS` |
| India BSE   | BSE         | `TICKER.BO` | `RELIANCE.BO`, `TCS.BO`            |
| UK          | LSE         | `TICKER.L`  | `SHEL.L`, `AZN.L`, `HSBA.L`        |
| Germany     | XETRA       | `TICKER.DE` | `SAP.DE`, `BMW.DE`                 |
| Netherlands | AEX         | `TICKER.AS` | `ASML.AS`                          |
| France      | CAC         | `TICKER.PA` | `MC.PA`, `OR.PA`                   |
| Japan       | Tokyo       | `CODE.T`    | `7203.T` (Toyota), `6758.T` (Sony) |
| Hong Kong   | HKEX        | `CODE.HK`   | `0700.HK` (Tencent)                |
| Switzerland | SIX         | `TICKER.SW` | `NESN.SW`                          |
| Canada      | TSX         | `TICKER.TO` | `SHOP.TO`                          |
| Australia   | ASX         | `TICKER.AX` | `BHP.AX`                           |

You can either pass a bare ticker or a full sentence containing one — `extract_ticker()` in `mesh.py` will find it either way.

---

## How the analysis works

All logic lives in `tools/analysis_engine.py` and `tools/synthesizer.py` — no LLM calls anywhere.

- **Bull** cites every strength signal found in the fetched fundamentals: revenue/earnings growth, margins, ROE, FCF yield, low leverage, favorable PEG, positive momentum.
- **Bear** cites every weakness signal: rich valuation vs. a sector-relative P/E band, high leverage, thin liquidity, high beta, weak growth, negative FCF, recent drawdown.
- **Macro** derives regime sensitivity from beta, dividend yield, currency exposure (for non-USD names), and realized 20/30-day volatility.
- **Devil's Advocate** flags framing risk: reliance on forward-earnings assumptions, mega-cap reflexivity, elevated short interest, or cases where neither Bull nor Bear found anything (meaning the real debate is qualitative, not quantitative).
- A **rebuttal round** has Bear directly counter Bull's single strongest cited metric (and vice versa) using whatever countervailing figure exists in the same dataset — or states plainly that the claim is unchallenged.
- A **deterministic synthesizer** scores the bull/bear signal count (adjusted for whether each rebuttal landed) into a `BULLISH` / `NEUTRAL` / `BEARISH` verdict with a confidence percentage, plus consensus points and open questions.

This is **not investment advice**. Every cited figure should be verified against primary filings (10-K/10-Q for US names, BSE/NSE disclosures for Indian names) — the report itself says so on every page footer.

---

## Project structure

```
agentmesh/
├── .claude/commands/        # Claude Code slash commands (/analyze, /agent, /chart)
├── CLAUDE.md                # Claude Code project instructions
├── mesh.py                  # CLI entry point
├── report.py                # PDF research-note generator (reportlab)
├── tools/
│   ├── fetch_global.py      # OpenBB/yfinance price + fundamentals, any market
│   ├── fetch_india.py       # Optional India-specific data (indianapi.in)
│   ├── fetch_filings.py     # SEC EDGAR (US) / BSE/NSE/SEBI links (India)
│   ├── render_chart.py      # Price chart with 52w high/low, volatility band, MA
│   ├── analysis_engine.py   # Bull/Bear/Macro/Devil's Advocate logic + rebuttal round
│   └── synthesizer.py       # Verdict, consensus, and open-questions logic
├── outputs/                 # Generated PDFs and PNGs land here (gitignored)
├── requirements.txt
└── .env.example
```

---

## Troubleshooting

**`TypeError` on import, mentioning `|` or union types** — you're running Python 3.9 or older. Use Python 3.10+ (see Requirements above).

**Slash commands don't show up in Claude Code** — your Claude Code session must be rooted at this `agentmesh/` folder, not a parent directory. `cd` into `agentmesh/` before launching `claude`, or open this exact folder as your IDE workspace.

**No price data / "No price history found for TICKER"** — check the ticker format against the table above; most non-US tickers need an exchange suffix (`.NS`, `.L`, `.T`, etc.).

**PDF fonts look like plain Helvetica/Times instead of Georgia/Arial** — that's a cosmetic fallback, not an error. The report looks for Georgia/Arial (macOS) or DejaVu (Linux) and falls back gracefully if neither is present on your system.

**First run is slow** — OpenBB builds a local provider registry on first import. Subsequent runs are fast.

---

*Not investment advice. Verify every figure against primary sources.*
