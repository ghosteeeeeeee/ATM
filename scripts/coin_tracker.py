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
    compute_coin_regime as _compute_coin_regime,
)

# ── Constants ──────────────────────────────────────────────────────────────────
MIN_PRICE = 1e-12           # Skip zero/near-zero prices
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST
SKIP_COINS = SHORT_BLACKLIST | LONG_BLACKLIST

# Also filter test/fake coins (@ prefix, numeric-only names)
def _is_fake_coin(symbol):
    """Filter test tokens: @-prefixed, #-prefixed, pure numeric, or too short."""
    if '@' in symbol:
        return True
    if symbol.startswith('#'):
        return True
    if symbol.isdigit():
        return True
    return False

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
    conn = None
    try:
        conn = sqlite3.connect(STATIC_DB, timeout=10)
        row = conn.execute(
            "SELECT regime, broad_z FROM regime_log ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        if row:
            return row[0], row[1]
    except Exception:
        pass
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    return 'NEUTRAL', 0.0

# ── Main collector ─────────────────────────────────────────────────────────────

def collect():
    """Main collection loop. Process all coins from HL universe."""
    init_db()
    now = int(time.time())

    cache = _read_cache()
    all_mids = cache.get('allMids') or {}
    universe = (cache.get('meta') or {}).get('universe') or []

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

    # Open a single write connection for all DB operations
    from coin_tracker_schema import _table_name
    write_conn = sqlite3.connect(COIN_TRACKER_DB, timeout=30)
    write_conn.execute("PRAGMA journal_mode=WAL")

    processed = 0
    skipped = 0
    errors = 0

    try:
        for symbol, mid_price in all_mids.items():
        try:
            price = float(mid_price) if mid_price else 0
        except (ValueError, TypeError):
            skipped += 1
            continue

        if price < MIN_PRICE or price == 0:
            skipped += 1
            continue

            meta = universe_map.get(symbol, {})
            if meta.get('isDelisted', False):
                skipped += 1
                continue
            if symbol in SKIP_COINS:
                skipped += 1
                continue
            if _is_fake_coin(symbol):
                skipped += 1
                continue

            try:
                # Ensure tables exist
                ensure_coin_table(symbol, conn=write_conn)
                # Inline registry update (avoids new connection per call)
                write_conn.execute("""
                    INSERT INTO _coin_registry (symbol, name, first_seen, last_seen, max_leverage, decimals)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol) DO UPDATE SET
                        last_seen = excluded.last_seen,
                        name = COALESCE(excluded.name, _coin_registry.name),
                        max_leverage = COALESCE(excluded.max_leverage, _coin_registry.max_leverage),
                        decimals = COALESCE(excluded.decimals, _coin_registry.decimals)
                """, (symbol, meta.get('name', symbol), now, now, meta.get('maxLeverage'), meta.get('decimals')))

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

                # ── Recent signals (time-weighted) ──
                coin_signals = signals.get(symbol, [])
                signal_count = 0
                avg_confidence = None
                last_signal_type = coin_signals[0][0] if coin_signals else None
                last_signal_conf = coin_signals[0][2] if coin_signals else None

                if coin_signals:
                    # Time weights: recent signals matter more for 1m trading
                    # Last 1h = 1.0, 1-4h = 0.5, 4-12h = 0.2, 12-24h = 0.1
                    now_ts = time.time()
                    weighted_types = {}  # signal_type -> max weight seen
                    weighted_conf = []   # (weight, confidence) pairs
                    recent_directions = []  # directions from last 2 hours

                    for s in coin_signals:
                        sig_type, direction, confidence, price, created_at = s
                        # Parse timestamp
                        try:
                            sig_ts = time.mktime(time.strptime(created_at, '%Y-%m-%d %H:%M:%S'))
                        except:
                            sig_ts = now_ts

                        hours_ago = (now_ts - sig_ts) / 3600
                        if hours_ago <= 1:
                            weight = 1.0
                        elif hours_ago <= 4:
                            weight = 0.5
                        elif hours_ago <= 12:
                            weight = 0.2
                        else:
                            weight = 0.1

                        # Track signal type with highest weight
                        if sig_type:
                            if sig_type not in weighted_types or weight > weighted_types[sig_type]:
                                weighted_types[sig_type] = weight

                        # Track confidence with weight
                        if confidence and weight > 0.2:
                            weighted_conf.append((weight, confidence))

                        # Track recent directions (last 2h)
                        if hours_ago <= 2 and direction:
                            recent_directions.append(direction.upper())

                    # Count weighted signal types
                    signal_count = len(weighted_types)

                    # Weighted average confidence
                    if weighted_conf:
                        total_weight = sum(w for w, _ in weighted_conf)
                        avg_confidence = sum(w * c for w, c in weighted_conf) / total_weight if total_weight > 0 else None

                    # Check for recent conflicts (last 2h)
                    has_long_recent = 'LONG' in recent_directions
                    has_short_recent = 'SHORT' in recent_directions
                    mixed_recent = has_long_recent and has_short_recent

                    # Also check overall mix
                    all_dirs = set(s[1].upper() for s in coin_signals if s[1])
                    mixed_overall = 'LONG' in all_dirs and 'SHORT' in all_dirs

                # ── Compute scores ──
                has_candles = bool(closes_5m)
                s_momentum = _score_momentum(closes_5m, ema_9, ema_20, ema_50)
                s_volume = _score_volume(vol_recent, vol_avg, vol_trend) if vol_avg else 30.0
                s_volatility = _score_volatility(atr_14, price)
                s_spread = _score_spread(spread_bps)
                s_signals = _score_signals(signal_count, avg_confidence, mixed_overall, mixed_recent)
                coin_regime = _compute_coin_regime(closes_5m, ema_9, ema_20, ema_50, rsi_14)
                s_regime = _score_regime(coin_regime)

                composite = (
                    s_momentum * WEIGHTS['momentum'] +
                    s_volume * WEIGHTS['volume'] +
                    s_volatility * WEIGHTS['volatility'] +
                    s_spread * WEIGHTS['spread'] +
                    s_signals * WEIGHTS['signals'] +
                    s_regime * WEIGHTS['regime']
                )

                # No candle data = no real activity → force cold/dead
                if not has_candles:
                    composite = min(composite, 30.0)

                health = health_from_score(composite)

                # ── Write event + score + registry update using shared connection ──
                table = _table_name(symbol)
                # Event
                allowed = {'price', 'spread_bps', 'vol_1h', 'vol_24h',
                           'rsi_14', 'macd_hist', 'ema_9', 'ema_20', 'ema_50', 'atr_14',
                           'health', 'health_score', 'signal_type', 'signal_confidence', 'regime'}
                event_data = {
                    'ts': now, 'event_type': 'tick', 'price': price, 'spread_bps': spread_bps,
                    'vol_1h': vol_1h, 'vol_24h': vol_24h,
                    'rsi_14': rsi_14, 'macd_hist': macd_hist,
                    'ema_9': ema_9, 'ema_20': ema_20, 'ema_50': ema_50, 'atr_14': atr_14,
                    'health': health, 'health_score': composite,
                    'signal_type': last_signal_type, 'signal_confidence': last_signal_conf,
                    'regime': coin_regime
                }
                event_cols = {k: v for k, v in event_data.items() if k in allowed and v is not None}
                event_cols['ts'] = now
                event_cols['event_type'] = 'tick'
                placeholders = ', '.join(['?'] * len(event_cols))
                col_names = ', '.join(event_cols.keys())
                write_conn.execute(f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})", list(event_cols.values()))

                # Score
                write_conn.execute("""
                    INSERT INTO agg_scores (symbol, ts, health, score, momentum, volume, volatility, spread, signals, regime, composite)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol) DO UPDATE SET
                        ts=excluded.ts, health=excluded.health, score=excluded.score,
                        momentum=excluded.momentum, volume=excluded.volume, volatility=excluded.volatility,
                        spread=excluded.spread, signals=excluded.signals, regime=excluded.regime,
                        composite=excluded.composite
                """, (symbol, now, health, composite, s_momentum, s_volume, s_volatility, s_spread, s_signals, s_regime, composite))

                # Registry
                write_conn.execute("""
                    UPDATE _coin_registry SET health=?, health_score=?, last_seen=? WHERE symbol=?
                """, (health, composite, now, symbol))

                processed += 1
            except Exception as e:
                errors += 1

        # Commit all writes at once
        write_conn.commit()
    finally:
        write_conn.close()

    # ── Prune old events (every 100 runs) ──
    run_count = int(time.time() / 60)
    if run_count % 100 == 0:
        from coin_tracker_schema import prune_old_events
        deleted = prune_old_events(days=30)
        if deleted:
            print(f'[coin_tracker] Pruned {deleted} old events')

    print(f'[coin_tracker] Done: {processed} coins processed, {skipped} skipped, {errors} errors', flush=True)

if __name__ == '__main__':
    collect()
