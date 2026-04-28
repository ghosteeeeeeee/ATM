#!/usr/bin/env python3
"""
backtest_ma_cross.py — EMA Cross Parameter Sweep Backtester

Tests multiple EMA period pairs across tokens on 1m candles.
Measures win rate, avg P&L, signal count, and per-token WR.

Usage:
  python3 scripts/backtest_ma_cross.py                    # all tokens, all combos
  python3 scripts/backtest_ma_cross.py --tokens BTC ETH  # specific tokens
  python3 scripts/backtest_ma_cross.py --top 20           # top 20 by volume/candles
  python3 scripts/backtest_ma_cross.py --min-candles 4000 # tokens with ≥4000 candles
"""

import sys, os, sqlite3, time, argparse
from collections import defaultdict
from typing import List, Tuple, Optional
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST

# ── CLI args ───────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description='EMA Cross Parameter Sweep')
parser.add_argument('--tokens', nargs='+', default=None,
                    help='Specific tokens to test (default: all with enough candles)')
parser.add_argument('--top', type=int, default=None,
                    help='Test top N tokens by candle count')
parser.add_argument('--min-candles', type=int, default=3000,
                    help='Minimum candles required (default: 3000)')
parser.add_argument('--sl-pct', type=float, default=0.75,
                    help='Stop loss %% (default: 0.75)')
parser.add_argument('--tp-pct', type=float, default=1.0,
                    help='Take profit %% (default: 1.0)')
parser.add_argument('--signal-type', default='both',
                    choices=['both', 'long', 'short'],
                    help='Signal direction to test (default: both)')
parser.add_argument('--output', default=None,
                    help='CSV output file for results')
args = parser.parse_args()

# ── EMA combos to sweep ────────────────────────────────────────────────────────
# (fast, slow) pairs — current 10/200 is the baseline
EMA_COMBOS = [
    (5, 50),
    (8, 50),
    (10, 50),
    (10, 100),
    (10, 150),
    (10, 200),   # baseline — current signal
    (12, 26),    # MACD classic
    (12, 50),
    (15, 50),
    (20, 50),
    (20, 100),
    (20, 200),
    (5, 100),
    (8, 100),
    (8, 200),
]

# ── DB ─────────────────────────────────────────────────────────────────────────

CANDLES_DB = '/root/.hermes/data/candles.db'

@dataclass
class TradeResult:
    direction: str       # 'LONG' or 'SHORT'
    entry_price: float
    exit_price: float
    pnl_pct: float
    bars_held: int
    exit_reason: str     # 'tp' | 'sl' | 'reverse' | 'end'
    combo: Tuple[int, int]
    token: str
    confidence: int

@dataclass
class ComboStats:
    fast: int
    slow: int
    n_signals: int = 0
    n_wins: int = 0
    n_losses: int = 0
    n_reverse: int = 0
    n_end: int = 0
    total_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    win_rate: float = 0.0
    avg_bars: float = 0.0
    wr_by_token: dict = field(default_factory=dict)

def get_tokens(min_candles=3000, top=None, specific=None):
    """Get eligible tokens."""
    conn = sqlite3.connect(CANDLES_DB)
    c = conn.cursor()
    query = """
        SELECT token, COUNT(*) as n
        FROM candles_1m
        GROUP BY token
        HAVING n >= ?
        ORDER BY n DESC
    """
    if specific:
        placeholders = ','.join('?' * len(specific))
        query = f"""
            SELECT token, COUNT(*) as n
            FROM candles_1m
            WHERE token IN ({placeholders})
            GROUP BY token
            ORDER BY n DESC
        """
        c.execute(query, specific)
    else:
        c.execute(query, (min_candles,))

    rows = c.fetchall()
    conn.close()

    if top:
        rows = rows[:top]
    return [r[0] for r in rows]

def get_candles(token: str, limit=None) -> List[dict]:
    """Fetch 1m candles for a token (oldest first)."""
    conn = sqlite3.connect(CANDLES_DB)
    c = conn.cursor()
    query = """
        SELECT ts, open, high, low, close, volume
        FROM candles_1m
        WHERE token = ?
        ORDER BY ts ASC
    """
    if limit:
        query += f" LIMIT {limit}"
    c.execute(query, (token.upper(),))
    rows = c.fetchall()
    conn.close()
    return [
        {'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3], 'close': r[4], 'volume': r[5]}
        for r in rows
    ]

def calc_ema_series(closes: List[float], period: int) -> List[Optional[float]]:
    """EMA series — None before warmup, float after."""
    n = len(closes)
    if n < period:
        return [None] * n
    k = 2 / (period + 1)
    result = [None] * (period - 1)
    ema = sum(closes[:period]) / period
    result.append(ema)
    for price in closes[period:]:
        ema = price * k + ema * (1 - k)
        result.append(ema)
    return result

def find_crosses(closes: List[float],
                  ema_fast: List[Optional[float]],
                  ema_slow: List[Optional[float]],
                  fast_p: int, slow_p: int,
                  token: str,
                  sl_pct: float, tp_pct: float,
                  direction_filter: str = 'both') -> List[TradeResult]:
    """Walk through candles, find crosses, simulate trades."""
    n = len(closes)
    results = []

    # Build aligned index: candle_idx -> (ema_fast, ema_slow)
    fast_valid = [(i, ema_fast[i]) for i in range(n) if ema_fast[i] is not None]
    slow_valid = [(i, ema_slow[i]) for i in range(n) if ema_slow[i] is not None]

    if not fast_valid or not slow_valid:
        return results

    # Index by candle number
    fast_by_idx = {i: v for i, v in fast_valid}
    slow_by_idx = {i: v for i, v in slow_valid}
    common = sorted(set(fast_by_idx.keys()) & set(slow_by_idx.keys()))

    if len(common) < 2:
        return results

    i = 1
    while i < len(common):
        idx_prev = common[i - 1]
        idx_cur  = common[i]
        ef_prev  = fast_by_idx[idx_prev]
        ef_cur   = fast_by_idx[idx_cur]
        es_prev  = slow_by_idx[idx_prev]
        es_cur   = slow_by_idx[idx_cur]

        cross_dir = None
        # Golden cross: fast crosses ABOVE slow
        if ef_prev <= es_prev and ef_cur > es_cur:
            cross_dir = 'LONG'
        # Death cross: fast crosses BELOW slow
        elif ef_prev >= es_prev and ef_cur < es_cur:
            cross_dir = 'SHORT'

        if cross_dir and cross_dir != direction_filter == 'short' and direction_filter != 'both':
            pass
        if cross_dir and (direction_filter == 'both' or direction_filter == cross_dir.lower()):
            entry_price = closes[idx_cur]
            in_position = True
            entry_bar = idx_cur

            if cross_dir == 'LONG':
                sl = entry_price * (1 - sl_pct / 100)
                tp = entry_price * (1 + tp_pct / 100)
            else:
                sl = entry_price * (1 + sl_pct / 100)
                tp = entry_price * (1 - tp_pct / 100)

            exit_reason = None
            exit_price = None
            exit_bar = idx_cur

            # Walk forward from cross candle + 1
            for j in range(idx_cur + 1, n):
                high = closes[j]  # use close as proxy; real backtest would use high/low
                low  = closes[j]

                if cross_dir == 'LONG':
                    if low <= sl:
                        exit_reason = 'sl'
                        exit_price = sl
                        exit_bar = j
                        break
                    elif high >= tp:
                        exit_reason = 'tp'
                        exit_price = tp
                        exit_bar = j
                        break
                else:  # SHORT
                    if high >= sl:
                        exit_reason = 'sl'
                        exit_price = sl
                        exit_bar = j
                        break
                    elif low <= tp:
                        exit_reason = 'tp'
                        exit_price = tp
                        exit_bar = j
                        break

                # Check for reverse signal at this candle
                if j in fast_by_idx and j in slow_by_idx:
                    ef_here = fast_by_idx[j]
                    es_here = slow_by_idx[j]
                    if cross_dir == 'LONG' and ef_here <= es_here:
                        exit_reason = 'reverse'
                        exit_price = closes[j]
                        exit_bar = j
                        break
                    elif cross_dir == 'SHORT' and ef_here >= es_here:
                        exit_reason = 'reverse'
                        exit_price = closes[j]
                        exit_bar = j
                        break

            if exit_reason is None:
                exit_reason = 'end'
                exit_price = closes[-1]
                exit_bar = n - 1

            pnl = (exit_price - entry_price) / entry_price * 100
            if cross_dir == 'SHORT':
                pnl = -pnl

            # EMA separation at cross
            sep_pct = abs(ef_cur - es_cur) / entry_price * 100
            recency_bonus = max(0, 10 - (idx_cur - common[i - 1]))
            conf = min(88, int(65 + min(sep_pct * 3, 15) + recency_bonus))

            results.append(TradeResult(
                direction=cross_dir,
                entry_price=entry_price,
                exit_price=exit_price,
                pnl_pct=pnl,
                bars_held=exit_bar - entry_bar,
                exit_reason=exit_reason,
                combo=(fast_p, slow_p),
                token=token,
                confidence=conf,
            ))
        i += 1

    return results

def stats_for_combo(results: List[TradeResult], fp, sp) -> ComboStats:
    s = ComboStats(fast=fp, slow=sp)
    token_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0.0})

    for r in results:
        s.n_signals += 1
        if r.exit_reason == 'tp':
            s.n_wins += 1
            token_stats[r.token]['wins'] += 1
        elif r.exit_reason == 'sl':
            s.n_losses += 1
            token_stats[r.token]['losses'] += 1
        elif r.exit_reason == 'reverse':
            s.n_reverse += 1
            # reverse is neutral-ish: price moved against then reversed
            # treat as partial win if pnl > 0, partial loss if pnl < 0
            if r.pnl_pct > 0:
                s.n_wins += 0.5
            else:
                s.n_losses += 0.5
        else:  # end of data
            s.n_end += 1
            if r.pnl_pct > 0:
                s.n_wins += 1
            else:
                s.n_losses += 1

        s.total_pnl += r.pnl_pct
        token_stats[r.token]['pnl'] += r.pnl_pct

    s.n_signals = len(results)
    if s.n_wins + s.n_losses > 0:
        s.win_rate = s.n_wins / (s.n_wins + s.n_losses) * 100

    wins = [r.pnl_pct for r in results if r.exit_reason == 'tp']
    losses = [r.pnl_pct for r in results if r.exit_reason == 'sl']
    s.avg_win = sum(wins) / len(wins) if wins else 0.0
    s.avg_loss = sum(losses) / len(losses) if losses else 0.0
    bars = [r.bars_held for r in results]
    s.avg_bars = sum(bars) / len(bars) if bars else 0

    # Per-token WR
    for tok, st in token_stats.items():
        total = st['wins'] + st['losses']
        if total > 0:
            s.wr_by_token[tok] = st['wins'] / total * 100

    return s

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    tokens = get_tokens(min_candles=args.min_candles, top=args.top, specific=args.tokens)
    print(f"[backtest] Testing {len(tokens)} tokens, SL={args.sl_pct}%, TP={args.tp_pct}%, "
          f"signal={args.signal_type}")
    print(f"[backtest] EMA combos: {len(EMA_COMBOS)} → {[f'{f}/{s}' for f,s in EMA_COMBOS]}")
    print(f"[backtest] Loading candles...")
    print()

    all_results = {}  # (fp, sp) -> List[TradeResult]

    for combo in EMA_COMBOS:
        fp, sp = combo
        all_results[combo] = []

    # Load candles once per token, then test all combos
    candles_cache = {}
    for idx, token in enumerate(tokens):
        if token.upper() in SHORT_BLACKLIST or token.upper() in LONG_BLACKLIST:
            continue
        candles = get_candles(token)
        if not candles:
            continue
        candles_cache[token] = candles
        if (idx + 1) % 20 == 0:
            print(f"  loaded {idx + 1}/{len(tokens)} tokens...")

    print(f"[backtest] Loaded {len(candles_cache)} tokens")
    print()

    # Run each combo
    for combo in EMA_COMBOS:
        fp, sp = combo
        combo_results = []
        for token, candles in candles_cache.items():
            closes = [c['close'] for c in candles]
            ema_fast = calc_ema_series(closes, fp)
            ema_slow = calc_ema_series(closes, sp)
            trades = find_crosses(
                closes, ema_fast, ema_slow,
                fp, sp, token,
                args.sl_pct, args.tp_pct,
                args.signal_type
            )
            combo_results.extend(trades)
        all_results[combo] = combo_results

    # Compute and print stats
    print()
    print("=" * 100)
    header = (f"{'Combo':>10} {'Signals':>8} {'WinRate':>8} {'AvgWin%':>8} "
              f"{'AvgLoss%':>9} {'P&L%':>8} {'AvgBars':>8} {'TP':>6} {'SL':>6} "
              f"{'Rev':>6} {'End':>6}")
    print(header)
    print("-" * 100)

    rows = []
    for combo in EMA_COMBOS:
        fp, sp = combo
        results = all_results[combo]
        s = stats_for_combo(results, fp, sp)
        rows.append(s)
        if s.n_signals < 5:
            continue
        marker = " ← CURRENT" if (fp, sp) == (10, 200) else ""
        print(
            f"  {fp:>3}/{sp:<4} {s.n_signals:>8} {s.win_rate:>7.1f}% "
            f"{s.avg_win:>7.2f}% {s.avg_loss:>8.2f}% {s.total_pnl:>7.2f}% "
            f"{s.avg_bars:>7.1f}  {int(s.n_wins):>5} {int(s.n_losses):>5} "
            f"{int(s.n_reverse):>5} {int(s.n_end):>5}{marker}"
        )

    # Sort by win rate
    print()
    print("=" * 100)
    print("TOP 10 by Win Rate (min 20 signals):")
    print("-" * 100)
    top10 = sorted(rows, key=lambda x: -x.win_rate if x.n_signals >= 20 else 0)
    for s in top10[:10]:
        if s.n_signals < 20:
            continue
        marker = " ← CURRENT" if (s.fast, s.slow) == (10, 200) else ""
        print(
            f"  {s.fast:>3}/{s.slow:<4} {s.n_signals:>8} {s.win_rate:>7.1f}% "
            f"{s.avg_win:>7.2f}% {s.avg_loss:>8.2f}% {s.total_pnl:>7.2f}% "
            f"{s.avg_bars:>7.1f}  {int(s.n_wins):>5} {int(s.n_losses):>5}{marker}"
        )

    print()
    print("TOP 10 by Total P&L (min 20 signals):")
    print("-" * 100)
    top10pnl = sorted(rows, key=lambda x: -x.total_pnl if x.n_signals >= 20 else 0)
    for s in top10pnl[:10]:
        if s.n_signals < 20:
            continue
        marker = " ← CURRENT" if (s.fast, s.slow) == (10, 200) else ""
        print(
            f"  {s.fast:>3}/{s.slow:<4} {s.n_signals:>8} {s.win_rate:>7.1f}% "
            f"{s.avg_win:>7.2f}% {s.avg_loss:>8.2f}% {s.total_pnl:>7.2f}% "
            f"{s.avg_bars:>7.1f}  {int(s.n_wins):>5} {int(s.n_losses):>5}{marker}"
        )

    # Per-token WR for current combo
    print()
    print("=" * 100)
    print("Per-token Win Rate — current (10/200):")
    print("-" * 60)
    current = all_results[(10, 200)]
    s = stats_for_combo(current, 10, 200)
    sorted_tokens = sorted(s.wr_by_token.items(), key=lambda x: -x[1])
    for tok, wr in sorted_tokens:
        n = len([r for r in current if r.token == tok])
        print(f"  {tok:<10} {wr:>6.1f}% WR  (n={n})")

    elapsed = time.time() - t0
    print()
    print(f"[backtest] Done in {elapsed:.1f}s")

    # CSV output
    if args.output:
        import csv
        with open(args.output, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['fast','slow','n_signals','win_rate','avg_win','avg_loss',
                        'total_pnl','avg_bars','n_wins','n_losses','n_reverse','n_end'])
            for combo in EMA_COMBOS:
                s = stats_for_combo(all_results[combo], combo[0], combo[1])
                w.writerow([s.fast, s.slow, s.n_signals,
                            round(s.win_rate, 2), round(s.avg_win, 4),
                            round(s.avg_loss, 4), round(s.total_pnl, 4),
                            round(s.avg_bars, 2), int(s.n_wins), int(s.n_losses),
                            int(s.n_reverse), int(s.n_end)])
        print(f"[backtest] CSV written to {args.output}")

if __name__ == '__main__':
    main()
