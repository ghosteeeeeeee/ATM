#!/usr/bin/env python3
"""Independent audit reproduction of 90m/4 temporal confluence backtest."""
import sqlite3, math, statistics, json
from datetime import datetime, timezone

SIG_DB = '/root/.hermes/data/signals_hermes_runtime.db'
CAND_DB = '/root/.hermes/data/candles.db'

# ---------- load signals ----------
sc = sqlite3.connect(SIG_DB)
sig_rows = sc.execute("""
SELECT token, direction, created_at, source, price, signal_type
FROM signals
WHERE decision IN ('PENDING','EXPIRED')
  AND created_at > datetime('now', '-7 days')
  AND source NOT LIKE '%,%%'
  AND price > 0
ORDER BY token, direction, created_at
""").fetchall()
sc.close()
print(f"base signals: {len(sig_rows)}")

def to_epoch(ts_str):
    dt = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    return int(dt.timestamp())

groups = {}
for token, direction, created_at, source, price, sig_type in sig_rows:
    groups.setdefault((token, direction), []).append({
        't': to_epoch(created_at),
        'ts': created_at,
        'source': source,
        'price': price,
        'signal_type': sig_type,
    })
for k in groups:
    groups[k].sort(key=lambda x: x['t'])

print(f"groups (token,direction): {len(groups)}")

# ---------- candle helper ----------
cc = sqlite3.connect(f"file:{CAND_DB}?mode=ro", uri=True, timeout=60)
cc.execute("PRAGMA query_only=ON")

def candle_price(token, t, how='close'):
    """Return (price, actual_ts) for candle whose ts <= t, nearest."""
    r = cc.execute(f"SELECT ts, close FROM candles_1m WHERE token=? AND ts<=? ORDER BY ts DESC LIMIT 1", (token, t)).fetchone()
    if r is None:
        return None, None
    return r[1], r[0]

def candle_forward(token, t_entry, hold_min=60):
    """Return (entry_close, exit_close) using candle closes at t_entry and t_entry+hold."""
    e = cc.execute("SELECT ts, close FROM candles_1m WHERE token=? AND ts<=? ORDER BY ts DESC LIMIT 1", (token, t_entry)).fetchone()
    if e is None:
        return None, None, None
    # find the candle closest to t_entry+hold (<= or >=)
    xt = t_entry + hold_min*60
    x = cc.execute("SELECT ts, close FROM candles_1m WHERE token=? AND ts<=? ORDER BY ts DESC LIMIT 1", (token, xt)).fetchone()
    if x is None:
        return e[1], None, e[0]
    return e[1], x[1], e[0]

# ---------- bypass detection ----------
WINDOW_MIN = 90
THRESH = 4
HOLD = 60

def find_clusters(fires, mode):
    """mode 'noreset': every fire with >=THRESH fires in trailing window is a bypass.
       mode 'reset': after a bypass, counter resets."""
    bypasses = []
    if mode == 'noreset':
        for i, f in enumerate(fires):
            wstart = f['t'] - WINDOW_MIN*60
            cnt = 0
            first_in_window = None
            for j in range(i, -1, -1):
                if fires[j]['t'] >= wstart:
                    cnt += 1
                    first_in_window = fires[j]
                else:
                    break
            if cnt >= THRESH:
                # first fire in window = earliest fire in [wstart, f.t]
                first_t = first_in_window['t']
                first_price = first_in_window['price']
                bypasses.append({'bypass': f, 'first': first_in_window, 'count': cnt})
    else:  # reset
        count = 0
        first_fire = None
        for f in fires:
            if first_fire is None or f['t'] - first_fire['t'] > WINDOW_MIN*60:
                count = 0
                first_fire = None
            count += 1
            if first_fire is None:
                first_fire = f
            if count >= THRESH:
                bypasses.append({'bypass': f, 'first': first_fire, 'count': count})
                count = 0
                first_fire = None
    return bypasses

for mode in ('noreset', 'reset'):
    trades = []
    for (token, direction), fires in groups.items():
        if len(fires) < THRESH:
            continue
        for b in find_clusters(fires, mode):
            bf = b['bypass']
            ec, xc, ets = candle_forward(token, bf['t'], HOLD)
            if ec is None or xc is None:
                continue
            # skip if candle at entry is more than 5 min stale relative to signal
            ret = (xc - ec) / ec * 100.0
            if direction == 'SHORT':
                ret = -ret
            trades.append({'token': token, 'direction': direction, 'bypass_t': bf['t'],
                           'first_t': b['first']['t'], 'count': b['count'],
                           'sig_price': bf['price'], 'first_sig_price': b['first']['price'],
                           'entry_close': ec, 'exit_close': xc, 'ret': ret})
    n = len(trades)
    if n:
        wins = sum(1 for t in trades if t['ret'] > 0)
        total = sum(t['ret'] for t in trades)
        avg = total / n
        print(f"mode={mode}: trades={n} wins={wins} WR={wins/n*100:.1f}% total={total:+.2f}% avg={avg:+.3f}%")
    else:
        print(f"mode={mode}: trades=0")

cc.close()
