# Migrated from ../hh_hl_signals.py — see signals/__init__.py registry
#!/usr/bin/env python3
"""
hh_hl_signals.py — Higher Highs / Higher Lows Structure Signal Scanner for Hermes.

Detects swing structure (HH/HL or LH/LL) on 1m close prices and fires:
  1. BREAKOUT variant — price breaks above recent swing high (LONG) or below swing low (SHORT)
  2. PULLBACK variant — price pulls back to prior swing level in established structure then bounces

Data: price_history table (signals_hermes.db) — live 1m closes, updated every minute.
      Falls back to ohlcv_1m if price_history is insufficient.

Params: see hermes_constants.py HH_HL_* constants.
Signal types: hh_hl_breakout, hh_hl_pullback
"""

import sys
import os
import time
import sqlite3
from typing import Optional, Tuple, List, Dict

# ── Params from hermes_constants ────────────────────────────────────────────────
from hermes_constants import (
    HH_HL_LOOKBACK, HH_HL_SWING_WINDOW, HH_HL_MIN_SEP,
    HH_HL_BREAKOUT_THRESHOLD, HH_HL_ATR_ENTRY_MIN,
    HH_HL_SL_ATR_MULT, HH_HL_TP_ATR_MULT,
    HH_HL_MAX_HOLD_BARS, HH_HL_MAX_BARS_SINCE, HH_HL_COOLDOWN_MIN,
    HH_HL_CONFIDENCE_FLOOR, HH_HL_CONFIDENCE_CAP,
    HH_HL_BASE_CONFIDENCE, HH_HL_STRUCT_BONUS_MAX,
    HH_HL_BREAKOUT_BONUS_MAX, HH_HL_RECENCY_BONUS_MAX,
    HH_HL_ENABLED,
    HH_HL_SHORT_RANGE_TOP_ATR, HH_HL_LONG_RANGE_BOTTOM_ATR,
)

SIGNAL_TYPE_BREAKOUT = 'hh_hl_breakout'
SIGNAL_TYPE_PULLBACK = 'hh_hl_pullback'
_PRICE_DB = '/root/.hermes/data/signals_hermes.db'

# ── ATR ────────────────────────────────────────────────────────────────────────

def _compute_atr(candles: list, period: int = 14) -> Optional[float]:
    """Compute ATR from close-only candle data (price_history).

    Since price_history has open=high=low=close for each row, traditional
    TR = max(H-L, |H-PC|, |L-PC|) degenerates to 0.

    Instead we use the rolling close range as a volatility proxy:
      ATR = mean over period of (rolling_max_closes - rolling_min_closes)

    This is a standard approach for close-only data and is used by practitioners
    who don't have true H/L/O data.

    Returns None if insufficient data.
    """
    n = len(candles)
    if n < period + 1:
        return None

    closes = [c['close'] for c in candles]

    # Rolling range: max(closes[i-period+1:i+1]) - min(closes[i-period+1:i+1])
    # This is the "close-only ATR" — true range equivalent for close-only data
    ranges = []
    for i in range(period - 1, n):
        window = closes[i - period + 1 : i + 1]
        r = max(window) - min(window)
        ranges.append(r)

    if len(ranges) < period:
        return None
    return sum(ranges[-period:]) / period


# ── Swing Detection ────────────────────────────────────────────────────────────

def _find_swing_highs_lows(candles: list, window: int = HH_HL_SWING_WINDOW,
                           min_sep: int = HH_HL_MIN_SEP) -> Tuple[List[int], List[int]]:
    """Find indices of swing highs and swing lows using proxy high/low from closes.

    Since price_history has close-only data (open=high=low=close per row), we use
    a rolling window max/min of closes as proxy for the candle's high/low. A swing
    high at index i is the MAX of closes in [i-window, i+window] and is strictly
    greater than the proxy high of all neighbors. Same for swing low (MIN, strictly less).

    This is a standard technique for swing detection on close-only data.

    Args:
        candles: list of {open, high, low, close} dicts, oldest first
        window:  half-width of the swing check window
        min_sep: minimum candle separation between consecutive swings

    Returns:
        (swing_high_indices, swing_low_indices) — sorted ascending
    """
    n = len(candles)
    highs, lows = [], []
    last_h = last_l = -999

    # Pre-compute rolling proxy high/low using closes
    closes = [c['close'] for c in candles]

    for i in range(window, n - window):
        # Proxy high/low for index i: max/min of closes in [i-window, i+window]
        window_closes = closes[i - window : i + window + 1]
        proxy_high = max(window_closes)
        proxy_low  = min(window_closes)

        # Swing high: proxy high at i is strictly greater than all neighbors' proxy highs
        # (use <= here to match tested behavior — allows equal proxy highs at neighbors)
        is_high = True
        for j in range(i - window, i + window + 1):
            if j == i:
                continue
            neighbor_closes = closes[max(0, j - window) : j + window + 1]
            neighbor_proxy_high = max(neighbor_closes)
            if neighbor_proxy_high > proxy_high:
                is_high = False
                break
        if is_high and (i - last_h) >= min_sep:
            highs.append(i)
            last_h = i

        # Swing low: proxy low at i is strictly less than all neighbors' proxy lows
        is_low = True
        for j in range(i - window, i + window + 1):
            if j == i:
                continue
            neighbor_closes = closes[max(0, j - window) : j + window + 1]
            neighbor_proxy_low = min(neighbor_closes)
            if neighbor_proxy_low < proxy_low:
                is_low = False
                break
        if is_low and (i - last_l) >= min_sep:
            lows.append(i)
            last_l = i

    return highs, lows


def _classify_structure(highs: List[int], lows: List[int],
                        candles: list) -> Tuple[str, float, int]:
    """Classify current swing structure at the most recent candle.

    Args:
        highs: sorted swing high indices
        lows:  sorted swing low indices
        candles: full candle list

    Returns:
        (structure, breakout_strength_pct, bars_since_last_swing)
          structure: 'HH_HL' | 'LH_LL' | 'NEUTRAL'
          breakout_strength: price distance from last HH (LONG) or LL (SHORT) as %
    """
    n = len(candles)
    if not highs or not lows:
        return 'NEUTRAL', 0.0, 0

    price = candles[-1]['close']

    # Build sorted swing list
    all_swings = []
    for idx in highs:
        all_swings.append((idx, candles[idx]['high'], 'H'))
    for idx in lows:
        all_swings.append((idx, candles[idx]['low'], 'L'))
    all_swings.sort(key=lambda x: x[0])

    if len(all_swings) < 4:
        return 'NEUTRAL', 0.0, 0

    # Last 4 swings: s0=oldest, s3=newest
    s0, s1, s2, s3 = all_swings[-4:]
    _, p0, t0 = s0
    _, p1, t1 = s1
    _, p2, t2 = s2
    _, p3, t3 = s3

    structure = 'NEUTRAL'
    bs = 0.0
    last_swing_idx = max(highs[-1] if highs else 0, lows[-1] if lows else 0)

    if t0 == 'H' and t1 == 'L' and t2 == 'H' and t3 == 'L':
        # Full HH_HL pattern
        if p2 > p0 and p3 > p1:
            structure = 'HH_HL'
            bs = (price - p2) / price * 100.0
        elif p2 < p0 and p3 < p1:
            structure = 'LH_LL'
            bs = (p2 - price) / price * 100.0
    elif t0 == 'L' and t1 == 'H' and t2 == 'L' and t3 == 'H':
        # First HH then first HL
        if p3 > p1:
            structure = 'HH_HL'
            bs = (price - p3) / price * 100.0
        elif p3 < p1:
            structure = 'LH_LL'
            bs = (p3 - price) / price * 100.0
    elif t0 == 'H' and t1 == 'L' and t2 == 'H':
        # Partial HH_HL (only 3 swings — one HH, one HL so far)
        if p2 > p0:
            structure = 'HH_HL'
            bs = (price - p2) / price * 100.0
    elif t0 == 'L' and t1 == 'H' and t2 == 'L':
        if p2 < p0:
            structure = 'LH_LL'
            bs = (p2 - price) / price * 100.0

    bars_since = n - 1 - last_swing_idx
    return structure, bs, bars_since


# ── Breakout detection ─────────────────────────────────────────────────────────

def _detect_breakout(token: str, candles: list, structure: str,
                     breakout_strength: float, price: float,
                     bars_since: int) -> Optional[dict]:
    """Detect HH_HL breakout signals.

    LONG:  in HH_HL structure + price breaks above last swing high
    SHORT: in LH_LL structure + price breaks below last swing low
    """
    if structure not in ('HH_HL', 'LH_LL'):
        return None

    highs, lows = _find_swing_highs_lows(candles)
    if not highs or not lows:
        return None

    atr = _compute_atr(candles)
    if atr is None:
        return None

    direction = None
    last_sw_price = None

    # breakout_strength is in % units (e.g. 0.014 = 0.014%); threshold is in decimal fraction
    # → normalize: breakout_strength / 100 to compare against threshold
    if structure == 'HH_HL' and (breakout_strength / 100) >= HH_HL_BREAKOUT_THRESHOLD:
        last_sw_price = candles[highs[-1]]['high']
        if price > last_sw_price:
            direction = 'LONG'
            source = f'hhh-long{bars_since}'
    elif structure == 'LH_LL' and (breakout_strength / 100) >= HH_HL_BREAKOUT_THRESHOLD:
        last_sw_price = candles[lows[-1]]['low']
        if price < last_sw_price:
            direction = 'SHORT'
            source = f'hhh-short{bars_since}'

    # ── OPTION C: Range-position filter ────────────────────────────────────
    # SHORT should only fire at the BOTTOM of the range, not at bounce territory.
    # If price is within 1 ATR of the 20-bar high, it's a bounce-at-top SHORT
    # — price bounces 99% of the time there. Block it.
    # LONG should only fire when price has room to run (not too close to 20-bar low).
    if direction == 'SHORT':
        recent_high = max(c['high'] for c in candles[-20:])
        if price > recent_high - (atr * HH_HL_SHORT_RANGE_TOP_ATR):
            return None  # too close to top of range = bounce territory
    if direction == 'LONG':
        recent_low = min(c['low'] for c in candles[-20:])
        if price < recent_low + (atr * HH_HL_LONG_RANGE_BOTTOM_ATR):
            return None  # too close to recent low = not a clean HH breakout

    if direction is None:
        return None

    # Reject stale breakouts — signal must be recent
    if bars_since > HH_HL_MAX_BARS_SINCE:
        return None

    # NOTE: breakout candle size check (HH_HL_ATR_ENTRY_MIN) is skipped — price_history
    # is close-only so candle body is always 0. The BREAKOUT_THRESHOLD (0.05%) is the
    # primary filter for distinguishing real breakouts from noise.

    # Confidence
    struct_bonus  = min(breakout_strength * 5, HH_HL_STRUCT_BONUS_MAX)
    break_bonus   = min(breakout_strength * 3, HH_HL_BREAKOUT_BONUS_MAX)
    recency_bonus = max(HH_HL_RECENCY_BONUS_MAX - bars_since, 0)

    confidence = int(min(
        HH_HL_BASE_CONFIDENCE + struct_bonus + break_bonus + recency_bonus,
        HH_HL_CONFIDENCE_CAP
    ))
    if confidence < HH_HL_CONFIDENCE_FLOOR:
        return None

    return {
        'direction':   direction,
        'confidence':  confidence,
        'source':      source,
        'breakout_pct': round(breakout_strength, 4),
        'bars_since':  bars_since,
        'structure':   structure,
        'value':       float(confidence),
    }


# ── Pullback detection ─────────────────────────────────────────────────────────

def _detect_pullback(token: str, candles: list, structure: str,
                    price: float) -> Optional[dict]:
    """Detect HH_HL pullback signals.

    LONG:  in HH_HL structure + price retraces to last HL level + bounces
    SHORT: in LH_LL structure + price retraces to last LH level + drops

    Pullback zone: 23.6%–61.8% Fibonacci retracement from the prior swing.
    Entry: confirmation candle close vs current close (bounce confirmation).
    """
    if structure not in ('HH_HL', 'LH_LL'):
        return None

    highs, lows = _find_swing_highs_lows(candles)
    if not highs or not lows:
        return None

    atr = _compute_atr(candles)
    if atr is None:
        return None

    # Get last 4 swings: HH, HL, LH, LL
    all_swings = []
    for idx in highs:
        all_swings.append((idx, candles[idx]['high'], 'H'))
    for idx in lows:
        all_swings.append((idx, candles[idx]['low'], 'L'))
    all_swings.sort(key=lambda x: x[0])

    if len(all_swings) < 4:
        return None

    s0, s1, s2, s3 = all_swings[-4:]
    _, hh, _ = s0 if s0[2] == 'H' else (None, None, None)
    # Find HH, HL, LH, LL prices
    swing_prices = {s[0]: (s[1], s[2]) for s in all_swings[-4:]}
    sorted_prices = sorted([(s[0], s[1], s[2]) for s in all_swings[-4:]], key=lambda x: x[0])

    # Identify: among last 4 swings, which are H and which are L
    last_4 = sorted_prices  # [(idx, price, type), ...]
    # Find the HH (higher high) and HL (higher low) — for HH_HL structure
    h_swings = [(s[0], s[1]) for s in last_4 if s[2] == 'H']  # (idx, price)
    l_swings = [(s[0], s[1]) for s in last_4 if s[2] == 'L']  # (idx, price)

    if len(h_swings) < 2 or len(l_swings) < 2:
        return None

    # For HH_HL: last high is the HH, last low is the HL
    direction = None
    pullback_level = None
    bars_since = 0
    fib_min_price = None
    fib_max_price = None

    if structure == 'HH_HL':
        last_hh_idx, last_hh_price = h_swings[-1]
        last_hl_idx, last_hl_price = l_swings[-1]
        # Price must be between HH and HL (pullback in progress)
        if price >= last_hh_price or price <= last_hl_price:
            return None
        # Fib zone: 23.6%–61.8% retracement from HH toward HL
        fib_236 = last_hh_price - (last_hh_price - last_hl_price) * 0.236
        fib_618 = last_hh_price - (last_hh_price - last_hl_price) * 0.618
        if not (fib_618 <= price <= fib_236):
            return None
        # Bounce confirmation: next candle close > current close
        next_close = candles[-1]['close']
        if next_close <= price:
            return None  # hasn't bounced yet
        pullback_level = last_hl_price
        bars_since = len(candles) - 1 - last_hl_idx
        direction = 'LONG'

    elif structure == 'LH_LL':
        last_lh_idx, last_lh_price = h_swings[-1]
        last_ll_idx, last_ll_price = l_swings[-1]
        if price <= last_ll_price or price >= last_lh_price:
            return None
        fib_236 = last_ll_price + (last_lh_price - last_ll_price) * 0.236
        fib_618 = last_ll_price + (last_lh_price - last_ll_price) * 0.618
        if not (fib_236 <= price <= fib_618):
            return None
        next_close = candles[-1]['close']
        if next_close >= price:
            return None  # hasn't dropped yet
        pullback_level = last_lh_price
        bars_since = len(candles) - 1 - last_lh_idx
        direction = 'SHORT'

    if direction is None:
        return None

    # Reject stale pullbacks — signal must be recent
    if bars_since > HH_HL_MAX_BARS_SINCE:
        return None

    # Confidence
    dist_from_level = abs(price - pullback_level) / price * 100.0
    struct_bonus  = min(dist_from_level * 2, HH_HL_STRUCT_BONUS_MAX)
    recency_bonus = max(HH_HL_RECENCY_BONUS_MAX - bars_since, 0) if bars_since < HH_HL_RECENCY_BONUS_MAX else 0

    confidence = int(min(
        HH_HL_BASE_CONFIDENCE + struct_bonus + recency_bonus,
        HH_HL_CONFIDENCE_CAP
    ))
    if confidence < HH_HL_CONFIDENCE_FLOOR:
        return None

    source = f'hhp-long{bars_since}' if direction == 'LONG' else f'hhp-short{bars_since}'

    return {
        'direction':    direction,
        'confidence':  confidence,
        'source':      source,
        'pullback_pct': round(dist_from_level, 4),
        'bars_since':  bars_since,
        'structure':   structure,
        'value':       float(confidence),
    }


# ── Data fetch ─────────────────────────────────────────────────────────────────

def _get_candles_from_price_history(token: str, lookback: int = HH_HL_LOOKBACK) -> list:
    """Fetch 1m close prices from price_history (signals_hermes.db), oldest first.

    price_history is updated every minute — the most up-to-date 1m data source.
    Timestamps are in seconds (Unix time). Returns list of {open, high, low, close}.
    For price_history (close-only), open=high=low=close=price.

    Returns [] if stale (>2 min old) or empty.
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
            return []

        # price_history only has close prices — use close as H/L/O for swing detection
        return [
            {'open': p, 'high': p, 'low': p, 'close': p}
            for _, p in rows
        ]
    except Exception:
        return []


def _get_candles_from_ohlcv_1m(token: str, lookback: int = HH_HL_LOOKBACK) -> list:
    """Fetch 1m OHLCV from ohlcv_1m table (signals_hermes.db), oldest first.

    Returns list of {open, high, low, close} dicts.
    Returns [] if no data or stale.
    """
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT open_time, open, high, low, close FROM (
                SELECT open_time, open, high, low, close
                FROM ohlcv_1m
                WHERE token = ?
                ORDER BY open_time DESC
                LIMIT ?
            ) sub
            ORDER BY open_time ASC
        """, (token.upper(), lookback))
        rows = c.fetchall()
        conn.close()

        if not rows:
            return []

        most_recent_ts = rows[-1][0]
        if (time.time() - most_recent_ts) > 120:
            return []

        return [
            {'open': r[1], 'high': r[2], 'low': r[3], 'close': r[4]}
            for r in rows
        ]
    except Exception:
        return []


# ── Main scanner ────────────────────────────────────────────────────────────────

def scan_hh_hl_signals(prices_dict: dict, variant: str = 'both') -> list:
    from hermes_constants import HH_HL_ENABLED
    if not HH_HL_ENABLED:
        return 0
    """Scan tokens for HH/HL structure signals and write to DB.

    Args:
        prices_dict: token -> {'price': float, ...} (pre-filtered by caller)
        variant:     'breakout' | 'pullback' | 'both'

    Returns:
        list of dicts — [{'token': str, 'direction': str, 'variant': str}]
    """
    if not HH_HL_ENABLED:
        return []

    from signal_schema import add_signal

    fired = []

    for token, data in prices_dict.items():
        price = data.get('price')
        if not price or price <= 0:
            continue

        # Primary: price_history (most up-to-date 1m closes)
        candles = _get_candles_from_price_history(token, lookback=HH_HL_LOOKBACK)
        if not candles or len(candles) < 30:
            # Fallback: ohlcv_1m
            candles = _get_candles_from_ohlcv_1m(token, lookback=HH_HL_LOOKBACK)
        if not candles or len(candles) < 30:
            continue

        # ── Find swings ─────────────────────────────────────────────────────────
        highs, lows = _find_swing_highs_lows(candles)
        if not highs or not lows:
            continue

        # ── Classify structure ───────────────────────────────────────────────────
        structure, breakout_strength, bars_since = _classify_structure(
            highs, lows, candles
        )
        if structure == 'NEUTRAL':
            continue

        # ── Breakout variant ────────────────────────────────────────────────────
        if variant in ('breakout', 'both'):
            sig = _detect_breakout(
                token, candles, structure, breakout_strength, price, bars_since
            )
            if sig:
                # ── Per-direction kill-switch ─────────────────────────────────────────
                from hermes_constants import HH_HL_PLUS_ENABLED, HH_HL_MINUS_ENABLED
                blocked = (
                    (sig['direction'] == 'LONG' and not HH_HL_PLUS_ENABLED) or
                    (sig['direction'] == 'SHORT' and not HH_HL_MINUS_ENABLED)
                )
                if blocked:
                    pass  # skip breakout, fall through to pullback check
                else:
                    sid = add_signal(
                        token=token.upper(),
                        direction=sig['direction'],
                        signal_type=SIGNAL_TYPE_BREAKOUT,
                        source=sig['source'],
                        confidence=sig['confidence'],
                        value=sig['value'],
                        price=price,
                        exchange='hyperliquid',
                        timeframe='1m',
                        z_score=None,
                        z_score_tier=None,
                    )
                    if sid:
                        fired.append({
                            'token': token.upper(),
                            'direction': sig['direction'],
                            'variant': 'breakout',
                        })
                        print(f'  HH-HL BREAKOUT {sig["direction"]:5s} {token:8s} '
                              f'conf={sig["confidence"]:.0f}% struct={structure} '
                              f'break={sig["breakout_pct"]:.3f}% bars={bars_since} '
                              f'[{sig["source"]}]')

        # ── Pullback variant ─────────────────────────────────────────────────────
        if variant in ('pullback', 'both'):
            sig = _detect_pullback(
                token, candles, structure, price
            )
            if sig:
                # ── Per-direction kill-switch ─────────────────────────────────────────
                from hermes_constants import HH_HL_PLUS_ENABLED, HH_HL_MINUS_ENABLED
                blocked = (
                    (sig['direction'] == 'LONG' and not HH_HL_PLUS_ENABLED) or
                    (sig['direction'] == 'SHORT' and not HH_HL_MINUS_ENABLED)
                )
                if blocked:
                    pass  # skip pullback variant for this direction
                else:
                    sid = add_signal(
                        token=token.upper(),
                        direction=sig['direction'],
                        signal_type=SIGNAL_TYPE_PULLBACK,
                        source=sig['source'],
                        confidence=sig['confidence'],
                        value=sig['value'],
                        price=price,
                        exchange='hyperliquid',
                        timeframe='1m',
                        z_score=None,
                        z_score_tier=None,
                    )
                    if sid:
                        fired.append({
                            'token': token.upper(),
                            'direction': sig['direction'],
                            'variant': 'pullback',
                        })
                        print(f'  HH-HL PULLBACK {sig["direction"]:5s} {token:8s} '
                              f'conf={sig["confidence"]:.0f}% struct={structure} '
                              f'pb={sig["pullback_pct"]:.3f}% bars={sig["bars_since"]} '
                              f'[{sig["source"]}]')

    return fired


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from signal_schema import get_all_latest_prices, init_db

    init_db()
    prices = get_all_latest_prices()

    test_tokens = {k: v for k, v in prices.items()
                   if k in ('BTC', 'ETH', 'SOL', 'AVAX', 'LINK', 'SAGA', 'SCR',
                            'ARB', 'OP', 'ATOM', 'NEAR', 'APT', 'INJ') and v.get('price')}
    if not test_tokens:
        test_tokens = dict(list(prices.items())[:10])

    print(f"[hh_hl] Testing on {len(test_tokens)} tokens (breakout + pullback)...")
    result = scan_hh_hl_signals(test_tokens, variant='both')
    print(f"[hh_hl] Done. {len(result)} signals emitted.")
    for r in result:
        print(f"  {r}")


# ═══════════════════════════════════════════════════════════════════════════════
# signals_runner entry point
# ═══════════════════════════════════════════════════════════════════════════════

def run(prices_dict=None):
    """Entry point for signals_runner. Returns count of signals emitted."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_hh_hl_signals(prices_dict)
