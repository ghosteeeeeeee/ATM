#!/usr/bin/env python3
"""Accel-300 V3 SHORT — Anti-Bottom-Catch Momentum Signal.

Branched from accel_300_v2_short to avoid "catching the bottom" losers.

THESIS:
  v2 fires when gap is large AND accelerating — but enters at the LOCAL BOTTOM
  of sharp drops, then gets stopped out on bounce.

  v3 adds:
  - RSI filter: don't enter when RSI is oversold (bounce risk)
  - Chase block: don't enter after price already dropped >2% in 30min
  - Volume confirmation: real drops have above-average volume (1.1x)
  - Staleness guards from v3 long (2-min candle freshness, gap staleness)
  - Tighter velocity magnitude (0.05% vs 0.03%)

ENTRY CONDITIONS:
  1. Price below EMA300 with gap >= 1.0% (trend established)
  2. Gap is accelerating (widening over 10-bar window)
  3. Price velocity negative with conviction (0.05% min)
  4. Price persisted below EMA for 3+ bars (not a cross wick)
  5. Linear regression slope negative (trending down)
  6. RSI not oversold (< 35) — avoid bounce risk
  7. Not chasing — don't enter after large 30m drops
  8. Volume confirms drop (>= 1.1x average)
  9. Staleness guards: 2-min candle freshness, gap staleness
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

# ── V3 SHORT constants (from hermes_constants.py) ────────────────────────────
from hermes_constants import (
    ACCEL_300_V3_SHORT_MIN_GAP,
    ACCEL_300_V3_SHORT_MAX_GAP,
    ACCEL_300_V3_SHORT_MIN_GAP_ACCEL,
    ACCEL_300_V3_SHORT_GAP_ACCEL_WINDOW,
    ACCEL_300_V3_SHORT_VELOCITY_WINDOW,
    ACCEL_300_V3_SHORT_MIN_VELOCITY,
    ACCEL_300_V3_SHORT_PERSISTENCE_BARS,
    ACCEL_300_V3_SHORT_SLOPE_WINDOW,
    ACCEL_300_V3_SHORT_MIN_SLOPE_PCT,
    ACCEL_300_V3_SHORT_RSI_MAX,
    ACCEL_300_V3_SHORT_RSI_MIN,
    ACCEL_300_V3_SHORT_CHASE_DROP_MAX,
    ACCEL_300_V3_SHORT_CHASE_RSI_MIN,
    ACCEL_300_V3_SHORT_VOLUME_LOOKBACK,
    ACCEL_300_V3_SHORT_VOLUME_MULT,
    ACCEL_300_V3_SHORT_COOLDOWN_BARS,
    ACCEL_300_V3_SHORT_LOOKBACK_1M,
    ACCEL_300_V3_SHORT_FRESH_CROSS_BARS,
    ACCEL_300_V3_SHORT_FRESH_CROSS_MIN_GAP,
    ACCEL_300_V3_SHORT_CONF_BASE,
    ACCEL_300_V3_SHORT_CONF_FLOOR,
    ACCEL_300_V3_SHORT_CONF_CAP,
)

# Aliases for shorter references in code
V3_SHORT_MIN_GAP = ACCEL_300_V3_SHORT_MIN_GAP
V3_SHORT_MAX_GAP = ACCEL_300_V3_SHORT_MAX_GAP
V3_SHORT_MIN_GAP_ACCEL = ACCEL_300_V3_SHORT_MIN_GAP_ACCEL
V3_SHORT_GAP_ACCEL_WINDOW = ACCEL_300_V3_SHORT_GAP_ACCEL_WINDOW
V3_SHORT_VELOCITY_WINDOW = ACCEL_300_V3_SHORT_VELOCITY_WINDOW
V3_SHORT_MIN_VELOCITY = ACCEL_300_V3_SHORT_MIN_VELOCITY
V3_SHORT_PERSISTENCE_BARS = ACCEL_300_V3_SHORT_PERSISTENCE_BARS
V3_SHORT_SLOPE_WINDOW = ACCEL_300_V3_SHORT_SLOPE_WINDOW
V3_SHORT_MIN_SLOPE_PCT = ACCEL_300_V3_SHORT_MIN_SLOPE_PCT
V3_SHORT_RSI_MAX = ACCEL_300_V3_SHORT_RSI_MAX
V3_SHORT_RSI_MIN = ACCEL_300_V3_SHORT_RSI_MIN
V3_SHORT_CHASE_DROP_MAX = ACCEL_300_V3_SHORT_CHASE_DROP_MAX
V3_SHORT_CHASE_RSI_MIN = ACCEL_300_V3_SHORT_CHASE_RSI_MIN
V3_SHORT_VOLUME_LOOKBACK = ACCEL_300_V3_SHORT_VOLUME_LOOKBACK
V3_SHORT_VOLUME_MULT = ACCEL_300_V3_SHORT_VOLUME_MULT
V3_SHORT_COOLDOWN_BARS = ACCEL_300_V3_SHORT_COOLDOWN_BARS
V3_SHORT_LOOKBACK_1M = ACCEL_300_V3_SHORT_LOOKBACK_1M
V3_SHORT_FRESH_CROSS_BARS = ACCEL_300_V3_SHORT_FRESH_CROSS_BARS
V3_SHORT_FRESH_CROSS_MIN_GAP = ACCEL_300_V3_SHORT_FRESH_CROSS_MIN_GAP
V3_SHORT_CONF_BASE = ACCEL_300_V3_SHORT_CONF_BASE
V3_SHORT_CONF_FLOOR = ACCEL_300_V3_SHORT_CONF_FLOOR
V3_SHORT_CONF_CAP = ACCEL_300_V3_SHORT_CONF_CAP

PERIOD = 300  # EMA300 period
DRY_RUN = '--dry' in sys.argv

SIGNAL_TYPE = 'accel_300_v3_short'
SOURCE = 'accel-300-v3-short-'


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
# RSI helper
# ═══════════════════════════════════════════════════════════════════════════════

def _rsi(closes: list, period: int = 14) -> float:
    """Compute RSI from closes. Returns 50 if insufficient data."""
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


# ═══════════════════════════════════════════════════════════════════════════════
# Data fetch — with staleness guards from v3 long
# ═══════════════════════════════════════════════════════════════════════════════

def _get_1m_prices(token: str, lookback: int = V3_SHORT_LOOKBACK_1M) -> list:
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
        print(f"  [accel-300-v3-short] price_history error for {token}: {e}")
        return []
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
        """, (token.upper(), V3_SHORT_VOLUME_LOOKBACK))
        rows = c.fetchall()
        volumes = [r[0] for r in rows if r[0] is not None]

        if not volumes or len(volumes) < 10:
            return True  # no data — don't block

        avg_vol = sum(volumes) / len(volumes)
        if avg_vol <= 0:
            return True  # stale data — don't block

        return volumes[-1] >= avg_vol * V3_SHORT_VOLUME_MULT
    except Exception:
        return True  # on error, don't block
    finally:
        if conn:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Detection — V3 Anti-Bottom-Catch SHORT
# ═══════════════════════════════════════════════════════════════════════════════

def detect_accel_300_v3_short(token: str, prices: list) -> Optional[dict]:
    """Detect strong SHORT momentum — avoids bottom-catching.

    v3 adds to v2:
      - RSI filter: don't enter when oversold (bounce risk)
      - Chase block: don't enter after large 30m drops
      - Tighter velocity (0.05% min vs 0.03%)
    """
    min_rows = PERIOD + max(V3_SHORT_GAP_ACCEL_WINDOW, V3_SHORT_SLOPE_WINDOW, 10) + 10
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
    if abs_gap < V3_SHORT_MIN_GAP or abs_gap > V3_SHORT_MAX_GAP:
        return None

    # ── FILTER 2: Gap acceleration (10-bar window, must be negative for SHORT) ─
    accel_start = latest_idx - V3_SHORT_GAP_ACCEL_WINDOW
    if accel_start < 0:
        return None
    gap_then = gap_pcts[accel_start]
    if gap_then is None:
        return None
    gap_acceleration = gap_now - gap_then  # negative = gap widening for SHORT

    if gap_acceleration > -V3_SHORT_MIN_GAP_ACCEL:
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
    fresh_cross = bars_since_cross <= V3_SHORT_FRESH_CROSS_BARS

    # ── FILTER 4: Price velocity (must be negative for SHORT) ───────────────
    if latest_idx < V3_SHORT_VELOCITY_WINDOW:
        return None
    price_velocity = closes[latest_idx] - closes[latest_idx - V3_SHORT_VELOCITY_WINDOW]
    price_epsilon = max(abs(closes[latest_idx]) * 1e-12, 1e-12)

    if price_velocity >= price_epsilon:
        return None  # price rising — not momentum

    # ── FILTER 4b: Minimum velocity magnitude (0.05% — stricter than v2) ────
    min_velocity = abs(closes[latest_idx]) * V3_SHORT_MIN_VELOCITY
    if abs(price_velocity) < min_velocity:
        return None  # price barely moving — no conviction

    # ── FILTER 5: Persistence — price must stay below EMA ───────────────────
    persist_start = latest_idx - V3_SHORT_PERSISTENCE_BARS + 1
    if persist_start < 0:
        return None
    for idx in range(persist_start, latest_idx + 1):
        ema = ema300[idx]
        if ema is None:
            return None
        if closes[idx] >= ema:
            return None

    # ── FILTER 6: Linear regression slope (must be negative for SHORT) ──────
    slope_window = min(V3_SHORT_SLOPE_WINDOW, len(closes))
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
            if pct_slope >= -V3_SHORT_MIN_SLOPE_PCT:
                return None

    # ── FILTER 7: RSI — don't enter when oversold (bounce risk) ────────────
    rsi = _rsi(closes, 14)
    if rsi < V3_SHORT_RSI_MIN:
        return None  # oversold — bounce likely imminent
    if rsi > V3_SHORT_RSI_MAX:
        return None  # too strong — may reverse

    # ── FILTER 8: Chase block — don't chase extended drops ──────────────────
    # Block entries after large downward moves (price already extended)
    if latest_idx >= 30:
        move_30m = (closes[latest_idx] - closes[latest_idx - 30]) / closes[latest_idx - 30] * 100
        if move_30m < -V3_SHORT_CHASE_DROP_MAX and rsi < V3_SHORT_CHASE_RSI_MIN:
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
    if fresh_cross and abs_gap < V3_SHORT_FRESH_CROSS_MIN_GAP:
        return None  # even fresh cross needs SOME gap

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
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_accel_300_v3_short_signals(prices_dict: dict) -> int:
    """Scan tokens for accel_300_v3_short (anti-bottom-catch SHORT) signals."""
    from hermes_constants import (
        ACCEL_300_V3_SHORT_ENABLED,
        SHORT_BLACKLIST,
    )
    if not ACCEL_300_V3_SHORT_ENABLED:
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

        sig = detect_accel_300_v3_short(token, prices)
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
                if _elapsed < V3_SHORT_COOLDOWN_BARS:
                    continue  # Still in cooldown
        except Exception as e:
            print(f"  [accel-300-v3-short] cooldown check FAILED for {token}: {e} — BLOCKING", flush=True)
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
                V3_ALLOWED_PHASES = {'accelerating', 'trending', 'building'}
                if phase and phase not in V3_ALLOWED_PHASES:
                    continue
        except (ImportError, Exception):
            pass

        # Confidence: base on gap strength + acceleration + RSI
        gap_bonus = min(20, (abs(sig['gap_pct']) - V3_SHORT_MIN_GAP) * 10)
        accel_bonus = min(15, abs(sig['gap_acceleration']) * 100)
        fresh_bonus = 8 if sig.get('fresh_cross') else 0
        # RSI bonus: sweet spot is 40-60 (not oversold, not too strong)
        rsi_bonus = 5 if 40 <= sig['rsi'] <= 60 else 0
        confidence = int(min(V3_SHORT_CONF_CAP,
            V3_SHORT_CONF_BASE + gap_bonus + accel_bonus + fresh_bonus + rsi_bonus))
        confidence = max(V3_SHORT_CONF_FLOOR, confidence)

        signal_price = float(sig['price'])

        if DRY_RUN:
            _log(f"  [DRY] SHORT-accel-300-v3-short {token:8s} conf={confidence:.0f}% "
                  f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                  f"accel={sig['gap_acceleration']:.3f}% "
                  f"gap_vel={sig['gap_velocity']:.3f}% "
                  f"rsi={sig['rsi']:.1f} "
                  f"[{SOURCE}]")
            continue

        # Staleness check — verify gap is still valid at current price
        current_ema = _ema_series([float(p['price']) for p in prices], PERIOD)[-1]
        if current_ema and current_ema > 0:
            current_gap = (price - current_ema) / current_ema * 100
            if current_gap >= 0:
                continue  # gap flipped positive — stale
            abs_current_gap = abs(current_gap)
            if abs_current_gap < V3_SHORT_MIN_GAP or abs_current_gap > V3_SHORT_MAX_GAP:
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
                set_cooldown(token, 'SHORT', hours=V3_SHORT_COOLDOWN_BARS / 60.0)
                _log(f"  SHORT-accel-300-v3-short {token:8s} conf={confidence:.0f}% "
                      f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                      f"accel={sig['gap_acceleration']:.3f}% "
                      f"gap_vel={sig['gap_velocity']:.3f}% "
                      f"rsi={sig['rsi']:.1f} "
                      f"[{SOURCE}]")
        except Exception as e:
            print(f"[accel-300-v3-short] add_signal error for {token}: {e}")

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
    print(f"[accel-300-v3-short] Testing on {len(prices)} tokens ({mode} mode)...")
    init_db()
    n = scan_accel_300_v3_short_signals(prices)
    print(f"[accel-300-v3-short] Done. {n} signals emitted.")


# ═══════════════════════════════════════════════════════════════════════════════
# signals_runner entry point
# ═══════════════════════════════════════════════════════════════════════════════

def run(prices_dict=None):
    """Entry point for signals_runner."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_accel_300_v3_short_signals(prices_dict)
