#!/usr/bin/env python3
"""shadow_tag_join.py — join-builder for the 5 SHORT-side shadow log tags.

Registry: data/shadow_disposition.json id `short-shadow-join-builder`
(pulled forward to deadline 2026-11-08 — must EXIST before the 2026-11-10
bear-single-source flip read).  LOG/ANALYTICS ONLY: reads pipeline.log and
data/candles.db, writes one JSON artifact.  Zero code in the live trading
path (same freeze-safe standalone pattern as gate_shadow.py / expiry_shadow.py).

What it does, per tag (TOKEN-DAY DEDUP first — registry
`gate-shadow-dedup-convention`: event n is 7-10x pseudo-replicated, so raw
line counts are NEVER quoted as evidence):

  1. parse `logs/pipeline.log` lines carrying the tag, tolerantly —
     the real formats vary per tag (see _SAMPLE_LINES / selfcheck):
       👁️ [SHORT-REGIME-EXEMPT-SHADOW] ETH SHORT jup_yolo_short: WOULD-PASS —
          conf=74 vol_regime=NORMAL regime_4h=SHORT_BIAS (min_conf=60) → ...
       👁️ [FLIP1-OVERRIDE-SHADOW] DOT SHORT WOULD-ALLOW — rsi=35.71 < 45 but ...
       👁️ [BEAR-SINGLE-SOURCE-SHADOW] WLD SHORT WOULD-PASS — source=rs-r72
          conf=88.0 regime_4h=SHORT_BIAS single-type need-2+ ...
       👁️ [VOLGATE-SHORT-EXEMPT-SHADOW] {token} {direction} WOULD-PASS — ...
       👁️ [MAXXED-SHORT-EXEMPT-SHADOW] {token} {direction} WOULD-PASS — ...
     Common skeleton after the tag: `<TOKEN> <LONG|SHORT>` (+ optional
     `<signal_type>:`); everything else (source/conf/regime_4h) is optional.
  2. dedup on tag|token|direction|UTC-day, KEEP EARLIEST (one tok-day per key).
  3. join to outcome with THE standard engine — identical to
     scripts/expiry_shadow.py::_fwd_metrics and scripts/gate_shadow.py::_fwd_4h:
       entry  = OPEN of the first CLOSED 5m candle with ts >= log timestamp
       sgn    = +1 LONG / -1 SHORT
       fwd4h  = sgn * (close[i+48] / open[i] - 1) * 100
       guard  = i + 48 >= len(rows)  ->  not joinable (no lookahead)
  4. per-tag table (n tok-days, joinable n, would-have-won WR, avg fwd,
     $ at $13.44 notional, net after 0.09% RT fee) + a BAR VERDICT against the
     registry threshold of that tag's own registry entry.
  5. writes data/shadow_tag_join_latest.json.

BEAR-SINGLE-SOURCE member filter: NONE by design.  The registry entry
`btc-standalone-deny-shadow` documents the retro-derivable member filter for
THAT stream; for bear-single-source the counterfactual IS "single-type passes
the need-2+ gate", so every parsed line counts (source/conf are parsed only as
context).  See registry `bear-single-source-shadow`.

Usage:
  python3 scripts/shadow_tag_join.py                 # full run + JSON artifact
  python3 scripts/shadow_tag_join.py --selfcheck     # fixtures, PASS/FAIL exit
  python3 scripts/shadow_tag_join.py --tag BEAR-SINGLE-SOURCE-SHADOW
"""
import argparse
import calendar
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, HERMES_LOG_DIR

LOG_PATH = os.path.join(HERMES_LOG_DIR, 'pipeline.log')
CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
OUT_JSON = os.path.join(HERMES_DATA, 'shadow_tag_join_latest.json')

# ── the 5 shadow tags this registry entry covers ──────────────────────────────
TAGS = (
    'SHORT-REGIME-EXEMPT-SHADOW',
    'FLIP1-OVERRIDE-SHADOW',
    'BEAR-SINGLE-SOURCE-SHADOW',
    'VOLGATE-SHORT-EXEMPT-SHADOW',
    'MAXXED-SHORT-EXEMPT-SHADOW',
)

# $-basis: live 30d avg PG notional at read time was $13.44 (the same basis the
# bear-single-source pre-read used).  RT fee = 0.09% round-trip per simulated fill.
NOTIONAL = 13.44
RT_FEE = 0.0009
FWD_HORIZON = 48  # 48 x 5m = 4h — mirror of gate_shadow.FWD_HORIZON_CANDLES

# ── parsing ───────────────────────────────────────────────────────────────────
TS_RE = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
# Common skeleton right after the tag: TOKEN DIRECTION, optionally followed by
# `signal_type:` (present on the SHORT-REGIME form, absent on FLIP1/VOLGATE/
# MAXXED/BEAR).  Deliberately tolerant: anything we cannot skeleton-parse is
# counted as `unparsed` and reported, never silently dropped.
AFTER_TAG_RE = re.compile(
    r'\s+([A-Za-z0-9]+)\s+(LONG|SHORT)\b(?:\s+([A-Za-z0-9_+-]+)\s*:\s*)?'
)
SOURCE_RE = re.compile(r'\bsource=([^\s,)]+)')
CONF_RE = re.compile(r'\bconf=([0-9]*\.?[0-9]+)')
REGIME_RE = re.compile(r'\bregime_4h=([A-Za-z0-9_]+)')

# Real log lines (sampled from logs/pipeline.log 2026-11-03..11-06) — used by
# --selfcheck as parser fixtures.
_SAMPLE_LINES = {
    'SHORT-REGIME-EXEMPT-SHADOW':
        '2026-11-03 14:39:02   \U0001f441️ [SHORT-REGIME-EXEMPT-SHADOW] ETH SHORT '
        'jup_yolo_short: WOULD-PASS — conf=74 vol_regime=NORMAL regime_4h=SHORT_BIAS '
        '(min_conf=60) → mult 0.85 WOULD be restored on enforce; kill stays '
        '(ENFORCE=False)',
    'FLIP1-OVERRIDE-SHADOW':
        '2026-11-04 03:10:03   \U0001f441️ [FLIP1-OVERRIDE-SHADOW] DOT SHORT '
        'WOULD-ALLOW — rsi=35.71 < 45 but BTC-bear structure (linreg=BEAR, age=1s<600) '
        'and flip1_active()=False (waiver expired); shadow only, stays blocked',
    'BEAR-SINGLE-SOURCE-SHADOW':
        '2026-11-06 05:41:00   \U0001f441️ [BEAR-SINGLE-SOURCE-SHADOW] CAKE SHORT '
        'WOULD-PASS — source=rs-r41 conf=88.0 regime_4h=SHORT_BIAS single-type need-2+ '
        '(pass_gate stays False, ENFORCE=False)',
    'VOLGATE-SHORT-EXEMPT-SHADOW':
        '2026-11-06 05:41:00   \U0001f441️ [VOLGATE-SHORT-EXEMPT-SHADOW] WLD SHORT '
        "WOULD-PASS — vol-gate 0.0 for 'pump-chain-' in EXTREME, regime_4h=BEAR "
        '(block stays, ENFORCE=False)',
    'MAXXED-SHORT-EXEMPT-SHADOW':
        '2026-11-06 05:41:00   \U0001f441️ [MAXXED-SHORT-EXEMPT-SHADOW] HYPE SHORT '
        'WOULD-PASS — ATR%=6.42 >= 6.0 maxxed tier, regime_4h=SHORT_BIAS '
        '(block stays, ENFORCE=False)',
}


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [shadow_tag_join] {msg}', flush=True)


def parse_line(line, tag):
    """-> dict event or None.  Tolerant of every real format variant."""
    m_ts = TS_RE.match(line)
    if not m_ts:
        return None
    marker = f'[{tag}]'
    idx = line.find(marker)
    if idx < 0:
        return None
    tail = line[idx + len(marker):]
    m_body = AFTER_TAG_RE.match(tail)
    if not m_body:
        return {'ts': m_ts.group(1), 'tag': tag, 'token': None, 'direction': None,
                'parsed': False}
    src = SOURCE_RE.search(line)
    conf = CONF_RE.search(line)
    reg = REGIME_RE.search(line)
    return {
        'ts': m_ts.group(1),
        'tag': tag,
        'token': m_body.group(1).upper(),
        'direction': m_body.group(2).upper(),
        'signal_type': m_body.group(3),
        'source': src.group(1) if src else None,
        'conf': float(conf.group(1)) if conf else None,
        'regime_4h': reg.group(1) if reg else None,
        'parsed': True,
        'day': m_ts.group(1)[:10],
    }


def collect_events(lines, tags=TAGS):
    """Parse + TOKEN-DAY DEDUP (tag|token|direction|UTC-day, keep earliest).

    Returns (events, stats) where stats[tag] = {'raw_lines', 'unparsed'}.
    """
    stats = {t: {'raw_lines': 0, 'unparsed': 0} for t in tags}
    picked = {}  # key -> event (earliest wins)
    for line in lines:
        for tag in tags:
            if f'[{tag}]' not in line:
                continue
            stats[tag]['raw_lines'] += 1
            ev = parse_line(line, tag)
            if ev is None:
                continue
            if not ev['parsed']:
                stats[tag]['unparsed'] += 1
                continue
            key = (ev['tag'], ev['token'], ev['direction'], ev['day'])
            prev = picked.get(key)
            if prev is None or ev['ts'] < prev['ts']:
                picked[key] = ev
            break  # a line belongs to at most one tag
    events = sorted(picked.values(), key=lambda e: (e['ts'], e['token']))
    return events, stats


# ── forward-return engine (verbatim mirror of gate_shadow._fwd_4h) ───────────
def fwd_4h(rows, entry_ts, direction):
    """fwd 4h %, direction-signed.  Entry = OPEN of the first CLOSED 5m candle
    with ts >= entry_ts (no lookahead); needs the +48th candle; sgn = +1 LONG /
    -1 SHORT.  Returns None when the horizon is not in the candle data."""
    lo, hi = 0, len(rows)
    while lo < hi:
        mid = (lo + hi) // 2
        if rows[mid][0] < entry_ts:
            lo = mid + 1
        else:
            hi = mid
    i = lo
    if i + FWD_HORIZON >= len(rows):
        return None
    o = rows[i][1]
    if not o:
        return None
    sgn = 1 if direction == 'LONG' else -1
    return sgn * (rows[i + FWD_HORIZON][2] / o - 1.0) * 100.0


_CANDLE_CACHE = {}


def load_candles(token, db_path=CANDLES_DB):
    token = (token or '').upper()
    if token in _CANDLE_CACHE:
        return _CANDLE_CACHE[token]
    rows = []
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        try:
            rows = conn.execute(
                "SELECT ts, open, close FROM candles_5m"
                " WHERE token=? AND is_closed=1 ORDER BY ts", (token,)).fetchall()
        finally:
            conn.close()
    except sqlite3.Error as e:
        log(f'candles read failed for {token}: {e}')
    _CANDLE_CACHE[token] = rows
    return rows


def entry_ts_of(ts):
    """'YYYY-MM-DD HH:MM:SS' (log line, UTC) -> epoch seconds (same
    calendar.timegm conversion as expiry_shadow.close_events / gate_shadow.close_fwd)."""
    return calendar.timegm(datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').utctimetuple())


def join_events(events, candle_loader=load_candles):
    """Attach fwd_4h (or a skip reason) to every event, in place."""
    for ev in events:
        ev['fwd_4h'] = None
        ev['join_reason'] = None
        if not ev['parsed']:
            ev['join_reason'] = 'unparsed'
            continue
        rows = candle_loader(ev['token'])
        if not rows:
            ev['join_reason'] = 'no_candles'
            continue
        f = fwd_4h(rows, entry_ts_of(ev['ts']), ev['direction'])
        if f is None:
            ev['join_reason'] = 'horizon_immature'
            continue
        ev['fwd_4h'] = f
        ev['join_reason'] = 'joined'


# ── aggregation ───────────────────────────────────────────────────────────────
def aggregate(events, tag):
    evs = [e for e in events if e['tag'] == tag]
    joined = [e for e in evs if e['join_reason'] == 'joined']
    reasons = {}
    for e in evs:
        if e['join_reason'] != 'joined':
            reasons[e['join_reason']] = reasons.get(e['join_reason'], 0) + 1
    n = len(joined)
    wins = sum(1 for e in joined if e['fwd_4h'] > 0)
    ties = sum(1 for e in joined if e['fwd_4h'] == 0)
    fwd_sum = sum(e['fwd_4h'] for e in joined)
    gross = fwd_sum / 100.0 * NOTIONAL
    fee = n * NOTIONAL * RT_FEE
    net = gross - fee

    # per-UTC-day net (positive-day limb of the short-regime / volgate bars)
    day_net = {}
    day_n = {}
    for e in joined:
        day_net[e['day']] = day_net.get(e['day'], 0.0) + e['fwd_4h'] / 100.0 * NOTIONAL
        day_n[e['day']] = day_n.get(e['day'], 0) + 1
    for d in day_net:
        day_net[d] -= day_n[d] * NOTIONAL * RT_FEE
    days = sorted(day_net)
    days_pos = sum(1 for d in days if day_net[d] > 0)

    # leave-one-out: worst net with any single tok-day removed (flip1 limb)
    loo_min = None
    if n >= 1:
        contrib = [e['fwd_4h'] / 100.0 * NOTIONAL - NOTIONAL * RT_FEE for e in joined]
        loo_min = min(net - c for c in contrib)

    return {
        'registry_id': TAG_REGISTRY_ID.get(tag),
        'raw_lines': RAW_STATS.get(tag, {}).get('raw_lines', 0),
        'unparsed_lines': RAW_STATS.get(tag, {}).get('unparsed', 0),
        'n_token_days': len(evs),
        'n_joinable': n,
        'n_wins': wins,
        'n_ties': ties,
        'skipped': reasons,
        'wr_pct': round(wins / n * 100.0, 1) if n else None,
        'avg_fwd_pct': round(fwd_sum / n, 4) if n else None,
        'fwd_sum_pct': round(fwd_sum, 4),
        'gross_usd': round(gross, 4),
        'fee_usd': round(fee, 4),
        'net_usd': round(net, 4),
        'days_total': len(days),
        'days_positive': days_pos,
        'pos_day_ratio': round(days_pos / len(days), 4) if days else None,
        'day_net_usd': {d: round(day_net[d], 4) for d in days},
        'loo_min_net_usd': round(loo_min, 4) if loo_min is not None else None,
    }


TAG_REGISTRY_ID = {
    'SHORT-REGIME-EXEMPT-SHADOW': 'short-regime-exempt-shadow',
    'FLIP1-OVERRIDE-SHADOW': 'flip1-bear-override-reshadow',
    'BEAR-SINGLE-SOURCE-SHADOW': 'bear-single-source-shadow',
    'VOLGATE-SHORT-EXEMPT-SHADOW': 'volgate-short-exempt-shadow',
    'MAXXED-SHORT-EXEMPT-SHADOW': 'maxxed-short-exempt-shadow',
}
RAW_STATS = {}

# ── registry bars (verbatim from each entry's `threshold`) ────────────────────
BAR_TEXT = {
    'BEAR-SINGLE-SOURCE-SHADOW':
        'n>=20 joinable tokdays AND WR>=55% AND net>=$1.00 '
        '(enforce flip read 2026-11-10)',
    'SHORT-REGIME-EXEMPT-SHADOW':
        'n>=15 joinable AND net>=$0.50 AND >=2/3 positive days',
    'FLIP1-OVERRIDE-SHADOW':
        'n>=20 joinable AND net>=$1.00 AND leave-one-out positive',
    'VOLGATE-SHORT-EXEMPT-SHADOW':
        'n>=100 joinable tokdays AND avg fwd>=+0.15 AND >=2/3 positive days',
    'MAXXED-SHORT-EXEMPT-SHADOW': 'n>=20 joinable tokdays',
}


def eval_bar(tag, m):
    """-> (met, [ {limb, need, have, pass} ... ]).  n = JOINABLE token-days
    (the strictest reading — a bar about simulated fills cannot count rows with
    no outcome)."""
    limbs = []

    def add(limb, need, have, ok):
        limbs.append({'limb': limb, 'need': need, 'have': have, 'pass': bool(ok)})

    n = m['n_joinable']
    if tag == 'BEAR-SINGLE-SOURCE-SHADOW':
        add('n_joinable >= 20', 20, n, n >= 20)
        wr = m['wr_pct']
        add('WR >= 55%', '55%', f'{wr}%' if wr is not None else 'n/a',
            wr is not None and wr >= 55.0)
        add('net >= +$1.00', 1.0, m['net_usd'], (m['net_usd'] or 0) >= 1.0)
    elif tag == 'SHORT-REGIME-EXEMPT-SHADOW':
        add('n_joinable >= 15', 15, n, n >= 15)
        add('net >= +$0.50', 0.5, m['net_usd'], (m['net_usd'] or 0) >= 0.5)
        add('>=2/3 positive days', '0.6667', m['pos_day_ratio'],
            m['pos_day_ratio'] is not None and m['pos_day_ratio'] >= 2.0 / 3.0)
    elif tag == 'FLIP1-OVERRIDE-SHADOW':
        add('n_joinable >= 20', 20, n, n >= 20)
        add('net >= +$1.00', 1.0, m['net_usd'], (m['net_usd'] or 0) >= 1.0)
        loo = m['loo_min_net_usd']
        add('leave-one-out net > 0', '>0.00', loo, loo is not None and loo > 0)
    elif tag == 'VOLGATE-SHORT-EXEMPT-SHADOW':
        add('n_joinable >= 100', 100, n, n >= 100)
        add('avg fwd >= +0.15%', 0.15, m['avg_fwd_pct'],
            m['avg_fwd_pct'] is not None and m['avg_fwd_pct'] >= 0.15)
        add('>=2/3 positive days', '0.6667', m['pos_day_ratio'],
            m['pos_day_ratio'] is not None and m['pos_day_ratio'] >= 2.0 / 3.0)
    elif tag == 'MAXXED-SHORT-EXEMPT-SHADOW':
        add('n_joinable >= 20', 20, n, n >= 20)
    return all(l['pass'] for l in limbs), limbs


def _fmt(v, spec, na='n/a'):
    return na if v is None else format(v, spec)


def print_table(metrics, tags=TAGS):
    hdr = (f'{"tag":32} {"raw":>6} {"tokday":>7} {"join":>6} {"WR%":>6} '
           f'{"avgfwd":>9} {"gross$":>8} {"fee$":>7} {"net$":>8} '
           f'{"days+":>6} {"LOO$":>8}  verdict')
    log('─── SHADOW TAG JOIN — token-day deduped (gate-shadow-dedup-convention) ───')
    log(f'  fwd_4h = sgn*(close[i+48]/open[i]-1)*100, entry = OPEN of first closed 5m'
        f' candle with ts >= log ts; $ basis = ${NOTIONAL} notional, {RT_FEE*100:.2f}% RT fee')
    log(hdr)
    log('-' * len(hdr))
    for tag in tags:
        m = metrics[tag]
        met, limbs = eval_bar(tag, m)
        dpos = (f"{m['days_positive']}/{m['days_total']}"
                if m['days_total'] else '0/0')
        row = (
            f"{tag:32} {m['raw_lines']:6d} {m['n_token_days']:7d} "
            f"{m['n_joinable']:6d} "
            f"{_fmt(m['wr_pct'], '.1f'):>6} "
            f"{_fmt(m['avg_fwd_pct'], '+.4f'):>9} "
            f"{m['gross_usd']:8.3f} {m['fee_usd']:7.3f} {m['net_usd']:8.3f} "
            f"{dpos:>6} "
            f"{_fmt(m['loo_min_net_usd'], '+.3f'):>8}  "
            f"{'BAR MET' if met else 'bar not met'}"
        )
        log(row)
        for l in limbs:
            log(f"    {'PASS' if l['pass'] else 'FAIL'}  {l['limb']:34}"
                f" need {l['need']}  have {l['have']}")
        if m['skipped']:
            log(f"    skipped: {m['skipped']}")


# ── selfcheck ─────────────────────────────────────────────────────────────────
def _synth_rows():
    """60 closed 5m candles, 300s apart, aligned so the fixture log timestamp
    ('2026-11-06 05:41:00') lands exactly on rows[10] (i=10, i+48=58).
    candle k: open=100.0, close=100.0, except rows[58].close=95.0 ->
    SHORT fwd = -1 * (95/100 - 1) * 100 = +5.000%, LONG fwd = -5.000%."""
    entry = calendar.timegm(
        datetime.strptime('2026-11-06 05:41:00', '%Y-%m-%d %H:%M:%S').utctimetuple())
    base = entry - 10 * 300
    rows = [(base + k * 300, 100.0, 100.0) for k in range(60)]
    rows[58] = (base + 58 * 300, 100.0, 95.0)
    return base, rows


def selfcheck():
    ok = True

    def chk(cond, name):
        nonlocal ok
        print(('PASS  ' if cond else 'FAIL  ') + name, flush=True)
        ok = ok and bool(cond)

    # 1) parser fixtures — one REAL line per tag (3+ lines of each were sampled
    #    from logs/pipeline.log while building this; these are the shapes).
    exp = {
        'SHORT-REGIME-EXEMPT-SHADOW': ('ETH', 'SHORT', 'jup_yolo_short'),
        'FLIP1-OVERRIDE-SHADOW': ('DOT', 'SHORT', None),
        'BEAR-SINGLE-SOURCE-SHADOW': ('CAKE', 'SHORT', None),
        'VOLGATE-SHORT-EXEMPT-SHADOW': ('WLD', 'SHORT', None),
        'MAXXED-SHORT-EXEMPT-SHADOW': ('HYPE', 'SHORT', None),
    }
    for tag, (tok, direc, sig) in exp.items():
        ev = parse_line(_SAMPLE_LINES[tag], tag)
        chk(ev is not None and ev['parsed']
            and ev['token'] == tok and ev['direction'] == direc
            and ev['signal_type'] == sig
            and re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', ev['ts'] or ''),
            f'parse {tag} -> {tok} {direc} sig={sig}')
    # optional fields where the line carries them
    ev = parse_line(_SAMPLE_LINES['BEAR-SINGLE-SOURCE-SHADOW'],
                    'BEAR-SINGLE-SOURCE-SHADOW')
    chk(ev['source'] == 'rs-r41' and ev['conf'] == 88.0
        and ev['regime_4h'] == 'SHORT_BIAS', 'bear line carries source/conf/regime')
    # a line WITHOUT the tag must not parse
    chk(parse_line('2026-11-06 05:41:00   👁️ [SOME-OTHER-TAG] XX SHORT', 'BEAR-SINGLE-SOURCE-SHADOW')
        is None, 'foreign tag line rejected')

    # 2) TOKEN-DAY DEDUP: same tag|token|direction|day x3 -> 1, earliest kept;
    #    a second UTC day, a second direction and a second tag all survive.
    bear = _SAMPLE_LINES['BEAR-SINGLE-SOURCE-SHADOW']
    fixture_lines = [
        bear,
        bear.replace('05:41:00', '05:42:00'),
        bear.replace('05:41:00', '05:43:00'),
        # next UTC day, same token+direction -> a SEPARATE token-day
        bear.replace('2026-11-06', '2026-11-07'),
        # same day, opposite direction -> separate key
        bear.replace(' CAKE SHORT ', ' CAKE LONG '),
        _SAMPLE_LINES['MAXXED-SHORT-EXEMPT-SHADOW'],
    ]
    evs, stats = collect_events(fixture_lines)
    bear_evs = [e for e in evs if e['tag'] == 'BEAR-SINGLE-SOURCE-SHADOW']
    chk(len(bear_evs) == 3, f'dedup 3 same-day lines -> 1 (got {len(bear_evs)} keys)')
    chk(bear_evs and bear_evs[0]['ts'] == '2026-11-06 05:41:00', 'earliest ts kept')
    chk(len({(e['day'], e['direction']) for e in bear_evs}) == len(bear_evs),
        'direction/day are part of the dedup key')
    chk(stats['BEAR-SINGLE-SOURCE-SHADOW']['raw_lines'] == 5,
        f"raw line count not deduped (got {stats['BEAR-SINGLE-SOURCE-SHADOW']['raw_lines']})")

    # 3) fwd engine correctness + NO LOOKAHEAD
    base, rows = _synth_rows()
    i = 10
    f_long = fwd_4h(rows, base + i * 300, 'LONG')
    chk(f_long is not None and abs(f_long + 5.0) < 1e-9,
        f'fwd LONG = -5.000% (close[i+48]=95 < open[i]=100) (got {f_long})')
    f_short = fwd_4h(rows, base + i * 300, 'SHORT')
    chk(f_short is not None and abs(f_short - 5.0) < 1e-9,
        f'fwd SHORT = +5.000% (sgn=-1) (got {f_short})')

    # entry = FIRST candle with ts >= entry_ts (1s later moves the entry)
    f_next = fwd_4h(rows, base + i * 300 + 1, 'LONG')
    chk(f_next is not None and abs(f_next) < 1e-9,
        f'entry +1s -> next candle (flat) (got {f_next})')

    # no lookahead: mutating candles BEFORE entry and AFTER the +48 horizon
    # cannot move the result; mutating the entry open or the +48 close can.
    mutated = list(rows)
    mutated[0] = (mutated[0][0], 1.0, 999.0)
    mutated[9] = (mutated[9][0], 1.0, 999.0)
    mutated[59] = (mutated[59][0], 1.0, 999.0)
    chk(fwd_4h(mutated, base + i * 300, 'LONG') == f_long,
        'candles outside [entry, entry+48] cannot change the result (no lookahead)')
    mutated2 = list(rows)
    mutated2[10] = (mutated2[10][0], 50.0, 50.0)
    chk(fwd_4h(mutated2, base + i * 300, 'LONG') != f_long,
        'entry OPEN does change the result (engine reads open[i])')
    mutated3 = list(rows)
    mutated3[58] = (mutated3[58][0], 100.0, 110.0)
    chk(fwd_4h(mutated3, base + i * 300, 'LONG') != f_long,
        'close[i+48] does change the result (engine reads close[i+48])')

    # i+48 bounds guard
    chk(fwd_4h(rows, base + 12 * 300, 'LONG') is None,
        'i+48 beyond series -> None (bounds guard, never a partial window)')
    chk(fwd_4h([], base, 'LONG') is None, 'empty candle series -> None')
    zero = list(rows)
    zero[10] = (zero[10][0], 0.0, 0.0)
    chk(fwd_4h(zero, base + i * 300, 'LONG') is None, 'zero open -> None (div guard)')

    # 4) end-to-end join on fixtures with a stubbed candle loader.
    #    join_lines: same-day bear SHORT (joinable, +5.000%), next-UTC-day bear
    #    SHORT (series too short -> horizon_immature), and a MAXXED line for a
    #    token the stub has no candles for (-> no_candles).
    bear = _SAMPLE_LINES['BEAR-SINGLE-SOURCE-SHADOW']
    join_lines = [
        bear,
        bear.replace('2026-11-06', '2026-11-07'),
        _SAMPLE_LINES['MAXXED-SHORT-EXEMPT-SHADOW'],
    ]

    def stub_loader(token):
        return rows if token == 'CAKE' else []

    evs2, _ = collect_events(join_lines)
    join_events(evs2, candle_loader=stub_loader)
    joined = [e for e in evs2 if e['join_reason'] == 'joined']
    reasons = {e['token'] + '/' + e['day']: e['join_reason'] for e in evs2}
    chk(len(joined) == 1 and reasons.get('CAKE/2026-11-07') == 'horizon_immature'
        and reasons.get('HYPE/2026-11-06') == 'no_candles',
        f'join reasons per event ({reasons})')
    chk(joined and abs(joined[0]['fwd_4h'] - 5.0) < 1e-9,
        'joined row carries fwd_4h from the stub series')

    # 5) aggregation + bar limbs on the stub
    m = aggregate(evs2, 'BEAR-SINGLE-SOURCE-SHADOW')
    chk(m['n_token_days'] == 2 and m['n_joinable'] == 1,
        f"aggregate counts (tokday={m['n_token_days']}, join={m['n_joinable']})")
    chk(m['days_total'] == 1 and m['days_positive'] == 1,
        f"per-day net computed ({m['days_positive']}/{m['days_total']} positive)")
    chk(abs(m['gross_usd'] - (5.0 / 100.0 * NOTIONAL)) < 1e-9,
        f"gross$ = sum(fwd)/100 * {NOTIONAL} (got {m['gross_usd']})")
    chk(abs(m['fee_usd'] - round(1 * NOTIONAL * RT_FEE, 4)) < 1e-9,
        f'fee$ = n * notional * 0.09% (got {m["fee_usd"]})')
    chk(abs(m['net_usd'] - (m['gross_usd'] - m['fee_usd'])) < 1e-9,
        'net$ = gross$ - fee$')
    met, limbs = eval_bar('BEAR-SINGLE-SOURCE-SHADOW', m)
    chk([l['limb'] for l in limbs][0] == 'n_joinable >= 20' and not met,
        'bar limbs evaluated (n=1 < 20 -> bar not met)')
    chk(all(l['limb'] != '' for l in limbs) and len(limbs) == 3,
        'bear bar exposes exactly 3 limbs (n / WR / net)')

    print('SELFCHECK ' + ('PASS' if ok else 'FAIL'), flush=True)
    return 0 if ok else 1


# ── main ──────────────────────────────────────────────────────────────────────
def run(log_path=LOG_PATH, out_json=OUT_JSON, tags=TAGS):
    global RAW_STATS
    if not os.path.exists(log_path):
        log(f'log missing: {log_path}')
        return 1
    log(f'reading {log_path} ...')
    with open(log_path, 'r', errors='replace') as f:
        events, stats = collect_events(f, tags=tags)
    RAW_STATS = stats
    log(f'{sum(s["raw_lines"] for s in stats.values())} raw tag lines -> '
        f'{len(events)} token-days after dedup; joining to {CANDLES_DB} ...')
    join_events(events)
    metrics = {t: aggregate(events, t) for t in tags}
    print_table(metrics, tags)

    payload = {
        'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'registry_id': 'short-shadow-join-builder',
        'log_path': log_path,
        'candles_db': CANDLES_DB,
        'notional_usd': NOTIONAL,
        'rt_fee': RT_FEE,
        'fwd_horizon_candles': FWD_HORIZON,
        'dedup': 'tag|token|direction|UTC-day, keep earliest '
                 '(gate-shadow-dedup-convention)',
        'fwd_engine': 'sgn*(close[i+48]/open[i]-1)*100; entry = OPEN of first '
                      'closed 5m candle with ts >= log ts (mirror of '
                      'expiry_shadow._fwd_metrics / gate_shadow._fwd_4h)',
        'member_filter': 'none — bear-single-source counterfactual IS single-type '
                         'passes (see registry bear-single-source-shadow)',
        'tags': {},
        'join_table': [],
    }
    for t in tags:
        m = dict(metrics[t])
        met, limbs = eval_bar(t, m)
        m['bar'] = {'threshold_text': BAR_TEXT.get(t), 'limbs': limbs, 'met': met}
        payload['tags'][t] = m
        payload['join_table'].append({
            'tag': t, 'registry_id': m['registry_id'], 'raw_lines': m['raw_lines'],
            'n_token_days': m['n_token_days'], 'n_joinable': m['n_joinable'],
            'wr_pct': m['wr_pct'], 'avg_fwd_pct': m['avg_fwd_pct'],
            'gross_usd': m['gross_usd'], 'net_usd': m['net_usd'],
            'days_positive': m['days_positive'], 'days_total': m['days_total'],
            'loo_min_net_usd': m['loo_min_net_usd'], 'bar_met': met,
        })
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    tmp = out_json + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)
    os.replace(tmp, out_json)
    log(f'wrote {out_json}')
    return 0


def main():
    ap = argparse.ArgumentParser(description='5-tag shadow log -> fwd4h join + bar verdicts')
    ap.add_argument('--selfcheck', action='store_true')
    ap.add_argument('--tag', action='append', choices=list(TAGS),
                    help='limit to one tag (repeatable)')
    ap.add_argument('--log', default=LOG_PATH)
    ap.add_argument('--json-out', default=OUT_JSON)
    args = ap.parse_args()
    if args.selfcheck:
        return selfcheck()
    return run(log_path=args.log, out_json=args.json_out,
               tags=tuple(args.tag) if args.tag else TAGS)


if __name__ == '__main__':
    sys.exit(main())
