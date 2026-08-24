#!/usr/bin/env python3
"""Backtest signal_confluence window sizes — analyze compounding frequency."""
import sqlite3, os, sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

RUNTIME_DB = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')

# Window sizes to test (minutes)
WINDOWS = [10, 15, 20, 25, 30, 40, 50, 60]

# Confluence params
COMPOUND_WEIGHT = 30
SURVIVED_BONUS = 10
RECENCY_BONUS = 5
MIN_COMPOUND = 2
CONFIDENCE_THRESHOLD = 50


def get_signals(days=7):
    """Load signals for the backtest period."""
    conn = sqlite3.connect(RUNTIME_DB, timeout=10)
    conn.row_factory = sqlite3.Row

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    signals = conn.execute("""
        SELECT token, direction, signal_type, source, confidence, price, created_at
        FROM signals
        WHERE created_at > ?
        ORDER BY created_at
    """, (cutoff,)).fetchall()
    conn.close()

    # Parse timestamps
    result = []
    for s in signals:
        d = dict(s)
        try:
            d['_ts'] = datetime.strptime(d['created_at'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        except:
            continue
        result.append(d)

    return result


def normalize_source(source):
    """Extract base source tags."""
    if not source:
        return set()
    results = set()
    for part in source.split(','):
        part = part.strip()
        if not part:
            continue
        base = part.split('@')[0]
        base = base.rstrip('+-').rstrip('0123456789')
        if base and base != 'unknown':
            results.add(base)
    return results


def simulate_window(signals, window_minutes, step_minutes=5):
    """Simulate confluence signals for a given window size (no persistence check)."""
    if not signals:
        return []

    start_time = signals[0]['_ts']
    end_time = signals[-1]['_ts']

    fired = []
    check_time = start_time + timedelta(minutes=window_minutes)

    while check_time <= end_time:
        # Get signals in window
        window_start = check_time - timedelta(minutes=window_minutes)
        window_signals = [s for s in signals if window_start <= s['_ts'] <= check_time]

        # Group by (token, direction)
        groups = defaultdict(list)
        for s in window_signals:
            key = (s['token'], s['direction'])
            groups[key].append(s)

        for (token, direction), sigs in groups.items():
            # Count unique sources
            unique_sources = set()
            for s in sigs:
                bases = normalize_source(s.get('source', ''))
                for base in bases:
                    if base != 'confluence':
                        unique_sources.add(base)

            compound_count = len(unique_sources)
            if compound_count < MIN_COMPOUND:
                continue

            # Recency bonus
            most_recent = max(s['_ts'] for s in sigs)
            minutes_ago = (check_time - most_recent).total_seconds() / 60
            recency_bonus = RECENCY_BONUS if minutes_ago < 10 else 0

            # Score (assume survived for frequency analysis)
            score = compound_count * COMPOUND_WEIGHT + SURVIVED_BONUS + recency_bonus

            if score >= CONFIDENCE_THRESHOLD:
                # Check cooldown — don't fire same token+direction within 1 hour
                last_fired = None
                for f in reversed(fired):
                    if f['token'] == token and f['direction'] == direction:
                        last_fired = f['timestamp']
                        break

                if last_fired and (check_time - last_fired).total_seconds() < 3600:
                    continue

                fired.append({
                    'token': token,
                    'direction': direction,
                    'timestamp': check_time,
                    'confidence': min(88, score),
                    'compound_count': compound_count,
                    'sources': list(unique_sources),
                    'window': window_minutes,
                })

        check_time += timedelta(minutes=step_minutes)

    return fired


def analyze_results(fired, window_minutes, total_days=7):
    """Analyze backtest results."""
    if not fired:
        return {
            'window': window_minutes,
            'total_fired': 0,
            'per_day': 0,
            'unique_tokens': 0,
            'avg_confidence': 0,
            'avg_sources': 0,
            'long_count': 0,
            'short_count': 0,
            'tokens_with_3plus': 0,
        }

    unique_tokens = set(f['token'] for f in fired)
    longs = [f for f in fired if f['direction'] == 'LONG']
    shorts = [f for f in fired if f['direction'] == 'SHORT']

    # Tokens that had 3+ source confluence
    tokens_3plus = set(f['token'] for f in fired if f['compound_count'] >= 3)

    return {
        'window': window_minutes,
        'total_fired': len(fired),
        'per_day': len(fired) / total_days,
        'unique_tokens': len(unique_tokens),
        'avg_confidence': sum(f['confidence'] for f in fired) / len(fired),
        'avg_sources': sum(f['compound_count'] for f in fired) / len(fired),
        'long_count': len(longs),
        'short_count': len(shorts),
        'tokens_with_3plus': len(tokens_3plus),
    }


def main():
    print("Loading signals (7 days)...")
    signals = get_signals(days=7)
    print(f"Loaded {len(signals)} signals")

    if not signals:
        print("No signals found. Exiting.")
        return

    print(f"Date range: {signals[0]['created_at']} to {signals[-1]['created_at']}")

    # Count source types
    source_counts = defaultdict(int)
    for s in signals:
        for base in normalize_source(s.get('source', '')):
            source_counts[base] += 1
    print(f"\nTop 10 source types (7d):")
    for src, cnt in sorted(source_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {src:30s} {cnt:5d}")

    print(f"\n{'Window':>8} | {'Per Day':>7} | {'Total':>6} | {'Tokens':>6} | {'3+Src':>5} | {'Avg Conf':>8} | {'Avg Src':>7} | {'LONG':>5} | {'SHORT':>6}")
    print("-" * 90)

    results = []
    for window in WINDOWS:
        fired = simulate_window(signals, window)
        stats = analyze_results(fired, window)
        results.append(stats)

        print(f"{window:>6}m | {stats['per_day']:>7.1f} | {stats['total_fired']:>6} | "
              f"{stats['unique_tokens']:>6} | {stats['tokens_with_3plus']:>5} | "
              f"{stats['avg_confidence']:>8.1f} | {stats['avg_sources']:>7.1f} | "
              f"{stats['long_count']:>5} | {stats['short_count']:>6}")

    # Scoring
    print("\n" + "=" * 90)
    print("SCORING (balancing frequency, quality, and uniqueness):")
    print("=" * 90)

    for r in results:
        if r['total_fired'] == 0:
            r['score'] = 0
            continue

        # Quality: avg sources (higher = better compounding)
        quality = r['avg_sources'] / 5 * 40

        # Uniqueness: % of signals with 3+ sources (stronger confluence)
        uniqueness = r['tokens_with_3plus'] / max(1, r['total_fired']) * 30

        # Frequency: sweet spot is 2-8 per day
        pd = r['per_day']
        if pd < 1:
            freq = pd * 15
        elif pd <= 8:
            freq = 15 + (pd - 1) * (15 / 7)
        else:
            freq = max(0, 30 - (pd - 8) * 2)

        r['score'] = quality + uniqueness + freq
        r['quality'] = quality
        r['uniqueness'] = uniqueness
        r['freq'] = freq

    sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)

    print(f"\n{'Rank':>4} | {'Window':>8} | {'Score':>6} | {'Quality':>7} | {'Unique':>6} | {'Freq':>5} | {'Per Day':>7} | {'AvgSrc':>6}")
    print("-" * 75)
    for i, r in enumerate(sorted_results):
        print(f"#{i+1:>3} | {r['window']:>6}m | {r['score']:>6.1f} | {r['quality']:>7.1f} | "
              f"{r.get('uniqueness', 0):>6.1f} | {r.get('freq', 0):>5.1f} | "
              f"{r['per_day']:>7.1f} | {r['avg_sources']:>6.1f}")

    best = sorted_results[0]
    print(f"\n{'=' * 90}")
    print(f"RECOMMENDATION: {best['window']}m window")
    print(f"{'=' * 90}")
    print(f"  - {best['per_day']:.1f} signals per day ({best['total_fired']} total over 7d)")
    print(f"  - {best['avg_sources']:.1f} avg sources per signal")
    print(f"  - {best['tokens_with_3plus']} signals with 3+ source confluence")
    print(f"  - {best['long_count']} LONG, {best['short_count']} SHORT")
    print(f"  - Score: {best['score']:.1f} (quality={best.get('quality', 0):.1f}, "
          f"uniqueness={best.get('uniqueness', 0):.1f}, freq={best.get('freq', 0):.1f})")


if __name__ == '__main__':
    main()
