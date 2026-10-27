"""Arm-timeout forward test: after a trail_arm_timeout/stale_exit cut, would price
have reached +0.40% arm within 30/60m? Answers "are the 45/55/60m stall cuts too early?"

Anchor: exit (close_time), forward 1m candles only — no lookahead.
Bars (pre-registered 2026-10-27, run #189):
  - review a timeout ONLY if would_arm_60m >= 40% at both 14d and 30d
  - < 25% = cuts validated, do not re-propose
  - between = monitor
selfcheck: synthetic arm detection + real row counts.
"""
import sqlite3, sys, datetime as dt
import psycopg2

CANDLES = '/root/.hermes/data/candles.db'
ARM_PCT = 0.40  # must match PM_TRAIL_ACTIVATE_PCT


def load_cuts(days):
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute("""
        SELECT id, token, direction, entry_price, close_time, pnl_usdt, signal, mfe_pct
        FROM trades
        WHERE status='closed' AND exit_reason IN ('trail_arm_timeout','stale_exit')
          AND close_time > NOW() - INTERVAL %s AND entry_price IS NOT NULL
        ORDER BY close_time DESC""", (f'{days} days',))
    rows = cur.fetchall()
    conn.close()
    return rows


def arm_time_min(c1, token, direction, entry, close_ts, horizon_s=3600):
    """Minutes after exit of first 1m close through +ARM_PCT favorable.
    Returns (minutes|None, saw_candles:bool)."""
    sgn = 1 if direction == 'LONG' else -1
    thr = entry * (1 + sgn * ARM_PCT / 100.0)
    for tok in (token, str(token).upper(), str(token).lower()):
        # ts+60 <= horizon: the arm is read from a candle CLOSE, so the whole
        # candle must complete inside the horizon (ts<=? admitted closes up to +61m)
        rs = c1.execute(
            "SELECT ts, close FROM candles_1m WHERE token=? AND ts>? AND ts+60<=? AND is_closed=1 ORDER BY ts",
            (tok, close_ts, close_ts + horizon_s)).fetchall()
        if rs:
            for ts, cl in rs:
                if (cl >= thr) if sgn == 1 else (cl <= thr):
                    return round((ts + 60 - close_ts) / 60.0, 1), True
            return None, True
    return None, False


def run(days):
    cuts = load_cuts(days)
    c1 = sqlite3.connect(CANDLES)
    rows = []
    for tid, tok, d, ep, ct, pnl, sig, mfe in cuts:
        ts = int(ct.replace(tzinfo=dt.timezone.utc).timestamp())
        t30, seen30 = arm_time_min(c1, tok, d, float(ep), ts, 1800)
        t60, seen60 = arm_time_min(c1, tok, d, float(ep), ts, 3600)
        rows.append(dict(id=tid, tok=tok, d=d, sig=sig, pnl=float(pnl),
                         t30=t30, t60=t60, seen=seen30 or seen60))
    c1.close()

    n = len(rows)
    nodata = sum(1 for r in rows if not r['seen'])
    rep = [r for r in rows if r['seen']]
    n30 = sum(1 for r in rep if r['t30'] is not None)
    n60 = sum(1 for r in rep if r['t60'] is not None)
    pct60 = 100.0 * n60 / max(1, len(rep))
    print(f'{days}d cuts={n} no_candles={nodata} replayable={len(rep)} '
          f'arm_within_30m={n30} ({100.0*n30/max(1,len(rep)):.1f}%) '
          f'arm_within_60m={n60} ({pct60:.1f}%)')
    bysig = {}
    for r in rep:
        bysig.setdefault(r['sig'], []).append(r)
    for sig, rs in sorted(bysig.items(), key=lambda kv: -len(kv[1])):
        a30 = sum(1 for r in rs if r['t30'] is not None)
        a60 = sum(1 for r in rs if r['t60'] is not None)
        print(f'  {sig[:42]:42s} n={len(rs):3d} arm30={a30} arm60={a60} pnl={sum(r["pnl"] for r in rs):+.2f}')
    # median time-to-arm for those that armed
    times = sorted(r['t60'] for r in rep if r['t60'] is not None)
    if times:
        print(f'  median arm latency after cut: {times[len(times)//2]:.1f}m '
              f'(p25={times[len(times)//4]:.1f} p75={times[3*len(times)//4]:.1f})')
    verdict = 'REVIEW' if pct60 >= 40 else ('VALIDATED' if pct60 < 25 else 'MONITOR')
    print(f'would_arm_60m={pct60:.1f}% -> {verdict} '
          '(pre-reg bars: >=40% both 14d+30d = review, <25% = validated)')
    return dict(n=n, nodata=nodata, rep=len(rep), n30=n30, n60=n60, pct60=pct60, verdict=verdict)


def selfcheck():
    c1 = sqlite3.connect(':memory:')
    c1.execute("CREATE TABLE candles_1m(token TEXT, ts INTEGER, close REAL, is_closed INT)")
    c1.executemany("INSERT INTO candles_1m VALUES (?,?,?,1)",
                   [('T', 1000, 99.0), ('T', 1060, 100.2), ('T', 1120, 100.5), ('T', 1180, 100.45)])
    t, seen = arm_time_min(c1, 'T', 'LONG', 100.0, 1000, 3600)
    assert seen and t is not None and abs(t - 3.0) < 0.01, (t, seen)  # arm candle ts=1120 closes at 1180 = 3.0m after exit 1000
    t, seen = arm_time_min(c1, 'T', 'SHORT', 100.0, 1000, 3600)
    assert seen and t is None, (t, seen)
    t, seen = arm_time_min(c1, 'T', 'LONG', 100.0, 1000, 30)
    assert t is None and not seen, (t, seen)  # no rows within 30s window -> treated as no-data
    t, seen = arm_time_min(c1, 'NOPE', 'LONG', 100.0, 1000, 3600)
    assert not seen, (t, seen)
    r14 = run(14)
    assert r14['n'] > 0 and r14['nodata'] <= r14['n'] and r14['rep'] + r14['nodata'] == r14['n']
    print('SELF CHECK PASS')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--selfcheck':
        selfcheck()
    else:
        run(int(sys.argv[1]) if len(sys.argv) > 1 else 14)
