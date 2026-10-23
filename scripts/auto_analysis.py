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
    db_path = os.path.join(HERMES_DATA, 'candles.db')
    if not os.path.exists(db_path):   # never create an empty candles.db
        return None
    conn = sqlite3.connect(db_path)
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
    db_path = os.path.join(HERMES_DATA, 'candles.db')
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
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

def score_direction(ind, continuum, direction='long', struct=None):
    """Skill probability table. Returns (total, trend_part, reasons).

    trend_part = 1h/15m/5m MACD + continuum — ONLY this gets halved in CHOP
    (skill chop-regime rule: halve trend inputs, not the total — bug_hunter
    parity fix). direction='short' inverts sign-carrying rows (MACD,
    continuum, EMA50, Pattern); RSI/volume/Z rows are direction-neutral per
    the table. Pattern row = structure-engine state (skill: Continuation
    +5 / Reversal-against-you -5): UPTREND=continuation for long,
    DOWNTREND=reversal against long, COMPRESSION/EXPANSION=0.
    """
    sign = 1 if direction == 'long' else -1
    s = 0
    trend = 0
    reasons = []
    # trend inputs: 1h/15m/5m MACD (halved in chop)
    for tf, pts in (('1h', 15), ('15m', 10), ('5m', 10)):
        t = ind.get(tf)
        if not t:
            continue
        v = (pts if t['macd_bull'] else -pts) * sign
        s += v
        trend += v
        reasons.append(f"{tf} MACD {'BULL' if t['macd_bull'] else 'BEAR'} {v:+d}")
    # continuum with linreg (skill row: ABOVE+BULL = +15, BELOW+BEAR = -15;
    # position-vs-linreg mismatch = partial ±5)
    if continuum:
        pos = continuum.get('ema300_position')
        lin = str(continuum.get('linreg_direction') or '')
        above = pos == 'ABOVE'
        matching = (above and 'BULL' in lin) or ((not above) and 'BEAR' in lin)
        base = (15 if above else -15) if matching else (5 if above else -5)
        pts = base * sign
        s += pts
        trend += pts
        reasons.append(f"continuum {pos}+{lin or '?'} {pts:+d}")
    # RSI: executing TF (5m) extremes — direction-neutral row
    t5 = ind.get('5m')
    if t5:
        if 45 <= t5['rsi'] <= 60:
            s += 10
            reasons.append("RSI sweet spot +10")
        elif t5['rsi'] < 30 or t5['rsi'] > 70:
            s -= 10
            reasons.append(f"RSI {t5['rsi']:.0f} extreme -10")
    # volume — direction-neutral row. 5m/15m only: skill "1m volume alone =
    # noise" — averaging it in dilutes conviction readings (parity fix).
    vols = [ind[t]['vol'] for t in ('5m', '15m') if t in ind]
    if vols:
        mv = sum(vols) / len(vols)
        if mv >= 1.5:
            s += 10
            reasons.append(f"volume surge {mv:.1f}x +10")
        elif mv < 0.5:
            s -= 10
            reasons.append(f"volume dead {mv:.1f}x -10")
    # Z-Score (5m): direction-neutral row
    if t5:
        if abs(t5['z']) > 2:
            s -= 10
            reasons.append(f"5m Z {t5['z']:+.2f} extreme -10")
        elif abs(t5['z']) <= 1:
            s += 5
            reasons.append("5m Z neutral +5")
    # EMA50 alignment — direction-aware (parity fix: short must NOT get +5
    # for price sitting above EMA50)
    above = sum(1 for t in ind.values() if t['ema50_dist'] > 0)
    ema_pts = (5 if above >= 3 else -5) * sign
    s += ema_pts
    reasons.append(f"EMA50 above on {above}/5 TFs {ema_pts:+d}")
    # Pattern row (skill table) — structure engine as the deterministic proxy
    if struct:
        cell = struct.get('15m') or struct.get('1h')
        pst = cell.get('state') if isinstance(cell, dict) else cell
        if pst == 'UPTREND':
            pts = 5 * sign
        elif pst == 'DOWNTREND':
            pts = -5 * sign
        else:
            pts = 0
        s += pts
        reasons.append(f"pattern {pst or 'unavailable'} {pts:+d}")
    return s, trend, reasons


def build_decision(cycle_id, open_positions, cfg):
    """The full cycle: analyze → score → decide → bracket levels."""
    token = 'BTC'
    price_rows = tf_indicators(token, '1m')
    price = price_rows['price'] if price_rows else None
    flips, continuum = chop_flips_24h(token)
    chop = flips is not None and flips >= 2
    regime = 'CHOP' if chop else ('TREND' if flips is not None else 'UNKNOWN')

    try:
        ind = {tf: tf_indicators(token, tf) for tf in ('1m', '5m', '15m', '1h', '4h')}
        ind = {k: v for k, v in ind.items() if v}
        struct = structure_summary(token)
    except Exception as e:
        # missing candles table etc — fail to STAND_DOWN, never crash (note 2)
        return {'ts': time.time(), 'cycle_id': cycle_id, 'price': price,
                'regime_state': regime, 'flips_24h': flips, 'structure': {},
                'score_long': 0, 'score_short': 0, 'score_adj_best': 'ERR',
                'decision': 'STAND_DOWN', 'mode': cfg.get('mode', 'shadow'),
                'reasons': [f'indicator failure: {e}']}

    score_long, trend_long, reasons_long = score_direction(
        ind, continuum, 'long', struct)
    score_short, trend_short, reasons_short = score_direction(
        ind, continuum, 'short', struct)
    # CHOP halving: ONLY trend inputs (skill rule), toward zero per subtotal
    if chop:
        score_long = int(trend_long / 2) + (score_long - trend_long)
        score_short = int(trend_short / 2) + (score_short - trend_short)

    # Missing-data guards: no chop check or no indicators → no aggression
    if flips is None or not ind:
        reasons = (["chop check unavailable — mandatory gate failed, "
                    "STAND_DOWN"] if flips is None else
                   ["no indicator data — STAND_DOWN"])
        return {'ts': time.time(), 'cycle_id': cycle_id, 'price': price,
                'regime_state': regime, 'flips_24h': flips,
                'structure': {tf: s['state'] for tf, s in struct.items()},
                'score_long': score_long, 'score_short': score_short,
                'score_adj_best': regime, 'decision': 'STAND_DOWN',
                'mode': cfg.get('mode', 'shadow'), 'reasons': reasons}

    btc_open = [p for p in open_positions if p['token'] == token]
    reasons = []
    # CHOP REGIME flag goes FIRST in decision-level reasons (persisted in
    # full — the skill mandates the flag; per-direction lists are truncated
    # to [:4] for display and silently dropped it, bug_hunter finding).
    if chop:
        reasons.append("CHOP REGIME — trend inputs halved; momentum over "
                       "trend, live-tape reads outrank trend scores")
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
                atr1 = h1.get('atr', 400) or 400
                cushion = max(30.0, 0.10 * atr1)
                risk = 0.5 * atr1
                rng = sh - sl  # range for measured-move targets
                # §12 FIXED DIRECTION MAPPING (skill: break down = SHORT,
                # break up = LONG — never silently all-longs; the 10-22 miss
                # wired both legs LONG and a breakdown long fired at the low).
                # Continuation geometry: SL retests the broken level (failed
                # break), TP = measured move of the range. CEOS: any leg
                # override (e.g. "defense long") is an explicit instruction,
                # never the default.
                bracket = {
                    'short': {'trigger': round(sl - cushion, 2),
                              'sl': round(sl + risk, 2),
                              'tp': round(sl - rng, 2),
                              'trigger_dir': 'below'},
                    'long': {'trigger': round(sh + cushion, 2),
                             'sl': round(sh - risk, 2),
                             'tp': round(sh + rng, 2),
                             'trigger_dir': 'above'},
                }
                # Skill mandate: PRINT the mapping back with every bracket
                reasons.append(
                    f"BRACKET MAPPING: lower-break {sl:.0f} → SHORT "
                    f"@{bracket['short']['trigger']:.0f} "
                    f"(SL {bracket['short']['sl']:.0f}, TP {bracket['short']['tp']:.0f}); "
                    f"upper-break {sh:.0f} → LONG "
                    f"@{bracket['long']['trigger']:.0f} "
                    f"(SL {bracket['long']['sl']:.0f}, TP {bracket['long']['tp']:.0f})")
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
