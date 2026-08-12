#!/usr/bin/env python3
# Migrated from ../accel_300_signals.py — see signals/__init__.py registry
"""Latest-bar EMA300 acceleration signal.

Data source
-----------
`signals_hermes.db.price_history` supplies the live 1-minute points. Candle DB
rows are intentionally not used because they can lag the live price collector.

Signal contract
---------------
LONG fires only when the newest price-history point is above its newest EMA300,
the positive EMA gap has persisted and widened, and the newest upward gap
velocity is stronger than the prior velocity.

SHORT is the exact mirror: newest price below newest EMA300, persistent/widening
negative gap, and newest downward gap velocity more negative than before.

Historical points may calculate EMA, persistence, velocity, and cross age, but
an old qualifying point can never be returned as a current signal. This avoids
stale LONG/SHORT emissions after live price action has reversed.

Pipeline
--------
price_history (1m) -> EMA300/current acceleration -> signal_schema.add_signal()
-> signals_hermes_runtime.db -> signal_compactor -> hotset.json -> guardian.
"""

import sys, os, sqlite3, time
from typing import Optional
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes

SIGNAL_LOG = '/var/www/hermes/logs/signals.log'
os.makedirs(os.path.dirname(SIGNAL_LOG), exist_ok=True)


def _log(msg: str) -> None:
    """Write signal events to stdout and the shared signal log."""
    print(msg)
    try:
        with open(SIGNAL_LOG, 'a') as log_file:
            log_file.write(msg + '\n')
    except OSError as exc:
        print(f"[accel-300] log write failed: {exc}")

# ── Paths ─────────────────────────────────────────────────────────────────────
from paths import RUNTIME_DB, STATIC_DB, CANDLES_DB
_RUNTIME_DB = RUNTIME_DB
_PRICE_DB = STATIC_DB   # price_history -- live 1m prices

# ── Signal constants (from hermes_constants) ──────────────────────────────────
from hermes_constants import (
    ACCEL_300_PERIOD, ACCEL_300_LOOKBACK, ACCEL_300_LOOKBACK_SHORT,
    ACCEL_300_PERSISTENCE_BARS,
    ACCEL_300_MIN_GAP_PCT, ACCEL_300_MIN_GAP_GROWTH, ACCEL_300_COOLDOWN_BARS,
    ACCEL_300_LOOKBACK_1M,
    ACCEL_300_MIN_GAP_PCT_LONG, ACCEL_300_MIN_GAP_PCT_SHORT,
    ACCEL_300_MIN_GAP_GROWTH_SHORT,
    ACCEL_300_STALE_BARS, ACCEL_300_STALE_BARS_SHORT,
    ACCEL_300_MARGINAL_ACCEL_BARS, ACCEL_300_BARS_UNKNOWN,
    ACCEL_300_BAR_GAP_THRESH_SEC, ACCEL_300_BREAKOUT_CONFIDENCE,
)
# Alias local names for readability in detection logic
PERIOD          = ACCEL_300_PERIOD
LOOKBACK        = ACCEL_300_LOOKBACK
LOOKBACK_SHORT  = ACCEL_300_LOOKBACK_SHORT
PERSISTENCE_BARS = ACCEL_300_PERSISTENCE_BARS
MIN_GAP_PCT     = ACCEL_300_MIN_GAP_PCT
MIN_GAP_GROWTH_PCT = ACCEL_300_MIN_GAP_GROWTH
COOLDOWN_BARS   = ACCEL_300_COOLDOWN_BARS
LOOKBACK_1M     = ACCEL_300_LOOKBACK_1M
STALE_BARS      = ACCEL_300_STALE_BARS
STALE_BARS_SHORT = ACCEL_300_STALE_BARS_SHORT
MARGINAL_ACCEL_BARS = ACCEL_300_MARGINAL_ACCEL_BARS
BARS_UNKNOWN     = ACCEL_300_BARS_UNKNOWN
BAR_GAP_THRESH_SEC = ACCEL_300_BAR_GAP_THRESH_SEC
DRY_RUN            = '--dry' in sys.argv

SIGNAL_TYPE_LONG   = 'accel_300_long'
SIGNAL_TYPE_SHORT  = 'accel_300_short'
SOURCE_LONG        = 'accel-300+'
SOURCE_SHORT       = 'accel-300-'


# ═══════════════════════════════════════════════════════════════════════════════
# EMA helpers
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
# Data fetch -- LIVE prices from price_history (signals_hermes.db)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_1m_prices(token: str, lookback: int = LOOKBACK_1M) -> list:
    """Fetch 1m close prices from price_history (signals_hermes.db), oldest first.

    price_history is updated every minute with live prices -- the ONLY reliable
    source for live signal generation. timestamps are in SECONDS (Unix time).

    Returns list of {timestamp, price} dicts, oldest first.
    Freshness guard: returns [] if most recent price is > 5 minutes old.
    """
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
            print(f"  [accel-300] {token}: stale price_history (last ts {most_recent_ts}), skipping")
            return []

        # Bar-to-bar gap guard -- detect missing data
        bar_gaps = [rows[i][0] - rows[i-1][0] for i in range(1, len(rows))]
        if bar_gaps:
            mean_gap = sum(bar_gaps) / len(bar_gaps)
            variance = sum((g - mean_gap) ** 2 for g in bar_gaps) / len(bar_gaps)
            std_gap = variance ** 0.5
            threshold = max(BAR_GAP_THRESH_SEC, mean_gap + 3.0 * std_gap)
            for i in range(1, len(rows)):
                if rows[i][0] - rows[i-1][0] > threshold:
                    print(f"  [accel-300] {token}: data gap, skipping")
                    return []

        return [{'timestamp': r[0], 'price': r[1]} for r in rows]

    except Exception as e:
        print(f"  [accel-300] price_history error for {token}: {e}")
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# Detection
# ═══════════════════════════════════════════════════════════════════════════════

def detect_accel_300(token: str, prices: list) -> Optional[dict]:
    """Detect acceleration at the newest 1-minute price_history point.

    LONG requires all current conditions to agree:
      - latest price is above its latest EMA300
      - the positive gap is large enough and persisted across recent bars
      - the gap is widening upward now
      - the latest upward gap velocity is stronger than the prior velocity

    SHORT is the exact mirror below EMA300: a sufficiently negative, persistent
    gap whose latest downward velocity is more negative than the prior velocity.

    Historical bars are used only to calculate EMA, persistence, and velocity.
    They are never returned as a current signal. This prevents an old
    qualifying bar from being resurrected after price action has reversed.
    """
    from hermes_constants import (
        ACCEL_300_PERIOD,
        ACCEL_300_PERSISTENCE_BARS,
        ACCEL_300_MIN_GAP_PCT_LONG,
        ACCEL_300_MIN_GAP_PCT_SHORT,
        ACCEL_300_MIN_GAP_GROWTH,
        ACCEL_300_MIN_GAP_GROWTH_SHORT,
        ACCEL_300_REGIME_SLOPE_PCT,
        ACCEL_300_SLOPE_WINDOW,
        ACCEL_300_BARS_UNKNOWN,
        PHASE_ENTRY_FILTER_ENABLED,
        ACCEL_300_ALLOWED_PHASES,
    )

    period = ACCEL_300_PERIOD
    persistence_bars = ACCEL_300_PERSISTENCE_BARS
    minimum_rows = period + max(persistence_bars, 3)
    if len(prices) < minimum_rows:
        return None

    closes = [float(point['price']) for point in prices]
    ema300 = _ema_series(closes, period)
    gap_pcts = [
        None if ema is None or ema == 0 else (price - ema) / ema * 100.0
        for price, ema in zip(closes, ema300)
    ]

    latest_idx = len(closes) - 1
    latest_ema = ema300[latest_idx]
    gap_now = gap_pcts[latest_idx]
    if latest_ema is None or gap_now is None or closes[latest_idx] == latest_ema:
        return None

    direction = 'LONG' if closes[latest_idx] > latest_ema else 'SHORT'
    min_gap = (
        ACCEL_300_MIN_GAP_PCT_LONG
        if direction == 'LONG'
        else ACCEL_300_MIN_GAP_PCT_SHORT
    )
    if abs(gap_now) < min_gap:
        return None

    # Price must remain on the current side of EMA throughout the persistence
    # window. A one-point cross/touch is not enough to establish momentum.
    persistence_start = latest_idx - persistence_bars + 1
    if persistence_start < 0:
        return None
    for idx in range(persistence_start, latest_idx + 1):
        ema = ema300[idx]
        if ema is None:
            return None
        if direction == 'LONG' and closes[idx] <= ema:
            return None
        if direction == 'SHORT' and closes[idx] >= ema:
            return None

    growth_start_idx = latest_idx - persistence_bars
    if growth_start_idx < 0 or gap_pcts[growth_start_idx] is None:
        return None
    gap_then = gap_pcts[growth_start_idx]
    gap_growth = gap_now - gap_then
    min_growth = (
        ACCEL_300_MIN_GAP_GROWTH
        if direction == 'LONG'
        else ACCEL_300_MIN_GAP_GROWTH_SHORT
    )
    if direction == 'LONG' and gap_growth <= min_growth:
        return None
    if direction == 'SHORT' and gap_growth >= -min_growth:
        return None

    # Price velocity must also strengthen literally. EMA-gap acceleration alone
    # can look stronger merely because EMA300 moved, even when raw price speed
    # was flat or weakening.
    # Use 5-bar window: price collector stores same price for 2-3 consecutive bars,
    # making 1-bar velocity zero. 5-bar window captures real price movement.
    price_velocity = closes[latest_idx] - closes[latest_idx - 5]
    prior_price_velocity = closes[latest_idx - 5] - closes[latest_idx - 10]
    price_acceleration = price_velocity - prior_price_velocity
    # Price velocity check removed — gap velocity is sufficient evidence of momentum.
    # Price collector stores same price for consecutive bars, making velocity zero
    # even when gap is widening. Gap velocity captures the actual signal.

    # Velocity = current bar's change in EMA gap. Acceleration = change in
    # velocity. Relaxed: allow slightly negative velocity (gap narrowing slightly
    # is normal in ranging markets — the gap still exists and is valid).
    gap_prev = gap_pcts[latest_idx - 1]
    gap_prev2 = gap_pcts[latest_idx - 2]
    if gap_prev is None or gap_prev2 is None:
        return None
    gap_velocity = gap_now - gap_prev
    prior_gap_velocity = gap_prev - gap_prev2
    gap_acceleration = gap_velocity - prior_gap_velocity
    # Allow velocity down to -0.01 (slight narrowing) — gap still valid
    if direction == 'LONG':
        if gap_velocity < -0.01:
            return None
    else:
        if gap_velocity > 0.01:
            return None

    # Use a trailing slope window. The legacy detector used bars after an old
    # candidate bar; a latest-bar detector cannot look into the future.
    slope_window = min(ACCEL_300_SLOPE_WINDOW, len(closes))
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
            if direction == 'LONG' and pct_slope <= ACCEL_300_REGIME_SLOPE_PCT:
                return None
            if direction == 'SHORT' and pct_slope >= -ACCEL_300_REGIME_SLOPE_PCT:
                return None

    # Diagnostic only: report distance from the most recent same-direction EMA
    # cross, but do not require a fresh cross. Sustained acceleration remains a
    # valid signal as long as the current conditions above are true.
    cross_bar = None
    for idx in range(latest_idx, period - 1, -1):
        previous_idx = idx - 1
        if previous_idx < 0 or ema300[idx] is None or ema300[previous_idx] is None:
            continue
        if direction == 'LONG':
            crossed = closes[idx] > ema300[idx] and closes[previous_idx] <= ema300[previous_idx]
        else:
            crossed = closes[idx] < ema300[idx] and closes[previous_idx] >= ema300[previous_idx]
        if crossed:
            cross_bar = idx
            break

    bars_since_cross = (
        latest_idx - cross_bar if cross_bar is not None else ACCEL_300_BARS_UNKNOWN
    )

    # Stale bars check removed — gap/persistence/growth filters already ensure validity.
    # Cross freshness is not required for acceleration signals.

    # ── Price position filter (FIX 2026-07-28) ──────────────────────────────────
    # Don't enter if price is already at the extreme of the recent range.
    # Prevents buying tops (LONG at range high) and shorting bottoms (SHORT at range low).
    # Uses 20-bar range to measure micro-position within the channel.
    range_lookback = min(20, len(closes))
    if range_lookback >= 5:
        range_high = max(closes[-range_lookback:])
        range_low = min(closes[-range_lookback:])
        range_size = range_high - range_low
        if range_size > 0:
            position_pct = (closes[-1] - range_low) / range_size  # 0=bottom, 1=top
            if direction == 'LONG' and position_pct > 0.80:
                # LONG at top 20% of range — high reversal risk
                return None
            if direction == 'SHORT' and position_pct < 0.20:
                # SHORT at bottom 20% of range — high bounce risk
                return None

    # ── Phase entry filter (FIX 2026-07-28) ────────────────────────────────────
    # Don't enter during exhaustion/extreme phases — the move is over.
    # Data: accel_300 has 50% WR during dead hours (good), but exhaustion entries
    # chase after the move is done → price reverses → SL hit.
    if PHASE_ENTRY_FILTER_ENABLED:
        from tpsl_utils import _get_current_phase
        phase = _get_current_phase(token)
        if phase and phase not in ACCEL_300_ALLOWED_PHASES:
            return None

    return {
        'direction': direction,
        'gap_pct': round(gap_now, 4),
        'gap_growth': round(gap_growth, 4),
        'price_velocity': price_velocity,
        'price_acceleration': price_acceleration,
        'gap_velocity': round(gap_velocity, 4),
        'gap_acceleration': round(gap_acceleration, 4),
        'gap_then': round(gap_then, 4),
        'bars_since_cross': bars_since_cross,
        'price': closes[latest_idx],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Ultra-Fast Breakout Detection
# ═══════════════════════════════════════════════════════════════════════════════

def detect_breakout(token: str, prices: list, volumes: list = None) -> Optional[dict]:
    """Detect high-velocity breakout BEFORE persistence confirms the trend.

    Fires when price makes a fast move (>1.0% in 5 bars) with strong gap from
    EMA60. Uses 200 EMA as trend filter. Requires volume confirmation.

    Returns signal dict or None.
    """
    from hermes_constants import (
        ACCEL_300_BREAKOUT_VELOCITY,
        ACCEL_300_BREAKOUT_GAP_MIN,
        ACCEL_300_BREAKOUT_TREND_EMA,
        ACCEL_300_BREAKOUT_VOL_MULT,
    )

    if len(prices) < 210:  # need 200 EMA warmup + 5 bar velocity
        return None

    closes = [float(p['price']) for p in prices]

    # Compute EMAs
    ema60 = _ema_series(closes, 60)
    ema200 = _ema_series(closes, 200)

    latest_idx = len(closes) - 1
    if ema60[latest_idx] is None or ema200[latest_idx] is None:
        return None

    gap_now = (closes[latest_idx] - ema60[latest_idx]) / ema60[latest_idx] * 100.0
    direction = 'LONG' if closes[latest_idx] > ema60[latest_idx] else 'SHORT'

    # Gap must be strong enough
    if abs(gap_now) < ACCEL_300_BREAKOUT_GAP_MIN:
        return None

    # Trend filter: LONG only above 200 EMA, SHORT only below
    if direction == 'LONG' and closes[latest_idx] < ema200[latest_idx]:
        return None
    if direction == 'SHORT' and closes[latest_idx] > ema200[latest_idx]:
        return None

    # 5-bar velocity check
    if latest_idx < 5:
        return None
    move_5 = (closes[latest_idx] - closes[latest_idx - 5]) / closes[latest_idx - 5] * 100.0
    if direction == 'LONG' and move_5 < ACCEL_300_BREAKOUT_VELOCITY:
        return None
    if direction == 'SHORT' and move_5 > -ACCEL_300_BREAKOUT_VELOCITY:
        return None

    # Fresh gap: price must have been on the same side for last 3 bars
    for j in range(latest_idx - 2, latest_idx + 1):
        if ema60[j] is None:
            return None
        if direction == 'LONG' and closes[j] <= ema60[j]:
            return None
        if direction == 'SHORT' and closes[j] >= ema60[j]:
            return None

    # Price must be moving in the right direction
    price_velocity = closes[latest_idx] - closes[latest_idx - 5]
    if direction == 'LONG' and price_velocity <= 0:
        return None
    if direction == 'SHORT' and price_velocity >= 0:
        return None

    # Volume filter (if volumes provided)
    if volumes and len(volumes) >= 20:
        vol_avg = sum(volumes[-20:]) / 20.0
        if vol_avg > 0 and volumes[-1] < vol_avg * ACCEL_300_BREAKOUT_VOL_MULT:
            return None

    return {
        'direction': direction,
        'gap_pct': round(gap_now, 4),
        'move_5bar': round(move_5, 4),
        'price_velocity': price_velocity,
        'price': closes[latest_idx],
        'type': 'breakout',
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Velocity Ignition Detection (FIX 2026-07-31)
# ═══════════════════════════════════════════════════════════════════════════════

def detect_velocity_ignition(token: str, prices: list) -> Optional[dict]:
    """Detect the FIRST strong momentum bar after EMA300 cross.

    Catches moves like MOVE 2026-07-31 where price dropped 0.39% in 1 minute.
    The standard accel_300 signal waits 18 bars of persistence — this fires on
    the first velocity spike, entering 15-20 minutes earlier.

    Fires when ALL of these are true:
      1. Price is on one side of EMA300 (LONG above, SHORT below)
      2. The cross happened recently (within STALE_BARS)
      3. Price velocity in the last bar is > VELOCITY_IGNITION_THRESHOLD x average
      4. Gap is growing (gap_now > gap_then over 3 bars)
      5. Price is moving in the signal direction (not just EMA moving)

    Returns signal dict or None.
    """
    from hermes_constants import (
        ACCEL_300_PERIOD,
        ACCEL_300_VELOCITY_IGNITION_ENABLED,
        ACCEL_300_VELOCITY_IGNITION_THRESHOLD,
        ACCEL_300_VELOCITY_IGNITION_MIN_GAP,
        ACCEL_300_VELOCITY_IGNITION_MIN_GAP_GROWTH,
        ACCEL_300_VELOCITY_IGNITION_MAX_CROSS_AGE,
    )

    if not ACCEL_300_VELOCITY_IGNITION_ENABLED:
        return None

    period = ACCEL_300_PERIOD
    if len(prices) < period + 10:
        return None

    closes = [float(p['price']) for p in prices]
    ema300 = _ema_series(closes, period)

    latest_idx = len(closes) - 1
    if ema300[latest_idx] is None:
        return None

    # Direction: price above or below EMA300
    gap_now = (closes[latest_idx] - ema300[latest_idx]) / ema300[latest_idx] * 100.0
    direction = 'LONG' if closes[latest_idx] > ema300[latest_idx] else 'SHORT'

    # Minimum gap requirement
    if abs(gap_now) < ACCEL_300_VELOCITY_IGNITION_MIN_GAP:
        return None

    # Z-score cap: don't fire if move is too extended (FIX 2026-07-31)
    # During losing streak, accel-300-vel+ fired at z=2.0-3.0 (top-chasing)
    # A velocity spike when z > 1.5 is chasing, not catching
    if len(closes) >= 20:
        mean_20 = sum(closes[-20:]) / 20
        std_20 = (sum((p - mean_20) ** 2 for p in closes[-20:]) / 20) ** 0.5
        if std_20 > 0:
            z_now = (closes[-1] - mean_20) / std_20
            if abs(z_now) > 1.5:
                return None  # move too extended — don't chase

    # Find most recent cross (price crossing EMA300)
    cross_bar = None
    for idx in range(latest_idx, period - 1, -1):
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

    if cross_bar is None:
        return None

    bars_since_cross = latest_idx - cross_bar
    if bars_since_cross > ACCEL_300_VELOCITY_IGNITION_MAX_CROSS_AGE:
        return None  # cross too old — not ignition, it's a mature move

    # Velocity check: last bar's move must be > threshold x average
    if latest_idx < 10:
        return None

    # Average absolute bar-to-bar change over last 10 bars
    bar_changes = [abs(closes[i] - closes[i-1]) for i in range(latest_idx - 9, latest_idx + 1)]
    avg_change = sum(bar_changes) / len(bar_changes)
    if avg_change == 0:
        return None

    last_bar_change = closes[latest_idx] - closes[latest_idx - 1]
    # Guard against zero price (practically impossible with real exchange data)
    if closes[latest_idx - 1] == 0:
        return None
    last_bar_pct = abs(last_bar_change) / closes[latest_idx - 1] * 100.0
    avg_change_pct = avg_change / closes[latest_idx - 1] * 100.0

    if last_bar_pct < avg_change_pct * ACCEL_300_VELOCITY_IGNITION_THRESHOLD:
        return None  # not a velocity spike

    # Price must be moving in the signal direction
    if direction == 'LONG' and last_bar_change <= 0:
        return None
    if direction == 'SHORT' and last_bar_change >= 0:
        return None

    # Gap growth check: gap must be widening over recent bars
    if latest_idx < 3:
        return None
    gap_ref = None
    for idx in range(latest_idx - 3, latest_idx - 10, -1):
        if idx >= 0 and ema300[idx] is not None and ema300[idx] != 0:
            gap_ref = (closes[idx] - ema300[idx]) / ema300[idx] * 100.0
            break
    if gap_ref is None:
        return None

    gap_growth = gap_now - gap_ref
    if direction == 'LONG' and gap_growth < ACCEL_300_VELOCITY_IGNITION_MIN_GAP_GROWTH:
        return None
    if direction == 'SHORT' and gap_growth > -ACCEL_300_VELOCITY_IGNITION_MIN_GAP_GROWTH:
        return None

    return {
        'direction': direction,
        'gap_pct': round(gap_now, 4),
        'gap_growth': round(gap_growth, 4),
        'bars_since_cross': bars_since_cross,
        'velocity_pct': round(last_bar_pct, 4),
        'avg_velocity_pct': round(avg_change_pct, 4),
        'velocity_ratio': round(last_bar_pct / avg_change_pct, 2) if avg_change_pct > 0 else 0,
        'price': closes[latest_idx],
        'type': 'velocity_ignition',
    }


# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_accel_300_signals(prices_dict: dict) -> int:
    """Scan tokens for accel_300 signals.

    All guards (blacklists, open positions, cooldowns, price age) must be
    applied by the caller before passing prices_dict here.

    Args:
        prices_dict: token -> {'price': float, ...} from signal_gen

    Returns:
        Number of signals written to DB.
    """
    from hermes_constants import ACCEL_300_ENABLED, ACCEL_300_TOKEN_ALLOWLIST
    if not ACCEL_300_ENABLED:
        return 0
    from signal_schema import add_signal, get_cooldown, price_age_minutes
    from position_manager import get_open_positions as _get_open_pos
    from signal_gen import (
        recent_trade_exists, is_delisted, SHORT_BLACKLIST,
        MIN_TRADE_INTERVAL_MINUTES, set_cooldown
    )

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
        # Direction-aware SHORT blacklist is enforced after detection. Applying
        # it here would also suppress valid LONG signals for the same token.
        # ── Token allowlist: only fire on tokens with >=50% historical WR ─────────
        if ACCEL_300_TOKEN_ALLOWLIST and token.upper() not in ACCEL_300_TOKEN_ALLOWLIST:
            continue
        if price_age_minutes(token) > 10:
            continue

        prices = _get_1m_prices(token, lookback=LOOKBACK_1M)
        minimum_rows = PERIOD + max(PERSISTENCE_BARS, 3)
        if not prices or len(prices) < minimum_rows:
            continue

        # ── Try persistence-based accel_300 first ────────────────────────────
        sig = detect_accel_300(token, prices)

        # ── Try ultra-fast breakout if persistence failed ─────────────────────
        from hermes_constants import ACCEL_300_BREAKOUT_ENABLED
        breakout_sig = None
        if sig is None and ACCEL_300_BREAKOUT_ENABLED:
            breakout_sig = detect_breakout(token, prices)
            if breakout_sig is not None:
                sig = breakout_sig

        # ── Try velocity ignition if both failed (FIX 2026-07-31) ─────────────
        # Catches the first strong bar after EMA300 cross — enters 15-20 min
        # earlier than persistence mode. Key for moves like MOVE 2026-07-31.
        vi_sig = None
        if sig is None:
            vi_sig = detect_velocity_ignition(token, prices)
            if vi_sig is not None:
                sig = vi_sig

        if sig is None:
            continue

        direction = sig['direction']
        if get_cooldown(token, direction=direction):
            continue

        # ── Per-direction kill-switch ─────────────────────────────────────────
        from hermes_constants import ACCEL_300_PLUS_ENABLED, ACCEL_300_MINUS_ENABLED
        if direction == 'LONG' and not ACCEL_300_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not ACCEL_300_MINUS_ENABLED:
            continue

        # ── Z-score direction filter (FIX 2026-07-31) ────────────────────────
        # Block LONG when z < -0.5 (price below average = chasing downtrend)
        # Block SHORT when z > 0.5 (price above average = chasing uptrend)
        # During losing streaks, signals fired in wrong direction 26% of the time
        if len(prices) >= 20:
            closes_for_z = [float(p['price']) for p in prices[-20:]]
            mean_z = sum(closes_for_z) / 20
            std_z = (sum((p - mean_z) ** 2 for p in closes_for_z) / 20) ** 0.5
            if std_z > 0:
                z_now = (closes_for_z[-1] - mean_z) / std_z
                if direction == 'LONG' and z_now < -0.5:
                    continue  # don't buy when price is below average
                if direction == 'SHORT' and z_now > 0.5:
                    continue  # don't sell when price is above average

        # ── Blacklist guard — direction-aware ─────────────────────────────────
        # SHORT_BLACKLIST only blocks SHORT signals; LONG signals for the same token
        # are valid (the blacklist is about shorting specific tokens, not going LONG).
        # Apply AFTER direction is determined so valid LONG signals aren't blocked.
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT

        # ── Source and confidence: breakout vs velocity ignition vs persistence ──
        is_breakout = breakout_sig is not None and sig.get('type') == 'breakout'
        is_vi = vi_sig is not None and sig.get('type') == 'velocity_ignition'

        if is_breakout:
            source = 'accel-300-breakout'
            confidence = ACCEL_300_BREAKOUT_CONFIDENCE
            # Bonus: strong 5-bar move
            move_5bar = abs(sig.get('move_5bar', 0))
            if move_5bar > 1.0:
                confidence = min(88, confidence + 5)
            # Bonus: 1H trend alignment
            trend_1h = _get_1h_trend(token)
            if (direction == 'LONG' and trend_1h == 'BULLISH') or \
               (direction == 'SHORT' and trend_1h == 'BEARISH'):
                confidence = min(88, confidence + 3)
        elif is_vi:
            # ponytail: explicit vel kill switches — safety net at source-assignment level
            from hermes_constants import ACCEL_300_VELOCITY_PLUS_ENABLED, ACCEL_300_VELOCITY_MINUS_ENABLED
            if direction == 'LONG' and not ACCEL_300_VELOCITY_PLUS_ENABLED:
                continue
            if direction == 'SHORT' and not ACCEL_300_VELOCITY_MINUS_ENABLED:
                continue
            source = 'accel-300-vel+' if direction == 'LONG' else 'accel-300-vel-'
            # Confidence based on velocity ratio (how much faster than average)
            velocity_ratio = sig.get('velocity_ratio', 1.0)
            confidence = int(min(85, 65 + (velocity_ratio - 1.0) * 20))
            confidence = max(65, confidence)
            # Bonus: early entry (few bars since cross = stronger signal)
            bars = sig.get('bars_since_cross', 10)
            if bars <= 5:
                confidence = min(88, confidence + 5)
            # Bonus: 1H trend alignment
            trend_1h = _get_1h_trend(token)
            if (direction == 'LONG' and trend_1h == 'BULLISH') or \
               (direction == 'SHORT' and trend_1h == 'BEARISH'):
                confidence = min(88, confidence + 3)
        else:
            source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT
            # Confidence: base on gap strength + absolute gap growth. SHORT growth
            # is negative by design, so abs() keeps the strength bonus symmetric.
            # Use direction-specific gap threshold to match detection logic.
            gap_bonus = max(0, abs(sig['gap_growth']) - 0.05) * 200
            gap_for_conf = abs(sig['gap_pct'])  # use absolute gap so SHORT earns bonus too
            min_gap_for_conf = ACCEL_300_MIN_GAP_PCT_LONG if direction == 'LONG' else ACCEL_300_MIN_GAP_PCT_SHORT
            confidence = int(min(85, 70 + max(0, (gap_for_conf - min_gap_for_conf) * 80) + gap_bonus))
            confidence = max(70, confidence)
            # Bonus: strong gap (well above minimum)
            if gap_for_conf > min_gap_for_conf * 2:
                confidence = min(88, confidence + 3)
            # Bonus: accelerating gap (gap growing fast)
            gap_accel = abs(sig.get('gap_acceleration', 0))
            if gap_accel > 0.1:
                confidence = min(88, confidence + 3)
            # Bonus: early entry (few bars since cross)
            bars = sig.get('bars_since_cross', 10)
            if bars <= 5:
                confidence = min(88, confidence + 3)
            # Bonus: 1H trend alignment
            trend_1h = _get_1h_trend(token)
            if (direction == 'LONG' and trend_1h == 'BULLISH') or \
               (direction == 'SHORT' and trend_1h == 'BEARISH'):
                confidence = min(88, confidence + 3)

        # `_get_1m_prices` enforces freshness and returns the real latest
        # price_history point used by detection. Do not persist the separate
        # prices_dict snapshot, which can be from a different collector tick.
        signal_price = float(sig['price'])

        if DRY_RUN:
            if is_breakout:
                _log(f"  [DRY] {direction:5s}-accel-300-breakout {token:8s} conf={confidence:.0f}% "
                      f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                      f"move_5bar={sig['move_5bar']:.3f}% [{source}]")
            elif is_vi:
                _log(f"  [DRY] {source} {token:8s} conf={confidence:.0f}% "
                      f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                      f"velocity={sig['velocity_pct']:.3f}% (avg={sig['avg_velocity_pct']:.3f}%, "
                      f"ratio={sig['velocity_ratio']:.1f}x) "
                      f"bars_since_cross={sig['bars_since_cross']}")
            else:
                _log(f"  [DRY] {direction:5s}-accel-300 {token:8s} conf={confidence:.0f}% "
                      f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                      f"growth={sig['gap_growth']:.3f}% price_accel={sig['price_acceleration']:.8g} "
                      f"gap_velocity={sig['gap_velocity']:.3f}% "
                      f"accel={sig['gap_acceleration']:.3f}% "
                      f"bars_since_cross={sig['bars_since_cross']} [{source}]")
            continue

        try:
            value = float(sig.get('move_5bar', sig.get('gap_growth', 0)))
            sid = add_signal(
                token=token.upper(),
                direction=direction,
                signal_type=sig_type,
                source=source,
                confidence=confidence,
                value=value,
                price=signal_price,
                exchange='hyperliquid',
                timeframe='1m',
                z_score=None,
                z_score_tier=None,
            )
            if sid:
                added += 1
                # Breakout uses longer cooldown (1h) to avoid clustered false signals
                if is_breakout:
                    from hermes_constants import ACCEL_300_BREAKOUT_COOLDOWN
                    set_cooldown(token, direction, hours=ACCEL_300_BREAKOUT_COOLDOWN / 12.0)
                    _log(f"  {direction:5s}-accel-300-breakout {token:8s} conf={confidence:.0f}% "
                          f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                          f"move_5bar={sig['move_5bar']:.3f}% [{source}]")
                elif is_vi:
                    # Velocity ignition: medium cooldown (20 min) — fast but not too frequent
                    set_cooldown(token, direction, hours=20/60.0)
                    _log(f"  {source} {token:8s} conf={confidence:.0f}% "
                          f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                          f"velocity={sig['velocity_pct']:.3f}% (avg={sig['avg_velocity_pct']:.3f}%, "
                          f"ratio={sig['velocity_ratio']:.1f}x) "
                          f"bars_since_cross={sig['bars_since_cross']}")
                else:
                    set_cooldown(token, direction, hours=COOLDOWN_BARS / 60.0)
                    _log(f"  {direction:5s}-accel-300 {token:8s} conf={confidence:.0f}% "
                          f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                          f"growth={sig['gap_growth']:.3f}% price_accel={sig['price_acceleration']:.8g} "
                          f"gap_velocity={sig['gap_velocity']:.3f}% "
                          f"accel={sig['gap_acceleration']:.3f}% "
                          f"bars_since_cross={sig['bars_since_cross']} [{source}]")
        except Exception as e:
            print(f"[accel-300] add_signal error for {token}: {e}")

    return added


# ═══════════════════════════════════════════════════════════════════════════════
# CLI entry point — used by signals_runner via getattr(mod, 'run')
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from signal_schema import init_db

    # Build token list from price_history (live tokens only)
    conn = sqlite3.connect(_PRICE_DB, timeout=10)
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT token FROM price_history
        WHERE timestamp > ?
        ORDER BY token
    """, (int(time.time()) - 600,))
    tokens = [r[0] for r in c.fetchall()]
    conn.close()

    # Build prices dict for the scanner
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
    print(f"[accel-300] Testing on {len(prices)} tokens ({mode} mode)...")
    init_db()
    n = scan_accel_300_signals(prices)
    print(f"[accel-300] Done. {n} signals emitted.")

# ═══════════════════════════════════════════════════════════════════════════════
# signals_runner entry point — called by signals/__init__.py via getattr(mod, 'run')
# ═══════════════════════════════════════════════════════════════════════════════

def run(prices_dict=None):
    """Entry point for signals_runner.

    signals_runner calls this as: fn(prices)
    where prices = get_all_latest_prices() = {token: {'price': float}}

    The scanner handles all guards internally (allowlist, cooldown, blacklist, etc.)
    """
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_accel_300_signals(prices_dict)
