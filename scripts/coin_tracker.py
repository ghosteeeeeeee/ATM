#!/usr/bin/env python3
"""
coin_tracker.py — Per-coin intelligence collector.

Reads from (NO new API calls):
  - hl_cache.json (allMids + meta) — written by price_collector
  - candles.db (multi-TF candles)
  - signals_hermes_runtime.db (recent signals)
  - signals_hermes.db (regime log)

Writes to:
  - coin_tracker.db (per-coin events, scores, registry)

Run: python3 coin_tracker.py
"""
import sys, os, time, json, sqlite3, math
sys.path.insert(0, os.path.dirname(__file__))

from paths import *
from coin_tracker_schema import (
    init_db, ensure_coin_table, upsert_registry, write_event, write_score,
    update_registry_health, get_all_coins, COIN_TRACKER_DB
)
from coin_tracker_score import (
    score_coin, health_from_score, WEIGHTS,
    ema as _ema, rsi as _rsi, macd as _macd, atr as _atr,
    spread_bps as _spread_bps, volume_trend as _volume_trend,
    score_momentum as _score_momentum, score_volume as _score_volume,
    score_volatility as _score_volatility, score_spread as _score_spread,
    score_signals as _score_signals, score_regime as _score_regime,
)

# ── Constants ──────────────────────────────────────────────────────────────────
MIN_PRICE = 1e-12           # Skip zero/near-zero prices

# ── Data readers ───────────────────────────────────────────────────────────────

def _read_cache():
    """Read hl_cache.json (written by price_collector)."""
    try:
        with open(HL_CACHE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def _read_candles(token, tf='5m', limit=200):
    """Read recent candles from candles.db."""
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        table = f'candles_{tf}'
        rows = conn.execute(
            f"SELECT ts, open, high, low, close, volume FROM {table} "
            f"WHERE token=? ORDER BY ts DESC LIMIT ?",
            (token, limit)
        ).fetchall()
        conn.close()
        return rows  # newest first
    except Exception:
        return []

def _read_signals(token, hours=24):
    """Read recent signals for a coin from runtime DB."""
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=10)
        cutoff = time.time() - (hours * 3600)
        rows = conn.execute(
            "SELECT signal_type, direction, confidence, price, created_at "
            "FROM signals WHERE token=? AND created_at > datetime(?, 'unixepoch') "
            "ORDER BY created_at DESC LIMIT 20",
            (token, cutoff)
        ).fetchall()
        conn.close()
        return rows
    except Exception:
        return []

def _read_regime():
    """Read current market regime."""
    try:
        conn = sqlite3.connect(STATIC_DB, timeout=10)
        row = conn.execute(
            "SELECT regime, broad_z FROM regime_log ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if row:
            return row[0], row[1]
    except Exception:
        pass
    return 'NEUTRAL', 0.0

# ── Indicator calculations ─────────────────────────────────────────────────────

def _ema(values, period):
    """Exponential moving average."""
    if not values or len(values) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(values[:period]) / period
    for v in values[period:]:
        ema = v * k + ema * (1 - k)
    return ema

def _rsi(closes, period=14):
    """Relative Strength Index."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i - 1] - closes[i]  # candles are newest first
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    if len(gains) < period:
        return None
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def _macd(closes, fast=12, slow=26, signal=9):
    """MACD histogram. Returns (macd_line, signal_line, histogram)."""
    if len(closes) < slow + signal:
        return None, None, None
    # Compute MACD line
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    if ema_fast is None or ema_slow is None:
        return None, None, None
    macd_line = ema_fast - ema_slow
    # For signal line we'd need MACD series — simplified version
    return macd_line, None, macd_line  # Return macd_line as proxy for histogram

def _atr(highs, lows, closes, period=14):
    """Average True Range."""
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(min(period, len(closes) - 1)):
        h = highs[i]
        l = lows[i]
        c_prev = closes[i + 1]
        tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
        trs.append(tr)
    if not trs:
        return None
    atr = sum(trs) / len(trs)
    return atr

def _compute_spread(bid, ask, price):
    """Spread in basis points."""
    if not bid or not ask or not price or price <= 0:
        return None
    return ((ask - bid) / price) * 10000

def _volume_trend(volumes):
    """Volume trend: positive = increasing, negative = decreasing. Returns -1 to 1."""
    if not volumes or len(volumes) < 2:
        return 0.0
    # Compare recent 30% vs earlier 30%
    n = len(volumes)
    split = max(1, n // 3)
    recent = sum(volumes[:split]) / split
    earlier = sum(volumes[split:split * 2]) / max(1, split)
    if earlier == 0:
        return 1.0 if recent > 0 else 0.0
    ratio = (recent - earlier) / earlier
    return max(-1.0, min(1.0, ratio))

# ── Scoring engine ─────────────────────────────────────────────────────────────

def _score_momentum(closes, ema_9, ema_20, ema_50):
    """Momentum score 0-100."""
    if not closes or len(closes) < 5:
        return 50.0
    # Price change over last 20 candles
    price_change = (closes[0] - closes[min(19, len(closes) - 1)]) / closes[min(19, len(closes) - 1)] * 100
    score = 50.0
    # Reward price change (clipped to ±20%)
    score += max(-30, min(30, price_change * 3))
    # EMA alignment bonus
    if ema_9 and ema_20:
        if ema_9 > ema_20:
            score += 10
        else:
            score -= 10
    if ema_20 and ema_50:
        if ema_20 > ema_50:
            score += 5
        else:
            score -= 5
    return max(0, min(100, score))

def _score_volume(vol_recent, vol_avg, vol_trend):
    """Volume score 0-100. High recent volume = high score."""
    if not vol_avg or vol_avg == 0:
        return 50.0
    ratio = vol_recent / vol_avg if vol_recent else 0
    score = 50.0
    # Volume ratio (0.1x to 5x maps to 20-90)
    score += max(-30, min(40, (ratio - 1) * 20))
    # Trend bonus
    score += vol_trend * 15
    return max(0, min(100, score))

def _score_volatility(atr, price, bb_width=None):
    """Volatility score 0-100. Moderate volatility is best (for trading)."""
    if not atr or not price or price <= 0:
        return 50.0
    atr_pct = (atr / price) * 100
    # Optimal range: 0.5% - 3% ATR
    if atr_pct < 0.3:
        return 20.0  # Too quiet
    elif atr_pct < 0.5:
        return 40.0
    elif atr_pct < 3.0:
        return 70.0 + (atr_pct - 0.5) * 8  # Peak around 2%
    elif atr_pct < 10.0:
        return 80.0 - (atr_pct - 3) * 5  # Declining
    else:
        return 30.0  # Too volatile

def _score_spread(spread_bps):
    """Spread score 0-100. Tight spread = high score."""
    if spread_bps is None:
        return 50.0
    if spread_bps < 5:
        return 95.0
    elif spread_bps < 10:
        return 85.0
    elif spread_bps < 20:
        return 70.0
    elif spread_bps < 50:
        return 50.0
    elif spread_bps < 100:
        return 30.0
    else:
        return 10.0

def _score_signals(signal_count, avg_confidence):
    """Signal confluence score 0-100."""
    score = 50.0
    # More signals = higher score (up to a point)
    score += min(25, signal_count * 5)
    # Confidence bonus
    if avg_confidence:
        score += (avg_confidence - 50) * 0.3
    return max(0, min(100, score))

def _score_regime(regime, broad_z, coin_bias=None):
    """Regime alignment score 0-100."""
    if regime in ('LONG_BIAS', 'BULL'):
        return 75.0
    elif regime in ('SHORT_BIAS', 'BEAR'):
        return 25.0
    else:
        return 50.0

def _health_from_score(composite):
    """Map composite score to health state."""
    if composite >= 91:
        return 'ready'
    elif composite >= 76:
        return 'setup'
    elif composite >= 51:
        return 'hot'
    elif composite >= 26:
        return 'warm'
    elif composite >= 11:
        return 'cold'
    else:
        return 'dead'

# ── Main collector ─────────────────────────────────────────────────────────────

def collect():
    """Main collection loop. Process all coins from HL universe."""
    init_db()
    now = int(time.time())

    cache = _read_cache()
    all_mids = cache.get('allMids', {})
    universe = cache.get('meta', {}).get('universe', [])

    if not all_mids or not universe:
        print('[coin_tracker] No data in hl_cache.json — skipping')
        return

    regime, broad_z = _read_regime()

    # Build universe lookup
    universe_map = {u['name']: u for u in universe if u.get('name')}

    processed = 0
    skipped = 0
    errors = 0

    for symbol, mid_price in all_mids.items():
        try:
            price = float(mid_price) if mid_price else 0
        except (ValueError, TypeError):
            skipped += 1
            continue

        if price < MIN_PRICE:
            skipped += 1
            continue

        meta = universe_map.get(symbol, {})
        if meta.get('isDelisted', False):
            skipped += 1
            continue

        # Ensure tables exist
        ensure_coin_table(symbol)
        upsert_registry(
            symbol,
            name=meta.get('name', symbol),
            max_leverage=meta.get('maxLeverage'),
            decimals=meta.get('decimals')
        )

        # ── Gather candle data ──
        candles_5m = _read_candles(symbol, '5m', 200)
        candles_1h = _read_candles(symbol, '1h', 100)

        # Parse candles (newest first)
        closes_5m = [c[4] for c in candles_5m if c[4]]
        highs_5m = [c[2] for c in candles_5m if c[2]]
        lows_5m = [c[3] for c in candles_5m if c[3]]
        volumes_5m = [c[5] for c in candles_5m if c[5]]

        closes_1h = [c[4] for c in candles_1h if c[4]]
        volumes_1h = [c[5] for c in candles_1h if c[5]]

        # ── Compute indicators ──
        ema_9 = _ema(closes_5m, 9) if len(closes_5m) >= 9 else None
        ema_20 = _ema(closes_5m, 20) if len(closes_5m) >= 20 else None
        ema_50 = _ema(closes_5m, 50) if len(closes_5m) >= 50 else None
        rsi_14 = _rsi(closes_5m, 14) if len(closes_5m) >= 15 else None
        _, _, macd_hist = _macd(closes_5m) if len(closes_5m) >= 35 else (None, None, None)
        atr_14 = _atr(highs_5m, lows_5m, closes_5m, 14) if len(closes_5m) >= 15 else None

        # ── Volume analysis ──
        vol_1m = volumes_5m[0] if volumes_5m else None
        vol_1h = volumes_1h[0] if volumes_1h else None
        vol_24h = sum(volumes_1h[:24]) if len(volumes_1h) >= 24 else sum(volumes_1h) if volumes_1h else None
        vol_avg = sum(volumes_5m[:50]) / min(50, len(volumes_5m)) if volumes_5m else None
        vol_recent = volumes_5m[0] if volumes_5m else 0
        vol_trend = _volume_trend(volumes_5m[:60])  # Last 5 hours

        # ── Spread (approximate from price history) ──
        spread_bps = None
        if closes_5m and len(closes_5m) >= 2:
            # Approximate spread from recent high-low range
            recent_range = highs_5m[0] - lows_5m[0] if highs_5m and lows_5m else None
            if recent_range and price > 0:
                spread_bps = (recent_range / price) * 10000

        # ── Recent signals ──
        signals = _read_signals(symbol, hours=24)
        signal_count = len(signals)
        avg_confidence = sum(s[2] for s in signals) / len(signals) if signals else None
        last_signal_type = signals[0][0] if signals else None
        last_signal_conf = signals[0][2] if signals else None

        # ── Compute scores ──
        s_momentum = _score_momentum(closes_5m, ema_9, ema_20, ema_50)
        s_volume = _score_volume(vol_recent, vol_avg, vol_trend) if vol_avg else 50.0
        s_volatility = _score_volatility(atr_14, price)
        s_spread = _score_spread(spread_bps)
        s_signals = _score_signals(signal_count, avg_confidence)
        s_regime = _score_regime(regime, broad_z)

        composite = (
            s_momentum * WEIGHTS['momentum'] +
            s_volume * WEIGHTS['volume'] +
            s_volatility * WEIGHTS['volatility'] +
            s_spread * WEIGHTS['spread'] +
            s_signals * WEIGHTS['signals'] +
            s_regime * WEIGHTS['regime']
        )

        health = _health_from_score(composite)

        # ── Write event ──
        write_event(symbol, 'tick', ts=now,
            price=price, spread_bps=spread_bps,
            vol_1m=vol_1m, vol_5m=vol_1m, vol_1h=vol_1h, vol_24h=vol_24h,
            rsi_14=rsi_14, macd_hist=macd_hist,
            ema_9=ema_9, ema_20=ema_20, ema_50=ema_50, atr_14=atr_14,
            health=health, health_score=composite,
            signal_type=last_signal_type, signal_confidence=last_signal_conf,
            regime=regime
        )

        # ── Write score ──
        write_score(symbol, now, health, composite,
            s_momentum, s_volume, s_volatility, s_spread, s_signals, s_regime, composite
        )

        # ── Update registry ──
        update_registry_health(symbol, health, composite)

        processed += 1

    # ── Prune old events (every 100 runs) ──
    run_count = int(time.time() / 60)
    if run_count % 100 == 0:
        from coin_tracker_schema import prune_old_events
        deleted = prune_old_events(days=30)
        if deleted:
            print(f'[coin_tracker] Pruned {deleted} old events')

    print(f'[coin_tracker] Done: {processed} coins processed, {skipped} skipped, {errors} errors')

if __name__ == '__main__':
    collect()
