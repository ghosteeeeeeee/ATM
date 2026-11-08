#!/usr/bin/env python3
"""ADX/ATR trend-lifecycle analysis — multi-timeframe (CEO rules, 2026-10-27).

The three rules:
  1. ADX back to ~0        → previous trend ENDED, a new trend is starting
  2. ADX peaks, then price prints a NEW major extreme after that peak
                             → exhaustion (5th-wave) → the move is usually over
     (price usually continues the OTHER way from the exhausted extreme)
  3. ADX peak + ATR peak   → climaxed move is over; a new extreme printed
                             after the dual-peak confirms it

Data: LOCAL candles.db, CLOSED bars only (full-analysis data-source rule).
ADX math = the reference implementation in backtest_trend_momentum_v3
(single source — imported, not copied).

Run: python3 scripts/adx_atr_analysis.py [COIN]     (default BTC)
"""
import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA
from hermes_constants import (ADX_PERIOD, ADX_NEAR_ZERO, ADX_PEAK_LOOKBACK,
                              ADX_PEAK_MIN_FALL, ADX_DUAL_PEAK_TOL,
                              ADX_EXTREME_WINDOW)
from backtest_trend_momentum_v3 import compute_adx   # reference ADX impl

TFS = ['1m', '5m', '15m', '1h', '4h']
BARS = 300


def _load(tf, token):
    """Closed candles: (highs, lows, closes) oldest→newest. Local DB only."""
    con = sqlite3.connect(f'file:{HERMES_DATA}/candles.db?mode=ro', uri=True)
    try:
        cur = con.cursor()
        cur.execute(f"SELECT high, low, close FROM candles_{tf} "
                    f"WHERE token=? AND is_closed=1 ORDER BY ts DESC LIMIT {BARS}",
                    (token,))
        rows = list(reversed(cur.fetchall()))
    finally:
        con.close()
    return [r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows]


def _wilder_atr(highs, lows, closes, period):
    """Wilder ATR series aligned with input bars (None until warm)."""
    trs = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        trs.append(max(highs[i] - lows[i],
                       abs(highs[i] - closes[i - 1]),
                       abs(lows[i] - closes[i - 1])))
    atr = [None] * len(trs)
    if len(trs) < period:
        return atr
    a = sum(trs[:period]) / period
    atr[period - 1] = a
    for i in range(period, len(trs)):
        a = (a * (period - 1) + trs[i]) / period
        atr[i] = a
    return atr


def _adx_peak(series):
    """Local ADX peak over the lookback: (peak_val, peak_idx, bars_ago, peaked).
    'peaked' = peak ≥3 bars back AND current fell ADX_PEAK_MIN_FALL below it."""
    vals = [(i, v) for i, v in enumerate(series) if v is not None]
    if not vals:
        return None
    win = vals[-min(ADX_PEAK_LOOKBACK, len(vals)):]
    pi, pv = max(win, key=lambda t: t[1])
    last_i, lv = win[-1]
    bars_ago = last_i - pi
    return pv, pi, bars_ago, (bars_ago >= 3 and lv <= pv - ADX_PEAK_MIN_FALL)


def _atr_peak(series):
    """ATR peak: peaked = ≥3 bars back AND current ≤90% of peak (10% off)."""
    vals = [(i, v) for i, v in enumerate(series) if v is not None]
    if not vals:
        return None
    win = vals[-min(ADX_PEAK_LOOKBACK, len(vals)):]
    pi, pv = max(win, key=lambda t: t[1])
    last_i, lv = win[-1]
    bars_ago = last_i - pi
    return pv, pi, bars_ago, (bars_ago >= 3 and lv <= pv * 0.90)


def _post_peak_extreme(peak_idx, highs, lows):
    """Rule 2/3 confirmation: new MAJOR price extreme printed AFTER the ADX
    peak vs the ADX_EXTREME_WINDOW bars before it. Returns flag strings."""
    flags = []
    if peak_idx <= 0:
        return flags
    pre = slice(max(0, peak_idx - ADX_EXTREME_WINDOW), peak_idx)
    post_idx = range(peak_idx + 1, len(lows))
    if not post_idx:
        return flags
    pre_lo, pre_hi = min(lows[pre]), max(highs[pre])
    post_lo = min(lows[i] for i in post_idx)
    post_hi = max(highs[i] for i in post_idx)
    if post_lo < pre_lo:
        flags.append('new major LOW after peak')
    if post_hi > pre_hi:
        flags.append('new major HIGH after peak')
    return flags


def lifecycle(tf, token):
    """One timeframe → dict with ADX/ATR values, peaks, and rule verdict."""
    highs, lows, closes = _load(tf, token)
    if len(closes) < ADX_PERIOD * 3 + 5:
        return None
    adx = compute_adx(highs, lows, closes, ADX_PERIOD)
    atr = _wilder_atr(highs, lows, closes, ADX_PERIOD)
    cur_adx = next((v for v in reversed(adx) if v is not None), None)
    cur_atr = next((v for v in reversed(atr) if v is not None), None)
    if cur_adx is None or cur_atr is None:
        return None

    a_pk = _adx_peak(adx)
    t_pk = _atr_peak(atr)
    apv, api, aba, a_peaked = a_pk
    tpv, tpi, tba, t_peaked = t_pk
    dual = a_peaked and t_peaked and abs(aba - tba) <= ADX_DUAL_PEAK_TOL
    flags = _post_peak_extreme(api, highs, lows)

    # Rule priority: 1 (trendless) > 3 (dual climax) > 2 (exhaustion) > running
    if cur_adx < ADX_NEAR_ZERO:
        state = (f"TRENDLESS — ADX {cur_adx:.1f} at zero: last trend ended, "
                 f"NEW trend starting (rule 1)")
    elif dual:
        apart = abs(aba - tba)
        conf = (", CONFIRMED by " + flags[0] if flags else
                " — awaiting post-peak extreme for confirmation (rule 3)")
        state = (f"DUAL-PEAK CLIMAX — ATR {tpv:.0f} & ADX {apv:.1f} peaked "
                 f"{apart} bar{'s' if apart != 1 else ''} apart: "
                 f"move is over{conf}")
    elif a_peaked and flags:
        state = (f"EXHAUSTION — ADX peaked {aba} bars ago ({apv:.1f}→{cur_adx:.1f}), "
                 f"price made {flags[0]} → move usually over, expect continuation "
                 f"the other way (rule 2)")
    elif a_peaked:
        state = (f"ADX PEAKED {aba} bars ago ({apv:.1f}→{cur_adx:.1f}) — "
                 f"watch for a post-peak extreme to confirm (rule 2 pending)")
    else:
        rising = len([v for v in adx[-7:] if v is not None]) >= 2 and \
            cur_adx > [v for v in adx[-7:] if v is not None][0]
        state = ("TREND RUNNING — ADX rising" if rising
                 else "TREND FADING — ADX falling, no peak yet")

    atr_pct = cur_atr / closes[-1] * 100
    return {'tf': tf, 'adx': cur_adx, 'adx_peak': apv, 'adx_peak_bars': aba,
            'adx_peaked': a_peaked, 'atr': cur_atr, 'atr_pct': atr_pct,
            'atr_peak': tpv, 'atr_peak_bars': tba, 'atr_peaked': t_peaked,
            'dual_peak': dual, 'extreme_flags': flags, 'state': state,
            'price': closes[-1]}


def main():
    token = (sys.argv[1] if len(sys.argv) > 1 else 'BTC').upper()
    print(f"ADX/ATR LIFECYCLE — {token} (period {ADX_PERIOD}, closed bars, local DB)")
    results = []
    for tf in TFS:
        try:
            r = lifecycle(tf, token)
        except Exception as e:
            print(f"  {tf:>4}: ERROR {e}")
            continue
        if not r:
            print(f"  {tf:>4}: insufficient data")
            continue
        results.append(r)
        print(f"  {tf:>4}: ADX {r['adx']:5.1f} (peak {r['adx_peak']:.1f} "
              f"{r['adx_peak_bars']}b ago) | ATR {r['atr']:.1f} "
              f"({r['atr_pct']:.2f}%) (peak {r['atr_peak']:.0f} "
              f"{r['atr_peak_bars']}b ago)")
        print(f"        → {r['state']}")
    # Combined read: rule-1 flags anywhere = fresh-trend zones; exhaustion
    # flags on higher TFs date the dominant move.
    trendless = [r['tf'] for r in results if r['adx'] < ADX_NEAR_ZERO]
    exhausted = [r['tf'] for r in results if r['extreme_flags'] and r['adx_peaked']]
    duals = [r['tf'] for r in results if r['dual_peak']]
    print("COMBINED: " + ", ".join([
        f"trendless: {trendless}" if trendless else "trendless: none",
        f"exhaustion flags: {exhausted}" if exhausted else "exhaustion flags: none",
        f"dual-peak: {duals}" if duals else "dual-peak: none",
    ]))


if __name__ == '__main__':
    main()
