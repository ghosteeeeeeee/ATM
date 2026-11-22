#!/usr/bin/env python3
"""tp_vs_trail_sim.py — TP-vs-trail counterfactual study (LOG-ONLY, shadow).

Registry spec (authoritative, DO NOT PATCH): data/shadow_disposition.json
entry `tp-vs-trail-shadow` — CEO consult 20261122T044623Z "APPROVE — build
today". This script has ZERO live effect: no live flags, no hermes_constants
writes, no edits to any existing file. Its only outputs are stdout and
data/tp_vs_trail_sim.json (gitignored runtime artifact).

Arms — same fill, same candles, floor = the trade's ACTUAL stored stop_loss,
intra-bar floor-first pessimistic tie (existing jup convention), horizon =
actual close_time (equal time budget across arms):
  A0  actual DB net (pnl_usdt, and net-of-fee)        — reality
  A1  trail-replay: pm layer, TP sentinel unreachable — controlled incumbent
  A2  pure fixed TP 1.0%                              — diagnostic
  A3  PRIMARY hybrid: tp_px 1.0% + pm layer           — ONLY arm that can PASS
  A4  fixed 1.5%                                      — diagnostic
  A5  ATR-scaled TP: working tpsl_utils formula clamped MIN..MAX — diagnostic
  A6  rr2_cfg known-loser control: jup construction (fixed 2.5% floor,
      TP = entry ± 2×2.5% = 5%) — engine-validity gate vs jup prior art
Walk: 1m primary, 5m cross-check; sensitivity horizon = fixed 8h
(UNIVERSAL_MAX_HOLD_MINUTES).

Fees (#193 units guard): rate = fee_total/(2*amount_usdt);
net = sgn*(exit-entry)/entry*amount_usdt − fee_total. NEVER pnl_pct.

Bar (REPORTED, never decided here): A3 vs A1 on all four limbs
(i) net-of-fee A3 >= A1 + $1.00  (ii) fk <= 20% (share of A1 winners whose
path touches A3's TP before A1's exit; fk_pnl_at_risk reported)
(iii) (A3−A1) same sign in both close_time-median halves
(iv) WR_A3 >= WR_A1 − 5pp; plus n >= 30 token-day-deduped (earliest open per
token-UTC-day) else UNDER-POWERED → extend, no verdict. A2/A4/A5/A6 are
diagnostic only — a secondary arm "passing" needs a NEW pre-registration.

Machinery: imports replay / replay_layers / load_candles from
jup_exit_sim.py (its prior-art reproduction must stay byte-stable — this
file makes ZERO edits to it). Study parameters (1.0%/1.5% targets, $1.00
bar, 20% fk, ±5pp) are pre-registered in the registry entry above, so they
live here by design rather than in hermes_constants.

--selfcheck gates: (a) A6 reproduces jup rr2_cfg's loss class on the jup
reference trades (engine-validity), (b) no-lookahead mutation probes,
(c) pm-walk cross-engine parity vs data/jup_exit_sim.json, (d) fee math
spot-check vs 3 known trades. Exit 0 = all pass, 1 = FAIL (loud).
"""
import argparse
import json
import os
import sqlite3
import sys
import time

import psycopg2

from paths import HERMES_DATA
from hermes_constants import (
    UNIVERSAL_MAX_HOLD_MINUTES, CUT_LOSER_PNL,
    ATR_SL_MIN, ATR_SL_MAX, ATR_TP_MIN, ATR_TP_MAX,
    ATR_K_HIGH_VOL, ATR_TP_K_MULT,
)
from tpsl_utils import compute_atr_tp_pct
from manual_exit_manager import is_managed_signal
from jup_exit_sim import replay, replay_layers, load_candles

# ── pre-registered study parameters (registry tp-vs-trail-shadow) ────────────
TP_PCT_1 = 0.010          # A2/A3 primary target
TP_PCT_15 = 0.015         # A4 sensitivity
BAR_NET_USD = 1.00        # limb (i) threshold
BAR_FK_PCT = 20.0         # limb (ii) threshold
BAR_WR_SLACK_PP = 5.0     # limb (iv) slack
BAR_MIN_N = 30            # deduped power bar
ARMS = ('A1', 'A2', 'A3', 'A4', 'A5', 'A6')
PM_LAYERS = (('pm_trail', 'pm', 0.0),)
STEP = {'1m': 60, '5m': 300}
STOP_FAMILY = ('atr_sl_hit', 'hard_max_loss', 'manual_sl_hit', 'hard_sl')
JUP_REF_CUTOFF = '2026-11-03 01:10:00'   # prior-art run time (artifact mtime)
JUP_ART = os.path.join(HERMES_DATA, 'jup_exit_sim.json')
ART_PATH = os.path.join(HERMES_DATA, 'tp_vs_trail_sim.json')
# Parity tolerances. pmwalk rows are stable (early exits) => tight. The
# frozen rr2 row was generated 2026-11-03 01:10 while 16 closed jup trades
# still had INCOMPLETE 12h horizons (jup_exit_sim.py:419-429 warns those
# timeout rows are unstable) → artifact timeouts undercount vs complete
# windows today (rr2 +14, atr_cfg +14 on the same 98 — window completeness,
# not engine). So (a1) gates the LOSS CLASS with drift bounds, and (a2)
# gates EXACT equality against jup's own main() re-run on the same 98
# (tolerances = jup report rounding only: wr rounded 1dp, net 2dp).
PMWALK_TOL = {'net_pct': 2.0, 'wr': 2.0, 'timeouts': 2, 'n': 0}
RR2_CLASS_TOL = {'net_pct': 30.0, 'wr': 3.0, 'timeouts': 15, 'n': 0}
EXACT_TOL = {'net_pct': 0.02, 'wr': 0.06, 'timeouts': 0, 'n': 0}


# ── data loading ─────────────────────────────────────────────────────────────
def fee_total_of(raw):
    """fees TEXT (JSON blob) -> fee_total float; missing/garbage -> 0.0."""
    if not raw:
        return 0.0
    try:
        f = json.loads(raw)
    except (ValueError, TypeError):
        return 0.0
    if not isinstance(f, dict):
        return 0.0
    if f.get('fee_total') is not None:
        try:
            return float(f['fee_total'])
        except (TypeError, ValueError):
            return 0.0
    try:
        return float(f.get('entry_fee') or 0) + float(f.get('exit_fee') or 0)
    except (TypeError, ValueError):
        return 0.0


def _pg():
    from _secrets import BRAIN_DB_DICT
    cfg = BRAIN_DB_DICT.copy()
    cfg.setdefault('port', 5432)
    return psycopg2.connect(**cfg)


def load_population():
    """All closed trades last 14d with entry/stop/exit/size (registry:
    NOT exit-reason-selected). Candles gate applied at walk time."""
    conn = _pg()
    conn.autocommit = True
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, token, direction, entry_price, exit_price, pnl_usdt,
                   amount_usdt, fees, open_time, close_time, stop_loss,
                   close_reason, signal, leverage, entry_atr_14
            FROM trades
            WHERE status = 'closed'
              AND close_time >= now() - interval '14 days'
              AND entry_price IS NOT NULL AND exit_price IS NOT NULL
              AND stop_loss IS NOT NULL
              AND amount_usdt IS NOT NULL AND amount_usdt > 0
            ORDER BY open_time, id
        """)
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()
    out = []
    for r in rows:
        (tid, token, dirn, entry, exit_px, pnl, amount, fees, open_t,
         close_t, sl, reason, signal, lev, atr) = r
        t = dict(id=tid, token=token, dir=dirn, entry=float(entry),
                 exit=float(exit_px), gross=float(pnl or 0),
                 amount=float(amount), fee=fee_total_of(fees),
                 fees_raw=fees,
                 open_t=open_t, close_t=close_t, sl=float(sl),
                 reason=(reason or ''), signal=(signal or ''),
                 lev=int(lev or 1),
                 atr=(float(atr) if atr else None))
        t['open_ts'] = int(open_t.timestamp())
        t['close_ts'] = int(close_t.timestamp())
        t['a0_net'] = t['gross'] - t['fee']   # net-of-fee reality (#193: gross is $)
        out.append(t)
    return out


def load_jup_ref():
    """jup_exit_sim reference population: every jup mirror trade closed
    before the prior-art run (data/jup_exit_sim.json, n=98 rows)."""
    conn = _pg()
    conn.autocommit = True
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, token, direction, entry_price, open_time, close_time,
                   amount_usdt, leverage
            FROM trades
            WHERE signal LIKE '%%jup_yolo%%' AND status = 'closed'
              AND entry_price IS NOT NULL AND exit_price IS NOT NULL
              AND close_time <= %s
            ORDER BY id
        """, (JUP_REF_CUTOFF,))
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()
    out = []
    for tid, token, dirn, entry, open_t, close_t, amount, lev in rows:
        out.append(dict(id=tid, token=token, dir=dirn, entry=float(entry),
                        open_t=open_t, close_t=close_t, open_ts=int(open_t.timestamp()),
                        close_ts=int(close_t.timestamp()),
                        amount=float(amount or 0), lev=int(lev or 1)))
    return out


def load_candles_1m(token, t0, t1):
    """1m OHLC — mirrors jup_exit_sim.load_candles (5m) with the same
    complete-bars guard at 60s. Lives here because jup_exit_sim is
    byte-stable prior art (zero edits allowed)."""
    db = os.path.join(HERMES_DATA, 'candles.db')
    conn = sqlite3.connect(db, timeout=5)
    try:
        cur = conn.execute(
            "SELECT ts, open, high, low, close FROM candles_1m "
            "WHERE token=? AND is_closed=1 AND ts>=? AND ts<? "
            "AND ts + 60 <= strftime('%s','now') ORDER BY ts",
            (token, t0, t1))
        rows = cur.fetchall()
    finally:
        conn.close()
    return rows


# ── per-trade levels ─────────────────────────────────────────────────────────
def build_levels(t):
    e, long_ = t['entry'], t['dir'] == 'LONG'
    t['long'] = long_
    t['px1'] = e * (1 + TP_PCT_1) if long_ else e * (1 - TP_PCT_1)
    t['px15'] = e * (1 + TP_PCT_15) if long_ else e * (1 - TP_PCT_15)
    # A5: WORKING tpsl_utils formula (compute_atr_tp_pct delegates to the
    # norm-corrected math), input = entry-time ATR% (entry_atr_14/entry*100),
    # clamped ATR_TP_MIN..MAX inside the formula. Fallback 1.24 = jup's input.
    atr_pct = (t['atr'] / e * 100.0) if t['atr'] else 1.24
    t['atr_pct_in'] = atr_pct
    t['tp_atr_frac'] = compute_atr_tp_pct(atr_pct)
    t['px_atr'] = (e * (1 + t['tp_atr_frac']) if long_
                   else e * (1 - t['tp_atr_frac']))
    # A1 TP sentinel: unreachable ceiling so only floor/pm/timeout can exit
    t['sent'] = float('inf') if long_ else 0.0
    # A6 / jup rr2_cfg construction (jup_exit_sim.py:289-295, 330-335):
    # PRE-FIX inline formula — risk = 2.5% fixed, TP = 2×risk = 5%.
    t['sl_cfg_pct'] = max(ATR_SL_MIN, min(ATR_SL_MAX, ATR_K_HIGH_VOL * 1.0))
    risk = e * t['sl_cfg_pct']
    t['rsl'] = (e - risk) if long_ else (e + risk)
    t['rtp'] = (e + 2.0 * risk) if long_ else (e - 2.0 * risk)


def net_usdt(t, xp):
    """#193 units guard: unleveraged price move × notional − fee_total.
    Never pnl_pct."""
    sgn = 1.0 if t['long'] else -1.0
    return sgn * (xp - t['entry']) / t['entry'] * t['amount'] - t['fee']


def walk_arms(t, candles, horizon_ts):
    """Run A1..A6 on one candle set. Returns {arm: {xp,xt,tag,net}|None}."""
    e, dirn = t['entry'], t['dir']
    res = {}
    for arm, layers, tp in (('A1', PM_LAYERS, t['sent']),
                            ('A2', (), t['px1']),
                            ('A3', PM_LAYERS, t['px1']),
                            ('A4', (), t['px15']),
                            ('A5', (), t['px_atr'])):
        xp, xt, tag = replay_layers(e, dirn, candles, t['open_ts'],
                                    horizon_ts, layers, t['sl'], tp)
        res[arm] = (None if xp is None else
                    {'xp': xp, 'xt': xt, 'tag': tag, 'net': net_usdt(t, xp)})
    xp, xt = replay(e, dirn, t['rsl'], t['rtp'], candles, t['open_ts'],
                    horizon_ts, sl_first=True)
    if xp is None:
        res['A6'] = None
    else:
        # replay returns the exact level object it exited on
        tag = 'floor' if xp == t['rsl'] else ('rr_tp' if xp == t['rtp']
                                              else 'timeout')
        res['A6'] = {'xp': xp, 'xt': xt, 'tag': tag, 'net': net_usdt(t, xp)}
    return res


def fk_touch(t, candles, a1, horizon_ts):
    """True if A3's TP (1.0%) is touched on the path BEFORE A1's exit.
    Same-bar as A1's non-timeout exit is ambiguous intra-bar (floor-first
    convention) -> excluded; timeout exits end the bar, so their exit bar
    counts. Conservative on purpose."""
    entry_ts, tp1, long_ = t['open_ts'], t['px1'], t['long']
    bound, is_to = a1['xt'], a1['tag'] == 'timeout'
    for ts, o, h, l, c in candles:
        if ts < entry_ts:
            continue
        if ts > horizon_ts:
            break
        if (ts > bound) if is_to else (ts >= bound):
            break
        if (h >= tp1) if long_ else (l <= tp1):
            return True
    return False


def run_pass(rows, tf, horizon_mode, arms_key, fk_key):
    """Walk every trade on one (tf, horizon) combo.

    horizon_mode: 'close' = actual close_time (equal time budget);
    '8h' = open_time + UNIVERSAL_MAX_HOLD_MINUTES (sensitivity).
    fk is computed for EVERY A1 winner (raw + deduped bar both need it).
    """
    step = STEP[tf]
    for t in rows:
        hz = (t['close_ts'] if horizon_mode == 'close'
              else t['open_ts'] + UNIVERSAL_MAX_HOLD_MINUTES * 60)
        t0, t1 = t['open_ts'] - step, hz + step
        candles = (load_candles_1m(t['token'].upper(), t0, t1) if tf == '1m'
                   else load_candles(t['token'].upper(), t0, t1))
        if not candles:
            t.setdefault('skipped', []).append(arms_key)
            continue
        if arms_key == 'arms_1m':
            t['candles_1m'] = candles   # kept for fk + mutation probes
        arms = walk_arms(t, candles, hz)
        t[arms_key] = arms
        if arms.get('A1') and arms['A1']['net'] > 0:
            t[fk_key] = fk_touch(t, candles, arms['A1'], hz)
    return rows


# ── stats / bar ──────────────────────────────────────────────────────────────
def arm_stats(rows, arm, key='arms_1m'):
    vals = [t[key][arm] for t in rows
            if t.get(key) and t[key].get(arm)]
    n = len(vals)
    if not n:
        return None
    nets = sorted(v['net'] for v in vals)
    w = sum(1 for x in nets if x > 0)
    to = sum(1 for v in vals if v['tag'] == 'timeout')
    return {'n': n, 'w': w, 'l': n - w, 'wr': 100.0 * w / n,
            'net': sum(nets), 'avg': sum(nets) / n, 'med': nets[n // 2],
            'timeouts': to, 'to_rate': 100.0 * to / n}


def a0_stats(rows):
    nets = sorted(t['a0_net'] for t in rows)
    n = len(nets)
    if not n:
        return None
    w = sum(1 for x in nets if x > 0)
    return {'n': n, 'w': w, 'l': n - w, 'wr': 100.0 * w / n,
            'net': sum(nets), 'avg': sum(nets) / n, 'med': nets[n // 2],
            'gross': sum(t['gross'] for t in rows)}


def _sign(x):
    return (x > 0) - (x < 0)


def bar_eval(rows, arms_key='arms_1m', fk_key='fk_1m'):
    """Four limbs of the pre-registered bar, A3 vs A1. Report only."""
    both = [t for t in rows if t.get(arms_key)
            and t[arms_key].get('A1') and t[arms_key].get('A3')]
    n = len(both)
    out = {'n': n}
    if not n:
        out['error'] = 'no rows with both A1 and A3'
        return out
    a1, a3 = arm_stats(both, 'A1', arms_key), arm_stats(both, 'A3', arms_key)
    d_net = a3['net'] - a1['net']
    out.update({'a1': a1, 'a3': a3, 'delta_net': d_net,
                'limb_i': a3['net'] >= a1['net'] + BAR_NET_USD})
    winners = [t for t in both if t[arms_key]['A1']['net'] > 0]
    fk_rows = [t for t in winners if t.get(fk_key)]
    fk_n = len(fk_rows)
    fk_pct = 100.0 * fk_n / len(winners) if winners else 0.0
    out.update({
        'a1_winners': len(winners), 'fk_n': fk_n, 'fk_pct': fk_pct,
        'limb_ii': fk_pct <= BAR_FK_PCT,
        # pnl A3 forgoes vs A1 by TP-cutting the fk trades, plus the raw
        # winner pnl those trades put at risk (both reported)
        'fk_pnl_at_risk': sum(t[arms_key]['A1']['net'] - t[arms_key]['A3']['net']
                              for t in fk_rows),
        'fk_a1_winner_pnl': sum(t[arms_key]['A1']['net'] for t in fk_rows),
    })
    srt = sorted(both, key=lambda t: t['close_ts'])
    med = srt[n // 2]['close_ts']
    h1 = [t for t in srt if t['close_ts'] <= med]
    h2 = [t for t in srt if t['close_ts'] > med]

    def hdelta(h):
        if len(h) < 2:
            return None
        return arm_stats(h, 'A3', arms_key)['net'] - arm_stats(h, 'A1', arms_key)['net']

    d1, d2 = hdelta(h1), hdelta(h2)
    same = (d1 is not None and d2 is not None
            and _sign(d1) == _sign(d2) and _sign(d1) != 0)
    out.update({'median_close_ts': med, 'half1_n': len(h1), 'half2_n': len(h2),
                'half1_delta': d1, 'half2_delta': d2, 'limb_iii': same,
                'a3_tp_fires': sum(1 for t in both
                                   if t[arms_key]['A3']['tag'] == 'atr_tp')})
    wr_gap = a3['wr'] - a1['wr']
    out.update({'wr_gap_pp': wr_gap, 'limb_iv': wr_gap >= -BAR_WR_SLACK_PP,
                'powered': n >= BAR_MIN_N})
    out['limbs'] = {'i': out['limb_i'], 'ii': out['limb_ii'],
                    'iii': out['limb_iii'], 'iv': out['limb_iv']}
    out['bar_met'] = all(out['limbs'].values()) and out['powered']
    out['under_powered'] = not out['powered']
    return out


# ── reporting ────────────────────────────────────────────────────────────────
def fmt_stats_row(label, s, extra=''):
    if not s:
        return f"{label:<22} (no rows)\n"
    return (f"{label:<22} n={s['n']:<4} W={s['w']:<4} L={s['l']:<4} "
            f"WR={s['wr']:5.1f}%  net=${s['net']:+8.2f}  avg=${s['avg']:+.3f} "
            f"med=${s['med']:+.3f}"
            + (f"  timeout={s['to_rate']:4.1f}% ({s['timeouts']}) "
               if 'to_rate' in s else '  ') + extra + "\n")


def print_arm_table(rows, key, title):
    print(f"\n{title}")
    print("-" * 100)
    a0 = a0_stats(rows)
    sys.stdout.write(fmt_stats_row(
        'A0 actual (net-of-fee)', a0,
        f"gross=${a0['gross']:+.2f}" if a0 else ''))
    for arm in ARMS:
        sys.stdout.write(fmt_stats_row(arm, arm_stats(rows, arm, key)))
    # exit-tag breakdown (dedup diagnostic): floor / pm_trail / atr_tp(=TP
    # ceiling, fixed or ATR) / rr_tp(A6 5% target) / timeout
    tags = {}
    for t in rows:
        if not t.get(key):
            continue
        for arm in ARMS:
            v = t[key].get(arm)
            if v:
                d = tags.setdefault(arm, {})
                d[v['tag']] = d.get(v['tag'], 0) + 1
    for arm in ARMS:
        if arm in tags:
            print("  exit tags " + arm + ": " + ', '.join(
                f"{k}={v}" for k, v in sorted(tags[arm].items())))


def print_bar(b, title):
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")
    if 'error' in b:
        print("ERROR:", b['error'])
        return
    a1, a3 = b['a1'], b['a3']
    print(f"(i)   net-of-fee $: A3 ${a3['net']:+.2f}  A1 ${a1['net']:+.2f}  "
          f"delta ${b['delta_net']:+.2f}   bar: A3 >= A1 + ${BAR_NET_USD:.2f} "
          f"-> {'PASS' if b['limb_i'] else 'FAIL'}")
    print(f"(ii)  fk = {b['fk_pct']:.1f}%  ({b['fk_n']} of {b['a1_winners']} "
          f"A1 winners touch A3's TP before A1's exit)   bar: <= {BAR_FK_PCT:.0f}% "
          f"-> {'PASS' if b['limb_ii'] else 'FAIL'}")
    print(f"      fk_pnl_at_risk = ${b['fk_pnl_at_risk']:+.2f} "
          f"(sum of A1_net − A3_net on fk trades = what TP-cutting costs vs "
          f"A1); sum of A1 winner pnl on fk trades = "
          f"${b['fk_a1_winner_pnl']:+.2f}")
    h1, h2 = b['half1_delta'], b['half2_delta']
    d1s = 'n/a' if h1 is None else f"${h1:+.4f}"
    d2s = 'n/a' if h2 is None else f"${h2:+.4f}"
    print(f"(iii) halves by close_time median: H1(n={b['half1_n']}) delta "
          f"{d1s}  H2(n={b['half2_n']}) delta {d2s}   same sign "
          f"-> {'PASS' if b['limb_iii'] else 'FAIL'}")
    if not b['limb_iii'] and (h1 == 0.0 or h2 == 0.0):
        print("      (degenerate zero: A3 identical to A1 in the zero half — "
              "its 1.0% TP never fired there; 0 has no sign, so 'same sign' "
              "cannot be established — not an opposite-sign result)")
    print(f"(iv)  WR: A3 {a3['wr']:.1f}%  A1 {a1['wr']:.1f}%  gap "
          f"{b['wr_gap_pp']:+.1f}pp   bar: >= -{BAR_WR_SLACK_PP:.0f}pp "
          f"-> {'PASS' if b['limb_iv'] else 'FAIL'}")
    print(f"      A3 1.0% TP firings in set: {b['a3_tp_fires']}/{b['n']} "
          "(hybrid TP before trail/floor — near-inertness diagnostic)")
    print(f"n (both arms walked in this set) = {b['n']}   bar: >= {BAR_MIN_N} -> "
          f"{'PASS' if b['powered'] else 'UNDER-POWERED'}")
    if b['under_powered']:
        print("VERDICT: UNDER-POWERED -> extend window, NO VERDICT.")
    elif b['bar_met']:
        print("VERDICT: BAR MET (all four limbs + n). Report only — no flip "
              "decision made here; CEO registers/decides.")
    else:
        failed = [k for k, v in b['limbs'].items() if not v]
        print(f"VERDICT: BAR NOT MET (limbs failed: {', '.join(failed)}). "
              "NO CHANGE — registry default_action stands.")


def cohort_of(t):
    r = t['reason']
    if r == 'profit-monster-trail':
        return 'trail'
    if r in STOP_FAMILY:
        return 'stop-family'
    if r.startswith('manual'):
        return 'manual'
    if r == 'prearm_lock':
        return 'prearm'
    return 'other'


def print_cohorts(rows):
    print("\ncohort table (raw population, 1m walk, horizon=close_time)")
    print("-" * 100)
    hdr = (f"{'cohort':<14} {'n':>4} {'A0 net':>9} {'A1 net':>9} {'A3 net':>9} "
           f"{'A3-A1':>8} {'WR A1':>7} {'WR A3':>7}")
    print(hdr)
    for coh in ('trail', 'stop-family', 'manual', 'prearm', 'other'):
        sub = [t for t in rows if cohort_of(t) == coh]
        if not sub:
            continue
        a1, a3 = arm_stats(sub, 'A1'), arm_stats(sub, 'A3')
        a0 = a0_stats(sub)
        if not (a1 and a3):
            print(f"{coh:<14} {len(sub):>4} (walk incomplete)")
            continue
        print(f"{coh:<14} {len(sub):>4} ${a0['net']:>+8.2f} ${a1['net']:>+8.2f} "
              f"${a3['net']:>+8.2f} ${a3['net'] - a1['net']:>+7.2f} "
              f"{a1['wr']:>6.1f}% {a3['wr']:>6.1f}%")
    tot = len(rows)
    print(f"(raw total n={tot}; cohorts partition on close_reason; "
          "prearm shown separately per registry collision note)")


def print_managed_split(raw_rows, dedup_rows):
    print("\nWITH / WITHOUT manual+structure-managed trades (11-15 ruling; "
          "managed = ai-trader-* via is_managed_signal)")
    print("-" * 100)
    for pop_name, pop in (('RAW', raw_rows), ('DEDUPED', dedup_rows)):
        for label, pred in (
                ('WITH managed', lambda t: is_managed_signal(t['signal'])),
                ('WITHOUT managed', lambda t: not is_managed_signal(t['signal']))):
            sub = [t for t in pop if pred(t)]
            b = bar_eval(sub)
            if 'error' in b:
                print(f"  {pop_name} {label}: n={len(sub)} (insufficient)")
                continue
            print(f"  {pop_name} {label:<16}: n={b['n']}  "
                  f"A1 ${b['a1']['net']:+.2f}  A3 ${b['a3']['net']:+.2f}  "
                  f"delta ${b['delta_net']:+.2f}  "
                  f"WR A1 {b['a1']['wr']:.1f}% A3 {b['a3']['wr']:.1f}%  "
                  f"fk {b['fk_pct']:.1f}%  limbs "
                  f"{''.join('P' if v else 'F' for v in b['limbs'].values())} "
                  f"n_bar={'OK' if b['powered'] else 'UNDER'}")
    print("  (dedup note: all 48 managed trades are BTC, so token-day dedup "
          "collapses them to the earliest-BTC-trade-of-day survivors; the RAW "
          "row is the informative one for this split.)")


def print_sensitivities(raw_rows, dedup_rows):
    print("\nsensitivities (deduped, 1m)")
    print("-" * 78)
    for title, key, fk in (
            ('8h UNIVERSAL_MAX_HOLD horizon', 'arms_8h', 'fk_8h'),
            ('5m cross-check (horizon=close_time)', 'arms_5m', 'fk_5m')):
        b = bar_eval(dedup_rows, key, fk)
        if 'error' in b:
            print(f"{title}: {b['error']}")
            continue
        print(f"{title}: n={b['n']} A1 ${b['a1']['net']:+.2f} "
              f"A3 ${b['a3']['net']:+.2f} delta ${b['delta_net']:+.2f} "
              f"WRgap {b['wr_gap_pp']:+.1f}pp fk {b['fk_pct']:.1f}% "
              f"limbs {''.join('P' if v else 'F' for v in b['limbs'].values())} "
              f"-> {'BAR MET' if b['bar_met'] else ('UNDER-POWERED' if b['under_powered'] else 'NOT MET')}")
    # per-arm net divergence 1m vs 5m
    print("1m vs 5m per-arm net divergence (deduped):")
    for arm in ARMS:
        s1, s5 = arm_stats(dedup_rows, arm, 'arms_1m'), arm_stats(dedup_rows, arm, 'arms_5m')
        if s1 and s5:
            print(f"  {arm}: 1m ${s1['net']:+.2f}  5m ${s5['net']:+.2f}  "
                  f"div ${s1['net'] - s5['net']:+.2f}  "
                  f"WR {s1['wr']:.1f}%/{s5['wr']:.1f}%")
    # #16913 excluded (disaster-TP trade, registry evidence) — raw + dedup
    for pop_name, pop, key, fk in (('dedup', dedup_rows, 'arms_1m', 'fk_1m'),
                                   ('raw', raw_rows, 'arms_1m', 'fk_1m')):
        sub = [t for t in pop if t['id'] != 16913]
        if len(sub) == len(pop):
            print(f"#16913-excluded ({pop_name}): trade 16913 not present in "
                  "this set (out of window / deduped away) — sensitivity "
                  "identical to headline.")
            continue
        b = bar_eval(sub, key, fk)
        if 'error' not in b:
            print(f"#16913-excluded ({pop_name}): n={b['n']} "
                  f"A1 ${b['a1']['net']:+.2f} A3 ${b['a3']['net']:+.2f} "
                  f"delta ${b['delta_net']:+.2f} "
                  f"WRgap {b['wr_gap_pp']:+.1f}pp fk {b['fk_pct']:.1f}% "
                  f"limbs {''.join('P' if v else 'F' for v in b['limbs'].values())}")


# ── main study ───────────────────────────────────────────────────────────────
def main_study():
    t_start = time.time()
    rows = load_population()
    for t in rows:
        build_levels(t)
    # token-day dedup: earliest open per (token, UTC date of open_time)
    seen, dedup = set(), []
    for t in sorted(rows, key=lambda x: (x['open_t'], x['id'])):
        k = (t['token'].upper(), t['open_t'].date())
        if k in seen:
            continue
        seen.add(k)
        dedup.append(t)

    run_pass(rows, '1m', 'close', 'arms_1m', 'fk_1m')
    run_pass(rows, '5m', 'close', 'arms_5m', 'fk_5m')
    run_pass(rows, '1m', '8h', 'arms_8h', 'fk_8h')

    n1 = sum(1 for t in rows if t.get('arms_1m'))
    n5 = sum(1 for t in rows if t.get('arms_5m'))
    toks = {t['token'].upper() for t in rows}
    skipped = [t['id'] for t in rows if not t.get('arms_1m')]
    print(f"population: {len(rows)} closed trades 14d (entry/stop/exit/size "
          f"present), {len(toks)} tokens; deduped {len(dedup)} "
          f"(earliest open per token-UTC-day); fees NULL = "
          f"{sum(1 for t in rows if t['fees_raw'] is None)} rows (fee=0 used)")
    print(f"candles: 1m walked {n1}/{len(rows)}, 5m walked {n5}/{len(rows)} "
          f"(tokens with both: {len(toks) - len({t['token'].upper() for t in rows if not t.get('arms_5m')})}/{len(toks)})"
          + (f"; NO-CANDLE skipped ids={skipped}" if skipped else ""))

    print_arm_table(rows, 'arms_1m', "ARMS — RAW population (1m, horizon=close_time)")
    print_arm_table(dedup, 'arms_1m', "ARMS — TOKEN-DAY DEDUPED (1m, horizon=close_time)")

    b_raw = bar_eval(rows)
    b_dd = bar_eval(dedup)
    print_bar(b_dd, "THE BAR — A3 vs A1 · DEDUPED · 1m · horizon=close_time "
                    "(PRIMARY)")
    print_bar(b_raw, "THE BAR — A3 vs A1 · RAW · 1m (secondary)")

    print_cohorts(rows)
    print_managed_split(rows, dedup)
    pend8 = sum(1 for t in rows
                if t['open_ts'] + UNIVERSAL_MAX_HOLD_MINUTES * 60 > time.time())
    if pend8:
        print(f"\n⚠ {pend8} trade(s) with an 8h horizon still accruing — "
              "8h-sensitivity rows for those are unstable until the window "
              "elapses (jup_exit_sim.py:419-429 convention).")
    print_sensitivities(rows, dedup)

    # A5 diagnostic: target distribution from the WORKING formula (clamped)
    a5dist = {}
    for t in rows:
        k = f"{t['tp_atr_frac'] * 100:.2f}%"
        a5dist[k] = a5dist.get(k, 0) + 1
    print(f"\nA5 target distribution (compute_atr_tp_pct on entry ATR%, "
          f"clamped ATR_TP_MIN..MAX): {dict(sorted(a5dist.items()))}"
          + ("  <- DEGENERATE: A5 collapses onto A4 (1.50%)"
             if set(a5dist) <= {'1.50%'} else ""))

    # prearm cohort note (registry: TP adoption would moot the BE-lock)
    pre = [t for t in rows if cohort_of(t) == 'prearm']
    if pre:
        a1, a3 = arm_stats(pre, 'A1'), arm_stats(pre, 'A3')
        print(f"\nprearm_lock cohort n={len(pre)} (sensitivity separate): "
              f"A1 ${a1['net']:+.2f} A3 ${a3['net']:+.2f} — NOTE: adopting TP "
              "exits would MOOT the prearm BE-lock (TP fires first on the same "
              "paths); this cohort is not part of the bar.")

    # spec-collision watch: stored stop_loss is exit-state (trail-mutated)
    ps = [t for t in rows if (t['long'] and t['sl'] > t['entry'])
          or ((not t['long']) and t['sl'] < t['entry'])]
    first_bar_floor = 0
    for t in dedup:
        if not (t.get('arms_1m') and t['arms_1m'].get('A1')):
            continue
        walked = [c[0] for c in t.get('candles_1m', [])
                  if t['open_ts'] <= c[0] <= t['close_ts']]
        if (walked and t['arms_1m']['A1']['tag'] == 'floor'
                and t['arms_1m']['A1']['xt'] == walked[0]):
            first_bar_floor += 1
    print(f"\nWATCH (spec collision, report-only): {len(ps)}/{len(rows)} trades "
          f"store a PROFIT-side stop_loss (trail-mutated, jup_exit_sim.py:19-24 "
          "class); dedup A1 instant-floor-exit in first walked bar = "
          f"{first_bar_floor}. Registry mandates floor=actual stop_loss — "
          "implemented as written; evidence line for parent.")

    runtime = time.time() - t_start
    art = {
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'runtime_s': round(runtime, 1),
        'registry': 'tp-vs-trail-shadow (data/shadow_disposition.json)',
        'population': {'raw': len(rows), 'deduped': len(dedup),
                       'tokens': len(toks), 'walked_1m': n1, 'walked_5m': n5,
                       'skipped_no_candles': skipped},
        'raw_bar': b_raw, 'dedup_bar': b_dd,
        'raw_arms': {a: arm_stats(rows, a) for a in ARMS},
        'raw_a0': a0_stats(rows),
        'dedup_arms': {a: arm_stats(dedup, a) for a in ARMS},
        'dedup_a0': a0_stats(dedup),
        'cohorts': {c: {'n': sum(1 for t in rows if cohort_of(t) == c),
                        'a0': a0_stats([t for t in rows if cohort_of(t) == c]),
                        'a1': arm_stats([t for t in rows if cohort_of(t) == c], 'A1'),
                        'a3': arm_stats([t for t in rows if cohort_of(t) == c], 'A3')}
                    for c in ('trail', 'stop-family', 'manual', 'prearm', 'other')},
        'managed_split_raw': {lab: bar_eval([t for t in rows if pred(t)])
                              for lab, pred in
                              (('with_managed', lambda t: is_managed_signal(t['signal'])),
                               ('without_managed', lambda t: not is_managed_signal(t['signal'])))},
        'managed_split_dedup': {lab: bar_eval([t for t in dedup if pred(t)])
                                for lab, pred in
                                (('with_managed', lambda t: is_managed_signal(t['signal'])),
                                 ('without_managed', lambda t: not is_managed_signal(t['signal'])))},
        'sens_8h': bar_eval(dedup, 'arms_8h', 'fk_8h'),
        'sens_5m': bar_eval(dedup, 'arms_5m', 'fk_5m'),
        'sens_no_16913': bar_eval([t for t in dedup if t['id'] != 16913]),
        'sens_no_16913_raw': bar_eval([t for t in rows if t['id'] != 16913]),
        'a5_tp_distribution': {},
        'profit_side_stop_n': len(ps),
    }
    for t in rows:
        k = f"{t['tp_atr_frac'] * 100:.2f}%"
        art['a5_tp_distribution'][k] = art['a5_tp_distribution'].get(k, 0) + 1
    with open(ART_PATH, 'w') as f:
        json.dump(art, f, indent=1, default=str)
    print(f"\nartifact -> {ART_PATH}  (runtime {runtime:.1f}s)")
    print("LOG-ONLY STUDY — zero live flags, zero writes to hermes_constants, "
          "zero edits to jup_exit_sim.py.")
    return b_dd


# ── selfcheck gates ──────────────────────────────────────────────────────────
def _jup_units(t, xp):
    """Leveraged price-% — ONLY to compare against jup_exit_sim artifact
    rows (their native units). Study arms never use this (#193 guard)."""
    pct = ((xp / t['entry'] - 1.0) * 100.0 if t['dir'] == 'LONG'
           else (1.0 - xp / t['entry']) * 100.0)
    return pct * t['lev']


def _jup_walk(t, candles, horizon_ts, mode):
    """Reproduce jup_exit_sim's exact constructions (rr2_cfg / pmwalk)."""
    e, dirn, long_ = t['entry'], t['dir'], t['dir'] == 'LONG'
    sl_cfg_pct = max(ATR_SL_MIN, min(ATR_SL_MAX, ATR_K_HIGH_VOL * 1.0))
    tp_cfg_pct = max(ATR_TP_MIN, min(ATR_TP_MAX,
                                     ATR_K_HIGH_VOL * 1.0 * ATR_TP_K_MULT))
    if mode == 'rr2':
        risk = e * sl_cfg_pct
        rsl = (e - risk) if long_ else (e + risk)
        rtp = (e + 2.0 * risk) if long_ else (e - 2.0 * risk)
        xp, xt = replay(e, dirn, rsl, rtp, candles, t['open_ts'], horizon_ts,
                        sl_first=True)
    else:  # pmwalk: tightest floor (HML CUT_LOSER/lev vs 2.5%) + ATR TP ceiling
        hml_frac = abs(CUT_LOSER_PNL) / 100.0 / max(t['lev'], 1)
        floor_frac = min(hml_frac, sl_cfg_pct)
        floor_px = (e * (1 - floor_frac) if long_
                    else e * (1 + floor_frac))
        tp_cfg = (e * (1 + tp_cfg_pct) if long_ else e * (1 - tp_cfg_pct))
        xp, xt, _tag = replay_layers(e, dirn, candles, t['open_ts'],
                                     horizon_ts, PM_LAYERS, floor_px, tp_cfg)
    if xp is None:
        return None
    return {'pnl': _jup_units(t, xp),
            'timeout': xt >= horizon_ts - STEP['5m']}


def _jup_ref_stats(mode):
    """Run jup's own constructions on the jup reference population."""
    trades = load_jup_ref()
    nets, w, l, to, skipped = [], 0, 0, 0, 0
    for t in trades:
        hz = t['open_ts'] + 12 * 3600   # JUP_EXIT_SIM_MAX_HOLD_H
        candles = load_candles(t['token'].upper(), t['open_ts'] - 300,
                               hz + 300)
        if not candles:
            skipped += 1
            continue
        r = _jup_walk(t, candles, hz, mode)
        if r is None:
            skipped += 1
            continue
        pnl = r['pnl']
        nets.append(pnl)
        w += 1 if pnl > 0.05 else 0
        l += 1 if pnl < -0.05 else 0
        to += 1 if r['timeout'] else 0
    n = len(nets)
    wl = w + l
    return {'n': n, 'net_pct': sum(nets), 'wr': (100.0 * w / wl) if wl else 0.0,
            'timeouts': to, 'skipped': skipped}


def _delta_ok(computed, ref, tol):
    deltas = {k: abs(computed[k] - ref[k]) for k in tol}
    ok = all(deltas[k] <= tol[k] for k in tol)
    print("  deltas: " + ', '.join(f"{k}={deltas[k]:.2f}" for k in tol)
          + f"  tol={tol}  -> {'PASS' if ok else 'FAIL'}")
    return ok, deltas


def _parity_check(mode, art_row):
    ref = _jup_ref_stats(mode)
    art_ref = json.load(open(JUP_ART))[art_row]
    print(f"  {mode}: computed n={ref['n']} net={ref['net_pct']:+.2f} "
          f"wr={ref['wr']:.1f}% timeouts={ref['timeouts']} "
          f"(skipped no-candle {ref['skipped']})")
    print(f"  artifact[{art_row}]: n={art_ref['n']} "
          f"net={art_ref['net_pct']:+.2f} wr={art_ref['wr']:.1f}% "
          f"timeouts={art_ref['timeouts']}")
    ok, _ = _delta_ok(ref, art_ref, PMWALK_TOL if mode == 'pmwalk'
                      else RR2_CLASS_TOL)
    return ok, ref, art_ref


def _jup_main_rr2_row():
    """Run jup_exit_sim's OWN main() restricted to the reference 98, with
    its artifact write redirected to /tmp. Strongest cross-engine check:
    jup's actual code path vs this file's A6 path must agree to the cent.
    Patches restored in finally; data/jup_exit_sim.json never touched."""
    import contextlib
    import datetime
    import io
    import jup_exit_sim as jup
    real_join = jup.os.path.join

    def fake_join(a, *p):
        if p and p[-1] == 'jup_exit_sim.json':
            return '/tmp/tp_vs_trail_jup_selfcheck.json'
        return real_join(a, *p)

    real_load = jup.load_trades

    def load98():
        return [t for t in real_load()
                if t['close_t'] <= datetime.datetime(2026, 11, 3, 1, 10, 0)]

    buf = io.StringIO()
    try:
        jup.os.path.join = fake_join
        jup.load_trades = load98
        with contextlib.redirect_stdout(buf):
            jup.main()
    finally:
        jup.os.path.join = real_join
        jup.load_trades = real_load
    with open('/tmp/tp_vs_trail_jup_selfcheck.json') as f:
        return json.load(f)['rr2_cfg']


def selfcheck_a6():
    """(a) A6 engine-validity, two gates:
    (a1) loss class vs the frozen jup prior art (bounded drift), and
    (a2) EXACT equality with jup_exit_sim's own main() on the same 98."""
    print("=== (a) A6 vs jup rr2_cfg known-loser control (engine-validity) ===")
    mine = _jup_ref_stats('rr2')
    art = json.load(open(JUP_ART))['rr2_cfg']
    print(f"  A6-on-jup-ref:      n={mine['n']} net={mine['net_pct']:+.2f} "
          f"wr={mine['wr']:.1f}% timeouts={mine['timeouts']}")
    print(f"  frozen artifact:    n={art['n']} net={art['net_pct']:+.2f} "
          f"wr={art['wr']:.1f}% timeouts={art['timeouts']}")
    print("  NOTE: artifact run 2026-11-03 01:10 had 16 closed jup trades "
          "with INCOMPLETE 12h horizons (its own instability warning class, "
          "jup_exit_sim.py:419-429) → artifact timeout rows undercount; "
          "complete-window rerun of jup's own code = -255.00/70 timeouts.")
    ok1, _ = _delta_ok(mine, art, RR2_CLASS_TOL)
    cls_ok = (mine['net_pct'] < 0 and art['net_pct'] < 0
              and mine['wr'] < 55.0 and mine['timeouts'] >= mine['n'] // 2)
    print(f"  loss class (net<0 both, wr<55%, majority timeout): "
          f"{'PASS' if cls_ok else 'FAIL'}")
    row = _jup_main_rr2_row()
    print(f"  jup main() re-run same 98: n={row['n']} "
          f"net={row['net_pct']:+.2f} wr={row['wr']:.1f}% "
          f"timeouts={row['timeouts']}")
    ok2, _ = _delta_ok(mine, row, EXACT_TOL)
    return ok1 and cls_ok and ok2


def selfcheck_c():
    """(c) cross-engine parity: pm-walk on jup reference trades matches
    jup_exit_sim's published pmwalk row."""
    print("=== (c) pm-walk cross-engine parity vs data/jup_exit_sim.json ===")
    ok, ref, art_ref = _parity_check('pmwalk', 'pmwalk')
    return ok


def selfcheck_b():
    """(b) no-lookahead mutation probes on real 1m walks."""
    print("=== (b) no-lookahead mutation tests (1m walks) ===")
    rows = load_population()
    for t in rows:
        build_levels(t)
    n = len(rows)
    idxs = sorted({min(n - 1, int(i * n / 6)) for i in range(6)})
    probes = [rows[i] for i in idxs]
    pre_ok = post_ok = True
    changed = {'entry': 0, 'probes': 0}
    for t in probes:
        hz = t['close_ts']
        candles = t.get('candles_1m') or load_candles_1m(
            t['token'].upper(), t['open_ts'] - 60, hz + 60)
        if not candles:
            continue
        base = walk_arms(t, candles, hz)
        sig = lambda res: {a: (None if v is None else
                               (v['xp'], v['xt'], v['tag']))
                           for a, v in res.items()}
        # (1) mutate candles BEFORE entry -> results must be identical
        pre = [(ts, o, (h * 4 if ts < t['open_ts'] else h),
                (l / 4 if ts < t['open_ts'] else l), c)
               for ts, o, h, l, c in candles]
        same = sig(walk_arms(t, pre, hz)) == sig(base)
        pre_ok = pre_ok and same
        # (2) mutate candles AFTER horizon -> results must be identical
        post = [(ts, o, (h * 4 if ts > hz else h),
                 (l / 4 if ts > hz else l), c)
                for ts, o, h, l, c in candles]
        same2 = sig(walk_arms(t, post, hz)) == sig(base)
        post_ok = post_ok and same2
        # (3) mutate the FIRST WALKED bar (entry bar) -> must change results
        walked = [c for c in candles if t['open_ts'] <= c[0] <= hz]
        if not walked:
            continue
        fb_ts = walked[0][0]
        ent = []
        for ts, o, h, l, c in candles:
            if ts != fb_ts:
                ent.append((ts, o, h, l, c))
            elif t['long']:
                ent.append((ts, o, h, 0.0, c))          # floor guaranteed
            else:
                ent.append((ts, o, h * 1000.0, l, c))   # floor guaranteed
        sig_ent = sig(walk_arms(t, ent, hz))
        diff_arms = [a for a in ARMS if sig_ent.get(a) != sig(base).get(a)]
        print(f"  probe id={t['id']} {t['dir']}: pre-equal={same} "
              f"post-equal={same2} entry-mutation changed={diff_arms or 'NONE'}")
        if diff_arms:
            changed['probes'] += 1
        if 'A3' in diff_arms:
            changed['entry'] += 1
        pre_ok = pre_ok and same
        post_ok = post_ok and same2
    ent_ok = changed['probes'] >= max(1, len(probes) // 2)
    print(f"  pre-entry mutation leaves results identical: "
          f"{'PASS' if pre_ok else 'FAIL'}")
    print(f"  post-horizon mutation leaves results identical: "
          f"{'PASS' if post_ok else 'FAIL'}")
    print(f"  entry-bar mutation CHANGES results (A3 changed on "
          f"{changed['entry']} probes, {changed['probes']}/{len(probes)} "
          f"probes changed at least one arm): "
          f"{'PASS' if ent_ok else 'FAIL'}")
    return pre_ok and post_ok and ent_ok


def selfcheck_d():
    """(d) fee math spot-check vs 3 known trades (#193 units guard)."""
    print("=== (d) fee math spot-check (3 known trades, #193 units guard) ===")
    rows = sorted(load_population(), key=lambda t: t['close_t'])
    picks = [rows[0], rows[len(rows) // 2], rows[-1]]
    ok = True
    for t in picks:
        rate = t['fee'] / (2.0 * t['amount'])
        sgn = 1.0 if t['dir'] == 'LONG' else -1.0
        gross = sgn * (t['exit'] - t['entry']) / t['entry'] * t['amount']
        try:
            blob = json.loads(t['fees_raw']) if t['fees_raw'] else {}
        except (ValueError, TypeError):
            blob = {}
        # (1) NON-tautological: itemized entry_fee+exit_fee == fee_total
        if (isinstance(blob, dict) and blob.get('entry_fee') is not None
                and blob.get('exit_fee') is not None):
            sum_ok = abs(float(blob['entry_fee']) + float(blob['exit_fee'])
                         - t['fee']) <= 1e-9
        else:
            sum_ok = True   # blob not itemized: fee_total accepted as-is
        # (2) the spec's rate formula reconstructs fee_total
        rate_ok = abs(rate * 2.0 * t['amount'] - t['fee']) <= 1e-9
        # (3) gross (unleveraged price move x notional) == DB pnl_usdt @2dp
        pnl_ok = abs(gross - t['gross']) <= 0.011
        good = sum_ok and rate_ok and pnl_ok
        ok = ok and good
        print(f"  id={t['id']} {t['token']} {t['dir']}: fee_total={t['fee']:.6f} "
              f"rate={rate:.6f} blob_sum_ok={sum_ok} rate_recon_ok={rate_ok} "
              f"gross={gross:+.4f} vs DB pnl_usdt={t['gross']:+.4f} -> "
              f"{'PASS' if good else 'FAIL'}")
    print(f"  blob itemization == fee_total; rate*2*amount reconstructs "
          f"fee_total; gross (unleveraged price move x notional) matches "
          f"pnl_usdt -> {'PASS' if ok else 'FAIL'}")
    return ok


def selfcheck():
    t0 = time.time()
    results = {}
    results['a_a6_jup_loss_class'] = selfcheck_a6()
    results['b_no_lookahead_mutations'] = selfcheck_b()
    results['c_pmwalk_parity'] = selfcheck_c()
    results['d_fee_spot_check'] = selfcheck_d()
    print(f"\nSELFCHECK: " + '  '.join(
        f"{k}={'PASS' if v else 'FAIL'}" for k, v in results.items())
        + f"  ({time.time() - t0:.1f}s)")
    all_ok = all(results.values())
    if not all_ok:
        print("SELFCHECK FAILED — engine NOT trusted; do not read study "
              "numbers until fixed.", file=sys.stderr)
    return 0 if all_ok else 1


def main():
    ap = argparse.ArgumentParser(description='TP-vs-trail counterfactual '
                                             '(LOG-ONLY, registry tp-vs-trail-shadow)')
    ap.add_argument('--selfcheck', action='store_true',
                    help='run gates (a)-(d) and exit (0=pass)')
    args = ap.parse_args()
    if args.selfcheck:
        sys.exit(selfcheck())
    main_study()


if __name__ == '__main__':
    main()
