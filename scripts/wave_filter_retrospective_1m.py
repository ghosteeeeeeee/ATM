#!/usr/bin/env python3
"""
wave_filter_retrospective_1m.py
================================
Speed threshold sweep on 1m price_history data for all 2566 closed trades.
Tests: does abs_speed >= 2.5% on 1m predict profitable entries?

Uses price_history from signals_hermes.db (1m resolution, ~40k rows per traded token).
Speed: % change over last 20 bars (~20 min) — same ~25min window as 5m test (5 bars × 5m).

Run:  python3 wave_filter_retrospective_1m.py
"""

import sqlite3, math
from datetime import datetime
from collections import defaultdict

TRADES_DB = '/root/.hermes/data/signals_hermes_runtime.db'
PRICE_DB  = '/root/.hermes/data/signals_hermes.db'

def compute_z(closes: list) -> float | None:
    if len(closes) < 20:
        return None
    recent = closes[-20:]
    mean = sum(recent) / 20
    variance = sum((x - mean) ** 2 for x in recent) / 20
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return (closes[-1] - mean) / std

def z_trajectory(closes: list, n: int = 6) -> str:
    if len(closes) < n + 5:
        return 'flat'
    z_vals = []
    for i in range(len(closes) - n, len(closes)):
        z = compute_z(closes[:i+1])
        if z is not None:
            z_vals.append(z)
    if len(z_vals) < 3:
        return 'flat'
    mid = len(z_vals) // 2
    first_half  = z_vals[:mid] if mid > 0 else z_vals[:1]
    second_half = z_vals[mid:]
    avg_abs_first  = sum(abs(z) for z in first_half)  / len(first_half)
    avg_abs_second = sum(abs(z) for z in second_half) / len(second_half)
    if avg_abs_second > avg_abs_first + 0.15:
        return 'extreme'
    elif avg_abs_second < avg_abs_first - 0.15:
        return 'revert'
    return 'flat'

def wave_phase_from_snapshot(z: float, speed: float, accel: float) -> str:
    if abs(speed) < 0.15:
        if abs(z) < 0.5:
            return 'neutral'
        return 'bottoming' if z < 0 else 'topping'
    if speed > 0 and accel > 0:
        return 'accelerating'
    if speed > 0 and accel < 0:
        return 'decelerating'
    if speed < 0 and accel > 0:
        return 'bottoming'
    if speed < 0 and accel < 0:
        return 'falling'
    return 'neutral'

def evaluate_trade_1m(token: str, direction: str, entry_ts: float, cc) -> dict:
    """
    Uses price_history (1m resolution, timestamps in seconds).
    Speed: % change over last 20 bars (~20 min).
    """
    # Fetch ±30min window (timestamps in seconds for price_history)
    cc.execute("""
        SELECT timestamp, price FROM price_history
        WHERE token=? AND timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp
    """, (token, entry_ts - 1800, entry_ts + 300))
    rows = cc.fetchall()

    if len(rows) < 12:
        return {
            'gate': 'REJECT_GATE1', 'reason': f'no_data_rows={len(rows)}',
            'z': None, 'speed': None, 'accel': None, 'phase': None,
            'token': token, 'direction': direction,
            'is_win': None, 'pnl_pct': None, 'confidence': None
        }

    closes = [r[1] for r in rows]

    # Speed: % change over last 20 bars (~20 min at 1m resolution)
    if len(closes) >= 21:
        speed = (closes[-1] - closes[-21]) / closes[-21] * 100
    elif len(closes) >= 11:
        speed = (closes[-1] - closes[-11]) / closes[-11] * 100
    else:
        speed = 0.0

    # Acceleration: current 20-bar speed vs prior 20-bar speed
    if len(closes) >= 42:
        s_now  = (closes[-1]  - closes[-21])  / closes[-21]  * 100
        s_prev = (closes[-21] - closes[-42]) / closes[-42] * 100
        accel  = s_now - s_prev
    elif len(closes) >= 22:
        s_now  = (closes[-1]  - closes[-11]) / closes[-11] * 100
        s_prev = (closes[-11] - closes[-22]) / closes[-22] * 100
        accel  = s_now - s_prev
    else:
        accel = 0.0

    z        = compute_z(closes) or 0.0
    z_traj   = z_trajectory(closes, 6)
    phase    = wave_phase_from_snapshot(z, speed, accel)
    abs_spd  = abs(speed)
    overext  = (abs(z) > 2.0) or (abs_spd > 4.0)

    # GATE 1: Wave energy
    if abs_spd < 0.3:
        return {
            'gate': 'REJECT_GATE1',
            'reason': f'flat_speed={abs_spd:.3f}%',
            'z': z, 'speed': speed, 'accel': accel, 'phase': phase,
            'overextended': overext,
            'token': token, 'direction': direction,
            'is_win': None, 'pnl_pct': None, 'confidence': None
        }

    # GATE 2: Wave position
    late_indicators = []
    if direction == 'LONG':
        if z_traj == 'revert' and speed > 0:
            late_indicators.append(f'z_revert_during_rally z={z:.2f}')
        if overext:
            late_indicators.append(f'overextended_long z={z:.2f} spd={abs_spd:.2f}%')
        if phase in ('falling', 'topping'):
            late_indicators.append(f'opposite_phase={phase}')
    else:  # SHORT
        if z_traj == 'revert' and speed < 0:
            late_indicators.append(f'z_revert_during_sell z={z:.2f}')
        if overext:
            late_indicators.append(f'overextended_short z={z:.2f} spd={abs_spd:.2f}%')
        if phase in ('accelerating', 'bottoming'):
            late_indicators.append(f'opposite_phase={phase}')

    if late_indicators:
        return {
            'gate': 'REJECT_GATE2',
            'reason': '; '.join(late_indicators),
            'z': z, 'speed': speed, 'accel': accel, 'phase': phase,
            'overextended': overext,
            'token': token, 'direction': direction,
            'is_win': None, 'pnl_pct': None, 'confidence': None
        }

    return {
        'gate': 'PASS',
        'reason': 'ok',
        'z': z, 'speed': speed, 'accel': accel, 'phase': phase,
        'overextended': overext,
        'token': token, 'direction': direction,
        'is_win': None, 'pnl_pct': None, 'confidence': None
    }


def main():
    print("Loading trades...", flush=True)
    t_conn = sqlite3.connect(TRADES_DB)
    t_conn.row_factory = sqlite3.Row
    tc = t_conn.cursor()
    tc.execute("""
        SELECT token, direction, signal_type, is_win, pnl_pct, confidence, created_at
        FROM signal_outcomes ORDER BY created_at
    """)
    trades = [dict(r) for r in tc.fetchall()]
    t_conn.close()
    print(f"Loaded {len(trades)} trades")

    p_conn = sqlite3.connect(PRICE_DB)
    p_conn.row_factory = sqlite3.Row
    cc = p_conn.cursor()

    results  = []
    skipped  = 0
    no_data  = 0

    print("Evaluating trades on 1m price_history...", flush=True)
    for i, t in enumerate(trades):
        if i % 400 == 0:
            print(f"  {i}/{len(trades)}...", flush=True)

        try:
            created  = datetime.fromisoformat(t['created_at'].replace('Z', '+00:00'))
            entry_ts = created.timestamp()
        except Exception:
            skipped += 1
            continue

        res = evaluate_trade_1m(t['token'], t['direction'], entry_ts, cc)
        res['signal_type'] = t['signal_type']
        res['is_win']      = t['is_win']
        res['pnl_pct']     = t['pnl_pct']
        res['confidence']  = t['confidence']
        if res['gate'] == 'REJECT_GATE1' and 'no_data' in res['reason']:
            no_data += 1
        results.append(res)

    p_conn.close()
    print(f"  {len(trades)}/{len(trades)} done. Skipped={skipped}, no_data={no_data}")

    # ── Gate breakdown ────────────────────────────────────────────────
    gate_stats = defaultdict(lambda: {
        'n': 0, 'wins': 0, 'losses': 0,
        'pnl_sum': 0.0, 'winners_pnl': 0.0, 'losers_pnl': 0.0
    })
    for r in results:
        g = r['gate']
        s = gate_stats[g]
        s['n'] += 1
        s['pnl_sum'] += r['pnl_pct'] or 0
        if r['is_win'] == 1:
            s['wins'] += 1
            s['winners_pnl'] += r['pnl_pct'] or 0
        elif r['is_win'] == 0:
            s['losses'] += 1
            s['losers_pnl'] += r['pnl_pct'] or 0

    total        = len(results)
    total_wins   = sum(1 for r in results if r['is_win'] == 1)
    total_losses = sum(1 for r in results if r['is_win'] == 0)
    total_pnl    = sum(r['pnl_pct'] or 0 for r in results)

    print(f"""
=================================================================
WAVE-FILTER RETROSPECTIVE — 1m price_history
=================================================================
Total analyzed: {total}  |  Skipped={skipped}  No data={no_data}
  Winners: {total_wins} ({total_wins/total*100:.1f}%)
  Losses:  {total_losses} ({total_losses/total*100:.1f}%)
  Net P&L: {total_pnl:+.2f}%

REJECTION BREAKDOWN:
""")
    for gate in ['PASS', 'REJECT_GATE1', 'REJECT_GATE2', 'REJECT_GATE3']:
        s = gate_stats[gate]
        if s['n'] == 0:
            continue
        wr  = s['wins'] / s['n'] * 100
        avg = s['pnl_sum'] / s['n']
        print(
            f"  {gate:16s}: n={s['n']:4d}  WR={wr:5.1f}%  "
            f"avg={avg:+.3f}%  losses={s['losses']}  wins={s['wins']}"
        )

    # ── Speed threshold sweep ────────────────────────────────────────
    print(f"""
=================================================================
1M SPEED THRESHOLD SWEEP
=================================================================
  {'MinSpd':>7s}  {'n':>5s}  {'Wins':>5s}  {'WR%':>5s}  {'Avg%':>7s}  {'Net%':>8s}  {'LossOut':>8s}  Status
  {'-'*7}  {'-'*5}  {'-'*5}  {'-'*5}  {'-'*7}  {'-'*8}  {'-'*8}  {'-'*10}
""")
    for min_spd in [0.0, 0.15, 0.20, 0.25, 0.30, 0.50, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0]:
        subset = [r for r in results if abs(r['speed'] or 0) >= min_spd]
        if not subset:
            continue
        wins   = sum(1 for r in subset if r['is_win'] == 1)
        losses = sum(1 for r in subset if r['is_win'] == 0)
        n      = len(subset)
        wr     = wins / n * 100
        avg    = sum(r['pnl_pct'] or 0 for r in subset) / n
        net    = sum(r['pnl_pct'] or 0 for r in subset)
        loss_out = total_losses - losses
        status = "BASELINE" if min_spd == 0.0 else ("← BREAK-EVEN" if 0 < net < 5 else ("← PROFITABLE" if net >= 5 else ""))
        print(
            f"  {min_spd:>6.2f}%  {n:>5d}  {wins:>5d}  {wr:>5.1f}  "
            f"{avg:>+7.3f}%  {net:>+8.2f}%  {loss_out:>8d}  {status}"
        )

    # ── GATE1-only vs full GATE1+2 filter ──────────────────────────
    print(f"""
=================================================================
GATE1 (speed>=0.3%) vs FULL GATE1+2 COMPARISON
=================================================================
""")
    g1 = [r for r in results if r['gate'] in ('PASS', 'REJECT_GATE1')]
    g2 = [r for r in results if r['gate'] == 'PASS']
    for label, subset in [("GATE1 (speed>=0.3%)", g1), ("GATE1+2 (full filter)", g2)]:
        n      = len(subset)
        if n == 0:
            continue
        wins   = sum(1 for r in subset if r['is_win'] == 1)
        wr     = wins / n * 100
        avg    = sum(r['pnl_pct'] or 0 for r in subset) / n
        net    = sum(r['pnl_pct'] or 0 for r in subset)
        loss_out = total_losses - (total_losses - sum(1 for r in subset if r['is_win'] == 0))
        print(
            f"  {label:22s}: n={n:4d}  WR={wr:5.1f}%  "
            f"avg={avg:+.3f}%  net={net:+.2f}%"
        )

    print("\nDone.")


if __name__ == '__main__':
    main()
