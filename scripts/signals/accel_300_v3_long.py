#!/usr/bin/env python3
"""Accel-300 V3 LONG — Pullback Entry into Established Trend.

Branched from accel_300_v2_long to fix the local-top entry problem.

THESIS:
  v2 fires when gap is ACCELERATING (widening) — this catches the spike
  but enters at the LOCAL TOP, then gets stopped out on retracement.

  v3 fires when price PULLS BACK to EMA after an established trend,
  then BOUNCES back up — entering at the dip, not the peak.

  Winners had: strong gap (≥2%), volume, trend alignment.
  Losers had: gap at local peak, no pullback confirmation, entered during spike.

ENTRY CONDITIONS:
  1. Price above EMA300 with gap ≥ 1.5% (trend established)
  2. Gap recently peaked and narrowed (pullback happened)
  3. Gap is re-expanding (bounce confirmed)
  4. Price velocity positive (bounce has momentum)
  5. Not after3+ consecutive green candles (avoid chasing)
  6. RSI not overbought (< 72)
  7. 15m trend must be BULLISH or NEUTRAL
  8. Linear regression slope positive (trending)
  9. Volume confirms bounce (≥ 1.1x average)
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

# ── V3 constants (from hermes_constants.py) ──────────────────────────────────
from hermes_constants import (
    ACCEL_300_V3_LONG_MIN_GAP,
    ACCEL_300_V3_LONG_MAX_GAP,
    ACCEL_300_V3_LONG_MIN_PULLBACK,
    ACCEL_300_V3_LONG_MAX_PULLBACK,
    ACCEL_300_V3_LONG_REEXPAND_MIN,
    ACCEL_300_V3_LONG_GAP_PEAK_WINDOW,
    ACCEL_300_V3_LONG_GAP_REEXPAND_WINDOW,
    ACCEL_300_V3_LONG_MIN_VELOCITY,
    ACCEL_300_V3_LONG_GREEN_CAP,
    ACCEL_300_V3_LONG_RSI_MAX,
    ACCEL_300_V3_LONG_RSI_MIN,
    ACCEL_300_V3_LONG_COOLDOWN_BARS,
    ACCEL_300_V3_LONG_LOOKBACK_1M,
    ACCEL_300_V3_LONG_SLOPE_WINDOW,
    ACCEL_300_V3_LONG_MIN_SLOPE_PCT,
    ACCEL_300_V3_LONG_PERSISTENCE_BARS,
    ACCEL_300_V3_LONG_VOLUME_LOOKBACK,
    ACCEL_300_V3_LONG_VOLUME_MULT,
    ACCEL_300_V3_LONG_CONF_BASE,
    ACCEL_300_V3_LONG_CONF_FLOOR,
    ACCEL_300_V3_LONG_CONF_CAP,
    ACCEL_300_V3_LONG_GAP_VELOCITY_THRESH,
    ACCEL_300_V3_LONG_VELOCITY_WINDOW,
    ACCEL_300_V3_LONG_GREEN_COUNT_WINDOW,
    ACCEL_300_V3_LONG_CONF_PULLBACK_MAX,
    ACCEL_300_V3_LONG_CONF_GAP_MAX,
    ACCEL_300_V3_LONG_CONF_REEXPAND_MAX,
    ACCEL_300_V3_LONG_CONF_TREND_BONUS,
    ACCEL_300_V3_LONG_CONF_FRESH_BONUS,
    ACCEL_300_V3_LONG_CONF_RSI_MIN,
    ACCEL_300_V3_LONG_CONF_RSI_MAX,
    ACCEL_300_V3_LONG_CONF_RSI_BONUS,
)

PERIOD = 300  # EMA300 period
DRY_RUN = '--dry' in sys.argv

SIGNAL_TYPE = 'accel_300_v3_long'
SOURCE = 'accel-300-v3-long+'


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
# Data fetch
# ═══════════════════════════════════════════════════════════════════════════════

def _get_1m_prices(token: str, lookback: int = ACCEL_300_V3_LONG_LOOKBACK_1M) -> list:
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
        print(f"  [accel-300-v3-long] price_history error for {token}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def _get_15m_trend(token: str) -> str:
    """Check 15M trend — price vs EMA20. Returns 'BULLISH', 'BEARISH', or 'NEUTRAL'."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_15m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT 30
        """, (token.upper(),))
        rows = cur.fetchall()
        if not rows or len(rows) < 20:
            return 'NEUTRAL'
        closes = [r[0] for r in reversed(rows)]

        def ema(data, period):
            k = 2.0 / (period + 1)
            val = data[0]
            for v in data[1:]:
                val = v * k + val * (1.0 - k)
            return val

        ema20 = ema(closes, 20)
        if ema20 == 0:
            return 'NEUTRAL'

        price = closes[-1]
        pct_above = (price - ema20) / ema20 * 100

        if pct_above > 0.1:
            return 'BULLISH'
        elif pct_above < -0.1:
            return 'BEARISH'
        else:
            return 'NEUTRAL'
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
        """, (token.upper(), ACCEL_300_V3_LONG_VOLUME_LOOKBACK))
        rows = c.fetchall()
        volumes = [r[0] for r in rows if r[0] is not None]

        if not volumes or len(volumes) < 10:
            return True  # no data — don't block

        avg_vol = sum(volumes) / len(volumes)
        if avg_vol <= 0:
            return True  # stale data — don't block

        return volumes[-1] >= avg_vol * ACCEL_300_V3_LONG_VOLUME_MULT
    except Exception:
        return True  # on error, don't block
    finally:
        if conn:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Detection — LONG-only Pullback Entry
# ═══════════════════════════════════════════════════════════════════════════════

def detect_accel_300_v3_long(token: str, prices: list) -> Optional[dict]:
    """Detect pullback entry into established LONG trend.

    v3 fires when:
      1. Price above EMA300 with gap ≥ 1.5% (trend established)
      2. Gap recently peaked and narrowed (pullback happened)
      3. Gap is re-expanding (bounce confirmed)
      4. Price velocity positive (bounce has momentum)
      5. Not chasing (not after3+ consecutive green candles)
      6. RSI not overbought
    """
    min_rows = PERIOD + max(ACCEL_300_V3_LONG_GAP_PEAK_WINDOW,
                            ACCEL_300_V3_LONG_SLOPE_WINDOW,
                            ACCEL_300_V3_LONG_PERSISTENCE_BARS, 20) + 10
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

    # ── FILTER 1: Price must be above EMA300 ──────────────────────────────
    if gap_now <= 0:
        return None

    # ── FILTER 2: Gap in valid range ───────────────────────────────────────
    if gap_now < ACCEL_300_V3_LONG_MIN_GAP or gap_now > ACCEL_300_V3_LONG_MAX_GAP:
        return None

    # ── FILTER 3: PULLBACK DETECTION — gap narrowed from recent peak ───────
    # Find the peak gap in the last N bars
    peak_start = latest_idx - ACCEL_300_V3_LONG_GAP_PEAK_WINDOW
    if peak_start < 0:
        peak_start = 0
    recent_gaps = [g for g in gap_pcts[peak_start:latest_idx+1] if g is not None]
    if len(recent_gaps) < 5:
        return None
    gap_peak = max(recent_gaps)

    # Pullback = gap narrowed from peak
    pullback = gap_peak - gap_now
    if pullback < ACCEL_300_V3_LONG_MIN_PULLBACK:
        return None  # no pullback — gap still near peak (chasing)
    if pullback > ACCEL_300_V3_LONG_MAX_PULLBACK:
        return None  # too much pullback — trend may be breaking

    # ── FILTER 4: RE-EXPANSION — gap is widening again (bounce confirmed) ──
    reexpand_start = latest_idx - ACCEL_300_V3_LONG_GAP_REEXPAND_WINDOW
    if reexpand_start < 0:
        reexpand_start = 0
    gap_at_reexpand_start = gap_pcts[reexpand_start]
    if gap_at_reexpand_start is None:
        return None
    reexpansion = gap_now - gap_at_reexpand_start
    if reexpansion < ACCEL_300_V3_LONG_REEXPAND_MIN:
        return None  # gap still narrowing — bounce not confirmed

    # ── FILTER 5: Price velocity positive (bounce has momentum) ────────────
    if latest_idx < ACCEL_300_V3_LONG_VELOCITY_WINDOW:
        return None
    price_velocity = closes[latest_idx] - closes[latest_idx - ACCEL_300_V3_LONG_VELOCITY_WINDOW]
    if price_velocity <= 0:
        return None  # price falling — no bounce

    # Minimum velocity magnitude
    min_velocity = abs(closes[latest_idx]) * ACCEL_300_V3_LONG_MIN_VELOCITY
    if abs(price_velocity) < min_velocity:
        return None  # price barely moving — no conviction

    # ── FILTER 6: Not chasing — cap consecutive green candles ──────────────
    green_count = 0
    for i in range(latest_idx, max(latest_idx - ACCEL_300_V3_LONG_GREEN_COUNT_WINDOW, 0), -1):
        if i > 0 and closes[i] > closes[i-1]:
            green_count += 1
        else:
            break
    if green_count > ACCEL_300_V3_LONG_GREEN_CAP:
        return None  #3+ consecutive greens — chasing the spike

    # ── FILTER 7: RSI not overbought ──────────────────────────────────────
    rsi = _rsi(closes, 14)
    if rsi > ACCEL_300_V3_LONG_RSI_MAX:
        return None  # overbought — pullback likely imminent
    if rsi < ACCEL_300_V3_LONG_RSI_MIN:
        return None  # too weak — no momentum

    # ── FILTER 8: Persistence — price must stay above EMA ──────────────────
    persist_start = latest_idx - ACCEL_300_V3_LONG_PERSISTENCE_BARS + 1
    if persist_start < 0:
        persist_start = 0
    for idx in range(persist_start, latest_idx + 1):
        ema = ema300[idx]
        if ema is None:
            return None
        if closes[idx] <= ema:
            return None

    # ── FILTER 9: Linear regression slope positive ─────────────────────────
    slope_window = min(ACCEL_300_V3_LONG_SLOPE_WINDOW, len(closes))
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
            if pct_slope <= ACCEL_300_V3_LONG_MIN_SLOPE_PCT:
                return None

    # ── FILTER 10: Fresh cross detection (bonus: earlier entry) ────────────
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
    fresh_cross = bars_since_cross <= 8

    # ── FILTER 11: Gap velocity must confirm (not narrowing) ───────────────
    if latest_idx < 3:
        return None
    gap_prev = gap_pcts[latest_idx - 1]
    if gap_prev is None:
        return None
    gap_velocity = gap_now - gap_prev
    # Allow noise but gap should not be narrowing significantly
    if gap_velocity < ACCEL_300_V3_LONG_GAP_VELOCITY_THRESH:
        return None  # gap narrowing — momentum fading

    # ── FILTER 12: Multi-bar gap confirmation ──────────────────────────────
    if latest_idx >= 3:
        gap_3_ago = gap_pcts[latest_idx - 3]
        if gap_3_ago is not None:
            gap_change_3 = gap_now - gap_3_ago
            if gap_change_3 < ACCEL_300_V3_LONG_GAP_VELOCITY_THRESH:
                return None  # gap narrowing over 3 bars — momentum fading

    return {
        'direction': 'LONG',
        'gap_pct': round(gap_now, 4),
        'gap_peak': round(gap_peak, 4),
        'pullback': round(pullback, 4),
        'reexpansion': round(reexpansion, 4),
        'gap_velocity': round(gap_velocity, 4),
        'price_velocity': price_velocity,
        'bars_since_cross': bars_since_cross,
        'fresh_cross': fresh_cross,
        'rsi': round(rsi, 1),
        'green_count': green_count,
        'price': closes[latest_idx],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_accel_300_v3_long_signals(prices_dict: dict) -> int:
    """Scan tokens for accel_300_v3_long (pullback entry LONG) signals."""
    from hermes_constants import (
        ACCEL_300_V3_LONG_ENABLED,
        LONG_BLACKLIST,
    )
    if not ACCEL_300_V3_LONG_ENABLED:
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

        sig = detect_accel_300_v3_long(token, prices)
        if sig is None:
            continue

        # Direct cooldown check
        _conn = None
        try:
            import sqlite3 as _sqlite3
            _conn = _sqlite3.connect(_RUNTIME_DB, timeout=5)
            _cur = _conn.cursor()
            _cur.execute("""
                SELECT created_at FROM signals
                WHERE token = ? AND direction = 'LONG' AND source = ?
                ORDER BY created_at DESC LIMIT 1
            """, (token.upper(), SOURCE))
            _last = _cur.fetchone()
            if _last:
                from datetime import datetime as _dt
                _last_ts = _dt.fromisoformat(_last[0])
                _elapsed = (_dt.now() - _last_ts).total_seconds() / 60
                if _elapsed < ACCEL_300_V3_LONG_COOLDOWN_BARS:
                    continue  # Still in cooldown
        except Exception:
            pass  # On error, don't block
        finally:
            if _conn:
                _conn.close()

        # Blacklist guard
        if token.upper() in LONG_BLACKLIST:
            continue

        # 15m trend filter — must be BULLISH or NEUTRAL for LONG
        trend_15m = _get_15m_trend(token)
        if trend_15m == 'BEARISH':
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

        # Confidence: base on pullback quality + gap strength
        pullback_quality = min(ACCEL_300_V3_LONG_CONF_PULLBACK_MAX, sig['pullback'] * 20)
        gap_bonus = min(ACCEL_300_V3_LONG_CONF_GAP_MAX, (sig['gap_pct'] - ACCEL_300_V3_LONG_MIN_GAP) * 5)
        reexpand_bonus = min(ACCEL_300_V3_LONG_CONF_REEXPAND_MAX, sig['reexpansion'] * 100)
        trend_bonus = ACCEL_300_V3_LONG_CONF_TREND_BONUS if trend_15m != 'NEUTRAL' else 0
        fresh_bonus = ACCEL_300_V3_LONG_CONF_FRESH_BONUS if sig.get('fresh_cross') else 0
        rsi_bonus = ACCEL_300_V3_LONG_CONF_RSI_BONUS if ACCEL_300_V3_LONG_CONF_RSI_MIN <= sig['rsi'] <= ACCEL_300_V3_LONG_CONF_RSI_MAX else 0
        confidence = int(min(
            ACCEL_300_V3_LONG_CONF_CAP,
            ACCEL_300_V3_LONG_CONF_BASE + pullback_quality + gap_bonus + reexpand_bonus + trend_bonus + fresh_bonus + rsi_bonus
        ))
        confidence = max(ACCEL_300_V3_LONG_CONF_FLOOR, confidence)

        signal_price = float(sig['price'])

        if DRY_RUN:
            _log(f"  [DRY] LONG-accel-300-v3-long {token:8s} conf={confidence:.0f}% "
                  f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                  f"peak={sig['gap_peak']:.3f}% pullback={sig['pullback']:.3f}% "
                  f"reexpand={sig['reexpansion']:.3f}% rsi={sig['rsi']:.1f} "
                  f"greens={sig['green_count']} trend_15m={trend_15m} [{SOURCE}]")
            continue

        # Staleness check — verify gap is still valid at current price
        current_ema = _ema_series([float(p['price']) for p in prices], PERIOD)[-1]
        if current_ema and current_ema > 0:
            current_gap = (price - current_ema) / current_ema * 100
            if current_gap <= 0:
                continue  # gap flipped negative — stale
            abs_current_gap = abs(current_gap)
            if abs_current_gap < ACCEL_300_V3_LONG_MIN_GAP or abs_current_gap > ACCEL_300_V3_LONG_MAX_GAP:
                continue

        try:
            sid = add_signal(
                token=token.upper(),
                direction='LONG',
                signal_type=SIGNAL_TYPE,
                source=SOURCE,
                confidence=confidence,
                value=float(sig['pullback']),
                price=signal_price,
                exchange='hyperliquid',
                timeframe='1m',
                z_score=None,
                z_score_tier=None,
            )
            if sid:
                added += 1
                set_cooldown(token, 'LONG', hours=ACCEL_300_V3_LONG_COOLDOWN_BARS / 60.0)
                _log(f"  LONG-accel-300-v3-long {token:8s} conf={confidence:.0f}% "
                      f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                      f"peak={sig['gap_peak']:.3f}% pullback={sig['pullback']:.3f}% "
                      f"reexpand={sig['reexpansion']:.3f}% rsi={sig['rsi']:.1f} "
                      f"greens={sig['green_count']} trend_15m={trend_15m} [{SOURCE}]")
        except Exception as e:
            print(f"[accel-300-v3-long] add_signal error for {token}: {e}")

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
    print(f"[accel-300-v3-long] Testing on {len(prices)} tokens ({mode} mode)...")
    init_db()
    n = scan_accel_300_v3_long_signals(prices)
    print(f"[accel-300-v3-long] Done. {n} signals emitted.")


# ═══════════════════════════════════════════════════════════════════════════════
# signals_runner entry point
# ═══════════════════════════════════════════════════════════════════════════════

def run(prices_dict=None):
    """Entry point for signals_runner."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_accel_300_v3_long_signals(prices_dict)
