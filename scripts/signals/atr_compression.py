# Migrated from ../atr_compression_signals.py — see signals/__init__.py registry
#!/usr/bin/env python3
"""
atr_compression_signals.py — 5m ATR Compression + Volume Breakout Signal.

Signal logic:
  - Detect compression: 5 consecutive 5m bars with rng% < 0.5% AND ATR% < 0.8%
  - Fire LONG when: close breaks above compression high +0.4% AND volume > 2x avg
  - Confidence: bounded by volume ratio + break magnitude

Architecture:
  candles_5m (local DB, zero HL API calls) → compression state machine
  → signal_schema.add_signal() → signals_hermes_runtime.db
  → signal_compactor → hotset.json → guardian → HL

Signal type: atr_compression_long / atr_compression_short
Source tags:   atr5m-comp  (e.g. "atr5m-comp@vol3.2")
"""

import sys, os, sqlite3, time, datetime
from typing import Optional, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, price_age_minutes

# ── Paths ─────────────────────────────────────────────────────────────────────
_RUNTIME_DB  = '/root/.hermes/data/signals_hermes_runtime.db'
_CANDLES_DB  = '/root/.hermes/data/candles.db'

# ── Signal constants ───────────────────────────────────────────────────────────
ATR_PCT_THRESH  = 0.8    # max ATR14/close % to qualify as compressed (ATR alone)
MIN_BARS        = 5      # minimum consecutive compressed bars
VOL_RATIO       = 2.0    # breakout bar volume must exceed comp avg by this
BREAK_PCT       = 0.4    # close must break this % above compression high
COOLDOWN_BARS   = 8      # bars between fires (avoid re-entry)
LOOKBACK_5M     = 500    # 5m bars to fetch

SIGNAL_TYPE_LONG   = 'atr_compression_long'
SIGNAL_TYPE_SHORT  = 'atr_compression_short'
SOURCE_TAG         = 'atr5m-comp'

# ── State constants ───────────────────────────────────────────────────────────
S_NO_SIGNAL      = 'NO_SIGNAL'
S_COMPRESSING    = 'COMPRESSING'
S_BREAK_LONG     = 'BREAK_LONG'
S_BREAK_SHORT    = 'BREAK_SHORT'


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_atr(rows: list, period: int = 14) -> list:
    """Return ATR(period) series (oldest first), None for indices < period-1."""
    if len(rows) < period:
        return [None] * len(rows)
    trs = []
    for i, r in enumerate(rows):
        h, l, c = r[2], r[3], r[4]
        if i == 0:
            tr = h - l
        else:
            prev_c = rows[i - 1][4]
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        trs.append(tr)
    atrs = []
    for i in range(len(trs)):
        if i < period - 1:
            atrs.append(None)
        else:
            atrs.append(sum(trs[i - period + 1:i + 1]) / period)
    return atrs


def _get_candles_5m(token: str, lookback: int = LOOKBACK_5M) -> Tuple[list, list]:
    """
    Fetch 5m candles for token from local candles.db.
    Returns (rows, atrs) where rows = [(ts, open, high, low, close, volume), ...]
    and atrs = ATR(14) series aligned to rows.
    """
    conn = sqlite3.connect(_CANDLES_DB, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()
    cur.execute("SELECT MAX(ts) FROM candles_5m")
    max_ts = cur.fetchone()[0]
    if max_ts is None:
        conn.close()
        return [], []
    since = max_ts - lookback * 300  # 5m bars

    cur.execute("""
        SELECT ts, open, high, low, close, volume
        FROM candles_5m
        WHERE token = ? AND ts >= ?
        ORDER BY ts ASC
    """, (token.upper(), since))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return [], []

    atrs = _compute_atr(rows, period=14)
    return rows, atrs


def _get_last_state(token: str) -> Tuple[str, dict]:
    """Read current compression state from runtime DB cache table."""
    conn = sqlite3.connect(_RUNTIME_DB, timeout=5)
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT state, comp_high, comp_low, comp_close, comp_avg_vol,
                   comp_len, state_bar_ts, cooldown_until_ts
            FROM atr_comp_cache
            WHERE token = ?
        """, (token.upper(),))
        row = cur.fetchone()
        conn.close()
        if not row:
            return S_NO_SIGNAL, {}
        return row[0], {
            'comp_high':      row[1],
            'comp_low':       row[2],
            'comp_close':     row[3],
            'comp_avg_vol':   row[4],
            'comp_len':       row[5],
            'state_bar_ts':   row[6],
            'cooldown_until': row[7],
        }
    except Exception:
        conn.close()
        return S_NO_SIGNAL, {}


def _save_state(token: str, state: str, comp_high: float, comp_low: float,
                 comp_close: float, comp_avg_vol: float, comp_len: int,
                 state_bar_ts: int, cooldown_until: int = 0):
    """Persist compression state to runtime DB."""
    conn = sqlite3.connect(_RUNTIME_DB, timeout=5)
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS atr_comp_cache (
                token TEXT PRIMARY KEY,
                state TEXT,
                comp_high REAL, comp_low REAL, comp_close REAL,
                comp_avg_vol REAL, comp_len INTEGER,
                state_bar_ts INTEGER, cooldown_until_ts INTEGER,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            INSERT OR REPLACE INTO atr_comp_cache
            (token, state, comp_high, comp_low, comp_close, comp_avg_vol,
             comp_len, state_bar_ts, cooldown_until_ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (token.upper(), state, comp_high, comp_low, comp_close,
               comp_avg_vol, comp_len, state_bar_ts, cooldown_until))
        conn.commit()
    except Exception as e:
        pass
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Core detection
# ═══════════════════════════════════════════════════════════════════════════════

def detect_atr_compression_signal(
    token: str,
    rows: list,
    atrs: list,
    current_state: str,
    state_data: dict,
) -> Tuple[Optional[str], Optional[dict]]:
    """
    State-machine ATR compression + breakout detector on 5m candles.

    States:
      NO_SIGNAL   — no compression active
      COMPRESSING — tracking a live compression
      BREAK_LONG  — compression high broken, confidence in progress
      BREAK_SHORT — compression low broken, confidence in progress

    Returns: (signal_type_or_None, signal_kwargs_or_None)
    """

    if len(rows) < MIN_BARS + 3:
        return None, None

    now_ts   = rows[-1][0]
    now_price = rows[-1][4]

    # ── Cooldown guard ───────────────────────────────────────────────────────
    if current_state != S_NO_SIGNAL:
        cooldown_until = state_data.get('cooldown_until', 0)
        if now_ts < cooldown_until:
            # In cooldown — reset to NO_SIGNAL and return
            _save_state(token, S_NO_SIGNAL, 0, 0, 0, 0, 0, now_ts, 0)
            return None, None

    # ── State: COMPRESSING ──────────────────────────────────────────────────
    if current_state == S_COMPRESSING:
        comp_high    = state_data['comp_high']
        comp_low     = state_data['comp_low']
        comp_close   = state_data['comp_close']
        comp_avg_vol = state_data['comp_avg_vol']
        comp_len     = state_data['comp_len']

        # Check for LONG break
        close_above = (now_price - comp_high) / comp_high * 100
        rng_now    = (rows[-1][2] - rows[-1][3]) / rows[-1][1] * 100
        vol_ratio  = rows[-1][5] / comp_avg_vol if comp_avg_vol > 0 else 0

        if close_above > BREAK_PCT and vol_ratio > VOL_RATIO and rng_now > 0.6:
            # LONG break confirmed
            confidence = min(95.0, 50 + vol_ratio * 8 + close_above * 8)
            state_data['confidence'] = confidence
            state_data['vol_ratio']   = vol_ratio
            state_data['close_above'] = close_above
            _save_state(token, S_BREAK_LONG, comp_high, comp_low, comp_close,
                        comp_avg_vol, comp_len, now_ts)
            return SIGNAL_TYPE_LONG, state_data

        # Check for SHORT break (below comp low with volume)
        close_below = (comp_low - now_price) / comp_low * 100
        if close_below > BREAK_PCT and vol_ratio > VOL_RATIO and rng_now > 0.6:
            confidence = min(95.0, 50 + vol_ratio * 8 + close_below * 8)
            state_data['confidence'] = confidence
            _save_state(token, S_BREAK_SHORT, comp_high, comp_low, comp_close,
                        comp_avg_vol, comp_len, now_ts)
            return SIGNAL_TYPE_SHORT, state_data

        # Compression still live — update comp_high/low if needed
        bar_high = rows[-1][2]
        bar_low  = rows[-1][3]
        new_comp_high = max(comp_high, bar_high)
        new_comp_low  = min(comp_low, bar_low)
        if new_comp_high != comp_high or new_comp_low != comp_low:
            _save_state(token, S_COMPRESSING, new_comp_high, new_comp_low,
                        comp_close, comp_avg_vol, comp_len, now_ts)

        return None, None

    # ── State: BREAK_LONG / BREAK_SHORT ─────────────────────────────────────
    if current_state in (S_BREAK_LONG, S_BREAK_SHORT):
        # Already fired — enter cooldown
        cooldown_until = now_ts + COOLDOWN_BARS * 300
        _save_state(token, S_NO_SIGNAL, 0, 0, 0, 0, 0, now_ts,
                    int(cooldown_until))
        return None, None

    # ── State: NO_SIGNAL — scan for new compression ──────────────────────────
    if current_state == S_NO_SIGNAL:
        # Scan last MIN_BARS bars for compression (ATR% only — rng% varies too much)
        window = rows[-(MIN_BARS + 1):-1]  # exclude current bar
        if len(window) < MIN_BARS:
            return None, None

        all_compressed = True
        for bar in window:
            bar_ts  = bar[0]
            bar_idx = next((i for i, r in enumerate(rows) if r[0] == bar_ts), -1)
            if bar_idx < 0 or atrs[bar_idx] is None:
                all_compressed = False
                break
            atr_pct = atrs[bar_idx] / bar[4] * 100
            if atr_pct >= ATR_PCT_THRESH:
                all_compressed = False
                break

        if all_compressed:
            comp_high    = max(b[2] for b in window)
            comp_low     = min(b[3] for b in window)
            comp_close   = window[-1][4]
            comp_avg_vol = sum(b[5] for b in window) / len(window)
            comp_len     = len(window)

            # Save compressing state
            _save_state(token, S_COMPRESSING, comp_high, comp_low, comp_close,
                        comp_avg_vol, comp_len, now_ts)
            return None, None

        return None, None

    return None, None


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_atr_compression_signals(prices_dict: dict) -> Tuple[int, set]:
    from hermes_constants import ATR_COMPRESSION_ENABLED
    if not ATR_COMPRESSION_ENABLED:
        return 0
    """
    Scan all tokens in prices_dict for ATR compression breakouts on 5m.

    Returns: (count_of_signals_written, set_of_tokens_that_fired)
    """
    added = 0
    fired_tokens = set()

    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue
        if not data.get('price') or data['price'] <= 0:
            continue
        if price_age_minutes(token) > 10:
            continue

        current_state, state_data = _get_last_state(token)

        rows, atrs = _get_candles_5m(token)
        if not rows or len(rows) < MIN_BARS + 3:
            continue

        signal_type, sig_kwargs = detect_atr_compression_signal(
            token, rows, atrs, current_state, state_data
        )

        if not signal_type:
            continue

        direction  = 'LONG' if signal_type == SIGNAL_TYPE_LONG else 'SHORT'
        confidence = sig_kwargs.get('confidence', 75)

        # ── Per-direction kill-switch ─────────────────────────────────────────
        from hermes_constants import ATR_COMPRESSION_PLUS_ENABLED, ATR_COMPRESSION_MINUS_ENABLED
        if direction == 'LONG' and not ATR_COMPRESSION_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not ATR_COMPRESSION_MINUS_ENABLED:
            continue

        price      = rows[-1][4]
        source     = f"{SOURCE_TAG}@vol{sig_kwargs.get('vol_ratio', 0):.1f}"
        value      = sig_kwargs.get('close_above', 0)

        if confidence < 50:
            continue

        sid = add_signal(
            token=token,
            direction=direction,
            signal_type=signal_type,
            source=source,
            confidence=confidence,
            value=float(value),
            price=float(price),
            exchange='hyperliquid',
            timeframe='5m',
            z_score=None,
            z_score_tier=None,
        )
        if sid:
            added += 1
            fired_tokens.add(token)

    return added, fired_tokens


# ═══════════════════════════════════════════════════════════════════════════════
# signals_runner entry point
# ═══════════════════════════════════════════════════════════════════════════════

def run(prices_dict=None):
    """Entry point for signals_runner. Returns count of signals emitted."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_atr_compression_signals(prices_dict)
