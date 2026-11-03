#!/usr/bin/env python3
"""
JUP mirror exit simulator (T 2026-10-31).

Question: for closed jup_yolo_mirrored trades, which exit style suits pro
moves — pm-trail (current), R:R fixed TP, ATR SL/TP, or just riding longer?

Method: replay 5m OHLC candles from each trade's actual entry to a horizon
(JUP_EXIT_SIM_MAX_HOLD_H). Conservative intrabar rule: when SL and TP both
touch inside one candle, SL wins (pessimistic bound; optimistic = TP-first
would only improve atr/rr rows). Strategies:
  pm_actual   — what actually happened (DB close, every engine mixed)
  pm_trail    — actual closes where profit-monster-trail fired (pure trail)
  atr_cfg     — static SYSTEM ATR levels from entry (compute_atr_sl/tp_pct)
  rr2_cfg/3   — risk = ATR-config SL (2.5%), TP = entry ± R×risk
  rr2_hml/3   — risk = CUT_LOSER/lev (account cap), TP = entry ± R×risk
  ride        — no exit until horizon close (longer-hold reference)

v2 discarded the stored stop_loss/target columns: they are MUTATED by the
trail + ATR-managed updates after entry (trail-won #16553 has SL ABOVE
entry), so replaying them bakes exit-state into entry-state. v3 reconstructs
entry-time levels via the system's own tpsl_utils functions (verified
invariant: ATR>0.015% → SL 2.50% / TP 2.00% because tier thresholds are
fraction-unit vs percent-unit — that's how the system actually behaves).

v4 (T 2026-10-31): MFE-giveback exit variants (replay_layers walk). Peak-
tracking profit layer over static floors; compares the literal spec (30%
giveback from any positive MFE) vs the armed variant (same +0.40% arm as
PM trail), plus a pm-trail WALKER (pmwalk) validated against pm_actual so
the walker itself is trusted before reading mfe rows. Background stack for
every walker: tightest floor (HML CUT_LOSER/lev vs ATR SL) + ATR TP + 12h
timeout — identical across variants, so deltas isolate the profit layer.
Intra-bar order: static floor first (v3 pessimism), then profit layer
(first-touch price; pessimistic same-bar tie vs TP), peak updated last
(thresholds use prior-bar peak — standard trail-sim practice).
This is ANALYSIS ONLY — no live behavior changes; the shipped exit was
sim-checked first and is scoped by MFE_EXIT_SIGNALS.
"""
import json
import os
import sys

from collections import defaultdict

import psycopg2

from paths import *
from hermes_constants import (
    JUP_EXIT_SIM_MAX_HOLD_H, JUP_EXIT_SIM_RR, JUP_EXIT_SIM_TIMEFRAME,
    ATR_SL_MIN_INIT, CUT_LOSER_PNL,
    MFE_EXIT_GIVEBACK_PCT, MFE_EXIT_ARM_PCT,
    PM_TRAIL_ACTIVATE_PCT, PM_TRAIL_DISTANCE_PCT,
)
from tpsl_utils import (compute_atr_sl_pct, compute_atr_tp_pct,
                        compute_atr_sl_pct_norm, compute_atr_tp_pct_norm)
from hermes_constants import (ATR_SL_MIN, ATR_SL_MAX, ATR_TP_MIN, ATR_TP_MAX,
                             ATR_K_HIGH_VOL, ATR_TP_K_MULT)

if JUP_EXIT_SIM_TIMEFRAME != '5m':
    raise SystemExit('replay logic assumes 5m candles')
HORIZON_S = int(JUP_EXIT_SIM_MAX_HOLD_H * 3600)
SEC_5M = 300


def load_trades():
    from _secrets import BRAIN_DB_DICT
    cfg = BRAIN_DB_DICT.copy(); cfg.setdefault('port', 5432)
    conn = psycopg2.connect(**cfg); conn.autocommit = True
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, token, direction, entry_price, exit_price, pnl_pct,
                   open_time, close_time, stop_loss, target,
                   volatility_regime, close_reason, amount_usdt, leverage
            FROM trades
            WHERE signal LIKE '%%jup_yolo%%' AND status = 'closed'
              AND entry_price IS NOT NULL AND exit_price IS NOT NULL
            ORDER BY id
        """)
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()
    out = []
    for r in rows:
        out.append(dict(zip(
            ['id', 'token', 'dir', 'entry', 'exit', 'pnl_pct', 'open_t', 'close_t',
             'sl', 'tp', 'regime', 'reason', 'amount', 'lev'], r)))
    return out


def load_candles(token, t0, t1):
    """5m OHLC as parallel lists; empty if none."""
    import sqlite3
    import os
    db = os.path.join(HERMES_DATA, 'candles.db')
    conn = sqlite3.connect(db, timeout=5)
    try:
        cur = conn.execute(
            "SELECT ts, open, high, low, close FROM candles_5m "
            "WHERE token=? AND is_closed=1 AND ts>=? AND ts<? "
            # COMPLETE-BARS ONLY (auditor F-1, 2026-10-31): price_collector
            # writes the DEVELOPING 5m bar with is_closed=1 (legacy DEFAULT-1
            # semantics, price_collector.py L178/196), so is_closed alone lets
            # partial bars into timeout/ride rows and the table drifts between
            # runs. ts+300 <= now guarantees the window has fully elapsed.
            "AND ts + 300 <= strftime('%s','now') ORDER BY ts",
            (token, t0, t1))
        rows = cur.fetchall()
    finally:
        conn.close()
    return rows  # [(ts, o, h, l, c)]


def replay(entry, direction, sl, tp, candles, entry_ts, horizon_ts,
           sl_first=True):
    """Return (exit_price, exit_ts). sl_first=True = conservative bound
    (SL wins same-candle ties); sl_first=False = optimistic bound."""
    long_ = direction == 'LONG'
    for ts, o, h, l, c in candles:
        if ts < entry_ts:
            continue  # skip partial entry bar
        if ts > horizon_ts:
            break
        sl_hit = (l <= sl) if long_ else (h >= sl)
        tp_hit = (h >= tp) if long_ else (l <= tp)
        if sl_hit and tp_hit:
            return (sl, ts) if sl_first else (tp, ts)
        if sl_hit:
            return sl, ts
        if tp_hit:
            return tp, ts
    # timeout: last candle's close within horizon (or entry if none)
    last = [r for r in candles if entry_ts <= r[0] <= horizon_ts]
    if last:
        return last[-1][4], last[-1][0]
    return None, None


def replay_layers(entry, direction, candles, entry_ts, horizon_ts, layers,
                  floor_px, tp_px):
    """Walk candles with a peak-tracking profit layer over static floors.

    layers: list of (name, mode, arm_pct_price); mode 'mfe' → threshold_fav =
    peak_fav × (1 − MFE_EXIT_GIVEBACK_PCT), mode 'pm' → peak_fav − trail dist
    (arms at PM_TRAIL_ACTIVATE). Eligibility for 'mfe': peak_fav ≥ arm AND
    peak_fav > 0 (arm 0.0 = literal spec: any positive MFE). First touch wins:
    LONG exits at the HIGHEST eligible threshold (price falls through it
    first), SHORT at the LOWEST.

    Intra-bar order (documented, conservative): (1) static floor — pessimistic
    tie-break, same convention as replay(); (2) profit layer at first-touch
    price (gap-at-open → open price), pessimistic same-bar tie vs TP;
    (3) TP ceiling; peak updated LAST so thresholds use prior-bar peak.
    Returns (exit_price, exit_ts, tag) or (None, None, None).
    """
    long_ = direction == 'LONG'
    peak_fav = 0.0
    giveback = float(MFE_EXIT_GIVEBACK_PCT)
    pm_arm = float(PM_TRAIL_ACTIVATE_PCT) * 100.0   # 0.40% price
    pm_dist = float(PM_TRAIL_DISTANCE_PCT) * 100.0  # 0.20% price
    for ts, o, h, l, c in candles:
        if ts < entry_ts:
            continue
        if ts > horizon_ts:
            break
        # ── profit threshold from PRIOR-bar peak ──
        t_px, t_tag = None, None
        if peak_fav > 0:
            pick = None
            for name, mode, arm in layers:
                if mode == 'mfe':
                    if peak_fav < arm:
                        continue
                    tf = peak_fav * (1.0 - giveback)
                else:  # 'pm'
                    if peak_fav < pm_arm:
                        continue
                    tf = peak_fav - pm_dist
                if tf <= 0:
                    continue
                px = entry * (1 + tf / 100.0) if long_ else entry * (1 - tf / 100.0)
                if pick is None:
                    pick = (px, name)
                elif long_ and px > pick[0]:
                    pick = (px, name)
                elif (not long_) and px < pick[0]:
                    pick = (px, name)
            if pick:
                t_px, t_tag = pick
        # (1) static floor — pessimistic tie-break (v3 convention)
        if (l <= floor_px) if long_ else (h >= floor_px):
            return floor_px, ts, 'floor'
        # (2) profit layer: gap-at-open or first touch within the bar
        if t_px is not None:
            at_open = (o <= t_px) if long_ else (o >= t_px)
            touched = (l <= t_px) if long_ else (h >= t_px)
            if at_open or touched:
                xp = o if at_open else t_px
                tp_touched = (h >= tp_px) if long_ else (l <= tp_px)
                if tp_touched and ((tp_px < xp) if long_ else (tp_px > xp)):
                    return tp_px, ts, 'atr_tp'  # pessimistic tie: TP is worse
                return xp, ts, t_tag
        # (3) TP ceiling
        if (h >= tp_px) if long_ else (l <= tp_px):
            return tp_px, ts, 'atr_tp'
        # update peak AFTER exit checks
        fav = ((h / entry) - 1.0) * 100.0 if long_ else (1.0 - (l / entry)) * 100.0
        if fav > peak_fav:
            peak_fav = fav
    # timeout: last close within horizon
    last = [r for r in candles if entry_ts <= r[0] <= horizon_ts]
    if last:
        return last[-1][4], last[-1][0], 'timeout'
    return None, None, None


def price_pnl_pct(direction, entry, exit_px):
    if long_p(direction):
        return (exit_px / entry - 1.0) * 100.0
    return (1.0 - exit_px / entry) * 100.0


def long_p(d):
    return d == 'LONG'


def pct_time(open_t, close_t):
    if not open_t or not close_t:
        return 0.0
    return (close_t - open_t).total_seconds() / 3600.0


def main():
    trades = load_trades()
    print(f"closed mirror trades loaded: {len(trades)}")

    results = []   # per trade per strategy
    skipped = {'atr': [], 'rr': [], 'candles': []}
    # per-strategy accumulator
    stats = {k: {'n': 0, 'w': 0, 'l': 0, 'pnl': [], 'hold': [], 'timeout': 0}
             for k in ('pm_actual', 'pm_trail', 'atr_cfg', 'atr_norm',
                       'rr2_cfg', 'rr3_cfg', 'rr2_hml', 'rr3_hml', 'ride',
                       'bg', 'mfe30', 'mfe30a040', 'pmwalk',
                       'pm_mfe30', 'pm_mfe30a')}
    tags = defaultdict(lambda: defaultdict(int))  # walker strategy -> exit tag

    for t in trades:
        en, entry = t['id'], float(t['entry'])
        if not entry or entry <= 0:
            continue
        open_ts = int(t['open_t'].timestamp())
        horizon_ts = open_ts + HORIZON_S
        t0 = open_ts - SEC_5M
        t1 = horizon_ts + SEC_5M
        candles = load_candles(t['token'].upper(), t0, t1)
        if not candles:
            skipped['candles'].append(en)
            continue

        # ── pm_actual (baseline from DB)
        actual_pnl = float(t['pnl_pct'] or 0)
        actual_hold = pct_time(t['open_t'], t['close_t'])
        for key, pnl, hold, timed_out in (
            ('pm_actual', actual_pnl, actual_hold, False),
        ):
            s = stats[key]
            s['n'] += 1
            s['w'] += 1 if pnl > 0.05 else 0
            s['l'] += 1 if pnl < -0.05 else 0
            s['pnl'].append(pnl)
            s['hold'].append(hold)

        # ── pm_trail subset (actual closes by the trail engine)
        if (t['reason'] or '') == 'profit-monster-trail':
            s = stats['pm_trail']
            s['n'] += 1
            s['w'] += 1 if actual_pnl > 0.05 else 0
            s['l'] += 1 if actual_pnl < -0.05 else 0
            s['pnl'].append(actual_pnl)
            s['hold'].append(actual_hold)

        # ── entry-time levels (see docstring v3) ──
        # PRE-FIX formula pinned INLINE (bug_hunter): compute_atr_sl/tp_pct
        # now delegate to norm (unit fix a032b01c), so calling them here would
        # make atr_cfg ≡ atr_norm and destroy the broken-arm baseline the
        # counterfactual needs. Broken math: percent input vs fraction
        # thresholds/clamps → every ATR clamps to MAX (2.50/2.00).
        _sl_cfg_pct = max(ATR_SL_MIN, min(ATR_SL_MAX, ATR_K_HIGH_VOL * 1.0))
        _tp_cfg_pct = max(ATR_TP_MIN, min(ATR_TP_MAX, ATR_K_HIGH_VOL * 1.0 * ATR_TP_K_MULT))
        sl_cfg = entry * (1 - _sl_cfg_pct) if long_p(t['dir']) else entry * (1 + _sl_cfg_pct)
        tp_cfg = entry * (1 + _tp_cfg_pct) if long_p(t['dir']) else entry * (1 - _tp_cfg_pct)
        risk_cfg = entry * _sl_cfg_pct          # price units (dollars)
        # HML account-cap risk: CUT_LOSER_PNL (account %) / leverage = price %
        # PRICE-UNIT risk: e.g. 4% account / lev 5 = 0.8% of entry in dollars
        risk_hml = entry * (abs(CUT_LOSER_PNL) / 100.0) / max(float(t['lev'] or 1), 1.0)
        # Unit canary (bug_hunter L4 fix): was assert == entry*0.008, which
        # hard-crashed on any non-5x trade or CUT_LOSER change. Range check
        # catches fraction-vs-percent unit flips without pinning values.
        assert 0.001 < abs(CUT_LOSER_PNL) / 100.0 < 0.20,             f'CUT_LOSER_PNL must be account percent (e.g. -4.00), got {CUT_LOSER_PNL}'

        def _run(key, sl_px, tp_px):
            xp, xt = replay(entry, t['dir'], sl_px, tp_px, candles,
                            open_ts, horizon_ts, sl_first=True)
            if xp is None:
                skipped.setdefault(key, []).append(en)
                return
            pnl = price_pnl_pct(t['dir'], entry, xp) * float(t['lev'] or 1)
            hold = (xt - open_ts) / 3600.0
            s = stats[key]
            s['n'] += 1
            s['w'] += 1 if pnl > 0.05 else 0
            s['l'] += 1 if pnl < -0.05 else 0
            s['pnl'].append(pnl)
            s['hold'].append(hold)
            s['timeout'] += 1 if (xt >= horizon_ts - SEC_5M) else 0

        # ── system ATR config (static from entry)
        _run('atr_cfg', sl_cfg, tp_cfg)

        # ── CORRECTED ATR config (norm math: input normalized to fraction) —
        # the unit-fix counterfactual (OOS: history predates any fix)
        _sl_n_pct = compute_atr_sl_pct_norm(1.24)
        _tp_n_pct = compute_atr_tp_pct_norm(1.24)
        sl_n = entry * (1 - _sl_n_pct) if long_p(t['dir']) else entry * (1 + _sl_n_pct)
        tp_n = entry * (1 + _tp_n_pct) if long_p(t['dir']) else entry * (1 - _tp_n_pct)
        _run('atr_norm', sl_n, tp_n)

        # ── R:R on both risk bases
        for R in JUP_EXIT_SIM_RR:
            _r = int(R) if R == int(R) else R
            for basis, risk in (('cfg', risk_cfg), ('hml', risk_hml)):
                rtp = (entry + R * risk) if long_p(t['dir']) else (entry - R * risk)
                rsl = (entry - risk) if long_p(t['dir']) else (entry + risk)
                _run(f'rr{_r}_{basis}', rsl, rtp)
        skipped['rr'] = []

        # ── ride (no exit until horizon)
        if candles:
            last = [r for r in candles if r[0] <= horizon_ts]
            if last:
                xp = last[-1][4]
                pnl = price_pnl_pct(t['dir'], entry, xp) * float(t['lev'] or 1)
                s = stats['ride']
                s['n'] += 1
                s['w'] += 1 if pnl > 0.05 else 0
                s['l'] += 1 if pnl < -0.05 else 0
                s['pnl'].append(pnl)
                s['hold'].append(JUP_EXIT_SIM_MAX_HOLD_H)

        # ── v4: MFE-giveback variants + pm-trail walker (T 2026-10-31) ──────
        # background stack identical for every walker: tightest floor
        # (HML CUT_LOSER/lev vs ATR SL, price fraction) + ATR TP + 12h timeout.
        hml_frac = abs(CUT_LOSER_PNL) / 100.0 / max(float(t['lev'] or 1), 1.0)
        floor_frac = min(hml_frac, _sl_cfg_pct)
        if long_p(t['dir']):
            floor_px = entry * (1 - floor_frac)
        else:
            floor_px = entry * (1 + floor_frac)
        # A/B arms are LITERAL (auditor M3): deriving them from the shipped
        # MFE_EXIT_ARM_PCT made mfe30a040/pm_mfe30a silently duplicate the
        # no-arm rows once the constant was set to 0.0 — the label lied.
        # Shipped config is printed with the report; re-arm A/B only via these
        # literals, never via the constant.
        ARM_NONE, ARM_040 = 0.0, 0.40
        _pm_layer = ('pm_trail', 'pm', 0.0)
        for key, layers in (
            ('bg', []),
            ('mfe30', [('mfe_exit', 'mfe', ARM_NONE)]),      # literal spec: any +MFE
            ('mfe30a040', [('mfe_exit', 'mfe', ARM_040)]),   # armed variant
            ('pmwalk', [_pm_layer]),
            ('pm_mfe30', [_pm_layer, ('mfe_exit', 'mfe', ARM_NONE)]),
            ('pm_mfe30a', [_pm_layer, ('mfe_exit', 'mfe', ARM_040)]),
        ):
            xp, xt, tag = replay_layers(entry, t['dir'], candles, open_ts,
                                        horizon_ts, layers, floor_px, tp_cfg)
            if xp is None:
                skipped.setdefault(key, []).append(en)
                continue
            pnl = price_pnl_pct(t['dir'], entry, xp) * float(t['lev'] or 1)
            hold = (xt - open_ts) / 3600.0
            s = stats[key]
            s['n'] += 1
            s['w'] += 1 if pnl > 0.05 else 0
            s['l'] += 1 if pnl < -0.05 else 0
            s['pnl'].append(pnl)
            s['hold'].append(hold)
            s['timeout'] += 1 if (xt >= horizon_ts - SEC_5M) else 0
            tags[key][tag] += 1

    # ── report
    print(f"\n{'strategy':<12} {'n':>3} {'W':>3} {'L':>3} {'WR%':>5} "
          f"{'net%':>8} {'avg%':>7} {'med%':>7} {'avgHold':>8} {'timeout':>7}")
    print('-' * 82)
    report = {}
    for key in ('pm_actual', 'pm_trail', 'atr_cfg', 'atr_norm',
                'rr2_cfg', 'rr3_cfg', 'rr2_hml', 'rr3_hml', 'ride',
                'bg', 'mfe30', 'mfe30a040', 'pmwalk', 'pm_mfe30', 'pm_mfe30a'):
        s = stats[key]
        n = s['n']
        if not n:
            continue
        tot = sum(s['pnl'])
        avg = tot / n
        med = sorted(s['pnl'])[n // 2]
        wl = s['w'] + s['l']
        wr = (s['w'] / wl * 100) if wl else 0.0
        ah = sum(s['hold']) / n
        print(f"{key:<12} {n:>3} {s['w']:>3} {s['l']:>3} {wr:>5.0f} "
              f"{tot:>+8.2f} {avg:>+7.2f} {med:>+7.2f} {ah:>7.1f}h {s['timeout']:>7}")
        report[key] = {'n': n, 'w': s['w'], 'l': s['l'], 'wr': round(wr, 1),
                       'net_pct': round(tot, 2), 'avg_pct': round(avg, 2),
                       'median_pct': round(med, 2), 'avg_hold_h': round(ah, 1),
                       'timeouts': s['timeout']}

    print(f"\nskipped: atr={len(skipped['atr'])} rr={len(skipped['rr'])} "
          f"no-candles={len(skipped['candles'])} (missing sl/tp columns)")

    # horizon maturity (auditor F-4): timeout/ride rows from trades whose 12h
    # window is still running WILL move as bars accrue — full re-measure
    # protocol: brain/verdicts/2026-10-31_mfe-exit-sim-independent-verify.md
    import time as _time
    _now = int(_time.time())
    _pending = [t['id'] for t in trades
                if int(t['open_t'].timestamp()) + HORIZON_S > _now]
    if _pending:
        print(f"\n⚠ {len(_pending)} trade(s) with 12h horizon still running "
              f"(ids {_pending[:8]}{'...' if len(_pending) > 8 else ''}) — "
              "timeout/ride rows unstable until they elapse.")
    print(f"shipped config: MFE_EXIT_GIVEBACK_PCT={MFE_EXIT_GIVEBACK_PCT:.0%} "
          f"MFE_EXIT_ARM_PCT={MFE_EXIT_ARM_PCT} "
          f"(A/B rows use ARM_NONE/ARM_040 literals, not the constant)")

    # why each walker closed — attribution matters more than the net here
    print("\nwalker exit-tag breakdown:")
    for key in ('bg', 'mfe30', 'mfe30a040', 'pmwalk', 'pm_mfe30', 'pm_mfe30a'):
        if tags.get(key):
            parts = ', '.join(f"{k}={v}" for k, v in sorted(tags[key].items()))
            print(f"  {key:<10} {parts}")
    if 'pmwalk' in report and 'pm_actual' in report:
        print(f"\nwalker validation: pmwalk net {report['pmwalk']['net_pct']:+.2f} "
              f"vs pm_actual {report['pm_actual']['net_pct']:+.2f} "
              f"(pm_actual = real DB closes incl. exits the walker does not model)")

    # per-token net for pm_actual (context for which exits suit which token)
    print("\nper-token pm_actual net (price %):")
    by_tok = defaultdict(lambda: [0, 0.0])
    for t in trades:
        p = float(t['pnl_pct'] or 0)
        by_tok[t['token']][0] += 1
        by_tok[t['token']][1] += p
    for tok, (n, tot) in sorted(by_tok.items(), key=lambda kv: kv[1][1]):
        print(f"  {tok:<6} n={n} net={tot:+.2f}%")

    with open(os.path.join(HERMES_DATA, 'jup_exit_sim.json'), 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nreport -> {HERMES_DATA}/jup_exit_sim.json")
    print("ANALYSIS ONLY — exit code lives in position_manager, gated by "
          "MFE_EXIT_* constants; this script never touches live behavior.")


if __name__ == '__main__':
    main()
