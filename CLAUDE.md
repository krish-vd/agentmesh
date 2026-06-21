# AgentMesh V2

Rule-based multi-lens equity analysis. No LLM, no API key. Four lenses
analyze any stock from real fundamentals/price data -- Bull, Bear, Macro,
Devil's Advocate -- and a deterministic synthesizer produces a verdict.
Produces an institutional-style PDF Analysis Report.

All findings are computed directly from live yfinance/OpenBB data via
`tools/analysis_engine.py` and `tools/synthesizer.py`. Nothing here calls
an LLM; an LLM-backed debate mode can be added back later as an option.

Supports stocks from any market: US (NVDA), India (RELIANCE.NS),
UK (SHEL.L), Europe (ASML.AS), Japan (7203.T), and more.

---

## Commands

### /analyze [ticker or question]
Full four-lens analysis + verdict. Saves a PDF.
  python mesh.py "Should I buy Reliance Industries at current valuation?"
  python mesh.py "Is HDFC Bank a buy after the merger integration?"
  python mesh.py NVDA

### /agent [lens_name] [ticker or question]
Single lens only: bull, bear, macro, or devils_advocate.
  python mesh.py --agent bull "Reliance thesis"
  python mesh.py --agent bear "Why HDFC Bank might disappoint"
  python mesh.py --agent macro "India macro regime right now"
  python mesh.py --agent devils_advocate "Is Nifty valuation even the question?"

### /chart [ticker]
Standalone price chart only. No analysis.
  python mesh.py --chart RELIANCE.NS
  python mesh.py --chart NVDA
  python mesh.py --chart 7203.T

---

## Global Ticker Formats

| Market        | Exchange    | Format    | Examples                         |
|---------------|-------------|-----------|-----------------------------------|
| US            | NYSE/NASDAQ | TICKER    | NVDA, AAPL, MSFT                  |
| India NSE     | NSE         | TICKER.NS | RELIANCE.NS, TCS.NS, HDFCBANK.NS  |
| India BSE     | BSE         | TICKER.BO | RELIANCE.BO, TCS.BO               |
| UK            | LSE         | TICKER.L  | SHEL.L, AZN.L, HSBA.L             |
| Germany       | XETRA       | TICKER.DE | SAP.DE, BMW.DE, SIE.DE            |
| Netherlands   | AEX         | TICKER.AS | ASML.AS, PHIA.AS                  |
| France        | CAC         | TICKER.PA | MC.PA, OR.PA, BNP.PA              |
| Japan         | Tokyo       | CODE.T    | 7203.T (Toyota), 6758.T (Sony)    |
| Hong Kong     | HKEX        | CODE.HK   | 0700.HK (Tencent), 9988.HK (BABA) |
| Switzerland   | SIX         | TICKER.SW | NESN.SW, NOVN.SW                  |
| Canada        | TSX         | TICKER.TO | SHOP.TO, RY.TO                    |
| Australia     | ASX         | TICKER.AX | BHP.AX, CBA.AX                    |

---

## Notes on the analysis lenses

- **Bull**: cites every strength metric (growth, margins, ROE, FCF, low
  leverage, favorable PEG) found in the fetched fundamentals.
- **Bear**: cites every weakness metric (rich multiples vs sector band,
  high leverage, thin liquidity, high beta, weak growth, negative FCF).
- **Macro**: derives regime sensitivity from beta, dividend yield, currency
  exposure, and realized volatility of the price history.
- **Devil's Advocate**: flags framing risk -- reliance on forward-earnings
  assumptions, mega-cap reflexivity, elevated short interest, or cases
  where Bull and Bear found nothing (meaning the real debate is
  qualitative, not in the numbers).
- A deterministic synthesizer scores bull vs. bear signal counts into a
  BULLISH / NEUTRAL / BEARISH verdict with a confidence percentage.

This is not investment advice. Every cited figure should be verified
against primary filings (10-K/10-Q, BSE/NSE disclosures).
