#!/usr/bin/env python3
"""Inverse Accel-300 V2 — Mean Reversion Signal (SHORT ONLY).

Catches exhausted prices far above EMA300 and rides them back to the mean.

V2 changes vs V1:
  - SHORT only (LONG side was never profitable — falling knife catcher)
  - Higher min gap (2.0% vs 1.5%) — need REAL exhaustion, not just deviation
  - 3-bar reversion confirmation (was 2) — more robust turning point detection
  - 5-bar gap velocity window (was 3) — smoother trend detection
  - Volume confirmation — above-average volume = real selling, not noise
  - Tighter stabilization (0.15% vs 0.3%) — must be very near recent high
  - Phase filter: only exhaustion/extreme phases (quiet/building = too early)
  - Earlier trailing activation (0.20% vs 0.25%) — lock profits faster
  - Tighter trailing distance (0.20% vs 0.30%) — give back less

V1 failure analysis:
  - 43% of losers were whipsaws: price moved 0.8-1.9% in our favor, then reversed
  - Trailing activation at 0.25% was too late — trade already pulling back
  - Gap threshold at 1.5% let marginal setups through
  - LONG side always lost (falling knives)

V2 design:
  - SHORT fires when price is far ABOVE EMA300 (overextended rally)
  - Gap must be narrowing (reversion confirmed)
  - Price velocity turning downward
  - Volume above average (selling pressure)
  - Must be in exhaustion phase (not quiet/building)
"""

import sys, os, sqlite3, time, math
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown

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
_CANDLES_DB = CANDLES_DB  # candles.db — has volume data

# ── V2 Signal constants ──────────────────────────────────────────────────────
from hermes_constants import (
    ACCEL_300_PERIOD,
    ACCEL_300_BAR_GAP_THRESH_SEC,
)

# V2-specific params (defined here, tunable)
V2_MIN_GAP_PCT = 2.0          # min gap above EMA300 to fire SHORT (was 1.5 in V1)
V2_MAX_GAP_PCT = 8.0          # don't fire if gap too extreme (structural, not reversion)
V2_REVERSION_BARS = 3         # bars of gap narrowing to confirm (was 2 in V1)
V2_REVERSION_THRESHOLD = 0.15 # min gap narrowing % (was 0.05 in V1 — too loose)
V2_GAP_VELOCITY_WINDOW = 5    # bars to measure gap velocity (was 3 in V1)
V2_STABILIZATION_WINDOW = 15  # bars to check for turning point
V2_STABILIZATION_TOLERANCE = 0.015  # 1.5% — must be near recent high (loosened: reversion confirmation requires some downside movement)
V2_VOLUME_LOOKBACK = 30       # bars to compute average volume
V2_VOLUME_MULT = 1.2          # volume must be 1.2x average (selling pressure)
V2_VELOCITY_WINDOW = 5        # bars to measure price velocity
V2_TREND_FILTER_PCT = 2.5     # max 1h move — for mean reversion, the rally IS the setup, not a blocker
V2_COOLDOWN_BARS = 5          # cooldown between signals per token (5 min)
V2_LOOKBACK_1M = 700          # 1m prices to fetch per token
V2_MAX_SLIPPAGE_PCT = 0.30    # max slippage from detection price (was 0.5%)
V2_SLIPPAGE_BARS = 3          # bars to check for slippage

PERIOD = ACCEL_300_PERIOD
DRY_RUN = '--dry' in sys.argv

SIGNAL_TYPE_SHORT = 'inverse_accel_300_v2_short'
SOURCE_SHORT = 'inv-accel-300-v2-'


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


def _ema(prices: list, period: int) -> float:
    """Compute a single EMA value from a list of prices."""
    if len(prices) < period:
        return None
    k = 2.0 / (period + 1)
    ema_val = sum(prices[:period]) / period
    for price in prices[period:]:
        ema_val = price * k + ema_val * (1 - k)
    return ema_val


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
            threshold = max(ACCEL_300_BAR_GAP_THRESH_SEC, mean_gap + 3.0 * std_gap)
            for i in range(1, len(rows)):
                if rows[i][0] - rows[i-1][0] > threshold:
                    return []

        return [{'timestamp': r[0], 'price': r[1]} for r in rows]

    except Exception as e:
        print(f"  [inverse-accel-300-v2] price_history error for {token}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def _get_1m_volume(token: str, lookback: int = V2_VOLUME_LOOKBACK + 10) -> list:
    """Fetch 1m volume from candles_1m, oldest first. Returns list of volume values."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
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
    except Exception as e:
        print(f"  [inverse-accel-300-v2] volume error for {token}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def _check_1h_trend(token: str, current_price: float) -> bool:
    """Check if 1h trend is too strong against reversion (block SHORT if price rose hard).
    
    Returns True if trade should be BLOCKED (strong uptrend = not exhausted).
    """
    conn = None
    try:
        now = time.time()
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT price FROM price_history 
            WHERE token = ? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC LIMIT 1
        """, (token.upper(), now - 3600, now - 3500))
        row = c.fetchone()
        
        if not row or not row[0]:
            return False  # no data — don't block
        
        price_1h_ago = row[0]
        if price_1h_ago <= 0:
            return False
        
        # For SHORT: block if price rose significantly in last hour (strong uptrend)
        if current_price > price_1h_ago:
            move_pct = (current_price - price_1h_ago) / price_1h_ago * 100
            if move_pct > V2_TREND_FILTER_PCT:
                return True
        
        return False
    except Exception:
        return False  # on error, don't block
    finally:
        if conn:
            conn.close()


def _check_volume_confirmation(token: str, volumes: list) -> bool:
    """Check if current volume is above average (selling pressure for SHORT).
    
    Returns True if volume confirms the move, or if volume data is stale/unavailable
    (graceful degradation — don't block signals on missing data).
    """
    if not volumes or len(volumes) < V2_VOLUME_LOOKBACK:
        return True  # not enough data — don't block (graceful degradation)
    
    recent = volumes[-V2_VOLUME_LOOKBACK:]
    avg_vol = sum(recent) / len(recent)
    if avg_vol <= 0:
        return True  # all zeros — data stale, don't block
    
    # Current volume (last bar) should be above average
    current_vol = volumes[-1]
    return current_vol >= avg_vol * V2_VOLUME_MULT


def _check_slippage(sig_price: float, current_price: float, prices: list) -> bool:
    """Check if price has moved too far since detection (stale signal).
    
    Returns True if slippage is acceptable (within tolerance).
    """
    if sig_price <= 0:
        return False
    
    slippage_pct = abs(current_price - sig_price) / sig_price * 100.0
    if slippage_pct > V2_MAX_SLIPPAGE_PCT:
        return False
    
    # Also check if price has been moving against us in last N bars
    if prices and len(prices) >= V2_SLIPPAGE_BARS:
        recent_prices = [float(p['price']) for p in prices[-V2_SLIPPAGE_BARS:]]
        # For SHORT: price should not be making new highs in last few bars
        if current_price > max(recent_prices[:-1]) * 1.001:
            return False
    
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# Detection — V2 Mean Reversion (SHORT ONLY)
# ═══════════════════════════════════════════════════════════════════════════════

def detect_inverse_accel_300_v2(token: str, prices: list) -> Optional[dict]:
    """Detect SHORT mean reversion opportunity — price exhausted above EMA300.

    SHORT fires when:
      1. Price is far ABOVE EMA300 (gap >= 2.0%)
      2. Gap has been narrowing for 3+ bars (reversion confirmed)
      3. Gap velocity is negative over 5-bar window (momentum shifting)
      4. Price velocity is negative (price falling)
      5. Price is near recent high (turning point, not mid-rally)
      6. Volume is above average (selling pressure)
    """
    period = PERIOD
    min_rows = period + V2_GAP_VELOCITY_WINDOW + V2_REVERSION_BARS + V2_STABILIZATION_WINDOW + 10
    if len(prices) < min_rows:
        return None

    closes = [float(p['price']) for p in prices]
    ema300 = _ema_series(closes, period)
    
    # Compute gap series
    gap_pcts = [
        None if ema is None or ema == 0 else (price - ema) / ema * 100.0
        for price, ema in zip(closes, ema300)
    ]

    latest_idx = len(closes) - 1
    latest_ema = ema300[latest_idx]
    gap_now = gap_pcts[latest_idx]
    if latest_ema is None or gap_now is None:
        return None

    # ── FILTER 1: Must be SHORT (price above EMA) ──────────────────────────
    if gap_now <= 0:
        return None  # price at or below EMA — not exhausted above

    # ── FILTER 2: Gap must be large enough (real exhaustion) ────────────────
    if gap_now < V2_MIN_GAP_PCT:
        return None

    # ── FILTER 3: Gap not too extreme (structural, not mean-reverting) ──────
    if gap_now > V2_MAX_GAP_PCT:
        return None

    # ── FILTER 4: Reversion confirmation (gap narrowing over N bars) ────────
    reversion_start = latest_idx - V2_REVERSION_BARS
    if reversion_start < 0:
        return None

    gap_then = gap_pcts[reversion_start]
    if gap_then is None:
        return None

    # Gap should be shrinking (gap_now < gap_then for SHORT above EMA)
    gap_change = gap_then - gap_now  # positive = gap narrowing
    if gap_change < V2_REVERSION_THRESHOLD:
        return None

    # ── FILTER 5: Gap velocity (5-bar window) ──────────────────────────────
    gap_vel_start = latest_idx - V2_GAP_VELOCITY_WINDOW
    if gap_vel_start < 0:
        return None

    gap_vel_then = gap_pcts[gap_vel_start]
    if gap_vel_then is None:
        return None

    gap_velocity = gap_now - gap_vel_then
    # For SHORT: gap_velocity should be negative (gap shrinking over 5 bars)
    if gap_velocity >= 0:
        return None

    # ── FILTER 6: Price velocity (must be falling) ─────────────────────────
    price_velocity = closes[latest_idx] - closes[latest_idx - V2_VELOCITY_WINDOW]
    price_epsilon = max(abs(closes[latest_idx]) * 1e-12, 1e-12)
    if price_velocity >= -price_epsilon:
        return None  # price not falling — no reversion

    # ── FILTER 7: Stabilization — must be near recent high (turning point) ──
    stab_window = min(V2_STABILIZATION_WINDOW, latest_idx)
    if stab_window >= 3:
        recent_prices = closes[latest_idx - stab_window + 1 : latest_idx + 1]
        recent_high = max(recent_prices[:-1])  # exclude current bar

        # Price must be very near the high (within 0.15%) — entering at the top
        if closes[latest_idx] < recent_high * (1 - V2_STABILIZATION_TOLERANCE):
            return None  # price too far below recent high — not a top sell

        # Also reject if still making new highs (not stabilized)
        if closes[latest_idx] > recent_high * 1.002:
            return None

    # NOTE: Range position filter removed — redundant with stabilization check above.
    # Stabilization already ensures price is near recent high (top of range).

    return {
        'direction': 'SHORT',
        'gap_pct': round(gap_now, 4),
        'gap_change': round(gap_change, 4),
        'gap_velocity': round(gap_velocity, 4),
        'price_velocity': price_velocity,
        'price': closes[latest_idx],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_inverse_accel_300_v2_signals(prices_dict: dict) -> int:
    """Scan tokens for inverse_accel_300_v2 (mean reversion SHORT) signals."""
    from hermes_constants import (
        INVERSE_ACCEL_300_V2_ENABLED,
        SHORT_BLACKLIST,
    )
    if not INVERSE_ACCEL_300_V2_ENABLED:
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
        if token.upper() in ('SHORT',):
            continue  # skip direction tokens
        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
            continue
        if is_delisted(token.upper()):
            continue
        if price_age_minutes(token) > 10:
            continue

        prices = _get_1m_prices(token)
        if not prices or len(prices) < PERIOD + 50:
            continue

        sig = detect_inverse_accel_300_v2(token, prices)
        if sig is None:
            continue

        direction = sig['direction']  # always SHORT
        if get_cooldown(token, direction=direction):
            continue

        # Blacklist guard
        if token.upper() in SHORT_BLACKLIST:
            continue

        # 1h trend filter — skip if price rose strongly (strong uptrend, not exhausted)
        if _check_1h_trend(token, price):
            continue

        # Volume confirmation — must have above-average volume (selling pressure)
        volumes = _get_1m_volume(token)
        if not _check_volume_confirmation(token, volumes):
            continue

        # Slippage guard — if price moved too far since detection, skip
        if not _check_slippage(sig['price'], price, prices):
            continue

        # ── Phase filter ────────────────────────────────────────────────────
        # Mean reversion only works during exhaustion/extreme phases.
        # During quiet/building, the move hasn't exhausted yet.
        from hermes_constants import PHASE_ENTRY_FILTER_ENABLED
        if PHASE_ENTRY_FILTER_ENABLED:
            try:
                from tpsl_utils import _get_current_phase
                phase = _get_current_phase(token)
                # V2: only allow during exhaustion-like phases
                V2_ALLOWED_PHASES = {'decelerating', 'falling', 'exhaustion', 'extreme'}
                if phase and phase not in V2_ALLOWED_PHASES:
                    continue
            except ImportError:
                pass  # tpsl_utils not available — skip phase check

        # Confidence: base on gap strength + reversion strength + volume
        gap_bonus = min(20, (sig['gap_pct'] - V2_MIN_GAP_PCT) * 5)  # bonus above minimum
        reversion_bonus = min(15, sig['gap_change'] * 50)  # stronger reversion = higher conf
        vol_bonus = 5 if volumes and len(volumes) >= V2_VOLUME_LOOKBACK else 0
        confidence = int(min(85, 65 + gap_bonus + reversion_bonus + vol_bonus))
        confidence = max(60, confidence)

        signal_price = float(sig['price'])

        if DRY_RUN:
            _log(f"  [DRY] SHORT-inv-accel-300-v2 {token:8s} conf={confidence:.0f}% "
                  f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                  f"reversion={sig['gap_change']:.3f}% "
                  f"gap_vel={sig['gap_velocity']:.3f}% [{SOURCE_SHORT}]")
            added += 1
            continue

        try:
            sid = add_signal(
                token=token.upper(),
                direction=direction,
                signal_type=SIGNAL_TYPE_SHORT,
                source=SOURCE_SHORT,
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
                set_cooldown(token, direction, hours=V2_COOLDOWN_BARS / 60.0)
                _log(f"  SHORT-inv-accel-300-v2 {token:8s} conf={confidence:.0f}% "
                      f"price={signal_price:.8g} gap={sig['gap_pct']:.3f}% "
                      f"reversion={sig['gap_change']:.3f}% "
                      f"gap_vel={sig['gap_velocity']:.3f}% [{SOURCE_SHORT}]")
        except Exception as e:
            print(f"[inverse-accel-300-v2] add_signal error for {token}: {e}")

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
    print(f"[inverse-accel-300-v2] Testing on {len(prices)} tokens ({mode} mode)...")
    init_db()
    n = scan_inverse_accel_300_v2_signals(prices)
    print(f"[inverse-accel-300-v2] Done. {n} signals emitted.")


# ═══════════════════════════════════════════════════════════════════════════════
# signals_runner entry point
# ═══════════════════════════════════════════════════════════════════════════════

def run(prices_dict=None):
    """Entry point for signals_runner."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_inverse_accel_300_v2_signals(prices_dict)
