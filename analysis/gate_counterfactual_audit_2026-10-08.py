#!/usr/bin/env python3
"""gate_counterfactual_audit_2026-10-08.py

Which entry/execution gates have NO edge — i.e. they block signals whose
forward returns are no worse than market baseline / vs trades that passed?

Method:
  1. Parse ALL block lines from pipeline.log (2026-10-02 20:24 → 2026-10-08 23:01).
     Shape-match emoji+[GATE]+TOKEN+DIR, then classify: gate name contains BLOCK
     or line contains a block marker (blocked/denied/skip/HARD BLOCK). Excludes
     soft multipliers (TIDE →0.7x, RR PENALTY, SLOPE-OVERRIDE, OPP-PENALTY),
     shadow (WOULD BLOCK/SHADOW), ✅ pass lines, DEBUG.
  2. Coalesce repeated per-minute blocks into episodes (gap > 60min = new episode).
  3. Counterfactual per episode: direction-aware forward return from candles.db.
     Entry = OPEN of first 5m candle with ts >= block timestamp (no lookahead).
     Horizons: +30m (+6), +1h (+12), +4h (+48). MFE/MAE over 4h, direction-aware.
  4. Market baseline DIRECTION-SIGNED (v3 fix, 2026-10-08): excess =
     sgn × (raw_fwd − market_mean), sgn=+1 LONG / −1 SHORT. The earlier unsigned
     baseline gave every SHORT episode ~2×market-drift free excess (+0.30% in
     this falling window) — it manufactured false "blocks-winners" verdicts
     (OVERSOLD-SHORT +1.17→+0.04, CHOP −0.91→−0.19). Auditor confirmed v3
     against an independent implementation (audit/gate_counterfactual_verify.md).
  5. Passed-side comparison: same forward metric applied to real live trades
     opened in the same window (brain.trades) — what the gates let through.
  6. OOS split: Oct 2-5 12:00 vs Oct 5 12:00 - Oct 8. Wilcoxon per gate,
     Bonferroni across gates, pooled blocked-vs-passed MWU.

KNOWN GAPS (auditor-verified): single-char token "W" (~864 lines) and
CONF-FILTER-PRESERVE/CONFLICT-RESCUE/LOSERS-BLOCK colon-glued formats still
unparsed (~2% of block volume); direction-level blocks (VOL-FLOOR, WARNING
BTC-momentum, DIRECTION-LOCK, VOL-GATE-v2) have no token+dir → unverifiable
by this method. Verdicts unaffected (auditor cross-validated full table).
"""
import re
import sys
import os
import sqlite3
import json
from datetime import datetime, timezone

sys.path.insert(0, '/root/.hermes/scripts')
from paths import HERMES_DATA

LOG = '/root/.hermes/logs/pipeline.log'
CANDLES = os.path.join(HERMES_DATA, 'candles.db')
OUT = '/root/.hermes/analysis/gate_counterfactual_audit_2026-10-08.out'

HORIZONS = {'30m': 6, '1h': 12, '4h': 48}  # in 5m candles
EPISODE_GAP_SEC = 3600
OOS_SPLIT = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc).timestamp()
LOG_START = datetime(2026, 10, 2, 20, 0, tzinfo=timezone.utc).timestamp()
LOG_END = datetime(2026, 10, 8, 23, 2, tzinfo=timezone.utc).timestamp()

# ── 1. Block-line parsing ────────────────────────────────────────────────────
# General shape: leading ts, emoji, [GATE], TOKEN, DIR (order varies), 'block'.
# Token charset excludes pure digits (prices) — matches gate_shadow convention.
BLOCK_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?'
    r'(?:🚫|🔒|🚧|🌊|🎯|⏱️|🛡️|🚨|⚠️)\s+\[([A-Za-z0-9_-]+)\]\s+'
    r'([A-Z0-9]{2,12})\s+(LONG|SHORT)\b',
)
# LONG-RSI-BLOCK variant: token carries its own colon: [GATE] CHIP: LONG blocked
COLON_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?'
    r'(?:🚫|🔒|🚧|🌊|🎯|⏱️|🛡️|🚨|⚠️)\s+\[([A-Za-z0-9_-]+)\]\s+'
    r'([A-Z0-9]{2,12}):\s+(LONG|SHORT)\b',
)
EXCLUDE_GATE = {'CONFLUENCE-DEBUG'}
# Soft-multiplier / debug lines that match the shape but are NOT blocks:
#   RR-ENGINE "RR PENALTY: ... mult=0.70" (soft conf penalty), TIDE "→ 0.7x",
#   SLOPE-OVERRIDE "threshold relaxed", OPP-PENALTY "→ 70%", PHANTOM-DBG traces,
#   ✅ "allowed"/"SKIPPED" pass lines.
EXCLUDE_SUBSTR = ('WOULD BLOCK', 'SKIPPED', ' shadow', 'SHADOW',
                  'RR PENALTY', '→ 0.', '→ 7', '→ 8', '→ 9', 'relaxed',
                  'allowed', 'DEBUG', 'preserved entry blocked — RSI')  # last one: dup of PRESERVE-SPIKE shape? no — keep, it IS a block; removed below
EXCLUDE_SUBSTR = ('WOULD BLOCK', 'SKIPPED', ' shadow', 'SHADOW',
                  'RR PENALTY', 'relaxed', 'allowed', 'DEBUG')
# A shape-matched line is a BLOCK iff:
#   gate name contains 'BLOCK' (covers CONFLUENCE-GATE-BLOCK, CHASE-BLOCK,
#   PUMP-CHAIN-GAP-BLOCK, PENALTY-BLOCK, HARD-BLOCK, EXEC-BLOCK, PRESERVE-*),
#   OR line contains a block marker (covers CONTINUUM-BULL "denied",
#   VOL-GATE-BYPASS "denied", SLOPE-FILTER "skip", SHORT-CONTINUUM "blocked"...)
BLOCK_MARKERS = ('blocked', 'BLOCKED', 'HARD BLOCK', 'denied', 'skip')

def parse_log():
    events = []
    skipped_shadow = 0
    with open(LOG, 'r', errors='replace') as f:
        for line in f:
            if any(s in line for s in EXCLUDE_SUBSTR):
                skipped_shadow += 1
                continue
            m = BLOCK_RE.match(line)
            if not m:
                m = COLON_RE.match(line)
            if not m:
                continue
            ts_s, gate, token, direction = m.groups()
            if gate in EXCLUDE_GATE:
                continue
            # classify: gate named *BLOCK* is a block; otherwise require a marker
            if 'BLOCK' not in gate.upper() and not any(k in line for k in BLOCK_MARKERS):
                skipped_shadow += 1
                continue
            ts = datetime.strptime(ts_s, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
            if ts < LOG_START or ts > LOG_END:
                continue
            events.append((ts, gate, token, direction))
    return events, skipped_shadow

# ── 2. Episode coalescing ────────────────────────────────────────────────────
def coalesce(events):
    # key: gate|token|direction ; episodes break on > EPISODE_GAP_SEC gap
    by_key = {}
    for ts, gate, token, direction in events:
        by_key.setdefault((gate, token, direction), []).append(ts)
    episodes = []
    for (gate, token, direction), tss in by_key.items():
        tss.sort()
        ep_start = tss[0]
        last = tss[0]
        for ts in tss[1:]:
            if ts - last > EPISODE_GAP_SEC:
                episodes.append((ep_start, gate, token, direction))
                ep_start = ts
            last = ts
        episodes.append((ep_start, gate, token, direction))
    episodes.sort()
    return episodes

# ── 3-4. Forward returns + market baseline from candles.db ──────────────────
def load_candles(tokens):
    conn = sqlite3.connect(CANDLES)
    out = {}
    try:
        cur = conn.cursor()
        for tok in tokens:
            rows = cur.execute(
                "SELECT ts, open, close, high, low FROM candles_5m "
                "WHERE token=? AND is_closed=1 AND ts>=? AND ts<=? ORDER BY ts",
                (tok, int(LOG_START), int(LOG_END) + 4 * 3600 + 300),
            ).fetchall()
            if rows:
                out[tok] = rows
    finally:
        conn.close()
    return out

def forward_metrics(rows, entry_ts, direction):
    """Entry at OPEN of first candle with ts >= entry_ts. Returns dict or None."""
    # binary search first candle with ts >= entry_ts
    lo, hi = 0, len(rows)
    while lo < hi:
        mid = (lo + hi) // 2
        if rows[mid][0] < entry_ts:
            lo = mid + 1
        else:
            hi = mid
    i = lo
    if i + 48 >= len(rows):
        return None  # not enough forward data (censoring)
    _, o, c, h, l = rows[i]
    sgn = 1 if direction == 'LONG' else -1
    res = {'entry': o}
    for name, n in HORIZONS.items():
        close_fwd = rows[i + n][2]
        res[name] = sgn * (close_fwd / o - 1.0) * 100.0
    # 4h MFE/MAE direction-aware
    highs = [r[3] for r in rows[i:i + 49]]
    lows = [r[4] for r in rows[i:i + 49]]
    if direction == 'LONG':
        res['mfe'] = (max(highs) / o - 1.0) * 100.0
        res['mae'] = (min(lows) / o - 1.0) * 100.0
    else:
        res['mfe'] = (1.0 - min(lows) / o) * 100.0
        res['mae'] = (1.0 - max(highs) / o) * 100.0
    return res

_MB_CACHE = {}
_TS2IDX = {}  # token -> {ts: idx}

def market_baseline(entry_ts, horizon):
    """Cross-sectional mean forward return at same entry candle index."""
    n = HORIZONS[horizon]
    # cache by ceiling-to-5m boundary (entry = first candle ts >= entry_ts;
    # candles are 5m-aligned, so all entry_ts in (b-300, b] share candle b)
    bucket = (int(entry_ts) + 299) // 300 * 300
    key = (bucket, horizon)
    if key in _MB_CACHE:
        return _MB_CACHE[key]
    rets = []
    for tok, idx_map in _TS2IDX.items():
        i = idx_map.get(bucket)
        if i is None or i + n >= len(_ROWS_BY_TOK[tok]):
            continue
        rows = _ROWS_BY_TOK[tok]
        rets.append((rows[i + n][2] / rows[i][1] - 1.0) * 100.0)
    if len(rets) < 20:
        _MB_CACHE[key] = None
        return None
    result = sum(rets) / len(rets)
    _MB_CACHE[key] = result
    return result

# ── main ─────────────────────────────────────────────────────────────────────
def main():
    events, skipped_shadow = parse_log()
    episodes = coalesce(events)
    print(f"raw block lines: {len(events)}  (shadow/skip excluded: {skipped_shadow})")
    print(f"episodes (gap>{EPISODE_GAP_SEC//60}min): {len(episodes)}")

    tokens = sorted({e[2] for e in episodes})
    print(f"distinct tokens: {len(tokens)} — loading candles...")
    candles = load_candles(tokens)
    covered = sum(1 for t in tokens if t in candles)
    print(f"tokens with candle coverage: {covered}/{len(tokens)}")

    global _ROWS_BY_TOK, _TS2IDX
    _ROWS_BY_TOK = candles
    _TS2IDX = {tok: {r[0]: i for i, r in enumerate(rows)} for tok, rows in candles.items()}

    # per-gate store: gate -> list of episode result dicts
    per_gate = {}
    no_cov = 0
    for ts, gate, token, direction in episodes:
        rows = candles.get(token)
        if not rows:
            no_cov += 1
            continue
        fm = forward_metrics(rows, ts, direction)
        if fm is None:
            no_cov += 1
            continue
        rec = {'ts': ts, 'token': token, 'dir': direction, **{h: fm[h] for h in HORIZONS},
               'mfe': fm['mfe'], 'mae': fm['mae']}
        for h in HORIZONS:
            mb = market_baseline(ts, h)
            # FIX 2026-10-08: sign the baseline by direction. Unsigned baseline
            # gave every SHORT episode +2×market-drift free excess (market fell
            # −0.20%/4h in window → SHORTs got +0.41% for free). Correct excess
            # = sgn × (raw_fwd − market_mean).
            if mb is None:
                rec[f'excess_{h}'] = None
            else:
                rec[f'excess_{h}'] = fm[h] - (mb if direction == 'LONG' else -mb)
        per_gate.setdefault(gate, []).append(rec)
    print(f"episodes without candle coverage/forward data: {no_cov}")

    # overlap analysis: how many gates fired on same token+dir within ±10min
    ep_index = [(ts, gate, token, direction) for ts, gate, token, direction in episodes]
    overlap_count = {}
    for ts, gate, token, direction in ep_index:
        others = {g for ts2, g, tk, dr in ep_index
                  if tk == token and dr == direction and g != gate and abs(ts2 - ts) <= 600}
        overlap_count.setdefault(gate, []).append(len(others))

    # ── stats helpers ────────────────────────────────────────────────────────
    from scipy import stats as sps
    def summarize(vals):
        vals = [v for v in vals if v is not None]
        n = len(vals)
        if n == 0:
            return None
        mean = sum(vals) / n
        med = sorted(vals)[n // 2] if n % 2 else (sorted(vals)[n // 2 - 1] + sorted(vals)[n // 2]) / 2
        wr = sum(1 for v in vals if v > 0) / n * 100
        if n >= 8 and len(set(vals)) > 1:
            _, p = sps.wilcoxon(vals)
        else:
            p = None
        return dict(n=n, mean=mean, med=med, wr=wr, p=p)

    # real trades opened in the same window — same forward metric (the PASSED side)
    import psycopg2
    from _secrets import BRAIN_DB_DICT
    pg = psycopg2.connect(**BRAIN_DB_DICT)
    tr = pg.cursor()
    tr.execute("""
        SELECT token, direction, EXTRACT(EPOCH FROM open_time), signal FROM trades
        WHERE status='closed' AND paper='f'
          AND open_time >= '2026-10-02 20:00:00+00' AND open_time < '2026-10-08 23:05:00+00'
        ORDER BY open_time
    """)
    trades = tr.fetchall()
    pg.close()
    passed = {'30m': [], '1h': [], '4h': [], 'excess_30m': [], 'excess_1h': [], 'excess_4h': []}
    passed_nocov = 0
    for tok, d, ets, sig in trades:
        rows = candles.get(tok)
        if not rows:
            passed_nocov += 1
            continue
        fm = forward_metrics(rows, ets, d)
        if fm is None:
            passed_nocov += 1
            continue
        for h in HORIZONS:
            passed[h].append(fm[h])
            mb = market_baseline(ets, h)
            # same direction-signed baseline fix as episodes
            passed[f'excess_{h}'].append(
                (fm[h] - (mb if d == 'LONG' else -mb)) if mb is not None else None)

    out = []
    def P(s=''):
        print(s)
        out.append(str(s))

    P("=" * 110)
    P("GATE COUNTERFACTUAL AUDIT — pipeline.log 2026-10-02 20:24 → 2026-10-08 23:01 UTC")
    P("=" * 110)
    P(f"raw block lines parsed: {len(events):,}  |  episodes: {len(episodes):,}  |  "
      f"episodes w/ candle coverage: {sum(len(v) for v in per_gate.values()):,}")
    P()

    # PASSED side first — the benchmark
    P("── PASSED SIDE (real live trades opened in window) " + "─" * 55)
    P(f"n trades in window: {len(trades)}  (no candle coverage: {passed_nocov})")
    for h in HORIZONS:
        s = summarize(passed[h])
        se = summarize(passed[f'excess_{h}'])
        if s:
            P(f"  fwd {h:4}: n={s['n']:3} mean={s['mean']:+.3f}% med={s['med']:+.3f}% wr={s['wr']:5.1f}%  "
              f"| excess vs market: mean={se['mean']:+.3f}% med={se['med']:+.3f}% wr={se['wr']:5.1f}%")
    P()

    # Per-gate table
    P("── PER-GATE COUNTERFACTUAL (episodes; fwd = direction-aware forward return) " + "─" * 33)
    hdr = (f"{'gate':28} {'eps':>5} {'solo':>5} {'ovl':>4} │ "
           f"{'4h wr%':>6} {'ex4h mean':>9} {'ex4h med':>8} {'p':>6} │ "
           f"{'1h wr%':>6} {'ex1h mean':>9} │ {'mfe':>5} {'mae':>6} {'mfe>2%':>6}")
    P(hdr)
    P("─" * len(hdr))

    gate_stats = {}
    for gate in sorted(per_gate, key=lambda g: -len(per_gate[g])):
        recs = per_gate[gate]
        n = len(recs)
        solo = sum(1 for c in overlap_count.get(gate, []) if c == 0)
        ovl = sum(overlap_count.get(gate, [])) / n if n else 0
        s4 = summarize([r['excess_4h'] for r in recs])
        s1 = summarize([r['excess_1h'] for r in recs])
        fwd4 = summarize([r['4h'] for r in recs])
        mfe = sum(r['mfe'] for r in recs) / n
        mae = sum(r['mae'] for r in recs) / n
        mfe2 = sum(1 for r in recs if r['mfe'] >= 2.0) / n * 100
        gate_stats[gate] = dict(n=n, solo=solo, ovl=ovl, s4=s4, s1=s1, fwd4=fwd4,
                                mfe=mfe, mae=mae, mfe2=mfe2)
        p_s = f"{s4['p']:.3f}" if s4 and s4['p'] is not None else "  n/a"
        P(f"{gate:28} {n:5} {solo:5} {ovl:4.1f} │ "
          f"{fwd4['wr']:6.1f} {s4['mean']:+9.3f} {s4['med']:+8.3f} {p_s:>6} │ "
          f"{s1['wr']:6.1f} {s1['mean']:+9.3f} │ {mfe:5.2f} {mae:6.2f} {mfe2:6.1f}")
    P()
    P("ex4h/ex1h = DIRECTION-SIGNED market excess: sgn × (fwd − market_mean), sgn=+1 LONG/−1 SHORT.")
    P("p = Wilcoxon signed-rank of excess vs 0 (edge test).")
    P("solo = episodes where NO other gate fired on same token+direction within ±10min (marginal value).")
    P("mfe>2% = share of blocked episodes that printed ≥+2% favorable excursion in 4h (killed winners).")
    P("VERDICT KEY (auditor-aligned): NO EDGE = |ex-mean| ≤ 0.2% AND p > Bonferroni threshold")
    P("  (gate blocks market-average signals = noise filter; nominal p<0.05 alone is NOT a verdict).")
    P("  WORKS = ex-mean < −0.2% AND p < threshold. BLOCKS WINNERS = ex-mean > +0.2% AND p < threshold.")
    P()

    # ── Pooled blocked-vs-passed (the headline stack-level test) ─────────────
    from scipy import stats as sps
    pooled_blocked = [r['excess_4h'] for recs in per_gate.values() for r in recs
                      if r['excess_4h'] is not None]
    pooled_passed = [v for v in passed['excess_4h'] if v is not None]
    P("── POOLED BLOCKED vs PASSED (excess_4h; does the stack select?) " + "─" * 46)
    if len(pooled_blocked) >= 10 and len(pooled_passed) >= 10:
        import statistics as st
        P(f"  blocked: n={len(pooled_blocked)} mean={st.mean(pooled_blocked):+.3f}% med={st.median(pooled_blocked):+.3f}%")
        P(f"  passed:  n={len(pooled_passed)} mean={st.mean(pooled_passed):+.3f}% med={st.median(pooled_passed):+.3f}%")
        u2, p2 = sps.mannwhitneyu(pooled_passed, pooled_blocked, alternative='two-sided')
        u1, p1 = sps.mannwhitneyu(pooled_passed, pooled_blocked, alternative='greater')
        P(f"  MWU two-sided p={p2:.4f}  one-sided (passed>blocked) p={p1:.4f}")
        P("  INTERPRETATION CAVEAT: power statement — the test can only detect selection")
        P("  ≳ mean-difference CI; gates also toggle minute-to-minute (passed set overlaps")
        P("  blocked set on same token+dir), so p>0.05 ≠ gates proven useless.")
    P()

    # ── Bonferroni summary ───────────────────────────────────────────────────
    n_gates = len(gate_stats)
    bonf = 0.05 / n_gates if n_gates else 0.05
    P(f"── BONFERRONI (gates tested: {n_gates} → threshold p < {bonf:.4f}) " + "─" * 39)
    survivors = [(g, s) for g, s in gate_stats.items()
                 if s['s4'] and s['s4']['p'] is not None and s['s4']['p'] < bonf]
    nominal = [(g, s) for g, s in gate_stats.items()
               if s['s4'] and s['s4']['p'] is not None and bonf <= s['s4']['p'] < 0.05]
    if survivors:
        P("  SURVIVES BONFERRONI:")
        for g, s in sorted(survivors, key=lambda x: x[1]['s4']['p']):
            verdict = 'WORKS' if s['s4']['mean'] < -0.2 else ('BLOCKS-WINNERS' if s['s4']['mean'] > 0.2 else 'DIFFERS-FROM-MARKET')
            P(f"    {g:26} n={s['n']:4} ex4h={s['s4']['mean']:+.3f}% p={s['s4']['p']:.5f} → {verdict}")
    else:
        P("  (none)")
    if nominal:
        P("  NOMINAL ONLY (p<0.05, does NOT survive Bonferroni — not actionable):")
        for g, s in sorted(nominal, key=lambda x: x[1]['s4']['p']):
            P(f"    {g:26} n={s['n']:4} ex4h={s['s4']['mean']:+.3f}% p={s['s4']['p']:.4f}")
    P()

    # OOS halves
    P("── OOS SPLIT (excess_4h mean; first half vs second half) " + "─" * 51)
    P(f"{'gate':28} {'n1':>4} {'ex1h1':>8} {'n2':>4} {'ex1h2':>8} {'same-sign':>9}")
    for gate in sorted(per_gate, key=lambda g: -len(per_gate[g])):
        recs = per_gate[gate]
        a = [r['excess_4h'] for r in recs if r['ts'] < OOS_SPLIT]
        b = [r['excess_4h'] for r in recs if r['ts'] >= OOS_SPLIT]
        ma = sum(a) / len(a) if a else float('nan')
        mb = sum(b) / len(b) if b else float('nan')
        same = '  —  ' if not (a and b) else ('YES' if ma * mb > 0 else 'NO ')
        P(f"{gate:28} {len(a):4} {ma:+8.3f} {len(b):4} {mb:+8.3f} {same:>9}")
    P()

    # Family rollup — group gates by theme for readability
    P("── BLOCK VOLUME ROLLUP " + "─" * 86)
    tot = sum(len(v) for v in per_gate.values())
    for gate in sorted(per_gate, key=lambda g: -len(per_gate[g])):
        n = len(per_gate[gate])
        P(f"  {gate:28} {n:5} episodes ({n/tot*100:4.1f}%)")
    P(f"  {'TOTAL':28} {tot:5}")

    with open(OUT, 'w') as f:
        f.write('\n'.join(out))
    print(f"\nwritten: {OUT}")

if __name__ == '__main__':
    main()
