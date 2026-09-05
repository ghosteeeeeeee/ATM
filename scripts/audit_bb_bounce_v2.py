#!/usr/bin/env python3
"""Independent audit of bb_bounce_v2_long trades — compute metrics from 5m candles."""

import sqlite3
import time
import statistics
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'
CANDLES_DB = '/root/.hermes/data/candles.db'

# Parameters from hermes_constants.py (current v2 settings)
BB_PERIOD = 20
BB_STDDEV = 1.8
BB_TOUCH_PCT = 0.15
BB_WIDTH_MAX = 0.5
RSI_PERIOD = 14
RSI_MAX = 45
BOUNCE_MIN_PCT = 0.10
VEL_MIN = -0.01
MOM_MIN = 0.0
VOL_MAX = 0.5
MIN_AGE_SEC = 600


def compute_bb(closes, period=BB_PERIOD, stddev=BB_STDDEV):
    if len(closes) < period:
        return None, None, None, None
    middle = sum(closes[-period:]) / period
    variance = sum((c - middle) ** 2 for c in closes[-period:]) / period
    std = variance ** 0.5
    upper = middle + stddev * std
    lower = middle - stddev * std
    width = (upper - lower) / middle * 100 if middle > 0 else 0
    return middle, upper, lower, width


def compute_rsi(closes, period=RSI_PERIOD):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        delta = closes[-i] - closes[-i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains) / len(gains) if gains else 0
    avg_loss = sum(losses) / len(losses) if losses else 0.001
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))


def get_5m_closes_at_time(token, entry_ts, lookback=100):
    """Get 5m closes leading up to entry time."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_5m
            WHERE token = ? AND ts <= ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), entry_ts, lookback))
        rows = cur.fetchall()
        return [r[0] for r in reversed(rows)] if rows else []
    except Exception as e:
        print(f"Error getting 5m candles for {token}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_1m_closes_at_time(token, entry_ts, lookback=30):
    """Get 1m closes leading up to entry time."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_1m
            WHERE token = ? AND ts <= ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), entry_ts, lookback))
        rows = cur.fetchall()
        return [r[0] for r in reversed(rows)] if rows else []
    except Exception as e:
        print(f"Error getting 1m candles for {token}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_1m_volatility_at_time(token, entry_ts):
    """Get average volatility (range %) of last 10 1m candles at entry time."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT high, low, close FROM candles_1m
            WHERE token = ? AND ts <= ?
            ORDER BY ts DESC
            LIMIT 10
        """, (token.upper(), entry_ts))
        rows = cur.fetchall()
        if len(rows) < 5:
            return None
        ranges = [(r[0] - r[1]) / r[2] * 100 for r in rows if r[2] > 0]
        return statistics.mean(ranges) if ranges else None
    except Exception as e:
        print(f"Error getting volatility for {token}: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_15m_velocity_at_time(token, entry_ts):
    """15m price velocity (% change over last 15 minutes) at entry time."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT close FROM candles_1m
            WHERE token = ? AND ts <= ?
            ORDER BY ts DESC LIMIT 15
        """, (token.upper(), entry_ts))
        rows = c.fetchall()
        if len(rows) < 5:
            return None
        closes = [r[0] for r in reversed(rows)]
        if closes[0] <= 0:
            return None
        return (closes[-1] - closes[0]) / closes[0] * 100
    except Exception as e:
        print(f"Error getting velocity for {token}: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_30m_momentum_at_time(token, entry_ts):
    """30m momentum via linear regression slope of 1m closes at entry time."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT close FROM candles_1m
            WHERE token = ? AND ts <= ?
            ORDER BY ts DESC LIMIT 30
        """, (token.upper(), entry_ts))
        rows = c.fetchall()
        if len(rows) < 10:
            return None
        closes = [r[0] for r in reversed(rows)]
        n = len(closes)
        x_mean = (n - 1) / 2
        y_mean = sum(closes) / n
        num = sum((i - x_mean) * (closes[i] - y_mean) for i in range(n))
        den = sum((i - x_mean) ** 2 for i in range(n))
        return (num / den / y_mean * 100) if den > 0 and y_mean > 0 else 0
    except Exception as e:
        print(f"Error getting momentum for {token}: {e}")
        return None
    finally:
        if conn:
            conn.close()


def parse_ts(ts_str):
    """Parse timestamp string to epoch seconds."""
    from datetime import datetime
    try:
        dt = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
        return int(dt.timestamp())
    except:
        return None


def main():
    # Get all bb_bounce_v2_long trades
    conn = sqlite3.connect(RUNTIME_DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT token, direction, signal_type, is_win, pnl_pct, pnl_usdt, created_at, regime
        FROM signal_outcomes 
        WHERE signal_type LIKE '%bb_bounce_v2_long%'
        ORDER BY created_at
    """)
    trades = cur.fetchall()
    conn.close()

    print(f"Found {len(trades)} bb_bounce_v2_long trades")
    print(f"Current parameters: BB_WIDTH_MAX={BB_WIDTH_MAX}%, RSI_MAX={RSI_MAX}, BOUNCE_MIN={BOUNCE_MIN_PCT}%")
    print()

    results = []
    for token, direction, sig_type, is_win, pnl_pct, pnl_usdt, created_at, regime in trades:
        entry_ts = parse_ts(created_at)
        if entry_ts is None:
            print(f"Could not parse timestamp for {token} {created_at}")
            continue

        # Get 5m closes at entry time
        closes_5m = get_5m_closes_at_time(token, entry_ts)
        if len(closes_5m) < BB_PERIOD + 5:
            print(f"Insufficient 5m data for {token} at {created_at}: {len(closes_5m)} bars")
            continue

        # Compute metrics
        middle, upper, lower, bb_width = compute_bb(closes_5m)
        rsi = compute_rsi(closes_5m)
        
        current = closes_5m[-1]
        bounce_pct = (current - lower) / lower * 100 if lower and lower > 0 else 0
        dist_from_lower = abs(current - lower) / lower * 100 if lower and lower > 0 else 999

        # Get velocity, momentum, volatility
        vel = get_15m_velocity_at_time(token, entry_ts)
        mom = get_30m_momentum_at_time(token, entry_ts)
        vol = get_1m_volatility_at_time(token, entry_ts)

        result = {
            'token': token,
            'is_win': is_win,
            'pnl_pct': pnl_pct,
            'pnl_usdt': pnl_usdt,
            'regime': regime,
            'bb_width': bb_width,
            'rsi': rsi,
            'bounce_pct': bounce_pct,
            'dist_from_lower': dist_from_lower,
            'velocity': vel,
            'momentum': mom,
            'volatility': vol,
            'current': current,
            'lower': lower,
            'middle': middle,
        }
        results.append(result)

    # Separate winners and losers
    winners = [r for r in results if r['is_win'] == 1]
    losers = [r for r in results if r['is_win'] == 0]

    print(f"\n{'='*80}")
    print(f"RESULTS: {len(winners)} winners, {len(losers)} losers out of {len(results)} total")
    print(f"{'='*80}")

    # Print each trade's metrics
    print(f"\n{'Token':<8} {'Win':>4} {'PnL%':>8} {'BB_W%':>8} {'RSI':>6} {'Bounce%':>8} {'Vel%':>8} {'Mom':>8} {'Vol%':>8} {'Regime':<10}")
    print("-" * 100)
    for r in results:
        win_str = "W" if r['is_win'] else "L"
        bb_str = f"{r['bb_width']:.2f}" if r['bb_width'] is not None else "N/A"
        rsi_str = f"{r['rsi']:.1f}" if r['rsi'] is not None else "N/A"
        bounce_str = f"{r['bounce_pct']:.2f}" if r['bounce_pct'] is not None else "N/A"
        vel_str = f"{r['velocity']:.3f}" if r['velocity'] is not None else "N/A"
        mom_str = f"{r['momentum']:.4f}" if r['momentum'] is not None else "N/A"
        vol_str = f"{r['volatility']:.3f}" if r['volatility'] is not None else "N/A"
        print(f"{r['token']:<8} {win_str:>4} {r['pnl_pct']:>8.2f} {bb_str:>8} {rsi_str:>6} {bounce_str:>8} {vel_str:>8} {mom_str:>8} {vol_str:>8} {r['regime']:<10}")

    # Statistical comparison
    print(f"\n{'='*80}")
    print("STATISTICAL COMPARISON: WINNERS vs LOSERS")
    print(f"{'='*80}")

    def stats_for(label, trades_list):
        if not trades_list:
            print(f"\n{label}: No trades")
            return
        
        bb_vals = [r['bb_width'] for r in trades_list if r['bb_width'] is not None]
        rsi_vals = [r['rsi'] for r in trades_list if r['rsi'] is not None]
        bounce_vals = [r['bounce_pct'] for r in trades_list if r['bounce_pct'] is not None]
        vel_vals = [r['velocity'] for r in trades_list if r['velocity'] is not None]
        mom_vals = [r['momentum'] for r in trades_list if r['momentum'] is not None]
        vol_vals = [r['volatility'] for r in trades_list if r['volatility'] is not None]
        
        print(f"\n{label} ({len(trades_list)} trades):")
        if bb_vals:
            print(f"  BB Width:  min={min(bb_vals):.3f}%  max={max(bb_vals):.3f}%  avg={statistics.mean(bb_vals):.3f}%  median={statistics.median(bb_vals):.3f}%")
        if rsi_vals:
            print(f"  RSI:       min={min(rsi_vals):.1f}  max={max(rsi_vals):.1f}  avg={statistics.mean(rsi_vals):.1f}  median={statistics.median(rsi_vals):.1f}")
        if bounce_vals:
            print(f"  Bounce%:   min={min(bounce_vals):.3f}%  max={max(bounce_vals):.3f}%  avg={statistics.mean(bounce_vals):.3f}%  median={statistics.median(bounce_vals):.3f}%")
        if vel_vals:
            print(f"  Velocity:  min={min(vel_vals):.4f}%  max={max(vel_vals):.4f}%  avg={statistics.mean(vel_vals):.4f}%  median={statistics.median(vel_vals):.4f}%")
        if mom_vals:
            print(f"  Momentum:  min={min(mom_vals):.4f}  max={max(mom_vals):.4f}  avg={statistics.mean(mom_vals):.4f}  median={statistics.median(mom_vals):.4f}")
        if vol_vals:
            print(f"  Volatility: min={min(vol_vals):.4f}%  max={max(vol_vals):.4f}%  avg={statistics.mean(vol_vals):.4f}%  median={statistics.median(vol_vals):.4f}%")

    stats_for("WINNERS", winners)
    stats_for("LOSERS", losers)

    # Test proposed relaxed filters
    print(f"\n{'='*80}")
    print("FILTER ANALYSIS: Current vs Proposed Relaxed Filters")
    print(f"{'='*80}")

    # Current filters
    print(f"\nCurrent filters (v2):")
    print(f"  BB_WIDTH_MAX = {BB_WIDTH_MAX}%")
    print(f"  RSI_MAX = {RSI_MAX}")
    print(f"  BOUNCE_MIN = {BOUNCE_MIN_PCT}%")
    print(f"  VEL_MIN = {VEL_MIN}%")
    print(f"  MOM_MIN = {MOM_MIN}")
    print(f"  VOL_MAX = {VOL_MAX}%")

    # Test various filter combinations
    filter_tests = [
        ("Current v2", BB_WIDTH_MAX, RSI_MAX, BOUNCE_MIN_PCT),
        ("Proposed relaxed", 2.5, 85, 0.10),
        ("Width <1.0%, RSI <55", 1.0, 55, 0.10),
        ("Width <1.5%, RSI <60", 1.5, 60, 0.10),
        ("Width <2.0%, RSI <70", 2.0, 70, 0.10),
        ("Width <3.0%, RSI <75", 3.0, 75, 0.10),
        ("Width <4.0%, RSI <80", 4.0, 80, 0.10),
    ]

    for name, width_thresh, rsi_thresh, bounce_thresh in filter_tests:
        winners_kept = 0
        losers_blocked = 0
        winners_blocked = 0
        losers_kept = 0

        for r in results:
            bb = r['bb_width'] if r['bb_width'] is not None else 999
            rsi = r['rsi'] if r['rsi'] is not None else 999
            bounce = r['bounce_pct'] if r['bounce_pct'] is not None else 0

            passes = bb <= width_thresh and rsi <= rsi_thresh and bounce >= bounce_thresh

            if r['is_win'] == 1:
                if passes:
                    winners_kept += 1
                else:
                    winners_blocked += 1
            else:
                if passes:
                    losers_kept += 1
                else:
                    losers_blocked += 1

        total_winners = len(winners)
        total_losers = len(losers)
        print(f"\n  {name}:")
        print(f"    BB_WIDTH <= {width_thresh}%, RSI <= {rsi_thresh}, BOUNCE >= {bounce_thresh}%")
        print(f"    Winners: {winners_kept}/{total_winners} kept ({100*winners_kept/total_winners:.1f}%), {winners_blocked} blocked")
        print(f"    Losers:  {losers_kept}/{total_losers} kept ({100*losers_kept/total_losers:.1f}%), {losers_blocked} blocked")
        if winners_kept + losers_kept > 0:
            wr = winners_kept / (winners_kept + losers_kept) * 100
            print(f"    Resulting WR: {wr:.1f}% ({winners_kept}W/{losers_kept}L)")
        else:
            print(f"    Resulting WR: N/A (0 trades)")

    # Detailed breakdown of each winner's BB width and RSI
    print(f"\n{'='*80}")
    print("WINNER DETAILS: BB Width and RSI values")
    print(f"{'='*80}")
    for r in winners:
        bb = r['bb_width'] if r['bb_width'] is not None else 0
        rsi = r['rsi'] if r['rsi'] is not None else 0
        bounce = r['bounce_pct'] if r['bounce_pct'] is not None else 0
        print(f"  {r['token']:<8} BB_width={bb:.3f}%  RSI={rsi:.1f}  Bounce={bounce:.3f}%  PnL={r['pnl_pct']:.2f}%  Regime={r['regime']}")

    # Detailed breakdown of each loser's BB width and RSI
    print(f"\n{'='*80}")
    print("LOSER DETAILS: BB Width and RSI values")
    print(f"{'='*80}")
    for r in losers:
        bb = r['bb_width'] if r['bb_width'] is not None else 0
        rsi = r['rsi'] if r['rsi'] is not None else 0
        bounce = r['bounce_pct'] if r['bounce_pct'] is not None else 0
        print(f"  {r['token']:<8} BB_width={bb:.3f}%  RSI={rsi:.1f}  Bounce={bounce:.3f}%  PnL={r['pnl_pct']:.2f}%  Regime={r['regime']}")

    # Count how many winners have BB width > 0.5% (current max)
    print(f"\n{'='*80}")
    print("CRITICAL ANALYSIS: How many trades would current filters block?")
    print(f"{'='*80}")

    blocked_by_width = [r for r in winners if r['bb_width'] is not None and r['bb_width'] > BB_WIDTH_MAX]
    blocked_by_rsi = [r for r in winners if r['rsi'] is not None and r['rsi'] > RSI_MAX]
    blocked_by_both = [r for r in winners if r['bb_width'] is not None and r['bb_width'] > BB_WIDTH_MAX and r['rsi'] is not None and r['rsi'] > RSI_MAX]

    print(f"\nCurrent filters would have blocked:")
    print(f"  Winners with BB_width > {BB_WIDTH_MAX}%: {len(blocked_by_width)}/{len(winners)} ({100*len(blocked_by_width)/len(winners):.1f}%)")
    for r in blocked_by_width:
        print(f"    {r['token']}: BB_width={r['bb_width']:.3f}%, PnL={r['pnl_pct']:.2f}%")
    
    print(f"\n  Winners with RSI > {RSI_MAX}: {len(blocked_by_rsi)}/{len(winners)} ({100*len(blocked_by_rsi)/len(winners):.1f}%)")
    for r in blocked_by_rsi:
        print(f"    {r['token']}: RSI={r['rsi']:.1f}, PnL={r['pnl_pct']:.2f}%")
    
    print(f"\n  Winners blocked by BOTH width AND RSI: {len(blocked_by_both)}/{len(winners)} ({100*len(blocked_by_both)/len(winners):.1f}%)")

    # Find optimal thresholds
    print(f"\n{'='*80}")
    print("OPTIMAL THRESHOLD ANALYSIS")
    print(f"{'='*80}")

    # Test width thresholds
    print(f"\nBB Width threshold impact on winners:")
    for thresh in [0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]:
        passed = [r for r in winners if r['bb_width'] is not None and r['bb_width'] <= thresh]
        failed = [r for r in winners if r['bb_width'] is not None and r['bb_width'] > thresh]
        print(f"  Width <= {thresh}%: {len(passed)}/{len(winners)} winners pass, {len(failed)} blocked")

    # Test RSI thresholds
    print(f"\nRSI threshold impact on winners:")
    for thresh in [45, 50, 55, 60, 65, 70, 75, 80, 85]:
        passed = [r for r in winners if r['rsi'] is not None and r['rsi'] <= thresh]
        failed = [r for r in winners if r['rsi'] is not None and r['rsi'] > thresh]
        print(f"  RSI <= {thresh}: {len(passed)}/{len(winners)} winners pass, {len(failed)} blocked")


if __name__ == '__main__':
    main()
