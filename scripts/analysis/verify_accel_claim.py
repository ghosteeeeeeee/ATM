#!/usr/bin/env python3
"""SKEPTICAL AUDIT: Verify whether the accel filter in rr_structural.py is backwards.

Computes BOTH accel metrics from raw candle data at ENTRY TIME for each rr-struct trade.
"""
import psycopg2
import sqlite3
import json
from datetime import datetime, timezone

# ── Connect to both databases ─────────────────────────────────────────────
pg = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
pg_cur = pg.cursor()

candles_db = sqlite3.connect('/root/.hermes/data/candles.db', timeout=10)
candles_cur = candles_db.cursor()

# ── Get all closed rr-struct trades ───────────────────────────────────────
pg_cur.execute("""
    SELECT id, token, direction, entry_price, exit_price, pnl_usdt, 
           open_time, close_time, _signal_metadata
    FROM trades 
    WHERE signal LIKE '%rr_struct%' AND status = 'closed'
    ORDER BY open_time
""")
trades = pg_cur.fetchall()
print(f"Total rr-struct closed trades: {len(trades)}")
print()

# ── Accel computation functions ───────────────────────────────────────────

def compute_rr_accel(token, entry_time):
    """RR accel from rr_structural.py: absolute price delta of delta.
    
    Takes last N 1m candle closes (default from RR_STRUCTURAL_ACCEL_LOOKBACK),
    splits into two halves, returns second_half_delta - first_half_delta.
    """
    try:
        candles_cur.execute("""
            SELECT close FROM candles_1m
            WHERE token = ? AND is_closed = 1 AND ts <= ?
            ORDER BY ts DESC LIMIT 31
        """, (token.upper(), int(entry_time.timestamp())))
        rows = candles_cur.fetchall()
        if len(rows) < 16:  # need at least lookback + 1
            return None
        closes = [r[0] for r in reversed(rows)]
        mid = len(closes) // 2
        first_half_delta = closes[mid] - closes[0]
        second_half_delta = closes[-1] - closes[mid]
        return second_half_delta - first_half_delta
    except Exception as e:
        print(f"  RR accel error for {token}: {e}")
        return None


def compute_metadata_accel(token, entry_time):
    """Metadata accel from speed_tracker.py: (vel_5m - vel_15m) / span.
    
    Uses average % price change per candle over 5m and 15m windows.
    Positive = momentum building, negative = momentum fading.
    """
    try:
        candles_cur.execute("""
            SELECT close FROM candles_1m
            WHERE token = ? AND is_closed = 1 AND ts <= ?
            ORDER BY ts DESC LIMIT 31
        """, (token.upper(), int(entry_time.timestamp())))
        rows = candles_cur.fetchall()
        if len(rows) < 16:
            return None
        closes = [r[0] for r in reversed(rows)]
        
        # Compute average velocity over windows
        def avg_vel(window):
            if len(closes) < window + 1:
                return None
            total = 0.0
            for i in range(1, window + 1):
                p_cur = closes[-i]
                p_prev = closes[-(i + 1)]
                if p_prev <= 0:
                    return None
                total += (p_cur - p_prev) / p_prev * 100
            return total / window
        
        vel_5m = avg_vel(5)
        vel_15m = avg_vel(15)
        
        if vel_5m is None or vel_15m is None:
            return None
        
        span = 15 - 5  # win_15m - win_5m
        accel = (vel_5m - vel_15m) / span
        return accel
    except Exception as e:
        print(f"  Metadata accel error for {token}: {e}")
        return None


# ── Analyze each trade ────────────────────────────────────────────────────
results = []
print(f"{'ID':<6} {'Token':<8} {'Dir':<6} {'PnL':>8} {'RR_Accel':>10} {'Meta_Accel':>10} {'RR_Aligned':>10} {'Meta_Aligned':>12} {'Result'}")
print("=" * 100)

for trade in trades:
    tid, token, direction, entry_price, exit_price, pnl, open_time, close_time, metadata = trade
    
    # Compute both accels at entry time
    rr_accel = compute_rr_accel(token, open_time)
    meta_accel = compute_metadata_accel(token, open_time)
    
    # Determine alignment with trade direction
    # For SHORT: aligned = negative accel (price going down), opposed = positive
    # For LONG: aligned = positive accel (price going up), opposed = negative
    if direction == 'SHORT':
        rr_aligned = rr_accel < 0 if rr_accel is not None else None
        meta_aligned = meta_accel < 0 if meta_accel is not None else None
    else:  # LONG
        rr_aligned = rr_accel > 0 if rr_accel is not None else None
        meta_aligned = meta_accel > 0 if meta_accel is not None else None
    
    result = "WIN" if pnl > 0 else "LOSS"
    
    results.append({
        'id': tid,
        'token': token,
        'direction': direction,
        'pnl': float(pnl),
        'rr_accel': rr_accel,
        'meta_accel': meta_accel,
        'rr_aligned': rr_aligned,
        'meta_aligned': meta_aligned,
        'result': result,
        'open_time': open_time,
        'entry_price': float(entry_price),
        'exit_price': float(exit_price) if exit_price else None,
    })
    
    rr_a_str = f"{rr_accel:+.6f}" if rr_accel is not None else "N/A"
    meta_a_str = f"{meta_accel:+.6f}" if meta_accel is not None else "N/A"
    rr_al_str = "ALIGNED" if rr_aligned else ("OPPOSED" if rr_aligned is False else "N/A")
    meta_al_str = "ALIGNED" if meta_aligned else ("OPPOSED" if meta_aligned is False else "N/A")
    
    print(f"{tid:<6} {token:<8} {direction:<6} {pnl:>+8.2f} {rr_a_str:>10} {meta_a_str:>10} {rr_al_str:>10} {meta_al_str:>12} {result}")

# ── Compute win rates ─────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("WIN RATE ANALYSIS")
print("=" * 80)

# RR accel
rr_aligned_trades = [r for r in results if r['rr_aligned'] is True]
rr_opposed_trades = [r for r in results if r['rr_aligned'] is False]

rr_aligned_wins = sum(1 for r in rr_aligned_trades if r['result'] == 'WIN')
rr_opposed_wins = sum(1 for r in rr_opposed_trades if r['result'] == 'WIN')

print(f"\nRR ACCEL (rr_structural.py):")
print(f"  ALIGNED  (accel in trade direction): {rr_aligned_wins}/{len(rr_aligned_trades)} = {rr_aligned_wins/len(rr_aligned_trades)*100:.1f}% WR" if rr_aligned_trades else "  ALIGNED: No trades")
print(f"  OPPOSED  (accel against trade dir): {rr_opposed_wins}/{len(rr_opposed_trades)} = {rr_opposed_wins/len(rr_opposed_trades)*100:.1f}% WR" if rr_opposed_trades else "  OPPOSED: No trades")

# Metadata accel
meta_aligned_trades = [r for r in results if r['meta_aligned'] is True]
meta_opposed_trades = [r for r in results if r['meta_aligned'] is False]

meta_aligned_wins = sum(1 for r in meta_aligned_trades if r['result'] == 'WIN')
meta_opposed_wins = sum(1 for r in meta_opposed_trades if r['result'] == 'WIN')

print(f"\nMETADATA ACCEL (speed_tracker.py):")
print(f"  ALIGNED  (accel in trade direction): {meta_aligned_wins}/{len(meta_aligned_trades)} = {meta_aligned_wins/len(meta_aligned_trades)*100:.1f}% WR" if meta_aligned_trades else "  ALIGNED: No trades")
print(f"  OPPOSED  (accel against trade dir): {meta_opposed_wins}/{len(meta_opposed_trades)} = {meta_opposed_wins/len(meta_opposed_trades)*100:.1f}% WR" if meta_opposed_trades else "  OPPOSED: No trades")

# ── Check what the FILTER would have blocked ──────────────────────────────
print("\n" + "=" * 80)
print("FILTER IMPACT ANALYSIS")
print("=" * 80)

# The rr_structural filter blocks:
# SHORT when accel > 0 (price going UP)
# LONG when accel < 0 (price going DOWN)
blocked_by_rr_filter = []
passed_by_rr_filter = []

for r in results:
    if r['rr_accel'] is None:
        passed_by_rr_filter.append(r)  # fail-open: no data = allow
        continue
    
    would_block = False
    if r['direction'] == 'SHORT' and r['rr_accel'] > 0:
        would_block = True
    elif r['direction'] == 'LONG' and r['rr_accel'] < 0:
        would_block = True
    
    if would_block:
        blocked_by_rr_filter.append(r)
    else:
        passed_by_rr_filter.append(r)

blocked_wins = sum(1 for r in blocked_by_rr_filter if r['result'] == 'WIN')
passed_wins = sum(1 for r in passed_by_rr_filter if r['result'] == 'WIN')

print(f"\nTrades BLOCKED by accel filter (opposed accel):")
for r in blocked_by_rr_filter:
    print(f"  {r['id']} {r['token']} {r['direction']} accel={r['rr_accel']:+.6f} → {r['result']} ${r['pnl']:+.2f}")
if blocked_by_rr_filter:
    print(f"  Summary: {blocked_wins}/{len(blocked_by_rr_filter)} = {blocked_wins/len(blocked_by_rr_filter)*100:.1f}% WR")
else:
    print(f"  No trades blocked")

print(f"\nTrades PASSED by accel filter (aligned accel or no data):")
for r in passed_by_rr_filter:
    accel_str = f"{r['rr_accel']:+.6f}" if r['rr_accel'] is not None else "N/A"
    print(f"  {r['id']} {r['token']} {r['direction']} accel={accel_str} → {r['result']} ${r['pnl']:+.2f}")
if passed_by_rr_filter:
    print(f"  Summary: {passed_wins}/{len(passed_by_rr_filter)} = {passed_wins/len(passed_by_rr_filter)*100:.1f}% WR")

# ── Check for TIMING issue ────────────────────────────────────────────────
print("\n" + "=" * 80)
print("TIMING CHECK: Acceleration at ENTRY vs CURRENT")
print("=" * 80)

# Check if accel values stored in metadata differ from what we computed at entry time
for r in results:
    if r['rr_accel'] is None:
        continue
    # Get stored metadata
    pg_cur.execute("SELECT _signal_metadata FROM trades WHERE id = %s", (r['id'],))
    row = pg_cur.fetchone()
    if row and row[0]:
        stored_accel = row[0].get('price_acceleration')
        if stored_accel is not None:
            diff = abs(r['rr_accel'] - stored_accel)
            if diff > 0.001:
                print(f"  {r['id']} {r['token']}: computed={r['rr_accel']:+.6f} stored={stored_accel:+.6f} diff={diff:.6f}")

# ── Extend to ALL SHORT trades ────────────────────────────────────────────
print("\n" + "=" * 80)
print("EXTENDED ANALYSIS: ALL SHORT trades (not just rr-struct)")
print("=" * 80)

pg_cur.execute("""
    SELECT id, token, direction, signal, entry_price, exit_price, pnl_usdt, 
           open_time, close_time, _signal_metadata
    FROM trades 
    WHERE direction = 'SHORT' AND status = 'closed'
    ORDER BY open_time
""")
all_shorts = pg_cur.fetchall()
print(f"Total SHORT closed trades: {len(all_shorts)}")

short_rr_aligned = 0
short_rr_opposed = 0
short_rr_aligned_wins = 0
short_rr_opposed_wins = 0
short_rr_none = 0

for trade in all_shorts:
    tid, token, direction, signal, entry_price, exit_price, pnl, open_time, close_time, metadata = trade
    rr_accel = compute_rr_accel(token, open_time)
    
    if rr_accel is None:
        short_rr_none += 1
        continue
    
    is_win = float(pnl) > 0
    if rr_accel < 0:  # Aligned with SHORT
        short_rr_aligned += 1
        if is_win:
            short_rr_aligned_wins += 1
    else:  # Opposed to SHORT
        short_rr_opposed += 1
        if is_win:
            short_rr_opposed_wins += 1

print(f"\nRR ACCEL for ALL SHORT trades:")
if short_rr_aligned:
    print(f"  ALIGNED (accel < 0): {short_rr_aligned_wins}/{short_rr_aligned} = {short_rr_aligned_wins/short_rr_aligned*100:.1f}% WR")
if short_rr_opposed:
    print(f"  OPPOSED (accel > 0): {short_rr_opposed_wins}/{short_rr_opposed} = {short_rr_opposed_wins/short_rr_opposed*100:.1f}% WR")
print(f"  No accel data: {short_rr_none}")

# ── Statistical significance check ────────────────────────────────────────
print("\n" + "=" * 80)
print("STATISTICAL SIGNIFICANCE")
print("=" * 80)

from scipy import stats
import math

def binomial_test(wins, total, expected_wr=0.5):
    """Two-tailed binomial test: is observed WR significantly different from expected?"""
    if total == 0:
        return None, None
    result = stats.binomtest(wins, total, expected_wr, alternative='two-sided')
    return result.pvalue, result.proportion_ci()

# Test RR accel alignment
if rr_aligned_trades and rr_opposed_trades:
    p_al, ci_al = binomial_test(rr_aligned_wins, len(rr_aligned_trades))
    p_op, ci_op = binomial_test(rr_opposed_wins, len(rr_opposed_trades))
    
    print(f"\nRR ALIGNED: {rr_aligned_wins}/{len(rr_aligned_trades)} = {rr_aligned_wins/len(rr_aligned_trades)*100:.1f}% WR")
    print(f"  p-value (H0: WR=50%): {p_al:.4f}")
    print(f"  95% CI: [{ci_al[0]*100:.1f}%, {ci_al[1]*100:.1f}%]")
    
    print(f"\nRR OPPOSED: {rr_opposed_wins}/{len(rr_opposed_trades)} = {rr_opposed_wins/len(rr_opposed_trades)*100:.1f}% WR")
    print(f"  p-value (H0: WR=50%): {p_op:.4f}")
    print(f"  95% CI: [{ci_op[0]*100:.1f}%, {ci_op[1]*100:.1f}%]")
    
    # Fisher's exact test: is there a difference between aligned vs opposed?
    if len(rr_aligned_trades) > 0 and len(rr_opposed_trades) > 0:
        table = [[rr_aligned_wins, len(rr_aligned_trades) - rr_aligned_wins],
                 [rr_opposed_wins, len(rr_opposed_trades) - rr_opposed_wins]]
        odds, p_fisher = stats.fisher_exact(table)
        print(f"\nFisher's exact test (aligned vs opposed):")
        print(f"  Odds ratio: {odds:.3f}")
        print(f"  p-value: {p_fisher:.4f}")
        print(f"  {'SIGNIFICANT' if p_fisher < 0.05 else 'NOT significant'} at α=0.05")

# Effect size and required sample
print(f"\nSample size analysis:")
total_trades = len(results)
rr_total = len(rr_aligned_trades) + len(rr_opposed_trades)
print(f"  Total trades analyzed: {total_trades}")
print(f"  RR accel trades (non-None): {rr_total}")
print(f"  RR aligned: {len(rr_aligned_trades)}")
print(f"  RR opposed: {len(rr_opposed_trades)}")

# How many trades needed for 80% power at α=0.05?
# Using arcsin approximation
if len(rr_opposed_trades) > 0 and len(rr_aligned_trades) > 0:
    observed_diff = abs(rr_opposed_wins/len(rr_opposed_trades) - rr_aligned_wins/len(rr_aligned_trades))
    print(f"\n  Observed WR difference: {observed_diff*100:.1f}%")
    if observed_diff > 0:
        # Required n for 80% power, two-sided, α=0.05
        # n = (Z_α/2 + Z_β)^2 * (p1*(1-p1) + p2*(1-p2)) / (p1-p2)^2
        z_alpha = 1.96
        z_beta = 0.84
        p1 = rr_aligned_wins/len(rr_aligned_trades)
        p2 = rr_opposed_wins/len(rr_opposed_trades)
        pooled = (p1*(1-p1)/len(rr_aligned_trades) + p2*(1-p2)/len(rr_opposed_trades))
        if pooled > 0 and observed_diff > 0:
            n_required = (z_alpha + z_beta)**2 * pooled / observed_diff**2
            print(f"  Approximate sample needed for 80% power: {n_required:.0f} per group")
            print(f"  Current per group: {len(rr_aligned_trades)} and {len(rr_opposed_trades)}")

pg.close()
candles_db.close()
