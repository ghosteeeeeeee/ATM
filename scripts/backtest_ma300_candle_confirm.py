#!/usr/bin/env python3
"""
backtest_ma300_candle_confirm.py — Backtester for MA300 + Candle Confirmation signal.

Signal:
  LONG:  candle[i] closes above EMA(300), candle[i+1] opens AND closes above candle[i]'s body high
  SHORT: candle[i] closes below EMA(300), candle[i+1] opens AND closes below candle[i]'s body low
Entry:  at candle[i+1] close (non-repainting)
Exit:   TP / SL / reverse signal / end-of-data

Usage:
  python3 scripts/backtest_ma300_candle_confirm.py --top 50
  python3 scripts/backtest_ma300_candle_confirm.py --tokens BTC ETH SOL
  python3 scripts/backtest_ma300_candle_confirm.py --min-candles 4000
"""

import sys, os, sqlite3, time, argparse
from collections import defaultdict
from typing import List, Tuple, Optional
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST

# ── CLI args ───────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description='MA300 Candle Confirmation Backtester')
parser.add_argument('--tokens', nargs='+', default=None,
                    help='Specific tokens to test')
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

# ── EMA calculation ───────────────────────────────────────────────────────────

def _ema_series(values: list, period: int) -> list:
    """Compute EMA series — returns EMA value at each index (oldest first).
    None for indices < period-1.
    """
    n = len(values)
    if n < period:
        return [None] * n
    k = 2 / (period + 1)
    result = [None] * (period - 1)
    ema_val = sum(values[:period]) / period
    result.append(ema_val)
    for price in values[period:]:
        ema_val = price * k + ema_val * (1 - k)
        result.append(ema_val)
    return result

# ── DB ─────────────────────────────────────────────────────────────────────────

CANDLES_DB = '/root/.hermes/data/candles.db'

@dataclass
class TradeResult:
    direction: str
    entry_price: float
    exit_price: float
    pnl_pct: float
    bars_held: int
    exit_reason: str     # 'tp' | 'sl' | 'reverse' | 'end'
    token: str
    confidence: int
    body_ratio: float   # body_next / body_i (momentum strength)
    ma_sep_pct: float   # |close_i - ema_val| / entry_price * 100

@dataclass
class Stats:
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
    pnl_by_token: dict = field(default_factory=dict)

def get_tokens(min_candles=3000, top=None, specific=None):
    conn = sqlite3.connect(CANDLES_DB)
    c = conn.cursor()
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
        c.execute("SELECT token, COUNT(*) as n FROM candles_1m GROUP BY token HAVING n >= ? ORDER BY n DESC", (min_candles,))
    rows = c.fetchall()
    conn.close()
    if top:
        rows = rows[:top]
    return [r[0] for r in rows]

def get_candles(token: str, limit=None) -> List[dict]:
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

def find_signals(candles: List[dict], sl_pct: float, tp_pct: float,
                 direction_filter: str = 'both') -> List[TradeResult]:
    """Find MA300 + candle confirmation signals and simulate trades."""
    n = len(candles)
    if n < 302:
        return []

    closes = [c['close'] for c in candles]
    ema300 = _ema_series(closes, 300)

    results = []

    # Valid start: index 299 (first candle where EMA is valid) to n-2 (need i and i+1)
    for i in range(299, n - 1):
        c_i    = candles[i]
        c_next = candles[i + 1]

        ema_val = ema300[i]
        if ema_val is None:
            continue

        body_high_i = max(c_i['open'], c_i['close'])
        body_low_i  = min(c_i['open'], c_i['close'])
        body_i      = body_high_i - body_low_i

        ma_sep_pct = abs(c_i['close'] - ema_val) / c_i['close'] * 100.0

        direction = None

        # LONG: candle[i] closes above EMA, candle[i+1] opens AND closes above body high
        if c_i['close'] > ema_val:
            if c_next['open'] > body_high_i and c_next['close'] > body_high_i:
                direction = 'LONG'

        # SHORT: candle[i] closes below EMA, candle[i+1] opens AND closes below body low
        elif c_i['close'] < ema_val:
            if c_next['open'] < body_low_i and c_next['close'] < body_low_i:
                direction = 'SHORT'

        if direction is None:
            continue
        if direction_filter != 'both' and direction_filter != direction.lower():
            continue

        # Entry at candle[i+1] close
        entry_price = c_next['close']
        entry_bar   = i + 1

        body_next       = abs(c_next['close'] - c_next['open'])
        body_ratio      = body_next / body_i if body_i > 0 else 0.0

        if direction == 'LONG':
            sl = entry_price * (1 - sl_pct / 100)
            tp = entry_price * (1 + tp_pct / 100)
        else:
            sl = entry_price * (1 + sl_pct / 100)
            tp = entry_price * (1 - tp_pct / 100)

        exit_reason = None
        exit_price  = None
        exit_bar    = entry_bar

        for j in range(entry_bar + 1, n):
            high_j = candles[j]['high']
            low_j  = candles[j]['low']

            if direction == 'LONG':
                if low_j <= sl:
                    exit_reason = 'sl'
                    exit_price  = sl
                    exit_bar    = j
                    break
                elif high_j >= tp:
                    exit_reason = 'tp'
                    exit_price  = tp
                    exit_bar    = j
                    break
            else:  # SHORT
                if high_j >= sl:
                    exit_reason = 'sl'
                    exit_price  = sl
                    exit_bar    = j
                    break
                elif low_j <= tp:
                    exit_reason = 'tp'
                    exit_price  = tp
                    exit_bar    = j
                    break

            # Reverse signal check (candle[j] closes through EMA)
            ema_j = ema300[j]
            if ema_j is not None:
                if direction == 'LONG' and candles[j]['close'] < ema_j:
                    exit_reason = 'reverse'
                    exit_price  = candles[j]['close']
                    exit_bar    = j
                    break
                elif direction == 'SHORT' and candles[j]['close'] > ema_j:
                    exit_reason = 'reverse'
                    exit_price  = candles[j]['close']
                    exit_bar    = j
                    break

        if exit_reason is None:
            exit_reason = 'end'
            exit_price  = closes[-1]
            exit_bar    = n - 1

        pnl = (exit_price - entry_price) / entry_price * 100.0
        if direction == 'SHORT':
            pnl = -pnl

        # Confidence
        conf = 65
        if body_ratio > 1.5:
            conf += 10
        if ma_sep_pct > 1.5:
            conf += 8
        conf = min(88, max(50, conf))

        results.append(TradeResult(
            direction=direction,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl_pct=pnl,
            bars_held=exit_bar - entry_bar,
            exit_reason=exit_reason,
            token='',
            confidence=conf,
            body_ratio=round(body_ratio, 3),
            ma_sep_pct=round(ma_sep_pct, 3),
        ))

    return results

def compute_stats(results: List[TradeResult], token: str = '') -> Stats:
    s = Stats()
    tok_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0.0})

    # Use the token parameter as the canonical key, not r.token (which may differ
    # between per-token aggregation and flat aggregation)
    key = token if token else (getattr(results[0], 'token', '') if results else '')

    for r in results:
        s.n_signals += 1

        if r.exit_reason == 'tp':
            s.n_wins += 1
            tok_stats[key]['wins'] += 1
        elif r.exit_reason == 'sl':
            s.n_losses += 1
            tok_stats[key]['losses'] += 1
        elif r.exit_reason == 'reverse':
            s.n_reverse += 1
            if r.pnl_pct > 0:
                s.n_wins += 0.5
                tok_stats[key]['wins'] += 0.5
            else:
                s.n_losses += 0.5
                tok_stats[key]['losses'] += 0.5
        else:  # end
            s.n_end += 1
            if r.pnl_pct > 0:
                s.n_wins += 1
                tok_stats[key]['wins'] += 1
            else:
                s.n_losses += 1
                tok_stats[key]['losses'] += 1

        s.total_pnl += r.pnl_pct
        tok_stats[key]['pnl'] += r.pnl_pct

    if s.n_wins + s.n_losses > 0:
        s.win_rate = s.n_wins / (s.n_wins + s.n_losses) * 100.0

    wins   = [r.pnl_pct for r in results if r.exit_reason == 'tp']
    losses = [r.pnl_pct for r in results if r.exit_reason == 'sl']
    s.avg_win  = sum(wins)   / len(wins)   if wins   else 0.0
    s.avg_loss = sum(losses) / len(losses) if losses else 0.0

    bars = [r.bars_held for r in results]
    s.avg_bars = sum(bars) / len(bars) if bars else 0.0

    for tok, st in tok_stats.items():
        total = st['wins'] + st['losses']
        if total > 0:
            s.wr_by_token[tok]   = st['wins'] / total * 100.0
            s.pnl_by_token[tok] = st['pnl']

    return s

# ── SL/TP sweep combos ─────────────────────────────────────────────────────────

SL_TP_COMBOS = [
    (0.50, 0.75),
    (0.75, 1.00),
    (0.75, 1.50),
    (1.00, 1.50),
    (1.00, 2.00),
]

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    tokens = get_tokens(min_candles=args.min_candles, top=args.top, specific=args.tokens)
    print(f"[backtest] MA300 Candle Confirmation | SL={args.sl_pct}% TP={args.tp_pct}% | "
          f"{len(tokens)} tokens | filter={args.signal_type}")

    # Load candles
    print("[backtest] Loading candles...")
    cache = {}
    for idx, token in enumerate(tokens):
        if token.upper() in SHORT_BLACKLIST or token.upper() in LONG_BLACKLIST:
            continue
        c = get_candles(token)
        if c:
            cache[token] = c
        if (idx + 1) % 20 == 0:
            print(f"  loaded {idx+1}/{len(tokens)}...")

    print(f"[backtest] Loaded {len(cache)} tokens | {args.min_candles}+ candles each")
    print()

    # ── Full results table (default SL/TP) ─────────────────────────────────────
    all_token_results = {}
    for token, candles in cache.items():
        results = find_signals(candles, args.sl_pct, args.tp_pct, args.signal_type)
        all_token_results[token] = results

    # Flatten
    flat = []
    for token, results in all_token_results.items():
        for r in results:
            r.token = token
            flat.append(r)

    s_all = compute_stats(flat)
    print(f"TOTAL  n={s_all.n_signals:>5}  WR={s_all.win_rate:>5.1f}%  "
          f"AvgWin={s_all.avg_win:>6.2f}%  AvgLoss={s_all.avg_loss:>7.2f}%  "
          f"PnL={s_all.total_pnl:>7.2f}%  AvgBars={s_all.avg_bars:>5.1f}")
    print()

    # ── Exit reason breakdown ──────────────────────────────────────────────────
    for reason in ('tp', 'sl', 'reverse', 'end'):
        cnt = len([r for r in flat if r.exit_reason == reason])
        avg = sum(r.pnl_pct for r in flat if r.exit_reason == reason) / cnt if cnt > 0 else 0
        print(f"  {reason:>8}: n={cnt:>4}  avg_pnl={avg:>7.2f}%")
    print()

    # ── Direction breakdown ───────────────────────────────────────────────────
    for d in ('LONG', 'SHORT'):
        sub = [r for r in flat if r.direction == d]
        if not sub:
            continue
        wr = len([r for r in sub if r.pnl_pct > 0]) / len(sub) * 100
        avg = sum(r.pnl_pct for r in sub) / len(sub)
        print(f"  {d}: n={len(sub):>4}  WR={wr:>5.1f}%  avg_pnl={avg:>7.2f}%")
    print()

    # ── SL/TP sweep ──────────────────────────────────────────────────────────
    print("=" * 90)
    print(f"{'SL%':>5} {'TP%':>5} {'Signals':>8} {'WinRate':>8} {'AvgWin%':>8} {'AvgLoss%':>9} {'PnL%':>8}")
    print("-" * 90)
    for sl_pct, tp_pct in SL_TP_COMBOS:
        results_sweep = []
        for token, candles in cache.items():
            results_sweep.extend(find_signals(candles, sl_pct, tp_pct, args.signal_type))
        if not results_sweep:
            continue
        ws = compute_stats(results_sweep)
        marker = " ← DEFAULT" if (sl_pct == args.sl_pct and tp_pct == args.tp_pct) else ""
        print(f"  {sl_pct:>4.2f} {tp_pct:>5.2f} {ws.n_signals:>8} {ws.win_rate:>7.1f}% "
              f"{ws.avg_win:>7.2f}% {ws.avg_loss:>8.2f}% {ws.total_pnl:>7.2f}%{marker}")
    print()

    # ── Per-token WR (default SL/TP) ──────────────────────────────────────────
    print("=" * 60)
    print("Per-token WR (min 5 signals):")
    print("-" * 60)
    token_stats = [(tok, wr, n, pnl)
                   for tok, wr, n, pnl in
                   [(tok, s.wr_by_token.get(tok, 0), len(results), s.pnl_by_token.get(tok, 0))
                    for tok, results in all_token_results.items()
                    for s in [compute_stats(results)]]  # compute once, read both dicts
                   if n >= 5]
    token_stats.sort(key=lambda x: -x[1])
    for tok, wr, n, pnl in token_stats:
        print(f"  {tok:<10} WR={wr:>5.1f}%  n={n:>4}  PnL={pnl:>7.2f}%")
    print()

    # ── Top/bottom tokens by PnL ──────────────────────────────────────────────
    sorted_by_pnl = sorted(token_stats, key=lambda x: -x[3])
    print("TOP 5 by PnL:")
    for tok, wr, n, pnl in sorted_by_pnl[:5]:
        print(f"  {tok:<10} PnL={pnl:>7.2f}%  WR={wr:>5.1f}%  n={n}")
    print()
    print("BOTTOM 5 by PnL:")
    for tok, wr, n, pnl in sorted_by_pnl[-5:]:
        print(f"  {tok:<10} PnL={pnl:>7.2f}%  WR={wr:>5.1f}%  n={n}")
    print()

    elapsed = time.time() - t0
    print(f"[backtest] Done in {elapsed:.1f}s")

    # CSV
    if args.output:
        import csv
        with open(args.output, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['token', 'direction', 'exit_reason', 'pnl_pct', 'bars_held',
                        'confidence', 'body_ratio', 'ma_sep_pct', 'entry_price', 'exit_price'])
            for r in flat:
                w.writerow([r.token, r.direction, r.exit_reason, round(r.pnl_pct, 4),
                            r.bars_held, r.confidence, r.body_ratio, r.ma_sep_pct,
                            round(r.entry_price, 6), round(r.exit_price, 6)])
        print(f"[backtest] CSV written to {args.output}")

if __name__ == '__main__':
    main()
