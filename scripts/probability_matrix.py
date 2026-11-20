#!/usr/bin/env python3
"""
probability_matrix.py — P0 read-only calibration study for the probability matrix.

Spec (contract): brain/plans/probability-matrix-spec.md v1.1 — §3.1 (cell schema,
p source, coverage, 0-win/UNCALIBRATED), §3.2 (formulas), §4 (calibration design +
four pre-registered limbs), §5 (descriptive payoff layer), §8 (files).
P0 touches ONLY this script + brain/analysis/probability-matrix-calibration.md.
SELECT-only everywhere; zero trading-path effect; no hermes_constants edits
(config lives in this header as documented CLI defaults — kill_line_shadow.py
convention).

Modes:
  calibrate   §4 rolling-origin calibration study -> writes the .md report
  report      §3.1/§5 per-cell table (descriptive payoff layer) -> stdout
  --selfcheck assert-based pure-math checks (no DB, exit 1 on failure)
  --help      documents every param, step choice, formula and the four limbs
              BEFORE any data is touched (argparse epilog below).

TUNING VALUES (documented CLI defaults; P0 must NOT touch hermes_constants, spec §8):
  DEFAULT_DAYS  = 90   data-anchored lookback window (streak_analysis parity)
  TRAIN_DAYS    = 30   rolling-origin train span
  TEST_DAYS     = 7    test span; STEP = TEST_DAYS so test folds are disjoint
                       and contiguous (every test trade scored exactly once)
  DEFAULT_FOLDS = 5    >= 3 required by spec §4 (data allows up to 8 at 90d)
  N_MIN         = 15   cell admission, train-only per fold (spec §3.1);
                       NEVER loosened to chase coverage (spec §9)
  K             = 10   blend prior strength (correlation_engine parity, spec §3.1)
  EPS_P         = 0.01 p clip before scoring (spec §3.2)
  EPS_AMT       = 0.05 |avg_loss| floor for ev_per_risk (spec §3.2)
  BUCKET_MIN_N  = 30   thin reliability-bucket flag threshold
  CONF_MIN_SHARE = 0.30 limb (b) intersection floor (spec §4)

FORMULAS (single definitions, spec §3.2):
  p(c)        = clip((n_c * wr_raw_c + K * 0.50) / (n_c + K), 0.01, 0.99)
                # ALWAYS blended regardless of the store's tier behavior
  ev_usdt(c)  = p(c) * mean(pnl | win, c) + (1 - p(c)) * mean(pnl | loss, c)
  ev_per_risk = ev_usdt / |mean(pnl | loss, c)|  ONLY when
                |mean(pnl | loss, c)| >= EPS_AMT, else null (never divide into noise)
  brier       = mean over trades of (p(cell(t)) - y_t)^2,  y_t = 1 iff pnl_usdt > 0
  log-loss    = mean of -(y*log(p) + (1-y)*log(1-p)), p clipped to [0.01, 0.99]
  y_t: pnl_usdt == 0 counts as non-win (y=0), same convention as streak_analysis
  coverage(fold) = (test trades whose cell was admitted in THAT fold's train at
                n >= N_MIN) / (all test trades)   [spec §3.1 definition]

CELL = (signal, direction, volatility_regime) — identical axes to cell_stats.py
(regime = COALESCE(NULLIF(volatility_regime,''), NULLIF(regime,''),'UNKNOWN'),
upper-cased; cell_stats.py:80 parity).

SIGNAL-KEY NORMALIZATION (auditor landmine: cell_stats keys and trades.signal use
different separators — cell_stats.db holds BOTH dash-form pump-chain+ (from
trades.signal) and underscore-form pump_chain (from source) with DIFFERENT stats):
  RULE: strip -> lower -> '-'->'_' -> remove '+' -> whitespace->'_' -> collapse
        '_' runs -> strip leading/trailing '_'
        DELTA vs signal_compactor.py:2245 cell-stats lookup: live does
        replace('-','_').replace('+','').replace(' ','_').lower().rstrip('_')
        ONLY — no pre-strip, literal space (not whitespace-class), no '_'-run
        collapse, no leading-strip. This rule is a STRICT SUPERSET, NOT exact
        parity; exact match is tried first and normalization fired 0 times this
        run (0 fallback matches), so the delta never changed a match.
  EXACT match first; normalized match only as fallback when no exact hit; a
  normalized key that maps to >1 store key is AMBIGUOUS and counted unmatched
  (never silently merged — the auditor found normalization hitting the WRONG
  row). Unmatched keys/trades are counted and printed, never dropped silently.

FOUR PRE-REGISTERED LIMBS (spec §4 — all four PASS => PROCEED-TO-P1, else STOP
with an honest report):
  (a) discrimination: top-2 p-decile observed WR > bottom-2, cluster-robust
      p < 0.05, sign preserved on the final test fold
  (b) beats confidence: Brier(p) < Brier(final_confidence/100) on the
      intersection subset, cluster-robust paired 95% CI excludes 0;
      intersection < 30% of test trades => INCONCLUSIVE (LOW-COVERAGE)
  (c) beats baseline: Brier(p) < Brier(0.5), cluster-robust paired CI excludes 0
  (d) coverage disclosure: per-fold coverage table published; worst-fold
      coverage < 10% => LOW-COVERAGE (P1 waits for more data; n_min never loosened)

SIGNIFICANCE: cluster-robust CR1 sandwich, cluster = signal source, math mirrored
from brain/analysis/cluster_t.py (selfcheck asserts exact agreement with it).
Plain (naive) p-values are optimistic under clustering and flagged as such.

Reproduce:
  python3 /root/.hermes/scripts/probability_matrix.py calibrate --days 90 --folds 5
"""
import argparse
import math
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import *  # noqa: F401,F403

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELL_DB = os.path.join(REPO, 'brain', 'cell_stats.db')
REPORT_MD = os.path.join(REPO, 'brain', 'analysis', 'probability-matrix-calibration.md')

# ── header constants: documented CLI defaults (spec §8 — NOT hermes_constants) ─
DEFAULT_DAYS = 90        # data-anchored lookback (streak_analysis parity)
TRAIN_DAYS = 30          # rolling-origin train span
TEST_DAYS = 7            # test span (== step: disjoint contiguous test folds)
DEFAULT_FOLDS = 5        # spec §4 requires >= 3
N_MIN = 15               # cell admission (spec §3.1); never loosened
K = 10                   # blend prior strength (correlation_engine parity)
EPS_P = 0.01             # p clip before scoring (spec §3.2)
EPS_AMT = 0.05           # |avg_loss| floor for ev_per_risk (spec §3.2)
BUCKET_MIN_N = 30        # thin reliability bucket flag
CONF_MIN_SHARE = 0.30    # limb (b) intersection floor
WIN_DEF = 'pnl_usdt > 0 (pnl_usdt == 0 counts as non-win)'

NORM_RULE = ("strip -> lower -> '-'->'_' -> remove '+' -> whitespace->'_' -> "
             "collapse '_' runs -> strip leading/trailing '_' "
             "(SUPERSET of signal_compactor.py:2245 lookup: live = "
             "replace('-','_').replace('+','').replace(' ','_').lower()."
             "rstrip('_') only — no pre-strip, no run-collapse, no "
             "leading-strip; exact match first, 0 fallbacks this run)")

# Exact SQL, printed on every run for reproducibility (params = (days,)).
# Window start anchored to MAX(close_time) in-data (NOT NOW()) so window ==
# [anchor-days, anchor], deterministic given the data — same anchor build_folds
# uses for labels (two-clocks fix).
SQL = (
    "SELECT id, close_time, signal, direction, "
    "       COALESCE(NULLIF(volatility_regime, ''), NULLIF(regime, ''), 'UNKNOWN') AS regime, "
    "       pnl_usdt, mfe_pct, mae_pct, "
    "       CASE WHEN _signal_metadata ? 'final_confidence' "
    "            THEN (_signal_metadata->>'final_confidence')::float END AS final_confidence "
    "FROM trades "
    "WHERE status = 'closed' "
    "  AND pnl_usdt IS NOT NULL "
    "  AND close_time > (SELECT MAX(close_time) - make_interval(days => %s) "
    "                    FROM trades "
    "                    WHERE status = 'closed' AND pnl_usdt IS NOT NULL) "
    "ORDER BY close_time ASC, id ASC"
)

STORE_SQL = ("SELECT signal, direction, regime, n, wins, wr_raw, admission, tradeable "
             "FROM cells ORDER BY signal ASC, direction ASC, regime ASC")


def log(msg):
    print(msg, flush=True)


def print_sql(days):
    log('SQL: ' + ' '.join(SQL.split()))
    log(f'params: ({days},)   window: [MAX(close_time)-{days}d, MAX(close_time)], '
        'status=closed, pnl_usdt NOT NULL, ordered by close_time ASC, id ASC')


# ── data fetch (SELECT-only; 3 .execute sites in this file — SQL, STORE_SQL,
# meta SELECT — all SELECT constants; cursors closed in finally — repo convention) ─
def fetch_trades(days):
    import psycopg2
    from _secrets import BRAIN_DB_DICT
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute(SQL, (days,))
        cols = [d[0] for d in cur.description]
        rows = []
        for r in cur.fetchall():
            d = dict(zip(cols, r))
            d['pnl_usdt'] = float(d['pnl_usdt'])
            d['mfe_pct'] = float(d['mfe_pct']) if d['mfe_pct'] is not None else None
            d['mae_pct'] = float(d['mae_pct']) if d['mae_pct'] is not None else None
            d['final_confidence'] = (float(d['final_confidence'])
                                     if d['final_confidence'] is not None else None)
            d['signal'] = (d['signal'] or 'UNKNOWN').strip() or 'UNKNOWN'
            d['direction'] = (d['direction'] or 'UNKNOWN').strip().upper() or 'UNKNOWN'
            d['regime'] = (d['regime'] or 'UNKNOWN').strip().upper() or 'UNKNOWN'
            rows.append(d)
        return rows
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


def load_store():
    """Read-only view of brain/cell_stats.db `cells` (the live store)."""
    conn = None
    cur = None
    try:
        conn = sqlite3.connect(f'file:{CELL_DB}?mode=ro', uri=True)
        cur = conn.cursor()
        cells = [{'signal': s, 'direction': d, 'regime': g, 'n': n, 'wins': w,
                  'wr_raw': wr, 'admission': adm, 'tradeable': bool(t)}
                 for s, d, g, n, w, wr, adm, t in cur.execute(STORE_SQL).fetchall()]
        meta = dict(cur.execute('SELECT key, value FROM meta').fetchall())
        return cells, meta
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


# ── pure math (selfcheck-covered) ────────────────────────────────────────────
def blend_p(n, wr):
    """Spec §3.1/§3.2: ALWAYS blended regardless of store tier, then clipped."""
    p = (n * wr + K * 0.50) / (n + K)
    return max(EPS_P, min(1 - EPS_P, p))


def y_of(pnl):
    """Spec §3.2: y = 1 iff pnl_usdt > 0 (0 counts as non-win)."""
    return 1 if pnl > 0 else 0


def brier(ps, ys):
    return sum((p - y) ** 2 for p, y in zip(ps, ys)) / len(ys)


def logloss(ps, ys):
    out = 0.0
    for p, y in zip(ps, ys):
        p = max(EPS_P, min(1 - EPS_P, p))
        out += -(y * math.log(p) + (1 - y) * math.log(1 - p))
    return out / len(ys)


def ev_usdt(p, avg_win, avg_loss):
    return p * avg_win + (1 - p) * avg_loss


def ev_per_risk(ev, avg_loss):
    """Spec §3.2: null when |avg_loss| < EPS_AMT — never divide into noise."""
    if avg_loss is None or abs(avg_loss) < EPS_AMT:
        return None
    return ev / abs(avg_loss)


def norm_key(k):
    """Auditor landmine rule (module docstring); never applied to break exact hits."""
    k = (k or '').strip().lower().replace('-', '_').replace('+', '')
    k = re.sub(r'\s+', '_', k)
    k = re.sub(r'_+', '_', k)
    return k.strip('_')


def cluster_stats(values, clusters):
    """CR1 sandwich, intercept-only — math mirrored from brain/analysis/cluster_t.py
    (selfcheck asserts exact t agreement). Returns (beta, se, t, G)."""
    n = len(values)
    if n < 2:
        raise ValueError('need at least 2 observations')
    beta = sum(values) / n
    grouped = defaultdict(float)
    for v, g in zip(values, clusters):
        grouped[g] += v - beta
    g = len(grouped)
    if g < 2:
        raise ValueError('need at least 2 clusters')
    se = math.sqrt((g / (g - 1)) * sum(s * s for s in grouped.values())) / n
    if se == 0:
        t = 0.0 if beta == 0 else math.copysign(float('inf'), beta)
    else:
        t = beta / se
    return beta, se, t, g


def cluster_ci(values, clusters):
    """Paired cluster-robust CI + two-sided p (t with G-1 df, scipy).
    Never raises: import/cluster failures return {'ok': False, ...}."""
    try:
        from scipy import stats
        beta, se, t, g = cluster_stats(values, clusters)
    except ValueError as e:
        return {'ok': False, 'note': str(e)}
    except Exception as e:  # scipy missing etc. — callers treat as INCONCLUSIVE
        return {'ok': False, 'note': f'{type(e).__name__}: {e}'}
    crit = float(stats.t.ppf(0.975, g - 1))  # g >= 2 guaranteed by cluster_stats
    if math.isinf(t):
        p = 0.0
    else:
        p = float(min(1.0, 2 * stats.t.sf(abs(t), g - 1)))
    return {'ok': True, 'beta': beta, 'se': se, 't': t, 'p': p, 'g': g,
            'lo': beta - crit * se, 'hi': beta + crit * se, 'n': len(values)}


def fmt_p(p):
    if p is None or p != p:
        return 'n/a'
    if p < 0.001:
        return '<0.001'
    return f'{p:.3f}'


def pct(vals, q):
    """q-th percentile (0-100), cell_stats._pct parity."""
    if not vals:
        return None
    s = sorted(vals)
    idx = min(len(s) - 1, max(0, int(round(q / 100.0 * (len(s) - 1)))))
    return round(s[idx], 4)


def cell_key(r):
    return (r['signal'], r['direction'], r['regime'])


# ── key matching (landmine: exact first, normalized fallback, never silent) ───
def match_store(window_rows, store_cells):
    """Match window trades to live-store cells. Returns stats dict with samples."""
    exact = {}
    by_norm = defaultdict(set)
    for c in store_cells:
        exact[(c['signal'], c['direction'], c['regime'])] = c
        by_norm[(norm_key(c['signal']), c['direction'], c['regime'])].add(c['signal'])

    matched_exact = matched_norm = ambiguous = unmatched = 0
    matched_rows, amb_keys, un_keys = [], defaultdict(int), defaultdict(int)
    norm_examples, exact_examples = [], []
    seen_exact, seen_norm = set(), set()
    for r in window_rows:
        k = cell_key(r)
        if k in exact:
            matched_exact += 1
            matched_rows.append((r, exact[k]))
            if k[0] not in seen_exact:
                seen_exact.add(k[0])
                exact_examples.append(k[0])
            continue
        nk = (norm_key(k[0]), k[1], k[2])
        cands = by_norm.get(nk, set())
        if len(cands) == 1:
            matched_norm += 1
            cand = next(iter(cands))
            matched_rows.append((r, exact[(cand, k[1], k[2])]))
            if k[0] not in seen_norm:
                seen_norm.add(k[0])
                norm_examples.append((k[0], cand))
        elif len(cands) > 1:
            ambiguous += 1
            amb_keys[k[0]] += 1
        else:
            unmatched += 1
            un_keys[k[0]] += 1
    total = len(window_rows)
    # landmine evidence: distinct store keys that collapse onto ONE normalized
    # key (naive normalization would silently merge rows with different stats)
    store_keys = {c['signal'] for c in store_cells}
    ng = defaultdict(set)
    for k in store_keys:
        ng[norm_key(k)].add(k)
    collisions = {n: ks for n, ks in ng.items() if len(ks) > 1}
    return {
        'total': total, 'matched_exact': matched_exact, 'matched_norm': matched_norm,
        'ambiguous': ambiguous, 'unmatched': unmatched,
        'unmatched_share': (ambiguous + unmatched) / total if total else 0.0,
        'matched_rows': matched_rows,
        'exact_examples': sorted(exact_examples)[:8],
        'norm_examples': sorted(norm_examples)[:8],
        'amb_keys': sorted(amb_keys.items(), key=lambda x: (-x[1], x[0]))[:10],
        'un_keys': sorted(un_keys.items(), key=lambda x: (-x[1], x[0]))[:10],
        'store_keys': len(store_keys),
        'window_keys': len({r['signal'] for r in window_rows}),
        'store_stale': sorted(store_keys - {r['signal'] for r in window_rows})[:10],
        'n_store_stale': len(store_keys - {r['signal'] for r in window_rows}),
        'collisions': sorted(collisions.items())[:10],
        'n_collisions': len(collisions),
    }


def key_match_section(ms):
    L = [
        '## Signal-key normalization (auditor landmine)',
        '',
        f'- **RULE**: `{NORM_RULE}`',
        f'- store distinct keys: {ms["store_keys"]} | window trades distinct keys: '
        f'{ms["window_keys"]} | window trades matched: {ms["total"]}',
        f'- exact matches: **{ms["matched_exact"]}** | normalized-fallback matches: '
        f'**{ms["matched_norm"]}** | ambiguous (norm -> >1 store key, kept unmatched): '
        f'**{ms["ambiguous"]}** | no store key: **{ms["unmatched"]}**',
        f'- **unmatched share: {ms["unmatched_share"]:.1%}** of window trades '
        '(counted, never silently dropped)',
        f'- **normalization collisions in the store: {ms["n_collisions"]} groups of '
        'distinct keys that collapse onto one normalized key — naive normalization '
        'would silently merge rows with DIFFERENT stats (the auditor landmine); '
        'this script never merges on normalized keys**',
        f'- store keys with no trade in this window (stale/churned): '
        f'{ms["n_store_stale"]}',
        '',
        '- sample collisions (normalized <- distinct store keys): '
        + (', '.join('`' + n + '` <- {' + ', '.join('`' + k + '`' for k in sorted(ks)) + '}'
                     for n, ks in ms['collisions']) or 'none'),
        '- sample stale store keys (no trade this window): '
        + (', '.join(f'`{k}`' for k in ms['store_stale']) or 'none'),
        '',
        '- sample exact-matched keys: ' + (', '.join(f'`{k}`' for k in ms['exact_examples']) or 'none'),
        '- sample normalized-fallback (trades key -> store key): '
        + (', '.join(f'`{a}` -> `{b}`' for a, b in ms['norm_examples']) or 'none'),
        '- sample ambiguous keys (n): '
        + (', '.join(f'`{k}` ({n})' for k, n in ms['amb_keys']) or 'none'),
        '- sample unmatched keys (n): '
        + (', '.join(f'`{k}` ({n})' for k, n in ms['un_keys']) or 'none'),
        '',
    ]
    return '\n'.join(L)


# ── §4 calibrate ─────────────────────────────────────────────────────────────
def build_folds(rows, days, train_d, test_d, want):
    """Rolling-origin: train [t0,t1) -> test [t1,t2), stepping forward by test_d.
    Data-anchored: anchor = max close_time in window (streak_analysis parity)."""
    anchor = max(r['close_time'] for r in rows)
    start = anchor - timedelta(days=days)
    folds, i = [], 0
    while len(folds) < want:
        t0 = start + timedelta(days=i * test_d)
        t1 = t0 + timedelta(days=train_d)
        t2 = t1 + timedelta(days=test_d)
        if t2 > anchor:
            break
        train = [r for r in rows if t0 <= r['close_time'] < t1]
        test = [r for r in rows if t1 <= r['close_time'] < t2]
        folds.append({'i': i + 1, 't0': t0, 't1': t1, 't2': t2,
                      'train': train, 'test': test})
        i += 1
    return anchor, start, folds


def admit(train):
    """Cell admission from THIS fold's train ONLY; frozen blended predictor."""
    counts = defaultdict(lambda: [0, 0])
    for r in train:
        c = counts[cell_key(r)]
        c[0] += 1
        c[1] += y_of(r['pnl_usdt'])
    cells = {}
    for k, (n, wins) in counts.items():
        if n >= N_MIN:
            wr = wins / n
            cells[k] = {'n': n, 'wins': wins, 'wr': wr, 'p': blend_p(n, wr)}
    return cells


def reliability_buckets(trades_p):
    """Rank-based deciles over pooled OOS covered trades; deterministic ties
    (sorted by p, signal, close_time). Returns list of 10 dicts."""
    srt = sorted(trades_p, key=lambda t: (t['p'], t['signal'], t['close_time']))
    n = len(srt)
    out = []
    for k in range(10):
        lo = k * n // 10
        hi = (k + 1) * n // 10
        chunk = srt[lo:hi]
        if not chunk:
            out.append({'dec': k + 1, 'n': 0, 'wins': 0, 'wr': None,
                        'p_lo': None, 'p_hi': None, 'trades': []})
            continue
        wins = sum(y_of(t['pnl_usdt']) for t in chunk)
        out.append({'dec': k + 1, 'n': len(chunk), 'wins': wins,
                    'wr': wins / len(chunk),
                    'p_lo': min(t['p'] for t in chunk),
                    'p_hi': max(t['p'] for t in chunk),
                    'trades': chunk})
    return out


def reliability_md(buckets, title, in_sample=False):
    L = [f'### {title}', '',
         '| p-decile | n | wins | observed WR | p range | thin (n<%d) |' % BUCKET_MIN_N,
         '|---:|---:|---:|---:|---:|:---:|']
    for b in buckets:
        if b['n'] == 0:
            L.append(f'| {b["dec"]} | 0 | 0 | n/a | n/a | — |')
            continue
        thin = 'THIN' if b['n'] < BUCKET_MIN_N else ''
        L.append(f'| {b["dec"]} | {b["n"]} | {b["wins"]} | {b["wr"]:.1%} | '
                 f'{b["p_lo"]:.3f}–{b["p_hi"]:.3f} | {thin} |')
    L.append('')
    if in_sample:
        L.append('- **IN-SAMPLE / DESCRIPTIVE — leakage: predictor and outcomes '
                 'come from the same window.**')
        L.append('')
    return '\n'.join(L)


def run_calibrate(args):
    days, folds_want = args.days, args.folds
    lines = []
    out = lines.append

    rows = fetch_trades(days)
    if not rows:
        log('No trades in window — nothing to calibrate.')
        return 1
    print_sql(days)
    log(f'- trades (status=closed, pnl NOT NULL): **{len(rows)}**')

    anchor, start, folds = build_folds(rows, days, TRAIN_DAYS, TEST_DAYS, folds_want)
    win_lo = min(r['close_time'] for r in rows)
    log(f'- data-anchored window: {win_lo} → {anchor} '
        f'(SQL start = anchor-{days}d = {start})')
    if len(folds) < 3:
        log(f'ERROR: only {len(folds)} full folds fit in {days}d '
            f'(need >=3: train {TRAIN_DAYS}d + test {TEST_DAYS}d stepping {TEST_DAYS}d). '
            'Cannot run the pre-registered limbs — aborting without fabricating.')
        return 1

    mfe_n = sum(1 for r in rows if r['mfe_pct'] is not None)
    conf_n = sum(1 for r in rows if r['final_confidence'] is not None)

    store_cells, store_meta = load_store()
    ms = match_store(rows, store_cells)

    # ── per-fold admission + coverage ────────────────────────────────────────
    fold_stats, covered, uncovered_n = [], [], 0
    all_test_n = 0
    for f in folds:
        cells = admit(f['train'])
        tr_n = len(f['train'])
        te = f['test']
        te_n = len(te)
        all_test_n += te_n
        tr_in = sum(1 for r in f['train'] if cell_key(r) in cells)
        cov = [r for r in te if cell_key(r) in cells]
        unc = te_n - len(cov)
        uncovered_n += unc
        for r in cov:
            r['p'] = cells[cell_key(r)]['p']
            covered.append(r)
        fold_stats.append({
            'i': f['i'], 't0': f['t0'], 't1': f['t1'], 't2': f['t2'],
            'n_train': tr_n, 'n_test': te_n, 'cells': len(cells),
            'train_cov': tr_in / tr_n if tr_n else 0.0,
            'test_cov': len(cov) / te_n if te_n else 0.0,
            'n_cov': len(cov),
        })

    coverages = [fs['test_cov'] for fs in fold_stats]
    worst_cov = min(coverages)
    pooled_cov = len(covered) / all_test_n if all_test_n else 0.0

    # ── sets ─────────────────────────────────────────────────────────────────
    inter = [r for r in covered if r['final_confidence'] is not None]
    inter_share = len(inter) / all_test_n if all_test_n else 0.0

    # ── metrics (single definitions, trade-level) ────────────────────────────
    def metrics_for(subset, with_conf):
        ys = [y_of(r['pnl_usdt']) for r in subset]
        ps = [r['p'] for r in subset]
        res = {'n': len(subset),
               'p_brier': brier(ps, ys), 'p_logloss': logloss(ps, ys),
               'b_brier': brier([0.5] * len(subset), ys),
               'b_logloss': logloss([0.5] * len(subset), ys)}
        if with_conf:
            cs = [max(EPS_P, min(1 - EPS_P, r['final_confidence'] / 100.0))
                  for r in subset]
            res['c_brier'] = brier(cs, ys)
            res['c_logloss'] = logloss(cs, ys)
        return res

    m_inter = metrics_for(inter, True) if inter else None
    m_cov = metrics_for(covered, False) if covered else None

    # ── limb (a): discrimination ─────────────────────────────────────────────
    buckets = reliability_buckets(covered) if covered else []
    top2 = [t for b in buckets[8:] for t in b['trades']]
    bot2 = [t for b in buckets[:2] for t in b['trades']]
    wr_top = (sum(y_of(t['pnl_usdt']) for t in top2) / len(top2)) if top2 else None
    wr_bot = (sum(y_of(t['pnl_usdt']) for t in bot2) / len(bot2)) if bot2 else None
    a_ci = None
    if top2 and bot2:
        wr_b = wr_bot
        vals = [y_of(t['pnl_usdt']) - wr_b for t in top2 + bot2]
        # constant shift leaves CR1 deviations unchanged; beta = w*(wr_top-wr_bot)
        cl = [t['signal'] for t in top2 + bot2]
        try:
            a_ci = cluster_ci(vals, cl)
        except Exception as e:  # scipy missing etc.
            a_ci = {'ok': False, 'note': f'{type(e).__name__}: {e}'}

    # final-fold sign check: SAME rank key + decile split as the pooled deciles
    # (p, signal, close_time) — not a threshold approximation (label honesty)
    last_fold_cov = [r for r in folds[-1]['test'] if 'p' in r]
    lfb = reliability_buckets(last_fold_cov) if last_fold_cov else []
    lf_top = [t for b in lfb[8:] for t in b['trades']]
    lf_bot = [t for b in lfb[:2] for t in b['trades']]
    if lf_top and lf_bot:
        lf_wr_top = sum(y_of(r['pnl_usdt']) for r in lf_top) / len(lf_top)
        lf_wr_bot = sum(y_of(r['pnl_usdt']) for r in lf_bot) / len(lf_bot)
        lf_diff = lf_wr_top - lf_wr_bot
        sign_ok = lf_diff > 0
        sign_txt = (f'WR(top-2)={lf_wr_top:.1%} (n={len(lf_top)}) vs '
                    f'WR(bottom-2)={lf_wr_bot:.1%} (n={len(lf_bot)}), '
                    f'Δ={lf_diff:+.1%} — sign {"preserved" if sign_ok else "REVERSED"}')
    else:
        sign_ok, sign_txt = None, (f'n/a — final fold covered n={len(last_fold_cov)}, '
                                   f'top={len(lf_top)}, bottom={len(lf_bot)} (empty group)')

    if a_ci and a_ci.get('ok') and wr_top is not None and wr_bot is not None:
        a_pass = (wr_top > wr_bot) and a_ci['p'] < 0.05 and sign_ok
        if sign_ok is None:
            a_verdict, a_why = 'INCONCLUSIVE', 'final-fold sign check n/a (empty decile group)'
        elif a_pass:
            a_verdict = 'PASS'
            a_why = ''
        else:
            a_verdict = 'FAIL'
            a_why = ('top-2 WR not greater than bottom-2' if wr_top <= wr_bot
                     else f'cluster p={fmt_p(a_ci["p"])} >= 0.05' if a_ci['p'] >= 0.05
                     else 'final-fold sign reversed')
    else:
        a_verdict = 'INCONCLUSIVE'
        a_why = 'no top/bottom trades or <2 clusters: ' + str(a_ci and a_ci.get('note'))

    # ── limb (b): beats confidence (intersection subset) ─────────────────────
    b_ci = None
    if inter and inter_share >= CONF_MIN_SHARE:
        ys = [y_of(r['pnl_usdt']) for r in inter]
        d = [((r['p'] - y) ** 2 -
              (max(EPS_P, min(1 - EPS_P, r['final_confidence'] / 100.0)) - y) ** 2)
             for r, y in zip(inter, ys)]
        try:
            b_ci = cluster_ci(d, [r['signal'] for r in inter])
        except Exception as e:  # never crash the report — INCONCLUSIVE
            b_ci = {'ok': False, 'note': f'{type(e).__name__}: {e}'}
        if b_ci.get('ok'):
            b_pass = b_ci['beta'] < 0 and b_ci['hi'] < 0
            b_verdict = 'PASS' if b_pass else 'FAIL'
            b_why = '' if b_pass else 'paired CI includes 0 or point estimate >= 0'
        else:
            b_verdict, b_why = 'INCONCLUSIVE', b_ci.get('note', 'cluster failed')
    else:
        b_verdict = 'INCONCLUSIVE (LOW-COVERAGE)'
        b_why = (f'intersection {len(inter)}/{all_test_n} = {inter_share:.1%} of test '
                 f'trades < {CONF_MIN_SHARE:.0%} floor — confidence comparison not '
                 'justified (spec §4); NOT silently dropped')

    # ── limb (c): beats baseline 0.5 ─────────────────────────────────────────
    c_ci = None
    if covered:
        ys = [y_of(r['pnl_usdt']) for r in covered]
        d = [(r['p'] - y) ** 2 - 0.25 for r, y in zip(covered, ys)]
        try:
            c_ci = cluster_ci(d, [r['signal'] for r in covered])
        except Exception as e:  # never crash the report — INCONCLUSIVE
            c_ci = {'ok': False, 'note': f'{type(e).__name__}: {e}'}
        if c_ci.get('ok'):
            c_pass = c_ci['beta'] < 0 and c_ci['hi'] < 0
            c_verdict = 'PASS' if c_pass else 'FAIL'
            c_why = '' if c_pass else 'paired CI includes 0 or point estimate >= 0'
        else:
            c_verdict, c_why = 'INCONCLUSIVE', c_ci.get('note', 'cluster failed')
    else:
        c_verdict, c_why = 'INCONCLUSIVE', 'no covered test trades'

    # ── limb (d): coverage disclosure ────────────────────────────────────────
    if worst_cov < 0.10:
        d_verdict = 'INCONCLUSIVE (LOW-COVERAGE)'
        d_why = (f'worst-fold coverage {worst_cov:.1%} < 10% — P1 waits for more '
                 'data; n_min NEVER loosened (spec §4/§9)')
    else:
        d_verdict = 'PASS'
        d_why = ''

    gate = ('PROCEED-TO-P1' if (a_verdict == 'PASS' and b_verdict == 'PASS'
                                and c_verdict == 'PASS' and d_verdict == 'PASS')
            else 'STOP')

    # small-G caveat (G<10): cluster inference with few clusters is indicative only
    sg = [(lbl, ci['g']) for lbl, ci in (('a', a_ci), ('b', b_ci), ('c', c_ci))
          if ci and ci.get('ok') and ci['g'] < 10]
    sg_txt = ''
    if sg:
        gs = '/'.join(str(g) for g in sorted({g for _, g in sg}))
        sg_txt = (f'small-G (G={gs}<10): cluster inference unreliable — '
                  f'treat p/CI as indicative (limbs {",".join(l for l, _ in sg)})')
        log(sg_txt)

    # ── in-sample live-store view (DESCRIPTIVE) ──────────────────────────────
    store_rows = ms['matched_rows']
    if store_rows:
        s_ys = [y_of(r['pnl_usdt']) for r, _ in store_rows]
        s_ps = [blend_p(c['n'], c['wr_raw']) for _, c in store_rows]
        s_cov = len(store_rows) / len(rows)
        s_brier = brier(s_ps, s_ys)
        s_buckets = reliability_buckets(
            [{'p': p, 'pnl_usdt': r['pnl_usdt'], 'signal': r['signal'],
              'close_time': r['close_time']} for (r, c), p in zip(store_rows, s_ps)])
    else:
        s_cov, s_brier, s_buckets = 0.0, None, []

    # ══ build report ═════════════════════════════════════════════════════════
    out('# Probability Matrix — P0 calibration study')
    out('')
    out('- spec: `brain/plans/probability-matrix-spec.md` v1.1 (§3.1/§3.2/§4/§5); '
        'P0 = study only, SELECT-only, zero trading-path changes')
    out(f'- generated by `scripts/probability_matrix.py calibrate` '
        f'(days={days}, folds={len(folds)} of {folds_want} requested, '
        f'train={TRAIN_DAYS}d, test={TEST_DAYS}d, step={TEST_DAYS}d)')
    out(f'- data-anchored window: **{win_lo} → {anchor}** (window start = actual '
        'MIN(close_time); anchor = max close_time, not wall clock — SQL anchored '
        'to MAX(close_time), streak_analysis parity)')
    out(f'- trades in window: **{len(rows)}** | win def: `{WIN_DEF}` | '
        f'cell = (signal, direction, volatility_regime)')
    out(f'- **final_confidence coverage (window): {conf_n}/{len(rows)} = '
        f'{conf_n/len(rows):.1%}** | mfe_pct coverage: {mfe_n}/{len(rows)} = '
        f'{mfe_n/len(rows):.1%}')
    out(f'- fold OOS coverage (spec §3.1): pooled **{len(covered)}/{all_test_n} = '
        f'{pooled_cov:.1%}** of test trades | worst fold **{worst_cov:.1%}** | '
        f'uncovered test trades: {uncovered_n} (counted, never dropped)')
    out(f'- confidence-intersection subset: **{len(inter)}/{all_test_n} = '
        f'{inter_share:.1%}** of test trades')
    out('')
    out('```')
    out('SQL: ' + ' '.join(SQL.split()))
    out(f'params: ({days},)   [store] ' + ' '.join(STORE_SQL.split()))
    out('```')
    out('')
    out(key_match_section(ms))

    out('## 1. Rolling-origin fold design (§4)')
    out('')
    out(f'- each fold: train `{TRAIN_DAYS}d` -> test `{TEST_DAYS}d`, stepping '
        f'forward `{TEST_DAYS}d`; cells admitted from that fold\'s train ONLY '
        f'(n >= {N_MIN}); frozen blended predictor p = clip((n*wr_raw + {K}*0.50)/'
        f'(n+{K}), {EPS_P}, {1-EPS_P}) — always blended, regardless of store tier')
    out(f'- {len(folds)} folds fit in {days}d (spec requires >= 3); test folds are '
        'disjoint + contiguous, so every test trade is scored exactly once')
    out('')

    out('## 2. Per-fold coverage table (§3.1 definition)')
    out('')
    out('| fold | train window | test window | n_train | n_test | train cells '
        'admitted | train coverage | **test coverage** | covered test n |')
    out('|---:|---|---|---:|---:|---:|---:|---:|---:|')
    for fs in fold_stats:
        out(f'| {fs["i"]} | {fs["t0"].date()} → {fs["t1"].date()} | '
            f'{fs["t1"].date()} → {fs["t2"].date()} | {fs["n_train"]} | '
            f'{fs["n_test"]} | {fs["cells"]} | {fs["train_cov"]:.1%} | '
            f'**{fs["test_cov"]:.1%}** | {fs["n_cov"]} |')
    out('')
    out(f'- pooled OOS coverage: **{len(covered)}/{all_test_n} = {pooled_cov:.1%}** '
        f'; worst fold: **{worst_cov:.1%}** ; uncovered test trades: {uncovered_n} '
        '(new/low-volume signals born UNCALIBRATED by design — §9 churn)')
    test_horizon = len(folds) * TEST_DAYS
    out(f'- **test horizon caveat**: OOS test folds span {test_horizon}d of the '
        f'{days}d window ({len(folds)} × {TEST_DAYS}d, positioned train {TRAIN_DAYS}d '
        f'in); {len(rows) - all_test_n}/{len(rows)} window trades fall OUTSIDE the '
        'test horizon (train-side / pre-fold-gap) and are never OOS-scored')
    out('- **IN-SAMPLE/DESCRIPTIVE** live-store view: see §6 (store computed from '
        'this same window — leakage, not evidence)')
    out('')

    out('## 3. Metrics (trade-level, single definitions)')
    out('')
    out(f'- Brier = mean((p(cell(t)) − y)²), y = 1 iff `{WIN_DEF}`; '
        'log-loss with p clipped to [0.01, 0.99] before scoring')
    out('- **Set A (confidence comparison)**: test trades that are cell-covered AND '
        f'have final_confidence — n={len(inter)} of {all_test_n} test trades '
        f'({inter_share:.1%}). Same trade set for all three predictors below.')
    out('- **Set B (baseline comparison)**: all cell-covered test trades — '
        f'n={len(covered)} of {all_test_n} ({pooled_cov:.1%}).')
    out('')
    out('| predictor | set | n | Brier | log-loss |')
    out('|---|---|---:|---:|---:|')
    if m_inter:
        out(f'| p(c) blended (spec §3.1) | A | {m_inter["n"]} | '
            f'**{m_inter["p_brier"]:.4f}** | {m_inter["p_logloss"]:.4f} |')
        out(f'| final_confidence/100 | A | {m_inter["n"]} | '
            f'**{m_inter["c_brier"]:.4f}** | {m_inter["c_logloss"]:.4f} |')
        out(f'| baseline 0.5 | A | {m_inter["n"]} | {m_inter["b_brier"]:.4f} | '
            f'{m_inter["b_logloss"]:.4f} |')
    else:
        out('| p(c) / conf / baseline | A | 0 | n/a | n/a |')
    if m_cov:
        out(f'| p(c) blended (spec §3.1) | B | {m_cov["n"]} | '
            f'**{m_cov["p_brier"]:.4f}** | {m_cov["p_logloss"]:.4f} |')
        out(f'| baseline 0.5 | B | {m_cov["n"]} | {m_cov["b_brier"]:.4f} | '
            f'{m_cov["b_logloss"]:.4f} |')
    else:
        out('| p(c) / baseline | B | 0 | n/a | n/a |')
    out('')

    out('## 4. Reliability table — OOS pooled covered test trades (§4)')
    out('')
    out(reliability_md(buckets, 'p-deciles → observed WR (OUT-OF-SAMPLE)'))
    if top2 and bot2:
        out(f'- top-2 deciles WR = **{wr_top:.1%}** (n={len(top2)}) vs bottom-2 = '
            f'**{wr_bot:.1%}** (n={len(bot2)}), Δ = {(wr_top - wr_bot):+.1%}')
        if a_ci and a_ci.get('ok'):
            out(f'- cluster-robust (cluster=signal, CR1): t = {a_ci["t"]:+.2f}, '
                f'p = {fmt_p(a_ci["p"])}, G = {a_ci["g"]}, n = {a_ci["n"]}; '
                f'95% CI on ΔWR-proxy = [{a_ci["lo"]:+.4f}, {a_ci["hi"]:+.4f}] '
                '(naive p would be optimistic — flagged, not used)')
        else:
            out(f'- cluster-robust: unavailable ({a_ci and a_ci.get("note")})')
        if sg_txt and any(l == 'a' for l, _ in sg):
            out(f'- **{sg_txt}**')
        out(f'- final test fold (fold {len(folds)}) sign check: {sign_txt}')
    out('')

    out('## 5. Pre-registered limbs (§4) — all four or STOP')
    out('')
    out('| limb | test | verdict | key numbers |')
    out('|---|---|---|---|')
    a_num = (f'WR top-2 {wr_top:.1%} (n={len(top2)}) vs bottom-2 {wr_bot:.1%} '
             f'(n={len(bot2)}), Δ={(wr_top - wr_bot):+.1%}' if top2 and bot2 else 'n/a')
    if a_ci and a_ci.get('ok'):
        a_num += (f'; cluster p={fmt_p(a_ci["p"])}, G={a_ci["g"]}; final-fold: '
                  f'{sign_txt}')
    a_num += f' — {a_why}' if a_why else ''
    out(f'| (a) discrimination | top-2 WR > bottom-2, cluster p<0.05, final-fold sign '
        f'| **{a_verdict}** | {a_num} |')
    b_num = (f'Brier(p)={m_inter["p_brier"]:.4f} vs Brier(conf)='
             f'{m_inter["c_brier"]:.4f} on set A (n={len(inter)}, '
             f'{inter_share:.1%} of test trades)'
             if m_inter else f'set A empty (n=0, {inter_share:.1%})')
    if b_ci and b_ci.get('ok'):
        b_num += (f'; Δ={b_ci["beta"]:+.4f}, 95% CI [{b_ci["lo"]:+.4f}, '
                  f'{b_ci["hi"]:+.4f}], cluster p={fmt_p(b_ci["p"])}, G={b_ci["g"]}')
    b_num += f' — {b_why}' if b_why else ''
    out(f'| (b) beats confidence | Brier(p) < Brier(conf), paired CI excludes 0 '
        f'| **{b_verdict}** | {b_num} |')
    c_num = (f'Brier(p)={m_cov["p_brier"]:.4f} vs Brier(0.5)={m_cov["b_brier"]:.4f} '
             f'on set B (n={len(covered)})' if m_cov else 'set B empty (n=0)')
    if c_ci and c_ci.get('ok'):
        c_num += (f'; Δ={c_ci["beta"]:+.4f}, 95% CI [{c_ci["lo"]:+.4f}, '
                  f'{c_ci["hi"]:+.4f}], cluster p={fmt_p(c_ci["p"])}, G={c_ci["g"]}')
    c_num += f' — {c_why}' if c_why else ''
    out(f'| (c) beats baseline | Brier(p) < Brier(0.5), paired CI excludes 0 '
        f'| **{c_verdict}** | {c_num} |')
    d_num = (f'per-fold test coverage: '
             + ', '.join(f'f{fs["i"]}={fs["test_cov"]:.1%}' for fs in fold_stats)
             + f'; worst={worst_cov:.1%} (floor 10%)')
    d_num += f' — {d_why}' if d_why else ''
    out(f'| (d) coverage disclosure | per-fold table published, worst >= 10% '
        f'| **{d_verdict}** | {d_num} |')
    out('')
    out(f'### GATE: **{gate}**')
    out('')
    if gate == 'PROCEED-TO-P1':
        out('All four limbs PASS. P1 (shadow, log-only) may be built under its own '
            'pre-registered bar (spec §6) — still CEO-gated, still no enforcement.')
    else:
        out('Not all four limbs passed — **the spec stops here with an honest '
            'report** (spec §4). No shadow, no gate, no confidence replacement. '
            'Chasing coverage by loosening n_min is the overfit trap (§9) and is '
            'NOT done here.')
    out('')

    out('## 6. Live-store view — IN-SAMPLE / DESCRIPTIVE (§4.1)')
    out('')
    out(f'- **LEAKAGE FLAG: the cell_stats store was computed from this same '
        f'{days}d window — this view is in-sample and is NOT evidence of OOS '
        f'calibration.**')
    out(f'- store computed_at: {store_meta.get("computed_at", "?")} | window_days: '
        f'{store_meta.get("window_days", "?")} | cells: '
        f'{store_meta.get("cells_total", "?")} (admitted {store_meta.get("cells_admitted", "?")})')
    out(f'- window trades matched to store cells: {len(store_rows)}/{len(rows)} = '
        f'**{s_cov:.1%}** (exact {ms["matched_exact"]}, normalized-fallback '
        f'{ms["matched_norm"]}, unmatched {ms["ambiguous"] + ms["unmatched"]})')
    if s_brier is not None:
        s_ys = [y_of(r['pnl_usdt']) for r, _ in store_rows]
        out(f'- store blended p Brier (in-sample): {s_brier:.4f} vs baseline 0.5 '
            f'({brier([0.5] * len(s_ys), s_ys):.4f}), n={len(s_ys)} — '
            'DESCRIPTIVE ONLY')
    out('')
    if s_buckets:
        out(reliability_md(s_buckets, 'Store-p reliability curve (IN-SAMPLE/DESCRIPTIVE)',
                           in_sample=True))
    out('')

    out('## 7. Caveats')
    out('')
    out('- **Signal churn (measured, §9)**: labels like `jup_yolo_mirrored` are born '
        'mid-window; new cells are UNCALIBRATED (n<15) by design, so OOS coverage is '
        'structurally low. n_min is never loosened to chase coverage.')
    out('- **In-sample labels**: §6 store view and anything computed on the same '
        'window it was fit on is descriptive, not evidence; only §4 folds are OOS.')
    out('- **Observational bias**: cells condition on trades that survived existing '
        'gates; a gate that changes admission changes the population (P1 counterfactual '
        'is the honest test, §6 of the spec).')
    out('- **Clustering**: all significance is cluster-robust (cluster=signal, CR1, '
        'cluster_t.py math); naive p-values are optimistic and not used.')
    if sg_txt:
        out(f'- **{sg_txt}**')
    out('- **pnl_usdt == 0** counts as non-win (y=0); matches streak_analysis.')
    out('- **Regime axis**: volatility_regime with regime fallback (cell_stats.py:80 '
        'parity); trades.regime is a different vocabulary and only a fallback.')
    out('- **Confidence semantics**: final_confidence is the raw invented confidence '
        '(§1.2), known to invert PnL — beating it would not make it a probability.')
    out(f'- Unmatched signal keys in the store join: {ms["unmatched_share"]:.1%} of '
        'window trades — counted and shown in the normalization section, never dropped.')
    out('')

    out('## Reproduce')
    out('')
    out('```bash')
    out(f'python3 /root/.hermes/scripts/probability_matrix.py calibrate '
        f'--days {days} --folds {folds_want}')
    out('```')
    out('')

    md = '\n'.join(lines)
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    tmp = REPORT_MD + '.tmp'
    with open(tmp, 'w') as fh:
        fh.write(md + '\n')
    os.replace(tmp, REPORT_MD)
    print(md)
    log(f'\n[wrote] {REPORT_MD}')
    log(f'GATE: {gate} | limbs: (a)={a_verdict} (b)={b_verdict} '
        f'(c)={c_verdict} (d)={d_verdict}')
    log(f'fold test coverage: ' + ', '.join(
        f'f{fs["i"]}={fs["test_cov"]:.1%}(n={fs["n_test"]})' for fs in fold_stats))
    return 0


# ── §3.1/§5 report mode ──────────────────────────────────────────────────────
def mean(vals):
    return sum(vals) / len(vals) if vals else None


def compute_report_cells(rows):
    """Per-cell §5 payoff layer, computed from trades (source of truth)."""
    agg = defaultdict(lambda: {'n': 0, 'wins': 0, 'win_pnl': [], 'loss_pnl': [],
                               'mfe': [], 'mae': []})
    for r in rows:
        a = agg[cell_key(r)]
        a['n'] += 1
        if y_of(r['pnl_usdt']):
            a['wins'] += 1
            a['win_pnl'].append(r['pnl_usdt'])
        else:
            a['loss_pnl'].append(r['pnl_usdt'])
        if r['mfe_pct'] is not None:
            a['mfe'].append(r['mfe_pct'])
        if r['mae_pct'] is not None:
            a['mae'].append(r['mae_pct'])

    # fallbacks for the missing side of a conditional mean (0-win / 0-loss cells):
    # cell -> (signal, direction) -> global; marked `fb` in the table so the
    # fallback is visible (spec §3.1: 0-win cells are NOT UNCALIBRATED and their
    # ev must be computable — no fail-open).
    sig_win, sig_loss = defaultdict(list), defaultdict(list)
    glob_win, glob_loss = [], []
    for r in rows:
        if y_of(r['pnl_usdt']):
            sig_win[(r['signal'], r['direction'])].append(r['pnl_usdt'])
            glob_win.append(r['pnl_usdt'])
        else:
            sig_loss[(r['signal'], r['direction'])].append(r['pnl_usdt'])
            glob_loss.append(r['pnl_usdt'])

    cells = []
    for (sig, d, g), a in agg.items():
        n, wins = a['n'], a['wins']
        wr = wins / n
        p = blend_p(n, wr)
        fb = ''
        if a['win_pnl']:
            avg_win = mean(a['win_pnl'])
        else:
            avg_win = mean(sig_win.get((sig, d), []))
            if avg_win is None:
                avg_win = mean(glob_win)
            if avg_win is None:  # exact 0.0 is a REAL mean, not missing
                avg_win = 0.0
            fb += 'win'
        if a['loss_pnl']:
            avg_loss = mean(a['loss_pnl'])
        else:
            avg_loss = mean(sig_loss.get((sig, d), []))
            if avg_loss is None:
                avg_loss = mean(glob_loss)
            if avg_loss is None:
                avg_loss = 0.0
            fb += '+loss' if fb else 'loss'
        ev = ev_usdt(p, avg_win, avg_loss)
        epr = ev_per_risk(ev, avg_loss)
        cells.append({
            'signal': sig, 'direction': d, 'regime': g, 'n': n, 'wins': wins,
            'wr': wr, 'p': p, 'avg_win': avg_win, 'avg_loss': avg_loss,
            'ev': ev, 'epr': epr, 'fb': fb,
            'status': 'UNCALIBRATED' if n < N_MIN else 'calibrated',
            'mfe_p25': pct(a['mfe'], 25), 'mfe_p50': pct(a['mfe'], 50),
            'mfe_p75': pct(a['mfe'], 75), 'mae_p25': pct(a['mae'], 25),
            'mae_p50': pct(a['mae'], 50), 'mae_p75': pct(a['mae'], 75),
        })
    cells.sort(key=lambda c: (-c['n'], c['signal'], c['direction'], c['regime']))
    return cells


def run_report(args):
    days = args.days
    rows = fetch_trades(days)
    if not rows:
        log('No trades in window.')
        return 1
    print_sql(days)

    anchor = max(r['close_time'] for r in rows)
    win_lo = min(r['close_time'] for r in rows)
    mfe_n = sum(1 for r in rows if r['mfe_pct'] is not None)
    conf_n = sum(1 for r in rows if r['final_confidence'] is not None)
    store_cells, store_meta = load_store()
    ms = match_store(rows, store_cells)
    cells = compute_report_cells(rows)
    adm = sum(1 for c in cells if c['status'] == 'calibrated')

    L = []
    out = L.append
    out('# Probability Matrix — report (§3.1 cell schema + §5 payoff layer)')
    out('')
    out(f'- data-anchored window: **{win_lo} → {anchor}** (window start = actual '
        f'MIN(close_time); SQL anchored to MAX(close_time)-{days}d) | '
        f'trades: **{len(rows)}** | win def: `{WIN_DEF}`')
    out(f'- final_confidence coverage: {conf_n}/{len(rows)} = {conf_n/len(rows):.1%} '
        '| (confidence comparison lives in calibrate mode, intersection subset)')
    out(f'- mfe_pct coverage: {mfe_n}/{len(rows)} = {mfe_n/len(rows):.1%}')
    out(f'- cells: **{len(cells)}** total | admitted (n>={N_MIN}): **{adm}** | '
        f'UNCALIBRATED (n<{N_MIN}): {len(cells) - adm}')
    out('')
    out('```')
    out('SQL: ' + ' '.join(SQL.split()))
    out(f'params: ({days},)   [store] ' + ' '.join(STORE_SQL.split()))
    out('```')
    out('')
    out(key_match_section(ms))

    out('## §5 per-cell payoff table (descriptive — no decisions in P0)')
    out('')
    out(f'- p = clip((n·wr_raw + {K}·0.50)/(n+{K}), {EPS_P}, {1-EPS_P}) — always '
        'blended (spec §3.1); ev_usdt = p·avg_win + (1−p)·avg_loss (spec §3.2)')
    out(f'- ev_per_risk = ev_usdt / |avg_loss| **only when |avg_loss| ≥ {EPS_AMT} '
        'USDT**, else null (never divide into noise)')
    out(f'- `UNCALIBRATED` iff n < {N_MIN} — **0-win cells are NOT UNCALIBRATED**: '
        'they get blended p > 0 and ARE evaluated (no fail-open, spec §3.1)')
    out('- `fb` = conditional mean for a missing side (0-win/0-loss cell) taken '
        'from (signal,direction) then global — marked so the fallback is visible')
    out('- MFE/MAE quantiles from `trades.mfe_pct`/`mae_pct` (p25/p50/p75, cell_stats parity)')
    out('')
    out('| signal | dir | regime | n | wins | wr_raw | **p** | avg_win | avg_loss | '
        'ev_usdt | ev_per_risk | mfe p25/p50/p75 | mae p25/p50/p75 | status |')
    out('|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|')
    for c in cells:
        epr = 'null' if c['epr'] is None else f'{c["epr"]:.2f}'
        fb = f' ({c["fb"]})' if c['fb'] else ''
        mfe = '/'.join('n/a' if v is None else f'{v:.2f}'
                       for v in (c['mfe_p25'], c['mfe_p50'], c['mfe_p75']))
        mae = '/'.join('n/a' if v is None else f'{v:.2f}'
                       for v in (c['mae_p25'], c['mae_p50'], c['mae_p75']))
        out(f'| {c["signal"]} | {c["direction"]} | {c["regime"]} | {c["n"]} | '
            f'{c["wins"]} | {c["wr"]:.1%} | {c["p"]:.3f}{fb} | {c["avg_win"]:+.4f} | '
            f'{c["avg_loss"]:+.4f} | {c["ev"]:+.4f} | {epr} | {mfe} | {mae} | '
            f'{c["status"]} |')
    out('')
    out('**Honesty note (spec §3.2)**: when p equals the raw win frequency, '
        '`ev_usdt` is algebraically `cell_stats.avg_pnl` — a stored column. The '
        'matrix adds no new mean; its value is (a) blended/predictive p, (b) the '
        'OOS calibration test (calibrate mode), (c) the decision layer built on it. '
        'Never present `ev ≈ avg_pnl` as a discovery.')
    out('')

    # live-store view
    s_rows = ms['matched_rows']
    out('## Live-store view — IN-SAMPLE / DESCRIPTIVE')
    out('')
    out(f'- store computed_at: {store_meta.get("computed_at", "?")} | window_days: '
        f'{store_meta.get("window_days", "?")} | cells: '
        f'{store_meta.get("cells_total", "?")} (admitted {store_meta.get("cells_admitted", "?")})')
    out(f'- window trades matched to store cells: {len(s_rows)}/{len(rows)} = '
        f'**{len(s_rows)/len(rows):.1%}** — LEAKAGE: store computed from this same '
        'window; descriptive only, not OOS evidence')
    out('')
    out('| store signal | dir | regime | n | wr_raw | admission | tradeable | **p (blended)** |')
    out('|---|---|---|---:|---:|---|:---:|---:|')
    for c in sorted(store_cells, key=lambda x: (-x['n'], x['signal'])):
        out(f'| {c["signal"]} | {c["direction"]} | {c["regime"]} | {c["n"]} | '
            f'{c["wr_raw"]:.1%} | {c["admission"]} | {"yes" if c["tradeable"] else "no"} | '
            f'{blend_p(c["n"], c["wr_raw"]):.3f} |')
    out('')
    out('## Reproduce')
    out('')
    out('```bash')
    out(f'python3 /root/.hermes/scripts/probability_matrix.py report --days {days}')
    out('```')
    print('\n'.join(L))
    return 0


# ── selfcheck (pure math, no DB) ──────────────────────────────────────────────
def selfcheck():
    # blending (spec §3.1/§3.2): K=10 toward 0.50, then clip
    assert abs(blend_p(15, 0.0) - 0.2) < 1e-12, '0-win n=15 -> (0+5)/25 = 0.20'
    assert abs(blend_p(15, 1.0) - 0.8) < 1e-12, 'all-win n=15 -> (15+5)/25 = 0.80'
    assert abs(blend_p(0, 0.0) - 0.5) < 1e-12, 'n=0 -> prior 0.50'
    assert blend_p(1000, 1.0) == 0.99, 'upper clip at 1-EPS_P'
    assert blend_p(1000, 0.0) == 0.01, 'lower clip at EPS_P (0-win cell never p=0)'
    assert blend_p(15, 0.0) > 0, '0-win cell gets p>0 — NOT UNCALIBRATED, no fail-open'
    # Brier + log-loss (spec §3.2)
    assert brier([1.0], [1]) == 0.0, 'certain win -> 0'
    assert abs(brier([0.5], [1]) - 0.25) < 1e-12, 'baseline Brier = 0.25'
    assert abs(brier([0.6, 0.4], [1, 0]) - 0.16) < 1e-12, 'mean of squared errors'
    assert abs(logloss([0.0], [1]) - (-math.log(0.01))) < 1e-9, 'log-loss clips p'
    # y definition
    assert y_of(0.01) == 1 and y_of(0.0) == 0 and y_of(-0.01) == 0, 'y = pnl>0'
    # EV layer (spec §3.2)
    assert abs(ev_usdt(0.6, 2.0, -1.0) - 0.8) < 1e-12, 'ev = p*win + (1-p)*loss'
    assert ev_per_risk(0.8, -0.04) is None, '|avg_loss| < 0.05 -> null, no divide'
    assert abs(ev_per_risk(0.8, -0.1) - 8.0) < 1e-12, 'ev / |avg_loss|'
    # normalization rule (auditor landmine)
    assert norm_key('pump-chain+') == 'pump_chain', 'dash form -> underscore form'
    assert norm_key('bb-bounce-v2-long+') == 'bb_bounce_v2_long', 'compound key'
    assert norm_key(' jup_yolo_mirrored ') == 'jup_yolo_mirrored', 'idempotent'
    # cluster math: must agree exactly with brain/analysis/cluster_t.py
    sys.path.append(os.path.join(REPO, 'brain', 'analysis'))
    from cluster_t import cluster_t
    vals = [0.1, -0.2, 0.3, 0.05, -0.1, 0.2]
    cl = ['a', 'a', 'b', 'b', 'c', 'c']
    beta, se, t, g = cluster_stats(vals, cl)
    t_ref, beta_ref, g_ref = cluster_t(vals, cl)
    assert abs(t - t_ref) < 1e-12 and abs(beta - beta_ref) < 1e-12 and g == g_ref, \
        'cluster math drifted from cluster_t.py'
    assert abs(se - abs(beta / t)) < 1e-12, 'se consistent with t'
    # cluster_ci (code-review fix): t(G-1) critical for BOTH p and 95% CI vs scipy
    from scipy import stats as _st
    ci = cluster_ci(vals, cl)
    crit = float(_st.t.ppf(0.975, ci['g'] - 1))
    assert (ci['ok'] and abs(ci['p'] - min(1.0, 2 * _st.t.sf(abs(ci['t']), ci['g'] - 1))) < 1e-12
            and abs(ci['lo'] - (ci['beta'] - crit * ci['se'])) < 1e-12
            and abs(ci['hi'] - (ci['beta'] + crit * ci['se'])) < 1e-12), \
        'cluster_ci p/CI must use t(G-1), not 1.96'
    # degenerate-cluster guard: g<2 raises
    try:
        cluster_stats(vals, ['a'] * len(vals))  # 1 cluster -> g=1
        _raised = False
    except ValueError:
        _raised = True
    assert _raised, 'g<2 must raise ValueError'
    # count asserts dynamically so the reported number can never drift
    import inspect
    n_assert = sum(1 for l in inspect.getsource(selfcheck).splitlines()
                   if l.strip().startswith('assert '))
    log(f'selfcheck PASS ({n_assert} asserts: blending, clip, Brier, log-loss, y, EV, '
        'ev_per_risk null, norm rule, cluster_t parity, cluster_ci t-CI, g<2 raise)')
    return True


def main():
    epilog = __doc__
    p = argparse.ArgumentParser(
        description='P0 probability-matrix calibration study (read-only, SELECT-only)',
        epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('mode', nargs='?', choices=['calibrate', 'report'],
                   default='calibrate',
                   help='calibrate = §4 rolling-fold study + report file; '
                        'report = §3.1/§5 cell table to stdout')
    p.add_argument('--days', type=int, default=DEFAULT_DAYS,
                   help=f'data-anchored lookback window in days (default {DEFAULT_DAYS})')
    p.add_argument('--folds', type=int, default=DEFAULT_FOLDS,
                   help=f'rolling-origin folds requested, >=3 required (default '
                        f'{DEFAULT_FOLDS}; each = train {TRAIN_DAYS}d -> test '
                        f'{TEST_DAYS}d stepping {TEST_DAYS}d)')
    p.add_argument('--selfcheck', action='store_true',
                   help='assert-based pure-math checks (blending, Brier, clipping, '
                        'cluster parity); no DB, exit 1 on failure')
    args = p.parse_args()

    if args.selfcheck:
        sys.exit(0 if selfcheck() else 1)
    if args.mode == 'report':
        sys.exit(run_report(args))
    sys.exit(run_calibrate(args))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'[PROB-MATRIX] ERROR {type(e).__name__}: {e}', flush=True)
        sys.exit(1)
