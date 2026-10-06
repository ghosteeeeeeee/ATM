#!/usr/bin/env python3
"""
sim_fixed_ride_it.py — Backtest the FIXED ride_it exit vs the current exit stack.

Replays every target LONG trade (closed last 30 days) forward over actual 5m
candles from candles.db and evaluates BOTH exit stacks candle-by-candle.

RIDE_IT stack (fixed implementation, mirrors ride_it_exit.py + overlays):
  1. ATR(14) from 1h candles, DESC->ASC reversed before TR (bug-fix path)
  2. Phase 1 (0-2h): SL = entry*(1 - min(max(2.0*ATR_pct, 1.3%), 2.5%)), no trailing,
     SL refreshes from live ATR (can widen — the phase-1 widen fix)
  3. HARD_MAX_LOSS -1.0% active (WARN #3 — fires before the ride_it SL)
  4. Phase 2 (2h+): trail at 2% profit, 1.2% distance (peak-based, price space)
  5. Momentum exit: 2h+, profit>1%, 2 consecutive 5m candles with return < -0.5%
  6. Volume spike override: vol>=5x 20-bar avg AND |pnl|>=3% -> 0.5% trail from peak
  7. SOFT PEAK-EXIT: age>=2h and pnl<=0 -> SL raised to close*(1-0.3%)
  8. stale_exit: STALE_WINNER +0.6%/60min, STALE_LOSER -1.0%/8min (stall approx.)
  9. Max hold 24h

CURRENT stack (task spec):
  1. SL = entry*(1-1.5%)  (never fires — HARD_MAX_LOSS dominates)
  2. cut_loser T1 -1.0..-2.5% (subsumed by HARD_MAX_LOSS at -1.0%)
  3. HARD_MAX_LOSS -1.0%
  4. PM trail: activate +0.4%, 1.2% distance (pnl-space, peak-based)
  5. SOFT PEAK-EXIT (same)
  6. stale_exit (same)
  7. Max hold 8h (universal)

Sensitivity variants (production caveats):
  current_tiered : PM trail with production PM_TRAIL_TIERS distance (0.2/0.5/0.8/1.2%)
  current_pump   : production pump_exit for pump-chain+ (ATR*3 trail + momentum +
                   dead-money 2h) on top of the same overlays

Usage:
  cd /root/.hermes/scripts && python3 /root/.hermes/brain/verdicts/audit_scripts/sim_fixed_ride_it.py
"""
import sys, os, json, sqlite3
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter
from bisect import bisect_right

sys.path.insert(0, '/root/.hermes/scripts')
from paths import CANDLES_DB  # noqa: E402
from hermes_constants import (  # noqa: E402
    RIDE_IT_SL_PHASE1_MULT, RIDE_IT_SL_PHASE1_FLOOR, RIDE_IT_SL_PHASE1_CAP,
    RIDE_IT_TRAIL_ACTIVATE, RIDE_IT_TRAIL_DISTANCE,
    RIDE_IT_MOMENTUM_VEL, RIDE_IT_MOMENTUM_CANDLES,
    RIDE_IT_SPIKE_VOLUME_MULT, RIDE_IT_SPIKE_TRAIL_DISTANCE, RIDE_IT_SPIKE_MIN_MOVE,
    RIDE_IT_PHASE1_TO_PHASE2_TIME, RIDE_IT_MAX_HOLD_HOURS,
    TRAILING_ACTIVATION_PCT, TRAILING_DISTANCE_PCT,
    CUT_LOSER_PNL, UNIVERSAL_MAX_HOLD_MINUTES,
    STALE_WINNER_TIMEOUT_MINUTES, STALE_LOSER_TIMEOUT_MINUTES,
    STALE_WINNER_MIN_PROFIT, STALE_LOSER_MAX_LOSS,
    PM_TRAIL_TIERS,
)
import psycopg2  # noqa: E402
from _secrets import BRAIN_DB_DICT  # noqa: E402

# ── Overlay constants (from position_manager.py) ──────────────────────────────
HARD_MAX_LOSS_PCT = CUT_LOSER_PNL / 100.0        # -1.00% -> -0.01
SOFT_TRIGGER_HOURS = 2.0
SOFT_TRAIL_PCT = 0.003                            # 0.3%
CURRENT_STACK_SL_PCT = 0.015                      # task-spec 1.5% initial SL
PM_TRAIL_ACTIVATE = TRAILING_ACTIVATION_PCT       # 0.004
PM_TRAIL_DISTANCE = TRAILING_DISTANCE_PCT         # 0.012
CURRENT_MAX_HOLD_H = UNIVERSAL_MAX_HOLD_MINUTES / 60.0   # 8h
RIDE_IT_MAX_HOLD_H = RIDE_IT_MAX_HOLD_HOURS                # 24h
# Production profit_monster tiered trail distances (pnl space) — sensitivity only
PM_TIER_DIST = [(m * 100, d) for m, d in PM_TRAIL_TIERS]  # (min_pnl_pct, dist_frac)
# pump_exit constants (production current exit for pump-chain+)
PUMP_TRAIL_MULT = 3.0
PUMP_MOM_VEL = -0.5
PUMP_MOM_CANDLES = 2
PUMP_TIME_THRESH = 2.0
PUMP_TIME_HOURS = 2.0

STALE_WINNER_PNL = STALE_WINNER_MIN_PROFIT / 100.0   # +0.006
STALE_LOSER_PNL = STALE_LOSER_MAX_LOSS / 100.0       # -0.01
STALL_RANGE_PCT = 0.003   # stall proxy: no 5m candle in window with (h-l)/l >= 0.3%
                          # (mirrors speed_tracker "last significant move >0.3% in 1min")

# ── Signal families ───────────────────────────────────────────────────────────
RIDE_IT_FAMILIES = ['volume-breakout-long+', 'doji-bottom-long', 'bb_bounce_v2_long',
                    'grind-trend+', 'pump-chain+']
CONTROL_FAMILIES = ['bb-squeeze+', 'mover+', 'rr-struct+']


def classify_signal(sig):
    """Map a (possibly comma-combo) signal string to a target family."""
    for part in str(sig or '').split(','):
        pl = part.strip().lower()
        if not pl:
            continue
        if 'volume-breakout-long' in pl or 'volume_breakout_long' in pl:
            return 'volume-breakout-long+'
        if pl.startswith('doji-bottom-long'):
            return 'doji-bottom-long'
        if pl.startswith('bb_bounce_v2_long') or pl.startswith('bb-bounce-v2-long'):
            return 'bb_bounce_v2_long'
        if pl.startswith('grind-trend'):
            return 'grind-trend+'
        if pl.startswith('pump-chain') or pl.startswith('pump_chain'):
            return 'pump-chain+'
        if pl.startswith('bb-squeeze'):
            return 'bb-squeeze+'
        if pl.startswith('mover'):
            return 'mover+'
        if pl.startswith('rr-struct+'):
            return 'rr-struct+'
    return None


# ── Candle / ATR loading ──────────────────────────────────────────────────────
_c5_cache = {}
_atr_cache = {}


def load_candles5(token, ts_from, ts_to):
    key = (token, ts_from // 3600, ts_to // 3600)
    if key in _c5_cache:
        return _c5_cache[key]
    conn = sqlite3.connect(CANDLES_DB, timeout=10)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT ts, open, high, low, close, volume FROM candles_5m
            WHERE token = ? AND is_closed = 1 AND ts >= ? AND ts <= ?
            ORDER BY ts ASC
        """, (token, ts_from, ts_to))
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()
    _c5_cache[key] = rows
    return rows


def load_atr_series(token, ts_from, ts_to):
    """Return [(ts, atr14)] from 1h candles, chronological. ATR computed with the
    bug-fixed path: query DESC, reverse to ASC, then TR with true previous close."""
    key = (token, ts_from // 3600, ts_to // 3600)
    if key in _atr_cache:
        return _atr_cache[key]
    conn = sqlite3.connect(CANDLES_DB, timeout=10)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT ts, open, high, low, close FROM candles_1h
            WHERE token = ? AND is_closed = 1 AND ts >= ? AND ts <= ?
            ORDER BY ts DESC LIMIT 600
        """, (token, ts_from, ts_to))
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()
    rows.reverse()  # DESC -> ASC  (THE bug-fix)
    series = []
    trs = []
    for i, (ts, o, h, l, c) in enumerate(rows):
        if i == 0:
            trs.append(h - l)
        else:
            pc = rows[i - 1][4]
            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        if len(trs) >= 14:
            series.append((ts, sum(trs[-14:]) / 14.0))
    _atr_cache[key] = series
    return series


def atr_as_of(series, ts):
    if not series:
        return 0.0
    idx = bisect_right([s[0] for s in series], ts) - 1
    if idx < 0:
        return 0.0
    return series[idx][1]


def _pm_tier_distance(peak_pnl_frac):
    dist = PM_TIER_DIST[0][1]
    for min_p, d in PM_TIER_DIST:
        if peak_pnl_frac * 100 >= min_p:
            dist = d
    return dist


def is_stalled(candles5, i, ts, window_sec):
    """Stall proxy: no 5m candle in (ts-window, ts] has (h-l)/l >= 0.3%."""
    lo = ts - window_sec
    for j in range(i, -1, -1):
        c = candles5[j]
        if c[0] <= lo:
            break
        if c[2] > 0 and (c[2] - c[3]) / c[3] >= STALL_RANGE_PCT:
            return False
    return True


def _parse_dt(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(v).replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None


# ── Core replay ───────────────────────────────────────────────────────────────
def simulate(trade, candles5, atr_series, stack):
    """Replay one trade under one exit stack. Returns dict or None if no data."""
    entry = float(trade['entry_price'])
    if entry <= 0 or not candles5:
        return None
    open_dt = trade['open_dt']
    close_dt = trade['close_dt']
    open_ts = open_dt.timestamp()

    if stack.startswith('ride_it'):
        max_hold_s = RIDE_IT_MAX_HOLD_H * 3600
    else:
        max_hold_s = CURRENT_MAX_HOLD_H * 3600
    end_limit = min(close_dt.timestamp(), open_ts + max_hold_s)

    bucket = int(open_ts // 300) * 300
    c5 = [c for c in candles5 if bucket <= c[0] <= end_limit + 300]
    if not c5:
        return None
    # coverage check: candles must reach (close to) end_limit
    if c5[-1][0] < end_limit - 900:
        return None  # insufficient candle coverage — excluded, counted separately

    # ── initial state ──
    peak_high = entry
    peak_pnl = 0.0
    sl_levels = {}          # name -> SL price (LONG: higher = tighter)
    trail_active = False    # current stack PM trail
    spike_active = False

    if stack.startswith('ride_it'):
        atr0 = atr_as_of(atr_series, open_ts)
        if atr0 > 0:
            d = min(max(RIDE_IT_SL_PHASE1_MULT * (atr0 / entry),
                        RIDE_IT_SL_PHASE1_FLOOR), RIDE_IT_SL_PHASE1_CAP) * entry
            sl_levels['phase1_sl'] = entry - d
    else:
        sl_levels['initial_sl'] = entry * (1 - CURRENT_STACK_SL_PCT)

    hard_stop = entry * (1 + HARD_MAX_LOSS_PCT)  # entry*0.99
    # ride_it_nohardmax: WARN #3 probe — what happens if the -1.0% hard stop is
    # removed and the ride_it phase-1 survival SL (1.3-2.5%) is allowed to fire?
    no_hard_max = (stack == 'ride_it_nohardmax')

    n = len(c5)
    for i in range(n):
        ts, o, h, l, c, v = c5[i]
        age_h = (ts - open_ts) / 3600.0
        pnl_c = (c - entry) / entry

        # ── ADVERSE checks on candle low (first level hit = highest price) ──
        levels = dict(sl_levels)
        if stack in ('current', 'current_tiered') and trail_active:
            dist = _pm_tier_distance(peak_pnl) if stack == 'current_tiered' else PM_TRAIL_DISTANCE
            levels['pm_trail'] = entry * (1 + peak_pnl - dist)
        if stack == 'current_pump' and atr_as_of(atr_series, ts) > 0:
            # pump trail active from the start (engine trails every wake)
            atr_now = atr_as_of(atr_series, ts)
            levels['pump_trail'] = peak_high - PUMP_TRAIL_MULT * atr_now
        cand = [] if no_hard_max else [('hard_max_loss', hard_stop)]
        for nm, px in levels.items():
            if nm == 'pm_trail':
                cand.append(('pm_trail', px))
            elif nm == 'pump_trail':
                cand.append(('pump_trail', px))
            else:
                cand.append((nm, px))
        cand = [(nm, px) for nm, px in cand if px and px > 0]
        if cand:
            tightest_nm, tightest_px = max(cand, key=lambda x: x[1])
            if l <= tightest_px:
                fill = tightest_px
                if tightest_nm == 'hard_max_loss':
                    reason = 'hard_max_loss'
                elif tightest_nm == 'initial_sl':
                    reason = 'atr_sl'          # 1.5% initial (unreachable vs hard_max)
                elif tightest_nm == 'phase1_sl':
                    reason = 'ride_it_phase1_sl'   # unreachable when dist>1.0%
                elif tightest_nm in ('pm_trail',):
                    reason = 'pm_trail'
                elif tightest_nm == 'pump_trail':
                    reason = 'pump_trail'
                elif tightest_nm in ('p2_trail', 'spike_trail'):
                    reason = 'ride_it_trail'
                elif tightest_nm == 'soft_trail':
                    reason = 'soft_peak_exit'
                else:
                    reason = tightest_nm
                return _result(trade, stack, reason, fill, ts)

        # ── UPDATES on candle close (favorable / neutral) ──
        peak_high = max(peak_high, h)
        peak_pnl = max(peak_pnl, pnl_c)

        # volume ratio for spike override
        def vol_ratio_at(idx):
            if idx < 20:
                return 1.0
            prev = [c5[k][5] for k in range(idx - 20, idx)]
            avg = sum(prev) / len(prev)
            return (c5[idx][5] / avg) if avg > 0 else 1.0

        if stack == 'current_tiered':
            if not trail_active and pnl_c >= PM_TRAIL_ACTIVATE and (ts - open_ts) >= 120:
                trail_active = True
        elif stack == 'current':
            if not trail_active and pnl_c >= PM_TRAIL_ACTIVATE and (ts - open_ts) >= 120:
                trail_active = True
        elif stack == 'current_pump':
            # pump momentum exit (2 consecutive 5m returns < -0.5%)
            if i >= PUMP_MOM_CANDLES:
                rets = []
                for k in range(i - PUMP_MOM_CANDLES + 1, i + 1):
                    pc = c5[k - 1][4]
                    rets.append((c5[k][4] - pc) / pc if pc > 0 else 0.0)
                if all(r < PUMP_MOM_VEL / 100.0 for r in rets):
                    return _result(trade, stack, 'pump_exit_momentum', c, ts)
            # dead money: >2h, pnl < 2%, 5m velocity fading
            if age_h > PUMP_TIME_HOURS and pnl_c * 100 < PUMP_TIME_THRESH and i >= 1:
                pc = c5[i - 1][4]
                vel = (c - pc) / pc if pc > 0 else 0.0
                if vel < 0:
                    return _result(trade, stack, 'pump_exit_dead_money', c, ts)
        elif stack.startswith('ride_it'):
            # volume spike override (any phase)
            vr = vol_ratio_at(i)
            if vr >= RIDE_IT_SPIKE_VOLUME_MULT and abs(pnl_c) >= RIDE_IT_SPIKE_MIN_MOVE:
                spike_sl = peak_high - RIDE_IT_SPIKE_TRAIL_DISTANCE * c
                if spike_sl > sl_levels.get('spike_trail', 0):
                    sl_levels['spike_trail'] = spike_sl
                    spike_active = True
            if age_h * 3600 >= RIDE_IT_PHASE1_TO_PHASE2_TIME:
                # momentum exit
                if pnl_c > 0.01 and i >= RIDE_IT_MOMENTUM_CANDLES:
                    rets = []
                    for k in range(i - RIDE_IT_MOMENTUM_CANDLES + 1, i + 1):
                        pc = c5[k - 1][4]
                        rets.append((c5[k][4] - pc) / pc if pc > 0 else 0.0)
                    if all(r < RIDE_IT_MOMENTUM_VEL / 100.0 for r in rets):
                        return _result(trade, stack, 'ride_it_momentum', c, ts)
                # phase-2 trail at 2% profit
                if pnl_c >= RIDE_IT_TRAIL_ACTIVATE:
                    p2 = peak_high - RIDE_IT_TRAIL_DISTANCE * c
                    if p2 > sl_levels.get('p2_trail', 0):
                        sl_levels['p2_trail'] = p2
            # phase-1 SL refresh from live ATR (can widen — the fix); phase 1 only
            if 'phase1_sl' in sl_levels and age_h * 3600 < RIDE_IT_PHASE1_TO_PHASE2_TIME:
                atr_now = atr_as_of(atr_series, ts)
                if atr_now > 0:
                    d = min(max(RIDE_IT_SL_PHASE1_MULT * (atr_now / entry),
                                RIDE_IT_SL_PHASE1_FLOOR), RIDE_IT_SL_PHASE1_CAP) * entry
                    sl_levels['phase1_sl'] = entry - d

        # stale exits (both stacks)
        if pnl_c >= STALE_WINNER_PNL and is_stalled(c5, i, ts, STALE_WINNER_TIMEOUT_MINUTES * 60):
            return _result(trade, stack, 'stale_winner', c, ts)
        if pnl_c <= STALE_LOSER_PNL and is_stalled(c5, i, ts, STALE_LOSER_TIMEOUT_MINUTES * 60):
            return _result(trade, stack, 'stale_loser', c, ts)

        # SOFT PEAK-EXIT (both stacks): 2h+, pnl<=0 -> raise SL to close*0.997
        if age_h >= SOFT_TRIGGER_HOURS and pnl_c <= 0:
            soft = c * (1 - SOFT_TRAIL_PCT)
            if soft > sl_levels.get('soft_trail', 0):
                sl_levels['soft_trail'] = soft

        # max hold (stack-specific)
        if stack.startswith('ride_it') and age_h >= RIDE_IT_MAX_HOLD_H:
            return _result(trade, stack, 'ride_it_max_hold', c, ts)
        if stack != 'ride_it' and age_h >= CURRENT_MAX_HOLD_H:
            return _result(trade, stack, 'universal_max_hold', c, ts)

    # No modeled trigger fired by end_limit — production closed it some other way
    # (ATR trailing SL, RR engine, guardian, manual). PnL = last candle close.
    last = c5[-1]
    return _result(trade, stack, 'unmodeled_close', last[4], last[0])


def _result(trade, stack, reason, fill_price, exit_ts):
    pnl = (fill_price - trade['entry_price']) / trade['entry_price']
    hold_h = (exit_ts - trade['open_dt'].timestamp()) / 3600.0
    return {
        'stack': stack, 'reason': reason, 'pnl_pct': pnl * 100.0,
        'hold_h': hold_h, 'exit_ts': exit_ts,
        'actual_pnl_pct': trade['pnl_pct'], 'family': trade['family'],
        'token': trade['token'], 'signal': trade['signal'], 'id': trade['id'],
        'leverage': trade['leverage'],
    }


# ── Aggregation ───────────────────────────────────────────────────────────────
def aggregate(rows):
    if not rows:
        return None
    pnls = [r['pnl_pct'] for r in rows]
    holds = [r['hold_h'] for r in rows]
    wins = sum(1 for p in pnls if p > 0)
    return {
        'n': len(rows),
        'win_rate': round(100.0 * wins / len(rows), 1),
        'avg_pnl_pct': round(sum(pnls) / len(pnls), 3),
        'total_pnl_pct': round(sum(pnls), 2),
        'avg_hold_h': round(sum(holds) / len(holds), 2),
        'exit_reasons': dict(Counter(r['reason'] for r in rows).most_common()),
    }


def main():
    now = datetime.now(timezone.utc)
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, token, signal, entry_price, open_time, close_time,
               pnl_pct, exit_reason, leverage, amount_usdt
        FROM trades
        WHERE status = 'closed' AND direction = 'LONG'
          AND close_time >= %s
          AND entry_price > 0 AND open_time IS NOT NULL AND close_time IS NOT NULL
    """, (now - timedelta(days=30),))
    raw = cur.fetchall()
    cur.close()
    conn.close()

    trades = []
    skipped = Counter()
    for (tid, token, signal, entry_price, open_time, close_time,
         pnl_pct, exit_reason, leverage, amount_usdt) in raw:
        fam = classify_signal(signal)
        if fam is None:
            skipped['unclassified_signal'] += 1
            continue
        od, cd = _parse_dt(open_time), _parse_dt(close_time)
        if od is None or cd is None:
            skipped['bad_datetime'] += 1
            continue
        trades.append({
            'id': tid, 'token': token, 'signal': signal, 'family': fam,
            'entry_price': float(entry_price), 'open_dt': od, 'close_dt': cd,
            'pnl_pct': float(pnl_pct or 0), 'exit_reason': exit_reason,
            'leverage': leverage, 'amount_usdt': amount_usdt,
        })
    print(f"Loaded {len(trades)} classified trades (skipped: {dict(skipped)})")

    stacks = ['current', 'current_tiered', 'current_pump', 'ride_it', 'ride_it_nohardmax']
    results = defaultdict(lambda: defaultdict(list))
    excluded = Counter()

    for t in trades:
        tok = t['token'].upper()
        open_ts = t['open_dt'].timestamp()
        end_limit = min(t['close_dt'].timestamp(), open_ts + RIDE_IT_MAX_HOLD_H * 3600)
        c5 = load_candles5(tok, int(open_ts) - 3600, int(end_limit) + 600)
        atr_s = load_atr_series(tok, int(open_ts) - 26 * 3600, int(end_limit) + 600)
        if not c5:
            excluded['no_candles'] += 1
            continue
        ok_any = False
        for stack in stacks:
            r = simulate(t, c5, atr_s, stack)
            if r is None:
                continue
            ok_any = True
            results[t['family']][stack].append(r)
        if not ok_any:
            excluded['insufficient_coverage'] += 1

    # ── Build report structure ──
    fam_order = RIDE_IT_FAMILIES + CONTROL_FAMILIES
    report = {
        'generated_at': now.isoformat(),
        'n_trades_classified': len(trades),
        'n_excluded': dict(excluded),
        'params': {
            'ride_it': {
                'sl_phase1_mult': RIDE_IT_SL_PHASE1_MULT,
                'sl_phase1_floor': RIDE_IT_SL_PHASE1_FLOOR,
                'sl_phase1_cap': RIDE_IT_SL_PHASE1_CAP,
                'trail_activate': RIDE_IT_TRAIL_ACTIVATE,
                'trail_distance': RIDE_IT_TRAIL_DISTANCE,
                'max_hold_h': RIDE_IT_MAX_HOLD_H,
                'hard_max_loss_pct': HARD_MAX_LOSS_PCT * 100,
                'soft_peak_exit': f"{SOFT_TRIGGER_HOURS}h+ pnl<=0, {SOFT_TRAIL_PCT*100}% trail",
                'stale_winner': f"+{STALE_WINNER_PNL*100}%/{STALE_WINNER_TIMEOUT_MINUTES}min",
                'stale_loser': f"{STALE_LOSER_PNL*100}%/{STALE_LOSER_TIMEOUT_MINUTES}min",
                'momentum_exit': f"{RIDE_IT_MOMENTUM_CANDLES}x5m ret<{RIDE_IT_MOMENTUM_VEL}% & pnl>1% @2h+",
                'spike_override': f"vol>={RIDE_IT_SPIKE_VOLUME_MULT}x & |pnl|>={RIDE_IT_SPIKE_MIN_MOVE*100}% -> {RIDE_IT_SPIKE_TRAIL_DISTANCE*100}% trail",
            },
            'current': {
                'initial_sl_pct': CURRENT_STACK_SL_PCT * 100,
                'pm_trail_activate': PM_TRAIL_ACTIVATE * 100,
                'pm_trail_distance': PM_TRAIL_DISTANCE * 100,
                'hard_max_loss_pct': HARD_MAX_LOSS_PCT * 100,
                'max_hold_h': CURRENT_MAX_HOLD_H,
            },
        },
        'families': {},
    }

    for fam in fam_order:
        fam_rep = {'role': 'ride_it_candidate' if fam in RIDE_IT_FAMILIES else 'control',
                   'stacks': {}, 'delta': {}}
        for stack in stacks:
            rows = results[fam][stack]
            agg = aggregate(rows)
            if agg:
                fam_rep['stacks'][stack] = agg
        cur_agg = fam_rep['stacks'].get('current')
        ride_agg = fam_rep['stacks'].get('ride_it')
        if cur_agg and ride_agg:
            fam_rep['delta'] = {
                'win_rate_pp': round(ride_agg['win_rate'] - cur_agg['win_rate'], 1),
                'avg_pnl_pct': round(ride_agg['avg_pnl_pct'] - cur_agg['avg_pnl_pct'], 3),
                'total_pnl_pct': round(ride_agg['total_pnl_pct'] - cur_agg['total_pnl_pct'], 2),
                'avg_hold_h': round(ride_agg['avg_hold_h'] - cur_agg['avg_hold_h'], 2),
            }
            # WARN #3 probe: ride_it with the -1.0% hard stop removed
            nohard_agg = fam_rep['stacks'].get('ride_it_nohardmax')
            if nohard_agg and ride_agg:
                fam_rep['delta_hardmax_probe'] = {
                    'note': 'ride_it_nohardmax minus ride_it (hard stop removed)',
                    'win_rate_pp': round(nohard_agg['win_rate'] - ride_agg['win_rate'], 1),
                    'avg_pnl_pct': round(nohard_agg['avg_pnl_pct'] - ride_agg['avg_pnl_pct'], 3),
                    'total_pnl_pct': round(nohard_agg['total_pnl_pct'] - ride_agg['total_pnl_pct'], 2),
                }
            # validation: simulated current vs actual DB pnl
            if results[fam]['current']:
                pairs = [(r['pnl_pct'], r['actual_pnl_pct']) for r in results[fam]['current']]
                fam_rep['validation_sim_vs_actual_current'] = {
                    'sim_avg': round(sum(p[0] for p in pairs) / len(pairs), 3),
                    'actual_avg': round(sum(p[1] for p in pairs) / len(pairs), 3),
                }
        report['families'][fam] = fam_rep

    # aggregate across all families
    all_cur, all_ride, all_nohard = [], [], []
    for fam in fam_order:
        all_cur.extend(results[fam]['current'])
        all_ride.extend(results[fam]['ride_it'])
        all_nohard.extend(results[fam]['ride_it_nohardmax'])
    report['aggregate_all'] = {
        'current': aggregate(all_cur), 'ride_it': aggregate(all_ride),
        'ride_it_nohardmax': aggregate(all_nohard),
    }
    if all_cur and all_ride:
        ac, ar = report['aggregate_all']['current'], report['aggregate_all']['ride_it']
        report['aggregate_all']['delta'] = {
            'win_rate_pp': round(ar['win_rate'] - ac['win_rate'], 1),
            'avg_pnl_pct': round(ar['avg_pnl_pct'] - ac['avg_pnl_pct'], 3),
            'total_pnl_pct': round(ar['total_pnl_pct'] - ac['total_pnl_pct'], 2),
        }
        anh = report['aggregate_all'].get('ride_it_nohardmax')
        if anh:
            report['aggregate_all']['delta_hardmax_probe'] = {
                'note': 'ride_it_nohardmax minus ride_it',
                'win_rate_pp': round(anh['win_rate'] - ar['win_rate'], 1),
                'avg_pnl_pct': round(anh['avg_pnl_pct'] - ar['avg_pnl_pct'], 3),
                'total_pnl_pct': round(anh['total_pnl_pct'] - ar['total_pnl_pct'], 2),
            }

    out_json = '/root/.hermes/brain/verdicts/audit_scripts/sim_fixed_results.json'
    with open(out_json, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(json.dumps(report, indent=2, default=str))
    print(f"\nSaved -> {out_json}")


if __name__ == '__main__':
    main()
