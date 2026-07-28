#!/usr/bin/env python3
"""Inverse Accel-300 — Mean Reversion Signal.

The opposite of accel_300: instead of riding momentum, this signal bets on
price reverting to EMA300 after an overextended move.

Signal contract
---------------
SHORT fires when:
  - price is far ABOVE EMA300 (overextended rally)
  - the gap has started narrowing (reversion confirmed)
  - price velocity is turning downward

LONG fires when:
  - price is far BELOW EMA300 (overextended selloff)
  - the gap has started narrowing (reversion confirmed)
  - price velocity is turning upward

This catches tops and bottoms that accel_300 misses.
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
_PRICE_DB = STATIC_DB   # price_history -- live 1m prices

# ── Signal constants ──────────────────────────────────────────────────────────
from hermes_constants import (
    ACCEL_300_PERIOD,
    INVERSE_ACCEL_300_MIN_GAP_PCT_LONG,
    INVERSE_ACCEL_300_MIN_GAP_PCT_SHORT,
    INVERSE_ACCEL_300_REVERSION_BARS,
    INVERSE_ACCEL_300_REVERSION_THRESHOLD,
    INVERSE_ACCEL_300_COOLDOWN_BARS,
    INVERSE_ACCEL_300_LOOKBACK_1M,
    INVERSE_ACCEL_300_MAX_GAP_PCT,
    INVERSE_ACCEL_300_TREND_FILTER_PCT,
    ACCEL_300_BAR_GAP_THRESH_SEC,
)

PERIOD = ACCEL_300_PERIOD
DRY_RUN = '--dry' in sys.argv

SIGNAL_TYPE_LONG  = 'inverse_accel_300_long'
SIGNAL_TYPE_SHORT = 'inverse_accel_300_short'
SOURCE_LONG       = 'inv-accel-300+'
SOURCE_SHORT      = 'inv-accel-300-'


# ═══════════════════════════════════════════════════════════════════════════════
# EMA helper (same as accel_300)
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

def _get_1m_prices(token: str, lookback: int = INVERSE_ACCEL_300_LOOKBACK_1M) -> list:
    """Fetch 1m close prices from price_history, oldest first."""
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
        conn.close()

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
            threshold = max(ACCEL_300_BAR_GAP_THRESH_SEC, mean_gap + 3.0 * std_gap)
            for i in range(1, len(rows)):
                if rows[i][0] - rows[i-1][0] > threshold:
                    return []

        return [{'timestamp': r[0], 'price': r[1]} for r in rows]

    except Exception as e:
        print(f"  [inverse-accel-300] price_history error for {token}: {e}")
    return []


def _check_1h_trend(token: str, direction: str, current_price: float) -> bool:
    """Check if 1h trend conflicts with reversion direction.
    
    Returns True if trade should be BLOCKED (trend too strong against us).
    For LONG reversion: block if price rose >TREND_FILTER_PCT in last hour (strong uptrend)
    For SHORT reversion: block if price fell >TREND_FILTER_PCT in last hour (strong downtrend)
    """
    try:
        import time
        now = time.time()
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT price FROM price_history 
            WHERE token = ? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC LIMIT 1
        """, (token.upper(), now - 3600, now - 3500))
        row = c.fetchone()
        conn.close()
        
        if not row or not row[0]:
            return False  # no data — don't block
        
        price_1h_ago = row[0]
        if price_1h_ago <= 0:
            return False
        
        move_pct = abs(current_price - price_1h_ago) / price_1h_ago * 100
        
        if direction == 'LONG' and current_price > price_1h_ago:
            # Price rose in last hour — strong uptrend, reversion LONG is counter-trend
            if move_pct > INVERSE_ACCEL_300_TREND_FILTER_PCT:
                return True
        elif direction == 'SHORT' and current_price < price_1h_ago:
            # Price fell in last hour — strong downtrend, reversion SHORT is counter-trend
            if move_pct > INVERSE_ACCEL_300_TREND_FILTER_PCT:
                return True
        
        return False
    except Exception:
        return False  # on error, don't block


# ═══════════════════════════════════════════════════════════════════════════════
# Detection — Mean Reversion
# ═══════════════════════════════════════════════════════════════════════════════

def detect_inverse_accel_300(token: str, prices: list) -> Optional[dict]:
    """Detect mean reversion opportunity at the newest price point.

    SHORT: price far above EMA300, gap narrowing, velocity turning down.
    LONG:  price far below EMA300, gap narrowing, velocity turning up.
    """
    period = PERIOD
    min_rows = period + 10
    if len(prices) < min_rows:
        return None

    closes = [float(p['price']) for p in prices]
    ema300 = _ema_series(closes, period)
    gap_pcts = [
        None if ema is None or ema == 0 else (price - ema) / ema * 100.0
        for price, ema in zip(closes, ema300)
    ]

    latest_idx = len(closes) - 1
    latest_ema = ema300[latest_idx]
    gap_now = gap_pcts[latest_idx]
    if latest_ema is None or gap_now is None:
        return None

    # Determine direction based on gap position
    if gap_now > 0:
        direction = 'SHORT'  # price above EMA → mean reversion SHORT
        min_gap = INVERSE_ACCEL_300_MIN_GAP_PCT_SHORT
    elif gap_now < 0:
        direction = 'LONG'   # price below EMA → mean reversion LONG
        min_gap = INVERSE_ACCEL_300_MIN_GAP_PCT_LONG
    else:
        return None

    # Gap must be large enough (overextended)
    if abs(gap_now) < min_gap:
        return None

    # Don't fire if gap is too extreme (likely structural, not mean-reverting)
    if abs(gap_now) > INVERSE_ACCEL_300_MAX_GAP_PCT:
        return None

    # Check for reversion: gap must be narrowing over recent bars
    reversion_bars = INVERSE_ACCEL_300_REVERSION_BARS
    reversion_start = latest_idx - reversion_bars
    if reversion_start < 0:
        return None

    gap_then = gap_pcts[reversion_start]
    if gap_then is None:
        return None

    # For SHORT (price above EMA): gap should be shrinking (gap_now < gap_then)
    # For LONG (price below EMA): gap should be shrinking (gap_now > gap_then, less negative)
    if direction == 'SHORT':
        gap_change = gap_then - gap_now  # positive = gap narrowing
    else:
        gap_change = gap_now - gap_then  # positive = gap narrowing (less negative)

    if gap_change < INVERSE_ACCEL_300_REVERSION_THRESHOLD:
        return None

    # Price velocity must confirm reversion
    # For SHORT: price should be falling (velocity negative)
    # For LONG: price should be rising (velocity positive)
    price_velocity = closes[latest_idx] - closes[latest_idx - 5]
    price_epsilon = max(abs(closes[latest_idx]) * 1e-12, 1e-12)

    if direction == 'SHORT' and price_velocity >= -price_epsilon:
        return None  # price not falling → no reversion
    if direction == 'LONG' and price_velocity <= price_epsilon:
        return None  # price not rising → no reversion

    # FIX (2026-07-27): Stabilization + local extreme check.
    # Don't catch falling knives (LONG) or short into rallies (SHORT).
    # For LONG: price must be near recent LOW (turning point, not mid-fall).
    # For SHORT: price must be near recent HIGH (turning point, not mid-rally).
    # NOTE: Falling knife protection is handled by staleness guard in scanner (0.5% slippage).
    stab_window = min(10, latest_idx)
    if stab_window >= 3:
        recent_prices = closes[latest_idx - stab_window + 1 : latest_idx + 1]
        if direction == 'LONG':
            recent_low = min(recent_prices[:-1])  # exclude current bar
            # Price must be near the low (within 0.3%) — entering at turning point
            if closes[latest_idx] > recent_low * 1.003:
                return None  # price too far above recent low — not a dip buy
            # Also reject if still making new lows (stabilization)
            if closes[latest_idx] < recent_low * 0.998:
                return None
        elif direction == 'SHORT':
            recent_high = max(recent_prices[:-1])  # exclude current bar
            # Price must be near the high (within 0.3%) — entering at turning point
            if closes[latest_idx] < recent_high * 0.997:
                return None  # price too far below recent high — not a rip sell
            # Also reject if still making new highs (stabilization)
            if closes[latest_idx] > recent_high * 1.002:
                return None

    # Gap velocity should confirm narrowing (use 3-bar window to filter noise)
    gap_prev3 = gap_pcts[latest_idx - 3]
    if gap_prev3 is None:
        return None

    gap_velocity = gap_now - gap_prev3
    # For SHORT: gap_velocity should be negative (gap shrinking)
    # For LONG: gap_velocity should be positive (gap shrinking toward zero)
    if direction == 'SHORT' and gap_velocity >= 0:
        return None
    if direction == 'LONG' and gap_velocity <= 0:
        return None

    # ── Price position filter (FIX 2026-07-28) ──────────────────────────────────
    # Don't enter if price is already at the extreme of the 20-bar range.
    # Prevents buying tops (LONG at range high) and shorting bottoms (SHORT at range low).
    # This is wider than the 10-bar stabilization check above.
    range_lookback = min(20, len(closes))
    if range_lookback >= 5:
        range_high = max(closes[-range_lookback:])
        range_low = min(closes[-range_lookback:])
        range_size = range_high - range_low
        if range_size > 0:
            position_pct = (closes[-1] - range_low) / range_size  # 0=bottom, 1=top
            if direction == 'LONG' and position_pct > 0.80:
                return None  # LONG at top 20% of range — high reversal risk
            if direction == 'SHORT' and position_pct < 0.20:
                return None  # SHORT at bottom 20% of range — high bounce risk

    # ── Phase entry filter (FIX 2026-07-28) ────────────────────────────────────
    # Mean reversion only works during exhaustion/extreme phases.
    # During quiet/building, the move hasn't exhausted yet — too early to catch turn.
    # Data: inv-accel-300 has 17% WR during dead hours vs 37% active (phase-related).
    from hermes_constants import PHASE_ENTRY_FILTER_ENABLED, INVERSE_ACCEL_300_ALLOWED_PHASES
    if PHASE_ENTRY_FILTER_ENABLED:
        from tpsl_utils import _get_current_phase
        phase = _get_current_phase(token)
        if phase and phase not in INVERSE_ACCEL_300_ALLOWED_PHASES:
            return None

    return {
        'direction': direction,
        'gap_pct': round(gap_now, 4),
        'gap_change': round(gap_change, 4),
        'gap_velocity': round(gap_velocity, 4),
        'price_velocity': price_velocity,
        'price': closes[latest_idx],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_inverse_accel_300_signals(prices_dict: dict) -> int:
    """Scan tokens for inverse_accel_300 (mean reversion) signals."""
    from hermes_constants import (
        INVERSE_ACCEL_300_ENABLED,
        INVERSE_ACCEL_300_PLUS_ENABLED,
        INVERSE_ACCEL_300_MINUS_ENABLED,
        SHORT_BLACKLIST,
    )
    if not INVERSE_ACCEL_300_ENABLED:
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
        if not prices or len(prices) < PERIOD + 10:
            continue

        sig = detect_inverse_accel_300(token, prices)
        if sig is None:
            continue

        direction = sig['direction']
        if get_cooldown(token, direction=direction):
            continue

        # Per-direction kill-switch
        if direction == 'LONG' and not INVERSE_ACCEL_300_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not INVERSE_ACCEL_300_MINUS_ENABLED:
            continue

        # Blacklist guard
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        # 1h trend filter — skip if price moved strongly against reversion direction
        if _check_1h_trend(token, direction, price):
            continue

        # Staleness guard — if price has moved >0.5% from detection, skip
        # Prevents stale signals where price dropped before entry (falling knife)
        sig_price = sig['price']
        if sig_price > 0:
            slippage_pct = abs(price - sig_price) / sig_price * 100.0
            if slippage_pct > 0.5:
                continue

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        # Confidence: base on gap strength + reversion strength
        gap_bonus = min(15, abs(sig['gap_pct']) * 5)
        reversion_bonus = min(10, sig['gap_change'] * 100)
        confidence = int(min(80, 60 + gap_bonus + reversion_bonus))
        confidence = max(55, confidence)

        signal_price = float(sig['price'])

        if DRY_RUN:
            _log(f"  [DRY] {direction:5s}-inv-accel-300 {token:8s} conf={confidence:.0f}% "
                  f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                  f"reversion={sig['gap_change']:.3f}% "
                  f"gap_vel={sig['gap_velocity']:.3f}% [{source}]")
            continue

        try:
            sid = add_signal(
                token=token.upper(),
                direction=direction,
                signal_type=sig_type,
                source=source,
                confidence=confidence,
                value=float(sig['gap_change']),
                price=signal_price,
                exchange='hyperliquid',
                timeframe='1m',
                z_score=None,
                z_score_tier=None,
            )
            if sid:
                added += 1
                set_cooldown(token, direction, hours=INVERSE_ACCEL_300_COOLDOWN_BARS / 60.0)
                _log(f"  {direction:5s}-inv-accel-300 {token:8s} conf={confidence:.0f}% "
                      f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                      f"reversion={sig['gap_change']:.3f}% "
                      f"gap_vel={sig['gap_velocity']:.3f}% [{source}]")
        except Exception as e:
            print(f"[inverse-accel-300] add_signal error for {token}: {e}")

    return added


# ═══════════════════════════════════════════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    from signal_schema import init_db

    conn = sqlite3.connect(_PRICE_DB, timeout=10)
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT token FROM price_history
        WHERE timestamp > ?
        ORDER BY token
    """, (int(time.time()) - 600,))
    tokens = [r[0] for r in c.fetchall()]
    conn.close()

    prices = {}
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
    conn.close()

    mode = "DRY" if DRY_RUN else "LIVE"
    print(f"[inverse-accel-300] Testing on {len(prices)} tokens ({mode} mode)...")
    init_db()
    n = scan_inverse_accel_300_signals(prices)
    print(f"[inverse-accel-300] Done. {n} signals emitted.")


# ═══════════════════════════════════════════════════════════════════════════════
# signals_runner entry point
# ═══════════════════════════════════════════════════════════════════════════════

def run(prices_dict=None):
    """Entry point for signals_runner."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_inverse_accel_300_signals(prices_dict)
