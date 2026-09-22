#!/usr/bin/env python3
"""
INDEPENDENT AUDIT: Verify LONG/SHORT continuum filter analysis
Verifies every number in the claims from scratch.
"""
import sys
import json
import math
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, '/root/.hermes/scripts')

# ─── PostgreSQL connection ────────────────────────────────────────────
from _secrets import BRAIN_DB_DICT
import psycopg2

# ─── SQLite connection ────────────────────────────────────────────────
import sqlite3

CONTINUUM_DB = '/root/.hermes/data/continuum.db'

# ═══════════════════════════════════════════════════════════════════════
# STEP 1: Load all trades with open_time, direction, pnl
# ═══════════════════════════════════════════════════════════════════════
print("=" * 80)
print("STEP 1: Loading trades from PostgreSQL brain DB")
print("=" * 80)

pg_conn = psycopg2.connect(**BRAIN_DB_DICT)
pg_cur = pg_conn.cursor()

pg_cur.execute("""
    SELECT id, token, direction, open_time, close_time, pnl_usdt, regime, volatility_regime,
           entry_trend, confidence, leverage, status
    FROM trades
    WHERE open_time IS NOT NULL
      AND pnl_usdt IS NOT NULL
      AND status = 'closed'
    ORDER BY open_time
""")
trades = pg_cur.fetchall()
print(f"Total closed trades with open_time and pnl: {len(trades)}")

# Direction distribution
long_trades = [t for t in trades if t[2] == 'LONG']
short_trades = [t for t in trades if t[2] == 'SHORT']
print(f"  LONG trades: {len(long_trades)}")
print(f"  SHORT trades: {len(short_trades)}")

# PnL stats
long_pnl = sum(t[5] for t in long_trades)
short_pnl = sum(t[5] for t in short_trades)
print(f"  LONG total PnL: ${long_pnl:.2f}")
print(f"  SHORT total PnL: ${short_pnl:.2f}")
print(f"  All trades PnL: ${long_pnl + short_pnl:.2f}")

pg_cur.close()
pg_conn.close()

# ═══════════════════════════════════════════════════════════════════════
# STEP 2: Load BTC continuum states (market-level context)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 2: Loading BTC continuum states from SQLite")
print("=" * 80)

ct_conn = sqlite3.connect(CONTINUUM_DB)
ct_cur = ct_conn.cursor()

ct_cur.execute("""
    SELECT ts, market_phase, linreg_direction, ema300_position, trend_quality,
           volume_regime, state_score
    FROM continuum_states
    ORDER BY ts
""")
states = ct_cur.fetchall()
print(f"Total continuum states: {len(states)}")
print(f"Date range: {datetime.fromtimestamp(states[0][0])} to {datetime.fromtimestamp(states[-1][0])}")

ct_cur.close()
ct_conn.close()

# Build a lookup: for each 1-minute bucket, store the state
# The states are at 1-minute intervals, so we can use binary search
state_times = [s[0] for s in states]

def find_state_for_ts(ts):
    """Find the continuum state closest to a given timestamp."""
    ts_epoch = int(ts.timestamp()) if isinstance(ts, datetime) else int(ts)
    # Binary search
    lo, hi = 0, len(state_times) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if state_times[mid] < ts_epoch:
            lo = mid + 1
        else:
            hi = mid
    # lo is now the first index where state_times[lo] >= ts_epoch
    # Pick the closest
    if lo > 0:
        if abs(state_times[lo] - ts_epoch) < abs(state_times[lo-1] - ts_epoch):
            return states[lo]
        else:
            return states[lo-1]
    return states[lo]

# ═══════════════════════════════════════════════════════════════════════
# STEP 3: Join trades with continuum states
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 3: Joining trades with BTC continuum states at trade open time")
print("=" * 80)

enriched_trades = []
skipped = 0
for t in trades:
    trade_id, token, direction, open_time, close_time, pnl, regime, vol_regime, trend, conf, lev, status = t
    state = find_state_for_ts(open_time)
    if state:
        ts, market_phase, linreg_dir, ema_pos, trend_qual, vol_reg, state_score = state
        enriched_trades.append({
            'id': trade_id,
            'token': token,
            'direction': direction,
            'open_time': open_time,
            'close_time': close_time,
            'pnl': float(pnl) if pnl else 0.0,
            'market_phase': market_phase,
            'linreg_direction': linreg_dir,
            'ema300_position': ema_pos,
            'trend_quality': trend_qual,
            'volume_regime': vol_reg,
            'state_score': state_score,
            'time_delta_seconds': abs((open_time - datetime.fromtimestamp(ts)).total_seconds()),
        })
    else:
        skipped += 1

print(f"Enriched trades: {len(enriched_trades)}")
print(f"Skipped (no state match): {skipped}")

# Time delta stats
deltas = [e['time_delta_seconds'] for e in enriched_trades]
print(f"Time delta to nearest state: min={min(deltas):.0f}s, max={max(deltas):.0f}s, avg={sum(deltas)/len(deltas):.0f}s, median={sorted(deltas)[len(deltas)//2]:.0f}s")
# Trades with >5min delta
big_delta = [d for d in deltas if d > 300]
print(f"Trades with >5min delta: {len(big_delta)} ({len(big_delta)/len(deltas)*100:.1f}%)")

# ═══════════════════════════════════════════════════════════════════════
# STEP 4: Verify Claim 1 - LONG in DECLINING + LEAN_BULL
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 4: Verifying Claim 1 - LONG in DECLINING + LEAN_BULL")
print("=" * 80)

def analyze_combo(trades_list, direction, market_phase, linreg_dir):
    """Analyze a specific direction + market_phase + linreg_direction combo."""
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
    # Profit factor
    gross_profit = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    return {
        'direction': direction,
        'market_phase': market_phase,
        'linreg_direction': linreg_dir,
        'trades': n,
        'wins': len(wins),
        'losses': len(losses),
        'winrate': winrate,
        'total_pnl': total_pnl,
        'avg_pnl': avg_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
    }

# Claim: LONG in DECLINING + LEAN_BULL = 93 trades, 51% WR, -$0.82 PnL
result = analyze_combo(enriched_trades, 'LONG', 'DECLINING', 'LEAN_BULL')
if result:
    print(f"  CLAIM: 93 trades, 51% WR, -$0.82 PnL")
    print(f"  FOUND: {result['trades']} trades, {result['winrate']:.1f}% WR, ${result['total_pnl']:.2f} PnL")
    print(f"  Avg PnL per trade: ${result['avg_pnl']:.2f}")
    print(f"  Avg win: ${result['avg_win']:.2f}, Avg loss: ${result['avg_loss']:.2f}")
    print(f"  Profit factor: {result['profit_factor']:.2f}")
    # Check claims
    trade_match = result['trades'] == 93
    wr_match = abs(result['winrate'] - 51) <= 2
    pnl_match = abs(result['total_pnl'] - (-0.82)) <= 0.2
    print(f"  Trades match: {'✅' if trade_match else '❌'} (claimed 93, found {result['trades']})")
    print(f"  WR match: {'✅' if wr_match else '❌'} (claimed 51%, found {result['winrate']:.1f}%)")
    print(f"  PnL match: {'✅' if pnl_match else '❌'} (claimed -$0.82, found ${result['total_pnl']:.2f})")
else:
    print("  ❌ No trades found for this combo!")

# ═══════════════════════════════════════════════════════════════════════
# STEP 5: Verify Claim 2 - SHORT in CALM + LEAN_BULL
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 5: Verifying Claim 2 - SHORT in CALM + LEAN_BULL")
print("=" * 80)

result = analyze_combo(enriched_trades, 'SHORT', 'CALM', 'LEAN_BULL')
if result:
    print(f"  CLAIM: 29 trades, 41% WR, -$1.08 PnL")
    print(f"  FOUND: {result['trades']} trades, {result['winrate']:.1f}% WR, ${result['total_pnl']:.2f} PnL")
    print(f"  Avg PnL per trade: ${result['avg_pnl']:.2f}")
    print(f"  Profit factor: {result['profit_factor']:.2f}")
    trade_match = result['trades'] == 29
    wr_match = abs(result['winrate'] - 41) <= 2
    pnl_match = abs(result['total_pnl'] - (-1.08)) <= 0.2
    print(f"  Trades match: {'✅' if trade_match else '❌'} (claimed 29, found {result['trades']})")
    print(f"  WR match: {'✅' if wr_match else '❌'} (claimed 41%, found {result['winrate']:.1f}%)")
    print(f"  PnL match: {'✅' if pnl_match else '❌'} (claimed -$1.08, found ${result['total_pnl']:.2f})")
else:
    print("  ❌ No trades found for this combo!")

# ═══════════════════════════════════════════════════════════════════════
# STEP 6: Verify Claim 3 - Best LONG combo: CALM + NEUTRAL
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 6: Verifying Claim 3 - Best LONG combo: CALM + NEUTRAL")
print("=" * 80)

# Get all LONG combos
phases = ['CALM', 'DECLINING', 'RECOVERY']
directions_linreg = ['LEAN_BULL', 'LEAN_BEAR', 'NEUTRAL', 'BULL', 'BEAR']

print("\n  All LONG combos:")
long_combos = []
for phase in phases:
    for linreg in directions_linreg:
        result = analyze_combo(enriched_trades, 'LONG', phase, linreg)
        if result:
            long_combos.append(result)
            marker = " <-- CLAIMED BEST" if (phase == 'CALM' and linreg == 'NEUTRAL') else ""
            print(f"    {phase} + {linreg:10s}: {result['trades']:4d} trades, {result['winrate']:5.1f}% WR, ${result['total_pnl']:+8.2f} PnL, PF={result['profit_factor']:.2f}{marker}")

# Sort by PnL
long_combos.sort(key=lambda x: x['total_pnl'], reverse=True)
if long_combos:
    best = long_combos[0]
    print(f"\n  Best LONG combo by PnL: {best['market_phase']} + {best['linreg_direction']}")
    print(f"    {best['trades']} trades, {best['winrate']:.1f}% WR, ${best['total_pnl']:.2f} PnL")
    # Also sort by avg_pnl
    long_combos_by_avg = sorted(long_combos, key=lambda x: x['avg_pnl'], reverse=True)
    best_avg = long_combos_by_avg[0]
    print(f"\n  Best LONG combo by avg PnL: {best_avg['market_phase']} + {best_avg['linreg_direction']}")
    print(f"    {best_avg['trades']} trades, {best_avg['winrate']:.1f}% WR, ${best_avg['avg_pnl']:.2f} avg PnL")

# Check CALM + NEUTRAL specifically
result_cn = analyze_combo(enriched_trades, 'LONG', 'CALM', 'NEUTRAL')
if result_cn:
    print(f"\n  CLAIM: CALM + NEUTRAL = 19 trades, 74% WR, +$0.65 PnL")
    print(f"  FOUND: {result_cn['trades']} trades, {result_cn['winrate']:.1f}% WR, ${result_cn['total_pnl']:.2f} PnL")
else:
    print(f"\n  ❌ CALM + NEUTRAL combo has no trades!")

# ═══════════════════════════════════════════════════════════════════════
# STEP 7: Verify Claim 4 - Best SHORT combo: DECLINING + NEUTRAL
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 7: Verifying Claim 4 - Best SHORT combo: DECLINING + NEUTRAL")
print("=" * 80)

print("\n  All SHORT combos:")
short_combos = []
for phase in phases:
    for linreg in directions_linreg:
        result = analyze_combo(enriched_trades, 'SHORT', phase, linreg)
        if result:
            short_combos.append(result)
            marker = " <-- CLAIMED BEST" if (phase == 'DECLINING' and linreg == 'NEUTRAL') else ""
            print(f"    {phase} + {linreg:10s}: {result['trades']:4d} trades, {result['winrate']:5.1f}% WR, ${result['total_pnl']:+8.2f} PnL, PF={result['profit_factor']:.2f}{marker}")

short_combos.sort(key=lambda x: x['total_pnl'], reverse=True)
if short_combos:
    best = short_combos[0]
    print(f"\n  Best SHORT combo by PnL: {best['market_phase']} + {best['linreg_direction']}")
    print(f"    {best['trades']} trades, {best['winrate']:.1f}% WR, ${best['total_pnl']:.2f} PnL")
    short_combos_by_avg = sorted(short_combos, key=lambda x: x['avg_pnl'], reverse=True)
    best_avg = short_combos_by_avg[0]
    print(f"\n  Best SHORT combo by avg PnL: {best_avg['market_phase']} + {best_avg['linreg_direction']}")
    print(f"    {best_avg['trades']} trades, {best_avg['winrate']:.1f}% WR, ${best_avg['avg_pnl']:.2f} avg PnL")

result_dn = analyze_combo(enriched_trades, 'SHORT', 'DECLINING', 'NEUTRAL')
if result_dn:
    print(f"\n  CLAIM: DECLINING + NEUTRAL = 12 trades, 67% WR, +$0.25 PnL")
    print(f"  FOUND: {result_dn['trades']} trades, {result_dn['winrate']:.1f}% WR, ${result_dn['total_pnl']:.2f} PnL")
else:
    print(f"\n  ❌ DECLINING + NEUTRAL combo has no trades!")

# ═══════════════════════════════════════════════════════════════════════
# STEP 8: Statistical significance of small sample sizes
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 8: Statistical significance analysis")
print("=" * 80)

def confidence_interval_wr(n, wins, confidence=0.95):
    """Wilson score interval for win rate."""
    if n == 0:
        return (0, 0)
    p = wins / n
    z = 1.96  # 95% CI
    denominator = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denominator
    margin = z * math.sqrt((p*(1-p) + z**2/(4*n)) / n) / denominator
    return (max(0, center - margin), min(1, center + margin))

def bootstrap_pnl_ci(pnls, n_bootstrap=10000, confidence=0.95):
    """Bootstrap confidence interval for mean PnL."""
    import random
    n = len(pnls)
    if n < 5:
        return None, None, None
    means = []
    for _ in range(n_bootstrap):
        sample = random.choices(pnls, k=n)
        means.append(sum(sample) / len(sample))
    means.sort()
    lo_idx = int((1 - confidence) / 2 * n_bootstrap)
    hi_idx = int((1 + confidence) / 2 * n_bootstrap)
    return means[lo_idx], sum(pnls)/n, means[hi_idx]

# Key combos to check significance
key_combos = [
    ('LONG', 'DECLINING', 'LEAN_BULL', 'Claim 1: Biggest LONG leak'),
    ('SHORT', 'CALM', 'LEAN_BULL', 'Claim 2: Biggest SHORT leak'),
    ('LONG', 'CALM', 'NEUTRAL', 'Claim 3: Best LONG'),
    ('SHORT', 'DECLINING', 'NEUTRAL', 'Claim 4: Best SHORT'),
]

import random
random.seed(42)

for direction, phase, linreg, desc in key_combos:
    filtered = [t for t in enriched_trades
                if t['direction'] == direction
                and t['market_phase'] == phase
                and t['linreg_direction'] == linreg]
    n = len(filtered)
    wins = len([t for t in filtered if t['pnl'] > 0])
    pnls = [t['pnl'] for t in filtered]

    print(f"\n  {desc}:")
    print(f"    {direction} {phase}+{linreg}: n={n}")

    if n == 0:
        print(f"    ❌ No trades - cannot assess")
        continue

    ci = confidence_interval_wr(n, wins)
    print(f"    Win rate: {wins}/{n} = {wins/n*100:.1f}%")
    print(f"    95% CI for WR: [{ci[0]*100:.1f}%, {ci[1]*100:.1f}%]")

    # Check if CI is wide (>20%)
    ci_width = ci[1] - ci[0]
    if ci_width > 0.20:
        print(f"    ⚠️  CI width is {ci_width*100:.1f}% — VERY UNCERTAIN, sample too small for reliable conclusions")
    elif ci_width > 0.15:
        print(f"    ⚠️  CI width is {ci_width*100:.1f}% — somewhat uncertain")
    else:
        print(f"    CI width: {ci_width*100:.1f}% — reasonable precision")

    if n >= 5:
        lo, mean, hi = bootstrap_pnl_ci(pnls)
        print(f"    Mean PnL: ${mean:.3f}")
        print(f"    95% CI for PnL: [${lo:.3f}, ${hi:.3f}]")
        if lo > 0:
            print(f"    ✅ PnL CI is entirely positive — statistically significant PROFIT")
        elif hi < 0:
            print(f"    ✅ PnL CI is entirely negative — statistically significant LOSS")
        else:
            print(f"    ⚠️  PnL CI crosses zero — NOT statistically significant")

    # Rule of thumb: need at least 30 trades for reliable win rate estimate
    if n < 30:
        print(f"    ⚠️  Sample size {n} < 30: results may be noise, not signal")
    else:
        print(f"    Sample size {n} >= 30: reasonable for statistical inference")

# ═══════════════════════════════════════════════════════════════════════
# STEP 9: Temporal stability analysis
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 9: Temporal stability — do combos work across time periods?")
print("=" * 80)

# Split into halves
all_times = sorted([t['open_time'] for t in enriched_trades])
midpoint = all_times[len(all_times)//2]
print(f"Midpoint: {midpoint}")
print(f"First half: {all_times[0]} to {midpoint}")
print(f"Second half: {midpoint} to {all_times[-1]}")

early_trades = [t for t in enriched_trades if t['open_time'] <= midpoint]
late_trades = [t for t in enriched_trades if t['open_time'] > midpoint]
print(f"Early trades: {len(early_trades)}, Late trades: {len(late_trades)}")

for direction, phase, linreg, desc in key_combos:
    print(f"\n  {desc} ({direction} {phase}+{linreg}):")

    early = [t for t in early_trades
             if t['direction'] == direction
             and t['market_phase'] == phase
             and t['linreg_direction'] == linreg]
    late = [t for t in late_trades
            if t['direction'] == direction
            and t['market_phase'] == phase
            and t['linreg_direction'] == linreg]

    for label, subset in [("  First half", early), ("  Second half", late)]:
        n = len(subset)
        if n == 0:
            print(f"{label}: 0 trades")
            continue
        wins = len([t for t in subset if t['pnl'] > 0])
        pnl = sum(t['pnl'] for t in subset)
        print(f"{label}: {n} trades, {wins}/{n} = {wins/n*100:.1f}% WR, ${pnl:.2f} PnL")

# ═══════════════════════════════════════════════════════════════════════
# STEP 10: Combined filter impact
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 10: Combined filter impact — block LONG DECLINING+LEAN_BULL AND block SHORT CALM+LEAN_BULL")
print("=" * 80)

# Without any filter
all_long = [t for t in enriched_trades if t['direction'] == 'LONG']
all_short = [t for t in enriched_trades if t['direction'] == 'SHORT']
all_trades_no_filter = all_long + all_short

def stats(label, trades_list):
    n = len(trades_list)
    if n == 0:
        print(f"  {label}: 0 trades")
        return
    wins = len([t for t in trades_list if t['pnl'] > 0])
    total_pnl = sum(t['pnl'] for t in trades_list)
    avg_pnl = total_pnl / n
    winrate = wins / n * 100
    print(f"  {label}: {n} trades, {wins}/{n} = {winrate:.1f}% WR, ${total_pnl:.2f} total PnL, ${avg_pnl:.3f} avg PnL")

print("\n  Baseline (no filter):")
stats("All trades", all_trades_no_filter)
stats("  LONG only", all_long)
stats("  SHORT only", all_short)

# Apply recommended filters:
# Block LONG when DECLINING + LEAN_BULL
# Block SHORT when CALM + LEAN_BULL
filtered_trades = []
blocked_long = []
blocked_short = []
for t in enriched_trades:
    if t['direction'] == 'LONG' and t['market_phase'] == 'DECLINING' and t['linreg_direction'] == 'LEAN_BULL':
        blocked_long.append(t)
    elif t['direction'] == 'SHORT' and t['market_phase'] == 'CALM' and t['linreg_direction'] == 'LEAN_BULL':
        blocked_short.append(t)
    else:
        filtered_trades.append(t)

print(f"\n  After applying recommended filters:")
print(f"  Blocked LONG (DECLINING+LEAN_BULL): {len(blocked_long)} trades")
print(f"  Blocked SHORT (CALM+LEAN_BULL): {len(blocked_short)} trades")
print(f"  Remaining trades: {len(filtered_trades)}")

filtered_long = [t for t in filtered_trades if t['direction'] == 'LONG']
filtered_short = [t for t in filtered_trades if t['direction'] == 'SHORT']
stats("All trades (filtered)", filtered_trades)
stats("  LONG (filtered)", filtered_long)
stats("  SHORT (filtered)", filtered_short)

# Improvement
baseline_pnl = sum(t['pnl'] for t in all_trades_no_filter)
filtered_pnl = sum(t['pnl'] for t in filtered_trades)
improvement = filtered_pnl - baseline_pnl
# Remove the blocked trades' PnL
blocked_pnl = sum(t['pnl'] for t in blocked_long) + sum(t['pnl'] for t in blocked_short)
print(f"\n  Blocked trades PnL: ${blocked_pnl:.2f}")
print(f"  Improvement from filtering: ${improvement:.2f}")

# ═══════════════════════════════════════════════════════════════════════
# STEP 11: What if we ONLY use these two filters (net effect)?
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 11: Net effect of both filters combined")
print("=" * 80)

# Baseline: total PnL
print(f"\n  Baseline total PnL (no filters): ${baseline_pnl:.2f}")
print(f"  Baseline total trades: {len(all_trades_no_filter)}")

# After both filters
print(f"  After filters total PnL: ${filtered_pnl:.2f}")
print(f"  After filters total trades: {len(filtered_trades)}")
print(f"  Net PnL improvement: ${improvement:.2f}")
if len(all_trades_no_filter) > 0 and len(filtered_trades) > 0:
    base_avg = baseline_pnl / len(all_trades_no_filter)
    filt_avg = filtered_pnl / len(filtered_trades)
    print(f"  Baseline avg PnL/trade: ${base_avg:.4f}")
    print(f"  Filtered avg PnL/trade: ${filt_avg:.4f}")
    print(f"  Avg PnL improvement: ${filt_avg - base_avg:.4f}")

# ═══════════════════════════════════════════════════════════════════════
# STEP 12: Is the improvement statistically significant?
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 12: Is the improvement statistically significant?")
print("=" * 80)

import random
random.seed(42)

# Bootstrap: compare baseline mean PnL vs filtered mean PnL
baseline_pnls = [t['pnl'] for t in all_trades_no_filter]
filtered_pnls = [t['pnl'] for t in filtered_trades]
blocked_pnls = [t['pnl'] for t in blocked_long + blocked_short]

print(f"\n  Baseline mean PnL: ${sum(baseline_pnls)/len(baseline_pnls):.4f}")
print(f"  Filtered mean PnL: ${sum(filtered_pnls)/len(filtered_pnls):.4f}")
print(f"  Blocked mean PnL: ${sum(blocked_pnls)/len(blocked_pnls):.4f}" if blocked_pnls else "  Blocked mean PnL: N/A")

# Paired bootstrap: resample both with same indices, compute difference
n_bootstrap = 10000
improvements = []
for _ in range(n_bootstrap):
    # Resample blocked trades
    sample_blocked = random.choices(blocked_pnls, k=len(blocked_pnls))
    # These would have been in the baseline but removed in filtered
    # Improvement = removing these trades
    improvement_sample = -sum(sample_blocked) / len(all_trades_no_filter)  # improvement from removing
    improvements.append(improvement_sample)

improvements.sort()
lo = improvements[int(0.025 * n_bootstrap)]
hi = improvements[int(0.975 * n_bootstrap)]
mean_imp = sum(improvements) / len(improvements)

print(f"\n  Bootstrap improvement estimate:")
print(f"    Mean: ${mean_imp:.4f} per trade")
print(f"    95% CI: [${lo:.4f}, ${hi:.4f}]")
if lo > 0:
    print(f"    ✅ Statistically significant improvement (CI > 0)")
elif hi < 0:
    print(f"    ❌ Statistically significant WORSENING (CI < 0)")
else:
    print(f"    ⚠️  NOT statistically significant (CI crosses zero)")

# ═══════════════════════════════════════════════════════════════════════
# STEP 13: Full combo table for context
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 13: Full combo performance table")
print("=" * 80)

print(f"\n  {'Direction':8s} {'Phase':12s} {'LinReg':10s} {'Trades':>6s} {'WR%':>6s} {'TotalPnL':>10s} {'AvgPnL':>8s} {'PF':>6s}")
print("  " + "-" * 72)

all_combos = []
for direction in ['LONG', 'SHORT']:
    for phase in phases:
        for linreg in directions_linreg:
            result = analyze_combo(enriched_trades, direction, phase, linreg)
            if result:
                all_combos.append(result)

all_combos.sort(key=lambda x: x['total_pnl'])
for c in all_combos:
    print(f"  {c['direction']:8s} {c['market_phase']:12s} {c['linreg_direction']:10s} {c['trades']:6d} {c['winrate']:5.1f}% ${c['total_pnl']:+9.2f} ${c['avg_pnl']:+7.3f} {c['profit_factor']:5.2f}")

# ═══════════════════════════════════════════════════════════════════════
# STEP 14: Check if the leaks are from specific tokens or time periods
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 14: Deep dive into biggest leak — LONG DECLINING+LEAN_BULL")
print("=" * 80)

leak_trades = [t for t in enriched_trades
               if t['direction'] == 'LONG'
               and t['market_phase'] == 'DECLINING'
               and t['linreg_direction'] == 'LEAN_BULL']

# By token
token_pnl = defaultdict(lambda: {'count': 0, 'pnl': 0, 'wins': 0})
for t in leak_trades:
    token_pnl[t['token']]['count'] += 1
    token_pnl[t['token']]['pnl'] += t['pnl']
    if t['pnl'] > 0:
        token_pnl[t['token']]['wins'] += 1

print(f"\n  Token breakdown ({len(leak_trades)} trades):")
for token, data in sorted(token_pnl.items(), key=lambda x: x[1]['pnl']):
    wr = data['wins'] / data['count'] * 100
    print(f"    {token:8s}: {data['count']:3d} trades, {wr:5.1f}% WR, ${data['pnl']:+.2f}")

# By month
month_pnl = defaultdict(lambda: {'count': 0, 'pnl': 0, 'wins': 0})
for t in leak_trades:
    month = t['open_time'].strftime('%Y-%m')
    month_pnl[month]['count'] += 1
    month_pnl[month]['pnl'] += t['pnl']
    if t['pnl'] > 0:
        month_pnl[month]['wins'] += 1

print(f"\n  Monthly breakdown:")
for month in sorted(month_pnl.keys()):
    data = month_pnl[month]
    wr = data['wins'] / data['count'] * 100
    print(f"    {month}: {data['count']:3d} trades, {wr:5.1f}% WR, ${data['pnl']:+.2f}")

# Check: are these mostly SL hits or bad entries?
print(f"\n  Time-of-day breakdown (UTC hour):")
hour_pnl = defaultdict(lambda: {'count': 0, 'pnl': 0, 'wins': 0})
for t in leak_trades:
    hour = t['open_time'].hour
    hour_pnl[hour]['count'] += 1
    hour_pnl[hour]['pnl'] += t['pnl']
    if t['pnl'] > 0:
        hour_pnl[hour]['wins'] += 1

for hour in sorted(hour_pnl.keys()):
    data = hour_pnl[hour]
    wr = data['wins'] / data['count'] * 100
    print(f"    {hour:02d}:00 UTC: {data['count']:3d} trades, {wr:5.1f}% WR, ${data['pnl']:+.2f}")

print("\n" + "=" * 80)
print("AUDIT COMPLETE")
print("=" * 80)
