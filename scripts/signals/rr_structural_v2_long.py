#!/usr/bin/env python3
"""rr_structural_v2_long — Structural LONG signal with enhanced filters.

V2 improvements over rr-struct+:
  - Blocks LONG when momentum is falling AND price is at extreme (z < -2.0 OR bb < 0)
  - This catches "buying into a falling knife" setups like KAS and WLD

Uses the risk_reward_engine for structural quality evaluation.
Fires ONLY LONG signals when engine scores Grade A/B with R:R >= 2.0.
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown, get_all_latest_prices
from tokens import get_all_tradeable_tokens
from risk_reward_engine import evaluate_rr
from paths import HERMES_DATA

from hermes_constants import (
    RR_STRUCTURAL_V2_LONG_ENABLED,
    RR_STRUCTURAL_MIN_SCORE,
    RR_STRUCTURAL_MIN_RR,
    RR_STRUCTURAL_MIN_ATR_PCT,
    RR_STRUCTURAL_MAX_ATR_PCT,
    RR_STRUCTURAL_REGIMES,
    RR_STRUCTURAL_COOLDOWN_HOURS,
    RR_STRUCTURAL_CONF_BASE,
    RR_STRUCTURAL_CONF_CAP,
    RR_STRUCTURAL_OPEN_SKY_BONUS,
    RR_STRUCTURAL_LIQ_BONUS,
    RR_STRUCTURAL_RR_CONF_MULT,
    RR_STRUCTURAL_RR_CONF_CAP,
    RR_STRUCTURAL_GRADE_A_BONUS,
    RR_STRUCTURAL_GRADE_B_BONUS,
    RR_STRUCTURAL_MAGNET_THRESH,
    RR_STRUCTURAL_MAX_PRICE_AGE,
    RR_STRUCTURAL_RSI_MAX,
    RR_STRUCTURAL_ACCEL_LOOKBACK,
    RR_STRUCTURAL_BLOCK_ACCEL,
    RR_STRUCTURAL_RANGE_LONG_MAX,
    RR_STRUCTURAL_V2_MOM_FALLING_Z_MIN,
    RR_STRUCTURAL_V2_MOM_FALLING_BB_MIN,
    LONG_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'rr_structural_v2_long'
SOURCE_LONG      = 'rr-struct-v2+'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')


def _log(msg):
    print(f'[rr-struct-v2+] {msg}', flush=True)


def _compute_rsi(closes, period=14):
    """Compute RSI from close prices. Returns float or None."""
    if not closes or len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _get_rsi(token):
    """Fetch RSI from 1m candles. Returns float or None."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_1m
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT 100
        """, (token.upper(),))
        rows = cur.fetchall()
        if len(rows) < 20:
            return None
        closes = [r[0] for r in reversed(rows)]
        return _compute_rsi(closes)
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


def _compute_price_acceleration(token, lookback=None):
    """Compute short-term price acceleration from recent 1m candle closes.

    Returns float: positive = price moving UP, negative = moving DOWN.
    Returns None if insufficient data.
    """
    if lookback is None:
        lookback = RR_STRUCTURAL_ACCEL_LOOKBACK
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_1m
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT ?
        """, (token.upper(), lookback + 1))
        rows = cur.fetchall()
        if len(rows) < lookback + 1:
            return None
        closes = [r[0] for r in reversed(rows)]
        mid = len(closes) // 2
        first_half_delta = closes[mid] - closes[0]
        second_half_delta = closes[-1] - closes[mid]
        return second_half_delta - first_half_delta
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


def _get_range_position(token):
    """Get price position within the rolling 6h range (0=at low, 100=at high).

    Uses MAX(high)/MIN(low) over last 6 1h candles for a dynamic range.
    Returns float 0-100 or None if insufficient data.
    """
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT MAX(high), MIN(low) FROM candles_1h
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT 6
        """, (token,))
        row = cur.fetchone()
        if not row or row[0] is None or row[1] is None or row[0] == row[1]:
            return None
        high, low = row[0], row[1]
        cur.execute("""
            SELECT close FROM candles_1m
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT 1
        """, (token,))
        price_row = cur.fetchone()
        if not price_row:
            return None
        price = price_row[0]
        return round((price - low) / (high - low) * 100, 1)
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


def _get_momentum_state(token):
    """Compute momentum state from last 6 1m candle closes.

    Returns 'rising', 'falling', or 'flat' based on 5-bar velocity.
    Returns None if insufficient data.
    """
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_1m
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT 6
        """, (token.upper(),))
        rows = cur.fetchall()
        if len(rows) < 6:
            return None
        closes = [r[0] for r in reversed(rows)]
        if closes[0] == 0:
            return None
        vel = (closes[-1] - closes[0]) / closes[0] * 100
        if vel > 0.5:
            return 'rising'
        elif vel < -0.5:
            return 'falling'
        else:
            return 'flat'
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


def detect(token, price):
    """Evaluate structural R:R for a LONG-only signal. Returns signal dict or None.

    V2 filters (in addition to base rr-struct filters):
      - Block LONG when momentum = falling AND (z_score < -2.0 OR bb_position < 0)
        This catches "buying into a falling knife" setups.
    """
    # Get RSI for overbought filtering
    rsi = _get_rsi(token)

    # Get price acceleration for direction filter
    price_accel = _compute_price_acceleration(token)

    # Get range position for top-of-range filter
    range_pos = _get_range_position(token)

    # Get momentum state for V2 filter
    momentum = _get_momentum_state(token)

    # LONG evaluation
    long_ok = False
    long_result = evaluate_rr(token, 'LONG', price)
    if (long_result['grade'] in ('A', 'B') and
        long_result['rr_ratio'] >= RR_STRUCTURAL_MIN_RR and
        long_result['score'] >= RR_STRUCTURAL_MIN_SCORE and
        long_result['vol_width']['atr_regime'] in RR_STRUCTURAL_REGIMES and
        RR_STRUCTURAL_MIN_ATR_PCT <= long_result['vol_width']['atr_pct'] <= RR_STRUCTURAL_MAX_ATR_PCT):

        # RSI check: don't LONG when overbought
        if rsi is not None and rsi > RR_STRUCTURAL_RSI_MAX:
            _log(f'{token} LONG blocked: RSI {rsi:.1f} > {RR_STRUCTURAL_RSI_MAX} (overbought)')
        # Acceleration check: don't LONG when price accelerating DOWN
        elif RR_STRUCTURAL_BLOCK_ACCEL and price_accel is not None and price_accel < 0:
            _log(f'{token} LONG blocked: accel {price_accel:+.6f} < 0 (price going DOWN)')
        # Range position check: don't LONG when price at top of 1h range
        elif range_pos is not None and range_pos >= RR_STRUCTURAL_RANGE_LONG_MAX:
            _log(f'{token} LONG blocked: range {range_pos:.1f}% >= {RR_STRUCTURAL_RANGE_LONG_MAX}% (buying at top)')
        # V2: Falling momentum + extreme oversold = catching falling knife
        elif (momentum == 'falling' and
              long_result['vol_width'].get('bb_position') is not None and
              long_result['vol_width']['bb_position'] < RR_STRUCTURAL_V2_MOM_FALLING_BB_MIN):
            _log(f'{token} LONG blocked: momentum=falling + bb={long_result["vol_width"]["bb_position"]:.3f} < {RR_STRUCTURAL_V2_MOM_FALLING_BB_MIN} (falling knife)')
        elif (momentum == 'falling' and
              long_result.get('z_score') is not None and
              long_result['z_score'] < RR_STRUCTURAL_V2_MOM_FALLING_Z_MIN):
            _log(f'{token} LONG blocked: momentum=falling + z={long_result["z_score"]:.3f} < {RR_STRUCTURAL_V2_MOM_FALLING_Z_MIN} (falling knife)')
        else:
            long_ok = True

    if not long_ok:
        return None

    result = long_result

    # Compute confidence
    conf = RR_STRUCTURAL_CONF_BASE
    conf += min(RR_STRUCTURAL_RR_CONF_CAP, int((result['rr_ratio'] - RR_STRUCTURAL_MIN_RR) * RR_STRUCTURAL_RR_CONF_MULT))
    conf += RR_STRUCTURAL_GRADE_A_BONUS if result['grade'] == 'A' else RR_STRUCTURAL_GRADE_B_BONUS

    # Open skies bonus
    has_target = any(l.get('type') == 'resistance' for l in result['sr_map'])
    if not has_target:
        conf += RR_STRUCTURAL_OPEN_SKY_BONUS

    # Liquidity proximity bonus
    if result['liquidity'].get('magnet_score', 0) > RR_STRUCTURAL_MAGNET_THRESH:
        conf += RR_STRUCTURAL_LIQ_BONUS

    conf = min(RR_STRUCTURAL_CONF_CAP, conf)

    return {
        'direction': 'LONG',
        'confidence': conf,
        'value': result['rr_ratio'],
        'price': price,
        'notes': f"R:R={result['rr_ratio']:.2f} Score={result['score']} Grade={result['grade']} "
                 f"Regime={result['vol_width']['atr_regime']} ATR={result['vol_width']['atr_pct']:.2f}% "
                 f"mom={momentum}",
    }


def scan_signals():
    """Scan all tradeable tokens for structurally excellent LONG setups."""
    added = 0
    tokens = get_all_tradeable_tokens()
    prices = get_all_latest_prices()

    for token in tokens:
        token_upper = token.upper()

        # Price age check
        if price_age_minutes(token) > RR_STRUCTURAL_MAX_PRICE_AGE:
            continue

        # Get latest price
        price_data = prices.get(token_upper)
        if not price_data or price_data.get('price', 0) <= 0:
            continue
        price = price_data['price']

        # Detect
        sig = detect(token_upper, price)
        if not sig:
            continue

        # Layer 1: kill-switch
        if not RR_STRUCTURAL_V2_LONG_ENABLED:
            continue

        # Layer 1: blacklists
        if token_upper in LONG_BLACKLIST:
            continue

        # Cooldown
        if get_cooldown(token_upper, direction='LONG'):
            continue

        sid = add_signal(
            token=token_upper,
            direction='LONG',
            signal_type=SIGNAL_TYPE_LONG,
            source=SOURCE_LONG,
            confidence=sig['confidence'],
            value=sig.get('value'),
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='15m',
            z_score=None,
        )
        if sid:
            added += 1
            set_cooldown(token_upper, 'LONG', hours=RR_STRUCTURAL_COOLDOWN_HOURS)
            _log(f'{token_upper} LONG conf={sig["confidence"]} {sig["notes"]}')

    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    added = run()
    _log(f'Total: {added} signals')
