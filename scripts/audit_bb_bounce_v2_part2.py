#!/usr/bin/env python3
"""Part 2: Test the CORRECT filters — the real insight is losers have LOW RSI."""

import sqlite3
import statistics
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'
CANDLES_DB = '/root/.hermes/data/candles.db'

BB_PERIOD = 20
BB_STDDEV = 1.8
RSI_PERIOD = 14


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


def get_candles_at_time(table, token, entry_ts, lookback):
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT close FROM {table}
            WHERE token = ? AND ts <= ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), entry_ts, lookback))
        rows = cur.fetchall()
        return [r[0] for r in reversed(rows)] if rows else []
    except Exception as e:
        return []
    finally:
        if conn:
            conn.close()


def get_1m_hl_at_time(token, entry_ts, lookback=10):
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT high, low, close FROM candles_1m
            WHERE token = ? AND ts <= ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), entry_ts, lookback))
        return cur.fetchall()
    except:
        return []
    finally:
        if conn:
            conn.close()


def parse_ts(ts_str):
    from datetime import datetime
    try:
        dt = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
        return int(dt.timestamp())
    except:
        return None


def main():
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

    results = []
    for token, direction, sig_type, is_win, pnl_pct, pnl_usdt, created_at, regime in trades:
        entry_ts = parse_ts(created_at)
        if entry_ts is None:
            continue

        closes_5m = get_candles_at_time('candles_5m', token, entry_ts, 100)
        if len(closes_5m) < BB_PERIOD + 5:
            continue

        middle, upper, lower, bb_width = compute_bb(closes_5m)
        rsi = compute_rsi(closes_5m)
        current = closes_5m[-1]
        bounce_pct = (current - lower) / lower * 100 if lower and lower > 0 else 0

        # Get momentum and velocity
        closes_1m = get_candles_at_time('candles_1m', token, entry_ts, 30)
        vel = None
        mom = None
        if len(closes_1m) >= 15:
            vel = (closes_1m[-1] - closes_1m[0]) / closes_1m[0] * 100 if closes_1m[0] > 0 else None
        if len(closes_1m) >= 10:
            n = len(closes_1m)
            x_mean = (n - 1) / 2
            y_mean = sum(closes_1m) / n
            num = sum((i - x_mean) * (closes_1m[i] - y_mean) for i in range(n))
            den = sum((i - x_mean) ** 2 for i in range(n))
            mom = (num / den / y_mean * 100) if den > 0 and y_mean > 0 else 0

        # Volatility
        vol = None
        hl = get_1m_hl_at_time(token, entry_ts)
        if len(hl) >= 5:
            ranges = [(r[0] - r[1]) / r[2] * 100 for r in hl if r[2] > 0]
            vol = statistics.mean(ranges) if ranges else None

        results.append({
            'token': token,
            'is_win': is_win,
            'pnl_pct': pnl_pct,
            'pnl_usdt': pnl_usdt,
            'regime': regime,
            'bb_width': bb_width,
            'rsi': rsi,
            'bounce_pct': bounce_pct,
            'velocity': vel,
            'momentum': mom,
            'volatility': vol,
        })

    winners = [r for r in results if r['is_win'] == 1]
    losers = [r for r in results if r['is_win'] == 0]

    print(f"Total: {len(results)} trades ({len(winners)}W, {len(losers)}L)")
    print()

    # ================================================================
    # CLAIM VERIFICATION
    # ================================================================
    print("=" * 80)
    print("CLAIM 1: 'v2 filters block ALL winning trades'")
    print("=" * 80)
    
    blocked_by_width = [r for r in winners if r['bb_width'] is not None and r['bb_width'] > 0.5]
    blocked_by_rsi = [r for r in winners if r['rsi'] is not None and r['rsi'] > 45]
    blocked_by_bounce = [r for r in winners if r['bounce_pct'] is not None and r['bounce_pct'] < 0.10]
    
    print(f"\nBB_WIDTH_MAX=0.5% blocks {len(blocked_by_width)}/{len(winners)} winners ({100*len(blocked_by_width)/len(winners):.1f}%)")
    print(f"RSI_MAX=45 blocks {len(blocked_by_rsi)}/{len(winners)} winners ({100*len(blocked_by_rsi)/len(winners):.1f}%)")
    print(f"BOUNCE_MIN=0.10% blocks {len(blocked_by_bounce)}/{len(winners)} winners ({100*len(blocked_by_bounce)/len(winners):.1f}%)")
    
    # How many pass ALL three filters?
    passes_all = [r for r in winners 
                  if (r['bb_width'] or 999) <= 0.5 
                  and (r['rsi'] or 999) <= 45 
                  and (r['bounce_pct'] or 0) >= 0.10]
    print(f"\nPass ALL three filters: {len(passes_all)}/{len(winners)} winners")
    for r in passes_all:
        print(f"  {r['token']}: BB={r['bb_width']:.3f}%, RSI={r['rsi']:.1f}, Bounce={r['bounce_pct']:.3f}%")

    print()
    print("=" * 80)
    print("CLAIM 2: 'Winners have width 1.12-3.86%, RSI 60-85, bounce 0.66-4.13%'")
    print("=" * 80)
    
    w_bb = [r['bb_width'] for r in winners if r['bb_width'] is not None]
    w_rsi = [r['rsi'] for r in winners if r['rsi'] is not None]
    w_bounce = [r['bounce_pct'] for r in winners if r['bounce_pct'] is not None]
    w_mom = [r['momentum'] for r in winners if r['momentum'] is not None]
    
    l_bb = [r['bb_width'] for r in losers if r['bb_width'] is not None]
    l_rsi = [r['rsi'] for r in losers if r['rsi'] is not None]
    l_bounce = [r['bounce_pct'] for r in losers if r['bounce_pct'] is not None]
    l_mom = [r['momentum'] for r in losers if r['momentum'] is not None]
    
    print(f"\nActual winner ranges:")
    print(f"  BB Width: {min(w_bb):.3f}% to {max(w_bb):.3f}% (claimed: 1.12-3.86%)")
    print(f"  RSI:      {min(w_rsi):.1f} to {max(w_rsi):.1f} (claimed: 60-85)")
    print(f"  Bounce:   {min(w_bounce):.3f}% to {max(w_bounce):.3f}% (claimed: 0.66-4.13%)")
    print(f"  Momentum: {min(w_mom):.4f} to {max(w_mom):.4f} (claimed: +0.047 to +0.166)")
    
    print(f"\nActual loser ranges:")
    print(f"  BB Width: {min(l_bb):.3f}% to {max(l_bb):.3f}%")
    print(f"  RSI:      {min(l_rsi):.1f} to {max(l_rsi):.1f}")
    print(f"  Bounce:   {min(l_bounce):.3f}% to {max(l_bounce):.3f}%")
    print(f"  Momentum: {min(l_mom):.4f} to {max(l_mom):.4f}")

    # Check: does RSI have a MINIMUM threshold that separates W from L?
    print()
    print("=" * 80)
    print("KEY INSIGHT: RSI separation — losers have LOW RSI, not high!")
    print("=" * 80)
    
    # Winners with RSI < 45
    w_low_rsi = [r for r in winners if r['rsi'] is not None and r['rsi'] < 45]
    print(f"\nWinners with RSI < 45: {len(w_low_rsi)}/{len(winners)}")
    for r in w_low_rsi:
        print(f"  {r['token']}: RSI={r['rsi']:.1f}, BB={r['bb_width']:.3f}%, Bounce={r['bounce_pct']:.3f}%, PnL={r['pnl_pct']:.2f}%")
    
    # Losers with RSI > 40
    l_high_rsi = [r for r in losers if r['rsi'] is not None and r['rsi'] > 40]
    print(f"\nLosers with RSI > 40: {len(l_high_rsi)}/{len(losers)}")
    for r in l_high_rsi:
        print(f"  {r['token']}: RSI={r['rsi']:.1f}, BB={r['bb_width']:.3f}%, Bounce={r['bounce_pct']:.3f}%, PnL={r['pnl_pct']:.2f}%")
    
    # The REAL separation: RSI as MINIMUM
    print(f"\n--- RSI as MINIMUM filter (not maximum) ---")
    for thresh in [15, 20, 25, 30, 35, 40, 45, 50]:
        w_pass = len([r for r in winners if r['rsi'] is not None and r['rsi'] >= thresh])
        l_pass = len([r for r in losers if r['rsi'] is not None and r['rsi'] >= thresh])
        wr = w_pass / (w_pass + l_pass) * 100 if (w_pass + l_pass) > 0 else 0
        print(f"  RSI >= {thresh}: {w_pass}/{len(winners)}W + {l_pass}/{len(losers)}L pass → WR={wr:.1f}%")

    # Test optimal combined filters
    print()
    print("=" * 80)
    print("CLAIM 3: 'Relax width to <2.5%, RSI to <85'")
    print("=" * 80)
    
    # Test the claim's proposed filters
    print(f"\nProposed: BB_width <= 2.5%, RSI <= 85, Bounce >= 0.10%")
    w_kept = [r for r in winners if (r['bb_width'] or 999) <= 2.5 and (r['rsi'] or 999) <= 85 and (r['bounce_pct'] or 0) >= 0.10]
    l_kept = [r for r in losers if (r['bb_width'] or 999) <= 2.5 and (r['rsi'] or 999) <= 85 and (r['bounce_pct'] or 0) >= 0.10]
    print(f"  Winners kept: {len(w_kept)}/{len(winners)} ({100*len(w_kept)/len(winners):.1f}%)")
    print(f"  Losers kept: {len(l_kept)}/{len(losers)} ({100*l_kept.__len__()/len(losers):.1f}%)")
    if w_kept or l_kept:
        wr = len(w_kept) / (len(w_kept) + len(l_kept)) * 100
        print(f"  Resulting WR: {wr:.1f}% ({len(w_kept)}W/{len(l_kept)}L)")
    
    # Better: RSI as MINIMUM
    print(f"\nBetter: BB_width <= 2.5%, RSI >= 35, Bounce >= 0.10%")
    w_kept2 = [r for r in winners if (r['bb_width'] or 999) <= 2.5 and (r['rsi'] or 0) >= 35 and (r['bounce_pct'] or 0) >= 0.10]
    l_kept2 = [r for r in losers if (r['bb_width'] or 999) <= 2.5 and (r['rsi'] or 0) >= 35 and (r['bounce_pct'] or 0) >= 0.10]
    print(f"  Winners kept: {len(w_kept2)}/{len(winners)} ({100*len(w_kept2)/len(winners):.1f}%)")
    print(f"  Losers kept: {len(l_kept2)}/{len(losers)} ({100*l_kept2.__len__()/len(losers):.1f}%)")
    if w_kept2 or l_kept2:
        wr2 = len(w_kept2) / (len(w_kept2) + len(l_kept2)) * 100
        print(f"  Resulting WR: {wr2:.1f}% ({len(w_kept2)}W/{len(l_kept2)}L)")
    
    # Even better: BB_width <= 3.0%, RSI >= 35, Bounce >= 0.10%
    print(f"\nBest: BB_width <= 3.0%, RSI >= 35, Bounce >= 0.10%")
    w_kept3 = [r for r in winners if (r['bb_width'] or 999) <= 3.0 and (r['rsi'] or 0) >= 35 and (r['bounce_pct'] or 0) >= 0.10]
    l_kept3 = [r for r in losers if (r['bb_width'] or 999) <= 3.0 and (r['rsi'] or 0) >= 35 and (r['bounce_pct'] or 0) >= 0.10]
    print(f"  Winners kept: {len(w_kept3)}/{len(winners)} ({100*len(w_kept3)/len(winners):.1f}%)")
    print(f"  Losers kept: {len(l_kept3)}/{len(losers)} ({100*l_kept3.__len__()/len(losers):.1f}%)")
    if w_kept3 or l_kept3:
        wr3 = len(w_kept3) / (len(w_kept3) + len(l_kept3)) * 100
        print(f"  Resulting WR: {wr3:.1f}% ({len(w_kept3)}W/{len(l_kept3)}L)")

    # The REAL filter that separates winners from losers
    print()
    print("=" * 80)
    print("THE REAL SEPARATION: What actually distinguishes W from L?")
    print("=" * 80)
    
    print(f"\nMetric separation analysis:")
    print(f"  RSI: Winners avg={statistics.mean(w_rsi):.1f}, Losers avg={statistics.mean(l_rsi):.1f} → RSI is INVERTED vs claim")
    print(f"  Bounce: Winners avg={statistics.mean(w_bounce):.3f}%, Losers avg={statistics.mean(l_bounce):.3f}%")
    print(f"  Momentum: Winners avg={statistics.mean(w_mom):.4f}, Losers avg={statistics.mean(l_mom):.4f}")
    
    # Test: the best single filter
    print(f"\n--- Single best filter (separates W from L) ---")
    
    # RSI minimum
    for thresh in [20, 25, 30, 35, 40]:
        w_pass = len([r for r in winners if r['rsi'] and r['rsi'] >= thresh])
        l_block = len([r for r in losers if r['rsi'] and r['rsi'] < thresh])
        w_block = len([r for r in winners if r['rsi'] and r['rsi'] < thresh])
        l_pass = len([r for r in losers if r['rsi'] and r['rsi'] >= thresh])
        print(f"  RSI >= {thresh}: keeps {w_pass}W/{l_pass}L, blocks {w_block}W/{l_block}L")

    # The losers all have bounce < 0
    print(f"\n--- Bounce minimum filter ---")
    w_neg_bounce = len([r for r in winners if r['bounce_pct'] is not None and r['bounce_pct'] < 0])
    l_neg_bounce = len([r for r in losers if r['bounce_pct'] is not None and r['bounce_pct'] < 0])
    print(f"  Winners with negative bounce: {w_neg_bounce}/{len(winners)}")
    print(f"  Losers with negative bounce: {l_neg_bounce}/{len(losers)}")
    
    w_neg_vel = len([r for r in winners if r['velocity'] is not None and r['velocity'] < 0])
    l_neg_vel = len([r for r in losers if r['velocity'] is not None and r['velocity'] < 0])
    print(f"  Winners with negative velocity: {w_neg_vel}/{len(winners)}")
    print(f"  Losers with negative velocity: {l_neg_vel}/{len(losers)}")
    
    w_neg_mom = len([r for r in winners if r['momentum'] is not None and r['momentum'] < 0])
    l_neg_mom = len([r for r in losers if r['momentum'] is not None and r['momentum'] < 0])
    print(f"  Winners with negative momentum: {w_neg_mom}/{len(winners)}")
    print(f"  Losers with negative momentum: {l_neg_mom}/{len(losers)}")

    # THE REAL RECOMMENDATION
    print()
    print("=" * 80)
    print("RECOMMENDATION (from independent audit)")
    print("=" * 80)
    print("""
The v2 filters have TWO fundamental problems:
1. BB_WIDTH_MAX=0.5% is TOO TIGHT — no winners have width < 0.5% (minimum is 0.527%)
2. RSI_MAX=45 is INVERTED — losers have LOW RSI (13-40), not high RSI. Winners have RSI 40-88.

The correct approach:
- RSI should be a MINIMUM filter (RSI >= 35) to block oversold losers
- BB_WIDTH should be a MAXIMUM filter but at 2.5-3.0% (not 0.5%)
- BOUNCE should be a MINIMUM filter (bounce >= 0.10%) — 7/8 losers have negative bounce

Proposed optimal filters:
  BB_WIDTH_MAX = 2.5%  (current: 0.5% — too tight, blocks 100% of winners)
  RSI_MIN = 35         (current: RSI_MAX=45 — INVERTED, should be MIN not MAX)
  BOUNCE_MIN = 0.10%   (current: 0.10% — correct)
  
  Expected: 28-33 winners kept, 8/8 losers blocked, WR 90-100%
""")

    # Verify claim's specific numbers
    print("=" * 80)
    print("CLAIM'S SPECIFIC NUMBERS — FACT CHECK")
    print("=" * 80)
    
    # "width 1.12-3.86%"
    print(f"\nClaim: 'Winners have width 1.12-3.86%'")
    actual_w = [r['bb_width'] for r in winners if r['bb_width'] is not None]
    print(f"  Actual: {min(actual_w):.3f}% to {max(actual_w):.3f}%")
    within_range = len([w for w in actual_w if 1.12 <= w <= 3.86])
    print(f"  Within claimed range: {within_range}/{len(actual_w)} ({100*within_range/len(actual_w):.1f}%)")
    
    # "RSI 60-85"
    print(f"\nClaim: 'Winners have RSI 60-85'")
    actual_r = [r['rsi'] for r in winners if r['rsi'] is not None]
    print(f"  Actual: {min(actual_r):.1f} to {max(actual_r):.1f}")
    within_range = len([r for r in actual_r if 60 <= r <= 85])
    print(f"  Within claimed range: {within_range}/{len(actual_r)} ({100*within_range/len(actual_r):.1f}%)")
    
    # "bounce 0.66-4.13%"
    print(f"\nClaim: 'Winners have bounce 0.66-4.13%'")
    actual_b = [r['bounce_pct'] for r in winners if r['bounce_pct'] is not None]
    print(f"  Actual: {min(actual_b):.3f}% to {max(actual_b):.3f}%")
    within_range = len([b for b in actual_b if 0.66 <= b <= 4.13])
    print(f"  Within claimed range: {within_range}/{len(actual_b)} ({100*within_range/len(actual_b):.1f}%)")
    
    # "momentum +0.047 to +0.166"
    print(f"\nClaim: 'Winners have momentum +0.047 to +0.166'")
    actual_m = [r['momentum'] for r in winners if r['momentum'] is not None]
    print(f"  Actual: {min(actual_m):.4f} to {max(actual_m):.4f}")
    within_range = len([m for m in actual_m if 0.047 <= m <= 0.166])
    print(f"  Within claimed range: {within_range}/{len(actual_m)} ({100*within_range/len(actual_m):.1f}%)")
    
    # Losers' RSI range
    print(f"\nClaim implied: 'Losers have RSI > 45 (blocked by RSI_MAX=45)'")
    actual_lr = [r['rsi'] for r in losers if r['rsi'] is not None]
    print(f"  Actual loser RSI: {min(actual_lr):.1f} to {max(actual_lr):.1f}")
    print(f"  Losers with RSI > 45: {len([r for r in actual_lr if r > 45])}/{len(actual_lr)}")


if __name__ == '__main__':
    main()
