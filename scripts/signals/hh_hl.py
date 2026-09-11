#!/usr/bin/env python3
"""hh_hl.py — Structure Sniper: multi-confluence market structure signal (v2).

Detects HH/HL (uptrend) and LH/LL (downtrend) structure on 5m OHLCV candles
and fires breakout signals when price breaks above the last swing high (LONG)
or below the last swing low (SHORT), with 7+ confluence gates.

Architecture: signal → add_signal() → compactor → hotset → guardian

Confluence gates (ALL must pass):
  1. Structure clarity — clear 4+ swing pattern on 5m
  2. Higher TF trend — 1H EMA20 vs EMA50 alignment
  3. Volume confirmation — breakout candle > 1.5x 20-period average
  4. Momentum — RSI in favorable zone
  5. EMA alignment — price vs 5m EMA20 + EMA20 vs EMA50
  6. Volatility — ATR% between 0.3% and 1.5%
  7. Freshness — breakout within last 5 bars on 5m

Data sources:
  Primary: candles_5m (OHLCV, proper H/L for swing detection)
  Higher TF: candles_1h (EMA20/50 trend confirmation)
  Fallback: price_history (close-only, lower quality — skip if possible)

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
    Returns [] if stale (>10 min old) or empty."""
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
        # Staleness: 5m candles update every 5 min — 10 min = 2 candles stale
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
    Returns [] if stale (>30 min old) or empty."""
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


def _ema_spread(closes: list, fast_period: int, slow_period: int) -> Optional[float]:
    """Return (ema_fast - ema_slow) / ema_slow as percentage. None if insufficient data."""
    if len(closes) < slow_period:
        return None
    ema_f = _ema(closes, fast_period)
    ema_s = _ema(closes, slow_period)
    if ema_s is None or ema_s == 0 or ema_f is None:
        return None
    return (ema_f - ema_s) / ema_s * 100.0


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


def _atr(closes: list, period: int = 14) -> Optional[float]:
    """ATR from close-only data using rolling range (max - min) over period windows."""
    if len(closes) < period + 1:
        return None
    ranges = []
    for i in range(period, len(closes)):
        window = closes[i - period:i + 1]
        ranges.append(max(window) - min(window))
    if not ranges:
        return None
    return sum(ranges[-period:]) / period


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
        # Check swing high: candle[i].high must be highest in window
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

        # Check swing low: candle[i].low must be lowest in window
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

    Requires minimum HH_HL_MIN_SWINGS (4) alternating H/L points.
    Checks H-L-H-L pattern: if highs rising + lows rising = HH/HL (uptrend).
    Checks L-H-L-H pattern: if lows rising + highs rising = HH/HL (uptrend).
    Vice versa for LH/LL (downtrend).

    Returns:
        (structure, num_swings) — 'HH_HL' | 'LH_LL' | 'NEUTRAL', swing count
    """
    if len(swings) < HH_HL_MIN_SWINGS:
        return 'NEUTRAL', 0

    # Build alternating swing sequence from the last swings
    # Take the most recent swings and check for HH/HL or LH/LL patterns
    recent = swings[-HH_HL_STRUCT_MIN_SWINGS:] if len(swings) >= HH_HL_STRUCT_MIN_SWINGS else swings

    # Separate highs and lows from the recent set
    h_swings = [(i, p) for i, p, t in recent if t == 'H']
    l_swings = [(i, p) for i, p, t in recent if t == 'L']

    if len(h_swings) < 2 or len(l_swings) < 2:
        return 'NEUTRAL', len(swings)

    # Check for HH/HL (uptrend): each high higher than previous, each low higher than previous
    hh_count = 0
    hl_count = 0
    for j in range(1, len(h_swings)):
        if h_swings[j][1] > h_swings[j - 1][1]:
            hh_count += 1
    for j in range(1, len(l_swings)):
        if l_swings[j][1] > l_swings[j - 1][1]:
            hl_count += 1

    lh_count = 0
    ll_count = 0
    for j in range(1, len(h_swings)):
        if h_swings[j][1] < h_swings[j - 1][1]:
            lh_count += 1
    for j in range(1, len(l_swings)):
        if l_swings[j][1] < l_swings[j - 1][1]:
            ll_count += 1

    # HH/HL requires at least 1 higher high AND 1 higher low
    if hh_count >= 1 and hl_count >= 1:
        return 'HH_HL', len(swings)
    # LH/LL requires at least 1 lower high AND 1 lower low
    if lh_count >= 1 and ll_count >= 1:
        return 'LH_LL', len(swings)

    return 'NEUTRAL', len(swings)


# ═══════════════════════════════════════════════════════════════════════════════
# Detection: 7 Confluence Gates
# ═══════════════════════════════════════════════════════════════════════════════

def detect(token: str, candles_5m: list = None, candles_1h: list = None) -> Optional[dict]:
    """Detect HH/HL structure breakout with 7 confluence gates.

    Returns {direction, confidence, value, price, source, ...} or None.
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
    # 1H data is optional — if missing, gate 2 is skipped (neutral)

    price = candles_5m[-1]['close']
    closes_5m = [c['close'] for c in candles_5m]

    # ════════════════════════════════════════════════════════════════════════════
    # GATE 1: Structure Clarity
    # ════════════════════════════════════════════════════════════════════════════
    swing_highs, swing_lows = _find_swings(candles_5m)
    if not swing_highs or not swing_lows:
        return None

    # Merge into chronological swing list
    all_swings = sorted(swing_highs + swing_lows, key=lambda x: x[0])
    structure, num_swings = _classify_structure(all_swings)
    if structure == 'NEUTRAL':
        return None

    direction = 'LONG' if structure == 'HH_HL' else 'SHORT'

    # ════════════════════════════════════════════════════════════════════════════
    # BREAKOUT DETECTION
    # ════════════════════════════════════════════════════════════════════════════
    # Get the most recent swing high and swing low
    last_sh = swing_highs[-1]  # (index, price, 'H')
    last_sl = swing_lows[-1]   # (index, price, 'L')
    last_swing_idx = max(last_sh[0], last_sl[0])
    bars_since = len(candles_5m) - 1 - last_swing_idx

    # ── GATE 7: Freshness ──────────────────────────────────────────────────────
    if bars_since > HH_HL_MAX_BARS_SINCE:
        return None

    # Breakout: price must exceed the relevant swing level by threshold
    if direction == 'LONG':
        # LONG breakout: price above last swing high
        swing_level = last_sh[1]
        breakout_pct = (price - swing_level) / swing_level
        if breakout_pct < HH_HL_BREAKOUT_THRESHOLD:
            return None
        # ── Late entry filter: price not already extended > 3x ATR above swing ──
        atr_val = _volume_atr(candles_5m) or (price * HH_HL_BACKUP_ATR_PCT)
        if breakout_pct > (atr_val / price * HH_HL_MAX_EXTENSION_ATR):
            return None  # price already extended = too late
    else:
        # SHORT breakout: price below last swing low
        swing_level = last_sl[1]
        breakout_pct = (swing_level - price) / swing_level
        if breakout_pct < HH_HL_BREAKOUT_THRESHOLD:
            return None
        # ── Late entry filter: price not already extended > 3x ATR below swing ──
        atr_val = _volume_atr(candles_5m) or (price * HH_HL_BACKUP_ATR_PCT)
        if breakout_pct > (atr_val / price * HH_HL_MAX_EXTENSION_ATR):
            return None  # price already extended = too late

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

            # If 1H trend STRONGLY disagrees, block the signal
            if not htf_aligned:
                # Strong disagreement: 1H EMA spread > threshold in wrong direction
                if abs(htf_spread) > HH_HL_HTF_STRONG_SPREAD:
                    return None
    # If no 1H data available, allow (neutral — don't block, don't bonus)

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
    # Volume is a strong filter — require it
    if not vol_ok:
        return None

    # ════════════════════════════════════════════════════════════════════════════
    # GATE 4: Momentum (RSI)
    # ════════════════════════════════════════════════════════════════════════════
    rsi_val = _rsi(closes_5m, HH_HL_RSI_PERIOD)
    if rsi_val is None:
        return None
    if direction == 'LONG' and (rsi_val < HH_HL_RSI_LONG_MIN or rsi_val > HH_HL_RSI_LONG_MAX):
        return None
    if direction == 'SHORT' and (rsi_val < HH_HL_RSI_SHORT_MIN or rsi_val > HH_HL_RSI_SHORT_MAX):
        return None

    # ════════════════════════════════════════════════════════════════════════════
    # GATE 5: EMA Alignment (5m)
    # ════════════════════════════════════════════════════════════════════════════
    if len(closes_5m) < HH_HL_EMA_SLOW:
        return None
    ema_fast_5m = _ema(closes_5m, HH_HL_EMA_FAST)
    ema_slow_5m = _ema(closes_5m, HH_HL_EMA_SLOW)
    if ema_fast_5m is None or ema_slow_5m is None:
        return None
    if direction == 'LONG':
        # Price must be above fast EMA, fast EMA above slow EMA
        if price < ema_fast_5m:
            return None
        if ema_fast_5m < ema_slow_5m:
            return None
    else:
        # Price must be below fast EMA, fast EMA below slow EMA
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

    # Bonus: deep structure (6+ swings = stronger pattern)
    if num_swings >= HH_HL_STRUCT_MIN_SWINGS:
        conf += HH_HL_CONF_STRUCT_BONUS

    # Bonus: strong volume (>2x average)
    if vol_ratio >= HH_HL_VOL_STRONG_MULT:
        conf += HH_HL_CONF_VOLUME_BONUS

    # Bonus: 1H trend strongly aligned
    if htf_aligned and abs(htf_spread) > HH_HL_HTF_BONUS_SPREAD:
        conf += HH_HL_CONF_HTF_BONUS

    # Bonus: RSI in sweet spot (momentum with the trade, not exhausted)
    if direction == 'LONG' and HH_HL_RSI_SWEET_LONG_LOW <= rsi_val <= HH_HL_RSI_SWEET_LONG_HIGH:
        conf += HH_HL_CONF_MOMENTUM_BONUS
    elif direction == 'SHORT' and HH_HL_RSI_SWEET_SHORT_LOW <= rsi_val <= HH_HL_RSI_SWEET_SHORT_HIGH:
        conf += HH_HL_CONF_MOMENTUM_BONUS

    conf = min(conf, HH_HL_CONF_CAP)
    if conf < HH_HL_CONF_FLOOR:
        return None

    source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

    return {
        'direction':   direction,
        'confidence':  conf,
        'value':       float(conf),
        'price':       price,
        'source':      source,
        'structure':   structure,
        'num_swings':  num_swings,
        'bars_since':  bars_since,
        'swing_level': swing_level,
        'breakout_pct': round(breakout_pct * 100, 4),
        'rsi':         round(rsi_val, 1),
        'vol_ratio':   round(vol_ratio, 2),
        'atr_pct':     round(atr_pct, 3),
        'htf_aligned': htf_aligned,
        'htf_spread':  round(htf_spread, 3),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner: iterate all tokens
# ═══════════════════════════════════════════════════════════════════════════════

def scan_signals() -> int:
    """Scan all tokens for HH/HL structure breakouts. Returns count of signals emitted."""
    from signal_schema import get_all_latest_prices

    added = 0
    prices = get_all_latest_prices()

    for token, data in prices.items():
        if token.startswith('@'):
            continue

        # Staleness
        if price_age_minutes(token) > 10:
            continue

        sig = detect(token)
        if not sig:
            continue

        direction = sig['direction']

        # Layer 1: per-direction kill-switch
        if direction == 'LONG' and not HH_HL_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not HH_HL_MINUS_ENABLED:
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
            print(f'  HH-HL v2 {direction:5s} {token:8s} '
                  f'conf={sig["confidence"]:.0f}% '
                  f'struct={sig["structure"]} '
                  f'swings={sig["num_swings"]} '
                  f'break={sig["breakout_pct"]:.3f}% '
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

    print(f"[hh_hl v2] Testing on {len(test_tokens)} tokens...")
    for token in test_tokens:
        sig = detect(token)
        if sig:
            print(f"  {token}: {sig['direction']} conf={sig['confidence']:.0f}% "
                  f"struct={sig['structure']} swings={sig['num_swings']} "
                  f"break={sig['breakout_pct']:.3f}% bars={sig['bars_since']} "
                  f"rsi={sig['rsi']:.0f} vol={sig['vol_ratio']:.1f}x "
                  f"htf={'✓' if sig['htf_aligned'] else '—'}")
        else:
            print(f"  {token}: no signal")
    print("[hh_hl v2] Done.")
