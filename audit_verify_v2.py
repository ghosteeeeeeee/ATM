#!/usr/bin/env python3
"""
AUDIT v2: Re-run analysis ONLY on trades where continuum state data exists (Sep 4+)
This is the critical correction - the original analysis was corrupted by
matching 87% of trades to wrong/repeated states.
"""
import sys
import json
import math
import random
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, '/root/.hermes/scripts')

from _secrets import BRAIN_DB_DICT
import psycopg2
import sqlite3

CONTINUUM_DB = '/root/.hermes/data/continuum.db'

# ═══════════════════════════════════════════════════════════════════════
# Load trades
# ═══════════════════════════════════════════════════════════════════════
pg_conn = psycopg2.connect(**BRAIN_DB_DICT)
pg_cur = pg_conn.cursor()

# CRITICAL FIX: Only load trades from Sep 4 onwards (when continuum data exists)
pg_cur.execute("""
    SELECT id, token, direction, open_time, close_time, pnl_usdt, regime, volatility_regime,
           entry_trend, confidence, leverage, status
    FROM trades
    WHERE open_time >= '2026-09-04'
      AND open_time IS NOT NULL
      AND pnl_usdt IS NOT NULL
      AND status = 'closed'
    ORDER BY open_time
""")
trades = pg_cur.fetchall()
print(f"Trades from Sep 4+ (valid joins): {len(trades)}")
pg_cur.close()
pg_conn.close()

# Load continuum states
ct_conn = sqlite3.connect(CONTINUUM_DB)
ct_cur = ct_conn.cursor()
ct_cur.execute("""
    SELECT ts, market_phase, linreg_direction, ema300_position, trend_quality,
           volume_regime, state_score
    FROM continuum_states ORDER BY ts
""")
states = ct_cur.fetchall()
state_times = [s[0] for s in states]
ct_cur.close()
ct_conn.close()

def find_state_for_ts(ts):
    ts_epoch = int(ts.timestamp()) if isinstance(ts, datetime) else int(ts)
    lo, hi = 0, len(state_times) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if state_times[mid] < ts_epoch:
            lo = mid + 1
        else:
            hi = mid
    if lo > 0:
        if abs(state_times[lo] - ts_epoch) < abs(state_times[lo-1] - ts_epoch):
            return states[lo]
        else:
            return states[lo-1]
    return states[lo]

# Enrich
enriched = []
for t in trades:
    trade_id, token, direction, open_time, close_time, pnl, regime, vol_regime, trend, conf, lev, status = t
    state = find_state_for_ts(open_time)
    if state:
        ts, market_phase, linreg_dir, ema_pos, trend_qual, vol_reg, state_score = state
        delta = abs((open_time - datetime.fromtimestamp(ts)).total_seconds())
        enriched.append({
            'id': trade_id, 'token': token, 'direction': direction,
            'open_time': open_time, 'close_time': close_time,
            'pnl': float(pnl) if pnl else 0.0,
            'market_phase': market_phase, 'linreg_direction': linreg_dir,
            'ema300_position': ema_pos, 'trend_quality': trend_qual,
            'volume_regime': vol_reg, 'state_score': state_score,
            'time_delta_seconds': delta,
        })

print(f"Enriched: {len(enriched)}")
deltas = [e['time_delta_seconds'] for e in enriched]
print(f"Time delta: min={min(deltas):.0f}s, max={max(deltas):.0f}s, avg={sum(deltas)/len(deltas):.0f}s, median={sorted(deltas)[len(deltas)//2]:.0f}s")
big_delta = [d for d in deltas if d > 300]
print(f"Trades with >5min delta: {len(big_delta)} ({len(big_delta)/len(deltas)*100:.1f}%)")

# ═══════════════════════════════════════════════════════════════════════
# Analysis
# ═══════════════════════════════════════════════════════════════════════

def analyze_combo(trades_list, direction, market_phase, linreg_dir):
    filtered = [t for t in trades_list
                if t['direction'] == direction
                and t['market_phase'] == market_phase
                and t['linreg_direction'] == linreg_dir]
    n = len(filtered)
    if n == 0:
        return None
    wins = [t for t in filtered if t['pnl'] > 0]
    losses = [t for t in filtered if t['pnl'] <= 0]
    total_pnl = sum(t['pnl'] for t in filtered)
    avg_pnl = total_pnl / n
    winrate = len(wins) / n * 100
    avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
    gross_profit = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    return {
        'direction': direction, 'market_phase': market_phase,
        'linreg_direction': linreg_dir, 'trades': n,
        'wins': len(wins), 'losses': len(losses),
        'winrate': winrate, 'total_pnl': total_pnl,
        'avg_pnl': avg_pnl, 'avg_win': avg_win, 'avg_loss': avg_loss,
        'profit_factor': profit_factor,
    }

def confidence_interval_wr(n, wins):
    if n == 0: return (0, 0)
    p = wins / n
    z = 1.96
    d = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / d
    margin = z * math.sqrt((p*(1-p) + z**2/(4*n)) / n) / d
    return (max(0, center - margin), min(1, center + margin))

def bootstrap_pnl_ci(pnls, n_bootstrap=10000):
    n = len(pnls)
    if n < 5: return None, None, None
    random.seed(42)
    means = [sum(random.choices(pnls, k=n))/n for _ in range(n_bootstrap)]
    means.sort()
    lo = means[int(0.025 * n_bootstrap)]
    hi = means[int(0.975 * n_bootstrap)]
    return lo, sum(pnls)/n, hi

# ═══════════════════════════════════════════════════════════════════════
# CLAIM VERIFICATION (Sep 4+ only)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("CLAIM VERIFICATION — Sept 4+ trades only (valid continuum joins)")
print("=" * 80)

phases = ['CALM', 'DECLINING', 'RECOVERY']
linregs = ['LEAN_BULL', 'LEAN_BEAR', 'NEUTRAL', 'BULL', 'BEAR']

print("\n  ALL LONG COMBOS:")
print(f"  {'Phase':12s} {'LinReg':10s} {'#Trades':>7s} {'WR%':>6s} {'PnL':>10s} {'AvgPnL':>8s} {'PF':>6s}")
print("  " + "-" * 65)
long_combos = []
for phase in phases:
    for lr in linregs:
        r = analyze_combo(enriched, 'LONG', phase, lr)
        if r:
            long_combos.append(r)
            star = " ◄ CLAIMED LEAK" if (phase=='DECLINING' and lr=='LEAN_BULL') else ""
            star = " ◄ CLAIMED BEST" if (phase=='CALM' and lr=='NEUTRAL') else star
            print(f"  {phase:12s} {lr:10s} {r['trades']:7d} {r['winrate']:5.1f}% ${r['total_pnl']:+9.2f} ${r['avg_pnl']:+7.3f} {r['profit_factor']:5.2f}{star}")

print("\n  ALL SHORT COMBOS:")
print(f"  {'Phase':12s} {'LinReg':10s} {'#Trades':>7s} {'WR%':>6s} {'PnL':>10s} {'AvgPnL':>8s} {'PF':>6s}")
print("  " + "-" * 65)
short_combos = []
for phase in phases:
    for lr in linregs:
        r = analyze_combo(enriched, 'SHORT', phase, lr)
        if r:
            short_combos.append(r)
            star = " ◄ CLAIMED LEAK" if (phase=='CALM' and lr=='LEAN_BULL') else ""
            star = " ◄ CLAIMED BEST" if (phase=='DECLINING' and lr=='NEUTRAL') else star
            print(f"  {phase:12s} {lr:10s} {r['trades']:7d} {r['winrate']:5.1f}% ${r['total_pnl']:+9.2f} ${r['avg_pnl']:+7.3f} {r['profit_factor']:5.2f}{star}")

# ═══════════════════════════════════════════════════════════════════════
# Specific claim checks
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("DETAILED CLAIM COMPARISON")
print("=" * 80)

claims = [
    ('LONG', 'DECLINING', 'LEAN_BULL', 93, 51, -0.82, 'Claim 1: Biggest LONG leak'),
    ('SHORT', 'CALM', 'LEAN_BULL', 29, 41, -1.08, 'Claim 2: Biggest SHORT leak'),
    ('LONG', 'CALM', 'NEUTRAL', 19, 74, 0.65, 'Claim 3: Best LONG'),
    ('SHORT', 'DECLINING', 'NEUTRAL', 12, 67, 0.25, 'Claim 4: Best SHORT'),
]

for direction, phase, lr, claimed_trades, claimed_wr, claimed_pnl, desc in claims:
    r = analyze_combo(enriched, direction, phase, lr)
    print(f"\n  {desc}:")
    print(f"  Filter: {direction} + {phase} + {lr}")
    if r:
        print(f"  CLAIMED: {claimed_trades} trades, {claimed_wr}% WR, ${claimed_pnl:.2f} PnL")
        print(f"  FOUND:   {r['trades']} trades, {r['winrate']:.1f}% WR, ${r['total_pnl']:.2f} PnL")
        t_match = r['trades'] == claimed_trades
        wr_match = abs(r['winrate'] - claimed_wr) <= 2
        pnl_match = abs(r['total_pnl'] - claimed_pnl) <= 0.15
        print(f"  Match trades: {'✅' if t_match else '❌'} ({r['trades']} vs {claimed_trades})")
        print(f"  Match WR:     {'✅' if wr_match else '❌'} ({r['winrate']:.1f}% vs {claimed_wr}%)")
        print(f"  Match PnL:    {'✅' if pnl_match else '❌'} (${r['total_pnl']:.2f} vs ${claimed_pnl:.2f})")

        # Significance
        ci = confidence_interval_wr(r['trades'], r['wins'])
        print(f"  95% CI WR: [{ci[0]*100:.1f}%, {ci[1]*100:.1f}%] (width: {(ci[1]-ci[0])*100:.1f}%)")

        pnls_list = [t['pnl'] for t in enriched if t['direction']==direction and t['market_phase']==phase and t['linreg_direction']==lr]
        if len(pnls_list) >= 5:
            lo, mean, hi = bootstrap_pnl_ci(pnls_list)
            sig = "SIGNIFICANT" if (lo > 0 or hi < 0) else "NOT SIGNIFICANT"
            print(f"  95% CI PnL: [${lo:.4f}, ${hi:.4f}] — {sig}")
        sample_status = 'ADEQUATE' if r['trades'] >= 30 else f"SMALL (n={r['trades']}, may be noise)"
        print(f"  Sample: {sample_status}")
    else:
        print(f"  ❌ NO TRADES FOUND")

# ═══════════════════════════════════════════════════════════════════════
# COMBINED FILTER IMPACT
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("COMBINED FILTER IMPACT")
print("=" * 80)

all_long = [t for t in enriched if t['direction'] == 'LONG']
all_short = [t for t in enriched if t['direction'] == 'SHORT']
all_no_filter = all_long + all_short

def stats(label, trades_list):
    n = len(trades_list)
    if n == 0:
        return
    wins = len([t for t in trades_list if t['pnl'] > 0])
    total_pnl = sum(t['pnl'] for t in trades_list)
    avg_pnl = total_pnl / n
    print(f"  {label}: {n} trades, {wins}/{n} = {wins/n*100:.1f}% WR, ${total_pnl:.2f} total, ${avg_pnl:.4f}/trade")

print("\n  BASELINE (no filter):")
stats("All trades", all_no_filter)
stats("  LONG only", all_long)
stats("  SHORT only", all_short)
baseline_pnl = sum(t['pnl'] for t in all_no_filter)
baseline_avg = baseline_pnl / len(all_no_filter)

# Apply filters
filtered = []
blocked_long = []
blocked_short = []
for t in enriched:
    if t['direction'] == 'LONG' and t['market_phase'] == 'DECLINING' and t['linreg_direction'] == 'LEAN_BULL':
        blocked_long.append(t)
    elif t['direction'] == 'SHORT' and t['market_phase'] == 'CALM' and t['linreg_direction'] == 'LEAN_BULL':
        blocked_short.append(t)
    else:
        filtered.append(t)

blocked = blocked_long + blocked_short
print(f"\n  FILTERED (block LONG DECLINING+LEAN_BULL, block SHORT CALM+LEAN_BULL):")
print(f"  Blocked: {len(blocked_long)} LONG + {len(blocked_short)} SHORT = {len(blocked)} total")
stats("All trades", filtered)
filtered_long = [t for t in filtered if t['direction'] == 'LONG']
filtered_short = [t for t in filtered if t['direction'] == 'SHORT']
stats("  LONG only", filtered_long)
stats("  SHORT only", filtered_short)

filtered_pnl = sum(t['pnl'] for t in filtered)
filtered_avg = filtered_pnl / len(filtered)
blocked_pnl = sum(t['pnl'] for t in blocked)

print(f"\n  IMPROVEMENT:")
print(f"  Blocked trades PnL: ${blocked_pnl:.2f}")
print(f"  Total PnL change: ${filtered_pnl - baseline_pnl:.2f}")
print(f"  Avg PnL/trade: ${baseline_avg:.4f} → ${filtered_avg:.4f} (Δ = ${filtered_avg - baseline_avg:+.4f})")

# ═══════════════════════════════════════════════════════════════════════
# STATISTICAL SIGNIFICANCE OF FILTER IMPROVEMENT
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STATISTICAL SIGNIFICANCE OF FILTER IMPROVEMENT")
print("=" * 80)

random.seed(42)
n_boot = 10000

# Method: Compare mean PnL of filtered vs baseline
baseline_pnls = [t['pnl'] for t in all_no_filter]
filtered_pnls = [t['pnl'] for t in filtered]
blocked_pnls = [t['pnl'] for t in blocked]

# Permutation test: shuffle which trades are blocked vs kept
print(f"\n  Baseline: {len(baseline_pnls)} trades, mean=${sum(baseline_pnls)/len(baseline_pnls):.4f}")
print(f"  Filtered: {len(filtered_pnls)} trades, mean=${sum(filtered_pnls)/len(filtered_pnls):.4f}")
print(f"  Blocked: {len(blocked_pnls)} trades, mean=${sum(blocked_pnls)/len(blocked_pnls):.4f}")

# Permutation test: relabel blocked trades as "filtered out" and compute improvement
# Under null hypothesis, which trades get blocked is random
improvements = []
for _ in range(n_boot):
    # Sample same number of random trades to "block"
    blocked_idx = set(random.sample(range(len(baseline_pnls)), len(blocked_pnls)))
    boot_blocked = [baseline_pnls[i] for i in blocked_idx]
    boot_filtered = [baseline_pnls[i] for i in range(len(baseline_pnls)) if i not in blocked_idx]
    imp = sum(boot_filtered)/len(boot_filtered) - sum(baseline_pnls)/len(baseline_pnls)
    improvements.append(imp)

improvements.sort()
lo = improvements[int(0.025 * n_boot)]
hi = improvements[int(0.975 * n_boot)]
mean_imp = sum(improvements)/len(improvements)
pct_above_zero = sum(1 for x in improvements if x > 0) / n_boot * 100

print(f"\n  Permutation test (n={n_boot}):")
print(f"    Mean improvement: ${mean_imp:.5f}")
print(f"    95% CI: [${lo:.5f}, ${hi:.5f}]")
print(f"    P(improvement > 0): {pct_above_zero:.1f}%")
if pct_above_zero > 95:
    print(f"    ✅ Statistically significant at 95% level")
elif pct_above_zero > 90:
    print(f"    ⚠️  Marginally significant (90-95%)")
else:
    print(f"    ❌ NOT statistically significant")

# ═══════════════════════════════════════════════════════════════════════
# THE REAL BIGGEST LEAKS
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("THE REAL BIGGEST LOSERS (sorted by total PnL, Sep 4+ only)")
print("=" * 80)

all_combos = long_combos + short_combos
all_combos.sort(key=lambda x: x['total_pnl'])
print(f"\n  {'Dir':5s} {'Phase':12s} {'LinReg':10s} {'#':>4s} {'WR%':>6s} {'PnL':>10s} {'AvgPnL':>8s} {'PF':>5s}")
print("  " + "-" * 63)
for c in all_combos:
    marker = ""
    if c['direction'] == 'LONG' and c['market_phase'] == 'DECLINING' and c['linreg_direction'] == 'LEAN_BULL':
        marker = " ◄ CLAIMED #1 LEAK"
    if c['direction'] == 'SHORT' and c['market_phase'] == 'CALM' and c['linreg_direction'] == 'LEAN_BULL':
        marker = " ◄ CLAIMED #1 SHORT LEAK"
    print(f"  {c['direction']:5s} {c['market_phase']:12s} {c['linreg_direction']:10s} {c['trades']:4d} {c['winrate']:5.1f}% ${c['total_pnl']:+9.2f} ${c['avg_pnl']:+7.3f} {c['profit_factor']:5.2f}{marker}")

# ═══════════════════════════════════════════════════════════════════════
# TEMPORAL STABILITY (within Sep 4-22 window)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("TEMPORAL STABILITY (Sep 4-22 window, split at midpoint)")
print("=" * 80)

all_times = sorted([t['open_time'] for t in enriched])
mid = all_times[len(all_times)//2]
early = [t for t in enriched if t['open_time'] <= mid]
late = [t for t in enriched if t['open_time'] > mid]
print(f"  Early: {all_times[0]} to {mid} ({len(early)} trades)")
print(f"  Late:  {mid} to {all_times[-1]} ({len(late)} trades)")

for direction, phase, lr, desc in [
    ('LONG', 'DECLINING', 'LEAN_BULL', 'Claim 1 leak'),
    ('SHORT', 'CALM', 'LEAN_BULL', 'Claim 2 leak'),
    ('LONG', 'CALM', 'NEUTRAL', 'Claim 3 best'),
    ('SHORT', 'DECLINING', 'NEUTRAL', 'Claim 4 best'),
]:
    print(f"\n  {desc} ({direction} {phase}+{lr}):")
    for label, subset in [("Early", early), ("Late", late)]:
        f = [t for t in subset if t['direction']==direction and t['market_phase']==phase and t['linreg_direction']==lr]
        n = len(f)
        if n == 0:
            print(f"    {label}: 0 trades")
        else:
            w = len([t for t in f if t['pnl'] > 0])
            p = sum(t['pnl'] for t in f)
            print(f"    {label}: {n} trades, {w}/{n}={w/n*100:.1f}% WR, ${p:.2f}")

print("\n" + "=" * 80)
print("AUDIT COMPLETE")
print("=" * 80)
