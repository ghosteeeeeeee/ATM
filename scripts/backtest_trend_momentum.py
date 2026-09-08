#!/usr/bin/env python3
"""
backtest_trend_momentum.py — Fast backtest using pre-computed indicators.

Pre-computes EMA, RSI, ATR, slope, acceleration for the entire series,
then scans for signals in one pass. Much faster than per-bar detection.
"""
import sys, os, sqlite3, time, json
from datetime import datetime
from collections import defaultdict

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

DB_PATH = os.path.join(os.path.dirname(SCRIPTS_DIR), 'data', 'signals_hermes.db')

# ── Parameters ─────────────────────────────────────────────────────────
EMA_FAST = 20
EMA_SLOW = 50
MIN_SLOPE_PCT = 0.0001
ACCEL_LOOKBACK = 10
RSI_PERIOD = 14
RSI_MIN = 35
RSI_MAX = 70
ATR_PERIOD = 14
ATR_MIN_PCT = 0.30
ATR_MAX_PCT = 2.0
CONF_BASE = 65
CONF_CAP = 88
SL_ATR_MULT = 1.5
TP_PCT = 2.5
MAX_HOLD_BARS = 60
COOLDOWN_BARS = 120


# ── Vectorized Indicators ──────────────────────────────────────────────

def compute_ema(prices, period):
    """Returns list of EMA values (None for warmup)."""
    result = [None] * (period - 1)
    k = 2 / (period + 1)
    sma = sum(prices[:period]) / period
    result.append(sma)
    for i in range(period, len(prices)):
        result.append(prices[i] * k + result[-1] * (1 - k))
    return result


def compute_rsi(prices, period=14):
    """Returns list of RSI values."""
    result = [None] * period
    if len(prices) < period + 1:
        return result
    gains, losses = [], []
    for i in range(1, period + 1):
        d = prices[i] - prices[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = sum(gains) / period
    al = sum(losses) / period
    result.append(100 if al == 0 else 100 - 100 / (1 + ag / al))
    for i in range(period + 1, len(prices)):
        d = prices[i] - prices[i-1]
        ag = (ag * (period - 1) + max(d, 0)) / period
        al = (al * (period - 1) + max(-d, 0)) / period
        result.append(100 if al == 0 else 100 - 100 / (1 + ag / al))
    return result


def compute_atr(highs, lows, closes, period=14):
    """Returns list of ATR values."""
    if len(closes) < period + 1:
        return [None] * len(closes)
    trs = []
    for i in range(1, len(closes)):
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
    result = [None] * period
    atr_val = sum(trs[:period]) / period
    result.append(atr_val)
    for i in range(period, len(trs)):
        atr_val = (atr_val * (period - 1) + trs[i]) / period
        result.append(atr_val)
    return result


def compute_slope(values, window=20):
    """Returns per-bar slope (None for warmup or if any None in window)."""
    result = [None] * (window - 1)
    for i in range(window - 1, len(values)):
        v = values[i - window + 1:i + 1]
        if any(x is None for x in v):
            result.append(None)
            continue
        n = len(v)
        xm = (n - 1) / 2.0
        ym = sum(v) / n
        num = sum((j - xm) * (vv - ym) for j, vv in enumerate(v))
        den = sum((j - xm) ** 2 for j in range(n))
        result.append(num / den if den > 0 else 0.0)
    return result


def compute_velocity(prices, lookback):
    """Velocity = price change per bar over lookback window."""
    result = [None] * lookback
    for i in range(lookback, len(prices)):
        if prices[i] is None or prices[i - lookback] is None:
            result.append(None)
        else:
            result.append((prices[i] - prices[i - lookback]) / lookback)
    return result


# ── Backtest Engine ────────────────────────────────────────────────────

def backtest_token(token, prices, timestamps, verbose=False):
    n = len(prices)
    min_bars = max(EMA_SLOW, RSI_PERIOD + 1, ATR_PERIOD + 1, ACCEL_LOOKBACK * 2) + 5
    if n < min_bars + 20:
        return []

    # OHLCV from 1m ticks
    highs = [max(prices[max(0,i-1):min(n,i+2)]) for i in range(n)]
    lows = [min(prices[max(0,i-1):min(n,i+2)]) for i in range(n)]
    closes = list(prices)

    # Pre-compute all indicators
    ema_f = compute_ema(prices, EMA_FAST)
    ema_s = compute_ema(prices, EMA_SLOW)
    rsi_vals = compute_rsi(prices, RSI_PERIOD)
    atr_vals = compute_atr(highs, lows, closes, ATR_PERIOD)
    slopes = compute_slope(ema_f, 20)
    vel_recent = compute_velocity(prices, ACCEL_LOOKBACK)
    vel_prev = compute_velocity(prices, ACCEL_LOOKBACK * 2)

    # Compute acceleration: vel_recent[i] - vel_prev[i] (when both valid)
    accel = [None] * n
    for i in range(ACCEL_LOOKBACK * 2, n):
        if vel_recent[i] is not None and vel_prev[i] is not None:
            accel[i] = vel_recent[i] - vel_prev[i]

    trades = []
    cooldown_until = 0

    for i in range(min_bars, n):
        if i <= cooldown_until:
            continue

        ef = ema_f[i]
        es = ema_s[i]
        rv = rsi_vals[i]
        av = atr_vals[i]
        sl = slopes[i]
        ac = accel[i]

        if None in (ef, es, rv, av, sl, ac):
            continue

        price = prices[i]
        atr_pct = av / price * 100 if price > 0 else 0
        slope_pct = sl / price if price > 0 else 0

        # ── LONG signal ─────────────────────────────────────────────
        if not (price > ef > es):
            continue
        if slope_pct < MIN_SLOPE_PCT:
            continue
        if rv < RSI_MIN or rv > RSI_MAX:
            continue
        if atr_pct < ATR_MIN_PCT or atr_pct > ATR_MAX_PCT:
            continue

        # Score
        score = 0
        reasons = ['ema_aligned']

        slope_q = min(8, int(slope_pct / 0.0002))
        score += slope_q
        reasons.append(f'slope={slope_pct:.5f}')

        if ac > 0:
            score += min(10, int(ac / price * 10000))
            reasons.append(f'accel=+')
        else:
            score += 2
            reasons.append(f'no_accel')

        rsi_bonus = max(0, int((70 - rv) / 10))
        score += rsi_bonus
        reasons.append(f'rsi={rv:.0f}')

        conf = min(CONF_CAP, CONF_BASE + score)

        sl_price = price - av * SL_ATR_MULT
        tp_price = price * (1 + TP_PCT / 100)

        # Simulate trade
        exit_idx = None
        exit_price = None
        exit_reason = None
        for j in range(i + 1, min(i + MAX_HOLD_BARS + 1, n)):
            if lows[j] <= sl_price:
                exit_idx, exit_price, exit_reason = j, sl_price, 'SL'
                break
            if highs[j] >= tp_price:
                exit_idx, exit_price, exit_reason = j, tp_price, 'TP'
                break
        if exit_idx is None:
            exit_idx = min(i + MAX_HOLD_BARS, n - 1)
            exit_price = prices[exit_idx]
            exit_reason = 'TIME'

        pnl_pct = (exit_price - price) / price * 100
        hold = exit_idx - i

        trade = {
            'token': token,
            'entry_time': timestamps[i] if timestamps else i,
            'entry_price': price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason,
            'confidence': conf,
            'hold_bars': hold,
            'atr_pct': atr_pct,
            'slope_pct': slope_pct,
            'has_accel': ac > 0,
            'rsi': rv,
        }
        trades.append(trade)
        cooldown_until = i + COOLDOWN_BARS

        if verbose:
            w = '✅' if pnl_pct > 0 else '❌'
            t_str = datetime.fromtimestamp(timestamps[i]).strftime('%m-%d %H:%M') if timestamps else str(i)
            print(f'  {w} {token} @ {t_str} entry={price:.4f} → {exit_price:.4f} ({pnl_pct:+.2f}%) [{exit_reason}] conf={conf} hold={hold}min')

    return trades


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--tokens', type=str, default=None)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    start_time = time.time()

    # Get tokens
    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()
    cutoff = int(datetime.now().timestamp()) - args.days * 86400

    if args.tokens:
        token_list = [t.strip().upper() for t in args.tokens.split(',')]
    else:
        c.execute("""
            SELECT token, COUNT(*) as cnt FROM price_history
            WHERE timestamp > ? GROUP BY token HAVING cnt >= 500
            ORDER BY cnt DESC LIMIT 25
        """, (cutoff,))
        token_list = [r[0] for r in c.fetchall()]

    print(f'\n{"="*70}')
    print(f'BACKTEST: trend_momentum | {len(token_list)} tokens | {args.days}d | {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print(f'{"="*70}')

    all_trades = []
    token_stats = {}

    for token in token_list:
        c.execute("""
            SELECT price, timestamp FROM price_history
            WHERE token = ? AND timestamp > ? ORDER BY timestamp ASC
        """, (token, cutoff))
        rows = c.fetchall()
        if len(rows) < 200:
            continue

        prices = [r[0] for r in rows]
        timestamps = [r[1] for r in rows]

        trades = backtest_token(token, prices, timestamps, verbose=args.verbose)

        if trades:
            wins = sum(1 for t in trades if t['pnl_pct'] > 0)
            total_pnl = sum(t['pnl_pct'] for t in trades)
            wr = wins / len(trades) * 100
            avg_pnl = total_pnl / len(trades)
            avg_win = sum(t['pnl_pct'] for t in trades if t['pnl_pct'] > 0) / max(1, wins)
            avg_loss = sum(t['pnl_pct'] for t in trades if t['pnl_pct'] <= 0) / max(1, len(trades) - wins)

            token_stats[token] = {
                'trades': len(trades), 'wins': wins, 'losses': len(trades) - wins,
                'wr': round(wr, 1), 'total_pnl': round(total_pnl, 2),
                'avg_pnl': round(avg_pnl, 2), 'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
            }
            print(f'  {token:8s}: {len(trades):3d}T | WR={wr:.0f}% | PnL={total_pnl:+.2f}% | avg={avg_pnl:+.2f}%')

        all_trades.extend(trades)

    conn.close()

    # Summary
    if all_trades:
        wins = sum(1 for t in all_trades if t['pnl_pct'] > 0)
        total_pnl = sum(t['pnl_pct'] for t in all_trades)
        wr = wins / len(all_trades) * 100
        sl = sum(1 for t in all_trades if t['exit_reason'] == 'SL')
        tp = sum(1 for t in all_trades if t['exit_reason'] == 'TP')
        tm = sum(1 for t in all_trades if t['exit_reason'] == 'TIME')
        avg_hold = sum(t['hold_bars'] for t in all_trades) / len(all_trades)

        print(f'\n{"="*70}')
        print(f'SUMMARY: {len(all_trades)} trades | {len(token_stats)} tokens | {time.time()-start_time:.1f}s')
        print(f'{"="*70}')
        print(f'  Win Rate:  {wr:.1f}% ({wins}W / {len(all_trades)-wins}L)')
        print(f'  Total PnL: {total_pnl:+.2f}%')
        print(f'  Avg PnL:   {total_pnl/len(all_trades):+.2f}% per trade')
        print(f'  Exits:     {tp} TP | {sl} SL | {tm} TIME')
        print(f'  Avg Hold:  {avg_hold:.0f} min')

        # With vs without acceleration
        w_a = [t for t in all_trades if t['has_accel']]
        wo_a = [t for t in all_trades if not t['has_accel']]
        if w_a:
            wa_wr = sum(1 for t in w_a if t['pnl_pct'] > 0) / len(w_a) * 100
            wa_pnl = sum(t['pnl_pct'] for t in w_a)
            print(f'\n  With accel:    {len(w_a):3d}T | WR={wa_wr:.0f}% | PnL={wa_pnl:+.2f}%')
        if wo_a:
            wo_wr = sum(1 for t in wo_a if t['pnl_pct'] > 0) / len(wo_a) * 100
            wo_pnl = sum(t['pnl_pct'] for t in wo_a)
            print(f'  Without accel: {len(wo_a):3d}T | WR={wo_wr:.0f}% | PnL={wo_pnl:+.2f}%')

        # Confidence buckets
        print(f'\n  By Confidence:')
        for lo, hi in [(65,70),(70,75),(75,80),(80,85),(85,88)]:
            bt = [t for t in all_trades if lo <= t['confidence'] < hi]
            if bt:
                bwr = sum(1 for t in bt if t['pnl_pct'] > 0) / len(bt) * 100
                bpnl = sum(t['pnl_pct'] for t in bt)
                print(f'    {lo}-{hi}: {len(bt):3d}T | WR={bwr:.0f}% | PnL={bpnl:+.2f}%')

        # Worst trades
        worst = sorted(all_trades, key=lambda t: t['pnl_pct'])[:5]
        print(f'\n  Worst 5:')
        for t in worst:
            ts = datetime.fromtimestamp(t['entry_time']).strftime('%m-%d %H:%M') if isinstance(t['entry_time'], (int, float)) else str(t['entry_time'])
            print(f'    {t["pnl_pct"]:+.2f}% | {t["token"]} @ {ts} | conf={t["confidence"]} hold={t["hold_bars"]}min')

        best = sorted(all_trades, key=lambda t: t['pnl_pct'], reverse=True)[:5]
        print(f'\n  Best 5:')
        for t in best:
            ts = datetime.fromtimestamp(t['entry_time']).strftime('%m-%d %H:%M') if isinstance(t['entry_time'], (int, float)) else str(t['entry_time'])
            print(f'    {t["pnl_pct"]:+.2f}% | {t["token"]} @ {ts} | conf={t["confidence"]} hold={t["hold_bars"]}min')

        # Save
        results = {
            'timestamp': datetime.now().isoformat(),
            'params': {
                'ema_fast': EMA_FAST, 'ema_slow': EMA_SLOW,
                'min_slope_pct': MIN_SLOPE_PCT, 'accel_lookback': ACCEL_LOOKBACK,
                'rsi_min': RSI_MIN, 'rsi_max': RSI_MAX,
                'atr_min_pct': ATR_MIN_PCT, 'atr_max_pct': ATR_MAX_PCT,
                'sl_atr_mult': SL_ATR_MULT, 'tp_pct': TP_PCT,
                'max_hold_bars': MAX_HOLD_BARS, 'cooldown_bars': COOLDOWN_BARS,
            },
            'summary': {
                'total_trades': len(all_trades),
                'tokens_with_signals': len(token_stats),
                'total_pnl': round(total_pnl, 2),
                'win_rate': round(wr, 1),
                'avg_pnl': round(total_pnl / len(all_trades), 2),
            },
            'token_stats': token_stats,
            'trades': all_trades[:300],
        }
        out_path = os.path.join(os.path.dirname(SCRIPTS_DIR), 'plans', 'trend_momentum_backtest.json')
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f'\nResults saved to: {out_path}')
    else:
        print('\n  No signals found across any token.')


if __name__ == '__main__':
    main()
