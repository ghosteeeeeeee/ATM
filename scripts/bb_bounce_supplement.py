#!/usr/bin/env python3
"""Supplementary: test handcrafted filter combos and check velocity gate details."""
import sqlite3, os, math
from collections import defaultdict

HERMES_DATA = '/root/.hermes/data'
RUNTIME_DB = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')
CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')

def linreg_slope(xs):
    n = len(xs)
    if n < 3: return 0.0
    x_mean = sum(range(n)) / n
    y_mean = sum(xs) / n
    num = sum((i - x_mean) * (xs[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den != 0 else 0.0

def compute_rsi(closes, period=14):
    if len(closes) < period + 1: return None
    gains, losses = [], []
    for i in range(1, period + 1):
        delta = closes[-i] - closes[-i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains) / len(gains) if gains else 0
    avg_loss = sum(losses) / len(losses) if losses else 0.001
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))

def compute_bb(closes, period=20, stddev=1.8):
    if len(closes) < period: return None, None, None, None, None
    recent = closes[-period:]
    middle = sum(recent) / period
    variance = sum((c - middle) ** 2 for c in recent) / period
    std = variance ** 0.5
    upper = middle + stddev * std
    lower = middle - stddev * std
    width = (upper - lower) / middle if middle > 0 else 0
    bb_pos = (closes[-1] - lower) / (upper - lower) if upper - lower > 0 else 0.5
    return middle, upper, lower, width, bb_pos

def get_metrics(token, entry_ts, direction):
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT ts, open, high, low, close, volume FROM candles_1m
            WHERE token = ? AND ts <= ? ORDER BY ts DESC LIMIT 60
        """, (token.upper(), entry_ts))
        rows = cur.fetchall()
        if len(rows) < 30: return None
        rows = list(reversed(rows))
        closes = [r[4] for r in rows]
        volumes = [r[5] for r in rows]
        highs = [r[2] for r in rows]
        lows = [r[3] for r in rows]
        cp = closes[-1]
        if cp <= 0: return None
        m = {}
        m['mom30'] = linreg_slope(closes[-30:]) / cp * 100 if len(closes) >= 30 else 0
        m['mom15'] = linreg_slope(closes[-15:]) / cp * 100 if len(closes) >= 15 else 0
        m['mom5'] = linreg_slope(closes[-5:]) / cp * 100 if len(closes) >= 5 else 0
        m['vel15'] = (closes[-1] - closes[-15]) / closes[-15] * 100 if len(closes) >= 15 and closes[-15] > 0 else 0
        m['vel5'] = (closes[-1] - closes[-5]) / closes[-5] * 100 if len(closes) >= 5 and closes[-5] > 0 else 0
        m['rsi'] = compute_rsi(closes) or 50
        _, _, _, width, bb_pos = compute_bb(closes)
        m['bb_width'] = width or 0
        m['bb_pos'] = bb_pos or 0.5
        if len(volumes) >= 25:
            a5 = sum(volumes[-5:]) / 5
            a20 = sum(volumes[-25:-5]) / 20
            m['vol_ratio'] = a5 / a20 if a20 > 0 else 1
        else:
            m['vol_ratio'] = 1
        if len(closes) >= 20:
            f = closes[-20:-10]
            s = closes[-10:]
            v1 = (f[-1] - f[0]) / f[0] * 100 if f[0] > 0 else 0
            v2 = (s[-1] - s[0]) / s[0] * 100 if s[0] > 0 else 0
            m['accel'] = v2 - v1
        else:
            m['accel'] = 0
        if len(highs) >= 30:
            pk = max(highs[-30:])
            tr = min(lows[-30:])
            m['mddd'] = (pk - tr) / pk * 100 if pk > 0 else 0
            rng = pk - tr
            m['range_pos'] = (cp - tr) / rng if rng > 0 else 0.5
        else:
            m['mddd'] = 0
            m['range_pos'] = 0.5
        if len(closes) >= 6:
            d = sum(1 for i in range(-5, 0) if (closes[i] > closes[i-1]) == (direction == 'LONG'))
            m['dir_c'] = d
        else:
            m['dir_c'] = 2.5
        return m
    except Exception as e:
        return None
    finally:
        if conn: conn.close()

# Load trades
conn = sqlite3.connect(RUNTIME_DB, timeout=10)
cur = conn.cursor()
cur.execute("""
    SELECT token, direction, is_win, pnl_pct, pnl_usdt, confidence, created_at, trade_id, signal_type
    FROM signal_outcomes WHERE signal_type LIKE '%bb_bounce%' ORDER BY created_at
""")
trades = cur.fetchall()
conn.close()

from datetime import datetime
data = []
for tok, direc, isw, pnp, pnus, conf, cat, tid, styp in trades:
    try:
        dt_str = str(cat).replace('Z','').replace('+00:00','')
        dt = datetime.fromisoformat(dt_str)
        ets = int(dt.timestamp())
    except:
        continue
    m = get_metrics(tok, ets, direc)
    if m: data.append({'t': tok, 'd': direc, 'w': bool(isw), 'pnl': pnus, 'm': m, 'st': styp})

winners = [t for t in data if t['w']]
losers = [t for t in data if not t['w']]
base_pnl = sum(t['pnl'] for t in data)
base_wr = len(winners)/len(data)*100

# Test handcrafted combos
combos = [
    ("Mom30>-0.01 & RSI<55 & Vel15>-0.3",
     lambda t: t['m']['mom30'] > -0.01 and t['m']['rsi'] < 55 and t['m']['vel15'] > -0.3),
    ("Mom30>-0.02 & RSI<50 & VolR>1.0",
     lambda t: t['m']['mom30'] > -0.02 and t['m']['rsi'] < 50 and t['m']['vol_ratio'] > 1.0),
    ("Mom30>-0.01 & BBwidth<0.05 & Vel15>-0.2",
     lambda t: t['m']['mom30'] > -0.01 and t['m']['bb_width'] < 0.05 and t['m']['vel15'] > -0.2),
    ("Vel15>-0.15 & RSI<55 & Mom30>-0.02",
     lambda t: t['m']['vel15'] > -0.15 and t['m']['rsi'] < 55 and t['m']['mom30'] > -0.02),
    ("Vel15>-0.15 & Mom30>-0.01 & VolR>0.75",
     lambda t: t['m']['vel15'] > -0.15 and t['m']['mom30'] > -0.01 and t['m']['vol_ratio'] > 0.75),
    ("Mom30>0 & Vel15>-0.15 (aligned)",
     lambda t: t['m']['mom30'] > 0 and t['m']['vel15'] > -0.15),
    ("RSI<50 & Vel15>-0.2 & Mom30>-0.01",
     lambda t: t['m']['rsi'] < 50 and t['m']['vel15'] > -0.2 and t['m']['mom30'] > -0.01),
    ("Accel<0 & Vel15>-0.3 & RSI<60",
     lambda t: t['m']['accel'] < 0 and t['m']['vel15'] > -0.3 and t['m']['rsi'] < 60),
    ("Mom30>-0.01 & Vel15>-0.15 & RSI<55 & VolR>0.75",
     lambda t: t['m']['mom30'] > -0.01 and t['m']['vel15'] > -0.15 and t['m']['rsi'] < 55 and t['m']['vol_ratio'] > 0.75),
    ("Mom30>-0.01 & Vel15>-0.15 & ATR>0.03",
     lambda t: t['m']['mom30'] > -0.01 and t['m']['vel15'] > -0.15),
    ("Mom30>-0.01 & Vel15>-0.15 & DirC>=2",
     lambda t: t['m']['mom30'] > -0.01 and t['m']['vel15'] > -0.15 and t['m']['dir_c'] >= 2),
    ("Mom30>-0.02 & Vel5>-0.1 & RSI<55",
     lambda t: t['m']['mom30'] > -0.02 and t['m']['vel5'] > -0.1 and t['m']['rsi'] < 55),
    ("Mom30>-0.01 & Vel15>-0.15 & Vol20<0.05",
     lambda t: t['m']['mom30'] > -0.01 and t['m']['vel15'] > -0.15),
    ("Existing vel gate: Vel15>-0.3",
     lambda t: t['m']['vel15'] > -0.3),
    ("|Vel5|<0.5 (spike exhaust)",
     lambda t: abs(t['m']['vel5']) < 0.5),
    ("Both existing gates",
     lambda t: t['m']['vel15'] > -0.3 and abs(t['m']['vel5']) < 0.5),
    ("Mom30>0 & RSI<45 & Vel15>-0.15",
     lambda t: t['m']['mom30'] > 0 and t['m']['rsi'] < 45 and t['m']['vel15'] > -0.15),
    ("Mom30>-0.01 & Vel15>-0.15 & VolR>1.5",
     lambda t: t['m']['mom30'] > -0.01 and t['m']['vel15'] > -0.15 and t['m']['vol_ratio'] > 1.5),
    ("Vol20<0.03 & Mom30>-0.01 & Vel15>-0.15",
     lambda t: t['m']['mom30'] > -0.01 and t['m']['vel15'] > -0.15),
    ("RangePos<0.3 & Mom30>-0.02",
     lambda t: t['m']['range_pos'] < 0.3 and t['m']['mom30'] > -0.02),
    ("Accel<0 & Mom30>-0.01 & Vel15>-0.15",
     lambda t: t['m']['accel'] < 0 and t['m']['mom30'] > -0.01 and t['m']['vel15'] > -0.15),
    ("Mom30>0 & Vel15>0 & Mom15>0 (all positive)",
     lambda t: t['m']['mom30'] > 0 and t['m']['vel15'] > 0 and t['m']['mom15'] > 0),
    ("Mom30>-0.01 & Vel15>-0.15",
     lambda t: t['m']['mom30'] > -0.01 and t['m']['vel15'] > -0.15),
    ("Mom30>-0.005 & Vel15>-0.1",
     lambda t: t['m']['mom30'] > -0.005 and t['m']['vel15'] > -0.1),
    ("DirC>=3 & Vel15>-0.15",
     lambda t: t['m']['dir_c'] >= 3 and t['m']['vel15'] > -0.15),
    ("Mom30>-0.005 & Mom15>0 & Vel15>-0.1",
     lambda t: t['m']['mom30'] > -0.005 and t['m']['mom15'] > 0 and t['m']['vel15'] > -0.1),
    ("BBwidth<0.04 & Mom30>-0.01",
     lambda t: t['m']['bb_width'] < 0.04 and t['m']['mom30'] > -0.01),
    ("BBwidth<0.03 & Mom30>-0.02",
     lambda t: t['m']['bb_width'] < 0.03 and t['m']['mom30'] > -0.02),
    ("MaxDD>0.75% & Vel15>-0.3 & RSI<55",
     lambda t: t['m']['mddd'] > 0.75 and t['m']['vel15'] > -0.3 and t['m']['rsi'] < 55),
    ("Mom30<0 & Mom5>0 (reversal in progress) & Vel15>-0.3",
     lambda t: t['m']['mom30'] < 0 and t['m']['mom5'] > 0 and t['m']['vel15'] > -0.3),
    # The TRULY best combos from Part 1
    ("Mom30>-0.001 & Vel15>-0.3 (BEST RAW PNL)",
     lambda t: t['m']['mom30'] > -0.001 and t['m']['vel15'] > -0.3),
    ("Mom30>-0.005 & Vel15>-0.3 (BEST BALANCED)",
     lambda t: t['m']['mom30'] > -0.005 and t['m']['vel15'] > -0.3),
    ("Vel15>-0.3 & Mom30>0.005 (BEST WR)",
     lambda t: t['m']['vel15'] > -0.3 and t['m']['mom30'] > 0.005),
]

print("=" * 100)
print("HANDCRAFTED COMBINATION ANALYSIS")
print("=" * 100)
print(f"\n  Base: {len(data)} trades, {base_wr:.1f}% WR, ${base_pnl:+.2f} PnL")
print(f"\n  {'Filter':<60} {'Kept':>5} {'WR%':>7} {'PnL':>10} {'ΔPnL':>10} {'Wkpt%':>7} {'Lkill%':>7}")
print("  " + "-" * 110)

results = []
for label, filt in combos:
    kept = [t for t in data if filt(t)]
    if len(kept) < 3: continue
    kw = [t for t in kept if t['w']]
    kl = [t for t in kept if not t['w']]
    wr = len(kw)/len(kept)*100
    pnl = sum(t['pnl'] for t in kept)
    wk = len(kw)/len(winners)*100 if winners else 0
    lk = (1 - len(kl)/len(losers))*100 if losers else 0
    results.append((label, len(kept), wr, pnl, pnl-base_pnl, wk, lk))

results.sort(key=lambda x: x[3], reverse=True)
for label, kept, wr, pnl, dpnl, wk, lk in results:
    star = " ***" if pnl > base_pnl and wr > base_wr + 10 else (" **" if pnl > base_pnl else "")
    print(f"  {label:<60} {kept:>5} {wr:>6.1f}% ${pnl:>+9.2f} ${dpnl:>+9.2f} {wk:>6.1f}% {lk:>6.1f}%{star}")

# Deeper: per-direction analysis
print("\n" + "=" * 100)
print("DIRECTION-SPECIFIC ANALYSIS")
print("=" * 100)

for direc in ['LONG', 'SHORT']:
    subset = [t for t in data if t['d'] == direc]
    if not subset: continue
    w = [t for t in subset if t['w']]
    l = [t for t in subset if not t['w']]
    print(f"\n  {direc}: {len(subset)} trades, {len(w)/len(subset)*100:.1f}% WR, ${sum(t['pnl'] for t in subset):+.2f}")
    
    # Best filter for this direction
    best_pnl = -999
    best_label = ""
    for label, filt in combos:
        kept = [t for t in subset if filt(t)]
        if len(kept) < 3: continue
        pnl = sum(t['pnl'] for t in kept)
        wr = len([t for t in kept if t['w']])/len(kept)*100
        if pnl > best_pnl:
            best_pnl = pnl
            best_label = label
            best_wr = wr
            best_kept = len(kept)
    if best_label:
        print(f"    Best for {direc}: {best_label} → {best_kept}/{len(subset)}, {best_wr:.1f}% WR, ${best_pnl:+.2f}")
    
    # Distribution of key metrics
    w_mom30 = [t['m']['mom30'] for t in w]
    l_mom30 = [t['m']['mom30'] for t in l]
    w_vel15 = [t['m']['vel15'] for t in w]
    l_vel15 = [t['m']['vel15'] for t in l]
    w_rsi = [t['m']['rsi'] for t in w]
    l_rsi = [t['m']['rsi'] for t in l]
    
    if w_mom30 and l_mom30:
        print(f"    Mom30:  W mean={sum(w_mom30)/len(w_mom30):.4f}, L mean={sum(l_mom30)/len(l_mom30):.4f}")
    if w_vel15 and l_vel15:
        print(f"    Vel15:  W mean={sum(w_vel15)/len(w_vel15):.4f}, L mean={sum(l_vel15)/len(l_vel15):.4f}")
    if w_rsi and l_rsi:
        print(f"    RSI:    W mean={sum(w_rsi)/len(w_rsi):.1f}, L mean={sum(l_rsi)/len(l_rsi):.1f}")

# Key insight: What does the BEST filter actually kill?
print("\n" + "=" * 100)
print("ANALYSIS OF KILLED LOSERS vs KILLED WINNERS")
print("=" * 100)

best_filt = lambda t: t['m']['mom30'] > -0.001 and t['m']['vel15'] > -0.3
killed = [t for t in data if not best_filt(t)]
kept = [t for t in data if best_filt(t)]

killed_winners = [t for t in killed if t['w']]
killed_losers = [t for t in killed if not t['w']]

print(f"\n  Filter: Mom30 > -0.001% AND Vel15 > -0.3%")
print(f"  Killed {len(killed)} trades ({len(killed)/len(data)*100:.1f}%):")
print(f"    Winners killed: {len(killed_winners)} (of {len(winners)} total)")
for t in killed_winners:
    print(f"      {t['t']:>8} {t['d']:>5} pnl=${t['pnl']:+.3f} mom30={t['m']['mom30']:.4f} vel15={t['m']['vel15']:.4f} rsi={t['m']['rsi']:.1f} sig={t['st']}")
print(f"    Losers killed:  {len(killed_losers)} (of {len(losers)} total)")
for t in killed_losers:
    print(f"      {t['t']:>8} {t['d']:>5} pnl=${t['pnl']:+.3f} mom30={t['m']['mom30']:.4f} vel15={t['m']['vel15']:.4f} rsi={t['m']['rsi']:.1f} sig={t['st']}")

# Also check: what's the WR of trades near the boundary?
print("\n" + "=" * 100)
print("BOUNDARY SENSITIVITY (Momentum threshold sweep)")
print("=" * 100)
print(f"\n  {'Threshold':>15} {'Kept':>5} {'WR%':>7} {'PnL':>10} {'AvgPnL':>10} {'Wkpt%':>7} {'Lkill%':>7}")
print("  " + "-" * 70)

for thresh in [-0.010, -0.008, -0.006, -0.005, -0.004, -0.003, -0.002, -0.001, 0, 0.001, 0.002, 0.003, 0.005]:
    filt = lambda t, th=thresh: t['m']['mom30'] > th
    kept = [t for t in data if filt(t)]
    if len(kept) < 3: continue
    kw = [t for t in kept if t['w']]
    kl = [t for t in kept if not t['w']]
    wr = len(kw)/len(kept)*100
    pnl = sum(t['pnl'] for t in kept)
    wk = len(kw)/len(winners)*100
    lk = (1-len(kl)/len(losers))*100
    print(f"  mom30 > {thresh:>+8.4f}  {len(kept):>5} {wr:>6.1f}% ${pnl:>+9.2f} ${pnl/len(kept):>+9.4f} {wk:>6.1f}% {lk:>6.1f}%")

# Velocity threshold sweep
print(f"\n  {'Threshold':>15} {'Kept':>5} {'WR%':>7} {'PnL':>10} {'AvgPnL':>10} {'Wkpt%':>7} {'Lkill%':>7}")
print("  " + "-" * 70)

for thresh in [-0.5, -0.4, -0.3, -0.25, -0.2, -0.15, -0.1, -0.05, 0]:
    filt = lambda t, th=thresh: t['m']['vel15'] > th
    kept = [t for t in data if filt(t)]
    if len(kept) < 3: continue
    kw = [t for t in kept if t['w']]
    kl = [t for t in kept if not t['w']]
    wr = len(kw)/len(kept)*100
    pnl = sum(t['pnl'] for t in kept)
    wk = len(kw)/len(winners)*100
    lk = (1-len(kl)/len(losers))*100
    print(f"  vel15  > {thresh:>+8.3f}  {len(kept):>5} {wr:>6.1f}% ${pnl:>+9.2f} ${pnl/len(kept):>+9.4f} {wk:>6.1f}% {lk:>6.1f}%")

print("\n" + "=" * 100)
print("SUPPLEMENTARY ANALYSIS COMPLETE")
print("=" * 100)
