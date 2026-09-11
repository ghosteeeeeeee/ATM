#!/usr/bin/env python3
"""
Fast EMA300 rejection backtest - 10 tokens max, vectorized where possible.
"""

import sqlite3
import time
from collections import defaultdict
from pathlib import Path

DB_PATH = Path('/root/.hermes/data/candles.db')

def calc_ema(closes, period):
    ema = [closes[0]]
    k = 2.0 / (period + 1)
    for c in closes[1:]:
        ema.append(c * k + ema[-1] * (1 - k))
    return ema

def load_candles(token, timeframe, min_rows=600):
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    rows = conn.execute(
        f"SELECT ts, open, high, low, close FROM {timeframe} WHERE token = ? ORDER BY ts ASC",
        (token,)
    ).fetchall()
    conn.close()
    if len(rows) < min_rows:
        return []
    return rows

def backtest_token(token, timeframe, lookahead=4):
    """Backtest one token. Returns list of result dicts."""
    rows = load_candles(token, timeframe, 600)
    if not rows:
        return []

    n = len(rows)
    closes = [r[4] for r in rows]
    ema = calc_ema(closes, 300)

    results = []
    min_wick_ratio = 0.30

    for i in range(300, n - lookahead - 1):
        o, h, l, c = rows[i][1], rows[i][2], rows[i][3], rows[i][4]
        ema_val = ema[i]
        candle_range = h - l
        if candle_range == 0:
            continue

        # Check if candle touches EMA
        touches_above = h >= ema_val * 0.999
        touches_below = l <= ema_val * 1.001

        direction = None
        wick_ratio = 0
        pre_move = 0

        if touches_above:
            upper_wick = h - max(o, c)
            if upper_wick > 0:
                wr = upper_wick / candle_range
                if wr >= min_wick_ratio:
                    direction = 'SHORT'
                    wick_ratio = wr
                    pre_move = (h - ema_val) / ema_val * 100

        if touches_below and direction is None:
            lower_wick = min(o, c) - l
            if lower_wick > 0:
                wr = lower_wick / candle_range
                if wr >= min_wick_ratio:
                    direction = 'LONG'
                    wick_ratio = wr
                    pre_move = (ema_val - l) / ema_val * 100

        if direction is None:
            continue

        # Evaluate outcome
        entry_idx = i + 1
        if entry_idx >= n:
            continue
        entry_price = rows[entry_idx][1]  # open of next candle

        last_idx = min(entry_idx + lookahead - 1, n - 1)
        exit_price = rows[last_idx][4]

        if direction == 'SHORT':
            pnl = (entry_price - exit_price) / entry_price * 100
        else:
            pnl = (exit_price - entry_price) / entry_price * 100

        # Max favorable / adverse
        best = 0
        worst = 0
        for j in range(1, lookahead + 1):
            idx = entry_idx + j - 1
            if idx >= n:
                break
            ch = rows[idx][2]
            cl = rows[idx][3]
            if direction == 'SHORT':
                mf = (entry_price - cl) / entry_price * 100
                ma = (entry_price - ch) / entry_price * 100
            else:
                mf = (ch - entry_price) / entry_price * 100
                ma = (cl - entry_price) / entry_price * 100
            best = max(best, mf)
            worst = min(worst, ma)

        # EMA slope
        ema_slope = (ema[i] - ema[max(0, i-20)]) / ema[max(0, i-20)] * 100 if i >= 20 else 0

        # RSI
        rsi = None
        if i >= 15:
            deltas = [closes[j] - closes[j-1] for j in range(i-13, i+1)]
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]
            ag = sum(gains) / 14
            al = sum(losses) / 14
            rsi = 100 - (100 / (1 + ag / al)) if al > 0 else 100.0

        # Consecutive candles on approach side
        consec = 0
        for k in range(i, max(i-50, 300), -1):
            if direction == 'SHORT' and closes[k] > ema[k]:
                consec += 1
            elif direction == 'LONG' and closes[k] < ema[k]:
                consec += 1
            else:
                break

        results.append({
            'token': token,
            'direction': direction,
            'wick_ratio': wick_ratio,
            'pre_move_pct': pre_move,
            'ema_slope': ema_slope,
            'rsi': rsi,
            'consec': consec,
            'pnl_pct': pnl,
            'win': pnl > 0,
            'mfe': best,
            'mae': worst,
        })

    return results


def analyze(results, label):
    if not results:
        print(f"  [{label}] No signals found")
        return 0, 0

    total = len(results)
    wins = sum(1 for r in results if r['win'])
    wr = wins / total * 100
    avg_pnl = sum(r['pnl_pct'] for r in results) / total
    avg_win = sum(r['pnl_pct'] for r in results if r['win']) / max(1, wins)
    avg_loss = sum(r['pnl_pct'] for r in results if not r['win']) / max(1, total - wins)

    longs = [r for r in results if r['direction'] == 'LONG']
    shorts = [r for r in results if r['direction'] == 'SHORT']

    print(f"\n{'='*70}")
    print(f"  {label} RESULTS")
    print(f"{'='*70}")
    print(f"  Total: {total} signals | WR: {wr:.1f}% ({wins}W/{total-wins}L)")
    print(f"  Avg PnL: {avg_pnl:+.4f}% | Avg win: {avg_win:+.4f}% | Avg loss: {avg_loss:+.4f}%")
    print(f"  LONG: {len(longs)} ({sum(1 for r in longs if r['win'])/max(1,len(longs))*100:.1f}% WR)")
    print(f"  SHORT: {len(shorts)} ({sum(1 for r in shorts if r['win'])/max(1,len(shorts))*100:.1f}% WR)")

    # Wick ratio buckets
    print(f"\n  --- Wick Ratio Buckets ---")
    for lo, hi, lbl in [(0.30,0.40,'30-40%'),(0.40,0.50,'40-50%'),(0.50,0.60,'50-60%'),(0.60,0.70,'60-70%'),(0.70,1.01,'70%+')]:
        s = [r for r in results if lo <= r['wick_ratio'] < hi]
        if not s: continue
        w = sum(1 for r in s if r['win'])
        print(f"    Wick {lbl:8s}: {len(s):4d} signals, WR={w/len(s)*100:.1f}%, AvgPnL={sum(r['pnl_pct'] for r in s)/len(s):+.4f}%")

    # Pre-move buckets
    print(f"\n  --- Pre-Move Buckets ---")
    for lo, hi, lbl in [(0,0.5,'<0.5%'),(0.5,1,'0.5-1%'),(1,2,'1-2%'),(2,5,'2-5%'),(5,100,'5%+')]:
        s = [r for r in results if lo <= r['pre_move_pct'] < hi]
        if not s: continue
        w = sum(1 for r in s if r['win'])
        print(f"    PreMove {lbl:8s}: {len(s):4d} signals, WR={w/len(s)*100:.1f}%, AvgPnL={sum(r['pnl_pct'] for r in s)/len(s):+.4f}%")

    # EMA slope
    print(f"\n  --- EMA Slope ---")
    for lo, hi, lbl in [(-100,-0.05,'Strong neg'),(-0.05,-0.01,'Weak neg'),(-0.01,0.01,'Flat'),(0.01,0.05,'Weak pos'),(0.05,100,'Strong pos')]:
        s = [r for r in results if lo <= r['ema_slope'] < hi]
        if not s: continue
        w = sum(1 for r in s if r['win'])
        print(f"    Slope {lbl:12s}: {len(s):4d} signals, WR={w/len(s)*100:.1f}%, AvgPnL={sum(r['pnl_pct'] for r in s)/len(s):+.4f}%")

    # RSI
    print(f"\n  --- RSI ---")
    for lo, hi, lbl in [(0,30,'<30'),(30,40,'30-40'),(40,50,'40-50'),(50,60,'50-60'),(60,70,'60-70'),(70,101,'>70')]:
        s = [r for r in results if r['rsi'] is not None and lo <= r['rsi'] < hi]
        if not s: continue
        w = sum(1 for r in s if r['win'])
        print(f"    RSI {lbl:10s}: {len(s):4d} signals, WR={w/len(s)*100:.1f}%, AvgPnL={sum(r['pnl_pct'] for r in s)/len(s):+.4f}%")

    # Consecutive
    print(f"\n  --- Consecutive Candles ---")
    for lo, hi, lbl in [(0,5,'0-4'),(5,10,'5-9'),(10,20,'10-19'),(20,50,'20-49'),(50,1000,'50+')]:
        s = [r for r in results if lo <= r['consec'] < hi]
        if not s: continue
        w = sum(1 for r in s if r['win'])
        print(f"    Consec {lbl:8s}: {len(s):4d} signals, WR={w/len(s)*100:.1f}%, AvgPnL={sum(r['pnl_pct'] for r in s)/len(s):+.4f}%")

    # Combo filters
    print(f"\n  --- Combo Filters ---")
    c1 = [r for r in results if r['wick_ratio'] >= 0.50 and r['ema_slope'] < -0.01]
    if c1:
        w = sum(1 for r in c1 if r['win'])
        print(f"    Wick>50% + Slope<0:     {len(c1):4d}, WR={w/len(c1)*100:.1f}%, PnL={sum(r['pnl_pct'] for r in c1)/len(c1):+.4f}%")

    c2 = [r for r in results if r['wick_ratio'] >= 0.50 and r['pre_move_pct'] < 1.0]
    if c2:
        w = sum(1 for r in c2 if r['win'])
        print(f"    Wick>50% + PreMove<1%:  {len(c2):4d}, WR={w/len(c2)*100:.1f}%, PnL={sum(r['pnl_pct'] for r in c2)/len(c2):+.4f}%")

    c3 = [r for r in results if r['wick_ratio'] >= 0.40 and r['pre_move_pct'] < 1.0]
    if c3:
        w = sum(1 for r in c3 if r['win'])
        print(f"    Wick>40% + PreMove<1%:  {len(c3):4d}, WR={w/len(c3)*100:.1f}%, PnL={sum(r['pnl_pct'] for r in c3)/len(c3):+.4f}%")

    c4 = [r for r in results if r['pre_move_pct'] > 2.0 and r['wick_ratio'] >= 0.40]
    if c4:
        w = sum(1 for r in c4 if r['win'])
        print(f"    PreMove>2% + Wick>40%:  {len(c4):4d}, WR={w/len(c4)*100:.1f}%, PnL={sum(r['pnl_pct'] for r in c4)/len(c4):+.4f}%")

    # MFE analysis
    print(f"\n  --- MFE / MAE ---")
    print(f"    Avg MFE: {sum(r['mfe'] for r in results)/len(results):+.4f}%")
    print(f"    Avg MAE: {sum(r['mae'] for r in results)/len(results):+.4f}%")

    return wr, avg_pnl


if __name__ == '__main__':
    t0 = time.time()

    # Get top 15 tokens by data availability
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    tokens_15m = [r[0] for r in conn.execute(
        "SELECT token, COUNT(*) as cnt FROM candles_15m "
        "WHERE token != 'BTC' GROUP BY token HAVING cnt >= 1000 "
        "ORDER BY cnt DESC LIMIT 15"
    ).fetchall()]
    tokens_1h = [r[0] for r in conn.execute(
        "SELECT token, COUNT(*) as cnt FROM candles_1h "
        "WHERE token != 'BTC' GROUP BY token HAVING cnt >= 1000 "
        "ORDER BY cnt DESC LIMIT 15"
    ).fetchall()]
    conn.close()

    print(f"Tokens (15m): {tokens_15m}")
    print(f"Tokens (1h):  {tokens_1h}")

    # 15m backtest
    all_15m = []
    for t in tokens_15m:
        res = backtest_token(t, 'candles_15m', lookahead=4)
        all_15m.extend(res)
    wr15, pnl15 = analyze(all_15m, "15m (4 candles lookahead = 1 hour)")

    # 1h backtest
    all_1h = []
    for t in tokens_1h:
        res = backtest_token(t, 'candles_1h', lookahead=4)
        all_1h.extend(res)
    wr1h, pnl1h = analyze(all_1h, "1h (4 candles lookahead = 4 hours)")

    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print(f"COMPLETED in {elapsed:.1f}s")
    print(f"15m: {len(all_15m)} signals, WR={wr15:.1f}%, AvgPnL={pnl15:+.4f}%")
    print(f"1h:  {len(all_1h)} signals, WR={wr1h:.1f}%, AvgPnL={pnl1h:+.4f}%")
    print(f"{'='*70}")
