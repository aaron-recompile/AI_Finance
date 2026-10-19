#!/usr/bin/env python3
"""Generate the Track B evidence-status PDF with verified and pending items.

Run from this folder with the bundled or system ReportLab installed:
    python3 generate_evidence_status_pdf.py

This status report is not the final course submission. Replace its pending
evidence only after the actual course leaderboard details and capture are available.
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


OUT = Path(__file__).with_name("AI_Finance_Midterm_Track_B_Evidence_Status.pdf")
WALLET = "0xB03B27ea60D9fcc73366bd0ECB41945E91307209"
APPROVAL_TX = "0x3dab3204cdf4ab28dd40d4b9940c4456b72375584b78c0ca42b250eb08f27e52"
APPROVAL_TX_URL = "https://sepolia.basescan.org/tx/" + APPROVAL_TX
BOT_TX = "0x033fcad2e3b1e2afbeeb92e150ace817aa03551cc6350f2aefa909a86b412069"
BOT_TX_URL = "https://sepolia.basescan.org/tx/" + BOT_TX

NAVY = colors.HexColor("#18344E")
BLUE = colors.HexColor("#EAF2F6")
RED = colors.HexColor("#9B352C")
AMBER = colors.HexColor("#FFF1D4")
GRAY = colors.HexColor("#526477")
GRID = colors.HexColor("#C9D7E0")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="TitleCustom", parent=styles["Title"], fontName="Helvetica-Bold",
    fontSize=23, leading=27, textColor=NAVY, alignment=TA_LEFT,
    spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="Subtitle", parent=styles["Normal"], fontName="Helvetica",
    fontSize=9.5, leading=13, textColor=GRAY, spaceAfter=13,
))
styles.add(ParagraphStyle(
    name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold",
    fontSize=14, leading=17, textColor=NAVY, spaceBefore=9, spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="BodySmall", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=9, leading=13, textColor=colors.HexColor("#243447"),
    spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="Cell", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=8.5, leading=11, textColor=colors.HexColor("#243447"),
))
styles.add(ParagraphStyle(
    name="CellBold", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=8.5, leading=11, textColor=NAVY,
))
styles.add(ParagraphStyle(
    name="Alert", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=9.5, leading=13, textColor=RED,
))


def P(text, style="BodySmall"):
    return Paragraph(text, styles[style])


def footer(canvas, doc):
    canvas.saveState()
    width, _ = letter
    canvas.setStrokeColor(GRID)
    canvas.line(0.65 * inch, 0.55 * inch, width - 0.65 * inch, 0.55 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GRAY)
    canvas.drawString(0.68 * inch, 0.36 * inch,
                      "AI Finance Midterm | Track B | Evidence status: PENDING ITEMS")
    canvas.drawRightString(width - 0.68 * inch, 0.36 * inch, f"Page {doc.page}")
    canvas.restoreState()


def grid_table(rows, widths):
    table = Table(rows, colWidths=widths, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), BLUE),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        rightMargin=0.68 * inch, leftMargin=0.68 * inch,
        topMargin=0.58 * inch, bottomMargin=0.75 * inch,
        title="AI Finance Midterm Track B - Evidence Status",
        author="Track B submission",
    )
    w1, w2 = 1.72 * inch, 5.42 * inch
    story = [
        P("AI Finance Midterm<br/>Track B Strategy Submission", "TitleCustom"),
        P("Liquidity-aware MAX/tUSDC cross-pool strategy | Evidence-status report | 2026-10-18", "Subtitle"),
    ]
    alert = Table([[P(
        "PENDING ITEMS - one bot-triggered Base Sepolia swap has a successful receipt, but leaderboard attribution/screenshot and the final evidence PDF remain pending.",
        "Alert")]], colWidths=[w1 + w2])
    alert.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AMBER),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#E4B950")),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story += [alert, P("Strategy summary", "Section"), P(
        "The bot compares MAX/tUSDC reserves in PoolA and PoolB, validates token "
        "addresses, and normalizes reserve order. It models buying MAX in the cheaper "
        "pool and selling in the dearer pool with integer constant-product quotes, an "
        "assumed 0.30% fee on each leg, reserve-driven price impact, and liquidity and "
        "modeled-net-return thresholds. A signal is an estimate only; it does not "
        "guarantee profit, and the two swaps are not atomic."),
        P("Last read-only wallet observation", "Section"),
    ]
    story.append(grid_table([
        [P("Network", "CellBold"), P("Base Sepolia; chain ID 84532", "Cell")],
        [P("Wallet", "CellBold"), P(WALLET, "Cell")],
        [P("Observation date", "CellBold"), P("2026-10-17 pre-swap observation; not a current balance reading", "Cell")],
        [P("Prior balances", "CellBold"), P("990 tUSDC; 0.022745172278331082 MAX; 0.008984434399283523 ETH", "Cell")],
        [P("Token decimals", "CellBold"), P("tUSDC: 18; MAX: 18", "Cell")],
        [P("Signer configuration", "CellBold"), P("One-time hidden-input check was reported MATCH; transaction sender is the target wallet; key is not stored", "Cell")],
    ], [w1, w2]))
    story += [P("Allowance investigation", "Section"), P(
        "The prior read-only observation recorded the tUSDC allowance to RouterA as "
        "uint256 maximum (unlimited). The latest "
        "matching Approval event found at chain head 48252597 was in block 48176047. "
        "The successful call was approve(RouterA, 2**256 - 1) on tUSDC, sent by the "
        "specified wallet. This identifies the on-chain grant transaction, not the "
        "person who initiated it or its purpose. OWNER CONFIRMED: the wallet owner has confirmed in "
        "chat that the allowance was intentional and accepts its risk; a compromised RouterA could put future "
        "tUSDC balances at risk. No approval was changed."),
        P(f"Historical approval (not trade evidence): <link href='{APPROVAL_TX_URL}' color='#245A80'>{APPROVAL_TX}</link> | 2026-10-16 03:13:02 UTC | receipt status 1", "BodySmall"),
        P("Verified ONE-LEG TEST SWAP (not a two-pool arbitrage): <link href='" + BOT_TX_URL + "' color='#245A80'>" + BOT_TX + "</link> | block 48269151 | receipt status 1 | 1 tUSDC spent | 0.001556838097665726 MAX received | amountOutMin 0.001541269716689068 MAX | gas used 96180. The initial receipt verification failed because transaction input bytes and locally encoded calldata used different 0x-prefix formats; the adapter now normalizes both. Dashboard P&amp;L is recorded as 0; no arbitrage profit is claimed.", "BodySmall"),
        PageBreak(),
        P("Execution guard, tests, and remaining evidence", "TitleCustom"),
        P("The one-shot path is a single tUSDC-to-MAX test swap, not arbitrage.", "Subtitle"),
        P("Execution safeguards", "Section"), P(
        "The bot requires a fresh signal, explicit AGENT_KEY matching AGENT_ADDRESS, "
        "the additional bot-specific COURSE_TEST_SWAP_AUTHORIZED=YES gate, Base Sepolia "
        "chain ID, expected token decimals, "
        "sufficient balance and existing RouterA allowance, and gas below its configured "
        "cap. It does not create an allowance or fall back to a funder or ephemeral key. "
        "The wallet owner has confirmed the uint256-max allowance is intentional and "
        "accepts its risk; execution still requires a separate local acknowledgement. "
        "It returns a structured proposal, computes positive amountOutMin, displays the "
        "gas cap and maximum gas cost, and binds the interactive approval phrase to the "
        "router and minimum output. After an approved transaction it verifies the "
        "receipt, exact tUSDC spend, minimum MAX received, and before/after balances."),
        P("Tests and PDF workflow", "Section"), P(
        "Command: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover over all submission test files. "
        "Result on 2026-10-18: 59 offline mock tests passed. The tests do not access RPC, "
        "load a real key, sign, or broadcast. Rebuild this status report with "
        "python3 generate_evidence_status_pdf.py. It lists verified and pending items "
        "and is not a final course submission. The final-PDF builder "
        "requires a real evidence manifest and screenshot, verifies swaps over RPC, "
        "and refuses to create a final PDF when evidence is missing."),
        P("Evidence status", "Section"),
    ]
    story.append(grid_table([
        [P("Course requirements", "CellBold"), P("The transaction is complete; leaderboard attribution remains PENDING. README gives no separate one-shot authorization procedure", "Cell")],
        [P("Bot-specific gate", "CellBold"), P("Set process-locally for the one-shot run only; it is a bot guard, not course authorization evidence", "Cell")],
        [P("Signer", "CellBold"), P("One-time hidden-input check was reported MATCH; successful transaction sender equals the target wallet. No key is stored in this submission", "Cell")],
        [P("Allowance risk", "CellBold"), P("OWNER CONFIRMED - intentional unlimited RouterA allowance; risk accepted. One-time local acknowledgement was process-only", "Cell")],
        [P("Bot tx / hash", "CellBold"), P("COMPLETE - one successful 1 tUSDC -> MAX swap; receipt and transfer events verified. This is not a two-pool arbitrage", "Cell")],
        [P("Leaderboard evidence", "CellBold"), P("PENDING - no verified URL, attribution rule, or authentic screenshot", "Cell")],
        [P("Transaction verification", "CellBold"), P("Receipt status, sender, router call, calldata and ERC-20 Transfer events verified for block 48269151; one tUSDC spent and 0.001556838097665726 MAX received. The local runner's calldata comparison bug is fixed and covered by mocks.", "Cell")],
        [P("Final evidence PDF", "CellBold"), P("PENDING - this is a status report, not final submission evidence", "Cell")],
    ], [w1, w2]))
    story += [P("Manual items", "Section"), P(
        "The swap receipt and Transfer events are verified, but leaderboard attribution is unverified. Request the actual leaderboard URL and attribution rules, capture the leaderboard entry, then generate and inspect the final PDF. The original runner verification error came from the 0x-prefix mismatch in transaction calldata comparison; the adapter now normalizes the values and mock tests cover it. One swap does not prove arbitrage profit.", "BodySmall")]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    build()
    print(OUT)
