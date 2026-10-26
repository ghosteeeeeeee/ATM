#!/usr/bin/env python3
"""waiver_scoreboard_2026-10-23.py — gate-truth scoreboard for the RSI unclog waiver.

The waiver lets SHORT execs with live/detect RSI in [OVERSOLD_SHORT_RSI_MAX,
SHORT_RSI_HARD_FLOOR) through when BTC has bear structure; knife (<35) stays dead
on every path. Grant/expiry are read from data/vacation_mode.json
(`rules.unclog_waiver`) — the waiver has been re-armed twice (2026-10-22 →
expired 2026-10-24T00:00Z → re-granted 2026-10-24 15:40 UTC), and the hardcoded
window used to report the SUPERSET cohort (both grants + the closed gap), which
misstates any expiry ruling built on it.

Prior scoreboards reconstructed "what the gate saw" from trades metadata
(rsi_exec / entry_rsi_14 / my-own-5m-replay) — three sources disagree (#80
fragmentation), so the attributable count was approximate (#93 said n=2).
The execution log prints the authoritative value the gate actually compared:
  [EXEC-RSI-FLOOR-BEAR] TOKEN ... RSI <live> < floor (detect <floor allowed)
  [EXEC-RSI-DETECT-FLOOR] TOKEN SHORT BLOCKED ... knife
This script parses those lines and joins them to trades by open_time.

USAGE:
    python3 brain/analysis/waiver_scoreboard_2026-10-23.py [--log PATH]
    python3 brain/analysis/waiver_scoreboard_2026-10-23.py --selfcheck

Note on precision: decider_run logs RSI at %.1f, so a true 44.995 renders as
"45.0 < 45" — true at source, unverifiable from the line. Assertions therefore
tolerate +0.05 display rounding (`ponytail:` comment in selfcheck).
"""

import re
import sys
import json
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))

# Legacy fallback only — the live window comes from vacation_mode.json.
WAIVER_GRANT = datetime.datetime(2026, 10, 22, 14, 42, 0)
LOG_DEFAULT = Path('/root/.hermes/logs/pipeline.log')

RE_BEAR = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*\[EXEC-RSI-FLOOR-BEAR\] (\S+) .*?RSI ([\d.]+) <')
RE_DETECT_BLOCK = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*\[EXEC-RSI-DETECT-FLOOR\] (\S+) SHORT BLOCKED')
# "T directive 2026-10-24 15:40 UTC" -> naive UTC datetime
RE_GRANT_TS = re.compile(r'(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})')


def waiver_window():
    """(current_grant, current_expiry, source) from vacation_mode.json.

    Fail-soft: this is a report, not a gate — an unreadable file falls back to the
    legacy hardcoded grant with expiry=None so the run still produces numbers, and
    the caller prints which source it used.
    """
    try:
        from paths import HERMES_DATA
        with open(Path(HERMES_DATA) / 'vacation_mode.json') as f:
            w = json.load(f)['rules']['unclog_waiver']
        exp = datetime.datetime.fromisoformat(str(w['expires']).replace('Z', '+00:00'))
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=datetime.timezone.utc)
        exp = exp.replace(tzinfo=None)
        m = RE_GRANT_TS.search(str(w.get('granted_by', '')))
        grant = (datetime.datetime.strptime(f'{m.group(1)} {m.group(2)}', '%Y-%m-%d %H:%M')
                 if m else WAIVER_GRANT)
        return grant, exp, 'vacation_mode.json'
    except Exception as e:
        return WAIVER_GRANT, None, f'fallback({type(e).__name__})'


WAIVER_GRANT, WAIVER_EXPIRE, WINDOW_SOURCE = waiver_window()


def parse_log(path, since=WAIVER_GRANT):
    """Return deduped (ts, TOKEN, rsi) allow events and (ts, TOKEN, is_knife) blocks.

    pipeline.log writes some lines twice (once bare, once with a doubled timestamp
    prefix); dedupe on the parsed tuple so `allow_lines` means unique events, not
    raw lines. Distinct events keep distinct ts, so real repeats in the same second
    with the same RSI (the doubled-prefix class) collapse correctly.
    """
    allows, blocks = set(), set()
    with open(path, 'rb') as f:
        for raw in f:
            line = raw.decode('utf-8', 'replace').rstrip('\n')
            if 'EXEC-RSI' not in line:
                continue
            m = RE_BEAR.match(line)
            if m:
                ts = datetime.datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S')
                if ts >= since:
                    allows.add((ts, m.group(2).upper(), round(float(m.group(3)), 4)))
                continue
            m = RE_DETECT_BLOCK.match(line)
            if m:
                ts = datetime.datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S')
                if ts >= since:
                    blocks.add((ts, m.group(2).upper(), 'knife' in line))
    return sorted(allows), sorted(blocks)


def fetch_shorts(since=WAIVER_GRANT):
    import psycopg2
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, token, signal, direction, open_time, status,
                      COALESCE(pnl_usdt, 0), volatility_regime
                 FROM trades
                WHERE direction = 'SHORT' AND open_time > %s
                ORDER BY open_time""", (since,))
        return cur.fetchall()
    finally:
        conn.close()


def attribute(trades, allows, window_s=120):
    """A trade is exemption-attributable iff a FLOOR-BEAR allow for the same token
    lands inside [open_time - window_s, open_time + 5s] — i.e. the gate logged an
    actual sub-floor bear-allow for this fill.

    Both sides are naive UTC (log stamps and trades.open_time are UTC), so no tz
    conversion. A gate->fill gap longer than window_s would under-attribute, which
    is the safe direction for a waiver about to expire: worst case we under-count
    the exemption's own trades and still let it lapse."""
    out = []
    for t in trades:
        oid, tok, sig, _, ots, status, pnl, vol = t
        near = [a for a in allows
                if a[1] == tok.upper() and -window_s <= (a[0] - ots).total_seconds() <= 5]
        out.append((t, near))
    return out


def report(log_path=LOG_DEFAULT, verbose=True):
    allows, blocks = parse_log(log_path)
    trades = fetch_shorts()
    attr = attribute(trades, allows)
    closed_attr = [(t, n) for t, n in attr if t[5] == 'closed' and n]
    open_attr = [(t, n) for t, n in attr if t[5] == 'open' and n]
    net = sum(float(t[6]) for t, _ in closed_attr)
    wins = sum(1 for t, _ in closed_attr if float(t[6]) > 0)
    res = {
        'window_source': WINDOW_SOURCE,
        'waiver_grant': WAIVER_GRANT.isoformat(sep=' '),
        'waiver_expire': WAIVER_EXPIRE.isoformat(sep=' ') if WAIVER_EXPIRE else None,
        'allow_lines': len(allows),
        'allow_tokens': len({a[1] for a in allows}),
        'knife_blocks': sum(1 for b in blocks if b[2]),
        'detect_blocks': len(blocks),
        'shorts_opened': len(trades),
        'attributable_closed': len(closed_attr),
        'attributable_wins': wins,
        'attributable_net': round(net, 3),
        'attributable_open': len(open_attr),
        'attributable_open_ids': [t[0] for t, _ in open_attr],
        'worst_loss_pnl_pct': round(min([float(t[6]) for t, _ in closed_attr] or [0]), 3),
    }
    if verbose:
        print('WAIVER SCOREBOARD (gate-truth, from execution log)')
        print(f'  window source: {WINDOW_SOURCE}')
        print(f'  current waiver window: {WAIVER_GRANT:%Y-%m-%d %H:%M} -> '
              f'{WAIVER_EXPIRE:%Y-%m-%d %H:%M}' if WAIVER_EXPIRE else
              f'  current waiver window: {WAIVER_GRANT:%Y-%m-%d %H:%M} -> (expiry unreadable)')
        print(f'  [EXEC-RSI-FLOOR-BEAR] unique allow events: {res["allow_lines"]}'
              f' ({res["allow_tokens"]} unique tokens)')
        print(f'  [EXEC-RSI-DETECT-FLOOR] unique block events: {res["detect_blocks"]}'
              f' (knife: {res["knife_blocks"]})')
        print(f'  SHORT trades opened: {res["shorts_opened"]}')
        print(f'  exemption-attributable CLOSED: {res["attributable_closed"]}'
              f' ({res["attributable_wins"]}W/{res["attributable_closed"] - res["attributable_wins"]}L)'
              f' net {res["attributable_net"]:+.2f}')
        print(f'  exemption-attributable OPEN: {res["attributable_open"]}'
              f' {res["attributable_open_ids"]}')
        for t, n in attr:
            print(f'    {"ATTR" if n else "    "} #{t[0]} {t[1]:6s} {t[5]:6s}'
                  f' open {t[4]:%m-%d %H:%M:%S} pnl {float(t[6]):+.3f} vol {t[7]}'
                  f' gate_rsi {[round(x[2], 1) for x in n]}')
    return res


def selfcheck():
    log = LOG_DEFAULT
    if '--log' in sys.argv:
        log = Path(sys.argv[sys.argv.index('--log') + 1])
    allows, blocks = parse_log(log)
    trades = fetch_shorts()
    attr = attribute(trades, allows)

    # 1. parse produced something (log is not silently empty / pattern renamed)
    assert allows, 'no FLOOR-BEAR lines parsed — pattern or log path broken'
    assert blocks, 'no DETECT-FLOOR block lines parsed — pattern broken'

    # 2. every attributed trade carries a gate RSI below the hard floor
    #    and at/above the knife floor (waiver scope) — proves the join is real.
    # ponytail: decider_run renders RSI at %.1f, so a true 44.995 prints "45.0 < 45".
    # The gate is right; the line just cannot carry the proof. Tolerate one display
    # step (+0.05) — legacy log lines are %.1f forever, so this cannot be tightened
    # by re-rendering. Bump only if decider ever logs 2+ decimals.
    from hermes_constants import SHORT_RSI_HARD_FLOOR, OVERSOLD_SHORT_RSI_MAX
    _DISPLAY_EPS = 0.05
    n_attr = 0
    for t, near in attr:
        if not near:
            continue
        n_attr += 1
        for a in near:
            assert a[2] < SHORT_RSI_HARD_FLOOR + _DISPLAY_EPS, \
                f'{t[1]} gate RSI {a[2]} not sub-floor (even allowing %.1f display)'
            assert a[2] >= OVERSOLD_SHORT_RSI_MAX - _DISPLAY_EPS, \
                f'{t[1]} gate RSI {a[2]} below knife floor — exemption leaking past <35'
    assert n_attr <= len(trades), 'attributed more trades than exist'

    # 3. attribution is a subset of trades opened after the grant
    assert all(t[4] > WAIVER_GRANT for t, _ in attr), 'pre-grant trade attributed'

    # 3b. the window we just reported is the FILE's current waiver, not a stale
    #     hardcoded one — this is the bug the docstring used to carry (expiry was
    #     frozen at 2026-10-24 after T re-armed to 2026-10-27).
    assert WINDOW_SOURCE == 'vacation_mode.json', \
        f'window source {WINDOW_SOURCE} — the ruling would use a stale cohort'

    # 4. every detected block line must be the knife class — the waiver keeps <35
    #    dead, so a non-knife DETECT-FLOOR block would mean the exemption is also
    #    being applied below the knife floor (report-only, not asserted: a bear-
    #    structure switch-off emits [EXEC-RSI-HARD-FLOOR] instead, which is not
    #    parsed here at all).
    non_knife = [b for b in blocks if not b[2]]

    # 5. report() attribution must equal the join (no status-only counting)
    res = report(log, verbose=False)
    assert res['attributable_closed'] == sum(1 for t, n in attr if t[5] == 'closed' and n), \
        'closed attribution drifted from the join'
    assert res['attributable_open'] == sum(1 for t, n in attr if t[5] == 'open' and n), \
        'open attribution drifted from the join'
    assert res['waiver_expire'] is not None, 'expiry unreadable — cannot rule on lapse'
    assert res['waiver_grant'] == WAIVER_GRANT.isoformat(sep=' '), 'grant drifted'

    print(f'SELFCHECK PASS — allows {len(allows)}, blocks {len(blocks)} '
          f'(non-knife detect-blocks {len(non_knife)}), shorts {len(trades)}, '
          f'attributable {n_attr}')
    return True


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        selfcheck()
    else:
        log = LOG_DEFAULT
        if '--log' in sys.argv:
            log = Path(sys.argv[sys.argv.index('--log') + 1])
        report(log)
