#!/usr/bin/env python3
"""
hype-paper-sync.py — Keep HL in sync with paper trades.json

Monitors paper DB (trades.json) vs live HL positions:
  1. Get open positions from paper trades.json
  2. Get open positions from HL via exchange API
  3. For each HL position NOT in paper → close it on HL
  4. Log everything clearly

Usage:
  python3 hype-paper-sync.py          # dry run
  python3 hype-paper-sync.py --apply  # actually close orphaned positions
"""
import sys, json, time, argparse
sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import (
    get_open_hype_positions_curl,
    is_live_trading_enabled,
    get_exchange,
)


PAPER_JSON = "/var/www/hermes/data/trades.json"
DRY = True


def log(msg, tag="INFO"):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{tag}] {msg}")


def get_paper_positions():
    """Load open positions from paper trades.json."""
    try:
        with open(PAPER_JSON) as f:
            data = json.load(f)
        positions = []
        for p in data.get("open", []):
            positions.append({
                "token": p.get("token"),
                "direction": p.get("direction"),
                "entry": p.get("entry"),
                "exchange": p.get("exchange", ""),
            })
        return positions
    except Exception as e:
        log(f"Failed to load paper trades: {e}", "FAIL")
        return []


def get_hype_positions():
    """Get live HL positions. Returns {} on failure."""
    try:
        return get_open_hype_positions_curl()
    except Exception as e:
        log(f"Failed to fetch HL positions: {e}", "WARN")
        return {}


def sync_closes(hype_positions, paper_positions):
    """
    Close any HL positions that don't have a corresponding paper position.
    This is the "safety net" — if paper says a trade is closed but HL still has it open,
    we close it on HL.
    """
    if not paper_positions:
        log("Paper positions empty — unknown state, skipping orphaned closes", "WARN")
        return 0, len(hype_positions)

    paper_tokens = {p["token"] for p in paper_positions if p.get("exchange", "").lower() == "hyperliquid"}
    closed = 0
    skipped = 0

    for token, pos in hype_positions.items():
        if token in paper_tokens:
            log(f"  {token}: paper confirms open ✓", "INFO")
            skipped += 1
            continue

        direction = pos.get("direction", "UNKNOWN")
        entry = pos.get("entry_price", "?")
        tag = "DRY" if DRY else "CLOSE"
        log(f"  {token}: on HL but NOT in paper → {tag} {direction} @ {entry}", "WARN")

        if DRY:
            closed += 1
            continue

        try:
            exchange = get_exchange()
            # Use market_close to close the orphaned position
            result = exchange.market_close(coin=token, slippage=0.005)
            statuses = result.get("response", {}).get("data", {}).get("statuses", [])
            for s in statuses:
                if "error" in s:
                    log(f"  {token}: ❌ close FAILED — {s['error']}", "FAIL")
                else:
                    log(f"  {token}: ✅ CLOSED on HL", "PASS")
            time.sleep(3)
        except Exception as e:
            log(f"  {token}: ❌ close EXCEPTION — {e}", "FAIL")

        closed += 1

    return closed, skipped


def main():
    global DRY
    parser = argparse.ArgumentParser(description="Sync HL with paper trades.json")
    parser.add_argument("--apply", action="store_true", help="Actually close orphaned positions (default is dry-run)")
    args = parser.parse_args()
    DRY = not args.apply

    mode = "DRY RUN" if DRY else "LIVE SYNC"
    live = is_live_trading_enabled()
    log(f"hype-paper-sync starting — {mode} | Live trading: {'ON' if live else 'OFF'}", "INFO")

    paper_pos = get_paper_positions()
    hype_pos = get_hype_positions()

    # Split paper positions by exchange
    paper_hl = [p for p in paper_pos if p.get("exchange", "").lower() == "hyperliquid"]
    paper_other = [p for p in paper_pos if p.get("exchange", "").lower() != "hyperliquid"]

    log(f"Paper HL positions: {len(paper_hl)}", "INFO")
    for p in paper_hl:
        log(f"  {p['token']} {p['direction']} entry={p['entry']}", "INFO")

    if paper_other:
        log(f"Paper non-HL positions: {len(paper_other)} (not relevant for HL sync)", "INFO")

    log(f"HL open positions: {len(hype_pos)}", "INFO")
    for token, p in hype_pos.items():
        log(f"  {token} {p.get('direction')} entry={p.get('entry_price')}", "INFO")

    log("--- Checking for orphaned HL positions (paper says closed, HL still open) ---", "INFO")
    closed, confirmed = sync_closes(hype_pos, paper_pos)

    orphaned = closed
    log(f"Result: {confirmed} confirmed in sync | {orphaned} orphaned (need closing)", "WARN" if orphaned else "PASS")

    if DRY:
        log("DRY RUN — re-run with --apply to close orphaned positions", "WARN")
    else:
        log(f"SYNC complete", "PASS")


if __name__ == "__main__":
    main()
