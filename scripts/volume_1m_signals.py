"""
volume_1m_signals.py — Volume spike signals on 1m candles.
Fires when a coin's volume exceeds Nx its 10-period SMA.
Emits signals via add_signal() so they go through the standard pipeline
and can combine with other signal types for confluence.

FIX (2026-04-26): Merges price (price_history) and volume (candles_1m) by
  timestamp key instead of by list index. Also uses CANDLES_STALENESS_SEC
  from hermes_constants for staleness threshold.
"""
import statistics
import sys
import os
import time
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal
from hermes_constants import CANDLES_STALENESS_SEC

_PRICE_DB = '/root/.hermes/data/signals_hermes.db'
_CANDLES_DB = '/root/.hermes/data/candles.db'

VOL_MULT   = 5.0
MIN_VOL    = 10_000      # USD
MAX_CONF   = 88
MIN_CONF   = 60


def get_candles(token: str, limit: int = 11) -> list[dict]:
    """Fetch last N 1m candles: price from price_history (fresh), volume from candles_1m.

    price_history: updated every minute (fresh).
    candles_1m: ~0.3h stale (acceptable for volume spike detection).
    Freshness guard: skip if candles_1m > 15 minutes old.
    Returns oldest-first list of {close, volume} dicts.
    """
    try:
        # Get prices from price_history (live)
        p_conn = sqlite3.connect(_PRICE_DB, timeout=10)
        p_c = p_conn.cursor()
        p_c.execute("""
            SELECT timestamp, price FROM (
                SELECT timestamp, price
                FROM price_history
                WHERE token = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ) sub
            ORDER BY timestamp ASC
        """, (token.upper(), limit))
        p_rows = p_c.fetchall()
        p_conn.close()
        if not p_rows or len(p_rows) < limit:
            return []

        most_recent_ts = p_rows[-1][0]
        if (time.time() - most_recent_ts) > CANDLES_STALENESS_SEC:
            return []

        # Get volumes from candles_1m (slightly stale but has volume data)
        c_conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c_c = c_conn.cursor()
        c_c.execute("SELECT MAX(ts) FROM candles_1m WHERE token = ?", (token.upper(),))
        freshness = c_c.fetchone()
        if freshness and freshness[0] and (time.time() - freshness[0]) > CANDLES_STALENESS_SEC:
            c_conn.close()
            return []  # candles too stale
        c_c.execute("""
            SELECT close, volume
            FROM candles_1m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), limit))
        c_rows = c_c.fetchall()
        c_conn.close()
        if len(c_rows) < limit:
            return []

        # Reverse to oldest-first
        c_rows = list(reversed(c_rows))

        # Merge: price from price_history, volume from candles_1m
        # BUG-FIX (2026-04-26): merge by timestamp key, not by list index.
        # p_rows and c_rows come from independent queries with independent LIMITs —
        # they may not have the same timestamp sets or length. Using index alignment
        # produced misaligned price/volume pairs. Now use a dict lookup by ts.
        c_by_ts = {r[0]: r[1] for r in c_rows}  # {ts -> volume}
        result = []
        for ts, price in p_rows:
            vol = c_by_ts.get(ts, 0.0)
            result.append({'close': price, 'volume': vol, 'ts': ts})
        return result
    except Exception as e:
        print(f"volume_1m get_candles EXCEPTION: {e}")
        return []


def scan_volume_1m_signals(prices_dict: dict) -> int:
    """
    Scan tokens in prices_dict for volume spikes on 1m candles.
    Returns: number of signals emitted.
    """
    added = 0
    for token, data in prices_dict.items():
        price = data.get('price')
        if not price or price <= 0:
            continue

        candles = get_candles(token, limit=11)
        if len(candles) < 11:
            continue

        closed = candles[:10]
        cur    = candles[10]

        # BUG-FIX (2026-04-26): Compute USD volume per bar BEFORE averaging.
        # Old code: sma = mean(volume) * mean(price) — approximation that introduces
        # systematic error when price and volume are correlated (which they usually are).
        # New code: mean of [volume[i] * close[i]] — the true USD volume average.
        closed_usd_vols = [closed[i]["volume"] * closed[i]["close"] for i in range(10)]
        cur_vol         = cur["volume"]
        cur_close       = cur["close"]

        try:
            sma_usd = statistics.mean(closed_usd_vols)
        except Exception:
            continue

        if sma_usd <= 0 or cur_vol <= 0:
            continue

        # Convert current bar volume to USD
        cur_vol_usd = cur_vol * cur_close

        if sma_usd <= 0 or cur_vol_usd <= 0:
            continue

        ratio = cur_vol_usd / sma_usd

        if ratio < VOL_MULT or cur_vol_usd < MIN_VOL:
            continue

        # wsc = oldest close in the 10-bar window — reference price for direction
        wsc = closed[0]["close"]

        # Direction from price change over the 10m window
        pct_change = ((cur_close - wsc) / wsc * 100) if wsc > 0 else 0
        direction  = "LONG" if pct_change >= 0 else "SHORT"
        source_tag = f"volume-1m-{direction.lower()}"
        confidence = min(MAX_CONF, max(MIN_CONF, int(ratio * 10)))

        sig = add_signal(
            token=token,
            direction=direction,
            signal_type="volume_1m",
            source=source_tag,
            confidence=confidence,
            value=round(ratio, 3),
            price=round(cur_close, 6),
            exchange="hyperliquid",
            timeframe="1m",
        )
        if sig:
            added += 1

    return added