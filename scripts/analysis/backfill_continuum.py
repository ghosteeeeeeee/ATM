#!/usr/bin/env python3
"""
backfill_continuum.py — Backfill BTC continuum_states using engine's own logic.

Runs the ContinuumEngine on historical 1m candles and saves results to a staging
table for verification before merging into the main continuum_states table.

Usage:
  python3 scripts/analysis/backfill_continuum.py              # Dry run
  python3 scripts/analysis/backfill_continuum.py --fetch      # Actually backfill
  python3 scripts/analysis/backfill_continuum.py --verify     # Verify staging data
  python3 scripts/analysis/backfill_continuum.py --merge      # Merge to main table
"""

import sys, os, sqlite3, time
from datetime import datetime, timezone

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS_DIR)
sys.path.insert(0, os.path.join(SCRIPTS_DIR, 'signals'))

from paths import HERMES_DATA, CANDLES_DB

CONTINUUM_DB = os.path.join(HERMES_DATA, 'continuum.db')
STAGING_TABLE = 'continuum_states_backfill'
TOKEN = 'BTC'
BACKFILL_START = '2026-08-11'
BACKFILL_END = '2026-09-04'


def create_staging():
    """Create staging table."""
    conn = sqlite3.connect(CONTINUUM_DB)
    conn.execute(f"DROP TABLE IF EXISTS {STAGING_TABLE}")
    cur = conn.cursor()
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='continuum_states'")
    schema = cur.fetchone()[0]
    conn.execute(schema.replace('continuum_states', STAGING_TABLE))
    conn.commit()
    conn.close()
    print(f"Created staging table: {STAGING_TABLE}")


def get_candles():
    """Get BTC 1m candles for backfill period."""
    start_epoch = int(datetime.strptime(BACKFILL_START, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp())
    end_epoch = int(datetime.strptime(BACKFILL_END, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp())
    
    conn = sqlite3.connect(f'file:{CANDLES_DB}?mode=ro', uri=True, timeout=10)
    cur = conn.cursor()
    cur.execute("""
        SELECT ts, open, high, low, close, volume
        FROM candles_1m WHERE token = ? AND ts >= ? AND ts < ?
        ORDER BY ts ASC
    """, (TOKEN, start_epoch, end_epoch))
    
    candles = [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3], 'close': r[4], 'volume': r[5]} for r in cur.fetchall()]
    cur.close()
    conn.close()
    
    if candles:
        print(f"Loaded {len(candles)} candles: {datetime.fromtimestamp(candles[0]['ts']).strftime('%Y-%m-%d %H:%M')} to {datetime.fromtimestamp(candles[-1]['ts']).strftime('%Y-%m-%d %H:%M')}")
    return candles


def run_backfill(candles):
    """Run backfill using engine's backtest logic (processes candles directly)."""
    from continuum_engine import ContinuumEngine, ema, zscore, velocity_5m, acceleration, \
        classify_ema300_position, classify_zscore, classify_volume, classify_velocity, \
        classify_acceleration, linreg_slope, linreg_slope_multi_tf, \
        ZSCORE_LOOKBACK, LINREG_1M_PERIOD, LINREG_STEEP_UP, LINREG_UP, LINREG_STEEP_DOWN, LINREG_DOWN, \
        VolumeRegime, Velocity, Acceleration, LinregSlope
    
    engine = ContinuumEngine(TOKEN)
    
    closes = []
    volumes = []
    results = []
    
    for i, candle in enumerate(candles):
        closes.append(candle['close'])
        volumes.append(candle['volume'])
        
        if len(closes) < 300:
            continue
        
        # Compute indicators directly (same as backtest function)
        ema300_val = ema(closes, 300)
        z = zscore(closes, lookback=ZSCORE_LOOKBACK)
        vel = velocity_5m(closes)
        acc = acceleration(closes)
        
        if len(volumes) > 60:
            prev_60 = volumes[-61:-1]
            avg_60 = sum(prev_60) / len(prev_60) if prev_60 else 1.0
            vol_ratio = volumes[-1] / avg_60 if avg_60 > 0 else 1.0
        else:
            vol_ratio = 1.0
        
        if ema300_val is None:
            continue
        
        price = closes[-1]
        
        # Classify
        raw_ema = classify_ema300_position(price, ema300_val)
        raw_z = classify_zscore(z) if z is not None else 'NEUTRAL'
        raw_vol = classify_volume(vol_ratio) if vol_ratio is not None else VolumeRegime.NORMAL
        raw_vel = classify_velocity(vel) if vel is not None else Velocity.SLOW
        raw_acc = classify_acceleration(acc) if acc is not None else Acceleration.FLAT
        
        # LinReg
        slope_1m = linreg_slope(closes, LINREG_1M_PERIOD)
        if slope_1m is not None:
            if slope_1m > LINREG_STEEP_UP: raw_linreg = LinregSlope.STEEP_UP
            elif slope_1m > LINREG_UP: raw_linreg = LinregSlope.UP
            elif slope_1m < LINREG_STEEP_DOWN: raw_linreg = LinregSlope.STEEP_DOWN
            elif slope_1m < LINREG_DOWN: raw_linreg = LinregSlope.DOWN
            else: raw_linreg = LinregSlope.FLAT
        else:
            raw_linreg = LinregSlope.FLAT
            slope_1m = 0
        
        # Hysteresis
        _, ema_conf = engine.hysteresis['ema300_position'].update(raw_ema)
        _, z_conf = engine.hysteresis['zscore_tier'].update(raw_z)
        _, vol_conf = engine.hysteresis['volume_regime'].update(raw_vol)
        _, vel_conf = engine.hysteresis['velocity'].update(raw_vel)
        _, acc_conf = engine.hysteresis['acceleration'].update(raw_acc)
        _, linreg_conf = engine.hysteresis['linreg_slope'].update(raw_linreg)
        
        ema_pos = engine.hysteresis['ema300_position'].get_confirmed() or raw_ema
        
        # Track duration
        current_dir = 'ABOVE' if price > ema300_val else 'BELOW'
        if current_dir == engine.ema300_direction:
            engine.ema300_duration += 1
        else:
            engine.ema300_direction = current_dir
            engine.ema300_duration = 1
        
        # Compute RSI and ATR for market phase
        from continuum_engine import rsi as _rsi
        rsi_val = _rsi(closes)
        
        # ATR
        if len(closes) >= 14:
            trs = []
            for j in range(1, len(closes)):
                h, l = candles[i-j]['high'], candles[i-j]['low']
                prev_c = candles[i-j-1]['close'] if j > 0 else closes[i-j]
                tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
                trs.append(tr)
            atr_val = sum(trs[-14:]) / 14
            atr_pct = (atr_val / price) * 100 if price > 0 else None
        else:
            atr_pct = None
        
        # Compute linreg alignment (multi-timeframe agreement proxy)
        linreg_alignment = 0.5 if abs(slope_1m) > 0.001 else 0.0
        
        # Compute trend quality
        trend_quality = 'NEUTRAL'
        if len(closes) >= 20:
            recent_20 = closes[-20:]
            first_10 = sum(recent_20[:10]) / 10
            last_10 = sum(recent_20[10:]) / 10
            change_pct = (last_10 - first_10) / first_10 * 100 if first_10 > 0 else 0
            if change_pct > 1.0: trend_quality = 'STRONG_UP'
            elif change_pct > 0.3: trend_quality = 'UP'
            elif change_pct < -1.0: trend_quality = 'STRONG_DOWN'
            elif change_pct < -0.3: trend_quality = 'DOWN'
            else: trend_quality = 'WEAK'
        
        # Compute Wyckoff phase
        wyckoff_phase = 'UNKNOWN'
        if len(closes) >= 100 and len(volumes) >= 100:
            recent = closes[-100:]
            first_25 = sum(recent[:25]) / 25
            mid_50 = sum(recent[25:75]) / 50
            last_25 = sum(recent[75:]) / 25
            vol_first = sum(volumes[-100:-75]) / 25 if len(volumes) >= 100 else 1
            vol_last = sum(volumes[-25:]) / 25 if len(volumes) >= 25 else 1
            if last_25 > mid_50 > first_25 and vol_last > vol_first * 1.2:
                wyckoff_phase = 'MARKUP'
            elif abs(last_25 - first_25) / first_25 < 0.005 and vol_last > vol_first * 1.1:
                wyckoff_phase = 'ACCUMULATION'
            elif abs(last_25 - first_25) / first_25 < 0.005 and vol_last > vol_first:
                wyckoff_phase = 'DISTRIBUTION'
            elif last_25 < mid_50 < first_25 and vol_last > vol_first * 1.2:
                wyckoff_phase = 'MARKDOWN'
        
        # Compute Elliott wave
        ewave_count = 'UNKNOWN'
        if len(closes) >= 50:
            recent = closes[-50:]
            pivots = []
            for j in range(2, len(recent) - 2):
                if recent[j] > recent[j-1] and recent[j] > recent[j+1]:
                    pivots.append(('H', recent[j]))
                elif recent[j] < recent[j-1] and recent[j] < recent[j+1]:
                    pivots.append(('L', recent[j]))
            if len(pivots) >= 4:
                highs = [p for p in pivots if p[0] == 'H']
                lows = [p for p in pivots if p[0] == 'L']
                if len(highs) >= 2 and highs[-1][1] > highs[-2][1]:
                    if len(lows) >= 1 and lows[-1][1] > (lows[-2][1] if len(lows) >= 2 else 0):
                        ewave_count = 'W3'
                    else:
                        ewave_count = 'W1'
                elif len(highs) >= 2 and highs[-1][1] < highs[-2][1]:
                    ewave_count = 'W4'
                elif len(lows) >= 2 and lows[-1][1] < lows[-2][1]:
                    ewave_count = 'CA'
        
        # Market phase
        market_phase = engine._detect_market_phase(rsi_val, atr_pct, vol_ratio)
        
        # Build ContinuumState and use engine's EXACT score computation
        from continuum_engine import ContinuumState
        
        # Strip enum prefixes (e.g., 'ZScoreTier.NEG' -> 'NEG')
        def _strip_enum(val):
            if isinstance(val, str) and '.' in val:
                return val.split('.')[-1]
            return val
        
        _state = ContinuumState(
            token=TOKEN, timeframe='1m', ts=candle['ts'],
            price=price, ema300=ema300_val,
            zscore_val=z if z else 0, velocity_val=vel if vel else 0,
            acceleration_val=acc if acc else 0, volume_ratio_val=vol_ratio,
            linreg_1m_slope=slope_1m, linreg_5m_slope=0,
            linreg_15m_slope=0, linreg_1h_slope=0,
            linreg_alignment=linreg_alignment, ema300_position=_strip_enum(ema_pos),
            ema300_duration=engine.ema300_duration,
            zscore_tier=_strip_enum(raw_z), volume_regime=_strip_enum(raw_vol),
            velocity_state=_strip_enum(raw_vel), acceleration_state=_strip_enum(raw_acc),
            linreg_slope_state=_strip_enum(raw_linreg), linreg_direction='NEUTRAL',
            wyckoff_phase=wyckoff_phase, ewave_count=ewave_count,
            trend_quality=trend_quality, market_phase=market_phase,
        )
        score = engine._compute_score(_state)
        
        result = {
            'token': TOKEN, 'timeframe': '1m', 'ts': candle['ts'],
            'price': price, 'ema300': ema300_val,
            'zscore_val': z if z else 0, 'velocity_val': vel if vel else 0,
            'acceleration_val': acc if acc else 0, 'volume_ratio_val': vol_ratio,
            'linreg_1m_slope': slope_1m, 'linreg_5m_slope': 0,
            'linreg_15m_slope': 0, 'linreg_1h_slope': 0,
            'linreg_alignment': 0, 'ema300_position': ema_pos.value if hasattr(ema_pos, 'value') else str(ema_pos),
            'ema300_duration': engine.ema300_duration,
            'zscore_tier': raw_z.value if hasattr(raw_z, 'value') else str(raw_z),
            'volume_regime': raw_vol.value if hasattr(raw_vol, 'value') else str(raw_vol),
            'velocity_state': raw_vel.value if hasattr(raw_vel, 'value') else str(raw_vel),
            'acceleration_state': raw_acc.value if hasattr(raw_acc, 'value') else str(raw_acc),
            'linreg_slope_state': raw_linreg.value if hasattr(raw_linreg, 'value') else str(raw_linreg),
            'linreg_direction': 'NEUTRAL',
            'wyckoff_phase': 'UNKNOWN', 'ewave_count': 'W0',
            'trend_quality': 'NEUTRAL', 'market_phase': market_phase,
            'state_score': score, 'entry_phase': 0, 'position_side': 'NONE',
            'position_size_pct': 0, 'consecutive_above': 0, 'consecutive_below': 0,
            'last_cross_ts': 0, 'updated_at': candle['ts'],
        }
        results.append(result)
        
        if len(results) % 5000 == 0 and len(results) > 0:
            print(f"  Processed {len(results)} states...")
    
    print(f"Total states generated: {len(results)}")
    return results


def save_staging(results):
    """Save to staging table."""
    conn = sqlite3.connect(CONTINUUM_DB)
    cur = conn.cursor()
    cols = list(results[0].keys())
    placeholders = ','.join(['?'] * len(cols))
    col_names = ','.join(cols)
    for r in results:
        cur.execute(f"INSERT INTO {STAGING_TABLE} ({col_names}) VALUES ({placeholders})", [r[c] for c in cols])
    conn.commit()
    conn.close()
    print(f"Saved {len(results)} rows to staging")


def verify_staging():
    """Verify staging data."""
    conn = sqlite3.connect(CONTINUUM_DB)
    cur = conn.cursor()
    
    print("=== VERIFICATION ===")
    cur.execute(f"SELECT COUNT(*) FROM {STAGING_TABLE}")
    count = cur.fetchone()[0]
    print(f"  Rows: {count}")
    
    cur.execute(f"SELECT COUNT(*) FROM {STAGING_TABLE} WHERE price IS NULL")
    nulls = cur.fetchone()[0]
    print(f"  NULLs: {nulls}")
    
    cur.execute(f"SELECT MIN(state_score), MAX(state_score), AVG(state_score) FROM {STAGING_TABLE}")
    r = cur.fetchone()
    print(f"  Score: {r[0]:.1f} to {r[1]:.1f}, avg={r[2]:.1f}")
    
    cur.execute(f"SELECT market_phase, COUNT(*) FROM {STAGING_TABLE} GROUP BY market_phase ORDER BY COUNT(*) DESC")
    print(f"  Phases:")
    for r in cur.fetchall():
        print(f"    {r[0]}: {r[1]}")
    
    cur.execute(f"SELECT ts, COUNT(*) FROM {STAGING_TABLE} GROUP BY ts HAVING COUNT(*) > 1")
    dupes = cur.fetchall()
    print(f"  Duplicates: {len(dupes)}")
    
    cur.execute(f"SELECT MIN(ts), MAX(ts) FROM {STAGING_TABLE}")
    r = cur.fetchone()
    print(f"  Range: {datetime.fromtimestamp(r[0]).strftime('%Y-%m-%d')} to {datetime.fromtimestamp(r[1]).strftime('%Y-%m-%d')}")
    
    cur.execute(f"SELECT COUNT(*) FROM {STAGING_TABLE} s JOIN continuum_states c ON s.ts = c.ts AND s.token = c.token WHERE c.token = 'BTC'")
    overlap = cur.fetchone()[0]
    print(f"  Overlap: {overlap}")
    
    print(f"\n  Spot-check (5 random):")
    cur.execute(f"SELECT * FROM {STAGING_TABLE} ORDER BY RANDOM() LIMIT 5")
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall():
        d = dict(zip(cols, r))
        dt = datetime.fromtimestamp(d['ts']).strftime('%Y-%m-%d %H:%M')
        print(f"    {dt}: price={d['price']:.1f} score={d['state_score']:.1f} phase={d['market_phase']} linreg={d['linreg_direction']}")
    
    print(f"\n  VERDICT: {'PASS' if nulls == 0 and len(dupes) == 0 else 'FAIL'}")
    conn.close()


def merge_to_main():
    """Merge staging into main."""
    conn = sqlite3.connect(CONTINUUM_DB)
    cur = conn.cursor()
    
    cur.execute(f"SELECT COUNT(*) FROM {STAGING_TABLE} s JOIN continuum_states c ON s.ts = c.ts AND s.token = c.token WHERE c.token = 'BTC'")
    overlap = cur.fetchone()[0]
    if overlap > 0:
        print(f"WARNING: {overlap} overlaps. Skipping.")
        conn.close()
        return
    
    cur.execute(f"""
        INSERT INTO continuum_states 
        SELECT id, token, timeframe, ts, price, ema300, zscore_val, velocity_val, 
               acceleration_val, volume_ratio_val, linreg_1m_slope, linreg_5m_slope,
               linreg_15m_slope, linreg_1h_slope, linreg_alignment, ema300_position,
               ema300_duration, zscore_tier, volume_regime, velocity_state, 
               acceleration_state, linreg_slope_state, linreg_direction, 
               wyckoff_phase, ewave_count, trend_quality, market_phase, state_score,
               entry_phase, position_side, position_size_pct, consecutive_above,
               consecutive_below, last_cross_ts, updated_at
        FROM {STAGING_TABLE}
    """)
    merged = cur.rowcount
    conn.commit()
    
    cur.execute("SELECT COUNT(*) FROM continuum_states WHERE token='BTC'")
    total = cur.fetchone()[0]
    cur.execute("SELECT MIN(ts), MAX(ts) FROM continuum_states WHERE token='BTC'")
    r = cur.fetchone()
    cur.close()
    conn.close()
    
    print(f"Merged {merged} rows. Total: {total}. Range: {datetime.fromtimestamp(r[0]).strftime('%Y-%m-%d')} to {datetime.fromtimestamp(r[1]).strftime('%Y-%m-%d')}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--merge', action='store_true')
    args = parser.parse_args()
    
    if args.verify:
        verify_staging()
        return
    if args.merge:
        merge_to_main()
        return
    
    create_staging()
    candles = get_candles()
    if not candles:
        print("No candles")
        return
    
    if not args.fetch:
        print(f"DRY RUN: {len(candles)} candles. Run with --fetch.")
        return
    
    start = time.time()
    results = run_backfill(candles)
    elapsed = time.time() - start
    
    if results:
        save_staging(results)
        print(f"\nDone: {len(results)} states in {elapsed:.1f}s")
        print("Run --verify then --merge")
    else:
        print("No results")


if __name__ == '__main__':
    main()
