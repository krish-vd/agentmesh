"""
Generates an institutional equity-research-style PDF from AgentMesh's
rule-based output (tools/analysis_engine.py + tools/synthesizer.py).
No LLM call anywhere in this module.

Design language: white page, navy/charcoal palette, serif headline,
small-caps sans section labels, dense data-table layout -- closer to a
sell-side research note than a consumer app screen.
"""
import os
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# -- Fonts ----------------------------------------------------------------------
# Font candidates in priority order: macOS system serif/sans first (Georgia /
# Arial -- both look far better than ReportLab's built-in Times/Helvetica),
# then DejaVu on Linux, then give up and use Helvetica everywhere.
_FONT_DIRS = [
    "/System/Library/Fonts/Supplemental/",
    "/usr/share/fonts/truetype/dejavu/",
    "/opt/homebrew/share/fonts/",
    "/usr/local/share/fonts/",
    "/Library/Fonts/",
    str(Path.home() / "Library/Fonts/"),
]

_FONT_CANDIDATES = {
    "sans":      ["Arial.ttf", "DejaVuSans.ttf"],
    "sans_b":    ["Arial Bold.ttf", "DejaVuSans-Bold.ttf"],
    "serif":     ["Georgia.ttf", "Charter.ttc", "DejaVuSerif.ttf"],
    "serif_b":   ["Georgia Bold.ttf", "DejaVuSerif-Bold.ttf"],
    "serif_i":   ["Georgia Italic.ttf", "DejaVuSerif-Italic.ttf"],
}


def _find_font(filenames) -> str | None:
    for d in _FONT_DIRS:
        for filename in filenames:
            candidate = os.path.join(d, filename)
            if os.path.isfile(candidate) and not candidate.endswith(".ttc"):
                return candidate
    return None


try:
    _sans    = _find_font(_FONT_CANDIDATES["sans"])
    _sans_b  = _find_font(_FONT_CANDIDATES["sans_b"])
    _serif   = _find_font(_FONT_CANDIDATES["serif"])
    _serif_b = _find_font(_FONT_CANDIDATES["serif_b"])
    _serif_i = _find_font(_FONT_CANDIDATES["serif_i"])

    if not all([_sans, _sans_b, _serif, _serif_b, _serif_i]):
        raise FileNotFoundError("No usable serif/sans font set found on this system")

    pdfmetrics.registerFont(TTFont("Sans",       _sans))
    pdfmetrics.registerFont(TTFont("Sans-Bold",  _sans_b))
    pdfmetrics.registerFont(TTFont("Serif",      _serif))
    pdfmetrics.registerFont(TTFont("Serif-Bold", _serif_b))
    pdfmetrics.registerFont(TTFont("Serif-Ital", _serif_i))
    SANS, SANS_B, SERIF, SERIF_B, SERIF_I = (
        "Sans", "Sans-Bold", "Serif", "Serif-Bold", "Serif-Ital"
    )
except Exception:
    SANS = SANS_B = "Helvetica"
    SERIF, SERIF_B, SERIF_I = "Times-Roman", "Times-Bold", "Times-Italic"

# -- Palette: institutional research-note (navy / charcoal / off-white) --------
C_BG        = colors.white
C_PANEL     = colors.HexColor("#F7F8FA")
C_BORDER    = colors.HexColor("#D7DBE2")
C_RULE      = colors.HexColor("#1B2A4A")   # navy hairline under header
C_TEXT      = colors.HexColor("#16181D")
C_MUTED     = colors.HexColor("#6B7280")
C_SUBTLE    = colors.HexColor("#9CA3AF")

C_NAVY      = colors.HexColor("#1B2A4A")
C_NAVY_BG   = colors.HexColor("#EEF1F6")
C_GOLD      = colors.HexColor("#9C7A1E")

C_BULL_TXT  = colors.HexColor("#0F7A4D")
C_BULL_BG   = colors.HexColor("#E7F6EE")
C_BEAR_TXT  = colors.HexColor("#B3261E")
C_BEAR_BG   = colors.HexColor("#FBEAEA")
C_MACRO_TXT = colors.HexColor("#5A4515")
C_MACRO_BG  = colors.HexColor("#F7F1E3")
C_DEVIL_TXT = colors.HexColor("#33363D")
C_DEVIL_BG  = colors.HexColor("#EDEEF1")

C_UNRES_BG  = colors.HexColor("#FBEAEA")
C_UNRES_BOR = colors.HexColor("#E2A19C")
C_UNRES_TXT = colors.HexColor("#8C1D14")

C_CON_BG    = colors.HexColor("#E7F6EE")
C_CON_BOR   = colors.HexColor("#7FCBA0")
C_CON_TXT   = colors.HexColor("#0F7A4D")

C_REBUT_BG  = colors.HexColor("#F7F8FA")
C_REBUT_BOR = colors.HexColor("#C3C9D4")

AGENT_COLORS = {
    "bull":            (C_BULL_BG,  C_BULL_TXT,  "Bull case"),
    "bear":            (C_BEAR_BG,  C_BEAR_TXT,  "Bear case"),
    "macro":           (C_MACRO_BG, C_MACRO_TXT, "Macro lens"),
    "devils_advocate": (C_DEVIL_BG, C_DEVIL_TXT, "Devil's advocate"),
}

VERDICT_COLORS = {
    "BULLISH": colors.HexColor("#0F7A4D"),
    "NEUTRAL": colors.HexColor("#9C7A1E"),
    "BEARISH": colors.HexColor("#B3261E"),
}


# -- Paragraph styles ----------------------------------------------------------------
def make_styles():
    return {
        "label": ParagraphStyle(
            "label", fontName=SANS, fontSize=7.5, textColor=C_MUTED,
            leading=11, spaceAfter=2, tracking=0.6
        ),
        "metric_val": ParagraphStyle(
            "metric_val", fontName=SERIF_B, fontSize=21, textColor=C_TEXT,
            leading=25, spaceAfter=2
        ),
        "metric_sub": ParagraphStyle(
            "metric_sub", fontName=SANS, fontSize=8.5, textColor=C_MUTED,
            leading=11
        ),
        "agent_body": ParagraphStyle(
            "agent_body", fontName=SERIF, fontSize=10, textColor=C_TEXT,
            leading=15, spaceAfter=0
        ),
        "agent_claim": ParagraphStyle(
            "agent_claim", fontName=SANS, fontSize=8, textColor=C_MUTED,
            leading=11
        ),
        "claim_val": ParagraphStyle(
            "claim_val", fontName=SANS_B, fontSize=9, textColor=C_TEXT,
            leading=13
        ),
        "rebuttal_body": ParagraphStyle(
            "rebuttal_body", fontName=SANS, fontSize=9, textColor=C_TEXT,
            leading=13.5
        ),
        "unres_title": ParagraphStyle(
            "unres_title", fontName=SANS_B, fontSize=8.5, textColor=C_UNRES_TXT,
            leading=12, spaceAfter=3
        ),
        "unres_body": ParagraphStyle(
            "unres_body", fontName=SANS, fontSize=9, textColor=C_UNRES_TXT,
            leading=13
        ),
        "con_body": ParagraphStyle(
            "con_body", fontName=SANS, fontSize=9, textColor=C_CON_TXT,
            leading=13
        ),
        "section_label": ParagraphStyle(
            "section_label", fontName=SANS_B, fontSize=8,
            textColor=C_NAVY, leading=12,
            spaceAfter=6, spaceBefore=11
        ),
        "footer": ParagraphStyle(
            "footer", fontName=SANS, fontSize=7.5, textColor=C_MUTED, leading=11
        ),
        "title": ParagraphStyle(
            "title", fontName=SERIF_B, fontSize=17, textColor=C_TEXT,
            leading=21, spaceAfter=3
        ),
        "kicker": ParagraphStyle(
            "kicker", fontName=SANS_B, fontSize=8, textColor=C_NAVY,
            leading=11, spaceAfter=4
        ),
        "header_brand": ParagraphStyle(
            "header_brand", fontName=SANS_B, fontSize=9, textColor=C_NAVY,
            leading=12, spaceAfter=2
        ),
        "data_label": ParagraphStyle(
            "data_label", fontName=SANS, fontSize=7.5, textColor=C_MUTED,
            leading=10
        ),
        "data_val": ParagraphStyle(
            "data_val", fontName=SANS_B, fontSize=9.5, textColor=C_TEXT,
            leading=12
        ),
    }


# -- Custom Flowables ----------------------------------------------------------------
class ColoredBox(Flowable):
    """A padded panel with background color and optional border accent."""
    def __init__(self, content_items, bg, border_color=None,
                 padding=(10, 12), radius=3):
        super().__init__()
        self.content = content_items
        self.bg = bg
        self.border_color = border_color
        self.pad_v, self.pad_h = padding
        self.radius = radius
        self._width = None
        self._height = None

    def wrap(self, aW, aH):
        self._width = aW
        inner_w = aW - 2 * self.pad_h
        h = self.pad_v
        from reportlab.platypus import Paragraph as P
        for text, style in self.content:
            p = P(text, style)
            _, ph = p.wrap(inner_w, 9999)
            h += ph + 4
        h += self.pad_v
        self._height = max(h, 34)
        return aW, self._height

    def draw(self):
        c = self.canv
        w, h = self._width, self._height
        c.setFillColor(self.bg)
        c.roundRect(0, 0, w, h, self.radius, fill=1, stroke=0)
        if self.border_color:
            c.setStrokeColor(self.border_color)
            c.setLineWidth(0.6)
            c.roundRect(0, 0, w, h, self.radius, fill=0, stroke=1)
        from reportlab.platypus import Paragraph as P
        inner_w = w - 2 * self.pad_h
        y = h - self.pad_v
        for text, style in self.content:
            p = P(text, style)
            pw, ph = p.wrap(inner_w, 9999)
            y -= ph
            p.drawOn(c, self.pad_h, y)
            y -= 4
        self._height = h


class AgentCard(Flowable):
    """Research-note style lens card: left rule accent, small-caps label, body, claim footer."""
    def __init__(self, agent: str, body: str, claim: str,
                 claim_label: str, confidence: str, styles: dict):
        super().__init__()
        self.agent      = agent
        self.body       = body
        self.claim      = claim
        self.c_label    = claim_label
        self.confidence = confidence
        self.styles     = styles
        self._w = self._h = None

    def wrap(self, aW, aH):
        self._w = aW
        pad = 11
        inner = aW - 2 * pad - 4  # 4pt for the left accent rule

        from reportlab.platypus import Paragraph as P
        _, bh = P(self.body, self.styles["agent_body"]).wrap(inner, 9999)
        _, lh = P(self.c_label, self.styles["agent_claim"]).wrap(inner, 9999)
        _, vh = P(self.claim, self.styles["claim_val"]).wrap(inner, 9999)

        self._h = pad + 16 + 7 + bh + 7 + 1 + 6 + lh + 2 + vh + pad
        return aW, self._h

    def draw(self):
        c  = self.canv
        w, h = self._w, self._h
        bg, accent_color, label = AGENT_COLORS.get(
            self.agent, (C_DEVIL_BG, C_DEVIL_TXT, self.agent.title())
        )
        styles = self.styles
        pad = 11

        # card background + thin border, sharp corners (research-note, not app-card)
        c.setFillColor(C_BG)
        c.setStrokeColor(C_BORDER)
        c.setLineWidth(0.6)
        c.rect(0, 0, w, h, fill=1, stroke=1)

        # left accent rule in the lens color
        c.setFillColor(accent_color)
        c.rect(0, 0, 3, h, fill=1, stroke=0)

        from reportlab.platypus import Paragraph as P
        left = pad + 4
        inner = w - left - pad

        y = h - pad

        # Small-caps style label (no badge pill -- text + rule, research-note style)
        c.setFillColor(accent_color)
        c.setFont(SANS_B, 8)
        c.drawString(left, y - 8, label.upper())

        conf_text = self.confidence
        conf_color = (
            C_BULL_TXT if "HIGH" in conf_text.upper()
            else colors.HexColor("#9C7A1E") if "MED" in conf_text.upper()
            else C_BEAR_TXT
        )
        c.setFillColor(conf_color)
        c.setFont(SANS_B, 7.5)
        c.drawRightString(w - pad, y - 8, conf_text.upper() + " CONFIDENCE")

        y -= 16

        c.setStrokeColor(C_BORDER)
        c.setLineWidth(0.4)
        c.line(left, y, w - pad, y)
        y -= 7

        p_body = P(self.body, styles["agent_body"])
        pw, ph = p_body.wrap(inner, 9999)
        y -= ph
        p_body.drawOn(c, left, y)
        y -= 7

        c.setStrokeColor(C_BORDER)
        c.setLineWidth(0.4)
        c.line(left, y, w - pad, y)
        y -= 6

        p_cl = P(self.c_label, styles["agent_claim"])
        _, clh = p_cl.wrap(inner, 9999)
        y -= clh
        p_cl.drawOn(c, left, y)
        y -= 2

        p_cv = P(self.claim, styles["claim_val"])
        _, cvh = p_cv.wrap(inner, 9999)
        y -= cvh
        p_cv.drawOn(c, left, y)


# -- Page template ----------------------------------------------------------------------
def _bg_canvas(c, doc):
    """White page, thin navy rule under header on page 1, footer on every page."""
    W, H = A4
    c.saveState()
    c.setFillColor(C_BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setStrokeColor(C_BORDER)
    c.setLineWidth(0.5)
    c.line(20 * mm, 18 * mm, W - 20 * mm, 18 * mm)
    c.setFillColor(C_MUTED)
    c.setFont(SANS, 7.2)
    c.drawString(
        20 * mm, 13 * mm,
        "Generated from live market data. Verify every figure against primary sources. Not investment advice."
    )
    c.drawRightString(
        W - 20 * mm, 13 * mm,
        f"AgentMesh  ·  Page {doc.page}"
    )
    c.restoreState()


# -- PDF builder ----------------------------------------------------------------------------
CLAIM_LABELS = {
    "bull": "Strongest data point",
    "bear": "Biggest red flag",
    "macro": "Regime verdict",
    "devils_advocate": "Framing risk",
}


def _agent_card_fields(agent: str, case: dict) -> tuple[str, str, str]:
    """Returns (body, claim, confidence) for an AgentCard from a rule-based case dict."""
    findings = case.get("findings", [])
    body = " ".join(findings[:2]) if findings else "No findings."

    if agent == "macro":
        claim = case.get("regime_verdict", "N/A")
        confidence = "MEDIUM"
    elif agent == "devils_advocate":
        claim = case.get("framing_challenge", "N/A")
        confidence = "MEDIUM"
    else:
        claim = case.get("strongest_claim", "N/A")
        confidence = case.get("confidence", "MEDIUM")

    return body, claim, confidence


def _key_metrics_table(data: dict, styles: dict) -> Table:
    """A dense key-metrics strip, research-note style, pulled from the same
    data dict the lenses analyzed -- gives the reader the receipts up front."""
    def cell(label, value):
        return [Paragraph(label.upper(), styles["data_label"]),
                Paragraph(str(value), styles["data_val"])]

    cur = data.get("currency", "USD")
    pe = data.get("pe_ratio")
    fwd_pe = data.get("forward_pe")
    rev_g = data.get("revenue_growth")
    roe = data.get("roe")
    de = data.get("debt_to_equity")
    beta = data.get("beta")

    row1 = [
        cell("Price", f"{cur} {data.get('price', 'N/A')}"),
        cell("Trailing P/E", f"{pe:.1f}" if isinstance(pe, (int, float)) else "N/A"),
        cell("Forward P/E", f"{fwd_pe:.1f}" if isinstance(fwd_pe, (int, float)) else "N/A"),
        cell("Rev. growth", f"{rev_g*100:.1f}%" if isinstance(rev_g, (int, float)) else "N/A"),
        cell("ROE", f"{roe*100:.1f}%" if isinstance(roe, (int, float)) else "N/A"),
        cell("Debt/Equity", f"{de:.2f}" if isinstance(de, (int, float)) else "N/A"),
        cell("Beta", f"{beta:.2f}" if isinstance(beta, (int, float)) else "N/A"),
    ]
    n = len(row1)
    tbl = Table([row1], colWidths=[(170 * mm) / n] * n)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_PANEL),
        ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, C_BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    return tbl


def generate_pdf(question: str, results: dict, verdict: dict,
                 ticker: str | None = None, market_data: dict | None = None) -> str:
    """
    Main entry point. Renders the PDF directly from rule-based analysis
    output (tools/analysis_engine.py + tools/synthesizer.py). No LLM call.
    Returns path to saved PDF.
    """
    os.makedirs("outputs", exist_ok=True)
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    ticker_part = f"_{ticker.upper().replace('.','_')}" if ticker else ""
    pdf_path    = f"outputs/analysis_report{ticker_part}_{timestamp}.pdf"

    styles = make_styles()
    story  = []

    # -- HEADER --------------------------------------------------------------------------
    now = datetime.now().strftime("%d %b %Y · %H:%M")
    company_name = (market_data or {}).get("company_name", ticker or "")

    header_data = [[
        Paragraph("AGENTMESH RESEARCH", styles["header_brand"]),
        Paragraph(now, styles["label"])
    ], [
        Paragraph(
            (f"{company_name} ({ticker.upper()})" if ticker else question[:90]),
            styles["title"]
        ),
        Paragraph(
            (f'<font color="#9CA3AF">Exchange</font>  {(market_data or {}).get("exchange", "N/A")}' if market_data else ""),
            styles["label"]
        )
    ], [
        Paragraph(question[:140] + ("..." if len(question) > 140 else ""), styles["kicker"]),
        Paragraph("", styles["label"]),
    ]]
    header_tbl = Table(header_data, colWidths=[125 * mm, 45 * mm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("ALIGN",         (1, 0), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("LINEBELOW",     (0, 2), (-1, 2), 1, C_RULE),
        ("BOTTOMPADDING", (0, 2), (-1, 2), 10),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 12))

    # -- KEY METRICS STRIP ------------------------------------------------------------------
    if market_data:
        story.append(_key_metrics_table(market_data, styles))
        story.append(Spacer(1, 12))

    # -- VERDICT ROW -----------------------------------------------------------------------
    v_label      = verdict.get("verdict", "NEUTRAL").upper()
    confidence   = verdict.get("confidence", 50)
    n_consensus  = len(verdict.get("consensus_points", []))
    n_unresolved = len(verdict.get("unresolved", []))

    v_color = VERDICT_COLORS.get(v_label, VERDICT_COLORS["NEUTRAL"])

    def metric_cell(label: str, value: str, sub: str, val_color=None):
        vp = ParagraphStyle(
            "mv2", fontName=SERIF_B, fontSize=20,
            textColor=val_color or C_TEXT, leading=24
        )
        return [
            Paragraph(label.upper(), styles["label"]),
            Paragraph(value, vp),
            Paragraph(sub, styles["metric_sub"]),
        ]

    verdict_data = [[
        metric_cell("Overall lean", v_label, f"{confidence}% confidence", v_color),
        metric_cell(
            "Consensus points", str(n_consensus), "lenses agreed on",
            C_BULL_TXT if n_consensus >= 1 else C_TEXT
        ),
        metric_cell(
            "Open questions", str(n_unresolved), "needs further research",
            C_BEAR_TXT if n_unresolved >= 1 else C_TEXT
        ),
    ]]
    vw = 56.6 * mm
    verdict_tbl = Table(verdict_data, colWidths=[vw, vw, vw])
    verdict_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_NAVY_BG),
        ("BOX",           (0, 0), (-1, -1), 0.6, C_NAVY),
        ("LINEAFTER",     (0, 0), (0, 0),   0.5, C_BORDER),
        ("LINEAFTER",     (1, 0), (1, 0),   0.5, C_BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
    ]))
    story.append(verdict_tbl)
    story.append(Spacer(1, 7))

    vs = verdict.get("verdict_summary", "")
    if vs:
        story.append(Paragraph(vs, styles["agent_body"]))
    story.append(Spacer(1, 8))

    # -- FOUR LENSES -----------------------------------------------------------------------
    story.append(Paragraph("ANALYSIS BY LENS", styles["section_label"]))
    story.append(HRFlowable(width="100%", thickness=0.6, color=C_RULE, spaceAfter=9))

    for agent in ["bull", "bear", "macro", "devils_advocate"]:
        case = results.get(agent, {})
        body, claim, confidence_label = _agent_card_fields(agent, case)
        card = AgentCard(
            agent=agent,
            body=body,
            claim=claim,
            claim_label=CLAIM_LABELS.get(agent, "Key point"),
            confidence=confidence_label,
            styles=styles,
        )
        story.append(KeepTogether([card, Spacer(1, 7)]))

    # -- REBUTTAL ROUND --------------------------------------------------------------------
    rebuttal = results.get("rebuttal")
    if rebuttal:
        story.append(Paragraph("REBUTTAL ROUND", styles["section_label"]))
        story.append(HRFlowable(width="100%", thickness=0.6, color=C_RULE, spaceAfter=9))

        bear_label = ParagraphStyle("rl1", fontName=SANS_B, fontSize=8, textColor=C_BEAR_TXT, leading=11, spaceAfter=2)
        bull_label = ParagraphStyle("rl2", fontName=SANS_B, fontSize=8, textColor=C_BULL_TXT, leading=11, spaceAfter=2)

        box1 = ColoredBox(
            content_items=[
                ("BEAR ON BULL'S TOP CLAIM", bear_label),
                (rebuttal.get("bear_rebuts_bull", ""), styles["rebuttal_body"]),
            ],
            bg=C_REBUT_BG, border_color=C_REBUT_BOR, padding=(9, 12),
        )
        box2 = ColoredBox(
            content_items=[
                ("BULL ON BEAR'S TOP CLAIM", bull_label),
                (rebuttal.get("bull_rebuts_bear", ""), styles["rebuttal_body"]),
            ],
            bg=C_REBUT_BG, border_color=C_REBUT_BOR, padding=(9, 12),
        )
        story.append(KeepTogether([box1, Spacer(1, 6)]))
        story.append(KeepTogether([box2, Spacer(1, 10)]))

    # -- CONSENSUS -----------------------------------------------------------------------
    cp = verdict.get("consensus_points", [])
    if cp:
        story.append(Paragraph("CONSENSUS POINTS", styles["section_label"]))
        story.append(HRFlowable(width="100%", thickness=0.6, color=C_RULE, spaceAfter=8))
        for point in cp:
            box = ColoredBox(
                content_items=[("&#x2713;  " + point, styles["con_body"])],
                bg=C_CON_BG, border_color=C_CON_BOR, padding=(8, 12)
            )
            story.append(box)
            story.append(Spacer(1, 5))
        story.append(Spacer(1, 4))

    # -- UNRESOLVED ----------------------------------------------------------------------
    ur = verdict.get("unresolved", [])
    if ur:
        story.append(Paragraph("NEEDS FURTHER RESEARCH", styles["section_label"]))
        story.append(HRFlowable(width="100%", thickness=0.6, color=C_RULE, spaceAfter=8))
        for i, item in enumerate(ur, 1):
            content = [(f"{i}. {item.get('title','Open question')}", styles["unres_title"])]
            if item.get("bull_position") and item["bull_position"] != "N/A":
                content.append((f"Bull side: {item['bull_position']}", styles["unres_body"]))
            if item.get("bear_position") and item["bear_position"] != "N/A":
                content.append((f"Bear side: {item['bear_position']}", styles["unres_body"]))
            content.append((f"Why: {item.get('why_unresolved','')}", styles["unres_body"]))
            box = ColoredBox(
                content_items=content,
                bg=C_UNRES_BG, border_color=C_UNRES_BOR, padding=(7, 12)
            )
            story.append(KeepTogether([box, Spacer(1, 5)]))

    # -- INVESTIGATE NEXT ------------------------------------------------------------------
    investigate = verdict.get("investigate_next", [])
    if investigate:
        story.append(Paragraph("WHAT TO INVESTIGATE NEXT", styles["section_label"]))
        story.append(HRFlowable(width="100%", thickness=0.6, color=C_RULE, spaceAfter=8))
        for i, item in enumerate(investigate, 1):
            story.append(Paragraph(f"{i}. {item}", styles["agent_body"]))
            story.append(Spacer(1, 3))

    story.append(Spacer(1, 8))

    # -- BUILD PDF ---------------------------------------------------------------------------
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=16 * mm, bottomMargin=20 * mm,
        title=f"AgentMesh Research Note - {question[:60]}",
        author="AgentMesh",
    )
    doc.build(story, onFirstPage=_bg_canvas, onLaterPages=_bg_canvas)
    return pdf_path


if __name__ == "__main__":
    from tools.analysis_engine import run_full_analysis
    from tools.synthesizer import synthesize

    dummy_data = {
        "ticker": "NVDA", "currency": "USD", "sector": "Technology",
        "company_name": "NVIDIA Corporation", "exchange": "US (NYSE / NASDAQ)",
        "price": 210.69,
        "revenue_growth": 0.852, "earnings_growth": 2.145,
        "gross_margin": 0.741, "operating_margin": 0.656, "net_margin": 0.630,
        "roe": 1.143, "roa": 0.527, "free_cashflow": 46.34e9, "market_cap": 5.1e12,
        "debt_to_equity": 6.55, "current_ratio": 3.44, "beta": 2.20,
        "pe_ratio": 32.26, "forward_pe": 16.55, "peg_ratio": 0.65,
        "ev_to_ebitda": 30.56, "return_6m": 23.2, "return_1m": -5.7,
        "country": "United States",
    }
    results = run_full_analysis(dummy_data)
    verdict = synthesize(
        results["bull"], results["bear"], results["macro"], results["devils_advocate"],
        rebuttal=results["rebuttal"],
    )
    path = generate_pdf(
        "Should I buy NVDA at current valuation?", results, verdict, "NVDA",
        market_data=dummy_data,
    )
    print(f"Test PDF: {path}")
