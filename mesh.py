"""
AgentMesh V2 - Rule-based multi-lens equity analysis.

No LLM, no API key. Every finding is computed directly from live
yfinance/OpenBB data (fundamentals, price history, SEC/BSE/NSE filings)
via tools/analysis_engine.py and tools/synthesizer.py.

Usage:
  python mesh.py "question"              # full analysis, saves PDF
  python mesh.py --agent bull "question" # single lens only
  python mesh.py --chart RELIANCE.NS     # price chart only
"""
import argparse
import sys
import re
from datetime import datetime

from tools.fetch_global    import fetch_price_data, format_for_agents
from tools.fetch_india     import fetch_india_data
from tools.fetch_filings   import fetch_filings
from tools.analysis_engine import run_full_analysis
from tools.synthesizer     import synthesize

AGENTS = ["bull", "bear", "macro", "devils_advocate"]


# -- Ticker detection -----------------------------------------------------------
def extract_ticker(question: str) -> str | None:
    """
    Detect a stock ticker in the question.
    Handles: NVDA, RELIANCE.NS, TCS.BO, ASML.AS, 7203.T, 0700.HK
    """
    intl = re.findall(
        r'\b([A-Z0-9]{1,15}\.(NS|BO|L|DE|AS|PA|T|HK|SW|TO|AX|ST|MI|CO|LS))\b',
        question.upper()
    )
    if intl:
        return intl[0][0]

    us = re.findall(r'\b[A-Z]{2,5}\b', question)
    skip = {
        "I", "IS", "AT", "FOR", "IN", "ON", "THE", "A", "AN", "BUY",
        "SELL", "THIS", "ARE", "BE", "TO", "OF", "MY", "OR", "NOT",
        "IT", "IF", "VS", "AND", "BUT", "SO", "US", "UK", "EU", "AI",
        "ML", "PE", "PB", "ROE", "ROA", "IPO", "EPS", "FCF"
    }
    candidates = [t for t in us if t not in skip]
    return candidates[0] if candidates else None


def is_indian(ticker: str) -> bool:
    return ticker.upper().endswith((".NS", ".BO"))


def _exchange_label(ticker: str) -> str:
    from tools.fetch_global import EXCHANGE_LABELS
    for suffix, label in EXCHANGE_LABELS.items():
        if suffix and ticker.upper().endswith(suffix.upper()):
            return label
    return "US market"


# -- Display helpers --------------------------------------------------------------
def divider(title: str = ""):
    w = 64
    if title:
        pad = w - len(title) - 3
        print(f"\n{'=' * 2} {title} {'=' * max(pad, 2)}\n")
    else:
        print(f"\n{'=' * w}\n")


def agent_label(agent: str) -> str:
    return agent.replace("_", " ").upper()


def print_case(case: dict):
    for line in case.get("findings", []):
        print(f"  - {line}")
    if "confidence" in case:
        print(f"\n  CONFIDENCE: {case['confidence']}")
    if "regime_verdict" in case:
        print(f"\n  REGIME VERDICT: {case['regime_verdict']}")
        print(f"  TAIL RISK TO WATCH: {case['tail_risk']}")
    if "framing_challenge" in case:
        print(f"\n  FRAMING CHALLENGE: {case['framing_challenge']}")


# -- Main analysis run ----------------------------------------------------------------
def run_analysis(question: str):
    divider("AgentMesh - Full Analysis")
    print(f"Question: {question}\n")

    ticker = extract_ticker(question)
    if not ticker:
        print("No ticker detected in the question. Provide a ticker, e.g. "
              "'Should I buy NVDA?' or 'RELIANCE.NS valuation check'.")
        sys.exit(1)

    print(f"Detected ticker: {ticker} ({_exchange_label(ticker)})")
    print("Fetching market data (yfinance / OpenBB)...")
    data = fetch_price_data(ticker)
    if data.get("error"):
        print(f"Error fetching data: {data['error']}")
        sys.exit(1)

    print(format_for_agents(data))
    print()
    print(fetch_filings(ticker))

    if is_indian(ticker):
        print()
        print(fetch_india_data(ticker))

    print("\nRunning rule-based analysis across four lenses...")
    results = run_full_analysis(data, hist_df=data.get("hist_df"))

    for agent in AGENTS:
        divider(agent_label(agent))
        print_case(results[agent])

    divider("Rebuttal Round")
    rebuttal = results["rebuttal"]
    print(f"BEAR REBUTS BULL: {rebuttal['bear_rebuts_bull']}\n")
    print(f"BULL REBUTS BEAR: {rebuttal['bull_rebuts_bear']}")

    divider("Synthesis")
    verdict = synthesize(
        results["bull"], results["bear"], results["macro"], results["devils_advocate"],
        rebuttal=rebuttal,
    )
    print(f"OVERALL LEAN: {verdict['verdict']} ({verdict['confidence']}% confidence)\n")
    print(verdict["verdict_summary"])
    print("\nCONSENSUS POINTS:")
    for p in verdict["consensus_points"]:
        print(f"  - {p}")
    print("\nUNRESOLVED:")
    for u in verdict["unresolved"]:
        print(f"  - {u['title']}: {u['why_unresolved']}")
    print("\nINVESTIGATE NEXT:")
    for i in verdict["investigate_next"]:
        print(f"  - {i}")

    divider("Generating PDF Report")
    from report import generate_pdf
    pdf_path = generate_pdf(question, results, verdict, ticker, market_data=data)
    print(f"\nReport saved: {pdf_path}")
    return results, verdict, pdf_path


# -- Single agent mode ------------------------------------------------------------------
def run_single_agent(agent: str, question: str):
    divider(f"{agent_label(agent)} - Rule-based analysis")
    print(f"Question: {question}\n")

    ticker = extract_ticker(question)
    if not ticker:
        print("No ticker detected in the question.")
        sys.exit(1)

    print(f"Detected ticker: {ticker} ({_exchange_label(ticker)})")
    data = fetch_price_data(ticker)
    if data.get("error"):
        print(f"Error fetching data: {data['error']}")
        sys.exit(1)

    print(format_for_agents(data))
    print()

    results = run_full_analysis(data, hist_df=data.get("hist_df"))
    print_case(results[agent])


# -- Chart-only mode ----------------------------------------------------------------------
def run_chart_only(ticker: str):
    from tools.fetch_global import fetch_price_data
    from tools.render_chart import render_chart
    divider(f"Chart - {ticker}")
    data = fetch_price_data(ticker)
    if data.get("hist_df") is not None:
        path = render_chart(ticker, data["hist_df"],
                            f"outputs/chart_{ticker.replace('.','_')}.png")
        print(f"Chart saved: {path}")
    else:
        print(f"Error: {data.get('error', 'no data')}")


# -- Entry point ----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="AgentMesh V2 - Rule-based multi-lens equity analysis (no LLM)"
    )
    parser.add_argument("question", nargs="*", help="Investment question")
    parser.add_argument("--agent",  type=str, help="Single lens only: bull, bear, macro, devils_advocate")
    parser.add_argument("--chart",  type=str, help="Ticker for chart only")
    args = parser.parse_args()

    question = " ".join(args.question).strip()

    if args.chart:
        run_chart_only(args.chart)

    elif args.agent:
        if not question:
            print("Provide a question after --agent [name]")
            sys.exit(1)
        if args.agent not in AGENTS:
            print(f"Unknown agent. Choose from: {', '.join(AGENTS)}")
            sys.exit(1)
        run_single_agent(args.agent, question)

    else:
        if not question:
            question = "Should I buy NVDA at current valuation?"
        run_analysis(question)


if __name__ == "__main__":
    main()
