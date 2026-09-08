#!/usr/bin/env python3
"""Accel-300 V4 SHORT — Earlier Entry (Pre-Drop Detection).

Branched from accel_300_v3_short to fire BEFORE the drop, not after.

THESIS:
  v3 fires when gap is already large AND accelerating — enters AFTER the drop
  has already happened (gap already widened). The WLD example: signal fired
  1h40m after the first drop.

  v4 adds:
  - Lower MIN_GAP_ACCEL (0.10 vs 0.20): fire when gap STARTS widening
  - Volume spike: detect 20%+ volume increase (smart money selling early)
  - Price at resistance: detect EMA300 touch+rejection (price tested and failed)
  - RSI divergence: bearish divergence (price higher high + RSI lower high)
  - Momentum shift: detect momentum changing from rising to falling

ENTRY CONDITIONS (v3 base, kept):
  1. Price below EMA300 with gap >= 0.8% (lowered from 1.0)
  2. Gap is accelerating (widening over 10-bar window) — LOWERED threshold
  3. Price velocity negative with conviction (0.03% min — lower than v3)
  4. Price persisted below EMA for 3+ bars (not a cross wick)
  5. Linear regression slope negative (trending down)
  6. RSI not oversold (< 25) — avoid bounce risk
  7. Not chasing — don't enter after large 30m drops
  8. Volume confirms drop (>= 1.1x average)
  9. Fresh cross within 10 bars (widened from 8)

V4 ADDITIONS:
  10. Volume spike: 20%+ volume increase in last 5 bars (smart money selling)
  11. Price at resistance: touched EMA300 and rejected in last 10 bars
  12. RSI divergence: bearish divergence (price higher high + RSI lower high)
  13. Momentum shift: momentum changed from rising to falling
"""

import sys, os, sqlite3, time
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes

SIGNAL_LOG = '/var/www/hermes/logs/signals.log'
os.makedirs(os.path.dirname(SIGNAL_LOG), exist_ok=True)


def _log(msg: str) -> None:
    print(msg)
    try:
        with open(SIGNAL_LOG, 'a') as log_file:
            log_file.write(msg + '\n')
    except OSError:
        pass


# ── Paths ─────────────────────────────────────────────────────────────────────
from paths import RUNTIME_DB, STATIC_DB, CANDLES_DB
_RUNTIME_DB = RUNTIME_DB
_PRICE_DB = STATIC_DB
_CANDLES_DB = CANDLES_DB

# ── V4 SHORT constants (from hermes_constants.py) ────────────────────────────
from hermes_constants import (
    ACCEL_300_V4_SHORT_MIN_GAP,
    ACCEL_300_V4_SHORT_MAX_GAP,
    ACCEL_300_V4_SHORT_MIN_GAP_ACCEL,
    ACCEL_300_V4_SHORT_GAP_ACCEL_WINDOW,
    ACCEL_300_V4_SHORT_VELOCITY_WINDOW,
    ACCEL_300_V4_SHORT_MIN_VELOCITY,
    ACCEL_300_V4_SHORT_PERSISTENCE_BARS,
    ACCEL_300_V4_SHORT_SLOPE_WINDOW,
    ACCEL_300_V4_SHORT_MIN_SLOPE_PCT,
    ACCEL_300_V4_SHORT_RSI_MAX,
    ACCEL_300_V4_SHORT_RSI_MIN,
    ACCEL_300_V4_SHORT_CHASE_DROP_MAX,
    ACCEL_300_V4_SHORT_CHASE_RSI_MIN,
    ACCEL_300_V4_SHORT_VOLUME_LOOKBACK,
    ACCEL_300_V4_SHORT_VOLUME_MULT,
    ACCEL_300_V4_SHORT_COOLDOWN_BARS,
    ACCEL_300_V4_SHORT_LOOKBACK_1M,
    ACCEL_300_V4_SHORT_FRESH_CROSS_BARS,
    ACCEL_300_V4_SHORT_FRESH_CROSS_MIN_GAP,
    ACCEL_300_V4_SHORT_CONF_BASE,
    ACCEL_300_V4_SHORT_CONF_FLOOR,
    ACCEL_300_V4_SHORT_CONF_CAP,
    ACCEL_300_V4_SHORT_VOL_SPIKE_WINDOW,
    ACCEL_300_V4_SHORT_VOL_SPIKE_MULT,
    ACCEL_300_V4_SHORT_RESISTANCE_WINDOW,
    ACCEL_300_V4_SHORT_RESISTANCE_THRESH,
    ACCEL_300_V4_SHORT_DIVERGENCE_WINDOW,
    ACCEL_300_V4_SHORT_MOMENTUM_SHIFT_WINDOW,
)

# Aliases for shorter references
V4_MIN_GAP = ACCEL_300_V4_SHORT_MIN_GAP
V4_MAX_GAP = ACCEL_300_V4_SHORT_MAX_GAP
V4_MIN_GAP_ACCEL = ACCEL_300_V4_SHORT_MIN_GAP_ACCEL
V4_GAP_ACCEL_WINDOW = ACCEL_300_V4_SHORT_GAP_ACCEL_WINDOW
V4_VELOCITY_WINDOW = ACCEL_300_V4_SHORT_VELOCITY_WINDOW
V4_MIN_VELOCITY = ACCEL_300_V4_SHORT_MIN_VELOCITY
V4_PERSISTENCE_BARS = ACCEL_300_V4_SHORT_PERSISTENCE_BARS
V4_SLOPE_WINDOW = ACCEL_300_V4_SHORT_SLOPE_WINDOW
V4_MIN_SLOPE_PCT = ACCEL_300_V4_SHORT_MIN_SLOPE_PCT
V4_RSI_MAX = ACCEL_300_V4_SHORT_RSI_MAX
V4_RSI_MIN = ACCEL_300_V4_SHORT_RSI_MIN
V4_CHASE_DROP_MAX = ACCEL_300_V4_SHORT_CHASE_DROP_MAX
V4_CHASE_RSI_MIN = ACCEL_300_V4_SHORT_CHASE_RSI_MIN
V4_VOLUME_LOOKBACK = ACCEL_300_V4_SHORT_VOLUME_LOOKBACK
V4_VOLUME_MULT = ACCEL_300_V4_SHORT_VOLUME_MULT
V4_COOLDOWN_BARS = ACCEL_300_V4_SHORT_COOLDOWN_BARS
V4_LOOKBACK_1M = ACCEL_300_V4_SHORT_LOOKBACK_1M
V4_FRESH_CROSS_BARS = ACCEL_300_V4_SHORT_FRESH_CROSS_BARS
V4_FRESH_CROSS_MIN_GAP = ACCEL_300_V4_SHORT_FRESH_CROSS_MIN_GAP
V4_CONF_BASE = ACCEL_300_V4_SHORT_CONF_BASE
V4_CONF_FLOOR = ACCEL_300_V4_SHORT_CONF_FLOOR
V4_CONF_CAP = ACCEL_300_V4_SHORT_CONF_CAP
V4_VOL_SPIKE_WINDOW = ACCEL_300_V4_SHORT_VOL_SPIKE_WINDOW
V4_VOL_SPIKE_MULT = ACCEL_300_V4_SHORT_VOL_SPIKE_MULT
V4_RESISTANCE_WINDOW = ACCEL_300_V4_SHORT_RESISTANCE_WINDOW
V4_RESISTANCE_THRESH = ACCEL_300_V4_SHORT_RESISTANCE_THRESH
V4_DIVERGENCE_WINDOW = ACCEL_300_V4_SHORT_DIVERGENCE_WINDOW
V4_MOMENTUM_SHIFT_WINDOW = ACCEL_300_V4_SHORT_MOMENTUM_SHIFT_WINDOW

PERIOD = 300  # EMA300 period
DRY_RUN = '--dry' in sys.argv

SIGNAL_TYPE = 'accel_300_v4_short'
SOURCE = 'accel-300-v4-short-'


def _get_token_params(token: str) -> dict:
    """Get signal params with regime-specific overrides applied."""
    from regime_params import get_regime_params, apply_overrides, PARAM_MAP_SHORT
    overrides = get_regime_params(token, 'accel_300_v4_short')
    if not overrides:
        return {}
    defaults = {k: v for k, v in globals().items() if k.startswith('ACCEL_300_V4_SHORT_')}
    return apply_overrides(defaults, overrides, PARAM_MAP_SHORT)


# ═══════════════════════════════════════════════════════════════════════════════
# EMA helper
# ═══════════════════════════════════════════════════════════════════════════════

def _ema_series(values: list, period: int) -> list:
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


# ═══════════════════════════════════════════════════════════════════════════════
# RSI helper (Wilder smoothing)
# ═══════════════════════════════════════════════════════════════════════════════

def _rsi(closes: list, period: int = 14) -> float:
    """Compute RSI from closes using Wilder smoothing. Returns 50 if insufficient data."""
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _rsi_series(closes: list, period: int = 14) -> list:
    """Compute RSI series (oldest first) using Wilder smoothing. Returns list of floats."""
    if len(closes) < period + 1:
        return [50.0] * len(closes)
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsi_values = [50.0] * period  # pad initial values
    if avg_loss == 0:
        rsi_values.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi_values.append(100.0 - (100.0 / (1.0 + rs)))
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100.0 - (100.0 / (1.0 + rs)))
    return rsi_values


# ═══════════════════════════════════════════════════════════════════════════════
# Data fetch — with staleness guards from v3
# ═══════════════════════════════════════════════════════════════════════════════

def _get_1m_prices(token: str, lookback: int = V4_LOOKBACK_1M) -> list:
    """Fetch 1m close prices from price_history, oldest first.
    Staleness guard: rejects if most recent candle is >2 minutes old."""
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

        # Staleness guard: reject if most recent candle is >2 minutes old
        most_recent_ts = rows[-1][0]
        if (time.time() - most_recent_ts) > 120:
            return []

        # Bar-to-bar gap guard
        bar_gaps = [rows[i][0] - rows[i-1][0] for i in range(1, len(rows))]
        if bar_gaps:
            mean_gap = sum(bar_gaps) / len(bar_gaps)
            variance = sum((g - mean_gap) ** 2 for g in bar_gaps) / len(bar_gaps)
            std_gap = variance ** 0.5
            threshold = max(150, mean_gap + 3.0 * std_gap)
            for i in range(1, len(rows)):
                if rows[i][0] - rows[i-1][0] > threshold:
                    return []

        return [{'timestamp': r[0], 'price': r[1]} for r in rows]

    except Exception as e:
        print(f"  [accel-300-v4-short] price_history error for {token}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def _check_volume(token: str, volume_mult: float = None) -> bool:
    """Check if volume is available and reasonable. Returns True if OK."""
    if volume_mult is None:
        volume_mult = V4_VOLUME_MULT
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=5)
        c = conn.cursor()
        c.execute("""
            SELECT volume FROM (
                SELECT ts, volume
                FROM candles_1m
                WHERE token = ? AND is_closed = 1
                ORDER BY ts DESC
                LIMIT ?
            ) sub
            ORDER BY ts ASC
        """, (token.upper(), V4_VOLUME_LOOKBACK))
        rows = c.fetchall()
        volumes = [r[0] for r in rows if r[0] is not None]

        if not volumes or len(volumes) < 10:
            return True  # no data — don't block

        avg_vol = sum(volumes) / len(volumes)
        if avg_vol <= 0:
            return True  # stale data — don't block

        return volumes[-1] >= avg_vol * volume_mult
    except Exception:
        return True  # on error, don't block
    finally:
        if conn:
            conn.close()


def _get_volume_series(token: str, lookback: int = 30) -> list:
    """Fetch volume series from candles_1m, oldest first."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=5)
        c = conn.cursor()
        c.execute("""
            SELECT volume FROM (
                SELECT ts, volume
                FROM candles_1m
                WHERE token = ? AND is_closed = 1
                ORDER BY ts DESC
                LIMIT ?
            ) sub
            ORDER BY ts ASC
        """, (token.upper(), lookback))
        rows = c.fetchall()
        return [r[0] for r in rows if r[0] is not None]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# V4 EARLIER DETECTION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _check_volume_spike(volumes: list) -> bool:
    """Check if volume increased 20%+ in last 5 bars (smart money selling).
    Returns True if spike detected or insufficient data."""
    if len(volumes) < V4_VOL_SPIKE_WINDOW + 2:
        return True  # insufficient data — don't block
    recent_avg = sum(volumes[-V4_VOL_SPIKE_WINDOW:]) / V4_VOL_SPIKE_WINDOW
    prior_avg = sum(volumes[-(V4_VOL_SPIKE_WINDOW*2):-V4_VOL_SPIKE_WINDOW]) / V4_VOL_SPIKE_WINDOW
    if prior_avg <= 0:
        return True
    return recent_avg >= prior_avg * V4_VOL_SPIKE_MULT


def _check_price_at_resistance(closes: list, ema300: list) -> bool:
    """Check if price touched EMA300 in last 10 bars and rejected (bearish signal).
    Returns True if rejection detected or insufficient data."""
    if len(closes) < V4_RESISTANCE_WINDOW:
        return False  # insufficient data — don't contribute bonus
    latest_idx = len(closes) - 1
    start = latest_idx - V4_RESISTANCE_WINDOW
    for idx in range(max(start, PERIOD - 1), latest_idx):
        ema = ema300[idx]
        if ema is None or ema == 0:
            continue
        gap_pct = abs(closes[idx] - ema) / ema * 100.0
        if gap_pct <= V4_RESISTANCE_THRESH:
            # Price touched EMA300 — check if it rejected (closed below after touching)
            if idx + 1 <= latest_idx and closes[idx + 1] < closes[idx]:
                return True
    return False


def _check_rsi_divergence(closes: list, rsi_series: list) -> bool:
    """Check for bearish RSI divergence: price makes higher high while RSI makes lower high.
    This is a leading indicator — RSI weakening before price drops.
    Returns True if divergence detected or insufficient data."""
    if len(closes) < V4_DIVERGENCE_WINDOW or len(rsi_series) < V4_DIVERGENCE_WINDOW:
        return False
    latest_idx = len(closes) - 1
    window_start = latest_idx - V4_DIVERGENCE_WINDOW

    # Find two local price highs in the window
    price_highs = []
    rsi_at_highs = []
    for idx in range(max(window_start + 2, PERIOD), latest_idx - 1):
        # Local high: price higher than neighbors
        if closes[idx] > closes[idx - 1] and closes[idx] > closes[idx + 1]:
            price_highs.append((idx, closes[idx]))
            rsi_at_highs.append((idx, rsi_series[idx]))

    if len(price_highs) < 2:
        return False

    # Check last two highs
    idx1, p1 = price_highs[-2]
    idx2, p2 = price_highs[-1]
    _, r1 = rsi_at_highs[-2]
    _, r2 = rsi_at_highs[-1]

    # Bearish divergence: price higher high + RSI lower high
    return p2 > p1 and r2 < r1


def _check_momentum_shift(closes: list) -> bool:
    """Check if momentum changed from rising to falling (momentum shift).
    Uses a simple velocity comparison over two consecutive windows.
    Returns True if shift detected or insufficient data."""
    if len(closes) < V4_MOMENTUM_SHIFT_WINDOW * 2:
        return False
    latest_idx = len(closes) - 1
    # Velocity in first half of window
    mid = latest_idx - V4_MOMENTUM_SHIFT_WINDOW
    vel_first = closes[mid] - closes[mid - V4_MOMENTUM_SHIFT_WINDOW]
    # Velocity in second half of window
    vel_second = closes[latest_idx] - closes[mid]
    # Momentum shift: was rising (vel_first > 0), now falling (vel_second < 0)
    return vel_first > 0 and vel_second < 0


# ═══════════════════════════════════════════════════════════════════════════════
# Detection — V4 Earlier-Entry SHORT
# ═══════════════════════════════════════════════════════════════════════════════

def detect_accel_300_v4_short(token: str, prices: list, params: dict = None) -> Optional[dict]:
    """Detect SHORT momentum — fires BEFORE the drop (earlier than v3).

    v4 improvements over v3:
      - Lower gap acceleration threshold (0.10 vs 0.20)
      - Volume spike detection (smart money selling early)
      - Price at resistance rejection
      - RSI bearish divergence
      - Momentum shift detection
    """
    # Apply regime-specific overrides
    _p = params or {}
    MIN_GAP = _p.get('ACCEL_300_V4_SHORT_MIN_GAP', ACCEL_300_V4_SHORT_MIN_GAP)
    MAX_GAP = _p.get('ACCEL_300_V4_SHORT_MAX_GAP', ACCEL_300_V4_SHORT_MAX_GAP)
    MIN_GAP_ACCEL = _p.get('ACCEL_300_V4_SHORT_MIN_GAP_ACCEL', ACCEL_300_V4_SHORT_MIN_GAP_ACCEL)
    CHASE_DROP_MAX = _p.get('ACCEL_300_V4_SHORT_CHASE_DROP_MAX', ACCEL_300_V4_SHORT_CHASE_DROP_MAX)
    COOLDOWN_BARS = _p.get('ACCEL_300_V4_SHORT_COOLDOWN_BARS', ACCEL_300_V4_SHORT_COOLDOWN_BARS)
    VOLUME_MULT = _p.get('ACCEL_300_V4_SHORT_VOLUME_MULT', ACCEL_300_V4_SHORT_VOLUME_MULT)
    CONF_BASE = _p.get('ACCEL_300_V4_SHORT_CONF_BASE', ACCEL_300_V4_SHORT_CONF_BASE)

    min_rows = PERIOD + max(V4_GAP_ACCEL_WINDOW, V4_SLOPE_WINDOW, 10) + 10
    if len(prices) < min_rows:
        return None

    closes = [float(p['price']) for p in prices]

    ema300 = _ema_series(closes, PERIOD)
    gap_pcts = [
        None if ema is None or ema == 0 else (price - ema) / ema * 100.0
        for price, ema in zip(closes, ema300)
    ]

    latest_idx = len(closes) - 1
    latest_ema = ema300[latest_idx]
    gap_now = gap_pcts[latest_idx]
    if latest_ema is None or gap_now is None:
        return None

    # ── SHORT only — price must be below EMA300 ────────────────────────────
    if gap_now >= 0:
        return None

    abs_gap = abs(gap_now)

    # ── FILTER 1: Gap in valid range ────────────────────────────────────────
    if abs_gap < MIN_GAP or abs_gap > MAX_GAP:
        return None

    # ── FILTER 2: Gap acceleration (10-bar window, must be negative for SHORT) ─
    accel_start = latest_idx - V4_GAP_ACCEL_WINDOW
    if accel_start < 0:
        return None
    gap_then = gap_pcts[accel_start]
    if gap_then is None:
        return None
    gap_acceleration = gap_now - gap_then  # negative = gap widening for SHORT

    if gap_acceleration > -MIN_GAP_ACCEL:
        return None

    # ── FILTER 3: Fresh cross detection ─────────────────────────────────────
    cross_bar = None
    for idx in range(latest_idx, PERIOD - 1, -1):
        prev_idx = idx - 1
        if prev_idx < 0 or ema300[idx] is None or ema300[prev_idx] is None:
            continue
        crossed = closes[idx] < ema300[idx] and closes[prev_idx] >= ema300[prev_idx]
        if crossed:
            cross_bar = idx
            break
    bars_since_cross = latest_idx - cross_bar if cross_bar is not None else 999
    fresh_cross = bars_since_cross <= V4_FRESH_CROSS_BARS

    # ── FILTER 4: Price velocity (must be negative for SHORT) ───────────────
    if latest_idx < V4_VELOCITY_WINDOW:
        return None
    price_velocity = closes[latest_idx] - closes[latest_idx - V4_VELOCITY_WINDOW]
    price_epsilon = max(abs(closes[latest_idx]) * 1e-12, 1e-12)

    if price_velocity >= price_epsilon:
        return None  # price rising — not momentum

    # ── FILTER 4b: Minimum velocity magnitude (0.03% — earlier than v3 0.05%)
    min_velocity = abs(closes[latest_idx]) * V4_MIN_VELOCITY
    if abs(price_velocity) < min_velocity:
        return None  # price barely moving — no conviction

    # ── FILTER 5: Persistence — price must stay below EMA ───────────────────
    persist_start = latest_idx - V4_PERSISTENCE_BARS + 1
    if persist_start < 0:
        return None
    for idx in range(persist_start, latest_idx + 1):
        ema = ema300[idx]
        if ema is None:
            return None
        if closes[idx] >= ema:
            return None

    # ── FILTER 6: Linear regression slope (must be negative for SHORT) ──────
    slope_window = min(V4_SLOPE_WINDOW, len(closes))
    if slope_window >= 2:
        slope_chunk = closes[-slope_window:]
        x_mean = (slope_window - 1) / 2.0
        y_mean = sum(slope_chunk) / slope_window
        denominator = sum((x - x_mean) ** 2 for x in range(slope_window))
        if denominator > 0 and y_mean != 0:
            numerator = sum(
                (x - x_mean) * (slope_chunk[x] - y_mean)
                for x in range(slope_window)
            )
            pct_slope = (numerator / denominator) / y_mean * 100.0
            if pct_slope >= -V4_MIN_SLOPE_PCT:
                return None

    # ── FILTER 7: RSI — don't enter when oversold (bounce risk) ────────────
    rsi = _rsi(closes, 14)
    if rsi < V4_RSI_MIN:
        return None  # oversold — bounce likely imminent
    if rsi > V4_RSI_MAX:
        return None  # too strong — may reverse

    # ── FILTER 8: Chase block — don't chase extended drops ──────────────────
    if latest_idx >= 30:
        move_30m = (closes[latest_idx] - closes[latest_idx - 30]) / closes[latest_idx - 30] * 100
        if move_30m < -CHASE_DROP_MAX and rsi < V4_CHASE_RSI_MIN:
            return None  # chasing extended drop — bounce imminent

    # ── FILTER 9: Gap velocity must confirm (not narrowing for SHORT) ───────
    if latest_idx < 3:
        return None
    gap_prev = gap_pcts[latest_idx - 1]
    if gap_prev is None:
        return None
    gap_velocity = gap_now - gap_prev
    if gap_velocity > 0.05:
        return None  # gap narrowing — momentum fading

    # ── FILTER 10: Multi-bar gap confirmation ───────────────────────────────
    if latest_idx >= 3:
        gap_3_ago = gap_pcts[latest_idx - 3]
        if gap_3_ago is not None:
            gap_change_3 = gap_now - gap_3_ago
            if gap_change_3 > 0.05:
                return None  # gap narrowing over 3 bars — momentum fading

    # ── FILTER 11: Fresh cross gap check ───────────────────────────────────
    if fresh_cross and abs_gap < V4_FRESH_CROSS_MIN_GAP:
        return None  # even fresh cross needs SOME gap

    # ══════════════════════════════════════════════════════════════════════════
    # V4 BONUS FILTERS — these don't block, they add confidence
    # ══════════════════════════════════════════════════════════════════════════

    vol_spike = False
    resistance_rejection = False
    rsi_divergence = False
    momentum_shift = False

    # ── BONUS 1: Volume spike (20%+ increase in last 5 bars) ───────────────
    volumes = _get_volume_series(token, 30)
    if volumes:
        vol_spike = _check_volume_spike(volumes)

    # ── BONUS 2: Price at resistance (touched EMA300 and rejected) ──────────
    resistance_rejection = _check_price_at_resistance(closes, ema300)

    # ── BONUS 3: RSI divergence (bearish: price higher high + RSI lower high) ─
    rsi_series = _rsi_series(closes, 14)
    rsi_divergence = _check_rsi_divergence(closes, rsi_series)

    # ── BONUS 4: Momentum shift (rising → falling) ──────────────────────────
    momentum_shift = _check_momentum_shift(closes)

    return {
        'direction': 'SHORT',
        'gap_pct': round(gap_now, 4),
        'gap_acceleration': round(gap_acceleration, 4),
        'gap_velocity': round(gap_velocity, 4),
        'price_velocity': price_velocity,
        'bars_since_cross': bars_since_cross,
        'fresh_cross': fresh_cross,
        'rsi': round(rsi, 1),
        'price': closes[latest_idx],
        # v4 bonuses
        'vol_spike': vol_spike,
        'resistance_rejection': resistance_rejection,
        'rsi_divergence': rsi_divergence,
        'momentum_shift': momentum_shift,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_accel_300_v4_short_signals(prices_dict: dict) -> int:
    """Scan tokens for accel_300_v4_short (earlier-entry SHORT) signals."""
    from hermes_constants import (
        ACCEL_300_V4_SHORT_ENABLED,
        SHORT_BLACKLIST,
    )
    if not ACCEL_300_V4_SHORT_ENABLED:
        return 0

    from position_manager import get_open_positions as _get_open_pos
    from hyperliquid_exchange import is_delisted
    from signals.fast_momentum import recent_trade_exists, MIN_TRADE_INTERVAL_MINUTES

    open_pos = {p['token']: p['direction'] for p in _get_open_pos()}
    added = 0

    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue
        price = data.get('price')
        if not price or price <= 0:
            continue
        if token.upper() in open_pos:
            continue
        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
            continue
        if is_delisted(token.upper()):
            continue
        if price_age_minutes(token) > 10:
            continue

        prices = _get_1m_prices(token)
        if not prices or len(prices) < PERIOD + 30:
            continue

        # Get regime-specific parameter overrides
        token_params = _get_token_params(token)

        sig = detect_accel_300_v4_short(token, prices, params=token_params)
        if sig is None:
            continue

        # Direct cooldown check — fail-closed (block on error)
        _conn = None
        try:
            import sqlite3 as _sqlite3
            _conn = _sqlite3.connect(_RUNTIME_DB, timeout=5)
            _cur = _conn.cursor()
            _cur.execute("""
                SELECT created_at FROM signals
                WHERE token = ? AND direction = 'SHORT' AND source = ?
                ORDER BY created_at DESC LIMIT 1
            """, (token.upper(), SOURCE))
            _last = _cur.fetchone()
            if _last:
                from datetime import datetime as _dt
                _last_ts = _dt.fromisoformat(_last[0])
                _elapsed = (_dt.now() - _last_ts).total_seconds() / 60
                if _elapsed < token_params.get('ACCEL_300_V4_SHORT_COOLDOWN_BARS', V4_COOLDOWN_BARS):
                    continue  # Still in cooldown
        except Exception as e:
            print(f"  [accel-300-v4-short] cooldown check FAILED for {token}: {e} — BLOCKING", flush=True)
            continue  # Fail-closed: block signal on DB error
        finally:
            if _conn:
                _conn.close()

        # Blacklist guard
        if token.upper() in SHORT_BLACKLIST:
            continue

        # Volume confirmation
        if not _check_volume(token):
            continue

        # Phase filter
        try:
            from hermes_constants import PHASE_ENTRY_FILTER_ENABLED
            if PHASE_ENTRY_FILTER_ENABLED:
                from tpsl_utils import _get_current_phase
                phase = _get_current_phase(token)
                V4_ALLOWED_PHASES = {'accelerating', 'trending', 'building'}
                if phase and phase not in V4_ALLOWED_PHASES:
                    continue
        except (ImportError, Exception):
            pass

        # Confidence: base on gap strength + acceleration + RSI + v4 bonuses
        conf_base = token_params.get('ACCEL_300_V4_SHORT_CONF_BASE', V4_CONF_BASE)
        gap_bonus = min(20, (abs(sig['gap_pct']) - V4_MIN_GAP) * 10)
        accel_bonus = min(15, abs(sig['gap_acceleration']) * 100)
        fresh_bonus = 8 if sig.get('fresh_cross') else 0
        # RSI bonus: sweet spot is 40-60
        rsi_bonus = 5 if 40 <= sig['rsi'] <= 60 else 0
        # v4 bonuses
        vol_spike_bonus = 5 if sig.get('vol_spike') else 0
        resistance_bonus = 5 if sig.get('resistance_rejection') else 0
        divergence_bonus = 5 if sig.get('rsi_divergence') else 0
        momentum_bonus = 3 if sig.get('momentum_shift') else 0

        confidence = int(min(V4_CONF_CAP,
            conf_base + gap_bonus + accel_bonus + fresh_bonus + rsi_bonus
            + vol_spike_bonus + resistance_bonus + divergence_bonus + momentum_bonus))
        confidence = max(V4_CONF_FLOOR, confidence)

        signal_price = float(sig['price'])

        if DRY_RUN:
            bonuses = []
            if sig.get('vol_spike'): bonuses.append('vol_spike')
            if sig.get('resistance_rejection'): bonuses.append('resist_rej')
            if sig.get('rsi_divergence'): bonuses.append('rsi_div')
            if sig.get('momentum_shift'): bonuses.append('mom_shift')
            bonus_str = f" [{','.join(bonuses)}]" if bonuses else ""
            _log(f"  [DRY] SHORT-accel-300-v4-short {token:8s} conf={confidence:.0f}% "
                  f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                  f"accel={sig['gap_acceleration']:.3f}% "
                  f"gap_vel={sig['gap_velocity']:.3f}% "
                  f"rsi={sig['rsi']:.1f}{bonus_str} "
                  f"[{SOURCE}]")
            continue

        # Staleness check — verify gap is still valid at current price
        current_ema = _ema_series([float(p['price']) for p in prices], PERIOD)[-1]
        if current_ema and current_ema > 0:
            current_gap = (price - current_ema) / current_ema * 100
            if current_gap >= 0:
                continue  # gap flipped positive — stale
            abs_current_gap = abs(current_gap)
            if abs_current_gap < V4_MIN_GAP or abs_current_gap > V4_MAX_GAP:
                continue

        try:
            sid = add_signal(
                token=token.upper(),
                direction='SHORT',
                signal_type=SIGNAL_TYPE,
                source=SOURCE,
                confidence=confidence,
                value=float(sig['gap_acceleration']),
                price=signal_price,
                exchange='hyperliquid',
                timeframe='1m',
                z_score=None,
                z_score_tier=None,
            )
            if sid:
                added += 1
                cd_hours = token_params.get('ACCEL_300_V4_SHORT_COOLDOWN_BARS', V4_COOLDOWN_BARS) / 60.0
                set_cooldown(token, 'SHORT', hours=cd_hours)
                bonuses = []
                if sig.get('vol_spike'): bonuses.append('vol_spike')
                if sig.get('resistance_rejection'): bonuses.append('resist_rej')
                if sig.get('rsi_divergence'): bonuses.append('rsi_div')
                if sig.get('momentum_shift'): bonuses.append('mom_shift')
                bonus_str = f" [{','.join(bonuses)}]" if bonuses else ""
                _log(f"  SHORT-accel-300-v4-short {token:8s} conf={confidence:.0f}% "
                      f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                      f"accel={sig['gap_acceleration']:.3f}% "
                      f"gap_vel={sig['gap_velocity']:.3f}% "
                      f"rsi={sig['rsi']:.1f}{bonus_str} "
                      f"[{SOURCE}]")
        except Exception as e:
            print(f"[accel-300-v4-short] add_signal error for {token}: {e}")

    return added


# ═══════════════════════════════════════════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    from signal_schema import init_db

    conn = None
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT DISTINCT token FROM price_history
            WHERE timestamp > ?
            ORDER BY token
        """, (int(time.time()) - 600,))
        tokens = [r[0] for r in c.fetchall()]
    finally:
        if conn:
            conn.close()

    prices = {}
    conn = None
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT token, price FROM price_history
            WHERE (token, timestamp) IN (
                SELECT token, MAX(timestamp) FROM price_history
                WHERE timestamp > ?
                GROUP BY token
            )
        """, (int(time.time()) - 600,))
        for row in c.fetchall():
            prices[row[0]] = {'price': row[1]}
    finally:
        if conn:
            conn.close()

    mode = "DRY" if DRY_RUN else "LIVE"
    print(f"[accel-300-v4-short] Testing on {len(prices)} tokens ({mode} mode)...")
    init_db()
    n = scan_accel_300_v4_short_signals(prices)
    print(f"[accel-300-v4-short] Done. {n} signals emitted.")


# ═══════════════════════════════════════════════════════════════════════════════
# signals_runner entry point
# ═══════════════════════════════════════════════════════════════════════════════

def run(prices_dict=None):
    """Entry point for signals_runner."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_accel_300_v4_short_signals(prices_dict)
