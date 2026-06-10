#!/usr/bin/env python3
"""
EMA300 Angle Signal — ema_angle.py

LONG: flat → steep transition (ema-angle+)
  • angle = arctan(Δprice_20 / price) in RADIANS (0.5-1.0 rad = 30°-45°)
  • was flat: angle < 0.5 rad (30°) for last 10 bars
  • now steep: angle >= 0.5 rad AND < 1.0 rad (30° to 45°, not past ceiling)
  • price must be above EMA300
  • Confluence required — never a solo signal

SHORT: angle <= p25 and falling (ema-angle-) — unchanged formula

Reference coin: PURR (flat-to-45° EMA300 angle transition ~48h ago, May 14 2026 ~03:00 EST)
"""

import math, sys, os
from typing import Optional

# ── imports from signal_schema ──────────────────────────────────────────────
# NOTE: signal_schema imports this module, so we lazy-import inside functions
# to avoid circular import at module load time.

# ── constants (loaded from hermes_constants) ────────────────────────────────
from hermes_constants import (
    EMA_ANGLE_LOOKBACK, EMA_ANGLE_SLOPE_PERIOD, EMA_ANGLE_SPEED_PERIOD,
    EMA_ANGLE_PERCENTILE_LONG, EMA_ANGLE_PERCENTILE_SHORT,
    EMA_ANGLE_STEEP_THRESHOLD_RAD, EMA_ANGLE_CEILING_RAD, EMA_ANGLE_FLAT_WINDOW,
    EMA_ANGLE_MIN_SPEED, EMA_ANGLE_MIN_BARS, EMA_ANGLE_COOLDOWN_MIN,
    EMA_ANGLE_ENABLED, EMA_ANGLE_PLUS_ENABLED, EMA_ANGLE_MINUS_ENABLED,
    EMA_ANGLE_CONFIDENCE_BASE, EMA_ANGLE_STEEP_BONUS_MAX,
    EMA_ANGLE_MOMENTUM_BONUS_MAX, EMA_ANGLE_RECENCY_BONUS_MAX,
)
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST

# ── signal identity ─────────────────────────────────────────────────────────
SIGNAL_TYPE = 'ema_angle'   # signal_type field in DB
SOURCE_LONG  = 'ema-angle+'   # source field for LONG
SOURCE_SHORT = 'ema-angle-'   # source field for SHORT

# ── debug flag ───────────────────────────────────────────────────────────────
DEBUG = os.environ.get('EMA_ANGLE_DEBUG', '0') == '1'


def _log(msg):
    if DEBUG:
        print(f"[ema-angle] {msg}", flush=True)


# ── EMA helper ────────────────────────────────────────────────────────────────
def _ema(values: list, period: int) -> list:
    if len(values) < period:
        return [None] * len(values)
    ema = [values[0]]
    k = 2 / (period + 1)
    for v in values[1:]:
        ema.append(v * k + ema[-1] * (1 - k))
    return ema


# ── data fetch ────────────────────────────────────────────────────────────────
def _get_1m_prices(token: str, lookback: int = None) -> list:
    """Fetch last N 1m closes from candles.db. Returns list of (ts, price)."""
    if lookback is None:
        lookback = EMA_ANGLE_LOOKBACK

    sys.path.insert(0, os.path.dirname(__file__))
    try:
        import sqlite3
    except ImportError:
        return []

    db_path = os.environ.get('CANDLES_DB', '/root/.hermes/data/candles.db')
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT ts, close FROM candles_1m
            WHERE token=?
            ORDER BY ts DESC LIMIT ?
        """, (token.upper(), lookback))
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return []
        # Return oldest first (reversed)
        return list(reversed([(r[0], r[1]) for r in rows]))
    except Exception as e:
        _log(f"_get_1m_prices error for {token}: {e}")
        return []


# ── angle detection ───────────────────────────────────────────────────────────
def detect_ema_angle(token: str, prices: list = None) -> Optional[dict]:
    """
    Compute EMA300 angle and speed. Fire signal if angle crosses threshold
    with confirming momentum.

    Angle = arctan(slope_20 / ema) in degrees — SIGNED.
      +angle = price above EMA, trending up (more positive = steeper up)
      -angle = price below EMA, trending down (more negative = steeper down)
      0°    = price at EMA, flat

    LONG:  angle crosses from near-0 (flat) into positive steep territory (>= p75), still rising.
    SHORT: angle crosses from near-0 (flat) into negative steep territory (<= p25), still falling.
    """
    if not EMA_ANGLE_ENABLED:
        return None

    if prices is None:
        prices = _get_1m_prices(token)
        if len(prices) < EMA_ANGLE_MIN_BARS:
            return None

    if len(prices) < EMA_ANGLE_MIN_BARS:
        return None

    closes = [p[1] for p in prices]

    # ── compute EMA300 ─────────────────────────────────────────────────────
    ema300 = _ema(closes, 300)
    if None in ema300:
        return None

    # ── compute angle: arctan(Δprice_20 / price) in RADIANS ─────────────────────
    # 0.5 rad = arctan(0.5) ≈ 30° (STEEP threshold for LONG)
    # 1.0 rad = arctan(1.0) = 45° (ceiling — don't fire into parabolic)
    # SHORT uses p25 percentile on same scale — no change needed there
    angles = []
    slope_period = EMA_ANGLE_SLOPE_PERIOD
    speed_period = EMA_ANGLE_SPEED_PERIOD

    for i in range(slope_period, len(closes)):
        delta = closes[i] - closes[i - slope_period]
        price = closes[i]
        if price <= 0:
            angles.append(0.0)
        else:
            # Signed angle — sign carries direction of the slope
            # +angle = price above EMA, trending up
            # -angle = price below EMA, trending down
            # abs(angle) = steepness regardless of direction
            # Using arctan(Δprice_20 / price) directly — natural 0-90° range
            angles.append(math.atan(delta / price))

    if len(angles) < speed_period + 5:
        return None

    # ── compute angle speed: rolling diff ──────────────────────────────────
    angle_speeds = []
    for i in range(speed_period, len(angles)):
        speed = angles[i] - angles[i - speed_period]
        angle_speeds.append((i, angles[i], speed))

    if not angle_speeds:
        return None

    # ── percentile thresholds (from angle history) ─────────────────────────
    valid_angles = angles[speed_period:]  # skip first speed_period to align
    sorted_angles = sorted(valid_angles)
    p25_idx = int(len(sorted_angles) * 0.25)
    p75_idx = int(len(sorted_angles) * 0.75)
    p25 = sorted_angles[p25_idx]
    p75 = sorted_angles[p75_idx]

    latest_idx, latest_angle, latest_speed = angle_speeds[-1]
    latest_ts = prices[latest_idx + speed_period][0]

    # ── LONG: flat → steep transition (0.5-1.0 rad = 30°-45°) ─────────────────
    # was flat: angle was < STEEP_THRESHOLD_RAD for last FLAT_WINDOW bars
    # is steep: angle now >= STEEP_THRESHOLD_RAD AND < CEILING_RAD
    # crossover: was below threshold, now above — the actual transition
    # accelerating: still gaining angle (not plateauing)
    price_above_ema = closes[-1] > ema300[-1]

    preflat_start = max(speed_period, latest_idx - EMA_ANGLE_FLAT_WINDOW)
    preflat_angles = angles[preflat_start:latest_idx]
    was_flat     = all(a < EMA_ANGLE_STEEP_THRESHOLD_RAD for a in preflat_angles)
    is_steep     = latest_angle >= EMA_ANGLE_STEEP_THRESHOLD_RAD and latest_angle < EMA_ANGLE_CEILING_RAD
    crossover    = all(angles[j] < EMA_ANGLE_STEEP_THRESHOLD_RAD for j in range(preflat_start, latest_idx))
    accelerating = latest_speed > EMA_ANGLE_MIN_SPEED

    _log(f"[ema-angle DEBUG] {token}: close={closes[-1]:.6f} ema300={ema300[-1]:.6f} "
         f"above={price_above_ema} angle={latest_angle:.6f} rad ({math.degrees(latest_angle):.2f}°) "
         f"speed={latest_speed:.6f} was_flat={was_flat} is_steep={is_steep}")

    if EMA_ANGLE_PLUS_ENABLED and price_above_ema and was_flat and is_steep and crossover and accelerating:
        # Steepness bonus: position between threshold (floor) and ceiling
        angle_range = EMA_ANGLE_CEILING_RAD - EMA_ANGLE_STEEP_THRESHOLD_RAD
        if angle_range > 0:
            steepness_pct = (latest_angle - EMA_ANGLE_STEEP_THRESHOLD_RAD) / angle_range
        else:
            steepness_pct = 0

        # Momentum bonus: speed relative to its own history
        speeds_only = [s for _, _, s in angle_speeds]
        speed_pct = 0
        if speeds_only:
            sorted_speeds = sorted(speeds_only)
            max_speed = sorted_speeds[-1]
            if max_speed > 0:
                speed_pct = min(1.0, latest_speed / max_speed)

        # Recency: how fresh is this signal
        speed_pos = latest_idx - speed_period
        bars_ago = len(angle_speeds) - 1 - speed_pos
        recency_pct = max(0, 1.0 - (bars_ago / 30.0))

        confidence = int(EMA_ANGLE_CONFIDENCE_BASE
                        + steepness_pct * EMA_ANGLE_STEEP_BONUS_MAX
                        + speed_pct * EMA_ANGLE_MOMENTUM_BONUS_MAX
                        + recency_pct * EMA_ANGLE_RECENCY_BONUS_MAX)
        confidence = max(50, min(92, confidence))

        return {
            'direction': 'LONG',
            'angle': latest_angle,
            'angle_radians': latest_angle,   # radians for T's reference
            'angle_degrees': math.degrees(latest_angle),
            'angle_speed': latest_speed,
            'steepness_pct': steepness_pct,
            'speed_pct': speed_pct,
            'recency_pct': recency_pct,
            'confidence': confidence,
            'ts': latest_ts,
            'price': closes[latest_idx + speed_period],
            'source': SOURCE_LONG,
            'signal_type': SIGNAL_TYPE,
        }

# ── SHORT: angle < 0 (crossed through flat into negative steep), speed < 0 ──
    if EMA_ANGLE_MINUS_ENABLED and latest_angle < 0 and latest_angle <= p25 and latest_speed < -EMA_ANGLE_MIN_SPEED:
        # flatness_pct: how far into the steep-down territory (more negative = steeper)
        # p25 is the boundary; as angle becomes more negative, we're deeper into the steep zone
        angle_range = max(valid_angles) - min(valid_angles)
        if angle_range > 0:
            flatness_pct = (p25 - latest_angle) / angle_range  # p25 more negative = steeper
            flatness_pct = max(0, flatness_pct)  # clamp in case latest_angle is deeply below p25
        else:
            flatness_pct = 0

        speeds_only = [abs(s) for _, _, s in angle_speeds]
        speed_pct = 0
        if speeds_only:
            sorted_speeds = sorted(speeds_only)
            max_speed = sorted_speeds[-1]
            if max_speed > 0:
                speed_pct = min(1.0, abs(latest_speed) / max_speed)

        bars_ago = len(angle_speeds) - 1 - latest_idx
        recency_pct = max(0, 1.0 - (bars_ago / 30.0))

        confidence = int(EMA_ANGLE_CONFIDENCE_BASE
                        + flatness_pct * EMA_ANGLE_STEEP_BONUS_MAX
                        + speed_pct * EMA_ANGLE_MOMENTUM_BONUS_MAX
                        + recency_pct * EMA_ANGLE_RECENCY_BONUS_MAX)
        confidence = max(50, min(92, confidence))

        return {
            'direction': 'SHORT',
            'angle': latest_angle,
            'angle_speed': latest_speed,
            'p25': p25,
            'p75': p75,
            'angle_range': angle_range,
            'steepness_pct': flatness_pct,
            'speed_pct': speed_pct,
            'recency_pct': recency_pct,
            'confidence': confidence,
            'ts': latest_ts,
            'price': closes[latest_idx + speed_period],
            'source': SOURCE_SHORT,
            'signal_type': SIGNAL_TYPE,
        }

    return None


# ── cooldown check (cached, no DB write) ─────────────────────────────────────
_last_signal_ts = {}  # token+direction → last signal timestamp (ms)


def _cooldown_ok(token: str, direction: str, now_ts: int) -> bool:
    key = f"{token}:{direction}"
    last = _last_signal_ts.get(key, 0)
    if (now_ts - last) < EMA_ANGLE_COOLDOWN_MIN * 60 * 1000:
        return False
    return True


def _mark_signal(token: str, direction: str, now_ts: int) -> None:
    """Call AFTER add_signal() succeeds to update in-memory cooldown."""
    _last_signal_ts[f"{token}:{direction}"] = now_ts


# ── main scan ─────────────────────────────────────────────────────────────────
def scan_ema_angle_signals(prices_dict: dict = None) -> int:
    """
    Scan all tokens in prices_dict for EMA angle signals.
    prices_dict: {TOKEN: [(ts, close), ...], ...}
    Returns count of signals added.
    """
    from signal_schema import add_signal, get_cooldown, price_age_minutes

    if not EMA_ANGLE_ENABLED:
        return 0

    added = 0

    # Get universe — use prices_dict keys or fallback to DB scan
    if prices_dict:
        tokens = list(prices_dict.keys())
    else:
        # Fallback: scan DB for tokens with recent 1m data
        import sqlite3
        db_path = os.environ.get('CANDLES_DB', '/root/.hermes/data/candles.db')
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            cur = conn.cursor()
            # Get tokens with activity in last 15 minutes
            cutoff_ts = int(os.environ.get('READY_BEFORE_TS', 0)) or (
                __import__('time').time() - 900
            )
            cur.execute("""
                SELECT DISTINCT token FROM candles_1m
                WHERE ts > ?
                ORDER BY ts DESC
            """, (cutoff_ts,))
            tokens = [r[0] for r in cur.fetchall()]
            conn.close()
        except Exception as e:
            _log(f"scan_ema_angle_signals: DB scan error: {e}")
            return 0

    for token in tokens:
        # ── blacklist guard ─────────────────────────────────────────────
        if token in SHORT_BLACKLIST or token in LONG_BLACKLIST:
            continue

        # ── staleness check ───────────────────────────────────────────────
        try:
            if price_age_minutes(token) > 5:
                continue
        except Exception:
            pass

        # ── get price data ────────────────────────────────────────────────
        # NOTE: prices_dict from get_all_latest_prices() only has {'price': float}
        # — not suitable for angle computation (needs 500 bars of 1m candles).
        # Always use _get_1m_prices which reads from candles.db directly.
        prices = _get_1m_prices(token)
        if len(prices) < EMA_ANGLE_MIN_BARS:
            continue

        # ── detect signal ─────────────────────────────────────────────────
        try:
            sig = detect_ema_angle(token, prices)
        except Exception as e:
            _log(f"detect_ema_angle error for {token}: {e}")
            continue

        if not sig:
            continue

        direction = sig['direction']
        source = sig['source']

        # ── cooldown check ───────────────────────────────────────────────
        now_ts = sig['ts']
        if not _cooldown_ok(token, direction, now_ts):
            _log(f"  {token} {direction}: cooldown active, skipping")
            continue

        # ── cooldown from DB (shared with other signals) ─────────────────
        try:
            cd = get_cooldown(token, direction)
            if cd and (now_ts / 1000 - cd) < EMA_ANGLE_COOLDOWN_MIN * 60:
                continue
        except Exception:
            pass

        price = sig['price']
        confidence = sig['confidence']

        _log(f"  {token} {direction} conf={confidence} "
             f"angle={sig['angle']:.6f} rad ({math.degrees(sig['angle']):.2f}°) "
             f"speed={sig['angle_speed']:.7f} price={price}")

        try:
            sid = add_signal(
                token=token.upper(),
                direction=direction,
                signal_type=SIGNAL_TYPE,
                source=source,
                confidence=confidence,
                value=float(sig['angle']),
                price=price,
                exchange='hyperliquid',
                timeframe='1m',
                z_score=None,
                z_score_tier=None,
            )
            if sid:
                added += 1
                _mark_signal(token, direction, now_ts)
        except Exception as e:
            _log(f"  add_signal error for {token}: {e}")

    return added


# ── standalone runner ─────────────────────────────────────────────────────────
def run(prices_dict=None):
    """Entry point for signals_runner.py"""
    added = scan_ema_angle_signals(prices_dict)
    if DEBUG or added > 0:
        print(f"[ema-angle] scan complete — {added} signals added", flush=True)
    return added


if __name__ == '__main__':
    run()