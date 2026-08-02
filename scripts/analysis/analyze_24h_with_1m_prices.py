#!/usr/bin/env python3
"""Final deep analysis using 1m price_history from signals_hermes.db."""
import psycopg2
import json
import gzip
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict

# PG conn
conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
cur = conn.cursor()

cur.execute("""
    SELECT id, token, direction, entry_price, exit_price, pnl_usdt, pnl_pct,
           exit_reason, open_time, close_time, signal, confidence, leverage,
           stop_loss, target, highest_price, _signal_metadata
    FROM trades
    WHERE status='closed' AND close_time > NOW() - INTERVAL '24 hours'
    ORDER BY open_time ASC
""")
trades = []
for r in cur.fetchall():
    trades.append({
        'id': r[0], 'token': r[1], 'dir': r[2],
        'entry': float(r[3]), 'exit': float(r[4]),
        'pnl': float(r[5]), 'pnl_pct': float(r[6]),
        'exit_reason': r[7], 'open_time': r[8], 'close_time': r[9],
        'signal': r[10], 'confidence': r[11], 'leverage': r[12],
        'sl': float(r[13]) if r[13] else None,
        'target': float(r[14]) if r[14] else None,
        'highest': float(r[15]) if r[15] else None,
        'meta': r[16] or {},
    })

# 1m price DB
price_db = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
price_cur = price_db.cursor()

# 1) 1m PRICE PATH FOR EVERY TRADE
print("=" * 80)
print("1m PRICE ACTION DURING TRADE — for every trade")
print("=" * 80)
print("  W/L id    token   dir   entry    exit      MFE      MAE    maxFavClose  endFav  pnl       dur")
print("  --- ------ ------ ---- -------- -------- -------- -------- ----------- -------- --------- ----")

for t in trades:
    open_unix = int(t['open_time'].timestamp())
    close_unix = int(t['close_time'].timestamp())
    price_cur.execute("""
        SELECT timestamp, price FROM price_history
        WHERE token=? AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp
    """, (t['token'], open_unix - 60, close_unix + 60))
    rows = price_cur.fetchall()
    if not rows:
        # Try with 1m ohlcv
        price_cur.execute("""
            SELECT name FROM sqlite_master WHERE type='table' AND name='ohlcv_1m'
        """)
        # fallback later
        print(f"  ?  #{t['id']:5d} {t['token']:6s} {t['dir']:5s} - NO PRICE DATA for {t['token']} between {open_unix} and {close_unix}")
        continue
    in_trade = [r for r in rows if open_unix <= r[0] <= close_unix]
    if not in_trade:
        print(f"  ?  #{t['id']:5d} {t['token']:6s} {t['dir']:5s} - in_trade empty (data gap)")
        continue
    prices = [r[1] for r in in_trade]
    if t['dir'] == 'LONG':
        mfe_pct = (max(prices) - t['entry']) / t['entry'] * 100
        mae_pct = (t['entry'] - min(prices)) / t['entry'] * 100
        favors = [(p - t['entry']) / t['entry'] * 100 for p in prices]
    else:
        mfe_pct = (t['entry'] - min(prices)) / t['entry'] * 100
        mae_pct = (max(prices) - t['entry']) / t['entry'] * 100
        favors = [(t['entry'] - p) / t['entry'] * 100 for p in prices]
    max_fav = max(favors)
    end_fav = favors[-1]
    marker = "W " if t['pnl'] > 0 else "L "
    flag = ""
    if max_fav > 0.5 and t['pnl'] < 0:
        flag = "*"
    dur = (t['close_time']-t['open_time']).total_seconds()
    print(f"  {marker} #{t['id']:5d} {t['token']:6s} {t['dir']:5s} "
          f"{t['entry']:8.5f} {t['exit']:8.5f} "
          f"{mfe_pct:6.2f}% {mae_pct:6.2f}% {max_fav:9.2f}% {end_fav:7.2f}% "
          f"${t['pnl']:+.2f} {dur:6.0f}s {flag}")

# 2) ASTER 10s BUG — DEEP DIVE
print("\n" + "=" * 80)
print("ASTER 10-SECOND BUG — full price history 5min before/after both trades")
print("=" * 80)
for tid in [12193, 12194]:
    t = next(t for t in trades if t['id'] == tid)
    open_unix = int(t['open_time'].timestamp())
    close_unix = int(t['close_time'].timestamp())
    print(f"\n  #{tid} {t['token']} {t['dir']} | open={t['open_time']} close={t['close_time']}")
    print(f"  entry={t['entry']} exit={t['exit']} SL={t['sl']} highest_recorded={t['highest']}")
    price_cur.execute("""
        SELECT timestamp, price FROM price_history
        WHERE token='ASTER' AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp
    """, (open_unix - 300, close_unix + 60))
    rows = price_cur.fetchall()
    print(f"  Got {len(rows)} price points")
    for r in rows:
        dt = datetime.fromtimestamp(r[0])
        in_trade = "*" if open_unix <= r[0] <= close_unix else " "
        flag = ""
        if t['dir'] == 'SHORT':
            if r[1] > t['entry']:
                flag = "↑against"
            elif r[1] < t['entry']:
                flag = "↓in-favor"
        print(f"    {in_trade} {dt.strftime('%H:%M:%S')}  {r[1]:.5f}  {flag}")

# 3) CONSECUTIVE LOSSES — what changed
print("\n" + "=" * 80)
print("THE LOSING STREAK: trades #12187-12195 (8 losses with only 1 win in middle)")
print("=" * 80)
loss_streak = [t for t in trades if t['id'] >= 12186]
for t in loss_streak:
    open_unix = int(t['open_time'].timestamp())
    close_unix = int(t['close_time'].timestamp())
    price_cur.execute("""
        SELECT timestamp, price FROM price_history
        WHERE token=? AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp
    """, (t['token'], open_unix, close_unix))
    rows = price_cur.fetchall()
    if not rows:
        print(f"  #{t['id']} {t['token']:6s} {t['dir']:5s} - NO PRICE DATA")
        continue
    prices = [r[1] for r in rows]
    if t['dir'] == 'LONG':
        mfe = (max(prices) - t['entry']) / t['entry'] * 100
        mae = (t['entry'] - min(prices)) / t['entry'] * 100
    else:
        mfe = (t['entry'] - min(prices)) / t['entry'] * 100
        mae = (max(prices) - t['entry']) / t['entry'] * 100
    marker = "W" if t['pnl'] > 0 else "L"
    print(f"  {marker} #{t['id']} {t['token']:6s} {t['dir']:5s} entry={t['entry']:.5f} exit={t['exit']:.5f} "
          f"SL={t['sl']:.5f if t['sl'] else 'NONE':.5f} | MFE={mfe:+.2f}% MAE={mae:+.2f}% | pnl=${t['pnl']:+.2f} exit={t['exit_reason']}")

# 4) PRICE FOR BOTH ASTER TRADES — second one had 12612s
print("\n" + "=" * 80)
print("ASTER 12194 (3.5h trade) — did price really stay above SL?")
print("=" * 80)
t = next(t for t in trades if t['id'] == 12194)
open_unix = int(t['open_time'].timestamp())
close_unix = int(t['close_time'].timestamp())
price_cur.execute("""
    SELECT timestamp, price FROM price_history
    WHERE token='ASTER' AND timestamp BETWEEN ? AND ?
    ORDER BY timestamp
""", (open_unix, close_unix))
rows = price_cur.fetchall()
print(f"  {len(rows)} price points. SL = {t['sl']:.5f}")
if rows:
    high_actual = max(r[1] for r in rows)
    low_actual = min(r[1] for r in rows)
    print(f"  Actual high during trade: {high_actual:.5f}  (SL was {t['sl']:.5f}, reached? {high_actual >= t['sl']})")
    print(f"  Actual low during trade:  {low_actual:.5f}")
    print(f"  Entry: {t['entry']:.5f}, Exit: {t['exit']:.5f}")
    # show price path
    n = len(rows)
    sample = rows[::max(1, n//30)]  # 30 points
    print(f"  Price path (sampled):")
    for r in sample:
        dt = datetime.fromtimestamp(r[0])
        marker = "  ENTRY" if abs(r[0] - open_unix) < 5 else ("  EXIT " if abs(r[0] - close_unix) < 5 else "")
        above_sl = "  above SL!" if r[1] >= t['sl'] else ""
        print(f"    {dt.strftime('%H:%M:%S')}  {r[1]:.5f}{above_sl}{marker}")

# 5) For the biggest losses — show full price path
print("\n" + "=" * 80)
print("FULL PRICE PATH — TOP 5 LOSERS (MERL, TAO, ONDO, AAVE, ENS)")
print("=" * 80)
top_loss_tokens = ['MERL', 'TAO', 'ONDO', 'AAVE', 'ENS']
for token in top_loss_tokens:
    tok_trades = [t for t in trades if t['token'] == token and t['pnl'] < 0]
    for t in sorted(tok_trades, key=lambda x: x['pnl'])[:2]:  # worst 2 per token
        open_unix = int(t['open_time'].timestamp())
        close_unix = int(t['close_time'].timestamp())
        price_cur.execute("""
            SELECT timestamp, price FROM price_history
            WHERE token=? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp
        """, (t['token'], open_unix - 600, close_unix + 600))
        rows = price_cur.fetchall()
        if not rows:
            continue
        in_trade = [r for r in rows if open_unix <= r[0] <= close_unix]
        print(f"\n  #{t['id']} {t['token']:6s} {t['dir']:5s} entry={t['entry']:.5f} exit={t['exit']:.5f} SL={t['sl']:.5f}")
        print(f"  Signal: {t['signal']} | exit_reason={t['exit_reason']} | pnl=${t['pnl']:+.2f}")
        if not in_trade:
            print(f"  No in-trade data points")
            continue
        # Show every 10th point + entry + exit + high/low
        n = len(in_trade)
        show_every = max(1, n // 15)
        for i, r in enumerate(in_trade):
            if i % show_every == 0 or i == n-1:
                dt = datetime.fromtimestamp(r[0])
                p = r[1]
                if t['dir'] == 'SHORT':
                    if p > t['entry']:
                        flag = " ABOVE entry"
                    elif p < t['entry']:
                        flag = " below entry"
                    if p >= t['sl']:
                        flag += " [AT/ABOVE SL!]"
                else:
                    if p > t['entry']:
                        flag = " above entry"
                    elif p < t['entry']:
                        flag = " BELOW entry"
                    if p <= t['sl']:
                        flag += " [AT/BELOW SL!]"
                print(f"    {dt.strftime('%H:%M:%S')}  {p:.6f} {flag}")

# 6) DURATION OF WINNERS VS LOSERS — clean numbers
print("\n" + "=" * 80)
print("DURATION & KEY METRICS — WINNERS vs LOSERS")
print("=" * 80)
for kind, label in [([t for t in trades if t['pnl']>0], "WINNERS"), ([t for t in trades if t['pnl']<0], "LOSERS")]:
    durs = [(t['close_time']-t['open_time']).total_seconds() for t in kind]
    pnls = [t['pnl_pct'] for t in kind]
    confs = [t['confidence'] for t in kind if t['confidence']]
    print(f"\n  {label} (n={len(kind)}):")
    print(f"    avg dur: {sum(durs)/len(durs):.0f}s | median: {sorted(durs)[len(durs)//2]:.0f}s")
    print(f"    avg pnl_pct: {sum(pnls)/len(pnls):+.2f}%")
    if confs:
        print(f"    avg confidence: {sum(confs)/len(confs):.1f}")
    # Sub-10min
    sub10 = [t for t in kind if (t['close_time']-t['open_time']).total_seconds() < 600]
    print(f"    Sub-10min: {len(sub10)}/{len(kind)}")
    sub5 = [t for t in kind if (t['close_time']-t['open_time']).total_seconds() < 60]
    print(f"    Sub-1min: {len(sub5)}/{len(kind)}")

# 7) WHEN DO WE LOSE? Pre vs during vs post streak
print("\n" + "=" * 80)
print("STREAK TIMING — when did wins become losses?")
print("=" * 80)
cum = 0
peak_cum = 0
print("  Time     | Cum PnL | This trade | Win/Loss | After this...")
for t in trades:
    cum += t['pnl']
    arrow = ""
    if cum > peak_cum:
        peak_cum = cum
        arrow = " <-- NEW PEAK"
    if t['pnl'] < 0 and cum < peak_cum - 0.30:
        arrow += " *** GIVING BACK PEAK ***"
    print(f"  {t['close_time'].strftime('%m-%d %H:%M')} | ${cum:+.2f}  | ${t['pnl']:+.2f}    | "
          f"{'W' if t['pnl']>0 else 'L'} {t['token']:6s} {t['dir']:5s}{arrow}")

# 8) THE 0.7-0.8% pnl_pct clustering — is profit-monster taking too much off the table?
print("\n" + "=" * 80)
print("PROFIT-MONSTER PNL PCT DISTRIBUTION — are we clipping at 0.7-0.8%?")
print("=" * 80)
wins = [t for t in trades if t['pnl'] > 0]
from collections import Counter
pnl_pct_buckets = Counter()
for t in wins:
    bucket = round(t['pnl_pct'], 1)
    pnl_pct_buckets[bucket] += 1
for pct in sorted(pnl_pct_buckets.keys()):
    print(f"  +{pct:.1f}%  : {pnl_pct_buckets[pct]} trades")
print(f"  max winner pnl_pct: {max(t['pnl_pct'] for t in wins):.2f}%")

# 9) Highest record vs actual 1m data
print("\n" + "=" * 80)
print("DB 'highest_price' field vs 1m ACTUAL high — is highest_price even accurate?")
print("=" * 80)
for t in trades:
    open_unix = int(t['open_time'].timestamp())
    close_unix = int(t['close_time'].timestamp())
    price_cur.execute("""
        SELECT MAX(price), MIN(price) FROM price_history
        WHERE token=? AND timestamp BETWEEN ? AND ?
    """, (t['token'], open_unix, close_unix))
    row = price_cur.fetchone()
    if not row or row[0] is None:
        continue
    actual_high, actual_low = row
    db_high = t['highest']
    if db_high is None: continue
    diff_pct = (db_high - actual_high) / actual_high * 100 if actual_high else 0
    flag = "MISMATCH!" if abs(diff_pct) > 1 else ""
    print(f"  #{t['id']} {t['token']:6s} {t['dir']:5s} | DB highest={db_high:.5f} actual_high={actual_high:.5f} diff={diff_pct:+.2f}% {flag}")

conn.close()
price_db.close()
