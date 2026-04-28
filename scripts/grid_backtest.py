#!/usr/bin/env python3
"""
Grid Trading Backtest v5 — final with ADX regime filter + realistic sizing
- Only trade when ADX < 25 (no trend / sideways)
- ATR-based range is now correctly implemented (14-period rolling ATR)
- Position sizing: % of current capital, realistic fees
"""

import sqlite3, math, statistics
from datetime import datetime

DB  = '/root/.hermes/data/candles.db'
TF  = 'candles_1h'
TOKENS = ['BTC', 'ETH', 'SOL', 'AVAX', 'ARB', 'APT', 'ORDI', 'TIA', 'OP', 'LINK']
INITIAL_CAPITAL = 1000.0
POSITION_PCT    = 0.20   # 20% of capital per trade
FEE       = 0.0005
SLIPPAGE  = 0.0003
GRID_N    = 10
RANGE_LOOKBACK = 48
ADX_THRESHOLD  = 25      # only trade when ADX < 25

def ema(data, period):
    k = 2 / (period + 1)
    val = sum(data[:period]) / period
    for v in data[period:]:
        val = v * k + val * (1 - k)
    return val

def compute_adx(closes, highs, lows, period=14):
    """Compute ADX using Wilder smoothing."""
    if len(closes) < period * 2 + 1:
        return None
    trs = []
    plus_dm, minus_dm = [], []
    for i in range(1, len(closes)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i-1])
        lc = abs(lows[i] - closes[i-1])
        tr = max(hl, hc, lc)
        plus_dm_val  = max(highs[i] - highs[i-1], 0) if (highs[i] - highs[i-1]) > (lows[i-1] - lows[i]) else 0
        minus_dm_val = max(lows[i-1] - lows[i], 0) if (lows[i-1] - lows[i]) > (highs[i] - highs[i-1]) else 0
        trs.append(tr)
        plus_dm.append(plus_dm_val)
        minus_dm.append(minus_dm_val)

    if len(trs) < period:
        return None

    # Wilder smooth
    def wilder_smooth(vals, period):
        sma = sum(vals[:period]) / period
        result = [sma]
        for v in vals[period:]:
            sma = (sma * (period - 1) + v) / period
            result.append(sma)
        return result

    tr_smooth   = wilder_smooth(trs, period)
    plus_smooth = wilder_smooth(plus_dm, period)
    minus_smooth = wilder_smooth(minus_dm, period)

    di_plus  = [100 * p / t if t > 0 else 0 for p, t in zip(plus_smooth, tr_smooth)]
    di_minus = [100 * m / t if t > 0 else 0 for m, t in zip(minus_smooth, tr_smooth)]

    dx = [100 * abs(a - b) / (a + b) if (a + b) > 0 else 0 for a, b in zip(di_plus, di_minus)]

    if len(dx) < period:
        return None

    adx = ema(dx[-period:], period)
    return adx

def true_range(h, l, pc):
    return max(abs(h - l), abs(h - pc), abs(l - pc))

def fetch_candles(token):
    conn = sqlite3.connect(DB, timeout=10)
    cur  = conn.cursor()
    cur.execute(f"SELECT ts,open,high,low,close,volume FROM {TF} WHERE token=? AND ts>0 ORDER BY ts", (token,))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return None
    return [{'ts':r[0],'open':r[1],'high':r[2],'low':r[3],'close':r[4],'volume':r[5]} for r in rows]

def run_backtest(candles, n_levels, spread_pct, min_adx=ADX_THRESHOLD):
    if len(candles) < 60:
        return None

    opens  = [c['open']  for c in candles]
    highs  = [c['high']  for c in candles]
    lows   = [c['low']   for c in candles]
    closes = [c['close'] for c in candles]

    capital  = INITIAL_CAPITAL
    equity   = [1.0]
    trades   = []
    position = None

    bars = list(zip(opens, highs, lows, closes))

    for i in range(50, len(candles) - 1):
        adx = compute_adx(closes[:i+1], highs[:i+1], lows[:i+1])
        if adx is None:
            continue

        o1, h1, l1, c1 = bars[i+1]
        prev_c = closes[i]

        # ── Skip if trending ──────────────────────────────────────────
        if adx >= min_adx:
            # In trend — skip, but close any open position
            if position is not None:
                exit_p = c1
                pos = position
                size = capital * POSITION_PCT
                if pos['dir'] == 'long':
                    pnl = size * ((exit_p - pos['entry']) / pos['entry'] - 2*FEE - SLIPPAGE)
                else:
                    pnl = size * ((pos['entry'] - exit_p) / pos['entry'] - 2*FEE - SLIPPAGE)
                capital += pnl
                equity.append(equity[-1] + pnl / INITIAL_CAPITAL)
                trades.append({'dir': pos['dir'], 'entry': pos['entry'], 'exit': exit_p,
                               'pnl': pnl, 'type': 'trend_exit'})
                position = None
            continue

        # ── Compute ATR-based range ────────────────────────────────────
        window_trs = [true_range(highs[j], lows[j], closes[j-1])
                      for j in range(i-RANGE_LOOKBACK+1, i+1)]
        if len(window_trs) < 14:
            continue
        atr14 = sum(window_trs[-14:]) / 14.0

        rng_mid  = prev_c
        rng_half = 2.0 * atr14  # ±2× ATR = ~4× ATR total range

        rng_top = rng_mid + rng_half
        rng_bot = rng_mid - rng_half

        step   = (rng_top - rng_bot) / n_levels
        levels = [rng_bot + k * step for k in range(n_levels + 1)]

        # Exit target = entry ± (spread_pct return)
        exit_dist = prev_c * (spread_pct / 100.0)

        # ── Entry ─────────────────────────────────────────────────────
        if position is None:
            for li, lvl in enumerate(levels):
                if l1 <= lvl <= h1:
                    if o1 > lvl:     # opened above, fell through → short
                        position = {'dir': 'short', 'entry': lvl,
                                    'exit': lvl - exit_dist}
                        break
                    else:            # opened at/below, rose through → long
                        position = {'dir': 'long', 'entry': lvl,
                                    'exit': lvl + exit_dist}
                        break

        # ── Exit ──────────────────────────────────────────────────────
        else:
            pos = position
            if pos['dir'] == 'long':
                if h1 >= pos['exit']:
                    pnl = capital * POSITION_PCT * ((pos['exit'] - pos['entry']) / pos['entry'] - 2*FEE - SLIPPAGE)
                    capital += pnl
                    equity.append(equity[-1] + pnl / INITIAL_CAPITAL)
                    trades.append({'dir': 'long', 'entry': pos['entry'], 'exit': pos['exit'],
                                   'pnl': pnl, 'type': 'grid_exit'})
                    position = None
                elif c1 < rng_bot:
                    pnl = capital * POSITION_PCT * ((c1 - pos['entry']) / pos['entry'] - 2*FEE - SLIPPAGE)
                    capital += pnl
                    equity.append(equity[-1] + pnl / INITIAL_CAPITAL)
                    trades.append({'dir': 'long', 'entry': pos['entry'], 'exit': c1,
                                   'pnl': pnl, 'type': 'stop'})
                    position = None
            else:
                if l1 <= pos['exit']:
                    pnl = capital * POSITION_PCT * ((pos['entry'] - pos['exit']) / pos['entry'] - 2*FEE - SLIPPAGE)
                    capital += pnl
                    equity.append(equity[-1] + pnl / INITIAL_CAPITAL)
                    trades.append({'dir': 'short', 'entry': pos['entry'], 'exit': pos['exit'],
                                   'pnl': pnl, 'type': 'grid_exit'})
                    position = None
                elif c1 > rng_top:
                    pnl = capital * POSITION_PCT * ((pos['entry'] - c1) / pos['entry'] - 2*FEE - SLIPPAGE)
                    capital += pnl
                    equity.append(equity[-1] + pnl / INITIAL_CAPITAL)
                    trades.append({'dir': 'short', 'entry': pos['entry'], 'exit': c1,
                                   'pnl': pnl, 'type': 'stop'})
                    position = None

    if not trades:
        return None

    pnls   = [t['pnl'] for t in trades]
    wins   = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    # Max drawdown
    peak, max_dd = equity[0], 0.0
    for v in equity:
        if v > peak: peak = v
        dd = (peak - v) / peak
        if dd > max_dd: max_dd = dd

    n_candles = len(candles) - 50
    years     = n_candles / 8760.0
    total_ret = (capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100.0
    annual_ret = total_ret / years if years > 0 else 0.0

    if len(pnls) > 1 and statistics.stdev(pnls) > 0:
        ret_std  = statistics.stdev(pnls)
        ret_mean = statistics.mean(pnls)
        sharpe   = (ret_mean / ret_std) * math.sqrt(8760.0 / n_candles) if n_candles > 0 else 0.0
    else:
        sharpe = 0.0

    return {
        'total_trades':     len(trades),
        'wins':             len(wins),
        'losses':           len(losses),
        'win_rate':         len(wins) / len(trades) * 100.0,
        'avg_win':          statistics.mean(wins) if wins else 0.0,
        'avg_loss':         statistics.mean(losses) if losses else 0.0,
        'total_return_pct': total_ret,
        'annual_ret_pct':   annual_ret,
        'sharpe':           sharpe,
        'max_drawdown_pct': min(max_dd * 100.0, 100.0),
        'best_trade':       max(pnls),
        'worst_trade':      min(pnls),
        'stop_losses':      sum(1 for t in trades if t.get('type') == 'stop'),
        'grid_exits':       sum(1 for t in trades if t.get('type') == 'grid_exit'),
        'trend_exits':      sum(1 for t in trades if t.get('type') == 'trend_exit'),
        'capital_end':      capital,
    }

# ── Sweep ───────────────────────────────────────────────────────────────────
SPREAD_PCTS = [1.0, 2.0, 3.0, 5.0]

print(f"{'Token':<6} {'N':>2} {'Sp%':>4} {'Trades':>6} {'Win%':>5} "
      f"{'Ret%':>7} {'Ann%':>6} {'Sharpe':>6} {'MaxDD%':>6} "
      f"{'AvgW$':>7} {'AvgL$':>7} {'Stops':>5} {'GridEx':>6}")
print("-" * 100)

all_results = []

for token in TOKENS:
    candles = fetch_candles(token)
    if not candles:
        continue
    for sp in SPREAD_PCTS:
        r = run_backtest(candles, GRID_N, sp)
        if r and r['total_trades'] >= 5:
            print(f"{token:<6} {GRID_N:>2} {sp:>4.1f} "
                  f"{r['total_trades']:>6} {r['win_rate']:>5.1f} "
                  f"{r['total_return_pct']:>7.1f} {r['annual_ret_pct']:>6.1f} "
                  f"{r['sharpe']:>6.2f} {r['max_drawdown_pct']:>6.1f} "
                  f"{r['avg_win']:>7.2f} {r['avg_loss']:>7.2f} "
                  f"{r['stop_losses']:>5} {r['grid_exits']:>6}")
            all_results.append({'token': token, 'n': GRID_N, 'sp': sp, **r})

if all_results:
    best_ret    = max(all_results, key=lambda x: x['total_return_pct'])
    best_sharpe = max(all_results, key=lambda x: x['sharpe'])
    safest_dd   = min(all_results, key=lambda x: x['max_drawdown_pct'])
    most_trades = max(all_results, key=lambda x: x['total_trades'])

    print()
    print("=== TOP PERFORMERS ===")
    sorted_by_ret = sorted(all_results, key=lambda x: x['total_return_pct'], reverse=True)[:5]
    for i, r in enumerate(sorted_by_ret):
        print(f"  {i+1}. {r['token']} Spread={r['sp']}% → Ret={r['total_return_pct']:+.1f}%  "
              f"Ann={r['annual_ret_pct']:+.1f}%  WR={r['win_rate']:.0f}%  "
              f"Sharpe={r['sharpe']:.2f}  MaxDD={r['max_drawdown_pct']:.1f}%  "
              f"Trades={r['total_trades']}")

    print()
    print(f"Best return:  {best_ret['token']} Spread={best_ret['sp']}% → {best_ret['total_return_pct']:+.1f}% total, "
          f"{best_ret['annual_ret_pct']:+.1f}% ann, {best_ret['win_rate']:.0f}% WR")
    print(f"Best Sharpe: {best_sharpe['token']} Spread={best_sharpe['sp']}% → Sharpe={best_sharpe['sharpe']:.2f}, "
          f"{best_sharpe['win_rate']:.0f}% WR, {best_sharpe['total_return_pct']:+.1f}% total")
    print(f"Safest DD:   {safest_dd['token']} Spread={safest_dd['sp']}% → MaxDD={safest_dd['max_drawdown_pct']:.1f}%, "
          f"{safest_dd['total_return_pct']:+.1f}% total")
