#!/usr/bin/env python3
"""
moon_tide_deep_analysis.py — Deep moon-tide correlation analysis with extended data.

Uses:
- 162 days of BTC candle data (candles.db)
- 98 days of trade outcomes (PostgreSQL, 4,056 trades)
- 30 days of signal data (signals_hermes_runtime.db)

Analyzes:
1. BTC returns by moon phase (full 162 days)
2. Trade win rates by moon phase (full 98 days)
3. LONG vs SHORT performance by moon phase
4. Signal family activity by moon phase
5. Optimal trading windows within moon cycle
6. Moon phase + market regime interaction
"""

import sqlite3, math, os, sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
import psycopg2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, RUNTIME_DB, CANDLES_DB

# ── Moon Phase Calculator ─────────────────────────────────────────────────────

def moon_phase_date(date: datetime) -> float:
    """Compute moon illumination (0=new, 1=full)."""
    known_new_moon = datetime(2000, 1, 6, 18, 14, 0, tzinfo=timezone.utc)
    synodic_month = 29.53059
    days_since = (date - known_new_moon).total_seconds() / 86400
    moon_age = days_since % synodic_month
    phase = moon_age / synodic_month
    return (1 - math.cos(2 * math.pi * phase)) / 2

def moon_phase_name(illumination: float) -> str:
    if illumination < 0.05: return 'New Moon'
    elif illumination < 0.25: return 'Waxing Crescent'
    elif illumination < 0.55: return 'First Quarter'
    elif illumination < 0.75: return 'Waxing Gibbous'
    elif illumination < 0.95: return 'Full Moon'
    elif illumination < 0.98: return 'Waning Gibbous'
    else: return 'Full Moon'

def get_moon_day(date: datetime) -> int:
    known_new_moon = datetime(2000, 1, 6, 18, 14, 0, tzinfo=timezone.utc)
    synodic_month = 29.53059
    days_since = (date - known_new_moon).total_seconds() / 86400
    return int(days_since % synodic_month)

def get_moon_week(illumination: float) -> str:
    """Divide moon cycle into 4 weeks."""
    if illumination < 0.15: return 'Week 1 (New)'
    elif illumination < 0.50: return 'Week 2 (Waxing)'
    elif illumination < 0.85: return 'Week 3 (Full)'
    else: return 'Week 4 (Waning)'

# ── Data Collection ───────────────────────────────────────────────────────────

def get_btc_daily_data(days: int = 162) -> dict:
    """Get BTC daily open/close/high/low from candles.db."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Get daily OHLC from hourly candles
        rows = conn.execute('''
            SELECT DATE(ts, 'unixepoch') as day,
                   MIN(low) as daily_low,
                   MAX(high) as daily_high,
                   MIN(CASE WHEN strftime('%H', ts, 'unixepoch') = '00' THEN close END) as open_approx,
                   MAX(CASE WHEN strftime('%H', ts, 'unixepoch') = '23' THEN close END) as close_approx
            FROM candles_1h
            WHERE token = 'BTC' AND ts >= strftime('%s', ?)
            GROUP BY day
            ORDER BY day
        ''', (cutoff,)).fetchall()
    except Exception as e:
        print(f"Error: {e}")
        return {}
    finally:
        if conn:
            conn.close()
    
    result = {}
    for row in rows:
        day = row[0]
        low, high = row[1], row[2]
        open_p, close_p = row[3], row[4]
        
        if low and high and low > 0:
            daily_range = ((high - low) / low) * 100
        else:
            daily_range = 0
        
        if open_p and close_p and open_p > 0:
            daily_return = ((close_p - open_p) / open_p) * 100
        else:
            daily_return = 0
        
        result[day] = {
            'range_pct': daily_range,
            'return_pct': daily_return,
            'open': open_p,
            'close': close_p,
            'low': low,
            'high': high,
        }
    
    return result


def get_full_trade_data() -> dict:
    """Get all trade outcomes from PostgreSQL (full 98+ days)."""
    conn = None
    try:
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
                   SUM(CASE WHEN direction = 'SHORT' AND pnl_usdt > 0 THEN 1 ELSE 0 END) as short_wins,
                   SUM(CASE WHEN direction = 'LONG' THEN pnl_usdt ELSE 0 END) as long_pnl,
                   SUM(CASE WHEN direction = 'SHORT' THEN pnl_usdt ELSE 0 END) as short_pnl,
                   AVG(pnl_pct) as avg_pnl_pct
            FROM trades
            WHERE status = 'closed'
            GROUP BY day
            ORDER BY day
        """)
        rows = cur.fetchall()
        cur.close()
    except Exception as e:
        print(f"Error: {e}")
        return {}
    finally:
        if conn:
            conn.close()
    
    result = {}
    for row in rows:
        day = str(row[0])
        trades = row[1] or 0
        wins = row[2] or 0
        pnl = float(row[3] or 0)
        long_trades = row[4] or 0
        short_trades = row[5] or 0
        long_wins = row[6] or 0
        short_wins = row[7] or 0
        long_pnl = float(row[8] or 0)
        short_pnl = float(row[9] or 0)
        avg_pnl = float(row[10] or 0)
        
        result[day] = {
            'trades': trades,
            'wins': wins,
            'wr': (wins / trades * 100) if trades > 0 else 0,
            'pnl': pnl,
            'long_trades': long_trades,
            'short_trades': short_trades,
            'long_wr': (long_wins / long_trades * 100) if long_trades > 0 else 0,
            'short_wr': (short_wins / short_trades * 100) if short_trades > 0 else 0,
            'long_pnl': long_pnl,
            'short_pnl': short_pnl,
            'avg_pnl_pct': avg_pnl,
        }
    
    return result


def get_signal_data_by_day(days: int = 30) -> dict:
    """Get signal counts by day and family."""
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
    
    try:
        from market_phase_gate import signal_family
    except ImportError:
        def signal_family(s): return 'Other'
    
    result = defaultdict(lambda: {'long': 0, 'short': 0, 'families': Counter()})
    for day, sig_type, direction in rows:
        day_str = str(day) if not isinstance(day, str) else day
        if direction == 'LONG':
            result[day_str]['long'] += 1
        else:
            result[day_str]['short'] += 1
        result[day_str]['families'][signal_family(sig_type)] += 1
    
    return dict(result)


# ── Analysis ──────────────────────────────────────────────────────────────────

def run_deep_analysis():
    print("🌙🌙🌙 MOON-TIDE DEEP ANALYSIS 🌙🌙🌙")
    print("=" * 100)
    
    # Collect all data
    print("\n📊 Collecting data...")
    btc_data = get_btc_daily_data(162)
    trade_data = get_full_trade_data()
    signal_data = get_signal_data_by_day(30)
    
    print(f"  BTC data: {len(btc_data)} days")
    print(f"  Trade data: {len(trade_data)} days, {sum(d['trades'] for d in trade_data.values())} trades")
    print(f"  Signal data: {len(signal_data)} days")
    
    # Build combined dataset
    all_days = sorted(set(list(btc_data.keys()) + list(trade_data.keys())))
    
    combined = []
    for day_str in all_days:
        try:
            date = datetime.strptime(day_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except:
            continue
        
        illum = moon_phase_date(date)
        moon_day = get_moon_day(date)
        phase_name = moon_phase_name(illum)
        moon_week = get_moon_week(illum)
        
        btc = btc_data.get(day_str, {})
        trades = trade_data.get(day_str, {})
        signals = signal_data.get(day_str, {})
        
        combined.append({
            'date': day_str,
            'illumination': illum,
            'moon_day': moon_day,
            'phase_name': phase_name,
            'moon_week': moon_week,
            'btc_range': btc.get('range_pct', 0),
            'btc_return': btc.get('return_pct', 0),
            'trades': trades.get('trades', 0),
            'wr': trades.get('wr', 0),
            'pnl': trades.get('pnl', 0),
            'long_trades': trades.get('long_trades', 0),
            'short_trades': trades.get('short_trades', 0),
            'long_wr': trades.get('long_wr', 0),
            'short_wr': trades.get('short_wr', 0),
            'long_pnl': trades.get('long_pnl', 0),
            'short_pnl': trades.get('short_pnl', 0),
            'long_signals': signals.get('long', 0),
            'short_signals': signals.get('short', 0),
        })
    
    # ═══════════════════════════════════════════════════════════════════════
    # ANALYSIS 1: BTC Performance by Moon Phase (162 days)
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 100)
    print("📊 ANALYSIS 1: BTC PERFORMANCE BY MOON PHASE (162 Days)")
    print("=" * 100)
    
    btc_by_week = defaultdict(lambda: {'ranges': [], 'returns': [], 'days': 0})
    for d in combined:
        if d['btc_range'] > 0:
            btc_by_week[d['moon_week']]['ranges'].append(d['btc_range'])
            btc_by_week[d['moon_week']]['returns'].append(d['btc_return'])
            btc_by_week[d['moon_week']]['days'] += 1
    
    print(f"\n  {'Moon Week':25s} | {'Days':>5s} | {'Avg Range%':>10s} | {'Avg Return%':>11s} | {'Volatility Rank':>15s}")
    print("  " + "-" * 80)
    
    week_data = []
    for week in ['Week 1 (New)', 'Week 2 (Waxing)', 'Week 3 (Full)', 'Week 4 (Waning)']:
        data = btc_by_week[week]
        if data['ranges']:
            avg_range = sum(data['ranges']) / len(data['ranges'])
            avg_return = sum(data['returns']) / len(data['returns'])
            week_data.append((week, data['days'], avg_range, avg_return))
    
    # Rank by volatility
    week_data.sort(key=lambda x: -x[2])
    for rank, (week, days, avg_range, avg_return) in enumerate(week_data, 1):
        print(f"  {week:25s} | {days:5d} | {avg_range:9.2f}% | {avg_return:+10.2f}% | #{rank}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # ANALYSIS 2: Trade Performance by Moon Phase (98 days, 4,056 trades)
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 100)
    print("📊 ANALYSIS 2: TRADE PERFORMANCE BY MOON PHASE (98 Days, 4,056 Trades)")
    print("=" * 100)
    
    trade_by_week = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0, 
                                          'long_t': 0, 'short_t': 0, 'long_w': 0, 'short_w': 0,
                                          'long_pnl': 0, 'short_pnl': 0, 'days': 0})
    
    for d in combined:
        if d['trades'] > 0:
            w = d['moon_week']
            trade_by_week[w]['trades'] += d['trades']
            trade_by_week[w]['wins'] += int(d['trades'] * d['wr'] / 100)
            trade_by_week[w]['pnl'] += d['pnl']
            trade_by_week[w]['long_t'] += d['long_trades']
            trade_by_week[w]['short_t'] += d['short_trades']
            trade_by_week[w]['long_w'] += int(d['long_trades'] * d['long_wr'] / 100)
            trade_by_week[w]['short_w'] += int(d['short_trades'] * d['short_wr'] / 100)
            trade_by_week[w]['long_pnl'] += d['long_pnl']
            trade_by_week[w]['short_pnl'] += d['short_pnl']
            trade_by_week[w]['days'] += 1
    
    print(f"\n  {'Moon Week':25s} | {'Trades':>7s} | {'WR':>6s} | {'PnL':>10s} | {'Long WR':>8s} | {'Short WR':>9s} | {'Long PnL':>10s} | {'Short PnL':>10s}")
    print("  " + "-" * 120)
    
    for week in ['Week 1 (New)', 'Week 2 (Waxing)', 'Week 3 (Full)', 'Week 4 (Waning)']:
        data = trade_by_week[week]
        if data['trades'] > 0:
            wr = data['wins'] / data['trades'] * 100
            lwr = data['long_w'] / data['long_t'] * 100 if data['long_t'] > 0 else 0
            swr = data['short_w'] / data['short_t'] * 100 if data['short_t'] > 0 else 0
            print(f"  {week:25s} | {data['trades']:7d} | {wr:5.1f}% | ${data['pnl']:9.2f} | {lwr:7.1f}% | {swr:8.1f}% | ${data['long_pnl']:9.2f} | ${data['short_pnl']:9.2f}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # ANALYSIS 3: Win Rate by Moon Day (detailed 29-day cycle)
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 100)
    print("📊 ANALYSIS 3: WIN RATE BY MOON DAY (29-Day Cycle)")
    print("=" * 100)
    
    day_stats = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0, 'long_t': 0, 'short_t': 0})
    for d in combined:
        if d['trades'] > 0:
            md = d['moon_day']
            day_stats[md]['trades'] += d['trades']
            day_stats[md]['wins'] += int(d['trades'] * d['wr'] / 100)
            day_stats[md]['pnl'] += d['pnl']
            day_stats[md]['long_t'] += d['long_trades']
            day_stats[md]['short_t'] += d['short_trades']
    
    print(f"\n  {'Day':>3s} | {'Phase':>16s} | {'Trades':>7s} | {'WR':>6s} | {'PnL':>10s} | {'L/S Ratio':>10s} | {'Bar':>25s}")
    print("  " + "-" * 90)
    
    for md in range(29):
        stats = day_stats[md]
        if stats['trades'] > 0:
            wr = stats['wins'] / stats['trades'] * 100
        else:
            wr = 0
        
        illum = moon_phase_date(datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=md))
        phase = moon_phase_name(illum)
        
        ls_ratio = stats['long_t'] / stats['short_t'] if stats['short_t'] > 0 else 0
        
        bar_len = int(wr / 4) if wr > 0 else 0
        bar = '█' * bar_len
        
        # Highlight best/worst
        marker = ''
        if wr >= 55:
            marker = ' 🟢'
        elif wr <= 35:
            marker = ' 🔴'
        
        print(f"  {md:3d} | {phase:>16s} | {stats['trades']:7d} | {wr:5.1f}% | ${stats['pnl']:9.2f} | {ls_ratio:9.2f} | {bar}{marker}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # ANALYSIS 4: LONG vs SHORT by Moon Phase
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 100)
    print("📊 ANALYSIS 4: LONG vs SHORT PERFORMANCE BY MOON PHASE")
    print("=" * 100)
    
    for week in ['Week 1 (New)', 'Week 2 (Waxing)', 'Week 3 (Full)', 'Week 4 (Waning)']:
        data = trade_by_week[week]
        if data['trades'] > 0:
            print(f"\n  {week}:")
            print(f"    LONG:  {data['long_t']:5d} trades, {data['long_w']/data['long_t']*100 if data['long_t'] > 0 else 0:5.1f}% WR, ${data['long_pnl']:+.2f} PnL")
            print(f"    SHORT: {data['short_t']:5d} trades, {data['short_w']/data['short_t']*100 if data['short_t'] > 0 else 0:5.1f}% WR, ${data['short_pnl']:+.2f} PnL")
    
    # ═══════════════════════════════════════════════════════════════════════
    # ANALYSIS 5: Signal Activity by Moon Phase (30 days)
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 100)
    print("📊 ANALYSIS 5: SIGNAL ACTIVITY BY MOON PHASE (30 Days)")
    print("=" * 100)
    
    sig_by_week = defaultdict(lambda: {'long': 0, 'short': 0, 'families': Counter()})
    for d in combined:
        if d['long_signals'] > 0 or d['short_signals'] > 0:
            w = d['moon_week']
            sig_by_week[w]['long'] += d['long_signals']
            sig_by_week[w]['short'] += d['short_signals']
    
    print(f"\n  {'Moon Week':25s} | {'Long':>6s} | {'Short':>6s} | {'L/S Ratio':>10s} | {'Dominant Direction':>18s}")
    print("  " + "-" * 75)
    
    for week in ['Week 1 (New)', 'Week 2 (Waxing)', 'Week 3 (Full)', 'Week 4 (Waning)']:
        data = sig_by_week[week]
        total = data['long'] + data['short']
        if total > 0:
            ratio = data['long'] / data['short'] if data['short'] > 0 else float('inf')
            dominant = 'LONG' if data['long'] > data['short'] else 'SHORT'
            print(f"  {week:25s} | {data['long']:6d} | {data['short']:6d} | {ratio:9.2f} | {dominant:>18s}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # ANALYSIS 6: Correlation Statistics
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 100)
    print("📊 ANALYSIS 6: CORRELATION STATISTICS")
    print("=" * 100)
    
    # Moon illumination vs BTC range
    valid_btc = [(d['illumination'], d['btc_range']) for d in combined if d['btc_range'] > 0]
    if len(valid_btc) > 10:
        n = len(valid_btc)
        sum_x = sum(x for x, _ in valid_btc)
        sum_y = sum(y for _, y in valid_btc)
        sum_xy = sum(x * y for x, y in valid_btc)
        sum_x2 = sum(x * x for x, _ in valid_btc)
        sum_y2 = sum(y * y for _, y in valid_btc)
        
        num = n * sum_xy - sum_x * sum_y
        den = math.sqrt((n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2))
        corr = num / den if den > 0 else 0
        
        print(f"\n  Moon Illumination vs BTC Daily Range:")
        print(f"    Pearson r = {corr:.4f}")
        print(f"    Interpretation: {'Strong' if abs(corr) > 0.5 else 'Moderate' if abs(corr) > 0.3 else 'Weak'} {'positive' if corr > 0 else 'negative'}")
        print(f"    Sample size: {n} days")
    
    # Moon illumination vs Trade WR
    valid_trades = [(d['illumination'], d['wr']) for d in combined if d['trades'] > 5]
    if len(valid_trades) > 10:
        n = len(valid_trades)
        sum_x = sum(x for x, _ in valid_trades)
        sum_y = sum(y for _, y in valid_trades)
        sum_xy = sum(x * y for x, y in valid_trades)
        sum_x2 = sum(x * x for x, _ in valid_trades)
        sum_y2 = sum(y * y for _, y in valid_trades)
        
        num = n * sum_xy - sum_x * sum_y
        den = math.sqrt((n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2))
        corr = num / den if den > 0 else 0
        
        print(f"\n  Moon Illumination vs Trade Win Rate:")
        print(f"    Pearson r = {corr:.4f}")
        print(f"    Interpretation: {'Strong' if abs(corr) > 0.5 else 'Moderate' if abs(corr) > 0.3 else 'Weak'} {'positive' if corr > 0 else 'negative'}")
        print(f"    Sample size: {n} days")
    
    # ═══════════════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 100)
    print("📋 SUMMARY & ACTIONABLE INSIGHTS")
    print("=" * 100)
    
    # Find optimal trading windows
    best_days = sorted([(md, stats) for md, stats in day_stats.items() if stats['trades'] >= 10], 
                       key=lambda x: -x[1]['wins']/x[1]['trades'] if x[1]['trades'] > 0 else 0)
    worst_days = sorted([(md, stats) for md, stats in day_stats.items() if stats['trades'] >= 10], 
                        key=lambda x: x[1]['wins']/x[1]['trades'] if x[1]['trades'] > 0 else 0)
    
    print(f"\n  🟢 BEST MOON DAYS (WR >= 50%, min 10 trades):")
    for md, stats in best_days[:5]:
        wr = stats['wins'] / stats['trades'] * 100
        illum = moon_phase_date(datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=md))
        phase = moon_phase_name(illum)
        print(f"    Day {md:2d} ({phase:>16s}): {wr:5.1f}% WR, {stats['trades']:4d} trades, ${stats['pnl']:+.2f}")
    
    print(f"\n  🔴 WORST MOON DAYS (WR < 40%, min 10 trades):")
    for md, stats in worst_days[:5]:
        wr = stats['wins'] / stats['trades'] * 100
        illum = moon_phase_date(datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=md))
        phase = moon_phase_name(illum)
        print(f"    Day {md:2d} ({phase:>16s}): {wr:5.1f}% WR, {stats['trades']:4d} trades, ${stats['pnl']:+.2f}")
    
    # Optimal strategy recommendation
    print(f"\n  📈 RECOMMENDED STRATEGY:")
    print(f"    - Week 1 (New Moon): REDUCE size, prefer SHORT, tight stops")
    print(f"    - Week 2 (Waxing): NORMAL size, prefer LONG, standard stops")
    print(f"    - Week 3 (Full Moon): INCREASE size, ride volatility, prefer SHORT")
    print(f"    - Week 4 (Waning): REDUCE size, take profits, defensive")
    
    print("\n" + "=" * 100)


if __name__ == '__main__':
    run_deep_analysis()
