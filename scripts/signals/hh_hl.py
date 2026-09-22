#!/usr/bin/env python3
"""hh_hl.py — Structure Sniper: multi-confluence market structure signal (v2).

Detects HH/HL (uptrend) and LH/LL (downtrend) structure on 5m OHLCV candles
and fires signals in TWO modes:

  1. BREAKOUT mode — price breaks above last swing high (LONG) / below swing low (SHORT)
  2. PULLBACK mode — price pulls back to the higher low (LONG) / lower high (SHORT)
     and shows bounce confirmation. Better R:R than chasing breakouts.

Architecture: signal → add_signal() → compactor → hotset → guardian

Confluence gates (ALL must pass):
  1. Structure clarity — clear 4+ swing pattern on 5m
  2. Higher TF trend — 1H EMA20 vs EMA50 alignment
  3. Volume confirmation — candle > 1.5x 20-period average
  4. Momentum — RSI in favorable zone (mode-aware thresholds)
  5. EMA alignment — price vs 5m EMA20 + EMA20 vs EMA50 (relaxed for pullback)
  6. Volatility — ATR% between 0.3% and 1.5%
  7. Freshness — signal within last 10 bars on 5m

Data sources:
  Primary: candles_5m (OHLCV, proper H/L for swing detection)
  Higher TF: candles_1h (EMA20/50 trend confirmation)

Signal types: hh_hl_breakout_long, hh_hl_breakout_short
Source strings: hh-hl+ (LONG), hh-hl- (SHORT)
"""

import sys, os, sqlite3, time
from typing import Optional, List, Tuple, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA, CANDLES_DB, STATIC_DB

from hermes_constants import (
    HH_HL_ENABLED, HH_HL_PLUS_ENABLED, HH_HL_MINUS_ENABLED,
    HH_HL_LOOKBACK, HH_HL_SWING_WINDOW, HH_HL_MIN_SEP, HH_HL_MIN_SWINGS,
    HH_HL_BREAKOUT_THRESHOLD, HH_HL_MAX_BARS_SINCE,
    HH_HL_SL_ATR_MULT, HH_HL_TP_ATR_MULT,
    HH_HL_AVG_VOL_MULT, HH_HL_VOL_LOOKBACK,
    HH_HL_RSI_PERIOD, HH_HL_RSI_LONG_MIN, HH_HL_RSI_LONG_MAX,
    HH_HL_RSI_SHORT_MIN, HH_HL_RSI_SHORT_MAX,
    HH_HL_EMA_FAST, HH_HL_EMA_SLOW,
    HH_HL_HTF_EMA_FAST, HH_HL_HTF_EMA_SLOW,
    HH_HL_VOL_FLOOR_PCT, HH_HL_VOL_CAP_PCT,
    HH_HL_CONF_BASE, HH_HL_CONF_FLOOR, HH_HL_CONF_CAP,
    HH_HL_CONF_STRUCT_BONUS, HH_HL_CONF_VOLUME_BONUS,
    HH_HL_CONF_HTF_BONUS, HH_HL_CONF_MOMENTUM_BONUS,
    HH_HL_COOLDOWN_HOURS,
    HH_HL_STALE_5M_SEC, HH_HL_STALE_1H_SEC,
    HH_HL_MIN_CANDLES_5M, HH_HL_MIN_CANDLES_1H,
    HH_HL_STRUCT_MIN_SWINGS, HH_HL_MAX_EXTENSION_ATR,
    HH_HL_HTF_STRONG_SPREAD, HH_HL_HTF_BONUS_SPREAD,
    HH_HL_RSI_SWEET_LONG_LOW, HH_HL_RSI_SWEET_LONG_HIGH,
    HH_HL_RSI_SWEET_SHORT_LOW, HH_HL_RSI_SWEET_SHORT_HIGH,
    HH_HL_VOL_STRONG_MULT, HH_HL_BACKUP_ATR_PCT,
    HH_HL_PB_ENABLED, HH_HL_PB_PROXIMITY_ATR,
    HH_HL_PB_RSI_LONG_MIN, HH_HL_PB_RSI_LONG_MAX,
    HH_HL_PB_RSI_SHORT_MIN, HH_HL_PB_RSI_SHORT_MAX,
    HH_HL_PB_BOUNCE_BODY_PCT, HH_HL_PB_MAX_PULLBACK_PCT,
    HH_HL_PB_STRUCT_LOOKBACK, HH_HL_PB_BOUNCE_LOOKBACK,
    HH_HL_PB_EMA_RELAXED, HH_HL_PB_CONF_BONUS,
    LONG_BLACKLIST, SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG  = 'hh_hl_breakout_long'
SIGNAL_TYPE_SHORT = 'hh_hl_breakout_short'
SOURCE_LONG       = 'hh-hl+'
SOURCE_SHORT      = 'hh-hl-'

_CANDLES_DB = CANDLES_DB
_PRICE_DB   = STATIC_DB  # signals_hermes.db (price_history fallback)


# ═══════════════════════════════════════════════════════════════════════════════
# Data Fetch
# ═══════════════════════════════════════════════════════════════════════════════

def _get_candles_5m(token: str, limit: int = 200) -> list:
    """Fetch 5m OHLCV from candles.db, oldest first. Returns [{open, high, low, close, volume}].
    Returns [] if stale or empty."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT open, high, low, close, volume, ts FROM (
                SELECT open, high, low, close, volume, ts
                FROM candles_5m
                WHERE token = ? AND is_closed = 1
                ORDER BY ts DESC
                LIMIT ?
            ) sub
            ORDER BY ts ASC
        """, (token.upper(), limit))
        rows = c.fetchall()
        if not rows:
            return []
        most_recent_ts = rows[-1][5]
        if (time.time() - most_recent_ts) > HH_HL_STALE_5M_SEC:
            return []
        return [{'open': r[0], 'high': r[1], 'low': r[2], 'close': r[3], 'volume': r[4]}
                for r in rows]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _get_candles_1h(token: str, limit: int = 60) -> list:
    """Fetch 1H OHLCV from candles.db, oldest first. Returns [{open, high, low, close}].
    Returns [] if stale or empty."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT open, high, low, close, ts FROM (
                SELECT open, high, low, close, ts
                FROM candles_1h
                WHERE token = ?
                ORDER BY ts DESC
                LIMIT ?
            ) sub
            ORDER BY ts ASC
        """, (token.upper(), limit))
        rows = c.fetchall()
        if not rows:
            return []
        most_recent_ts = rows[-1][4]
        if (time.time() - most_recent_ts) > HH_HL_STALE_1H_SEC:
            return []
        return [{'open': r[0], 'high': r[1], 'low': r[2], 'close': r[3]}
                for r in rows]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Technical Indicators
# ═══════════════════════════════════════════════════════════════════════════════

def _ema(closes: list, period: int) -> Optional[float]:
    """Return latest EMA value. Returns None if insufficient data."""
    if len(closes) < period:
        return None
    k = 2.0 / (period + 1)
    val = sum(closes[:period]) / period
    for price in closes[period:]:
        val = price * k + val * (1 - k)
    return val


def _rsi(closes: list, period: int = 14) -> Optional[float]:
    """Calculate RSI. Returns None if insufficient data."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _volume_atr(candles: list, period: int = 14) -> Optional[float]:
    """ATR from OHLCV data using true range."""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        h = candles[i]['high']
        l = candles[i]['low']
        pc = candles[i - 1]['close']
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period


# ═══════════════════════════════════════════════════════════════════════════════
# Swing Detection (on 5m OHLCV candles)
# ═══════════════════════════════════════════════════════════════════════════════

def _find_swings(candles: list, window: int = HH_HL_SWING_WINDOW,
                 min_sep: int = HH_HL_MIN_SEP) -> Tuple[List[Tuple[int, float, str]],
                                                          List[Tuple[int, float, str]]]:
    """Find swing highs and swing lows on 5m OHLCV data.

    Swing high at index i: candle[i].high is the highest high in [i-window, i+window].
    Swing low at index i: candle[i].low is the lowest low in [i-window, i+window].

    Returns:
        (swing_highs, swing_lows) — each is list of (index, price, type) sorted by index.
    """
    n = len(candles)
    if n < 2 * window + 1:
        return [], []

    highs = []
    lows = []
    last_h_idx = -999
    last_l_idx = -999

    for i in range(window, n - window):
        # Check swing high
        is_high = True
        for j in range(i - window, i + window + 1):
            if j == i:
                continue
            if candles[j]['high'] >= candles[i]['high']:
                is_high = False
                break
        if is_high and (i - last_h_idx) >= min_sep:
            highs.append((i, candles[i]['high'], 'H'))
            last_h_idx = i

        # Check swing low
        is_low = True
        for j in range(i - window, i + window + 1):
            if j == i:
                continue
            if candles[j]['low'] <= candles[i]['low']:
                is_low = False
                break
        if is_low and (i - last_l_idx) >= min_sep:
            lows.append((i, candles[i]['low'], 'L'))
            last_l_idx = i

    return highs, lows


def _classify_structure(swings: list) -> Tuple[str, int]:
    """Classify market structure from sorted swing points.

    Returns:
        (structure, num_swings) — 'HH_HL' | 'LH_LL' | 'NEUTRAL', swing count
    """
    if len(swings) < HH_HL_MIN_SWINGS:
        return 'NEUTRAL', 0

    recent = swings[-6:] if len(swings) >= 6 else swings

    h_swings = [(i, p) for i, p, t in recent if t == 'H']
    l_swings = [(i, p) for i, p, t in recent if t == 'L']

    if len(h_swings) < 2 or len(l_swings) < 2:
        return 'NEUTRAL', len(swings)

    hh_count = sum(1 for j in range(1, len(h_swings)) if h_swings[j][1] > h_swings[j - 1][1])
    hl_count = sum(1 for j in range(1, len(l_swings)) if l_swings[j][1] > l_swings[j - 1][1])
    lh_count = sum(1 for j in range(1, len(h_swings)) if h_swings[j][1] < h_swings[j - 1][1])
    ll_count = sum(1 for j in range(1, len(l_swings)) if l_swings[j][1] < l_swings[j - 1][1])

    if hh_count >= 1 and hl_count >= 1:
        return 'HH_HL', len(swings)
    if lh_count >= 1 and ll_count >= 1:
        return 'LH_LL', len(swings)

    return 'NEUTRAL', len(swings)


# ═══════════════════════════════════════════════════════════════════════════════
# Pullback Detection
# ═══════════════════════════════════════════════════════════════════════════════

def _detect_pullback(direction: str, candles_5m: list,
                     swing_highs: list, swing_lows: list, all_swings: list,
                     price: float, atr_val: float,
                     closes_5m: list) -> Optional[dict]:
    """Detect pullback to HL/LH level with bounce confirmation.

    For LONG (HH/HL structure):
      - Price is dipping toward the last higher low
      - Price is within ATR proximity of the HL level
      - Last N candles show bounce (bullish body > threshold)
      - Not below the Fibonacci 61.8% retracement from the recent HH to HL

    For SHORT (LH/LL structure):
      - Price is rallying toward the last lower high
      - Price is within ATR proximity of the LH level
      - Last N candles show rejection (bearish body > threshold)
      - Not above the Fibonacci 61.8% retracement from the recent LL to LH

    Returns {swing_level, pullback_pct, bounce_quality} or None.
    """
    if len(swing_highs) < HH_HL_PB_STRUCT_LOOKBACK or len(swing_lows) < HH_HL_PB_STRUCT_LOOKBACK:
        return None

    # Get the last HH_HL_PB_STRUCT_LOOKBACK swing highs and lows
    recent_hs = swing_highs[-HH_HL_PB_STRUCT_LOOKBACK:]
    recent_ls = swing_lows[-HH_HL_PB_STRUCT_LOOKBACK:]

    if direction == 'LONG':
        # Need: last swing low = HL (higher than previous)
        if len(recent_ls) < 2:
            return None
        last_hl_price = recent_ls[-1][1]
        prev_hl_price = recent_ls[-2][1]
        if last_hl_price <= prev_hl_price:
            return None  # not a higher low

        # Last swing high = HH (higher than previous)
        if len(recent_hs) < 2:
            return None
        last_hh_price = recent_hs[-1][1]

        # Price must be between HH and HL (pulling back)
        if price >= last_hh_price or price <= last_hl_price:
            return None

        # Proximity: price must be within ATR of the HL level
        dist_from_hl = abs(price - last_hl_price)
        if dist_from_hl > atr_val * HH_HL_PB_PROXIMITY_ATR:
            return None

        # Fibonacci: pullback must not exceed 61.8% from HH toward HL
        pullback_range = last_hh_price - last_hl_price
        if pullback_range <= 0:
            return None
        pullback_depth = (last_hh_price - price) / pullback_range
        if pullback_depth > HH_HL_PB_MAX_PULLBACK_PCT:
            return None

        # Bounce confirmation: last N candles show buying pressure
        n = HH_HL_PB_BOUNCE_LOOKBACK
        if len(candles_5m) < n + 1:
            return None
        bounce_candles = candles_5m[-(n + 1):-1]  # exclude current (we're IN the bounce)
        if not bounce_candles:
            return None
        # At least one candle must have bullish body > threshold of its range
        has_bounce = False
        for bc in bounce_candles:
            body = bc['close'] - bc['open']
            rng = bc['high'] - bc['low']
            if rng > 0 and body / rng >= HH_HL_PB_BOUNCE_BODY_PCT:
                has_bounce = True
                break
        if not has_bounce:
            return None

        pullback_pct = pullback_depth * 100.0
        return {
            'swing_level': last_hl_price,
            'pullback_pct': round(pullback_pct, 4),
            'pullback_depth': round(pullback_depth, 4),
        }

    else:  # SHORT
        # Need: last swing high = LH (lower than previous)
        if len(recent_hs) < 2:
            return None
        last_lh_price = recent_hs[-1][1]
        prev_lh_price = recent_hs[-2][1]
        if last_lh_price >= prev_lh_price:
            return None  # not a lower high

        # Last swing low = LL (lower than previous)
        if len(recent_ls) < 2:
            return None
        last_ll_price = recent_ls[-1][1]

        # Price must be between LL and LH (rallying back)
        if price <= last_ll_price or price >= last_lh_price:
            return None

        # Proximity: price must be within ATR of the LH level
        dist_from_lh = abs(price - last_lh_price)
        if dist_from_lh > atr_val * HH_HL_PB_PROXIMITY_ATR:
            return None

        # Fibonacci: rally must not exceed 61.8% from LL toward LH
        pullback_range = last_lh_price - last_ll_price
        if pullback_range <= 0:
            return None
        pullback_depth = (price - last_ll_price) / pullback_range
        if pullback_depth > HH_HL_PB_MAX_PULLBACK_PCT:
            return None

        # Bounce confirmation: last N candles show selling pressure
        n = HH_HL_PB_BOUNCE_LOOKBACK
        if len(candles_5m) < n + 1:
            return None
        bounce_candles = candles_5m[-(n + 1):-1]
        if not bounce_candles:
            return None
        has_bounce = False
        for bc in bounce_candles:
            body = bc['open'] - bc['close']  # bearish = open > close
            rng = bc['high'] - bc['low']
            if rng > 0 and body / rng >= HH_HL_PB_BOUNCE_BODY_PCT:
                has_bounce = True
                break
        if not has_bounce:
            return None

        pullback_pct = pullback_depth * 100.0
        return {
            'swing_level': last_lh_price,
            'pullback_pct': round(pullback_pct, 4),
            'pullback_depth': round(pullback_depth, 4),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Detection: 7 Confluence Gates + Dual Entry Mode
# ═══════════════════════════════════════════════════════════════════════════════

def detect(token: str, candles_5m: list = None, candles_1h: list = None) -> Optional[dict]:
    """Detect HH/HL structure with breakout or pullback entry.

    Tries breakout mode first (price above HH / below LL).
    If breakout doesn't qualify, tries pullback mode (dip to HL / rally to LH).

    Returns {direction, confidence, value, price, source, entry_mode, ...} or None.
    """
    if not HH_HL_ENABLED:
        return None

    # ── Fetch data if not provided ─────────────────────────────────────────────
    if candles_5m is None:
        candles_5m = _get_candles_5m(token, limit=HH_HL_LOOKBACK)
    if not candles_5m or len(candles_5m) < HH_HL_MIN_CANDLES_5M:
        return None

    if candles_1h is None:
        candles_1h = _get_candles_1h(token, limit=60)

    price = candles_5m[-1]['close']
    closes_5m = [c['close'] for c in candles_5m]

    # ════════════════════════════════════════════════════════════════════════════
    # GATE 1: Structure Clarity
    # ════════════════════════════════════════════════════════════════════════════
    swing_highs, swing_lows = _find_swings(candles_5m)
    if not swing_highs or not swing_lows:
        return None

    all_swings = sorted(swing_highs + swing_lows, key=lambda x: x[0])
    structure, num_swings = _classify_structure(all_swings)
    if structure == 'NEUTRAL':
        return None

    direction = 'LONG' if structure == 'HH_HL' else 'SHORT'

    last_sh = swing_highs[-1]
    last_sl = swing_lows[-1]
    last_swing_idx = max(last_sh[0], last_sl[0])
    bars_since = len(candles_5m) - 1 - last_swing_idx

    # ── GATE 7: Freshness ──────────────────────────────────────────────────────
    if bars_since > HH_HL_MAX_BARS_SINCE:
        return None

    atr_val = _volume_atr(candles_5m) or (price * HH_HL_BACKUP_ATR_PCT)

    # ════════════════════════════════════════════════════════════════════════════
    # ENTRY MODE SELECTION: Breakout vs Pullback
    # ════════════════════════════════════════════════════════════════════════════
    entry_mode = None
    swing_level = None
    breakout_pct = 0.0

    # ── Try Breakout Mode first ────────────────────────────────────────────────
    if direction == 'LONG':
        bp = (price - last_sh[1]) / last_sh[1]
        if bp >= HH_HL_BREAKOUT_THRESHOLD:
            if bp <= (atr_val / price * HH_HL_MAX_EXTENSION_ATR):
                entry_mode = 'breakout'
                swing_level = last_sh[1]
                breakout_pct = bp
    else:
        bp = (last_sl[1] - price) / last_sl[1]
        if bp >= HH_HL_BREAKOUT_THRESHOLD:
            if bp <= (atr_val / price * HH_HL_MAX_EXTENSION_ATR):
                entry_mode = 'breakout'
                swing_level = last_sl[1]
                breakout_pct = bp

    # ── Try Pullback Mode if breakout didn't qualify ───────────────────────────
    if entry_mode is None and HH_HL_PB_ENABLED:
        pb = _detect_pullback(
            direction, candles_5m, swing_highs, swing_lows, all_swings,
            price, atr_val, closes_5m
        )
        if pb:
            entry_mode = 'pullback'
            swing_level = pb['swing_level']
            breakout_pct = pb['pullback_pct']

    if entry_mode is None:
        return None

    # ════════════════════════════════════════════════════════════════════════════
    # GATE 2: Higher Timeframe Trend (1H)
    # ════════════════════════════════════════════════════════════════════════════
    htf_aligned = False
    htf_spread = 0.0
    if candles_1h and len(candles_1h) >= HH_HL_HTF_EMA_SLOW:
        closes_1h = [c['close'] for c in candles_1h]
        ema_fast_1h = _ema(closes_1h, HH_HL_HTF_EMA_FAST)
        ema_slow_1h = _ema(closes_1h, HH_HL_HTF_EMA_SLOW)
        if ema_fast_1h is not None and ema_slow_1h is not None and ema_slow_1h > 0:
            htf_spread = (ema_fast_1h - ema_slow_1h) / ema_slow_1h * 100.0
            if direction == 'LONG' and ema_fast_1h > ema_slow_1h:
                htf_aligned = True
            elif direction == 'SHORT' and ema_fast_1h < ema_slow_1h:
                htf_aligned = True
            if not htf_aligned:
                if abs(htf_spread) > HH_HL_HTF_STRONG_SPREAD:
                    return None

    # ════════════════════════════════════════════════════════════════════════════
    # GATE 3: Volume Confirmation
    # ════════════════════════════════════════════════════════════════════════════
    volumes = [c['volume'] for c in candles_5m]
    vol_ok = False
    vol_ratio = 0.0
    if len(volumes) >= HH_HL_VOL_LOOKBACK:
        avg_vol = sum(volumes[-HH_HL_VOL_LOOKBACK:]) / HH_HL_VOL_LOOKBACK
        if avg_vol > 0:
            vol_ratio = volumes[-1] / avg_vol
            if vol_ratio >= HH_HL_AVG_VOL_MULT:
                vol_ok = True
    if not vol_ok:
        return None

    # ════════════════════════════════════════════════════════════════════════════
    # GATE 4: Momentum (RSI) — mode-aware thresholds
    # ════════════════════════════════════════════════════════════════════════════
    rsi_val = _rsi(closes_5m, HH_HL_RSI_PERIOD)
    # Compute 1m RSI for metadata (execution filter drift detection)
    from signals.rsi_1m import compute_rsi_1m
    rsi_1m = compute_rsi_1m(token)
    if rsi_val is None:
        return None
    if entry_mode == 'pullback':
        if direction == 'LONG' and (rsi_val < HH_HL_PB_RSI_LONG_MIN or rsi_val > HH_HL_PB_RSI_LONG_MAX):
            return None
        if direction == 'SHORT' and (rsi_val < HH_HL_PB_RSI_SHORT_MIN or rsi_val > HH_HL_PB_RSI_SHORT_MAX):
            return None
    else:
        if direction == 'LONG' and (rsi_val < HH_HL_RSI_LONG_MIN or rsi_val > HH_HL_RSI_LONG_MAX):
            return None
        if direction == 'SHORT' and (rsi_val < HH_HL_RSI_SHORT_MIN or rsi_val > HH_HL_RSI_SHORT_MAX):
            return None

    # ════════════════════════════════════════════════════════════════════════════
    # GATE 5: EMA Alignment (5m) — relaxed for pullback mode
    # ════════════════════════════════════════════════════════════════════════════
    if len(closes_5m) < HH_HL_EMA_SLOW:
        return None
    ema_fast_5m = _ema(closes_5m, HH_HL_EMA_FAST)
    ema_slow_5m = _ema(closes_5m, HH_HL_EMA_SLOW)
    if ema_fast_5m is None or ema_slow_5m is None:
        return None
    if entry_mode == 'pullback' and HH_HL_PB_EMA_RELAXED:
        # Pullback mode: only require slow EMA direction (price can dip below fast EMA)
        if direction == 'LONG' and ema_slow_5m > ema_fast_5m:
            return None  # slow EMA above fast = downtrend, pullback invalid
        if direction == 'SHORT' and ema_slow_5m < ema_fast_5m:
            return None
    else:
        # Breakout mode: strict EMA alignment
        if direction == 'LONG':
            if price < ema_fast_5m:
                return None
            if ema_fast_5m < ema_slow_5m:
                return None
        else:
            if price > ema_fast_5m:
                return None
            if ema_fast_5m > ema_slow_5m:
                return None

    # ════════════════════════════════════════════════════════════════════════════
    # GATE 6: Volatility
    # ════════════════════════════════════════════════════════════════════════════
    atr_val = _volume_atr(candles_5m)
    if atr_val is None or price <= 0:
        return None
    atr_pct = atr_val / price * 100.0
    if atr_pct < HH_HL_VOL_FLOOR_PCT or atr_pct > HH_HL_VOL_CAP_PCT:
        return None

    # ════════════════════════════════════════════════════════════════════════════
    # CONFIDENCE SCORING
    # ════════════════════════════════════════════════════════════════════════════
    conf = HH_HL_CONF_BASE

    # Bonus: deep structure
    if num_swings >= HH_HL_STRUCT_MIN_SWINGS:
        conf += HH_HL_CONF_STRUCT_BONUS

    # Bonus: strong volume
    if vol_ratio >= HH_HL_VOL_STRONG_MULT:
        conf += HH_HL_CONF_VOLUME_BONUS

    # Bonus: 1H trend strongly aligned
    if htf_aligned and abs(htf_spread) > HH_HL_HTF_BONUS_SPREAD:
        conf += HH_HL_CONF_HTF_BONUS

    # Bonus: RSI in sweet spot
    if direction == 'LONG' and HH_HL_RSI_SWEET_LONG_LOW <= rsi_val <= HH_HL_RSI_SWEET_LONG_HIGH:
        conf += HH_HL_CONF_MOMENTUM_BONUS
    elif direction == 'SHORT' and HH_HL_RSI_SWEET_SHORT_LOW <= rsi_val <= HH_HL_RSI_SWEET_SHORT_HIGH:
        conf += HH_HL_CONF_MOMENTUM_BONUS

    # Bonus: pullback entry (better R:R than chasing breakouts)
    if entry_mode == 'pullback':
        conf += HH_HL_PB_CONF_BONUS

    conf = min(conf, HH_HL_CONF_CAP)
    if conf < HH_HL_CONF_FLOOR:
        return None

    source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

    return {
        'direction':    direction,
        'confidence':   conf,
        'value':        float(conf),
        'price':        price,
        'source':       source,
        'entry_mode':   entry_mode,
        'structure':    structure,
        'num_swings':   num_swings,
        'bars_since':   bars_since,
        'swing_level':  swing_level,
        'breakout_pct': round(breakout_pct * 100, 4),
        'rsi':          round(rsi_val, 1),
        'vol_ratio':    round(vol_ratio, 2),
        'atr_pct':      round(atr_pct, 3),
        'htf_aligned':  htf_aligned,
        'htf_spread':   round(htf_spread, 3),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner: iterate all tokens
# ═══════════════════════════════════════════════════════════════════════════════

def scan_signals() -> int:
    """Scan all tokens for HH/HL structure signals. Returns count of signals emitted."""
    from signal_schema import get_all_latest_prices

    added = 0
    prices = get_all_latest_prices()

    for token, data in prices.items():
        if token.startswith('@'):
            continue

        if price_age_minutes(token) > 10:
            continue

        sig = detect(token)
        if not sig:
            continue

        direction = sig['direction']

        if direction == 'LONG' and not HH_HL_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not HH_HL_MINUS_ENABLED:
            continue

        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        if get_cooldown(token, direction=direction):
            continue

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        sid = add_signal(
            token=token.upper(),
            direction=direction,
            signal_type=sig_type,
            source=source,
            confidence=sig['confidence'],
            value=sig['value'],
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='5m',
            z_score=None,
        )
        if sid:
            added += 1
            set_cooldown(token, direction, hours=HH_HL_COOLDOWN_HOURS)
            mode_tag = 'PB' if sig['entry_mode'] == 'pullback' else 'BRK'
            print(f'  HH-HL v2 [{mode_tag}] {direction:5s} {token:8s} '
                  f'conf={sig["confidence"]:.0f}% '
                  f'struct={sig["structure"]} '
                  f'swings={sig["num_swings"]} '
                  f'pct={sig["breakout_pct"]:.3f}% '
                  f'bars={sig["bars_since"]} '
                  f'rsi={sig["rsi"]:.0f} '
                  f'vol={sig["vol_ratio"]:.1f}x '
                  f'htf={"✓" if sig["htf_aligned"] else "—"} '
                  f'[{source}]')

    return added


def run():
    """Entry point for signals_runner. No prices_dict — reads from DB directly."""
    return scan_signals()


# ═══════════════════════════════════════════════════════════════════════════════
# CLI test
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from signal_schema import get_all_latest_prices

    prices = get_all_latest_prices()
    test_tokens = {k: v for k, v in prices.items()
                   if k in ('BTC', 'ETH', 'SOL', 'AVAX', 'LINK', 'ARB', 'OP',
                            'NEAR', 'APT', 'INJ', 'DOGE', 'PEPE', 'WIF') and v.get('price')}
    if not test_tokens:
        test_tokens = dict(list(prices.items())[:15])

    print(f"[hh_hl v2] Testing on {len(test_tokens)} tokens (breakout + pullback)...")
    for token in test_tokens:
        sig = detect(token)
        if sig:
            mode = 'PB' if sig['entry_mode'] == 'pullback' else 'BRK'
            print(f"  {token}: [{mode}] {sig['direction']} conf={sig['confidence']:.0f}% "
                  f"struct={sig['structure']} swings={sig['num_swings']} "
                  f"pct={sig['breakout_pct']:.3f}% bars={sig['bars_since']} "
                  f"rsi={sig['rsi']:.0f} vol={sig['vol_ratio']:.1f}x "
                  f"htf={'✓' if sig['htf_aligned'] else '—'}")
        else:
            print(f"  {token}: no signal")
    print("[hh_hl v2] Done.")
