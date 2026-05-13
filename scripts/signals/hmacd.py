#!/usr/bin/env python3
"""
hmacd.py — HMACD BARE: Pure MACD Histogram Alignment Signal.

Fires when MACD histogram agrees across 15m + 1H timeframes:
  hmacd+ = LONG  (macd_line > signal_line → bullish histogram agreement)
  hmacd- = SHORT (macd_line < signal_line → bearish histogram agreement)

signal_type: hmacd_bare (distinguished from hmacd_mtf which adds z-score filter)

Architecture:
  - Reads from local price_history (signals_hermes.db) — zero HL API calls
  - Aggregates raw 90-sec candles into 15m / 1H candles
  - Computes per-token tuned MACD via get_macd_params()
  - Fires hmacd_bare+ / hmacd_bare- source tags via signal_schema.add_signal()
"""

import sys, os, sqlite3, json, time
from typing import Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import (
    add_signal, get_all_latest_prices, get_price_history,
    price_age_minutes, init_db,
)
from hermes_constants import (
    HMACD_ENABLED, HMACD_PLUS_ENABLED, HMACD_MINUS_ENABLED,
)
from macd_rules import get_macd_params
from position_manager import get_open_positions as _get_open_pos

# ── Constants ─────────────────────────────────────────────────────────────────

Z_MACD_THRESH = 2.0   # z-score threshold for MTF MACD entry
MIN_TRADE_INTERVAL_MINUTES = 15

# ── MACD Crossover (internal) ─────────────────────────────────────────────────

def _macd_crossover(token: str, minutes: int):
    """
    Compute MACD histogram for a token at given timeframe.

    Aggregates raw 90-sec candles into target timeframe candles,
    computes MACD using per-token tuned params from get_macd_params(),
    returns (histogram, macd_line, signal_line) or None.

    Logic:
      macd_line > signal_line  → histogram > 0 → bullish
      macd_line < signal_line  → histogram < 0 → bearish
    """
    tf_minutes = minutes
    lookback_raw = tf_minutes * 40
    rows = get_price_history(token, lookback_minutes=lookback_raw)
    if not rows or len(rows) < 40:
        return None

    # Aggregate raw 90-sec candles into TF candles (OHLC)
    tf_sec = tf_minutes * 60
    buckets = {}
    for ts, close in rows:
        bucket_ts = (ts // tf_sec) * tf_sec
        if bucket_ts not in buckets:
            buckets[bucket_ts] = [close, close, close, close]  # open, high, low, close
        else:
            buckets[bucket_ts][1] = max(buckets[bucket_ts][1], close)   # high
            buckets[bucket_ts][2] = min(buckets[bucket_ts][2], close)   # low
            buckets[bucket_ts][3] = close                                # close

    sorted_ts = sorted(buckets.keys())
    if len(sorted_ts) < 4:
        return None

    closes_all = [buckets[ts][3] for ts in sorted_ts]

    # Per-token tuned MACD params
    params = get_macd_params(token)
    fast, slow, sig = params['fast'], params['slow'], params['signal']
    n_bars = len(closes_all)
    if n_bars < slow + sig:
        return None

    def _ema(data, period):
        if len(data) < period:
            return None
        k = 2 / (period + 1)
        ema_val = sum(data[:period]) / period
        for price in data[period:]:
            ema_val = price * k + ema_val * (1 - k)
        return ema_val

    def _macd_from_closes(closes_list):
        if len(closes_list) < slow + sig:
            return None, None, None
        ef = _ema(closes_list, fast)
        es = _ema(closes_list, slow)
        if ef is None or es is None:
            return None, None, None
        macd_line = ef - es
        macd_vals = []
        for i in range(slow, len(closes_list)):
            efa = _ema(closes_list[:i+1], fast)
            esa = _ema(closes_list[:i+1], slow)
            if efa and esa:
                macd_vals.append(efa - esa)
        if len(macd_vals) < sig:
            return None, None, None
        sig_val = _ema(macd_vals, sig)
        if sig_val is None:
            return None, None, None
        return round(macd_line, 6), round(sig_val, 6), round(macd_line - sig_val, 6)

    macd_line, sig_line, hist = _macd_from_closes(closes_all)
    return hist, macd_line, sig_line


# ── Main Signal Runner ─────────────────────────────────────────────────────────

def run() -> int:
    """
    HMACD signal scanner.

    Fetches prices internally, iterates tokens, fires hmacd+ / hmacd- signals
    based on 15m + 1H MACD histogram agreement.

    Returns:
        Number of signals added.
    """
    # NOTE: HMACD_ENABLED guard is in signal_gen.py (inline version).
    # Per-direction HMACD_PLUS/MINUS_ENABLED checks remain active.
    # This registry version is called by signals_runner.py — Layer 2 add_signal()
    # guard handles final per-source filtering.

    init_db()
    prices_dict = get_all_latest_prices()
    open_pos = {p['token']: p['direction'] for p in _get_open_pos()}

    added = 0

    for token, data in prices_dict.items():
        # ── Skip conditions (same as signal_gen.py token loop) ──────────────────
        if token.startswith('@'):
            continue
        if price_age_minutes(token) > 10:
            continue
        if not data.get('price') or data['price'] <= 0:
            continue
        if token.upper() in open_pos:
            continue
        if _recent_trade_exists(token):
            continue
        if token.upper() in SHORT_BLACKLIST:
            continue
        if is_delisted(token.upper()):
            continue

        price = data['price']
        if not is_reasonable_price(token, price):
            continue

        # ── MACD across 15m + 1H ─────────────────────────────────────────────
        xo_15m = _macd_crossover(token, 15)
        xo_1h  = _macd_crossover(token, 60)

        h_15m = xo_15m[0] if xo_15m else None
        h_1h  = xo_1h[0]  if xo_1h  else None

        if h_15m is None or h_1h is None:
            continue

        # ── Direction: histogram agreement across timeframes ─────────────────
        if h_15m > 0 and h_1h > 0:
            direction = 'LONG'
        elif h_15m < 0 and h_1h < 0:
            direction = 'SHORT'
        else:
            continue  # no agreement across TFs

        # ── Directional gate ─────────────────────────────────────────────────
        if direction == 'LONG' and not HMACD_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not HMACD_MINUS_ENABLED:
            continue

        # ── BLACKLIST guard for SHORT ────────────────────────────────────────
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        # ── Compute confidence from histogram strength ──────────────────────
        avg_hist = (abs(h_15m) + abs(h_1h)) / 2
        confidence = min(80.0, 50 + avg_hist * 50)

        # ── Source tag ───────────────────────────────────────────────────────
        hmacd_char = '+' if direction == 'LONG' else '-'
        source = f'hmacd_bare-{hmacd_char}'   # hmacd_bare+ / hmacd_bare- (distinct from hmacd_mtf)

        sid = add_signal(
            token=token,
            direction=direction,
            signal_type='hmacd_bare',   # bare = pure histogram agreement (no z-score filter)
            source=source,   # hmacd_bare+/hmacd_bare- (set on line 194)
            confidence=confidence,
            value=round(avg_hist, 6),
            price=float(price),
            exchange='hyperliquid',
            timeframe='15m_1h',
            macd_hist=avg_hist,
        )
        if sid:
            added += 1

    return added


# ── Guard helpers (mirrored from signal_gen.py) ────────────────────────────────

def _recent_trade_exists(token: str, minutes: int = MIN_TRADE_INTERVAL_MINUTES) -> bool:
    """Return True if token was traded in last N minutes."""
    TRADE_LOG_FILE = '/var/www/hermes/data/recent_trades.json'
    try:
        if not os.path.exists(TRADE_LOG_FILE):
            return False
        with open(TRADE_LOG_FILE) as f:
            data = json.load(f)
        cutoff = time.time() - minutes * 60
        entries = data.get(token.upper(), [])
        for entry in entries:
            if isinstance(entry, dict):
                ts = entry.get('timestamp', 0)
            else:
                ts = entry
            if ts > cutoff:
                return True
    except Exception:
        pass
    return False


def is_delisted(token: str) -> bool:
    """Return True if token is on the delistment blacklist."""
    from hyperliquid_exchange import is_delisted as _is_delisted
    return _is_delisted(token)


def is_reasonable_price(token: str, price: float) -> bool:
    """Reject junk prices (too low or zero)."""
    if price is None or price <= 0:
        return False
    if price < 0.0001:
        return False
    return True


# ── Module-level BLACKLIST (from signal_gen.py) ────────────────────────────────

SHORT_BLACKLIST = {
    'MEME', 'PEPE', 'SHIB', 'DOGE', 'FLOKI', 'BONK',
    'WIF', 'TRUMP', 'MAGA', 'AI16Z', 'ZEREBRO', 'CHILLGUY',
    'FNW', 'SLERF', 'BOME', 'SLERF', '朕',
}
