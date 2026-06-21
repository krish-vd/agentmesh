"""
Rule-based analysis engine for AgentMesh.

No LLM calls anywhere in this module. Every agent's case is built from
real numbers already fetched by fetch_global.py / fetch_india.py /
fetch_filings.py (yfinance + OpenBB). Each function takes the same
market data dict and returns a structured finding -- the equivalent of
what the rdcf engine does for valuation, generalized across four lenses.
"""
from __future__ import annotations
import statistics


def _pct(x):
    return f"{x*100:.1f}%" if isinstance(x, (int, float)) else "N/A"


def _num(x, decimals=2):
    return f"{x:.{decimals}f}" if isinstance(x, (int, float)) else "N/A"


# -- Sector-relative valuation bands (rough, public-market heuristics) ---------
# Used only to give Bull/Bear something concrete to anchor "cheap" / "expensive"
# claims to, since we have no live peer-comparison feed wired in yet.
SECTOR_PE_BANDS = {
    "Technology":             (18, 35),
    "Financial Services":     (8,  16),
    "Healthcare":             (15, 28),
    "Consumer Cyclical":      (12, 25),
    "Consumer Defensive":     (15, 24),
    "Industrials":            (12, 22),
    "Energy":                 (8,  15),
    "Utilities":              (12, 20),
    "Communication Services": (12, 24),
    "Basic Materials":        (8,  18),
    "Real Estate":            (10, 20),
}
DEFAULT_PE_BAND = (12, 25)


def _pe_band(sector):
    return SECTOR_PE_BANDS.get(sector, DEFAULT_PE_BAND)


# -- BULL: strongest case FOR, from real strength signals ----------------------
def bull_case(data: dict) -> dict:
    findings = []
    strengths = []

    rev_g  = data.get("revenue_growth")
    earn_g = data.get("earnings_growth")
    if rev_g is not None and rev_g > 0.10:
        findings.append(f"Revenue growth of {_pct(rev_g)} YoY signals real demand expansion, not just pricing.")
        strengths.append(("Revenue growth", _pct(rev_g)))
    if earn_g is not None and earn_g > 0.10:
        findings.append(f"Earnings growth of {_pct(earn_g)} YoY outpaces typical market growth (~8-10%).")
        strengths.append(("Earnings growth", _pct(earn_g)))

    gm = data.get("gross_margin")
    om = data.get("operating_margin")
    nm = data.get("net_margin")
    if gm is not None and gm > 0.40:
        findings.append(f"Gross margin of {_pct(gm)} suggests pricing power or a durable cost advantage.")
        strengths.append(("Gross margin", _pct(gm)))
    if om is not None and om > 0.20:
        findings.append(f"Operating margin of {_pct(om)} indicates efficient conversion of revenue to operating profit.")
        strengths.append(("Operating margin", _pct(om)))

    roe = data.get("roe")
    if roe is not None and roe > 0.15:
        findings.append(f"ROE of {_pct(roe)} is well above the long-run market average (~10-12%), pointing to efficient capital use.")
        strengths.append(("ROE", _pct(roe)))

    fcf = data.get("free_cashflow")
    mc  = data.get("market_cap")
    if fcf is not None and fcf > 0:
        fcf_yield = fcf / mc if mc else None
        line = f"Positive free cash flow of {data.get('currency','USD')} {fcf/1e9:.2f}B"
        if fcf_yield is not None:
            line += f" ({_pct(fcf_yield)} FCF yield on market cap)"
        findings.append(line + " funds growth without dilution or added leverage.")
        strengths.append(("FCF", f"{data.get('currency','USD')} {fcf/1e9:.2f}B"))

    de = data.get("debt_to_equity")
    if de is not None and de < 50:
        findings.append(f"Debt/Equity of {_num(de)} is conservative, leaving balance-sheet room to invest through a downturn.")
        strengths.append(("Debt/Equity", _num(de)))

    pe, fwd_pe = data.get("pe_ratio"), data.get("forward_pe")
    if pe and fwd_pe and fwd_pe < pe:
        findings.append(f"Forward P/E ({_num(fwd_pe)}) sits below trailing P/E ({_num(pe)}), implying the market expects earnings to grow into the multiple.")

    peg = data.get("peg_ratio")
    if peg is not None and peg < 1.5:
        findings.append(f"PEG ratio of {_num(peg)} suggests the stock is not overpaying for its growth rate (PEG < 1.5 is reasonable, < 1.0 is cheap).")
        strengths.append(("PEG", _num(peg)))

    ret_6m = data.get("return_6m")
    if ret_6m is not None and ret_6m > 0:
        findings.append(f"6-month return of {ret_6m:+.1f}% shows the market is already rewarding the thesis -- momentum is a tailwind, not a headwind, here.")

    if not findings:
        findings.append("No standout strength signals were found in the available fundamentals data -- "
                         "the bull case here would need to rest on qualitative factors (management quality, "
                         "TAM expansion, optionality) not captured by the metrics fetched.")

    confidence = "HIGH" if len(strengths) >= 4 else "MEDIUM" if len(strengths) >= 2 else "LOW"

    if strengths:
        top_label, top_value = strengths[0]
        strongest_claim = f"{top_label}: {top_value} -- the single strongest data point in the bull case."
    else:
        strongest_claim = "No quantitative edge found; thesis would rest on qualitative factors."

    return {
        "agent": "bull",
        "findings": findings,
        "strongest_claim": strongest_claim,
        "confidence": confidence,
        "metrics_cited": strengths,
    }


# -- BEAR: strongest case AGAINST, from real weakness signals ------------------
def bear_case(data: dict) -> dict:
    findings = []
    weaknesses = []

    sector = data.get("sector")
    pe, fwd_pe = data.get("pe_ratio"), data.get("forward_pe")
    lo, hi = _pe_band(sector)
    if pe is not None and pe > hi:
        findings.append(
            f"Trailing P/E of {_num(pe)} sits above the typical {lo}-{hi}x band for {sector or 'this sector'}, "
            f"meaning the market is pricing in growth that has not yet shown up in earnings -- "
            f"this is a forecast, not a fact."
        )
        weaknesses.append(("P/E vs sector band", f"{_num(pe)} vs {lo}-{hi}x"))

    ev_ebitda = data.get("ev_to_ebitda")
    if ev_ebitda is not None and ev_ebitda > 20:
        findings.append(f"EV/EBITDA of {_num(ev_ebitda)} is rich by historical market standards (long-run median is roughly 11-13x); "
                         f"any multiple compression hits the share price directly, independent of operating performance.")
        weaknesses.append(("EV/EBITDA", _num(ev_ebitda)))

    de = data.get("debt_to_equity")
    if de is not None and de > 100:
        findings.append(f"Debt/Equity of {_num(de)} is elevated -- rising rates or a credit-spread widening event "
                         f"would compress equity value disproportionately versus a less levered peer.")
        weaknesses.append(("Debt/Equity", _num(de)))

    cr = data.get("current_ratio")
    if cr is not None and cr < 1.0:
        findings.append(f"Current ratio of {_num(cr)} is below 1.0, meaning short-term liabilities exceed short-term assets -- "
                         f"a liquidity squeeze risk if financing conditions tighten.")
        weaknesses.append(("Current ratio", _num(cr)))

    beta = data.get("beta")
    if beta is not None and beta > 1.5:
        findings.append(f"Beta of {_num(beta)} means this stock amplifies market drawdowns -- "
                         f"in a 20% market correction, this name has historically moved roughly {beta*20:.0f}%.")
        weaknesses.append(("Beta", _num(beta)))

    rev_g = data.get("revenue_growth")
    om = data.get("operating_margin")
    if rev_g is not None and rev_g < 0.05:
        findings.append(f"Revenue growth of only {_pct(rev_g)} YoY is below typical market growth -- "
                         f"the bull case for a premium multiple requires accelerating growth that isn't showing in the trailing numbers.")
        weaknesses.append(("Revenue growth", _pct(rev_g)))

    fcf = data.get("free_cashflow")
    if fcf is not None and fcf < 0:
        findings.append("Negative free cash flow means the business is currently consuming cash rather than generating it -- "
                         "the thesis depends on a future inflection that has not yet arrived.")
        weaknesses.append(("FCF", "negative"))

    ret_1m = data.get("return_1m")
    if ret_1m is not None and ret_1m < -5:
        findings.append(f"1-month return of {ret_1m:+.1f}% shows the market already pulling back -- "
                         f"worth asking whether this is repricing a real deterioration or just noise.")

    if not findings:
        findings.append("No standout weakness signals were found in the available fundamentals data. "
                         "The strongest bear case here is simply that current pricing already reflects "
                         "most of the good news, leaving asymmetric downside if execution slips even slightly.")

    confidence = "HIGH" if len(weaknesses) >= 3 else "MEDIUM" if len(weaknesses) >= 1 else "LOW"

    if weaknesses:
        top_label, top_value = weaknesses[0]
        strongest_claim = f"{top_label}: {top_value} -- the single biggest red flag in the data."
    else:
        strongest_claim = "No quantitative red flag found; risk is that the good news is already priced in."

    return {
        "agent": "bear",
        "findings": findings,
        "strongest_claim": strongest_claim,
        "confidence": confidence,
        "metrics_cited": weaknesses,
    }


# -- MACRO: regime context derived from the same data, no separate feed yet ----
def macro_case(data: dict, hist_df=None) -> dict:
    findings = []

    beta = data.get("beta")
    if beta is not None:
        if beta > 1.3:
            findings.append(f"Beta of {_num(beta)} means this name is rate- and risk-sentiment-sensitive -- "
                             f"it will move more than the broad market in either direction as macro conditions shift.")
            regime_impact = "HEADWIND in a risk-off regime, TAILWIND in risk-on"
        elif beta < 0.7:
            findings.append(f"Beta of {_num(beta)} suggests defensive characteristics -- "
                             f"this name should hold up better than the market in a broad selloff, but also lag in a rally.")
            regime_impact = "NEUTRAL to TAILWIND in risk-off, lags in risk-on"
        else:
            regime_impact = "NEUTRAL"
    else:
        regime_impact = "NEUTRAL"

    div_y = data.get("dividend_yield")
    if div_y is not None and div_y > 0.03:
        findings.append(f"Dividend yield of {_pct(div_y)} makes this name relatively more attractive "
                         f"if the rate cycle turns toward cuts and investors rotate toward income.")

    country = data.get("country")
    currency = data.get("currency")
    if country and currency and currency != "USD":
        findings.append(f"This is a {country}-domiciled, {currency}-denominated security -- "
                         f"USD-based investors carry currency translation risk on top of the equity risk, "
                         f"and FX moves can swing reported USD returns independent of the underlying business.")

    if hist_df is not None and len(hist_df) >= 50:
        try:
            recent_vol = hist_df["close"].pct_change().tail(30).std() * (252 ** 0.5)
            findings.append(f"Realized 30-day annualized volatility is approximately {recent_vol*100:.0f}% -- "
                             f"{'elevated' if recent_vol > 0.40 else 'moderate' if recent_vol > 0.25 else 'subdued'} "
                             f"relative to typical single-stock volatility (25-40%).")
        except Exception:
            pass

    if not findings:
        findings.append("No strong macro-sensitivity signal in the available data. "
                         "Treat this name as roughly market-correlated until proven otherwise.")

    return {
        "agent": "macro",
        "findings": findings,
        "regime_verdict": regime_impact,
        "tail_risk": (
            f"Currency translation risk ({data.get('currency')} -> USD)"
            if currency and currency != "USD" else
            "Beta-driven drawdown risk in a broad market correction"
        ),
    }


# -- DEVIL'S ADVOCATE: framing challenge + concrete second-order flags ---------
def devils_advocate_case(data: dict, bull: dict, bear: dict) -> dict:
    findings = []
    tags = []

    pe, fwd_pe = data.get("pe_ratio"), data.get("forward_pe")
    if pe and fwd_pe:
        implied_growth_reliance = (pe - fwd_pe) / pe if pe else None
        if implied_growth_reliance and implied_growth_reliance > 0.15:
            findings.append(
                f"The valuation case depends heavily on forward earnings growth materializing -- "
                f"forward P/E ({_num(fwd_pe)}) is {implied_growth_reliance*100:.0f}% below trailing P/E ({_num(pe)}). "
                f"If growth disappoints even modestly, the multiple re-rates on trailing numbers, not forward ones."
            )
            tags.append("Thesis is forward-earnings-dependent")

    n_bull = len(bull.get("metrics_cited", []))
    n_bear = len(bear.get("metrics_cited", []))
    if n_bull == 0 and n_bear == 0:
        findings.append("Neither Bull nor Bear found standout signals in the fundamentals data -- "
                         "this suggests the real debate here is not about this company's numbers at all, "
                         "but about a qualitative or narrative factor the data can't capture.")
        tags.append("Real debate is qualitative, not quantitative")
    elif n_bull > 0 and n_bear > 0:
        findings.append(f"Bull cites {n_bull} strength metrics, Bear cites {n_bear} weakness metrics from the same "
                         f"dataset -- both are correct simultaneously. The real question is which set of metrics "
                         f"the market will weight more heavily over the relevant holding period, not which side is 'right.'")
        tags.append(f"Bull ({n_bull} signals) vs Bear ({n_bear} signals) -- a weighting question, not a facts dispute")

    mc = data.get("market_cap")
    if mc is not None and mc > 5e11:
        findings.append("This is a mega-cap name -- at this size, index-fund flows and passive ownership concentration "
                         "can move the price independent of company-specific fundamentals (reflexivity risk).")
        tags.append("Mega-cap reflexivity risk (passive flows can move price independent of fundamentals)")

    short_ratio = data.get("short_ratio")
    if short_ratio is not None and short_ratio > 5:
        findings.append(f"Short ratio (days to cover) of {_num(short_ratio)} is elevated -- "
                         f"meaningful short interest exists, and a squeeze or a confirmation of the bear case "
                         f"could both move the price sharply.")
        tags.append(f"Elevated short interest ({_num(short_ratio)} days to cover)")

    if not findings:
        findings.append("The available data doesn't surface an obvious framing problem -- "
                         "the bull/bear debate here appears to be a genuine disagreement about the same numbers, "
                         "not a case of debating the wrong question.")
        tags.append("No framing issue detected -- this is a genuine numbers disagreement")

    return {
        "agent": "devils_advocate",
        "findings": findings,
        "framing_challenge": tags[0] if tags else "N/A",
        "all_tags": tags,
    }


# -- REBUTTAL ROUND: Bull and Bear each directly counter the other's top claim -
# This is what makes it a debate rather than two parallel monologues -- each
# side has to engage with the other's strongest cited metric, not just list
# its own. Still 100% rule-based: the "rebuttal" is a deterministic lookup
# of whether a countervailing metric exists in the same dataset.
REBUTTAL_COUNTERS = {
    "Revenue growth":     ("ev_to_ebitda", "EV/EBITDA", lambda v: v > 20,
                            "but that growth is already richly priced in at {val}x EV/EBITDA"),
    "Earnings growth":    ("pe_ratio", "trailing P/E", lambda v: v > 30,
                            "but a {val}x trailing P/E means most of that growth is already in the price"),
    "Gross margin":       ("debt_to_equity", "Debt/Equity", lambda v: v > 100,
                            "but {val}x leverage means margin gains could reverse fast if rates rise"),
    "Operating margin":   ("beta", "beta", lambda v: v > 1.5,
                            "but a beta of {val} means those margins get re-rated hard in a risk-off move"),
    "ROE":                ("debt_to_equity", "Debt/Equity", lambda v: v > 100,
                            "but ROE this high is partly a leverage effect at {val}x Debt/Equity, not pure capital efficiency"),
    "FCF":                ("ev_to_ebitda", "EV/EBITDA", lambda v: v > 20,
                            "but the cash flow is already capitalized into a rich {val}x EV/EBITDA multiple"),
    "Debt/Equity":        ("revenue_growth", "revenue growth", lambda v: v < 0.05,
                            "but a clean balance sheet means little if growth ({val}) can't justify the multiple"),
    "PEG":                ("current_ratio", "current ratio", lambda v: v < 1.0,
                            "but a low PEG doesn't offset a current ratio of {val}, a near-term liquidity flag"),
}


def rebuttal_round(bull: dict, bear: dict, data: dict) -> dict:
    """Has Bear counter Bull's strongest metric, and Bull counter Bear's, using
    whichever real countervailing figure exists in the same dataset."""
    bull_top = bull["metrics_cited"][0] if bull.get("metrics_cited") else None
    bear_top = bear["metrics_cited"][0] if bear.get("metrics_cited") else None

    def counter_for(top_metric, default_text):
        if not top_metric:
            return default_text
        label, value = top_metric
        rule = REBUTTAL_COUNTERS.get(label)
        if not rule:
            return default_text
        field, counter_label, predicate, template = rule
        raw = data.get(field)
        if raw is None or not predicate(raw):
            return (f"No countervailing weakness found for \"{label}: {value}\" in the available data -- "
                     f"this point stands unchallenged this round.")
        shown = _pct(raw) if field in ("revenue_growth", "earnings_growth") else _num(raw)
        return f"On \"{label}: {value}\" -- " + template.format(val=shown) + "."

    bear_rebuts_bull = counter_for(
        bull_top, "Bull's case has no single standout metric to target directly."
    )
    bull_rebuts_bear = counter_for(
        bear_top, "Bear's case has no single standout metric to target directly."
    )

    return {
        "bear_rebuts_bull": bear_rebuts_bull,
        "bull_rebuts_bear": bull_rebuts_bear,
        "bull_top_metric": bull_top,
        "bear_top_metric": bear_top,
    }


def run_full_analysis(data: dict, hist_df=None) -> dict:
    """Runs all four lenses against one data dict, then a rebuttal round
    between Bull and Bear. No LLM calls."""
    bull     = bull_case(data)
    bear     = bear_case(data)
    macro    = macro_case(data, hist_df=hist_df)
    devil    = devils_advocate_case(data, bull, bear)
    rebuttal = rebuttal_round(bull, bear, data)
    return {
        "bull": bull, "bear": bear, "macro": macro, "devils_advocate": devil,
        "rebuttal": rebuttal,
    }
