#!/usr/bin/env python3
"""
Structure Analysis — per-timeframe HH/HL/LH/LL sequences, channel state,
and structure-break levels. Feeds the full-analysis skill (structure section).

Usage: python3 structure_analysis.py [COIN] [tf1 tf2 ...]
Defaults: BTC on 1m 5m 15m 1h 4h.

Design notes:
- Swings via ZIGZAG with an ATR-scaled reversal threshold (0.6 x ATR(14)).
  A fixed bar-window fractal CANNOT see staircases — in a rising channel each
  higher low is not a local minimum of a ±N window (the earlier deeper low
  dominates). Zigzag confirms a swing when price retraces by the threshold
  from the running extreme, which captures the HH/HL ladder as drawn.
- Four structure states per TF:
    UPTREND     — higher highs + higher lows
    DOWNTREND   — lower highs + lower lows
    COMPRESSION — higher lows + lower highs (triangle coil -> expansion next)
    EXPANSION   — lower lows + higher highs (broadening -> chaos/transition)
- Structure break = price beyond the last opposite swing (zigzag swing point).
  Wick sweeps are the zigzag's liquidity grab (full-analysis §11) — a break
  tag here is a LEVEL STATE; the close-based confirmation is the trade rule.
- SL/TP belong AT these swing levels, never at round numbers.
"""
import sys
import os
import sqlite3
from paths import HERMES_DATA

MAX_SWINGS_SHOWN = 4
TF_LIMIT = {'1m': 300, '5m': 300, '15m': 200, '1h': 150, '4h': 100}
ATR_LEN = 14
ZIGZAG_ATR_MULT = 0.6   # reversal threshold as fraction of ATR


def load_candles(token, tf, limit):
    conn = sqlite3.connect(os.path.join(HERMES_DATA, 'candles.db'))
    cur = conn.cursor()
    cur.execute(f"SELECT ts, high, low, close FROM candles_{tf} "
                "WHERE token=? AND is_closed=1 ORDER BY ts DESC LIMIT ?",
                (token, limit))
    rows = cur.fetchall()
    conn.close()
    return [(r[0], float(r[1]), float(r[2]), float(r[3])) for r in reversed(rows)]


def atr(candles, length=ATR_LEN):
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i][1], candles[i][2], candles[i - 1][3]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if len(trs) < length:
        return trs[-1] if trs else 0.0
    return sum(trs[-length:]) / length


def zigzag(candles, thresh):
    """Return confirmed swings as list of ('H'|'L', idx, price).

    One confirmation per bar max: after a swing confirms, the same bar must
    NOT be able to confirm the opposite swing (a wide bar's full range would
    otherwise append both — that produced ~1 swing per bar in testing).
    """
    swings = []
    direction = None       # 'up' or 'down' — the leg being extended
    ext_i, ext_p = 0, candles[0][1]
    for i in range(1, len(candles)):
        h, l = candles[i][1], candles[i][2]
        if direction in (None, 'up'):
            if h >= ext_p:
                ext_i, ext_p = i, h
            if ext_p - l >= thresh:          # reversal down confirmed
                swings.append(('H', ext_i, ext_p))
                direction = 'down'
                ext_i, ext_p = i, l
                continue                     # one swing per bar
        if direction == 'down':
            if l <= ext_p:
                ext_i, ext_p = i, l
            if h - ext_p >= thresh:          # reversal up confirmed
                swings.append(('L', ext_i, ext_p))
                direction = 'up'
                ext_i, ext_p = i, h
    return swings


def classify(swings, last_close):
    hs = [s for s in swings if s[0] == 'H']
    ls = [s for s in swings if s[0] == 'L']
    if len(hs) < 2 or len(ls) < 2:
        return 'UNDEFINED', '', None, None
    # swings are (type, idx, price) — price is index [2]
    hh = hs[-1][2] > hs[-2][2]
    hl = ls[-1][2] > ls[-2][2]
    last_sh, last_sl = hs[-1][2], ls[-1][2]
    if hh and hl:
        state, broken = 'UPTREND', last_close < last_sl
    elif (not hh) and (not hl):
        state, broken = 'DOWNTREND', last_close > last_sh
    elif hl and not hh:
        state, broken = 'COMPRESSION', False      # HL + LH coil
    elif hh and not hl:
        state, broken = 'EXPANSION', False        # HH + LL broadening
    else:
        state, broken = 'MIXED', False
    tags = ('HH' if hh else 'LH') + ' ' + ('HL' if hl else 'LL')
    return state, tags, last_sh, last_sl


def analyze(token, tf):
    candles = load_candles(token, tf, TF_LIMIT.get(tf, 200))
    if len(candles) < 50:
        return f'  {tf:4s}: insufficient data ({len(candles)} bars)'
    last_close = candles[-1][3]
    a = atr(candles)
    if a <= 0:
        return f'  {tf:4s}: zero ATR — data suspect'
    swings = zigzag(candles, a * ZIGZAG_ATR_MULT)
    state, tags, last_sh, last_sl = classify(swings, last_close)
    broken = ''
    if state == 'UPTREND' and last_close < last_sl:
        broken = 'BROKEN! '
    elif state == 'DOWNTREND' and last_close > last_sh:
        broken = 'BROKEN! '
    # Slope: price change per bar across the swing span
    slope = 0.0
    if len(swings) >= 2:
        # swings are (type, idx, price) — idx is [1], price is [2]
        s0 = swings[-4] if len(swings) >= 4 else swings[0]
        s1 = swings[-1]
        i0, p0 = s0[1], s0[2]
        i1, p1 = s1[1], s1[2]
        bars = max(1, i1 - i0)
        slope = (p1 - p0) / p0 * 100.0 / bars
    # Price position vs last swing range
    if last_sh and last_sl and last_sh > last_sl:
        if last_close > last_sh:
            pos = f'above last SH (+{(last_close-last_sh)/last_close*100:.2f}%)'
        elif last_close < last_sl:
            pos = f'below last SL (-{(last_sl-last_close)/last_close*100:.2f}%)'
        else:
            pos = f'in-range {(last_close-last_sl)/(last_sh-last_sl)*100:.0f}%'
    else:
        pos = ''
    n_sw = len([s for s in swings])
    return (f'  {tf:4s}: {broken}{state:11s} [{tags}] '
            f'SH={last_sh:.6g} SL={last_sl:.6g} slope={slope:+.3f}%/bar {pos} '
            f'(ATR {a:.6g}, {n_sw} swings)')


def main():
    args = sys.argv[1:]
    token = args[0].upper() if args and not args[0].isdigit() else 'BTC'
    tfs = [a for a in args if a in TF_LIMIT] or ['1m', '5m', '15m', '1h', '4h']
    print(f'STRUCTURE — {token} (zigzag 0.6xATR({ATR_LEN}), swings alternate H/L):')
    for tf in tfs:
        try:
            print(analyze(token, tf))
        except Exception as e:
            print(f'  {tf:4s}: error — {e}')


if __name__ == '__main__':
    main()
