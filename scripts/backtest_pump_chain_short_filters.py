#!/usr/bin/env python3
"""
Independent backtest of ALL pump-chain SHORT velocity and RSI filters.
Runs from scratch - no trust in previous claims.
"""
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT
import psycopg2
import sqlite3
import json
from datetime import datetime, timedelta
from collections import defaultdict

# ─── Connect to databases ───
pg_conn = psycopg2.connect(**BRAIN_DB_DICT)
pg_cur = pg_conn.cursor()

candle_db = sqlite3.connect('/root/.hermes/data/candles.db')
candle_cur = candle_db.cursor()

# ─── Step 1: Get ALL pump-chain SHORT trades ───
print("=" * 80)
print("=== PUMP-CHAIN SHORT FILTER BACKTEST ===")
print("=" * 80)
print()

# Get all trades matching pump-chain SHORT
pg_cur.execute("""
    SELECT id, token, direction, entry_price, exit_price, pnl_usdt, signal,
           open_time, close_time, volatility_regime, exit_reason,
           _signal_metadata
    FROM trades
    WHERE signal = 'pump-chain-' AND direction = 'SHORT'
    ORDER BY open_time
""")
trades = pg_cur.fetchall()
col_names = [desc[0] for desc in pg_cur.description]
print(f"Total pump-chain SHORT trades: {len(trades)}")
print()

# ─── Step 2: For each trade, get velocity and RSI data ───
trade_data = []
missing_candle = 0
missing_rsi = 0

for row in trades:
    t = dict(zip(col_names, row))
    token = t['token']
    open_time = t['open_time']  # This is the entry time

    # Parse signal metadata for RSI
    rsi = None
    if t['_signal_metadata']:
        meta = t['_signal_metadata']
        if isinstance(meta, str):
            meta = json.loads(meta)
        rsi = meta.get('rsi_14')
    if rsi is None:
        missing_rsi += 1

    # Get 5m candles before entry time
    # Need: most recent closed candles before open_time
    candle_cur.execute("""
        SELECT close FROM candles_5m
        WHERE token = ? AND ts < ? AND is_closed = 1
        ORDER BY ts DESC LIMIT 6
    """, (token, open_time))
    candles_5m = candle_cur.fetchall()

    vel_5m = None
    vel_15m = None
    vel_30m = None

    if len(candles_5m) >= 2:
        # 5m velocity: [0] is most recent, [1] is 5m ago
        close_now = candles_5m[0][0]
        close_5m_ago = candles_5m[1][0]
        if close_5m_ago > 0:
            vel_5m = (close_now - close_5m_ago) / close_5m_ago * 100
    else:
        missing_candle += 1

    if len(candles_5m) >= 4:
        # 15m velocity: [0] is most recent, [3] is 15m ago
        close_now = candles_5m[0][0]
        close_15m_ago = candles_5m[3][0]
        if close_15m_ago > 0:
            vel_15m = (close_now - close_15m_ago) / close_15m_ago * 100

    if len(candles_5m) >= 6:
        # 30m velocity: [0] is most recent, [5] is 30m ago
        close_now = candles_5m[0][0]
        close_30m_ago = candles_5m[5][0]
        if close_30m_ago > 0:
            vel_30m = (close_now - close_30m_ago) / close_30m_ago * 100

    trade_data.append({
        'id': t['id'],
        'token': token,
        'pnl': t['pnl_usdt'],
        'open_time': open_time,
        'close_time': t['close_time'],
        'entry_price': t['entry_price'],
        'exit_price': t['exit_price'],
        'signal': t['signal'],
        'regime': t['volatility_regime'],
        'exit_reason': t['exit_reason'],
        'rsi': rsi,
        'vel_5m': vel_5m,
        'vel_15m': vel_15m,
        'vel_30m': vel_30m,
    })

trades_with_candles = sum(1 for t in trade_data if t['vel_5m'] is not None)
trades_with_rsi = sum(1 for t in trade_data if t['rsi'] is not None)

print(f"Trades with candle data (5m vel): {trades_with_candles}")
print(f"Trades with RSI data: {trades_with_rsi}")
print()

# ─── Step 3: Define filters ───
filters = {
    '5m vel > 0%': lambda t: t['vel_5m'] is not None and t['vel_5m'] > 0,
    '15m vel > 0%': lambda t: t['vel_15m'] is not None and t['vel_15m'] > 0,
    '30m vel > 0%': lambda t: t['vel_30m'] is not None and t['vel_30m'] > 0,
    'RSI < 15': lambda t: t['rsi'] is not None and t['rsi'] < 15,
    'RSI < 20': lambda t: t['rsi'] is not None and t['rsi'] < 20,
    'RSI < 30': lambda t: t['rsi'] is not None and t['rsi'] < 30,
}

combos = {
    'COMBO: 5m vel>0 OR 15m vel>0 OR RSI<15': lambda t: (
        (t['vel_5m'] is not None and t['vel_5m'] > 0) or
        (t['vel_15m'] is not None and t['vel_15m'] > 0) or
        (t['rsi'] is not None and t['rsi'] < 15)
    ),
    'COMBO: 15m vel>0 OR RSI<20': lambda t: (
        (t['vel_15m'] is not None and t['vel_15m'] > 0) or
        (t['rsi'] is not None and t['rsi'] < 20)
    ),
}

# ─── Step 4: Evaluate each filter ───
def evaluate_filter(name, filter_fn, trade_data):
    """Evaluate a filter across all trades."""
    wins_killed = []  # Would have won, but filter blocks
    losses_caught = []  # Would have lost, but filter blocks
    wins_allowed = []
    losses_allowed = []
    no_data = []

    for t in trade_data:
        # Check if filter can be evaluated
        blocks = filter_fn(t)

        if t['pnl'] is not None:
            is_win = t['pnl'] > 0
        else:
            continue  # Skip trades with no PnL

        if blocks:
            if is_win:
                wins_killed.append(t)
            else:
                losses_caught.append(t)
        else:
            if is_win:
                wins_allowed.append(t)
            else:
                losses_allowed.append(t)

    total_kills = len(wins_killed) + len(losses_caught)
    win_rate_killed = (len(wins_killed) / total_kills * 100) if total_kills > 0 else 0

    sum_killed_wins = sum(t['pnl'] for t in wins_killed)
    sum_caught_losses = sum(t['pnl'] for t in losses_caught)
    net_impact = sum_caught_losses - sum_killed_wins  # Positive = filter helps

    return {
        'name': name,
        'wins_killed': wins_killed,
        'losses_caught': losses_caught,
        'wins_allowed': wins_allowed,
        'losses_allowed': losses_allowed,
        'win_rate_killed': win_rate_killed,
        'net_impact': net_impact,
        'sum_killed_wins': sum_killed_wins,
        'sum_caught_losses': sum_caught_losses,
    }

# Print filter results
all_filters = {**filters, **combos}
results = {}

for name, fn in all_filters.items():
    r = evaluate_filter(name, fn, trade_data)
    results[name] = r

    print(f"{'─' * 60}")
    print(f"Filter: {name}")
    print(f"  Wins killed: {len(r['wins_killed'])}/{len(trade_data)} total")
    for t in r['wins_killed']:
        v5 = f"{t['vel_5m']:.2f}%" if t['vel_5m'] is not None else "N/A"
        v15 = f"{t['vel_15m']:.2f}%" if t['vel_15m'] is not None else "N/A"
        v30 = f"{t['vel_30m']:.2f}%" if t['vel_30m'] is not None else "N/A"
        rsi_s = f"{t['rsi']:.1f}" if t['rsi'] is not None else "N/A"
        print(f"    ✗ KILLED WIN: {t['token']} pnl=${t['pnl']:+.2f} "
              f"vel5m={v5} vel15m={v15} vel30m={v30} RSI={rsi_s} "
              f"entry={t['entry_price']:.6f} open={t['open_time']}")
    print(f"  Losses caught: {len(r['losses_caught'])}/{len(trade_data)} total")
    for t in r['losses_caught']:
        v5 = f"{t['vel_5m']:.2f}%" if t['vel_5m'] is not None else "N/A"
        v15 = f"{t['vel_15m']:.2f}%" if t['vel_15m'] is not None else "N/A"
        v30 = f"{t['vel_30m']:.2f}%" if t['vel_30m'] is not None else "N/A"
        rsi_s = f"{t['rsi']:.1f}" if t['rsi'] is not None else "N/A"
        print(f"    ✓ CAUGHT LOSS: {t['token']} pnl=${t['pnl']:+.2f} "
              f"vel5m={v5} vel15m={v15} vel30m={v30} RSI={rsi_s} "
              f"entry={t['entry_price']:.6f} open={t['open_time']}")
    print(f"  Win rate of killed trades: {r['win_rate_killed']:.1f}%")
    print(f"  Sum of killed wins: ${r['sum_killed_wins']:+.2f}")
    print(f"  Sum of caught losses: ${r['sum_caught_losses']:+.2f}")
    print(f"  Net PnL impact: ${r['net_impact']:+.2f}")
    print()

# ─── Step 5: Summary table ───
print()
print("=" * 80)
print("=== SUMMARY TABLE ===")
print("=" * 80)
print(f"{'Filter':<40} {'Killed':>8} {'Caught':>8} {'WR kill':>8} {'Net $':>10}")
print("─" * 80)
for name, r in results.items():
    print(f"{name:<40} {len(r['wins_killed']):>8} {len(r['losses_caught']):>8} "
          f"{r['win_rate_killed']:>7.1f}% ${r['net_impact']:>+9.2f}")
print()

# ─── Step 6: Full trade data ───
print()
print("=" * 80)
print("=== FULL TRADE DATA ===")
print("=" * 80)
print(f"{'Token':<12} {'PnL':>10} {'Open Time':<22} {'5m Vel':>8} {'15m Vel':>8} "
      f"{'30m Vel':>8} {'RSI':>6} {'Verdict':<12}")
print("─" * 100)

for t in trade_data:
    # Determine verdict for each filter
    verdicts = []
    for name, fn in all_filters.items():
        if fn(t):
            verdicts.append('BLOCK')

    v5 = f"{t['vel_5m']:.2f}" if t['vel_5m'] is not None else "N/A"
    v15 = f"{t['vel_15m']:.2f}" if t['vel_15m'] is not None else "N/A"
    v30 = f"{t['vel_30m']:.2f}" if t['vel_30m'] is not None else "N/A"
    rsi_str = f"{t['rsi']:.1f}" if t['rsi'] is not None else "N/A"
    verdict = ",".join(verdicts) if verdicts else "PASS"
    pnl_str = f"${t['pnl']:+.2f}" if t['pnl'] is not None else "N/A"

    ot = t['open_time'].strftime('%Y-%m-%d %H:%M:%S') if t['open_time'] else "N/A"

    print(f"{t['token']:<12} {pnl_str:>10} {ot:<22} {v5:>8} {v15:>8} "
          f"{v30:>8} {rsi_str:>6} {verdict:<12}")

print()

# ─── Step 7: Additional analysis ───
print()
print("=" * 80)
print("=== ADDITIONAL ANALYSIS ===")
print("=" * 80)

# Win rate without any filter
wins = [t for t in trade_data if t['pnl'] and t['pnl'] > 0]
losses = [t for t in trade_data if t['pnl'] and t['pnl'] <= 0]
total_pnl = sum(t['pnl'] for t in trade_data if t['pnl'])
print(f"Baseline (no filter): {len(wins)} wins / {len(losses)} losses = "
      f"{len(wins)/(len(wins)+len(losses))*100:.1f}% win rate")
print(f"Baseline total PnL: ${total_pnl:+.2f}")
print()

# Show distribution of velocity and RSI values
vels_5m = [t['vel_5m'] for t in trade_data if t['vel_5m'] is not None]
vels_15m = [t['vel_15m'] for t in trade_data if t['vel_15m'] is not None]
vels_30m = [t['vel_30m'] for t in trade_data if t['vel_30m'] is not None]
rsis = [t['rsi'] for t in trade_data if t['rsi'] is not None]

if vels_5m:
    print(f"5m velocity distribution: min={min(vels_5m):.2f}% max={max(vels_5m):.2f}% "
          f"avg={sum(vels_5m)/len(vels_5m):.2f}%")
if vels_15m:
    print(f"15m velocity distribution: min={min(vels_15m):.2f}% max={max(vels_15m):.2f}% "
          f"avg={sum(vels_15m)/len(vels_15m):.2f}%")
if vels_30m:
    print(f"30m velocity distribution: min={min(vels_30m):.2f}% max={max(vels_30m):.2f}% "
          f"avg={sum(vels_30m)/len(vels_30m):.2f}%")
if rsis:
    print(f"RSI distribution: min={min(rsis):.1f} max={max(rsis):.1f} "
          f"avg={sum(rsis)/len(rsis):.1f}")

print()
print("Backtest complete.")
print("=" * 80)

# Clean up
pg_cur.close()
pg_conn.close()
candle_cur.close()
candle_db.close()
