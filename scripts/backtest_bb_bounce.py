#!/usr/bin/env python3
"""
backtest_bb_bounce.py — Backtest bb_bounce signal with current vs proposed params.

Tests whether loosening filters improves win rate and trade volume.

Usage:
    python3 backtest_bb_bounce.py                  # all tokens
    python3 backtest_bb_bounce.py --token AXS ETH  # specific tokens
    python3 backtest_bb_bounce.py --verbose         # per-trade details
"""

import sys, os, sqlite3, argparse
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERMES_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'data')
CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')

# ── Trade simulation params ───────────────────────────────────────────────────
SL_PCT = 0.008    # 0.8% stop loss (matches current ATR_SL_MIN_INIT)
TP_PCT = 0.015    # 1.5% take profit
MAX_HOLD_BARS = 24  # 2h at 5m = 24 candles
LEVERAGE = 5

# ── Token list ────────────────────────────────────────────────────────────────
DEFAULT_TOKENS = [
    'APEX', 'AZTEC', 'BSV', 'CC', 'GOAT', 'MNT', 'MOODENG', 'PURR',
    'SKR', 'STBL', 'VINE', 'KBONK', 'KFLOKI', 'KLUNC', 'KSHIB',
    'MERL', 'ZORA', 'GRASS', 'MON', 'KNEIRO', 'KPEPE', 'AXS',
    'ETH', 'SOL', 'AVAX', 'XRP', 'DOGE', 'PEPE', 'WIF', 'BONK',
]

# ── Parameter Sets ────────────────────────────────────────────────────────────

CURRENT = {
    'bb_period': 20,
    'bb_stddev': 2.0,
    'bb_touch_pct': 0.20,
    'rsi_oversold': 40,
    'rsi_overbought': 60,
    'bounce_min_pct': 0.05,
    'cooldown_min': 10,
    'label': 'CURRENT (tight)',
}

PROPOSED = {
    'bb_period': 20,
    'bb_stddev': 1.8,
    'bb_touch_pct': 0.30,
    'rsi_oversold': 45,
    'rsi_overbought': 55,
    'bounce_min_pct': 0.03,
    'cooldown_min': 5,
    'label': 'PROPOSED (loose)',
}


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

def compute_bb(closes: List[float], period: int = 20, stddev: float = 2.0):
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


def compute_rsi(closes: List[float], period: int = 14) -> Optional[float]:
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


def get_1h_trend(closes_1h: List[float]) -> str:
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

def detect_bb_bounce(closes: List[float], closes_1h: List[float], params: dict):
    """Detect BB bounce signal. Returns (direction, confidence) or (None, 0)."""
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
        if width < 0.03:
            conf += 10
        if trend != 'NEUTRAL':
            conf += 5
        if bounce_pct > 0.15:
            conf += 5
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
        if width < 0.03:
            conf += 10
        if trend != 'NEUTRAL':
            conf += 5
        if bounce_pct > 0.15:
            conf += 5
        return 'SHORT', min(conf, 88)

    return None, 0


# ── Trade Simulation ──────────────────────────────────────────────────────────

def simulate_trade(candles: List[dict], entry_idx: int, direction: str,
                   sl_pct: float = SL_PCT, tp_pct: float = TP_PCT,
                   max_hold: int = MAX_HOLD_BARS) -> Optional[Dict]:
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

def backtest_token(token: str, candles: List[dict], closes_1h: List[float],
                   params: dict, verbose: bool = False) -> List[Dict]:
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
            trade = simulate_trade(candles, i, direction)
            if trade:
                trade['token'] = token
                trade['direction'] = direction
                trade['confidence'] = conf
                trade['entry_ts'] = candles[i]['ts']
                trade['entry_price'] = candles[i]['close']
                trades.append(trade)
                cooldown = cooldown_min  # 5m bars between trades

                if verbose:
                    print(f"  {token} {direction} @ {candles[i]['close']:.4f} "
                          f"conf={conf} -> {trade['result']} pnl={trade['pnl_pct']:+.2f}% "
                          f"({trade['bars']} bars)")

    return trades


def run_backtest(tokens: List[str], params: dict, verbose: bool = False) -> Dict:
    all_trades = []
    for token in tokens:
        candles = load_candles_5m(token)
        if not candles or len(candles) < 50:
            continue
        closes_1h = load_candles_1h(token)
        trades = backtest_token(token, candles, closes_1h, params, verbose)
        all_trades.extend(trades)

    if not all_trades:
        return {'total': 0, 'wins': 0, 'losses': 0, 'wr': 0, 'pnl': 0,
                'avg_pnl': 0, 'trades': [], 'label': params['label']}

    wins = sum(1 for t in all_trades if t['result'] == 'win')
    losses = len(all_trades) - wins
    pnl = sum(t['pnl_pct'] for t in all_trades)
    avg_pnl = pnl / len(all_trades)

    return {
        'total': len(all_trades),
        'wins': wins,
        'losses': losses,
        'wr': round(100 * wins / len(all_trades), 1) if all_trades else 0,
        'pnl': round(pnl, 2),
        'avg_pnl': round(avg_pnl, 3),
        'trades': all_trades,
        'label': params['label'],
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Backtest bb_bounce signal')
    parser.add_argument('--token', nargs='*', help='Specific tokens to test')
    parser.add_argument('--verbose', action='store_true', help='Per-trade output')
    args = parser.parse_args()

    tokens = args.token if args.token else DEFAULT_TOKENS
    verbose = args.verbose

    print(f"Backtesting bb_bounce on {len(tokens)} tokens...")
    print(f"SL={SL_PCT*100}% TP={TP_PCT*100}% MAX_HOLD={MAX_HOLD_BARS}bars LEVERAGE={LEVERAGE}x")
    print()

    # Run both parameter sets
    print("Running CURRENT (tight) params...")
    current = run_backtest(tokens, CURRENT, verbose)
    print()

    print("Running PROPOSED (loose) params...")
    proposed = run_backtest(tokens, PROPOSED, verbose)
    print()

    # Compare
    print("=" * 60)
    print(f"{'METRIC':<25} {'CURRENT':>12} {'PROPOSED':>12} {'DELTA':>10}")
    print("=" * 60)
    print(f"{'Total Trades':<25} {current['total']:>12} {proposed['total']:>12} {proposed['total']-current['total']:>+10}")
    print(f"{'Wins':<25} {current['wins']:>12} {proposed['wins']:>12} {proposed['wins']-current['wins']:>+10}")
    print(f"{'Losses':<25} {current['losses']:>12} {proposed['losses']:>12} {proposed['losses']-current['losses']:>+10}")
    print(f"{'Win Rate':<25} {current['wr']:>11.1f}% {proposed['wr']:>11.1f}% {proposed['wr']-current['wr']:>+9.1f}%")
    print(f"{'Total PnL':<25} {current['pnl']:>11.2f}% {proposed['pnl']:>11.2f}% {proposed['pnl']-current['pnl']:>+9.2f}%")
    print(f"{'Avg PnL/Trade':<25} {current['avg_pnl']:>11.3f}% {proposed['avg_pnl']:>11.3f}% {proposed['avg_pnl']-current['avg_pnl']:>+9.3f}%")
    print("=" * 60)

    # Per-token breakdown
    if verbose:
        print("\nPer-token breakdown:")
        for label, result in [('CURRENT', current), ('PROPOSED', proposed)]:
            by_token = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0})
            for t in result['trades']:
                by_token[t['token']]['wins' if t['result'] == 'win' else 'losses'] += 1
                by_token[t['token']]['pnl'] += t['pnl_pct']
            print(f"\n  {label}:")
            for tok in sorted(by_token.keys()):
                d = by_token[tok]
                total = d['wins'] + d['losses']
                wr = 100 * d['wins'] / total if total else 0
                print(f"    {tok:10s} {total:3d} trades  WR={wr:5.1f}%  PnL={d['pnl']:+.2f}%")

    # Verdict
    print()
    if proposed['wr'] > current['wr'] and proposed['total'] > current['total']:
        print("PROPOSED wins on both volume AND quality.")
    elif proposed['wr'] > current['wr']:
        print("PROPOSED has better win rate but fewer trades.")
    elif proposed['total'] > current['total']:
        print("PROPOSED has more trades but lower win rate.")
    else:
        print("CURRENT params look better. Reconsider proposed changes.")


if __name__ == '__main__':
    main()
