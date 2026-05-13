# Migrated from ../guppy_signals.py — see signals/__init__.py registry
"""
Guppy MMA Signal Detection Engine
==================================
Pure detection library — reads candles_1m from local candles.db, no HL API calls.

Guppy Multiple Moving Average (MMA) strategy:
  - FAST group: EMA 3, 5, 8, 10, 12, 15
  - SLOW group: EMA 30, 35, 40, 45, 50, 60
  - Signal: fast group crosses slow group WITH squeeze resolution
  - Exit: fast group flips direction (price action against the group)

No external dependencies beyond stdlib + sqlite3.
"""

import sqlite3
import math
from typing import Optional

# ── Guppy MMA Parameters ────────────────────────────────────────────
FAST_GROUP = [3, 5, 8, 10, 12, 15]
SLOW_GROUP = [30, 35, 40, 45, 50, 60]

SQUEEZE_THRESHOLD = 0.003    # 0.3% — fast group within this % of slow group = squeeze
MIN_SEPARATION_PCT = 0.2      # 0.2% — minimum separation to confirm expansion after squeeze
EXPANSION_BARS     = 6         # bars over which separation must be growing

CANDLES_DB = "/root/.hermes/data/candles.db"
DEFAULT_LOOKBACK = 120        # bars — enough for EMA 60 + confirmation buffer


# ── Core EMA Math ──────────────────────────────────────────────────

def compute_ema(closes: list, period: int) -> float:
    """Compute EMA for a single period from a list of close prices (oldest first)."""
    if len(closes) < period:
        return None
    k = 2.0 / (period + 1)
    ema = sum(closes[:period]) / period
    for price in closes[period:]:
        ema = price * k + ema * (1 - k)
    return ema


def compute_group_emas(closes: list, periods: list) -> dict:
    """Compute EMA for each period in a group. Returns {period: ema_value}."""
    result = {}
    for p in periods:
        ema = compute_ema(closes, p)
        if ema is not None:
            result[p] = ema
    return result


def get_group_mid(group_emas: dict) -> float:
    """Midpoint of a group — average of all EMAs in the group."""
    if not group_emas:
        return None
    return sum(group_emas.values()) / len(group_emas)


def get_group_high_low(group_emas: dict) -> tuple:
    """(high, low) of all EMAs in the group."""
    if not group_emas:
        return None, None
    vals = list(group_emas.values())
    return max(vals), min(vals)


# ── Squeeze Detection ──────────────────────────────────────────────

def is_squeezed(fast_emas: dict, slow_emas: dict, threshold: float = SQUEEZE_THRESHOLD) -> bool:
    """
    Squeeze = fast group is within threshold% of slow group.
    All fast EMAs must be within threshold% of the corresponding slow EMAs.
    Uses midpoint comparison for robustness.
    """
    if not fast_emas or not slow_emas:
        return False

    fast_mid = get_group_mid(fast_emas)
    slow_mid = get_group_mid(slow_emas)
    if fast_mid is None or slow_mid is None or slow_mid == 0:
        return False

    # All fast EMAs must be within threshold% of slow group midpoint
    for fp, fv in fast_emas.items():
        spread = abs(fv - slow_mid) / slow_mid
        if spread > threshold:
            return False
    return True


def get_separation_pct(fast_emas: dict, slow_emas: dict) -> float:
    """
    How far apart are the groups? Returns % separation.
    Positive = fast above slow (bullish), Negative = fast below slow (bearish).
    """
    if not fast_emas or not slow_emas:
        return 0.0
    fast_mid = get_group_mid(fast_emas)
    slow_mid = get_group_mid(slow_emas)
    if fast_mid is None or slow_mid is None or slow_mid == 0:
        return 0.0
    return ((fast_mid - slow_mid) / slow_mid) * 100.0


# ── Trend / Slope Detection ──────────────────────────────────────

def get_group_slope(ema_history: list) -> float:
    """
    Slope of the group EMA over recent bars.
    ema_history: list of group midpoints (oldest first), length >= 2.
    Returns per-bar slope as a decimal fraction of price.
    """
    if len(ema_history) < 2:
        return 0.0
    # Simple linear slope over the history
    n = len(ema_history)
    xs = list(range(n))
    x_mean = (n - 1) / 2.0
    y_mean = sum(ema_history) / n
    num = sum((xs[i] - x_mean) * (ema_history[i] - y_mean) for i in range(n))
    den = sum((xs[i] - x_mean) ** 2 for i in range(n))
    if den == 0:
        return 0.0
    slope = num / den
    # Normalize by latest price to get fraction
    latest = ema_history[-1]
    if latest == 0:
        return 0.0
    return slope / latest


def get_fast_group_direction(ema_history: list, lookback: int = 3) -> int:
    """
    Direction of fast group: +1 = rising, -1 = falling, 0 = flat.
    Uses slope of group midpoint over lookback bars.
    """
    if len(ema_history) < 2:
        return 0
    history = ema_history[-lookback:] if len(ema_history) >= lookback else ema_history
    slope = get_group_slope(history)
    if slope > MIN_GROUP_SLOPE:
        return 1
    elif slope < -MIN_GROUP_SLOPE:
        return -1
    return 0


# ── Cross Detection ────────────────────────────────────────────────

# ── Expansion Detection ─────────────────────────────────────────────

def detect_expansion(fast_emas: dict, slow_emas: dict,
                    closes: list, period: int = EXPANSION_BARS) -> dict:
    """
    Detect if fast group is expanding away from slow group.

    Returns: {
        'direction': 'LONG' | 'SHORT' | None,
        'expanding':  bool,    # True if expansion confirmed
        'sep_now':    float,   # current separation %
        'sep_then':   float,   # separation EXPANSION_BARS ago
        'expansion_pct': float, # % growth in separation
    }
    """
    if len(closes) < max(max(FAST_GROUP), max(SLOW_GROUP)) + period:
        return {'direction': None, 'expanding': False,
                'sep_now': 0.0, 'sep_then': 0.0, 'expansion_pct': 0.0}

    # Compute past EMAs (EXPANSION_BARS ago)
    past_closes = closes[:len(closes) - period]
    past_fast = compute_group_emas(past_closes, FAST_GROUP)
    past_slow = compute_group_emas(past_closes, SLOW_GROUP)

    if not past_fast or not past_slow:
        return {'direction': None, 'expanding': False,
                'sep_now': 0.0, 'sep_then': 0.0, 'expansion_pct': 0.0}

    fast_mid_now  = get_group_mid(fast_emas)
    slow_mid_now  = get_group_mid(slow_emas)
    fast_mid_then = get_group_mid(past_fast)
    slow_mid_then = get_group_mid(past_slow)

    if not all([fast_mid_now, slow_mid_now, fast_mid_then, slow_mid_then]):
        return {'direction': None, 'expanding': False,
                'sep_now': 0.0, 'sep_then': 0.0, 'expansion_pct': 0.0}

    sep_now  = (fast_mid_now  - slow_mid_now)  / slow_mid_now  * 100.0
    sep_then = (fast_mid_then - slow_mid_then) / slow_mid_then * 100.0

    # Direction: positive = fast above slow (LONG), negative = SHORT
    direction = 'LONG' if sep_now > 0 else 'SHORT'

    # Expanding: separation has grown AND is growing in the right direction
    # (positive sep_now means fast is already above slow → LONG setup)
    # (negative sep_now means fast is below slow → SHORT setup)
    abs_sep_now  = abs(sep_now)
    abs_sep_then = abs(sep_then)

    # Expansion: absolute separation must be larger now than then
    # AND must meet minimum threshold
    if abs_sep_now >= MIN_SEPARATION_PCT and abs_sep_now > abs_sep_then:
        return {
            'direction':    direction,
            'expanding':   True,
            'sep_now':      sep_now,
            'sep_then':     sep_then,
            'expansion_pct': (abs_sep_now - abs_sep_then) / max(abs_sep_then, 0.001) * 100,
        }

    return {'direction': None, 'expanding': False,
            'sep_now': sep_now, 'sep_then': sep_then, 'expansion_pct': 0.0}


def detect_squeeze(rows: list) -> dict:
    """
    Detect current squeeze state: were the groups compressed recently?

    Returns: {
        'in_squeeze':    bool,   # currently squeezed
        'squeeze_bars':  int,    # bars since squeeze started (0 if not in squeeze)
        'squeeze_start': float,  # separation % at squeeze start
    }
    """
    closes = [r[4] for r in rows]
    max_p = max(max(FAST_GROUP), max(SLOW_GROUP))

    # Track separation over last 20 bars
    seps = []
    for i in range(max_p, len(closes)):
        subset = closes[:i+1]
        fe = compute_group_emas(subset, FAST_GROUP)
        se = compute_group_emas(subset, SLOW_GROUP)
        fm = get_group_mid(fe)
        sm = get_group_mid(se)
        if fm and sm:
            seps.append((fm - sm) / sm * 100)

    if not seps:
        return {'in_squeeze': False, 'squeeze_bars': 0, 'squeeze_start': 0.0}

    # Current
    curr_sep = seps[-1]
    in_squeeze = abs(curr_sep) <= SQUEEZE_THRESHOLD * 100

    # Count consecutive bars in squeeze
    squeeze_bars = 0
    squeeze_start_sep = curr_sep
    for s in reversed(seps):
        if abs(s) <= SQUEEZE_THRESHOLD * 100:
            squeeze_bars += 1
            squeeze_start_sep = s
        else:
            break

    return {
        'in_squeeze':    in_squeeze,
        'squeeze_bars':  squeeze_bars,
        'squeeze_start': squeeze_start_sep,
    }


def detect_cross_with_setup(rows: list, fast_group: list, slow_group: list,
                           cross_lookback: int = 3) -> Optional[dict]:
    """
    Detect if a valid cross occurred within the last cross_lookback bars,
    and return the setup state at the current bar.

    Returns: {
        'direction':    'LONG' | 'SHORT',
        'cross_bars_ago': int,
        'sep_now':      float,
        'squeeze_now':   bool,
    } or None.
    """
    if len(rows) < DEFAULT_LOOKBACK:
        return None

    closes = [r[4] for r in rows]
    fast_emas = compute_group_emas(closes, fast_group)
    slow_emas = compute_group_emas(closes, slow_group)
    if len(fast_emas) < len(fast_group) or len(slow_emas) < len(slow_group):
        return None

    sep_now     = get_separation_pct(fast_emas, slow_emas)
    squeeze_now = is_squeezed(fast_emas, slow_emas)

    fast_mid_hist = _compute_ema_mid_history(closes, fast_group, window=cross_lookback + 2)
    slow_mid_hist = _compute_ema_mid_history(closes, slow_group, window=cross_lookback + 2)

    if len(fast_mid_hist) < cross_lookback + 1:
        return None

    for bars_ago in range(1, cross_lookback + 1):
        idx = -bars_ago
        prev_f = fast_mid_hist[idx - 1]
        prev_s = slow_mid_hist[idx - 1]
        curr_f = fast_mid_hist[idx]
        curr_s = slow_mid_hist[idx]

        if prev_f < prev_s and curr_f > curr_s:
            return {'direction': 'LONG',  'cross_bars_ago': bars_ago,
                    'sep_now': sep_now, 'squeeze_now': squeeze_now}
        elif prev_f > prev_s and curr_f < curr_s:
            return {'direction': 'SHORT', 'cross_bars_ago': bars_ago,
                    'sep_now': sep_now, 'squeeze_now': squeeze_now}

    return None


def detect_cross(fast_mid_history: list, slow_mid_history: list,
                 min_bars: int = 1) -> Optional[str]:
    """
    Detect if fast group has crossed slow group and held for min_bars consecutive bars.
    Returns: 'LONG', 'SHORT', or None.
    """
    if len(fast_mid_history) < min_bars + 1 or len(slow_mid_history) < min_bars + 1:
        return None

    directions = []
    for i in range(1, min_bars + 1):
        idx = -i
        prev_fast, prev_slow = fast_mid_history[idx - 1], slow_mid_history[idx - 1]
        curr_fast, curr_slow = fast_mid_history[idx], slow_mid_history[idx]

        if prev_fast < prev_slow and curr_fast > curr_slow:
            directions.append('LONG')
        elif prev_fast > prev_slow and curr_fast < curr_slow:
            directions.append('SHORT')
        else:
            directions.append(None)

    if all(d == 'LONG' for d in directions):
        return 'LONG'
    elif all(d == 'SHORT' for d in directions):
        return 'SHORT'
    return None


def detect_slow_group_trend(slow_mid_history: list, lookback: int = None) -> int:
    """
    Detect the trend of the slow group over lookback bars.
    Returns: 1 (rising), -1 (falling), 0 (flat).
    Used as a trend filter for entries.

    Uses relative slope: (latest - oldest) / (oldest * lookback)
    """
    lookback = lookback or SLOW_TREND_LOOKBACK
    if len(slow_mid_history) < 3:
        return 0
    lookback = min(lookback, len(slow_mid_history))
    subset = slow_mid_history[-lookback:]
    oldest = subset[0]
    latest = subset[-1]
    if oldest == 0:
        return 0
    rel_slope = (latest - oldest) / (oldest * lookback)
    if rel_slope > 1e-5:
        return 1
    elif rel_slope < -1e-5:
        return -1
    return 0


# ── Volume Confirmation ────────────────────────────────────────────

def get_volume_ratio(rows: list) -> float:
    """
    Current bar volume vs trailing average (last 20 bars).
    Returns ratio: > 1.0 means above average.
    """
    if len(rows) < 5:
        return 1.0
    vols = [r[6] for r in rows[-21:-1]]  # exclude current bar
    if not vols or sum(vols) == 0:
        return 1.0
    avg_vol = sum(vols) / len(vols)
    curr_vol = rows[-1][6]
    if avg_vol == 0:
        return 1.0
    return curr_vol / avg_vol


# ── Main Signal Detection ─────────────────────────────────────────

def detect_guppy_signal(rows: list) -> Optional[dict]:
    """
    Main entry point: given a list of candle rows (from candles_1m),
    detect if a Guppy MMA signal is present.

    Signal = squeeze resolved into directional expansion:
      1. Fast group was compressed near slow group (squeeze)
      2. Fast group is now expanding away from slow group (momentum)
      3. Volume confirms the move

    rows: list of tuples (token, ts, open, high, low, close, volume, is_closed)
          MUST be ordered oldest → newest, at least 120 rows for full EMA coverage.

    Returns: signal dict or None
        {
            'signal':     'guppy_long' | 'guppy_short',
            'direction':  'LONG'       | 'SHORT',
            'confidence': 0.0–1.0,
            'source':     'guppy+'     | 'guppy-',
            'squeeze':    bool,
            'separation': float,
            'expansion':  bool,
            'volume_confirm': bool,
            'fast_mid':   float,
            'slow_mid':   float,
            'fast_high':  float,
            'fast_low':   float,
        }
    """
    if len(rows) < DEFAULT_LOOKBACK:
        return None

    closes = [r[4] for r in rows]

    # Compute current EMAs
    fast_emas = compute_group_emas(closes, FAST_GROUP)
    slow_emas = compute_group_emas(closes, SLOW_GROUP)

    if len(fast_emas) < len(FAST_GROUP) or len(slow_emas) < len(SLOW_GROUP):
        return None

    # Squeeze detection
    squeeze_state = detect_squeeze(rows)
    in_squeeze = squeeze_state['in_squeeze']
    squeeze_bars = squeeze_state['squeeze_bars']

    # Expansion detection
    exp = detect_expansion(fast_emas, slow_emas, closes, period=EXPANSION_BARS)
    if not exp['expanding']:
        return None

    direction = exp['direction']
    sep_now = exp['sep_now']
    expansion_pct = exp['expansion_pct']

    # Volume confirmation
    vol_ratio = get_volume_ratio(rows)
    volume_confirm = vol_ratio >= 1.2  # 1.2x average

    # Confidence scoring
    confidence = _compute_confidence(
        in_squeeze=in_squeeze,
        squeeze_bars=squeeze_bars,
        expansion_pct=expansion_pct,
        separation=sep_now,
        volume_confirm=volume_confirm,
    )

    if confidence < 0.50:
        return None

    fast_mid = get_group_mid(fast_emas)
    slow_mid = get_group_mid(slow_emas)
    fast_high, fast_low = get_group_high_low(fast_emas)

    return {
        'signal':          f'guppy_{direction.lower()}',
        'direction':       direction,
        'confidence':      confidence,
        'source':          'guppy+' if direction == 'LONG' else 'guppy-',
        'squeeze':         in_squeeze,
        'separation':      sep_now,
        'expansion':       True,
        'volume_confirm':  volume_confirm,
        'fast_mid':        fast_mid,
        'slow_mid':        slow_mid,
        'fast_high':       fast_high,
        'fast_low':        fast_low,
    }


def _compute_confidence(
    in_squeeze: bool,
    squeeze_bars: int,
    expansion_pct: float,
    separation: float,
    volume_confirm: bool,
) -> float:
    """
    Compute 0–1 confidence score.
    """
    score = 0.0

    # Expansion is the primary signal
    if expansion_pct > 50:
        score += 0.30
    elif expansion_pct > 20:
        score += 0.20
    elif expansion_pct > 10:
        score += 0.10

    # Squeeze conviction bonus
    if in_squeeze and squeeze_bars >= 3:
        score += 0.20
    elif in_squeeze:
        score += 0.10

    # Separation bonus
    abs_sep = abs(separation)
    if abs_sep > 1.0:
        score += 0.20
    elif abs_sep > 0.5:
        score += 0.10

    # Volume confirmation
    if volume_confirm:
        score += 0.10

    return min(score, 1.0)


def _compute_ema_mid_history(closes: list, periods: list, window: int) -> list:
    """
    Compute rolling group-midpoint EMA history for the last `window` bars.
    Returns list of floats (oldest first) — one midpoint per bar.
    """
    if len(closes) < max(periods) + window:
        return []
    results = []
    for i in range(window):
        # Use data up to the (len - window + i) bar as "current"
        cutoff = len(closes) - window + i + 1
        subset = closes[:cutoff]
        group = compute_group_emas(subset, periods)
        mid = get_group_mid(group)
        if mid is not None:
            results.append(mid)
    return results


# ── Exit Detection ─────────────────────────────────────────────────

def detect_guppy_exit(rows: list, position_direction: str) -> dict:
    """
    Check if a guppy open position should be exited.

    position_direction: 'LONG' or 'SHORT'

    Exit logic (guppy fast-group flip):
      - LONG exit: price closes below fast group LOW
      - SHORT exit: price closes above fast group HIGH

    Returns: {'exit': bool, 'reason': str, 'price': float, 'signal_price': float}
    """
    if len(rows) < DEFAULT_LOOKBACK:
        return {'exit': False, 'reason': None, 'price': None, 'signal_price': None}

    closes = [r[4] for r in rows]
    fast_emas = compute_group_emas(closes, FAST_GROUP)
    slow_emas = compute_group_emas(closes, SLOW_GROUP)

    if not fast_emas or not slow_emas:
        return {'exit': False, 'reason': None, 'price': None, 'signal_price': None}

    fast_high, fast_low = get_group_high_low(fast_emas)
    curr_close = closes[-1]
    prev_close = closes[-2] if len(closes) >= 2 else None

    # Primary exit: fast group flips (cross back through)
    fast_mid_history = _compute_ema_mid_history(closes, FAST_GROUP, window=3)
    slow_mid_history = _compute_ema_mid_history(closes, SLOW_GROUP, window=3)

    if len(fast_mid_history) >= 2 and len(slow_mid_history) >= 2:
        cross = detect_cross(fast_mid_history, slow_mid_history)
        if cross is not None and cross != position_direction:
            return {
                'exit': True,
                'reason': 'guppy_fast_flip',
                'price': curr_close,
                'signal_price': fast_low if position_direction == 'LONG' else fast_high,
            }

    # Secondary exit: price closes below fast group low (LONG) or above fast group high (SHORT)
    if position_direction == 'LONG':
        # Price closes below fast group low = exit
        if prev_close is not None and prev_close >= fast_low and curr_close < fast_low:
            return {
                'exit': True,
                'reason': 'guppy_fast_break',
                'price': curr_close,
                'signal_price': fast_low,
            }
    elif position_direction == 'SHORT':
        # Price closes above fast group high = exit
        if prev_close is not None and prev_close <= fast_high and curr_close > fast_high:
            return {
                'exit': True,
                'reason': 'guppy_fast_break',
                'price': curr_close,
                'signal_price': fast_high,
            }

    return {'exit': False, 'reason': None, 'price': None, 'signal_price': None}


# ── Data Fetching ──────────────────────────────────────────────────

def get_candles(token: str, lookback: int = DEFAULT_LOOKBACK,
                interval: str = "1m") -> list:
    """
    Fetch candle rows from candles.db.

    interval: '1m', '5m', '15m', '1h', '4h'
    Returns: list of (token, ts, open, high, low, close, volume, is_closed)
             ordered oldest → newest.
    """
    table_map = {
        '1m':  'candles_1m',
        '5m':  'candles_5m',
        '15m': 'candles_15m',
        '1h':  'candles_1h',
        '4h':  'candles_4h',
    }
    table = table_map.get(interval, 'candles_1m')

    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(f"""
            SELECT token, ts, open, high, low, close, volume, is_closed
            FROM {table}
            WHERE token = ?
            ORDER BY ts ASC
            LIMIT ?
        """, (token.upper(), lookback))
        rows = cur.fetchall()
        conn.close()
        return [tuple(r) for r in rows]
    except sqlite3.Error as e:
        print(f"[guppy_signals] DB error fetching {token} {interval}: {e}")
        return []


def get_available_tokens(interval: str = "1m") -> list:
    """Return list of tokens available in candles_1m."""
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute(f"SELECT DISTINCT token FROM candles_{interval} ORDER BY token")
        tokens = [r[0] for r in cur.fetchall()]
        conn.close()
        return tokens
    except sqlite3.Error as e:
        print(f"[guppy_signals] DB error listing tokens: {e}")
        return []


# ── Scan All Tokens ────────────────────────────────────────────────

def scan_token(token: str, interval: str = "1m", lookback: int = DEFAULT_LOOKBACK) -> Optional[dict]:
    """
    Scan a single token for guppy signal.
    Returns signal dict or None.
    """
    rows = get_candles(token, lookback=lookback, interval=interval)
    if not rows:
        return None
    return detect_guppy_signal(rows)


def scan_all_tokens(interval: str = "1m", lookback: int = DEFAULT_LOOKBACK) -> list:
    from hermes_constants import GUPPY_ENABLED
    if not GUPPY_ENABLED:
        return 0
    """
    Scan all available tokens in candles_1m for guppy signals.
    Returns list of signal dicts (one per token with signal).
    """
    tokens = get_available_tokens(interval=interval)
    results = []
    for token in tokens:
        sig = scan_token(token, interval=interval, lookback=lookback)
        if sig is not None:
            # ── Per-direction kill-switch ─────────────────────────────────────────
            from hermes_constants import GUPPY_PLUS_ENABLED, GUPPY_MINUS_ENABLED
            if sig['direction'] == 'LONG' and not GUPPY_PLUS_ENABLED:
                continue
            if sig['direction'] == 'SHORT' and not GUPPY_MINUS_ENABLED:
                continue
            sig['token'] = token
            results.append(sig)
    return results


def run(prices_dict=None):
    """Entry point for signals_runner. Returns count of signals emitted."""
    from signals.guppy import scan_all_tokens
    result = scan_all_tokens(interval="1m", lookback=120)
    return len(result) if isinstance(result, list) else result


# ── CLI Test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys, json

    if len(sys.argv) < 2:
        print("Usage: python3 guppy_signals.py <TOKEN> [interval=1m] [lookback=120]")
        sys.exit(1)

    token    = sys.argv[1].upper()
    interval = sys.argv[2] if len(sys.argv) > 2 else "1m"
    lookback = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_LOOKBACK

    rows = get_candles(token, lookback=lookback, interval=interval)
    if not rows:
        print(f"No data for {token}")
        sys.exit(1)

    print(f"Loaded {len(rows)} rows for {token}, interval={interval}")
    print(f"Latest close: {rows[-1][4]:.4f}  ts={rows[-1][1]}")

    sig = detect_guppy_signal(rows)
    if sig:
        print(f"\n=== SIGNAL: {sig['signal']} ===")
        print(f"  direction:    {sig['direction']}")
        print(f"  confidence:   {sig['confidence']:.2f}")
        print(f"  squeeze:       {sig['squeeze']}")
        print(f"  separation:   {sig['separation']:.3f}%")
        print(f"  cross:        {sig['cross']}")
        print(f"  vol confirm:  {sig['volume_confirm']}")
        print(f"  fast_mid:     {sig['fast_mid']:.4f}")
        print(f"  slow_mid:     {sig['slow_mid']:.4f}")
        print(f"  fast range:   {sig['fast_low']:.4f} – {sig['fast_high']:.4f}")
    else:
        print("\nNo signal.")

    # Also check exit on a hypothetical LONG position
    exit_check = detect_guppy_exit(rows, 'LONG')
    print(f"\nExit check (LONG): exit={exit_check['exit']}, reason={exit_check['reason']}, price={exit_check['price']}")
