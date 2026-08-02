#!/usr/bin/env python3
"""
backtest_rs_tiers.py — Enhanced RS signal backtest with touch-count tier analysis.

Tests what the RS signal SHOULD be filtering on:
  1. Win rate by touch-count tier (low/mid/high)
  2. Win rate with and without bounce confirmation
  3. Win rate by ATR distance from level (closer = better?)
  4. Win rate by whether level was recently broken (invalidated)
  5. Win rate by direction (LONG vs SHORT)

Usage:
    python3 backtest_rs_tiers.py [token ...]
    python3 backtest_rs_tiers.py BTC ETH SOL AVAX LINK ARB APT DOT
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
import statistics
from collections import defaultdict

# ── Constants (must match rs_signals.py) ─────────────────────────────────────
_RS_LOOKBACK       = 4700
_RS_LEVEL_LOOKBACK = 20
_RS_ATR_PERIOD     = 14
_RS_CLUSTER_ATR    = 0.50
_RS_PROXIMITY_K    = 1.20
_RS_MIN_TOUCHES    = 2
_BOUNCE_LOOKBACK   = 6
_FWD_WIN           = 15   # candles to check for directional success

# ── Helpers (mirrors rs_signals.py) ───────────────────────────────────────────

def _atr(candles, period=14):
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        tr = max(
            candles[i]['high'] - candles[i]['low'],
            abs(candles[i]['high'] - candles[i-1]['close']),
            abs(candles[i]['low']  - candles[i-1]['close'])
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def _atr_pct(price, atr):
    if price <= 0 or atr is None:
        return 0.0
    return atr / price * 100.0


def _find_swing_highs_lows(candles, window=20):
    if len(candles) < window * 2 + 1:
        return [], []
    swing_highs, swing_lows = [], []
    for i in range(window, len(candles) - window):
        wh = [candles[j]['high'] for j in range(i - window, i + window + 1)]
        wl = [candles[j]['low']  for j in range(i - window, i + window + 1)]
        if candles[i]['high'] == max(wh):
            swing_highs.append((i, candles[i]['high']))
        if candles[i]['low'] == min(wl):
            swing_lows.append((i, candles[i]['low']))
    return swing_highs, swing_lows


def _cluster_levels(levels, cluster_atr_pct):
    if not levels:
        return []
    sorted_levels = sorted(levels, key=lambda x: x[0])
    clusters = []
    current = [sorted_levels[0]]
    for level in sorted_levels[1:]:
        cp = sum(p for p, _ in current) / len(current)
        if abs(level[0] - cp) / cp * 100.0 <= cluster_atr_pct:
            current.append(level)
        else:
            clusters.append(current)
            current = [level]
    clusters.append(current)
    return [(sum(p for p, _ in c) / len(c), sum(cnt for _, cnt in c))
            for c in clusters]


def _price_near_level(price, level, atr_pct, k=1.20):
    if price <= 0 or level <= 0 or atr_pct <= 0:
        return False
    dist_pct = abs(price - level) / price * 100.0
    atr_dist = dist_pct / atr_pct
    return atr_dist <= k


def _build_level_touches(candles, level):
    thresh = 0.15
    return sum(
        1 for c in candles
        if abs(c['high'] - level) / level * 100.0 < thresh
        or abs(c['low']  - level) / level * 100.0 < thresh
    )


def _bounce_confirmed(candles, level, direction, lookback=6):
    if len(candles) < lookback:
        return False
    recent = candles[-lookback:]
    if direction == 'LONG':
        for c in recent:
            if abs(c['low'] - level) / level * 100.0 < 0.20 and c['close'] > c['open']:
                return True
    else:
        for c in recent:
            if abs(c['high'] - level) / level * 100.0 < 0.20 and c['close'] < c['open']:
                return True
    return False


def _level_recently_broken(candles, level, direction, lookback=20):
    """Check if price CROSSED the level in the last lookback candles.
    If resistance was crossed from below (price went above), it's invalidated for SHORT.
    If support was crossed from above (price went below), it's invalidated for LONG.
    """
    if len(candles) < lookback:
        return False
    recent = candles[-lookback:]
    for c in recent:
        if direction == 'LONG':
            # Support broken: candle low went BELOW level
            if c['low'] < level * 0.999:
                return True
        else:
            # Resistance broken: candle high went ABOVE level
            if c['high'] > level * 1.001:
                return True
    return False


def _compute_confidence(atr_pct, dist_pct, touch_count, bounces):
    base = 65.0
    if atr_pct > 0:
        atr_dist = dist_pct / atr_pct
        prox = max(0, 15 * (1 - atr_dist / 1.20))
    else:
        prox = 0
    touch_bonus = 3 if touch_count <= 2 else (6 if touch_count == 3 else min(10, 3 + touch_count))
    bounce_bonus = 5 if bounces else 0
    conf = base + prox + touch_bonus + bounce_bonus
    return min(88, max(50, round(conf)))


def detect_rs_with_touch_count(candles, price):
    """Return (direction, confidence, level, touch_count, atr_dist, bounces) or None."""
    if not candles or len(candles) < _RS_LEVEL_LOOKBACK * 2:
        return None
    atr = _atr(candles, _RS_ATR_PERIOD)
    if atr is None:
        return None
    atr_pct = _atr_pct(price, atr)

    sh, sl = _find_swing_highs_lows(candles, _RS_LEVEL_LOOKBACK)
    raw_r = [(l, _build_level_touches(candles, l)) for _, l in sh]
    raw_s = [(l, _build_level_touches(candles, l)) for _, l in sl]
    cp = _RS_CLUSTER_ATR * atr_pct
    r_levels = _cluster_levels(raw_r, cp)
    s_levels = _cluster_levels(raw_s, cp)
    if not r_levels and not s_levels:
        return None

    best_s = None; best_sd = float('inf')
    best_r = None; best_rd = float('inf')
    for lvl, cnt in s_levels:
        if cnt < _RS_MIN_TOUCHES:
            continue
        d = abs(price - lvl) / price * 100.0
        if _price_near_level(price, lvl, atr_pct) and d < best_sd:
            best_sd = d; best_s = (lvl, cnt)
    for lvl, cnt in r_levels:
        if cnt < _RS_MIN_TOUCHES:
            continue
        d = abs(price - lvl) / price * 100.0
        if _price_near_level(price, lvl, atr_pct) and d < best_rd:
            best_rd = d; best_r = (lvl, cnt)

    sig = None
    if best_s:
        lvl, cnt = best_s
        bounces = _bounce_confirmed(candles, lvl, 'LONG')
        conf = _compute_confidence(atr_pct, best_sd, cnt, bounces)
        atr_dist = best_sd / atr_pct if atr_pct > 0 else 999
        sig = ('LONG', conf, lvl, cnt, atr_dist, bounces)
    if best_r:
        lvl, cnt = best_r
        bounces = _bounce_confirmed(candles, lvl, 'SHORT')
        conf = _compute_confidence(atr_pct, best_rd, cnt, bounces)
        atr_dist = best_rd / atr_pct if atr_pct > 0 else 999
        cs = ('SHORT', conf, lvl, cnt, atr_dist, bounces)
        if sig is None or cs[1] > sig[1]:
            sig = cs
    return sig


# ── Main backtest ───────────────────────────────────────────────────────────────

_CANDLES_DB = '/root/.hermes/data/candles.db'
DEFAULT_TOKENS = ['BTC', 'ETH', 'SOL', 'AVAX', 'LINK', 'ARB', 'APT', 'DOT']
SAMPLE_INTERVAL = 30


def main():
    tokens = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_TOKENS
    results = []

    for token in tokens:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_1m WHERE token=? ORDER BY ts ASC LIMIT ?
        """, (token, _RS_LOOKBACK))
        rows = list(c.fetchall())
        conn.close()

        if len(rows) < 200:
            print(f'{token}: only {len(rows)} candles, skipping')
            continue

        candles = [
            {'open_time': r[0], 'open': r[1], 'high': r[2],
             'low': r[3], 'close': r[4], 'volume': r[5]}
            for r in rows
        ]
        print(f'{token}: {len(candles)} candles, {candles[0]["close"]:.4f} -> {candles[-1]["close"]:.4f}')

        start_idx = _RS_LEVEL_LOOKBACK * 2 + _RS_ATR_PERIOD
        for i in range(start_idx, len(candles) - _FWD_WIN, SAMPLE_INTERVAL):
            window_candles = candles[:i]
            price = candles[i]['close']
            sig = detect_rs_with_touch_count(window_candles, price)
            if sig is None:
                continue

            direction, conf, level, touch_count, atr_dist, bounces = sig
            entry_price = price
            win = _FWD_WIN

            # Check forward price action
            future_lows  = [candles[i + j]['low']  for j in range(1, win + 1)]
            future_highs = [candles[i + j]['high'] for j in range(1, win + 1)]
            future_closes = [candles[i + j]['close'] for j in range(1, win + 1)]

            if direction == 'LONG':
                breaks_level = any(low < level * 0.999 for low in future_lows)
                reaches_tp   = any(c > level * 1.005 for c in future_closes)
                win_trade    = reaches_tp or not breaks_level
                pnl_pct = (candles[i + win]['close'] - entry_price) / entry_price * 100
            else:
                breaks_level = any(high > level * 1.001 for high in future_highs)
                reaches_tp   = any(c < level * 0.995 for c in future_closes)
                win_trade    = reaches_tp or not breaks_level
                pnl_pct = (entry_price - candles[i + win]['close']) / entry_price * 100

            # Compute ATR % for this candle
            atr = _atr(window_candles, _RS_ATR_PERIOD)
            atr_pct_now = _atr_pct(price, atr) if atr else 0.0

            # Level age: how many candles ago was this level formed?
            # (find the swing point index for this level)
            level_age = None
            if direction == 'LONG':
                sh, sl = _find_swing_highs_lows(window_candles, _RS_LEVEL_LOOKBACK)
                for idx, lvl_price in sl:
                    if abs(lvl_price - level) / level < 0.001:  # same level
                        level_age = len(window_candles) - idx
                        break
            else:
                sh, sl = _find_swing_highs_lows(window_candles, _RS_LEVEL_LOOKBACK)
                for idx, lvl_price in sh:
                    if abs(lvl_price - level) / level < 0.001:
                        level_age = len(window_candles) - idx
                        break

            # Recently broken?
            recently_broken = _level_recently_broken(window_candles, level, direction, lookback=20)

            results.append({
                'token': token,
                'direction': direction,
                'confidence': conf,
                'level': level,
                'entry_price': entry_price,
                'pnl_pct': pnl_pct,
                'win': win_trade,
                'touch_count': touch_count,
                'atr_dist': atr_dist,
                'bounces': bounces,
                'atr_pct': atr_pct_now,
                'level_age': level_age,
                'recently_broken': recently_broken,
            })

    # ── Analysis ────────────────────────────────────────────────────────────────
    print()
    print('═' * 70)
    print('ENHANCED RS ANALYSIS — ALL TOKENS')
    print('═' * 70)

    n_total = len(results)
    n_win   = sum(1 for r in results if r['win'])
    avg_pnl = statistics.mean(r["pnl_pct"] for r in results)
    print(f"\nTotal RS signals: {n_total}, Win rate: {n_win/n_total*100:.1f}%, avg PnL: {avg_pnl:+.4f}%")
    print()

    # 1. BY TOUCH-COUNT TIER
    print('─' * 70)
    print('1. BY TOUCH-COUNT TIER')
    print('─' * 70)
    def touch_tier(tc):
        if tc < 10:    return 'low (<10)'
        elif tc < 50:  return 'mid (10-49)'
        elif tc < 200: return 'high (50-199)'
        else:          return 'vhigh (200+)'

    for tier in ['low (<10)', 'mid (10-49)', 'high (50-199)', 'vhigh (200+)']:
        subset = [r for r in results if touch_tier(r['touch_count']) == tier]
        if not subset:
            continue
        nw = sum(1 for r in subset if r['win'])
        avg_pnl = statistics.mean(r['pnl_pct'] for r in subset)
        print(f'  {tier:15s}: n={len(subset):4d}  WR={nw/len(subset)*100:5.1f}%  avgPnL={avg_pnl:+.4f}%')

    print()

    # 2. BY BOUNCE CONFIRMATION
    print('─' * 70)
    print('2. BY BOUNCE CONFIRMATION')
    print('─' * 70)
    for bounce_val in [True, False]:
        subset = [r for r in results if r['bounces'] == bounce_val]
        if not subset:
            continue
        nw = sum(1 for r in subset if r['win'])
        avg_pnl = statistics.mean(r['pnl_pct'] for r in subset)
        label = 'bounce_confirmed' if bounce_val else 'no_bounce'
        print(f'  {label:20s}: n={len(subset):4d}  WR={nw/len(subset)*100:5.1f}%  avgPnL={avg_pnl:+.4f}%')

    print()

    # 3. BY ATR DISTANCE FROM LEVEL
    print('─' * 70)
    print('3. BY ATR DISTANCE (closer = better?)')
    print('─' * 70)
    for atr_lo, atr_hi, label in [
        (0.0, 0.3, "0.0-0.3"),
        (0.3, 0.6, "0.3-0.6"),
        (0.6, 0.9, "0.6-0.9"),
        (0.9, 1.21, "0.9-1.2"),
    ]:
        subset = [r for r in results if atr_lo <= r['atr_dist'] < atr_hi]
        if not subset:
            continue
        nw = sum(1 for r in subset if r['win'])
        avg_pnl = statistics.mean(r['pnl_pct'] for r in subset)
        print(f"  atr_dist {label:10s}: n={len(subset):4d}  WR={nw/len(subset)*100:5.1f}%  avgPnL={avg_pnl:+.4f}%")

    print()

    # 4. BY WHETHER LEVEL WAS RECENTLY BROKEN
    print('─' * 70)
    print('4. BY LEVEL RECENTLY BROKEN (level invalidated?)')
    print('─' * 70)
    for broken in [True, False]:
        subset = [r for r in results if r['recently_broken'] == broken]
        if not subset:
            continue
        nw = sum(1 for r in subset if r['win'])
        avg_pnl = statistics.mean(r['pnl_pct'] for r in subset)
        label = 'recently_broken' if broken else 'level_intact'
        print(f'  {label:20s}: n={len(subset):4d}  WR={nw/len(subset)*100:5.1f}%  avgPnL={avg_pnl:+.4f}%')

    print()

    # 5. BY DIRECTION
    print('─' * 70)
    print('5. BY DIRECTION')
    print('─' * 70)
    for d in ['LONG', 'SHORT']:
        subset = [r for r in results if r['direction'] == d]
        if not subset:
            continue
        nw = sum(1 for r in subset if r['win'])
        avg_pnl = statistics.mean(r['pnl_pct'] for r in subset)
        print(f'  {d:6s}: n={len(subset):4d}  WR={nw/len(subset)*100:5.1f}%  avgPnL={avg_pnl:+.4f}%')

    print()

    # 6. COMBINED FILTER: high touch + bounce + not broken
    print('─' * 70)
    print('6. COMBINED FILTERS (what the ideal RS signal should require)')
    print('─' * 70)

    filters = [
        ('touch>=10',          lambda r: r['touch_count'] >= 10),
        ('touch>=50',          lambda r: r['touch_count'] >= 50),
        ('touch>=10 + bounce', lambda r: r['touch_count'] >= 10 and r['bounces']),
        ('touch>=10 + intact', lambda r: r['touch_count'] >= 10 and not r['recently_broken']),
        ('touch>=50 + bounce', lambda r: r['touch_count'] >= 50 and r['bounces']),
        ('all 3 conditions',   lambda r: r['touch_count'] >= 50 and r['bounces'] and not r['recently_broken']),
        ('atr_dist<0.6',       lambda r: r['atr_dist'] < 0.6),
        ('touch>=50 + bounce + intact + close', lambda r: r['touch_count'] >= 50 and r['bounces'] and not r['recently_broken'] and r['atr_dist'] < 0.6),
    ]

    for label, fn in filters:
        subset = [r for r in results if fn(r)]
        if not subset:
            continue
        nw = sum(1 for r in subset if r['win'])
        avg_pnl = statistics.mean(r['pnl_pct'] for r in subset)
        print(f'  {label:35s}: n={len(subset):4d}  WR={nw/len(subset)*100:5.1f}%  avgPnL={avg_pnl:+.4f}%')

    print()
    print('═' * 70)


if __name__ == '__main__':
    main()
