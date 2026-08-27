#!/usr/bin/env python3
"""Standalone backtest for accel_300_v2 signal."""
import sys, os, sqlite3, time, datetime
sys.path.insert(0, '/root/.hermes/scripts')
from paths import STATIC_DB

def _ema_series(values, period):
    if len(values) < period:
        return [None] * len(values)
    k = 2.0 / (period + 1)
    result = [None] * (period - 1)
    ema_val = sum(values[:period]) / period
    result.append(ema_val)
    for price in values[period:]:
        ema_val = price * k + ema_val * (1 - k)
        result.append(ema_val)
    return result

def detect(token, prices):
    PERIOD = 300
    V2_GAP_ACCEL_WINDOW = 10
    V2_MIN_GAP_ACCEL = 0.06
    V2_VELOCITY_WINDOW = 5
    V2_PERSISTENCE_BARS = 2
    V2_MIN_GAP_PCT = 0.8
    V2_FRESH_CROSS_BARS = 8
    V2_FRESH_CROSS_MIN_GAP = 0.30

    if len(prices) < PERIOD + 30:
        return None
    closes = [float(p['price']) for p in prices]

    # ATR floor removed — signal fires at start of move when last 14 bars are quiet

    ema300 = _ema_series(closes, PERIOD)
    gap_pcts = [None if e is None or e == 0 else (p - e) / e * 100.0 for p, e in zip(closes, ema300)]
    latest_idx = len(closes) - 1
    gap_now = gap_pcts[latest_idx]
    if gap_now is None:
        return None

    direction = 'LONG' if gap_now > 0 else 'SHORT'
    abs_gap = abs(gap_now)

    # Gap thresholds
    accel_start = latest_idx - V2_GAP_ACCEL_WINDOW
    gap_then = gap_pcts[accel_start] if accel_start >= 0 else None
    if gap_then is None:
        return None
    gap_acceleration = gap_now - gap_then

    # Fresh cross detection
    cross_bar = None
    for idx in range(latest_idx, PERIOD - 1, -1):
        prev = idx - 1
        if prev < 0 or ema300[idx] is None or ema300[prev] is None:
            continue
        if direction == 'LONG':
            crossed = closes[idx] > ema300[idx] and closes[prev] <= ema300[prev]
        else:
            crossed = closes[idx] < ema300[idx] and closes[prev] >= ema300[prev]
        if crossed:
            cross_bar = idx
            break
    bars_since_cross = latest_idx - cross_bar if cross_bar is not None else 999
    fresh_cross = bars_since_cross <= V2_FRESH_CROSS_BARS

    if fresh_cross:
        if abs_gap < V2_FRESH_CROSS_MIN_GAP:
            return None
    else:
        if abs_gap < V2_MIN_GAP_PCT:
            return None

    if abs_gap > 10.0:
        return None
    if direction == 'LONG' and gap_acceleration < V2_MIN_GAP_ACCEL:
        return None
    if direction == 'SHORT' and gap_acceleration > -V2_MIN_GAP_ACCEL:
        return None

    # Price velocity
    if latest_idx < V2_VELOCITY_WINDOW:
        return None
    price_velocity = closes[latest_idx] - closes[latest_idx - V2_VELOCITY_WINDOW]
    if direction == 'LONG' and price_velocity <= 0:
        return None
    if direction == 'SHORT' and price_velocity >= 0:
        return None

    # Persistence
    persist_start = latest_idx - V2_PERSISTENCE_BARS + 1
    if persist_start < 0:
        return None
    for idx in range(persist_start, latest_idx + 1):
        ema = ema300[idx]
        if ema is None:
            return None
        if direction == 'LONG' and closes[idx] <= ema:
            return None
        if direction == 'SHORT' and closes[idx] >= ema:
            return None

    # Gap velocity
    if latest_idx < 3:
        return None
    gap_prev = gap_pcts[latest_idx - 1]
    if gap_prev is None:
        return None
    gap_velocity = gap_now - gap_prev
    if direction == 'LONG' and gap_velocity < -0.05:
        return None
    if direction == 'SHORT' and gap_velocity > 0.05:
        return None

    return {'direction': direction, 'gap_pct': gap_now, 'gap_acceleration': gap_acceleration,
            'fresh_cross': fresh_cross, 'bars_since_cross': bars_since_cross}


# Get tokens
conn = sqlite3.connect(STATIC_DB, timeout=10)
c = conn.cursor()
c.execute('SELECT DISTINCT token FROM price_history WHERE timestamp > ? ORDER BY token', (int(time.time()) - 604800,))
tokens = [r[0] for r in c.fetchall()]
conn.close()

print(f'Backtesting accel_300_v2 on {len(tokens)} tokens (7 days)')
print(f'Params: TP=2%, SL=1%, timeout=30 bars')
print()

total_trades = 0
wins = 0
losses = 0
total_pnl = 0
trades = []

for token in tokens:
    conn = sqlite3.connect(STATIC_DB, timeout=10)
    c = conn.cursor()
    c.execute('''SELECT timestamp, price FROM (SELECT timestamp, price FROM price_history WHERE token = ? ORDER BY timestamp DESC LIMIT 700) sub ORDER BY timestamp ASC''', (token.upper(),))
    rows = c.fetchall()
    conn.close()

    if not rows or len(rows) < 350:
        continue

    prices = [{'timestamp': r[0], 'price': r[1]} for r in rows]
    closes = [float(r[1]) for r in rows]
    timestamps = [r[0] for r in rows]

    cutoff = int(time.time()) - 604800
    start_bar = 0
    for j in range(len(timestamps)):
        if timestamps[j] >= cutoff:
            start_bar = j
            break
    if start_bar < 330:
        start_bar = 330

    in_trade = False
    entry_price = 0
    entry_bar = 0
    entry_direction = ''

    for i in range(start_bar, len(closes)):
        if not in_trade:
            test_prices = prices[:i+1]
            sig = detect(token, test_prices)
            if sig:
                in_trade = True
                entry_price = closes[i]
                entry_bar = i
                entry_direction = sig['direction']
        else:
            pnl_pct = (closes[i] - entry_price) / entry_price * 100
            if entry_direction == 'SHORT':
                pnl_pct = -pnl_pct
            bars_held = i - entry_bar

            if pnl_pct >= 2.0:
                total_trades += 1; wins += 1; total_pnl += pnl_pct
                trades.append((token, entry_direction, entry_price, closes[i], pnl_pct, 'TP', bars_held, timestamps[entry_bar]))
                in_trade = False
            elif pnl_pct <= -1.0:
                total_trades += 1; losses += 1; total_pnl += pnl_pct
                trades.append((token, entry_direction, entry_price, closes[i], pnl_pct, 'SL', bars_held, timestamps[entry_bar]))
                in_trade = False
            elif bars_held >= 30:
                total_trades += 1
                if pnl_pct > 0: wins += 1
                else: losses += 1
                total_pnl += pnl_pct
                trades.append((token, entry_direction, entry_price, closes[i], pnl_pct, 'TIMEOUT', bars_held, timestamps[entry_bar]))
                in_trade = False

print(f'=== ACCEL-300-V2 BACKTEST (7 days) ===')
print(f'Total trades: {total_trades}')
if total_trades > 0:
    print(f'Wins: {wins}, Losses: {losses}')
    print(f'Win Rate: {wins/total_trades*100:.1f}%')
    print(f'Total PnL: {total_pnl:+.2f}%')
    print(f'Avg PnL: {total_pnl/total_trades:+.2f}%')
    avg_win = sum(t[4] for t in trades if t[4] > 0) / max(wins, 1)
    avg_loss = sum(t[4] for t in trades if t[4] <= 0) / max(losses, 1)
    print(f'Avg Win: {avg_win:+.2f}%')
    print(f'Avg Loss: {avg_loss:+.2f}%')
    if avg_loss != 0:
        print(f'R:R Ratio: {abs(avg_win/avg_loss):.2f}:1')

    tp = [t for t in trades if t[5] == 'TP']
    sl = [t for t in trades if t[5] == 'SL']
    timeout = [t for t in trades if t[5] == 'TIMEOUT']
    print(f'\nBy exit type:')
    print(f'  TP: {len(tp)} trades ({len([t for t in tp if t[4]>0])} wins)')
    print(f'  SL: {len(sl)} trades ({len([t for t in sl if t[4]>0])} wins)')
    print(f'  TIMEOUT: {len(timeout)} trades ({len([t for t in timeout if t[4]>0])} wins)')

    # By direction
    longs = [t for t in trades if t[1] == 'LONG']
    shorts = [t for t in trades if t[1] == 'SHORT']
    print(f'\nBy direction:')
    if longs:
        l_wins = len([t for t in longs if t[4] > 0])
        print(f'  LONG: {len(longs)} trades, {l_wins} wins ({l_wins/len(longs)*100:.0f}%)')
    if shorts:
        s_wins = len([t for t in shorts if t[4] > 0])
        print(f'  SHORT: {len(shorts)} trades, {s_wins} wins ({s_wins/len(shorts)*100:.0f}%)')

    print(f'\n=== TRADES ===')
    for t in sorted(trades, key=lambda x: x[7]):
        token, direction, entry, exit_price, pnl, reason, bars, open_ts = t
        dt = datetime.datetime.fromtimestamp(open_ts, tz=datetime.timezone.utc)
        marker = '✅' if pnl > 0 else '❌'
        print(f'  {marker} {dt.strftime("%m-%d %H:%M")} {token:8s} {direction:5s} entry={entry:.6g} exit={exit_price:.6g} pnl={pnl:+.2f}% {reason:7s} {bars}bars')
else:
    print('No trades found in 7-day window')
