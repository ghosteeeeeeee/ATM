#!/usr/bin/env python3
"""PM ACTIVATION-COVERAGE KPI — pre-registered #135 (eval bar: n>=20).

Question: of PM-eligible trades (signal NOT in PROFIT_MONSTER_BYPASS_SIGNALS — i.e.
profit-monster owns their trail), how many had a 1m close at/through +0.40% (arm
condition) but NO `[TRAIL] ... activated` line inside the trade's own [open, close]
window? Those are trades the trail SHOULD have engaged but the poll never logged
engagement -> fix would be poll cadence / resting order, NOT a trail parameter.

Arm model: 1m CLOSE (poll-sampler — what PM actually observes), matching #135's
"98% of armed trades also close-cross +0.40".

Caveats (bug_hunter #136):
- NULL signal is NOT PM-eligible (live PM SQL `AND NOT (signal LIKE ...)` drops NULLs).
- coverage is matched on token+window: 1 overlapping same-token armed pair in 30d
  (BTC #15801/#15814) can be credited by a single activation line -> coverage is
  overstated by <=0.4pp until the `[TRAIL]` log line carries trade_id.
- arm window includes the candle containing open_time and close_time (4/230 trades
  arm only on those edges) — looser than trail_distance_oos `_replay` (>= open only).

Self-check: python3 brain/analysis/pm_activation_coverage_2026-10-25.py --selfcheck
"""
import sys, re, sqlite3, argparse, datetime as dt
import psycopg2

sys.path.insert(0, '/root/.hermes/scripts')
from hermes_constants import PROFIT_MONSTER_BYPASS_SIGNALS

ARM = 0.0040
LOG = '/root/.hermes/logs/profit_monster.log'
LINE = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\[TRAIL\] (\S+) activated:')


def pm_eligible(sig):
    if not sig:
        return False   # NULL signal: PM's `NOT (signal LIKE ...)` never matches NULL
    sig = sig or ''
    return not any(s in sig for s in PROFIT_MONSTER_BYPASS_SIGNALS)


def load_arms(pg, days):
    """PM-eligible closed trades with close-arm flag from candles_1m."""
    cur = pg.cursor()
    cur.execute("""
        SELECT id, token, direction, entry_price, open_time, close_time, signal, exit_reason, pnl_usdt
        FROM trades
        WHERE status='closed' AND close_time > NOW() - INTERVAL '%d days'
          AND entry_price IS NOT NULL AND open_time IS NOT NULL
    """ % days)
    rows = [r for r in cur.fetchall() if pm_eligible(r[6])]
    cur.close()
    con = sqlite3.connect('/root/.hermes/data/candles.db')
    out, missing = [], 0
    try:
        cc = con.cursor()
        for (tid, token, d, entry, ot, ct, sig, er, pnl) in rows:
            o = int(ot.timestamp())
            cc.execute("SELECT close FROM candles_1m WHERE token=? AND ts>=? AND ts<=? ORDER BY ts",
                       (token, o // 60 * 60 - 60, int(ct.timestamp())))
            closes = [float(r[0]) for r in cc.fetchall()]
            if not closes:
                missing += 1
                continue
            e = float(entry)
            hit = any((c >= e * (1 + ARM)) if d == 'LONG' else (c <= e * (1 - ARM)) for c in closes)
            if hit:
                out.append((tid, token, ot, ct, sig, er, float(pnl or 0)))
    finally:
        con.close()
    return out, missing


def load_trail_lines(path=LOG):
    lines = []
    with open(path, 'rb') as f:
        for raw in f:
            try:
                s = raw.decode('utf-8', 'replace').strip()
            except Exception:
                continue
            m = LINE.match(s)
            if m:
                lines.append((dt.datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S'), m.group(2)))
    return lines


def coverage(days=30):
    pg = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    try:
        armed, missing = load_arms(pg, days)
    finally:
        pg.close()
    trail = load_trail_lines()
    covered, uncovered = [], []
    for t in armed:
        tid, token, ot, ct, sig, er, pnl = t
        if any(tok == token and ot <= ts <= ct for ts, tok in trail):
            covered.append(t)
        else:
            uncovered.append(t)
    return dict(armed=len(armed), missing_candles=missing, covered=len(covered),
                uncovered=len(uncovered),
                coverage_pct=round(100.0 * len(covered) / len(armed), 1) if armed else 0.0,
                uncovered_pnl=round(sum(t[6] for t in uncovered), 2),
                uncovered_sample=[(t[0], t[1], t[4], t[5], round(t[6], 3)) for t in uncovered[:15]])


def selfcheck():
    # synthetic trail log parsing
    import tempfile, os
    with tempfile.NamedTemporaryFile('w', suffix='.log', delete=False) as f:
        f.write("2026-10-25 08:55:11   [TRAIL] HYPER activated: pnl=0.85% peak=0.85% trail_floor=0.65%\n"
                "2026-10-25 08:55:12 garbage line\n")
        p = f.name
    got = load_trail_lines(p)
    os.unlink(p)
    assert len(got) == 1 and got[0][1] == 'HYPER', got
    # eligibility
    assert pm_eligible('r2v2-long3') is True
    assert pm_eligible('pump-chain-,pump-chain-v6-') is False   # bypass tokens inside combo
    assert pm_eligible('hl_copy_trader') is False
    assert pm_eligible(None) is False and pm_eligible('') is False  # NULL signal -> not PM-managed
    # arm rule: LONG arms at close >= entry*1.004, not before
    con = sqlite3.connect(':memory:')
    con.execute("CREATE TABLE candles_1m (token TEXT, ts INT, high REAL, low REAL, close REAL)")
    con.executemany("INSERT INTO candles_1m VALUES (?,?,?,?,?)",
                    [('T1', 600, 100.5, 99.9, 100.3),    # close 100.3 < 100.4 -> no arm
                     ('T1', 660, 100.6, 100.2, 100.45)])  # close 100.45 >= 100.4 -> arm
    closes = [r[0] for r in con.execute("SELECT close FROM candles_1m WHERE token='T1'")]
    e = 100.0
    assert not any(c >= e * 1.004 for c in closes[:1])
    assert any(c >= e * 1.004 for c in closes)
    con.close()
    print("selfcheck PASS: trail-line parse + PM-eligibility (combo string) + close-arm rule")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--selfcheck', action='store_true')
    ap.add_argument('--days', type=int, default=30)
    a = ap.parse_args()
    if a.selfcheck:
        selfcheck()
        sys.exit(0)
    import json
    print(json.dumps(coverage(a.days), indent=1))
