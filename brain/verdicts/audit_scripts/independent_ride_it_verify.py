#!/usr/bin/env python3
"""
independent_ride_it_verify.py — INDEPENDENT AUDIT of Option B (ride_it HARD_MAX_LOSS -2.5%)

Fresh implementation. Does NOT reuse any prior backtest code or results.
Simulates two exit scenarios on ride_it-mapped LONG trades (last 30d) from PostgreSQL,
using 5m candles from /root/.hermes/data/candles.db, time-sliced (no look-ahead).

Scenarios:
  CURRENT: HARD_MAX_LOSS = -1.0% (unleveraged price move, as compute_live_pnl)
  OPTION_B: HARD_MAX_LOSS = -2.5% for _is_ride_it substring signals (per plan code), else -1.0%

Two stacks per scenario:
  ISOLATED: hard stop + ride_it exit only (mirrors the claimed backtest's apparent methodology)
  PRODUCTION: + stale_exit(-1.0% stalled 8min), SOFT PEAK-EXIT(2h, 0.3%), cut_loser T1
              (non-bypass signals), profit-monster/PM trail(non-bypass), ATR-engine trail
              (0.4% act, 0.15% dist), UNIVERSAL_MAX_HOLD 8h (non-ride_it substring)

Run: cd /root/.hermes/scripts && python3 ../brain/verdicts/audit_scripts/independent_ride_it_verify.py
"""
import json, math, os, sqlite3, sys
from datetime import datetime, timezone, timedelta
from collections import Counter

sys.path.insert(0, '/root/.hermes/scripts')

CANDLES_DB = '/root/.hermes/data/candles.db'

# ── Constants (read from hermes_constants.py at runtime) ──────────────────────
from hermes_constants import (
    RIDE_IT_SL_PHASE1_MULT, RIDE_IT_SL_PHASE1_FLOOR, RIDE_IT_SL_PHASE1_CAP,
    RIDE_IT_TRAIL_ACTIVATE, RIDE_IT_TRAIL_DISTANCE,
    RIDE_IT_MOMENTUM_VEL, RIDE_IT_MOMENTUM_CANDLES,
    RIDE_IT_SPIKE_VOLUME_MULT, RIDE_IT_SPIKE_TRAIL_DISTANCE, RIDE_IT_SPIKE_MIN_MOVE,
    RIDE_IT_MAX_HOLD_HOURS, RIDE_IT_PHASE1_TO_PHASE2_TIME,
    STALE_LOSER_MAX_LOSS, STALE_LOSER_TIMEOUT_MINUTES, VEL_STALE_THRESHOLD_PCT,
    UNIVERSAL_MAX_HOLD_MINUTES, PM_TRAIL_ACTIVATE_PCT, PM_TRAIL_TIERS,
    PROFIT_MONSTER_BYPASS_SIGNALS, CL_TIER1_MIN_PCT, CL_TIER1_MAX_PCT,
)

RIDE_IT_EXIT_PREFIXES = (
    'trend-ride', 'trend_ride', 'volume-breakout', 'volume_breakout', 'mover',
)  # SIGNAL_EXIT_CONFIG ride_it keys (mover+ NOT exit-mapped, but plan's hard-stop
   # exemption uses _is_ride_it substring which includes 'mover' — noted separately)

def is_ride_it_exit(signal: str) -> bool:
    """Per SIGNAL_EXIT_CONFIG: which parts map to ride_it exit management."""
    for part in str(signal).split(','):
        p = part.strip()
        if any(p.startswith(x) for x in ('trend-ride', 'trend_ride', 'volume-breakout', 'volume_breakout')):
            return True
        if p in ('mover', 'mover-'):
            return True
    return False

def is_ride_it_substring(signal: str) -> bool:
    """Per position_manager._is_ride_it (used for hard-stop exemption + 8h hold exemption)."""
    s = str(signal)
    return any(x in s for x in ('ride_it', 'trend-ride', 'trend_ride',
                                'volume-breakout', 'volume_breakout', 'mover'))

def bypasses_pm_trail(signal: str) -> bool:
    """PROFIT_MONSTER_BYPASS_SIGNALS — substring match (as cut_loser SQL uses LIKE %s%)."""
    s = str(signal)
    return any(b in s for b in PROFIT_MONSTER_BYPASS_SIGNALS)

# ── Data loading ──────────────────────────────────────────────────────────────
conn = sqlite3.connect(CANDLES_DB, timeout=10)

def load_5m(token, t_from, t_to):
    cur = conn.cursor()
    cur.execute("""SELECT ts, open, high, low, close, volume FROM candles_5m
                   WHERE token=? AND is_closed=1 AND ts>=? AND ts<=? ORDER BY ts""",
                (token, t_from, t_to))
    rows = cur.fetchall()
    cur.close()
    return rows

def atr_14_at(token, ts, cache):
    """ATR(14) from 1h candles closed at or before ts. Chronological (fixed order)."""
    key = (token, ts // 3600)  # hourly cache granularity
    if key in cache:
        return cache[key]
    cur = conn.cursor()
    cur.execute("""SELECT open, high, low, close FROM candles_1h
                   WHERE token=? AND is_closed=1 AND ts<=? ORDER BY ts DESC LIMIT 19""",
                (token, ts))
    rows = cur.fetchall()
    cur.close()
    rows.reverse()
    if len(rows) < 15:
        cache[key] = 0.0
        return 0.0
    trs = []
    for i in range(1, len(rows)):
        h, l, pc = rows[i][1], rows[i][2], rows[i - 1][3]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    atr = sum(trs[-14:]) / 14
    cache[key] = atr
    return atr

# ── Load trades from PostgreSQL ───────────────────────────────────────────────
import psycopg2
from _secrets import BRAIN_DB_DICT
pconn = psycopg2.connect(**BRAIN_DB_DICT)
pcur = pconn.cursor()
pcur.execute("""
SELECT id, token, signal, entry_price, exit_price, pnl_pct, open_time, close_time,
       close_reason, sl_distance
FROM trades
WHERE direction='LONG'
AND (signal LIKE '%trend-ride%' OR signal LIKE '%volume-breakout%' OR signal LIKE '%volume_breakout%' OR signal LIKE '%mover%')
AND open_time >= now() - interval '30 days'
ORDER BY open_time
""")
cols = [d[0] for d in pcur.description]
trades = [dict(zip(cols, r)) for r in pcur.fetchall()]
pcur.close(); pconn.close()

# Exclude the trade the claimed backtest also excluded (AVAX id 15967) for comparability
AVAX_ID = 15967
sample = [t for t in trades if t['id'] != AVAX_ID]
print(f"Trades in DB window: {len(trades)}; using claimed-comparable sample: {len(sample)}")

# ── Simulation core ───────────────────────────────────────────────────────────
def simulate2(trade, stack, option_b):
    """Same as simulate but tracks hold time properly."""
    token = trade['token'].upper()
    signal = str(trade['signal'] or '')
    entry = float(trade['entry_price'])
    if entry <= 0:
        return None
    open_dt = trade['open_time']
    if open_dt.tzinfo is None:
        open_dt = open_dt.replace(tzinfo=timezone.utc)
    t0 = int(open_dt.timestamp())
    db_sl_dist = float(trade['sl_distance'] or 0.015)

    bars = load_5m(token, t0 - 60, t0 + 26 * 3600)
    bars = [b for b in bars if b[0] >= t0 - 55]
    if not bars:
        return {'pnl': 0.0, 'reason': 'no_data', 'hold_h': 0.0}

    atr_cache = {}
    ride_exit = is_ride_it_exit(signal)
    ride_substr = is_ride_it_substring(signal)
    pm_bypass = bypasses_pm_trail(signal)

    atr0 = atr_14_at(token, bars[0][0], atr_cache)
    if ride_exit and atr0 > 0:
        dist = min(max(atr0 * RIDE_IT_SL_PHASE1_MULT, entry * RIDE_IT_SL_PHASE1_FLOOR),
                   entry * RIDE_IT_SL_PHASE1_CAP)
        sl = entry - dist
    else:
        sl = entry * (1 - db_sl_dist)

    highest = entry
    closes = []
    vol_hist = []
    flat_bars = 0
    hard_level = -2.5 if (option_b and ride_substr) else -1.0
    hard_price = entry * (1 + hard_level / 100.0)

    for (ts, o, h, l, c, v) in bars:
        age_s = ts - t0
        if l <= sl:
            return {'pnl': (sl / entry - 1) * 100.0, 'reason': 'sl_hit',
                    'hold_h': age_s / 3600.0}
        highest = max(highest, h)
        profit = (c / entry - 1) * 100.0

        if ride_exit:
            if vol_hist:
                avg_v = sum(vol_hist[-20:]) / len(vol_hist[-20:])
                vol_ratio = v / avg_v if avg_v > 0 else 1.0
            else:
                vol_ratio = 1.0
            if vol_ratio >= RIDE_IT_SPIKE_VOLUME_MULT and abs(profit) >= RIDE_IT_SPIKE_MIN_MOVE * 100:
                spike_sl = highest * (1 - RIDE_IT_SPIKE_TRAIL_DISTANCE)
                if spike_sl > sl:
                    sl = spike_sl
            elif age_s < RIDE_IT_PHASE1_TO_PHASE2_TIME:
                atr = atr_14_at(token, ts, atr_cache)
                if atr > 0:
                    dist = min(max(atr * RIDE_IT_SL_PHASE1_MULT, entry * RIDE_IT_SL_PHASE1_FLOOR),
                               entry * RIDE_IT_SL_PHASE1_CAP)
                    sl = entry - dist
            else:
                if len(closes) >= RIDE_IT_MOMENTUM_CANDLES + 1 and profit > 1.0:
                    bad = 0
                    for k in range(1, min(RIDE_IT_MOMENTUM_CANDLES + 1, len(closes))):
                        vel = (closes[-k] - closes[-k - 1]) / closes[-k - 1] * 100 if closes[-k - 1] > 0 else 0
                        if vel < RIDE_IT_MOMENTUM_VEL:
                            bad += 1
                        else:
                            break
                    if bad >= RIDE_IT_MOMENTUM_CANDLES:
                        return {'pnl': profit, 'reason': 'ride_it_momentum', 'hold_h': age_s / 3600.0}
                if profit >= RIDE_IT_TRAIL_ACTIVATE * 100:
                    trail_sl = highest * (1 - RIDE_IT_TRAIL_DISTANCE)
                    if trail_sl > sl:
                        sl = trail_sl

        if profit <= hard_level:
            return {'pnl': (min(hard_price, c) / entry - 1) * 100.0, 'reason': 'hard_stop',
                    'hold_h': age_s / 3600.0}

        if stack == 'production':
            if profit <= STALE_LOSER_MAX_LOSS and len(closes) >= 2:
                m1 = abs((closes[-1] - closes[-2]) / closes[-2] * 100) if closes[-2] > 0 else 99
                m2 = abs((closes[-2] - closes[-3]) / closes[-3] * 100) if len(closes) >= 3 and closes[-3] > 0 else 99
                if m1 < VEL_STALE_THRESHOLD_PCT and m2 < VEL_STALE_THRESHOLD_PCT:
                    flat_bars += 1
                else:
                    flat_bars = 0
                if flat_bars * 5 >= STALE_LOSER_TIMEOUT_MINUTES:
                    return {'pnl': profit, 'reason': 'stale_exit', 'hold_h': age_s / 3600.0}

            if age_s >= 2 * 3600 and profit <= 0:
                soft_sl = c * (1 - 0.003)
                if soft_sl > sl:
                    sl = soft_sl

            if not pm_bypass and CL_TIER1_MIN_PCT <= profit <= CL_TIER1_MAX_PCT:
                return {'pnl': profit, 'reason': 'cut_loser_T1', 'hold_h': age_s / 3600.0}

            if not pm_bypass and profit >= PM_TRAIL_ACTIVATE_PCT * 100:
                for minp, d in PM_TRAIL_TIERS:
                    if profit >= minp * 100:
                        pm_sl = highest * (1 - d)
                        if pm_sl > sl:
                            sl = pm_sl
                        break

            if profit >= 0.4:
                atr_sl = highest * (1 - 0.0015)
                if atr_sl > sl:
                    sl = atr_sl

            if not ride_substr and age_s >= UNIVERSAL_MAX_HOLD_MINUTES * 60:
                return {'pnl': profit, 'reason': 'universal_max_hold', 'hold_h': age_s / 3600.0}

        if ride_exit and age_s >= RIDE_IT_MAX_HOLD_HOURS * 3600:
            return {'pnl': profit, 'reason': 'ride_it_max_hold', 'hold_h': age_s / 3600.0}

        closes.append(c)
        vol_hist.append(v)

    last = bars[-1]
    return {'pnl': (last[4] / entry - 1) * 100.0, 'reason': 'data_end',
            'hold_h': (last[0] - t0) / 3600.0}

# ── Run all scenario/stack combos ────────────────────────────────────────────
results = {}
for stack in ('isolated', 'production'):
    for ob in (False, True):
        key = f"{stack}__{'optionB' if ob else 'current'}"
        out = []
        for t in sample:
            r = simulate2(t, stack, ob)
            if r:
                r.update({'token': t['token'], 'signal': t['signal'], 'id': t['id'],
                          'db_pnl_pct': float(t['pnl_pct']) if t['pnl_pct'] is not None else None,
                          'db_reason': t['close_reason']})
                out.append(r)
        results[key] = out

def agg(rows):
    pnls = [r['pnl'] for r in rows]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    holds = [r['hold_h'] for r in rows]
    return {
        'n': n,
        'WR%': round(wins / n * 100, 1) if n else 0,
        'avg%': round(sum(pnls) / n, 3) if n else 0,
        'total%': round(sum(pnls), 1),
        'max_loss%': round(min(pnls), 2) if n else 0,
        'avg_hold_h': round(sum(holds) / n, 2) if n else 0,
        'reasons': dict(Counter(r['reason'] for r in rows)),
        'avg_leveraged%': round(sum(pnls) / n * 3, 3) if n else 0,
    }

print("\n" + "=" * 70)
print("INDEPENDENT SIMULATION RESULTS (my code, my data, no look-ahead)")
print("=" * 70)
for key, rows in results.items():
    a = agg(rows)
    print(f"\n--- {key} ---")
    print(f"  n={a['n']}  WR={a['WR%']}%  avg={a['avg%']}%  total={a['total%']}%  "
          f"max_loss={a['max_loss%']}%  avg_hold={a['avg_hold_h']}h")
    print(f"  reasons: {a['reasons']}")
    print(f"  avg @3x lev: {a['avg_leveraged%']}%")

# Deltas
print("\n" + "=" * 70)
print("DELTA (Option B - Current)")
print("=" * 70)
for stack in ('isolated', 'production'):
    cur = agg(results[f'{stack}__current'])
    ob = agg(results[f'{stack}__optionB'])
    print(f"\n{stack}:")
    print(f"  WR: {cur['WR%']}% -> {ob['WR%']}%  (delta {ob['WR%']-cur['WR%']:+.1f}pp)")
    print(f"  avg: {cur['avg%']}% -> {ob['avg%']}%  (delta {ob['avg%']-cur['avg%']:+.3f}pp)")
    print(f"  total: {cur['total%']}% -> {ob['total%']}%  (delta {ob['total%']-cur['total%']:+.1f}pp)")
    print(f"  max_loss: {cur['max_loss%']}% -> {ob['max_loss%']}%")
    print(f"  reasons cur: {cur['reasons']}")
    print(f"  reasons ob : {ob['reasons']}")

# Per-signal-family breakdown for production stack
print("\n" + "=" * 70)
print("PER-SIGNAL BREAKDOWN (production stack)")
print("=" * 70)
for fam in ('trend-ride', 'volume-breakout', 'volume_breakout', 'mover+'):
    fam_cur = [r for r in results['production__current'] if fam in str(r['signal'])]
    fam_ob = [r for r in results['production__optionB'] if fam in str(r['signal'])]
    if not fam_cur:
        continue
    ac, ao = agg(fam_cur), agg(fam_ob)
    print(f"  {fam:<20} n={ac['n']}  WR {ac['WR%']}%->{ao['WR%']}%  "
          f"avg {ac['avg%']}%->{ao['avg%']}%  total {ac['total%']}%->{ao['total%']}%")

# Trade-by-trade comparison for trades whose outcome CHANGES between scenarios (production)
print("\n" + "=" * 70)
print("TRADES WHOSE OUTCOME CHANGES CURRENT->OPTION_B (production stack)")
print("=" * 70)
cur_by_id = {r['id']: r for r in results['production__current']}
ob_by_id = {r['id']: r for r in results['production__optionB']}
for tid, rc in cur_by_id.items():
    ro = ob_by_id[tid]
    if abs(rc['pnl'] - ro['pnl']) > 0.01:
        print(f"  id={tid} {rc['token']:<8} {str(rc['signal'])[:32]:<32} "
              f"cur={rc['pnl']:+.2f}% ({rc['reason']}, {rc['hold_h']:.2f}h) -> "
              f"ob={ro['pnl']:+.2f}% ({ro['reason']}, {ro['hold_h']:.2f}h)")

# Save full results
out_path = '/root/.hermes/brain/verdicts/audit_scripts/independent_verify_results.json'
with open(out_path, 'w') as f:
    json.dump({k: agg(v) | {'trades': v} for k, v in results.items()}, f, indent=1, default=str)
print(f"\nSaved: {out_path}")
conn.close()
