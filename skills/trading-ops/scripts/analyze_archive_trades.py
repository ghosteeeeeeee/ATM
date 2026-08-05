#!/usr/bin/env python3
"""
Analyze archived trades + cross-reference with signals archive.
Produces: top winners/losers, signal fingerprints, A/B test results by SL variant.

Usage:
    python3 /root/.hermes/skills/trading-ops/scripts/analyze_archive_trades.py
    python3 /root/.hermes/skills/trading-ops/scripts/analyze_archive_trades.py --top 20 --min-pnl 0
"""
import gzip, re, json, os, sys
from datetime import datetime
from collections import defaultdict

ARCHIVE_TRADES = '/root/.hermes/archive/trades'
ARCHIVE_SIGNALS_04 = '/root/.hermes/archive/signals/signals_2026-04.jsonl.gz'
ARCHIVE_SIGNALS_05 = '/root/.hermes/archive/signals/signals_2026-05.jsonl.gz'


def parse_dt(s):
    if not s:
        return None
    s = s.replace('Z', '').replace('+00:00', '')
    s = re.sub(r'\.\d+', '', s)
    try:
        return datetime.fromisoformat(s)
    except:
        return None


def load_signals(gz_path):
    sigs = defaultdict(list)
    if not os.path.exists(gz_path):
        return sigs
    with gzip.open(gz_path, 'rt') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            s = json.loads(line)
            key = (s.get('token'), s.get('direction'))
            sigs[key].append(s)
    return sigs


def load_trades():
    all_trades = []
    for f in sorted(os.listdir(ARCHIVE_TRADES)):
        if not f.endswith('.json'):
            continue
        path = os.path.join(ARCHIVE_TRADES, f)
        try:
            with open(path) as fh:
                d = json.load(fh)
            trades = d.get('trades', [])
            if isinstance(trades, list):
                for t in trades:
                    if isinstance(t, dict) and t.get('pnl_usdt') is not None:
                        all_trades.append(t)
        except Exception as e:
            print(f"  SKIP {f}: {e}", file=sys.stderr)
    return all_trades


def find_signal(token, direction, open_time_str, all_sigs, max_seconds=14400):
    """Find closest signal within window. Returns (signal, diff_seconds)."""
    open_dt = parse_dt(open_time_str)
    if not open_dt:
        return None, None
    key = (token, direction)
    sigs = all_sigs.get(key, [])
    best, best_diff = None, float('inf')
    for s in sigs:
        sig_dt = parse_dt(s.get('created_at', ''))
        if not sig_dt:
            continue
        diff = abs((sig_dt - open_dt).total_seconds())
        if diff < best_diff:
            best_diff, best = diff, s
    return (best, best_diff) if best_diff <= max_seconds else (None, best_diff)


def parse_exp(exp_str):
    if not exp_str:
        return {}
    try:
        if isinstance(exp_str, str) and exp_str.startswith('{'):
            exp = json.loads(exp_str)
        else:
            exp = {}
        parts = {}
        raw = exp.get('experiment', '')
        for part in raw.split('|'):
            if ':' in part:
                k, v = part.split(':', 1)
                parts[k] = v
        for k in ['confidence', 'regime', 'zscore', 'signals', 'rsi', 'macd', 'atr_pct', 'direction']:
            if k in exp:
                parts[k] = exp[k]
        return parts
    except:
        return {}


def main():
    min_pnl = 0
    top_n = 30
    args = sys.argv[1:]
    if '--help' in args or '-h' in args:
        print(__doc__)
        return

    # Load signals
    april = load_signals(ARCHIVE_SIGNALS_04)
    may = load_signals(ARCHIVE_SIGNALS_05)
    all_sigs = defaultdict(list)
    for k, v in april.items():
        all_sigs[k].extend(v)
    for k, v in may.items():
        all_sigs[k].extend(v)
    print(f"Signals: {len(all_sigs)} (token,dir) pairs, {sum(len(v) for v in all_sigs.values())} total")

    # Load trades
    all_trades = load_trades()
    print(f"Trades: {len(all_trades)} loaded")

    # Filter real winners (has experiment, |pnl| < 200, positive)
    real = [
        t for t in all_trades
        if isinstance(t.get('pnl_usdt'), (int, float))
        and t.get('experiment')
        and abs(t['pnl_usdt']) < 200
        and t['pnl_usdt'] > min_pnl
    ]
    winners = sorted(real, key=lambda x: x['pnl_usdt'], reverse=True)[:top_n]
    losers = sorted(real, key=lambda x: x['pnl_usdt'])[:top_n]

    print(f"\n{'='*130}")
    print(f"{'#':>3} {'pnl_usdt':>10} {'pnl_pct':>8} {'token':>8} {'dir':>6} {'open_time':>22} {'Δt':>8} "
          f"{'signal_type':>22} {'z_score':>9} {'rsi':>7} {'conf':>6}")
    print(f"{'='*130}")

    for i, t in enumerate(winners, 1):
        token = t.get('token', '')
        direction = t.get('direction', '')
        open_time = str(t.get('open_time', t.get('created_at', '')))[:22]
        pnl = t.get('pnl_usdt', 0)
        pct = t.get('pnl_pct', 0)
        exp_parts = parse_exp(t.get('experiment', ''))
        sl_var = exp_parts.get('sl-distance-test', '')

        sig, diff_s = find_signal(token, direction, open_time, all_sigs, max_seconds=14400)
        delta = f"{diff_s/3600:.1f}h" if diff_s and diff_s != float('inf') else "?"
        stype = sig.get('signal_type', '?') if sig else 'NO MATCH'
        z = f"{sig.get('z_score', '?')}" if sig else '?'
        rsi = f"{sig.get('rsi_14', '?')}" if sig else '?'
        conf = f"{sig.get('confidence', '?')}" if sig else '?'
        pct_str = f"{float(pct):.2f}%" if isinstance(pct, (int, float)) else '?'
        print(f"{i:>3} {pnl:>10.2f} {pct_str:>8} {token:>8} {direction:>6} {open_time:>22} {delta:>8} "
              f"{stype:>22} {z:>9} {rsi:>7} {conf:>6}  SL={sl_var}")

    # A/B test summary by SL variant
    print(f"\n\n{'='*70}")
    print("WIN RATE BY SL DISTANCE VARIANT")
    print(f"{'='*70}")
    sl_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total_pnl': 0.0})
    for t in real:
        exp_parts = parse_exp(t.get('experiment', ''))
        sl_var = exp_parts.get('sl-distance-test', 'unknown')
        pnl = t['pnl_usdt']
        sl_stats[sl_var]['total_pnl'] += pnl
        if pnl > 0:
            sl_stats[sl_var]['wins'] += 1
        else:
            sl_stats[sl_var]['losses'] += 1

    ranked_sl = sorted(sl_stats.items(), key=lambda x: x[1]['total_pnl'], reverse=True)
    print(f"\n{'SL Variant':30s} {'n':>4} {'W':>4} {'L':>4} {'WR%':>6} {'avg_PNL':>8} {'net_PNL':>10}")
    print("-"*70)
    for var, s in ranked_sl:
        n = s['wins'] + s['losses']
        if n == 0:
            continue
        wr = s['wins'] / n * 100
        avg = s['total_pnl'] / n
        print(f"{var:30s} {n:>4} {s['wins']:>4} {s['losses']:>4} {wr:>5.1f}% {avg:>8.2f} {s['total_pnl']:>10.2f}")


if __name__ == '__main__':
    main()
