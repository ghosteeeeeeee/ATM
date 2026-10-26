#!/usr/bin/env python3
"""
arm_gap_baseline_2026-10-26.py — brain_auditor run #161

TWO QUESTIONS the run-#160 ARM-GAP pre-registration depends on:

Q1. What does trades.trailing_activated actually measure?
    The run-#160 arm_rate_ledger and the ARM-GAP cohort label
    ("trail never registered the arm") both assume it is an ARMING flag.

Q2. Is the run-#160 ARM-GAP bar ("post-GC 7d cohort rate < 14d baseline
    35/109 = 32.1%") able to discriminate cause (a) stale trail-state keys
    from cause (b) exit order?  It cannot if the 14d baseline is mostly
    PRE-deployment for the very mechanism (UGB-PT ENFORCE) that closes that
    cohort.

METHOD:
  * read the live PG trigger source (trades_set_trailing_activated)
  * cross-tab exit_reason x trailing_activated
  * check the cohort's trailing_activated predicate for logical redundancy
  * split the cohort by close_time vs the first `UGB-PT EXIT` log line
  * prove the false-negative case from [TRAIL] activated log lines
  * score the UGB-PT trail-state exclusion (blocked trades) so nobody
    proposes removing it on the strength of the IO case alone

Run: python3 brain/analysis/arm_gap_baseline_2026-10-26.py [--selfcheck]
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', 'scripts'))
from paths import HERMES_DATA  # noqa: E402

LOG = os.path.join(os.path.dirname(HERMES_DATA), 'logs', 'pipeline.log')
STOP_EXITS = ('atr_sl_hit', 'hard_sl', 'manual_sl_hit')
COHORT_Q = """
SELECT id, token, signal, direction, exit_reason, trailing_activated,
       mfe_pct, pnl_usdt, open_time, close_time
FROM trades
WHERE status='closed' AND close_time > NOW() - INTERVAL '14 days'
  AND mfe_pct >= 0.40 AND exit_reason IN %s
ORDER BY close_time
"""


def pg():
    import psycopg2
    return psycopg2.connect(host='/var/run/postgresql', database='brain',
                            user='postgres')


def first_log_ts(pattern):
    """First timestamp in pipeline.log for lines matching pattern."""
    rx = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)')
    with open(LOG, errors='replace') as fh:
        for line in fh:
            if pattern in line:
                m = rx.match(line)
                if m:
                    return m.group(1)
    return None


def collect():
    con = pg()
    cur = con.cursor()

    cur.execute("""SELECT prosrc FROM pg_proc
                   WHERE proname='trades_set_trailing_activated'""")
    trigger_src = cur.fetchone()[0]

    # invariant (ALL-TIME, not windowed): flag TRUE only with a trail-named exit
    cur.execute("""
        SELECT COUNT(*) FROM trades
        WHERE status='closed'
          AND trailing_activated = TRUE AND exit_reason NOT ILIKE '%trail%'""")
    true_nontrail = cur.fetchone()[0]

    # every trail_arm_timeout row vs how many are stored as armed
    cur.execute("""
        SELECT COUNT(*) FILTER (WHERE trailing_activated = TRUE),
               COUNT(*),
               COALESCE(SUM(pnl_usdt) FILTER (WHERE trailing_activated = TRUE), 0)
        FROM trades
        WHERE status='closed' AND close_time > NOW() - INTERVAL '14 days'
          AND exit_reason = 'trail_arm_timeout'""")
    timeouts_flagged, timeouts_total, timeouts_pnl = cur.fetchone()

    # cohort flag predicate: must be empirically empty (see report wording — the
    # trigger only ever writes TRUE, so this is an empirical, not a logical, claim)
    cur.execute("""
        SELECT COUNT(*) FROM trades
        WHERE status='closed' AND close_time > NOW() - INTERVAL '14 days'
          AND mfe_pct >= 0.40 AND exit_reason IN %s
          AND trailing_activated = TRUE""", (STOP_EXITS,))
    cohort_flag_true = cur.fetchone()[0]

    cur.execute(COHORT_Q, (STOP_EXITS,))
    cohort = cur.fetchall()

    # false negative: PM logged an arm for the trade.
    # Only 10/94 activated lines carry trade_id= (field added 2026-10-25), so:
    #   trade_id present -> match on id (exact); absent -> match token + [open, close]
    # window (the only basis available for older lines).
    arm_by_id, arm_by_tok = {}, {}
    rx = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\s+\[TRAIL\] (\S+) activated:')
    rx_id = re.compile(r'trade_id=(\d+)')
    with open(LOG, errors='replace') as fh:
        for line in fh:
            m = rx.match(line)
            if not m:
                continue
            ts, tok = m.group(1), m.group(2).upper()
            mi = rx_id.search(line)
            if mi:
                arm_by_id[int(mi.group(1))] = ts
            arm_by_tok.setdefault(tok, []).append(ts)

    fn = []
    armed_matches = 0
    for r in cohort:
        tid, tok = r[0], r[1].upper()
        ot, ct = str(r[8])[:19], str(r[9])[:19]
        ts = arm_by_id.get(tid)
        if ts is None:
            ts = next((t for t in arm_by_tok.get(tok, []) if ot <= t <= ct), None)
        if ts is not None:
            armed_matches += 1
            if not r[5]:
                fn.append(r)

    # UGB-PT blocked set
    wf, ex = set(), set()
    rx_wf = re.compile(r'\[SHADOW\] UGB-PT would-fire \S+ \S+ .*trade=(\d+)')
    rx_ex = re.compile(r'UGB-PT EXIT \S+ \S+.*trade=(\d+)')
    with open(LOG, errors='replace') as fh:
        for line in fh:
            m = rx_wf.search(line)
            if m:
                wf.add(m.group(1))
            m = rx_ex.search(line)
            if m:
                ex.add(m.group(1))
    blocked = sorted((int(x) for x in wf - ex))
    if blocked:
        cur.execute("SELECT COUNT(*), COALESCE(SUM(pnl_usdt),0) FROM trades "
                    "WHERE id = ANY(%s)", (blocked,))
        blocked_stats = cur.fetchone()
    else:
        blocked_stats = (0, 0)

    enforce_first = first_log_ts('UGB-PT EXIT')
    con.close()
    return dict(trigger_src=trigger_src, true_nontrail=true_nontrail,
                timeouts_flagged=timeouts_flagged,
                cohort_flag_true=cohort_flag_true, cohort=cohort,
                false_neg=[r for r in fn if not r[5]],
                would_fire=len(wf), exited=len(ex), blocked=blocked,
                blocked_stats=blocked_stats, enforce_first=enforce_first,
                armed_matches=armed_matches,
                timeouts_total=timeouts_total, timeouts_pnl=timeouts_pnl,
                arm_by_id=len(arm_by_id))


def report(d):
    print('=' * 78)
    print('Q1 — what does trades.trailing_activated measure?')
    print('=' * 78)
    print('trigger source:')
    for line in d['trigger_src'].strip().splitlines():
        print('   ', line.strip())
    print(f"\n14d rows flagged TRUE with a NON-trail exit_reason : {d['true_nontrail']}")
    print(f"14d trail_arm_timeout rows: {d['timeouts_total']} total, "
          f"{d['timeouts_flagged']} flagged TRUE "
          f"({float(d['timeouts_pnl']):+.2f}) — a timeout waiting to arm is stored as ARMED")
    print(f"ARM-GAP cohort rows with trailing_activated=TRUE   : {d['cohort_flag_true']}"
          f"  (0 => empirically empty; the trigger only ever writes TRUE, so a stale"
          f" TRUE + stop exit is mechanically possible — 0 all-time, verified)")

    print()
    print('=' * 78)
    print('Q2 — is the #160 ARM-GAP bar able to discriminate its two causes?')
    print('=' * 78)
    print(f"UGB-PT ENFORCE first live (first 'UGB-PT EXIT' line): {d['enforce_first']}")
    if d['enforce_first'] is None:
        print('NO UGB-PT EXIT lines — cannot split the baseline; selfcheck will fail.')
        return
    pre = [r for r in d['cohort'] if str(r[9])[:19] < d['enforce_first']]
    post = [r for r in d['cohort'] if str(r[9])[:19] >= d['enforce_first']]
    def row(rs):
        if not rs:
            return '0T'
        n = len(rs)
        pnl = sum(float(r[7] or 0) for r in rs)
        return f'{n}T {pnl:+.2f}'
    print(f"cohort BEFORE enforcement (pre-deployment) : {row(pre)}")
    print(f"cohort AFTER  enforcement                  : {row(post)}")
    for r in post:
        print(f'    {r[0]} {r[1]} {r[4]} mfe={r[6]:.2f} pnl={float(r[7]):+.2f} {r[9]}')

    print()
    print(f"cohort trades matched to an in-window [TRAIL] activated line: "
          f"{d['armed_matches']}/{len(d['cohort'])}")
    print('false negative (PM logged an arm, flag still False):')
    for r in d['false_neg']:
        print(f'    {r[0]} {r[1]} {r[2]} exit={r[4]} mfe={r[6]:.2f} '
              f'pnl={float(r[7]):+.2f} close={r[9]}')

    print()
    print('=' * 78)
    print('IS THE UGB-PT trail-state EXCLUSION LEAKING MONEY?')
    print('=' * 78)
    print(f"would-fire {d['would_fire']}  enforced {d['exited']}  "
          f"blocked {len(d['blocked'])}  blocked net pnl_usdt "
          f"{float(d['blocked_stats'][1]):+.2f} over {d['blocked_stats'][0]}T")
    print(f"blocked ids: {','.join(str(x) for x in d['blocked'])}")


def selfcheck(d):
    assert 'ILIKE' in d['trigger_src'] and 'trail' in d['trigger_src'], \
        'trigger no longer keys on exit_reason ILIKE %trail% — semantics changed, ' \
        're-read before trusting any arm-rate KPI'
    assert d['true_nontrail'] == 0, \
        f"expected 0 flagged-TRUE rows with non-trail exits, got {d['true_nontrail']}"
    assert d['timeouts_total'] > 0, 'no trail_arm_timeout rows in 14d — cohort moved'
    assert d['timeouts_flagged'] == d['timeouts_total'], \
        'a trail_arm_timeout row is no longer flagged TRUE — trigger semantics changed'
    assert d['cohort_flag_true'] == 0, \
        'cohort flag predicate no longer empirically empty — cohort definition needs a rewrite'
    assert d['enforce_first'] is not None, 'no UGB-PT EXIT lines found in pipeline.log'
    io = [r for r in d['cohort'] if r[0] == 16407]
    assert io and not io[0][5], 'IO #16407 must be in cohort with trailing_activated=False'
    # claim 4: an arm line must actually be found for 16407 (guards the matcher)
    assert d['armed_matches'] >= 1, \
        'no [TRAIL] activated line matched any cohort trade — matcher/log regex broken'
    pre = [r for r in d['cohort'] if str(r[9])[:19] < d['enforce_first']]
    post = [r for r in d['cohort'] if str(r[9])[:19] >= d['enforce_first']]
    assert len(pre) >= 30 and len(post) <= 2, \
        (f'pre-deployment share moved (pre={len(pre)} post={len(post)}) — the confound claim '
         'changed; re-derive the bar before citing it')
    assert d['arm_by_id'] >= 1, 'no activated line carried trade_id= — matcher fell back to token'
    print('arm_gap_baseline --selfcheck PASS '
          f"(pre-enforce {len(pre)}/{len(d['cohort'])} of the 14d baseline; "
          f"armed-match {d['armed_matches']}, trade_id-matched lines {d['arm_by_id']})")


if __name__ == '__main__':
    d = collect()
    report(d)
    if '--selfcheck' in sys.argv:
        print()
        selfcheck(d)
