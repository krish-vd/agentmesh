"""
Global market data via OpenBB + yfinance provider.
Supports: US, India (NSE/BSE), UK, Europe, Japan, HK, Australia, Canada.
"""
from openbb import obb
import pandas as pd
from datetime import datetime, timedelta


EXCHANGE_LABELS = {
    ".NS": "NSE India",
    ".BO": "BSE India",
    ".L":  "London Stock Exchange",
    ".DE": "XETRA Germany",
    ".AS": "Amsterdam (AEX)",
    ".PA": "Paris (CAC)",
    ".T":  "Tokyo Stock Exchange",
    ".HK": "Hong Kong Stock Exchange",
    ".SW": "Swiss Exchange",
    ".TO": "Toronto Stock Exchange",
    ".AX": "Australian Securities Exchange",
    "":    "US (NYSE / NASDAQ)",
}


def detect_exchange(ticker: str) -> str:
    for suffix, label in EXCHANGE_LABELS.items():
        if suffix and ticker.upper().endswith(suffix.upper()):
            return label
    return EXCHANGE_LABELS[""]


def fetch_price_data(ticker: str) -> dict:
    """
    Fetches price history and snapshot data for any global ticker via OpenBB.
    """
    result = {
        "ticker":   ticker.upper(),
        "exchange": detect_exchange(ticker),
        "error":    None,
    }

    try:
        # 1-year price history
        end   = datetime.today().strftime("%Y-%m-%d")
        start = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")

        hist = obb.equity.price.historical(
            ticker, provider="yfinance",
            start_date=start, end_date=end
        ).to_dataframe()

        if hist.empty:
            result["error"] = f"No price history found for {ticker}"
            return result

        result["price"]    = round(hist["close"].iloc[-1], 2)
        result["52w_high"] = round(hist["high"].max(), 2)
        result["52w_low"]  = round(hist["low"].min(), 2)
        result["hist_df"]  = hist  # keep for chart rendering

        # 1-month return
        if len(hist) >= 21:
            result["return_1m"] = round(
                (hist["close"].iloc[-1] / hist["close"].iloc[-21] - 1) * 100, 2
            )

        # 6-month return
        if len(hist) >= 126:
            result["return_6m"] = round(
                (hist["close"].iloc[-1] / hist["close"].iloc[-126] - 1) * 100, 2
            )

    except Exception as e:
        result["error"] = f"Price history error: {e}"
        return result

    try:
        # Fundamentals via yfinance info
        import yfinance as yf
        info = yf.Ticker(ticker).info

        result.update({
            "company_name":   info.get("longName") or info.get("shortName", ticker),
            "sector":         info.get("sector"),
            "industry":       info.get("industry"),
            "market_cap":     info.get("marketCap"),
            "currency":       info.get("currency", "USD"),
            "pe_ratio":       info.get("trailingPE"),
            "forward_pe":     info.get("forwardPE"),
            "peg_ratio":      info.get("pegRatio"),
            "ev_to_ebitda":   info.get("enterpriseToEbitda"),
            "ev_to_revenue":  info.get("enterpriseToRevenue"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "price_to_book":  info.get("priceToBook"),
            "gross_margin":   info.get("grossMargins"),
            "operating_margin": info.get("operatingMargins"),
            "net_margin":     info.get("profitMargins"),
            "revenue_ttm":    info.get("totalRevenue"),
            "free_cashflow":  info.get("freeCashflow"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "roe":            info.get("returnOnEquity"),
            "roa":            info.get("returnOnAssets"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio":  info.get("currentRatio"),
            "beta":           info.get("beta"),
            # yfinance's "dividendYield" field is inconsistently scaled across
            # versions (sometimes a fraction, sometimes already a percent).
            # trailingAnnualDividendYield is reliably a fraction, so prefer it.
            "dividend_yield": info.get("trailingAnnualDividendYield"),
            "short_ratio":    info.get("shortRatio"),
            "employees":      info.get("fullTimeEmployees"),
            "country":        info.get("country"),
            "description":    (info.get("longBusinessSummary") or "")[:400],
        })

    except Exception as e:
        result["fundamentals_note"] = f"Could not fetch fundamentals: {e}"

    return result


def format_for_agents(data: dict) -> str:
    """Formats fetched data as clean context string for agent prompts."""
    if data.get("error"):
        return f"Data error for {data['ticker']}: {data['error']}"

    cur = data.get("currency", "USD")
    lines = []

    lines.append(f"LIVE MARKET DATA: {data.get('company_name', data['ticker'])} ({data['ticker']})")
    lines.append(f"Exchange: {data.get('exchange', 'Unknown')} | Currency: {cur}")
    if data.get("sector"):
        lines.append(f"Sector: {data['sector']} | Industry: {data.get('industry', 'N/A')}")
    if data.get("country"):
        lines.append(f"Country: {data['country']}")
    lines.append("")

    lines.append("PRICE:")
    lines.append(f"  Current: {cur} {data.get('price', 'N/A')}")
    lines.append(f"  52-week range: {data.get('52w_low', 'N/A')} - {data.get('52w_high', 'N/A')}")
    if "return_1m" in data:
        lines.append(f"  1-month return: {data['return_1m']:+.1f}%")
    if "return_6m" in data:
        lines.append(f"  6-month return: {data['return_6m']:+.1f}%")
    if data.get("market_cap"):
        mc = data["market_cap"]
        mc_str = f"{mc/1e12:.2f}T" if mc > 1e12 else f"{mc/1e9:.1f}B" if mc > 1e9 else f"{mc/1e6:.0f}M"
        lines.append(f"  Market cap: {cur} {mc_str}")
    lines.append("")

    lines.append("VALUATION:")
    lines.append(f"  Trailing P/E:  {data.get('pe_ratio', 'N/A')}")
    lines.append(f"  Forward P/E:   {data.get('forward_pe', 'N/A')}")
    lines.append(f"  EV/EBITDA:     {data.get('ev_to_ebitda', 'N/A')}")
    lines.append(f"  Price/Sales:   {data.get('price_to_sales', 'N/A')}")
    lines.append(f"  Price/Book:    {data.get('price_to_book', 'N/A')}")
    if data.get("peg_ratio"):
        lines.append(f"  PEG:           {data['peg_ratio']}")
    lines.append("")

    lines.append("PROFITABILITY:")
    for k, label in [
        ("gross_margin", "Gross margin"),
        ("operating_margin", "Operating margin"),
        ("net_margin", "Net margin"),
        ("roe", "ROE"),
        ("roa", "ROA"),
    ]:
        if data.get(k) is not None:
            lines.append(f"  {label}: {data[k]*100:.1f}%")
    lines.append("")

    lines.append("GROWTH (YoY):")
    if data.get("revenue_growth") is not None:
        lines.append(f"  Revenue: {data['revenue_growth']*100:.1f}%")
    if data.get("earnings_growth") is not None:
        lines.append(f"  Earnings: {data['earnings_growth']*100:.1f}%")
    lines.append("")

    lines.append("BALANCE SHEET:")
    if data.get("debt_to_equity") is not None:
        lines.append(f"  Debt/Equity:   {data['debt_to_equity']:.2f}")
    if data.get("current_ratio") is not None:
        lines.append(f"  Current ratio: {data['current_ratio']:.2f}")
    if data.get("beta") is not None:
        lines.append(f"  Beta:          {data['beta']:.2f}")
    if data.get("free_cashflow") is not None:
        fcf = data["free_cashflow"]
        lines.append(f"  Free cashflow: {cur} {fcf/1e9:.2f}B")
    lines.append("")

    if data.get("description"):
        lines.append(f"BUSINESS: {data['description']}")

    if data.get("fundamentals_note"):
        lines.append(f"\nNote: {data['fundamentals_note']}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE.NS"
    data = fetch_price_data(ticker)
    print(format_for_agents(data))
