#!/usr/bin/env python3
"""Focused analysis: the winning streak, the losing streak, and ASTER bug."""
import psycopg2
import json
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict, Counter

conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
cur = conn.cursor()
price_db = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
price_cur = price_db.cursor()

cur.execute("""
    SELECT id, token, direction, entry_price, exit_price, pnl_usdt, pnl_pct,
           exit_reason, open_time, close_time, signal, confidence, leverage,
           stop_loss, target, highest_price
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
    })

def get_price_path(t):
    """Get all 1m prices during a trade."""
    open_unix = int(t['open_time'].timestamp())
    close_unix = int(t['close_time'].timestamp())
    price_cur.execute("""
        SELECT timestamp, price FROM price_history
        WHERE token=? AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp
    """, (t['token'], open_unix, close_unix))
    return price_cur.fetchall()

def mfe_mae(t, prices):
    if not prices: return 0, 0
    arr = [p[1] for p in prices]
    if t['dir'] == 'LONG':
        mfe = (max(arr) - t['entry']) / t['entry'] * 100
        mae = (t['entry'] - min(arr)) / t['entry'] * 100
    else:
        mfe = (t['entry'] - min(arr)) / t['entry'] * 100
        mae = (max(arr) - t['entry']) / t['entry'] * 100
    return mfe, mae

# 1) THE WIN STREAK: 11 wins in a row
print("=" * 80)
print("THE 11-WIN STREAK (trades #12175 to #12185)")
print("=" * 80)
streak = [t for t in trades if 12175 <= t['id'] <= 12185]
print(f"  Cumulative PnL: ${sum(t['pnl'] for t in streak):+.2f}")
for t in streak:
    prices = get_price_path(t)
    mfe, mae = mfe_mae(t, prices)
    sl_str = f"{t['sl']:.5f}" if t['sl'] else "NONE"
    reached = ""
    if t['sl'] and prices:
        actual_high = max(p[1] for p in prices)
        actual_low = min(p[1] for p in prices)
        if t['dir'] == 'SHORT':
            reached = "SL-reached" if actual_high >= t['sl'] else "SL-safe"
        else:
            reached = "SL-reached" if actual_low <= t['sl'] else "SL-safe"
    print(f"  W #{t['id']:5d} {t['token']:6s} {t['dir']:5s} | MFE={mfe:5.2f}% MAE={mae:5.2f}% | "
          f"SL={sl_str} ({reached}) | ${t['pnl']:+.2f} dur={(t['close_time']-t['open_time']).total_seconds():.0f}s | {t['signal']}")

# 2) THE LOSE STREAK: 6 losses in a row
print("\n" + "=" * 80)
print("THE 6-LOSS STREAK (trades #12187 to #12195 minus the 1 win)")
print("=" * 80)
streak_l = [t for t in trades if 12187 <= t['id'] <= 12195]
print(f"  Cumulative PnL: ${sum(t['pnl'] for t in streak_l):+.2f}")
for t in streak_l:
    prices = get_price_path(t)
    mfe, mae = mfe_mae(t, prices)
    sl_str = f"{t['sl']:.5f}" if t['sl'] else "NONE"
    reached = ""
    if t['sl'] and prices:
        actual_high = max(p[1] for p in prices)
        actual_low = min(p[1] for p in prices)
        if t['dir'] == 'SHORT':
            reached = "SL-reached" if actual_high >= t['sl'] else "SL-safe"
        else:
            reached = "SL-reached" if actual_low <= t['sl'] else "SL-safe"
    print(f"  L #{t['id']:5d} {t['token']:6s} {t['dir']:5s} | MFE={mfe:5.2f}% MAE={mae:5.2f}% | "
          f"SL={sl_str} ({reached}) | ${t['pnl']:+.2f} dur={(t['close_time']-t['open_time']).total_seconds():.0f}s | {t['signal']}")

# 3) PROFIT-MONSTER PNL BUCKETING
print("\n" + "=" * 80)
print("PROFIT-MONSTER EXIT — are we cutting winners short?")
print("=" * 80)
wins = [t for t in trades if t['pnl'] > 0]
print(f"  Total wins: {len(wins)}")
print(f"  Winners by leverage:")
for lev in [3, 5]:
    sub = [t for t in wins if t['leverage'] == lev]
    if sub:
        pcts = [t['pnl_pct'] for t in sub]
        print(f"    {lev}x (n={len(sub)}): avg pnl_pct={sum(pcts)/len(pcts):+.2f}% | max={max(pcts):.2f}% | min={min(pcts):.2f}%")
# Bucketed at 0.1% steps
buckets = Counter()
for t in wins:
    buckets[round(t['pnl_pct'], 1)] += 1
print(f"  Pnl_pct distribution:")
for k in sorted(buckets):
    bar = "█" * buckets[k]
    print(f"    +{k:.1f}% : {buckets[k]:2d} {bar}")

# Compare MAE during winners vs losers
print("\n  MAE (max adverse excursion) on winners vs losers:")
wins_mae = []
losses_mae = []
for t in wins:
    p = get_price_path(t)
    _, mae = mfe_mae(t, p)
    wins_mae.append(mae)
for t in [x for x in trades if x['pnl']<0]:
    p = get_price_path(t)
    _, mae = mfe_mae(t, p)
    losses_mae.append(mae)
if wins_mae and losses_mae:
    print(f"    WINNERS avg MAE: {sum(wins_mae)/len(wins_mae):.2f}% (max {max(wins_mae):.2f}%)")
    print(f"    LOSERS  avg MAE: {sum(losses_mae)/len(losses_mae):.2f}% (max {max(losses_mae):.2f}%)")

# 4) WHICH TOKENS ARE PROFITABLE VS UNPROFITABLE
print("\n" + "=" * 80)
print("PER-TOKEN PnL (≥3 trades) — blacklist candidates?")
print("=" * 80)
by_tok = defaultdict(list)
for t in trades:
    by_tok[t['token']].append(t)
for tok in sorted(by_tok):
    grp = by_tok[tok]
    if len(grp) < 2: continue
    net = sum(t['pnl'] for t in grp)
    wr = sum(1 for t in grp if t['pnl']>0) / len(grp) * 100
    print(f"  {tok:8s} n={len(grp):2d}  wr={wr:5.0f}%  net=${net:+.2f}  pnl_pct avg={sum(t['pnl_pct'] for t in grp)/len(grp):+.2f}%")

# 5) TIME-OF-DAY ANALYSIS
print("\n" + "=" * 80)
print("TIME OF DAY — when do wins vs losses occur?")
print("=" * 80)
hours_w = Counter()
hours_l = Counter()
for t in trades:
    h = t['open_time'].hour
    if t['pnl'] > 0:
        hours_w[h] += 1
    else:
        hours_l[h] += 1
print("  Hour (UTC) | W | L | net$ | WR")
all_hours = sorted(set(list(hours_w.keys()) + list(hours_l.keys())))
for h in all_hours:
    w = hours_w[h]
    l = hours_l[h]
    w_pnl = sum(t['pnl'] for t in trades if t['pnl']>0 and t['open_time'].hour==h)
    l_pnl = sum(t['pnl'] for t in trades if t['pnl']<0 and t['open_time'].hour==h)
    net = w_pnl + l_pnl
    total = w+l
    wr = (w/total*100) if total else 0
    print(f"  {h:02d}:00      | {w} | {l} | ${net:+.2f} | {wr:.0f}%")

# 6) CONSECUTIVE PATTERN
print("\n" + "=" * 80)
print("CONSECUTIVE PATTERN — did the same signal fire repeatedly?")
print("=" * 80)
# Find tokens traded 3+ times in 24h
for tok in sorted(by_tok):
    grp = sorted(by_tok[tok], key=lambda x: x['open_time'])
    if len(grp) < 3: continue
    print(f"\n  {tok} - {len(grp)} trades:")
    for t in grp:
        p = get_price_path(t)
        mfe, mae = mfe_mae(t, p)
        outcome = "W" if t['pnl']>0 else "L"
        print(f"    {outcome} #{t['id']} {t['open_time'].strftime('%H:%M')} {t['dir']:5s} | "
              f"MFE={mfe:5.2f}% MAE={mae:5.2f}% | pnl=${t['pnl']:+.2f} | sig={t['signal']}")

# 7) DB highest_price field
print("\n" + "=" * 80)
print("DB highest_price field integrity — does it match actual 1m data?")
print("=" * 80)
mis = 0
for t in trades:
    p = get_price_path(t)
    if not p or not t['highest']: continue
    actual_high = max(x[1] for x in p)
    db_high = t['highest']
    diff = (db_high - actual_high) / actual_high * 100
    if abs(diff) > 0.5:
        print(f"  #{t['id']} {t['token']:6s} | DB highest={db_high:.5f} actual_high={actual_high:.5f} diff={diff:+.1f}%")
        mis += 1
print(f"  Mismatches >0.5%: {mis}/{len(trades)}")

# 8) Biggest winners vs biggest losers — REPLICATE / AVOID analysis
print("\n" + "=" * 80)
print("REPLICATE (biggest winners) — what made them win?")
print("=" * 80)
for t in sorted([x for x in trades if x['pnl']>0], key=lambda x: -x['pnl'])[:5]:
    p = get_price_path(t)
    mfe, mae = mfe_mae(t, p)
    # check: did it dip in MAE early then recover, or go straight up?
    if p:
        # find first 25% vs last 25%
        n = len(p)
        q1 = p[:n//4]
        q4 = p[-n//4:] if n//4 > 0 else p[-1:]
        if q1 and q4:
            q1_avg = sum(x[1] for x in q1)/len(q1)
            q4_avg = sum(x[1] for x in q4)/len(q4)
            if t['dir'] == 'SHORT':
                trajectory = "DROPPED then ROSE" if q4_avg > q1_avg else "DROPPED continuously"
            else:
                trajectory = "ROSE then FELL" if q4_avg < q1_avg else "ROSE continuously"
        else:
            trajectory = "?"
    else:
        trajectory = "no data"
    print(f"  W #{t['id']} {t['token']:6s} {t['dir']:5s} | ${t['pnl']:+.2f} ({t['pnl_pct']:+.2f}%) | MFE={mfe:.2f}% | "
          f"path={trajectory} | signal={t['signal']}")

print("\n" + "=" * 80)
print("AVOID (biggest losers) — what did they have in common?")
print("=" * 80)
for t in sorted([x for x in trades if x['pnl']<0], key=lambda x: x['pnl'])[:5]:
    p = get_price_path(t)
    mfe, mae = mfe_mae(t, p)
    if p:
        n = len(p)
        q1 = p[:n//4]
        q4 = p[-n//4:] if n//4 > 0 else p[-1:]
        if q1 and q4:
            q1_avg = sum(x[1] for x in q1)/len(q1)
            q4_avg = sum(x[1] for x in q4)/len(q4)
            if t['dir'] == 'SHORT':
                trajectory = "ROSE then FELL" if q4_avg < q1_avg else "ROSE continuously"
            else:
                trajectory = "FELL then ROSE" if q4_avg > q1_avg else "FELL continuously"
        else:
            trajectory = "?"
    else:
        trajectory = "no data"
    print(f"  L #{t['id']} {t['token']:6s} {t['dir']:5s} | ${t['pnl']:+.2f} ({t['pnl_pct']:+.2f}%) | MFE={mfe:.2f}% MAE={mae:.2f}% | "
          f"path={trajectory} | signal={t['signal']}")

# 9) Quick summary
print("\n" + "=" * 80)
print("ONE-LINE SUMMARY OF EACH TRADE")
print("=" * 80)
for t in trades:
    p = get_price_path(t)
    mfe, mae = mfe_mae(t, p)
    outcome = "WIN " if t['pnl']>0 else "LOSS"
    pnl_str = f"${t['pnl']:+.2f}"
    sl_str = f"SL={t['sl']:.5f}" if t['sl'] else "SL=N/A"
    print(f"  {outcome} #{t['id']:5d} {t['token']:6s} {t['dir']:5s} {pnl_str:>7s} ({t['pnl_pct']:+.2f}%) | "
          f"MFE={mfe:5.2f}% MAE={mae:5.2f}% | {sl_str} | exit={t['exit_reason']:15s} | {t['signal']}")

conn.close()
price_db.close()
