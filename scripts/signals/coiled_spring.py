#!/usr/bin/env python3
"""
coiled_spring.py — Volume Contraction Pullback in Bullish Trend.

Catches the "coiled spring" pattern: after an initial impulse move establishes
a bullish trend (HH/HL structure, EMA alignment), price pulls back with
declining volume and compressed volatility into a support zone. When volume
returns, the next leg up fires.

The pattern has 5 phases:
  1. IMPULSE   — Initial push establishes bullish structure (higher lows)
  2. PAUSE     — First consolidation, volume contracts moderately
  3. SECOND_PUSH — Continuation confirms trend (new higher high)
  4. COILED    — Price leaks lower on DEAD volume, ATR compresses, RSI cools
  5. TRIGGER   — Volume spike breaks compression, re-enters trend

Entry: During phase 4 (the coiled spring) or at phase 5 trigger.
Best R:R because entry is near support with tight stop below recent swing low.

Signal type: coiled_spring_long
Source tags:  coil-spring@volX.X, coil-spring@rsiXX

Data: candles_5m from candles.db (local, zero API calls)
"""

import sys
import os
import sqlite3
import time
from typing import Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, price_age_minutes
from paths import RUNTIME_DB, CANDLES_DB

# ── Constants ──────────────────────────────────────────────────────────────────
LOOKBACK       = 500    # 5m candles to load
SIGNAL_TYPE    = 'coiled_spring_long'
SOURCE_TAG     = 'coil-spring'

# Phase 2 — Trend establishment requirements
MIN_IMPULSE_PCT     = 1.5    # min % move from swing low to confirm impulse
MIN_HIGHER_LOW_GAP  = 0.3    # min % gap between successive swing lows

# Phase 4 — The coiled spring conditions
COIL_MIN_BARS       = 4      # min consecutive bars with vol < threshold
COIL_VOL_RATIO_MAX  = 0.65   # volume must be below this fraction of 20-bar avg
COIL_ATR_PCT_MAX    = 0.55   # ATR% must be below this (volatility compressed)
COIL_RSI_MIN        = 30     # RSI must be in this range (not too hot, not dead)
COIL_RSI_MAX        = 50

# Phase 5 — Trigger confirmation
TRIGGER_VOL_RATIO   = 2.0    # breakout bar must have this much volume vs avg
TRIGGER_BODY_PCT    = 0.5    # min body % of trigger candle

# Risk management
SL_ATR_MULT         = 1.5    # stop loss = 1.5x ATR below entry
TP_ATR_MULT         = 4.0    # take profit = 4x ATR above entry

# Confidence
CONF_BASE           = 55
CONF_VOL_SPIKE_MAX  = 25     # bonus for volume spike magnitude
CONF_RSI_BONUS_MAX  = 10     # bonus for ideal RSI zone
CONF_STRUCT_MAX     = 10     # bonus for clean HH/HL structure

COOLDOWN_BARS       = 12     # 1 hour cooldown between fires (12 x 5m)


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


def _find_swing_lows(closes, window=5):
    """Find swing lows (local minima) in close prices."""
    lows = []
    for i in range(window, len(closes) - window):
        if all(closes[i] <= closes[i - j] for j in range(1, window + 1)) and \
           all(closes[i] <= closes[i + j] for j in range(1, window + 1)):
            lows.append(i)
    return lows


def _find_swing_highs(closes, window=5):
    """Find swing highs (local maxima) in close prices."""
    highs = []
    for i in range(window, len(closes) - window):
        if all(closes[i] >= closes[i - j] for j in range(1, window + 1)) and \
           all(closes[i] >= closes[i + j] for j in range(1, window + 1)):
            highs.append(i)
    return highs


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
    if n < 60:
        return None, {'reason': f'insufficient data ({n} bars)'}

    closes  = [r[4] for r in rows]
    volumes = [r[5] for r in rows]
    highs   = [r[2] for r in rows]
    lows    = [r[3] for r in rows]

    # ── Indicators ──────────────────────────────────────────────────────────
    ema9  = _ema(closes, 9)
    ema21 = _ema(closes, 21)
    ema50 = _ema(closes, 50)
    rsi14 = _rsi(closes, 14)
    atr14 = _atr(rows, 14)
    vm20  = _vol_ma(volumes, 20)

    # Current values
    i = n - 1
    price      = closes[i]
    vol_now    = volumes[i]
    ema9_now   = ema9[i]
    ema21_now  = ema21[i]
    ema50_now  = ema50[i]
    rsi_now    = rsi14[i] if rsi14[i] else 50
    atr_now    = atr14[i] if atr14[i] else price * 0.005
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
        # Relaxed: allow price temporarily below EMA9 but EMA9 must still > EMA21
        if not (ema9_now > ema21_now):
            diag['reason'] = 'EMA not bullish'
            return None, diag

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 2: Higher lows structure (at least 2 higher lows in recent 100 bars)
    # ════════════════════════════════════════════════════════════════════════
    lookback_window = min(100, n)
    recent_lows = lows[-lookback_window:]
    swing_low_idxs = _find_swing_lows(closes[-lookback_window:], window=3)

    if len(swing_low_idxs) < 2:
        diag['reason'] = f'insufficient swing lows ({len(swing_low_idxs)})'
        return None, diag

    # Check that last 2 swing lows are ascending
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
    for j in range(i, max(i - 8, 0), -1):
        vr = volumes[j] / vm20[j] if vm20[j] > 0 else 1
        if vr < COIL_VOL_RATIO_MAX:
            coil_bars += 1
        else:
            break

    diag['coil_bars'] = coil_bars

    if coil_bars < COIL_MIN_BARS:
        # Also check: current bar itself might be the trigger (volume returns)
        # So check if PREVIOUS bars were coiled
        prev_coil = 0
        for j in range(i - 1, max(i - 8, 0), -1):
            vr = volumes[j] / vm20[j] if vm20[j] > 0 else 1
            if vr < COIL_VOL_RATIO_MAX:
                prev_coil += 1
            else:
                break
        diag['prev_coil_bars'] = prev_coil
        if prev_coil < COIL_MIN_BARS:
            diag['reason'] = f'insufficient coil (cur={coil_bars}, prev={prev_coil})'
            return None, diag
        # Current bar IS the trigger — use prev coil count
        coil_bars = prev_coil

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 4: ATR compression
    # ════════════════════════════════════════════════════════════════════════
    # Check that ATR% is compressed (below threshold or declining)
    atr_compressed = atr_pct < COIL_ATR_PCT_MAX

    # Also check if ATR is declining (even if absolute is still above threshold)
    if not atr_compressed and len(atr14) >= 10:
        recent_atrs = [a for a in atr14[-10:] if a is not None]
        if len(recent_atrs) >= 5:
            atr_trend = (sum(recent_atrs[-3:]) / 3) / (sum(recent_atrs[:3]) / 3)
            atr_compressed = atr_trend < 0.85  # ATR declining by 15%+

    diag['atr_compressed'] = atr_compressed

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 5: RSI in the sweet spot
    # ════════════════════════════════════════════════════════════════════════
    rsi_sweet = COIL_RSI_MIN <= rsi_now <= COIL_RSI_MAX
    # Also accept if RSI recently dipped into the zone
    if not rsi_sweet and i >= 3:
        rsi_recent = [r for r in rsi14[i - 3:i] if r is not None]
        rsi_sweet = any(COIL_RSI_MIN <= r <= COIL_RSI_MAX for r in rsi_recent)
    diag['rsi_sweet'] = rsi_sweet

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 6: Price near support (EMA21 or EMA50 zone)
    # ════════════════════════════════════════════════════════════════════════
    # Price should be within 1 ATR of EMA21 or EMA50 (pullback to support)
    near_ema21 = abs(price - ema21_now) < atr_now * 1.5
    near_ema50 = abs(price - ema50_now) < atr_now * 1.5
    at_support = near_ema21 or near_ema50
    diag['at_support'] = at_support
    diag['dist_ema21_pct'] = (price / ema21_now - 1) * 100
    diag['dist_ema50_pct'] = (price / ema50_now - 1) * 100

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 7: Impulse validation (recent move established the trend)
    # ════════════════════════════════════════════════════════════════════════
    # Find the most recent significant low and compute the impulse from it
    if len(swing_low_idxs) >= 1:
        recent_low_price = closes[-lookback_window + swing_low_idxs[-1]]
        impulse_pct = (price / recent_low_price - 1) * 100
        diag['impulse_pct'] = impulse_pct
        # We want the impulse to have happened (move FROM the low)
        # but now price is pulling back within the impulse
    else:
        impulse_pct = 0

    # ════════════════════════════════════════════════════════════════════════
    # GATE: Must pass at least 4 of 6 conditions (excluding EMA which is hard gate)
    # ════════════════════════════════════════════════════════════════════════
    conditions = [
        ('higher_lows', True),     # Always checked above
        ('coil_volume', coil_bars >= COIL_MIN_BARS),
        ('atr_compressed', atr_compressed),
        ('rsi_sweet', rsi_sweet),
        ('at_support', at_support),
        ('vol_trigger', vol_ratio > TRIGGER_VOL_RATIO),
    ]
    passed = sum(1 for _, ok in conditions if ok)
    diag['conditions_passed'] = f'{passed}/{len(conditions)}'
    diag['conditions'] = {name: ok for name, ok in conditions}

    # ── MODE 1: TRIGGER MODE (volume spike after coil) — highest quality ────
    # This catches the EXACT entry: volume returns after compression
    is_trigger_mode = (
        vol_ratio > TRIGGER_VOL_RATIO and
        coil_bars >= 2 and  # at least 2 prior coil bars
        rsi_now > 45 and    # RSI turning up
        ema9_now > ema21_now
    )

    # ── MODE 2: COIL MODE (buy the dip during compression) — good R:R ──────
    # Catching the setup before it triggers
    is_coil_mode = (
        coil_bars >= COIL_MIN_BARS and
        atr_compressed and
        rsi_sweet and
        at_support and
        vol_ratio < 1.0  # volume must still be quiet
    )

    if not (is_trigger_mode or is_coil_mode):
        # Must pass at least 4 conditions AND be in one of the two modes
        if not (passed >= 4 and (coil_bars >= 3 or vol_ratio > TRIGGER_VOL_RATIO)):
            diag['reason'] = f'not in trigger or coil mode (trigger={is_trigger_mode} coil={is_coil_mode} pass={passed})'
            return None, diag

    # Mandatory: higher_lows
    if not any(n == 'higher_lows' for n, ok in conditions if ok):
        diag['reason'] = 'mandatory: higher_lows failed'
        return None, diag

    # ════════════════════════════════════════════════════════════════════════
    # SIGNAL GENERATION
    # ════════════════════════════════════════════════════════════════════════

    # Confidence scoring
    confidence = CONF_BASE

    # Volume spike bonus
    if vol_ratio > TRIGGER_VOL_RATIO:
        vol_bonus = min(CONF_VOL_SPIKE_MAX, (vol_ratio - 1) * 5)
        confidence += vol_bonus
        diag['conf_vol_bonus'] = vol_bonus
    elif coil_bars >= 5:
        # Deep coil = high quality even without trigger
        confidence += 10
        diag['conf_deep_coil'] = 10

    # RSI bonus
    if 35 <= rsi_now <= 45:
        rsi_bonus = CONF_RSI_BONUS_MAX
        confidence += rsi_bonus
        diag['conf_rsi_bonus'] = rsi_bonus

    # Structure bonus (clean HH/HL)
    if len(swing_low_idxs) >= 3:
        sl_all = [closes[-lookback_window + idx] for idx in swing_low_idxs[-3:]]
        if all(sl_all[k + 1] > sl_all[k] for k in range(len(sl_all) - 1)):
            struct_bonus = min(CONF_STRUCT_MAX, 5 + len(swing_low_idxs) * 2)
            confidence += struct_bonus
            diag['conf_struct_bonus'] = struct_bonus

    confidence = min(95, confidence)
    diag['final_confidence'] = confidence

    # Stop loss and take profit
    sl_price = price - atr_now * SL_ATR_MULT
    tp_price = price + atr_now * TP_ATR_MULT
    rr_ratio = (tp_price - price) / (price - sl_price) if price > sl_price else 0

    diag['sl_price'] = sl_price
    diag['tp_price'] = tp_price
    diag['rr_ratio'] = rr_ratio

    # Source tag
    source = f"{SOURCE_TAG}@vol{vol_ratio:.1f}"
    if vol_ratio <= 1:
        source = f"{SOURCE_TAG}@coil{coil_bars}"

    return {
        'token': None,  # filled by scanner
        'direction': 'LONG',
        'signal_type': SIGNAL_TYPE,
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
    }, diag


# ═══════════════════════════════════════════════════════════════════════════════
# Data fetcher
# ═══════════════════════════════════════════════════════════════════════════════

def _get_candles_5m(token, lookback=LOOKBACK):
    """Fetch 5m candles for token from local candles.db."""
    conn = sqlite3.connect(CANDLES_DB, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()
    cur.execute("SELECT MAX(ts) FROM candles_5m")
    max_ts = cur.fetchone()[0]
    if max_ts is None:
        conn.close()
        return []
    since = max_ts - lookback * 300

    cur.execute("""
        SELECT ts, open, high, low, close, volume
        FROM candles_5m
        WHERE token = ? AND ts >= ?
        ORDER BY ts ASC
    """, (token.upper(), since))
    rows = cur.fetchall()
    conn.close()
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def _get_last_fire(token):
    """Read last fire timestamp from runtime DB."""
    conn = sqlite3.connect(RUNTIME_DB, timeout=5)
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS coil_spring_cooldown (
                token TEXT PRIMARY KEY,
                last_fire_ts INTEGER,
                fires_count INTEGER DEFAULT 0
            )
        """)
        cur.execute("SELECT last_fire_ts FROM coil_spring_cooldown WHERE token = ?", (token.upper(),))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else 0
    except Exception:
        conn.close()
        return 0


def _record_fire(token, ts):
    """Record a fire event for cooldown tracking."""
    conn = sqlite3.connect(RUNTIME_DB, timeout=5)
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS coil_spring_cooldown (
                token TEXT PRIMARY KEY,
                last_fire_ts INTEGER,
                fires_count INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            INSERT OR REPLACE INTO coil_spring_cooldown (token, last_fire_ts, fires_count)
            VALUES (?, ?, COALESCE((SELECT fires_count FROM coil_spring_cooldown WHERE token = ?), 0) + 1)
        """, (token.upper(), ts, token.upper()))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def scan_coiled_spring(prices_dict=None):
    """
    Scan all tokens for coiled spring patterns on 5m.
    Returns: (count_of_signals_written, set_of_tokens_that_fired)
    """
    from hermes_constants import COILED_SPRING_ENABLED
    if not COILED_SPRING_ENABLED:
        return 0, set()

    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()

    added = 0
    fired = set()

    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue
        if not data.get('price') or data['price'] <= 0:
            continue
        if price_age_minutes(token) > 10:
            continue

        # Per-token cooldown check
        now_ts = int(time.time())
        last_fire = _get_last_fire(token)
        if now_ts - last_fire < COOLDOWN_BARS * 300:
            continue  # Still in cooldown

        rows = _get_candles_5m(token)
        if not rows or len(rows) < 60:
            continue

        sig_kwargs, diag = detect_coiled_spring(rows)
        if sig_kwargs is None:
            continue

        sig_kwargs['token'] = token
        confidence = sig_kwargs['confidence']

        if confidence < 55:
            continue

        # Record fire for cooldown
        _record_fire(token, rows[-1][0])

        sid = add_signal(
            token=token,
            direction=sig_kwargs['direction'],
            signal_type=sig_kwargs['signal_type'],
            source=sig_kwargs['source'],
            confidence=confidence,
            value=sig_kwargs['value'],
            price=sig_kwargs['price'],
            exchange=sig_kwargs['exchange'],
            timeframe=sig_kwargs['timeframe'],
            z_score=sig_kwargs['z_score'],
            z_score_tier=sig_kwargs['z_score_tier'],
        )
        if sid:
            added += 1
            fired.add(token)

    return added, fired


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point for signals_runner
# ═══════════════════════════════════════════════════════════════════════════════

def run(prices_dict=None):
    """Entry point for signals_runner."""
    return scan_coiled_spring(prices_dict)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI backtest / analysis tool
# ═══════════════════════════════════════════════════════════════════════════════

def analyze(token='ENA'):
    """Run detection on a token and print detailed diagnostics."""
    rows = _get_candles_5m(token)
    if not rows:
        print(f"No 5m data for {token}")
        return

    print(f"Analyzing {token} — {len(rows)} candles loaded")
    print(f"Latest: {rows[-1]}")

    sig, diag = detect_coiled_spring(rows)
    print(f"\nDiagnostics:")
    for k, v in diag.items():
        print(f"  {k}: {v}")

    if sig:
        print(f"\n🚨 SIGNAL FIRED!")
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
    token = sys.argv[1] if len(sys.argv) > 1 else 'ENA'
    analyze(token)
