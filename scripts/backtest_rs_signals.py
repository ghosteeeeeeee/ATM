#!/usr/bin/env python3
"""
backtest_rs_signals.py — Backtest the support_resistance signal.

Tests:
  1. Signal fires and price subsequently bounces (directional agreement)
  2. Signal fires and price crosses the level (invalid — false positive)
  3. Win rate and avg PnL by direction, confidence tier, token

Usage:
  python3 backtest_rs_signals.py [lookback_tokens]
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
import statistics

# ── Constants ───────────────────────────────────────────────────────────────────
_RS_LOOKBACK       = 4700   # candles to analyze
_RS_LEVEL_LOOKBACK = 20
_RS_ATR_PERIOD     = 14
_RS_CLUSTER_ATR    = 0.50
_RS_PROXIMITY_K    = 1.20
_RS_MIN_TOUCHES    = 2
_BOUNCE_LOOKBACK   = 6

# Forward windows to check for valid bounce (price moved in signal direction)
_FWD_WIN_LONG  = 15   # candles to check for LONG success
_FWD_WIN_SHORT = 15

# ── Helpers (same as rs_signals.py) ───────────────────────────────────────────

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


def detect_rs(candles, price):
    """Return (direction, confidence, level) or None."""
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
        sig = ('LONG', conf, lvl)
    if best_r:
        lvl, cnt = best_r
        bounces = _bounce_confirmed(candles, lvl, 'SHORT')
        conf = _compute_confidence(atr_pct, best_rd, cnt, bounces)
        cs = ('SHORT', conf, lvl)
        if sig is None or cs[1] > sig[1]:
            sig = cs
    return sig


# ── Main backtest ────────────────────────────────────────────────────────────────

_CANDLES_DB = '/root/.hermes/data/candles.db'
TEST_TOKENS = ['BTC', 'ETH', 'SOL', 'AVAX', 'LINK', 'ARB', 'APT', 'DOT']


def main():
    results = []
    token_stats = {}

    for token in TEST_TOKENS:
        # Load candles
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

        token_long_wins = 0; token_long_losses = 0
        token_short_wins = 0; token_short_losses = 0
        token_long_pnls = []; token_short_pnls = []
        signals = 0

        # Walk forward through candles, checking for signals at intervals
        # (full per-candle is O(n²) with swing detection — too slow for 4700 candles)
        SAMPLE_INTERVAL = 30
        start_idx = _RS_LEVEL_LOOKBACK * 2 + _RS_ATR_PERIOD
        for i in range(start_idx, len(candles) - _FWD_WIN_LONG, SAMPLE_INTERVAL):
            window_candles = candles[:i]
            price = candles[i]['close']
            sig = detect_rs(window_candles, price)
            if sig is None:
                continue

            signals += 1
            direction, conf, level = sig
            win = _FWD_WIN_LONG if direction == 'LONG' else _FWD_WIN_SHORT

            # Check price action in forward window
            entry_price = price
            future_closes = [candles[i + j]['close'] for j in range(1, win + 1)]

            if direction == 'LONG':
                # Success: price bounces up (close above level) within window
                # Failure: price continues below level
                breaks_level = any(candles[i + j]['low'] < level * 0.999
                                   for j in range(1, win + 1))
                reaches_tp   = any(c > level * 1.005 for c in future_closes)
                # Win: reaches TP or still above level; Loss: breaks below
                win_trade = reaches_tp or not breaks_level
                pnl_pct   = (candles[i + win]['close'] - entry_price) / entry_price * 100
                token_long_pnls.append(pnl_pct)
                if win_trade:
                    token_long_wins += 1
                else:
                    token_long_losses += 1

            else:  # SHORT
                breaks_level = any(candles[i + j]['high'] > level * 1.001
                                   for j in range(1, win + 1))
                reaches_tp   = any(c < level * 0.995 for c in future_closes)
                win_trade    = reaches_tp or not breaks_level
                pnl_pct      = (entry_price - candles[i + win]['close']) / entry_price * 100
                token_short_pnls.append(pnl_pct)
                if win_trade:
                    token_short_wins += 1
                else:
                    token_short_losses += 1

            results.append({
                'token': token, 'direction': direction,
                'confidence': conf, 'level': level,
                'entry_price': entry_price, 'pnl_pct': pnl_pct,
                'win': win_trade
            })

        n_l = token_long_wins + token_long_losses
        n_s = token_short_wins + token_short_losses
        lwrate = token_long_wins / n_l * 100 if n_l else 0
        swrate = token_short_wins / n_s * 100 if n_s else 0
        lapnl  = statistics.mean(token_long_pnls)  if token_long_pnls  else 0
        sapnl  = statistics.mean(token_short_pnls) if token_short_pnls else 0

        print(f'  LONG:  {n_l} trades, WR={lwrate:.1f}%, avgPnL={lapnl:+.3f}%')
        print(f'  SHORT: {n_s} trades, WR={swrate:.1f}%, avgPnL={sapnl:+.3f}%')
        print(f'  Total signals: {signals}')
        print()

        token_stats[token] = {
            'long_wins': token_long_wins, 'long_losses': token_long_losses,
            'short_wins': token_short_wins, 'short_losses': token_short_losses,
            'long_pnls': token_long_pnls, 'short_pnls': token_short_pnls,
        }

    # ── Aggregate stats ──────────────────────────────────────────────────────────
    print('═' * 60)
    print('AGGREGATE RESULTS')
    print('═' * 60)
    total_long_wins = sum(s['long_wins'] for s in token_stats.values())
    total_long_losses = sum(s['long_losses'] for s in token_stats.values())
    total_short_wins = sum(s['short_wins'] for s in token_stats.values())
    total_short_losses = sum(s['short_losses'] for s in token_stats.values())
    all_long_pnls  = [p for s in token_stats.values() for p in s['long_pnls']]
    all_short_pnls = [p for s in token_stats.values() for p in s['short_pnls']]

    n_lt = total_long_wins + total_long_losses
    n_st = total_short_wins + total_short_losses
    lwrate_t = total_long_wins / n_lt * 100 if n_lt else 0
    swrate_t = total_short_wins / n_st * 100 if n_st else 0
    lapnl_t  = statistics.mean(all_long_pnls)  if all_long_pnls  else 0
    sapnl_t  = statistics.mean(all_short_pnls) if all_short_pnls else 0

    print(f'LONG:  {n_lt} trades, WR={lwrate_t:.1f}%, avgPnL={lapnl_t:+.3f}%')
    print(f'SHORT: {n_st} trades, WR={swrate_t:.1f}%, avgPnL={sapnl_t:+.3f}%')
    print(f'TOTAL: {n_lt+n_st} trades')

    # Confidence tier breakdown
    print()
    print('BY CONFIDENCE TIER:')
    for tier, lo, hi in [('HIGH 75-88', 75, 88), ('MID 60-74', 60, 74), ('LOW 50-59', 50, 59)]:
        tier_trades = [r for r in results if lo <= r['confidence'] <= hi]
        if tier_trades:
            wr  = sum(t['win'] for t in tier_trades) / len(tier_trades) * 100
            pn  = statistics.mean(t['pnl_pct'] for t in tier_trades)
            print(f'  {tier}: {len(tier_trades)} trades, WR={wr:.1f}%, avgPnL={pn:+.3f}%')

    # Direction breakdown
    print()
    print('BY DIRECTION:')
    for d in ('LONG', 'SHORT'):
        d_trades = [r for r in results if r['direction'] == d]
        if d_trades:
            wr = sum(t['win'] for t in d_trades) / len(d_trades) * 100
            pn = statistics.mean(t['pnl_pct'] for t in d_trades)
            print(f'  {d}: {len(d_trades)} trades, WR={wr:.1f}%, avgPnL={pn:+.3f}%')


if __name__ == '__main__':
    main()
