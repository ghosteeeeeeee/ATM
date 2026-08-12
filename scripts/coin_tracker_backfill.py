#!/usr/bin/env python3
"""
coin_tracker_backfill.py — Backfill historical events from candles.db into coin_tracker.db.

Reads 5m candles and writes one event per candle to per-coin tables.
Gives the dashboard actual price history for charting.

Run once: python3 coin_tracker_backfill.py
"""
import sys, os, time, sqlite3
sys.path.insert(0, os.path.dirname(__file__))

from paths import HERMES_DATA, CANDLES_DB
from coin_tracker_schema import (
    init_db, ensure_coin_table, _table_name, _conn, COIN_TRACKER_DB, _TABLE_EXISTS_CACHE
)
from coin_tracker_score import (
    ema, rsi, macd, atr, volume_trend,
    score_momentum, score_volume, score_volatility, score_spread,
    score_signals, score_regime, compute_coin_regime, health_from_score, WEIGHTS
)
from coin_tracker import SKIP_COINS, _is_fake_coin

BATCH_SIZE = 500  # Events per commit


def backfill():
    init_db()
    _TABLE_EXISTS_CACHE.clear()  # Force table checks

    candles_conn = None
    write_conn = None
    try:
        candles_conn = sqlite3.connect(CANDLES_DB, timeout=10)
        candles_conn.row_factory = sqlite3.Row

        # Get all tokens with 5m candles
        tokens = [r[0] for r in candles_conn.execute(
            "SELECT DISTINCT token FROM candles_5m ORDER BY token"
        ).fetchall()]
        print(f'[backfill] {len(tokens)} tokens with 5m candles', flush=True)

        # Read regime once
        regime = 'NEUTRAL'
        regime_conn = None
        try:
            regime_conn = sqlite3.connect(os.path.join(HERMES_DATA, 'signals_hermes.db'), timeout=10)
            row = regime_conn.execute(
                "SELECT regime FROM regime_log ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
            regime = row[0] if row else 'NEUTRAL'
        except Exception:
            pass
        finally:
            if regime_conn:
                try:
                    regime_conn.close()
                except Exception:
                    pass

        write_conn = sqlite3.connect(COIN_TRACKER_DB, timeout=30)
        write_conn.execute("PRAGMA journal_mode=WAL")

        total_events = 0
        processed_tokens = 0
        SAMPLE_EVERY = 1  # every candle for smooth sparklines

        for token in tokens:
            if token in SKIP_COINS or _is_fake_coin(token):
                continue

            candles = candles_conn.execute(
                "SELECT ts, open, high, low, close, volume FROM candles_5m "
                "WHERE token=? ORDER BY ts DESC LIMIT 1000",
                (token,)
            ).fetchall()
            candles.reverse()

            if len(candles) < 2:
                continue

            ensure_coin_table(token, conn=write_conn)
            events_written = 0

            closes = [c['close'] for c in candles]
            highs = [c['high'] for c in candles]
            lows = [c['low'] for c in candles]
            volumes = [c['volume'] for c in candles]

            for i in range(len(candles)):
                if i % SAMPLE_EVERY != 0 and i != len(candles) - 1:
                    continue

                c = candles[i]
                ts = c['ts']
                price = c['close']

                if price <= 0:
                    continue

                h_closes = closes[:i+1]
                h_highs = highs[:i+1]
                h_lows = lows[:i+1]
                h_volumes = volumes[:i+1]

                ema_9_val = ema(h_closes, 9) if len(h_closes) >= 9 else None
                ema_20_val = ema(h_closes, 20) if len(h_closes) >= 20 else None
                ema_50_val = ema(h_closes, 50) if len(h_closes) >= 50 else None
                rsi_14_val = rsi(h_closes, 14) if len(h_closes) >= 15 else None
                _, _, macd_hist_val = macd(h_closes) if len(h_closes) >= 35 else (None, None, None)
                atr_14_val = atr(h_highs, h_lows, h_closes, 14) if len(h_closes) >= 15 else None

                vol_1h = sum(h_volumes[-12:]) if len(h_volumes) >= 12 else sum(h_volumes)
                vol_avg = sum(h_volumes[-50:]) / min(50, len(h_volumes)) if h_volumes else None
                vol_recent = h_volumes[-1] if h_volumes else 0
                vt = volume_trend(h_volumes[-60:]) if len(h_volumes) >= 2 else 0

                # Spread
                spread_bps = None
                if h_highs and h_lows and price > 0:
                    r = h_highs[-1] - h_lows[-1]
                    if r:
                        spread_bps = (r / price) * 10000

                # Scores
                s_mom = score_momentum(h_closes, ema_9_val, ema_20_val, ema_50_val)
                s_vol = score_volume(vol_recent, vol_avg, vt) if vol_avg else 30.0
                s_vola = score_volatility(atr_14_val, price)
                s_spread = score_spread(spread_bps)
                s_sig = score_signals(0, None)  # No signal history in backfill
                coin_regime = compute_coin_regime(h_closes, ema_9_val, ema_20_val, ema_50_val, rsi_14_val)
                s_reg = score_regime(coin_regime)

                composite = (
                    s_mom * WEIGHTS['momentum'] +
                    s_vol * WEIGHTS['volume'] +
                    s_vola * WEIGHTS['volatility'] +
                    s_spread * WEIGHTS['spread'] +
                    s_sig * WEIGHTS['signals'] +
                    s_reg * WEIGHTS['regime']
                )

                # No candle data check not needed — we're reading candles
                health = health_from_score(composite)

                # Write event
                table = _table_name(token)
                write_conn.execute(
                    f"INSERT INTO {table} (ts, event_type, price, spread_bps, "
                    f"vol_1h, rsi_14, macd_hist, ema_9, ema_20, ema_50, atr_14, "
                    f"health, health_score, regime) "
                    f"VALUES (?, 'candle', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (ts, price, spread_bps, vol_1h,
                     rsi_14_val, macd_hist_val, ema_9_val, ema_20_val, ema_50_val, atr_14_val,
                     health, composite, coin_regime)
                )
                events_written += 1
                total_events += 1

                if events_written % BATCH_SIZE == 0:
                    write_conn.commit()

            processed_tokens += 1

            if processed_tokens % 20 == 0:
                print(f'[backfill] {processed_tokens}/{len(tokens)} tokens, {total_events} events', flush=True)
    finally:
        if write_conn:
            try:
                write_conn.commit()
                write_conn.close()
            except Exception:
                pass
        if candles_conn:
            try:
                candles_conn.close()
            except Exception:
                pass

    print(f'[backfill] Done: {processed_tokens} tokens, {total_events} events', flush=True)


if __name__ == '__main__':
    backfill()
