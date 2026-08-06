#!/usr/bin/env python3
"""
backtest_ma100_cross.py — Quick verification backtest for ma_100_cross signal.

Walks through historical 1m candles from candles.db, resamples to 5m,
and fires detect_ma_100_signal at each candle to measure:
  - Signal frequency (signals per day)
  - Direction distribution (LONG vs SHORT)
  - Win rate via simple forward-returns (1h, 2h, 4h)
  - Signal quality (cross distance, ATR%, confidence)

Usage:
  python3 scripts/backtest_ma100_cross.py                     # all tokens with >=2500 candles
  python3 scripts/backtest_ma100_cross.py --tokens BTC ETH    # specific tokens
  python3 scripts/backtest_ma100_cross.py --top 30            # top 30 by candle count
  python3 scripts/backtest_ma100_cross.py --forward-bars 48   # 4h forward return (5m bars)
"""

import sys, os, sqlite3, time, argparse
import numpy as np
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import CANDLES_DB
from signals.ma_100_cross import (
    _resample_5m, _compute_ma, _compute_atr,
    MA_PERIOD, ATR_PERIOD, CROSS_CONFIRM_ATR, MIN_ATR_PCT, REQUIRE_2_CANDLE,
)

# ── CLI ────────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description='ma_100_cross signal backtest')
parser.add_argument('--tokens', nargs='+', default=None)
parser.add_argument('--top', type=int, default=None)
parser.add_argument('--min-candles', type=int, default=2500,
                    help='Min 1m candles required (default: 2500)')
parser.add_argument('--forward-bars', type=int, default=24,
                    help='Forward return horizon in 5m bars (default: 24 = 2h)')
args = parser.parse_args()

FORWARD_BARS = args.forward_bars

# ── Data loading ───────────────────────────────────────────────────────────────

def get_tokens(min_candles, top=None, specific=None):
    conn = sqlite3.connect(CANDLES_DB)
    c = conn.cursor()
    if specific:
        ph = ','.join('?' * len(specific))
        c.execute(f"SELECT token, COUNT(*) as n FROM candles_1m WHERE token IN ({ph}) GROUP BY token ORDER BY n DESC", specific)
    else:
        c.execute("SELECT token, COUNT(*) as n FROM candles_1m GROUP BY token HAVING n >= ? ORDER BY n DESC", (min_candles,))
    rows = c.fetchall()
    conn.close()
    if top:
        rows = rows[:top]
    return [(r[0], r[1]) for r in rows]

def get_closes(token):
    conn = sqlite3.connect(CANDLES_DB)
    c = conn.cursor()
    c.execute("SELECT ts, close FROM candles_1m WHERE token = ? ORDER BY ts ASC", (token.upper(),))
    rows = c.fetchall()
    conn.close()
    return rows  # [(ts, close), ...]

# ── Walk-forward signal detection ──────────────────────────────────────────────

def walk_signals(closes_1m):
    """Walk through 1m closes, resample to 5m windows, detect signals at each 5m boundary."""
    n = len(closes_1m)
    # Need at least 600 1m candles for the signal
    if n < 600:
        return []

    signals = []
    # Walk from the minimum window to the end, stepping by 5m (= 5 1m candles)
    min_start = 600  # signal requires 600 1m candles

    for end_idx in range(min_start, n + 1, 5):
        chunk = closes_1m[:end_idx]
        closes_arr = np.array([c[1] for c in chunk], dtype=np.float64)
        closes_5m = _resample_5m(closes_arr)

        if len(closes_5m) < MA_PERIOD + ATR_PERIOD + 5:
            continue

        ma = _compute_ma(closes_5m, MA_PERIOD)
        atr = _compute_atr(closes_5m, ATR_PERIOD)

        i = len(closes_5m) - 1
        if i < 2:
            continue
        if np.isnan(ma[i]) or np.isnan(atr[i]) or atr[i] <= 0:
            continue
        if np.isnan(ma[i - 1]):
            continue

        current_ma = ma[i]
        current_atr = atr[i]
        current_price = closes_5m[i]
        prev_price = closes_5m[i - 1]
        prev_ma = ma[i - 1]

        atr_pct = current_atr / current_price * 100
        if atr_pct < MIN_ATR_PCT:
            continue

        prev_above = prev_price > prev_ma
        curr_above = current_price > current_ma
        if prev_above == curr_above:
            continue

        if curr_above:
            cross_distance = current_price - current_ma
        else:
            cross_distance = current_ma - current_price

        if cross_distance < current_atr * CROSS_CONFIRM_ATR:
            continue

        if REQUIRE_2_CANDLE and i >= 2:
            prev_prev_price = closes_5m[i - 2]
            prev_prev_ma = ma[i - 2]
            if not np.isnan(prev_prev_ma):
                prev_prev_above = prev_prev_price > prev_prev_ma
                if prev_prev_above == curr_above:
                    continue

        cross_strength = cross_distance / current_atr
        conf = min(85, max(65, int(65 + cross_strength * 10)))
        direction = 'LONG' if curr_above else 'SHORT'
        ts_5m = chunk[-1][0]  # timestamp of last 1m candle in this 5m window

        signals.append({
            'ts': ts_5m,
            'direction': direction,
            'confidence': conf,
            'cross_distance_pct': cross_distance / current_price * 100,
            'atr_pct': atr_pct,
            'price': current_price,
            'ma': current_ma,
        })

    return signals


def forward_returns(closes_1m, signals, forward_bars):
    """Compute forward returns for each signal."""
    for sig in signals:
        ts_sig = sig['ts']
        # Find the index of this ts in closes_1m
        idx = None
        for j, (ts, _) in enumerate(closes_1m):
            if ts >= ts_sig:
                idx = j
                break
        if idx is None:
            sig['fwd_return'] = None
            continue

        fwd_idx = idx + forward_bars * 5  # 5m bars * 5 = 1m candles
        if fwd_idx >= len(closes_1m):
            sig['fwd_return'] = None
            continue

        entry = closes_1m[idx][1]
        exit_ = closes_1m[fwd_idx][1]
        ret = (exit_ - entry) / entry * 100
        if sig['direction'] == 'SHORT':
            ret = -ret
        sig['fwd_return'] = ret

    return signals

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()

    tokens = get_tokens(args.min_candles, top=args.top, specific=args.tokens)
    print(f"[ma100-backtest] Testing {len(tokens)} tokens, forward horizon={FORWARD_BARS} 5m bars ({FORWARD_BARS*5/60:.1f}h)")
    print(f"[ma100-backtest] Using candles.db at {CANDLES_DB}")
    print()

    all_signals = []
    per_token = {}

    for idx, (token, count) in enumerate(tokens):
        closes = get_candles_raw(token)
        if not closes or len(closes) < 600:
            continue

        sigs = walk_signals(closes)
        sigs = forward_returns(closes, sigs, FORWARD_BARS)
        all_signals.extend([(token, s) for s in sigs])

        if sigs:
            per_token[token] = sigs

        if (idx + 1) % 20 == 0:
            print(f"  processed {idx+1}/{len(tokens)} tokens...")

    print(f"\n[ma100-backtest] Total signals: {len(all_signals)}")

    if not all_signals:
        print("No signals found. Check candle data availability.")
        return

    # Direction distribution
    longs = [s for _, s in all_signals if s['direction'] == 'LONG']
    shorts = [s for _, s in all_signals if s['direction'] == 'SHORT']
    print(f"  LONG:  {len(longs)} ({len(longs)/len(all_signals)*100:.1f}%)")
    print(f"  SHORT: {len(shorts)} ({len(shorts)/len(all_signals)*100:.1f}%)")

    # Signal frequency: signals per day per token
    # Estimate time span from first to last signal
    all_ts = [s['ts'] for _, s in all_signals]
    span_days = (max(all_ts) - min(all_ts)) / 86400 if max(all_ts) != min(all_ts) else 1
    n_tokens = len(per_token)
    sigs_per_day_total = len(all_signals) / span_days
    sigs_per_day_per_token = sigs_per_day_total / n_tokens if n_tokens else 0
    print(f"  Time span: {span_days:.1f} days")
    print(f"  Signals/day (total): {sigs_per_day_total:.1f}")
    print(f"  Signals/day/token:   {sigs_per_day_per_token:.2f}")

    # Quality metrics
    cross_dists = [s['cross_distance_pct'] for _, s in all_signals]
    atr_pcts = [s['atr_pct'] for _, s in all_signals]
    confs = [s['confidence'] for _, s in all_signals]
    print(f"\n  Cross distance%: avg={np.mean(cross_dists):.4f}% med={np.median(cross_dists):.4f}%")
    print(f"  ATR%:            avg={np.mean(atr_pcts):.4f}% med={np.median(atr_pcts):.4f}%")
    print(f"  Confidence:      avg={np.mean(confs):.1f} med={np.median(confs):.0f}")

    # Forward returns
    valid = [s for _, s in all_signals if s.get('fwd_return') is not None]
    if valid:
        fwd = [s['fwd_return'] for s in valid]
        wins = [r for r in fwd if r > 0]
        losses = [r for r in fwd if r <= 0]
        wr = len(wins) / len(fwd) * 100 if fwd else 0
        print(f"\n  Forward return ({FORWARD_BARS*5/60:.1f}h):")
        print(f"    WR:   {wr:.1f}% ({len(wins)}W / {len(losses)}L of {len(fwd)} total)")
        print(f"    Avg:  {np.mean(fwd):.4f}%")
        print(f"    Med:  {np.median(fwd):.4f}%")
        print(f"    Sum:  {sum(fwd):.2f}%")

        # Per-direction forward returns
        for d in ('LONG', 'SHORT'):
            d_fwd = [s['fwd_return'] for _, s in all_signals if s['direction'] == d and s.get('fwd_return') is not None]
            if d_fwd:
                d_wins = [r for r in d_fwd if r > 0]
                d_wr = len(d_wins) / len(d_fwd) * 100
                print(f"    {d:5s} WR: {d_wr:.1f}%  avg={np.mean(d_fwd):.4f}%  n={len(d_fwd)}")

    # Sample recent signals
    recent = sorted(all_signals, key=lambda x: x[1]['ts'], reverse=True)[:15]
    print(f"\n  Recent signals (last 15):")
    print(f"  {'Token':<8} {'Dir':>5} {'Conf':>4} {'CrossDist%':>10} {'ATR%':>7} {'Price':>12}")
    print(f"  {'-'*55}")
    for tok, s in recent:
        from datetime import datetime
        ts_str = datetime.utcfromtimestamp(s['ts']).strftime('%m-%d %H:%M')
        print(f"  {tok:<8} {s['direction']:>5} {s['confidence']:>3}% {s['cross_distance_pct']:>9.4f}% "
              f"{s['atr_pct']:>6.4f}% {s['price']:>12.6f}")

    # Per-token summary
    print(f"\n  Per-token signal counts:")
    tok_counts = defaultdict(lambda: {'LONG': 0, 'SHORT': 0})
    for tok, s in all_signals:
        tok_counts[tok][s['direction']] += 1
    sorted_toks = sorted(tok_counts.items(), key=lambda x: sum(x[1].values()), reverse=True)
    for tok, counts in sorted_toks[:20]:
        total = counts['LONG'] + counts['SHORT']
        print(f"    {tok:<10} {total:>4} signals  (L={counts['LONG']} S={counts['SHORT']})")

    elapsed = time.time() - t0
    print(f"\n[ma100-backtest] Done in {elapsed:.1f}s")


def get_candles_raw(token):
    """Raw 1m close data from candles.db."""
    conn = sqlite3.connect(CANDLES_DB)
    c = conn.cursor()
    c.execute("SELECT ts, close FROM candles_1m WHERE token = ? ORDER BY ts ASC", (token.upper(),))
    rows = c.fetchall()
    conn.close()
    return rows


if __name__ == '__main__':
    main()
