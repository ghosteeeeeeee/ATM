#!/usr/bin/env python3
"""
Force ATR SL/TP Update — One-shot script to apply ATR-based stop-loss and
take-profit to all currently open positions in Hermes.

Usage:
  python3 force_atr_update.py          # paper mode (default)
  python3 force_atr_update.py --live  # push to real Hyperliquid

This script:
  1. Reads all open positions from brain DB via get_open_positions()
  2. Computes ATR-based SL and TP for each using _force_fresh_atr()
  3. Bypasses ATR_UPDATE_THRESHOLD_PCT to force-push ALL positions
  4. Calls _execute_atr_bulk_updates() to push orders to Hyperliquid
  5. Logs before/after for each position
"""

import argparse
import sys
import os

# Add scripts/ to path so we can import position_manager
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Paper/live flag — must be set before position_manager imports hype_cache
PAPER_MODE = True  # default

def parse_args():
    parser = argparse.ArgumentParser(description="Force ATR SL/TP update on all open positions")
    parser.add_argument("--live", action="store_true", help="Push to real Hyperliquid (default: paper)")
    return parser.parse_args()


def force_atr_update():
    from position_manager import (
        get_open_positions,
        _force_fresh_atr,
        _atr_multiplier,
        _execute_atr_bulk_updates,
        SERVER_NAME,
    )

    print(f"[Force ATR] Starting force-update (paper={PAPER_MODE})")
    print(f"[Force ATR] Server: {SERVER_NAME}")

    # ── 1. Read open positions ──────────────────────────────────────────────
    open_positions = get_open_positions(server=SERVER_NAME)
    if not open_positions:
        print("[Force ATR] No open positions found.")
        return

    print(f"[Force ATR] Found {len(open_positions)} open positions")

    # ── 2. Deduplicate tokens and fetch fresh ATR for each ──────────────────
    tokens_seen = {}
    for pos in open_positions:
        token = str(pos.get("token", "")).upper()
        if token and token not in tokens_seen:
            atr = _force_fresh_atr(token)
            tokens_seen[token] = atr
            entry = float(pos.get('entry_price') or 0)
            atr_info = f"{atr:.4f} ({atr/entry*100:.2f}%)" if atr and entry else "FAILED (no entry_price)"
            print(f"  [ATR] {token}: {atr_info}")

    # ── 3. Build force-update dicts (bypass threshold check) ───────────────
    updates = []
    for pos in open_positions:
        token = str(pos.get("token", "")).upper()
        direction = str(pos.get("direction", "")).upper()
        entry_price = float(pos.get("entry_price") or 0)
        trade_id = pos.get("id")
        current_sl = float(pos.get("stop_loss") or 0)
        current_tp = float(pos.get("target") or 0)
        source = str(pos.get("source") or "")

        # Skip cascade-flip positions — they manage their own tighter SL
        if source.startswith("cascade-reverse-"):
            print(f"  [Skip] {token} {trade_id}: cascade-flip position")
            continue

        if not token or not entry_price or not trade_id:
            continue

        atr = tokens_seen.get(token)
        if atr is None:
            print(f"  [Skip] {token}: no ATR available")
            continue

        atr_pct = atr / entry_price
        k = _atr_multiplier(atr_pct)
        sl_pct = k * atr_pct
        tp_pct = 2 * k * atr_pct

        if direction == "LONG":
            new_sl = round(entry_price * (1 - sl_pct), 8)
            new_tp = round(entry_price * (1 + tp_pct), 8)
        elif direction == "SHORT":
            new_sl = round(entry_price * (1 + sl_pct), 8)
            new_tp = round(entry_price * (1 - tp_pct), 8)
        else:
            continue

        updates.append({
            "trade_id": trade_id,
            "token": token,
            "direction": direction,
            "entry_price": entry_price,
            "old_sl": current_sl,
            "new_sl": new_sl,
            "old_tp": current_tp,
            "new_tp": new_tp,
            "needs_sl": True,   # FORCE — bypass threshold
            "needs_tp": True,   # FORCE — bypass threshold
            "atr": atr,
            "atr_pct": atr_pct,
            "k": k,
        })

        sl_delta = abs(new_sl - current_sl) / current_sl if current_sl > 0 else 1.0
        tp_delta = abs(new_tp - current_tp) / current_tp if current_tp > 0 else 1.0
        print(
            f"  [Update] {token} {direction} trade_id={trade_id}\n"
            f"           SL: {current_sl:.4f} → {new_sl:.4f} "
            f"(\u0394{sl_delta*100:+.2f}%, k={k}, ATR={atr:.4f})\n"
            f"           TP: {current_tp:.4f} → {new_tp:.4f} "
            f"(\u0394{tp_delta*100:+.2f}%)"
        )

    if not updates:
        print("[Force ATR] No positions needed updating.")
        return

    print(f"[Force ATR] Forcing SL/TP update on {len(updates)} positions...")

    # ── 4. Execute bulk updates ────────────────────────────────────────────
    result = _execute_atr_bulk_updates(updates)

    print(f"[Force ATR] Bulk push result:")
    print(f"           Cancelled: {result['cancelled']}")
    print(f"           Placed:    {result['placed']}")
    if result["errors"]:
        for err in result["errors"]:
            print(f"           Error: {err}")

    # ── 5. Summary ─────────────────────────────────────────────────────────
    print("\n[Force ATR] Summary:")
    print(f"  Positions processed: {len(updates)}")
    print(f"  Orders placed:      {result['placed']}")
    print(f"  Orders cancelled:   {result['cancelled']}")
    print(f"  Errors:             {len(result['errors'])}")

    if result["errors"]:
        print("\n[Force ATR] ERRORS — review before continuing:")
        for err in result["errors"]:
            print(f"  ! {err}")
        sys.exit(1)
    else:
        print("\n[Force ATR] Done — all positions updated successfully.")


if __name__ == "__main__":
    args = parse_args()
    PAPER_MODE = not args.live  # flip: paper if not --live

    # Also flip hype_cache paper flag
    import hype_cache as hc
    hc.PAPER_MODE = PAPER_MODE

    force_atr_update()
