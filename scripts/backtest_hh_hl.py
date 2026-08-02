#!/usr/bin/env python3
"""
backtest_hh_hl.py — Backtest HH/HL structure signals (breakout + pullback variants).
Optimized: pre-computes swings, ATR, and structure classification once per token.

Usage:
    python3 backtest_hh_hl.py
    python3 backtest_hh_hl.py --tokens BTC ETH SOL --days 7
    python3 backtest_hh_hl.py --variant breakout
    python3 backtest_hh_hl.py --debug
"""

import sys
import os
import sqlite3
import time
import argparse
from datetime import datetime
from typing import Optional, Tuple, List, Dict
from collections import defaultdict

CANDLES_DB = '/root/.hermes/data/candles.db'      # legacy — not used
PRICE_DB   = '/root/.hermes/data/signals_hermes.db' # price_history (live 1m closes)

TOP_TOKENS = [
    'BTC', 'ETH', 'SOL', 'AVAX', 'LINK', 'SAGA', 'SCR', 'ARB', 'OP',
    'ATOM', 'NEAR', 'APT', 'INJ', 'FTM', 'CRO', 'SEI', 'TIA', 'STRK', 'WLD', 'IMX'
]
TOP_TOKENS = list(dict.fromkeys(TOP_TOKENS))[:20]

# ── Tunable params ────────────────────────────────────────────────────────────
SWING_WINDOW        = 8
MIN_SEP             = 3
BREAKOUT_THRESHOLD = 0.0005   # price must exceed HH/LL by this fraction
SL_ATR_MULT       = 1.5
TP_ATR_MULT        = 3.0
ATR_PERIOD          = 14
MAX_HOLD_BARS       = 20        # auto-close after N bars if no SL/TP hit
PULLBACK_FIB_MIN    = 0.236     # min fib retracement (23.6%)
PULLBACK_FIB_MAX    = 0.618     # max fib retracement (61.8%)
PULLBACK_ATR_MAX    = 2.0       # price must be within this many ATRs of swing level


# ── Helpers ───────────────────────────────────────────────────────────────────

def compute_atr_series(candles: list, period: int = ATR_PERIOD) -> list:
    """Pre-compute ATR value at each candle index using close-only method.
    price_history has open=high=low=close per row, so traditional TR=0.
    We use rolling (max-min) of closes over period as the volatility measure.
    ATR = sum of rolling_ranges over period / period.
    Matches _compute_atr in hh_hl_signals.py.
    """
    n = len(candles)
    result = [None] * n
    if n < period + 1:
        return result
    closes = [c['close'] for c in candles]
    # Step 1: rolling range (max - min) at each index
    ranges = [None] * n
    for i in range(period - 1, n):
        window = closes[i - period + 1 : i + 1]
        ranges[i] = max(window) - min(window)
    # Step 2: ATR = simple moving average of ranges, valid at index >= period-1
    for i in range(period - 1, n):
        window_ranges = [r for r in ranges[i - period + 1 : i + 1] if r is not None]
        if len(window_ranges) == period:
            result[i] = sum(window_ranges) / period
    return result


def find_swings_upfront(candles: list, window: int = SWING_WINDOW,
                        min_sep: int = MIN_SEP) -> Tuple[List[int], List[int]]:
    """Find all swing highs/lows. O(n)."""
    n = len(candles)
    highs, lows = [], []
    last_h, last_l = -999, -999
    for i in range(window, n - window):
        h_val = candles[i]['high']
        is_h = all(candles[j]['high'] < h_val
                   for j in range(i - window, i + window + 1) if j != i)
        if is_h and (i - last_h) >= min_sep:
            highs.append(i); last_h = i

        l_val = candles[i]['low']
        is_l = all(candles[j]['low'] > l_val
                   for j in range(i - window, i + window + 1) if j != i)
        if is_l and (i - last_l) >= min_sep:
            lows.append(i); last_l = i
    return highs, lows


def build_structure_series(candles: list, highs: List[int], lows: List[int]) -> list:
    """Pre-compute structure at every candle index. Returns list of (structure, bs_pct).
    structure: 'HH_HL' | 'LH_LL' | 'NEUTRAL'
    bs_pct: breakout strength vs last HH (LONG) or LL (SHORT)
    """
    n = len(candles)
    result = [('NEUTRAL', 0.0)] * n

    for i in range(20, n):
        vh = [h for h in highs if h <= i]
        vl = [l for l in lows  if l <= i]
        if len(vh) < 2 or len(vl) < 2:
            continue

        all_sw = sorted(
            [(h, candles[h]['high'], 'H') for h in vh] +
            [(l, candles[l]['low'],  'L') for l in vl],
            key=lambda x: x[0]
        )
        if len(all_sw) < 4:
            continue

        s0, s1, s2, s3 = all_sw[-4:]
        _, p0, t0 = s0; _, p1, t1 = s1; _, p2, t2 = s2; _, p3, t3 = s3
        price = candles[i]['close']

        struct = 'NEUTRAL'; bs = 0.0
        if t0 == 'H' and t1 == 'L' and t2 == 'H' and t3 == 'L':
            if p2 > p0 and p3 > p1:
                struct = 'HH_HL'; bs = (price - p2) / price * 100.0
            elif p2 < p0 and p3 < p1:
                struct = 'LH_LL'; bs = (p2 - price) / price * 100.0
        elif t0 == 'L' and t1 == 'H' and t2 == 'L' and t3 == 'H':
            if p3 > p1:
                struct = 'HH_HL'; bs = (price - p3) / price * 100.0
            elif p3 < p1:
                struct = 'LH_LL'; bs = (p3 - price) / price * 100.0
        elif t0 == 'H' and t1 == 'L' and t2 == 'H':
            if p2 > p0:
                struct = 'HH_HL'; bs = (price - p2) / price * 100.0
        elif t0 == 'L' and t1 == 'H' and t2 == 'L':
            if p2 < p0:
                struct = 'LH_LL'; bs = (p2 - price) / price * 100.0

        result[i] = (struct, bs)

    return result


def get_swing_prices(i: int, highs: List[int], lows: List[int],
                     candles: list) -> Tuple[Optional[float], ...]:
    """Return (HH, HL, LH, LL) from last 4 swings up to index i. None if not available."""
    vh = [h for h in highs if h <= i]
    vl = [l for l in lows  if l <= i]
    if len(vh) < 2 or len(vl) < 2:
        return (None,) * 4
    all_sw = sorted(
        [(h, candles[h]['high'], 'H') for h in vh] +
        [(l, candles[l]['low'],  'L') for l in vl],
        key=lambda x: x[0]
    )
    if len(all_sw) < 4:
        return (None,) * 4
    s0, s1, s2, s3 = all_sw[-4:]
    return s0[1], s1[1], s2[1], s3[1]   # HH, HL, LH, LL


def check_exit(trade, i: int, candles: list) -> Optional[str]:
    """Check if open trade hits SL/TP/timeout on candle i+1. Returns exit reason or None."""
    if trade is None or trade.status != 'open':
        return None
    c = candles[i+1]
    lo, hi = c['low'], c['high']
    tp_hit = trade.tp >= lo and trade.tp <= hi
    sl_hit = trade.sl >= lo and trade.sl <= hi
    if tp_hit:
        trade.close(i+1, trade.tp, 'tp'); return 'tp'
    if sl_hit:
        trade.close(i+1, trade.sl, 'sl'); return 'sl'
    if (i + 1 - trade.entry_idx) >= MAX_HOLD_BARS:
        trade.close(i+1, c['close'], 'timeout'); return 'timeout'
    return None


# ── Data fetch ─────────────────────────────────────────────────────────────────

def get_candles(token: str, days: int = 30) -> list:
    """Fetch 1m close prices from price_history (signals_hermes.db), oldest first."""
    cutoff_ts = int(time.time()) - days * 86400
    conn = sqlite3.connect(PRICE_DB, timeout=30)
    c = conn.cursor()
    c.execute("""
        SELECT timestamp, price
        FROM price_history
        WHERE token = ? AND timestamp >= ?
        ORDER BY timestamp ASC
    """, (token.upper(), cutoff_ts))
    rows = c.fetchall()
    conn.close()
    if not rows:
        return []
    # price_history is close-only: open=high=low=close
    return [{'open': r[1], 'high': r[1], 'low': r[1], 'close': r[1], 'ts': r[0]} for r in rows]


# ── Trade ───────────────────────────────────────────────────────────────────────

class Trade:
    def __init__(self, direction, entry_idx, entry_price, sl, tp, atr,
                 structure, variant):
        self.direction   = direction
        self.entry_idx   = entry_idx
        self.entry_price = entry_price
        self.sl          = sl
        self.tp          = tp
        self.atr         = atr
        self.structure   = structure
        self.variant     = variant
        self.pnl_pct     = 0.0
        self.status      = 'open'

    def close(self, idx, price, reason):
        self.status      = reason
        mult = 1 if self.direction == 'LONG' else -1
        self.pnl_pct     = mult * (price - self.entry_price) / self.entry_price * 100.0


# ── Simulate breakout ───────────────────────────────────────────────────────────

def simulate_breakout(candles: list, token: str,
                      highs: List[int], lows: List[int],
                      atr_series: list, struct_series: list,
                      debug: bool = False) -> List[Trade]:
    trades = []
    n = len(candles)
    open_trade = None

    for i in range(30, n - 1):
        # 1. Check exit for open trade
        if open_trade and open_trade.status == 'open':
            exit_reason = check_exit(open_trade, i, candles)
            if exit_reason:
                trades.append(open_trade)
                open_trade = None

        if open_trade:
            continue  # can only hold one trade at a time

        # 2. New signal check
        struct, bs = struct_series[i]
        atr = atr_series[i]
        if struct == 'NEUTRAL' or atr is None:
            continue

        price = candles[i]['close']
        vh = [h for h in highs if h <= i]
        vl = [l for l in lows  if l <= i]
        if not vh or not vl:
            continue

        # LONG: HH_HL + price breaks above last HH
        if struct == 'HH_HL':
            hh_price = candles[vh[-1]]['high']
            if price <= hh_price:
                continue
            break_pct = (price - hh_price) / price * 100.0
            if break_pct < BREAKOUT_THRESHOLD:
                continue
            sl = hh_price * (1 - SL_ATR_MULT * atr / hh_price)
            tp = price + TP_ATR_MULT * atr
            open_trade = Trade('LONG', i, price, sl, tp, atr, struct, 'breakout')
            if debug:
                print(f"  [{token}] LONG BREAK @ {price:.4f} HH={hh_price:.4f} "
                      f"break={break_pct:.3f}% ATR={atr:.4f}")

        # SHORT: LH_LL + price breaks below last LL
        elif struct == 'LH_LL':
            ll_price = candles[vl[-1]]['low']
            if price >= ll_price:
                continue
            break_pct = (ll_price - price) / price * 100.0
            if break_pct < BREAKOUT_THRESHOLD:
                continue
            sl = ll_price * (1 + SL_ATR_MULT * atr / ll_price)
            tp = price - TP_ATR_MULT * atr
            open_trade = Trade('SHORT', i, price, sl, tp, atr, struct, 'breakout')
            if debug:
                print(f"  [{token}] SHORT BREAK @ {price:.4f} LL={ll_price:.4f} "
                      f"break={break_pct:.3f}% ATR={atr:.4f}")

    # Close any remaining trade at end of data
    if open_trade and open_trade.status == 'open':
        open_trade.close(n-1, candles[-1]['close'], 'eod')
        trades.append(open_trade)

    return trades


# ── Simulate pullback ─────────────────────────────────────────────────────────

def simulate_pullback(candles: list, token: str,
                     highs: List[int], lows: List[int],
                     atr_series: list, struct_series: list,
                     debug: bool = False) -> List[Trade]:
    trades = []
    n = len(candles)
    open_trade = None

    for i in range(30, n - 2):
        # 1. Check exit
        if open_trade and open_trade.status == 'open':
            exit_reason = check_exit(open_trade, i, candles)
            if exit_reason:
                trades.append(open_trade)
                open_trade = None

        if open_trade:
            continue

        struct, bs = struct_series[i]
        atr = atr_series[i]
        if struct == 'NEUTRAL' or atr is None:
            continue

        price = candles[i]['close']
        hh, hl, lh, ll_ = get_swing_prices(i, highs, lows, candles)
        if hh is None:
            continue

        # LONG pullback: HH_HL, price pulls back to HL zone (23.6%-61.8% fib), bounces
        if struct == 'HH_HL':
            # Price must be between HH (no pullback) and HL (already at support)
            if price >= hh or price <= hl:
                continue
            # Fib zone: 23.6%-61.8% retracement from HH toward HL
            fib_min_p = hh - (hh - hl) * PULLBACK_FIB_MIN
            fib_max_p = hh - (hh - hl) * PULLBACK_FIB_MAX
            if not (fib_max_p <= price <= fib_min_p):
                continue
            # ATR proximity: price must be within PULLBACK_ATR_MAX ATRs of HL
            dist_to_hl = (price - hl) / price * 100.0
            if dist_to_hl > atr / price * 100.0 * PULLBACK_ATR_MAX:
                pass  # skip only if way too far from HL

            # Bounce check: next candle close > current close
            next_c = candles[i+1]
            if next_c['close'] <= price:
                continue  # no bounce yet

            entry = next_c['close']
            # SL: below pullback low (with buffer) and HL
            sl = min(candles[i]['low'], candles[i+1]['low'], hl) * (1 - 0.003)
            tp = hh
            open_trade = Trade('LONG', i+1, entry, sl, tp, atr, struct, 'pullback')
            if debug:
                print(f"  [{token}] LONG PULL @ {entry:.4f} HH={hh:.4f} HL={hl:.4f} "
                      f"ATR={atr:.4f} SL={sl:.4f} TP={tp:.4f}")

        # SHORT pullback: LH_LL, price rallies to LH zone, drops
        elif struct == 'LH_LL':
            if price <= ll_ or price >= lh:
                continue
            fib_min_p = ll_ + (lh - ll_) * PULLBACK_FIB_MIN
            fib_max_p = ll_ + (lh - ll_) * PULLBACK_FIB_MAX
            if not (fib_min_p <= price <= fib_max_p):
                continue

            next_c = candles[i+1]
            if next_c['close'] >= price:
                continue  # hasn't dropped yet

            entry = next_c['close']
            sl = max(candles[i]['high'], candles[i+1]['high'], lh) * (1 + 0.003)
            tp = ll_
            open_trade = Trade('SHORT', i+1, entry, sl, tp, atr, struct, 'pullback')
            if debug:
                print(f"  [{token}] SHORT PULL @ {entry:.4f} LH={lh:.4f} LL={ll_:.4f} "
                      f"ATR={atr:.4f} SL={sl:.4f} TP={tp:.4f}")

    if open_trade and open_trade.status == 'open':
        open_trade.close(n-1, candles[-1]['close'], 'eod')
        trades.append(open_trade)

    return trades


# ── Stats ──────────────────────────────────────────────────────────────────────

def compute_stats(trades: List[Trade], label: str) -> Optional[Dict]:
    if not trades:
        return None
    won     = [t for t in trades if t.pnl_pct > 0]
    lost    = [t for t in trades if t.pnl_pct <= 0 and t.status != 'eod']
    timeout = sum(1 for t in trades if t.status == 'timeout')
    total   = len(trades)
    wr      = len(won) / total * 100 if total else 0
    avg_w   = sum(t.pnl_pct for t in won)   / len(won)  if won  else 0
    avg_l   = sum(abs(t.pnl_pct) for t in lost) / len(lost) if lost else 0
    net     = sum(t.pnl_pct for t in trades)
    pf      = avg_w / avg_l if avg_l else 0

    longs  = [t for t in trades if t.direction == 'LONG']
    shorts = [t for t in trades if t.direction == 'SHORT']
    long_wr  = sum(1 for t in longs  if t.pnl_pct > 0) / len(longs)  * 100 if longs  else 0
    short_wr = sum(1 for t in shorts if t.pnl_pct > 0) / len(shorts) * 100 if shorts else 0

    return dict(label=label, total=total, won=len(won), lost=len(lost),
                timeout=timeout, wr=round(wr, 1),
                long_n=len(longs), short_n=len(shorts),
                long_wr=round(long_wr, 1), short_wr=round(short_wr, 1),
                avg_winner=round(avg_w, 3), avg_loser=round(avg_l, 3),
                net_pnl=round(net, 2), pf=round(pf, 2))


def fmt(s: Optional[Dict]) -> str:
    if not s: return "  No trades"
    return (f"  {s['label']}: {s['total']}tr "
            f"WR={s['wr']}% | L:{s['long_n']}tr {s['long_wr']}%WR "
            f"S:{s['short_n']}tr {s['short_wr']}%WR | "
            f"W=+{s['avg_winner']:.3f}% L=-{s['avg_loser']:.3f}% "
            f"PF={s['pf']} Net={s['net_pnl']:+.2f}%")


# ── Main ──────────────────────────────────────────────────────────────────────

def run_backtest(tokens: List[str], days: int, variant: str, debug: bool):
    all_stats = []

    for token in tokens:
        t0 = time.time()
        candles = get_candles(token, days)
        if not candles:
            print(f"[{token}] No data"); continue

        n = len(candles)
        t0s = datetime.fromtimestamp(candles[0]['ts']).strftime('%m-%d')
        t1s = datetime.fromtimestamp(candles[-1]['ts']).strftime('%m-%d')
        print(f"\n[{token}] {n} candles | {days}d | {t0s} -> {t1s}")

        highs, lows        = find_swings_upfront(candles)
        atr_series         = compute_atr_series(candles)
        struct_series      = build_structure_series(candles, highs, lows)
        hh_hl_count        = sum(1 for s, _ in struct_series if s == 'HH_HL')
        lh_ll_count        = sum(1 for s, _ in struct_series if s == 'LH_LL')
        print(f"  swings: {len(highs)}H/{len(lows)}L | "
              f"HH_HL={hh_hl_count} LH_LL={lh_ll_count} | "
              f"precompute done in {time.time()-t0:.1f}s")

        if variant in ('breakout', 'both'):
            trades = simulate_breakout(candles, token, highs, lows,
                                        atr_series, struct_series, debug)
            stats = compute_stats(trades, f'BREAKOUT {token}')
            print(fmt(stats))
            if stats: all_stats.append(stats)

        if variant in ('pullback', 'both'):
            trades = simulate_pullback(candles, token, highs, lows,
                                        atr_series, struct_series, debug)
            stats = compute_stats(trades, f'PULLBACK {token}')
            print(fmt(stats))
            if stats: all_stats.append(stats)

        print(f"  [{token}] total time: {time.time()-t0:.1f}s")

    if not all_stats:
        print("\nNo results."); return

    # Aggregate
    print("\n" + "="*70)
    print("AGGREGATE SUMMARY")
    print("="*70)
    for vl in ('BREAKOUT', 'PULLBACK'):
        ss = [s for s in all_stats if s and vl in s['label']]
        if not ss: continue
        tot  = sum(s['total'] for s in ss)
        won  = sum(s['won']   for s in ss)
        los  = sum(s['lost']  for s in ss)
        to_  = sum(s['timeout'] for s in ss)
        net  = sum(s['net_pnl'] for s in ss)
        lw   = sum(s['avg_winner']*s['won'] for s in ss if s['won'])
        ll   = sum(s['avg_loser'] *s['lost'] for s in ss if s['lost'])
        nw   = sum(s['won']   for s in ss)
        nl   = sum(s['lost']  for s in ss)
        avg_w = lw/nw if nw else 0
        avg_l = ll/nl if nl else 0
        wr    = won/tot*100 if tot else 0
        ln    = sum(s['long_n']  for s in ss)
        sn    = sum(s['short_n'] for s in ss)
        lwr   = sum(s['long_wr'] *s['long_n']  for s in ss if s['long_n']) / max(ln, 1)
        swr   = sum(s['short_wr']*s['short_n'] for s in ss if s['short_n']) / max(sn, 1)
        print(f"\n{vl} ({len(ss)} tokens)")
        print(f"  {tot} trades ({won}W/{los}L/{to_}T) WR={wr:.1f}%")
        print(f"  LONG  ({ln:3d}): {lwr:.1f}%WR")
        print(f"  SHORT ({sn:3d}): {swr:.1f}%WR")
        print(f"  AvgW=+{avg_w:.3f}% AvgL=-{avg_l:.3f}% PF={avg_w/avg_l:.2f} Net={net:+.2f}%")

    # Per-token table
    print("\n" + "="*70)
    print(f"{'Token':<8} {'Variant':<10} {'N':>4} {'WR%':>5} "
          f"{'LongN':>5} {'LWR%':>5} {'ShortN':>6} {'SWR%':>5} "
          f"{'AvgW%':>6} {'AvgL%':>6} {'PF':>5} {'Net%':>7}")
    print("-"*70)
    for s in all_stats:
        if not s: continue
        tok = s['label'].split(maxsplit=1)[1] if len(s['label'].split()) > 1 else s['label']
        var = s['label'].split(maxsplit=1)[0]
        print(f"{tok:<8} {var:<10} {s['total']:>4} {s['wr']:>5.1f} "
              f"{s['long_n']:>5} {s['long_wr']:>5.1f} "
              f"{s['short_n']:>6} {s['short_wr']:>5.1f} "
              f"{'+' if s['avg_winner'] >= 0 else ''}{s['avg_winner']:>5.3f} "
              f"{'-' if s['avg_loser']  >= 0 else ''}{s['avg_loser']:>5.3f} "
              f"{s['pf']:>5.2f} {s['net_pnl']:>+7.2f}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--tokens', nargs='+', default=None)
    p.add_argument('--days', type=int, default=30)
    p.add_argument('--variant', choices=['breakout', 'pullback', 'both'], default='both')
    p.add_argument('--debug', action='store_true')
    args = p.parse_args()
    tokens = args.tokens or TOP_TOKENS
    print(f"HH/HL Backtest | tokens={len(tokens)} | days={args.days} | variant={args.variant}")
    run_backtest(tokens, args.days, args.variant, args.debug)
