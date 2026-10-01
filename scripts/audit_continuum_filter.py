#!/usr/bin/env python3
"""
Independent audit of continuum phase filter claims.
Reads trades from PostgreSQL, joins BTC continuum state at entry time,
categorizes and computes WR/PnL per category.
"""
import subprocess
import sqlite3
import json
import sys
from datetime import datetime, timezone
from collections import defaultdict

# ── 1. Pull trades from PostgreSQL ──────────────────────────────────
SQL = """
SELECT id, token, direction, signal, open_time, close_time, pnl_usdt,
       amount_usdt, _signal_metadata
FROM trades
WHERE status = 'closed'
  AND close_time > now() - interval '14 days'
ORDER BY open_time;
"""

result = subprocess.run(
    ['psql', '-h', '/var/run/postgresql', '-d', 'brain', '-U', 'postgres',
     '--no-align', '--tuples-only', '-F', '\t', '-c', SQL],
    capture_output=True, text=True
)

if result.returncode != 0:
    print(f"PSQL ERROR: {result.stderr}")
    sys.exit(1)

trades = []
for line in result.stdout.strip().split('\n'):
    if not line:
        continue
    if line.startswith('id\t'):  # defensive header skip
        continue
    parts = line.split('\t')
    if len(parts) < 9:
        continue
    tid, token, direction, signal, open_time, close_time, pnl, amount, meta = parts[:9]
    try:
        pnl_f = float(pnl) if pnl else 0.0
    except ValueError:
        pnl_f = 0.0
    try:
        meta_j = json.loads(meta) if meta and meta != '' else {}
    except json.JSONDecodeError:
        meta_j = {}

    # Parse open_time to unix ts
    # Format: 2026-10-01 13:08:46.706951
    try:
        dt = datetime.strptime(open_time[:26], '%Y-%m-%d %H:%M:%S.%f')
    except ValueError:
        try:
            dt = datetime.strptime(open_time[:19], '%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue
    ts = int(dt.replace(tzinfo=timezone.utc).timestamp())

    try:
        close_dt = datetime.strptime(close_time[:19], '%Y-%m-%d %H:%M:%S')
        close_ts = int(close_dt.replace(tzinfo=timezone.utc).timestamp())
    except (ValueError, TypeError):
        close_ts = 0

    trades.append({
        'id': int(tid),
        'token': token,
        'direction': direction,
        'signal': signal,
        'open_time': open_time,
        'close_time': close_time,
        'open_ts': ts,
        'close_ts': close_ts,
        'pnl': pnl_f,
        'amount': float(amount) if amount else 0.0,
        'meta': meta_j,
    })

print(f"Loaded {len(trades)} closed trades from PostgreSQL (14 days)")

# ── 2. Load BTC continuum states ────────────────────────────────────
conn = sqlite3.connect('/root/.hermes/data/continuum.db')
cur = conn.cursor()

# Get time range of trades
min_ts = min(t['open_ts'] for t in trades)
max_ts = max(t['open_ts'] for t in trades)
# Extend window a bit for lookback
min_ts -= 600

cur.execute("""
    SELECT ts, state_score, zscore_tier, ema300_position, ema300_duration,
           zscore_val, velocity_state, market_phase, wyckoff_phase,
           trend_quality, linreg_direction
    FROM continuum_states
    WHERE token='BTC' AND timeframe='1m'
      AND ts >= ? AND ts <= ?
    ORDER BY ts
""", (min_ts, max_ts + 600))

btc_rows = cur.fetchall()
conn.close()

print(f"Loaded {len(btc_rows)} BTC continuum rows")

# Build lookup: for a given ts, find the latest continuum row at or before ts
# Since rows are ordered, we can binary search
btc_ts_list = [r[0] for r in btc_rows]

import bisect

def get_btc_state(trade_ts):
    """Get BTC continuum state at or just before trade_ts."""
    idx = bisect.bisect_right(btc_ts_list, trade_ts) - 1
    if idx < 0:
        return None
    r = btc_rows[idx]
    return {
        'ts': r[0],
        'state_score': r[1],
        'zscore_tier': r[2],
        'ema300_position': r[3],
        'ema300_duration': r[4],
        'zscore_val': r[5],
        'velocity_state': r[6],
        'market_phase': r[7],
        'wyckoff_phase': r[8],
        'trend_quality': r[9],
        'linreg_direction': r[10],
        'age_seconds': trade_ts - r[0],
    }

# ── 3. Enrich trades with BTC continuum state ──────────────────────
matched = 0
unmatched = 0
for t in trades:
    state = get_btc_state(t['open_ts'])
    if state and state['age_seconds'] <= 300:  # within 5 minutes
        t['btc'] = state
        matched += 1
    else:
        t['btc'] = None
        unmatched += 1

print(f"Matched {matched} trades to BTC continuum state (within 5 min)")
print(f"Unmatched: {unmatched}")

# ── 4. Categorize trades ────────────────────────────────────────────
# Categories from the claims:
# SHORT extreme bearish: score<5 AND zscore_tier IN ('STRONG_NEG','NEG')
# SHORT neutral: score 10-30 AND zscore_tier='NEUTRAL'
# LONG high+above: score>70 AND ema300_position='ABOVE'
# LONG low+below: score<40 OR ema300_position='BELOW'

categories = defaultdict(list)

for t in trades:
    btc = t.get('btc')
    if not btc:
        categories['UNMATCHED'].append(t)
        continue

    score = btc['state_score'] if btc['state_score'] is not None else -999
    tier = btc['zscore_tier'] or ''
    ema_pos = btc['ema300_position'] or ''
    direction = t['direction']

    if direction == 'SHORT':
        if score < 5 and tier in ('STRONG_NEG', 'NEG'):
            categories['SHORT_extreme_bear'].append(t)
        elif 10 <= score <= 30 and tier == 'NEUTRAL':
            categories['SHORT_neutral'].append(t)
        else:
            categories['SHORT_other'].append(t)
    elif direction == 'LONG':
        if score > 70 and ema_pos == 'ABOVE':
            categories['LONG_high_above'].append(t)
        elif score < 40 or ema_pos == 'BELOW':
            categories['LONG_low_below'].append(t)
        else:
            categories['LONG_other'].append(t)
    else:
        categories['UNKNOWN_DIR'].append(t)

# ── 5. Compute stats per category ───────────────────────────────────
def compute_stats(trade_list):
    n = len(trade_list)
    if n == 0:
        return {'n': 0, 'wins': 0, 'losses': 0, 'wr': 0, 'pnl': 0, 'avg_pnl': 0}
    wins = sum(1 for t in trade_list if t['pnl'] > 0)
    losses = sum(1 for t in trade_list if t['pnl'] < 0)
    breakeven = n - wins - losses
    total_pnl = sum(t['pnl'] for t in trade_list)
    return {
        'n': n,
        'wins': wins,
        'losses': losses,
        'breakeven': breakeven,
        'wr': round(wins / n * 100, 1) if n else 0,
        'pnl': round(total_pnl, 2),
        'avg_pnl': round(total_pnl / n, 4) if n else 0,
    }

print("\n" + "=" * 70)
print("CATEGORY BREAKDOWN")
print("=" * 70)

for cat in ['SHORT_extreme_bear', 'SHORT_neutral', 'SHORT_other',
            'LONG_high_above', 'LONG_low_below', 'LONG_other',
            'UNMATCHED', 'UNKNOWN_DIR']:
    stats = compute_stats(categories.get(cat, []))
    if stats['n'] > 0:
        print(f"\n{cat}:")
        print(f"  Trades: {stats['n']}, Wins: {stats['wins']}, Losses: {stats['losses']}, Breakeven: {stats['breakeven']}")
        print(f"  WR: {stats['wr']}%, Total PnL: ${stats['pnl']}, Avg PnL: ${stats['avg_pnl']}")

# ── 6. Signal type breakdown per category ───────────────────────────
print("\n" + "=" * 70)
print("SIGNAL TYPE BREAKDOWN PER CATEGORY")
print("=" * 70)

for cat in ['SHORT_extreme_bear', 'SHORT_neutral', 'SHORT_other',
            'LONG_high_above', 'LONG_low_below', 'LONG_other']:
    trade_list = categories.get(cat, [])
    if not trade_list:
        continue
    print(f"\n{cat} ({len(trade_list)} trades):")
    sig_stats = defaultdict(lambda: {'n': 0, 'pnl': 0, 'wins': 0})
    for t in trade_list:
        sig = t['signal'] or 'unknown'
        # Normalize: take primary signal (before comma)
        primary = sig.split(',')[0].strip()
        sig_stats[primary]['n'] += 1
        sig_stats[primary]['pnl'] += t['pnl']
        if t['pnl'] > 0:
            sig_stats[primary]['wins'] += 1
    for sig, s in sorted(sig_stats.items(), key=lambda x: -x[1]['n']):
        wr = round(s['wins'] / s['n'] * 100, 1) if s['n'] else 0
        print(f"  {sig:40s}  n={s['n']:3d}  WR={wr:5.1f}%  PnL=${s['pnl']:.2f}")

# ── 7. Time-of-day analysis ─────────────────────────────────────────
print("\n" + "=" * 70)
print("TIME-OF-DAY ANALYSIS (UTC hour)")
print("=" * 70)

for cat in ['LONG_low_below', 'LONG_high_above', 'SHORT_neutral', 'SHORT_extreme_bear']:
    trade_list = categories.get(cat, [])
    if not trade_list:
        continue
    print(f"\n{cat}:")
    hour_stats = defaultdict(lambda: {'n': 0, 'pnl': 0, 'wins': 0})
    for t in trade_list:
        hour = int(t['open_time'][11:13])
        hour_stats[hour]['n'] += 1
        hour_stats[hour]['pnl'] += t['pnl']
        if t['pnl'] > 0:
            hour_stats[hour]['wins'] += 1
    for h in sorted(hour_stats.keys()):
        s = hour_stats[h]
        wr = round(s['wins'] / s['n'] * 100, 1) if s['n'] else 0
        print(f"  {h:02d}:00  n={s['n']:3d}  WR={wr:5.1f}%  PnL=${s['pnl']:.2f}")

# ── 8. Verify specific claims ───────────────────────────────────────
print("\n" + "=" * 70)
print("CLAIM VERIFICATION")
print("=" * 70)

# Claim 1: SHORT neutral worse than extreme bearish
sn = compute_stats(categories.get('SHORT_neutral', []))
se = compute_stats(categories.get('SHORT_extreme_bear', []))
print(f"\nClaim 1: SHORT neutral (score 10-30, z=NEUTRAL) WR vs extreme bearish (score<5, z=STRONG_NEG)")
print(f"  Previous claim: neutral 40.9% WR, extreme bearish 48.1% WR")
print(f"  My data:        neutral {sn['wr']}% WR (n={sn['n']}), extreme bearish {se['wr']}% WR (n={se['n']})")
print(f"  PnL:            neutral ${sn['pnl']}, extreme bearish ${se['pnl']}")

# Claim 2: Block SHORT score>10 AND z!=STRONG_NEG saves $0.61
# This would block SHORT_neutral + SHORT_other (where score>10 and tier != STRONG_NEG)
blocked_shorts = []
for t in trades:
    btc = t.get('btc')
    if not btc or t['direction'] != 'SHORT':
        continue
    score = btc['state_score'] if btc['state_score'] is not None else -999
    tier = btc['zscore_tier'] or ''
    if score > 10 and tier != 'STRONG_NEG':
        blocked_shorts.append(t)

blocked_stats = compute_stats(blocked_shorts)
print(f"\nClaim 2: Block SHORT when score>10 AND z!=STRONG_NEG")
print(f"  Previous claim: would block 22 trades, save $0.61")
print(f"  My data:        would block {blocked_stats['n']} trades, total PnL of blocked = ${blocked_stats['pnl']}")
print(f"  => Savings if blocked: ${-blocked_stats['pnl']:.2f}")

# Claim 3: LONG below EMA300 profitable
llb = compute_stats(categories.get('LONG_low_below', []))
lha = compute_stats(categories.get('LONG_high_above', []))
print(f"\nClaim 3: LONG below EMA300 (or low score) profitable (+$1.24)")
print(f"  Previous claim: score<40 OR ema=BELOW => +$1.24, WR 45.2%, n=73")
print(f"  My data:        score<40 OR ema=BELOW => ${llb['pnl']}, WR {llb['wr']}%, n={llb['n']}")

print(f"\nClaim 4: LONG high score + above EMA breakeven (-$0.02)")
print(f"  Previous claim: score>70 AND ema=ABOVE => -$0.02, WR 47.0%, n=83")
print(f"  My data:        score>70 AND ema=ABOVE => ${lha['pnl']}, WR {lha['wr']}%, n={lha['n']}")

# Claim 5: Blocking low-score LONGs would lose money
print(f"\nClaim 5: Blocking low-score LONGs would LOSE money")
print(f"  My data: LONG_low_below total PnL = ${llb['pnl']}")
print(f"  If blocked, system loses ${-llb['pnl']:.2f} of profit")
print(f"  => {'CONFIRMED' if llb['pnl'] > 0 else 'DISPUTED — blocking would SAVE money'}")

# ── 9. Sample size check ────────────────────────────────────────────
print("\n" + "=" * 70)
print("SAMPLE SIZE ASSESSMENT")
print("=" * 70)
for cat in ['SHORT_extreme_bear', 'SHORT_neutral', 'LONG_high_above', 'LONG_low_below']:
    stats = compute_stats(categories.get(cat, []))
    n = stats['n']
    wr = stats['wr']
    # Wilson score interval approximation
    if n > 0:
        z = 1.96
        p = wr / 100
        denom = 1 + z*z/n
        centre = p + z*z/(2*n)
        spread = z * ((p*(1-p)/n + z*z/(4*n*n)) ** 0.5)
        low = round((centre - spread) / denom * 100, 1)
        high = round((centre + spread) / denom * 100, 1)
        print(f"  {cat:25s}  n={n:3d}  WR={wr:5.1f}%  95% CI: [{low}%, {high}%]")
    else:
        print(f"  {cat:25s}  n=0")

# ── 10. Detailed breakdown of LONG_low_below ────────────────────────
print("\n" + "=" * 70)
print("DEEP DIVE: LONG_low_below (the 'profitable' category)")
print("=" * 70)

llb_trades = categories.get('LONG_low_below', [])
if llb_trades:
    # Split by reason: low score vs below EMA
    low_score_only = [t for t in llb_trades if (t.get('btc') and t['btc']['state_score'] is not None and t['btc']['state_score'] < 40 and t['btc']['ema300_position'] != 'BELOW')]
    below_ema_only = [t for t in llb_trades if (t.get('btc') and t['btc']['ema300_position'] == 'BELOW' and t['btc']['state_score'] is not None and t['btc']['state_score'] >= 40)]
    both = [t for t in llb_trades if (t.get('btc') and t['btc']['state_score'] is not None and t['btc']['state_score'] < 40 and t['btc']['ema300_position'] == 'BELOW')]

    for label, subset in [('Low score only (score<40, ema!=BELOW)', low_score_only),
                          ('Below EMA only (ema=BELOW, score>=40)', below_ema_only),
                          ('Both (score<40 AND ema=BELOW)', both)]:
        stats = compute_stats(subset)
        if stats['n'] > 0:
            print(f"\n  {label}:")
            print(f"    n={stats['n']}, WR={stats['wr']}%, PnL=${stats['pnl']}, Avg=${stats['avg_pnl']}")

# ── 11. Distribution of state_score in LONG_low_below ──────────────
print("\n" + "=" * 70)
print("STATE SCORE DISTRIBUTION in LONG_low_below")
print("=" * 70)
if llb_trades:
    buckets = defaultdict(int)
    pnl_buckets = defaultdict(float)
    for t in llb_trades:
        btc = t.get('btc')
        if btc and btc['state_score'] is not None:
            s = btc['state_score']
            if s < 0:
                b = '<0'
            elif s < 10:
                b = '0-10'
            elif s < 20:
                b = '10-20'
            elif s < 40:
                b = '20-40'
            elif s < 70:
                b = '40-70'
            else:
                b = '70+'
            buckets[b] += 1
            pnl_buckets[b] += t['pnl']
    for b in ['<0', '0-10', '10-20', '20-40', '40-70', '70+']:
        if buckets[b]:
            print(f"  Score {b:6s}: n={buckets[b]:3d}  PnL=${pnl_buckets[b]:.2f}")

print("\n" + "=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)
