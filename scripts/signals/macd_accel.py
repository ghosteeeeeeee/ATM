# Migrated from ../macd_accel_signals.py — see signals/__init__.py registry
#!/usr/bin/env python3
"""
macd_accel_signals.py — MACD (8,50,12) Crossover + Acceleration Signal.

Signal logic:
  - LONG:  MACD line crosses ABOVE signal line
           AND MACD values are rising (acceleration confirmed)
           → hist is increasing (growing positive OR shrinking negative)
  - SHORT: MACD line crosses BELOW signal line
           AND MACD values are falling (acceleration confirmed)
           → hist is decreasing (growing negative OR shrinking positive)

Crossover detection:
  - Bullish:  prev_hist <= 0 AND cur_hist > 0
  - Bearish:  prev_hist >= 0 AND cur_hist < 0

Acceleration detection:
  - LONG:  cur_hist > prev_hist  (histogram is rising = MACD accelerating up)
  - SHORT: cur_hist < prev_hist  (histogram is falling = MACD accelerating down)

Architecture:
  price_history (1m closes) → detect_crossover_accel() → add_signal()
  → signals_hermes_runtime.db → signal_compactor → hotset.json → guardian

Signal types:
  - macd_accel_long  : MACD crosses above signal + histogram rising
  - macd_accel_short : MACD crosses below signal + histogram falling

Fixed params (8, 50, 12) — no per-token tuning.
"""

import sys, os, sqlite3
from typing import Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, price_age_minutes

# ── Paths ─────────────────────────────────────────────────────────────────────
_RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'
_CANDLES_DB  = '/root/.hermes/data/candles.db'          # candles_1m — 1m OHLCV
_PRICE_DB    = '/root/.hermes/data/signals_hermes.db'   # price_history — live 1m prices (fallback)

# ── Fixed MACD params (8, 50, 12) ──────────────────────────────────────────────
FAST   = 8
SLOW   = 50
SIGNAL = 12

# ── Warmup ─────────────────────────────────────────────────────────────────────
# Need slow + signal bars for MACD to be valid
MIN_BARS = SLOW + SIGNAL  # 50 + 12 = 62 bars minimum
# Fetch extra for slope/acceleration check (compare 2 consecutive histogram values)
LOOKBACK_BARS = MIN_BARS + 5  # 67 bars

# ── Signal metadata ─────────────────────────────────────────────────────────────
SIGNAL_TYPE_LONG  = 'macd_accel_long'
SIGNAL_TYPE_SHORT = 'macd_accel_short'
SOURCE_LONG       = 'macd-accel+'
SOURCE_SHORT      = 'macd-accel-'


# ═══════════════════════════════════════════════════════════════════════════════
# EMA helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _ema(data, period):
    """Return EMA series (oldest first), None for indices < period-1."""
    if len(data) < period:
        return [None] * len(data)
    k = 2.0 / (period + 1)
    result = [None] * (period - 1)
    ema_val = sum(data[:period]) / period
    result.append(ema_val)
    for price in data[period:]:
        ema_val = price * k + ema_val * (1 - k)
        result.append(ema_val)
    return result


def _sma(data, period):
    """Return SMA series (oldest first), None for indices < period-1."""
    if len(data) < period:
        return [None] * len(data)
    result = [None] * (period - 1)
    for i in range(period - 1, len(data)):
        result.append(sum(data[i - period + 1:i + 1]) / period)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# MACD computation
# ═══════════════════════════════════════════════════════════════════════════════

def compute_macd_series(closes):
    """Compute MACD(8,50,12) on a closes list. Returns (macd_line, signal_line, hist_series).
    All series are oldest-first and aligned to the same starting index.
    Values before warmup are None.
    """
    if len(closes) < MIN_BARS:
        return None, None, None

    # EMA(8) and EMA(50)
    ema_fast = _ema(closes, FAST)
    ema_slow = _ema(closes, SLOW)

    # MACD line = EMA(fast) - EMA(slow)
    macd_line = []
    for ef, es in zip(ema_fast, ema_slow):
        if ef is None or es is None:
            macd_line.append(None)
        else:
            macd_line.append(ef - es)

    # Signal line = EMA(9) of MACD line
    # Only compute where MACD has enough warmup
    first_valid = SLOW - 1  # index of first valid MACD value
    macd_valid = macd_line[first_valid:]

    if len(macd_valid) < SIGNAL:
        return None, None, None

    ema_sig = _ema(macd_valid, SIGNAL)
    if ema_sig is None or len(ema_sig) < SIGNAL:
        return None, None, None

    # Align: macd_line[first_valid] corresponds to ema_sig[0]
    signal_line = [None] * first_valid + ema_sig

    # Histogram = MACD line - signal line
    hist = []
    for m, s in zip(macd_line, signal_line):
        if m is None or s is None:
            hist.append(None)
        else:
            hist.append(m - s)

    # Trim leading Nones so last N bars are the only valid ones
    # Find last non-None
    last_valid_idx = -1
    for i in range(len(hist) - 1, -1, -1):
        if hist[i] is not None:
            last_valid_idx = i
            break
    if last_valid_idx < 0:
        return None, None, None

    return macd_line, signal_line, hist


# ═══════════════════════════════════════════════════════════════════════════════
# Core signal detection
# ═══════════════════════════════════════════════════════════════════════════════

def detect_macd_accel(closes) -> Optional[Tuple[str, int]]:
    """Detect MACD(8,50,12) crossover with acceleration confirmation.

    Args:
        closes: list of 1m close prices, oldest-first

    Returns:
        ('LONG', confidence)  — bullish crossover + rising hist
        ('SHORT', confidence) — bearish crossover + falling hist
        None                  — no signal
    """
    macd_line, signal_line, hist = compute_macd_series(closes)
    if macd_line is None or hist is None:
        return None

    # Need at least 2 valid hist bars for crossover + acceleration check
    valid_hist = [h for h in hist if h is not None]
    if len(valid_hist) < 3:
        return None

    prev_hist = valid_hist[-2]
    cur_hist  = valid_hist[-1]

    # Crossover detection
    # Bullish: MACD crossed above signal (hist: ≤0 → >0)
    # Bearish: MACD crossed below signal (hist: ≥0 → <0)
    bullish_cross = (prev_hist <= 0) and (cur_hist > 0)
    bearish_cross = (prev_hist >= 0) and (cur_hist < 0)

    # Acceleration: hist is moving in the direction of the crossover
    # LONG  → hist rising (cur > prev, meaning MACD line is gaining on signal line)
    # SHORT → hist falling (cur < prev, meaning MACD line is losing to signal line)
    hist_rising  = cur_hist > prev_hist
    hist_falling = cur_hist < prev_hist

    if bullish_cross and hist_rising:
        # Confidence: how strong is the histogram?
        # Map hist magnitude to confidence: 0.01% price-based hist → ~50 conf, higher → ~75
        conf = min(75, max(61, int(55 + abs(cur_hist) * 400)))
        return ('LONG', conf)

    if bearish_cross and hist_falling:
        conf = min(75, max(61, int(55 + abs(cur_hist) * 400)))
        return ('SHORT', conf)

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Per-token scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_macd_accel_signals(prices_dict: dict) -> Tuple[int, set]:
    from hermes_constants import MACD_ACCEL_ENABLED
    if not MACD_ACCEL_ENABLED:
        return 0
    """Scan for MACD acceleration signals across all tokens.

    Args:
        prices_dict: {token: {price, ...}} from get_all_latest_prices()

    Returns:
        (count_of_signals_written, set_of_tokens_that_fired)
    """
    from position_manager import get_open_positions as _get_open_pos

    open_pos = {p['token']: p['direction'] for p in _get_open_pos()}
    added = 0
    fired_tokens = set()

    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue
        if not data.get('price') or data['price'] <= 0:
            continue
        if token.upper() in open_pos:
            continue
        if price_age_minutes(token) > 10:
            continue

        # ── Fetch 1m closes from price_history ────────────────────────────
        closes = _get_1m_closes(token, LOOKBACK_BARS)
        if closes is None or len(closes) < MIN_BARS:
            continue

        # ── Detect signal ────────────────────────────────────────────────
        result = detect_macd_accel(closes)
        if result is None:
            continue

        direction, confidence = result
        price = data['price']
        signal_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        # ── Per-direction kill-switch ─────────────────────────────────────────
        from hermes_constants import MACD_ACCEL_PLUS_ENABLED, MACD_ACCEL_MINUS_ENABLED
        if direction == 'LONG' and not MACD_ACCEL_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not MACD_ACCEL_MINUS_ENABLED:
            continue

        sid = add_signal(
            token=token,
            direction=direction,
            signal_type=signal_type,
            source=source,
            confidence=confidence,
            value=float(confidence),
            price=price,
            exchange='hyperliquid',
            timeframe='1m',
            z_score=None,
            z_score_tier=None,
        )
        if sid:
            added += 1
            fired_tokens.add(token)

    return added, fired_tokens


# ═══════════════════════════════════════════════════════════════════════════════
# Data fetch
# ═══════════════════════════════════════════════════════════════════════════════

def _get_1m_closes(token: str, lookback: int = None) -> Optional[list]:
    """Fetch 1m close prices from candles.db (candles_1m table).

    Returns: list of floats, oldest-first, or None on error.
    Note: freshness is checked at signal level via price_age_minutes(),
    not here — candles.db may be up to a few hours stale during backtesting.
    """
    if lookback is None:
        lookback = LOOKBACK_BARS
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute(
            "SELECT close FROM candles_1m WHERE token=? "
            "ORDER BY ts ASC LIMIT ?",
            (token.upper(), lookback)
        )
        rows = c.fetchall()
        conn.close()
        if not rows:
            return None
        return [r[0] for r in rows]
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# signals_runner entry point
# ═══════════════════════════════════════════════════════════════════════════════

def run(prices_dict=None):
    """Entry point for signals_runner. Returns count of signals emitted."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_macd_accel_signals(prices_dict)
