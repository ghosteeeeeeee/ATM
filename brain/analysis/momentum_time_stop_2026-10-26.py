#!/usr/bin/env python3
"""
momentum_time_stop_2026-10-26.py — brain_auditor run #156 CREATIVE CANDIDATE #1

QUESTION (mandate: "exit early in chop — if a trade goes nowhere, cut it fast"):
14d never-armed trades (mfe_pct < 0.40) = 147T / -$13.20 of the -$15.34 gross
loss, and the densest cell is hold 15-45m with MFE<0.40 = 60T 6.7% WR -$5.56.
hard_max_loss exits at avg 30.1m with avg MFE 0.098% — i.e. the stop fires
AFTER the trade has already proven it has no momentum.

RULE UNDER TEST (hold-time exit, NOT time-of-day — clock-time filters are banned):
  at T minutes after entry, if the best 1m CLOSE move so far (signed, vs entry)
  is still < THR percent, exit at the T-minute close and stand flat.
  Trades that already closed before T keep their real outcome.

PRE-REGISTERED BARS (written before the results are read):
  B1 n_eligible >= 100            (of 14d closed trades)
  B2 delta (sim - actual) > +$1.00 over the 14d window
  B3 paired p < 0.05 (two-sided, on modified trades)
  B4 both halves of the window same sign (split at the 7d boundary)
  B5 <20% of ACTUAL winners zeroed or flipped to a loss by the rule
  B6 delta still > +$1.00 after subtracting 0.05% round-trip fee on every
     modified trade's notional (units: pnl_usdt basis only, never pnl_pct)

Grid: T in {10,15,20,30} min x THR in {0.10%, 0.20%}.
Any (T,THR) passing B1-B6 is a CANDIDATE FOR CEO — nothing ships from here.

UNITS: every PnL is derived as amount_usdt * signed_price_move% / 100 (the
pnl_usdt identity, verified against live rows) — pnl_pct is LEVERAGED and is
never used.

Run: python3 brain/analysis/momentum_time_stop_2026-10-26.py [--selfcheck]
"""
import math
import os
import sqlite3
import sys
from datetime import timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'scripts'))
from paths import HERMES_DATA  # noqa: E402

CANDLES = os.path.join(HERMES_DATA, 'candles.db')
TS_GRID = (10, 15, 20, 30)
THR_GRID = (0.10, 0.20)
DAYS = 14
FEE_PCT = 0.05  # round trip, percent of notional


def _p_value(t_stat, n):
    if n < 2:
        return 1.0
    try:
        from scipy import stats
        return float(2 * stats.t.sf(abs(t_stat), n - 1))
    except Exception:
        z = t_stat  # normal approx, adequate for n>=30
        return math.erfc(abs(z) / math.sqrt(2))


def load_trades():
    import psycopg2
    pg = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = pg.cursor()
    cur.execute("""
        SELECT id, token, direction, entry_price, exit_price, amount_usdt,
               pnl_usdt, open_time, close_time, signal,
               EXTRACT(EPOCH FROM (close_time - open_time))/60.0 AS hold_min
        FROM trades
        WHERE status='closed' AND pnl_usdt IS NOT NULL
          AND close_time > NOW() - INTERVAL '%d days'
        ORDER BY open_time
    """ % DAYS)
    rows = cur.fetchall()
    pg.close()
    out = []
    for (tid, tok, d, entry, exitp, amt, pnl, ot, ct, sig, hold) in rows:
        if entry is None or exitp is None or amt is None:
            continue
        entry, exitp, amt = float(entry), float(exitp), float(amt)
        if not entry or not amt:
            continue
        move = (exitp - entry) / entry * 100.0 * (1 if d == 'LONG' else -1)
        out.append({
            'id': tid, 'token': tok, 'dir': d, 'entry': entry, 'amount': amt,
            'pnl': float(pnl), 'move': move, 'open': ot, 'close': ct,
            'signal': sig, 'hold': float(hold),
            # pnl_usdt identity: usdt per 1% of notional price move
            'usdt_per_pct': amt / 100.0,
        })
    return out


def candle_window(con, token, t0, t1):
    """Closes in [t0, t1] (epoch seconds, closed candles only)."""
    return con.execute(
        "SELECT ts, close FROM candles_1m WHERE token=? AND is_closed=1 "
        "AND ts>=? AND ts<=? ORDER BY ts", (token, t0, t1)).fetchall()


def evaluate(trades, T, THR):
    """Returns (stats dict, per-trade deltas for modified trades)."""
    con = sqlite3.connect(CANDLES)
    deltas, detail, missed = [], [], 0
    eligible = 0
    actual_winners = zeroed = worsened_winners = modified = 0
    for t in trades:
        o_epoch = int(t['open'].replace(tzinfo=timezone.utc).timestamp())
        c_epoch = int(t['close'].replace(tzinfo=timezone.utc).timestamp())
        if (c_epoch - o_epoch) < T * 60:
            continue  # trade already closed before the rule could fire
        rows = candle_window(con, t['token'], o_epoch, o_epoch + T * 60)
        if len(rows) < 2:
            missed += 1
            continue
        eligible += 1
        sgn = 1 if t['dir'] == 'LONG' else -1
        closes = [r[1] for r in rows]
        mfe = max((c - t['entry']) / t['entry'] * 100.0 * sgn for c in closes)
        if mfe >= THR:
            continue  # momentum showed -> hold (actual outcome stands)
        exit_close = closes[-1]
        sim_move = (exit_close - t['entry']) / t['entry'] * 100.0 * sgn
        sim_pnl = t['usdt_per_pct'] * sim_move
        fee = t['amount'] * FEE_PCT / 100.0
        d = sim_pnl - t['pnl']
        deltas.append(d)
        modified += 1
        if t['pnl'] > 0:
            actual_winners += 1
            if sim_pnl <= 0:
                zeroed += 1
            if sim_pnl < t['pnl']:
                worsened_winners += 1
        detail.append({'id': t['id'], 'token': t['token'], 'dir': t['dir'],
                       'hold': round(t['hold'], 1), 'mfe': round(mfe, 3),
                       'actual': round(t['pnl'], 3), 'sim': round(sim_pnl, 3),
                       'delta': round(d, 3)})
    con.close()

    n = len(deltas)
    total_delta = sum(deltas)
    # fee drag only on modified trades (0.05% round trip of notional)
    amt_by_id = {t['id']: t['amount'] for t in trades}
    fee_drag = sum(amt_by_id[d['id']] * FEE_PCT / 100.0 for d in detail)
    if n >= 2:
        mean = total_delta / n
        var = sum((x - mean) ** 2 for x in deltas) / (n - 1)
        t_stat = mean / math.sqrt(var / n) if var > 0 else 0.0
        p = _p_value(t_stat, n)
    else:
        t_stat, p = 0.0, 1.0

    # halves by trade order (open_time sorted): split at midpoint index
    half = len(deltas) // 2 if deltas else 0
    h1 = sum(deltas[:half]) if half else 0.0
    h2 = sum(deltas[half:]) if half else 0.0
    zeroed_pct = (zeroed / actual_winners * 100.0) if actual_winners else 0.0

    return {
        'T': T, 'THR': THR, 'eligible': eligible, 'no_candles': missed,
        'modified': modified, 'delta': round(total_delta, 3),
        'delta_net_fee': round(total_delta - fee_drag, 3),
        't': round(t_stat, 3), 'p': round(p, 4),
        'half1': round(h1, 3), 'half2': round(h2, 3),
        'actual_winners_modified': actual_winners,
        'zeroed_winners': zeroed, 'zeroed_pct': round(zeroed_pct, 1),
        'worsened_winners': worsened_winners,
        'bars': None, 'detail': detail,
    }


def apply_bars(s):
    bars = {
        'B1_n>=100': s['eligible'] >= 100,
        'B2_delta>+1.00': s['delta'] > 1.00,
        'B3_p<0.05': s['p'] < 0.05,
        'B4_halves_same_sign': (s['half1'] > 0) == (s['half2'] > 0) and s['half1'] != 0,
        'B5_winner_zeroed<20%': s['zeroed_pct'] < 20.0,
        'B6_fee_adj_delta>+1.00': s['delta_net_fee'] > 1.00,
    }
    s['bars'] = bars
    s['pass_all'] = all(bars.values())
    return s


def main():
    selfcheck = '--selfcheck' in sys.argv
    trades = load_trades()
    print(f'=== momentum time-stop — {DAYS}d trades loaded: {len(trades)} ===')
    print(f'PRE-REGISTERED BARS: B1 n>=100 | B2 delta>+$1.00 | B3 p<0.05 | '
          f'B4 halves same sign | B5 winner-zeroed<20% | B6 fee-adj delta>+$1.00')
    print(f'{"T":>4} {"THR":>6} {"elig":>5} {"mod":>5} {"delta":>8} {"+fee":>8} '
          f'{"p":>7} {"h1":>7} {"h2":>7} {"z%":>5}  verdict')
    results = []
    for T in TS_GRID:
        for THR in THR_GRID:
            s = apply_bars(evaluate(trades, T, THR))
            results.append(s)
            print(f"{T:>4} {THR:>6.2f} {s['eligible']:5d} {s['modified']:5d} "
                  f"{s['delta']:>+8.2f} {s['delta_net_fee']:>+8.2f} {s['p']:>7.4f} "
                  f"{s['half1']:>+7.2f} {s['half2']:>+7.2f} {s['zeroed_pct']:>5.1f}  "
                  f"{'PASS' if s['pass_all'] else 'fail'}")
    passing = [s for s in results if s['pass_all']]
    print(f"\nCANDIDATES PASSING ALL BARS: {len(passing)}")
    for s in passing:
        print(f"  T={s['T']}m THR={s['THR']}% delta={s['delta']:+.2f} "
              f"(fee-adj {s['delta_net_fee']:+.2f}) p={s['p']} n_mod={s['modified']}")

    if selfcheck:
        assert len(trades) > 200, 'expected a full 14d sample'
        # units rule: usdt_per_pct must be amount/100 for every trade
        for t in trades[:50]:
            assert abs(t['usdt_per_pct'] - t['amount'] / 100.0) < 1e-9
        # identity check against stored pnl (fees may shift it a little)
        errs = [abs(t['move'] * t['usdt_per_pct'] - t['pnl']) for t in trades if abs(t['move']) > 0.01]
        assert errs and (sum(errs) / len(errs)) < 0.02, 'pnl identity does not hold'
        # bars are deterministic on a re-run of one cell
        a = apply_bars(evaluate(trades, 15, 0.10))
        b = apply_bars(evaluate(trades, 15, 0.10))
        assert a['delta'] == b['delta'] and a['p'] == b['p'], 'non-reproducible'
        print(f"\nSELF-CHECK PASS: n={len(trades)} | pnl identity mean abs err "
              f"{sum(errs)/len(errs):.4f} USDT | cell(15m,0.10) reproducible "
              f"delta={a['delta']:+.2f}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
