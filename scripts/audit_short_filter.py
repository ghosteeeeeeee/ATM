#!/usr/bin/env python3
"""Independent audit of pump-chain SHORT signal filter performance."""

import sys
sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT
import psycopg2
import json
from collections import defaultdict

conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()

# Query all pump-chain SHORT trades
query = """
SELECT
    token,
    pnl_usdt,
    signal,
    _signal_metadata,
    open_time,
    close_time,
    direction,
    status,
    chain
FROM trades
WHERE signal LIKE 'pump-chain-%'
  AND direction = 'SHORT'
ORDER BY open_time;
"""

cur.execute(query)
rows = cur.fetchall()
print(f"Total SHORT trades found: {len(rows)}")
print()

# Parse metadata
trades = []
for row in rows:
    token, pnl, signal, meta, open_t, close_t, direction, status, chain = row

    # meta could be dict or JSON string
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except:
            meta = {}
    if meta is None:
        meta = {}

    wave_phase = meta.get('wave_phase', 'unknown')
    momentum_state = meta.get('momentum_state', 'unknown')
    bb_position = meta.get('bb_position', None)
    speed_percentile = meta.get('speed_percentile', None)

    trades.append({
        'token': token,
        'pnl': float(pnl) if pnl else 0.0,
        'signal': signal,
        'wave_phase': wave_phase,
        'momentum_state': momentum_state,
        'bb_position': float(bb_position) if bb_position is not None else None,
        'speed_percentile': float(speed_percentile) if speed_percentile is not None else None,
        'open_time': str(open_t) if open_t else 'unknown',
        'close_time': str(close_t) if close_t else 'unknown',
        'status': status,
        'chain': chain,
    })

# Print all trades
print("=" * 140)
print(f"{'#':>3} {'Token':<10} {'PnL':>8} {'Status':<10} {'Wave Phase':<15} {'Momentum':<12} {'BB Pos':>8} {'Speed':>8}")
print("=" * 140)

total_pnl = 0
wins = 0
losses = 0
breakeven = 0
win_pnl = 0
loss_pnl = 0

for i, t in enumerate(trades):
    total_pnl += t['pnl']
    if t['pnl'] > 0:
        wins += 1
        win_pnl += t['pnl']
    elif t['pnl'] < 0:
        losses += 1
        loss_pnl += t['pnl']
    else:
        breakeven += 1

    bb_str = f"{t['bb_position']:.3f}" if t['bb_position'] is not None else "N/A"
    speed_str = f"{t['speed_percentile']:.1f}" if t['speed_percentile'] is not None else "N/A"
    status_str = t['status'] if t['status'] else "N/A"

    print(f"{i+1:>3} {t['token']:<10} {t['pnl']:>+8.2f} {status_str:<10} {t['wave_phase']:<15} {t['momentum_state']:<12} {bb_str:>8} {speed_str:>8}")

print("=" * 140)
print(f"\nBASELINE STATS:")
print(f"  Total trades: {len(trades)}")
print(f"  Wins: {wins} (PnL: ${win_pnl:+.2f})")
print(f"  Losses: {losses} (PnL: ${loss_pnl:+.2f})")
print(f"  Breakeven: {breakeven}")
print(f"  Total PnL: ${total_pnl:+.2f}")
if wins + losses > 0:
    print(f"  Win Rate: {wins/(wins+losses)*100:.1f}%")

# Show all trades with zero PnL to check if they're real breakeven
zero_pnl = [t for t in trades if t['pnl'] == 0]
if zero_pnl:
    print(f"\n  Zero-PnL trades (may be open/unfinished):")
    for t in zero_pnl:
        print(f"    {t['token']:<10} status={t['status']} open={t['open_time']} close={t['close_time']}")

# Now analyze all unique metadata values
print("\n" + "=" * 80)
print("UNIQUE METADATA VALUES:")
print("=" * 80)

phases = defaultdict(int)
momentum = defaultdict(int)
for t in trades:
    phases[t['wave_phase']] += 1
    momentum[t['momentum_state']] += 1

print(f"  wave_phase distribution: {dict(sorted(phases.items()))}")
print(f"  momentum_state distribution: {dict(sorted(momentum.items()))}")

bb_vals = [t['bb_position'] for t in trades if t['bb_position'] is not None]
speed_vals = [t['speed_percentile'] for t in trades if t['speed_percentile'] is not None]
print(f"  bb_position range: {min(bb_vals):.3f} to {max(bb_vals):.3f} (count={len(bb_vals)})" if bb_vals else "  bb_position: no data")
print(f"  speed_percentile range: {min(speed_vals):.1f} to {max(speed_vals):.1f} (count={len(speed_vals)})" if speed_vals else "  speed_percentile: no data")

# Show per-coin details with all metadata
print("\n" + "=" * 140)
print("DETAILED TRADE LIST (sorted by PnL):")
print("=" * 140)
sorted_trades = sorted(trades, key=lambda x: x['pnl'])
for i, t in enumerate(sorted_trades):
    bb_str = f"{t['bb_position']:.3f}" if t['bb_position'] is not None else "N/A"
    speed_str = f"{t['speed_percentile']:.1f}" if t['speed_percentile'] is not None else "N/A"
    print(f"  {t['token']:<10} PnL=${t['pnl']:>+7.2f}  phase={t['wave_phase']:<15} mom={t['momentum_state']:<12} bb={bb_str:>6} speed={speed_str:>6}")

# ============================================================
# FILTER ANALYSIS
# ============================================================
print("\n" + "=" * 80)
print("FILTER ANALYSIS")
print("=" * 80)

# Only consider trades with non-zero PnL for filter analysis (exclude open/breakeven)
active_trades = [t for t in trades if t['pnl'] != 0]
print(f"\nActive trades (non-zero PnL): {len(active_trades)}")
active_wins = len([t for t in active_trades if t['pnl'] > 0])
active_losses = len([t for t in active_trades if t['pnl'] < 0])
active_pnl = sum(t['pnl'] for t in active_trades)
print(f"  Wins: {active_wins}, Losses: {active_losses}, PnL: ${active_pnl:+.2f}")

def analyze_filter(name, filter_func, dataset=None):
    """Apply filter, count catches and kills."""
    if dataset is None:
        dataset = active_trades

    catches = []
    kills = []
    passed = []

    for t in dataset:
        if filter_func(t):
            passed.append(t)
            if t['pnl'] < 0:
                catches.append(t)
            elif t['pnl'] > 0:
                kills.append(t)

    remaining = [t for t in dataset if not filter_func(t)]

    caught_pnl = sum(t['pnl'] for t in catches)
    killed_pnl = sum(t['pnl'] for t in kills)
    remaining_pnl = sum(t['pnl'] for t in remaining)
    remaining_wins = len([t for t in remaining if t['pnl'] > 0])
    remaining_losses = len([t for t in remaining if t['pnl'] < 0])
    remaining_total = len(remaining)

    print(f"\n--- {name} ---")
    print(f"  Filter passes: {len(passed)} / {len(dataset)}")
    print(f"  Losses caught (excluded): {len(catches)} (PnL: ${caught_pnl:+.2f})")
    print(f"  Wins killed (excluded): {len(kills)} (PnL: ${killed_pnl:+.2f})")
    print(f"  Remaining trades: {remaining_total}")
    if remaining_total > 0:
        print(f"  Remaining wins: {remaining_wins}, losses: {remaining_losses}")
        print(f"  Remaining WR: {remaining_wins/remaining_total*100:.1f}%")
        print(f"  Remaining PnL: ${remaining_pnl:+.2f}")

    if catches:
        print(f"  Caught losses:")
        for c in catches:
            print(f"    {c['token']:<10} ${c['pnl']:+.2f}  (phase={c['wave_phase']}/mom={c['momentum_state']}/bb={c['bb_position']})")
    if kills:
        print(f"  Killed wins:")
        for k in kills:
            print(f"    {k['token']:<10} ${k['pnl']:+.2f}  (phase={k['wave_phase']}/mom={k['momentum_state']}/bb={k['bb_position']})")

    return catches, kills, remaining

# ============================================================
# CLAIMED FILTER 1: accel+rising OR falling+BB>0.4
# ============================================================
print("\n" + "=" * 80)
print("CLAIMED FILTER 1: (accel + rising) OR (falling + BB > 0.4)")
print("=" * 80)

def claimed_filter(t):
    bb = t['bb_position']
    phase = t['wave_phase'].lower() if t['wave_phase'] else ''
    mom = t['momentum_state'].lower() if t['momentum_state'] else ''

    cond1 = ('accel' in phase) and ('rising' in mom)
    cond2 = ('falling' in phase) and (bb is not None and bb > 0.4)
    return cond1 or cond2

catches1, kills1, remaining1 = analyze_filter("Claimed Filter", claimed_filter)

# ============================================================
# SUB-FILTER: accel+rising only
# ============================================================
print("\n" + "=" * 80)
print("SUB-FILTER: accel + rising only")
print("=" * 80)

def accel_rising(t):
    phase = t['wave_phase'].lower() if t['wave_phase'] else ''
    mom = t['momentum_state'].lower() if t['momentum_state'] else ''
    return ('accel' in phase) and ('rising' in mom)

catches2, kills2, remaining2 = analyze_filter("accel+rising", accel_rising)

# ============================================================
# SUB-FILTER: falling+BB>0.4 only
# ============================================================
print("\n" + "=" * 80)
print("SUB-FILTER: falling + BB > 0.4 only")
print("=" * 80)

def falling_bb(t):
    phase = t['wave_phase'].lower() if t['wave_phase'] else ''
    bb = t['bb_position']
    return ('falling' in phase) and (bb is not None and bb > 0.4)

catches3, kills3, remaining3 = analyze_filter("falling+BB>0.4", falling_bb)

# ============================================================
# SUB-FILTER: accel+flat
# ============================================================
print("\n" + "=" * 80)
print("SUB-FILTER: accel + flat")
print("=" * 80)

def accel_flat(t):
    phase = t['wave_phase'].lower() if t['wave_phase'] else ''
    mom = t['momentum_state'].lower() if t['momentum_state'] else ''
    return ('accel' in phase) and ('flat' in mom)

catches4, kills4, remaining4 = analyze_filter("accel+flat", accel_flat)

# ============================================================
# SUB-FILTER: speed > 80
# ============================================================
print("\n" + "=" * 80)
print("SUB-FILTER: speed > 80")
print("=" * 80)

def speed_80(t):
    sp = t['speed_percentile']
    return sp is not None and sp > 80

catches5, kills5, remaining5 = analyze_filter("speed>80", speed_80)

# ============================================================
# EXHAUSTIVE FILTER SEARCH
# ============================================================
print("\n" + "=" * 80)
print("EXHAUSTIVE FILTER SEARCH")
print("=" * 80)

phases_list = list(set(t['wave_phase'] for t in active_trades))
momentum_list = list(set(t['momentum_state'] for t in active_trades))
phases_norm = sorted(set(p.lower() for p in phases_list))
momentum_norm = sorted(set(m.lower() for m in momentum_list))

print(f"Phases found: {phases_norm}")
print(f"Momentum states found: {momentum_norm}")

results = []

# Single: wave_phase
for ph in phases_norm:
    def f(t, _ph=ph):
        return _ph in (t['wave_phase'].lower() if t['wave_phase'] else '')
    catches, kills, remaining = analyze_filter(f"phase={ph}", f)
    caught_pnl = sum(t['pnl'] for t in catches)
    killed_pnl = sum(t['pnl'] for t in kills)
    remaining_pnl = sum(t['pnl'] for t in remaining)
    remaining_wins = len([t for t in remaining if t['pnl'] > 0])
    results.append({
        'name': f"phase={ph}",
        'catches': len(catches),
        'kills': len(kills),
        'caught_pnl': caught_pnl,
        'killed_pnl': killed_pnl,
        'remaining_pnl': remaining_pnl,
        'remaining_trades': len(remaining),
        'remaining_wins': remaining_wins,
        'remaining_losses': len([t for t in remaining if t['pnl'] < 0]),
    })

# Single: momentum_state
for mom in momentum_norm:
    def f(t, _mom=mom):
        return _mom in (t['momentum_state'].lower() if t['momentum_state'] else '')
    catches, kills, remaining = analyze_filter(f"mom={mom}", f)
    caught_pnl = sum(t['pnl'] for t in catches)
    killed_pnl = sum(t['pnl'] for t in kills)
    remaining_pnl = sum(t['pnl'] for t in remaining)
    remaining_wins = len([t for t in remaining if t['pnl'] > 0])
    results.append({
        'name': f"mom={mom}",
        'catches': len(catches),
        'kills': len(kills),
        'caught_pnl': caught_pnl,
        'killed_pnl': killed_pnl,
        'remaining_pnl': remaining_pnl,
        'remaining_trades': len(remaining),
        'remaining_wins': remaining_wins,
        'remaining_losses': len([t for t in remaining if t['pnl'] < 0]),
    })

# Two-feature AND: phase+momentum
for ph in phases_norm:
    for mom in momentum_norm:
        def f(t, _ph=ph, _mom=mom):
            return (_ph in (t['wave_phase'].lower() if t['wave_phase'] else '')) and (_mom in (t['momentum_state'].lower() if t['momentum_state'] else ''))
        catches, kills, remaining = analyze_filter(f"phase={ph}+mom={mom}", f)
        caught_pnl = sum(t['pnl'] for t in catches)
        killed_pnl = sum(t['pnl'] for t in kills)
        remaining_pnl = sum(t['pnl'] for t in remaining)
        remaining_wins = len([t for t in remaining if t['pnl'] > 0])
        results.append({
            'name': f"phase={ph} AND mom={mom}",
            'catches': len(catches),
            'kills': len(kills),
            'caught_pnl': caught_pnl,
            'killed_pnl': killed_pnl,
            'remaining_pnl': remaining_pnl,
            'remaining_trades': len(remaining),
            'remaining_wins': remaining_wins,
            'remaining_losses': len([t for t in remaining if t['pnl'] < 0]),
        })

# BB thresholds
for bb_thresh in [0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]:
    def f(t, _bb=bb_thresh):
        return t['bb_position'] is not None and t['bb_position'] > _bb
    catches, kills, remaining = analyze_filter(f"bb>{bb_thresh}", f)
    caught_pnl = sum(t['pnl'] for t in catches)
    killed_pnl = sum(t['pnl'] for t in kills)
    remaining_pnl = sum(t['pnl'] for t in remaining)
    remaining_wins = len([t for t in remaining if t['pnl'] > 0])
    results.append({
        'name': f"bb>{bb_thresh}",
        'catches': len(catches),
        'kills': len(kills),
        'caught_pnl': caught_pnl,
        'killed_pnl': killed_pnl,
        'remaining_pnl': remaining_pnl,
        'remaining_trades': len(remaining),
        'remaining_wins': remaining_wins,
        'remaining_losses': len([t for t in remaining if t['pnl'] < 0]),
    })

# Speed thresholds
for sp_thresh in [50, 60, 70, 80, 90]:
    def f(t, _sp=sp_thresh):
        return t['speed_percentile'] is not None and t['speed_percentile'] > _sp
    catches, kills, remaining = analyze_filter(f"speed>{sp_thresh}", f)
    caught_pnl = sum(t['pnl'] for t in catches)
    killed_pnl = sum(t['pnl'] for t in kills)
    remaining_pnl = sum(t['pnl'] for t in remaining)
    remaining_wins = len([t for t in remaining if t['pnl'] > 0])
    results.append({
        'name': f"speed>{sp_thresh}",
        'catches': len(catches),
        'kills': len(kills),
        'caught_pnl': caught_pnl,
        'killed_pnl': killed_pnl,
        'remaining_pnl': remaining_pnl,
        'remaining_trades': len(remaining),
        'remaining_wins': remaining_wins,
        'remaining_losses': len([t for t in remaining if t['pnl'] < 0]),
    })

# Combo: phase+bb
for ph in phases_norm:
    for bb_thresh in [0.3, 0.4, 0.5]:
        def f(t, _ph=ph, _bb=bb_thresh):
            return (_ph in (t['wave_phase'].lower() if t['wave_phase'] else '')) and (t['bb_position'] is not None and t['bb_position'] > _bb)
        catches, kills, remaining = analyze_filter(f"phase={ph}+bb>{bb_thresh}", f)
        caught_pnl = sum(t['pnl'] for t in catches)
        killed_pnl = sum(t['pnl'] for t in kills)
        remaining_pnl = sum(t['pnl'] for t in remaining)
        remaining_wins = len([t for t in remaining if t['pnl'] > 0])
        results.append({
            'name': f"phase={ph} AND bb>{bb_thresh}",
            'catches': len(catches),
            'kills': len(kills),
            'caught_pnl': caught_pnl,
            'killed_pnl': killed_pnl,
            'remaining_pnl': remaining_pnl,
            'remaining_trades': len(remaining),
            'remaining_wins': remaining_wins,
            'remaining_losses': len([t for t in remaining if t['pnl'] < 0]),
        })

# Combo: mom+bb
for mom in momentum_norm:
    for bb_thresh in [0.3, 0.4, 0.5]:
        def f(t, _mom=mom, _bb=bb_thresh):
            return (_mom in (t['momentum_state'].lower() if t['momentum_state'] else '')) and (t['bb_position'] is not None and t['bb_position'] > _bb)
        catches, kills, remaining = analyze_filter(f"mom={mom}+bb>{bb_thresh}", f)
        caught_pnl = sum(t['pnl'] for t in catches)
        killed_pnl = sum(t['pnl'] for t in kills)
        remaining_pnl = sum(t['pnl'] for t in remaining)
        remaining_wins = len([t for t in remaining if t['pnl'] > 0])
        results.append({
            'name': f"mom={mom} AND bb>{bb_thresh}",
            'catches': len(catches),
            'kills': len(kills),
            'caught_pnl': caught_pnl,
            'killed_pnl': killed_pnl,
            'remaining_pnl': remaining_pnl,
            'remaining_trades': len(remaining),
            'remaining_wins': remaining_wins,
            'remaining_losses': len([t for t in remaining if t['pnl'] < 0]),
        })

# Combo: phase+momentum+bb
for ph in phases_norm:
    for mom in momentum_norm:
        for bb_thresh in [0.3, 0.4]:
            def f(t, _ph=ph, _mom=mom, _bb=bb_thresh):
                return (_ph in (t['wave_phase'].lower() if t['wave_phase'] else '')) and (_mom in (t['momentum_state'].lower() if t['momentum_state'] else '')) and (t['bb_position'] is not None and t['bb_position'] > _bb)
            catches, kills, remaining = analyze_filter(f"phase={ph}+mom={mom}+bb>{bb_thresh}", f)
            caught_pnl = sum(t['pnl'] for t in catches)
            killed_pnl = sum(t['pnl'] for t in kills)
            remaining_pnl = sum(t['pnl'] for t in remaining)
            remaining_wins = len([t for t in remaining if t['pnl'] > 0])
            results.append({
                'name': f"phase={ph} AND mom={mom} AND bb>{bb_thresh}",
                'catches': len(catches),
                'kills': len(kills),
                'caught_pnl': caught_pnl,
                'killed_pnl': killed_pnl,
                'remaining_pnl': remaining_pnl,
                'remaining_trades': len(remaining),
                'remaining_wins': remaining_wins,
                'remaining_losses': len([t for t in remaining if t['pnl'] < 0]),
            })

# OR filters
for ph in phases_norm:
    for mom in momentum_norm:
        def f(t, _ph=ph, _mom=mom):
            return (_ph in (t['wave_phase'].lower() if t['wave_phase'] else '')) or (_mom in (t['momentum_state'].lower() if t['momentum_state'] else ''))
        catches, kills, remaining = analyze_filter(f"OR(phase={ph},mom={mom})", f)
        caught_pnl = sum(t['pnl'] for t in catches)
        killed_pnl = sum(t['pnl'] for t in kills)
        remaining_pnl = sum(t['pnl'] for t in remaining)
        remaining_wins = len([t for t in remaining if t['pnl'] > 0])
        results.append({
            'name': f"OR(phase={ph}, mom={mom})",
            'catches': len(catches),
            'kills': len(kills),
            'caught_pnl': caught_pnl,
            'killed_pnl': killed_pnl,
            'remaining_pnl': remaining_pnl,
            'remaining_trades': len(remaining),
            'remaining_wins': remaining_wins,
            'remaining_losses': len([t for t in remaining if t['pnl'] < 0]),
        })

# OR(phase, bb)
for ph in phases_norm:
    for bb_thresh in [0.3, 0.4, 0.5]:
        def f(t, _ph=ph, _bb=bb_thresh):
            return (_ph in (t['wave_phase'].lower() if t['wave_phase'] else '')) or (t['bb_position'] is not None and t['bb_position'] > _bb)
        catches, kills, remaining = analyze_filter(f"OR(phase={ph},bb>{bb_thresh})", f)
        caught_pnl = sum(t['pnl'] for t in catches)
        killed_pnl = sum(t['pnl'] for t in kills)
        remaining_pnl = sum(t['pnl'] for t in remaining)
        remaining_wins = len([t for t in remaining if t['pnl'] > 0])
        results.append({
            'name': f"OR(phase={ph}, bb>{bb_thresh})",
            'catches': len(catches),
            'kills': len(kills),
            'caught_pnl': caught_pnl,
            'killed_pnl': killed_pnl,
            'remaining_pnl': remaining_pnl,
            'remaining_trades': len(remaining),
            'remaining_wins': remaining_wins,
            'remaining_losses': len([t for t in remaining if t['pnl'] < 0]),
        })

# OR(mom, bb)
for mom in momentum_norm:
    for bb_thresh in [0.3, 0.4, 0.5]:
        def f(t, _mom=mom, _bb=bb_thresh):
            return (_mom in (t['momentum_state'].lower() if t['momentum_state'] else '')) or (t['bb_position'] is not None and t['bb_position'] > _bb)
        catches, kills, remaining = analyze_filter(f"OR(mom={mom},bb>{bb_thresh})", f)
        caught_pnl = sum(t['pnl'] for t in catches)
        killed_pnl = sum(t['pnl'] for t in kills)
        remaining_pnl = sum(t['pnl'] for t in remaining)
        remaining_wins = len([t for t in remaining if t['pnl'] > 0])
        results.append({
            'name': f"OR(mom={mom}, bb>{bb_thresh})",
            'catches': len(catches),
            'kills': len(kills),
            'caught_pnl': caught_pnl,
            'killed_pnl': killed_pnl,
            'remaining_pnl': remaining_pnl,
            'remaining_trades': len(remaining),
            'remaining_wins': remaining_wins,
            'remaining_losses': len([t for t in remaining if t['pnl'] < 0]),
        })

# Compound: (accel+rising) OR (falling+BB>0.4) — claimed filter
def claimed_combined(t):
    bb = t['bb_position']
    phase = t['wave_phase'].lower() if t['wave_phase'] else ''
    mom = t['momentum_state'].lower() if t['momentum_state'] else ''
    cond1 = ('accel' in phase) and ('rising' in mom)
    cond2 = ('falling' in phase) and (bb is not None and bb > 0.4)
    return cond1 or cond2

catches_cc, kills_cc, remaining_cc = analyze_filter("CLAIMED COMBINED", claimed_combined)
caught_pnl_cc = sum(t['pnl'] for t in catches_cc)
killed_pnl_cc = sum(t['pnl'] for t in kills_cc)
remaining_pnl_cc = sum(t['pnl'] for t in remaining_cc)
remaining_wins_cc = len([t for t in remaining_cc if t['pnl'] > 0])
remaining_losses_cc = len([t for t in remaining_cc if t['pnl'] < 0])
results.append({
    'name': "CLAIMED: (accel+rising) OR (falling+BB>0.4)",
    'catches': len(catches_cc),
    'kills': len(kills_cc),
    'caught_pnl': caught_pnl_cc,
    'killed_pnl': killed_pnl_cc,
    'remaining_pnl': remaining_pnl_cc,
    'remaining_trades': len(remaining_cc),
    'remaining_wins': remaining_wins_cc,
    'remaining_losses': remaining_losses_cc,
})

# ============================================================
# RANKING
# ============================================================
print("\n" + "=" * 80)
print("TOP 30 FILTERS BY EFFICIENCY SCORE")
print("(Score = catches*100 - kills*500 + 500 if zero kills)")
print("=" * 80)

scored = []
for r in results:
    score = r['catches'] * 100 - r['kills'] * 500
    if r['kills'] == 0 and r['catches'] > 0:
        score += 500
    scored.append((score, r))

scored.sort(key=lambda x: -x[0])

print(f"\n{'Filter':<65} {'C':>2} {'K':>2} {'Catch$':>8} {'Kill$':>8} {'Rem$':>8} {'RW':>3} {'RL':>3} {'RT':>3}")
print("-" * 120)
for score, r in scored[:30]:
    marker = " ***" if r['kills'] == 0 and r['catches'] > 0 else ""
    print(f"{r['name']:<65} {r['catches']:>2} {r['kills']:>2} {r['caught_pnl']:>+8.2f} {r['killed_pnl']:>+8.2f} {r['remaining_pnl']:>+8.2f} {r['remaining_wins']:>3} {r['remaining_losses']:>3} {r['remaining_trades']:>3}{marker}")

# Zero-kill filters only
print("\n" + "=" * 80)
print("ALL ZERO-KILL FILTERS (catches > 0)")
print("=" * 80)
zero_kill = [(s, r) for s, r in scored if r['kills'] == 0 and r['catches'] > 0]
print(f"\n{'Filter':<65} {'C':>2} {'Catch$':>8} {'Rem$':>8} {'RW':>3} {'RL':>3} {'RT':>3}")
print("-" * 100)
for score, r in zero_kill:
    print(f"{r['name']:<65} {r['catches']:>2} {r['caught_pnl']:>+8.2f} {r['remaining_pnl']:>+8.2f} {r['remaining_wins']:>3} {r['remaining_losses']:>3} {r['remaining_trades']:>3}")

# ============================================================
# SPECIFIC VERIFICATION OF EACH CLAIM
# ============================================================
print("\n" + "=" * 80)
print("VERIFICATION OF CLAIMS")
print("=" * 80)

# Build lookup for each trade
print("\n--- Checking which trades accel+rising catches ---")
for t in active_trades:
    phase = t['wave_phase'].lower() if t['wave_phase'] else ''
    mom = t['momentum_state'].lower() if t['momentum_state'] else ''
    bb = t['bb_position']
    sp = t['speed_percentile']
    match_ar = ('accel' in phase) and ('rising' in mom)
    match_fb = ('falling' in phase) and (bb is not None and bb > 0.4)
    if match_ar or match_fb:
        print(f"  {t['token']:<10} PnL=${t['pnl']:>+7.2f}  phase={t['wave_phase']:<15} mom={t['momentum_state']:<12} bb={f'{bb:.3f}' if bb else 'N/A':>6} speed={f'{sp:.1f}' if sp else 'N/A':>6}  match={'AR' if match_ar else 'FB'}")

# Check the specific 4 losses claimed to be caught
print("\n--- Verifying the 4 claimed caught losses ---")
claimed_losses = {
    'BCH': {'expected_pnl': -0.12, 'expected': 'falling/flat/BB=0.401'},
    'INJ': {'expected_pnl': -0.27, 'expected': 'accelerating/rising/BB=0.453'},
    'ARB': {'expected_pnl': -0.13, 'expected': 'accelerating/rising/BB=0.353'},
    'ENA': {'expected_pnl': -0.16, 'expected': 'falling/flat/BB=0.419'},
}

for t in active_trades:
    if t['token'] in claimed_losses:
        cl = claimed_losses[t['token']]
        print(f"\n  {t['token']}:")
        print(f"    Actual PnL: ${t['pnl']:+.2f} (claimed: ${cl['expected_pnl']:+.2f}) {'MATCH' if abs(t['pnl'] - cl['expected_pnl']) < 0.005 else 'MISMATCH!'}")
        print(f"    phase={t['wave_phase']}, mom={t['momentum_state']}, bb={t['bb_position']}")
        print(f"    Claimed: {cl['expected']}")
        match_ar = ('accel' in t['wave_phase'].lower()) and ('rising' in t['momentum_state'].lower())
        match_fb = ('falling' in t['wave_phase'].lower()) and (t['bb_position'] is not None and t['bb_position'] > 0.4)
        caught = match_ar or match_fb
        print(f"    Filter match: accel+rising={'YES' if match_ar else 'no'}, falling+BB>0.4={'YES' if match_fb else 'no'}")
        print(f"    Caught by claimed filter: {'YES' if caught else 'NO!'}")

# Check the 2 wins killed by accel+flat
print("\n--- Verifying the 2 claimed wins killed by accel+flat ---")
claimed_kills_apt_ena = {
    'APT': {'expected_pnl': 0.11},
    'ENA': {'expected_pnl': 0.13},
}
for t in active_trades:
    if t['token'] in claimed_kills_apt_ena and t['pnl'] > 0:
        ck = claimed_kills_apt_ena[t['token']]
        phase = t['wave_phase'].lower() if t['wave_phase'] else ''
        mom = t['momentum_state'].lower() if t['momentum_state'] else ''
        match_af = ('accel' in phase) and ('flat' in mom)
        print(f"  {t['token']}: PnL=${t['pnl']:+.2f} (claimed: ${ck['expected_pnl']:+.2f}) phase={t['wave_phase']}, mom={t['momentum_state']}")
        print(f"    accel+flat match: {'YES' if match_af else 'NO!'}")
        print(f"    Killed by accel+flat: {'YES' if match_af else 'NO!'}")

conn.close()
