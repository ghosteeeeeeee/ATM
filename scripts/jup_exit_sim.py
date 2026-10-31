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
This is ANALYSIS ONLY — no live behavior changes; any winning exit ships as
shadow via automatic-implementation first.
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
)
from tpsl_utils import compute_atr_sl_pct, compute_atr_tp_pct

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
            "WHERE token=? AND is_closed=1 AND ts>=? AND ts<? ORDER BY ts",
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
             for k in ('pm_actual', 'pm_trail', 'atr_cfg',
                       'rr2_cfg', 'rr3_cfg', 'rr2_hml', 'rr3_hml', 'ride')}

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

        # ── entry-time levels (system formulas; see docstring v3) ──
        _sl_cfg_pct = compute_atr_sl_pct(1.0)   # invariant for any ATR>0.015%
        _tp_cfg_pct = compute_atr_tp_pct(1.0)
        sl_cfg = entry * (1 - _sl_cfg_pct) if long_p(t['dir']) else entry * (1 + _sl_cfg_pct)
        tp_cfg = entry * (1 + _tp_cfg_pct) if long_p(t['dir']) else entry * (1 - _tp_cfg_pct)
        risk_cfg = entry * _sl_cfg_pct          # price units (dollars)
        # HML account-cap risk: CUT_LOSER_PNL (account %) / leverage = price %
        # PRICE-UNIT risk: 4% account / lev = 0.8% of entry in dollars
        risk_hml = entry * (abs(CUT_LOSER_PNL) / 100.0) / max(float(t['lev'] or 1), 1.0)
        assert abs(risk_hml - entry * 0.008) < entry * 0.001,             f'hml risk must be 0.8% of entry: {risk_hml} vs {entry * 0.008}'

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

    # ── report
    print(f"\n{'strategy':<12} {'n':>3} {'W':>3} {'L':>3} {'WR%':>5} "
          f"{'net%':>8} {'avg%':>7} {'med%':>7} {'avgHold':>8} {'timeout':>7}")
    print('-' * 82)
    report = {}
    for key in ('pm_actual', 'pm_trail', 'atr_cfg',
                'rr2_cfg', 'rr3_cfg', 'rr2_hml', 'rr3_hml', 'ride'):
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
    print("ANALYSIS ONLY — no live exit changes; winner ships as shadow first.")


if __name__ == '__main__':
    main()
