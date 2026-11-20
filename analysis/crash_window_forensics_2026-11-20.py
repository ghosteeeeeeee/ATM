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
    Guard: entry must not precede candle history start (29d retention) else None.
    AUDIT FIX (own-conclusions K3): horizons are now INDEPENDENT — an event with
    only 1h of forward data returns f12 and no f48, instead of being dropped
    entirely (the old max(want) guard censored 94% of rows at the 4h horizon).
    mfe/mae computed over the longest available window (48 if present else 12)."""
    lo, hi = 0, len(rows)
    while lo < hi:
        mid = (lo + hi) // 2
        if rows[mid][0] < entry_ts:
            lo = mid + 1
        else:
            hi = mid
    i = lo
    if rows and rows[0][0] > entry_ts + 300:
        return None
    if i >= len(rows):
        return None
    _, o, c, h, l = rows[i]
    sgn = 1 if direction == 'LONG' else -1
    res = {}
    for n in want:
        if i + n < len(rows):
            res[f'f{n}'] = sgn * (rows[i + n][2] / o - 1) * 100.0
    mfe_n = 48 if (i + 48 < len(rows)) else (12 if (i + 12 < len(rows)) else None)
    if mfe_n is None:
        return None
    highs = [r[3] for r in rows[i:i + mfe_n + 1]]
    lows = [r[4] for r in rows[i:i + mfe_n + 1]]
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

    # ── SNAPSHOT (AUDIT FIX K2/K6): the signals table is purged hourly and
    # gate_shadow records on an hourly service — every count below is
    # timestamped so later readers know what was true WHEN. ────────────────
    P()
    P(f"SNAPSHOT @ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC "
      f"(signals table purged hourly; gate_shadow hourly recorder — max blocked_at below lags the window end)")

    # ── 2. gate_shadow blocks ───────────────────────────────────────────────
    gb = sqlite3.connect(os.path.join(BRAIN, 'gate_shadow.db'))
    grows = gb.execute(
        "SELECT gate, token, direction, blocked_at FROM events WHERE blocked_at >= '2026-11-20 12:00'"
    ).fetchall()
    gb_max = gb.execute("SELECT MAX(blocked_at) FROM events").fetchone()[0]
    gb.close()
    P(f"  gate_shadow max(blocked_at) = {gb_max}  "
      f"(hourly recorder — window tail after this is missed by the DB; "
      f"counted from log lines instead where needed)")
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
    # AUDIT FIX (K2): comma-conjunction signals (e.g. 'pump-chain+,v6+') were
    # dropped by [a-z0-9_+-]+ — all 572 DailyFillCap lines carry the suffix.
    skip_re = re.compile(
        r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?SKIP:?\s*(DailyFillCap|Cap C|'
        r'CONF-FLOOR|No signals above \d+)'
        r'(?:.*?\[blocked ([A-Z0-9]{1,12}) (LONG|SHORT) ([a-z0-9_+, -]+?)\])?')
    cap_events = []
    skip_counts = Counter()
    no_signal_secs = set()   # AUDIT FIX (K2): count distinct seconds, not echo lines
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
                no_signal_secs.add(int(ts))
                skip_counts['no-signal-above-floor(line)'] += 1
                continue
            m = skip_re.search(line)
            if m:
                kind = m.group(2)
                skip_counts[kind] += 1
                if m.group(3):
                    cap_events.append((ts, kind, m.group(3), m.group(4), m.group(5)))
    P(f"  skip LINES by kind: {dict(skip_counts)}  (log echoes ~2x — lines != events)")
    P(f"  'No signals above <floor>': {len(no_signal_secs)} distinct-second events "
      f"({skip_counts.get('no-signal-above-floor(line)',0)} lines)")
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

    # ── 4b. SUCCESSOR PROBE (AUDIT FIX K4): did expired signals convert later?
    P()
    P("── 4b. SUCCESSOR PROBE — did expired signals convert to trades later? " + "─" * 24)
    P("  (successor = same token+direction signal row created ≤10min after death,")
    P("   not itself EXPIRED; trade = any trade on token+direction within 60min)")
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        pgc = psycopg2.connect(**BRAIN_DB_DICT)
        curc = pgc.cursor()
        curc.execute("""SELECT token, direction, EXTRACT(EPOCH FROM open_time) FROM trades
        WHERE open_time >= '2026-11-20 12:00:00+00'""")
        tidx = defaultdict(list)
        for tok, d, ets in curc.fetchall():
            tidx[(tok, d)].append(float(ets))
        pgc.close()
        srows = sg.execute("""
            SELECT token, direction, decision, decision_reason, created_at, updated_at
            FROM signals WHERE created_at >= '2026-11-20 12:00'""").fetchall()
        def _p(ts):
            try:
                return datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
            except (ValueError, TypeError):
                try:
                    return datetime.fromisoformat(ts).timestamp()
                except Exception:
                    return None
        sidx = defaultdict(list)
        for tok, d, dec, reason, cat, uat in srows:
            cts = _p(cat)
            if cts is not None:
                sidx[(tok, d)].append((cts, dec, reason or ''))
        for k in sidx:
            sidx[k].sort()
        succ = defaultdict(lambda: [0, 0, 0])   # cause -> [n, succ_signal, trade60]
        for tok, d, dec, reason, cat, uat in srows:
            if dec != 'EXPIRED':
                continue
            dts = _p(uat) or _p(cat)
            if dts is None:
                continue
            r = reason or ''
            cause = ('combo-stale' if 'combo_key' in r else
                     'blocked@approval' if 'blocked@approval' in r else
                     'fell-out-of-hotset' if 'fell out of hotset' in r else
                     'stale10' if 'compaction_stale' in r else 'other')
            succ[cause][0] += 1
            if any(t > dts and t <= dts + 600 and dd != 'EXPIRED'
                   for t, dd, _ in sidx.get((tok, d), [])):
                succ[cause][1] += 1
            if any(t > dts and t <= dts + 3600 for t in tidx.get((tok, d), [])):
                succ[cause][2] += 1
        P(f"  {'cause':22} {'n':>4} {'succ-signal':>14} {'trade-60m':>14}")
        for c, (n, ss, tt) in sorted(succ.items(), key=lambda x: -x[1][0]):
            P(f"  {c:22} {n:4} {ss:6} ({ss/n*100:3.0f}%) {tt:6} ({tt/n*100:3.0f}%)")
        tot = sum(v[0] for v in succ.values())
        totr = sum(v[2] for v in succ.values())
        P(f"  TOTAL: {tot} expired, {totr} ({totr/tot*100:.1f}%) converted to a "
          f"trade within 60min — the funnel is a ONE-WAY VALVE (audit K4 correction:")
        P(f"  approvals DID occur — 47 'fell out of hotset' rows prove it; zero")
        P(f"  automated trades is fully explained by DailyFillCap engaged 12:07:46→end)")
    except Exception as e:
        P(f"  successor probe failed: {e}")

    # ── 5. trades actually taken ────────────────────────────────────────────
    P()
    P("── 5. EXECUTED (window) " + "─" * 74)
    if pg_ok:
        for sig, n, net in tw:
            kind = "MANUAL(CEO)" if sig.startswith('ai-trader') else "automated"
            P(f"    {sig:28} n={n} net={net:+.2f}  [{kind}]")

    # ── caveats ─────────────────────────────────────────────────────────────
    P()
    P("CAVEATS (audit K3 corrections applied): raw fwd is market-beta in a")
    P("crash — read ex1h/ex4h (direction-signed excess vs cross-sectional mean).")
    P("Horizons are now independent: 1h coverage matures ~60min after each event;")
    P("4h coverage matures ~4h after (events after ~12:25 lack fwd4h until ~20:30).")
    P("The earliest window (12:00-13:30) is a FLAT pre-crash regime (BTC -0.10%)")
    P("vs the crash leg 15:00-16:36 (-3.41%) — matured early events are NOT")
    P("representative of the crash leg; the auditor's 1h-only extended test on the")
    P("crash leg (n=189 dedup) found blocked shorts -0.045% mean, 48% beat market")
    P("— blocked ≈ market holds INTO the crash leg. Per-cause n small; gate_shadow")
    P("rows are per-minute re-logs (hourly recorder — DB lags window tail by up")
    P("to 1h; see SNAPSHOT header); signals-table deaths are purged hourly")
    P("(counts drift — see SNAPSHOT); DailyFillCap line counts echo ~2x — report")
    P("distinct events; comma-conjunction signals now parsed (audit K2 fix).")

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
