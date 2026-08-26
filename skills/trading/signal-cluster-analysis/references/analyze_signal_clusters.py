#!/usr/bin/env python3
"""
Signal Cluster Analysis — Look for temporal patterns in signal generation.
Analyzes last 30 days of signals to find:
1. Daily signal type distributions (which signals spike on which days)
2. Sequential patterns (signal A waves followed by signal B waves)
3. Correlation between signal type activity levels
4. "Signal regime" detection — periods dominated by specific signal families
"""

import sqlite3
import json
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from paths import RUNTIME_DB

def get_signal_data():
    """Get all signals from last 30 days with timestamps."""
    conn = sqlite3.connect(RUNTIME_DB)
    c = conn.cursor()
    
    c.execute('''
        SELECT signal_type, token, direction, confidence, created_at, 
               decision, z_score, momentum_state, price
        FROM signals 
        WHERE created_at >= date('now', '-30 days')
        ORDER BY created_at ASC
    ''')
    
    rows = c.fetchall()
    conn.close()
    return rows

def group_by_day(rows):
    """Group signals by day."""
    daily = defaultdict(lambda: defaultdict(list))
    for row in rows:
        sig_type, token, direction, conf, created_at, decision, zscore, mom, price = row
        day = created_at[:10]  # YYYY-MM-DD
        daily[day][sig_type].append(row)
    return daily

def group_by_6h_window(rows):
    """Group signals into 6-hour windows for finer granularity."""
    windows = defaultdict(lambda: defaultdict(list))
    for row in rows:
        sig_type, token, direction, conf, created_at, decision, zscore, mom, price = row
        dt = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
        # Round to nearest 6h window
        hour = (dt.hour // 6) * 6
        window_key = f"{dt.strftime('%Y-%m-%d')} {hour:02d}:00"
        windows[window_key][sig_type].append(row)
    return windows

def signal_family(sig_type):
    """Categorize signals into families/groups."""
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

def analyze_daily_dominance(daily):
    """Find which signal families dominate each day."""
    print("\n" + "="*120)
    print("📊 DAILY SIGNAL FAMILY DOMINANCE (Top 3 families per day)")
    print("="*120)
    
    day_families = {}
    for day in sorted(daily.keys()):
        family_counts = Counter()
        for sig_type, signals in daily[day].items():
            fam = signal_family(sig_type)
            family_counts[fam] += len(signals)
        
        day_families[day] = family_counts
        top3 = family_counts.most_common(3)
        total = sum(family_counts.values())
        bars = []
        for fam, cnt in top3:
            pct = cnt / total * 100
            bar = '█' * int(pct / 2)
            bars.append(f"{fam}: {cnt} ({pct:.0f}%) {bar}")
        
        print(f"  {day} | Total: {total:5d} | {' | '.join(bars)}")
    
    return day_families

def analyze_signal_waves(daily):
    """Detect 'waves' — periods where a signal type spikes then fades."""
    print("\n" + "="*120)
    print("🌊 SIGNAL WAVES — Detecting spike-and-fade patterns (>2x avg on consecutive days)")
    print("="*120)
    
    days_sorted = sorted(daily.keys())
    if len(days_sorted) < 3:
        print("  Not enough data for wave detection")
        return
    
    # Compute per-signal-type daily counts
    signal_daily_counts = defaultdict(lambda: defaultdict(int))
    for day in days_sorted:
        for sig_type, signals in daily[day].items():
            signal_daily_counts[sig_type][day] = len(signals)
    
    # Detect waves: find signals that spike >2x their rolling 3-day average
    waves = []
    for sig_type in signal_daily_counts:
        counts = [signal_daily_counts[sig_type].get(d, 0) for d in days_sorted]
        
        for i in range(3, len(counts)):
            rolling_avg = sum(counts[i-3:i]) / 3 if sum(counts[i-3:i]) > 0 else 1
            if counts[i] > rolling_avg * 2 and counts[i] >= 50:  # significant spike
                waves.append({
                    'signal': sig_type,
                    'day': days_sorted[i],
                    'count': counts[i],
                    'avg': rolling_avg,
                    'ratio': counts[i] / rolling_avg if rolling_avg > 0 else float('inf'),
                    'family': signal_family(sig_type)
                })
    
    waves.sort(key=lambda x: x['day'])
    
    # Group by day
    waves_by_day = defaultdict(list)
    for w in waves:
        waves_by_day[w['day']].append(w)
    
    for day in sorted(waves_by_day.keys()):
        day_waves = waves_by_day[day]
        print(f"\n  📅 {day}:")
        for w in sorted(day_waves, key=lambda x: -x['ratio']):
            print(f"    🔥 {w['signal']:35s} | {w['count']:4d} signals ({w['ratio']:.1f}x avg) | Family: {w['family']}")

def analyze_sequential_patterns(daily):
    """Look for sequential patterns — does signal family A spike, then family B?"""
    print("\n" + "="*120)
    print("🔗 SEQUENTIAL PATTERN ANALYSIS — Does one family's spike predict another?")
    print("="*120)
    
    days_sorted = sorted(daily.keys())
    
    # Compute daily family activity (normalized by total signals that day)
    family_activity = defaultdict(lambda: defaultdict(float))
    for day in days_sorted:
        total = sum(len(sigs) for sigs in daily[day].values())
        if total == 0:
            continue
        for sig_type, signals in daily[day].items():
            fam = signal_family(sig_type)
            family_activity[fam][day] += len(signals) / total
    
    # For each pair of families, compute lagged correlation
    families = sorted(family_activity.keys())
    
    print("\n  Top leading indicators (family activity on day N predicts other families on day N+1, N+2):")
    print(f"  {'Leading Family':30s} | {'Lag':>4s} | {'Following Family':30s} | {'Correlation':>10s}")
    print("  " + "-"*85)
    
    correlations = []
    for fam_a in families:
        for lag in [1, 2, 3]:
            for fam_b in families:
                if fam_a == fam_b:
                    continue
                
                # Get values aligned with lag
                vals_a = []
                vals_b = []
                for i, day in enumerate(days_sorted):
                    next_day_idx = i + lag
                    if next_day_idx < len(days_sorted):
                        a_val = family_activity[fam_a].get(day, 0)
                        b_val = family_activity[fam_b].get(days_sorted[next_day_idx], 0)
                        if a_val > 0 or b_val > 0:  # skip days with no activity
                            vals_a.append(a_val)
                            vals_b.append(b_val)
                
                if len(vals_a) < 5:
                    continue
                
                # Simple Pearson correlation
                mean_a = sum(vals_a) / len(vals_a)
                mean_b = sum(vals_b) / len(vals_b)
                std_a = (sum((x - mean_a)**2 for x in vals_a) / len(vals_a)) ** 0.5
                std_b = (sum((x - mean_b)**2 for x in vals_b) / len(vals_b)) ** 0.5
                
                if std_a > 0 and std_b > 0:
                    cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(vals_a, vals_b)) / len(vals_a)
                    corr = cov / (std_a * std_b)
                    if abs(corr) > 0.3:
                        correlations.append((fam_a, lag, fam_b, corr))
    
    correlations.sort(key=lambda x: -abs(x[3]))
    seen = set()
    for fam_a, lag, fam_b, corr in correlations[:30]:
        key = (fam_a, lag, fam_b)
        if key not in seen:
            seen.add(key)
            direction = "↑ positive" if corr > 0 else "↓ inverse"
            print(f"  {fam_a:30s} | +{lag}d  | {fam_b:30s} | {corr:+.3f} ({direction})")

def analyze_co_signal_patterns(daily):
    """Look for which signals tend to fire together on the same coins."""
    print("\n" + "="*120)
    print("🎯 CO-SIGNAL PATTERNS — Signals that fire on the same coin within 1 day")
    print("="*120)
    
    # Build token -> [(signal_type, day)] mapping
    token_signals = defaultdict(list)
    
    # Re-read to get per-token per-day data
    conn = sqlite3.connect(RUNTIME_DB)
    c = conn.cursor()
    c.execute('''
        SELECT token, signal_type, created_at
        FROM signals 
        WHERE created_at >= date('now', '-30 days')
    ''')
    
    for token, sig_type, created_at in c.fetchall():
        day = created_at[:10]
        token_signals[(token, day)].append(sig_type)
    
    conn.close()
    
    # Count co-occurrences
    co_signal_counts = Counter()
    pair_total_days = Counter()
    
    for (token, day), sig_types in token_signals.items():
        unique_sigs = list(set(sig_types))
        if len(unique_sigs) > 1:
            for i in range(len(unique_sigs)):
                for j in range(i+1, len(unique_sigs)):
                    pair = tuple(sorted([unique_sigs[i], unique_sigs[j]]))
                    co_signal_counts[pair] += 1
        
        # Count how many days each signal pair could co-occur
        for st in unique_sigs:
            for st2 in unique_sigs:
                if st < st2:
                    pair_total_days[(st, st2)] += 1
    
    # Get most frequent co-occurring pairs
    top_pairs = co_signal_counts.most_common(40)
    
    print(f"\n  {'Signal A':40s} | {'Signal B':40s} | {'Co-occurs':>10s} | {'Family A':>15s} | {'Family B':>15s}")
    print("  " + "-"*130)
    
    for (sig_a, sig_b), count in top_pairs:
        print(f"  {sig_a:40s} | {sig_b:40s} | {count:10d} | {signal_family(sig_a):>15s} | {signal_family(sig_b):>15s}")

def analyze_market_regime_signals(daily):
    """Analyze how signal composition changes with market conditions."""
    print("\n" + "="*120)
    print("📈 SIGNAL REGIME TRANSITIONS — How signal mix evolves over time")
    print("="*120)
    
    days_sorted = sorted(daily.keys())
    
    # Compute daily family ratios
    regime_data = []
    for day in days_sorted:
        total = sum(len(sigs) for sigs in daily[day].values())
        if total == 0:
            continue
        
        family_counts = Counter()
        for sig_type, signals in daily[day].items():
            family_counts[signal_family(sig_type)] += len(signals)
        
        # Determine dominant "regime"
        top_families = family_counts.most_common(3)
        regime = '/'.join(f for f, _ in top_families[:2])
        
        regime_data.append({
            'day': day,
            'total': total,
            'regime': regime,
            'top_families': top_families,
            'families': family_counts
        })
    
    # Print regime evolution
    print("\n  Day-by-day regime evolution:")
    prev_regime = None
    for rd in regime_data:
        marker = " ⚡ SHIFT" if prev_regime and rd['regime'] != prev_regime else ""
        total = rd['total']
        bar_len = min(50, total // 100)
        print(f"  {rd['day']} | {rd['regime']:50s} | {total:5d} signals | {'█' * bar_len}{marker}")
        prev_regime = rd['regime']
    
    # Count regime transitions
    transitions = Counter()
    for i in range(1, len(regime_data)):
        prev = regime_data[i-1]['regime']
        curr = regime_data[i]['regime']
        if prev != curr:
            transitions[(prev, curr)] += 1
    
    if transitions:
        print("\n  Most common regime transitions:")
        for (prev, curr), cnt in transitions.most_common(15):
            print(f"    {prev:50s} → {curr:50s} ({cnt}x)")

def analyze_time_of_day_patterns(rows):
    """Check if certain signals cluster at specific times of day."""
    print("\n" + "="*120)
    print("⏰ TIME-OF-DAY PATTERNS — Do certain signals prefer certain hours?")
    print("="*120)
    
    hour_signals = defaultdict(lambda: Counter())
    for row in rows:
        sig_type, _, _, _, created_at, _, _, _, _ = row
        try:
            dt = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
            hour = dt.hour
            hour_signals[hour][sig_type] += 1
        except:
            continue
    
    # For each hour, show top 3 signal types
    print(f"\n  {'Hour (UTC)':>10s} | {'Top Signal Types'}")
    print("  " + "-"*90)
    
    for hour in sorted(hour_signals.keys()):
        total = sum(hour_signals[hour].values())
        top3 = hour_signals[hour].most_common(3)
        sigs = [f"{s}({c})" for s, c in top3]
        print(f"  {hour:10d} | Total: {total:5d} | {', '.join(sigs)}")

def analyze_confidence_trends(daily):
    """Check if confidence levels vary by day or signal type patterns."""
    print("\n" + "="*120)
    print("🎯 CONFIDENCE PATTERNS — Average confidence by day and signal family")
    print("="*120)
    
    conn = sqlite3.connect(RUNTIME_DB)
    c = conn.cursor()
    c.execute('''
        SELECT signal_type, confidence, created_at
        FROM signals 
        WHERE created_at >= date('now', '-30 days')
    ''')
    
    family_conf = defaultdict(list)
    for sig_type, conf, created_at in c.fetchall():
        family_conf[signal_family(sig_type)].append(conf)
    
    conn.close()
    
    print(f"\n  {'Family':30s} | {'Avg Conf':>8s} | {'# Signals':>10s} | {'Min':>6s} | {'Max':>6s}")
    print("  " + "-"*70)
    
    for fam in sorted(family_conf.keys(), key=lambda x: -sum(family_conf[x])/len(family_conf[x])):
        confs = family_conf[fam]
        avg = sum(confs) / len(confs)
        print(f"  {fam:30s} | {avg:8.3f} | {len(confs):10d} | {min(confs):6.3f} | {max(confs):6.3f}")

def analyze_pairwise_family_correlations(daily):
    """Which families tend to be active on the same days?"""
    print("\n" + "="*120)
    print("📊 FAMILY CO-ACTIVITY — Which signal families rise and fall together?")
    print("="*120)
    
    days_sorted = sorted(daily.keys())
    
    # Build daily family counts
    family_daily = defaultdict(lambda: defaultdict(int))
    for day in days_sorted:
        for sig_type, signals in daily[day].items():
            family_daily[signal_family(sig_type)][day] += len(signals)
    
    families = list(family_daily.keys())
    
    # Compute co-activity correlation
    co_correlations = []
    for i in range(len(families)):
        for j in range(i+1, len(families)):
            fam_a, fam_b = families[i], families[j]
            
            vals_a = [family_daily[fam_a].get(d, 0) for d in days_sorted]
            vals_b = [family_daily[fam_b].get(d, 0) for d in days_sorted]
            
            mean_a = sum(vals_a) / len(vals_a) if vals_a else 0
            mean_b = sum(vals_b) / len(vals_b) if vals_b else 0
            std_a = (sum((x - mean_a)**2 for x in vals_a) / len(vals_a)) ** 0.5 if vals_a else 0
            std_b = (sum((x - mean_b)**2 for x in vals_b) / len(vals_b)) ** 0.5 if vals_b else 0
            
            if std_a > 0 and std_b > 0:
                cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(vals_a, vals_b)) / len(vals_a)
                corr = cov / (std_a * std_b)
                co_correlations.append((fam_a, fam_b, corr))
    
    co_correlations.sort(key=lambda x: -x[2])
    
    print("\n  Most positively correlated (active on same days):")
    for fam_a, fam_b, corr in co_correlations[:10]:
        print(f"    {fam_a:30s} ↔ {fam_b:30s} | r = {corr:+.3f}")
    
    print("\n  Most inversely correlated (active on opposite days):")
    for fam_a, fam_b, corr in co_correlations[-5:]:
        print(f"    {fam_a:30s} ↔ {fam_b:30s} | r = {corr:+.3f}")

def main():
    print("🔬 HERMES SIGNAL CLUSTER ANALYSIS — Last 30 Days")
    print("="*120)
    print(f"Analysis generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    rows = get_signal_data()
    print(f"Total signals analyzed: {len(rows)}")
    
    daily = group_by_day(rows)
    
    # Run analyses
    analyze_daily_dominance(daily)
    analyze_signal_waves(daily)
    analyze_sequential_patterns(daily)
    analyze_co_signal_patterns(rows)
    analyze_market_regime_signals(daily)
    analyze_pairwise_family_correlations(daily)
    analyze_time_of_day_patterns(rows)
    analyze_confidence_trends(daily)
    
    print("\n" + "="*120)
    print("✅ ANALYSIS COMPLETE")
    print("="*120)

if __name__ == '__main__':
    main()
