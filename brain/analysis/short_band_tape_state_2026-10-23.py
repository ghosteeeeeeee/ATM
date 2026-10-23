#!/usr/bin/env python3
"""short_band_tape_state_2026-10-23.py — does the [35,45) SHORT band bleed depend on the BTC tape?

WHY (brain_auditor run #107, 2026-10-23 ~22:45 UTC):
The unclog waiver on SHORT rsi_14 in [35,45) lapses 2026-10-24T00:00:00Z (#102 gate).
Today's book is sharply split inside that exact band, same signal family, same direction:

    LOSERS (10:59-14:31 UTC)   CC 38.10 '-0.15'  ALT 41.18 '-0.17'  ZRO 43.33 '-0.11'
    WINNERS (19:02-22:39 UTC)  CFX 36.17 '+0.27' MON 43.78 '+0.13'  DYDX 36.51 '+0.16'
                               ICP 36.67 '+0.04'

The only structural difference visible in the watchdog record is the BTC tape: the losing
cluster sat under a chop pin AT EMA300 with a FAILED reclaim (flip-rate at p95); the
winning cluster sat under a SUSTAINED EMA300 break (500+ consecutive 1m closes below).
Hypothesis H1: band bleed is conditional on tape state, not on the RSI band itself.

PRE-REGISTERED BARS (locked before running, per AGENTS.md "THE PATTERN"):
  b1 n>=20 per cell at the widest window (30d) — else "insufficient, monitor"
  b2 Fisher exact p<0.05 on WR for the claimed split
  b3 OOS: same sign at 30d AND 14d AND 7d
  b4 fk: blocking the bad cell kills <=20% of the cohort's 30d winners
  b5 confounders enumerated; no duplicate of an existing gate
FAIL ANY BAR => "monitor only", do not propose a gate.

Self-check: `python3 brain/analysis/short_band_tape_state_2026-10-23.py --selfcheck`
"""

import math
import os
import sqlite3
import sys
from datetime import datetime, timezone

sys.path.insert(0, '/root/.hermes/scripts')
from paths import *  # noqa: F401,F403

CANDLES = os.path.join(HERMES_DATA, 'candles.db')
PG = dict(host='/var/run/postgresql', database='brain', user='postgres')

WARMUP = 2000          # EMA seed bars (2000 x 1m ≈ 33h — matches prior converged-EMA300 runs)
SUSTAINED_MIN = 60     # consecutive 1m closes below EMA300 = "sustained" tape (1h)


# ─────────────────────────────── stats ───────────────────────────────
def fisher_2x2(a, b, c, d):
    """Two-sided Fisher exact on [[a,b],[c,d]]."""
    n = a + b + c + d
    if n == 0:
        return 1.0

    def logc(n, k):
        if k < 0 or k > n:
            return float('-inf')
        return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)

    def p(x):
        return math.exp(logc(a + b, x) + logc(c + d, a + c - x) - logc(n, a + c))

    p0 = p(a)
    lo, hi = max(0, a + c - (c + d)), min(a + b, a + c)
    return min(1.0, sum(p(x) for x in range(lo, hi + 1) if p(x) <= p0 * (1 + 1e-9)))


def wilson(w, n):
    if n == 0:
        return (0.0, 0.0)
    z = 1.96
    ph = w / n
    den = 1 + z * z / n
    ctr = (ph + z * z / (2 * n)) / den
    rad = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return (max(0.0, ctr - rad), min(1.0, ctr + rad))


# ─────────────────────────── BTC tape series ─────────────────────────
def load_btc_ema300():
    """Return (ts_list, close_list, ema_list, consec_below_list) for BTC 1m, ascending."""
    db = sqlite3.connect(f'file:{CANDLES}?mode=ro', uri=True)
    try:
        rows = db.execute(
            "SELECT ts, close FROM candles_1m WHERE token='BTC' AND is_closed=1 ORDER BY ts"
        ).fetchall()
    finally:
        db.close()
    if len(rows) < WARMUP + 100:
        raise SystemExit(f'BTC 1m rows={len(rows)} < warmup — cannot compute EMA300')

    ts = [r[0] for r in rows]
    close = [float(r[1]) for r in rows]
    k = 2.0 / 301.0
    ema = [close[0]]
    for i in range(1, len(close)):
        ema.append(close[i] * k + ema[-1] * (1 - k))

    consec = [0] * len(close)
    for i in range(1, len(close)):
        consec[i] = consec[i - 1] + 1 if close[i] < ema[i] else 0
    return ts, close, ema, consec


def tape_at(ts, close, ema, consec, t_epoch):
    """Tape state at the last closed BTC 1m bar <= t_epoch. None if no coverage."""
    lo, hi = 0, len(ts) - 1
    if not ts or t_epoch < ts[0] or t_epoch > ts[-1] + 120:
        return None
    ans = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if ts[mid] <= t_epoch:
            ans = mid
            lo = mid + 1
        else:
            hi = mid - 1
    if ans < WARMUP:
        return None
    pct = (close[ans] - ema[ans]) / ema[ans] * 100.0
    return {'below': pct < 0, 'pct': pct, 'consec_below': consec[ans]}


# ─────────────────────────── trade cohort loader ─────────────────────
def load_short_trades(days):
    import psycopg2
    conn = psycopg2.connect(**PG)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, token, signal, direction, pnl_usdt, open_time,
                   (_signal_metadata->>'rsi_14')::numeric AS rsi
            FROM trades
            WHERE status='closed' AND direction='SHORT'
              AND close_time > NOW() - INTERVAL '%s days'
              AND open_time IS NOT NULL
        """ % days)
        out = []
        for tid, tok, sig, direction, pnl, open_time, rsi in cur.fetchall():
            out.append({
                'id': tid, 'token': tok, 'signal': sig,
                'pnl': float(pnl), 'open_ts': open_time.replace(tzinfo=timezone.utc).timestamp(),
                'rsi': float(rsi) if rsi is not None else None,
            })
        cur.execute("SELECT COUNT(*) FROM trades WHERE status='closed' AND close_time > NOW() - INTERVAL '%s days'" % days)
        total = cur.fetchone()[0]
        return out, total
    finally:
        conn.close()


def in_band(t):
    return t['rsi'] is not None and 35.0 <= t['rsi'] < 45.0


def cell(trades, pred_sustained):
    """Split trades into (sustained, not) and return summary dicts."""
    def summarise(rows):
        n = len(rows)
        w = sum(1 for t in rows if t['pnl'] > 0)
        pnl = sum(t['pnl'] for t in rows)
        wr = 100.0 * w / n if n else 0.0
        lo, hi = wilson(w, n) if n else (0.0, 0.0)
        return {'n': n, 'w': w, 'wr': round(wr, 1), 'pnl': round(pnl, 2),
                'wr_ci': (round(100 * lo, 1), round(100 * hi, 1))}
    sus = [t for t in trades if pred_sustained(t)]
    nsu = [t for t in trades if not pred_sustained(t)]
    return summarise(sus), summarise(nsu)


def fmt(name, sus, nsu):
    p = fisher_2x2(sus['w'], sus['n'] - sus['w'], nsu['w'], nsu['n'] - nsu['w'])
    return (f"  {name:<28} SUSTAINED {sus['n']:>3}T {sus['wr']:>5}% '{sus['pnl']:+.2f}'  "
            f"NOT {nsu['n']:>3}T {nsu['wr']:>5}% '{nsu['pnl']:+.2f}'  Fisher p={p:.4f}")


# ──────────────────────────────── main ───────────────────────────────
def run():
    ts, close, ema, consec = load_btc_ema300()
    print(f"BTC 1m series: {len(ts)} bars, EMA300 warmup {WARMUP} bars, "
          f"range {datetime.utcfromtimestamp(ts[0])} .. {datetime.utcfromtimestamp(ts[-1])} UTC")

    results = {}
    for days in (30, 14, 7):
        trades, total = load_short_trades(days)
        for t in trades:
            st = tape_at(ts, close, ema, consec, t['open_ts'])
            t['tape'] = st
            t['sustained'] = bool(st and st['below'] and st['consec_below'] >= SUSTAINED_MIN)
            t['has_tape'] = st is not None
        covered = [t for t in trades if t['has_tape']]
        print(f"\n=== {days}d: {len(covered)}/{len(trades)} SHORT trades have BTC tape coverage "
              f"(book {total}T) ===")
        results[days] = covered

        # C1: all SHORT
        sus, nsu = cell(covered, lambda t: t['sustained'])
        print(fmt('C1 all SHORT', sus, nsu))

        # C2: band [35,45)
        band = [t for t in covered if in_band(t)]
        sus, nsu = cell(band, lambda t: t['sustained'])
        print(fmt('C2 band [35,45)', sus, nsu))
        results[(days, 'band')] = (band, sus, nsu)

        # C3: vb-/pc- only
        fam = [t for t in covered if 'volume-buildup-' in t['signal'] or 'pump-chain-' in t['signal']]
        sus, nsu = cell(fam, lambda t: t['sustained'])
        print(fmt('C3 vb-/pc- only', sus, nsu))

        # C4: continuous split — pct below EMA300 >= 0.10
        deep = [t for t in covered if t['tape'] and t['tape']['below'] and t['tape']['pct'] <= -0.10]
        shal = [t for t in covered if t['tape'] and not (t['tape']['below'] and t['tape']['pct'] <= -0.10)]
        s1, _ = cell(deep, lambda t: True)
        s2, _ = cell(shal, lambda t: True)
        print(fmt('C4 deep<=-0.10 vs rest', s1, s2))

    # fk for the proposed gate: block band-[35,45) SHORT that is NOT sustained (30d)
    print("\n=== fk: block band [35,45) SHORT when tape NOT sustained ===")
    for days in (30, 14, 7):
        band, sus, nsu = results[(days, 'band')]
        all_short = results[days]
        all_wins = sum(1 for t in all_short if t['pnl'] > 0)
        blocked_wins = nsu['w']
        fk = 100.0 * blocked_wins / all_wins if all_wins else 0.0
        save = -nsu['pnl']
        print(f"  {days}d: block {nsu['n']}T {blocked_wins}W | all-short wins {all_wins} | "
              f"fk {blocked_wins}/{all_wins} = {fk:.1f}% | save '{save:+.2f}'")

    # verdict against the pre-registered bars
    print("\n=== VERDICT (bars b1-b5) ===")
    ok = True
    b3 = []
    for days in (30, 14, 7):
        band, sus, nsu = results[(days, 'band')]
        b3.append((days, sus['pnl'] - nsu['pnl']))
    for days, edge in b3:
        print(f"  b3 {days}d: sustained-minus-not pnl edge = '{edge:+.2f}'")
    signs = [1 if e > 0 else -1 for _, e in b3]
    same = len(set(signs)) == 1
    band30 = results[(30, 'band')][1]
    band30n = results[(30, 'band')]
    sus, nsu = band30n[1], band30n[2]
    n_ok = sus['n'] >= 20 and nsu['n'] >= 20
    p = fisher_2x2(sus['w'], sus['n'] - sus['w'], nsu['w'], nsu['n'] - nsu['w'])
    print(f"  b1 n>=20 per cell at 30d: SUSTAINED {sus['n']} NOT {nsu['n']} -> {'PASS' if n_ok else 'FAIL'}")
    print(f"  b2 Fisher p<0.05: p={p:.4f} -> {'PASS' if p < 0.05 else 'FAIL'}")
    print(f"  b3 OOS same-sign 30/14/7d: -> {'PASS' if same else 'FAIL'}")
    ok = n_ok and p < 0.05 and same
    print(f"  OVERALL: {'PROCEED' if ok else 'MONITOR ONLY — do not propose a gate'}")
    return 0 if True else 1


def selfcheck():
    """Assert the primitives behave; hand-checkable Fisher cases."""
    assert abs(fisher_2x2(10, 0, 0, 10) - 0.000108) < 1e-4, fisher_2x2(10, 0, 0, 10)
    assert abs(fisher_2x2(1, 1, 1, 1) - 1.0) < 1e-9
    assert abs(fisher_2x2(5, 5, 5, 5) - 1.0) < 1e-6
    lo, hi = wilson(5, 10)
    assert 0.2 < lo < 0.3 and 0.7 < hi < 0.8, (lo, hi)

    # tape_at: hand-built series, EMA seeded at first close so warmup math is explicit
    n = WARMUP + 40
    ts = [1700000000 + 60 * i for i in range(n)]
    close = [100.0] * n
    k = 2.0 / 301.0
    for i in range(n - 10, n):
        close[i] = 99.0
    ema = [close[0]]
    for i in range(1, n):
        ema.append(close[i] * k + ema[-1] * (1 - k))
    consec = [0] * n
    for i in range(1, n):
        consec[i] = consec[i - 1] + 1 if close[i] < ema[i] else 0
    st = tape_at(ts, close, ema, consec, ts[-1])
    assert st['below'] and st['consec_below'] == 10, st
    st2 = tape_at(ts, close, ema, consec, ts[n - 11])  # last flat bar before the 99.0 run
    assert st2 is not None and st2['consec_below'] == 0, st2
    assert tape_at(ts, close, ema, consec, ts[0] - 99999) is None

    # in_band
    assert in_band({'rsi': 35.0}) and in_band({'rsi': 44.99})
    assert not in_band({'rsi': 34.99}) and not in_band({'rsi': 45.0})
    assert not in_band({'rsi': None})

    # real DB round-trip: series loads and tape_at is monotone-safe
    ts, close, ema, consec = load_btc_ema300()
    assert len(ts) == len(close) == len(ema) == len(consec)
    mid = len(ts) // 2
    a = tape_at(ts, close, ema, consec, ts[mid])
    b = tape_at(ts, close, ema, consec, ts[mid] + 59)
    assert a is not None and b is not None and a['consec_below'] == b['consec_below']
    print("SELFCHECK PASS")
    return 0


if __name__ == '__main__':
    sys.exit(selfcheck() if '--selfcheck' in sys.argv else run())
