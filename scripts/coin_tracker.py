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

def _read_candles_batch(tokens, tf='5m', limit=200, conn=None):
    """Read recent candles for multiple tokens in one connection."""
    results = {}
    try:
        table = f'candles_{tf}'
        for token in tokens:
            rows = conn.execute(
                f"SELECT ts, open, high, low, close, volume FROM {table} "
                f"WHERE token=? ORDER BY ts DESC LIMIT ?",
                (token, limit)
            ).fetchall()
            results[token] = rows
    except Exception:
        pass
    return results

def _read_signals_batch(tokens, hours=24, conn=None):
    """Read recent signals for multiple tokens in one connection."""
    results = {}
    try:
        cutoff = time.time() - (hours * 3600)
        for token in tokens:
            rows = conn.execute(
                "SELECT signal_type, direction, confidence, price, created_at "
                "FROM signals WHERE token=? AND created_at > datetime(?, 'unixepoch') "
                "ORDER BY created_at DESC LIMIT 20",
                (token, cutoff)
            ).fetchall()
            results[token] = rows
    except Exception:
        pass
    return results

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

    # Batch read candle and signal data with shared connections
    tokens = list(all_mids.keys())
    candles_conn = sqlite3.connect(CANDLES_DB, timeout=10)
    signals_conn = sqlite3.connect(RUNTIME_DB, timeout=10)
    try:
        candles_5m = _read_candles_batch(tokens, '5m', 200, candles_conn)
        candles_1h = _read_candles_batch(tokens, '1h', 100, candles_conn)
        signals = _read_signals_batch(tokens, hours=24, conn=signals_conn)
    finally:
        candles_conn.close()
        signals_conn.close()

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

        try:
            # Ensure tables exist
            ensure_coin_table(symbol)
            upsert_registry(
                symbol,
                name=meta.get('name', symbol),
                max_leverage=meta.get('maxLeverage'),
                decimals=meta.get('decimals')
            )

            # Parse candles (newest first)
            c5m = candles_5m.get(symbol, [])
            c1h = candles_1h.get(symbol, [])

            closes_5m = [c[4] for c in c5m if c[4]]
            highs_5m = [c[2] for c in c5m if c[2]]
            lows_5m = [c[3] for c in c5m if c[3]]
            volumes_5m = [c[5] for c in c5m if c[5]]

            closes_1h = [c[4] for c in c1h if c[4]]
            volumes_1h = [c[5] for c in c1h if c[5]]

            # ── Compute indicators ──
            ema_9 = _ema(closes_5m, 9) if len(closes_5m) >= 9 else None
            ema_20 = _ema(closes_5m, 20) if len(closes_5m) >= 20 else None
            ema_50 = _ema(closes_5m, 50) if len(closes_5m) >= 50 else None
            rsi_14 = _rsi(closes_5m, 14) if len(closes_5m) >= 15 else None
            _, _, macd_hist = _macd(closes_5m) if len(closes_5m) >= 35 else (None, None, None)
            atr_14 = _atr(highs_5m, lows_5m, closes_5m, 14) if len(closes_5m) >= 15 else None

            # ── Volume analysis ──
            vol_1h = volumes_1h[0] if volumes_1h else None
            vol_24h = sum(volumes_1h[:24]) if len(volumes_1h) >= 24 else sum(volumes_1h) if volumes_1h else None
            vol_avg = sum(volumes_5m[:50]) / min(50, len(volumes_5m)) if volumes_5m else None
            vol_recent = volumes_5m[0] if volumes_5m else 0
            vol_trend = _volume_trend(volumes_5m[:60])

            # ── Spread (approximate from candle range) ──
            spread_bps = None
            if highs_5m and lows_5m and price > 0:
                recent_range = highs_5m[0] - lows_5m[0]
                if recent_range:
                    spread_bps = (recent_range / price) * 10000

            # ── Recent signals ──
            coin_signals = signals.get(symbol, [])
            signal_count = len(coin_signals)
            avg_confidence = sum(s[2] for s in coin_signals) / len(coin_signals) if coin_signals else None
            last_signal_type = coin_signals[0][0] if coin_signals else None
            last_signal_conf = coin_signals[0][2] if coin_signals else None

            # ── Compute scores ──
            s_momentum = _score_momentum(closes_5m, ema_9, ema_20, ema_50)
            s_volume = _score_volume(vol_recent, vol_avg, vol_trend) if vol_avg else 50.0
            s_volatility = _score_volatility(atr_14, price)
            s_spread = _score_spread(spread_bps)
            s_signals = _score_signals(signal_count, avg_confidence)
            s_regime = _score_regime(regime)

            composite = (
                s_momentum * WEIGHTS['momentum'] +
                s_volume * WEIGHTS['volume'] +
                s_volatility * WEIGHTS['volatility'] +
                s_spread * WEIGHTS['spread'] +
                s_signals * WEIGHTS['signals'] +
                s_regime * WEIGHTS['regime']
            )

            health = health_from_score(composite)

            # ── Write event ──
            write_event(symbol, 'tick', ts=now,
                price=price, spread_bps=spread_bps,
                vol_1h=vol_1h, vol_24h=vol_24h,
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
        except Exception as e:
            errors += 1

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
