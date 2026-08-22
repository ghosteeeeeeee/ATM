#!/usr/bin/env python3
"""
Market Weather Station — Hermes Trading System
================================================
Reads 30+ days of signal data like ocean conditions:
- Tide direction (regime flow)
- Wave height (signal intensity)
- Swell period (signal spacing/patterns)
- Wind (momentum/velocity)
- Sea state (overall market health)
- Lightning strikes (crash/pump events)

Output: A weather-report-style summary of market conditions.
"""

import sqlite3
import json
import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

# Import paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

DB_PATH = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')

def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def analyze_tide(conn):
    """
    TIDE ANALYSIS — Direction and strength of the market flow.
    Like reading the tide: incoming (bullish), outgoing (bearish), or slack.
    """
    # Get recent signal direction balance (last 24h, 7d, 30d)
    periods = {
        '24h': 24,
        '7d': 7 * 24,
        '30d': 30 * 24,
    }
    
    results = {}
    for label, hours in periods.items():
        cutoff = f"-{hours} hours"
        row = conn.execute(f"""
            SELECT 
                SUM(CASE WHEN direction = 'LONG' THEN 1 ELSE 0 END) as long_signals,
                SUM(CASE WHEN direction = 'SHORT' THEN 1 ELSE 0 END) as short_signals,
                COUNT(*) as total
            FROM signals
            WHERE created_at >= datetime('now', ?)
        """, (cutoff,)).fetchone()
        
        if row and row['total'] > 0:
            long_pct = 100.0 * row['long_signals'] / row['total']
            short_pct = 100.0 * row['short_signals'] / row['total']
            
            # Tide strength: how imbalanced
            imbalance = abs(long_pct - 50) / 50  # 0 = balanced, 1 = one-sided
            
            if long_pct > 55:
                tide = "INCOMING (BULLISH)"
                emoji = "🌊📈"
            elif short_pct > 55:
                tide = "OUTGOING (BEARISH)"
                emoji = "🌊📉"
            else:
                tide = "SLACK (NEUTRAL)"
                emoji = "🌊➡️"
            
            results[label] = {
                'tide': tide,
                'emoji': emoji,
                'long_pct': round(long_pct, 1),
                'short_pct': round(short_pct, 1),
                'imbalance': round(imbalance, 2),
                'total_signals': row['total'],
            }
    
    return results

def analyze_waves(conn):
    """
    WAVE ANALYSIS — Signal intensity and quality.
    Like reading wave height: big waves = lots of activity, clean waves = quality signals.
    """
    # Signal volume over time (hourly buckets for last 7 days)
    hourly = conn.execute("""
        SELECT 
            strftime('%Y-%m-%d %H:00:00', created_at) as hour,
            COUNT(*) as signal_count,
            COUNT(DISTINCT token) as tokens,
            COUNT(DISTINCT signal_type) as types,
            AVG(confidence) as avg_confidence,
            SUM(CASE WHEN direction = 'LONG' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as long_ratio
        FROM signals
        WHERE created_at >= datetime('now', '-7 days')
        GROUP BY hour
        ORDER BY hour
    """).fetchall()
    
    if not hourly:
        return {'status': 'NO_DATA'}
    
    # Calculate wave metrics
    counts = [r['signal_count'] for r in hourly]
    avg_wave_height = sum(counts) / len(counts) if counts else 0
    max_wave = max(counts) if counts else 0
    min_wave = min(counts) if counts else 0
    
    # Wave consistency (coefficient of variation — lower = more consistent)
    if avg_wave_height > 0:
        variance = sum((x - avg_wave_height) ** 2 for x in counts) / len(counts)
        std_dev = variance ** 0.5
        cv = std_dev / avg_wave_height
    else:
        cv = 0
    
    # Wave height classification
    if avg_wave_height > 300:
        wave_state = "HEAVY SWELL (300+ signals/hr)"
        emoji = "🌊🌊🌊"
    elif avg_wave_height > 200:
        wave_state = "MODERATE SWELL (200-300 signals/hr)"
        emoji = "🌊🌊"
    elif avg_wave_height > 100:
        wave_state = "SMALL SWELL (100-200 signals/hr)"
        emoji = "🌊"
    else:
        wave_state = "CALM SEA (<100 signals/hr)"
        emoji = "🏖️"
    
    # Consistency rating
    if cv < 0.3:
        consistency = "CLEAN & CONSISTENT"
    elif cv < 0.5:
        consistency = "MODERATELY CONSISTENT"
    else:
        consistency = "CHAOTIC / WHITewater"
    
    # Direction of swell (are longs or shorts dominating the wave?)
    avg_long_ratio = sum(r['long_ratio'] for r in hourly if r['long_ratio']) / len(hourly)
    
    return {
        'wave_state': wave_state,
        'emoji': emoji,
        'avg_wave_height': round(avg_wave_height, 1),
        'max_wave': max_wave,
        'min_wave': min_wave,
        'consistency': consistency,
        'cv': round(cv, 2),
        'avg_long_ratio': round(avg_long_ratio * 100, 1),
        'hours_analyzed': len(hourly),
    }

def analyze_wind(conn):
    """
    WIND ANALYSIS — Momentum and velocity.
    Like reading wind: sustained speed vs gusts.
    """
    # Token speed statistics
    speeds = conn.execute("""
        SELECT 
            speed_percentile,
            price_velocity_5m,
            price_acceleration,
            is_stale,
            wave_phase,
            momentum_score
        FROM token_speeds
    """).fetchall()
    
    if not speeds:
        return {'status': 'NO_DATA'}
    
    velocities = [abs(r['price_velocity_5m']) for r in speeds if r['price_velocity_5m'] is not None]
    accelerations = [r['price_acceleration'] for r in speeds if r['price_acceleration'] is not None]
    stale_count = sum(1 for r in speeds if r['is_stale'])
    
    # Wave phases
    phases = defaultdict(int)
    for r in speeds:
        if r['wave_phase']:
            phases[r['wave_phase']] += 1
    
    # Speed distribution
    fast = sum(1 for r in speeds if r['speed_percentile'] and r['speed_percentile'] >= 80)
    slow = sum(1 for r in speeds if r['speed_percentile'] and r['speed_percentile'] < 20)
    mid = len(speeds) - fast - slow
    
    avg_vel = sum(velocities) / len(velocities) if velocities else 0
    max_vel = max(velocities) if velocities else 0
    avg_accel = sum(accelerations) / len(accelerations) if accelerations else 0
    
    # Wind classification
    if avg_vel > 1.0:
        wind_state = "STRONG GUSTS (avg >1% moves)"
        emoji = "💨💨💨"
    elif avg_vel > 0.5:
        wind_state = "MODERATE BREEZE (avg 0.5-1% moves)"
        emoji = "💨💨"
    elif avg_vel > 0.2:
        wind_state = "LIGHT AIR (avg 0.2-0.5% moves)"
        emoji = "💨"
    else:
        wind_state = "CALM (avg <0.2% moves)"
        emoji = "🍃"
    
    # Sustained vs gusts
    if velocities:
        sorted_vel = sorted(velocities)
        p50 = sorted_vel[len(sorted_vel) // 2]  # median = sustained
        p95 = sorted_vel[int(len(sorted_vel) * 0.95)]  # 95th percentile = gusts
    else:
        p50 = p95 = 0
    
    return {
        'wind_state': wind_state,
        'emoji': emoji,
        'sustained_speed': round(p50, 4),
        'gust_speed': round(p95, 4),
        'avg_velocity': round(avg_vel, 4),
        'max_velocity': round(max_vel, 4),
        'avg_acceleration': round(avg_accel, 4),
        'acceleration_trend': 'BULLISH' if avg_accel > 0 else 'BEARISH',
        'stale_tokens': stale_count,
        'total_tokens': len(speeds),
        'fast_tokens': fast,
        'slow_tokens': slow,
        'mid_tokens': mid,
        'phases': dict(phases),
    }

def analyze_sea_state(conn):
    """
    SEA STATE — Overall market health and regime.
    Like reading sea state: calm, moderate, rough, or extreme.
    """
    # Recent signal outcomes (last 14 days)
    outcomes = conn.execute("""
        SELECT 
            DATE(created_at) as day,
            COUNT(*) as trades,
            SUM(is_win) as wins,
            SUM(pnl_pct) as total_pnl,
            AVG(pnl_pct) as avg_pnl
        FROM signal_outcomes
        WHERE created_at >= datetime('now', '-14 days')
        GROUP BY day
        ORDER BY day
    """).fetchall()
    
    if not outcomes:
        return {'status': 'NO_DATA'}
    
    total_trades = sum(r['trades'] for r in outcomes)
    total_wins = sum(r['wins'] for r in outcomes)
    total_pnl = sum(r['total_pnl'] for r in outcomes)
    winrate = 100.0 * total_wins / total_trades if total_trades else 0
    
    # Daily PnL trend (are we getting better or worse?)
    if len(outcomes) >= 3:
        early_pnl = sum(r['total_pnl'] for r in outcomes[:len(outcomes)//3])
        late_pnl = sum(r['total_pnl'] for r in outcomes[-len(outcomes)//3:])
        trend = 'IMPROVING' if late_pnl > early_pnl else 'DETERIORATING'
    else:
        trend = 'INSUFFICIENT_DATA'
    
    # Sea state classification
    if winrate > 55 and total_pnl > 0:
        sea_state = "FAVORABLE — Good conditions for trading"
        emoji = "☀️🌊"
    elif winrate > 45:
        sea_state = "MODERATE — Mixed conditions, selective trading"
        emoji = "⛅🌊"
    elif winrate > 35:
        sea_state = "ROUGH — Difficult conditions, reduce exposure"
        emoji = "🌧️🌊"
    else:
        sea_state = "STORM — Very difficult, consider sitting out"
        emoji = "⛈️🌊"
    
    # Best performing days
    good_days = [r for r in outcomes if r['total_pnl'] > 0]
    bad_days = [r for r in outcomes if r['total_pnl'] < 0]
    
    return {
        'sea_state': sea_state,
        'emoji': emoji,
        'total_trades_14d': total_trades,
        'winrate_14d': round(winrate, 1),
        'total_pnl_14d': round(total_pnl, 2),
        'avg_daily_pnl': round(total_pnl / len(outcomes), 2),
        'good_days': len(good_days),
        'bad_days': len(bad_days),
        'trend': trend,
        'best_day_pnl': round(max(r['total_pnl'] for r in outcomes), 2) if outcomes else 0,
        'worst_day_pnl': round(min(r['total_pnl'] for r in outcomes), 2) if outcomes else 0,
    }

def analyze_lightning(conn):
    """
    LIGHTNING STRIKES — Crash and pump events.
    Like tracking lightning: where did the bolts hit, and what came before?
    """
    # Find extreme PnL events (big wins and big losses)
    extreme_events = conn.execute("""
        SELECT 
            token,
            direction,
            signal_type,
            pnl_pct,
            confidence,
            created_at,
            is_win
        FROM signal_outcomes
        WHERE ABS(pnl_pct) > 2.0
        ORDER BY created_at
    """).fetchall()
    
    # Find tokens with repeated crashes (multiple losses)
    crash_patterns = conn.execute("""
        SELECT 
            token,
            COUNT(*) as total_trades,
            SUM(is_win) as wins,
            SUM(pnl_pct) as total_pnl,
            AVG(pnl_pct) as avg_pnl,
            MIN(pnl_pct) as worst_loss
        FROM signal_outcomes
        GROUP BY token
        HAVING total_trades >= 3
        ORDER BY total_pnl ASC
        LIMIT 10
    """).fetchall()
    
    # Find tokens with repeated pumps (multiple wins)
    pump_patterns = conn.execute("""
        SELECT 
            token,
            COUNT(*) as total_trades,
            SUM(is_win) as wins,
            SUM(pnl_pct) as total_pnl,
            AVG(pnl_pct) as avg_pnl,
            MAX(pnl_pct) as best_win
        FROM signal_outcomes
        GROUP BY token
        HAVING total_trades >= 3
        ORDER BY total_pnl DESC
        LIMIT 10
    """).fetchall()
    
    return {
        'extreme_events_count': len(extreme_events),
        'big_wins': len([e for e in extreme_events if e['pnl_pct'] > 0]),
        'big_losses': len([e for e in extreme_events if e['pnl_pct'] < 0]),
        'crash_tokens': [dict(r) for r in crash_patterns],
        'pump_tokens': [dict(r) for r in pump_patterns],
    }

def analyze_swell_period(conn):
    """
    SWELL PERIOD — Time between signal clusters.
    Like reading swell period: longer period = more organized, powerful swell.
    """
    # Signal spacing analysis
    signals = conn.execute("""
        SELECT created_at, token, direction, signal_type
        FROM signals
        WHERE created_at >= datetime('now', '-7 days')
        ORDER BY created_at
    """).fetchall()
    
    if len(signals) < 2:
        return {'status': 'INSUFFICIENT_DATA'}
    
    # Calculate time gaps between consecutive signals
    from datetime import datetime
    gaps = []
    for i in range(1, len(signals)):
        t1 = datetime.strptime(signals[i-1]['created_at'], '%Y-%m-%d %H:%M:%S')
        t2 = datetime.strptime(signals[i]['created_at'], '%Y-%m-%d %H:%M:%S')
        gap_seconds = (t2 - t1).total_seconds()
        gaps.append(gap_seconds)
    
    if not gaps:
        return {'status': 'NO_GAPS'}
    
    avg_gap = sum(gaps) / len(gaps)
    min_gap = min(gaps)
    max_gap = max(gaps)
    
    # Swell period classification (in seconds)
    if avg_gap < 30:
        period_state = "SHORT PERIOD — Choppy, confused seas"
        emoji = "🌊〰️🌊"
    elif avg_gap < 60:
        period_state = "MEDIUM PERIOD — Organizing swell"
        emoji = "🌊〰️〰️🌊"
    else:
        period_state = "LONG PERIOD — Clean, powerful swell"
        emoji = "🌊〰️〰️〰️🌊"
    
    return {
        'period_state': period_state,
        'emoji': emoji,
        'avg_gap_seconds': round(avg_gap, 1),
        'min_gap_seconds': round(min_gap, 1),
        'max_gap_seconds': round(max_gap, 1),
        'signals_per_minute': round(60 / avg_gap, 2) if avg_gap > 0 else 0,
    }

def analyze_correlations(conn):
    """
    SIGNAL CORRELATIONS — Which signals appear together?
    Like reading weather patterns: when wind is from the NW, rain often follows.
    """
    # Signal type co-occurrence (same token, within 1 hour)
    cooccur = conn.execute("""
        SELECT 
            s1.signal_type as type_a,
            s2.signal_type as type_b,
            COUNT(*) as co_count
        FROM signals s1
        JOIN signals s2 ON s1.token = s2.token 
            AND s1.direction = s2.direction
            AND s2.created_at > s1.created_at
            AND s2.created_at <= datetime(s1.created_at, '+1 hour')
            AND s1.id != s2.id
        WHERE s1.created_at >= datetime('now', '-14 days')
        GROUP BY s1.signal_type, s2.signal_type
        HAVING co_count >= 5
        ORDER BY co_count DESC
        LIMIT 20
    """).fetchall()
    
    return {
        'co_occurrences': [dict(r) for r in cooccur],
    }

def generate_weather_report(conn):
    """Generate the complete weather report."""
    print("=" * 70)
    print("🌊🌊🌊 HERMES MARKET WEATHER STATION 🌊🌊🌊")
    print(f"   Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)
    
    # 1. TIDE
    print("\n" + "─" * 70)
    print("📊 TIDE DIRECTION — Market Flow")
    print("─" * 70)
    tide = analyze_tide(conn)
    for period, data in tide.items():
        print(f"  {period:>4}: {data['emoji']} {data['tide']}")
        print(f"        Long: {data['long_pct']}% | Short: {data['short_pct']}% | Signals: {data['total_signals']}")
        print(f"        Imbalance: {data['imbalance']:.0%} {'⚠️ HEAVY' if data['imbalance'] > 0.2 else '✅ BALANCED'}")
    
    # 2. WAVES
    print("\n" + "─" * 70)
    print("🌊 WAVE HEIGHT — Signal Intensity")
    print("─" * 70)
    waves = analyze_waves(conn)
    if waves.get('status') != 'NO_DATA':
        print(f"  {waves['emoji']} {waves['wave_state']}")
        print(f"  Average: {waves['avg_wave_height']} signals/hr | Peak: {waves['max_wave']} | Low: {waves['min_wave']}")
        print(f"  Consistency: {waves['consistency']} (CV: {waves['cv']})")
        print(f"  Swell Direction: {waves['avg_long_ratio']}% LONG bias")
    
    # 3. WIND
    print("\n" + "─" * 70)
    print("💨 WIND — Momentum & Velocity")
    print("─" * 70)
    wind = analyze_wind(conn)
    if wind.get('status') != 'NO_DATA':
        print(f"  {wind['emoji']} {wind['wind_state']}")
        print(f"  Sustained: {wind['sustained_speed']:.2%} | Gusts: {wind['gust_speed']:.2%}")
        print(f"  Acceleration Trend: {wind['acceleration_trend']}")
        print(f"  Stale Tokens: {wind['stale_tokens']}/{wind['total_tokens']} ({100*wind['stale_tokens']/wind['total_tokens']:.0f}%)")
        print(f"  Fast: {wind['fast_tokens']} | Mid: {wind['mid_tokens']} | Slow: {wind['slow_tokens']}")
        print(f"  Wave Phases: {wind['phases']}")
    
    # 4. SWELL PERIOD
    print("\n" + "─" * 70)
    print("〰️ SWELL PERIOD — Signal Spacing")
    print("─" * 70)
    swell = analyze_swell_period(conn)
    if swell.get('status') not in ('INSUFFICIENT_DATA', 'NO_GAPS'):
        print(f"  {swell['emoji']} {swell['period_state']}")
        print(f"  Avg Gap: {swell['avg_gap_seconds']:.0f}s | Min: {swell['min_gap_seconds']:.0f}s | Max: {swell['max_gap_seconds']:.0f}s")
        print(f"  Signal Rate: {swell['signals_per_minute']:.1f}/min")
    
    # 5. SEA STATE
    print("\n" + "─" * 70)
    print("⚓ SEA STATE — Overall Market Health")
    print("─" * 70)
    sea = analyze_sea_state(conn)
    if sea.get('status') != 'NO_DATA':
        print(f"  {sea['emoji']} {sea['sea_state']}")
        print(f"  Winrate (14d): {sea['winrate_14d']}% | Trades: {sea['total_trades_14d']}")
        print(f"  Total PnL (14d): {sea['total_pnl_14d']:.2f}% | Avg Daily: {sea['avg_daily_pnl']:.2f}%")
        print(f"  Good Days: {sea['good_days']} | Bad Days: {sea['bad_days']}")
        print(f"  Trend: {sea['trend']}")
        print(f"  Best Day: {sea['best_day_pnl']:.2f}% | Worst Day: {sea['worst_day_pnl']:.2f}%")
    
    # 6. LIGHTNING
    print("\n" + "─" * 70)
    print("⚡ LIGHTNING — Crash & Pump Events")
    print("─" * 70)
    lightning = analyze_lightning(conn)
    print(f"  Extreme Events (|PnL| > 2%): {lightning['extreme_events_count']}")
    print(f"  Big Wins: {lightning['big_wins']} | Big Losses: {lightning['big_losses']}")
    
    if lightning['crash_tokens']:
        print(f"\n  🔴 CRASH MAGNETS (repeated losses):")
        for t in lightning['crash_tokens'][:5]:
            print(f"     {t['token']:>8}: {t['total_trades']} trades, {t['wins']}/{t['total_trades']} wins, "
                  f"PnL: {t['total_pnl']:.2f}%, worst: {t['worst_loss']:.2f}%")
    
    if lightning['pump_tokens']:
        print(f"\n  🟢 PUMP MAGNETS (repeated wins):")
        for t in lightning['pump_tokens'][:5]:
            print(f"     {t['token']:>8}: {t['total_trades']} trades, {t['wins']}/{t['total_trades']} wins, "
                  f"PnL: {t['total_pnl']:.2f}%, best: {t['best_win']:.2f}%")
    
    # 7. CORRELATIONS
    print("\n" + "─" * 70)
    print("🔗 SIGNAL CORRELATIONS — Pattern Recognition")
    print("─" * 70)
    corr = analyze_correlations(conn)
    if corr['co_occurrences']:
        print(f"  Top co-occurring signal pairs (same token, within 1hr):")
        for c in corr['co_occurrences'][:10]:
            print(f"     {c['type_a']:<30} + {c['type_b']:<30} = {c['co_count']}x")
    
    # SUMMARY
    print("\n" + "=" * 70)
    print("📋 WEATHER SUMMARY")
    print("=" * 70)
    
    # Overall condition rating
    conditions = []
    if tide.get('24h', {}).get('imbalance', 0) > 0.2:
        conditions.append(f"Strong {tide['24h']['tide'].split('(')[1].replace(')', '')} tide")
    else:
        conditions.append("Balanced tide")
    
    conditions.append(f"Waves: {waves.get('wave_state', 'N/A').split('(')[0].strip()}")
    conditions.append(f"Wind: {wind.get('wind_state', 'N/A').split('(')[0].strip()}")
    conditions.append(f"Sea: {sea.get('sea_state', 'N/A').split('—')[0].strip()}")
    
    print(f"  {' | '.join(conditions)}")
    
    # Trading recommendation
    print(f"\n  🎯 TRADING RECOMMENDATION:")
    if sea.get('winrate_14d', 0) > 50 and sea.get('total_pnl_14d', 0) > 0:
        print(f"  ✅ CONDITIONS FAVORABLE — Standard position sizing")
    elif sea.get('winrate_14d', 0) > 40:
        print(f"  ⚠️ MIXED CONDITIONS — Reduce size, be selective")
    else:
        print(f"  🛑 DIFFICULT CONDITIONS — Consider sitting out or paper trading")
    
    print("\n" + "=" * 70)
    print("🌊 End of Weather Report 🌊")
    print("=" * 70)

def main():
    """Main entry point."""
    conn = get_db()
    try:
        generate_weather_report(conn)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
