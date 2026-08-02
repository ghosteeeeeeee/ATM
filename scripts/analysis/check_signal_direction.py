#!/usr/bin/env python3
"""For each accel-300- losing trade, check if price was actually below EMA300
at signal time. If price was above EMA300, the signal direction was WRONG.
"""
import sqlite3
import json
from datetime import datetime, timezone

db = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = db.cursor()

# trades from T's list (losses only)
trades = [
    # (id, token, dir, entry, exit, signal, open_time)
    (12196, 'UMA',  'SHORT', 0.389650, 0.392890, 'accel-300-', '2026-06-24 23:31:06'),
    (12194, 'ASTER', 'SHORT', 0.613460, 0.617120, 'accel-300-', '2026-06-24 22:08:07'),
    (12191, 'TAO',   'SHORT', 217.540,  220.200,  'accel-300-', '2026-06-24 21:43:06'),
    (12195, 'FET',   'SHORT', 0.172380, 0.173630, 'accel-300-', '2026-06-24 22:17:06'),
    (12190, 'ENS',   'SHORT', 4.3127,   4.3540,   'accel-300-', '2026-06-24 21:13:07'),
    (12188, 'ONDO',  'SHORT', 0.3080,   0.31133,  'accel-300-', '2026-06-24 20:34:08'),
    (12187, 'ENS',   'SHORT', 4.3064,   4.3442,   'accel-300-', '2026-06-24 20:16:07'),
    (12172, 'AAVE',  'SHORT', 74.03,    74.727,   'accel-300-', '2026-06-24 13:46:07'),
    (12166, 'MERL',  'SHORT', 0.019872, 0.020126, 'accel-300-', '2026-06-24 10:48:07'),
    (12159, 'MERL',  'SHORT', 0.020133, 0.020403, 'accel-300-', '2026-06-24 04:26:17'),
    (12163, 'MERL',  'SHORT', 0.020297, 0.020328, 'accel-300-', '2026-06-24 08:58:07'),
    (12189, 'UMA',   'SHORT', 0.389390, 0.391970, 'accel-300-', '2026-06-24 20:41:07'),
]

# EMA period
PERIOD = 300
MULT = 2.0 / (PERIOD + 1)

print(f"{'ID':<6} {'TOK':<6} {'OPEN_TIME':<18} {'PRICE':<12} {'EMA300':<12} {'GAP%':<8} {'VALID?':<8} {'NOTE'}")
print("=" * 110)

wrong_direction = []
for tid, tok, direction, entry, exit_px, sig, open_time_str in trades:
    # Parse timestamp
    dt = datetime.strptime(open_time_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    target = int(dt.timestamp())

    # Get 600 prices leading up to and including the trade time
    c.execute('SELECT timestamp, price FROM price_history WHERE token=? AND timestamp <= ? ORDER BY timestamp DESC LIMIT 600', (tok, target))
    rows = list(reversed(c.fetchall()))
    if len(rows) < PERIOD:
        print(f"{tid:<6} {tok:<6} {open_time_str:<18} {'NO DATA':<12}")
        continue
    closes = [r[1] for r in rows]

    # Compute EMA
    ema = None
    for px in closes:
        if ema is None:
            ema = px
        else:
            ema = px * MULT + ema * (1 - MULT)

    last_price = closes[-1]
    gap = (last_price - ema) / ema * 100
    above = "ABOVE" if last_price > ema else "BELOW"

    # For a SHORT, valid requires price BELOW EMA
    if direction == 'SHORT':
        valid = "VALID" if last_price < ema else "WRONG_DIR"
    else:
        valid = "VALID" if last_price > ema else "WRONG_DIR"

    note = ""
    if valid == "WRONG_DIR":
        wrong_direction.append((tid, tok, direction, last_price, ema, gap, above))
        note = f"  <-- {above} EMA, signal said {direction}, INVALID"
    print(f"{tid:<6} {tok:<6} {open_time_str:<18} {last_price:<12.6f} {ema:<12.6f} {gap:<+8.3f} {valid:<8} {note}")

print()
print("=" * 110)
print(f"TRADES WITH WRONG DIRECTION: {len(wrong_direction)} of {len(trades)}")
for tid, tok, d, p, e, g, ab in wrong_direction:
    print(f"  #{tid} {tok} {d}: price {p:.6f} {ab} EMA {e:.6f} (gap={g:+.3f}%)")
