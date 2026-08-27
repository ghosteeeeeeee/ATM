#!/usr/bin/env python3
"""Accel-300 V2 — Strong Trend Momentum Signal.

Catches accelerating moves where the gap from EMA300 is large AND widening fast.
Designed for moves like CHIP (gap 4% → 7.5% in 30 min with strong momentum).

V1 was dead (0% WR) because:
  - Position filter blocked signals at range highs (but for momentum, that IS the signal)
  - Too slow to enter (persistence-based, waited too long)
  - No multi-timeframe confirmation
  - No volume filter

V2 design:
  - Fires when gap is ALREADY large (>1.5%) AND accelerating (widening fast)
  - No position filter — being at range high IS the momentum signal
  - Multi-timeframe: 1h trend must align (EMA20 > EMA50 for LONG)
  - Volume confirmation — real moves have above-average volume
  - Gap acceleration: gap must be widening over 10-bar window
  - Price velocity: price must be moving in signal direction
  - Phase filter: only during accelerating/trending phases

LONG: price above EMA300, gap large and widening, 1h bullish, volume confirms
SHORT: price below EMA300, gap large and widening, 1h bearish, volume confirms
"""

import sys, os, sqlite3, time
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from signal_schema import add_signal, get_cooldown, price_age_minutes
from signal_gen import set_cooldown

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

# ── V2 Signal constants ──────────────────────────────────────────────────────
V2_MIN_GAP_PCT = 1.5           # min gap from EMA300 to fire — raised from 0.8 (too noisy)
V2_MAX_GAP_PCT = 3.5           # max gap — entering >3.5% = too extended (profitable sweet spot 1.5-3.5%)
V2_MIN_GAP_ACCEL = 0.10        # min gap acceleration over 10 bars — raised from 0.06
V2_GAP_ACCEL_WINDOW = 10       # bars to measure gap acceleration
V2_VELOCITY_WINDOW = 5         # bars to measure price velocity
V2_PERSISTENCE_BARS = 3        # min bars price must stay on same side of EMA (raised from 2)
V2_MIN_ATR_PCT = 0.02          # min ATR% — skip ultra-low-vol tokens
V2_VOLUME_LOOKBACK = 30        # bars for average volume
V2_VOLUME_MULT = 1.0           # volume must be >= average (any volume OK)
V2_COOLDOWN_BARS = 15          # cooldown between signals per token
V2_LOOKBACK_1M = 700           # 1m prices to fetch
V2_SLOPE_WINDOW = 20           # bars for linear regression slope
V2_MIN_SLOPE_PCT = 0.0005      # min slope % per bar (lower = earlier entry)
# Fresh cross mode: catch the FIRST momentum bar after EMA300 cross
V2_FRESH_CROSS_BARS = 8        # max bars since cross to qualify for fresh entry
V2_FRESH_CROSS_MIN_GAP = 0.50  # raised from 0.30 (too many false signals)
V2_LONG_ONLY = True            # SHORT side had 23% WR — LONG only

PERIOD = 300  # EMA300 period
DRY_RUN = '--dry' in sys.argv

SIGNAL_TYPE_LONG = 'accel_300_v2_long'
SIGNAL_TYPE_SHORT = 'accel_300_v2_short'
SOURCE_LONG = 'accel-300-v2+'
SOURCE_SHORT = 'accel-300-v2-'


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
        print(f"  [accel-300-v2] price_history error for {token}: {e}")
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
# Detection — V2 Strong Trend Momentum
# ═══════════════════════════════════════════════════════════════════════════════

def detect_accel_300_v2(token: str, prices: list) -> Optional[dict]:
    """Detect strong trend momentum — gap large AND accelerating.

    LONG fires when:
      1. Price above EMA300 with gap >= 1.5%
      2. Gap is accelerating (widening over 10-bar window)
      3. Price velocity positive (price moving up)
      4. Price persisted above EMA for 3+ bars (not a cross wick)
      5. Linear regression slope positive (trending)
      6. ATR above minimum (not ultra-low-vol)

    SHORT is the exact mirror.
    """
    min_rows = PERIOD + max(V2_GAP_ACCEL_WINDOW, V2_SLOPE_WINDOW, 10) + 10
    if len(prices) < min_rows:
        return None

    closes = [float(p['price']) for p in prices]

    # ATR floor: REMOVED — signal fires at the START of a move when last 14 bars are quiet
    # The gap acceleration filter already handles volatility filtering

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

    # ── Direction ──────────────────────────────────────────────────────────
    direction = 'LONG' if gap_now > 0 else 'SHORT'
    abs_gap = abs(gap_now)

    # ── FILTER 1: Gap must be large enough ─────────────────────────────────
    if abs_gap < V2_MIN_GAP_PCT:
        return None

    # ── FILTER 2: Gap not too extreme ──────────────────────────────────────
    if abs_gap > V2_MAX_GAP_PCT:
        return None

    # ── FILTER 3: Gap acceleration (10-bar window) ────────────────────────
    accel_start = latest_idx - V2_GAP_ACCEL_WINDOW
    if accel_start < 0:
        return None
    gap_then = gap_pcts[accel_start]
    if gap_then is None:
        return None
    gap_acceleration = gap_now - gap_then  # positive = gap widening for LONG

    if direction == 'LONG' and gap_acceleration < V2_MIN_GAP_ACCEL:
        return None
    if direction == 'SHORT' and gap_acceleration > -V2_MIN_GAP_ACCEL:
        return None

    # ── FILTER 4: Price velocity (must be moving in direction) ────────────
    if latest_idx < V2_VELOCITY_WINDOW:
        return None
    price_velocity = closes[latest_idx] - closes[latest_idx - V2_VELOCITY_WINDOW]
    price_epsilon = max(abs(closes[latest_idx]) * 1e-12, 1e-12)

    if direction == 'LONG' and price_velocity <= -price_epsilon:
        return None  # price falling — not momentum
    if direction == 'SHORT' and price_velocity >= price_epsilon:
        return None  # price rising — not momentum

    # ── FILTER 5: Persistence — price must stay on same side of EMA ───────
    persist_start = latest_idx - V2_PERSISTENCE_BARS + 1
    if persist_start < 0:
        return None
    for idx in range(persist_start, latest_idx + 1):
        ema = ema300[idx]
        if ema is None:
            return None
        if direction == 'LONG' and closes[idx] <= ema:
            return None
        if direction == 'SHORT' and closes[idx] >= ema:
            return None

    # ── FILTER 6: Linear regression slope (trending) ──────────────────────
    slope_window = min(V2_SLOPE_WINDOW, len(closes))
    if slope_window >= 2:
        slope_chunk = closes[-slope_window:]
        x_mean = (slope_window - 1) / 2.0
        y_mean = sum(slope_chunk) / slope_window
        denominator = sum((idx - x_mean) ** 2 for idx in range(slope_window))
        if denominator > 0 and y_mean != 0:
            numerator = sum(
                (idx - x_mean) * (slope_chunk[idx] - y_mean)
                for idx in range(slope_window)
            )
            pct_slope = (numerator / denominator) / y_mean * 100.0
            if direction == 'LONG' and pct_slope <= V2_MIN_SLOPE_PCT:
                return None
            if direction == 'SHORT' and pct_slope >= -V2_MIN_SLOPE_PCT:
                return None

    # ── FILTER 7: Gap velocity must confirm (not just level) ───────────────
    if latest_idx < 3:
        return None
    gap_prev = gap_pcts[latest_idx - 1]
    gap_prev2 = gap_pcts[latest_idx - 2]
    if gap_prev is None or gap_prev2 is None:
        return None
    gap_velocity = gap_now - gap_prev
    # Allow slight narrowing (noise) but velocity should generally confirm
    if direction == 'LONG' and gap_velocity < -0.05:
        return None  # gap narrowing too fast — reversal risk
    if direction == 'SHORT' and gap_velocity > 0.05:
        return None

    # ── FILTER 8: Fresh cross detection — catch the FIRST momentum bar ─────
    # Find most recent EMA300 cross (price crossing from below to above for LONG)
    fresh_cross = False
    cross_bar = None
    for idx in range(latest_idx, PERIOD - 1, -1):
        prev_idx = idx - 1
        if prev_idx < 0 or ema300[idx] is None or ema300[prev_idx] is None:
            continue
        if direction == 'LONG':
            crossed = closes[idx] > ema300[idx] and closes[prev_idx] <= ema300[prev_idx]
        else:
            crossed = closes[idx] < ema300[idx] and closes[prev_idx] >= ema300[prev_idx]
        if crossed:
            cross_bar = idx
            break

    bars_since_cross = latest_idx - cross_bar if cross_bar is not None else 999
    if bars_since_cross <= V2_FRESH_CROSS_BARS:
        fresh_cross = True

    # For fresh cross entries, relax the gap threshold (catch early)
    if fresh_cross and abs_gap < V2_FRESH_CROSS_MIN_GAP:
        return None  # even fresh cross needs SOME gap

    # For mature moves (not fresh cross), keep the higher gap threshold
    if not fresh_cross and abs_gap < V2_MIN_GAP_PCT:
        return None

    return {
        'direction': direction,
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

def scan_accel_300_v2_signals(prices_dict: dict) -> int:
    """Scan tokens for accel_300_v2 (strong trend momentum) signals."""
    from hermes_constants import (
        ACCEL_300_V2_ENABLED,
        ACCEL_300_V2_PLUS_ENABLED,
        ACCEL_300_V2_MINUS_ENABLED,
        SHORT_BLACKLIST,
    )
    if not ACCEL_300_V2_ENABLED:
        return 0

    from position_manager import get_open_positions as _get_open_pos
    from signal_gen import recent_trade_exists, is_delisted, MIN_TRADE_INTERVAL_MINUTES

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

        sig = detect_accel_300_v2(token, prices)
        if sig is None:
            continue

        direction = sig['direction']

        # LONG_ONLY mode — SHORT side had 23% WR in backtest
        if V2_LONG_ONLY and direction == 'SHORT':
            continue

        if get_cooldown(token, direction=direction):
            continue

        # Per-direction kill-switch
        if direction == 'LONG' and not ACCEL_300_V2_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not ACCEL_300_V2_MINUS_ENABLED:
            continue

        # Blacklist guard
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        # 1h trend filter — must align with signal direction
        trend_1h = _get_1h_trend(token)
        if direction == 'LONG' and trend_1h == 'BEARISH':
            continue  # don't go LONG in bearish 1h
        if direction == 'SHORT' and trend_1h == 'BULLISH':
            continue  # don't go SHORT in bullish 1h

        # Volume confirmation
        if not _check_volume(token):
            continue

        # Phase filter — only during trending/accelerating phases
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
        fresh_bonus = 8 if sig.get('fresh_cross') else 0  # early entry bonus
        confidence = int(min(88, 62 + gap_bonus + accel_bonus + trend_bonus + fresh_bonus))
        confidence = max(60, confidence)

        signal_price = float(sig['price'])
        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        if DRY_RUN:
            _log(f"  [DRY] {direction:5s}-accel-300-v2 {token:8s} conf={confidence:.0f}% "
                  f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                  f"accel={sig['gap_acceleration']:.3f}% "
                  f"gap_vel={sig['gap_velocity']:.3f}% "
                  f"trend_1h={trend_1h} [{source}]")
            continue

        try:
            sid = add_signal(
                token=token.upper(),
                direction=direction,
                signal_type=sig_type,
                source=source,
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
                set_cooldown(token, direction, hours=V2_COOLDOWN_BARS / 60.0)
                _log(f"  {direction:5s}-accel-300-v2 {token:8s} conf={confidence:.0f}% "
                      f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                      f"accel={sig['gap_acceleration']:.3f}% "
                      f"gap_vel={sig['gap_velocity']:.3f}% "
                      f"trend_1h={trend_1h} [{source}]")
        except Exception as e:
            print(f"[accel-300-v2] add_signal error for {token}: {e}")

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
    print(f"[accel-300-v2] Testing on {len(prices)} tokens ({mode} mode)...")
    init_db()
    n = scan_accel_300_v2_signals(prices)
    print(f"[accel-300-v2] Done. {n} signals emitted.")


# ═══════════════════════════════════════════════════════════════════════════════
# signals_runner entry point
# ═══════════════════════════════════════════════════════════════════════════════

def run(prices_dict=None):
    """Entry point for signals_runner."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_accel_300_v2_signals(prices_dict)
