#!/usr/bin/env python3
"""Accel-300 V2 LONG — Strong Trend Momentum Signal (LONG-only).

Branched from accel_300_v2.py to allow independent LONG tuning.
Catches accelerating moves where the gap ABOVE EMA300 is large AND widening.

LONG fires when:
  1. Price above EMA300 with gap >= 1.5%
  2. Gap is accelerating (widening over 10-bar window)
  3. Price velocity positive (price moving up)
  4. Price persisted above EMA for 3+ bars (not a cross wick)
  5. Linear regression slope positive (trending)
  6. 1h trend must be BULLISH or NEUTRAL
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

# ── LONG-specific constants ──────────────────────────────────────────────────
# All tunables in hermes_constants.py (ACCEL_300_V2_LONG_*)
# These are local fallbacks / internal implementation details
V2_MIN_GAP_ACCEL = 0.20        # min gap acceleration (positive = widening for LONG)
V2_GAP_ACCEL_WINDOW = 10       # bars to measure gap acceleration
V2_VELOCITY_WINDOW = 5         # bars to measure price velocity
V2_PERSISTENCE_BARS = 3        # min bars price must stay above EMA
V2_VOLUME_LOOKBACK = 30        # bars for average volume
V2_VOLUME_MULT = 1.0           # volume must be >= average
V2_COOLDOWN_BARS = 15          # cooldown between signals per token
V2_LOOKBACK_1M = 700           # 1m prices to fetch
V2_SLOPE_WINDOW = 20           # bars for linear regression slope
V2_MIN_SLOPE_PCT = 0.0005      # min slope % per bar (positive for LONG)
V2_MIN_GAP_PCT = 1.5           # min gap % for confidence bonus
V2_FRESH_CROSS_BARS = 8        # max bars since cross to qualify for fresh entry
V2_FRESH_CROSS_MIN_GAP = 0.50  # min gap for fresh cross entry

# Direction-specific gap thresholds (from hermes_constants.py)
from hermes_constants import (
    ACCEL_300_V2_LONG_MIN_GAP, ACCEL_300_V2_LONG_MAX_GAP,
)

PERIOD = 300  # EMA300 period
DRY_RUN = '--dry' in sys.argv

SIGNAL_TYPE = 'accel_300_v2_long'
SOURCE = 'accel-300-v2-long'


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
# Data fetch
# ═══════════════════════════════════════════════════════════════════════════════

def _get_1m_prices(token: str, lookback: int = V2_LOOKBACK_1M) -> list:
    """Fetch 1m close prices from price_history, oldest first."""
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
        print(f"  [accel-300-v2-long] price_history error for {token}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def _get_1h_trend(token: str) -> str:
    """Check 1H EMA trend. Returns 'BULLISH', 'BEARISH', or 'NEUTRAL'."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_1h
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT 60
        """, (token.upper(),))
        rows = cur.fetchall()
        if not rows or len(rows) < 50:
            return 'NEUTRAL'
        closes = [r[0] for r in reversed(rows)]

        def ema(data, period):
            k = 2.0 / (period + 1)
            val = data[0]
            for v in data[1:]:
                val = v * k + val * (1.0 - k)
            return val

        ema20 = ema(closes, 20)
        ema50 = ema(closes, 50)
        if ema50 == 0:
            return 'NEUTRAL'
        spread = abs(ema20 - ema50) / ema50 * 100
        if spread < 0.1:
            return 'NEUTRAL'
        return 'BULLISH' if ema20 > ema50 else 'BEARISH'
    except Exception:
        return 'NEUTRAL'
    finally:
        if conn:
            conn.close()


def _check_volume(token: str) -> bool:
    """Check if volume is available and reasonable. Returns True if OK."""
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
        """, (token.upper(), V2_VOLUME_LOOKBACK))
        rows = c.fetchall()
        volumes = [r[0] for r in rows if r[0] is not None]

        if not volumes or len(volumes) < 10:
            return True  # no data — don't block

        avg_vol = sum(volumes) / len(volumes)
        if avg_vol <= 0:
            return True  # stale data — don't block

        return volumes[-1] >= avg_vol * V2_VOLUME_MULT
    except Exception:
        return True  # on error, don't block
    finally:
        if conn:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Detection — LONG-only
# ═══════════════════════════════════════════════════════════════════════════════

def detect_accel_300_v2_long(token: str, prices: list) -> Optional[dict]:
    """Detect strong LONG momentum — gap above EMA300 large AND accelerating.

    LONG fires when:
      1. Price above EMA300 with gap >= 1.5%
      2. Gap is accelerating (widening over 10-bar window)
      3. Price velocity positive (price moving up)
      4. Price persisted above EMA for 3+ bars (not a cross wick)
      5. Linear regression slope positive (trending)
    """
    min_rows = PERIOD + max(V2_GAP_ACCEL_WINDOW, V2_SLOPE_WINDOW, 10) + 10
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

    # ── LONG only — price must be above EMA300 ─────────────────────────────
    if gap_now <= 0:
        return None

    abs_gap = gap_now

    # ── FILTER 1: Gap in valid range ────────────────────────────────────────
    if abs_gap < ACCEL_300_V2_LONG_MIN_GAP or abs_gap > ACCEL_300_V2_LONG_MAX_GAP:
        return None

    # ── FILTER 2: Gap acceleration (10-bar window, must be positive) ────────
    accel_start = latest_idx - V2_GAP_ACCEL_WINDOW
    if accel_start < 0:
        return None
    gap_then = gap_pcts[accel_start]
    if gap_then is None:
        return None
    gap_acceleration = gap_now - gap_then  # positive = gap widening for LONG

    if gap_acceleration < V2_MIN_GAP_ACCEL:
        return None

    # ── FILTER 3: Fresh cross detection ─────────────────────────────────────
    cross_bar = None
    for idx in range(latest_idx, PERIOD - 1, -1):
        prev_idx = idx - 1
        if prev_idx < 0 or ema300[idx] is None or ema300[prev_idx] is None:
            continue
        crossed = closes[idx] > ema300[idx] and closes[prev_idx] <= ema300[prev_idx]
        if crossed:
            cross_bar = idx
            break
    bars_since_cross = latest_idx - cross_bar if cross_bar is not None else 999
    fresh_cross = bars_since_cross <= V2_FRESH_CROSS_BARS

    # ── FILTER 4: Price velocity (must be positive for LONG) ────────────────
    if latest_idx < V2_VELOCITY_WINDOW:
        return None
    price_velocity = closes[latest_idx] - closes[latest_idx - V2_VELOCITY_WINDOW]
    price_epsilon = max(abs(closes[latest_idx]) * 1e-12, 1e-12)

    if price_velocity <= -price_epsilon:
        return None  # price falling — not momentum

    # ── FILTER 4b: Minimum velocity magnitude ───────────────────────────────
    min_velocity = abs(closes[latest_idx]) * 0.0003
    if abs(price_velocity) < min_velocity:
        return None  # price barely moving — no conviction

    # ── FILTER 5: Persistence — price must stay above EMA ───────────────────
    persist_start = latest_idx - V2_PERSISTENCE_BARS + 1
    if persist_start < 0:
        return None
    for idx in range(persist_start, latest_idx + 1):
        ema = ema300[idx]
        if ema is None:
            return None
        if closes[idx] <= ema:
            return None

    # ── FILTER 6: Linear regression slope (must be positive for LONG) ───────
    slope_window = min(V2_SLOPE_WINDOW, len(closes))
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
            if pct_slope <= V2_MIN_SLOPE_PCT:
                return None

    # ── FILTER 7: Gap velocity must confirm (not narrowing for LONG) ────────
    if latest_idx < 3:
        return None
    gap_prev = gap_pcts[latest_idx - 1]
    if gap_prev is None:
        return None
    gap_velocity = gap_now - gap_prev
    # Allow small noise but gap should not be narrowing
    if gap_velocity < -0.05:
        return None  # gap narrowing — reversal risk

    # ── FILTER 8: Multi-bar gap confirmation ────────────────────────────────
    if latest_idx >= 3:
        gap_3_ago = gap_pcts[latest_idx - 3]
        if gap_3_ago is not None:
            gap_change_3 = gap_now - gap_3_ago
            if gap_change_3 < -0.05:
                return None  # gap narrowing over 3 bars — momentum fading

    # ── FILTER 9: Fresh cross gap check ─────────────────────────────────────
    if fresh_cross and abs_gap < V2_FRESH_CROSS_MIN_GAP:
        return None  # even fresh cross needs SOME gap

    return {
        'direction': 'LONG',
        'gap_pct': round(gap_now, 4),
        'gap_acceleration': round(gap_acceleration, 4),
        'gap_velocity': round(gap_velocity, 4),
        'price_velocity': price_velocity,
        'bars_since_cross': bars_since_cross,
        'fresh_cross': fresh_cross,
        'price': closes[latest_idx],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_accel_300_v2_long_signals(prices_dict: dict) -> int:
    """Scan tokens for accel_300_v2_long (strong trend momentum LONG) signals."""
    from hermes_constants import (
        ACCEL_300_V2_LONG_ENABLED,
        LONG_BLACKLIST,
    )
    if not ACCEL_300_V2_LONG_ENABLED:
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

        sig = detect_accel_300_v2_long(token, prices)
        if sig is None:
            continue

        if get_cooldown(token, direction='LONG'):
            continue

        # Blacklist guard
        if token.upper() in LONG_BLACKLIST:
            continue

        # 1h trend filter — must be BULLISH or NEUTRAL for LONG
        trend_1h = _get_1h_trend(token)
        if trend_1h == 'BEARISH':
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
                V2_ALLOWED_PHASES = {'accelerating', 'trending', 'building'}
                if phase and phase not in V2_ALLOWED_PHASES:
                    continue
        except (ImportError, Exception):
            pass

        # Confidence: base on gap strength + acceleration
        gap_bonus = min(20, (abs(sig['gap_pct']) - V2_MIN_GAP_PCT) * 10)
        accel_bonus = min(15, abs(sig['gap_acceleration']) * 100)
        trend_bonus = 5 if trend_1h != 'NEUTRAL' else 0
        fresh_bonus = 8 if sig.get('fresh_cross') else 0
        confidence = int(min(88, 62 + gap_bonus + accel_bonus + trend_bonus + fresh_bonus))
        confidence = max(60, confidence)

        signal_price = float(sig['price'])

        if DRY_RUN:
            _log(f"  [DRY] LONG-accel-300-v2-long {token:8s} conf={confidence:.0f}% "
                  f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                  f"accel={sig['gap_acceleration']:.3f}% "
                  f"gap_vel={sig['gap_velocity']:.3f}% "
                  f"trend_1h={trend_1h} [{SOURCE}]")
            continue

        # Staleness check — verify gap is still valid at current price
        current_ema = _ema_series([float(p['price']) for p in prices], PERIOD)[-1]
        if current_ema and current_ema > 0:
            current_gap = (price - current_ema) / current_ema * 100
            if current_gap <= 0:
                continue  # gap flipped negative — stale
            abs_current_gap = abs(current_gap)
            if abs_current_gap < ACCEL_300_V2_LONG_MIN_GAP or abs_current_gap > ACCEL_300_V2_LONG_MAX_GAP:
                continue

        try:
            sid = add_signal(
                token=token.upper(),
                direction='LONG',
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
                set_cooldown(token, 'LONG', hours=V2_COOLDOWN_BARS / 60.0)
                _log(f"  LONG-accel-300-v2-long {token:8s} conf={confidence:.0f}% "
                      f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                      f"accel={sig['gap_acceleration']:.3f}% "
                      f"gap_vel={sig['gap_velocity']:.3f}% "
                      f"trend_1h={trend_1h} [{SOURCE}]")
        except Exception as e:
            print(f"[accel-300-v2-long] add_signal error for {token}: {e}")

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
    print(f"[accel-300-v2-long] Testing on {len(prices)} tokens ({mode} mode)...")
    init_db()
    n = scan_accel_300_v2_long_signals(prices)
    print(f"[accel-300-v2-long] Done. {n} signals emitted.")


# ═══════════════════════════════════════════════════════════════════════════════
# signals_runner entry point
# ═══════════════════════════════════════════════════════════════════════════════

def run(prices_dict=None):
    """Entry point for signals_runner."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_accel_300_v2_long_signals(prices_dict)
