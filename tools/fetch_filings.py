"""
Regulatory filings fetcher.
- US stocks: SEC EDGAR (10-K, 10-Q)
- Indian stocks: BSE/NSE filing links + indianapi.in annual reports
"""
import requests


HEADERS = {"User-Agent": "AgentMesh research@agentmesh.ai"}


def is_indian(ticker: str) -> bool:
    return ticker.upper().endswith(".NS") or ticker.upper().endswith(".BO")


def fetch_sec_filing(ticker: str) -> str:
    """Fetch most recent 10-K metadata from SEC EDGAR."""
    try:
        tickers_url = "https://www.sec.gov/files/company_tickers.json"
        r = requests.get(tickers_url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return f"SEC EDGAR unavailable (status {r.status_code})."

        cik = None
        for _, val in r.json().items():
            if val.get("ticker", "").upper() == ticker.upper():
                cik = str(val["cik_str"]).zfill(10)
                break

        if not cik:
            return f"No CIK found for {ticker} on SEC EDGAR."

        sub_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        r2 = requests.get(sub_url, headers=HEADERS, timeout=10)
        if r2.status_code != 200:
            return f"Could not fetch SEC submissions for {ticker}."

        data    = r2.json()
        name    = data.get("name", ticker)
        filings = data.get("filings", {}).get("recent", {})
        forms   = filings.get("form", [])
        dates   = filings.get("filingDate", [])
        acc_nos = filings.get("accessionNumber", [])

        results = []
        for i, form in enumerate(forms):
            if form in ("10-K", "10-Q") and len(results) < 2:
                acc_clean = acc_nos[i].replace("-", "")
                url = (f"https://www.sec.gov/Archives/edgar/data/"
                       f"{int(cik)}/{acc_clean}/")
                results.append(f"{form} filed {dates[i]}: {url}")

        if not results:
            return f"No 10-K/10-Q found in recent filings for {ticker}."

        return (
            f"SEC EDGAR FILINGS: {name} ({ticker.upper()})\n"
            f"CIK: {cik}\n" +
            "\n".join(results) +
            "\n\nAll cited figures must be traceable to these filings."
        )

    except Exception as e:
        return f"SEC filing error for {ticker}: {e}"


def fetch_india_filings(ticker: str) -> str:
    """Return BSE/NSE filing links for an Indian stock."""
    symbol = ticker.upper().replace(".NS", "").replace(".BO", "")
    return (
        f"INDIAN REGULATORY FILINGS: {symbol}\n"
        f"BSE filings: https://www.bseindia.com/stock-share-price/{symbol}/\n"
        f"NSE filings: https://www.nseindia.com/get-quotes/equity?symbol={symbol}\n"
        f"Annual reports & DRHP: https://www.sebi.gov.in\n"
        f"Screener fundamentals: https://www.screener.in/company/{symbol}/\n\n"
        f"Note: Indian companies report under IndAS (converged with IFRS).\n"
        f"All cited figures should be verified against BSE/NSE filing disclosures."
    )


def fetch_filings(ticker: str) -> str:
    if is_indian(ticker):
        return fetch_india_filings(ticker)
    return fetch_sec_filing(ticker)


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    print(fetch_filings(ticker))
