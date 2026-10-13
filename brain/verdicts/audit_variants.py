#!/usr/bin/env python3
"""Variant sweep to match claimed 182 / 57.1% / +60.68% exactly."""
import sqlite3
from datetime import datetime, timezone

SIG_DB = '/root/.hermes/data/signals_hermes_runtime.db'
CAND_DB = '/root/.hermes/data/candles.db'

sc = sqlite3.connect(SIG_DB)
sig_rows = sc.execute("""
SELECT token, direction, created_at, source, price
FROM signals
WHERE decision IN ('PENDING','EXPIRED')
  AND created_at > datetime('now', '-7 days')
  AND source NOT LIKE '%,%'
  AND price > 0
ORDER BY token, direction, created_at
""").fetchall()
sc.close()

def to_epoch(ts_str):
    dt = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    return int(dt.timestamp())

groups = {}
for token, direction, created_at, source, price in sig_rows:
    groups.setdefault((token, direction), []).append({'t': to_epoch(created_at), 'source': source, 'price': price})
for k in groups:
    groups[k].sort(key=lambda x: x['t'])

cc = sqlite3.connect(f"file:{CAND_DB}?mode=ro", uri=True, timeout=60)

def c_at_or_before(token, t):
    return cc.execute("SELECT ts, close FROM candles_1m WHERE token=? AND ts<=? ORDER BY ts DESC LIMIT 1", (token, t)).fetchone()

def c_at_or_after(token, t):
    return cc.execute("SELECT ts, close FROM candles_1m WHERE token=? AND ts>=? ORDER BY ts ASC LIMIT 1", (token, t)).fetchone()

WINDOW_MIN, THRESH, HOLD = 90, 4, 60

bypasses = []
for (token, direction), fires in groups.items():
    if len(fires) < THRESH:
        continue
    for i, f in enumerate(fires):
        wstart = f['t'] - WINDOW_MIN*60
        inwin = [g for g in fires[:i+1] if g['t'] >= wstart]
        if len(inwin) >= THRESH:
            bypasses.append({'token': token, 'direction': direction, 'bypass': f,
                             'first': inwin[0], 'count': len(inwin)})
print(f"bypass events: {len(bypasses)}")

def evaluate(name, entry_fn, exit_fn):
    trades = []
    for b in bypasses:
        token, direction = b['token'], b['direction']
        t = b['bypass']['t']
        ep = entry_fn(token, t, b)
        xp = exit_fn(token, t)
        if ep is None or xp is None:
            continue
        ret = (xp - ep) / ep * 100.0
        if direction == 'SHORT':
            ret = -ret
        trades.append(ret)
    n = len(trades)
    if not n:
        print(f"{name}: 0 trades")
        return
    wins = sum(1 for r in trades if r > 0)
    print(f"{name}: n={n} wins={wins} WR={wins/n*100:.1f}% total={sum(trades):+.2f}% avg={sum(trades)/n:+.3f}%")

def entry_candle(token, t, b):
    r = c_at_or_before(token, t)
    return r[1] if r else None

def entry_sigprice(token, t, b):
    return b['bypass']['price']

def exit_c_at_or_before(token, t):
    r = c_at_or_before(token, t + HOLD*60)
    return r[1] if r else None

def exit_c_at_or_after(token, t):
    r = c_at_or_after(token, t + HOLD*60)
    return r[1] if r else None

def exit_c_at_or_before_containing(token, t):
    # candle whose ts is exactly t+60min boundary or the one covering it
    r = c_at_or_before(token, t + HOLD*60 - 1)
    return r[1] if r else None

evaluate('entry=candle_close, exit=candle_close@t+60(<=)', entry_candle, exit_c_at_or_before)
evaluate('entry=signal_price, exit=candle_close@t+60(<=)', entry_sigprice, exit_c_at_or_before)
evaluate('entry=candle_close, exit=candle_close@t+60(>=)', entry_candle, exit_c_at_or_after)
evaluate('entry=signal_price, exit=candle_close@t+60(>=)', entry_sigprice, exit_c_at_or_after)
evaluate('entry=candle_close, exit=candle@t+59(<=)', entry_candle, exit_c_at_or_before_containing)
evaluate('entry=signal_price, exit=candle@t+59(<=)', entry_sigprice, exit_c_at_or_before_containing)

# staleness-filtered variants (signal price must be close to candle price)
for max_stale_pct in (0.5, 1.0, 2.0):
    trades = []
    for b in bypasses:
        token, direction = b['token'], b['direction']
        t = b['bypass']['t']
        r = c_at_or_before(token, t)
        if r is None:
            continue
        stale = abs(b['bypass']['price'] - r[1]) / r[1] * 100
        if stale > max_stale_pct:
            continue
        xp = exit_c_at_or_before(token, t)
        if xp is None:
            continue
        ret = (xp - r[1]) / r[1] * 100.0
        if direction == 'SHORT':
            ret = -ret
        trades.append(ret)
    n = len(trades)
    if n:
        wins = sum(1 for r in trades if r > 0)
        print(f"stale<={max_stale_pct}%: n={n} WR={wins/n*100:.1f}% total={sum(trades):+.2f}% avg={sum(trades)/n:+.3f}%")

cc.close()
