#!/usr/bin/env python3
"""
wave_filter_retrospective.py
=============================
Retrospective test: would the wave-state filter have avoided our losing trades?

Loads all 2566 closed trades from signal_outcomes, reconstructs market state at
each entry using candles_5m data, and evaluates 3 wave gates:
  GATE1: Is there wave energy? (speed > 0.3%)
  GATE2: Are we early/mid vs late/exhausted in the wave?
  GATE3: Do multiple timeframes agree on direction?

Reports losses_avoided and winners_kept to decide if filter is worth building.

Run:  python3 wave_filter_retrospective.py
Output: printed to stdout, ~30-60s on full dataset.
"""

import sqlite3, math
from datetime import datetime
from collections import defaultdict

# ─── DB paths ─────────────────────────────────────────────────────────────────
TRADES_DB  = '/root/.hermes/data/signals_hermes_runtime.db'
CANDLES_DB = '/root/.hermes/data/candles.db'
PRICE_DB   = '/root/.hermes/data/signals_hermes.db'

# ─── Helpers ───────────────────────────────────────────────────────────────────

def nearest_5m(ts: float) -> int:
    return int(ts // 300) * 300

def compute_z(closes: list) -> float | None:
    """Z-score of last close vs 20-bar rolling mean. None if < 20 bars."""
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
    """
    Is z_score becoming more extreme (toward ±2) or reverting toward 0?
    """
    if len(closes) < n + 5:
        return 'flat'
    z_vals = []
    for i in range(len(closes) - n, len(closes)):
        z = compute_z(closes[:i+1])
        if z is not None:
            z_vals.append(z)
    if len(z_vals) < 3:
        return 'flat'
    # Compare first half avg abs-z vs second half avg abs-z
    mid = len(z_vals) // 2
    first_half = z_vals[:mid] if mid > 0 else z_vals[:1]
    second_half = z_vals[mid:]
    avg_abs_first  = sum(abs(z) for z in first_half)  / len(first_half)
    avg_abs_second = sum(abs(z) for z in second_half) / len(second_half)
    if avg_abs_second > avg_abs_first + 0.15:
        return 'extreme'
    elif avg_abs_second < avg_abs_first - 0.15:
        return 'revert'
    return 'flat'

def wave_phase_from_snapshot(z: float, speed: float, accel: float) -> str:
    """Derive wave_phase label from snapshot values."""
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

def mtf_alignment(token: str, entry_ts: int, cc) -> float:
    """
    Returns alignment score 0.0-1.0.
    Checks net direction of 5m, 15m, 1h candles around entry_ts.
    1.0 = 2+ TFs agree in same direction, 0.5 = mixed, 0.0 = no data.
    """
    scores = []
    for tf_name, tf_sec, lookback in [
        ('5m',  300,  6),
        ('15m', 900,  4),
        ('1h',  3600, 4),
    ]:
        t_start = entry_ts - tf_sec * lookback
        t_end   = entry_ts + tf_sec * 2
        cc.execute(f"""
            SELECT close FROM candles_{tf_name}
            WHERE token=? AND ts >= ? AND ts <= ?
            ORDER BY ts
        """, (token, t_start, t_end))
        rows = [r[0] for r in cc.fetchall()]
        if len(rows) >= 3:
            net = rows[-1] - rows[0]
            scores.append(1 if net > 0 else -1 if net < 0 else 0)
        else:
            scores.append(0)
    pos = scores.count(1)
    neg = scores.count(-1)
    if pos >= 2:
        return 1.0
    if neg >= 2:
        return 0.0
    return 0.5  # mixed or insufficient data

# ─── Gate evaluators ───────────────────────────────────────────────────────────

def evaluate_trade(token: str, direction: str, entry_ts: float, cc) -> dict:
    """
    Returns gate result dict for a single trade.
    entry_ts = unix timestamp of trade entry (from signal_outcomes.created_at)
    """
    floor_ts = nearest_5m(entry_ts)

    # ── Fetch 5m candles for trajectory ────────────────────────────────────
    cc.execute("""
        SELECT ts, close FROM candles_5m
        WHERE token=? AND ts >= ? AND ts <= ?
        ORDER BY ts
    """, (token, floor_ts - 2400, floor_ts + 300))
    rows5 = cc.fetchall()
    if len(rows5) < 6:
        return {
            'gate': 'REJECT_GATE1', 'reason': f'no_data_rows={len(rows5)}',
            'z': None, 'speed': None, 'accel': None, 'phase': None,
            'overextended': None, 'mtf_score': None,
            'token': token, 'direction': direction,
            'is_win': None, 'pnl_pct': None, 'confidence': None
        }

    closes5 = [r[1] for r in rows5]

    # Speed: % change over last 5 bars (~25min)
    if len(closes5) >= 6:
        speed = (closes5[-1] - closes5[-6]) / closes5[-6] * 100
    else:
        speed = 0.0

    # Acceleration: change in speed (current 5-bar vs prior 5-bar)
    if len(closes5) >= 12:
        s_now  = (closes5[-1]  - closes5[-6])  / closes5[-6]  * 100
        s_prev = (closes5[-6]  - closes5[-11]) / closes5[-11] * 100
        accel  = s_now - s_prev
    else:
        accel = 0.0

    z        = compute_z(closes5) or 0.0
    z_traj   = z_trajectory(closes5, 6)
    phase    = wave_phase_from_snapshot(z, speed, accel)
    abs_spd  = abs(speed)

    # Overextended: z too far from mean OR speed extremely high
    overext = (abs(z) > 2.0) or (abs_spd > 4.0)

    # ── GATE 1: Wave energy ──────────────────────────────────────────────
    if abs_spd < 0.3:
        return {
            'gate': 'REJECT_GATE1',
            'reason': f'flat_speed={abs_spd:.3f}%',
            'z': z, 'speed': speed, 'accel': accel, 'phase': phase,
            'overextended': overext, 'mtf_score': None,
            'token': token, 'direction': direction,
            'is_win': None, 'pnl_pct': None, 'confidence': None
        }

    # ── GATE 2: Wave position (early vs late/exhausted) ───────────────────
    # Late-wave indicators
    late_indicators = []

    if direction == 'LONG':
        # z reverting toward 0 while price was moving up = exhaustion
        if z_traj == 'revert' and speed > 0:
            late_indicators.append(f'z_revert_during_rally z={z:.2f}')
        # Overextended
        if overext:
            late_indicators.append(f'overextended_long z={z:.2f} spd={abs_spd:.2f}%')
        # Phase opposite to trade
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
            'overextended': overext, 'mtf_score': None,
            'token': token, 'direction': direction,
            'is_win': None, 'pnl_pct': None, 'confidence': None
        }

    # ── GATE 3: MTF alignment ─────────────────────────────────────────────
    mtf = mtf_alignment(token, floor_ts, cc)
    if mtf < 0.5:
        return {
            'gate': 'REJECT_GATE3',
            'reason': f'no_mtf_alignment mtf={mtf:.2f}',
            'z': z, 'speed': speed, 'accel': accel, 'phase': phase,
            'overextended': overext, 'mtf_score': mtf,
            'token': token, 'direction': direction,
            'is_win': None, 'pnl_pct': None, 'confidence': None
        }

    return {
        'gate': 'PASS',
        'reason': 'ok',
        'z': z, 'speed': speed, 'accel': accel, 'phase': phase,
        'overextended': overext, 'mtf_score': mtf,
        'token': token, 'direction': direction,
        'is_win': None, 'pnl_pct': None, 'confidence': None
    }


# ─── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("Loading trades...", flush=True)
    t_conn = sqlite3.connect(TRADES_DB)
    t_conn.row_factory = sqlite3.Row
    tc = t_conn.cursor()
    tc.execute("""
        SELECT token, direction, signal_type, is_win, pnl_pct, confidence, created_at
        FROM signal_outcomes
        ORDER BY created_at
    """)
    trades = [dict(r) for r in tc.fetchall()]
    t_conn.close()
    print(f"Loaded {len(trades)} trades")

    c_conn = sqlite3.connect(CANDLES_DB)
    c_conn.row_factory = sqlite3.Row
    cc = c_conn.cursor()

    results    = []
    skipped    = 0

    print("Evaluating trades...", flush=True)
    for i, t in enumerate(trades):
        if i % 400 == 0:
            print(f"  {i}/{len(trades)}...", flush=True)

        try:
            created  = datetime.fromisoformat(t['created_at'].replace('Z', '+00:00'))
            entry_ts = created.timestamp()
        except Exception:
            skipped += 1
            continue

        res = evaluate_trade(t['token'], t['direction'], entry_ts, cc)
        # Attach trade metadata
        res['signal_type'] = t['signal_type']
        res['is_win']      = t['is_win']
        res['pnl_pct']     = t['pnl_pct']
        res['confidence']   = t['confidence']
        results.append(res)

    c_conn.close()
    print(f"  {len(trades)}/{len(trades)} done. Skipped={skipped}")

    # ── Aggregate ────────────────────────────────────────────────────────────
    gate_stats = defaultdict(lambda: {
        'n': 0, 'wins': 0, 'losses': 0,
        'pnl_sum': 0.0, 'winners_pnl': 0.0, 'losers_pnl': 0.0
    })

    for r in results:
        g  = r['gate']
        s  = gate_stats[g]
        s['n'] += 1
        s['pnl_sum'] += r['pnl_pct'] or 0
        if r['is_win'] == 1:
            s['wins'] += 1
            s['winners_pnl'] += r['pnl_pct'] or 0
        elif r['is_win'] == 0:
            s['losses'] += 1
            s['losers_pnl'] += r['pnl_pct'] or 0

    total          = len(results)
    total_wins     = sum(1 for r in results if r['is_win'] == 1)
    total_losses   = sum(1 for r in results if r['is_win'] == 0)
    total_pnl      = sum(r['pnl_pct'] or 0 for r in results)
    total_win_pnl  = sum(r['pnl_pct'] or 0 for r in results if r['is_win'] == 1)
    total_loss_pnl = sum(r['pnl_pct'] or 0 for r in results if r['is_win'] == 0)

    print(f"""
=================================================================
WAVE-FILTER RETROSPECTIVE RESULTS
=================================================================
Total analyzed: {total}  |  Skipped (bad ts): {skipped}
  Winners: {total_wins} ({total_wins/total*100:.1f}%)  P&L: {total_win_pnl:+.2f}%
  Losses:  {total_losses} ({total_losses/total*100:.1f}%)  P&L: {total_loss_pnl:+.2f}%
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
            f"avg={avg:+.3f}%  losses_avoided={s['losses']}  "
            f"(wins={s['wins']} losses={s['losses']})"
        )

    # ── Filter impact ───────────────────────────────────────────────────────
    pass_s = gate_stats['PASS']
    g1_s   = gate_stats['REJECT_GATE1']
    g2_s   = gate_stats['REJECT_GATE2']
    g3_s   = gate_stats['REJECT_GATE3']

    losses_total    = total_losses
    losses_rejected  = g1_s['losses'] + g2_s['losses'] + g3_s['losses']
    winners_total    = total_wins
    winners_pass     = pass_s['wins']
    losses_avoided_pct = losses_rejected / losses_total * 100 if losses_total else 0
    winners_kept_pct   = winners_pass    / winners_total  * 100 if winners_total  else 0

    pass_avg  = pass_s['pnl_sum'] / pass_s['n'] if pass_s['n'] else 0
    all_avg   = total_pnl          / total       if total        else 0

    print(f"""
FILTER IMPACT:
  Losses avoided:  {losses_rejected}/{losses_total}  ({losses_avoided_pct:.1f}%)
  Winners kept:   {winners_pass}/{winners_total}  ({winners_kept_pct:.1f}%)

  Avg trade AFTER filter:  {pass_avg:+.3f}%
  Avg trade BEFORE filter: {all_avg:+.3f}%
  Improvement:             {pass_avg - all_avg:+.3f}%

NET P&L COMPARISON:
  If running PASS-only:   {pass_s['pnl_sum']:+.2f}%
  If running all trades: {total_pnl:+.2f}%
""")

    # ── Per-signal-type breakdown for PASS trades ──────────────────────────
    print(f"\nPASS — win rate by signal_type (n >= 3):")
    sig_stats = defaultdict(lambda: {'n': 0, 'wins': 0, 'pnl_sum': 0.0})
    for r in results:
        if r['gate'] != 'PASS':
            continue
        st = (r['signal_type'] or '')[:45]
        sig_stats[st]['n']      += 1
        sig_stats[st]['pnl_sum'] += r['pnl_pct'] or 0
        if r['is_win'] == 1:
            sig_stats[st]['wins'] += 1

    for st, s in sorted(sig_stats.items(), key=lambda x: -x[1]['pnl_sum']):
        if s['n'] < 3:
            continue
        wr  = s['wins'] / s['n'] * 100
        avg = s['pnl_sum'] / s['n']
        print(f"  {st:46s}: n={s['n']:3d} WR={wr:5.1f}%  avg={avg:+.3f}%")

    # ── Rejection reason breakdown ──────────────────────────────────────────
    print(f"\nGATE2 — top rejection reasons:")
    g2_reasons: dict[str, int] = {}
    for r in results:
        if r['gate'] == 'REJECT_GATE2':
            reason = r['reason'] or 'unknown'
            g2_reasons[reason] = g2_reasons.get(reason, 0) + 1
    for reason, cnt in sorted(g2_reasons, key=g2_reasons.__getitem__, reverse=True)[:10]:
        print(f"  [{cnt:4d}] {reason}")

    print("\nDone.")


if __name__ == '__main__':
    main()
