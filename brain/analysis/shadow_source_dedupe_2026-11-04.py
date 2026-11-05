"""Dedupe-aware re-ranking of shadow_trader SIGNAL QUALITY BY SOURCE.

The published report counts every signal fire as an independent observation, so a
single token-event that fires N times is counted N times (same token, same day,
identical simulated net_pnl_pct). This script recomputes the ranking after
collapsing those duplicates and prints raw-vs-deduped for every source with n>=5.
"""
import sqlite3, datetime, sys
from math import comb

DB = '/root/.hermes/brain/shadow_trades.db'


def fisher_binom(w, n):
    if n <= 0:
        return 1.0
    return sum(comb(n, k) for k in range(w, n + 1)) / 2 ** n


def run(days=30):
    c = sqlite3.connect(DB)
    cur = c.cursor()
    since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
    cur.execute("""SELECT source, created_at, token, net_pnl_pct FROM shadow_trades
                   WHERE closed=1 AND created_at>=?""", (since,))
    raw, dedup = {}, {}
    for src, ts, tok, pct in cur.fetchall():
        if pct is None:
            continue
        raw.setdefault(src, []).append(pct)
        dedup.setdefault(src, {})[(tok, ts[:10], round(pct, 3))] = pct
    c.close()

    rows = []
    for src, vals in raw.items():
        if len(vals) < 5:
            continue
        dv = list(dedup[src].values())
        rw = sum(1 for v in vals if v > 0)
        dw = sum(1 for v in dv if v > 0)
        rows.append((src, len(vals), rw, sum(vals), len(dv), dw, sum(dv)))
    rows.sort(key=lambda r: -r[6] / max(r[4], 1))  # rank by deduped avg
    out = []
    out.append(f'SHADOW SOURCE RANKING — raw (published) vs deduped (independent events), {days}d')
    out.append(f'{"source":32} {"raw_n":>6} {"rawWR":>6} {"raw_avg":>8} | {"ded_n":>6} {"dedWR":>6} {"ded_avg":>8} {"ded_sum":>8}')
    for src, rn, rw, rs, dn, dw, ds in rows:
        out.append(f'{src[:32]:32} {rn:6d} {rw/rn*100:5.1f}% {rs/rn:+8.2f} | {dn:6d} {dw/max(dn,1)*100:5.1f}% {ds/max(dn,1):+8.2f} {ds:+8.2f}')
    return out


def selfcheck():
    # 1. a repeated identical token-event must collapse to one observation
    c = sqlite3.connect(DB)
    cur = c.cursor()
    since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14)).isoformat()
    cur.execute("""SELECT created_at, token, net_pnl_pct FROM shadow_trades
                   WHERE signal_type='grind_breakout_short' AND gate_blocked=1
                     AND gate_name='UNKNOWN' AND created_at>=? AND closed=1""", (since,))
    raw_rows = cur.fetchall()
    c.close()
    d = {}
    for ts, tok, pct in raw_rows:
        d[(tok, ts[:10], round(pct, 3))] = pct
    assert len(d) < len(raw_rows), 'dedupe must remove duplicated token-events'
    vals = list(d.values())
    p = fisher_binom(sum(1 for v in vals if v > 0), len(vals))
    # 2. grind knife-floor cohort must NOT clear p<0.05 after dedupe
    assert p > 0.05, f'expected post-dedupe p>0.05, got {p:.4f}'
    # 3. duplicate CRV pair present in raw
    crv = [r for r in raw_rows if r[1] == 'CRV']
    assert len(crv) >= 2, 'expected the duplicated CRV pair in raw rows'
    print(f'SELFCHECK PASS (raw={len(raw_rows)} dedup={len(vals)} p={p:.4f} crv_rows={len(crv)})')
    return True


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        selfcheck()
        sys.exit(0)
    days = 30
    for a in sys.argv[1:]:
        if a.isdigit():
            days = int(a)
    print('\n'.join(run(days)))
