#!/usr/bin/env python3
"""
moon_tide_correlation.py — Analyze correlations between moon phases and market tides.

Tests the hypothesis: Do market peaks/troughs correlate with lunar cycles?
- Full Moon (100% illumination) → market peak?
- New Moon (0% illumination) → market trough?
- Quarter Moons → transitions?

Uses astronomical algorithm to compute moon phases, then correlates with:
1. Signal family activity (from signals_hermes_runtime.db)
2. BTC price movements (from candles.db)
3. LONG/SHORT signal ratios
4. Win rates by moon phase

Usage:
    python3 moon_tide_correlation.py           # Full analysis
    python3 moon_tide_correlation.py --days 90 # Extended window
"""

import sqlite3, math, os, sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, RUNTIME_DB, CANDLES_DB

# ── Moon Phase Calculator (Astronomical Algorithm) ────────────────────────────
# Based on Meeus "Astronomical Algorithms" - simplified for moon phase

def moon_phase_date(date: datetime) -> float:
    """
    Compute moon illumination percentage for a given date.
    
    Returns: 0.0 (new moon) to 1.0 (full moon)
    
    Algorithm: Simple synodic month calculation
    - Synodic month = 29.53059 days
    - Known new moon: 2000-01-06 18:14 UTC
    """
    # Known new moon (Jan 6, 2000 18:14 UTC)
    known_new_moon = datetime(2000, 1, 6, 18, 14, 0, tzinfo=timezone.utc)
    synodic_month = 29.53059  # days
    
    # Days since known new moon
    days_since = (date - known_new_moon).total_seconds() / 86400
    
    # Moon age (days into current cycle)
    moon_age = days_since % synodic_month
    
    # Convert to illumination (0-1-0)
    # 0 = new moon, ~7.4 = first quarter, ~14.8 = full moon, ~22.1 = last quarter
    phase = moon_age / synodic_month  # 0 to 1
    
    # Illumination follows a cosine curve
    illumination = (1 - math.cos(2 * math.pi * phase)) / 2
    
    return illumination


def moon_phase_name(illumination: float) -> str:
    """Get human-readable moon phase name."""
    if illumination < 0.05:
        return 'New Moon'
    elif illumination < 0.25:
        return 'Waxing Crescent'
    elif illumination < 0.55:
        return 'First Quarter'
    elif illumination < 0.75:
        return 'Waxing Gibbous'
    elif illumination < 0.95:
        return 'Full Moon'
    elif illumination < 0.98:
        return 'Waning Gibbous'
    else:
        return 'Full Moon'


def get_moon_phase_bucket(illumination: float) -> str:
    """Bucket moon phase into 4 categories."""
    if illumination < 0.15:
        return 'New'
    elif illumination < 0.45:
        return 'Waxing'
    elif illumination < 0.85:
        return 'Full/Waning'
    else:
        return 'New'  # Wraps around


def get_moon_day(date: datetime) -> int:
    """Get day in moon cycle (0-28)."""
    known_new_moon = datetime(2000, 1, 6, 18, 14, 0, tzinfo=timezone.utc)
    synodic_month = 29.53059
    days_since = (date - known_new_moon).total_seconds() / 86400
    return int(days_since % synodic_month)


# ── Data Collection ───────────────────────────────────────────────────────────

def get_btc_daily_returns(days: int = 90) -> dict:
    """Get BTC daily returns for correlation analysis."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')
        
        rows = conn.execute('''
            SELECT DATE(ts, 'unixepoch') as day, 
                   FIRST_VALUE(close) OVER (PARTITION BY DATE(ts, 'unixepoch') ORDER BY ts) as open,
                   LAST_VALUE(close) OVER (PARTITION BY DATE(ts, 'unixepoch') ORDER BY ts ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as close
            FROM candles_1h
            WHERE token = 'BTC' AND ts >= strftime('%s', ?)
            ORDER BY ts
        ''', (cutoff,)).fetchall()
        
        # Alternative: use simpler query
        if not rows:
            rows = conn.execute('''
                SELECT DATE(ts, 'unixepoch') as day, MIN(close) as low, MAX(close) as high
                FROM candles_1h
                WHERE token = 'BTC' AND ts >= strftime('%s', ?)
                GROUP BY day
                ORDER BY day
            ''', (cutoff,)).fetchall()
    except Exception as e:
        print(f"Error querying candles: {e}")
        return {}
    finally:
        if conn:
            conn.close()
    
    returns = {}
    for row in rows:
        day = row[0]
        if row[1] and row[2] and row[1] > 0:
            # Use high-low range as proxy for volatility
            range_pct = ((row[2] - row[1]) / row[1]) * 100
            returns[day] = range_pct
    
    return returns


def get_signal_activity_by_day(days: int = 90) -> dict:
    """Get signal activity grouped by day and family."""
    conn = None
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=10)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')
        
        rows = conn.execute('''
            SELECT DATE(created_at) as day, signal_type, direction
            FROM signals
            WHERE created_at >= ?
        ''', (cutoff,)).fetchall()
    except Exception:
        return {}
    finally:
        if conn:
            conn.close()
    
    daily = defaultdict(lambda: {'long_count': 0, 'short_count': 0, 'families': Counter()})
    
    # Import family mapping
    try:
        from market_phase_gate import signal_family
    except ImportError:
        def signal_family(s):
            return 'Other'
    
    for day, sig_type, direction in rows:
        if direction == 'LONG':
            daily[day]['long_count'] += 1
        else:
            daily[day]['short_count'] += 1
        daily[day]['families'][signal_family(sig_type)] += 1
    
    return dict(daily)


def get_trade_outcomes_by_day(days: int = 90) -> dict:
    """Get trade outcomes grouped by day."""
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(host='/var/run/postgresql', database='brain',
                                user='postgres', connect_timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT DATE(close_time) as day, 
                   COUNT(*) as trades,
                   SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(pnl_usdt) as total_pnl,
                   SUM(CASE WHEN direction = 'LONG' THEN 1 ELSE 0 END) as long_trades,
                   SUM(CASE WHEN direction = 'SHORT' THEN 1 ELSE 0 END) as short_trades,
                   SUM(CASE WHEN direction = 'LONG' AND pnl_usdt > 0 THEN 1 ELSE 0 END) as long_wins,
                   SUM(CASE WHEN direction = 'SHORT' AND pnl_usdt > 0 THEN 1 ELSE 0 END) as short_wins
            FROM trades
            WHERE status = 'closed' AND close_time > NOW() - INTERVAL '%s days'
            GROUP BY day
            ORDER BY day
        """, (days,))
        rows = cur.fetchall()
        cur.close()
    except Exception as e:
        print(f"Error querying trades: {e}")
        return {}
    finally:
        if conn:
            conn.close()
    
    results = {}
    for row in rows:
        day = str(row[0])
        trades = row[1] or 0
        wins = row[2] or 0
        pnl = row[3] or 0
        long_trades = row[4] or 0
        short_trades = row[5] or 0
        long_wins = row[6] or 0
        short_wins = row[7] or 0
        
        wr = (wins / trades * 100) if trades > 0 else 0
        long_wr = (long_wins / long_trades * 100) if long_trades > 0 else 0
        short_wr = (short_wins / short_trades * 100) if short_trades > 0 else 0
        
        results[day] = {
            'trades': trades,
            'wins': wins,
            'wr': wr,
            'pnl': pnl,
            'long_trades': long_trades,
            'short_trades': short_trades,
            'long_wr': long_wr,
            'short_wr': short_wr,
        }
    
    return results


# ── Correlation Analysis ──────────────────────────────────────────────────────

def analyze_correlations(days: int = 90):
    """Main analysis function."""
    print(f"🌙 Moon-Tide Correlation Analysis — Last {days} Days")
    print("=" * 80)
    
    # Get data
    btc_returns = get_btc_daily_returns(days)
    signal_activity = get_signal_activity_by_day(days)
    trade_outcomes = get_trade_outcomes_by_day(days)
    
    # Build daily dataset with moon phases
    daily_data = []
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    for i in range(days):
        date = start_date + timedelta(days=i)
        day_str = date.strftime('%Y-%m-%d')
        
        # Moon phase
        illumination = moon_phase_date(date)
        phase_name = moon_phase_name(illumination)
        phase_bucket = get_moon_phase_bucket(illumination)
        moon_day = get_moon_day(date)
        
        # BTC data
        btc_range = btc_returns.get(day_str, 0)
        
        # Signal activity
        sig_data = signal_activity.get(day_str, {'long_count': 0, 'short_count': 0, 'families': Counter()})
        long_signals = sig_data['long_count']
        short_signals = sig_data['short_count']
        total_signals = long_signals + short_signals
        long_ratio = long_signals / total_signals if total_signals > 0 else 0.5
        
        # Trade outcomes
        trades = trade_outcomes.get(day_str, {'trades': 0, 'wr': 0, 'pnl': 0, 'long_wr': 0, 'short_wr': 0})
        
        daily_data.append({
            'date': day_str,
            'illumination': illumination,
            'phase_name': phase_name,
            'phase_bucket': phase_bucket,
            'moon_day': moon_day,
            'btc_range': btc_range,
            'long_signals': long_signals,
            'short_signals': short_signals,
            'long_ratio': long_ratio,
            'trades': trades['trades'],
            'wr': trades['wr'],
            'pnl': trades['pnl'],
            'long_wr': trades['long_wr'],
            'short_wr': trades['short_wr'],
        })
    
    # ── Analysis 1: Performance by Moon Phase ──────────────────────────────
    print("\n📊 PERFORMANCE BY MOON PHASE")
    print("-" * 80)
    
    phase_stats = defaultdict(lambda: {'days': 0, 'trades': 0, 'wins': 0, 'pnl': 0, 
                                        'long_signals': 0, 'short_signals': 0, 'wr': 0})
    
    for d in daily_data:
        phase = d['phase_bucket']
        phase_stats[phase]['days'] += 1
        phase_stats[phase]['trades'] += d['trades']
        phase_stats[phase]['wins'] += int(d['trades'] * d['wr'] / 100)
        phase_stats[phase]['pnl'] += d['pnl']
        phase_stats[phase]['long_signals'] += d['long_signals']
        phase_stats[phase]['short_signals'] += d['short_signals']
    
    print(f"\n  {'Phase':15s} | {'Days':>5s} | {'Trades':>7s} | {'WR':>6s} | {'PnL':>8s} | {'Long:Short':>12s}")
    print("  " + "-" * 70)
    
    for phase in ['New', 'Waxing', 'Full/Waning']:
        stats = phase_stats[phase]
        if stats['trades'] > 0:
            stats['wr'] = stats['wins'] / stats['trades'] * 100
        ratio = f"{stats['long_signals']}:{stats['short_signals']}"
        print(f"  {phase:15s} | {stats['days']:5d} | {stats['trades']:7d} | {stats['wr']:5.1f}% | ${stats['pnl']:7.2f} | {ratio:>12s}")
    
    # ── Analysis 2: Signal Family Activity by Moon Phase ───────────────────
    print("\n📊 SIGNAL FAMILY ACTIVITY BY MOON PHASE")
    print("-" * 80)
    
    family_by_phase = defaultdict(lambda: defaultdict(int))
    for d in daily_data:
        # Reconstruct families from signal counts (simplified)
        phase = d['phase_bucket']
        family_by_phase[phase]['Long'] += d['long_signals']
        family_by_phase[phase]['Short'] += d['short_signals']
    
    print(f"\n  {'Phase':15s} | {'Long Signals':>12s} | {'Short Signals':>12s} | {'L/S Ratio':>10s}")
    print("  " + "-" * 60)
    
    for phase in ['New', 'Waxing', 'Full/Waning']:
        data = family_by_phase[phase]
        total = data['Long'] + data['Short']
        ratio = data['Long'] / data['Short'] if data['Short'] > 0 else float('inf')
        print(f"  {phase:15s} | {data['Long']:12d} | {data['Short']:12d} | {ratio:10.2f}")
    
    # ── Analysis 3: Win Rate by Moon Day ───────────────────────────────────
    print("\n📊 WIN RATE BY MOON DAY (0-28)")
    print("-" * 80)
    
    day_stats = defaultdict(lambda: {'trades': 0, 'wins': 0})
    for d in daily_data:
        moon_day = d['moon_day']
        day_stats[moon_day]['trades'] += d['trades']
        day_stats[moon_day]['wins'] += int(d['trades'] * d['wr'] / 100)
    
    print(f"\n  {'Moon Day':>8s} | {'Phase':>12s} | {'Trades':>7s} | {'WR':>6s} | {'Bar':>20s}")
    print("  " + "-" * 65)
    
    for moon_day in range(29):
        stats = day_stats[moon_day]
        if stats['trades'] > 0:
            wr = stats['wins'] / stats['trades'] * 100
        else:
            wr = 0
        
        # Create moon phase name for this day
        illum = moon_phase_date(datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=moon_day))
        phase = moon_phase_name(illum)
        
        bar_len = int(wr / 5) if wr > 0 else 0
        bar = '█' * bar_len
        print(f"  {moon_day:8d} | {phase:>12s} | {stats['trades']:7d} | {wr:5.1f}% | {bar}")
    
    # ── Analysis 4: BTC Volatility by Moon Phase ──────────────────────────
    print("\n📊 BTC VOLATILITY BY MOON PHASE")
    print("-" * 80)
    
    btc_by_phase = defaultdict(list)
    for d in daily_data:
        if d['btc_range'] > 0:
            btc_by_phase[d['phase_bucket']].append(d['btc_range'])
    
    print(f"\n  {'Phase':15s} | {'Avg Range%':>10s} | {'Min':>8s} | {'Max':>8s} | {'Days':>5s}")
    print("  " + "-" * 55)
    
    for phase in ['New', 'Waxing', 'Full/Waning']:
        ranges = btc_by_phase[phase]
        if ranges:
            avg = sum(ranges) / len(ranges)
            print(f"  {phase:15s} | {avg:9.2f}% | {min(ranges):7.2f}% | {max(ranges):7.2f}% | {len(ranges):5d}")
    
    # ── Analysis 5: Correlation Coefficient ────────────────────────────────
    print("\n📊 CORRELATION: Moon Illumination vs BTC Range")
    print("-" * 80)
    
    valid_data = [(d['illumination'], d['btc_range']) for d in daily_data if d['btc_range'] > 0]
    if len(valid_data) > 10:
        n = len(valid_data)
        sum_x = sum(x for x, _ in valid_data)
        sum_y = sum(y for _, y in valid_data)
        sum_xy = sum(x * y for x, y in valid_data)
        sum_x2 = sum(x * x for x, _ in valid_data)
        sum_y2 = sum(y * y for _, y in valid_data)
        
        numerator = n * sum_xy - sum_x * sum_y
        denominator = math.sqrt((n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2))
        
        if denominator > 0:
            correlation = numerator / denominator
            print(f"\n  Pearson correlation: {correlation:.4f}")
            print(f"  Interpretation: {'Strong' if abs(correlation) > 0.5 else 'Moderate' if abs(correlation) > 0.3 else 'Weak'} {'positive' if correlation > 0 else 'negative'}")
            print(f"  Sample size: {n} days")
            
            # Statistical significance (simplified t-test)
            if abs(correlation) < 1:
                t_stat = correlation * math.sqrt((n - 2) / (1 - correlation**2))
                print(f"  t-statistic: {t_stat:.2f}")
                print(f"  Significant at 95%: {'Yes' if abs(t_stat) > 2.0 else 'No'}")
        else:
            print("\n  Cannot compute correlation (zero variance)")
    else:
        print("\n  Insufficient data for correlation analysis")
    
    # ── Summary ────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("📋 SUMMARY")
    print("=" * 80)
    
    # Find best/worst phases
    best_phase = max(phase_stats.items(), key=lambda x: x[1]['pnl'] if x[1]['trades'] > 0 else -999)
    worst_phase = min(phase_stats.items(), key=lambda x: x[1]['pnl'] if x[1]['trades'] > 0 else 999)
    
    print(f"\n  Best phase for trading: {best_phase[0]} (${best_phase[1]['pnl']:.2f} PnL)")
    print(f"  Worst phase for trading: {worst_phase[0]} (${worst_phase[1]['pnl']:.2f} PnL)")
    
    # Long/Short preference
    for phase in ['New', 'Waxing', 'Full/Waning']:
        data = family_by_phase[phase]
        if data['Long'] > data['Short']:
            print(f"  {phase}: LONG preferred ({data['Long']}/{data['Short']} signals)")
        elif data['Short'] > data['Long']:
            print(f"  {phase}: SHORT preferred ({data['Short']}/{data['Long']} signals)")
        else:
            print(f"  {phase}: Neutral")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    days = 90
    if '--days' in sys.argv:
        idx = sys.argv.index('--days')
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])
    
    analyze_correlations(days)
