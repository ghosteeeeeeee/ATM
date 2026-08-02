#!/usr/bin/env python3
"""Comprehensive check: for EVERY accel-300- trade in last 24h, verify if price was
actually below EMA300 at signal time."""
import psycopg2
import sqlite3
import sys
from datetime import datetime, timezone

conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
cur = conn.cursor()

# Get all accel-300- trades in last 24h
cur.execute("""
    SELECT id, token, direction, entry_price, leverage, pnl_usdt, pnl_pct,
           open_time, close_time, exit_reason
    FROM trades
    WHERE signal LIKE 'accel%' AND close_time > NOW() - INTERVAL '7 days'
    ORDER BY open_time DESC
""")
trades = cur.fetchall()
print(f"Total accel-300 trades (last 7d): {len(trades)}")
conn.close()

# Connect to prices
price_db = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
price_cur = price_db.cursor()

# EMA params
PERIOD = 300
MULT = 2.0 / (PERIOD + 1)

def compute_ema(closes):
    if len(closes) < PERIOD:
        return None
    ema = sum(closes[:PERIOD]) / PERIOD
    for px in closes[PERIOD:]:
        ema = px * MULT + ema * (1 - MULT)
    return ema

def check_trade(trade):
    tid, tok, direction, entry, lev, pnl_usdt, pnl_pct, open_time, close_time, exit_reason = trade
    # Get unix timestamp of open_time
    ts = int(open_time.timestamp())
    # Get 700 1m prices up to and including this time
    price_cur.execute("""
        SELECT timestamp, price FROM (
            SELECT timestamp, price FROM price_history
            WHERE token=? AND timestamp <= ?
            ORDER BY timestamp DESC LIMIT 700
        ) sub ORDER BY timestamp ASC
    """, (tok, ts))
    rows = price_cur.fetchall()
    if len(rows) < PERIOD:
        return None
    
    closes = [r[1] for r in rows]
    last_price = closes[-1]
    last_ts = rows[-1][0]
    
    # Compute EMA at each bar
    ema_at_bar = [None] * len(closes)
    ema_val = sum(closes[:PERIOD]) / PERIOD
    ema_at_bar[PERIOD - 1] = ema_val
    for i in range(PERIOD, len(closes)):
        ema_val = closes[i] * MULT + ema_val * (1 - MULT)
        ema_at_bar[i] = ema_val
    
    last_ema = ema_at_bar[-1]
    last_gap = (last_price - last_ema) / last_ema * 100
    last_above = last_price > last_ema
    
    # For SHORT: should be price < EMA (below)
    if direction == 'SHORT':
        valid = last_price < last_ema
    else:
        valid = last_price > last_ema
    
    # Find last below-EMA bar (for SHORT)
    last_below_idx = None
    if direction == 'SHORT':
        for i in range(len(closes) - 1, -1, -1):
            if closes[i] < ema_at_bar[i]:
                last_below_idx = i
                break
    
    bars_stale = (len(closes) - 1 - last_below_idx) if last_below_idx is not None else None
    
    return {
        'tid': tid,
        'tok': tok,
        'direction': direction,
        'entry': entry,
        'pnl_usdt': pnl_usdt,
        'pnl_pct': pnl_pct,
        'lev': lev,
        'last_price': last_price,
        'last_ema': last_ema,
        'last_gap': last_gap,
        'last_above': last_above,
        'valid_at_signal': valid,
        'last_below_idx': last_below_idx,
        'bars_stale': bars_stale,
        'open_time': open_time,
    }

print(f"\n{'ID':<6} {'TOK':<6} {'DIR':<6} {'PnL':<8} {'LIVE_GAP':<10} {'VALID?':<8} {'BARS_STALE':<10} {'NOTE'}")
print("=" * 130)

wrong_dir = 0
stale_but_valid = 0
for t in trades:
    r = check_trade(t)
    if r is None:
        print(f"{t[0]:<6} {t[1]:<6} (insufficient data)")
        continue
    if not r['valid_at_signal']:
        wrong_dir += 1
        note = "*** INVALID: price on WRONG side of EMA"
    elif r['bars_stale'] is not None and r['bars_stale'] > 30:
        stale_but_valid += 1
        note = f"stale: last below-EMA bar was {r['bars_stale']} bars ago"
    else:
        note = "ok"
    outcome = "W" if r['pnl_usdt'] > 0 else "L"
    print(f"{r['tid']:<6} {r['tok']:<6} {r['direction']:<6} "
              f"{outcome} ${r['pnl_usdt']:+.2f} "
              f"{r['last_gap']:+8.3f}%  "
              f"{'YES' if r['valid_at_signal'] else 'NO':<8} "
              f"{str(r['bars_stale']):<10} "
              f"{note}")
print()
print(f"WRONG DIRECTION (price on wrong side of EMA at signal time): {wrong_dir}/{len(trades)}")
print(f"VALID but STALE (last below-EMA bar >30 bars ago): {stale_but_valid}/{len(trades)}")

price_db.close()