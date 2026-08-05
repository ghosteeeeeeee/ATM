#!/usr/bin/env python3
"""Trace regime slope for all active tokens in candles.db.
Usage: python3 /root/.hermes/skills/hermes-signal-debugging/scripts/accel_300_regime_trace.py
"""
import sqlite3, statistics
from datetime import datetime

CANDLE_DB = '/root/.hermes/data/candles.db'
tokens = ['XLM', 'ONDO', 'GRASS', 'GALA', 'BRETT', 'BTC', 'ETH', 'SOL', 'DOGE']

print("=== Regime slope + LONG blocking status ===\n")
for token in tokens:
    conn = sqlite3.connect(CANDLE_DB)
    c = conn.cursor()
    c.execute("SELECT close, ts FROM candles_1m WHERE token=? ORDER BY ts ASC LIMIT 50", (token,))
    rows = c.fetchall()
    if not rows:
        print(f"{token}: NO candles_1m data")
        conn.close()
        continue

    closes = [r[0] for r in rows]
    ts_list = [r[1] for r in rows]
    n = len(closes)
    mean_x = (n - 1) / 2.0
    mean_y = statistics.mean(closes)
    cov = sum((i - mean_x) * (closes[i] - mean_y) for i in range(n))
    var_x = sum((i - mean_x) ** 2 for i in range(n))
    slope = cov / var_x if var_x > 0 else 0

    newest_ts = ts_list[-1]
    now_ts = int(datetime.now().timestamp())
    age_hours = (now_ts - newest_ts) / 3600

    print(f"{token}: slope={slope:.8f} LONG blocked={'YES' if slope < 0 else 'NO'}")
    print(f"  candle newest: {datetime.fromtimestamp(newest_ts)} | age: {age_hours:.1f}h stale")
    conn.close()