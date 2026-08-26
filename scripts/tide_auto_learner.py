#!/usr/bin/env python3
"""
tide_auto_learner.py — Auto-learn new signal families and lead-lag patterns.

Extends tide_detector.py by:
1. Auto-detecting new signal types not in FAMILY_MAP
2. Tracking their performance by phase
3. Learning new lead-lag correlations from trade outcomes
4. Suggesting updates to FAMILY_MAP and LEAD_LAG_RULES

Run periodically (daily) to update the tide detector's knowledge.

Usage:
    python3 tide_auto_learner.py           # Full learning cycle
    python3 tide_auto_learner.py --dry     # Dry run (show suggestions)
"""

import sys, os, json, sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, RUNTIME_DB
from market_phase_gate import FAMILY_MAP, signal_family

# ── Auto-learning thresholds ──────────────────────────────────────────────────
MIN_SIGNALS_FOR_FAMILY = 20   # Minimum signals to consider a new family
MIN_CORRELATION = 0.6         # Minimum correlation for lead-lag rules
MIN_TRADES_FOR_PATTERN = 10   # Minimum trades to learn a pattern

LEARNED_DATA_FILE = os.path.join(HERMES_DATA, 'tide_learned_patterns.json')


def get_unknown_signals(lookback_days: int = 30) -> dict:
    """
    Find signal types not in FAMILY_MAP and count their occurrences.
    
    Returns: {signal_type: count}
    """
    conn = None
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=10)
        cutoff = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        
        rows = conn.execute('''
            SELECT signal_type, COUNT(*) as cnt
            FROM signals
            WHERE created_at >= ?
            GROUP BY signal_type
            ORDER BY cnt DESC
        ''', (cutoff,)).fetchall()
    except Exception:
        return {}
    finally:
        if conn:
            conn.close()
    
    # Get all known signal types from FAMILY_MAP
    known_signals = set()
    for family, members in FAMILY_MAP.items():
        for m in members:
            known_signals.add(m)
            # Also add variants
            known_signals.add(m + '_long')
            known_signals.add(m + '_short')
            known_signals.add(m + '+')
            known_signals.add(m + '-')
    
    # Find unknown signals
    unknown = {}
    for sig_type, count in rows:
        if sig_type not in known_signals:
            # Check if it's a variant of a known signal
            base = sig_type.replace('_long', '').replace('_short', '').replace('+', '').replace('-', '')
            if base not in known_signals:
                unknown[sig_type] = count
    
    return unknown


def analyze_unknown_performance(lookback_days: int = 30) -> dict:
    """
    Analyze performance of unknown signals by phase.
    
    Returns: {signal_type: {phase: {wins, losses, pnl}}}
    """
    conn = None
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=10)
        cutoff = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        
        # Get signal outcomes
        rows = conn.execute('''
            SELECT s.signal_type, s.created_at, o.is_win, o.pnl_pct
            FROM signals s
            JOIN signal_outcomes o ON s.token = o.token 
                AND s.signal_type = o.signal_type 
                AND s.direction = o.direction
            WHERE s.created_at >= ?
        ''', (cutoff,)).fetchall()
    except Exception:
        return {}
    finally:
        if conn:
            conn.close()
    
    # Get unknown signals
    unknown = get_unknown_signals(lookback_days)
    
    # Analyze performance by phase (simplified - use time-based phase detection)
    performance = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0}))
    
    for sig_type, created_at, is_win, pnl_pct in rows:
        if sig_type in unknown:
            # Simple phase detection based on time of day
            hour = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S').hour
            if 0 <= hour < 6:
                phase = 'quiet'
            elif 6 <= hour < 12:
                phase = 'trend_building'
            elif 12 <= hour < 18:
                phase = 'explosion'
            else:
                phase = 'defensive'
            
            if is_win:
                performance[sig_type][phase]['wins'] += 1
            else:
                performance[sig_type][phase]['losses'] += 1
            performance[sig_type][phase]['pnl'] += pnl_pct or 0
    
    return dict(performance)


def learn_lead_lag_patterns(lookback_days: int = 30) -> list:
    """
    Learn new lead-lag correlations from trade data.
    
    Returns: [{leader, follower, lag_days, corr, n_trades}]
    """
    conn = None
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=10)
        cutoff = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        
        # Get signal sequence per token
        rows = conn.execute('''
            SELECT token, signal_type, created_at
            FROM signals
            WHERE created_at >= ?
            ORDER BY token, created_at
        ''', (cutoff,)).fetchall()
    except Exception:
        return []
    finally:
        if conn:
            conn.close()
    
    # Group by token
    token_signals = defaultdict(list)
    for token, sig_type, created_at in rows:
        family = signal_family(sig_type)
        token_signals[token].append((family, created_at))
    
    # Find co-occurring families (within 2 days)
    family_pairs = Counter()
    for token, signals in token_signals.items():
        for i in range(len(signals)):
            for j in range(i+1, min(i+10, len(signals))):
                fam_a, ts_a = signals[i]
                fam_b, ts_b = signals[j]
                
                # Check time difference
                try:
                    dt_a = datetime.strptime(ts_a, '%Y-%m-%d %H:%M:%S')
                    dt_b = datetime.strptime(ts_b, '%Y-%m-%d %H:%M:%S')
                    lag_hours = (dt_b - dt_a).total_seconds() / 3600
                    
                    if 0 < lag_hours <= 48:  # Within 2 days
                        lag_days = round(lag_hours / 24)
                        family_pairs[(fam_a, fam_b, lag_days)] += 1
                except Exception:
                    pass
    
    # Find significant patterns
    patterns = []
    for (fam_a, fam_b, lag_days), count in family_pairs.items():
        if count >= MIN_TRADES_FOR_PATTERN and fam_a != fam_b:
            patterns.append({
                'leader': fam_a,
                'follower': fam_b,
                'lag_days': lag_days,
                'n_co_occurrences': count,
            })
    
    return patterns


def load_learned_data() -> dict:
    """Load previously learned patterns."""
    try:
        with open(LEARNED_DATA_FILE) as f:
            return json.load(f)
    except Exception:
        return {'unknown_families': {}, 'learned_patterns': [], 'last_updated': None}


def save_learned_data(data: dict):
    """Save learned patterns."""
    data['last_updated'] = datetime.now().isoformat()
    try:
        with open(LEARNED_DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def suggest_family_mapping(unknown_signals: dict) -> list:
    """
    Suggest family mappings for unknown signals based on name patterns.
    
    Returns: [{signal_type, suggested_family, confidence}]
    """
    suggestions = []
    
    # Name pattern matching
    patterns = {
        'Trendline': ['tl_break', 'trendline', 'trend_break'],
        'Bollinger': ['bb_', 'bollinger', 'squeeze'],
        'Momentum': ['momentum', 'velocity', 'accel'],
        'Exhaustion': ['exhaust', 'return'],
        'R2': ['r2_', 'r_squared'],
        'Range': ['range', 'channel'],
        'Mover': ['mover', 'hot', 'pump'],
        'HL_Copy': ['hl_copy', 'copy'],
        'Support_Resistance': ['support', 'resistance', 'sr_'],
    }
    
    for sig_type, count in unknown_signals.items():
        if count < MIN_SIGNALS_FOR_FAMILY:
            continue
        
        for family, keywords in patterns.items():
            for keyword in keywords:
                if keyword in sig_type.lower():
                    suggestions.append({
                        'signal_type': sig_type,
                        'suggested_family': family,
                        'confidence': min(1.0, count / 100),  # Higher count = higher confidence
                        'reason': f'Name contains "{keyword}"',
                    })
                    break
    
    return suggestions


def run_learning_cycle(dry_run: bool = False):
    """Run the full learning cycle."""
    print("=== Tide Auto-Learner ===\n")
    
    # 1. Find unknown signals
    unknown = get_unknown_signals()
    print(f"Unknown signals (not in FAMILY_MAP): {len(unknown)}")
    for sig, count in sorted(unknown.items(), key=lambda x: -x[1])[:10]:
        print(f"  {sig}: {count} signals")
    
    # 2. Suggest family mappings
    suggestions = suggest_family_mapping(unknown)
    print(f"\nSuggested family mappings: {len(suggestions)}")
    for s in suggestions:
        print(f"  {s['signal_type']} → {s['suggested_family']} (conf={s['confidence']:.0%}, {s['reason']})")
    
    # 3. Learn lead-lag patterns
    patterns = learn_lead_lag_patterns()
    print(f"\nLearned lead-lag patterns: {len(patterns)}")
    for p in sorted(patterns, key=lambda x: -x['n_co_occurrences'])[:10]:
        print(f"  {p['leader']} → {p['follower']} (+{p['lag_days']}d, n={p['n_co_occurrences']})")
    
    # 4. Save learned data
    if not dry_run and (suggestions or patterns):
        learned = load_learned_data()
        learned['unknown_families'] = {s['signal_type']: s['suggested_family'] for s in suggestions}
        learned['learned_patterns'] = patterns
        save_learned_data(learned)
        print(f"\nSaved learned data to {LEARNED_DATA_FILE}")
    
    print("\n=== Learning Complete ===")


if __name__ == '__main__':
    dry_run = '--dry' in sys.argv
    run_learning_cycle(dry_run)
