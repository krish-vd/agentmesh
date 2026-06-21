"""
Rule-based synthesis/orchestration for AgentMesh.

Takes the four analysis_engine.py findings dicts and produces a verdict,
consensus points, and unresolved tensions -- all derived deterministically
from how many strength/weakness metrics each side cited, with no LLM call.
"""
from __future__ import annotations


def synthesize(bull: dict, bear: dict, macro: dict, devil: dict, rebuttal: dict | None = None) -> dict:
    n_bull = len(bull.get("metrics_cited", []))
    n_bear = len(bear.get("metrics_cited", []))

    # A rebuttal that goes unanswered (no countervailing metric in the data)
    # is a stronger signal than a raw metric count, so it shifts the score.
    rebuttal = rebuttal or {}
    bull_unanswered = "unchallenged" in rebuttal.get("bear_rebuts_bull", "")
    bear_unanswered = "unchallenged" in rebuttal.get("bull_rebuts_bear", "")

    score = n_bull - n_bear
    if bull_unanswered and not bear_unanswered:
        score += 1
    if bear_unanswered and not bull_unanswered:
        score -= 1

    if score >= 2:
        verdict = "BULLISH"
    elif score <= -2:
        verdict = "BEARISH"
    else:
        verdict = "NEUTRAL"

    total_signals = max(n_bull + n_bear, 1)
    confidence = min(95, 50 + int(abs(score) / total_signals * 50))

    consensus_points = []
    bull_metric_names = {m[0] for m in bull.get("metrics_cited", [])}
    bear_metric_names = {m[0] for m in bear.get("metrics_cited", [])}

    if "Revenue growth" in bull_metric_names and "Revenue growth" not in bear_metric_names:
        consensus_points.append("Revenue growth is genuinely strong -- neither side disputes this, only what it implies for the price already paid.")
    if macro.get("regime_verdict"):
        consensus_points.append(f"Macro sensitivity: {macro['regime_verdict']}.")
    if not consensus_points:
        consensus_points.append("Bull and Bear are working from the same dataset; the disagreement is about weighting, not about the facts.")

    unresolved = []
    if n_bull > 0 and n_bear > 0:
        unresolved.append({
            "title": "Valuation vs. quality",
            "bull_position": bull["findings"][0],
            "bear_position": bear["findings"][0],
            "why_unresolved": "Both claims are simultaneously true from the same data -- resolving this "
                               "requires a view on the holding period and which metric the market re-rates on first.",
        })
    if devil.get("framing_challenge"):
        unresolved.append({
            "title": "Framing challenge",
            "bull_position": "N/A",
            "bear_position": "N/A",
            "why_unresolved": devil["framing_challenge"],
        })

    investigate_next = [
        "Verify every cited figure against the most recent 10-K/10-Q or BSE/NSE filing -- this analysis uses live yfinance/OpenBB data, which can lag or restate.",
        "Compare valuation multiples against named peers directly, not just sector averages.",
        "Check the next 1-2 quarters of guidance for the specific metric (revenue growth, margin) the debate hinges on.",
    ]

    if verdict == "BULLISH":
        summary = (
            f"Bull lands {n_bull} cited strengths against Bear's {n_bear}, and Bear's rebuttal of Bull's "
            f"top claim {'lands' if not bull_unanswered else 'does not land'} -- net edge to the bull case "
            f"on the data available. This is not investment advice; verify every figure against primary sources."
        )
    elif verdict == "BEARISH":
        summary = (
            f"Bear lands {n_bear} cited weaknesses against Bull's {n_bull}, and Bull's rebuttal of Bear's "
            f"top claim {'lands' if not bear_unanswered else 'does not land'} -- net edge to the bear case "
            f"on the data available. This is not investment advice; verify every figure against primary sources."
        )
    else:
        summary = (
            f"Bull cites {n_bull} strengths, Bear cites {n_bear} weaknesses, and each side's rebuttal of the "
            f"other's top claim broadly lands -- no clear net edge from the data alone. "
            f"This is not investment advice; verify every figure against primary sources."
        )

    return {
        "verdict": verdict,
        "confidence": confidence,
        "verdict_summary": summary,
        "consensus_points": consensus_points,
        "unresolved": unresolved,
        "strongest_case": "bull" if score > 0 else "bear" if score < 0 else "neither",
        "investigate_next": investigate_next,
    }
