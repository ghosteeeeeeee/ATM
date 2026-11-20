#!/usr/bin/env python3
"""crash_window_forensics_2026-11-20.py

BTC crash 2026-11-20 (user: "zero trades in a major btc crash") — full funnel
forensics for the window 12:00 UTC -> run time, with direction-signed
counterfactuals (the engine method independently cross-validated in
audit/gate_counterfactual_verify.md; direction-signed excess = sgn*(raw_fwd -
cross-sectional market mean)).

Funnel sources (every row traceable):
  1. signals table (data/signals_hermes_runtime.db) — per-signal death
     certificates (decision, decision_reason, confidence) for signals created
     in-window. Emission denominator.
  2. brain/gate_shadow.db — gate block events blocked_at >= window start.
  3. pipeline.log window lines — decider SKIP lines (DailyFillCap / Cap C /
     conf floor) incl. the [blocked TOKEN DIR signal] suffix = ready-to-trade
     candidates that passed everything and died at the capital brake.
  4. PG brain.trades — executed trades in window (automated vs manual signal
     naming: ai-trader-* = CEO-directed manual per AGENTS.md).

Outputs:
  analysis/crash_window_forensics_2026-11-20.out
  analysis/exports/crash_funnel.tsv     (per-cause funnel rows)
  analysis/exports/crash_events.tsv     (every event + forward metrics)
"""
import sys
import os
import re
import gzip
import sqlite3
from datetime import datetime, timezone
from collections import defaultdict, Counter

sys.path.insert(0, '/root/.hermes/scripts')
from paths import HERMES_DATA

BRAIN = os.path.join(os.path.dirname(HERMES_DATA), 'brain')
CANDLES = os.path.join(HERMES_DATA, 'candles.db')
SIGNALS = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')
PIPELINE_LOG = '/root/.hermes/logs/pipeline.log'
EXPORTS = '/root/.hermes/analysis/exports'
WINDOW_START = datetime(2026, 11, 20, 12, 0, 0, tzinfo=timezone.utc).timestamp()

from scipy import stats as sps

# ── candles + audited forward engine ────────────────────────────────────────
_C = {}
def candles(tok):
    if tok in _C:
        return _C[tok]
    conn = sqlite3.connect(CANDLES, timeout=10)
    try:
        rows = conn.execute(
            "SELECT ts, open, close, high, low FROM candles_5m"
            " WHERE token=? AND is_closed=1 ORDER BY ts", (tok,)).fetchall()
    finally:
        conn.close()
    _C[tok] = rows
    return rows

def fwd_metrics(rows, entry_ts, direction, want=(12, 48)):
    """Entry = OPEN of first 5m candle with ts >= entry_ts (no lookahead).
    Guard: entry must precede candle history start (29d retention) else None.
    Returns dict of direction-signed raw fwd at horizons + mfe/mae (max horizon)."""
    lo, hi = 0, len(rows)
    while lo < hi:
        mid = (lo + hi) // 2
        if rows[mid][0] < entry_ts:
            lo = mid + 1
        else:
            hi = mid
    i = lo
    need = max(want)
    if rows and rows[0][0] > entry_ts + 300:
        return None
    if i + need >= len(rows):
        return None
    _, o, c, h, l = rows[i]
    sgn = 1 if direction == 'LONG' else -1
    res = {}
    for n in want:
        res[f'f{n}'] = sgn * (rows[i + n][2] / o - 1) * 100.0
    highs = [r[3] for r in rows[i:i + need + 1]]
    lows = [r[4] for r in rows[i:i + need + 1]]
    if direction == 'LONG':
        res['mfe'] = (max(highs) / o - 1.0) * 100.0
        res['mae'] = (min(lows) / o - 1.0) * 100.0
    else:
        res['mfe'] = (1.0 - min(lows) / o) * 100.0
        res['mae'] = (1.0 - max(highs) / o) * 100.0
    return res

_MKT = {}      # horizon_n -> {bucket_ts: {token: fwd}}
_MKT_CACHE = {}
def market_mean(bucket_ts, horizon_n):
    global _MKT
    if horizon_n not in _MKT:
        conn = sqlite3.connect(CANDLES, timeout=10)
        try:
            rows = conn.execute(
                "SELECT token, ts, open, close FROM candles_5m WHERE is_closed=1"
                " ORDER BY token, ts").fetchall()
        finally:
            conn.close()
        by_tok = defaultdict(list)
        for tok, ts, o, c in rows:
            by_tok[tok].append((ts, o, c))
        d = defaultdict(dict)
        for tok, tr in by_tok.items():
            for i in range(len(tr) - horizon_n):
                ts, o, c = tr[i]
                d[ts][tok] = (tr[i + horizon_n][2] / o - 1.0) * 100.0
        _MKT[horizon_n] = d
    key = (horizon_n, (int(bucket_ts) + 299) // 300 * 300)
    if key in _MKT_CACHE:
        return _MKT_CACHE[key]
    dd = _MKT[horizon_n].get(key[1])
    if not dd or len(dd) < 20:
        _MKT_CACHE[key] = None
        return None
    m = sum(dd.values()) / len(dd)
    _MKT_CACHE[key] = m
    return m

# ── window sources ───────────────────────────────────────────────────────────
CAUSE_KEYS = [
    ('short-rsi-hard-floor', 'short-rsi-hard-floor'),
    ('vol-gate-override-0', 'vol-gate-override-0'),
    ('combo_key', 'combo-stale(merge-window)'),
    ('compaction_stale', 'compaction-stale-10min'),
    ('fell out of hotset', 'approved-fell-out-of-hotset'),
    ('rr-engine', 'rr-engine-hard-block'),
    ('short-regime', 'short-regime-gate'),
    ('pump-chain-short-high', 'pump-chain-short-high'),
    ('oversold-knife', 'oversold-knife'),
    ('confluence: single-type', 'confluence-single-not-bypass'),
    ('long-rsi-ceiling', 'long-rsi-ceiling'),
    ('long-high-70', 'long-high-70'),
    ('spike-filter', 'spike-filter-long'),
    ('pump-chain-long-high', 'pump-chain-long-high'),
    ('pump-chain-rsi-max', 'pump-chain-rsi-max'),
    ('pump-chain-vel', 'pump-chain-vel'),
    ('long-neutral-chop', 'long-neutral-chop'),
    ('long-midband', 'long-midband'),
    ('long-rsi-floor', 'long-rsi-floor'),
    ('long-rsi-block', 'long-rsi-block'),
    ('vol-gate-override', 'vol-gate-override-0'),
]

def classify_cause(reason):
    if not reason:
        return 'no-reason'
    for key, lab in CAUSE_KEYS:
        if key in reason:
            return lab
    if 'blocked@approval' in reason:
        return 'blocked@approval(other)'
    if 'combo_key' in reason:
        return 'combo-stale(merge-window)'
    if 'compaction_stale' in reason:
        return 'compaction-stale-10min'
    if 'hotset' in reason:
        return 'hotset-related'
    return 'other:' + reason[:40]

def main():
    out = []
    def P(s=''):
        print(s)
        out.append(str(s))

    now = datetime.now(timezone.utc).timestamp()
    P("=" * 100)
    P(f"CRASH-WINDOW FUNNEL FORENSICS — 2026-11-20 12:00 → {datetime.fromtimestamp(now, timezone.utc):%H:%M} UTC")
    P("=" * 100)

    # ── 0. incident verification ─────────────────────────────────────────────
    conn = sqlite3.connect(CANDLES)
    btc = conn.execute(
        "SELECT ts, close FROM candles_5m WHERE token='BTC' AND is_closed=1 AND ts>=? "
        "ORDER BY ts", (int(now) - 21600,)).fetchall()
    hi = max(c for _, c in btc); lo = min(c for _, c in btc)
    P(f"BTC last 6h: high={hi:,.0f} low={lo:,.0f} drawdown={(lo/hi-1)*100:+.2f}% "
      f"last={btc[-1][1]:,.0f}")
    conn.close()

    pg_ok = True
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        pg = psycopg2.connect(**BRAIN_DB_DICT)
        cur = pg.cursor()
        cur.execute("""
            SELECT signal, COUNT(*), SUM(pnl_usdt) FROM trades
            WHERE open_time >= '2026-11-20 12:00:00+00' GROUP BY 1 ORDER BY 2 DESC""")
        tw = cur.fetchall()
        cur.execute("SELECT COUNT(*) FROM trades WHERE status='open'")
        nopen = cur.fetchone()[0]
        pg.close()
        tot = sum(r[1] for r in tw)
        P(f"trades since 12:00: {tot} (open: {nopen}) — breakdown: {tw}")
        P(f"  automated (non-ai-trader-*) = {sum(r[1] for r in tw if not r[0].startswith('ai-trader'))}")
    except Exception as e:
        P(f"PG query failed: {e}")
        pg_ok = False

    # ── 1. emissions (signals table) ────────────────────────────────────────
    sg = sqlite3.connect(SIGNALS)
    em = sg.execute("""
        SELECT direction, decision, COUNT(*), ROUND(AVG(confidence),1)
        FROM signals WHERE created_at >= '2026-11-20 12:00'
        GROUP BY 1, 2 ORDER BY 1, 3 DESC""").fetchall()
    P()
    P("── 1. EMISSIONS + PER-SIGNAL DEATH CERTIFICATES (signals table) " + "─" * 33)
    P(f"  {'dir':6} {'decision':10} {'n':>4} {'avg_conf':>8}")
    for d, dec, n, c in em:
        P(f"  {d:6} {dec:10} {n:4} {c or 0:8}")
    deaths = sg.execute("""
        SELECT direction, decision_reason, COUNT(*), ROUND(AVG(confidence),1)
        FROM signals WHERE created_at >= '2026-11-20 12:00' AND decision='EXPIRED'
        GROUP BY 1, 2 ORDER BY 1, 3 DESC""").fetchall()
    P("  death causes (EXPIRED):")
    for d, reason, n, c in deaths:
        P(f"    {d:6} n={n:3} conf={c or 0:5} :: {classify_cause(reason)}")

    # ── 2. gate_shadow blocks ───────────────────────────────────────────────
    gb = sqlite3.connect(os.path.join(BRAIN, 'gate_shadow.db'))
    grows = gb.execute(
        "SELECT gate, token, direction, blocked_at FROM events WHERE blocked_at >= '2026-11-20 12:00'"
    ).fetchall()
    gb.close()
    P()
    P("── 2. GATE SHADOW BLOCK EVENTS (window) " + "─" * 58)
    gc = Counter(g[0] for g in grows)
    gd = Counter(g[2] for g in grows)
    P(f"  total={len(grows)}  by direction: LONG={gd.get('LONG',0)} SHORT={gd.get('SHORT',0)}")
    for k, v in gc.most_common(20):
        P(f"    {k:32} {v}")

    # ── 3. decider SKIP lines (DailyFillCap / Cap C / conf floor) ───────────
    P()
    P("── 3. DECIDER SKIP LINES (window, pipeline.log) " + "─" * 49)
    skip_re = re.compile(
        r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?SKIP:?\s*(DailyFillCap|Cap C|'
        r'CONF-FLOOR|No signals above \d+)'
        r'(?:.*?\[blocked ([A-Z0-9]{1,12}) (LONG|SHORT) ([a-z0-9_+-]+)\])?')
    cap_events = []
    skip_counts = Counter()
    no_signal_cycles = 0
    with open(PIPELINE_LOG, 'r', errors='replace') as f:
        for line in f:
            ts_m = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            if not ts_m:
                continue
            ts = datetime.strptime(ts_m.group(1), '%Y-%m-%d %H:%M:%S').replace(
                tzinfo=timezone.utc).timestamp()
            if ts < WINDOW_START:
                continue
            if 'No signals above' in line:
                no_signal_cycles += 1
                skip_counts['no-signal-above-floor(cycle)'] += 1
                continue
            m = skip_re.search(line)
            if m:
                kind = m.group(2)
                skip_counts[kind] += 1
                if m.group(3):
                    cap_events.append((ts, kind, m.group(3), m.group(4), m.group(5)))
    P(f"  skip lines by kind: {dict(skip_counts)}")
    P(f"  'No signals above <floor>' cycles: {no_signal_cycles}")
    P(f"  ready-candidate blocks with [blocked tok dir signal]: {len(cap_events)}")
    cc = Counter((k, d, s) for _, k, _, d, s in cap_events)
    for (k, d, s), v in cc.most_common(12):
        P(f"    {k:14} {d:5} {s:26} {v}")

    # ── 4. counterfactual: every window event through the audited engine ────
    P()
    P("── 4. COUNTERFACTUAL (direction-signed excess; entry=next 5m open) " + "─" * 31)
    events = []  # (ts, source, gate_or_cause, token, direction, conf)
    for tok, d, reason, conf, cat, uat in sg.execute("""
            SELECT token, direction, decision_reason, confidence, created_at, updated_at
            FROM signals WHERE created_at >= '2026-11-20 12:00' AND decision='EXPIRED'"""):
        try:
            ts = datetime.strptime(uat, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
        except (ValueError, TypeError):
            try:
                ts = datetime.fromisoformat(uat).timestamp()
            except Exception:
                ts = None
        if ts is None:
            continue
        events.append((ts, 'signals-expired', classify_cause(reason), tok, d, conf))
    for ts, kind, tok, d, sig in cap_events:
        events.append((ts, 'decider-skip', kind, tok, d, None))
    for gate, tok, d, bat in grows:
        try:
            ts = datetime.fromisoformat(bat).timestamp()
        except (ValueError, TypeError):
            continue
        events.append((ts, 'gate-shadow', gate, tok, d, None))

    enriched = []
    for ts, src, cause, tok, d, conf in events:
        rows = candles(tok)
        fm = fwd_metrics(rows, ts, d) if rows else None
        if fm is None:
            enriched.append((ts, src, cause, tok, d, conf, None, None, None, None, None))
            continue
        bucket = int(ts + 299) // 300 * 300
        raw1 = fm.get('f12')
        raw4 = fm.get('f48')
        mb1 = market_mean(bucket, 12)
        mb4 = market_mean(bucket, 48)
        exc1 = (raw1 - (mb1 if d == 'LONG' else -mb1)) if (mb1 is not None and raw1 is not None) else None
        exc4 = (raw4 - (mb4 if d == 'LONG' else -mb4)) if (mb4 is not None and raw4 is not None) else None
        enriched.append((ts, src, cause, tok, d, conf, raw1, raw4, exc1, exc4, fm.get('mfe')))

    # per-cause summary on the 1h horizon (mature for the window)
    P(f"  {'source':15} {'cause':30} {'n':>4} {'cov1h':>5} {'ex1h':>8} {'cov4h':>5} {'ex4h':>8}")
    P("  (ex = direction-signed excess vs cross-sectional market mean at same bucket)")
    by = defaultdict(list)
    for e in enriched:
        by[(e[1], e[2])].append(e)
    for key in sorted(by, key=lambda k: -len(by[k])):
        v = by[key]
        c1 = [x[8] for x in v if x[8] is not None]
        c4 = [x[9] for x in v if x[9] is not None]
        m1 = f"{sum(c1)/len(c1):+.2f}%" if c1 else "n/a"
        m4 = f"{sum(c4)/len(c4):+.2f}%" if c4 else "n/a"
        P(f"  {key[0]:15} {key[1]:30} {len(v):4} {len(c1):5} {m1:>8} {len(c4):5} {m4:>8}")

    # biggest individual misses (shorts that dumped hard after being blocked)
    seen = set()
    shorts = []
    for x in enriched:
        if x[4] != 'SHORT' or x[6] is None:
            continue
        bkey = (x[3], int(x[0]) // 600)   # token + 10min bucket dedup
        if bkey in seen:
            continue
        seen.add(bkey)
        shorts.append((x[8] if x[8] is not None else x[6], x[3], x[5], x[2], x[8] is not None))
    shorts.sort(key=lambda t: -t[0])
    P()
    P("  biggest blocked-SHORT misses (dedup token+10min; prefer market-adjusted ex1h):")
    for r, tok, conf, cause, is_ex in shorts[:10]:
        tag = 'ex1h' if is_ex else 'raw1h'
        P(f"    {tok:8} conf={conf if conf is not None else 'n/a':>4} {tag}={r:+6.2f}%  ({cause})")
    exv = [x[0] for x in shorts if x[4]]
    if exv:
        pos = sum(1 for r in exv if r > 0)
        P(f"  MARKET-ADJUSTED: {len(exv)} blocked shorts with ex1h coverage — "
          f"{pos} ({pos/len(exv)*100:.0f}%) beat the market in the next hour")
        P(f"  mean ex1h = {sum(exv)/len(exv):+.2f}%")

    # ── 5. trades actually taken ────────────────────────────────────────────
    P()
    P("── 5. EXECUTED (window) " + "─" * 74)
    if pg_ok:
        for sig, n, net in tw:
            kind = "MANUAL(CEO)" if sig.startswith('ai-trader') else "automated"
            P(f"    {sig:28} n={n} net={net:+.2f}  [{kind}]")

    # ── caveats ─────────────────────────────────────────────────────────────
    P()
    P("CAVEATS: during a -5% crash hour raw fwd is market-beta — read ex1h/ex4h")
    P("(direction-signed excess vs cross-sectional mean), not raw fwd. Events")
    P("within the last 1h/4h are right-censored (no mature forward yet) — rerun")
    P("after 18:00 for full 1h coverage. Per-cause n small; gate_shadow rows are")
    P("per-minute re-logs (dedup applied to the misses list only); signals-table")
    P("deaths are per-signal truth; gate_shadow capture = 10-emoji set since the")
    P("Oct-20 port; DailyFillCap [blocked] suffix present on 507/572 lines.")

    # ── exports ─────────────────────────────────────────────────────────────
    os.makedirs(EXPORTS, exist_ok=True)
    with open(os.path.join(EXPORTS, 'crash_events.tsv'), 'w') as f:
        f.write("ts\tsource\tcause\ttoken\tdirection\tconfidence\t"
                "fwd_1h_raw\tfwd_4h_raw\texcess_1h\texcess_4h\tmfe_4h\n")
        for e in enriched:
            f.write('\t'.join('' if v is None else (
                f'{v:.4f}' if isinstance(v, float) else str(v)) for v in e) + '\n')
    with open(os.path.join(EXPORTS, 'crash_funnel.tsv'), 'w') as f:
        f.write("source\tcause\tn\tcov_ex1h\tex1h_mean\tcov_ex4h\tex4h_mean\n")
        for key in sorted(by, key=lambda k: -len(by[k])):
            v = by[key]
            c1 = [x[8] for x in v if x[8] is not None]
            c4 = [x[9] for x in v if x[9] is not None]
            f.write(f"{key[0]}\t{key[1]}\t{len(v)}\t{len(c1)}\t"
                    f"{(sum(c1)/len(c1)) if c1 else ''}\t{len(c4)}\t"
                    f"{(sum(c4)/len(c4)) if c4 else ''}\n")
    P()
    P(f"exports: {EXPORTS}/crash_events.tsv, crash_funnel.tsv")

    with open('/root/.hermes/analysis/crash_window_forensics_2026-11-20.out', 'w') as f:
        f.write('\n'.join(out))

if __name__ == '__main__':
    main()
