#!/usr/bin/env python3
"""setup_recall cohort-pollution audit (brain_auditor #198, 2026-10-29).

BUG UNDER TEST
--------------
decider_run.similar_setup_lookup() claims "past trades with same signal+direction"
but the SQL is

    signal LIKE '%' || %s || '%'   -- %s = source (may be comma-joined)

Substring semantics means a bare source that is a strict substring of another
signal name silently inherits that other signal's win rate.  Verified live:
source='pump-chain-' matches 'pump-chain-v5', 'pump-chain-v6+', 'pump-chain-v6-'
-- none of which are the minus family the lookup is asked about.

The house convention is EXACT comma-part matching (decider_run._contrarian_live_hit:
"Exact-part match, NOT startswith"; confluence gate uses set(source.split(','))).

WHAT WE MEASURE
---------------
For every (source, direction) that produced a setup-recall HARD BLOCK in the log
window, compute the cohort twice and report whether the block verdict flips:

    A (live)   : signal LIKE '%'||source||'%'
    B (fixed)  : set(signal parts) intersects set(source parts)

Plus, for context, the CONTRARIAN-LIVE fade conversion since 2026-10-27 (the
CEO-approved pump-chain- fade that this block is starving).

Usage:
    python3 brain/analysis/setup_recall_pollution_2026-10-29.py
    python3 brain/analysis/setup_recall_pollution_2026-10-29.py --selfcheck
"""
import os
import re
import sys
import json
import datetime
import collections

sys.path.insert(0, '/root/.hermes/scripts')
import psycopg2  # noqa: E402

LOG = '/root/.hermes/data/../logs/pipeline.log'
HARD_BLOCK_WR = 30      # hermes_constants.SIMILAR_SETUP_HARD_BLOCK_WR
HARD_BLOCK_MIN_N = 5    # hermes_constants.SIMILAR_SETUP_HARD_BLOCK_MIN_N
MIN_SAMPLE = 3          # hermes_constants.SIMILAR_SETUP_MIN_SAMPLE
WINDOW_START = datetime.datetime(2026, 9, 29)
FADE_START = datetime.datetime(2026, 10, 27, 15, 0, 0)
SMOKE = {'TESTCOIN', 'SMOKE', 'TKN', 'TOK'}


def _is_echo(line):
    """True for the double-timestamp child-process echo of an already-logged line."""
    return bool(re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s+\d{4}-', line))


def parse_log(path=LOG):
    """Return (hard_blocks, fade_events) from pipeline.log.

    hard_blocks: list of (ts, token, source, direction)
    fade_events: list of (ts, token, source, new_direction)
    """
    recalls = {}
    blocks = []
    fades = []
    try:
        fh = open(path, 'rb')
    except FileNotFoundError:
        return blocks, fades
    with fh:
        for raw in fh:
            s = raw.decode('utf-8', 'replace')
            m = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', s)
            if not m or _is_echo(s):
                continue
            ts = datetime.datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S')
            if ts < WINDOW_START:
                continue
            r = re.search(r'\[SETUP-RECALL\] (\S+) (\S+) (\S+): n=(\d+) WR=(\d+)%', s)
            if r:
                recalls[(ts, r.group(1))] = (r.group(2), r.group(3))
                continue
            b = re.search(r'\] (\S+) (\S+) blocked: similar setup', s)
            if b:
                blocks.append((ts, b.group(1), b.group(2)))
                continue
            f = re.search(r'\[CONTRARIAN-LIVE\] (\S+) (\S+): \S+ → (\S+)', s)
            if f and f.group(1) not in SMOKE:
                fades.append((ts, f.group(1), f.group(2), f.group(3)))
    # correlate block -> source via same-token recall within +-1s
    out = []
    for ts, tok, dirn in blocks:
        src = None
        for d in (0, 1, -1):
            k = (ts + datetime.timedelta(seconds=d), tok)
            if k in recalls:
                src, _ = recalls[k]
                break
        if src:
            out.append((ts, tok, src, dirn))
    return out, fades


def _parts(s):
    return {p.strip() for p in (s or '').split(',') if p.strip()}


def cohorts(cur, source, direction):
    """Return (n, wr) for each matching rule.

    A (live)  : signal LIKE '%'||source||'%'
                substring -> a bare source that is a strict substring of another
                signal name silently inherits that other signal's cohort.
    B (fix)   : ','||signal||',' LIKE '%,'||source||',%'
                comma-boundary anchored -> contiguous same-part-sequence match.
                Fixes pollution; leaves combo (multi-part) cohorts identical.
    C (info)  : set(signal parts) intersects set(source parts)
                loosest rule; shown for blast-radius context only, NOT proposed.
    """
    a = '%' + source + '%'
    b = '%,' + source + ',%'
    plist = sorted(_parts(source))
    cur.execute("""
        SELECT COUNT(*) FILTER (WHERE signal LIKE %s) AS a_n,
               AVG(CASE WHEN pnl_pct > 0 THEN 1.0 ELSE 0 END) FILTER (WHERE signal LIKE %s) AS a_wr,
               COUNT(*) FILTER (WHERE (',' || signal || ',') LIKE %s) AS b_n,
               AVG(CASE WHEN pnl_pct > 0 THEN 1.0 ELSE 0 END) FILTER (WHERE (',' || signal || ',') LIKE %s) AS b_wr,
               COUNT(*) FILTER (WHERE EXISTS (
                     SELECT 1 FROM unnest(string_to_array(signal, ',')) p
                     WHERE trim(p) = ANY(%s))) AS c_n,
               AVG(CASE WHEN pnl_pct > 0 THEN 1.0 ELSE 0 END) FILTER (WHERE EXISTS (
                     SELECT 1 FROM unnest(string_to_array(signal, ',')) p
                     WHERE trim(p) = ANY(%s))) AS c_wr
        FROM trades
        WHERE status = 'closed' AND direction = %s AND signal IS NOT NULL
    """, (a, a, b, b, plist, plist, direction))
    a_n, a_wr, b_n, b_wr, c_n, c_wr = cur.fetchone()
    return (int(a_n or 0), a_wr), (int(b_n or 0), b_wr), (int(c_n or 0), c_wr)


def verdict(n, wr):
    if n >= MIN_SAMPLE and wr is not None and n >= HARD_BLOCK_MIN_N and wr * 100 < HARD_BLOCK_WR:
        return 'HARD_BLOCK'
    return 'pass'


def main():
    blocks, fades = parse_log()
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()

    keys = sorted({(s, d) for _, _, s, d in blocks})
    # also evaluate every polluted bare source in both directions, so the fix's
    # ability to CREATE a new hard block (cohort shrinks -> WR can fall) is visible
    cur.execute("SELECT DISTINCT unnest(string_to_array(signal,',')) FROM trades WHERE signal IS NOT NULL")
    parts = sorted({p.strip() for (p,) in cur.fetchall()})
    polluted = [p for p in parts if any(q != p and p in q for q in parts)]
    for p in polluted:
        for d in ('LONG', 'SHORT'):
            if (p, d) not in keys:
                keys.append((p, d))

    print(f"hard-block events parsed: {len(blocks)}  |  evaluating {len(keys)} (source,direction)")
    print(f"{'source':<44} {'dir':<6} {'A live':>11} {'B fix':>11} {'C loose':>11}  verdict")
    flips, new_blocks = [], []
    for src, dirn in keys:
        (an, awr), (bn, bwr), (cn, cwr) = cohorts(cur, src, dirn)
        va = verdict(an, awr or 0)
        vb = verdict(bn, bwr or 0)
        if an == 0 and bn == 0 and va == vb:
            continue  # both cohorts empty -> nothing to say
        flag = '  <== FLIP' if va != vb else ''
        print(f"{src:<44} {dirn:<6} {an:>5}/{(awr or 0)*100:>4.0f}% "
              f"{bn:>4}/{(bwr or 0)*100:>4.0f}% {cn:>6}/{(cwr or 0)*100:>4.0f}%  {va}->{vb}{flag}")
        if va != vb:
            flips.append((src, dirn, an, awr, bn, bwr, va, vb))
            if vb == 'HARD_BLOCK':
                new_blocks.append((src, dirn, an, awr, bn, bwr))

    print(f"\nsignal parts that are a strict substring of another part: {len(polluted)}/{len(parts)}")

    # contrarian fade conversion
    cur.execute("SELECT id, token, signal, open_time FROM trades WHERE open_time > %s ORDER BY open_time",
                (FADE_START,))
    trades = cur.fetchall()
    uniq = sorted(set(fades))
    hit = sum(1 for f in uniq
              if any(t[1] == f[1] and abs((t[3] - f[0]).total_seconds()) <= 600 for t in trades))
    print(f"CONTRARIAN-LIVE fade events (non-smoke, deduped): {len(uniq)}")
    print(f"  -> booked a trade within 10min: {hit}/{len(uniq)}"
          f" = {100.0 * hit / max(len(uniq), 1):.1f}%")

    conn.close()
    print(json.dumps({'hard_blocks': len(blocks), 'evaluated': len(keys),
                      'verdict_flips': len(flips), 'new_hard_blocks': len(new_blocks),
                      'fade_events': len(uniq), 'fade_converted': hit}, indent=1))


def selfcheck():
    # 1. substring pollution exists; comma-boundary anchoring removes it
    assert 'pump-chain-v5'.find('pump-chain-') >= 0          # substring rule matches
    assert ',pump-chain-v5,'.find(',pump-chain-,') < 0        # anchored rule does not
    assert ',pump-chain-,pump-chain-v6-,'.find(',pump-chain-,') >= 0
    assert ',pump-chain+,'.find(',pump-chain-,') < 0
    # 2. echo filter
    assert _is_echo('2026-10-29 00:00:00   2026-10-29 00:00:00   [X]')
    assert not _is_echo('2026-10-29 00:00:00   [X]')
    # 3. cohort SQL: live substring vs anchored disagree for pump-chain- LONG
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    (an, awr), (bn, bwr), _ = cohorts(cur, 'pump-chain-', 'LONG')
    assert an > bn, f'expected pollution (a={an} > b={bn})'
    cur.execute("""SELECT COUNT(*) FROM trades WHERE status='closed' AND direction='LONG'
                   AND (',' || signal || ',') LIKE '%,pump-chain-,%'""")
    assert cur.fetchone()[0] == bn, 'anchored count must reproduce'
    # 4. combo cohorts unchanged by the fix (anchoring only removes non-part matches)
    (an2, _), (bn2, _), _ = cohorts(cur, 'pump-chain-,pump-chain-v6-', 'SHORT')
    assert an2 == bn2, f'combo cohort must be invariant (a={an2} b={bn2})'
    conn.close()
    # 5. verdict truth table
    assert verdict(23, 0.261) == 'HARD_BLOCK'
    assert verdict(1, 0.0) == 'pass'
    assert verdict(5, 0.30) == 'pass'
    print(f'selfcheck PASS (pc- LONG a_n={an} b_n={bn}; combo invariant a_n={an2})')


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        selfcheck()
    else:
        main()
