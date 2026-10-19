#!/usr/bin/env python3
"""Assemble final Track B evidence only from supplied real evidence.

This command intentionally fails until a complete JSON evidence manifest and
real leaderboard screenshot are supplied. It checks every transaction against
the configured Base Sepolia RPC and refuses the historical unlimited-approval
transaction recorded in NOTES.md.

Manifest format is documented in NOTES.md. Run from this folder:
    python3 generate_final_submission_pdf.py --manifest final_evidence.json
"""
import argparse
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit
from xml.sax.saxutils import escape, quoteattr

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.utils import ImageReader

HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / "AI_Finance_Midterm_Track_B_Final_Submission.pdf"
APPROVAL_TX = "0x3dab3204cdf4ab28dd40d4b9940c4456b72375584b78c0ca42b250eb08f27e52"
EXPECTED_CHAIN_ID = 84532
TOKEN_DECIMALS_ABI = [{
    "name": "decimals", "type": "function", "stateMutability": "view",
    "inputs": [], "outputs": [{"type": "uint8"}],
}]
SWAP_ABI = [{
    "name": "swapExactTokensForTokens", "type": "function",
    "stateMutability": "nonpayable",
    "inputs": [
        {"name": "amountIn", "type": "uint256"},
        {"name": "amountOutMin", "type": "uint256"},
        {"name": "tokenIn", "type": "address"},
        {"name": "tokenOut", "type": "address"},
        {"name": "to", "type": "address"},
    ], "outputs": [{"type": "uint256"}],
}]
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="TitleCustom", parent=styles["Title"], fontName="Helvetica-Bold",
    fontSize=23, leading=27, textColor=colors.HexColor("#18344E"), alignment=TA_LEFT,
    spaceAfter=7,
))
styles.add(ParagraphStyle(
    name="SectionCustom", parent=styles["Heading2"], fontName="Helvetica-Bold",
    fontSize=13, leading=16, textColor=colors.HexColor("#18344E"),
    spaceBefore=8, spaceAfter=5,
))
styles.add(ParagraphStyle(
    name="BodyCustom", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=9, leading=13, textColor=colors.HexColor("#263747"), spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="CellCustom", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=8, leading=10, textColor=colors.HexColor("#263747"),
))
styles.add(ParagraphStyle(
    name="CellLabel", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=8, leading=10, textColor=colors.HexColor("#18344E"),
))


def p(text, style="BodyCustom"):
    return Paragraph(str(text), styles[style])


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _human_to_units(value, decimals, label):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} must be a decimal number") from None
    _require(number.is_finite() and number >= 0, f"{label} must be nonnegative")
    units = number * (10 ** decimals)
    _require(units == units.to_integral_value(), f"{label} has excess token precision")
    return int(units)


def _format_units(value, decimals):
    text = format(Decimal(value) / (10 ** decimals), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _topic_address(topic):
    from web3 import Web3
    raw = topic.hex() if hasattr(topic, "hex") else str(topic)
    return Web3.to_checksum_address("0x" + raw[-40:])


def _transfers(receipt, token_address):
    from web3 import Web3
    transfer_topic = Web3.keccak(text="Transfer(address,address,uint256)").hex().lower()
    result = []
    for log in receipt["logs"]:
        if Web3.to_checksum_address(log["address"]) != token_address:
            continue
        if not log["topics"] or log["topics"][0].hex().lower() != transfer_topic:
            continue
        result.append((
            _topic_address(log["topics"][1]),
            _topic_address(log["topics"][2]),
            int.from_bytes(log["data"], "big"),
        ))
    return result


def verify_manifest(manifest, manifest_path):
    from web3 import Web3
    from chain import ADDR, CHAIN_ID, w3

    _require(w3.eth.chain_id == EXPECTED_CHAIN_ID == CHAIN_ID,
             "Configured RPC is not Base Sepolia chain ID 84532")
    try:
        wallet = Web3.to_checksum_address(manifest["wallet_address"])
    except Exception:
        raise ValueError("wallet_address is missing or malformed") from None
    _require(re.fullmatch(r"0x[0-9a-fA-F]{40}", manifest["wallet_address"]) is not None,
             "wallet_address is malformed")
    _require(manifest.get("chain_id") == EXPECTED_CHAIN_ID,
             "manifest chain_id must be 84532")
    summary = manifest.get("strategy_sentences")
    _require(isinstance(summary, list) and 3 <= len(summary) <= 5
             and all(isinstance(s, str) and s.strip() for s in summary),
             "strategy_sentences must contain 3 to 5 complete sentences")
    tests = manifest.get("offline_tests", {})
    _require(isinstance(tests, dict) and bool(tests.get("command"))
             and bool(tests.get("result")),
             "offline_tests.command and offline_tests.result are required")
    leaderboard_url = manifest.get("leaderboard_url", "")
    parsed_url = urlsplit(leaderboard_url)
    _require(parsed_url.scheme in ("https", "http") and bool(parsed_url.netloc)
             and "localhost" not in (parsed_url.hostname or "").lower(),
             "leaderboard_url must be the instructor-provided live URL")
    screenshot_path = Path(manifest.get("leaderboard_screenshot", ""))
    if not screenshot_path.is_absolute():
        screenshot_path = (manifest_path.parent / screenshot_path).resolve()
    _require(screenshot_path.is_file(), "real leaderboard_screenshot file is missing")
    try:
        ImageReader(str(screenshot_path)).getSize()
    except Exception:
        raise ValueError("leaderboard_screenshot is not a readable image") from None

    tx_items = manifest.get("transactions")
    _require(isinstance(tx_items, list) and tx_items
             and all(isinstance(item, dict) for item in tx_items),
             "at least one real bot-triggered transaction is required")
    token_in = Web3.to_checksum_address(ADDR["tUSDC"])
    token_out = Web3.to_checksum_address(ADDR["MAX"])
    decimals_in = w3.eth.contract(address=token_in, abi=TOKEN_DECIMALS_ABI).functions.decimals().call()
    decimals_out = w3.eth.contract(address=token_out, abi=TOKEN_DECIMALS_ABI).functions.decimals().call()
    verified = []
    seen = set()
    for i, item in enumerate(tx_items, 1):
        tx_hash = item.get("hash", "")
        _require(re.fullmatch(r"0x[0-9a-fA-F]{64}", tx_hash) is not None,
                 f"transactions[{i}].hash must be a 32-byte transaction hash")
        _require(tx_hash.lower() != APPROVAL_TX.lower(),
                 "the historical approve transaction is not bot-trade evidence")
        _require(tx_hash.lower() not in seen, "duplicate transaction hash")
        seen.add(tx_hash.lower())
        tx = w3.eth.get_transaction(tx_hash)
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        _require(receipt.status == 1, f"transactions[{i}] receipt did not succeed")
        _require(Web3.to_checksum_address(tx["from"]) == wallet,
                 f"transactions[{i}] sender does not match wallet_address")
        _require(int(tx.get("chainId", -1)) == EXPECTED_CHAIN_ID,
                 f"transactions[{i}] is not on Base Sepolia")
        router_address = Web3.to_checksum_address(tx["to"])
        routers = {Web3.to_checksum_address(ADDR["RouterA"]),
                   Web3.to_checksum_address(ADDR["RouterB"])}
        _require(router_address in routers, f"transactions[{i}] is not sent to a course router")
        router = w3.eth.contract(address=router_address, abi=SWAP_ABI)
        try:
            function, args = router.decode_function_input(tx["input"])
        except Exception:
            raise ValueError(f"transactions[{i}] calldata is not a supported swap") from None
        _require(function.fn_name == "swapExactTokensForTokens",
                 f"transactions[{i}] is not a token swap")
        _require(Web3.to_checksum_address(args["to"]) == wallet,
                 f"transactions[{i}] recipient does not match wallet_address")
        _require(Web3.to_checksum_address(args["tokenIn"]) == token_in
                 and Web3.to_checksum_address(args["tokenOut"]) == token_out,
                 f"transactions[{i}] is not the expected tUSDC-to-MAX bot swap")
        amount_in, amount_out_min = int(args["amountIn"]), int(args["amountOutMin"])
        _require(amount_in > 0 and amount_out_min > 0,
                 f"transactions[{i}] has a zero amount or minimum output")

        in_events = _transfers(receipt, token_in)
        out_events = _transfers(receipt, token_out)
        _require(any(src == wallet and value == amount_in for src, _dst, value in in_events),
                 f"transactions[{i}] lacks matching tUSDC spend event")
        received = sum(value for _src, dst, value in out_events if dst == wallet)
        _require(received >= amount_out_min,
                 f"transactions[{i}] MAX transfer events are below amountOutMin")

        before, after = item.get("balances_before", {}), item.get("balances_after", {})
        _require(all(k in before and k in after for k in ("tUSDC", "MAX")),
                 f"transactions[{i}] requires before/after tUSDC and MAX balances")
        before_in = _human_to_units(before["tUSDC"], decimals_in, "before tUSDC")
        after_in = _human_to_units(after["tUSDC"], decimals_in, "after tUSDC")
        before_out = _human_to_units(before["MAX"], decimals_out, "before MAX")
        after_out = _human_to_units(after["MAX"], decimals_out, "after MAX")
        _require(before_in - after_in == amount_in,
                 f"transactions[{i}] tUSDC balance delta does not equal swap amountIn")
        _require(after_out - before_out == received,
                 f"transactions[{i}] MAX balance delta does not match receipt transfer events")
        verified.append({
            "hash": tx_hash,
            "url": "https://sepolia.basescan.org/tx/" + tx_hash,
            "block": receipt.blockNumber,
            "router": router_address,
            "amount_in": amount_in,
            "amount_out_min": amount_out_min,
            "received": received,
            "amount_in_display": _format_units(amount_in, decimals_in),
            "amount_out_min_display": _format_units(amount_out_min, decimals_out),
            "received_display": _format_units(received, decimals_out),
            "gas_used": receipt.gasUsed,
            "gas_price": int(receipt.effectiveGasPrice),
            "before": before,
            "after": after,
        })
    return wallet, screenshot_path, leaderboard_url, summary, tests, verified


def build_pdf(data, output_path):
    wallet, screenshot, leaderboard_url, summary, tests, transactions = data
    doc = SimpleDocTemplate(
        str(output_path), pagesize=letter,
        rightMargin=0.68 * inch, leftMargin=0.68 * inch,
        topMargin=0.58 * inch, bottomMargin=0.68 * inch,
        title="AI Finance Midterm Track B Final Evidence",
        author="Track B submission",
    )
    story = [
        p("AI Finance Midterm<br/>Track B Final Submission", "TitleCustom"),
        p("Verified Base Sepolia bot action and leaderboard evidence", "BodyCustom"),
        p("Wallet and strategy", "SectionCustom"),
        p(f"Wallet: {wallet}<br/>Network: Base Sepolia (chain ID {EXPECTED_CHAIN_ID})"),
    ]
    story.extend(p(escape(sentence)) for sentence in summary)
    story += [p("Verified bot transactions", "SectionCustom")]
    for i, tx in enumerate(transactions, 1):
        story.append(p(
            f"Transaction {i}: <link href='{tx['url']}' color='#245A80'>{tx['hash']}</link><br/>"
            f"Block {tx['block']}; receipt status 1; Router {tx['router']}<br/>"
            f"tUSDC spent: {tx['amount_in_display']}; MAX amountOutMin: "
            f"{tx['amount_out_min_display']}; MAX received: {tx['received_display']}<br/>"
            f"Gas used: {tx['gas_used']}; effective gas price: {tx['gas_price']} wei<br/>"
            f"tUSDC balance: {tx['before']['tUSDC']} -> {tx['after']['tUSDC']}; "
            f"MAX balance: {tx['before']['MAX']} -> {tx['after']['MAX']}"
        ))
    story += [
        p("Leaderboard evidence", "SectionCustom"),
        p(f"Live leaderboard: <link href={quoteattr(leaderboard_url)} color='#245A80'>"
          f"{escape(leaderboard_url)}</link>"),
        Image(str(screenshot), width=7.05 * inch, height=4.0 * inch, kind="proportional"),
        Spacer(1, 5),
        p("Offline testing", "SectionCustom"),
        p(f"Command: {escape(tests['command'])}<br/>Result: {escape(tests['result'])}"),
        p("This PDF is generated from a manifest after checking each transaction "
          "against the configured Base Sepolia RPC. The leaderboard screenshot is "
          "included as provided and must be an authentic capture.", "BodyCustom"),
    ]
    doc.build(story)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path,
                        help="JSON file containing real, verified submission evidence")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        manifest_path = args.manifest.resolve()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        data = verify_manifest(manifest, manifest_path)
        output_path = args.output.resolve()
        _require(output_path.parent == HERE,
                 "output must stay inside the zhenzhenfang-source submission folder")
        _require(output_path != HERE / "AI_Finance_Midterm_Track_B_Evidence_Status.pdf",
                 "final evidence output cannot overwrite the pending status PDF")
        build_pdf(data, output_path)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, RuntimeError) as exc:
        print(f"Final evidence PDF not generated: {exc}", file=sys.stderr)
        return 2
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
