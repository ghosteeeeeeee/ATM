#!/usr/bin/env python3
"""
auto_analysis — scriptable full-analysis → decision object (spec §2 skill 1).

Runs the SAME engines the skill uses (chop flip counter, structure engine,
MTF scoring with chop adjustment) and emits a machine-readable decision.
One brain, two consumers — this never re-implements judgment, it packages it.

Scoring mirrors full-analysis §Probability + chop adjustment verbatim:
trend inputs (1h/15m/5m MACD, continuum) halved in CHOP (>=2 flips/24h).
"""
import os
import sys
import json
import time
import sqlite3
import statistics

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA
import structure_analysis as SA

CONTINUUM = os.path.join('/var/www/hermes/data', 'continuum_data.json')


# ---------- engines (same logic as the skill) ----------

def chop_flips_24h(coin='BTC'):
    """Hourly EMA300-position flips in the last 24h (skill chop check)."""
    try:
        with open(CONTINUUM) as f:
            d = json.load(f)
        h = [e for e in d['history'] if e.get('token') == coin]
        if not h:
            return None, None
        now = h[-1]['ts']
        hours = {}
        for e in h:
            if e['ts'] < now - 86400:
                continue
            hours[time.gmtime(e['ts']).tm_hour] = 'ABOVE' if e['price'] > e['ema300'] else 'BELOW'
        states = [hours[k] for k in sorted(hours)]
        flips = sum(1 for a, b in zip(states, states[1:]) if a != b)
        c = d.get('current', {})
        return flips, c
    except Exception:
        return None, None


def _ema(data, period):
    k = 2 / (period + 1)
    e = [data[0]]
    for i in range(1, len(data)):
        e.append(data[i] * k + e[-1] * (1 - k))
    return e


def tf_indicators(token, tf, limit=200):
    conn = sqlite3.connect(os.path.join(HERMES_DATA, 'candles.db'))
    cur = conn.cursor()
    cur.execute(f"SELECT high, low, close, volume FROM candles_{tf} "
                "WHERE token=? AND is_closed=1 ORDER BY ts DESC LIMIT ?",
                (token, limit))
    rows = [r for r in cur.fetchall()][::-1]
    conn.close()
    if len(rows) < 50:
        return None
    closes = [r[2] for r in rows]
    vols = [r[3] for r in rows]
    ema50 = _ema(closes, 50)
    ema8 = _ema(closes, 8)
    macd_line = [a - b for a, b in zip(ema8, ema50)]
    sig = _ema(macd_line, 12)
    gains = [max(0, closes[i] - closes[i-1]) for i in range(1, len(closes))]
    losses = [max(0, closes[i-1] - closes[i]) for i in range(1, len(closes))]
    ag = sum(gains[-14:]) / 14
    al = sum(losses[-14:]) / 14
    rsi = 100 - (100 / (1 + (ag / al if al > 0 else 100))) if al > 0 else 100.0
    w = closes[-20:]
    z = ((closes[-1] - statistics.mean(w)) / statistics.stdev(w)
         if len(w) > 1 and statistics.stdev(w) > 0 else 0.0)
    avg_vol = sum(vols[-21:-1]) / 20 if len(vols) > 20 else sum(vols) / len(vols)
    vol = vols[-1] / avg_vol if avg_vol > 0 else 0.0
    ema50_dist = (closes[-1] - ema50[-1]) / ema50[-1] * 100
    return {'rsi': rsi, 'macd_bull': macd_line[-1] > sig[-1], 'z': z,
            'vol': vol, 'ema50_dist': ema50_dist, 'price': closes[-1]}


def atr_pct(token, tf='1h', length=14):
    conn = sqlite3.connect(os.path.join(HERMES_DATA, 'candles.db'))
    cur = conn.cursor()
    cur.execute(f"SELECT high, low, close FROM candles_{tf} "
                "WHERE token=? AND is_closed=1 ORDER BY ts DESC LIMIT ?",
                (token, length + 1))
    rows = cur.fetchall()
    conn.close()
    if len(rows) < length + 1:
        return None
    trs = [max(rows[i][0] - rows[i][1],
               abs(rows[i][0] - rows[i-1][2]),
               abs(rows[i][1] - rows[i-1][2])) for i in range(1, len(rows))]
    atr = sum(trs) / length
    return atr / rows[-1][2] * 100  # percent


def structure_summary(token):
    """Per-TF state via the structure engine (module reuse)."""
    out = {}
    for tf in ('1m', '5m', '15m', '1h', '4h'):
        try:
            candles = SA.load_candles(token, tf, SA.TF_LIMIT.get(tf, 200))
            if len(candles) < 50:
                continue
            a = SA.atr(candles)
            swings = SA.zigzag(candles, a * SA.ZIGZAG_ATR_MULT)
            state, tags, sh, sl = SA.classify(swings, candles[-1][3])
            out[tf] = {'state': state, 'tags': tags, 'sh': sh, 'sl': sl,
                       'atr': a, 'price': candles[-1][3]}
        except Exception:
            continue
    return out


# ---------- scoring (skill table verbatim) ----------

def score_direction(ind, continuum, chop):
    """Raw score per skill probability table; caller applies chop halving."""
    s = 0
    reasons = []
    # trend inputs: 1h/15m/5m MACD + continuum (halved in chop)
    for tf, pts in (('1h', 15), ('15m', 10), ('5m', 10)):
        t = ind.get(tf)
        if not t:
            continue
        v = pts if t['macd_bull'] else -pts
        s += v
        reasons.append(f"{tf} MACD {'BULL' if t['macd_bull'] else 'BEAR'} {v:+d}")
    cont_bull = continuum and continuum.get('ema300_position') == 'ABOVE'
    cont_pts = 15 if cont_bull else -15
    s += cont_pts
    reasons.append(f"continuum {'ABOVE' if cont_bull else 'BELOW'} {cont_pts:+d}")
    # RSI: executing TF (5m) extremes
    t5 = ind.get('5m')
    if t5:
        if 45 <= t5['rsi'] <= 60:
            s += 10; reasons.append("RSI sweet spot +10")
        elif t5['rsi'] < 30 or t5['rsi'] > 70:
            s -= 10; reasons.append(f"RSI {t5['rsi']:.0f} extreme -10")
    # volume
    vols = [ind[t]['vol'] for t in ('1m', '5m', '15m') if t in ind]
    if vols:
        mv = sum(vols) / len(vols)
        if mv >= 1.5:
            s += 10; reasons.append(f"volume surge {mv:.1f}x +10")
        elif mv < 0.5:
            s -= 10; reasons.append(f"volume dead {mv:.1f}x -10")
    # Z-Score (5m): extreme against, neutral for
    if t5:
        if abs(t5['z']) > 2:
            s -= 10; reasons.append(f"5m Z {t5['z']:+.2f} extreme -10")
        elif abs(t5['z']) <= 1:
            s += 5; reasons.append("5m Z neutral +5")
    # EMA50 alignment: count TFs above
    above = sum(1 for t in ind.values() if t['ema50_dist'] > 0)
    s += 5 if above >= 3 else -5
    reasons.append(f"EMA50 above on {above}/5 TFs")
    return s, reasons


def build_decision(cycle_id, open_positions, cfg):
    """The full cycle: analyze → score → decide → bracket levels."""
    token = 'BTC'
    price_rows = tf_indicators(token, '1m')
    price = price_rows['price'] if price_rows else None
    flips, continuum = chop_flips_24h(token)
    chop = flips is not None and flips >= 2
    regime = 'CHOP' if chop else 'TREND'

    ind = {tf: tf_indicators(token, tf) for tf in ('1m', '5m', '15m', '1h', '4h')}
    ind = {k: v for k, v in ind.items() if v}
    struct = structure_summary(token)

    score_long, reasons_long = score_direction(ind, continuum, chop)
    score_short, reasons_short = score_direction(
        {k: {**v, 'macd_bull': not v['macd_bull']} for k, v in ind.items()},
        None if not continuum else {**continuum,
            'ema300_position': 'BELOW' if continuum.get('ema300_position') == 'ABOVE' else 'ABOVE'},
        chop)
    # chop halving of trend inputs: approximate by halving the total toward zero
    if chop:
        score_long = int(score_long / 2)
        score_short = int(score_short / 2)

    btc_open = [p for p in open_positions if p['token'] == token]
    reasons = []
    decision = 'STAND_DOWN'
    bracket = None

    a_pct = atr_pct(token) or 0.5

    if not btc_open:
        best = max(score_long, score_short)
        if best >= 30 and regime == 'TREND':
            decision = 'SINGLE_SIDE'
            reasons.append(f"score {best:+d} in TREND regime")
        elif abs(score_long - score_short) >= 20 and best >= 15 and regime == 'TREND':
            decision = 'SINGLE_SIDE'
            reasons.append(f"one-sided score {score_long:+d}/{score_short:+d} in TREND")
        else:
            decision = 'BRACKET'
            reasons.append(f"no-edge state ({score_long:+d}/{score_short:+d}, "
                           f"{regime} {flips} flips) — §12 bracket default")
            h1 = struct.get('1h') or {}
            sh, sl = h1.get('sh'), h1.get('sl')
            if sh and sl and sh > sl:
                cushion = max(30.0, 0.10 * h1.get('atr', 400))
                risk = 0.5 * h1.get('atr', 400)
                into = 0.10 * h1.get('atr', 400)
                bracket = {
                    'long': {'trigger': round(sl - cushion, 2),
                             'sl': round(sl - cushion - risk, 2),
                             'tp': round(sh - into, 2)},
                    'short': {'trigger': round(sh + cushion, 2),
                              'sl': round(sh + cushion + risk, 2),
                              'tp': round(sl + into, 2)},
                }
            else:
                decision = 'STAND_DOWN'
                reasons.append('no usable 1h structure for bracket')
    else:
        pos = btc_open[0]
        entry = float(pos['entry_price'] or 0)
        cur_px = float(pos['current_price'] or price or 0)
        pnl_pct = ((cur_px - entry) / entry * 100 if pos['direction'] == 'LONG'
                   else (entry - cur_px) / entry * 100) if entry else 0
        if pnl_pct >= 0.3:
            decision = 'ADD_OK' if cfg.get('phase', 0) >= 2 else 'MANAGE_ONLY'
            reasons.append(f"position in favor +{pnl_pct:.2f}% — "
                           + ("add criteria window" if decision == 'ADD_OK'
                              else "phase 0/1: manage only"))
        else:
            decision = 'MANAGE_ONLY'
            reasons.append(f"position {'against' if pnl_pct < 0 else 'flat'} "
                           f"({pnl_pct:+.2f}%) — engines manage, never add")

    return {
        'ts': time.time(), 'cycle_id': cycle_id, 'price': price,
        'regime_state': regime, 'flips_24h': flips,
        'structure': {tf: s['state'] for tf, s in struct.items()},
        'structure_detail': struct,
        'score_long': score_long, 'score_short': score_short,
        'score_adj_best': 'CHOP' if chop else 'TREND',
        'decision': decision, 'bracket': bracket,
        'reasons': reasons + [f"long: {'; '.join(reasons_long[:4])}",
                              f"short: {'; '.join(reasons_short[:4])}"],
        'atr_pct': a_pct, 'mode': cfg.get('mode', 'shadow'),
    }


if __name__ == '__main__':
    d = build_decision('manual', [], {'mode': 'shadow', 'phase': 0})
    print(json.dumps(d, indent=1, default=str)[:2000])
