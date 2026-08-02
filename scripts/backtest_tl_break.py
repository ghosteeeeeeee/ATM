#!/usr/bin/env python3
"""
backtest_tl_break.py — Backtest tl_break signal improvements.

Tests 4 improvements individually and combined against baseline:
  1. RSI confirmation (RSI > 50 for LONG, < 50 for SHORT)
  2. MACD histogram confirming direction
  3. Breakout candle > 0.5 ATR body
  4. Min 4 bounces (was 3)

Usage:
    python3 backtest_tl_break.py                  # all tokens
    python3 backtest_tl_break.py --token ETH SOL  # specific tokens
    python3 backtest_tl_break.py --verbose         # per-trade details
"""

import sys, os, sqlite3, argparse, time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERMES_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'data')
CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')

# ── Trade simulation params (matching hermes_constants.py) ────────────────────
SL_PCT = 0.005    # 0.5% stop loss
TP_PCT = 0.012    # 1.2% take profit
MAX_HOLD_BARS = 24  # 2h at 5m = 24 candles
LEVERAGE = 5

# ── Tokens to backtest (top by data availability) ─────────────────────────────
DEFAULT_TOKENS = [
    'APEX', 'AZTEC', 'BSV', 'CC', 'GOAT', 'MNT', 'MOODENG', 'PURR',
    'SKR', 'STBL', 'VINE', 'KBONK', 'KFLOKI', 'KLUNC', 'KSHIB',
    'MERL', 'ZORA', 'GRASS', 'MON', 'KNEIRO', 'KPEPE',
]


# ── Data Loading ──────────────────────────────────────────────────────────────

def load_candles_5m(token: str) -> List[dict]:
    """Load all 5m candles for a token, oldest first."""
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


# ── Indicator Helpers ─────────────────────────────────────────────────────────

def compute_rsi(closes: List[float], period: int = 14) -> Optional[float]:
    """Compute RSI(period) from closes."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(0, diff))
        losses.append(max(0, -diff))
    if len(gains) < period:
        return None
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_macd(closes: List[float]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Compute MACD (line, signal, histogram). Returns (macd, signal, hist) or (None, None, None)."""
    if len(closes) < 35:
        return None, None, None
    # EMA helper
    def ema(data, period):
        k = 2 / (period + 1)
        result = [data[0]]
        for i in range(1, len(data)):
            result.append(data[i] * k + result[-1] * (1 - k))
        return result
    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    macd_line = [a - b for a, b in zip(ema12, ema26)]
    signal_line = ema(macd_line, 9)
    histogram = macd_line[-1] - signal_line[-1]
    return macd_line[-1], signal_line[-1], histogram


def compute_atr(candles: List[dict], period: int = 14) -> Optional[float]:
    """Compute ATR(period) from OHLCV candles."""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        h, l, prev_c = candles[i]['high'], candles[i]['low'], candles[i-1]['close']
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        trs.append(tr)
    if len(trs) < period:
        return None
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


# ── Trade Simulation ──────────────────────────────────────────────────────────

def simulate_trade(candles: List[dict], entry_idx: int, direction: str,
                   sl_pct: float = SL_PCT, tp_pct: float = TP_PCT,
                   max_hold: int = MAX_HOLD_BARS) -> Optional[Dict]:
    """Simulate a trade from entry_idx forward. Returns trade result dict or None."""
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
            # Check SL first (worst case: low hits SL)
            if c['low'] <= sl_price:
                return {'result': 'loss', 'pnl_pct': -sl_pct * 100, 'bars': i - entry_idx}
            if c['high'] >= tp_price:
                return {'result': 'win', 'pnl_pct': tp_pct * 100, 'bars': i - entry_idx}
        else:  # SHORT
            if c['high'] >= sl_price:
                return {'result': 'loss', 'pnl_pct': -sl_pct * 100, 'bars': i - entry_idx}
            if c['low'] <= tp_price:
                return {'result': 'win', 'pnl_pct': tp_pct * 100, 'bars': i - entry_idx}

    # Time exit — exit at close of last bar
    exit_price = candles[min(entry_idx + max_hold, len(candles) - 1)]['close']
    if direction == 'LONG':
        pnl = (exit_price - entry_price) / entry_price * 100
    else:
        pnl = (entry_price - exit_price) / entry_price * 100
    return {'result': 'win' if pnl > 0 else 'loss', 'pnl_pct': pnl, 'bars': max_hold}


# ── Baseline tl_break Detection (exact copy from tl_break.py) ────────────────

def _linear_regression(closes):
    n = len(closes)
    if n < 2:
        return 0.0, (sum(closes)/n) if closes else 0.0, 0.0
    sx = sum(range(n)); sy = sum(closes)
    sxy = sum(i*c for i,c in enumerate(closes))
    sx2 = sum(i*i for i in range(n))
    d = n*sx2 - sx*sx
    if abs(d) < 1e-10:
        return 0.0, sy/n, 0.0
    slope = (n*sxy - sx*sy) / d
    intercept = (sy - slope*sx) / n
    mean_y = sy/n
    ss_tot = sum((y-mean_y)**2 for y in closes)
    ss_res = sum((closes[i]-(intercept+slope*i))**2 for i in range(n))
    r2 = max(0.0, 1.0 - ss_res/ss_tot) if ss_tot > 0 else 0.0
    return slope, intercept, r2


def _atr_raw(closes, period=14):
    if len(closes) < period+1:
        return None
    trs = []
    for i in range(1, len(closes)):
        diff = abs(closes[i] - closes[i-1])
        trs.append(diff)
    if len(trs) < period:
        return None
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr*(period-1) + tr) / period
    return atr


def detect_tl_break_baseline(closes: List[float]) -> Optional[Dict]:
    """Baseline tl_break detection. Returns direction + metadata or None."""
    n = len(closes)
    if n < 70:
        return None

    fit_end = int(n * 0.50)
    if fit_end < 30:
        return None

    # Trendline via linear regression
    slope, intercept, r2 = _linear_regression(closes[:fit_end])
    if r2 < 0.40:
        return None
    avg_price = sum(closes[:fit_end]) / fit_end
    if avg_price <= 0:
        return None
    slope_pct = abs(slope) / avg_price
    if slope_pct < 0.0003:
        return None

    direction = 'LONG' if slope < 0 else 'SHORT'

    # Bounces
    atr = _atr_raw(closes)
    if atr is None:
        return None
    bounce_thresh = atr * 0.5
    rejection_thresh = atr * 0.25
    bounce_count = 0
    for i in range(fit_end - 1):
        tl_price = slope * i + intercept
        dist = abs(closes[i] - tl_price)
        if dist > bounce_thresh:
            continue
        next_tl = slope * (i+1) + intercept
        next_dist = closes[i+1] - next_tl
        if direction == 'LONG' and next_dist < -rejection_thresh:
            bounce_count += 1
        elif direction == 'SHORT' and next_dist > rejection_thresh:
            bounce_count += 1
    if bounce_count < 3:
        return None
    if bounce_count / fit_end > 0.20:
        return None

    # Z-score filter
    import statistics as _stat
    recent = closes[-20:] if len(closes) >= 20 else closes
    if len(recent) >= 10:
        mean = _stat.mean(recent)
        stdev = _stat.stdev(recent) if len(recent) > 1 else 1
        z = (recent[-1] - mean) / stdev if stdev > 0 else 0
        if direction == 'LONG' and z < -1.5:
            return None
        if direction == 'LONG' and z > 0.5:
            return None
        if direction == 'SHORT' and z > 1.5:
            return None
        if direction == 'SHORT' and z < -0.5:
            return None
    else:
        z = 0

    # Breakout confirmation
    breakout_thresh = atr * 0.8
    breakout_start = fit_end
    breakout_end = min(fit_end + 15, n)
    follow_count = 0
    for i in range(breakout_start, breakout_end):
        tl_price = slope * i + intercept
        if direction == 'LONG' and closes[i] > tl_price + breakout_thresh:
            follow_count += 1
        elif direction == 'SHORT' and closes[i] < tl_price - breakout_thresh:
            follow_count += 1
    if follow_count < 4:
        return None

    # Fakeout guard
    survival_start = fit_end + 15
    survival_end = min(survival_start + 15, n)
    buffer = atr * 0.2
    fakeout = False
    for i in range(survival_start, survival_end):
        tl_price = slope * i + intercept
        if direction == 'LONG' and closes[i] < tl_price - buffer:
            fakeout = True
            break
        elif direction == 'SHORT' and closes[i] > tl_price + buffer:
            fakeout = True
            break
    if fakeout:
        return None

    return {
        'direction': direction,
        'r2': r2,
        'n_bounces': bounce_count,
        'z': z,
        'breakout_follow': follow_count,
    }


# ── Improved Detection (with additional filters) ─────────────────────────────

def detect_tl_break_improved(closes: List[float], candles: List[dict],
                              use_rsi=False, use_macd=False,
                              use_breakout_candle=False, min_bounces=3) -> Optional[Dict]:
    """Improved tl_break with optional filters."""
    n = len(closes)
    if n < 70:
        return None

    fit_end = int(n * 0.50)
    if fit_end < 30:
        return None

    slope, intercept, r2 = _linear_regression(closes[:fit_end])
    if r2 < 0.40:
        return None
    avg_price = sum(closes[:fit_end]) / fit_end
    if avg_price <= 0:
        return None
    slope_pct = abs(slope) / avg_price
    if slope_pct < 0.0003:
        return None

    direction = 'LONG' if slope < 0 else 'SHORT'

    atr = _atr_raw(closes)
    if atr is None:
        return None

    # Bounces (with configurable min)
    bounce_thresh = atr * 0.5
    rejection_thresh = atr * 0.25
    bounce_count = 0
    for i in range(fit_end - 1):
        tl_price = slope * i + intercept
        dist = abs(closes[i] - tl_price)
        if dist > bounce_thresh:
            continue
        next_tl = slope * (i+1) + intercept
        next_dist = closes[i+1] - next_tl
        if direction == 'LONG' and next_dist < -rejection_thresh:
            bounce_count += 1
        elif direction == 'SHORT' and next_dist > rejection_thresh:
            bounce_count += 1
    if bounce_count < min_bounces:
        return None
    if bounce_count / fit_end > 0.20:
        return None

    # Z-score filter (same as baseline)
    import statistics as _stat
    recent = closes[-20:] if len(closes) >= 20 else closes
    if len(recent) >= 10:
        mean = _stat.mean(recent)
        stdev = _stat.stdev(recent) if len(recent) > 1 else 1
        z = (recent[-1] - mean) / stdev if stdev > 0 else 0
        if direction == 'LONG' and z < -1.5:
            return None
        if direction == 'LONG' and z > 0.5:
            return None
        if direction == 'SHORT' and z > 1.5:
            return None
        if direction == 'SHORT' and z < -0.5:
            return None
    else:
        z = 0

    # ── IMPROVEMENT 1: RSI confirmation ────────────────────────────────────
    if use_rsi:
        rsi = compute_rsi(closes)
        if rsi is None:
            return None
        if direction == 'LONG' and rsi < 50:
            return None  # RSI below 50 — no bullish momentum
        if direction == 'SHORT' and rsi > 50:
            return None  # RSI above 50 — no bearish momentum
    else:
        rsi = compute_rsi(closes)

    # ── IMPROVEMENT 2: MACD confirmation ───────────────────────────────────
    if use_macd:
        macd_line, signal_line, histogram = compute_macd(closes)
        if histogram is None:
            return None
        if direction == 'LONG' and histogram < 0:
            return None  # MACD histogram negative — no bullish momentum
        if direction == 'SHORT' and histogram > 0:
            return None  # MACD histogram positive — no bearish momentum

    # Breakout confirmation
    breakout_thresh = atr * 0.8
    breakout_start = fit_end
    breakout_end = min(fit_end + 15, n)
    follow_count = 0
    breakout_strength = 0.0

    # ── IMPROVEMENT 3: Breakout candle strength ────────────────────────────
    first_breakout_idx = None
    for i in range(breakout_start, breakout_end):
        tl_price = slope * i + intercept
        if direction == 'LONG' and closes[i] > tl_price + breakout_thresh:
            follow_count += 1
            breakout_strength = max(breakout_strength, (closes[i] - tl_price) / atr)
            if first_breakout_idx is None:
                first_breakout_idx = i
        elif direction == 'SHORT' and closes[i] < tl_price - breakout_thresh:
            follow_count += 1
            breakout_strength = max(breakout_strength, (tl_price - closes[i]) / atr)
            if first_breakout_idx is None:
                first_breakout_idx = i

    if follow_count < 4:
        return None

    if use_breakout_candle and first_breakout_idx is not None:
        # Require breakout candle body > 0.5 ATR
        bc = candles[first_breakout_idx] if first_breakout_idx < len(candles) else None
        if bc:
            body = abs(bc['close'] - bc['open'])
            if body < atr * 0.5:
                return None  # weak breakout candle

    # Fakeout guard
    survival_start = fit_end + 15
    survival_end = min(survival_start + 15, n)
    buffer = atr * 0.2
    fakeout = False
    for i in range(survival_start, survival_end):
        tl_price = slope * i + intercept
        if direction == 'LONG' and closes[i] < tl_price - buffer:
            fakeout = True
            break
        elif direction == 'SHORT' and closes[i] > tl_price + buffer:
            fakeout = True
            break
    if fakeout:
        return None

    return {
        'direction': direction,
        'r2': r2,
        'n_bounces': bounce_count,
        'z': z,
        'breakout_follow': follow_count,
        'breakout_strength': breakout_strength,
        'rsi': rsi if use_rsi else None,
    }


# ── Main Backtest ─────────────────────────────────────────────────────────────

def run_backtest(tokens: List[str], verbose: bool = False):
    """Run backtest across all tokens for baseline and 4 improvements."""
    configs = [
        ('baseline',        {}),
        ('+RSI',            {'use_rsi': True}),
        ('+MACD',           {'use_macd': True}),
        ('+BreakoutCandle', {'use_breakout_candle': True}),
        ('+4Bounces',       {'min_bounces': 4}),
        ('ALL 4',           {'use_rsi': True, 'use_macd': True,
                             'use_breakout_candle': True, 'min_bounces': 4}),
    ]

    results = {name: {'wins': 0, 'losses': 0, 'pnl': [], 'trades': []}
               for name, _ in configs}

    total_candles = 0
    tokens_tested = 0

    for token in tokens:
        candles = load_candles_5m(token)
        if len(candles) < 100:
            continue
        tokens_tested += 1
        closes = [c['close'] for c in candles]
        total_candles += len(candles)

        # Slide window through history
        window = 96  # 8h
        step = 6     # slide every 30min
        last_signal_idx = -999  # cooldown: no re-fire within 36 candles (3h)

        for idx in range(window, len(candles) - MAX_HOLD_BARS - 1, step):
            # Cooldown check
            if idx - last_signal_idx < 36:
                continue

            window_closes = closes[idx - window:idx]
            window_candles = candles[idx - window:idx]

            for name, cfg in configs:
                if name == 'baseline':
                    sig = detect_tl_break_baseline(window_closes)
                else:
                    sig = detect_tl_break_improved(window_closes, window_candles, **cfg)

                if sig is None:
                    continue

                # Simulate trade from next candle
                trade = simulate_trade(candles, idx, sig['direction'])
                if trade is None:
                    continue

                trade['token'] = token
                trade['idx'] = idx
                trade['direction'] = sig['direction']
                trade['ts'] = candles[idx]['ts']

                results[name]['trades'].append(trade)
                if trade['result'] == 'win':
                    results[name]['wins'] += 1
                else:
                    results[name]['losses'] += 1
                results[name]['pnl'].append(trade['pnl_pct'])

                # Only count baseline signal for cooldown
                if name == 'baseline':
                    last_signal_idx = idx

    # ── Print Results ──────────────────────────────────────────────────────
    print(f"\n{'='*80}")
    print(f"TL_BREAK BACKTEST RESULTS")
    print(f"{'='*80}")
    print(f"Tokens: {tokens_tested} | Candles: {total_candles:,} | Period: ~3 months (5m)")
    print(f"SL: {SL_PCT*100:.1f}% | TP: {TP_PCT*100:.1f}% | Max hold: {MAX_HOLD_BARS*5}min | Leverage: {LEVERAGE}x")
    print(f"{'='*80}\n")

    print(f"{'Config':<18s} {'Trades':>7s} {'Wins':>6s} {'Losses':>7s} {'WR%':>6s} "
          f"{'AvgPnL':>8s} {'TotalPnL':>10s} {'MaxDD':>8s} {'ProfitFactor':>12s}")
    print(f"{'-'*18} {'-'*7} {'-'*6} {'-'*7} {'-'*6} {'-'*8} {'-'*10} {'-'*8} {'-'*12}")

    for name, _ in configs:
        r = results[name]
        total = r['wins'] + r['losses']
        if total == 0:
            print(f"{name:<18s} {'0':>7s} {'-':>6s} {'-':>7s} {'-':>6s} {'-':>8s} {'-':>10s} {'-':>8s} {'-':>12s}")
            continue
        wr = r['wins'] / total * 100
        avg_pnl = sum(r['pnl']) / len(r['pnl'])
        total_pnl = sum(r['pnl'])
        # Max drawdown
        peak = 0; dd = 0; cum = 0
        for p in r['pnl']:
            cum += p
            peak = max(peak, cum)
            dd = min(dd, cum - peak)
        # Profit factor
        gross_profit = sum(p for p in r['pnl'] if p > 0)
        gross_loss = abs(sum(p for p in r['pnl'] if p < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        pf_str = f"{pf:.2f}" if pf < 100 else "∞"

        print(f"{name:<18s} {total:>7d} {r['wins']:>6d} {r['losses']:>7d} {wr:>5.1f}% "
              f"{avg_pnl:>+7.3f}% {total_pnl:>+9.2f}% {dd:>+7.2f}% {pf_str:>12s}")

    # ── Improvement deltas ─────────────────────────────────────────────────
    base = results['baseline']
    base_total = base['wins'] + base['losses']
    if base_total > 0:
        base_wr = base['wins'] / base_total * 100
        base_avg = sum(base['pnl']) / len(base['pnl']) if base['pnl'] else 0
        print(f"\n{'IMPROVEMENTS vs BASELINE':}")
        print(f"{'-'*60}")
        for name, _ in configs[1:]:
            r = results[name]
            total = r['wins'] + r['losses']
            if total == 0:
                continue
            wr = r['wins'] / total * 100
            avg = sum(r['pnl']) / len(r['pnl'])
            delta_wr = wr - base_wr
            delta_avg = avg - base_avg
            print(f"  {name:<18s}: WR {delta_wr:+.1f}%  AvgPnL {delta_avg:+.3f}%  "
                  f"({total} trades)")

    # ── Per-token breakdown (verbose) ──────────────────────────────────────
    if verbose:
        print(f"\n{'PER-TOKEN BREAKDOWN (baseline)':}")
        print(f"{'-'*60}")
        token_stats = defaultdict(lambda: {'w': 0, 'l': 0, 'pnl': []})
        for t in base['trades']:
            token_stats[t['token']]['w' if t['result'] == 'win' else 'l'] += 1
            token_stats[t['token']]['pnl'].append(t['pnl_pct'])
        for tok in sorted(token_stats.keys()):
            s = token_stats[tok]
            total = s['w'] + s['l']
            wr = s['w'] / total * 100 if total > 0 else 0
            avg = sum(s['pnl']) / len(s['pnl']) if s['pnl'] else 0
            print(f"  {tok:<12s}: {s['w']}/{total} WR ({wr:.0f}%) AvgPnL={avg:+.3f}%")

    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backtest tl_break improvements')
    parser.add_argument('--token', nargs='*', default=None, help='Specific tokens')
    parser.add_argument('--verbose', action='store_true', help='Per-trade details')
    args = parser.parse_args()

    tokens = args.token if args.token else DEFAULT_TOKENS
    run_backtest(tokens, verbose=args.verbose)
