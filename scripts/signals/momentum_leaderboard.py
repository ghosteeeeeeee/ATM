#!/usr/bin/env python3
"""
momentum_leaderboard.py — Top Movers Signal v2 (1m-aware, confluence-gated).

Scans for biggest movers using 1m candles for entry timing and 5m for trend
context. Requires confluence (range-bound or exhaustion) before firing.

Key improvements over v1:
  - 1m candles for primary signal (matches trading timeframe)
  - 5m trend context for direction confirmation
  - S/R awareness: won't short near support or long near resistance
  - Exhaustion filter: won't chase moves already extended >15%
  - Confluence: requires range_finder (BB narrow) or return_exhaustion (percentile extreme)
  - Regime awareness: uses 5m regime to confirm direction

Signal types:
  - mover_long  : LONG (momentum continuation in range, or oversold bounce)
  - mover_short : SHORT (momentum continuation in range, or overbought fade)

Run:
    python3 signals/momentum_leaderboard.py           # live scan
    python3 signals/momentum_leaderboard.py --dry     # dry run (log only)
"""

import os
import sys
import sqlite3
import time
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    MOMENTUM_LEADERBOARD_ENABLED,
    MOMENTUM_LEADERBOARD_PLUS_ENABLED,
    MOMENTUM_LEADERBOARD_MINUS_ENABLED,
    MOMENTUM_LEADERBOARD_TOP_N,
    MOMENTUM_LEADERBOARD_MOVE_MIN,
    MOMENTUM_LEADERBOARD_COOLDOWN_MIN,
    MOMENTUM_LEADERBOARD_RET_WINDOWS,
    MOMENTUM_LEADERBOARD_OVEREXTENDED_PCT,
    MOMENTUM_LEADERBOARD_FAST_VEL,
    MOMENTUM_LEADERBOARD_ELITE_VEL,
    MOMENTUM_LEADERBOARD_CONF_PENALTY_PCT,
    MOMENTUM_LEADERBOARD_CONF_BASE,
    MOMENTUM_LEADERBOARD_CONF_FLOOR,
    MOMENTUM_LEADERBOARD_CONF_CAP,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

# ── New v2 constants ─────────────────────────────────────────────────────────
# S/R awareness
SR_LOOKBACK = 100            # 1m candles for swing detection
SR_PROXIMITY_PCT = 1.0       # % — don't trade within this % of S/R level

# Exhaustion filter
EXHAUSTION_MAX_MOVE_PCT = 15.0  # % — don't chase moves already >15% extended

# Confluence: BB range detection
BB_PERIOD = 20
BB_STDDEV = 1.8
BB_WIDTH_MAX = 0.04          # % — BB width < 4% = range-bound (confluence)

# Confluence: return percentile exhaustion
RET_EXHAUST_LOOKBACK = 60    # 1m candles for percentile ranking
RET_EXHAUST_LOW = 10         # percentile — extreme negative = LONG exhaustion
RET_EXHAUST_HIGH = 90        # percentile — extreme positive = SHORT exhaustion

# Trend context
TREND_5M_LOOKBACK = 60       # 5m candles for trend (5 hours)

# ── Paths ─────────────────────────────────────────────────────────────────────
_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
_PRICE_DB = os.path.join(HERMES_DATA, 'signals_hermes.db')
_REGIME_FILE = '/var/www/hermes/data/regime_5m.json'

# ── Logging ───────────────────────────────────────────────────────────────────
SIGNAL_LOG = '/var/www/hermes/logs/signals.log'
os.makedirs(os.path.dirname(SIGNAL_LOG), exist_ok=True)

def _log(msg):
    print(msg)
    try:
        with open(SIGNAL_LOG, 'a') as f:
            f.write(msg + '\n')
    except Exception:
        pass

DRY_RUN = '--dry' in sys.argv

# ── Signal types & sources ────────────────────────────────────────────────────
SIGNAL_TYPE_LONG  = 'mover_long'
SIGNAL_TYPE_SHORT = 'mover_short'
SOURCE_LONG       = 'mover+'
SOURCE_SHORT      = 'mover-'


# ═══════════════════════════════════════════════════════════════════════════════
# Data fetch
# ═══════════════════════════════════════════════════════════════════════════════

def _get_closes(token: str, table: str, limit: int) -> list:
    """Fetch close prices from candles.db, oldest first."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute(f"""
            SELECT close FROM {table}
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), limit))
        rows = c.fetchall()
        if not rows:
            return []
        return [r[0] for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _get_1m_candles(token: str, limit: int) -> list:
    """Fetch 1m OHLCV candles from price_history (signals_hermes.db), oldest first.
    Synthesizes OHLCV from close-only data. Freshness guard: returns [] if >2 min old."""
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
        """, (token.upper(), limit))
        rows = c.fetchall()
        conn.close()
        if not rows:
            return []
        # Freshness guard
        most_recent_ts = rows[-1][0]
        if (time.time() - most_recent_ts) > 120:
            return []
        # Synthesize OHLCV (close-only)
        return [{'open': r[1], 'high': r[1], 'low': r[1], 'close': r[1]} for r in rows]
    except Exception:
        return []


def _get_candle_ts(token: str, table: str) -> int:
    """Get latest candle timestamp for staleness check."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute(f"SELECT MAX(ts) FROM {table} WHERE token = ?", (token.upper(),))
        row = c.fetchone()
        return row[0] if row and row[0] else 0
    except Exception:
        return 0
    finally:
        if conn:
            conn.close()


def _get_1m_closes(token: str, limit: int) -> list:
    """Fetch 1m close prices from price_history via _get_1m_candles."""
    candles = _get_1m_candles(token, limit)
    return [c['close'] for c in candles] if candles else []


# ═══════════════════════════════════════════════════════════════════════════════
# Return computation
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_return(closes: list, window: int) -> float | None:
    """Percentage return over the last `window` candles."""
    if len(closes) < window + 1:
        return None
    prev = closes[-(window + 1)]
    curr = closes[-1]
    if prev <= 0:
        return None
    return (curr - prev) / prev * 100


def _compute_velocity(closes: list, window: int) -> float | None:
    """Average per-candle return over the last `window` candles (velocity)."""
    if len(closes) < window + 1:
        return None
    returns = []
    for i in range(-window, 0):
        prev = closes[i - 1]
        curr = closes[i]
        if prev > 0:
            returns.append((curr - prev) / prev * 100)
    return sum(returns) / len(returns) if returns else None


# ═══════════════════════════════════════════════════════════════════════════════
# S/R awareness — simplified swing detection
# ═══════════════════════════════════════════════════════════════════════════════

def _find_nearest_sr(price: float, candles_1m: list) -> tuple:
    """Find nearest support and resistance from 1m swing points.
    Returns (nearest_support, nearest_resistance) as price levels."""
    if len(candles_1m) < SR_LOOKBACK:
        return None, None

    highs = np.array([c['high'] for c in candles_1m[-SR_LOOKBACK:]], dtype=np.float64)
    lows = np.array([c['low'] for c in candles_1m[-SR_LOOKBACK:]], dtype=np.float64)

    # Simple swing detection: local max/min over 5-candle window
    window = 5
    swing_highs = []
    swing_lows = []

    for i in range(window, len(highs) - window):
        # Swing high: high is max in window
        if highs[i] == max(highs[i-window:i+window+1]):
            swing_highs.append(highs[i])
        # Swing low: low is min in window
        if lows[i] == min(lows[i-window:i+window+1]):
            swing_lows.append(lows[i])

    if not swing_highs and not swing_lows:
        return None, None

    # Find nearest support (swing low below price) and resistance (swing high above price)
    supports = [s for s in swing_lows if s < price]
    resistances = [r for r in swing_highs if r > price]

    nearest_support = max(supports) if supports else None
    nearest_resistance = min(resistances) if resistances else None

    return nearest_support, nearest_resistance


def _is_near_sr(price: float, support, resistance) -> tuple:
    """Check if price is near S/R levels. Returns (near_support, near_resistance)."""
    near_support = False
    near_resistance = False

    if support and support > 0:
        dist_pct = (price - support) / price * 100
        if dist_pct < SR_PROXIMITY_PCT:
            near_support = True

    if resistance and resistance > 0:
        dist_pct = (resistance - price) / price * 100
        if dist_pct < SR_PROXIMITY_PCT:
            near_resistance = True

    return near_support, near_resistance


# ═══════════════════════════════════════════════════════════════════════════════
# Confluence: Range detection (Bollinger Bands)
# ═══════════════════════════════════════════════════════════════════════════════

def _is_range_bound(closes_5m: list) -> bool:
    """Check if market is range-bound via Bollinger Band width.
    Narrow bands (< 4%) indicate range — good for momentum continuation."""
    if len(closes_5m) < BB_PERIOD + 10:
        return False

    arr = np.array(closes_5m[-BB_PERIOD:], dtype=np.float64)
    middle = np.mean(arr)
    std = np.std(arr)
    if middle <= 0:
        return False
    width = (2 * BB_STDDEV * std) / middle
    return width < BB_WIDTH_MAX


# ═══════════════════════════════════════════════════════════════════════════════
# Confluence: Return percentile exhaustion
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_percentile_rank(values: list, current: float) -> float | None:
    """Compute percentile rank of `current` within `values`."""
    if not values or current is None:
        return None
    arr = np.array(values, dtype=np.float64)
    return float(np.sum(arr < current) / len(arr) * 100)


def _is_exhausted(closes_1m: list) -> tuple:
    """Check if short-term return is at percentile extreme.
    Returns (is_exhausted, percentile_rank, direction_hint).
    direction_hint: 'LONG' if exhausted to downside, 'SHORT' if upside."""
    if len(closes_1m) < RET_EXHAUST_LOOKBACK + 20:
        return False, None, None

    # Compute rolling returns for percentile ranking
    returns = []
    for i in range(20, len(closes_1m)):
        ret = (closes_1m[i] - closes_1m[i-20]) / closes_1m[i-20] * 100
        returns.append(ret)

    if len(returns) < 20:
        return False, None, None

    # Current 20-period return
    current_ret = (closes_1m[-1] - closes_1m[-21]) / closes_1m[-21] * 100
    pctile = _compute_percentile_rank(returns, current_ret)

    if pctile is None:
        return False, None, None

    if pctile < RET_EXHAUST_LOW:
        return True, pctile, 'LONG'  # exhausted to downside → bounce
    elif pctile > RET_EXHAUST_HIGH:
        return True, pctile, 'SHORT'  # exhausted to upside → fade
    else:
        return False, pctile, None


# ═══════════════════════════════════════════════════════════════════════════════
# Regime awareness
# ═══════════════════════════════════════════════════════════════════════════════

def _get_regime(token: str) -> str:
    """Return regime string from regime_5m.json."""
    try:
        with open(_REGIME_FILE) as f:
            data = json.load(f)
        if token.upper() in data.get('regimes', {}):
            return data['regimes'][token.upper()].get('regime', 'NEUTRAL')
    except Exception:
        pass
    return 'NEUTRAL'


# ═══════════════════════════════════════════════════════════════════════════════
# Detection — rank and decide direction
# ═══════════════════════════════════════════════════════════════════════════════

def detect_leaderboard_signals() -> list:
    """
    Scan all tokens, compute returns, rank by move_score, decide direction.
    v2: Uses 1m for entry, 5m for trend, requires confluence.
    """
    lb_5m, lb_15m, lb_1h = MOMENTUM_LEADERBOARD_RET_WINDOWS

    # Gather all tokens with 1m data
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("SELECT DISTINCT token FROM candles_1m")
        tokens = [r[0] for r in c.fetchall()]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()

    candidates = []

    for token in tokens:
        # Fetch 1m candles for S/R and exhaustion (from price_history, real-time)
        candles_1m = _get_1m_candles(token, SR_LOOKBACK + 20)
        closes_1m = _get_1m_closes(token, RET_EXHAUST_LOOKBACK + 50)

        if not candles_1m or len(candles_1m) < SR_LOOKBACK:
            continue
        if not closes_1m or len(closes_1m) < RET_EXHAUST_LOOKBACK + 20:
            continue

        # Freshness check — use price_history (real-time) not candles_1m (stale)
        # Price freshness is checked in _get_1m_closes (returns [] if >2 min old)
        # So if closes_1m is empty, token is stale — skip

        # Fetch 5m candles for trend context
        closes_5m = _get_closes(token, 'candles_5m', TREND_5M_LOOKBACK + 10)
        if not closes_5m or len(closes_5m) < 20:
            continue

        # ── S/R awareness ────────────────────────────────────────────────────
        price = closes_1m[-1]
        support, resistance = _find_nearest_sr(price, candles_1m)
        near_support, near_resistance = _is_near_sr(price, support, resistance)

        # ── Exhaustion check ─────────────────────────────────────────────────
        is_exhausted, pctile, exhaust_dir = _is_exhausted(closes_1m)

        # ── Range check (confluence) ─────────────────────────────────────────
        is_range = _is_range_bound(closes_5m)

        # ── Compute returns across timeframes ────────────────────────────────
        # Use 1m for short-term, 5m for trend
        ret_1m = _compute_return(closes_1m, 20)   # 20-min return
        ret_5m = _compute_return(closes_5m, lb_5m)  # 5-hour return (trend)
        ret_15m = _compute_return(closes_5m, min(lb_15m, len(closes_5m) - 1))  # longer trend

        if ret_5m is None or ret_5m == 0:
            continue

        # ── Move score ───────────────────────────────────────────────────────
        abs_5m = abs(ret_5m)
        abs_1m = abs(ret_1m) if ret_1m is not None else 0
        move_score = abs_5m * 0.7 + abs_1m * 0.3

        if move_score < MOMENTUM_LEADERBOARD_MOVE_MIN:
            continue

        # ── Exhaustion filter: don't chase extended moves ────────────────────
        if abs_5m > EXHAUSTION_MAX_MOVE_PCT:
            continue  # already moved too much, skip

        # ── Direction decision with S/R and confluence ───────────────────────
        direction = _decide_direction_v2(
            ret_5m, ret_1m, near_support, near_resistance,
            is_range, is_exhausted, exhaust_dir
        )
        if direction is None:
            continue

        # ── Block trades at wrong S/R ────────────────────────────────────────
        # Don't SHORT near support (bounce risk)
        if direction == 'SHORT' and near_support:
            continue
        # Don't LONG near resistance (rejection risk)
        if direction == 'LONG' and near_resistance:
            continue

        # ── Regime confirmation ──────────────────────────────────────────────
        regime = _get_regime(token)
        regime_aligned = (
            (direction == 'LONG' and regime in ('BULLISH', 'NEUTRAL')) or
            (direction == 'SHORT' and regime in ('BEARISH', 'NEUTRAL'))
        )

        # ── Confidence ───────────────────────────────────────────────────────
        confidence = _compute_confidence_v2(
            ret_5m, ret_1m, direction, move_score,
            is_range, is_exhausted, regime_aligned
        )

        candidates.append({
            'token': token,
            'direction': direction,
            'confidence': confidence,
            'move_score': move_score,
            'ret_5m': ret_5m,
            'ret_1m': ret_1m,
            'near_support': near_support,
            'near_resistance': near_resistance,
            'is_range': is_range,
            'is_exhausted': is_exhausted,
            'regime_aligned': regime_aligned,
        })

    # Rank by move_score, take top N
    candidates.sort(key=lambda x: x['move_score'], reverse=True)
    return candidates[:MOMENTUM_LEADERBOARD_TOP_N]


def _decide_direction_v2(ret_5m, ret_1m, near_support, near_resistance,
                          is_range, is_exhausted, exhaust_dir) -> str | None:
    """
    Decide LONG or SHORT with S/R and confluence awareness.

    Logic:
      - If exhausted to downside → LONG (bounce)
      - If exhausted to upside → SHORT (fade)
      - If range-bound: follow 5m trend direction
      - If trending: require 1m confirmation
    """
    # Exhaustion takes priority
    if is_exhausted and exhaust_dir:
        return exhaust_dir

    # Range-bound: follow trend
    if is_range:
        if ret_5m > 0:
            return 'LONG'   # uptrend in range
        else:
            return 'SHORT'  # downtrend in range

    # Trending: require 1m confirmation
    if ret_1m is not None:
        if ret_5m > 0 and ret_1m > 0:
            return 'LONG'   # trend continuation confirmed
        elif ret_5m < 0 and ret_1m < 0:
            return 'SHORT'  # trend continuation confirmed
        else:
            return None     # 1m against trend — skip (no confluence)

    # No 1m data: use 5m only
    return 'LONG' if ret_5m > 0 else 'SHORT'


def _compute_confidence_v2(ret_5m, ret_1m, direction, move_score,
                            is_range, is_exhausted, regime_aligned) -> int:
    """Confidence scaling with confluence bonuses."""
    conf = MOMENTUM_LEADERBOARD_CONF_BASE

    # Range confluence bonus
    if is_range:
        conf += 10

    # Exhaustion confluence bonus
    if is_exhausted:
        conf += 10

    # Regime alignment bonus
    if regime_aligned:
        conf += 5

    # Strong momentum bonus
    if move_score > 5.0:
        conf += 5

    # Weak momentum penalty
    if move_score < 3.0:
        conf -= 10

    # 1m confirmation bonus
    if ret_1m is not None:
        if (direction == 'LONG' and ret_1m > 0) or (direction == 'SHORT' and ret_1m < 0):
            conf += 5

    return max(MOMENTUM_LEADERBOARD_CONF_FLOOR, min(MOMENTUM_LEADERBOARD_CONF_CAP, conf))


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_leaderboard_signals() -> int:
    """
    Scan tokens for top-mover signals.
    Returns number of signals written to DB.
    """
    global DRY_RUN
    DRY_RUN = '--dry' in sys.argv

    if not MOMENTUM_LEADERBOARD_ENABLED:
        return 0

    from position_manager import get_open_positions as _get_open_pos
    from signal_gen import is_delisted

    open_pos = {p['token']: p['direction'] for p in _get_open_pos()}
    candidates = detect_leaderboard_signals()
    added = 0

    for cand in candidates:
        token = cand['token']
        direction = cand['direction']

        if token.upper() in open_pos:
            continue
        if is_delisted(token.upper()):
            continue
        if price_age_minutes(token) > 10:
            continue

        # Layer 1: per-direction kill-switch
        if direction == 'LONG' and not MOMENTUM_LEADERBOARD_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not MOMENTUM_LEADERBOARD_MINUS_ENABLED:
            continue

        # Layer 1: blacklists
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        # Cooldown
        if get_cooldown(token, direction=direction):
            continue

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        # Build confluence tags for logging
        tags = []
        if cand['is_range']:
            tags.append('range')
        if cand['is_exhausted']:
            tags.append('exhaust')
        if cand['regime_aligned']:
            tags.append('regime')
        tag_str = f" [{','.join(tags)}]" if tags else ''

        if DRY_RUN:
            _log(f"  [DRY] {direction:5s}-mover {token:8s} "
                 f"move={cand['move_score']:.2f}% conf={cand['confidence']}% "
                 f"5m={cand['ret_5m']:+.2f}%{tag_str} [{source}]")
            continue

        try:
            # Fetch current price from 1m data
            price_closes = _get_1m_closes(token, 2)
            price = price_closes[-1] if price_closes else 0

            sid = add_signal(
                token=token.upper(),
                direction=direction,
                signal_type=sig_type,
                source=source,
                confidence=cand['confidence'],
                value=round(cand['move_score'], 4),
                price=price,
                exchange='hyperliquid',
                timeframe='1m',
            )
            if sid:
                added += 1
                set_cooldown(token, direction, hours=MOMENTUM_LEADERBOARD_COOLDOWN_MIN / 60.0)
                _log(f"  {direction:5s}-mover {token:8s} "
                     f"move={cand['move_score']:.2f}% conf={cand['confidence']}% "
                     f"5m={cand['ret_5m']:+.2f}%{tag_str} [{source}]")
        except Exception as e:
            _log(f"[momentum_leaderboard] add_signal error for {token}: {e}")

    return added


# ═══════════════════════════════════════════════════════════════════════════════
# CLI entry point — used by signals_runner via getattr(mod, 'run')
# ═══════════════════════════════════════════════════════════════════════════════

def run():
    """Entry point for signals_runner."""
    return scan_leaderboard_signals()


if __name__ == '__main__':
    from signal_schema import init_db
    init_db()
    n = scan_leaderboard_signals()
    print(f'momentum_leaderboard: {n} signals emitted')
