#!/usr/bin/env python3
"""Direction Matrix v1 — BTC P(up/side/down) per horizon, rolling, self-calibrating.

Spec: brain/plans/direction-matrix-spec.md (v1.0, operator-ordered 2026-11-22).
Informational only — no trading-path consumer (spec §2.5).

FORMULAS (before any data — spec §2.1/§2.2/§2.3/§2.5):
  label   r = close(t+H)/close(t) - 1        t = base-tier bar CLOSE time
          up   if r >=  eps_H                down if r <= -eps_H        else side
          eps_H = 5 bps * sqrt(H_min/15)  ->  15m: 5 bps, 1h: 10 bps, 4h: 20 bps
          (spec-fixed deadband table; labels stable across retrains)
  feats   per TF in {5m,15m,1h,4h}, numbers only (never the skill's +-point heuristic):
          macd_hist_sign, macd_hist_slope_sign (EMA8-EMA50 vs signal, hist slope),
          rsi14, z20, bb_pos(20,2), vol_ratio(20), ema50_dist_pct, ema200_dist_pct,
          ema300_side, slope20_pct (linreg slope sign 20, kept as signed magnitude),
          mom{1h,4h,24h}z = return over window / rolling-20 std of that return
            (tier too coarse for a window -> omitted: 4h tier has no 1h momentum),
          1h_chop24 = hourly EMA300 flips in last 24h >= 2 (chop FLAG as a feature),
          votes_{bull,bear,neutral} = counts across the 4 TFs
            (bull = macd_hist_sign>0 AND slope20_pct>0; bear mirrors; else neutral),
          tod_sin/tod_cos = hour-of-day (UTC) sin/cos.
          1m features OMITTED (spec allows): 1m depth ~30d leaves no warmup headroom
          for EMA200/300 at window start and would push features past the 40-70 target.
  model   sklearn Pipeline: StandardScaler -> LogisticRegression(C=1.0, L2, lbfgs,
          random_state=42), multinomial, fit PER HORIZON on a 30d rolling window of
          closed candles; retrain hourly (systemd timer).
  brier   Brier = mean_i sum_c (p_ic - y_ic)^2      (multiclass, 3 classes, range 0..2)
          logloss = mean_i -log(p_i[actual])        (clipped at 1e-15)
  gate    walk-forward inside the window: train first 80% -> test last 20%
          (k = 20% of window), per horizon, never pooled:
            (a) Brier_model - Brier_base < 0 with day-cluster-robust 95% t-CI
                excluding 0; base-rate predictor = TRAIN class frequencies.
            (b) calibration-in-the-large: max_c |mean p_c - freq_c(test)| <= 0.05;
                top decile by p_up: day-cluster 95% CI of the empirical up-frequency
                contains the claimed mean p_up.
            (c) n disclosed per horizon; 4h judged alone. UNSTABLE-LOW-N if n < 300.
          All three -> VALIDATED, else UNVALIDATED (status: data/dir_matrix_state.json).
  resolve a call matures when ts + H < now: join realized class from the same local
          candle tier (SELECT-only); hit = argmax(p) == actual.

Reproduce (one-liners, every mode):
  python3 scripts/dir_matrix.py --selfcheck
  python3 scripts/dir_matrix.py train
  python3 scripts/dir_matrix.py predict            # hourly timer mode
  python3 scripts/dir_matrix.py resolve
  python3 scripts/dir_matrix.py score
  python3 scripts/dir_matrix.py query --horizon all
  python3 scripts/dir_matrix.py validate           # writes brain/analysis/direction-matrix-validation.md

Data: LOCAL data/candles.db ONLY (SQLite mode=ro, cursors closed in finally,
tables candles_<tf>, column ts = bar OPEN time, is_closed=1 filter). NO external API.
"""

import argparse
import hashlib
import json
import math
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from paths import CANDLES_DB, HERMES_DATA  # noqa: E402  (scripts/paths.py)

import joblib  # noqa: E402
from scipy.stats import t as student_t  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

# ───────────────────────── CLI-default constants (spec §2.1–2.3; monitor-tool
# precedent: freq/kill-line shadows keep thresholds in-script, hermes_constants
# NEVER touched) ─────────────────────────
HORIZONS = {'15m': 15, '1h': 60, '4h': 240}          # name -> H minutes
TF_MIN = {'1m': 1, '5m': 5, '15m': 15, '1h': 60, '4h': 240}
EPS_BPS = {'15m': 5.0, '1h': 10.0, '4h': 20.0}       # 5*sqrt(H_min/15), spec-fixed
FEATURE_TFS = ('5m', '15m', '1h', '4h')              # spec §2.2 TF set (1m omitted)
MOM_MIN = (60, 240, 1440)                            # momentum windows (minutes)
WINDOW_DAYS = 30                                     # rolling window (spec §2.3)
FETCH_DAYS = 41                                      # 30d window + 11d feature warmup
TEST_FRAC = 0.20                                     # walk-forward k (spec §2.5)
LOW_N_FLAG = 300                                     # UNSTABLE-LOW-N threshold (spec §2.3)
RANDOM_STATE = 42                                    # fixed -> byte-identical reruns
TOKEN = 'BTC'
CLASS_NAMES = ('up', 'side', 'down')                 # y: 0, 1, 2

MODELS_DIR = os.path.join(HERMES_DATA, 'dir_matrix_models')
PRED_FILE = os.path.join(HERMES_DATA, 'dir_matrix_predictions.jsonl')
STATE_FILE = os.path.join(HERMES_DATA, 'dir_matrix_state.json')
VALIDATION_REPORT = '/root/.hermes/brain/analysis/direction-matrix-validation.md'

EPILOG = """\
FORMULAS (spec §2.1–2.5, printed before any data):
  label:  r = close(t+H)/close(t) - 1; up if r >= eps, down if r <= -eps, else side
          eps = 5 bps * sqrt(H_min/15) -> 15m: 5 bps, 1h: 10 bps, 4h: 20 bps (fixed)
  feats:  MACD state+hist slope, RSI14, z20, BB pos(20,2), vol ratio(20),
          EMA50/200 distance %, EMA300 side, mom 1h/4h/24h vol-z, linreg slope sign 20,
          cross-TF votes, hourly EMA300 flip>=2 chop flag, hour-of-day sin/cos
          (57 features; 1m omitted for warmup depth, 4h tier omits 1h momentum)
  model:  StandardScaler -> LogisticRegression(C=1.0, L2, random_state=42), per
          horizon, 30d rolling window, retrain hourly
  brier:  mean_i sum_c (p_ic - y_ic)^2   logloss: mean_i -log(p_actual)
  gate:   walk-forward train 80% -> test 20% of window, per horizon:
            (a) Brier_model < Brier_base(train freqs), day-cluster 95% CI excludes 0
            (b) |mean p_c - freq_c| <= 0.05 (calibration-in-the-large) AND top-decile
                p_up empirical frequency CI contains claimed mean p
            (c) n disclosed; 4h alone; UNSTABLE-LOW-N if n < 300
          all three -> VALIDATED else UNVALIDATED (data/dir_matrix_state.json)

MODES (data):
  train    fit per-horizon models on the 30d rolling window, save (joblib, data/dir_matrix_models/)
  predict  slide window to now, retrain, append one call row per horizon to
           data/dir_matrix_predictions.jsonl, resolve matured calls, update state
           [--backfill N]: also log N historical hourly-anchored out-of-sample calls
           (each trained only through its own anchor) so score/resolve have data
  resolve  join realized class for matured calls only (ts + H < now)
  score    per-horizon Brier + log-loss of logged calls, reliability decile table
           (p_up decile -> empirical up frequency, n each), >=70% call hit-rate
  query    operator answer: BTC <h>: P(up)/P(side)/P(down) + reliability + status
           [--horizon 15m|1h|4h|all] [--json]
  validate pre-registered walk-forward gate -> brain/analysis/direction-matrix-validation.md
           with data-pin header (window bounds + row count + sha of candle slice)
  --selfcheck  label/eps math, no-lookahead, scaler-train-only, brier math,
           resolve join arithmetic, determinism (fixed random_state)

Data: LOCAL data/candles.db only (mode=ro, SELECT-only, cursors closed in finally).
"""


# ───────────────────────── helpers ─────────────────────────

def iso(ts):
    return datetime.fromtimestamp(int(ts), timezone.utc).strftime('%Y-%m-%d %H:%M')


def iso_z(ts):
    return datetime.fromtimestamp(int(ts), timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sq(sql, params=()):
    """SELECT-only SQLite helper (mode=ro); SQL+params printed; cursor closed in finally."""
    print(f'SQL(sq:candles.db): {" ".join(sql.split())} | params={params!r}', file=sys.stderr)
    conn = None
    cur = None
    try:
        conn = sqlite3.connect(f'file:{CANDLES_DB}?mode=ro', uri=True, timeout=10)
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


def read_calls():
    rows = []
    if not os.path.exists(PRED_FILE):
        return rows
    with open(PRED_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                print(f'[DIR-MATRIX] WARN bad jsonl line skipped: {line[:80]!r}',
                      file=sys.stderr)
    return rows


def write_calls(rows):
    tmp = PRED_FILE + '.tmp'
    with open(tmp, 'w') as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + '\n')
    os.replace(tmp, PRED_FILE)


def append_calls(rows):
    os.makedirs(os.path.dirname(PRED_FILE), exist_ok=True)
    with open(PRED_FILE, 'a') as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + '\n')


def read_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE) as f:
        return json.load(f)


def write_state(state):
    tmp = STATE_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write('\n')
    os.replace(tmp, STATE_FILE)


# ───────────────────────── data fetch (SELECT-only) ─────────────────────────

def fetch_tier(tf, min_open_ts):
    """Closed candles for one tier from local candles.db. ts = bar OPEN time."""
    iv = TF_MIN[tf]
    sql = (f'SELECT ts, open, high, low, close, volume FROM candles_{tf} '
           'WHERE token = ? AND is_closed = 1 AND ts >= ? ORDER BY ts')
    rows = sq(sql, (TOKEN, int(min_open_ts)))
    if not rows:
        raise SystemExit(f'[DIR-MATRIX] no closed rows for candles_{tf} '
                         f'(token={TOKEN}, ts>={int(min_open_ts)}) — cannot continue')
    a = np.asarray(rows, dtype=float)
    return {
        'ts': a[:, 0].astype(np.int64),
        'open': a[:, 1], 'high': a[:, 2], 'low': a[:, 3],
        'close': a[:, 4], 'volume': a[:, 5],
        'closed_at': a[:, 0].astype(np.int64) + iv * 60,   # bar close time
    }


# ───────────────────────── features (spec §2.2, numbers only) ─────────────────────────

def tier_features(tr, tf):
    """Causal feature frame for one tier. Row i uses bars <= i (bar i closed at
    closed_at[i]); no future bar is ever read. Returns DataFrame sorted by closed_at."""
    iv = TF_MIN[tf]
    c = pd.Series(tr['close'])
    v = pd.Series(tr['volume'])
    out = pd.DataFrame({'closed_at': tr['closed_at']})

    # MACD state: EMA8-EMA50 vs its signal; histogram slope sign (2-bar)
    ema8 = c.ewm(span=8, adjust=False).mean()
    ema50 = c.ewm(span=50, adjust=False).mean()
    ema200 = c.ewm(span=200, adjust=False).mean()
    ema300 = c.ewm(span=300, adjust=False).mean()
    macd = ema8 - ema50
    sig = macd.ewm(span=9, adjust=False).mean()
    hist = macd - sig
    out['macd_hist_sign'] = np.sign(hist)
    out['macd_hist_slope_sign'] = np.sign(hist - hist.shift(2))

    # RSI(14) (Wilder ewm alpha=1/14)
    delta = c.diff()
    up = delta.clip(lower=0)
    dn = (-delta).clip(lower=0)
    au = up.ewm(alpha=1 / 14, adjust=False).mean()
    ad = dn.ewm(alpha=1 / 14, adjust=False).mean()
    with np.errstate(divide='ignore', invalid='ignore'):
        rsi = 100 - 100 / (1 + au / ad)
    rsi = pd.Series(np.where(ad == 0, np.where(au == 0, 50.0, 100.0), rsi))
    out['rsi14'] = rsi

    # z-score(20), BB position(20,2), volume ratio(20-bar avg)
    zm = c.rolling(20).mean()
    zs = c.rolling(20).std()
    out['z20'] = np.where(zs > 0, (c - zm) / zs, 0.0)
    bb_up, bb_lo = zm + 2 * zs, zm - 2 * zs
    width = bb_up - bb_lo
    out['bb_pos'] = np.where(width > 0, (c - bb_lo) / width, 0.5)
    vmean = v.rolling(20).mean()
    out['vol_ratio'] = np.where(vmean > 0, v / vmean, 0.0)

    # EMA structure
    out['ema50_dist_pct'] = (c - ema50) / ema50 * 100
    out['ema200_dist_pct'] = (c - ema200) / ema200 * 100
    out['ema300_side'] = np.sign(c - ema300)

    # structure-lite: linreg slope over 20 bars (signed magnitude, per bar, % of price)
    x = pd.Series(np.arange(len(c), dtype=float))
    slope = c.rolling(20).cov(x) / x.rolling(20).var()
    out['slope20_pct'] = slope / c * 100

    # momentum: window returns z-ized by rolling-20 std of that same return
    for w in MOM_MIN:
        if w < iv:
            continue                     # tier too coarse (4h tier omits 1h momentum)
        lag = w // iv
        ret = c / c.shift(lag) - 1
        sd = ret.rolling(20).std()
        out[f'mom{w}z'] = np.where(sd > 0, ret / sd, 0.0)

    # chop flag (spec §2.2): hourly EMA300 flips in last 24h >= 2 — FEATURE only
    if tf == '1h':
        side = np.sign(c - ema300)
        flips = (side.diff().fillna(0) != 0).astype(float)
        out['chop24'] = (flips.rolling(24, min_periods=24).sum() >= 2).astype(float)

    out = out.replace([np.inf, -np.inf], np.nan)
    return out


def align_features(anchors, frames):
    """For each anchor (base-tier bar close time t), take every tier's LAST row with
    closed_at <= t (bar closed by t — no-lookahead), plus votes/time-of-day."""
    out = {}
    for tf, fr in frames.items():
        ct = fr['closed_at'].to_numpy()
        idx = np.searchsorted(ct, anchors, side='right') - 1
        idxc = np.clip(idx, 0, None)
        for col in fr.columns:
            if col == 'closed_at':
                continue
            vals = fr[col].to_numpy(dtype=float)
            out[f'{tf}_{col}'] = np.where(idx >= 0, vals[idxc], np.nan)
    X = pd.DataFrame(out)

    # cross-TF agreement votes: bull = macd_hist_sign>0 AND slope20>0 (bear mirrors)
    bull = np.zeros(len(X), dtype=int)
    bear = np.zeros(len(X), dtype=int)
    for tf in frames:
        bull += ((X[f'{tf}_macd_hist_sign'] > 0) &
                 (X[f'{tf}_slope20_pct'] > 0)).to_numpy()
        bear += ((X[f'{tf}_macd_hist_sign'] < 0) &
                 (X[f'{tf}_slope20_pct'] < 0)).to_numpy()
    X['votes_bull'] = bull
    X['votes_bear'] = bear
    X['votes_neutral'] = len(frames) - bull - bear

    hod = (np.asarray(anchors, dtype=np.int64) % 86400) // 3600     # UTC hour 0..23
    X['tod_sin'] = np.sin(2 * np.pi * hod / 24)
    X['tod_cos'] = np.cos(2 * np.pi * hod / 24)
    return X


def classify(r, horizon):
    """r -> class index: 0 up, 1 side, 2 down (eps boundary inclusive on both sides)."""
    eps = EPS_BPS[horizon] / 1e4
    if r >= eps:
        return 0
    if r <= -eps:
        return 2
    return 1


# ───────────────────────── dataset ─────────────────────────

def build_dataset(horizon, now_ts=None):
    """Fetch local candles, compute features/labels for one horizon.

    Returns dict: anchors, closes, X (DataFrame), y (-1 = label not yet known),
    r, usable (window rows with known label + no NaN features), pin (data-pin), meta.
    """
    now_ts = int(now_ts or time.time())
    base = horizon
    iv = TF_MIN[base]
    step = HORIZONS[horizon] // iv
    fetch_start = now_ts - FETCH_DAYS * 86400

    tiers = {tf: fetch_tier(tf, fetch_start) for tf in FEATURE_TFS}
    b = tiers[base]
    anchors = b['closed_at']
    closes = b['close']
    n = len(anchors)
    if n < step + 50:
        raise SystemExit(f'[DIR-MATRIX] candles_{base} too shallow: n={n}')
    T_last = int(anchors[-1])
    window_start = T_last - WINDOW_DAYS * 86400

    frames = {tf: tier_features(tiers[tf], tf) for tf in FEATURE_TFS}
    X = align_features(anchors, frames)
    # window must be covered by EVERY tier -> the LAST-starting tier binds (5m is shallow)
    tier_first = max(int(frames[tf]['closed_at'][0]) for tf in FEATURE_TFS)

    # labels (evaluation-only; t+H never a feature)
    r = np.full(n, np.nan)
    r[:n - step] = closes[step:] / closes[:n - step] - 1
    eps = EPS_BPS[horizon] / 1e4
    y = np.full(n, -1, dtype=int)
    y[(r >= eps)] = 0
    y[(r <= -eps)] = 2
    y[(r > -eps) & (r < eps)] = 1

    window_mask = anchors >= window_start
    feat_ok = X.notna().all(axis=1).to_numpy()
    usable = window_mask & (y >= 0) & feat_ok

    # data pin (§15.6): window bounds + row count + sha of the candle slice
    h = hashlib.sha256()
    widx = np.flatnonzero(window_mask)
    for i in widx:
        h.update(f'{int(b["ts"][i])},{b["open"][i]},{b["high"][i]},'
                 f'{b["low"][i]},{b["close"][i]},{b["volume"][i]}\n'.encode())
    pin = {
        'tier': f'candles_{base}',
        'window_start': int(anchors[widx[0]]),
        'window_end': int(anchors[widx[-1]]),
        'rows': int(len(widx)),
        'sha256': h.hexdigest(),
    }
    return {
        'horizon': horizon, 'iv': iv, 'step': step, 'now': now_ts,
        'anchors': anchors, 'closes': closes, 'X': X, 'y': y, 'r': r,
        'window_mask': window_mask, 'usable': usable, 'feat_ok': feat_ok,
        'T_last': T_last, 'window_start': window_start,
        'fetch_start': fetch_start, 'tier_first': tier_first, 'pin': pin,
        'feature_names': list(X.columns),
    }


def train_mask_at(ds, anchor):
    """Rows trainable AT time `anchor`: inside the 30d window ending at anchor,
    features present, and the outcome bar (anchor_j + H) already closed by anchor."""
    anchors = ds['anchors']
    n = len(anchors)
    step = ds['step']
    win = anchors >= (anchor - WINDOW_DAYS * 86400)
    win &= anchors <= anchor
    known = np.zeros(n, dtype=bool)
    idx = np.flatnonzero(ds['y'] >= 0)          # labels computable from full data
    known[idx] = anchors[np.minimum(idx + step, n - 1)] <= anchor
    return win & known & ds['feat_ok']


def fit_pipeline(X, y):
    pipe = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', LogisticRegression(C=1.0, max_iter=1000, random_state=RANDOM_STATE)),
    ])
    pipe.fit(X, y)
    return pipe


def proba3(pipe, X):
    """(n,3) probabilities in CLASS_NAMES order even if a class is absent in train."""
    p = pipe.predict_proba(X)
    out = np.zeros((X.shape[0], 3))
    for j, cls in enumerate(pipe.named_steps['clf'].classes_):
        out[:, int(cls)] = p[:, j]
    return out


def save_model(horizon, pipe, ds, trained_through, n_train):
    os.makedirs(MODELS_DIR, exist_ok=True)
    path = os.path.join(MODELS_DIR, f'{horizon}.joblib')
    joblib.dump({
        'pipeline': pipe,
        'feature_names': ds['feature_names'],
        'meta': {
            'format': 'joblib', 'horizon': horizon, 'eps_bps': EPS_BPS[horizon],
            'window_days': WINDOW_DAYS, 'random_state': RANDOM_STATE,
            'trained_through': int(trained_through), 'n_train': int(n_train),
            'window_start': int(trained_through - WINDOW_DAYS * 86400),
            'data_pin': ds['pin'], 'saved_at': iso_z(time.time()),
        },
    }, path)
    return path


def pin_line(pin):
    return (f'window=[{iso(pin["window_start"])} .. {iso(pin["window_end"])}] '
            f'rows={pin["rows"]} tier={pin["tier"]} sha256={pin["sha256"][:16]}…')


def eps_line():
    return ('ε fixed: 15m=5bps 1h=10bps 4h=20bps '
            '(ε = 5bps·√(H_min/15); spec-fixed table)')


# ───────────────────────── metrics ─────────────────────────

def brier_one(p, actual_idx):
    y = np.zeros(3)
    y[actual_idx] = 1.0
    return float(np.sum((p - y) ** 2))


def logloss_one(p, actual_idx):
    return -math.log(max(float(p[actual_idx]), 1e-15))


def cluster_ci(vals, days):
    """Day-cluster-robust 95% t-CI for the mean of `vals` (spec §2.5a/b).

    Returns (lo, hi, n_clusters, mean, tstat, pvalue) or None if <2 clusters.
    """
    s = pd.Series(np.asarray(vals, dtype=float))
    g = s.groupby(np.asarray(days)).mean()
    D = len(g)
    if D < 2:
        return None
    m = float(g.mean())
    sd = float(g.std(ddof=1))
    se = sd / math.sqrt(D)
    if se == 0:
        return (m, m, D, m, None, None)
    tc = float(student_t.ppf(0.975, D - 1))
    tstat = m / se
    pval = float(2 * (1 - student_t.cdf(abs(tstat), D - 1)))
    return (m - tc * se, m + tc * se, D, m, tstat, pval)


def day_labels(anchors):
    return np.array([datetime.fromtimestamp(int(a), timezone.utc).date().isoformat()
                     for a in anchors])


# ───────────────────────── resolve ─────────────────────────

def resolve_rows(rows, now_ts, lookup):
    """Join realized class into matured call rows. lookup(h, ts) -> (close_in,
    close_out) or None (outcome bar not closed yet). Pure: no I/O. Returns n resolved."""
    changed = 0
    for row in rows:
        if row.get('actual') is not None:
            continue
        h = row['horizon']
        if int(row['ts']) + HORIZONS[h] * 60 > now_ts:
            continue
        closes = lookup(h, int(row['ts']))
        if closes is None:
            continue
        close_in, close_out = closes
        row['actual'] = CLASS_NAMES[classify(close_out / close_in - 1, h)]
        probs = {'up': row['p_up'], 'side': row['p_side'], 'down': row['p_down']}
        row['hit'] = max(probs, key=probs.get) == row['actual']
        changed += 1
    return changed


def db_lookup(h, ts_call):
    """Outcome closes for a call: input bar closing at ts_call, outcome bar closing
    at ts_call + H. Both are closed by the time we ask (matured)."""
    iv = TF_MIN[h]
    open_in = ts_call - iv * 60
    open_out = ts_call + HORIZONS[h] * 60 - iv * 60
    sql = (f'SELECT ts, close FROM candles_{h} '
           'WHERE token = ? AND is_closed = 1 AND ts IN (?, ?) ORDER BY ts')
    got = {int(r[0]): float(r[1]) for r in sq(sql, (TOKEN, open_in, open_out))}
    if open_in in got and open_out in got:
        return (got[open_in], got[open_out])
    return None


def do_resolve(now_ts=None):
    now_ts = int(now_ts or time.time())
    rows = read_calls()
    if not rows:
        print('resolve: 0 rows in data/dir_matrix_predictions.jsonl (nothing to join)')
        return 0
    n = resolve_rows(rows, now_ts, db_lookup)
    if n:
        write_calls(rows)
    by_h = {}
    for r in rows:
        d = by_h.setdefault(r['horizon'], {'total': 0, 'resolved': 0, 'hits': 0,
                                           'ts': []})
        d['total'] += 1
        d['ts'].append(int(r['ts']))
        if r.get('actual') is not None:
            d['resolved'] += 1
            d['hits'] += int(bool(r.get('hit')))
    for h in HORIZONS:
        d = by_h.get(h)
        if not d:
            print(f'resolve {h}: n_calls=0')
            continue
        w = f'[{iso(min(d["ts"]))} .. {iso(max(d["ts"]))}]'
        print(f'resolve {h}: resolved={d["resolved"]}/{d["total"]} '
              f'(joined_now={n}) window={w} {WINDOW_DAYS}d '
              f'ε={EPS_BPS[h]:g}bps hits={d["hits"]}')
    print(f'resolve: {n} matured call(s) joined (now={iso_z(now_ts)})')
    return n


# ───────────────────────── modes ─────────────────────────

def mode_train(args):
    print(f'[DIR-MATRIX] train · {eps_line()}')
    print(f'[DIR-MATRIX] data: {CANDLES_DB} (mode=ro, SELECT-only) · '
          f'window={WINDOW_DAYS}d · C=1.0 L2 · random_state={RANDOM_STATE}')
    for h in HORIZONS:
        ds = build_dataset(h)
        mask = ds['usable']
        n = int(mask.sum())
        if n < 30:
            raise SystemExit(f'[DIR-MATRIX] {h}: only n={n} trainable rows — abort')
        X = ds['X'].to_numpy()[mask]
        y = ds['y'][mask]
        pipe = fit_pipeline(X, y)
        freqs = np.bincount(y, minlength=3) / len(y)
        path = save_model(h, pipe, ds, int(ds['anchors'][mask][-1]), n)
        print(f'train {h}: n_train={n} window=[{iso(ds["window_start"])} .. '
              f'{iso(ds["T_last"])}] {WINDOW_DAYS}d features={X.shape[1]} '
              f'eps={EPS_BPS[h]:g}bps trained_through={iso(ds["anchors"][mask][-1])} '
              f'class_freq(up/side/down)={freqs[0]:.3f}/{freqs[1]:.3f}/{freqs[2]:.3f} '
              f'pin {pin_line(ds["pin"])} -> {os.path.relpath(path, "/root/.hermes")}')
    print('[DIR-MATRIX] train done (models saved as joblib under data/dir_matrix_models/)')
    return 0


def _log_call_rows(ds, anchors_to_log, dedup):
    """Fit through each anchor and build call rows (trained only through that anchor)."""
    new_rows = []
    for a in anchors_to_log:
        a = int(a)
        if (a, ds['horizon']) in dedup:
            continue
        tmask = train_mask_at(ds, a)
        n_train = int(tmask.sum())
        if n_train < 30:
            print(f'  skip {ds["horizon"]} @{iso(a)}: n_train={n_train} < 30',
                  file=sys.stderr)
            continue
        i = int(np.searchsorted(ds['anchors'], a, side='right')) - 1
        if i < 0 or ds['anchors'][i] != a:
            print(f'  skip {ds["horizon"]}: no base-tier bar closing at {iso(a)}',
                  file=sys.stderr)
            continue
        pipe = fit_pipeline(ds['X'].to_numpy()[tmask], ds['y'][tmask])
        p = proba3(pipe, ds['X'].to_numpy()[i:i + 1])[0]
        trained_through = int(ds['anchors'][tmask][-1])
        win_start = int(ds['anchors'][tmask][0])
        span_days = (trained_through - win_start) / 86400
        new_rows.append({
            'ts': a, 'horizon': ds['horizon'],
            'p_up': round(float(p[0]), 6), 'p_side': round(float(p[1]), 6),
            'p_down': round(float(p[2]), 6),
            'trained_through': trained_through, 'n_train': n_train,
            'window': f'{span_days:.1f}d', 'eps': EPS_BPS[ds['horizon']],
        })
    return new_rows


def mode_predict(args):
    now_ts = int(time.time())
    print(f'[DIR-MATRIX] predict · {eps_line()} · now={iso_z(now_ts)}')
    rows = read_calls()
    dedup = {(int(r['ts']), r['horizon']) for r in rows}
    new_all = []
    state = read_state()
    state.setdefault('horizons', {})
    state.update({
        'updated': iso_z(now_ts), 'eps_bps': EPS_BPS, 'models_format': 'joblib',
        'window_days': WINDOW_DAYS, 'random_state': RANDOM_STATE,
        'feature_count': None, 'data_source': f'{CANDLES_DB} (mode=ro)',
    })

    for h in HORIZONS:
        ds = build_dataset(h)
        spacing = max(3600, ds['iv'] * 60)
        anchors = [ds['T_last']]
        if args.backfill > 0:
            # deepest anchor whose 30d window still starts at/after first tier data
            # (rows without feature warmup are dropped by feat_ok; n_train discloses)
            max_back = int(max(0, ds['T_last'] - ds['tier_first']
                               - WINDOW_DAYS * 86400) // spacing)
            k = min(args.backfill, max(0, max_back))
            if k < args.backfill:
                print(f'  {h}: backfill clamped {args.backfill} -> {k} '
                      f'(feature depth, fetch_start={iso(ds["fetch_start"])})')
            anchors += [ds['T_last'] - j * spacing for j in range(k, 0, -1)]
        new_rows = _log_call_rows(ds, anchors, dedup)
        new_all.extend(new_rows)

        # always retrain + save the current-anchor model (spec: predict = retrain)
        tmask = train_mask_at(ds, ds['T_last'])
        n_train = int(tmask.sum())
        if n_train < 30:
            raise SystemExit(f'[DIR-MATRIX] {h}: current n_train={n_train} < 30')
        pipe = fit_pipeline(ds['X'].to_numpy()[tmask], ds['y'][tmask])
        trained_through = int(ds['anchors'][tmask][-1])
        save_model(h, pipe, ds, trained_through, n_train)
        state['feature_count'] = len(ds['feature_names'])
        state['horizons'][h] = {
            **state['horizons'].get(h, {}),
            'last_call_ts': ds['T_last'],
            'trained_through': trained_through,
            'n_train': n_train,
            'eps_bps': EPS_BPS[h],
            'data_pin': ds['pin'],
        }
        top = next((r for r in new_rows if r['ts'] == ds['T_last']), None)
        if top is None:
            top = next((r for r in rows if r['horizon'] == h
                        and int(r['ts']) == ds['T_last']), None)
            note = ' (already logged for this anchor)'
        else:
            note = ''
        if top is None:
            print(f'predict {h}: current-anchor call not logged — investigate '
                  f'(ts={iso(ds["T_last"])})', file=sys.stderr)
            continue
        print(f'predict {h}: P(up)={top["p_up"]:.2f} P(side)={top["p_side"]:.2f} '
              f'P(down)={top["p_down"]:.2f} ts={iso(ds["T_last"])} '
              f'n_train={top["n_train"]} window=[{iso(ds["window_start"])} .. '
              f'{iso(ds["T_last"])}] {WINDOW_DAYS}d eps={EPS_BPS[h]:g}bps '
              f'trained_through={iso(top["trained_through"])} '
              f'new_rows={len(new_rows)} pin {pin_line(ds["pin"])}{note}')

    if new_all:
        append_calls(new_all)
        print(f'predict: appended {len(new_all)} call row(s) -> '
              f'{os.path.relpath(PRED_FILE, "/root/.hermes")} '
              f'(one per horizon per anchor; dedup by (ts,horizon))')
    else:
        print('predict: no new call rows (all (ts,horizon) already logged)')
    write_state(state)
    do_resolve(now_ts)
    write_state(state)
    return 0


def mode_resolve(args):
    return do_resolve()


def mode_score(args):
    rows = read_calls()
    resolved = [r for r in rows if r.get('actual') is not None]
    print(f'[DIR-MATRIX] score · {eps_line()}')
    print(f'score: n_calls={len(rows)} n_resolved={len(resolved)} '
          f'source={os.path.relpath(PRED_FILE, "/root/.hermes")}')
    if not resolved:
        print('score: 0 resolved calls — run `predict --backfill N` then `resolve` '
              'to collect out-of-sample calls (nothing fabricated here)')
        return 0
    for h in HORIZONS:
        hr = sorted([r for r in resolved if r['horizon'] == h], key=lambda r: r['ts'])
        if not hr:
            print(f'score {h}: n_resolved=0')
            continue
        w = f'[{iso(hr[0]["ts"])} .. {iso(hr[-1]["ts"])}]'
        n = len(hr)
        br, ll = [], []
        for r in hr:
            p = np.array([r['p_up'], r['p_side'], r['p_down']])
            br.append(brier_one(p, CLASS_NAMES.index(r['actual'])))
            ll.append(logloss_one(p, CLASS_NAMES.index(r['actual'])))
        print(f'score {h}: n={n} window={w} calls Brier={np.mean(br):.4f} '
              f'logloss={np.mean(ll):.4f} ε={EPS_BPS[h]:g}bps')

        # reliability: p_up decile -> empirical up frequency, n each
        if n >= 10:
            order = np.argsort([r['p_up'] for r in hr])
            bins = np.array_split(order, 10)
            print(f'  reliability (p_up decile -> up freq, n), n={n} window={w}:')
            for bi, bidx in enumerate(bins):
                if len(bidx) == 0:
                    continue
                pv = float(np.mean([hr[i]['p_up'] for i in bidx]))
                uv = float(np.mean([hr[i]['actual'] == 'up' for i in bidx]))
                print(f'    decile {bi}: mean_p_up={pv:.3f} up_freq={uv:.3f} '
                      f'n={len(bidx)}')
        else:
            print(f'  reliability: skipped (n={n} < 10) window={w}')

        hi = [r for r in hr if max(r['p_up'], r['p_side'], r['p_down']) >= 0.70]
        if hi:
            hits = sum(1 for r in hi if r.get('hit'))
            print(f'  >=70% calls: hit={hits}/{len(hi)} = {hits / len(hi):.0%} '
                  f'window={w}')
        else:
            print(f'  >=70% calls: n=0 window={w}')
    return 0


def mode_query(args):
    rows = read_calls()
    state = read_state()
    hs = list(HORIZONS) if args.horizon == 'all' else [args.horizon]
    now_ts = int(time.time())
    out = []
    for h in hs:
        hr = [r for r in rows if r['horizon'] == h]
        if not hr:
            line = (f'BTC {h}: no call logged yet — run `python3 scripts/dir_matrix.py '
                    f'predict` first')
            print(line)
            out.append({'horizon': h, 'error': 'no_calls'})
            continue
        call = max(hr, key=lambda r: r['ts'])
        res = [r for r in hr if r.get('actual') is not None
               and r['ts'] >= now_ts - 30 * 86400]
        status = state.get('horizons', {}).get(h, {}).get('status', 'PENDING')
        if res:
            br = np.mean([brier_one(np.array([r['p_up'], r['p_side'], r['p_down']]),
                                    CLASS_NAMES.index(r['actual'])) for r in res])
            hi = [r for r in res if max(r['p_up'], r['p_side'], r['p_down']) >= 0.70]
            if hi:
                hit = sum(1 for r in hi if r.get('hit'))
                rel = (f'reliability: last-30d Brier {br:.2f} · ≥70% calls: '
                       f'{hit / len(hi):.0%} hit (n={len(hi)})')
            else:
                rel = (f'reliability: last-30d Brier {br:.2f} · ≥70% calls: n=0 '
                       f'(n_resolved_30d={len(res)})')
        else:
            rel = (f'reliability: n/a (0 resolved calls in last 30d of '
                   f'{len(hr)} logged)')
        line1 = (f'BTC {h}: P(up)={call["p_up"]:.0%} P(side)={call["p_side"]:.0%} '
                 f'P(down)={call["p_down"]:.0%}   [trained through '
                 f'{iso(call["trained_through"])}, {call["window"]} '
                 f'n={call["n_train"]}]')
        line2 = f'           {rel} · {status}'
        print(line1)
        print(line2)
        out.append({'horizon': h, 'ts': call['ts'], 'p_up': call['p_up'],
                    'p_side': call['p_side'], 'p_down': call['p_down'],
                    'trained_through': call['trained_through'],
                    'n_train': call['n_train'], 'window': call['window'],
                    'eps': call['eps'], 'status': status,
                    'brier_30d': (round(float(br), 4) if res else None),
                    'n_resolved_30d': len(res)})
    if args.json:
        print(json.dumps({'generated': iso_z(now_ts), 'ε_bps': EPS_BPS,
                          'calls': out}, sort_keys=True))
    return 0


# ───────────────────────── validate (pre-registered gate, spec §2.5) ─────────────────────────

def walk_forward(h, ds):
    """Train first 80% of the labeled window -> test last 20% (k = 20% of window)."""
    mask = ds['usable']
    idx = np.flatnonzero(mask)
    n_win = len(idx)
    k = max(1, int(round(TEST_FRAC * n_win)))
    test_idx, train_idx = idx[-k:], idx[:-k]
    X = ds['X'].to_numpy()
    y = ds['y']
    pipe = fit_pipeline(X[train_idx], y[train_idx])
    p = proba3(pipe, X[test_idx])
    yte = y[test_idx]
    days = day_labels(ds['anchors'][test_idx])

    freq_tr = np.bincount(y[train_idx], minlength=3) / len(train_idx)
    brier_m = float(np.mean([brier_one(pi, yi) for pi, yi in zip(p, yte)]))
    brier_b = float(np.mean([brier_one(freq_tr, yi) for yi in yte]))
    diff = np.array([brier_one(pi, yi) - brier_one(freq_tr, yi)
                     for pi, yi in zip(p, yte)])
    ci_a = cluster_ci(diff, days)

    # (b) calibration-in-the-large vs observed test frequencies
    freq_te = np.bincount(yte, minlength=3) / len(yte)
    mean_p = p.mean(axis=0)
    citl = [abs(float(mean_p[c]) - float(freq_te[c])) for c in range(3)]
    citl_max = max(citl)
    pass_b1 = citl_max <= 0.05

    # (b) top decile by claimed p_up: empirical up-frequency CI contains mean p_up
    q90 = float(np.quantile(p[:, 0], 0.90))
    top = p[:, 0] >= q90
    n_top = int(top.sum())
    claim = float(p[top, 0].mean()) if n_top else float('nan')
    ci_top = cluster_ci((yte[top] == 0).astype(float), days[top]) if n_top else None
    pass_b2 = bool(ci_top is not None and ci_top[0] <= claim <= ci_top[1])

    pass_a = bool(ci_a is not None and ci_a[1] < 0)
    pass_b = bool(pass_b1 and pass_b2)
    pass_c = True                                   # n disclosed (this report)
    verdict = 'VALIDATED' if (pass_a and pass_b and pass_c) else 'UNVALIDATED'
    return {
        'n_window': n_win, 'n_train': int(len(train_idx)), 'n_test': int(len(test_idx)),
        'k': k, 'days': (len(set(days.tolist()))),
        'brier_model': brier_m, 'brier_base': brier_b, 'diff': float(diff.mean()),
        'ci_a': ci_a, 'pass_a': pass_a,
        'freq_train': freq_tr, 'freq_test': freq_te, 'mean_p': mean_p,
        'citl': citl, 'citl_max': citl_max, 'pass_b1': pass_b1,
        'q90': q90, 'n_top': n_top, 'top_claim': claim, 'top_freq':
            (float((yte[top] == 0).mean()) if n_top else float('nan')),
        'ci_top': ci_top, 'pass_b2': pass_b2, 'pass_b': pass_b, 'pass_c': pass_c,
        'unstable_low_n': n_win < LOW_N_FLAG, 'verdict': verdict,
    }


def mode_validate(args):
    print(f'[DIR-MATRIX] validate (spec §2.5 walk-forward) · {eps_line()}')
    results, pins = {}, {}
    for h in HORIZONS:
        ds = build_dataset(h)
        pins[h] = ds['pin']
        results[h] = walk_forward(h, ds)
        print(f'validate {h}: n_window={results[h]["n_window"]} '
              f'window=[{iso(ds["window_start"])} .. {iso(ds["T_last"])}] {WINDOW_DAYS}d '
              f'pin {pin_line(ds["pin"])}')

    # state: per-horizon verdicts live here (spec §2.5)
    state = read_state()
    state.setdefault('horizons', {})
    state['validation_run'] = iso_z(int(time.time()))
    state['eps_bps'] = EPS_BPS
    for h in HORIZONS:
        r = results[h]
        state['horizons'][h] = {
            **state['horizons'].get(h, {}),
            'status': r['verdict'],
            'unstable_low_n': r['unstable_low_n'],
            'gate': {
                'n_window': r['n_window'], 'n_train': r['n_train'],
                'n_test': r['n_test'], 'days': r['days'],
                'brier_model': round(r['brier_model'], 6),
                'brier_base': round(r['brier_base'], 6),
                'ci_a': ([round(x, 6) for x in r['ci_a'][:2]] if r['ci_a'] else None),
                'pass_a': r['pass_a'], 'citl_max': round(r['citl_max'], 6),
                'pass_b1': r['pass_b1'], 'pass_b2': r['pass_b2'],
                'pass_b': r['pass_b'], 'pass_c': r['pass_c'],
            },
            'data_pin': pins[h],
        }
    write_state(state)

    # report (§15.6 data-pin header, reproduce one-liner, every number carries n+window)
    lines = []
    lines.append('# Direction Matrix v1 — validation gate (spec §2.5)')
    lines.append('')
    lines.append(f'Generated: {iso_z(int(time.time()))} · mode=validate · reproduce: '
                 '`python3 scripts/dir_matrix.py validate`')
    lines.append(f'Spec: brain/plans/direction-matrix-spec.md (v1.0, 2026-11-22) · '
                 f'data: local `{CANDLES_DB}` ONLY (SELECT-only, mode=ro, is_closed=1, '
                 f'token=BTC, cursors closed in finally) · NO external API · '
                 f'model: StandardScaler→LogisticRegression(C=1.0, L2, '
                 f'random_state={RANDOM_STATE}), per horizon, {WINDOW_DAYS}d rolling window.')
    lines.append(f'{eps_line()} (printed every run)')
    lines.append('')
    lines.append('## Data pin (§15.6) — window bounds + row count + sha of candle slice')
    lines.append('')
    lines.append('| horizon tier | window [first_close .. last_close] UTC | rows | sha256 |')
    lines.append('|---|---|---|---|')
    for h in HORIZONS:
        p = pins[h]
        lines.append(f'| {p["tier"]} (H={h}) | [{iso(p["window_start"])} .. '
                     f'{iso(p["window_end"])}] | {p["rows"]} | `{p["sha256"]}` |')
    lines.append('')
    lines.append('## Gate definitions (pre-registered §2.5, judged per horizon, never pooled)')
    lines.append('')
    lines.append(f'- Walk-forward inside the {WINDOW_DAYS}d window: train first '
                 f'{int((1 - TEST_FRAC) * 100)}% → test last {int(TEST_FRAC * 100)}% '
                 f'(k = 20% of window).')
    lines.append('- **(a)** Brier(p) < Brier(base-rate predictor = TRAIN class '
                 'frequencies), day-cluster-robust 95% t-CI of per-row difference '
                 'excludes 0 (upper bound < 0).')
    lines.append('- **(b)** calibration-in-the-large: max_c |mean p_c − freq_c(test)| ≤ '
                 '0.05; top decile by claimed p_up: day-cluster 95% CI of empirical '
                 'up-frequency contains the claimed mean p_up.')
    lines.append(f'- **(c)** n disclosed per horizon; 4h judged alone. '
                 f'UNSTABLE-LOW-N flag if window n < {LOW_N_FLAG}.')
    lines.append('- Brier = mean_i Σ_c (p_ic − y_ic)² (3 classes, range 0..2).')
    lines.append('')
    lines.append('## Results per horizon')
    lines.append('')
    for h in HORIZONS:
        r = results[h]
        flag = ' **UNSTABLE-LOW-N**' if r['unstable_low_n'] else ''
        lines.append(f'### {h} — {r["verdict"]}{flag}')
        lines.append('')
        cia = (f'[{r["ci_a"][0]:.4f}, {r["ci_a"][1]:.4f}]'
               if r['ci_a'] else 'n/a (<2 day clusters)')
        p_a = f'{r["ci_a"][5]:.4g}' if (r['ci_a'] and r['ci_a'][5] is not None) else 'n/a'
        lines.append(f'- n: window n={r["n_window"]} ({WINDOW_DAYS}d, '
                     f'window=[{iso(pins[h]["window_start"])} .. {iso(pins[h]["window_end"])}]), '
                     f'train n={r["n_train"]}, test n={r["n_test"]} over {r["days"]} days')
        lines.append(f'- (a) Brier_model={r["brier_model"]:.4f} vs Brier_base='
                     f'{r["brier_base"]:.4f}, diff={r["diff"]:.4f}, day-cluster 95% CI '
                     f'{cia} p={p_a} → {"PASS" if r["pass_a"] else "FAIL"}')
        citl_s = ', '.join(f'{CLASS_NAMES[c]} |{r["citl"][c]:.3f}|' for c in range(3))
        lines.append(f'- (b) calibration-in-the-large: {citl_s} → max={r["citl_max"]:.4f} '
                     f'{"≤" if r["pass_b1"] else ">"} 0.05 → '
                     f'{"PASS" if r["pass_b1"] else "FAIL"}; top decile p_up≥{r["q90"]:.3f}: '
                     f'n={r["n_top"]}, claimed mean p={r["top_claim"]:.3f}, empirical '
                     f'up freq={r["top_freq"]:.3f}, day-cluster 95% CI '
                     + (f'[{r["ci_top"][0]:.3f}, {r["ci_top"][1]:.3f}]'
                        if r['ci_top'] else 'n/a (<2 day clusters)')
                     + f' → {"PASS" if r["pass_b2"] else "FAIL"} → (b) '
                     + ('PASS' if r['pass_b'] else 'FAIL'))
        lines.append(f'- (c) n disclosed: window n={r["n_window"]}, train n='
                     f'{r["n_train"]}, test n={r["n_test"]}; 4h judged alone '
                     f'(no pooling) → PASS'
                     + (' · **UNSTABLE-LOW-N (n < '
                        f'{LOW_N_FLAG})**' if r['unstable_low_n'] else ''))
        lines.append(f'- train class freq (up/side/down) = '
                     f'{r["freq_train"][0]:.3f}/{r["freq_train"][1]:.3f}/'
                     f'{r["freq_train"][2]:.3f} (n={r["n_train"]}) · test freq = '
                     f'{r["freq_test"][0]:.3f}/{r["freq_test"][1]:.3f}/'
                     f'{r["freq_test"][2]:.3f} (n={r["n_test"]}) · mean p = '
                     f'{r["mean_p"][0]:.3f}/{r["mean_p"][1]:.3f}/{r["mean_p"][2]:.3f}')
        lines.append('')
    lines.append('## Verdicts')
    lines.append('')
    lines.append('| horizon | (a) Brier vs base | (b) calibration | (c) n | flag | VERDICT |')
    lines.append('|---|---|---|---|---|---|')
    for h in HORIZONS:
        r = results[h]
        lines.append(
            f'| {h} | {"PASS" if r["pass_a"] else "FAIL"} '
            f'(Δ={r["diff"]:.4f}, CI {("[" + f"{r["ci_a"][0]:.4f}, {r["ci_a"][1]:.4f}" + "]") if r["ci_a"] else "n/a"}) '
            f'| {"PASS" if r["pass_b"] else "FAIL"} (CITL max {r["citl_max"]:.4f}, '
            f'topdec {"PASS" if r["pass_b2"] else "FAIL"}) '
            f'| n_window={r["n_window"]} n_test={r["n_test"]} | '
            f'{"UNSTABLE-LOW-N" if r["unstable_low_n"] else "—"} '
            f'| **{r["verdict"]}** |')
    lines.append('')
    lines.append('Status written to `data/dir_matrix_state.json`. Consumers v1: '
                 'informational only — any trading-path consumer requires validated '
                 'status + shadow wiring (automatic-implementation) + CEO approval '
                 '(spec §2.5).')
    lines.append('')
    lines.append('Reproduce: `python3 scripts/dir_matrix.py validate` · selfcheck: '
                 '`python3 scripts/dir_matrix.py --selfcheck`')
    report = '\n'.join(lines) + '\n'
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, 'w') as f:
        f.write(report)
    print(report)
    print(f'[DIR-MATRIX] report -> {args.report}')
    print('[DIR-MATRIX] verdicts: ' + ' · '.join(
        f'{h}={results[h]["verdict"]}'
        + ('+UNSTABLE-LOW-N' if results[h]['unstable_low_n'] else '')
        for h in HORIZONS))
    return 0


# ───────────────────────── selfcheck ─────────────────────────

def selfcheck():
    checks = []

    def chk(cond, msg):
        if not cond:
            raise AssertionError(f'selfcheck failed: {msg}')
        checks.append(msg)

    # 1) ε + label math (spec §2.1)
    chk(EPS_BPS == {'15m': 5.0, '1h': 10.0, '4h': 20.0}, 'eps fixed table 5/10/20')
    for h, mins in HORIZONS.items():
        chk(abs(EPS_BPS[h] - 5.0 * math.sqrt(mins / 15.0)) < 1e-9, f'eps formula {h}')
    chk(classify(5e-4, '15m') == 0, '15m r=+5bps boundary -> up')
    chk(classify(4.9e-4, '15m') == 1, '15m r=+4.9bps -> side')
    chk(classify(-5e-4, '15m') == 2, '15m r=-5bps boundary -> down')
    chk(classify(9e-4, '1h') == 1, '1h r=+9bps -> side (eps 10)')
    chk(classify(10e-4, '1h') == 0, '1h r=+10bps -> up')
    chk(classify(-10e-4, '1h') == 2, '1h r=-10bps -> down')
    chk(classify(1.9e-3, '4h') == 1, '4h r=+19bps -> side (eps 20)')
    chk(classify(20e-4, '4h') == 0, '4h r=+20bps -> up')
    chk(classify(-2.1e-3, '4h') == 2, '4h r=-21bps -> down')

    # 2) no-lookahead: features at row i unchanged when data after i is removed;
    #    alignment always picks the LAST bar with closed_at <= anchor
    rng = np.random.RandomState(7)
    n = 700
    close = 60000 * np.exp(np.cumsum(rng.normal(0, 0.001, n)))
    tr = {'ts': (np.arange(n) * 900).astype(np.int64), 'open': close,
          'high': close * 1.001, 'low': close * 0.999, 'close': close,
          'volume': rng.uniform(1, 5, n),
          'closed_at': (np.arange(n) * 900 + 900).astype(np.int64)}
    full = tier_features(tr, '15m')
    k = 450
    trunc = {kk: vv[:k + 1] for kk, vv in tr.items()}
    part = tier_features(trunc, '15m')
    common = [c for c in full.columns if c != 'closed_at']
    a = full[common].iloc[:k + 1].reset_index(drop=True)
    b = part[common].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b, check_exact=False, atol=1e-9,
                                  obj='features after truncation')
    chk(True, 'no-lookahead: features identical on truncated data (rows <= t)')

    # alignment: brute-force check on interleaved anchors
    anchors = np.array([tr['closed_at'][i] for i in (100, 349, 450, 699)] +
                       [tr['closed_at'][349] - 1, tr['closed_at'][100] + 900])
    Xa = align_features(anchors, {'15m': full})
    ct = full['closed_at'].to_numpy()
    for j, anc in enumerate(anchors):
        expect = np.flatnonzero(ct <= anc)
        chk(len(expect) > 0 and ct[expect[-1]] <= anc,
            f'alignment picks closed bar <= anchor ({anc})')
        got = Xa.iloc[j]['15m_rsi14']
        want = full.iloc[expect[-1]]['rsi14']
        chk(np.isnan(got) == np.isnan(want) and
            (np.isnan(got) or abs(got - want) < 1e-12),
            'alignment value == last closed bar value')

    # 3) scaler fit on TRAIN only (spec selfcheck list)
    Xs = np.random.RandomState(3).randn(80, 6)
    ys = np.random.RandomState(4).randint(0, 3, 80)
    pipe = fit_pipeline(Xs[:50], ys[:50])
    sc = pipe.named_steps['scaler']
    chk(np.allclose(sc.mean_, Xs[:50].mean(axis=0)), 'scaler mean == train mean')
    chk(not np.allclose(sc.mean_, Xs.mean(axis=0)), 'scaler mean != full-data mean')

    # 4) Brier / logloss math (hand-computed)
    chk(abs(brier_one(np.array([0.5, 0.3, 0.2]), 0) - 0.38) < 1e-12,
        'brier([.5,.3,.2], up) == 0.38')
    chk(abs(brier_one(np.array([1 / 3, 1 / 3, 1 / 3]), 2) - 2 / 3) < 1e-12,
        'brier(uniform) == 2/3')
    chk(abs(brier_one(np.array([1.0, 0.0, 0.0]), 0)) < 1e-12, 'brier(perfect) == 0')
    chk(abs(logloss_one(np.array([0.5, 0.3, 0.2]), 0) - math.log(2)) < 1e-12,
        'logloss(p=.5) == ln2')

    # 5) resolve join arithmetic (pure, synthetic outcomes)
    def lookup(h, ts_call):
        table = {15: (100.0, 100.07), 60: (100.0, 99.85), 240: (100.0, 100.01)}
        ci, co = table[HORIZONS[h]]
        return (ci, co)

    rows = [
        {'ts': 1000, 'horizon': '15m', 'p_up': 0.6, 'p_side': 0.3, 'p_down': 0.1},
        {'ts': 2000, 'horizon': '1h', 'p_up': 0.2, 'p_side': 0.3, 'p_down': 0.5},
        {'ts': 3000, 'horizon': '4h', 'p_up': 0.3, 'p_side': 0.4, 'p_down': 0.3},
        {'ts': 9000, 'horizon': '15m', 'p_up': 0.9, 'p_side': 0.05, 'p_down': 0.05},
        {'ts': 100, 'horizon': '15m', 'p_up': 0.5, 'p_side': 0.4, 'p_down': 0.1,
         'actual': 'up', 'hit': True},
    ]
    now = 1000 + 15 * 60 + 1            # 15m matured; 1h/4h not; last already resolved
    n_res = resolve_rows(rows, now, lookup)
    chk(n_res == 1, 'resolve joins exactly the matured call')
    chk(rows[0]['actual'] == 'up' and rows[0]['hit'] is True,
        '15m outcome +7bps >= 5bps -> actual=up, hit=argmax(p_up)=True')
    chk('actual' not in rows[1] and 'actual' not in rows[2],
        'immature 1h/4h calls untouched')
    chk(rows[4]['actual'] == 'up' and rows[4]['hit'] is True,
        'already-resolved row untouched')
    now2 = 2000 + 60 * 60 + 1
    n2 = resolve_rows(rows, now2, lookup)
    chk(n2 == 1 and rows[1]['actual'] == 'down' and rows[1]['hit'] is True,
        '1h outcome -15bps <= -10bps -> down, argmax(p_down)=hit')

    # 6) determinism: fixed random_state -> identical fits on identical data
    p1 = fit_pipeline(Xs, ys)
    p2 = fit_pipeline(Xs, ys)
    chk(np.array_equal(p1.named_steps['clf'].coef_, p2.named_steps['clf'].coef_),
        'identical coefficients on identical data (random_state=42)')
    chk(np.array_equal(p1.predict_proba(Xs), p2.predict_proba(Xs)),
        'identical proba on identical data')
    f1 = tier_features(tr, '15m')
    f2 = tier_features({kk: vv.copy() for kk, vv in tr.items()}, '15m')
    chk(f1.equals(f2), 'feature build deterministic on identical data')

    print(f'[DIR-MATRIX] SELFCHECK PASS ({len(checks)} checks):')
    for m in checks:
        print(f'  ok - {m}')
    return 0


# ───────────────────────── main ─────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog='dir_matrix.py',
        description='Direction Matrix v1 — BTC P(up/side/down) per horizon '
                    '(rolling logistic, self-calibrating). Informational only.',
        epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', nargs='?',
                    choices=['train', 'predict', 'resolve', 'score', 'query',
                             'validate'],
                    help='mode to run (see FORMULAS/MODES above)')
    ap.add_argument('--horizon', default='all', choices=['15m', '1h', '4h', 'all'],
                    help='query: which horizon (default all)')
    ap.add_argument('--json', action='store_true',
                    help='query: also emit machine-readable JSON')
    ap.add_argument('--backfill', type=int, default=0, metavar='N',
                    help='predict: also log N historical hourly-anchored '
                         'out-of-sample calls per horizon (each trained only through '
                         'its own anchor; default 0 = timer behavior)')
    ap.add_argument('--report', default=VALIDATION_REPORT,
                    help='validate: output markdown path')
    ap.add_argument('--selfcheck', action='store_true',
                    help='run the assertion suite (label/eps, no-lookahead, '
                         'scaler-train-only, brier, resolve join, determinism)')
    args = ap.parse_args(argv)

    if args.selfcheck:
        return selfcheck()
    if not args.mode:
        ap.print_help()
        return 2
    return {'train': mode_train, 'predict': mode_predict, 'resolve': mode_resolve,
            'score': mode_score, 'query': mode_query,
            'validate': mode_validate}[args.mode](args)


if __name__ == '__main__':
    sys.exit(main())
