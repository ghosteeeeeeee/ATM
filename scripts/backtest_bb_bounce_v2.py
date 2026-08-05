#!/usr/bin/env python3
"""
backtest_bb_bounce_v2.py — Multi-variant backtest for bb_bounce.

Tests 6 parameter sets to find the sweet spot, keeping the AXS +0.65% trade in mind.
That trade was a lower-band touch → bounce → quick profit. Mean reversion at its best.
"""

import sys, os, sqlite3, argparse
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERMES_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'data')
CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')

# ── Trade simulation variants ─────────────────────────────────────────────────
SL_PCTS = [0.005, 0.008, 0.010, 0.012]   # 0.5%, 0.8%, 1.0%, 1.2%
TP_PCTS = [0.008, 0.010, 0.015, 0.020]   # 0.8%, 1.0%, 1.5%, 2.0%
MAX_HOLD = 24  # 2h at 5m

# ── Token list (top by data, fast subset) ─────────────────────────────────────
DEFAULT_TOKENS = [
    'AZTEC', 'BSV', 'CC', 'GOAT', 'MNT', 'MOODENG', 'PURR',
    'SKR', 'STBL', 'VINE', 'KBONK', 'KPEPE', 'AXS',
    'ETH', 'XRP', 'ZORA',
]

# ── Parameter Sets ────────────────────────────────────────────────────────────

PARAM_SETS = {
    'ORIGINAL': {
        'label': 'ORIGINAL (current code)',
        'bb_period': 20, 'bb_stddev': 2.0, 'bb_touch_pct': 0.20,
        'rsi_oversold': 40, 'rsi_overbought': 60,
        'bounce_min_pct': 0.05, 'cooldown_min': 10,
    },
    'LOOSE_V1': {
        'label': 'LOOSE V1 (proposed earlier)',
        'bb_period': 20, 'bb_stddev': 1.8, 'bb_touch_pct': 0.30,
        'rsi_oversold': 45, 'rsi_overbought': 55,
        'bounce_min_pct': 0.03, 'cooldown_min': 5,
    },
    'AGGRESSIVE': {
        'label': 'AGGRESSIVE (max volume)',
        'bb_period': 20, 'bb_stddev': 1.8, 'bb_touch_pct': 0.40,
        'rsi_oversold': 50, 'rsi_overbought': 50,
        'bounce_min_pct': 0.02, 'cooldown_min': 3,
    },
    'TUNED': {
        'label': 'TUNED (bug-hunter fixes)',
        'bb_period': 20, 'bb_stddev': 1.8, 'bb_touch_pct': 0.25,
        'rsi_oversold': 40, 'rsi_overbought': 60,
        'bounce_min_pct': 0.10, 'cooldown_min': 5,
    },
    'RSI_FOCUS': {
        'label': 'RSI FOCUS (tight RSI, wide band)',
        'bb_period': 20, 'bb_stddev': 2.0, 'bb_touch_pct': 0.35,
        'rsi_oversold': 35, 'rsi_overbought': 65,
        'bounce_min_pct': 0.03, 'cooldown_min': 5,
    },
    'SQUEEZE_HUNTER': {
        'label': 'SQUEEZE HUNTER (narrow stddev)',
        'bb_period': 20, 'bb_stddev': 1.5, 'bb_touch_pct': 0.30,
        'rsi_oversold': 45, 'rsi_overbought': 55,
        'bounce_min_pct': 0.03, 'cooldown_min': 5,
    },
    'BALANCED': {
        'label': 'BALANCED (middle ground)',
        'bb_period': 20, 'bb_stddev': 1.8, 'bb_touch_pct': 0.25,
        'rsi_oversold': 42, 'rsi_overbought': 58,
        'bounce_min_pct': 0.04, 'cooldown_min': 7,
    },
}

# Best SL/TP per trade (from the first backtest, mean-reversion favors tighter SL)
DEFAULT_SL = 0.008
DEFAULT_TP = 0.015


# ── Data Loading ──────────────────────────────────────────────────────────────

def load_candles_5m(token: str) -> List[dict]:
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        rows = conn.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_5m WHERE token = ?
            ORDER BY ts ASC
        """, (token.upper(),)).fetchall()
        conn.close()
        if not rows:
            return []
        return [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3],
                 'close': r[4], 'volume': r[5]} for r in rows]
    except Exception:
        return []


def load_candles_1h(token: str) -> List[float]:
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        rows = conn.execute("""
            SELECT close FROM candles_1h WHERE token = ?
            ORDER BY ts ASC
        """, (token.upper(),)).fetchall()
        conn.close()
        return [r[0] for r in rows] if rows else []
    except Exception:
        return []


# ── Indicators ────────────────────────────────────────────────────────────────

def compute_bb(closes, period=20, stddev=2.0):
    if len(closes) < period:
        return None, None, None, None
    window = closes[-period:]
    middle = sum(window) / period
    variance = sum((c - middle) ** 2 for c in window) / period
    std = variance ** 0.5
    upper = middle + stddev * std
    lower = middle - stddev * std
    width = (upper - lower) / middle if middle > 0 else 0
    return middle, upper, lower, width


def compute_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        delta = closes[-i] - closes[-i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains) / len(gains) if gains else 0
    avg_loss = sum(losses) / len(losses) if losses else 0.001
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))


def get_1h_trend(closes_1h):
    if len(closes_1h) < 50:
        return 'NEUTRAL'
    def ema(data, period):
        k = 2 / (period + 1)
        val = data[0]
        for v in data[1:]:
            val = v * k + val * (1 - k)
        return val
    ema20 = ema(closes_1h[-60:], 20)
    ema50 = ema(closes_1h[-60:], 50)
    if ema50 == 0:
        return 'NEUTRAL'
    spread = abs(ema20 - ema50) / ema50 * 100
    if spread < 0.1:
        return 'NEUTRAL'
    return 'BULLISH' if ema20 > ema50 else 'BEARISH'


# ── Signal Detection ──────────────────────────────────────────────────────────

def detect_bb_bounce(closes, closes_1h, params):
    bb_period = params['bb_period']
    bb_stddev = params['bb_stddev']
    touch_pct = params['bb_touch_pct']
    rsi_os = params['rsi_oversold']
    rsi_ob = params['rsi_overbought']
    bounce_min = params['bounce_min_pct']

    if len(closes) < bb_period + 10:
        return None, 0

    middle, upper, lower, width = compute_bb(closes, bb_period, bb_stddev)
    if middle is None:
        return None, 0

    current = closes[-1]
    prev = closes[-2]

    rsi = compute_rsi(closes)
    if rsi is None:
        return None, 0

    trend = get_1h_trend(closes_1h)

    dist_from_lower = abs(current - lower) / lower * 100 if lower > 0 else 999
    dist_from_upper = abs(current - upper) / upper * 100 if upper > 0 else 999

    # LONG
    if dist_from_lower <= touch_pct and current > prev:
        if rsi > rsi_os:
            return None, 0
        if trend == 'BEARISH':
            return None, 0
        if current <= lower:
            return None, 0
        bounce_pct = (current - lower) / lower * 100 if lower > 0 else 0
        if bounce_pct < bounce_min:
            return None, 0
        conf = 65
        if width < 0.03: conf += 10
        if trend != 'NEUTRAL': conf += 5
        if bounce_pct > 0.15: conf += 5
        return 'LONG', min(conf, 88)

    # SHORT
    if dist_from_upper <= touch_pct and current < prev:
        if rsi < rsi_ob:
            return None, 0
        if trend == 'BULLISH':
            return None, 0
        if current >= upper:
            return None, 0
        bounce_pct = (upper - current) / upper * 100 if upper > 0 else 0
        if bounce_pct < bounce_min:
            return None, 0
        conf = 65
        if width < 0.03: conf += 10
        if trend != 'NEUTRAL': conf += 5
        if bounce_pct > 0.15: conf += 5
        return 'SHORT', min(conf, 88)

    return None, 0


# ── Trade Simulation ──────────────────────────────────────────────────────────

def simulate_trade(candles, entry_idx, direction, sl_pct, tp_pct, max_hold=MAX_HOLD):
    entry_price = candles[entry_idx]['close']
    if direction == 'LONG':
        sl_price = entry_price * (1 - sl_pct)
        tp_price = entry_price * (1 + tp_pct)
    else:
        sl_price = entry_price * (1 + sl_pct)
        tp_price = entry_price * (1 - tp_pct)

    for i in range(entry_idx + 1, min(entry_idx + max_hold + 1, len(candles))):
        c = candles[i]
        if direction == 'LONG':
            if c['low'] <= sl_price:
                return {'result': 'loss', 'pnl_pct': -sl_pct * 100, 'bars': i - entry_idx}
            if c['high'] >= tp_price:
                return {'result': 'win', 'pnl_pct': tp_pct * 100, 'bars': i - entry_idx}
        else:
            if c['high'] >= sl_price:
                return {'result': 'loss', 'pnl_pct': -sl_pct * 100, 'bars': i - entry_idx}
            if c['low'] <= tp_price:
                return {'result': 'win', 'pnl_pct': tp_pct * 100, 'bars': i - entry_idx}

    exit_price = candles[min(entry_idx + max_hold, len(candles) - 1)]['close']
    if direction == 'LONG':
        pnl = (exit_price - entry_price) / entry_price * 100
    else:
        pnl = (entry_price - exit_price) / entry_price * 100
    return {'result': 'win' if pnl > 0 else 'loss', 'pnl_pct': pnl, 'bars': max_hold}


# ── Backtest Engine ───────────────────────────────────────────────────────────

def backtest_token(token, candles, closes_1h, params, sl_pct, tp_pct):
    trades = []
    cooldown = 0
    cooldown_min = params['cooldown_min']

    for i in range(30, len(candles)):
        if cooldown > 0:
            cooldown -= 1
            continue

        window = [c['close'] for c in candles[max(0, i - 100):i + 1]]
        direction, conf = detect_bb_bounce(window, closes_1h, params)

        if direction:
            trade = simulate_trade(candles, i, direction, sl_pct, tp_pct)
            if trade:
                trade['token'] = token
                trade['direction'] = direction
                trade['confidence'] = conf
                trades.append(trade)
                cooldown = cooldown_min

    return trades


def run_backtest(tokens, params, sl_pct, tp_pct):
    all_trades = []
    for token in tokens:
        candles = load_candles_5m(token)
        if not candles or len(candles) < 50:
            continue
        closes_1h = load_candles_1h(token)
        trades = backtest_token(token, candles, closes_1h, params, sl_pct, tp_pct)
        all_trades.extend(trades)

    if not all_trades:
        return {'total': 0, 'wins': 0, 'wr': 0, 'pnl': 0, 'avg_pnl': 0,
                'expectancy': 0, 'profit_factor': 0}

    wins = [t for t in all_trades if t['result'] == 'win']
    losses = [t for t in all_trades if t['result'] == 'loss']
    total_pnl = sum(t['pnl_pct'] for t in all_trades)
    win_pnl = sum(t['pnl_pct'] for t in wins)
    loss_pnl = abs(sum(t['pnl_pct'] for t in losses))

    return {
        'total': len(all_trades),
        'wins': len(wins),
        'losses': len(losses),
        'wr': round(100 * len(wins) / len(all_trades), 1),
        'pnl': round(total_pnl, 2),
        'avg_pnl': round(total_pnl / len(all_trades), 3),
        'expectancy': round(total_pnl / len(all_trades), 3),
        'profit_factor': round(win_pnl / loss_pnl, 2) if loss_pnl > 0 else 999,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', nargs='*', help='Specific tokens')
    parser.add_argument('--sl', type=float, default=DEFAULT_SL, help='Stop loss pct')
    parser.add_argument('--tp', type=float, default=DEFAULT_TP, help='Take profit pct')
    args = parser.parse_args()

    tokens = args.token if args.token else DEFAULT_TOKENS
    sl_pct = args.sl
    tp_pct = args.tp

    print(f"bb_bounce multi-variant backtest: {len(tokens)} tokens")
    print(f"SL={sl_pct*100}% TP={tp_pct*100}%\n")

    # Run all parameter sets
    results = {}
    for name, params in PARAM_SETS.items():
        r = run_backtest(tokens, params, sl_pct, tp_pct)
        results[name] = r
        print(f"  {params['label']:45s} trades={r['total']:5d}  WR={r['wr']:5.1f}%  "
              f"PnL={r['pnl']:+8.2f}%  PF={r['profit_factor']:5.2f}")

    # ── Find best per metric ──────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("RANKINGS")
    print("=" * 80)

    by_wr = sorted(results.items(), key=lambda x: x[1]['wr'], reverse=True)
    by_pnl = sorted(results.items(), key=lambda x: x[1]['pnl'], reverse=True)
    by_pf = sorted(results.items(), key=lambda x: x[1]['profit_factor'], reverse=True)
    by_volume = sorted(results.items(), key=lambda x: x[1]['total'], reverse=True)

    print(f"\n  Best WR:        {by_wr[0][0]:15s} {by_wr[0][1]['wr']}%")
    print(f"  Best PnL:       {by_pnl[0][0]:15s} {by_pnl[0][1]['pnl']:+.2f}%")
    print(f"  Best PF:        {by_pf[0][0]:15s} {by_pf[0][1]['profit_factor']}")
    print(f"  Most Volume:    {by_volume[0][0]:15s} {by_volume[0][1]['total']} trades")

    # ── Full comparison table ─────────────────────────────────────────────────
    print(f"\n{'SET':<18} {'TRADES':>7} {'WR':>6} {'PnL':>10} {'AVG':>8} {'PF':>6}")
    print("-" * 60)
    for name, r in results.items():
        print(f"{name:<18} {r['total']:>7} {r['wr']:>5.1f}% {r['pnl']:>+9.2f}% "
              f"{r['avg_pnl']:>+7.3f}% {r['profit_factor']:>5.2f}")

    # ── SL/TP sensitivity for best set ───────────────────────────────────────
    best_name = by_pf[0][0]
    best_params = PARAM_SETS[best_name]
    print(f"\n{'=' * 80}")
    print(f"SL/TP SENSITIVITY for {best_name}")
    print(f"{'=' * 80}")
    print(f"{'SL':>6} {'TP':>6} {'TRADES':>7} {'WR':>6} {'PnL':>10} {'PF':>6}")
    print("-" * 50)

    for sl in [0.005, 0.008, 0.010, 0.012]:
        for tp in [0.010, 0.015, 0.020]:
            r = run_backtest(tokens, best_params, sl, tp)
            marker = " <-- current" if (sl == sl_pct and tp == tp_pct) else ""
            print(f"{sl*100:>5.1f}% {tp*100:>5.1f}% {r['total']:>7} {r['wr']:>5.1f}% "
                  f"{r['pnl']:>+9.2f}% {r['profit_factor']:>5.2f}{marker}")

    # ── Per-token for best set ───────────────────────────────────────────────
    print(f"\n{'=' * 80}")
    print(f"PER-TOKEN BREAKDOWN for {best_name}")
    print(f"{'=' * 80}")
    by_token = defaultdict(lambda: {'w': 0, 'l': 0, 'pnl': 0})
    # Need to re-run to get per-token data
    for token in tokens:
        candles = load_candles_5m(token)
        if not candles or len(candles) < 50:
            continue
        closes_1h = load_candles_1h(token)
        trades = backtest_token(token, candles, closes_1h, best_params, sl_pct, tp_pct)
        for t in trades:
            by_token[token]['w' if t['result'] == 'win' else 'l'] += 1
            by_token[token]['pnl'] += t['pnl_pct']

    print(f"{'TOKEN':<12} {'TRADES':>7} {'WR':>6} {'PnL':>10}")
    print("-" * 40)
    for tok in sorted(by_token.keys()):
        d = by_token[tok]
        total = d['w'] + d['l']
        wr = 100 * d['w'] / total if total else 0
        print(f"{tok:<12} {total:>7} {wr:>5.1f}% {d['pnl']:>+9.2f}%")


if __name__ == '__main__':
    main()
