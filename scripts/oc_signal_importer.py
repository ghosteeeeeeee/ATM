#!/usr/bin/env python3
"""
oc_signal_importer.py — Import OpenClaw signals into Hermes signal pipeline.

Data sources (written by OpenClaw workspace, copied to Hermes data dir):
  /var/www/hermes/data/oc_indicators.json   (OC_INDICATORS_FILE)
  /var/www/hermes/data/oc_pending_signals.json (OC_PENDING_FILE)

Signal types imported:
  - oc_mtf_macd    : Multi-TF MACD (4H+1H+15m alignment)
  - oc_rsi         : Multi-TF RSI (4H+1H+15m, Wilder smoothing, oversold/overbought)
  - oc_pending     : Pre-approved pending signals from OC pipeline (price fixed to live for zscore)

Appends 'oc-' prefix to all source tags so signals are identifiable as OC-derived.
Does NOT modify OC code — reads OC JSON files and translates to Hermes add_signal() calls.

PRICE SOURCE FIX (2026-04-25):
  - MACD: computed locally from candles.db (15m/1h/4h OHLCV, fresh locally)
  - RSI:  computed locally from candles.db (15m/1h/4h, Wilder smoothing)
  - Price for both: pulled from signals_hermes.db latest_prices (fresh)
  - oc-zscore-v9: price overridden to live latest_prices (was stale OC entry price)
  - NO LONGER trusts stale oc_indicators.json price, MACD histogram, or RSI values
"""
from paths import OC_INDICATORS_FILE, OC_PENDING_FILE
from signal_schema import add_signal
import json, time, sqlite3, os

# ── Local price sources ───────────────────────────────────────────────────────
_SIGNALS_DB = '/root/.hermes/data/signals_hermes.db'
_CANDLES_DB = '/root/.hermes/data/candles.db'


def _get_fresh_price(token: str) -> float:
    """Fetch current price from signals_hermes.db latest_prices (updated every minute)."""
    try:
        conn = sqlite3.connect(_SIGNALS_DB, timeout=5)
        row = conn.execute(
            "SELECT price FROM latest_prices WHERE token = ?",
            (token.upper(),)
        ).fetchone()
        conn.close()
        return float(row[0]) if row else 0.0
    except Exception:
        return 0.0


def _fetch_candles(token: str, table: str, limit: int = 100) -> list:
    """Fetch close prices from candles.db table, oldest-first. Returns list of floats."""
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=5)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(f"""
            SELECT ts, close FROM (
                SELECT ts, close FROM {table}
                WHERE token = ?
                ORDER BY ts DESC
                LIMIT ?
            ) sub
            ORDER BY ts ASC
        """, (token.upper(), limit)).fetchall()
        conn.close()
        return [float(r['close']) for r in rows]
    except Exception:
        return []


def _ema(data: list, period: int) -> float:
    """Compute EMA of a price list. Returns last EMA value or None if insufficient data."""
    if len(data) < period:
        return None
    k = 2.0 / (period + 1)
    ema_val = data[0]
    for price in data[1:]:
        ema_val = price * k + ema_val * (1 - k)
    return ema_val


def _compute_rsi(token: str, period: int = 14) -> float | None:
    """
    DEPRECATED — kept for backward compat. Use _compute_rsi_per_tf() instead.
    Compute RSI-14 from local candles_1h table using Wilder smoothing.
    Returns RSI value (0-100) or None if insufficient data.
    """
    now = time.time()
    cutoff = now - 9000  # 2.5h

    closes = _fetch_candles(token, 'candles_1h', limit=200)
    if not closes or len(closes) < period + 1:
        return None

    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=3)
        max_ts = conn.execute(
            "SELECT MAX(ts) FROM candles_1h WHERE token = ?",
            (token.upper(),)
        ).fetchone()[0]
        conn.close()
        if max_ts and max_ts < cutoff:
            return None
    except Exception:
        pass

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        return 100.0

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def _compute_rsi_per_tf(token: str, period: int = 14) -> dict:
    """
    Compute RSI-14 per timeframe from local candles.db.
    Returns dict:
      {tf: {'oversold': bool, 'overbought': bool, 'rsi': float}}
    Uses 5m / 15m / 1h candles. RSI < 30 = oversold, > 70 = overbought.
    Freshness: 5m < 10min, 15m < 20min, 1h < 2.5h (allow forming candles).
    """
    result = {}
    now = time.time()
    freshness = {'5m': 600, '15m': 1200, '1h': 9000}

    for tf, table in [('5m', 'candles_5m'), ('15m', 'candles_15m'), ('1h', 'candles_1h')]:
        cutoff = now - freshness[tf]

        closes = _fetch_candles(token, table, limit=200)
        if not closes or len(closes) < period + 1:
            continue

        # Freshness check
        try:
            conn = sqlite3.connect(_CANDLES_DB, timeout=3)
            max_ts = conn.execute(
                f"SELECT MAX(ts) FROM {table} WHERE token = ?",
                (token.upper(),)
            ).fetchone()[0]
            conn.close()
            if max_ts and max_ts < cutoff:
                print(f"  [OC RSI] {token} {tf}: stale max_ts={max_ts} age={now-max_ts:.0f}s > {freshness[tf]}s — skipping")
                continue
        except Exception:
            pass

        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        if avg_loss == 0:
            rsi = 100.0
        else:
            for i in range(period, len(deltas)):
                avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))

        result[tf] = {
            'oversold': rsi < 30,
            'overbought': rsi > 70,
            'rsi': rsi,
        }

    return result


def _mtf_rsi(token: str) -> tuple:
    """
    Compute multi-TF RSI states for a token.
    Returns (oversold_count, overbought_count, tf_states).
    """
    tf_states = _compute_rsi_per_tf(token)
    oversold = sum(1 for s in tf_states.values() if s['oversold'])
    overbought = sum(1 for s in tf_states.values() if s['overbought'])
    return oversold, overbought, tf_states

def _compute_macd_histograms(token: str) -> dict:
    """
    Compute MACD histogram sign per timeframe from local candles.db.

    Returns dict with:
      {tf: {'bullish': bool, 'histogram': float, 'macd_line': float, 'signal_line': float}}

    Uses EMA12/26/9 (standard MACD). Histogram > 0 = bullish, < 0 = bearish.
    Freshness: 5m < 10min, 15m < 20min, 1h < 2.5h.
    """
    result = {}
    now = time.time()
    # Per-TF freshness: allow candles that might still be "forming" (not yet closed)
    freshness = {'5m': 600, '15m': 1200, '1h': 9000}  # 10min, 20min, 2.5h

    for tf, table in [('5m', 'candles_5m'), ('15m', 'candles_15m'), ('1h', 'candles_1h')]:
        cutoff = now - freshness[tf]

        closes = _fetch_candles(token, table, limit=100)
        if not closes or len(closes) < 35:
            continue

        # Freshness: check last candle timestamp
        try:
            conn = sqlite3.connect(_CANDLES_DB, timeout=3)
            max_ts = conn.execute(
                f"SELECT MAX(ts) FROM {table} WHERE token = ?",
                (token.upper(),)
            ).fetchone()[0]
            conn.close()
            if max_ts and max_ts < cutoff:
                print(f"  [OC MACD] {token} {tf}: stale max_ts={max_ts} age={now-max_ts:.0f}s > {freshness[tf]}s — skipping")
                continue
        except Exception:
            pass

        # Compute MACD series (EMA12 - EMA26) for all valid windows
        macd_series = []
        for i in range(26 - 1, len(closes)):  # start at index 25 (first valid EMA slow)
            e_fast = _ema(closes[:i + 1], 12)
            e_slow = _ema(closes[:i + 1], 26)
            if e_fast is not None and e_slow is not None:
                macd_series.append(e_fast - e_slow)

        if len(macd_series) < 9:
            continue

        macd_line = macd_series[-1]
        signal_line = _ema(macd_series, 9)
        if signal_line is None:
            continue

        histogram = macd_line - signal_line

        result[tf] = {
            'bullish': histogram > 0,
            'histogram': histogram,
            'macd_line': macd_line,
            'signal_line': signal_line,
        }

    return result


def _mtf_bull_bear(token: str) -> tuple:
    """
    Compute mt_tf_bullish / mt_tf_bearish from local candles.db.
    Returns (mt_bull: int, mt_bear: int, tf_states: dict).
    mt_bull = count of TFs with histogram > 0 (bullish)
    mt_bear = count of TFs with histogram < 0 (bearish)
    """
    tf_states = _compute_macd_histograms(token)
    mt_bull = sum(1 for s in tf_states.values() if s['bullish'])
    mt_bear = sum(1 for s in tf_states.values() if not s['bullish'])
    return mt_bull, mt_bear, tf_states


def _load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        print(f"[OC importer] WARNING: could not load {path}: {e}")
        return {}


def import_mtf_macd_signals(indicators: dict) -> int:
    """Import multi-timeframe MACD signals — computed locally from fresh candles.db."""
    count = 0
    for token, data in indicators.items():
        mt_bull, mt_bear, tf_states = _mtf_bull_bear(token)

        # Skip if we couldn't compute at least 2 TFs (insufficient data)
        if len(tf_states) < 2:
            continue

        price = _get_fresh_price(token)
        if price <= 0:
            price = data.get('price', 0)

        if mt_bull >= 3:
            sid = add_signal(
                token=token, direction='LONG',
                signal_type='oc_mtf_macd',
                source='oc-mtf-macd+',
                confidence=80, value=mt_bull, price=price,
                timeframe='5m+15m+1h'
            )
            if sid:
                bullish_tfs = [tf for tf, s in tf_states.items() if s['bullish']]
                print(f"  [OC] MTF-MACD LONG: {token} ({mt_bull}/3 TFs: {bullish_tfs}) conf=80 [+], price={price}")
                count += 1

        elif mt_bear >= 3:
            sid = add_signal(
                token=token, direction='SHORT',
                signal_type='oc_mtf_macd',
                source='oc-mtf-macd-',
                confidence=80, value=mt_bear, price=price,
                timeframe='5m+15m+1h'
            )
            if sid:
                bearish_tfs = [tf for tf, s in tf_states.items() if not s['bullish']]
                print(f"  [OC] MTF-MACD SHORT: {token} ({mt_bear}/3 TFs: {bearish_tfs}) conf=80 [-], price={price}")
                count += 1

    return count


def import_rsi_signals(indicators: dict) -> int:
    """Import multi-TF RSI signals — computed locally from candles.db (15m/1h/4h)."""
    count = 0
    for token in list(indicators.keys()):
        oversold_count, overbought_count, tf_states = _mtf_rsi(token)

        # Need at least 2 TFs to emit a signal
        if len(tf_states) < 2:
            continue

        price = _get_fresh_price(token)
        if price <= 0:
            price = indicators.get(token, {}).get('price', 0)

        # Get average RSI for logging
        avg_rsi = sum(s['rsi'] for s in tf_states.values()) / len(tf_states)

        if oversold_count >= 3:
            conf = min(90, 70 + (30 - avg_rsi) * 2)
            sid = add_signal(
                token=token, direction='LONG',
                signal_type='oc_rsi',
                source='oc-rsi+',
                confidence=conf, value=avg_rsi, price=price,
                rsi_14=avg_rsi, timeframe='5m+15m+1h'
            )
            if sid:
                oversold_tfs = [tf for tf, s in tf_states.items() if s['oversold']]
                print(f"  [OC] RSI MTF LONG: {token} ({oversold_count}/3 TFs: {oversold_tfs}) RSI={avg_rsi:.1f} conf={conf:.0f}")
                count += 1

        elif overbought_count >= 3:
            conf = min(90, 70 + (avg_rsi - 70) * 2)
            sid = add_signal(
                token=token, direction='SHORT',
                signal_type='oc_rsi',
                source='oc-rsi-',
                confidence=conf, value=avg_rsi, price=price,
                rsi_14=avg_rsi, timeframe='5m+15m+1h'
            )
            if sid:
                overbought_tfs = [tf for tf, s in tf_states.items() if s['overbought']]
                print(f"  [OC] RSI MTF SHORT: {token} ({overbought_count}/3 TFs: {overbought_tfs}) RSI={avg_rsi:.1f} conf={conf:.0f}")
                count += 1

    return count


def import_pending_signals(pending_data: dict) -> int:
    """Import pre-approved pending signals from OC pipeline."""
    signals = pending_data.get('pending_signals', [])
    count = 0
    for sig in signals:
        token     = sig.get('token')
        side      = sig.get('side', '').upper()
        direction = 'LONG' if side == 'LONG' else ('SHORT' if side == 'SHORT' else None)
        if not direction:
            continue

        confidence = sig.get('confidence', 60)
        price      = sig.get('entry')
        oc_source = sig.get('source', 'unknown')

        # Skip scanner-v9 — it's OC echoing Hermes's own signals back.
        # signal_gen.py generates native confluence; scanner-v9 is redundant.
        if oc_source == 'scanner-v9':
            continue

        # oc-zscore-v9 signals: use live local price instead of stale OC entry price
        if oc_source == 'zscore-v9' and token:
            fresh = _get_fresh_price(token)
            if fresh > 0:
                price = fresh

        # Flip: bullish→short, bearish→long (opposite of raw OC interpretation)
        if oc_source == 'mtf-macd-bullish':
            source = 'oc-mtf-macd+'
        elif oc_source == 'mtf-macd-bearish':
            source = 'oc-mtf-macd-'
        elif oc_source == 'oc-pending-mtf-macd-bullish':
            source = 'oc-mtf-macd+'
        elif oc_source == 'oc-pending-mtf-macd-bearish':
            source = 'oc-mtf-macd-'
        elif oc_source == 'zscore-v9':
            # OC pending signals use bare 'zscore-v9' (not 'oc-pending-zscore-v9')
            # Rename to directional form; never write raw 'oc-pending-zscore-v9' to DB
            source = 'oc-zscore-v9+' if direction == 'LONG' else 'oc-zscore-v9-'
        elif oc_source == 'oc-pending-mtf-rsi-overbought':
            source = 'oc-mtf-rsi+'
        elif oc_source == 'oc-pending-mtf-rsi-oversold':
            source = 'oc-mtf-rsi-'
        else:
            # oc_source may already have 'oc-pending-' prefix if coming from OC with full names
            # Normalize bare OC sources (e.g. 'mtf-rsi-oversold' → 'oc-mtf-rsi+')
            if oc_source == 'mtf-rsi-oversold':
                source = 'oc-mtf-rsi+'
            elif oc_source == 'mtf-rsi-overbought':
                source = 'oc-mtf-rsi-'
            else:
                source = oc_source if oc_source.startswith('oc-') else f'oc-pending-{oc_source}'
        value      = sig.get('atrPercent')

        sid = add_signal(
            token=token, direction=direction,
            signal_type='oc_pending',
            source=source,
            confidence=confidence, value=value, price=price,
            timeframe='oc-approved'
        )
        if sid:
            print(f"  [OC] PENDING {direction}: {token} conf={confidence:.0f} source={source}")
            count += 1

    return count


def run_oc_import() -> int:
    """Import OC signals from workspace snapshot files into the Hermes signal pipeline.
    
    Returns total number of signals emitted (across all OC signal types).
    All signals go through add_signal() — they are NOT auto-approved, they participate
    in confluence exactly like any other signal generator.
    """
    print(f"[OC signal importer] Starting at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    indicators = _load_json(OC_INDICATORS_FILE)
    pending    = _load_json(OC_PENDING_FILE)

    total = 0

    if indicators:
        n = import_mtf_macd_signals(indicators)
        print(f"[OC] MTF-MACD signals: {n}")
        total += n

    if indicators:
        n = import_rsi_signals(indicators)
        print(f"[OC] RSI signals: {n}")
        total += n

    if pending:
        n = import_pending_signals(pending)
        print(f"[OC] Pending signals: {n}")
        total += n

    print(f"[OC signal importer] Done. Total signals emitted: {total}")


if __name__ == '__main__':
    run_oc_import()
