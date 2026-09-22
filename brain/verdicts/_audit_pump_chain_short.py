#!/usr/bin/env python3
"""
Independent Audit: Pump-Chain SHORT Signal Performance
Analyzes ALL pump-chain SHORT trades from PostgreSQL brain DB.
Cross-references with 5m candle data for velocity calculations.
"""

import sys
import json
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT
import psycopg2

# Connect to databases
conn_pg = psycopg2.connect(**BRAIN_DB_DICT)
conn_c = sqlite3.connect('/root/.hermes/data/candles.db')

cur_pg = conn_pg.cursor()
cur_c = conn_c.cursor()

# ============================================
# STEP 1: Get ALL pump-chain SHORT trades
# ============================================
cur_pg.execute("""
    SELECT id, token, direction, entry_price, exit_price, pnl_usdt, signal, 
           open_time, close_time, volatility_regime, _signal_metadata, 
           exit_reason, stop_loss, sl_distance
    FROM trades 
    WHERE signal = 'pump-chain-' AND direction = 'SHORT'
    ORDER BY open_time
""")
trades_raw = cur_pg.fetchall()
columns = [desc[0] for desc in cur_pg.description]

print(f"{'='*80}")
print(f"STEP 1: TOTAL TRADES")
print(f"{'='*80}")
print(f"Total pump-chain SHORT trades: {len(trades_raw)}")

trades = []
for t in trades_raw:
    d = dict(zip(columns, t))
    # Parse signal_metadata if it's a string
    if d['_signal_metadata']:
        if isinstance(d['_signal_metadata'], str):
            try:
                d['_signal_metadata'] = json.loads(d['_signal_metadata'])
            except:
                pass
    trades.append(d)

# ============================================
# STEP 2: Verify baseline WR and PnL
# ============================================
print(f"\n{'='*80}")
print(f"STEP 2: BASELINE WR AND PnL")
print(f"{'='*80}")

wins = [t for t in trades if t['pnl_usdt'] > 0]
losses = [t for t in trades if t['pnl_usdt'] < 0]
breakeven = [t for t in trades if t['pnl_usdt'] == 0]

total_pnl = sum(t['pnl_usdt'] for t in trades)
win_rate = len(wins) / len(trades) * 100

print(f"Total trades: {len(trades)}")
print(f"Wins: {len(wins)}")
print(f"Losses: {len(losses)}")
print(f"Breakeven: {len(breakeven)}")
print(f"Win Rate (excluding BE): {len(wins)}/{len(wins)+len(losses)} = {len(wins)/(len(wins)+len(losses))*100:.1f}%")
print(f"Win Rate (including BE as losses): {len(wins)}/{len(trades)} = {win_rate:.1f}%")
print(f"Total PnL: ${total_pnl:.2f}")
print(f"Average PnL per trade: ${total_pnl/len(trades):.4f}")

# Check: what's the claim? "61 total trades, 35W 26L, 57.4% WR, +$0.24 PnL"
print(f"\n--- CLAIM CHECK ---")
print(f"Claim: 61 trades, 35W 26L, 57.4% WR, +$0.24 PnL")
print(f"Actual: {len(trades)} trades, {len(wins)}W {len(losses)}L {len(breakeven)}BE")
print(f"Actual WR (W/L only): {len(wins)/(len(wins)+len(losses))*100:.1f}%")
print(f"Actual PnL: ${total_pnl:.2f}")

# ============================================
# STEP 3: Check 5m candle data availability
# ============================================
print(f"\n{'='*80}")
print(f"STEP 3: CANDLE DATA AVAILABILITY")
print(f"{'='*80}")

# Check candles_5m schema
cur_c.execute("PRAGMA table_info(candles_5m)")
cols = [r[1] for r in cur_c.fetchall()]
print(f"candles_5m columns: {cols}")

# Count tokens with candle data
cur_c.execute("SELECT COUNT(DISTINCT token) FROM candles_5m WHERE is_closed = 1")
token_count = cur_c.fetchone()[0]
print(f"Tokens with 5m candle data: {token_count}")

# For each trade, check if candle data exists at entry time
trades_with_candle = []
trades_without_candle = []

for t in trades:
    entry_time = t['open_time']
    token = t['token']
    
    # Look for 5m candle at entry time (within 5min window)
    entry_ts = entry_time.timestamp() if hasattr(entry_time, 'timestamp') else entry_time
    
    cur_c.execute("""
        SELECT COUNT(*) FROM candles_5m 
        WHERE token = ? AND is_closed = 1
        AND ts >= ? AND ts <= ?
    """, (token, entry_ts - 300, entry_ts + 300))
    
    candle_count = cur_c.fetchone()[0]
    t['has_candle_data'] = candle_count > 0
    t['candle_count_at_entry'] = candle_count
    
    if candle_count > 0:
        trades_with_candle.append(t)
    else:
        trades_without_candle.append(t)

print(f"\nTrades WITH candle data at entry: {len(trades_with_candle)}")
print(f"Trades WITHOUT candle data at entry: {len(trades_without_candle)}")

# WR split
cw_wins = len([t for t in trades_with_candle if t['pnl_usdt'] > 0])
cw_losses = len([t for t in trades_with_candle if t['pnl_usdt'] < 0])
ncw_wins = len([t for t in trades_without_candle if t['pnl_usdt'] > 0])
ncw_losses = len([t for t in trades_without_candle if t['pnl_usdt'] < 0])

print(f"\nWith candle data: {cw_wins}W {cw_losses}L = {cw_wins/(cw_wins+cw_losses)*100:.1f}% WR" if (cw_wins+cw_losses) > 0 else "With candle data: no W/L")
print(f"Without candle data: {ncw_wins}W {ncw_losses}L = {ncw_wins/(ncw_wins+ncw_losses)*100:.1f}% WR" if (ncw_wins+ncw_losses) > 0 else "Without candle data: no W/L")

print(f"\n--- CLAIM CHECK ---")
print(f"Claim: 'When candle data exists: 2W 4L (33.3% WR), when NO candle data: 33W 22L (60.0% WR)'")
print(f"Actual with candle: {cw_wins}W {cw_losses}L = {cw_wins/(cw_wins+cw_losses)*100:.1f}% WR" if (cw_wins+cw_losses) > 0 else "N/A")
print(f"Actual without candle: {ncw_wins}W {ncw_losses}L = {ncw_wins/(ncw_wins+ncw_losses)*100:.1f}% WR" if (ncw_wins+ncw_losses) > 0 else "N/A")

# ============================================
# STEP 4: Calculate velocities for each trade
# ============================================
print(f"\n{'='*80}")
print(f"STEP 4: VELOCITY CALCULATIONS")
print(f"{'='*80}")

def get_candles(token, entry_ts, lookback_seconds):
    """Get closed 5m candles before entry time within lookback window."""
    start_ts = entry_ts - lookback_seconds
    cur_c.execute("""
        SELECT ts, open, high, low, close, volume FROM candles_5m 
        WHERE token = ? AND is_closed = 1 AND ts >= ? AND ts < ?
        ORDER BY ts ASC
    """, (token, start_ts, entry_ts + 300))  # +300 to include current candle
    return cur_c.fetchall()

def calc_velocity(candles, num_periods):
    """Calculate velocity as % change over num_periods candles."""
    if len(candles) < num_periods + 1:
        return None
    # Velocity = (close of latest - close of earliest) / close of earliest * 100
    earliest_close = candles[0][4]  # close is index 4
    latest_close = candles[num_periods][4]
    if earliest_close == 0:
        return None
    return (latest_close - earliest_close) / earliest_close * 100

for t in trades:
    entry_ts = t['open_time'].timestamp() if hasattr(t['open_time'], 'timestamp') else t['open_time']
    token = t['token']
    
    # 5m velocity (1 candle = 5min)
    candles_5m = get_candles(token, entry_ts, 30 * 60)  # 30min lookback
    t['vel_30m'] = calc_velocity(candles_5m, 6)  # 6 * 5min = 30min
    t['vel_15m'] = calc_velocity(candles_5m, 3)  # 3 * 5min = 15min
    t['vel_5m'] = calc_velocity(candles_5m, 1)   # 1 * 5min = 5min
    t['num_candles_30m'] = len(candles_5m)
    
    if candles_5m:
        t['entry_from_candle'] = candles_5m[-1][4]  # last candle close
        t['volatility_30m'] = max(c[2] for c in candles_5m) - min(c[3] for c in candles_5m)  # 30min range

# Print velocity summary
print(f"\nVelocities computed for {len(trades)} trades")
print(f"Trades with valid 30m velocity: {len([t for t in trades if t['vel_30m'] is not None])}")
print(f"Trades with valid 15m velocity: {len([t for t in trades if t['vel_15m'] is not None])}")
print(f"Trades with valid 5m velocity: {len([t for t in trades if t['vel_5m'] is not None])}")

# ============================================
# STEP 5: Velocity filter analysis
# ============================================
print(f"\n{'='*80}")
print(f"STEP 5: VELOCITY FILTER ANALYSIS")
print(f"{'='*80}")

def velocity_filter_analysis(vel_key, thresholds, trades_list):
    """Test various velocity thresholds as filters."""
    print(f"\n--- {vel_key} ---")
    for threshold in thresholds:
        # Filter: block trades where velocity < threshold (too bearish for SHORT = losing)
        filtered = [t for t in trades_list if t[vel_key] is not None and t[vel_key] < threshold]
        wins_killed = len([t for t in filtered if t['pnl_usdt'] > 0])
        losses_caught = len([t for t in filtered if t['pnl_usdt'] < 0])
        trades_remaining = [t for t in trades_list if t[vel_key] is None or t[vel_key] >= threshold]
        remaining_wins = len([t for t in trades_remaining if t['pnl_usdt'] > 0])
        remaining_losses = len([t for t in trades_remaining if t['pnl_usdt'] < 0])
        remaining_wr = remaining_wins / (remaining_wins + remaining_losses) * 100 if (remaining_wins + remaining_losses) > 0 else 0
        print(f"  vel < {threshold}%: kills {wins_killed}W, catches {losses_caught}L | "
              f"Remaining: {remaining_wins}W {remaining_losses}L = {remaining_wr:.1f}% WR")

# Print each trade's velocities
print("\n--- PER-TRADE VELOCITIES ---")
for t in trades:
    win = "W" if t['pnl_usdt'] > 0 else ("L" if t['pnl_usdt'] < 0 else "BE")
    candle = "C" if t['has_candle_data'] else "NC"
    vel30 = f"{t['vel_30m']:.4f}" if t['vel_30m'] is not None else "N/A"
    vel15 = f"{t['vel_15m']:.4f}" if t['vel_15m'] is not None else "N/A"
    vel5 = f"{t['vel_5m']:.4f}" if t['vel_5m'] is not None else "N/A"
    rsi = t['_signal_metadata'].get('rsi_14', 'N/A') if t['_signal_metadata'] else 'N/A'
    wave = t['_signal_metadata'].get('wave_phase', 'N/A') if t['_signal_metadata'] else 'N/A'
    bb = t['_signal_metadata'].get('bb_position', 'N/A') if t['_signal_metadata'] else 'N/A'
    print(f"  {t['token']:10s} {t['open_time'].strftime('%m-%d %H:%M')} | {win} ${t['pnl_usdt']:+.2f} | "
          f"vel30={vel30:>8s} vel15={vel15:>8s} vel5={vel5:>8s} | "
          f"RSI={rsi:>6} wave={wave:>12s} BB={bb:>6} | {candle}")

# Test specific claims
print(f"\n--- CLAIM: 30m velocity > -0.8% catches ALL 4 losses with candle data, kills 0 wins ---")
candle_losses = [t for t in trades_with_candle if t['pnl_usdt'] < 0]
candle_wins = [t for t in trades_with_candle if t['pnl_usdt'] > 0]
print(f"Candle-data losses ({len(candle_losses)}):")
for t in candle_losses:
    vel30 = f"{t['vel_30m']:.4f}" if t['vel_30m'] is not None else "N/A"
    print(f"  {t['token']:10s} ${t['pnl_usdt']:+.2f} vel30={vel30} vel15={t['vel_15m']}")
print(f"Candle-data wins ({len(candle_wins)}):")
for t in candle_wins:
    vel30 = f"{t['vel_30m']:.4f}" if t['vel_30m'] is not None else "N/A"
    print(f"  {t['token']:10s} ${t['pnl_usdt']:+.2f} vel30={vel30} vel15={t['vel_15m']}")

# Test vel > -0.8%
blocked_losses = [t for t in candle_losses if t['vel_30m'] is not None and t['vel_30m'] < -0.8]
blocked_wins = [t for t in candle_wins if t['vel_30m'] is not None and t['vel_30m'] < -0.8]
print(f"\nFilter vel_30m < -0.8%: blocks {len(blocked_losses)}/{len(candle_losses)} losses, kills {len(blocked_wins)}/{len(candle_wins)} wins")

# Also test on ALL trades
all_losses = [t for t in trades if t['pnl_usdt'] < 0]
all_wins = [t for t in trades if t['pnl_usdt'] > 0]
blocked_all_losses = [t for t in all_losses if t['vel_30m'] is not None and t['vel_30m'] < -0.8]
blocked_all_wins = [t for t in all_wins if t['vel_30m'] is not None and t['vel_30m'] < -0.8]
print(f"Filter vel_30m < -0.8% (ALL trades): blocks {len(blocked_all_losses)}/{len(all_losses)} losses, kills {len(blocked_all_wins)}/{len(all_wins)} wins")

# Test the "free alpha" claim: vel > -0.5% catches 3/26 losses, kills 0/35 wins
print(f"\n--- CLAIM: 30m velocity > -0.5% kills 0/35 wins, catches 3/26 losses ---")
blocked_05_losses = [t for t in all_losses if t['vel_30m'] is not None and t['vel_30m'] < -0.5]
blocked_05_wins = [t for t in all_wins if t['vel_30m'] is not None and t['vel_30m'] < -0.5]
print(f"Filter vel_30m < -0.5%: blocks {len(blocked_05_losses)}/{len(all_losses)} losses, kills {len(blocked_05_wins)}/{len(all_wins)} wins")
print(f"Remaining WR: {len(all_wins)-len(blocked_05_wins)}/{len(all_wins)-len(blocked_05_wins)+len(all_losses)-len(blocked_05_losses)}")

# ============================================
# STEP 6: Wave phase analysis
# ============================================
print(f"\n{'='*80}")
print(f"STEP 6: WAVE PHASE ANALYSIS")
print(f"{'='*80}")

wave_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0})
for t in trades:
    meta = t['_signal_metadata'] or {}
    wave = meta.get('wave_phase', 'unknown')
    if t['pnl_usdt'] > 0:
        wave_stats[wave]['wins'] += 1
    elif t['pnl_usdt'] < 0:
        wave_stats[wave]['losses'] += 1
    wave_stats[wave]['pnl'] += t['pnl_usdt']

for wave, stats in sorted(wave_stats.items()):
    total = stats['wins'] + stats['losses']
    wr = stats['wins'] / total * 100 if total > 0 else 0
    print(f"  {wave:15s}: {stats['wins']}W {stats['losses']}L = {wr:.1f}% WR | PnL=${stats['pnl']:.2f}")

# ============================================
# STEP 7: Momentum (MACD histogram) analysis
# ============================================
print(f"\n{'='*80}")
print(f"STEP 7: MOMENTUM (MACD HIST) ANALYSIS")
print(f"{'='*80}")

# Categorize by MACD histogram sign
macd_pos = {'wins': 0, 'losses': 0, 'pnl': 0}
macd_neg = {'wins': 0, 'losses': 0, 'pnl': 0}
macd_zero = {'wins': 0, 'losses': 0, 'pnl': 0}

for t in trades:
    meta = t['_signal_metadata'] or {}
    hist = meta.get('macd_hist')
    if hist is None:
        continue
    if hist > 0:
        bucket = macd_pos
    elif hist < 0:
        bucket = macd_neg
    else:
        bucket = macd_zero
    if t['pnl_usdt'] > 0:
        bucket['wins'] += 1
    elif t['pnl_usdt'] < 0:
        bucket['losses'] += 1
    bucket['pnl'] += t['pnl_usdt']

for label, stats in [("MACD hist > 0", macd_pos), ("MACD hist < 0", macd_neg), ("MACD hist = 0", macd_zero)]:
    total = stats['wins'] + stats['losses']
    wr = stats['wins'] / total * 100 if total > 0 else 0
    print(f"  {label:20s}: {stats['wins']}W {stats['losses']}L = {wr:.1f}% WR | PnL=${stats['pnl']:.2f}")

# ============================================
# STEP 8: RSI analysis
# ============================================
print(f"\n{'='*80}")
print(f"STEP 8: RSI ANALYSIS")
print(f"{'='*80}")

rsi_buckets = {
    'oversold (<25)': {'wins': 0, 'losses': 0, 'pnl': 0},
    'low (25-40)': {'wins': 0, 'losses': 0, 'pnl': 0},
    'mid (40-55)': {'wins': 0, 'losses': 0, 'pnl': 0},
    'high (55-70)': {'wins': 0, 'losses': 0, 'pnl': 0},
    'overbought (>70)': {'wins': 0, 'losses': 0, 'pnl': 0},
}

for t in trades:
    meta = t['_signal_metadata'] or {}
    rsi = meta.get('rsi_14')
    if rsi is None:
        continue
    if rsi < 25:
        bucket = rsi_buckets['oversold (<25)']
    elif rsi < 40:
        bucket = rsi_buckets['low (25-40)']
    elif rsi < 55:
        bucket = rsi_buckets['mid (40-55)']
    elif rsi < 70:
        bucket = rsi_buckets['high (55-70)']
    else:
        bucket = rsi_buckets['overbought (>70)']
    if t['pnl_usdt'] > 0:
        bucket['wins'] += 1
    elif t['pnl_usdt'] < 0:
        bucket['losses'] += 1
    bucket['pnl'] += t['pnl_usdt']

for label, stats in rsi_buckets.items():
    total = stats['wins'] + stats['losses']
    wr = stats['wins'] / total * 100 if total > 0 else 0
    print(f"  RSI {label:20s}: {stats['wins']:2d}W {stats['losses']:2d}L = {wr:5.1f}% WR | PnL=${stats['pnl']:+.2f}")

# ============================================
# STEP 9: BB position analysis
# ============================================
print(f"\n{'='*80}")
print(f"STEP 9: BOLLINGER BAND POSITION ANALYSIS")
print(f"{'='*80}")

bb_buckets = {
    'below (-1 to -0.1)': {'wins': 0, 'losses': 0, 'pnl': 0},
    'near_low (-0.1 to 0.1)': {'wins': 0, 'losses': 0, 'pnl': 0},
    'mid (0.1 to 0.3)': {'wins': 0, 'losses': 0, 'pnl': 0},
    'high (0.3 to 0.5)': {'wins': 0, 'losses': 0, 'pnl': 0},
    'above (>0.5)': {'wins': 0, 'losses': 0, 'pnl': 0},
}

for t in trades:
    meta = t['_signal_metadata'] or {}
    bb = meta.get('bb_position')
    if bb is None:
        continue
    if bb < -0.1:
        bucket = bb_buckets['below (-1 to -0.1)']
    elif bb < 0.1:
        bucket = bb_buckets['near_low (-0.1 to 0.1)']
    elif bb < 0.3:
        bucket = bb_buckets['mid (0.1 to 0.3)']
    elif bb < 0.5:
        bucket = bb_buckets['high (0.3 to 0.5)']
    else:
        bucket = bb_buckets['above (>0.5)']
    if t['pnl_usdt'] > 0:
        bucket['wins'] += 1
    elif t['pnl_usdt'] < 0:
        bucket['losses'] += 1
    bucket['pnl'] += t['pnl_usdt']

for label, stats in bb_buckets.items():
    total = stats['wins'] + stats['losses']
    wr = stats['wins'] / total * 100 if total > 0 else 0
    print(f"  BB {label:25s}: {stats['wins']:2d}W {stats['losses']:2d}L = {wr:5.1f}% WR | PnL=${stats['pnl']:+.2f}")

# ============================================
# STEP 10: Volatility regime analysis
# ============================================
print(f"\n{'='*80}")
print(f"STEP 10: VOLATILITY REGIME ANALYSIS")
print(f"{'='*80}")

vol_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0})
for t in trades:
    regime = t['volatility_regime']
    if t['pnl_usdt'] > 0:
        vol_stats[regime]['wins'] += 1
    elif t['pnl_usdt'] < 0:
        vol_stats[regime]['losses'] += 1
    vol_stats[regime]['pnl'] += t['pnl_usdt']

for regime, stats in sorted(vol_stats.items()):
    total = stats['wins'] + stats['losses']
    wr = stats['wins'] / total * 100 if total > 0 else 0
    print(f"  {regime:10s}: {stats['wins']:2d}W {stats['losses']:2d}L = {wr:5.1f}% WR | PnL=${stats['pnl']:+.2f}")

# ============================================
# STEP 11: Time of day analysis
# ============================================
print(f"\n{'='*80}")
print(f"STEP 11: TIME OF DAY ANALYSIS (UTC hours)")
print(f"{'='*80}")

hour_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0})
for t in trades:
    hour = t['open_time'].hour
    if t['pnl_usdt'] > 0:
        hour_stats[hour]['wins'] += 1
    elif t['pnl_usdt'] < 0:
        hour_stats[hour]['losses'] += 1
    hour_stats[hour]['pnl'] += t['pnl_usdt']

for hour in range(24):
    if hour in hour_stats:
        stats = hour_stats[hour]
        total = stats['wins'] + stats['losses']
        wr = stats['wins'] / total * 100 if total > 0 else 0
        print(f"  {hour:02d}:00 UTC: {stats['wins']:2d}W {stats['losses']:2d}L = {wr:5.1f}% WR | PnL=${stats['pnl']:+.2f}")

# ============================================
# STEP 12: Exit reason analysis
# ============================================
print(f"\n{'='*80}")
print(f"STEP 12: EXIT REASON ANALYSIS")
print(f"{'='*80}")

exit_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0})
for t in trades:
    reason = t['exit_reason']
    if t['pnl_usdt'] > 0:
        exit_stats[reason]['wins'] += 1
    elif t['pnl_usdt'] < 0:
        exit_stats[reason]['losses'] += 1
    exit_stats[reason]['pnl'] += t['pnl_usdt']

for reason, stats in sorted(exit_stats.items(), key=lambda x: -sum([x[1]['wins'], x[1]['losses']])):
    total = stats['wins'] + stats['losses']
    wr = stats['wins'] / total * 100 if total > 0 else 0
    print(f"  {reason:35s}: {stats['wins']:2d}W {stats['losses']:2d}L = {wr:5.1f}% WR | PnL=${stats['pnl']:+.2f}")

# ============================================
# STEP 13: Token analysis
# ============================================
print(f"\n{'='*80}")
print(f"STEP 13: TOKEN ANALYSIS")
print(f"{'='*80}")

token_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0, 'trades': 0})
for t in trades:
    token = t['token']
    token_stats[token]['trades'] += 1
    if t['pnl_usdt'] > 0:
        token_stats[token]['wins'] += 1
    elif t['pnl_usdt'] < 0:
        token_stats[token]['losses'] += 1
    token_stats[token]['pnl'] += t['pnl_usdt']

for token, stats in sorted(token_stats.items(), key=lambda x: -x[1]['trades']):
    total = stats['wins'] + stats['losses']
    wr = stats['wins'] / total * 100 if total > 0 else 0
    print(f"  {token:10s}: {stats['trades']:2d} trades, {stats['wins']}W {stats['losses']}L = {wr:5.1f}% WR | PnL=${stats['pnl']:+.2f}")

# ============================================
# STEP 14: Z-score analysis
# ============================================
print(f"\n{'='*80}")
print(f"STEP 14: Z-SCORE ANALYSIS")
print(f"{'='*80}")

z_buckets = {
    'extreme (<-2.5)': {'wins': 0, 'losses': 0, 'pnl': 0},
    'strong (-2.5 to -1.5)': {'wins': 0, 'losses': 0, 'pnl': 0},
    'moderate (-1.5 to -0.5)': {'wins': 0, 'losses': 0, 'pnl': 0},
    'weak (-0.5 to 0)': {'wins': 0, 'losses': 0, 'pnl': 0},
    'positive (>0)': {'wins': 0, 'losses': 0, 'pnl': 0},
}

for t in trades:
    meta = t['_signal_metadata'] or {}
    z = meta.get('z_score')
    if z is None:
        continue
    if z < -2.5:
        bucket = z_buckets['extreme (<-2.5)']
    elif z < -1.5:
        bucket = z_buckets['strong (-2.5 to -1.5)']
    elif z < -0.5:
        bucket = z_buckets['moderate (-1.5 to -0.5)']
    elif z < 0:
        bucket = z_buckets['weak (-0.5 to 0)']
    else:
        bucket = z_buckets['positive (>0)']
    if t['pnl_usdt'] > 0:
        bucket['wins'] += 1
    elif t['pnl_usdt'] < 0:
        bucket['losses'] += 1
    bucket['pnl'] += t['pnl_usdt']

for label, stats in z_buckets.items():
    total = stats['wins'] + stats['losses']
    wr = stats['wins'] / total * 100 if total > 0 else 0
    print(f"  Z-score {label:25s}: {stats['wins']:2d}W {stats['losses']:2d}L = {wr:5.1f}% WR | PnL=${stats['pnl']:+.2f}")

# ============================================
# STEP 15: Stale signal analysis
# ============================================
print(f"\n{'='*80}")
print(f"STEP 15: STALE SIGNAL ANALYSIS")
print(f"{'='*80}")

stale_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0})
for t in trades:
    meta = t['_signal_metadata'] or {}
    stale = meta.get('is_stale', None)
    key = str(stale)
    if t['pnl_usdt'] > 0:
        stale_stats[key]['wins'] += 1
    elif t['pnl_usdt'] < 0:
        stale_stats[key]['losses'] += 1
    stale_stats[key]['pnl'] += t['pnl_usdt']

for key, stats in stale_stats.items():
    total = stats['wins'] + stats['losses']
    wr = stats['wins'] / total * 100 if total > 0 else 0
    print(f"  is_stale={key:6s}: {stats['wins']:2d}W {stats['losses']:2d}L = {wr:5.1f}% WR | PnL=${stats['pnl']:+.2f}")

# ============================================
# STEP 16: Why do trades WITH candle data perform worse?
# ============================================
print(f"\n{'='*80}")
print(f"STEP 16: WHY DO TRADES WITH CANDLE DATA PERFORM WORSE?")
print(f"{'='*80}")

# Compare attributes between candle vs no-candle groups
def compare_groups(g1, g2, label1, label2):
    # Average entry price
    avg_ep1 = sum(t['entry_price'] for t in g1) / len(g1) if g1 else 0
    avg_ep2 = sum(t['entry_price'] for t in g2) / len(g2) if g2 else 0
    
    # Average RSI
    rsi1 = [t['_signal_metadata'].get('rsi_14') for t in g1 if t['_signal_metadata'] and 'rsi_14' in t['_signal_metadata']]
    rsi2 = [t['_signal_metadata'].get('rsi_14') for t in g2 if t['_signal_metadata'] and 'rsi_14' in t['_signal_metadata']]
    
    # Average z-score
    z1 = [t['_signal_metadata'].get('z_score') for t in g1 if t['_signal_metadata'] and 'z_score' in t['_signal_metadata']]
    z2 = [t['_signal_metadata'].get('z_score') for t in g2 if t['_signal_metadata'] and 'z_score' in t['_signal_metadata']]
    
    # Stale percentage
    stale1 = len([t for t in g1 if t['_signal_metadata'] and t['_signal_metadata'].get('is_stale')]) / len(g1) * 100 if g1 else 0
    stale2 = len([t for t in g2 if t['_signal_metadata'] and t['_signal_metadata'].get('is_stale')]) / len(g2) * 100 if g2 else 0
    
    # Unique tokens
    tokens1 = set(t['token'] for t in g1)
    tokens2 = set(t['token'] for t in g2)
    overlap = tokens1 & tokens2
    
    # Date range
    dates1 = [t['open_time'] for t in g1]
    dates2 = [t['open_time'] for t in g2]
    
    print(f"\n  {label1} (n={len(g1)}):")
    print(f"    Date range: {min(dates1).strftime('%Y-%m-%d')} to {max(dates1).strftime('%Y-%m-%d')}")
    print(f"    Avg RSI: {sum(rsi1)/len(rsi1):.1f}" if rsi1 else "    Avg RSI: N/A")
    print(f"    Avg Z-score: {sum(z1)/len(z1):.4f}" if z1 else "    Avg Z-score: N/A")
    print(f"    Stale %: {stale1:.1f}%")
    print(f"    Unique tokens: {len(tokens1)}: {sorted(tokens1)}")
    
    print(f"\n  {label2} (n={len(g2)}):")
    print(f"    Date range: {min(dates2).strftime('%Y-%m-%d')} to {max(dates2).strftime('%Y-%m-%d')}")
    print(f"    Avg RSI: {sum(rsi2)/len(rsi2):.1f}" if rsi2 else "    Avg RSI: N/A")
    print(f"    Avg Z-score: {sum(z2)/len(z2):.4f}" if z2 else "    Avg Z-score: N/A")
    print(f"    Stale %: {stale2:.1f}%")
    print(f"    Unique tokens: {len(tokens2)}: {sorted(tokens2)}")
    
    print(f"\n    Token overlap: {len(overlap)}: {sorted(overlap)}")
    
    # Volatility regime
    vol1 = defaultdict(int)
    vol2 = defaultdict(int)
    for t in g1: vol1[t['volatility_regime']] += 1
    for t in g2: vol2[t['volatility_regime']] += 1
    print(f"    {label1} vol regimes: {dict(vol1)}")
    print(f"    {label2} vol regimes: {dict(vol2)}")

compare_groups(trades_with_candle, trades_without_candle, "WITH candle data", "WITHOUT candle data")

# ============================================
# STEP 17: Best filter combination search
# ============================================
print(f"\n{'='*80}")
print(f"STEP 17: FILTER COMBINATION SEARCH")
print(f"{'='*80}")

# Try various single filters and their combinations
best_filters = []

for vel_key in ['vel_30m', 'vel_15m', 'vel_5m']:
    for threshold in [-0.2, -0.3, -0.4, -0.5, -0.6, -0.7, -0.8, -1.0, -1.5]:
        valid = [t for t in trades if t[vel_key] is not None]
        blocked = [t for t in valid if t[vel_key] < threshold]
        remaining = [t for t in valid if t[vel_key] >= threshold]
        
        wins_killed = len([t for t in blocked if t['pnl_usdt'] > 0])
        losses_caught = len([t for t in blocked if t['pnl_usdt'] < 0])
        rem_wins = len([t for t in remaining if t['pnl_usdt'] > 0])
        rem_losses = len([t for t in remaining if t['pnl_usdt'] < 0])
        rem_wr = rem_wins / (rem_wins + rem_losses) * 100 if (rem_wins + rem_losses) > 0 else 0
        rem_pnl = sum(t['pnl_usdt'] for t in remaining)
        
        if rem_wr > 55 and losses_caught > 0:
            best_filters.append({
                'filter': f"{vel_key} < {threshold}%",
                'kills': wins_killed,
                'catches': losses_caught,
                'rem_wr': rem_wr,
                'rem_pnl': rem_pnl,
                'rem_trades': len(remaining),
            })

# Sort by net benefit (rem_wr improvement * catches)
best_filters.sort(key=lambda x: (x['rem_wr'], x['catches']), reverse=True)
print("\nTop filters (WR > 55% after filtering, catches at least 1 loss):")
for f in best_filters[:15]:
    print(f"  {f['filter']:30s}: kills {f['kills']}W, catches {f['catches']}L → {f['rem_trades']} trades, {f['rem_wr']:.1f}% WR, ${f['rem_pnl']:.2f} PnL")

# ============================================
# STEP 18: Comprehensive BEST combined filter
# ============================================
print(f"\n{'='*80}")
print(f"STEP 18: BEST COMBINED FILTERS")
print(f"{'='*80}")

# Try combining RSI + velocity
for rsi_max in [30, 40, 50, 60]:
    for vel_thresh in [-0.3, -0.5, -0.8]:
        filtered = [t for t in trades if 
                    t['vel_30m'] is not None and t['vel_30m'] < vel_thresh]
        remaining = [t for t in trades if t['vel_30m'] is None or t['vel_30m'] >= vel_thresh]
        
        rem_wins = len([t for t in remaining if t['pnl_usdt'] > 0])
        rem_losses = len([t for t in remaining if t['pnl_usdt'] < 0])
        rem_wr = rem_wins / (rem_wins + rem_losses) * 100 if (rem_wins + rem_losses) > 0 else 0
        kills = len([t for t in filtered if t['pnl_usdt'] > 0])
        catches = len([t for t in filtered if t['pnl_usdt'] < 0])
        
        if catches >= 2 and kills == 0:
            print(f"  vel30 < {vel_thresh}%: kills {kills}W, catches {catches}L → {rem_wins}W {rem_losses}L = {rem_wr:.1f}% WR")

# Try BB position filter
for bb_max in [0.2, 0.3, 0.4]:
    filtered = [t for t in trades if 
                t['_signal_metadata'] and 
                t['_signal_metadata'].get('bb_position') is not None and
                t['_signal_metadata']['bb_position'] > bb_max]
    remaining = [t for t in trades if 
                t['_signal_metadata'] is None or 
                t['_signal_metadata'].get('bb_position') is None or
                t['_signal_metadata']['bb_position'] <= bb_max]
    
    rem_wins = len([t for t in remaining if t['pnl_usdt'] > 0])
    rem_losses = len([t for t in remaining if t['pnl_usdt'] < 0])
    rem_wr = rem_wins / (rem_wins + rem_losses) * 100 if (rem_wins + rem_losses) > 0 else 0
    kills = len([t for t in filtered if t['pnl_usdt'] > 0])
    catches = len([t for t in filtered if t['pnl_usdt'] < 0])
    
    if catches > 0:
        print(f"  bb_position > {bb_max}: kills {kills}W, catches {catches}L → {rem_wins}W {rem_losses}L = {rem_wr:.1f}% WR")

# ============================================
# STEP 19: Date distribution analysis
# ============================================
print(f"\n{'='*80}")
print(f"STEP 19: DATE DISTRIBUTION ANALYSIS")
print(f"{'='*80}")

date_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0, 'tokens': set()})
for t in trades:
    date = t['open_time'].strftime('%Y-%m-%d')
    if t['pnl_usdt'] > 0:
        date_stats[date]['wins'] += 1
    elif t['pnl_usdt'] < 0:
        date_stats[date]['losses'] += 1
    date_stats[date]['pnl'] += t['pnl_usdt']
    date_stats[date]['tokens'].add(t['token'])

for date in sorted(date_stats.keys()):
    stats = date_stats[date]
    total = stats['wins'] + stats['losses']
    wr = stats['wins'] / total * 100 if total > 0 else 0
    print(f"  {date}: {stats['wins']}W {stats['losses']}L = {wr:.1f}% WR | PnL=${stats['pnl']:+.2f} | {sorted(stats['tokens'])}")

# ============================================
# STEP 20: BTC regime analysis
# ============================================
print(f"\n{'='*80}")
print(f"STEP 20: BTC REGIME ANALYSIS")
print(f"{'='*80}")

btc_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0})
for t in trades:
    meta = t['_signal_metadata'] or {}
    btc_reg = meta.get('btc_regime', 'unknown')
    if t['pnl_usdt'] > 0:
        btc_stats[btc_reg]['wins'] += 1
    elif t['pnl_usdt'] < 0:
        btc_stats[btc_reg]['losses'] += 1
    btc_stats[btc_reg]['pnl'] += t['pnl_usdt']

for reg, stats in sorted(btc_stats.items()):
    total = stats['wins'] + stats['losses']
    wr = stats['wins'] / total * 100 if total > 0 else 0
    print(f"  BTC {reg:15s}: {stats['wins']:2d}W {stats['losses']:2d}L = {wr:5.1f}% WR | PnL=${stats['pnl']:+.2f}")

# ============================================
# STEP 21: BB position filter - "oversold SHORT" pattern
# ============================================
print(f"\n{'='*80}")
print(f"STEP 21: BB POSITION - OVERSOLD SHORT PATTERN")
print(f"{'='*80}")

# SHORTing when BB is already low (below midline) should be worse
bb_low = [t for t in trades if t['_signal_metadata'] and 
          t['_signal_metadata'].get('bb_position') is not None and
          t['_signal_metadata']['bb_position'] < 0]
bb_high = [t for t in trades if t['_signal_metadata'] and 
           t['_signal_metadata'].get('bb_position') is not None and
           t['_signal_metadata']['bb_position'] >= 0]

bb_low_w = len([t for t in bb_low if t['pnl_usdt'] > 0])
bb_low_l = len([t for t in bb_low if t['pnl_usdt'] < 0])
bb_high_w = len([t for t in bb_high if t['pnl_usdt'] > 0])
bb_high_l = len([t for t in bb_high if t['pnl_usdt'] < 0])

bb_low_wr = bb_low_w / (bb_low_w + bb_low_l) * 100 if (bb_low_w + bb_low_l) > 0 else 0
bb_high_wr = bb_high_w / (bb_high_w + bb_high_l) * 100 if (bb_high_w + bb_high_l) > 0 else 0

print(f"  BB position < 0 (price below mid): {bb_low_w}W {bb_low_l}L = {bb_low_wr:.1f}% WR")
print(f"  BB position >= 0 (price above mid): {bb_high_w}W {bb_high_l}L = {bb_high_wr:.1f}% WR")

# ============================================
# STEP 22: RSI + BB combined pattern
# ============================================
print(f"\n{'='*80}")
print(f"STEP 22: RSI + BB POSITION COMBINED PATTERNS")
print(f"{'='*80}")

# For SHORT: good = RSI high (overbought) + BB high (price elevated)
# Bad = RSI low (oversold) + BB low (already dumped)
for rsi_range, bb_range in [
    ("RSI<30, BB<0", lambda r, b: r < 30 and b < 0),
    ("RSI<30, BB>=0", lambda r, b: r < 30 and b >= 0),
    ("RSI 30-50, BB<0", lambda r, b: 30 <= r < 50 and b < 0),
    ("RSI 30-50, BB>=0", lambda r, b: 30 <= r < 50 and b >= 0),
    ("RSI 50-70, BB<0", lambda r, b: 50 <= r < 70 and b < 0),
    ("RSI 50-70, BB>=0", lambda r, b: 50 <= r < 70 and b >= 0),
    ("RSI>=70, BB<0", lambda r, b: r >= 70 and b < 0),
    ("RSI>=70, BB>=0", lambda r, b: r >= 70 and b >= 0),
]:
    group = []
    for t in trades:
        meta = t['_signal_metadata'] or {}
        rsi = meta.get('rsi_14')
        bb = meta.get('bb_position')
        if rsi is None or bb is None:
            continue
        if bb_range(rsi, bb):
            group.append(t)
    
    if group:
        w = len([t for t in group if t['pnl_usdt'] > 0])
        l = len([t for t in group if t['pnl_usdt'] < 0])
        wr = w / (w + l) * 100 if (w + l) > 0 else 0
        pnl = sum(t['pnl_usdt'] for t in group)
        print(f"  {rsi_range:25s}: {w}W {l}L = {wr:5.1f}% WR | PnL=${pnl:+.2f}")

# ============================================
# STEP 23: Losses with candle data - detailed investigation
# ============================================
print(f"\n{'='*80}")
print(f"STEP 23: DETAILED INVESTIGATION OF CANDLE-DATA LOSSES")
print(f"{'='*80}")

for t in candle_losses:
    meta = t['_signal_metadata'] or {}
    print(f"\n  Token: {t['token']}")
    print(f"  Entry: {t['open_time']}")
    print(f"  PnL: ${t['pnl_usdt']:+.2f}")
    print(f"  Exit reason: {t['exit_reason']}")
    print(f"  Volatility: {t['volatility_regime']}")
    print(f"  RSI: {meta.get('rsi_14')}")
    print(f"  Z-score: {meta.get('z_score')}")
    print(f"  BB position: {meta.get('bb_position')}")
    print(f"  Wave phase: {meta.get('wave_phase')}")
    print(f"  MACD hist: {meta.get('macd_hist')}")
    print(f"  Stale: {meta.get('is_stale')}")
    print(f"  BTC regime: {meta.get('btc_regime')}")
    print(f"  BTC score: {meta.get('btc_score')}")
    print(f"  vel_30m: {t.get('vel_30m')}")
    print(f"  vel_15m: {t.get('vel_15m')}")
    print(f"  vel_5m: {t.get('vel_5m')}")
    print(f"  Candles at entry: {t['candle_count_at_entry']}")

# ============================================
# STEP 24: Threshold sweep for 30m velocity
# ============================================
print(f"\n{'='*80}")
print(f"STEP 24: THRESHOLD SWEEP FOR 30M VELOCITY")
print(f"{'='*80}")

print(f"\n{'Threshold':>12s} | {'Kills W':>8s} | {'Catches L':>9s} | {'Net L avoided':>12s} | {'Rem WR':>8s} | {'Rem PnL':>8s}")
print(f"{'-'*12}-+-{'-'*8}-+-{'-'*9}-+-{'-'*12}-+-{'-'*8}-+-{'-'*8}")

for threshold in [x * 0.1 for x in range(-20, 1)]:
    valid = [t for t in trades if t['vel_30m'] is not None]
    blocked = [t for t in valid if t['vel_30m'] < threshold]
    remaining = [t for t in valid if t['vel_30m'] >= threshold]
    
    kills = len([t for t in blocked if t['pnl_usdt'] > 0])
    catches = len([t for t in blocked if t['pnl_usdt'] < 0])
    rem_wins = len([t for t in remaining if t['pnl_usdt'] > 0])
    rem_losses = len([t for t in remaining if t['pnl_usdt'] < 0])
    rem_wr = rem_wins / (rem_wins + rem_losses) * 100 if (rem_wins + rem_losses) > 0 else 0
    rem_pnl = sum(t['pnl_usdt'] for t in remaining)
    
    print(f"{threshold:>11.1f}% | {kills:>8d} | {catches:>9d} | {catches-kills:>12d} | {rem_wr:>7.1f}% | ${rem_pnl:>7.2f}")

# ============================================
# STEP 25: Check if "no candle data" tokens are newer/less popular
# ============================================
print(f"\n{'='*80}")
print(f"STEP 25: TOKEN CHARACTERISTICS - CANDLE vs NO CANDLE")
print(f"{'='*80}")

# Check if tokens without candle data have less data overall
tokens_with = set(t['token'] for t in trades_with_candle)
tokens_without = set(t['token'] for t in trades_without_candle)

print(f"\nTokens WITH candle data at entry: {sorted(tokens_with)}")
print(f"Tokens WITHOUT candle data at entry: {sorted(tokens_without)}")
print(f"Overlap: {sorted(tokens_with & tokens_without)}")

# For each token without candle data, check total candle count
for token in sorted(tokens_without):
    cur_c.execute("SELECT COUNT(*), MIN(ts), MAX(ts) FROM candles_5m WHERE token = ? AND is_closed = 1", (token,))
    result = cur_c.fetchone()
    count = result[0]
    min_ts = datetime.fromtimestamp(result[1]) if result[1] else None
    max_ts = datetime.fromtimestamp(result[2]) if result[2] else None
    
    # Get trade entry times for this token
    trade_times = [t['open_time'] for t in trades_without_candle if t['token'] == token]
    
    if count > 0:
        print(f"  {token:10s}: {count:5d} candles, range {min_ts} to {max_ts}")
        for tt in trade_times:
            print(f"    Trade entry: {tt} — {'IN range' if min_ts <= tt <= max_ts else 'OUTSIDE range'}")
    else:
        print(f"  {token:10s}: NO candle data at all")
        for tt in trade_times:
            print(f"    Trade entry: {tt}")

# ============================================
# SUMMARY
# ============================================
print(f"\n{'='*80}")
print(f"SUMMARY OF FINDINGS")
print(f"{'='*80}")

print(f"""
1. BASELINE: {len(trades)} trades, {len(wins)}W {len(losses)}L {len(breakeven)}BE
   WR (W/L only): {len(wins)/(len(wins)+len(losses))*100:.1f}%
   Total PnL: ${total_pnl:.2f}

2. CANDLE DATA SPLIT:
   With candles: {len(trades_with_candle)} trades ({cw_wins}W {cw_losses}L)
   Without candles: {len(trades_without_candle)} trades ({ncw_wins}W {ncw_losses}L)

3. VELOCITY FILTERS:
   Best single filter: vel_30m thresholds found above

4. WAVE PHASE:
   Accelerating: WR calculated above
   Falling: WR calculated above

5. BTC REGIME:
   BULL_TREND: WR calculated above
   BEAR_TREND: WR calculated above
""")

# Cleanup
cur_pg.close()
cur_c.close()
conn_pg.close()
conn_c.close()

print("Audit complete.")
