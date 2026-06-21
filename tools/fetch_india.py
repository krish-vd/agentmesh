"""
India-specific market data via indianapi.in.
Covers: NSE/BSE fundamentals, quarterly results, analyst targets,
shareholding pattern, SEBI filings, FII/DII data.

Sign up free at: https://indianapi.in
Get your free API key from the dashboard.
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://analyst.indianapi.in"
API_KEY  = os.getenv("INDIA_API_KEY", "")


def _get(endpoint: str, params: dict = {}) -> dict | None:
    if not API_KEY:
        return None
    headers = {"X-API-Key": API_KEY}
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", headers=headers,
                         params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None


def clean_ticker(ticker: str) -> str:
    """Strip .NS or .BO suffix for indianapi.in calls."""
    return ticker.upper().replace(".NS", "").replace(".BO", "")


def fetch_india_data(ticker: str) -> str:
    """
    Fetches India-specific data for a NSE/BSE stock.
    Returns a formatted string for agent context.
    """
    symbol = clean_ticker(ticker)
    lines  = [f"INDIA MARKET DATA (indianapi.in): {symbol}"]

    if not API_KEY:
        lines.append("Note: Set INDIA_API_KEY in .env for India-specific data.")
        lines.append("Free signup at https://indianapi.in")
        return "\n".join(lines)

    # Stock overview
    stock = _get(f"/stock", {"name": symbol})
    if stock:
        lines.append(f"\nCOMPANY: {stock.get('companyName', symbol)}")
        lines.append(f"Sector:  {stock.get('sector', 'N/A')}")
        lines.append(f"Industry: {stock.get('industry', 'N/A')}")

        price_info = stock.get("currentPrice", {})
        if price_info:
            lines.append(f"\nPRICE (NSE):")
            lines.append(f"  LTP:    Rs.{price_info.get('NSE', 'N/A')}")
            lines.append(f"  BSE:    Rs.{price_info.get('BSE', 'N/A')}")

        ratios = stock.get("ratios", {})
        if ratios:
            lines.append(f"\nKEY RATIOS:")
            for k, label in [
                ("pe",    "P/E"),
                ("pb",    "P/B"),
                ("roce",  "ROCE"),
                ("roe",   "ROE"),
                ("evEbitda", "EV/EBITDA"),
                ("debtEquity", "Debt/Equity"),
                ("dividendYield", "Dividend yield"),
                ("bookValue", "Book value"),
            ]:
                val = ratios.get(k)
                if val is not None:
                    lines.append(f"  {label}: {val}")

    # Quarterly results
    fin = _get(f"/financial-data", {"stock_name": symbol})
    if fin:
        quarterly = fin.get("quarterly", [])
        if quarterly:
            lines.append(f"\nQUARTERLY RESULTS (last 4):")
            for q in quarterly[:4]:
                lines.append(
                    f"  {q.get('period','?')}: "
                    f"Revenue Rs.{q.get('revenue','?')}Cr | "
                    f"PAT Rs.{q.get('netProfit','?')}Cr | "
                    f"Margin {q.get('netProfitMargin','?')}%"
                )

        annual = fin.get("annual", [])
        if annual:
            lines.append(f"\nANNUAL FINANCIALS (last 3 years):")
            for a in annual[:3]:
                lines.append(
                    f"  FY{a.get('year','?')}: "
                    f"Revenue Rs.{a.get('revenue','?')}Cr | "
                    f"PAT Rs.{a.get('netProfit','?')}Cr"
                )

    # Shareholding pattern
    sh = _get(f"/shareholding-pattern", {"stock_name": symbol})
    if sh:
        latest = sh.get("shareholding", [{}])[0] if sh.get("shareholding") else {}
        if latest:
            lines.append(f"\nSHAREHOLDING PATTERN ({latest.get('period','latest')}):")
            lines.append(f"  Promoter:  {latest.get('promoter','N/A')}%")
            lines.append(f"  FII/FPI:   {latest.get('fii','N/A')}%")
            lines.append(f"  DII:       {latest.get('dii','N/A')}%")
            lines.append(f"  Public:    {latest.get('public','N/A')}%")
            promoter_pledge = latest.get("promoterPledge")
            if promoter_pledge:
                lines.append(f"  Promoter pledge: {promoter_pledge}%  [RISK FACTOR]")

    # Analyst consensus
    analyst = _get(f"/stock-target-price", {"stock_name": symbol})
    if analyst:
        lines.append(f"\nANALYST CONSENSUS:")
        lines.append(f"  Target price: Rs.{analyst.get('targetPrice','N/A')}")
        lines.append(f"  Rating:       {analyst.get('rating','N/A')}")
        lines.append(f"  Upside:       {analyst.get('upside','N/A')}%")
        lines.append(f"  Analysts:     {analyst.get('numberOfAnalysts','N/A')}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE.NS"
    print(fetch_india_data(ticker))
