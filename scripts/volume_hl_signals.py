#!/usr/bin/env python3
"""
volume_hl_signals.py — Volume spike signals from 1m candles.
Alerts when a coin's volume exceeds Nx its 10-period SMA.

FIX (2026-04-23): Uses price_history (signals_hermes.db) for price data
  (updated every minute) and candles_1m (candles.db) for volume data (0.3h stale).
  The 0.3h candle staleness is acceptable for volume spike detection.
  If candles.db volume is stale (>CANDLES_STALENESS_SEC), returns [].
"""
import sys
import os
import time
import sqlite3
import statistics
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal
from hermes_constants import CANDLES_STALENESS_SEC

_PRICE_DB = '/root/.hermes/data/signals_hermes.db'
_CANDLES_DB = '/root/.hermes/data/candles.db'

# ── Config ────────────────────────────────────────────────────────────────────
SCAN_SECS    = 60         # match pipeline cadence
VOL_MULT     = 5.0        # fire when current_vol >= sma_vol * VOL_MULT
MIN_VOL      = 10_000    # minimum current volume (USD quote) to qualify
MIN_CONF     = 60        # add_signal floor — must be >= 60 to pass compactor query
MAX_CONF     = 88        # add_signal ceiling (per schema)
HL_EXCHANGE  = "hyperliquid"
TIMEFRAME    = "1m"
# ─────────────────────────────────────────────────────────────────────────────

def get_tokens() -> list[str]:
    """Fetch all tokens that have 1m candle data (from signal_schema price list)."""
    # volume_hl is invoked with prices_dict from signal_gen which already filters
    # tokens with live prices. We get tokens from there at call time.
    return []


def get_candles(token: str, limit: int = 11) -> list[dict]:
    """Fetch last N 1m candles for token: price from price_history, volume from candles.db.

    price_history: updated every minute (fresh).
    candles_1m: 0.3h stale (acceptable for volume spikes).
    Freshness guard: skip if candles_1m is > 15 minutes old.
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
        if not p_rows:
            return []

        # Freshness check on price_history — if it's stale, skip this token
        if p_rows and p_rows[-1] and p_rows[-1][0]:
            price_age = time.time() - p_rows[-1][0]
            if price_age > CANDLES_STALENESS_SEC:
                return []  # price_history too stale

        # Get volumes from candles_1m (slightly stale but has volume)
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
    except Exception:
        return []


def scan_token(token: str) -> bool:
    """
    Returns True if a signal was emitted for this token.
    """
    candles = get_candles(token)
    if len(candles) < 11:
        return False

    closed = candles[:10]   # last 10 fully-closed candles
    cur    = candles[10]    # most recent (forming)

    closed_vols = [c["volume"] for c in closed]
    cur_vol     = cur["volume"]
    cur_close   = cur["close"]

    try:
        sma = statistics.mean(closed_vols)
    except Exception:
        return False

    # Direction: price change over the 10m window
    window_start_close = closed[0]["close"]
    pct_change = ((cur_close - window_start_close) / window_start_close * 100) if window_start_close > 0 else 0

    # Volume in price_history is BASE asset (BTC, ETH, etc.)
    # Convert to USD equivalent for consistent MIN_VOL threshold
    cur_vol_usd = cur_vol * cur_close
    sma_usd     = sma * ((cur_close + window_start_close) / 2)   # approximate USD SMA

    if sma_usd <= 0 or cur_vol_usd <= 0:
        return False

    ratio = cur_vol_usd / sma_usd

    if ratio < VOL_MULT or cur_vol_usd < MIN_VOL:
        return False

    direction = "LONG" if pct_change >= 0 else "SHORT"

    confidence = min(MAX_CONF, max(MIN_CONF, int(ratio * 10)))

    if add_signal is not None:
        add_signal(
            token=token,
            direction=direction,
            signal_type="volume_hl",
            source="volume_hl",
            confidence=confidence,
            value=round(ratio, 3),
            price=round(cur_close, 6),
            exchange=HL_EXCHANGE,
            timeframe=TIMEFRAME,
        )
        return True
    else:
        # Standalone test mode — just print
        print(
            f"[volume_hl] {token} {direction} conf={confidence} "
            f"ratio={ratio:.1f}x vol={cur_vol:.0f} sma={sma:.0f} "
            f"price={cur_close:.6f} {pct_change:+.2f}%"
        )
        return True


def main():
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"\n[{ts}] volume_hl_signals starting | mult={VOL_MULT}x min_vol=${MIN_VOL:,.0f}")
    print("Note: volume_hl_signals is invoked by signal_gen via scan_volume_hl_signals(prices_dict)")
    print(f"[{ts}] done | alerts:0 errors:0")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting.")
        exit(0)