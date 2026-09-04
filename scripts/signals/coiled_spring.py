#!/usr/bin/env python3
"""
coiled_spring.py — Volume Contraction Pullback in Bullish Trend (LONG only).

Catches the "coiled spring" pattern: after an initial impulse establishes a
bullish trend (HH/HL structure, EMA alignment), price pulls back with
declining volume and compressed volatility into a support zone. When volume
returns, the next leg fires.

Phases:
  1. IMPULSE     — Initial push establishes bullish structure (higher lows)
  2. PAUSE       — First consolidation, volume contracts moderately
  3. SECOND_PUSH — Continuation confirms trend (new higher high)
  4. COILED      — Price leaks lower on DEAD volume, ATR compresses, RSI cools
  5. TRIGGER     — Volume spike breaks compression, re-enters trend

Data: candles_5m from candles.db (local, zero API calls)
Signal type: coiled_spring_long
Source tags:  coil-spring+@coil{N} (coil mode), coil-spring+@vol{X} (trigger mode)
"""

import sys
import os
import sqlite3
import time
from typing import Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    COILED_SPRING_ENABLED,
    COILED_SPRING_PLUS_ENABLED,
    COILED_SPRING_MINUS_ENABLED,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
    COILED_SPRING_LOOKBACK,
    COILED_SPRING_MIN_IMPULSE_PCT,
    COILED_SPRING_COIL_MIN_BARS,
    COILED_SPRING_COIL_VOL_RATIO_MAX,
    COILED_SPRING_COIL_ATR_PCT_MAX,
    COILED_SPRING_RSI_MIN,
    COILED_SPRING_RSI_MAX,
    COILED_SPRING_RSI_TRIGGER_MIN,
    COILED_SPRING_RSI_BONUS_MIN,
    COILED_SPRING_RSI_BONUS_MAX,
    COILED_SPRING_MIN_CONDITIONS,
    COILED_SPRING_MIN_COIL_FALLBACK,
    COILED_SPRING_TRIGGER_VOL_RATIO,
    COILED_SPRING_TRIGGER_BODY_PCT,
    COILED_SPRING_SL_ATR_MULT,
    COILED_SPRING_TP_ATR_MULT,
    COILED_SPRING_CONF_BASE,
    COILED_SPRING_CONF_VOL_SPIKE_MAX,
    COILED_SPRING_CONF_RSI_BONUS_MAX,
    COILED_SPRING_CONF_STRUCT_MAX,
    COILED_SPRING_CONF_DEEP_COIL_MAX,
    COILED_SPRING_CONF_EMA_ALIGN_BONUS,
    COILED_SPRING_CONF_FLOOR,
    COILED_SPRING_CONF_CAP,
    COILED_SPRING_COOLDOWN_HOURS,
    COILED_SPRING_MIN_BARS,
    COILED_SPRING_SWING_LOOKBACK,
    COILED_SPRING_COIL_SCAN_RANGE,
    COILED_SPRING_ATR_TREND_THRESH,
    COILED_SPRING_EMA_PROX_ATR_MULT,
    COILED_SPRING_VOL_MODE_THRESH,
    COILED_SPRING_VOL_BONUS_MULT,
    COILED_SPRING_DEEP_COIL_BARS,
    COILED_SPRING_DEEP_COIL_BONUS,
    COILED_SPRING_STRUCT_BASE,
    COILED_SPRING_STRUCT_PER_LOW,
    COILED_SPRING_PRICE_AGE_MAX,
    COILED_SPRING_RSI_FALLBACK,
    COILED_SPRING_ATR_FALLBACK_PCT,
)

SIGNAL_TYPE_LONG  = 'coiled_spring_long'
SIGNAL_TYPE_SHORT = 'coiled_spring_short'
SOURCE_LONG       = 'coil-spring+'
SOURCE_SHORT      = 'coil-spring-'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')


# ═══════════════════════════════════════════════════════════════════════════════
# Technical indicator helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _ema(data, period):
    """Exponential moving average."""
    k = 2 / (period + 1)
    result = [data[0]]
    for i in range(1, len(data)):
        result.append(data[i] * k + result[-1] * (1 - k))
    return result


def _rsi(data, period=14):
    """Relative Strength Index."""
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
    result.append(None)  # pad for alignment
    return result


def _atr(rows, period=14):
    """Average True Range."""
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
    """Simple moving average of volume."""
    result = []
    for i in range(len(volumes)):
        start = max(0, i - period + 1)
        result.append(sum(volumes[start:i + 1]) / (i + 1 - start))
    return result


def _find_swing_lows(closes, window=3):
    """Find swing lows (local minima) in close prices."""
    lows = []
    for i in range(window, len(closes) - window):
        if all(closes[i] <= closes[i - j] for j in range(1, window + 1)) and \
           all(closes[i] <= closes[i + j] for j in range(1, window + 1)):
            lows.append(i)
    return lows


# ═══════════════════════════════════════════════════════════════════════════════
# Data fetcher (with proper connection cleanup)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_candles_5m(token, lookback=None):
    """Fetch 5m candles for token from local candles.db. Returns oldest-first."""
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
        since = max_ts - lookback * 300  # 5m bars
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
# Core detection
# ═══════════════════════════════════════════════════════════════════════════════

def detect_coiled_spring(rows):
    """
    Analyze 5m candle data for the coiled spring pattern.

    Returns: (signal_kwargs or None, diagnostics dict)
    Diagnostics always returned for logging.
    """
    n = len(rows)
    if n < COILED_SPRING_MIN_BARS:
        return None, {'reason': f'insufficient data ({n} bars, need {COILED_SPRING_MIN_BARS})'}

    closes  = [r[4] for r in rows]
    volumes = [r[5] for r in rows]
    highs   = [r[2] for r in rows]
    lows    = [r[3] for r in rows]
    opens   = [r[1] for r in rows]

    # ── Indicators ──────────────────────────────────────────────────────────
    ema9  = _ema(closes, 9)
    ema21 = _ema(closes, 21)
    ema50 = _ema(closes, 50)
    rsi14 = _rsi(closes, 14)
    atr14 = _atr(rows, 14)
    vm20  = _vol_ma(volumes, 20)

    # Current values — use is not None to avoid RSI/ATR=0.0 being treated as missing
    i = n - 1
    price      = closes[i]
    vol_now    = volumes[i]
    ema9_now   = ema9[i]
    ema21_now  = ema21[i]
    ema50_now  = ema50[i]
    rsi_now    = rsi14[i] if rsi14[i] is not None else COILED_SPRING_RSI_FALLBACK
    atr_now    = atr14[i] if atr14[i] is not None else price * COILED_SPRING_ATR_FALLBACK_PCT
    atr_pct    = atr_now / price * 100
    vol_ratio  = vol_now / vm20[i] if vm20[i] > 0 else 1

    diag = {
        'price': price,
        'ema9': ema9_now,
        'ema21': ema21_now,
        'ema50': ema50_now,
        'rsi': rsi_now,
        'atr_pct': atr_pct,
        'vol_ratio': vol_ratio,
    }

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 1: EMA alignment (bullish trend context)
    # ════════════════════════════════════════════════════════════════════════
    if not (ema9_now > ema21_now > ema50_now):
        if not (ema9_now > ema21_now):
            diag['reason'] = 'EMA not bullish'
            return None, diag

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 2: Higher lows structure (at least 2 ascending swing lows)
    # ════════════════════════════════════════════════════════════════════════
    lookback_window = min(COILED_SPRING_SWING_LOOKBACK, n)
    swing_low_idxs = _find_swing_lows(closes[-lookback_window:], window=3)

    if len(swing_low_idxs) < 2:
        diag['reason'] = f'insufficient swing lows ({len(swing_low_idxs)})'
        return None, diag

    sl1 = closes[-lookback_window + swing_low_idxs[-2]]
    sl2 = closes[-lookback_window + swing_low_idxs[-1]]
    if sl2 <= sl1:
        diag['reason'] = f'not higher lows: {sl1:.6f} -> {sl2:.6f}'
        return None, diag

    hl_gap_pct = (sl2 / sl1 - 1) * 100
    diag['higher_lows'] = f'{sl1:.6f} -> {sl2:.6f} (+{hl_gap_pct:.2f}%)'

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 3: Volume contraction (the coiled spring)
    # ════════════════════════════════════════════════════════════════════════
    coil_bars = 0
    for j in range(i, max(i - COILED_SPRING_COIL_SCAN_RANGE, 0), -1):
        vr = volumes[j] / vm20[j] if vm20[j] > 0 else 1
        if vr < COILED_SPRING_COIL_VOL_RATIO_MAX:
            coil_bars += 1
        else:
            break

    diag['coil_bars'] = coil_bars

    # Also check: current bar might be the trigger (volume returns after coil)
    if coil_bars < COILED_SPRING_COIL_MIN_BARS:
        prev_coil = 0
        for j in range(i - 1, max(i - COILED_SPRING_COIL_SCAN_RANGE, 0), -1):
            vr = volumes[j] / vm20[j] if vm20[j] > 0 else 1
            if vr < COILED_SPRING_COIL_VOL_RATIO_MAX:
                prev_coil += 1
            else:
                break
        diag['prev_coil_bars'] = prev_coil
        if prev_coil < COILED_SPRING_COIL_MIN_BARS:
            diag['reason'] = f'insufficient coil (cur={coil_bars}, prev={prev_coil})'
            return None, diag
        coil_bars = prev_coil

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 4: ATR compression
    # ════════════════════════════════════════════════════════════════════════
    atr_compressed = atr_pct < COILED_SPRING_COIL_ATR_PCT_MAX
    if not atr_compressed and len(atr14) >= 10:
        recent_atrs = [a for a in atr14[-10:] if a is not None]
        if len(recent_atrs) >= 5:
            atr_trend = (sum(recent_atrs[-3:]) / 3) / (sum(recent_atrs[:3]) / 3)
            atr_compressed = atr_trend < COILED_SPRING_ATR_TREND_THRESH
    diag['atr_compressed'] = atr_compressed

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 5: RSI in the sweet spot
    # ════════════════════════════════════════════════════════════════════════
    rsi_sweet = COILED_SPRING_RSI_MIN <= rsi_now <= COILED_SPRING_RSI_MAX
    if not rsi_sweet and i >= 3:
        rsi_recent = [r for r in rsi14[i - 3:i] if r is not None]
        rsi_sweet = any(COILED_SPRING_RSI_MIN <= r <= COILED_SPRING_RSI_MAX for r in rsi_recent)
    diag['rsi_sweet'] = rsi_sweet

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 6: Price near support (EMA21 or EMA50 zone)
    # ════════════════════════════════════════════════════════════════════════
    near_ema21 = abs(price - ema21_now) < atr_now * COILED_SPRING_EMA_PROX_ATR_MULT
    near_ema50 = abs(price - ema50_now) < atr_now * COILED_SPRING_EMA_PROX_ATR_MULT
    at_support = near_ema21 or near_ema50
    diag['at_support'] = at_support
    diag['dist_ema21_pct'] = (price / ema21_now - 1) * 100
    diag['dist_ema50_pct'] = (price / ema50_now - 1) * 100

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 7: Impulse validation (minimum move from recent swing low)
    # ════════════════════════════════════════════════════════════════════════
    if len(swing_low_idxs) >= 1:
        recent_low_price = closes[-lookback_window + swing_low_idxs[-1]]
        impulse_pct = (price / recent_low_price - 1) * 100
        diag['impulse_pct'] = impulse_pct
    else:
        impulse_pct = 0
        diag['impulse_pct'] = 0

    # GATE: Impulse must be meaningful — otherwise no trend was established
    if impulse_pct < COILED_SPRING_MIN_IMPULSE_PCT:
        diag['reason'] = f'impulse too small ({impulse_pct:.2f}% < {COILED_SPRING_MIN_IMPULSE_PCT}%)'
        return None, diag

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 8: Trigger candle body quality (for trigger mode)
    # ════════════════════════════════════════════════════════════════════════
    trigger_body_pct = abs(closes[i] - opens[i]) / opens[i] * 100 if opens[i] > 0 else 0
    diag['trigger_body_pct'] = trigger_body_pct

    # ════════════════════════════════════════════════════════════════════════
    # GATE: Determine mode and validate
    # ════════════════════════════════════════════════════════════════════════
    conditions = [
        ('higher_lows', True),
        ('coil_volume', coil_bars >= COILED_SPRING_COIL_MIN_BARS),
        ('atr_compressed', atr_compressed),
        ('rsi_sweet', rsi_sweet),
        ('at_support', at_support),
        ('vol_trigger', vol_ratio > COILED_SPRING_TRIGGER_VOL_RATIO),
    ]
    passed = sum(1 for _, ok in conditions if ok)
    diag['conditions_passed'] = f'{passed}/{len(conditions)}'
    diag['conditions'] = {name: ok for name, ok in conditions}

    # ── MODE 1: TRIGGER MODE (volume spike after coil) — highest quality ────
    # Requires: volume spike + prior coil + RSI turning up + body quality
    is_trigger_mode = (
        vol_ratio > COILED_SPRING_TRIGGER_VOL_RATIO and
        coil_bars >= 2 and
        rsi_now > COILED_SPRING_RSI_TRIGGER_MIN and
        ema9_now > ema21_now and
        trigger_body_pct >= COILED_SPRING_TRIGGER_BODY_PCT
    )

    # ── MODE 2: COIL MODE (buy the dip during compression) — good R:R ──────
    # Requires: sustained coil + ATR compressed + RSI in zone + at support
    is_coil_mode = (
        coil_bars >= COILED_SPRING_COIL_MIN_BARS and
        atr_compressed and
        rsi_sweet and
        at_support and
        vol_ratio < COILED_SPRING_VOL_MODE_THRESH
    )

    if not (is_trigger_mode or is_coil_mode):
        if not (passed >= COILED_SPRING_MIN_CONDITIONS and (coil_bars >= COILED_SPRING_MIN_COIL_FALLBACK or vol_ratio > COILED_SPRING_TRIGGER_VOL_RATIO)):
            diag['reason'] = f'not in trigger or coil mode (trigger={is_trigger_mode} coil={is_coil_mode} pass={passed})'
            return None, diag

    # Mandatory: higher_lows
    if not any(n == 'higher_lows' for n, ok in conditions if ok):
        diag['reason'] = 'mandatory: higher_lows failed'
        return None, diag

    # ════════════════════════════════════════════════════════════════════════
    # SIGNAL GENERATION
    # ════════════════════════════════════════════════════════════════════════
    confidence = COILED_SPRING_CONF_BASE

    # Volume spike bonus — strong confirmation of buyer interest
    if vol_ratio > COILED_SPRING_TRIGGER_VOL_RATIO:
        vol_bonus = min(COILED_SPRING_CONF_VOL_SPIKE_MAX, int((vol_ratio - 1) * COILED_SPRING_VOL_BONUS_MULT))
        confidence += vol_bonus
        diag['conf_vol_bonus'] = vol_bonus

    # Deep coil bonus — sustained compression = spring loaded
    if coil_bars >= COILED_SPRING_DEEP_COIL_BARS:
        deep_bonus = min(COILED_SPRING_CONF_DEEP_COIL_MAX, COILED_SPRING_DEEP_COIL_BONUS)
        confidence += deep_bonus
        diag['conf_deep_coil'] = deep_bonus

    # RSI bonus — ideal zone means room to run
    if COILED_SPRING_RSI_BONUS_MIN <= rsi_now <= COILED_SPRING_RSI_BONUS_MAX:
        rsi_bonus = COILED_SPRING_CONF_RSI_BONUS_MAX
        confidence += rsi_bonus
        diag['conf_rsi_bonus'] = rsi_bonus

    # Structure bonus — clean HH/HL = established trend
    if len(swing_low_idxs) >= 3:
        sl_all = [closes[-lookback_window + idx] for idx in swing_low_idxs[-3:]]
        if all(sl_all[k + 1] > sl_all[k] for k in range(len(sl_all) - 1)):
            struct_bonus = min(COILED_SPRING_CONF_STRUCT_MAX,
                               COILED_SPRING_STRUCT_BASE + len(swing_low_idxs) * COILED_SPRING_STRUCT_PER_LOW)
            confidence += struct_bonus
            diag['conf_struct_bonus'] = struct_bonus

    # EMA alignment bonus — full bullish stack (9>21>50) is strongest confirmation
    if ema9_now > ema21_now > ema50_now:
        ema_bonus = COILED_SPRING_CONF_EMA_ALIGN_BONUS
        confidence += ema_bonus
        diag['conf_ema_bonus'] = ema_bonus

    confidence = max(COILED_SPRING_CONF_FLOOR, min(COILED_SPRING_CONF_CAP, confidence))
    diag['final_confidence'] = confidence

    # Stop loss and take profit
    sl_price = price - atr_now * COILED_SPRING_SL_ATR_MULT
    tp_price = price + atr_now * COILED_SPRING_TP_ATR_MULT
    rr_ratio = (tp_price - price) / (price - sl_price) if price > sl_price else 0

    diag['sl_price'] = sl_price
    diag['tp_price'] = tp_price
    diag['rr_ratio'] = rr_ratio

    # Source tag — use clean directional format for standalone bypass matching
    # Metadata (coil/vol) is logged in diagnostics, not in source field
    source = SOURCE_LONG

    return {
        'token': None,  # filled by scanner
        'direction': 'LONG',
        'signal_type': SIGNAL_TYPE_LONG,
        'source': source,
        'confidence': confidence,
        'value': round(impulse_pct, 2),
        'price': price,
        'exchange': 'hyperliquid',
        'timeframe': '5m',
        'z_score': None,
        'z_score_tier': None,
        'sl_price': sl_price,
        'tp_price': tp_price,
        'rr_ratio': rr_ratio,
        'coil_bars': coil_bars,
        'mode': mode,
    }, diag


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_coiled_spring():
    """Scan all tokens for coiled spring patterns on 5m. Returns count of signals emitted."""
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

        # Layer 1: per-direction kill-switch
        if not COILED_SPRING_PLUS_ENABLED:
            continue

        # Layer 1: blacklists
        if token.upper() in LONG_BLACKLIST:
            continue

        # Layer 1: cooldown
        if get_cooldown(token, direction='LONG'):
            continue

        rows = _get_candles_5m(token)
        if not rows or len(rows) < COILED_SPRING_MIN_BARS:
            continue

        sig_kwargs, diag = detect_coiled_spring(rows)
        if sig_kwargs is None:
            continue

        sig_kwargs['token'] = token
        confidence = sig_kwargs['confidence']

        if confidence < COILED_SPRING_CONF_FLOOR:
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
            set_cooldown(token, direction='LONG', hours=COILED_SPRING_COOLDOWN_HOURS)

    return added


def run():
    """Entry point for signals_runner. Reads from DB directly (no prices_dict needed)."""
    return scan_coiled_spring()


# ═══════════════════════════════════════════════════════════════════════════════
# CLI analysis tool
# ═══════════════════════════════════════════════════════════════════════════════

def analyze(token='ENA'):
    """Run detection on a token and print detailed diagnostics."""
    rows = _get_candles_5m(token)
    if not rows:
        print(f"No 5m data for {token}")
        return

    print(f"Analyzing {token} — {len(rows)} candles loaded")

    sig, diag = detect_coiled_spring(rows)
    print(f"\nDiagnostics:")
    for k, v in diag.items():
        print(f"  {k}: {v}")

    if sig:
        print(f"\nSIGNAL FIRED!")
        print(f"  Type: {sig['signal_type']}")
        print(f"  Mode: {sig['mode']}")
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
    token = sys.argv[1] if len(sys.argv) > 1 else 'ENA'
    analyze(token)
