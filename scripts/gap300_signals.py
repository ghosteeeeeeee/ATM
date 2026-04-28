#!/usr/bin/env python3
"""
gap300_signals.py — EMA(300) vs SMA(300) Gap Widening Signal on 1m prices.

REDESIGNED: State machine model (2026-04-27)

Signal logic:
  - LONG:  EMA(300) > SMA(300) AND gap crosses above MIN_GAP_PCT, gap widening
  - SHORT: EMA(300) < SMA(300) AND gap crosses above MIN_GAP_PCT, gap widening

Architecture:
  price_history (1m closes, fresh every minute) → EMA(300) + SMA(300) + state machine
  → signal_schema.add_signal() → signals_hermes_runtime.db
  → signal_compactor → hotset.json → guardian → HL

Signal types:
  - ema_sma_gap_300_long  : gap widens bullish (EMA above SMA, gap crossing up)
  - ema_sma_gap_300_short : gap widens bearish (EMA below SMA, gap crossing down)
"""

import sys, os, sqlite3, time, datetime
from typing import Optional, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, price_age_minutes

# ── Paths ─────────────────────────────────────────────────────────────────────
_RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'
_PRICE_DB   = '/root/.hermes/data/signals_hermes.db'

# ── Signal constants ────────────────────────────────────────────────────────────
PERIOD             = 300       # 300 × 1m = 5 hours
MIN_GAP_PCT        = 0.05     # gap as % of price — cross above this to start tracking
COOLDOWN_MIN       = 5        # bars between fires (was 10)
MOMENTUM_BARS      = 10       # lookback for momentum check
COLLAPSE_PCT        = 0.70     # fire only if gap > peak × this
LOOKBACK_1M        = 700      # 1m prices to fetch
SIGNAL_TYPE_LONG   = 'ema_sma_gap_300_long'
SIGNAL_TYPE_SHORT  = 'ema_sma_gap_300_short'
SOURCE_LONG        = 'gap-300+'
SOURCE_SHORT       = 'gap-300-'

# ── State constants ───────────────────────────────────────────────────────────
S_NO_SIGNAL         = 'NO_SIGNAL'
S_TRACKING_LONG     = 'TRACKING_LONG'
S_TRACKING_SHORT    = 'TRACKING_SHORT'
S_ACTIVE_LONG       = 'ACTIVE_LONG'
S_ACTIVE_SHORT      = 'ACTIVE_SHORT'


# ═══════════════════════════════════════════════════════════════════════════════
# EMA / SMA helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _ema_series(values: list, period: int) -> list:
    """Return EMA series (oldest first), None for indices < period-1."""
    if len(values) < period:
        return [None] * len(values)
    k = 2.0 / (period + 1)
    result = [None] * (period - 1)
    ema_val = sum(values[:period]) / period  # SMA of first period bars as EMA seed
    result.append(ema_val)
    for price in values[period:]:
        ema_val = price * k + ema_val * (1 - k)
        result.append(ema_val)
    return result


def _sma_series(values: list, period: int) -> list:
    """Return SMA series (oldest first), None for indices < period-1."""
    if len(values) < period:
        return [None] * len(values)
    result = [None] * (period - 1)
    for i in range(period - 1, len(values)):
        result.append(sum(values[i - period + 1:i + 1]) / period)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# State persistence
# ═══════════════════════════════════════════════════════════════════════════════

def _init_state_table():
    """Create gap300_state table if it doesn't exist."""
    try:
        conn = sqlite3.connect(_RUNTIME_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS gap300_state (
                token         TEXT PRIMARY KEY,
                state         TEXT NOT NULL,
                direction     TEXT,
                peak_gap      REAL DEFAULT 0,
                cooldown_until INTEGER DEFAULT 0,
                updated_at    INTEGER
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"  [gap300] state table init error: {e}")


def _load_state(token: str) -> dict:
    """Load state for a token. Returns default (no signal) if none found."""
    _init_state_table()
    try:
        conn = sqlite3.connect(_RUNTIME_DB, timeout=10)
        c = conn.cursor()
        c.execute(
            "SELECT state, direction, peak_gap, cooldown_until, updated_at "
            "FROM gap300_state WHERE token = ?",
            (token.upper(),)
        )
        row = c.fetchone()
        conn.close()
        if row:
            return {
                'state':         row[0],
                'direction':     row[1],
                'peak_gap':      row[2] or 0.0,
                'cooldown_until': row[3] or 0,
                'updated_at':    row[4],
            }
    except Exception as e:
        print(f"  [gap300] load_state error for {token}: {e}")
    return {
        'state': S_NO_SIGNAL, 'direction': None,
        'peak_gap': 0.0, 'cooldown_until': 0, 'updated_at': int(time.time())
    }


def _save_state(token: str, state: str, direction: Optional[str],
                peak_gap: float, cooldown_until: int):
    """Save state for a token to DB."""
    _init_state_table()
    try:
        conn = sqlite3.connect(_RUNTIME_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO gap300_state
            (token, state, direction, peak_gap, cooldown_until, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (token.upper(), state, direction, peak_gap,
              cooldown_until, int(time.time())))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"  [gap300] save_state error for {token}: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# Data fetch — LIVE prices from price_history (signals_hermes.db)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_1m_prices(token: str, lookback: int = LOOKBACK_1M) -> list:
    """Fetch 1m close prices from price_history (signals_hermes.db), oldest first.

    price_history is updated every minute with live prices — the ONLY reliable
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

        # Freshness guard — skip if most recent price is older than 2 minutes
        most_recent_ts = rows[-1][0]
        if (time.time() - most_recent_ts) > 120:
            print(f"  [gap300] {token}: stale price_history (last ts {most_recent_ts}, skipping)")
            return []

        # Bar-to-bar gap guard
        bar_gaps = [rows[i][0] - rows[i-1][0] for i in range(1, len(rows))]
        mean_gap = sum(bar_gaps) / len(bar_gaps)
        variance = sum((g - mean_gap) ** 2 for g in bar_gaps) / len(bar_gaps)
        std_gap = variance ** 0.5
        threshold = max(150, mean_gap + 3.0 * std_gap)
        for i in range(1, len(rows)):
            bar_gap = rows[i][0] - rows[i-1][0]
            if bar_gap > threshold:
                print(f"  [gap300] {token}: data gap ({bar_gap:.0f}s, threshold={threshold:.0f}s), skipping")
                return []

        # Window-span guard
        window_start = rows[0][0]
        window_end   = rows[-1][0]
        actual_span  = window_end - window_start
        expected_max_span = (len(rows) - 1) * 90
        if actual_span > expected_max_span:
            print(f"  [gap300] {token}: window span gap ({actual_span:.0f}s for {len(rows)} bars, "
                  f"expected <{expected_max_span:.0f}s), skipping")
            return []

        return [{'timestamp': r[0], 'price': r[1]} for r in rows]

    except Exception as e:
        print(f"  [gap300] price_history error for {token}: {e}")
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# State machine core
# ═══════════════════════════════════════════════════════════════════════════════

def scan_gap300_state(token: str, prices: list, price: float,
                      open_pos: dict) -> tuple:
    """
    State machine scanner for gap-300 signals.

    Loads existing state for token, walks the price series bar-by-bar from the
    last known state, updates state, and returns (signal_dict_or_None, new_state_dict).

    Opposite cross: ALLOW on any sign flip (raw_gap changes sign).
    No requirement that gap_prev < MIN_GAP_PCT — sign flip alone is sufficient.

    Args:
        token: token symbol
        prices: list of {timestamp, price} oldest-first (from _get_1m_prices)
        price: current/latest price from signal_gen
        open_pos: dict of token -> direction for open positions (unused, caller filters)

    Returns:
        (signal_dict_or_None, final_state_dict)
        signal_dict: {'direction': 'LONG'/'SHORT', 'gap_pct': float, 'confidence': int}
    """
    if not prices or len(prices) < PERIOD * 2:
        return None, {'state': S_NO_SIGNAL, 'direction': None,
                      'peak_gap': 0.0, 'cooldown_until': 0}

    # Load persisted state
    st = _load_state(token)

    closes = [p['price'] for p in prices]
    timestamps = [p['timestamp'] for p in prices]

    ema_s = _ema_series(closes, PERIOD)
    sma_s = _sma_series(closes, PERIOD)

    gap_pcts = []
    raw_gaps = []
    for i in range(PERIOD - 1, len(closes)):
        if ema_s[i] is None or sma_s[i] is None:
            gap_pcts.append(None)
            raw_gaps.append(None)
        else:
            gap = ema_s[i] - sma_s[i]
            gap_pcts.append(abs(gap) / closes[i] * 100.0)
            raw_gaps.append(gap)

    n = len(gap_pcts)
    valid_start = PERIOD - 1

    # Current bar index (most recent)
    cur_idx = n - 1
    cur_ts = timestamps[cur_idx]
    cur_gap = gap_pcts[cur_idx]
    cur_raw = raw_gaps[cur_idx]
    prev_gap = gap_pcts[cur_idx - 1] if cur_idx > valid_start else None

    state = st['state']
    direction = st['direction']
    peak_gap = st['peak_gap']
    cooldown_until = st['cooldown_until']

    fired = None  # signal dict if we fired this tick

    # ── NO_SIGNAL ──────────────────────────────────────────────────────────────
    if state == S_NO_SIGNAL:
        if cur_gap is not None and prev_gap is not None:
            # Cross above threshold starts tracking
            if prev_gap < MIN_GAP_PCT <= cur_gap:
                direction = 'LONG' if cur_raw > 0 else 'SHORT'
                peak_gap = cur_gap
                cooldown_until = 0  # reset on every state transition
                state = S_TRACKING_LONG if direction == 'LONG' else S_TRACKING_SHORT

    # ── TRACKING_* ────────────────────────────────────────────────────────────
    elif state in (S_TRACKING_LONG, S_TRACKING_SHORT):
        if cur_gap is not None and prev_gap is not None:
            opp_sign = -1 if direction == 'LONG' else 1
            opp_cross = cur_raw * opp_sign < 0

            if opp_cross:
                # Opposite cross — ALLOW on any sign flip, replace direction
                direction = 'SHORT' if direction == 'LONG' else 'LONG'
                peak_gap = cur_gap
                cooldown_until = 0
                state = S_TRACKING_LONG if direction == 'LONG' else S_TRACKING_SHORT

            elif cur_gap < MIN_GAP_PCT:
                # Gap below threshold → reset completely
                state = S_NO_SIGNAL
                direction = None
                peak_gap = 0.0
                cooldown_until = 0

            else:
                contracting = cur_gap <= prev_gap
                collapsed = peak_gap > 0 and cur_gap < peak_gap * COLLAPSE_PCT

                # Always update peak_gap when contracting so collapsed check uses current peak
                if contracting:
                    peak_gap = cur_gap
                elif cur_gap > peak_gap:
                    peak_gap = cur_gap

                if contracting or collapsed:
                    state = S_TRACKING_LONG if direction == 'LONG' else S_TRACKING_SHORT
                else:
                    widening = cur_gap > prev_gap
                    momentum_ok = True
                    if cur_idx >= MOMENTUM_BARS:
                        ret = (closes[cur_idx] / closes[cur_idx - MOMENTUM_BARS] - 1) * 100.0
                        momentum_ok = (direction == 'LONG' and ret >= 0) or (direction == 'SHORT' and ret <= 0)
                    not_collapsed = peak_gap > 0 and cur_gap >= peak_gap * COLLAPSE_PCT
                    cooldown_ok = cur_ts >= cooldown_until

                    if widening and momentum_ok and not_collapsed and cooldown_ok:
                        confidence = int(min(75, max(60, 60 + (cur_gap - MIN_GAP_PCT) * 200)))
                        fired = {
                            'direction': direction,
                            'gap_pct': round(cur_gap, 4),
                            'confidence': confidence,
                        }
                        cooldown_until = int(cur_ts + COOLDOWN_MIN * 60)
                        state = S_ACTIVE_LONG if direction == 'LONG' else S_ACTIVE_SHORT
                        return fired, {
                            'state': state, 'direction': direction,
                            'peak_gap': peak_gap, 'cooldown_until': cooldown_until,
                        }

    # ── ACTIVE_* ─────────────────────────────────────────────────────────────
    elif state in (S_ACTIVE_LONG, S_ACTIVE_SHORT):
        if cur_gap is not None and prev_gap is not None:
            opp_sign = -1 if direction == 'LONG' else 1
            opp_cross = cur_raw * opp_sign < 0

            if opp_cross:
                # Opposite cross — ALLOW on any sign flip, replace direction
                direction = 'SHORT' if direction == 'LONG' else 'LONG'
                peak_gap = cur_gap
                cooldown_until = 0
                state = S_TRACKING_LONG if direction == 'LONG' else S_TRACKING_SHORT

            elif cur_gap < MIN_GAP_PCT:
                # Gap below threshold → reset completely
                state = S_NO_SIGNAL
                direction = None
                peak_gap = 0.0
                cooldown_until = 0

            else:
                contracting = cur_gap <= prev_gap
                collapsed = peak_gap > 0 and cur_gap < peak_gap * COLLAPSE_PCT

                # Always update peak_gap when contracting so collapsed check uses current peak
                if contracting:
                    peak_gap = cur_gap
                elif cur_gap > peak_gap:
                    peak_gap = cur_gap

                if contracting or collapsed:
                    state = S_TRACKING_LONG if direction == 'LONG' else S_TRACKING_SHORT
                else:
                    # Update peak (already done above)
                    # Re-fire check
                    if cur_ts >= cooldown_until:
                        widening = cur_gap > prev_gap
                        momentum_ok = True
                        if cur_idx >= MOMENTUM_BARS:
                            ret = (closes[cur_idx] / closes[cur_idx - MOMENTUM_BARS] - 1) * 100.0
                            momentum_ok = (direction == 'LONG' and ret >= 0) or (direction == 'SHORT' and ret <= 0)
                        not_collapsed = peak_gap > 0 and cur_gap >= peak_gap * COLLAPSE_PCT

                        if widening and momentum_ok and not_collapsed:
                            confidence = int(min(75, max(60, 60 + (cur_gap - MIN_GAP_PCT) * 200)))
                            fired = {
                                'direction': direction,
                                'gap_pct': round(cur_gap, 4),
                                'confidence': confidence,
                            }
                            cooldown_until = int(cur_ts + COOLDOWN_MIN * 60)

    # Save state
    _save_state(token, state, direction, peak_gap, cooldown_until)

    new_state = {
        'state': state,
        'direction': direction,
        'peak_gap': peak_gap,
        'cooldown_until': cooldown_until,
    }

    return fired, new_state


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner (caller-facing)
# ═══════════════════════════════════════════════════════════════════════════════

def scan_gap300_signals(prices_dict: dict) -> int:
    """
    Scan tokens for EMA(300)/SMA(300) gap widening signals.

    All guards (blacklists, open positions, cooldowns, price age) must be
    applied by the caller before passing prices_dict here.

    Args:
        prices_dict: token -> {'price': float, ...} from signal_gen

    Returns:
        Number of signals written to DB.
    """
    from signal_schema import add_signal, price_age_minutes
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
        if token.upper() in SHORT_BLACKLIST:
            continue
        if price_age_minutes(token) > 10:
            continue

        prices = _get_1m_prices(token, lookback=LOOKBACK_1M)
        if not prices or len(prices) < PERIOD + 2:
            continue

        sig, final_state = scan_gap300_state(token, prices, price, open_pos)
        if sig is None:
            continue

        direction = sig['direction']
        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        try:
            sid = add_signal(
                token=token.upper(),
                direction=direction,
                signal_type=sig_type,
                source=source,
                confidence=sig['confidence'],
                value=float(sig['confidence']),
                price=price,
                exchange='hyperliquid',
                timeframe='1m',
                z_score=None,
                z_score_tier=None,
            )
            if sid:
                added += 1
                set_cooldown(token, direction, hours=COOLDOWN_MIN / 60.0)
                print(f"  {direction:5s}-gap300 {token:8s} conf={sig['confidence']:.0f}% "
                      f"gap={sig['gap_pct']:.3f}% [{source}]")
        except Exception as e:
            print(f"[gap300] add_signal error for {token}: {e}")

    return added


# ═══════════════════════════════════════════════════════════════════════════════
# Backwards compatibility shims
# ═══════════════════════════════════════════════════════════════════════════════

def detect_gap_cross(token: str, prices: list, price: float):
    """
    DEPRECATED — use scan_gap300_state() instead.
    Kept for backwards compatibility with any callers that import this directly.
    """
    return None   # Legacy detection is replaced by the state machine.
