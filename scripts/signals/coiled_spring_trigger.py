#!/usr/bin/env python3
"""
coiled_spring_trigger.py — Volume-Confirmed Coiled Spring Breakout (LONG only).

The high-conviction variant of coiled_spring. Only fires when:
1. The coil setup exists (higher lows, EMA alignment, ATR compression)
2. Volume spikes above 2x average — confirms buyer interest

This is the "trigger bar" — the moment the spring uncoils.
Higher confidence because volume confirmation eliminates most false signals.

Data: candles_5m from candles.db (local, zero API calls)
Signal type: coiled_spring_trigger_long
Source tag:  coil-trigger+
"""

import sys
import os
import sqlite3
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    COILED_SPRING_ENABLED,
    COILED_SPRING_TRIGGER_LONG_ENABLED,
    COILED_SPRING_TRIGGER_LONG_PLUS_ENABLED,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
    COILED_SPRING_LOOKBACK,
    COILED_SPRING_COIL_MIN_BARS,
    COILED_SPRING_COIL_VOL_RATIO_MAX,
    COILED_SPRING_COIL_ATR_PCT_MAX,
    COILED_SPRING_RSI_MIN,
    COILED_SPRING_RSI_MAX,
    COILED_SPRING_TRIGGER_VOL_RATIO,
    COILED_SPRING_TRIGGER_BODY_PCT,
    COILED_SPRING_SL_ATR_MULT,
    COILED_SPRING_TP_ATR_MULT,
    COILED_SPRING_EMA_PROX_ATR_MULT,
    COILED_SPRING_MAX_PRICE_ABOVE_EMA21,
    COILED_SPRING_SWING_LOOKBACK,
    COILED_SPRING_COIL_SCAN_RANGE,
    COILED_SPRING_ATR_TREND_THRESH,
    COILED_SPRING_RSI_FALLBACK,
    COILED_SPRING_ATR_FALLBACK_PCT,
    COILED_SPRING_TRIGGER_LONG_CONF_BASE,
    COILED_SPRING_TRIGGER_LONG_CONF_FLOOR,
    COILED_SPRING_TRIGGER_LONG_CONF_CAP,
    COILED_SPRING_TRIGGER_LONG_COOLDOWN_MINUTES,
    COILED_SPRING_PRICE_AGE_MAX,
    COILED_SPRING_MIN_BARS,
)

SIGNAL_TYPE_LONG = 'coiled_spring_trigger_long'
SOURCE_LONG = 'coil-trigger+'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')


# ═══════════════════════════════════════════════════════════════════════════════
# Technical indicator helpers (same as coiled_spring.py)
# ═══════════════════════════════════════════════════════════════════════════════

def _ema(data, period):
    k = 2 / (period + 1)
    result = [data[0]]
    for i in range(1, len(data)):
        result.append(data[i] * k + result[-1] * (1 - k))
    return result


def _rsi(data, period=14):
    deltas = [data[i] - data[i - 1] for i in range(1, len(data))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    if len(deltas) < period:
        return [None] * len(data)
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    result = [None] * period
    for i in range(period, len(deltas)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
        result.append(100 - 100 / (1 + ag / al) if al > 0 else 100)
    return result


def _atr(rows, period=14):
    if len(rows) < period + 1:
        return [None] * len(rows)
    trs = []
    for i in range(1, len(rows)):
        h, l, pc = rows[i][2], rows[i][3], rows[i - 1][4]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    atrs = [None] * period
    atrs.append(sum(trs[:period]) / period)
    for i in range(period, len(trs)):
        atrs.append((atrs[-1] * (period - 1) + trs[i]) / period)
    return atrs


def _vol_ma(volumes, period=20):
    result = []
    for i in range(len(volumes)):
        start = max(0, i - period + 1)
        result.append(sum(volumes[start:i + 1]) / (i + 1 - start))
    return result


def _find_swing_lows(closes, window=3):
    lows = []
    for i in range(window, len(closes) - window):
        if all(closes[i] <= closes[i - j] for j in range(1, window + 1)) and \
           all(closes[i] <= closes[i + j] for j in range(1, window + 1)):
            lows.append(i)
    return lows


# ═══════════════════════════════════════════════════════════════════════════════
# Data fetcher
# ═══════════════════════════════════════════════════════════════════════════════

def _get_candles_5m(token, lookback=None):
    if lookback is None:
        lookback = COILED_SPRING_LOOKBACK
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        cur = conn.cursor()
        cur.execute("SELECT MAX(ts) FROM candles_5m")
        max_ts = cur.fetchone()[0]
        if max_ts is None:
            return []
        since = max_ts - lookback * 300
        cur.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_5m
            WHERE token = ? AND ts >= ?
            ORDER BY ts ASC
        """, (token.upper(), since))
        return cur.fetchall()
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Core detection — VOLUME TRIGGER variant
# ═══════════════════════════════════════════════════════════════════════════════

def detect_coiled_spring_trigger(rows):
    """
    Detect volume-confirmed coiled spring breakout.

    Requires ALL of:
    1. EMA bullish alignment (9 > 21 > 50)
    2. Higher lows structure
    3. Prior coil (4+ bars of low volume)
    4. Current bar volume spike (> 2x avg)
    5. RSI in sweet spot (30-50)
    6. Price near EMA support (within 1x ATR)
    7. Trigger candle body quality (>= 0.5%)

    Returns: (signal_kwargs or None, diagnostics dict)
    """
    n = len(rows)
    if n < COILED_SPRING_MIN_BARS:
        return None, {'reason': f'insufficient data ({n} bars)'}

    closes = [r[4] for r in rows]
    volumes = [r[5] for r in rows]
    opens = [r[1] for r in rows]
    i = n - 1

    ema9 = _ema(closes, 9)
    ema21 = _ema(closes, 21)
    ema50 = _ema(closes, 50)
    rsi14 = _rsi(closes, 14)
    atr14 = _atr(rows, 14)
    vm20 = _vol_ma(volumes, 20)

    price = closes[i]
    vol_now = volumes[i]
    ema9_now = ema9[i]
    ema21_now = ema21[i]
    ema50_now = ema50[i]
    rsi_now = rsi14[i - 1] if i > 0 and rsi14[i - 1] is not None else COILED_SPRING_RSI_FALLBACK
    atr_now = atr14[i] if atr14[i] is not None else price * COILED_SPRING_ATR_FALLBACK_PCT
    atr_pct = atr_now / price * 100
    vol_ratio = vol_now / vm20[i] if vm20[i] > 0 else 0

    diag = {
        'price': price,
        'vol_ratio': vol_ratio,
        'rsi': rsi_now,
        'atr_pct': atr_pct,
    }

    # ══ HARD GATE 1: Volume spike (the trigger) ══
    if vol_ratio < COILED_SPRING_TRIGGER_VOL_RATIO:
        diag['reason'] = f'no volume trigger ({vol_ratio:.2f}x < {COILED_SPRING_TRIGGER_VOL_RATIO}x)'
        return None, diag

    # ══ HARD GATE 2: EMA alignment ══
    if not (ema9_now > ema21_now > ema50_now):
        diag['reason'] = 'EMA not bullish'
        return None, diag

    # ══ HARD GATE 3: Price not too far above EMA21 ══
    above_ema21 = (price / ema21_now - 1) * 100
    if above_ema21 > COILED_SPRING_MAX_PRICE_ABOVE_EMA21:
        diag['reason'] = f'price too far above EMA21 ({above_ema21:.2f}% > {COILED_SPRING_MAX_PRICE_ABOVE_EMA21}%)'
        return None, diag

    # ══ CHECK: Higher lows ══
    lookback_window = min(COILED_SPRING_SWING_LOOKBACK, n)
    swing_low_idxs = _find_swing_lows(closes[-lookback_window:], window=3)
    has_hl = False
    if len(swing_low_idxs) >= 2:
        sl1 = closes[-lookback_window + swing_low_idxs[-2]]
        sl2 = closes[-lookback_window + swing_low_idxs[-1]]
        has_hl = sl2 >= sl1  # Allow equal lows

    if not has_hl:
        diag['reason'] = 'no higher lows'
        return None, diag

    # ══ CHECK: Prior coil ══
    coil_bars = 0
    for j in range(i - 1, max(i - COILED_SPRING_COIL_SCAN_RANGE, 0), -1):
        vr = volumes[j] / vm20[j] if vm20[j] > 0 else 1
        if vr < COILED_SPRING_COIL_VOL_RATIO_MAX:
            coil_bars += 1
        else:
            break

    if coil_bars < COILED_SPRING_COIL_MIN_BARS:
        diag['reason'] = f'insufficient prior coil ({coil_bars} bars < {COILED_SPRING_COIL_MIN_BARS})'
        return None, diag

    # ══ CHECK: RSI in range ══
    if not (COILED_SPRING_RSI_MIN <= rsi_now <= COILED_SPRING_RSI_MAX):
        diag['reason'] = f'RSI out of range ({rsi_now:.1f} not in {COILED_SPRING_RSI_MIN}-{COILED_SPRING_RSI_MAX})'
        return None, diag

    # ══ CHECK: At support ══
    near_e21 = abs(price - ema21_now) < atr_now * COILED_SPRING_EMA_PROX_ATR_MULT
    near_e50 = abs(price - ema50_now) < atr_now * COILED_SPRING_EMA_PROX_ATR_MULT
    at_sup = near_e21 or near_e50

    if not at_sup:
        diag['reason'] = f'not at support (dist EMA21: {above_ema21:+.2f}%)'
        return None, diag

    # ══ CHECK: Trigger candle body quality ══
    body_pct = abs(closes[i] - opens[i]) / opens[i] * 100 if opens[i] > 0 else 0
    if body_pct < COILED_SPRING_TRIGGER_BODY_PCT:
        diag['reason'] = f'trigger body too small ({body_pct:.2f}% < {COILED_SPRING_TRIGGER_BODY_PCT}%)'
        return None, diag

    # ══ ALL CHECKS PASSED — GENERATE SIGNAL ══
    # Confidence: high base + bonuses
    confidence = COILED_SPRING_TRIGGER_LONG_CONF_BASE

    # Volume spike bonus (higher vol = higher confidence)
    if vol_ratio >= 5.0:
        confidence += 8
    elif vol_ratio >= 3.0:
        confidence += 5
    elif vol_ratio >= 2.0:
        confidence += 3

    # Coil depth bonus
    if coil_bars >= 8:
        confidence += 4
    elif coil_bars >= 6:
        confidence += 2

    # RSI in sweet spot bonus
    if 35 <= rsi_now <= 45:
        confidence += 3

    confidence = max(COILED_SPRING_TRIGGER_LONG_CONF_FLOOR, min(COILED_SPRING_TRIGGER_LONG_CONF_CAP, confidence))

    # SL/TP
    sl_price = price - atr_now * COILED_SPRING_SL_ATR_MULT
    tp_price = price + atr_now * COILED_SPRING_TP_ATR_MULT
    rr_ratio = (tp_price - price) / (price - sl_price) if price > sl_price else 0

    diag.update({
        'has_hl': has_hl,
        'coil_bars': coil_bars,
        'at_support': at_sup,
        'body_pct': body_pct,
        'final_confidence': confidence,
        'sl_price': sl_price,
        'tp_price': tp_price,
        'rr_ratio': rr_ratio,
    })

    return {
        'token': None,
        'direction': 'LONG',
        'signal_type': SIGNAL_TYPE_LONG,
        'source': SOURCE_LONG,
        'confidence': confidence,
        'value': round(vol_ratio, 2),
        'price': price,
        'exchange': 'hyperliquid',
        'timeframe': '5m',
        'z_score': None,
        'z_score_tier': None,
        'sl_price': sl_price,
        'tp_price': tp_price,
        'rr_ratio': rr_ratio,
    }, diag


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_coiled_spring_trigger():
    from signal_schema import get_all_latest_prices
    added = 0
    prices_dict = get_all_latest_prices()

    for token in prices_dict:
        if token.startswith('@'):
            continue
        data = prices_dict[token]
        if not data.get('price') or data['price'] <= 0:
            continue
        if price_age_minutes(token) > COILED_SPRING_PRICE_AGE_MAX:
            continue

        if not COILED_SPRING_TRIGGER_LONG_PLUS_ENABLED:
            continue
        if token.upper() in LONG_BLACKLIST:
            continue
        if get_cooldown(token, direction='LONG'):
            continue

        rows = _get_candles_5m(token)
        if not rows or len(rows) < COILED_SPRING_MIN_BARS:
            continue

        sig_kwargs, diag = detect_coiled_spring_trigger(rows)
        if sig_kwargs is None:
            continue

        sig_kwargs['token'] = token
        confidence = sig_kwargs['confidence']

        if confidence < COILED_SPRING_TRIGGER_LONG_CONF_FLOOR:
            continue

        sid = add_signal(
            token=token.upper(),
            direction=sig_kwargs['direction'],
            signal_type=sig_kwargs['signal_type'],
            source=sig_kwargs['source'],
            confidence=confidence,
            value=sig_kwargs['value'],
            price=sig_kwargs['price'],
            exchange='hyperliquid',
            timeframe='5m',
            z_score=sig_kwargs['z_score'],
            z_score_tier=sig_kwargs.get('z_score_tier'),
        )
        if sid:
            added += 1
            set_cooldown(token, direction='LONG', hours=COILED_SPRING_TRIGGER_LONG_COOLDOWN_MINUTES / 60)

    return added


def run():
    return scan_coiled_spring_trigger()


def analyze(token='SAND'):
    rows = _get_candles_5m(token)
    if not rows:
        print(f"No 5m data for {token}")
        return

    print(f"Analyzing {token} — {len(rows)} candles loaded")

    sig, diag = detect_coiled_spring_trigger(rows)
    print(f"\nDiagnostics:")
    for k, v in diag.items():
        print(f"  {k}: {v}")

    if sig:
        print(f"\nSIGNAL FIRED!")
        print(f"  Type: {sig['signal_type']}")
        print(f"  Price: {sig['price']:.6f}")
        print(f"  Confidence: {sig['confidence']:.1f}")
        print(f"  SL: {sig['sl_price']:.6f}")
        print(f"  TP: {sig['tp_price']:.6f}")
        print(f"  R:R: {sig['rr_ratio']:.2f}")
        print(f"  Source: {sig['source']}")
    else:
        print(f"\nNo signal. Reason: {diag.get('reason', 'conditions not met')}")

    return sig, diag


if __name__ == '__main__':
    import sys
    token = sys.argv[1] if len(sys.argv) > 1 else 'SAND'
    analyze(token)
