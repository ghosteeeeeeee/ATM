#!/usr/bin/env python3
"""
momentum_leaderboard.py — Top Movers Signal (pipeline-integrated).

Scans the HL tradable universe for biggest gainers/losers across multiple
timeframes, then decides direction: ride continuation or fade overextension.

Data: candles.db (5m/15m/1h) — zero external API calls.

Signal types:
  - mover_long  : LONG (momentum continuation or oversold bounce)
  - mover_short : SHORT (momentum continuation or blow-off fade)

Run:
    python3 signals/momentum_leaderboard.py           # live scan
    python3 signals/momentum_leaderboard.py --dry     # dry run (log only)
"""

import os
import sys
import sqlite3
import time

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
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

# ── Paths ─────────────────────────────────────────────────────────────────────
_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')

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
# Data fetch — candle close prices from candles.db
# ═══════════════════════════════════════════════════════════════════════════════

def _get_closes(token: str, table: str, limit: int) -> list:
    """Fetch close prices from candles.db, oldest first. Returns list of float."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute(f"""
            SELECT close FROM (
                SELECT close FROM {table}
                WHERE token = ?
                ORDER BY ts DESC
                LIMIT ?
            ) sub
            ORDER BY ts ASC
        """, (token.upper(), limit))
        rows = c.fetchall()
        return [r[0] for r in rows] if rows else []
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _get_candle_ts(token: str, table: str) -> int:
    """Get latest candle timestamp for staleness check."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute(f"""
            SELECT MAX(ts) FROM {table} WHERE token = ?
        """, (token.upper(),))
        row = c.fetchone()
        return row[0] if row and row[0] else 0
    except Exception:
        return 0
    finally:
        if conn:
            conn.close()


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
# Detection — rank and decide direction
# ═══════════════════════════════════════════════════════════════════════════════

def detect_leaderboard_signals() -> list:
    """
    Scan all tokens, compute returns, rank by move_score, decide direction.
    Returns list of signal dicts.
    """
    lb_5m, lb_15m, lb_1h = MOMENTUM_LEADERBOARD_RET_WINDOWS

    # Gather all tokens with 1h data
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("SELECT DISTINCT token FROM candles_1h")
        tokens = [r[0] for r in c.fetchall()]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()

    candidates = []

    for token in tokens:
        # Fetch candles
        closes_5m = _get_closes(token, 'candles_5m', lb_5m + 10)
        closes_15m = _get_closes(token, 'candles_15m', lb_15m + 10)
        closes_1h = _get_closes(token, 'candles_1h', lb_1h + 10)

        if not closes_1h or len(closes_1h) < lb_1h + 1:
            continue

        # Staleness check — skip if latest 1h candle is > 15 min old
        latest_ts = _get_candle_ts(token, 'candles_1h')
        if latest_ts and (time.time() - latest_ts) > 900:
            continue

        # Compute returns
        ret_5m = _compute_return(closes_5m, lb_5m) if len(closes_5m) >= lb_5m + 1 else None
        ret_15m = _compute_return(closes_15m, lb_15m) if len(closes_15m) >= lb_15m + 1 else None
        ret_1h = _compute_return(closes_1h, lb_1h)

        if ret_1h is None or ret_1h == 0:
            continue

        # Velocity for overextension detection (5m per-candle avg)
        vel_5m = _compute_velocity(closes_5m, lb_5m) if len(closes_5m) >= lb_5m + 1 else None

        # move_score: weighted absolute returns
        abs_1h = abs(ret_1h)
        abs_15m = abs(ret_15m) if ret_15m is not None else 0
        abs_5m = abs(ret_5m) if ret_5m is not None else 0
        move_score = abs_1h * 0.5 + abs_15m * 0.3 + abs_5m * 0.2

        if move_score < MOMENTUM_LEADERBOARD_MOVE_MIN:
            continue

        # Overextended filter — too risky to enter
        if ret_5m is not None and abs(ret_5m) > 3.0:
            continue

        # Direction decision
        direction = _decide_direction(ret_1h, ret_5m, ret_15m, vel_5m)
        if direction is None:
            continue

        # Confidence
        confidence = _compute_confidence(ret_1h, ret_5m, ret_15m, direction, vel_5m)

        candidates.append({
            'token': token,
            'direction': direction,
            'confidence': confidence,
            'move_score': move_score,
            'ret_1h': ret_1h,
            'ret_15m': ret_15m,
            'ret_5m': ret_5m,
        })

    # Rank by move_score, take top N
    candidates.sort(key=lambda x: x['move_score'], reverse=True)
    return candidates[:MOMENTUM_LEADERBOARD_TOP_N]


def _decide_direction(ret_1h, ret_5m, ret_15m, vel_5m) -> str | None:
    """
    Decide LONG or SHORT based on multi-timeframe returns.

    Logic:
      - 1h up + 5m still up → LONG (continuation)
      - 1h up + 5m reversing + fast velocity → SHORT (fade)
      - 1h down + 5m still down → SHORT (continuation)
      - 1h down + 5m bouncing + fast velocity → LONG (bounce)
    """
    if ret_5m is None:
        # No 5m data — direction from 1h sign only
        return 'LONG' if ret_1h > 0 else 'SHORT'

    fast = vel_5m is not None and abs(vel_5m) > 0.3  # 0.3% per candle = fast

    if ret_1h > 0:
        if ret_5m > 0:
            return 'LONG'   # trend continuation
        elif ret_5m < 0 and fast:
            return 'SHORT'  # fade the blow-off
        else:
            return 'LONG'   # 5m flat — still bullish trend
    else:
        if ret_5m < 0:
            return 'SHORT'  # breakdown continuation
        elif ret_5m > 0 and fast:
            return 'LONG'   # oversold bounce
        else:
            return 'SHORT'  # 5m flat — still bearish trend


def _compute_confidence(ret_1h, ret_5m, ret_15m, direction, vel_5m) -> int:
    """Confidence scaling based on confluence and speed."""
    conf = 75

    # Confluence: 15m and 1h agree on sign
    if ret_15m is not None:
        if (ret_1h > 0 and ret_15m > 0) or (ret_1h < 0 and ret_15m < 0):
            conf += 5

    # Elite velocity
    if vel_5m is not None and abs(vel_5m) > 0.5:
        conf += 5

    # Overextension penalty
    if ret_5m is not None and abs(ret_5m) > 2.0:
        conf -= 10

    return max(50, min(88, conf))


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

        if DRY_RUN:
            _log(f"  [DRY] {direction:5s}-mover {token:8s} "
                 f"move={cand['move_score']:.2f}% conf={cand['confidence']}% "
                 f"1h={cand['ret_1h']:+.2f}% [{source}]")
            continue

        try:
            price_closes = _get_closes(token, 'candles_1h', 2)
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
                timeframe='1h',
            )
            if sid:
                added += 1
                set_cooldown(token, direction, hours=MOMENTUM_LEADERBOARD_COOLDOWN_MIN / 60.0)
                _log(f"  {direction:5s}-mover {token:8s} "
                     f"move={cand['move_score']:.2f}% conf={cand['confidence']}% "
                     f"1h={cand['ret_1h']:+.2f}% [{source}]")
        except Exception as e:
            _log(f"[momentum_leaderboard] add_signal error for {token}: {e}")

    return added


# ═══════════════════════════════════════════════════════════════════════════════
# CLI entry point — used by signals_runner via getattr(mod, 'run')
# ═══════════════════════════════════════════════════════════════════════════════

def run():
    """Entry point for signals_runner. No prices_dict needed — reads from candles.db."""
    return scan_leaderboard_signals()


if __name__ == '__main__':
    from signal_schema import init_db
    init_db()
    n = scan_leaderboard_signals()
    print(f'momentum_leaderboard: {n} signals emitted')
