#!/usr/bin/env python3
"""
pump_catcher.py — Early-Stage Momentum Breakout Signal.

Catches the FIRST explosive move in a new direction by detecting price
acceleration. Unlike pump_hunter (reversion/fade), this RIDES the spike.

Detection:
  1. Price velocity > threshold in N bars (explosive move)
  2. Acceleration > 0 (momentum building, not just a spike)
  3. Price above EMA (trend aligned)
  4. RSI not overbought (room to run)
  5. Fresh move (cooldown dedup)

Architecture:
  price_history (1m) → velocity/acceleration detection
  → signal_schema.add_signal() → signals_hermes_runtime.db
  → signal_compactor → hotset.json → guardian → HL

Signal types:
  - pump_catcher_long  : momentum breakout LONG
  - pump_catcher_short : momentum breakout SHORT (future)

Pipeline: runs as a fast signal (every minute) via signals_runner.
"""

import os
import sys
import time
import sqlite3
import statistics

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes

SIGNAL_LOG = '/var/www/hermes/logs/signals.log'
os.makedirs(os.path.dirname(SIGNAL_LOG), exist_ok=True)


def _log(msg):
    print(msg)
    try:
        with open(SIGNAL_LOG, 'a') as f:
            f.write(msg + '\n')
    except Exception:
        pass


# ── Paths ─────────────────────────────────────────────────────────────────────
from paths import RUNTIME_DB, STATIC_DB
_RUNTIME_DB = RUNTIME_DB
_PRICE_DB = STATIC_DB  # price_history — live 1m prices

# ── Parameters (from hermes_constants, read at call time) ─────────────────────
from hermes_constants import (
    PUMP_CATCHER_ENABLED,
    PUMP_CATCHER_PLUS_ENABLED,
    PUMP_CATCHER_MINUS_ENABLED,
    PUMP_CATCHER_VELOCITY_MIN,
    PUMP_CATCHER_VELOCITY_BARS,
    PUMP_CATCHER_ACCEL_MIN,
    PUMP_CATCHER_TREND_EMA,
    PUMP_CATCHER_RSI_MAX,
    PUMP_CATCHER_RSI_MIN,
    PUMP_CATCHER_RSI_PERIOD,
    PUMP_CATCHER_COOLDOWN_BARS,
    PUMP_CATCHER_MIN_PRICE_ROWS,
    PUMP_CATCHER_CONFIDENCE_BASE,
    PUMP_CATCHER_CONFIDENCE_CAP,
)


# ═══════════════════════════════════════════════════════════════════════════════
# EMA / RSI Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _ema(values, period):
    """Compute EMA for a list of values. Returns latest EMA value."""
    if len(values) < period:
        return values[-1] if values else 0
    k = 2.0 / (period + 1)
    ema_val = sum(values[:period]) / period
    for v in values[period:]:
        ema_val = v * k + ema_val * (1 - k)
    return ema_val


def _ema_series(values, period):
    """Return EMA series (oldest first), None for indices < period-1."""
    if len(values) < period:
        return [None] * len(values)
    k = 2.0 / (period + 1)
    result = [None] * (period - 1)
    ema_val = sum(values[:period]) / period
    result.append(ema_val)
    for price in values[period:]:
        ema_val = price * k + ema_val * (1 - k)
        result.append(ema_val)
    return result


def _rsi(closes, period=14):
    """Compute RSI. Returns float or None if insufficient data."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    # Use last `period` deltas
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


# ═══════════════════════════════════════════════════════════════════════════════
# Data Fetch — LIVE prices from price_history (signals_hermes.db)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_1m_prices(token, lookback=120):
    """Fetch 1m close prices from price_history, oldest first.

    Freshness guard: returns [] if most recent price is > 3 minutes old.
    Returns list of floats (closes), oldest first.
    """
    conn = None
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT timestamp, price FROM (
                SELECT timestamp, price
                FROM price_history
                WHERE token = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ) sub
            ORDER BY timestamp ASC
        """, (token.upper(), lookback))
        rows = c.fetchall()

        if not rows:
            return []

        most_recent_ts = rows[-1][0]
        if (time.time() - most_recent_ts) > 180:  # 3 min freshness
            return []

        return [r[1] for r in rows]

    except Exception as e:
        print(f"  [pump-catcher] price_history error for {token}: {e}")
        return []
    finally:
        if conn:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Detection
# ═══════════════════════════════════════════════════════════════════════════════

def detect_pump(token, closes):
    """Detect early-stage momentum breakout.

    Fires when:
      1. Price velocity > threshold in N bars (explosive move)
      2. Acceleration > 0 (momentum building — current velocity > prior velocity)
      3. Price above EMA (trend aligned — not fighting the trend)
      4. RSI not overbought/oversold (room to run)

    Args:
        token: str (for logging)
        closes: list of float (1m closes, oldest first)

    Returns:
        dict with direction, velocity, acceleration, rsi, ema, confidence — or None
    """
    if len(closes) < PUMP_CATCHER_MIN_PRICE_ROWS:
        return None

    n = PUMP_CATCHER_VELOCITY_BARS  # typically 3
    latest_idx = len(closes) - 1

    # Need at least 2 windows for velocity + acceleration
    if latest_idx < n * 2 + PUMP_CATCHER_TREND_EMA:
        return None

    # ── 1. Velocity: price move in last N bars ────────────────────────────────
    price_now = closes[latest_idx]
    price_n_bars_ago = closes[latest_idx - n]
    if price_n_bars_ago == 0:
        return None

    velocity = (price_now - price_n_bars_ago) / price_n_bars_ago * 100.0

    # ── 2. Acceleration: current velocity > prior velocity ─────────────────────
    # Prior N bars (bars -2N to -N)
    price_2n_ago = closes[latest_idx - n * 2]
    if price_2n_ago == 0:
        return None

    prior_velocity = (price_n_bars_ago - price_2n_ago) / price_2n_ago * 100.0
    acceleration = velocity - prior_velocity

    # ── 3. Direction based on velocity sign ────────────────────────────────────
    if velocity > PUMP_CATCHER_VELOCITY_MIN:
        direction = 'LONG'
    elif velocity < -PUMP_CATCHER_VELOCITY_MIN:
        direction = 'SHORT'
    else:
        return None  # not explosive enough

    # ── 4. Acceleration must be positive (momentum building) ───────────────────
    if direction == 'LONG' and acceleration < PUMP_CATCHER_ACCEL_MIN:
        return None
    if direction == 'SHORT' and acceleration > -PUMP_CATCHER_ACCEL_MIN:
        return None

    # ── 5. Trend alignment: price above/below EMA ─────────────────────────────
    ema_period = PUMP_CATCHER_TREND_EMA
    ema_val = _ema(closes[-ema_period - 10:], ema_period)
    if ema_val is None or ema_val == 0:
        return None

    if direction == 'LONG' and price_now < ema_val:
        return None  # not trending up
    if direction == 'SHORT' and price_now > ema_val:
        return None  # not trending down

    # ── 6. RSI filter ──────────────────────────────────────────────────────────
    rsi_val = _rsi(closes, PUMP_CATCHER_RSI_PERIOD)
    if rsi_val is not None:
        if direction == 'LONG' and rsi_val > PUMP_CATCHER_RSI_MAX:
            return None  # overbought — too late
        if direction == 'SHORT' and rsi_val < PUMP_CATCHER_RSI_MIN:
            return None  # oversold — too late

    # ── 7. Single-bar spike filter: skip if velocity is one huge candle ────────
    # Real momentum has follow-through, not just one candle. Check that at least
    # 2 of the last 3 candles closed in the signal direction.
    recent_3 = closes[-3:]
    if direction == 'LONG':
        green_count = sum(1 for i in range(1, len(recent_3)) if recent_3[i] > recent_3[i - 1])
        if green_count < 2:
            return None  # not enough follow-through
    else:
        red_count = sum(1 for i in range(1, len(recent_3)) if recent_3[i] < recent_3[i - 1])
        if red_count < 2:
            return None  # not enough follow-through

    # ── Confidence scoring ─────────────────────────────────────────────────────
    conf = PUMP_CATCHER_CONFIDENCE_BASE

    # Strong velocity bonus
    if abs(velocity) > 0.8:
        conf += 5

    # Strong acceleration bonus
    if abs(acceleration) > 0.3:
        conf += 5

    # Higher timeframe alignment: check if price > EMA50
    if len(closes) >= 60:
        ema50 = _ema(closes[-60:], 50)
        if ema50 and ((direction == 'LONG' and price_now > ema50) or
                      (direction == 'SHORT' and price_now < ema50)):
            conf += 5

    # RSI sweet spot (not extreme)
    if rsi_val is not None and 40 <= rsi_val <= 65:
        conf += 5

    # Consistency bonus: all 3 recent bars in same direction
    if direction == 'LONG':
        all_green = all(recent_3[i] > recent_3[i - 1] for i in range(1, len(recent_3)))
        if all_green:
            conf += 3
    else:
        all_red = all(recent_3[i] < recent_3[i - 1] for i in range(1, len(recent_3)))
        if all_red:
            conf += 3

    conf = min(PUMP_CATCHER_CONFIDENCE_CAP, max(50, conf))

    return {
        'direction': direction,
        'velocity': round(velocity, 4),
        'acceleration': round(acceleration, 4),
        'price': price_now,
        'ema': round(ema_val, 8),
        'rsi': round(rsi_val, 1) if rsi_val is not None else None,
        'confidence': conf,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner — Entry Point for signals_runner
# ═══════════════════════════════════════════════════════════════════════════════

def run(prices_dict=None):
    """Scan all tokens for pump-catcher signals.

    Entry point for signals_runner via signals/__init__.py.
    prices_dict: {token: {'price': float}} from get_all_latest_prices().
    """
    if not PUMP_CATCHER_ENABLED:
        return 0

    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()

    from position_manager import get_open_positions as _get_open_pos
    from signal_gen import recent_trade_exists, is_delisted, MIN_TRADE_INTERVAL_MINUTES
    from hyperliquid_exchange import get_open_hype_positions_curl

    open_pos = {p['token']: p['direction'] for p in _get_open_pos()}

    # Also check HL positions directly (pump_catcher may not be in PM tracking)
    try:
        hl_positions = get_open_hype_positions_curl()
        for p in hl_positions:
            tok = p.get('token', '').upper()
            if tok and tok not in open_pos:
                open_pos[tok] = p.get('direction', 'LONG')
    except Exception:
        pass

    added = 0

    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue
        if price_age_minutes(token) > 5:  # tight freshness — we need live data
            continue
        price = data.get('price')
        if not price or price <= 0:
            continue

        token_upper = token.upper()

        # Skip if already have a position
        if token_upper in open_pos:
            continue

        # Skip if recently traded
        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
            continue

        # Skip delisted
        if is_delisted(token_upper):
            continue

        # ── Get 1m price history ───────────────────────────────────────────────
        closes = _get_1m_prices(token, lookback=120)
        if not closes or len(closes) < PUMP_CATCHER_MIN_PRICE_ROWS:
            continue

        # ── Detect pump momentum ───────────────────────────────────────────────
        sig = detect_pump(token, closes)
        if sig is None:
            continue

        direction = sig['direction']

        # ── Per-direction kill-switch ──────────────────────────────────────────
        if direction == 'LONG' and not PUMP_CATCHER_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not PUMP_CATCHER_MINUS_ENABLED:
            continue

        # ── Cooldown ───────────────────────────────────────────────────────────
        if get_cooldown(token, direction=direction):
            continue

        # ── Write signal ───────────────────────────────────────────────────────
        source = 'pump-catcher+' if direction == 'LONG' else 'pump-catcher-'
        signal_type = 'pump_catcher_long' if direction == 'LONG' else 'pump_catcher_short'

        try:
            sid = add_signal(
                token=token_upper,
                direction=direction,
                signal_type=signal_type,
                source=source,
                confidence=sig['confidence'],
                value=sig['velocity'],
                price=sig['price'],
                exchange='hyperliquid',
                timeframe='1m',
                z_score=None,
                z_score_tier=None,
                rsi_14=sig.get('rsi'),
            )
            if sid:
                added += 1
                from signal_gen import set_cooldown
                set_cooldown(token, direction, hours=PUMP_CATCHER_COOLDOWN_BARS / 60.0)
                _log(
                    f"  {direction:5s}-pump-catcher {token_upper:8s} "
                    f"conf={sig['confidence']:.0f}% "
                    f"vel={sig['velocity']:+.3f}% accel={sig['acceleration']:+.3f}% "
                    f"price={sig['price']:.8g} ema={sig['ema']:.8g} "
                    f"rsi={sig.get('rsi', 'N/A')}"
                )
        except Exception as e:
            print(f"[pump-catcher] add_signal error for {token}: {e}")

    return added


# ═══════════════════════════════════════════════════════════════════════════════
# CLI — standalone testing
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import time as _time
    from signal_schema import init_db, get_all_latest_prices

    init_db()
    prices = get_all_latest_prices()
    print(f"[pump-catcher] Scanning {len(prices)} tokens...")
    n = run(prices)
    print(f"[pump-catcher] Done. {n} signals emitted.")
