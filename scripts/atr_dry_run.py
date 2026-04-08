#!/usr/bin/env python3
"""
Dry-run validation of ATR TP/SL bug fixes (2026-04-08).
Does NOT place any orders — computes what _collect_atr_updates() would produce.
"""
import sys
import os
sys.path.insert(0, '/root/.hermes/scripts')

from position_manager import (
    get_open_positions, _force_fresh_atr, _atr_multiplier,
    ATR_UPDATE_THRESHOLD_PCT, refresh_current_prices
)

ATR_UPDATE_THRESHOLD_PCT = 0.005  # 0.5%

def _atr_multiplier(atr_pct):
    if atr_pct >= 0.10:   return 2.0
    elif atr_pct >= 0.05: return 1.5
    elif atr_pct >= 0.02: return 1.0
    elif atr_pct >= 0.01: return 0.5
    else:                 return 0.25

def main():
    positions = refresh_current_prices()
    if not positions:
        print("No open positions found.")
        return

    # Deduplicate tokens
    tokens_seen = {}
    for pos in positions:
        token = str(pos.get('token', '')).upper()
        if token and token not in tokens_seen:
            atr = _force_fresh_atr(token)
            tokens_seen[token] = atr

    print(f"=== ATR TP/SL Dry-Run Validation ({len(positions)} positions, {len(tokens_seen)} tokens) ===\n")

    updates_total = 0
    for pos in positions:
        token = str(pos.get('token', '')).upper()
        direction = str(pos.get('direction', '')).upper()
        entry_price = float(pos.get('entry_price') or 0)
        current_price = float(pos.get('current_price') or 0)
        trade_id = pos.get('id')
        current_sl = float(pos.get('stop_loss') or 0)
        current_tp = float(pos.get('target') or 0)
        source = str(pos.get('source') or '')

        if source.startswith('cascade-reverse-'):
            print(f"[SKIP] {token} — cascade-flip managed")
            continue
        if not token or not trade_id:
            continue
        atr = tokens_seen.get(token)
        if atr is None:
            print(f"[SKIP] {token} — no ATR")
            continue
        if entry_price <= 0:
            print(f"[SKIP] {token} — no entry_price")
            continue

        atr_pct = atr / entry_price
        k = _atr_multiplier(atr_pct)
        sl_pct = k * atr_pct
        tp_pct = 2 * k * atr_pct

        ref_price = current_price if current_price > 0 else entry_price
        if not ref_price > 0:
            print(f"[SKIP] {token} — no ref_price")
            continue

        if direction == "LONG":
            new_sl = round(ref_price * (1 - sl_pct), 8)
            new_tp = round(ref_price * (1 + tp_pct), 8)
        elif direction == "SHORT":
            new_sl = round(ref_price * (1 + sl_pct), 8)
            new_tp = round(ref_price * (1 - tp_pct), 8)
        else:
            continue

        sl_delta = abs(new_sl - current_sl) / current_sl if current_sl > 0 else 1.0
        tp_delta = abs(new_tp - current_tp) / current_tp if current_tp > 0 else 1.0

        needs_sl = sl_delta > ATR_UPDATE_THRESHOLD_PCT
        needs_tp = tp_delta > ATR_UPDATE_THRESHOLD_PCT

        ref_label = f"cur ${ref_price:.6f}" if current_price > 0 else f"entry ${entry_price:.6f} (no cur)"
        entry_label = f"entry ${entry_price:.6f}"

        print(f"[POSITION] {token} {direction}")
        print(f"  Prices  : {entry_label} | current={ref_label}")
        print(f"  ATR     : {atr:.6f} ({atr_pct*100:.3f}%) | k={k}")
        print(f"  SL      : old={current_sl:.6f} new={new_sl:.6f} delta={sl_delta*100:.3f}% {'✅ NEEDS_UPDATE' if needs_sl else 'ok'}")
        print(f"  TP      : old={current_tp:.6f} new={new_tp:.6f} delta={tp_delta*100:.3f}% {'✅ NEEDS_UPDATE' if needs_tp else 'ok'}")

        if needs_sl or needs_tp:
            updates_total += 1
            print(f"  >>> FLAGS: needs_sl={needs_sl} needs_tp={needs_tp}")
        print()

    print(f"=== Summary: {updates_total}/{len(positions)} positions need SL and/or TP update ===")

if __name__ == '__main__':
    main()
