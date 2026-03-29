#!/usr/bin/env python3
"""
hype-sync.py — Reconcile brain DB positions with live Hyperliquid positions.

Usage:
  python3 hype-sync.py          # dry run (shows what would happen)
  python3 hype-sync.py --apply  # actually mirror missing trades

What it does:
  1. Get open positions from brain DB (paper + live)
  2. Get actual open positions from Hyperliquid
  3. For each brain position not on HL → mirror_open
  4. For each HL position not in brain  → mirror_close (paper-only protection)
  5. Log everything with clear PASS/FAIL/INFO tags
"""
import sys, argparse, time
sys.path.insert(0, '/root/.hermes/scripts')

from hyperliquid_exchange import (
    mirror_open, mirror_close, is_live_trading_enabled,
    get_open_hype_positions_curl, is_delisted, get_tradeable_tokens
)
from position_manager import get_open_positions as pm_get_open

DRY = True  # overridden by --apply


def log(msg, tag="INFO"):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{tag}] {msg}")



def get_hype_positions():
    """Get live HL positions. Returns {} on failure."""
    try:
        return get_open_hype_positions_curl()
    except Exception as e:
        log(f"Failed to fetch HL positions: {e}", "WARN")
        return {}


def sync_opens(brain_positions, hype_positions):
    """Mirror any brain positions missing from HL."""
    hype_tokens = set(hype_positions.keys())
    tradeable = get_tradeable_tokens()
    opened = skipped = delisted = 0

    for pos in brain_positions:
        token = pos["token"]

        # Check if delisted FIRST (before claiming "missing on HL")
        if is_delisted(token):
            log(f"  {token}: DELISTED on HL — cannot mirror", "WARN")
            delisted += 1
            continue

        if token in hype_tokens:
            log(f"  {token}: already on HL ✓", "INFO")
            skipped += 1
            continue

        tag = "DRY" if DRY else "SYNC"
        log(f"  {token}: missing on HL → {tag} {pos['direction']} @ ${pos['entry_price']:.4f} lev={pos['leverage']}x", "WARN")

        if DRY:
            opened += 1
            continue

        try:
            result = mirror_open(
                token, pos["direction"].upper(),
                float(pos["entry_price"]),
                leverage=int(pos["leverage"])
            )
            if result.get("success"):
                log(f"  {token}: ✅ mirror_open SUCCESS — {result.get('size')} units @ ${result.get('entry_price')} lev={result.get('leverage')}x", "PASS")
            else:
                msg = result.get("message", "unknown error")
                log(f"  {token}: ❌ mirror_open FAILED — {msg}", "FAIL")
        except Exception as e:
            log(f"  {token}: ❌ mirror_open EXCEPTION — {e}", "FAIL")

        opened += 1
        time.sleep(1)  # rate limit protection

    return opened, skipped, delisted


def sync_closes(hype_positions, brain_positions):
    """Close any HL positions that aren't in brain DB (paper protection)."""
    brain_tokens = {p["token"] for p in brain_positions}
    closed = 0

    for token, pos in hype_positions.items():
        if token in brain_tokens:
            continue

        tag = "DRY" if DRY else "SYNC"
        direction = pos.get("direction", "UNKNOWN")
        log(f"  {token}: on HL but not in brain → {tag} CLOSE {direction}", "WARN")

        if DRY:
            closed += 1
            continue

        try:
            result = mirror_close(token)
            if result.get("success"):
                log(f"  {token}: ✅ mirror_close SUCCESS — closed {result.get('size')} units", "PASS")
            else:
                msg = result.get("message", "unknown error")
                log(f"  {token}: ❌ mirror_close FAILED — {msg}", "FAIL")
        except Exception as e:
            log(f"  {token}: ❌ mirror_close EXCEPTION — {e}", "FAIL")

        closed += 1
        time.sleep(1)

    return closed


def main():
    global DRY
    parser = argparse.ArgumentParser(description="Sync brain positions with Hyperliquid")
    parser.add_argument("--apply", action="store_true", help="Actually execute mirror trades (default is dry-run)")
    parser.add_argument("--opens-only", action="store_true", help="Only check missing opens")
    parser.add_argument("--closes-only", action="store_true", help="Only check unexpected closes")
    args = parser.parse_args()
    DRY = not args.apply

    mode = "DRY RUN" if DRY else "LIVE SYNC"
    live = is_live_trading_enabled()
    log(f"hype-sync starting — {mode} | Live trading: {'ON' if live else 'OFF'}", "INFO")

    if not live:
        log("Live trading is DISABLED — opens will be blocked by hyperliquid_exchange", "WARN")

    brain_pos = pm_get_open()
    log(f"Brain open positions: {len(brain_pos)}", "INFO")
    for p in brain_pos:
        log(f"  {p['token']} {p['direction']} @ ${p['entry_price']:.4f} lev={p['leverage']}x", "INFO")

    hype_pos = get_hype_positions()
    log(f"HL open positions: {len(hype_pos)}", "INFO")
    for token, p in hype_pos.items():
        log(f"  {token} {p.get('direction')} ${p.get('entry_price')} lev={p.get('leverage')}x", "INFO")

    opens_ok = closes_ok = 0
    if not args.closes_only:
        log("--- Checking missing HL opens ---", "INFO")
        opened, skipped, delisted = sync_opens(brain_pos, hype_pos)
        to_mirror = opened - skipped
        log(f"Opens: {skipped} already on HL | {delisted} delisted | {to_mirror} would mirror", "INFO")

    if not args.opens_only:
        log("--- Checking unexpected HL closes ---", "INFO")
        closed = sync_closes(hype_pos, brain_pos)
        closes_ok = closed
        log(f"Closes: {closed} closed (should be 0 — if not, investigate)", "WARN" if closed else "INFO")

    if DRY:
        log("DRY RUN complete — re-run with --apply to execute", "WARN")
    else:
        log(f"SYNC complete — {opens_ok} opened, {closes_ok} closed", "PASS")


if __name__ == "__main__":
    main()
