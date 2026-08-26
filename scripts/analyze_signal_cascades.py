#!/usr/bin/env python3
"""
Signal Cascade Analysis — Deep dive into signal sequence patterns.
Focuses on:
1. What signals appear BEFORE/after big moves
2. "Signal lifecycle" — which signal families are early vs late market indicators
3. Market phase detection via signal composition
"""

import sqlite3
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from paths import RUNTIME_DB

def get_daily_family_data():
    """Get daily family counts for analysis."""
    conn = None
    try:
        conn = sqlite3.connect(RUNTIME_DB)
        c = conn.cursor()
        
        c.execute('''
            SELECT signal_type, created_at
            FROM signals 
            WHERE created_at >= date('now', '-30 days')
            ORDER BY created_at ASC
        ''')
        
        daily = defaultdict(lambda: defaultdict(int))
        days_set = set()
        
        for sig_type, created_at in c.fetchall():
            day = created_at[:10]
            days_set.add(day)
            daily[day][sig_type] += 1
        
        return daily, sorted(days_set)
    finally:
        if conn:
            conn.close()

def signal_family(sig_type):
    """Categorize signals into families."""
    families = {
        'Momentum': ['momentum', 'fast_momentum', 'mtf_momentum', 'velocity', 'phase_accel'],
        'MACD': ['hmacd', 'macd_accel', 'macd_1m', 'mtf_macd', 'macd_divergence_short', 'macd_divergence_long'],
        'Bollinger': ['bb_bounce', 'bb_bounce_short', 'bollinger_squeeze_long', 'bollinger_squeeze_short'],
        'Trend/MA': ['ma_cross', 'ma_cross_5m', 'ema9_sma20', 'ema20_50', 'ema_angle', 
                      'ma_100_cross', 'ma_100_cross_long', 'ma_100_cross_short', 'ma_100_bounce'],
        'Range': ['range_finder', 'range_finder_short', 'range_breakout', 'range_breakout_short'],
        'ZScore': ['zscore_rising', 'zscore_rising_long', 'zscore_rising_short', 'hzscore', 'mtp_zscore'],
        'Exhaustion': ['exhaustion', 'return_exhaustion', 'return_exhaustion_short', 'return_exhaustion_long',
                        'spike_exhaustion_short'],
        'R2': ['r2_rev', 'r2_trend', 'r2_trend_long', 'r2_trend_short'],
        'Accelerate': ['accel_300', 'accel_300_long', 'accel_300_short', 'inverse_accel_300_long', 'inverse_accel_300_short'],
        'Squeeze': ['squeeze_cross', 'bollinger_squeeze_long', 'bollinger_squeeze_short', 'atr_compression'],
        'Trendline': ['tl_break', 'tl_break_long', 'tl_break_short', 'vortex_break_long', 'vortex_break_short'],
        'Mover': ['mover_long', 'mover_short', 'coin_tracker_hot_long', 'coin_tracker_hot_short', 'coin_tracker_hot'],
        'Pattern': ['pattern_wolf', 'pattern_micro_flag', 'pattern_channel_long', 'pattern_channel_short',
                     'hh_hl_choch', 'hh_hl_breakout', 'engulfing_long', 'engulfing_short'],
        'HL_Copy': ['hl_copy_plus', 'hl_copy_minus'],
        'Support/Resistance': ['support_resistance'],
        'Hot_Set': ['hot-set'],
        'Continuation': ['continuation_long', 'continuation_short'],
        'Wave': ['wave_catcher_long', 'wave_catcher_short', 'trend_momentum_near_sma', 'guppy'],
        'Stop_Hunt': ['stop_hunt_reversal_long', 'liquidation_hunt_long', 'liquidation_hunt_short'],
        'Confluence': ['signal_confluence'],
        'Volume': ['volume_hl', 'pump_catcher_long'],
        'ATR': ['atr_spike_long'],
    }
    for family, members in families.items():
        if sig_type in members:
            return family
    return 'Other'

def analyze_market_phases(daily, days):
    """Detect market phases based on signal composition changes."""
    print("="*120)
    print("🔍 MARKET PHASE ANALYSIS — Phases detected from signal patterns")
    print("="*120)
    
    # Build daily family activity (normalized)
    family_norm = defaultdict(lambda: defaultdict(float))
    for day in days:
        total = sum(daily[day].values())
        if total == 0:
            continue
        for sig_type, count in daily[day].items():
            fam = signal_family(sig_type)
            family_norm[fam][day] = count / total
    
    # Classify each day into a market phase
    phases = []
    for day in days:
        total = sum(daily[day].values())
        if total < 100:
            phases.append((day, 'Quiet', total, ''))
            continue
        
        top_families = sorted(family_norm.items(), key=lambda x: -x[1].get(day, 0))[:5]
        top_names = [(f, family_norm[f].get(day, 0)) for f, _ in top_families if family_norm[f].get(day, 0) > 0.05]
        
        # Classify phase
        dominant = top_names[0][0] if top_names else 'Unknown'
        
        # Check for specific patterns
        zscore_dominant = any('ZScore' in n for n, _ in top_names if _ > 0.15)
        momentum_dominant = any('Momentum' in n or 'Accelerate' in n for n, _ in top_names if _ > 0.15)
        trend_dominant = any('Trend' in n or 'MA' in n for n, _ in top_names if _ > 0.15)
        range_dominant = any('Range' in n or 'Bollinger' in n for n, _ in top_names if _ > 0.15)
        exhaustion_present = any('Exhaustion' in n for n, _ in top_names if _ > 0.08)
        mover_active = any('Mover' in n for n, _ in top_names if _ > 0.15)
        
        if zscore_dominant:
            phase = 'ZScore Surge'
        elif momentum_dominant and trend_dominant:
            phase = 'Trend Building'
        elif momentum_dominant:
            phase = 'Momentum Explosion'
        elif range_dominant and exhaustion_present:
            phase = 'Exhaustion/Range'
        elif range_dominant:
            phase = 'Range-Bound'
        elif mover_active:
            phase = 'Mover Hunting'
        elif trend_dominant:
            phase = 'Trend Following'
        elif dominant in ['Hot_Set', 'Support/Resistance']:
            phase = 'Reactive/Defensive'
        else:
            phase = f'{dominant}-Led'
        
        detail = ', '.join(f"{n}({_*100:.0f}%)" for n, _ in top_names[:3])
        phases.append((day, phase, total, detail))
    
    # Print phase timeline
    print(f"\n  {'Date':12s} | {'Phase':25s} | {'Signals':>8s} | Top Signals")
    print("  " + "-"*110)
    
    prev_phase = None
    phase_runs = []
    current_run = None
    
    for day, phase, total, detail in phases:
        marker = " ← CHANGE" if prev_phase and phase != prev_phase else ""
        bar = '█' * min(30, total // 200)
        print(f"  {day:12s} | {phase:25s} | {total:8d} | {detail}{marker}")
        
        # Track phase runs
        if phase != prev_phase:
            if current_run:
                phase_runs.append(current_run)
            current_run = {'phase': phase, 'start': day, 'end': day, 'days': 1, 'total_signals': total}
        else:
            current_run['end'] = day
            current_run['days'] += 1
            current_run['total_signals'] += total
        prev_phase = phase
    
    if current_run:
        phase_runs.append(current_run)
    
    # Print phase summary
    print(f"\n  Phase Duration Summary:")
    print(f"  {'Phase':25s} | {'Start':>12s} | {'End':>12s} | {'Days':>5s} | {'Total Signals':>14s}")
    print("  " + "-"*80)
    for run in sorted(phase_runs, key=lambda x: -x['days']):
        print(f"  {run['phase']:25s} | {run['start']:>12s} | {run['end']:>12s} | {run['days']:5d} | {run['total_signals']:14d}")
    
    return phases

def analyze_signal_lifecycle(daily, days):
    """Determine which signals are 'early', 'mid', or 'late' indicators."""
    print("\n" + "="*120)
    print("🔄 SIGNAL LIFECYCLE — Which signals appear early vs late in market moves?")
    print("="*120)
    
    # Find "events" — days with >2x average total signals
    daily_totals = [(day, sum(daily[day].values())) for day in days]
    avg_total = sum(t for _, t in daily_totals) / len(daily_totals)
    
    event_days = [day for day, total in daily_totals if total > avg_total * 1.5]
    quiet_days = [day for day, total in daily_totals if total < avg_total * 0.5]
    
    print(f"\n  Average daily signals: {avg_total:.0f}")
    print(f"  High-activity days (>1.5x avg): {len(event_days)}")
    print(f"  Low-activity days (<0.5x avg): {len(quiet_days)}")
    
    # For each event, look at signals in the 3 days before and 3 days after
    print(f"\n  Signal behavior around high-activity days:")
    print(f"  {'Signal Family':25s} | {'3d Before':>10s} | {'Event Day':>10s} | {'3d After':>10s} | {'Pattern':>20s}")
    print("  " + "-"*85)
    
    family_before = defaultdict(list)
    family_event = defaultdict(list)
    family_after = defaultdict(list)
    
    for event_day in event_days:
        event_idx = days.index(event_day) if event_day in days else -1
        if event_idx < 3:
            continue
        
        # Compute family activity in before/event/after windows
        before_days = days[event_idx-3:event_idx]
        after_days = days[event_idx+1:min(event_idx+4, len(days))]
        
        for window, storage in [(before_days, family_before), ([event_day], family_event), (after_days, family_after)]:
            window_totals = defaultdict(int)
            for d in window:
                total = sum(daily[d].values())
                if total == 0:
                    continue
                for sig_type, count in daily[d].items():
                    fam = signal_family(sig_type)
                    window_totals[fam] += count / max(total, 1)
            
            for fam, val in window_totals.items():
                storage[fam].append(val / max(len(window), 1))
    
    results = []
    for fam in set(list(family_before.keys()) + list(family_event.keys())):
        before_avg = sum(family_before[fam]) / len(family_before[fam]) if family_before[fam] else 0
        event_avg = sum(family_event[fam]) / len(family_event[fam]) if family_event[fam] else 0
        after_avg = sum(family_after[fam]) / len(family_after[fam]) if family_after[fam] else 0
        
        # Classify
        if event_avg > before_avg * 1.5 and event_avg > after_avg * 1.5:
            pattern = "PEAK at event"
        elif before_avg > event_avg * 1.3:
            pattern = "EARLY (before event)"
        elif after_avg > event_avg * 1.3:
            pattern = "LAGGING (after event)"
        elif event_avg > before_avg and after_avg > event_avg:
            pattern = "BUILDING"
        elif before_avg > event_avg and after_avg < before_avg:
            pattern = "FADING"
        else:
            pattern = "STEADY"
        
        results.append((fam, before_avg, event_avg, after_avg, pattern))
    
    results.sort(key=lambda x: x[2], reverse=True)
    for fam, before, event, after, pattern in results:
        print(f"  {fam:25s} | {before*100:9.1f}% | {event*100:9.1f}% | {after*100:9.1f}% | {pattern:>20s}")

def analyze_transition_matrix(daily, days):
    """Build a transition matrix: given today's dominant family, what's tomorrow's?"""
    print("\n" + "="*120)
    print("📊 SIGNAL FAMILY TRANSITION MATRIX — What follows what?")
    print("="*120)
    
    # Get daily dominant family
    dominant_chain = []
    for day in days:
        total = sum(daily[day].values())
        if total < 100:
            dominant_chain.append(('Quiet', day))
            continue
        
        family_counts = Counter()
        for sig_type, count in daily[day].items():
            family_counts[signal_family(sig_type)] += count
        
        top = family_counts.most_common(1)[0][0]
        dominant_chain.append((top, day))
    
    # Build transition counts
    transitions = defaultdict(lambda: defaultdict(int))
    for i in range(len(dominant_chain) - 1):
        current_fam = dominant_chain[i][0]
        next_fam = dominant_chain[i+1][0]
        transitions[current_fam][next_fam] += 1
    
    # Print matrix
    families = sorted(set(f for fam_dict in transitions.values() for f in fam_dict))
    families = [f for f in families if f != 'Quiet'] + (['Quiet'] if 'Quiet' in families else [])
    
    print(f"\n  Given today's dominant family → Most likely tomorrow's dominant family:")
    print(f"  {'From':25s} | {'To':25s} | {'Count':>5s} | {'%':>5s}")
    print("  " + "-"*65)
    
    for from_fam in sorted(transitions.keys()):
        total_from = sum(transitions[from_fam].values())
        if total_from < 2:
            continue
        sorted_to = sorted(transitions[from_fam].items(), key=lambda x: -x[1])
        top_to = sorted_to[0]
        pct = top_to[1] / total_from * 100
        print(f"  {from_fam:25s} → {top_to[0]:25s} | {top_to[1]:5d} | {pct:5.1f}%")

def analyze_confluence_opportunities(daily, days):
    """Find days where multiple families spike simultaneously — confluence zones."""
    print("\n" + "="*120)
    print("🎯 CONFLUENCE ZONES — Days with multiple family spikes (= best trade setups)")
    print("="*120)
    
    # Compute daily family activity and z-scores
    family_daily = defaultdict(list)
    for day in days:
        total = sum(daily[day].values())
        for sig_type, count in daily[day].items():
            fam = signal_family(sig_type)
            # Normalize to percentage
            pct = count / max(total, 1) * 100
            family_daily[fam].append((day, pct))
    
    # Find days where 3+ families are >1 std above their mean
    print(f"\n  Days with 3+ families at >1σ above their mean activity:")
    print(f"  {'Date':12s} | {'# Families Spiking':>18s} | {'Spiking Families'}")
    print("  " + "-"*100)
    
    for i, day in enumerate(days):
        total = sum(daily[day].values())
        if total < 500:
            continue
        
        spiking = []
        for fam, day_vals in family_daily.items():
            vals = [v for _, v in day_vals]
            if len(vals) < 5:
                continue
            mean = sum(vals) / len(vals)
            std = (sum((v - mean)**2 for v in vals) / len(vals)) ** 0.5
            if std > 0:
                today_pct = daily[day].get(fam, 0) / max(total, 1) * 100
                # Use today's count / total as the family percentage
                fam_today = sum(v for sig_type, v in daily[day].items() if signal_family(sig_type) == fam) / max(total, 1) * 100
                if fam_today > mean + std:
                    spiking.append(f"{fam}({fam_today:.0f}%)")
        
        if len(spiking) >= 3:
            print(f"  {day:12s} | {len(spiking):>18d} | {', '.join(spiking)}")

def main():
    print("🔬 HERMES SIGNAL CASCADE DEEP DIVE")
    print("="*120)
    
    daily, days = get_daily_family_data()
    
    analyze_market_phases(daily, days)
    analyze_signal_lifecycle(daily, days)
    analyze_transition_matrix(daily, days)
    analyze_confluence_opportunities(daily, days)
    
    print("\n" + "="*120)
    print("✅ CASCADE ANALYSIS COMPLETE")
    print("="*120)

if __name__ == '__main__':
    main()
