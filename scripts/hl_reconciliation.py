#!/usr/bin/env python3
"""
hl_reconciliation.py — Automated HL reconciliation post-mortem.

Runs every 4 hours via systemd timer. Fetches HL fills, compares against
DB trades, auto-corrects PnL divergences > 5%.

Usage:
    python3 scripts/hl_reconciliation.py                  # normal run
    python3 scripts/hl_reconciliation.py --dry            # dry run (no DB writes)
    python3 scripts/hl_reconciliation.py --lookback 24    # custom lookback hours
"""

import sys
import time
import argparse
from collections import defaultdict
from datetime import datetime, timezone, timedelta

sys.path.insert(0, 'scripts')
import psycopg2
from _secrets import BRAIN_DB_DICT
from hyperliquid_exchange import get_trade_history
from hermes_constants import (
    HL_RECONCILIATION_ENABLED,
    HL_RECONCILIATION_DIVERGENCE_THRESHOLD,
    HL_RECONCILIATION_LOOKBACK_HOURS,
    HL_RECONCILIATION_MATCH_WINDOW_MINUTES,
)

DRY = False


def log(msg, level='INFO'):
    ts = datetime.now(timezone.utc).strftime('%H:%M:%S')
    print(f'[{ts}] [{level}] [HL-RECONCILE] {msg}')


def fetch_hl_fills(lookback_hours):
    """Fetch HL fills from the last N hours."""
    start_ms = int((time.time() - lookback_hours * 3600) * 1000)
    history = get_trade_history(start_ms)
    log(f'HL API returned {len(history)} fills')
    return history


def fetch_db_trades(conn, lookback_hours):
    """Fetch closed trades from DB within lookback window."""
    cur = conn.cursor()
    cur.execute("""
        SELECT id, token, direction, entry_price, exit_price,
               pnl_usdt, pnl_pct, amount_usdt, leverage,
               close_time, close_reason, paper, hype_realized_pnl_usdt
        FROM trades
        WHERE status = 'closed'
          AND server = 'Hermes'
          AND close_time > NOW() - INTERVAL '%s hours'
          AND paper = FALSE
        ORDER BY close_time DESC
    """, (lookback_hours,))
    trades = cur.fetchall()
    cur.close()
    return trades


def match_trades_to_fills(trades, hl_fills):
    """Match DB trades to HL close fills by coin + timestamp proximity."""
    # Group HL fills by coin
    fills_by_coin = defaultdict(list)
    for f in hl_fills:
        fills_by_coin[f['coin']].append(f)

    matched = []
    unmatched = []

    for trade in trades:
        trade_id, token, direction, entry_price, exit_price, \
            db_pnl_usdt, db_pnl_pct, amount_usdt, leverage, \
            close_time, close_reason, paper, hl_pnl_existing = trade

        if not close_time:
            unmatched.append(trade)
            continue

        close_ts = close_time.timestamp() * 1000
        coin_fills = fills_by_coin.get(token, [])

        # Find close fills within match window
        match_window = HL_RECONCILIATION_MATCH_WINDOW_MINUTES * 60 * 1000
        close_fills = [
            f for f in coin_fills
            if 'Close' in str(f.get('dir', ''))
            and abs(f['time_ms'] - close_ts) < match_window
        ]

        if close_fills:
            total_pnl = sum(f.get('closed_pnl', 0) or 0 for f in close_fills)
            total_sz = sum(f['sz'] for f in close_fills)
            wavg_exit = sum(f['px'] * f['sz'] for f in close_fills) / total_sz if total_sz > 0 else float(exit_price)

            matched.append({
                'trade': trade,
                'hl_pnl': total_pnl,
                'hl_exit': wavg_exit,
                'hl_fills': close_fills,
            })
        else:
            unmatched.append(trade)

    return matched, unmatched


def compute_divergence(trade, hl_pnl, hl_exit):
    """Compute divergence between DB PnL and HL PnL."""
    trade_id, token, direction, entry_price, exit_price, \
        db_pnl_usdt, db_pnl_pct, amount_usdt, leverage, \
        close_time, close_reason, paper, hl_pnl_existing = trade

    db_val = float(db_pnl_usdt) if db_pnl_usdt else 0
    hl_val = hl_pnl

    if abs(hl_val) < 0.001 and abs(db_val) < 0.001:
        return None  # both zero — no divergence

    divergence = abs(db_val - hl_val)
    pct_div = (divergence / abs(hl_val) * 100) if abs(hl_val) > 0.001 else (
        100.0 if abs(db_val) > 0.001 else 0.0
    )

    # Compute correct pnl_pct from HL exit
    entry_px = float(entry_price)
    if direction == 'SHORT':
        hl_pct = ((entry_px - hl_exit) / entry_px) * 100
    else:
        hl_pct = ((hl_exit - entry_px) / entry_px) * 100

    return {
        'trade_id': trade_id,
        'token': token,
        'direction': direction,
        'close_time': close_time,
        'close_reason': close_reason,
        'db_pnl_usdt': db_val,
        'hl_pnl_usdt': hl_val,
        'divergence_usdt': divergence,
        'divergence_pct': pct_div,
        'hl_pct': hl_pct,
        'hl_exit': hl_exit,
    }


def apply_fixes(conn, divergences):
    """Auto-fix trades with divergence > threshold."""
    cur = conn.cursor()
    fixed = 0

    for div in divergences:
        if div['divergence_pct'] < HL_RECONCILIATION_DIVERGENCE_THRESHOLD:
            continue

        if DRY:
            log(f"  [DRY] Would fix #{div['trade_id']} {div['token']}: "
                f"${div['db_pnl_usdt']:+.4f} -> ${div['hl_pnl_usdt']:+.4f} "
                f"({div['divergence_pct']:.1f}%)")
            continue

        cur.execute("""
            UPDATE trades
            SET pnl_usdt = %s, pnl_pct = %s, exit_price = %s,
                hype_realized_pnl_usdt = %s, hype_realized_pnl_pct = %s
            WHERE id = %s
        """, (
            round(div['hl_pnl_usdt'], 4),
            round(div['hl_pct'], 4),
            div['hl_exit'],
            round(div['hl_pnl_usdt'], 6),
            round(div['hl_pct'], 4),
            div['trade_id'],
        ))
        fixed += 1
        log(f"  FIXED #{div['trade_id']} {div['token']} {div['direction']}: "
            f"${div['db_pnl_usdt']:+.4f} -> ${div['hl_pnl_usdt']:+.4f} "
            f"({div['divergence_pct']:.1f}%)")

    if fixed > 0 and not DRY:
        conn.commit()

    cur.close()
    return fixed


def main():
    global DRY

    parser = argparse.ArgumentParser(description='HL reconciliation post-mortem')
    parser.add_argument('--dry', action='store_true', help='Dry run (no DB writes)')
    parser.add_argument('--lookback', type=int, default=HL_RECONCILIATION_LOOKBACK_HOURS,
                        help=f'Lookback hours (default: {HL_RECONCILIATION_LOOKBACK_HOURS})')
    args = parser.parse_args()

    DRY = args.dry

    if not HL_RECONCILIATION_ENABLED:
        log('HL_RECONCILIATION_ENABLED is False — skipping', 'WARN')
        return

    start = time.time()
    mode = 'DRY RUN' if DRY else 'LIVE'
    log(f'Starting reconciliation ({mode}, lookback={args.lookback}h)')

    # Fetch data
    hl_fills = fetch_hl_fills(args.lookback + 2)  # extra 2h buffer for matching
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    db_trades = fetch_db_trades(conn, args.lookback)

    log(f'HL fills: {len(hl_fills)}, DB trades: {len(db_trades)}')

    # Match and compare
    matched, unmatched = match_trades_to_fills(db_trades, hl_fills)
    log(f'Matched: {len(matched)}, Unmatched (no HL fill): {len(unmatched)}')

    # Compute divergences
    divergences = []
    for m in matched:
        div = compute_divergence(m['trade'], m['hl_pnl'], m['hl_exit'])
        if div and div['divergence_pct'] > 1:  # log anything > 1%
            divergences.append(div)

    log(f'Divergences >1%: {len(divergences)}')

    # Apply fixes
    fixed = apply_fixes(conn, divergences)
    warnings = [d for d in divergences
                if 1 <= d['divergence_pct'] < HL_RECONCILIATION_DIVERGENCE_THRESHOLD]

    # Summary
    elapsed = time.time() - start
    log(f'Complete: {fixed} fixed, {len(warnings)} warnings, {elapsed:.1f}s')

    if warnings:
        log('Warnings (2-5% divergence — investigate manually):', 'WARN')
        for w in warnings:
            log(f"  #{w['trade_id']} {w['token']} {w['direction']}: "
                f"${w['db_pnl_usdt']:+.4f} vs HL ${w['hl_pnl_usdt']:+.4f} "
                f"({w['divergence_pct']:.1f}%)", 'WARN')

    conn.close()


if __name__ == '__main__':
    main()
