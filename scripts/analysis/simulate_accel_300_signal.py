#!/usr/bin/env python3
"""Simulate the accel_300 detector and find the actual signal bar for each losing trade."""
import sqlite3
from datetime import datetime, timezone

db = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = db.cursor()

trades = [
    (12196, 'UMA',  'SHORT', 0.389650, '2026-06-24 23:31:06'),
    (12194, 'ASTER', 'SHORT', 0.613460, '2026-06-24 22:08:07'),
    (12191, 'TAO',   'SHORT', 217.540,  '2026-06-24 21:43:06'),
    (12195, 'FET',   'SHORT', 0.172380, '2026-06-24 22:17:06'),
    (12190, 'ENS',   'SHORT', 4.3127,   '2026-06-24 21:13:07'),
    (12188, 'ONDO',  'SHORT', 0.3080,   '2026-06-24 20:34:08'),
    (12187, 'ENS',   'SHORT', 4.3064,   '2026-06-24 20:16:07'),
    (12172, 'AAVE',  'SHORT', 74.03,    '2026-06-24 13:46:07'),
    (12166, 'MERL',  'SHORT', 0.019872, '2026-06-24 10:48:07'),
    (12159, 'MERL',  'SHORT', 0.020133, '2026-06-24 04:26:17'),
    (12189, 'UMA',   'SHORT', 0.389390, '2026-06-24 20:41:07'),
]

# Detector params (from hermes_constants.py)
PERIOD = 300
PERSISTENCE_BARS = 2
LOOKBACK = 30
LOOKBACK_SHORT = 500
MIN_GAP_PCT_SHORT = 0.25
MIN_GAP_PCT_LONG = 0.20
MULT = 2.0 / (PERIOD + 1)

def ema_series(values, period):
    if len(values) < period:
        return [None] * len(values)
    k = 2.0 / (period + 1)
    result = [None] * (period - 1)
    ema = None
    for i, v in enumerate(values):
        if ema is None:
            ema = v
        else:
            ema = v * k + ema * (1 - k)
        if i >= period - 1:
            result.append(ema)
    return result

def find_latest_below_bar(closes, ema300, start_idx):
    """Find the latest bar where price was below EMA, starting from start_idx and going backward."""
    for i in range(start_idx, PERIOD - 1, -1):
        if ema300[i] is None: continue
        if closes[i] < ema300[i]:
            return i
    return None

def find_cross_bar(closes, ema300, signal_idx, direction):
    """Find the cross bar (most recent transition to direction)."""
    for j in range(signal_idx, PERIOD - 1, -1):
        if j <= 0: break
        if ema300[j] is None or ema300[j-1] is None: continue
        if direction == 'SHORT' and closes[j] < ema300[j] and closes[j-1] >= ema300[j-1]:
            return j
        if direction == 'LONG' and closes[j] > ema300[j] and closes[j-1] <= ema300[j-1]:
            return j
    return None

for tid, tok, direction, entry, open_time_str in trades:
    dt = datetime.strptime(open_time_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    target = int(dt.timestamp())

    c.execute('SELECT timestamp, price FROM price_history WHERE token=? AND timestamp <= ? ORDER BY timestamp DESC LIMIT 800', (tok, target))
    rows = list(reversed(c.fetchall()))
    if len(rows) < PERIOD + PERSISTENCE_BARS:
        print(f"#{tid} {tok}: insufficient data")
        continue
    closes = [r[1] for r in rows]
    ema300 = ema_series(closes, PERIOD)
    if ema300[-1] is None:
        continue

    last_idx = len(closes) - 1
    last_price = closes[last_idx]
    last_ema = ema300[last_idx]
    last_gap = (last_price - last_ema) / last_ema * 100
    last_above = last_price > last_ema

    # Find the latest bar where price was below EMA (candidate signal bar for SHORT)
    latest_below_idx = find_latest_below_bar(closes, ema300, last_idx)

    if latest_below_idx is None:
        print(f"#{tid} {tok} SHORT: no below-EMA bar in window. Last bar: price={last_price:.6f} EMA={last_ema:.6f} gap={last_gap:+.3f}% ({'ABOVE' if last_above else 'BELOW'})")
        continue

    bars_before_latest = last_idx - latest_below_idx
    sig_price = closes[latest_below_idx]
    sig_ema = ema300[latest_below_idx]
    sig_gap = (sig_price - sig_ema) / sig_ema * 100
    sig_time = datetime.fromtimestamp(rows[latest_below_idx][0], tz=timezone.utc)

    # Check persistence: was price below EMA at sig_idx-1 and sig_idx?
    persist_below = True
    for j in range(max(0, latest_below_idx - PERSISTENCE_BARS + 1), latest_below_idx + 1):
        if closes[j] >= ema300[j]:
            persist_below = False
            break

    # Check new min gap threshold (SHORT = 0.25, LONG = 0.20)
    min_gap_ok = abs(sig_gap) >= MIN_GAP_PCT_SHORT

    # Find cross_bar
    cross_idx = find_cross_bar(closes, ema300, latest_below_idx, 'SHORT')
    cross_time = datetime.fromtimestamp(rows[cross_idx][0], tz=timezone.utc) if cross_idx is not None else None
    bars_since_cross = latest_below_idx - cross_idx if cross_idx is not None else 999

    # Stale check
    stale_ok = bars_before_latest <= 400

    signal_passes = (persist_below and stale_ok and min_gap_ok)

    print(f"#{tid} {tok} {direction} entry={entry:.6f}")
    print(f"  Last bar (idx={last_idx}): price={last_price:.6f} EMA={last_ema:.6f} gap={last_gap:+.3f}% {'ABOVE' if last_above else 'BELOW'}")
    print(f"  Signal bar candidate: idx={latest_below_idx} ({bars_before_latest} bars ago) time={sig_time.strftime('%H:%M:%S')}")
    print(f"    price={sig_price:.6f} EMA={sig_ema:.6f} gap={sig_gap:+.3f}% BELOW")
    print(f"    persist_below_past_2_bars: {persist_below}")
    print(f"    abs_gap {abs(sig_gap):.3f}% >= MIN_GAP_PCT_SHORT 0.25: {min_gap_ok}")
    print(f"    cross_bar: idx={cross_idx} time={cross_time.strftime('%H:%M:%S') if cross_time else 'None'}")
    print(f"    bars_since_cross: {bars_since_cross}")
    print(f"    bars_from_latest check (must be <=400): {stale_ok} (value={bars_before_latest})")
    print(f"    SIGNAL WOULD PASS: {signal_passes}")
    print()
