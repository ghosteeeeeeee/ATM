#!/usr/bin/env python3
"""
neighbor_step_sweep.py — ±step neighbor sweep (hill-vs-spike) for named hermes_constants.

Item B, CEO deep run checkpoint 20261108T173238Z. ANALYSIS ONLY.

A robust ("lucky") parameter looks like a HILL: neighbouring settings also
perform acceptably. A luck-tuned parameter looks like a SPIKE: only the exact
current value works and the neighbours collapse. This tool sweeps a constant
across ±depth steps and evaluates a consistent performance metric at every grid
point against LOCAL data only:

  * PostgreSQL brain DB, `trades` table (source of truth; has `_signal_metadata`
    JSON with `speed_percentile`, plus MFE/MAE, pnl_usdt, win info).
  * Local candles DB (sqlite, 1m OHLC) — only used to order barrier touches
    (TP vs exit) and to extend the path past an actual stop-out when a WIDER
    stop would have survived it.

NEVER calls an external API. NEVER writes to any DB. NEVER modifies a trading
path — this script only reads.

Constants swept (current values are READ from hermes_constants at runtime, not
hardcoded):

  SIGNAL_FILTER_SPEED_MIN  counterfactual admission: which recorded trades
                           would pass the speed gate at each threshold, using
                           `_signal_metadata->>'speed_percentile'` (the field
                           actually present — verified at runtime; see --help
                           "data fields").
  ATR_SL_MIN               stop-placement counterfactual: reconstruct each
                           trade's initial stop from `sl_distance`, re-place it
                           at the neighbour value, and re-decide the outcome
                           from MFE/MAE (+ candle path where a wider stop
                           survives the actual stop-out).
  ATR_TP_K_MULT            target-placement counterfactual: re-derive each
                           trade's target from the recorded `target` column at
                           the neighbour K, and re-decide the outcome from
                           MFE/MAE with candle-ordered first-touch.

Every approximation and its bias direction is printed in the audit output and
documented in the result file. Where the data cannot support a faithful
counterfactual the verdict comes out INDETERMINATE with the specific reason —
this tool never fabricates a verdict.

Sample-size discipline ("THE PATTERN"): n is printed for every number, the
identifying sample (n_swung = trades whose computed outcome actually differs
between a grid point and the current value) is checked against --min-n before
any verdict, and bootstrap / Wilson 95% intervals are reported.

Reproducibility: the exact SQL, bind params, window, seed, and grids are
printed on every run (and the REPRODUCE line at the end pins them).

Usage:
  python3 scripts/neighbor_step_sweep.py --help
  python3 scripts/neighbor_step_sweep.py                       # all 3 constants
  python3 scripts/neighbor_step_sweep.py --constants speed --days 30
"""

import argparse
import json
import math
import os
import random
import sqlite3
import sys
import time
import zlib
from datetime import datetime, timedelta, timezone

# ── Repo imports (single source of truth for paths + constants) ───────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import *  # noqa: F401,F403  (HERMES_DATA, CANDLES_DB, ...)
import hermes_constants as hc
from _secrets import BRAIN_DB_DICT  # local PG brain DB (never leaves the box)

import psycopg2

# Tier logic for ATR-based SL/TP placement is imported (not re-implemented) so
# the counterfactual cannot drift from the live placement math.
from tpsl_utils import _atr_tier

# ── Historical floor values (NOT current constants — they no longer exist) ────
# ATR_SL_MIN history inside any usable window (sources: hermes_constants.py:717
# comment "widened from 1.3% ... CEO Oct 16"; brain/changes_log.json entry
# "ATR_SL_MIN 1.2%→1.3%"). A trade whose recorded initial stop distance equals
# one of these was pinned at THAT era's floor (the floor bound its placement).
# 0.012/0.013 are era floors; 0.015 is the current hc.ATR_SL_MIN (read at
# runtime below, so this tuple stays a historical record only).
HISTORICAL_ERA_FLOORS = (0.012, 0.013)

# close_reason values that are a genuine initial-stop stop-out (price died AT
# the stop). Other loss reasons (hard_max_loss, cut-loser-*) are their own
# barriers that fire before any stop in our grid — they are handled by the
# MAE-vs-stop rule and never need path continuation.
# 'no_sl_tp' (n=1 in-window) is a guardian close with no stop level set —
# NOT a stop-level exit, deliberately excluded.
STOP_LOSS_REASONS = {'atr_sl_hit', 'hard_sl', 'manual_sl_hit', 'HARD_SL_FAILED'}

# close_reason values that mean "the TP barrier fired".
TP_FIRE_REASONS = {'atr_tp_hit', 'position_manager_hard_tp'}

BANNER = "=" * 78


def log(msg=""):
    print(msg, flush=True)


def loga(msg=""):
    """Audit/progress line."""
    print(f"  [sweep] {msg}", flush=True)


# resolution counters — printed per sweep so an INDETERMINATE verdict can cite
# the SPECIFIC data gap instead of a vague "uncertainty"
STATS = {}


def stat(key, n=1):
    STATS[key] = STATS.get(key, 0) + n


def stat_block(prefix):
    return {k: v for k, v in sorted(STATS.items()) if k.startswith(prefix)}


# ── CLI ───────────────────────────────────────────────────────────────────────
def build_parser():
    epilog = f"""
step-size justification (this tool's own parameters — NOT trading thresholds):
  --sl-step 0.002    self_learner.py:102 tunes ATR_SL_MIN with step=0.002
                     (range 0.008–0.025); also matches the constant's own
                     history granularity (1.2% → 1.3% → 1.5%).
  --speed-step 5     self_learner.py:85 tunes SIGNAL_FILTER_SPEED_MIN with
                     step=5 (range 30–60); matches the 30→40 history.
  --tpk-step 0.25    no self_learner entry; half of the last real move
                     (1.5→2.0, hermes_constants.py:722) and the grid therefore
                     contains both values the CEO actually tried (1.5 prior,
                     2.5 tried-and-reverted).

data fields (verified at runtime, printed in the audit block):
  speed  -> trades._signal_metadata->>'speed_percentile'  (0–100 percentile;
            the same field decider_run.py's gate consumes via SpeedTracker).
            Trades without it are excluded at EVERY grid point (count printed).
  SL     -> trades.sl_distance (recorded initial stop distance, fraction —
            an A/B-group field, see caveats) plus mae_pct/mfe_pct (percent
            units) for the outcome re-decision; non-trailed stop-outs use
            their recorded fired-stop level as conclusive evidence.
  TP     -> trades.target (recorded target distance, fraction) + mfe_pct/mae_pct.

approximations (full list printed at the end of each sweep; bias direction in
brackets):
  * speed  — the gate returns AMBIGUOUS (a penalty), not a hard SKIP, so
            "admission" is a hypothetical strict enforcement; signals blocked
            entirely never appear in trades (unknown PnL for them) [direction
            unknown, likely small: sub-threshold trades demonstrably DID trade
            (porosity count printed)]. Gate consumes execution-time speed while
            the DB records signal-time speed_percentile [noise, direction
            unknown].
  * SL     — trailing/PM_TRAIL path is assumed unaffected by a changed initial
            floor [for widening: overstates profit-locking, since a wider floor
            also widens the trailing anchors]; historical trades ran under the
            era floor they were opened with, the sweep applies ONE uniform
            value across the window [by design — this is what "set the constant
            to v" means]; below-floor explicit-SL trades (A/B groups, guardian
            paths) are treated as unaffected in the primary model [sensitivity
            variant printed].
  * TP     — target assumed ATR-derived when strictly inside the floor/cap
            (structural rr_engine targets misread as ATR ones) [direction
            unknown]; path continuation past an actual TP exit replicates only
            {{stop, TP, horizon}} barriers — no trailing, no hard-exit logic
            [widens outcome dispersion]; same-candle barrier ties resolved
            pessimistically in one envelope arm and optimistically in the other
            [true value lies inside the printed envelope].
"""
    p = argparse.ArgumentParser(
        prog="neighbor_step_sweep.py",
        description="±step neighbour sweep (hill-vs-spike verdict) for "
                    "ATR_SL_MIN / SIGNAL_FILTER_SPEED_MIN / ATR_TP_K_MULT. "
                    "Read-only: local brain PG + local candles sqlite. "
                    "Analysis only — changes nothing on the trading path.",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--constants", default="all",
                   help="Comma list from {speed,sl,tpk} or 'all' (default: all)")
    p.add_argument("--days", type=int, default=90,
                   help="Lookback window in days if --since is not given (default: 90)")
    p.add_argument("--since", default=None, metavar="TS",
                   help="Window start, UTC (YYYY-MM-DD or full ISO datetime; "
                        "inclusive). Overrides --days.")
    p.add_argument("--until", default=None, metavar="TS",
                   help="Window end, UTC (YYYY-MM-DD or full ISO datetime; "
                        "exclusive). Default: now. The REPRODUCE line prints "
                        "the exact values used.")
    p.add_argument("--sl-step", type=float, default=0.002,
                   help="ATR_SL_MIN step (fraction; default 0.002 = self_learner step)")
    p.add_argument("--sl-depth", type=int, default=2,
                   help="ATR_SL_MIN ±steps (default 2)")
    p.add_argument("--speed-step", type=float, default=5,
                   help="SIGNAL_FILTER_SPEED_MIN step (default 5 = self_learner step)")
    p.add_argument("--speed-depth", type=int, default=2,
                   help="SIGNAL_FILTER_SPEED_MIN ±steps (default 2)")
    p.add_argument("--tpk-step", type=float, default=0.25,
                   help="ATR_TP_K_MULT step (default 0.25)")
    p.add_argument("--tpk-depth", type=int, default=2,
                   help="ATR_TP_K_MULT ±steps (default 2)")
    p.add_argument("--min-n", type=int, default=30,
                   help="Minimum identifying sample (n_swung) per grid point "
                        "before a verdict may be non-INDETERMINATE (default 30)")
    p.add_argument("--bootstrap", type=int, default=1000,
                   help="Bootstrap resamples for 95%% CIs (default 1000)")
    p.add_argument("--seed", type=int, default=20261108,
                   help="Bootstrap seed (default 20261108) — reproducibility")
    p.add_argument("--horizon-hours", type=float, default=48.0,
                   help="Path-continuation horizon in hours after the actual "
                        "close when a wider barrier survives (default 48)")
    p.add_argument("--json-out", default=None, metavar="PATH",
                   help="Also dump every table + verdict as JSON to PATH")
    p.add_argument("--no-candles", action="store_true",
                   help="Skip the candles DB (ordering/continuation degrade to "
                        "envelopes; verdicts likely INDETERMINATE)")
    p.add_argument("--quiet", action="store_true", help="Less audit output")
    return p


def parse_grid(current, step, depth, lo=None, hi=None):
    vals = [round(current + i * step, 10) for i in range(-depth, depth + 1)]
    if lo is not None:
        vals = [v for v in vals if v >= lo - 1e-12]
    if hi is not None:
        vals = [v for v in vals if v <= hi + 1e-12]
    # de-dup, keep sorted
    out = []
    for v in sorted(set(vals)):
        if not out or abs(v - out[-1]) > 1e-12:
            out.append(v)
    return out


# ── Stats helpers �─────────────────────────────────────────────────────────────
def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def bootstrap_sum_ci(values, seed, B):
    """95% CI for the SUM of values (resample with replacement)."""
    n = len(values)
    if n == 0:
        return (0.0, 0.0)
    rng = random.Random(seed)
    total = sum(values)
    if n == 1 or len(set(values)) == 1:
        return (total, total)
    sums = []
    for _ in range(B):
        s = 0.0
        for _ in range(n):
            s += values[rng.randrange(n)]
        sums.append(s)
    sums.sort()
    lo = sums[int(0.025 * (B - 1))]
    hi = sums[int(0.975 * (B - 1))]
    return (lo, hi)


def money(x):
    return f"{x:+.2f}"


# ── Data fetch (PostgreSQL brain DB) ──────────────────────────────────────────
TRADES_SQL = """
SELECT
    id,
    token,
    direction,
    entry_price,
    exit_price,
    stop_loss,
    target,
    sl_distance,
    pnl_usdt,
    amount_usdt,
    mfe_pct,
    mae_pct,
    close_reason,
    trailing_activated,
    volatility_regime,
    open_time,
    close_time,
    entry_atr_14,
    _signal_metadata ->> 'speed_percentile' AS speed_percentile
FROM trades
WHERE status = 'closed'
  AND open_time >= %(since)s
  AND open_time <  %(until)s
  AND entry_price IS NOT NULL
  AND entry_price > 0
ORDER BY open_time, id
"""


def fetch_trades(since, until, quiet=False):
    """Read-only SELECT. Cursors/connections always closed in finally."""
    loga("QUERY (PostgreSQL brain DB, table `trades`):")
    for line in TRADES_SQL.strip().splitlines():
        loga("    " + line)
    params = {"since": since.strftime("%Y-%m-%d %H:%M:%S"),
              "until": until.strftime("%Y-%m-%d %H:%M:%S")}
    loga(f"    params = {params}")
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute(TRADES_SQL, params)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return rows
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


def metadata_inventory(quiet=False):
    """Print which fields actually exist in _signal_metadata (spec: inspect
    what fields actually exist first). Read-only, closed in finally."""
    if quiet:
        return
    sql = """
SELECT _signal_metadata FROM trades
WHERE status = 'closed' AND _signal_metadata IS NOT NULL
ORDER BY open_time DESC LIMIT 1000
"""
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute(sql)
        from collections import Counter
        keys = Counter()
        n = 0
        bad = 0
        for (m,) in cur.fetchall():
            n += 1
            if isinstance(m, str):
                try:
                    m = json.loads(m)
                except Exception:
                    bad += 1
                    continue
            if isinstance(m, dict):
                for k in m:
                    keys[k] += 1
        loga(f"_signal_metadata inventory over the {n} most recent trades "
             f"with metadata:")
        speed_keys = [(k, c) for k, c in keys.most_common() if "speed" in k]
        loga(f"  speed-like keys: {speed_keys or 'NONE FOUND'}")
        loga(f"  top 20 keys: {keys.most_common(20)}")
        loga(f"  malformed/unparseable metadata documents: {bad}")
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


# ── Candle store (local sqlite; read-only) ────────────────────────────────────
class CandleStore:
    """Lazy reader for the local candles DB. Timeframes are tried finest-first
    with a COVERAGE check (the 1m/5m tables only hold the last ~30 days, the
    15m/1h/4h tables hold the full 90-day window), so every trade in the
    window gets path data at the best available resolution. Used for
    (a) first-touch ordering of the TP barrier vs the actual exit, and
    (b) extending the path past an actual stop-out when a wider stop would
    have survived it."""

    TFS = (("1m", 60), ("5m", 300), ("15m", 900), ("1h", 3600), ("4h", 14400))

    def __init__(self, db_path, quiet=False):
        self.db_path = db_path
        self.conn = None
        self.cache = {}
        self.quiet = quiet
        self.n_fetch = 0
        self.n_queries = 0
        self.tf_used = {}

    def open(self):
        self.conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)

    def close(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    @staticmethod
    def _cands(token):
        out = []
        for c in (token, token.upper(), token.lower()):
            if c not in out:
                out.append(c)
        return out

    def series(self, token, ts0, ts1):
        """List of (ts, open, high, low, close) covering [ts0, ts1] as well as
        the available data does. Empty list if nothing covers the START of the
        range (tail may be truncated at the end of available data — the
        horizon walk treats the last candle as the horizon mark)."""
        key = (token, int(ts0), int(ts1))
        if key in self.cache:
            return self.cache[key]
        if self.conn is None:
            self.open()
        for tf, spacing in self.TFS:
            for cand in self._cands(token):
                cur = self.conn.cursor()
                try:
                    self.n_queries += 1
                    cur.execute(
                        f"SELECT ts, open, high, low, close FROM candles_{tf} "
                        "WHERE token = ? AND ts >= ? AND ts <= ? ORDER BY ts",
                        (cand, int(ts0), int(ts1)))
                    rows = cur.fetchall()
                finally:
                    cur.close()
                if rows and rows[0][0] <= int(ts0) + 2 * spacing:
                    self.n_fetch += 1
                    self.tf_used[tf] = self.tf_used.get(tf, 0) + 1
                    self.cache[key] = rows
                    return rows
        self.cache[key] = []
        return []


def first_touch_ts(candles, ts_lo, ts_hi, level, direction):
    """First candle in [ts_lo, ts_hi] whose range touches `level` on the
    favourable side (LONG: high >= level, SHORT: low <= level).
    Returns candle ts or None. 1m granularity: a candle that spans both
    barriers is a tie (caller resolves with the envelope)."""
    for (ts, o, hi, lo, c) in candles:
        if ts < ts_lo:
            continue
        if ts > ts_hi:
            break
        if direction == "LONG":
            if hi >= level:
                return ts
        else:
            if lo <= level:
                return ts
    return None


def close_candle_ts(candles, close_ts):
    """Greatest candle ts <= close_ts (candle containing the actual exit)."""
    best = None
    for row in candles:
        if row[0] <= close_ts:
            best = row[0]
        else:
            break
    return best


def continuation_candidates(candles, t_start, horizon_end, stop_level,
                            tp_level, direction, entry_price):
    """Walk candles from the actual close forward. Returns a list of
    (world_label, exit_price_fraction) candidates for a barrier system of
    {stop_level, tp_level} until the horizon. Labels let the verdict stage
    pair the SAME hypothetical world across grid points (die-vs-die,
    horizon-vs-horizon), which keeps the delta envelope tight. Same-candle
    stop+tp ties yield BOTH candidates (envelope takes min/max). No trailing /
    hard-exit logic is replicated — documented approximation."""
    out = []
    got = False
    for (ts, o, hi, lo, c) in candles:
        if ts < t_start:
            continue
        if ts > horizon_end:
            break
        got = True
        hit_stop = (lo <= stop_level) if direction == "LONG" else (hi >= stop_level)
        hit_tp = (hi >= tp_level) if direction == "LONG" else (lo <= tp_level)
        if direction == "LONG":
            stop_frac = (stop_level - entry_price) / entry_price
            tp_frac = (tp_level - entry_price) / entry_price
        else:
            stop_frac = (entry_price - stop_level) / entry_price
            tp_frac = (entry_price - tp_level) / entry_price
        if hit_stop and hit_tp:
            out.append(("cont_stop", stop_frac))
            out.append(("cont_tp", tp_frac))
            return out
        if hit_stop:
            out.append(("cont_stop", stop_frac))
            return out
        if hit_tp:
            out.append(("cont_tp", tp_frac))
            return out
    if got:
        # horizon reached without either barrier: mark to horizon close
        last = None
        for row in candles:
            if row[0] <= horizon_end:
                last = row
            else:
                break
        if last is not None:
            hc_price = last[4]
            if direction == "LONG":
                out.append(("cont_horizon", (hc_price - entry_price) / entry_price))
            else:
                out.append(("cont_horizon", (entry_price - hc_price) / entry_price))
            return out
    return out  # empty -> caller falls back to envelope bounds


def delta_range(vd, cd):
    """Envelope of (pnl_v - pnl_cur) for one trade, pairing the SAME world
    label on both sides (die-vs-die, tp-vs-tp, horizon-vs-horizon) and
    conservatively crossing labels that exist on only one side. Identical
    candidate dicts contribute exactly 0 (they are not a swing)."""
    def flat(d):
        out = []
        for vs in d.values():
            out.extend(vs)
        return out

    ds = []
    for k in set(vd) & set(cd):
        if vd[k] == cd[k]:
            continue                       # same world, same value -> 0
        for a in vd[k]:
            for b in cd[k]:
                ds.append(a - b)
    for k in set(vd) - set(cd):
        for a in vd[k]:
            for b in flat(cd):
                ds.append(a - b)
    for k in set(cd) - set(vd):
        for b in cd[k]:
            for a in flat(vd):
                ds.append(a - b)
    if not ds:
        return (0.0, 0.0)
    return (min(ds), max(ds))


# ── Core: per-trade helpers ───────────────────────────────────────────────────
def row_frac_act(r):
    ep, xp = r["entry_price"], r["exit_price"]
    if ep is None or xp is None:
        return None
    ep, xp = float(ep), float(xp)
    if r["direction"] == "LONG":
        return (xp - ep) / ep
    return (ep - xp) / ep


def row_dist(price, r):
    """Distance (fraction) of `price` from entry, sign irrelevant."""
    return abs(float(price) - float(r["entry_price"])) / float(r["entry_price"])


def ts_of(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


# ── Sweep: SIGNAL_FILTER_SPEED_MIN (counterfactual admission) ────────────────
def sweep_speed(rows, thresholds, current, args, quiet=False):
    log("")
    log(BANNER)
    log("SWEEP 1 — SIGNAL_FILTER_SPEED_MIN  (counterfactual admission)")
    log(BANNER)
    reg_seen = sorted({str(r["volatility_regime"]) for r in rows})
    loga("Scope: the gate applies SIGNAL_FILTER_SPEED_MIN to SHORT signals in "
         "non-NEUTRAL regime (decider_run.py:1400). volatility_regime values "
         f"present in this window: {reg_seen} — "
         f"{'NEUTRAL absent, so' if 'NEUTRAL' not in reg_seen else 'NEUTRAL present — check override handling:'} "
         "the governed cohort = ALL SHORT trades with a recorded "
         "speed_percentile. The NEUTRAL override (15) and the LONG threshold "
         "(SPEED_MIN_THRESHOLD_LONG) are NOT this constant.")
    loga("Caveat A: the gate returns AMBIGUOUS (penalty), not a hard SKIP — "
         "'admission' here is a hypothetical strict enforcement.")
    loga("Caveat B: signals blocked entirely never appear in `trades`, so "
         "below-current thresholds can only re-weight already-recorded trades.")
    loga("Caveat C: the gate reads execution-time speed; the DB records "
         "signal-time speed_percentile (measurement noise, direction unknown).")

    cohort = [r for r in rows if r["direction"] == "SHORT"
              and r["_speed"] is not None]
    excluded = sum(1 for r in rows if r["direction"] == "SHORT"
                   and r["_speed"] is None)
    loga(f"Cohort: {len(cohort)} SHORT trades with speed_percentile "
         f"({excluded} SHORT trades lack the field and are excluded at EVERY "
         f"grid point — no cross-grid bias).")

    # porosity evidence: sub-threshold trades that DID trade after the raise
    # date the CEO raised the threshold 30 -> 40 (hermes_constants.py:1057)
    raise_date = datetime(2026, 8, 16, tzinfo=timezone.utc)
    porosity = [r for r in cohort
                if r["open_time"] is not None
                and ts_of(r["open_time"]) >= raise_date.timestamp()
                and r["_speed"] < current]
    loga(f"Porosity evidence: {len(porosity)} SHORT trades opened AFTER the "
         f"2026-08-16 raise to {current:g} still had speed < {current:g} "
         f"(AMBIGUOUS pass-through / bypass paths) — the gate is not binary "
         f"in production.")

    def metrics(subset, tag):
        pnls = [float(r["pnl_usdt"] or 0.0) for r in subset]
        n = len(subset)
        if n == 0:
            return dict(n=0, net=0.0, wr=0.0, mean=0.0, ci=(0.0, 0.0),
                        wr_ci=(0.0, 0.0))
        wins = sum(1 for p in pnls if p > 0)
        seed = args.seed + zlib.crc32(f"speed|{tag}|{n}".encode())
        ci = bootstrap_sum_ci(pnls, seed, args.bootstrap)
        return dict(n=n, net=sum(pnls), wr=100.0 * wins / n,
                    mean=sum(pnls) / n, ci=ci,
                    wr_ci=tuple(100.0 * x for x in wilson_ci(wins, n)))

    points = {}
    log("")
    hdr = (f"{'threshold':>9} {'n_admit':>8} {'n_swung':>8} {'net_USDT':>10} "
           f"{'net 95% CI':>22} {'WR%':>7} {'WR 95% CI':>16} "
           f"{'mean/tr':>9} {'n_removed':>9} {'removed_net':>11}")
    log(hdr)
    log("-" * len(hdr))
    for t in thresholds:
        sub = [r for r in cohort if r["_speed"] >= t]
        m = metrics(sub, f"{t}")
        rem = [r for r in cohort if r["_speed"] < t]
        rem_net = sum(float(r["pnl_usdt"] or 0.0) for r in rem)
        swung = sum(1 for r in cohort
                    if (r["_speed"] >= t) != (r["_speed"] >= current))
        lo, hi = m["ci"]
        wlo, whi = m["wr_ci"]
        log(f"{t:>9g} {m['n']:>8} {swung:>8} {money(m['net']):>10} "
            f"[{money(lo)}, {money(hi)}] {m['wr']:>6.1f}% "
            f"[{wlo:.1f}, {whi:.1f}] {m['mean']:>9.4f} {len(rem):>9} "
            f"{money(rem_net):>11}")
        points[t] = dict(lo=lo, hi=hi, n_book=m["n"], n_swung=swung,
                         net=m["net"], wr=m["wr"], removed_net=rem_net)

    # paired delta vs the current threshold: exact recount of the recorded
    # book (the admission model makes it deterministic), bootstrap CI printed
    # as a power note (how big an effect this sample could even resolve).
    cur_net = points[current]["net"]
    log("")
    loga("Paired delta vs the current threshold (d = net(t) - net(current); "
         "exact on the recorded book, CI = generalisation power):")
    log(f"{'threshold':>9} {'d_net':>9} {'d 95% CI':>24} {'n_swung':>8} {'check':>8}")
    for t in thresholds:
        p = points[t]
        p["mid"] = p["net"]
        if t == current:
            p["d_lo"] = p["d_hi"] = 0.0
            p["d_ci"] = (0.0, 0.0)
            log(f"{t:>9g} {money(0.0):>9} {'(current)':>24} "
                f"{p['n_swung']:>8} {'ref':>8}")
            continue
        signed = []
        for r in cohort:
            a_t = r["_speed"] >= t
            a_c = r["_speed"] >= current
            if a_t != a_c:
                pnl = float(r["pnl_usdt"] or 0.0)
                signed.append(pnl if a_t else -pnl)
        d = p["net"] - cur_net
        check = "ok" if abs(sum(signed) - d) < 1e-6 else "MISMATCH"
        seed = args.seed + zlib.crc32(f"speed-d|{t}".encode())
        d_ci = bootstrap_sum_ci(signed, seed, args.bootstrap)
        p["d_lo"] = p["d_hi"] = d
        p["d_ci"] = d_ci
        log(f"{t:>9g} {money(d):>9} [{money(d_ci[0])}, {money(d_ci[1])}]"
            f"  {p['n_swung']:>8} {check:>8}")

    # sensitivity: all directions (LONG is governed by a different constant —
    # shown only to demonstrate the result is not an artifact of the cohort)
    if not quiet:
        log("")
        loga("Sensitivity (ALL directions, not the governed scope):")
        log(f"{'threshold':>9} {'n':>8} {'net_USDT':>10} {'WR%':>7}")
        for t in thresholds:
            sub = [r for r in rows if r["_speed"] is not None
                   and r["_speed"] >= t]
            m = metrics(sub, f"{t}")
            log(f"{t:>9g} {m['n']:>8} {money(m['net']):>10} "
                f"{m['wr']:>6.1f}%")

    log("")
    loga("Approximations: (1) strict-enforcement counterfactual on a gate that "
         "is porous in production; (2) trades speed-blocked entirely are "
         "absent from the DB — below-threshold sets only re-weight recorded "
         "trades [bias direction unknown; porosity count above bounds the "
         "gap]; (3) signal-time vs execution-time speed mismatch [noise].")
    verdict, reasons = classify_verdict(current, points, args.min_n,
                                        mode="exact")
    # power note: the bootstrap CI of each paired delta shows how big an
    # effect this window could even resolve (THE PATTERN: significance)
    for t in thresholds:
        if t == current:
            continue
        p = points[t]
        ci = p.get("d_ci")
        if ci:
            reasons.append(
                f"power note: threshold {t:g} d={money(p['d_lo'])}, 95% CI "
                f"[{money(ci[0])}, {money(ci[1])}] (n_swung={p['n_swung']}) "
                f"— effects inside this CI are not resolvable in this window")
    print_verdict("SIGNAL_FILTER_SPEED_MIN", verdict, reasons)
    return dict(points=points, verdict=verdict, reasons=reasons,
                cohort_n=len(cohort), porosity_n=len(porosity))


# ── Sweep: ATR_SL_MIN ─────────────────────────────────────────────────────────
def prepare_sl(rows, cohort_c_mode, quiet=False):
    """Classify each trade for the SL counterfactual. Returns (ok_rows,
    excluded_counts)."""
    from tpsl_utils import _atr_tier  # noqa: F811 (explicit, same import)
    excluded = {"no_sl_distance": 0, "no_mae": 0, "no_prices": 0,
                "no_pnl_amount": 0}
    ok = []
    for r in rows:
        d = r["sl_distance"]
        if d is None:
            excluded["no_sl_distance"] += 1
            continue
        d = float(d)
        r["_d"] = d
        if r["mae_pct"] is None:
            excluded["no_mae"] += 1
            continue
        r["_mae_f"] = float(r["mae_pct"]) / 100.0
        r["_mfe_f"] = None if r["mfe_pct"] is None else float(r["mfe_pct"]) / 100.0
        f_act = row_frac_act(r)
        if f_act is None:
            excluded["no_prices"] += 1
            continue
        r["_f_act"] = f_act
        if r["pnl_usdt"] is None or r["amount_usdt"] is None:
            excluded["no_pnl_amount"] += 1
            continue
        r["_pnl"] = float(r["pnl_usdt"])
        r["_amt"] = float(r["amount_usdt"])
        r["_tp_fire"] = r["close_reason"] in TP_FIRE_REASONS
        r["_stop_out"] = r["close_reason"] in STOP_LOSS_REASONS
        # conclusive evidence: a NON-TRAILED stop-out's recorded stop level IS
        # the initial stop. If it sits above the current floor, the floor never
        # bound this trade (sl_distance is an A/B-group field and can say
        # otherwise — see approximation note). Count printed in cohort mix.
        r["_fired"] = None
        if (r["_stop_out"] and not r["trailing_activated"]
                and r["stop_loss"] is not None):
            ep, xp = float(r["entry_price"]), float(r["stop_loss"])
            if ep > 0:
                r["_fired"] = abs(xp - ep) / ep
        # cohort classification (documented model — see --help epilog)
        if (r["_fired"] is not None
                and r["_fired"] > hc.ATR_SL_MIN + 1e-6):
            r["_sl_cohort"] = "B_evidence_fired_above_floor"
        elif abs(d - hc.ATR_SL_MIN) < 1e-9 or any(
                abs(d - f) < 1e-9 for f in HISTORICAL_ERA_FLOORS):
            r["_sl_cohort"] = "A_floor_pinned"      # floor bound its placement
        elif d > hc.ATR_SL_MIN + 1e-12:
            r["_sl_cohort"] = "B_above_floor"       # atr/structural > floor
        else:
            r["_sl_cohort"] = ("C_below_floor_pinned" if cohort_c_mode == "pinned"
                               else "C_below_floor_unaffected")
        ok.append(r)
    return ok, excluded


def sl_new_sl_candidates(r, v, atr_cache):
    """Candidate values for the counterfactual initial stop distance (fraction)
    at floor value v, per the documented model. Returns a list of distinct
    candidates covering the envelope (breakpoints at v, d and mae). The
    sentinel None means 'actual outcome arm' (see the sweep loop)."""
    d = r["_d"]
    mae = r["_mae_f"]
    if r["_sl_cohort"] == "B_evidence_fired_above_floor":
        # fired stop level (> floor) = the initial stop, so:
        #   v <= fired: initial unchanged if it already >= v (actual arm),
        #               or the stop widens to v and mae >= fired >= v kills it
        #               (die-at-v arm) -> {actual, v};
        #   v >  fired: initial = max(initial, v) = v (die/cont via the mae
        #               rule), plus the actual arm in case an ATR update had
        #               pushed the stop above v -> {actual, v}
        return [None, v]
    if r["_sl_cohort"] == "B_above_floor":
        return [max(d, v)]                      # exact under the model
    if r["_sl_cohort"].startswith("C_below_floor_unaffected"):
        return [d]                              # floor never consulted
    # cohort A (and C_pinned): atr_comp <= d, new = max(atr_comp, v)
    atr_c = atr_cache.get(r["id"])
    if v >= d - 1e-12:
        if atr_c is not None:
            # 5/1295 reconstructed atr values exceed the recorded stop
            # (era/formula drift) — trust the reconstruction over [v]
            stat("sl_place_atr_reconstructed")
            return [max(atr_c, v)]
        return [v]                              # exact: atr_comp <= d <= v
    # v < d: atr_comp unknown in [0, d] -> envelope over breakpoints
    atr_c = atr_cache.get(r["id"])
    if atr_c is not None:
        stat("sl_place_atr_reconstructed")
        return [max(atr_c, v)]
    stat("sl_place_envelope_v_to_d")
    cands = [v, d]
    if v < mae < d:
        cands.append(mae)                       # pnl piecewise breaks at mae
    return sorted(set(cands))


def atr_component(r):
    """Reconstruct the ATR-based (pre-floor) SL from entry_atr_14 when
    available: min(ATR_SL_MAX, tier(a) * a), a = ATR in fraction of price.
    Returns None when unavailable — caller falls back to bounds."""
    a_abs = r.get("entry_atr_14")
    ep = float(r["entry_price"])
    if a_abs is None or ep is None:
        return None
    try:
        a = float(a_abs) / float(ep)
    except Exception:
        return None
    if a <= 0:
        return None
    val = min(hc.ATR_SL_MAX, _atr_tier(a) * a)
    return val


def sl_outcome_candidates(r, ns, candles_by_id, args, atr_cache):
    """dict world_label -> [pnl_usdt] for this trade with initial stop = ns.
    See --help epilog for the rules and their bias directions."""
    pnl, amt, mae, f_act = r["_pnl"], r["_amt"], r["_mae_f"], r["_f_act"]
    out = {}
    if mae >= ns - 1e-12:
        # new stop touched at or before the actual close -> dies at -ns
        out["die"] = [pnl + amt * ((-ns) - f_act)]
        return out
    # new stop never touched during the actual life
    if r["_stop_out"] and ns > abs(f_act) + 1e-12:
        # actual system died AT its stop; wider stop survives -> extend path
        cands = continuation_for_sl(r, ns, candles_by_id, args)
        if cands is None:                       # no candle data -> bounds
            out["die"] = [pnl + amt * ((-ns) - f_act)]                # pessimistic
            mfe_f = r["_mfe_f"]
            # optimistic: survive to the recorded MFE; with MFE missing the
            # best case degrades to ~breakeven (no favourable excursion known)
            out["ride_mfe"] = [pnl + amt * ((mfe_f if mfe_f is not None else 0.0)
                                            - f_act)]
            return out
        for label, frac in cands:
            out.setdefault(label, []).append(pnl + amt * (frac - f_act))
        return out
    out["actual"] = [pnl]                       # actual outcome stands
    return out


def continuation_for_sl(r, ns, candles_by_id, args):
    stat("sl_cont_attempt")
    if args.no_candles or r["open_time"] is None or r["close_time"] is None:
        stat("sl_cont_unresolved_notime")
        return None
    cid = r["id"]
    if cid in candles_by_id:
        candles = candles_by_id[cid]
        if candles is None:
            stat("sl_cont_unresolved_nocandle")
            return None
    else:
        ts0 = ts_of(r["open_time"])
        ts1 = ts_of(r["close_time"]) + args.horizon_hours * 3600
        candles = args.candles.series(r["token"], ts0, ts1)
        candles_by_id[cid] = candles if candles else None
        if not candles:
            stat("sl_cont_unresolved_nocandle")
            return None
    ep = float(r["entry_price"])
    if r["direction"] == "LONG":
        stop_level = ep * (1 - ns)
        tp_level = r["target"] if r["target"] is not None else None
        if tp_level is None:
            stat("sl_cont_unresolved_notarget")
            return None
    else:
        stop_level = ep * (1 + ns)
        tp_level = r["target"] if r["target"] is not None else None
        if tp_level is None:
            stat("sl_cont_unresolved_notarget")
            return None
    ts_start = ts_of(r["close_time"])
    horizon_end = ts_start + args.horizon_hours * 3600
    cands = continuation_candidates(candles, ts_start, horizon_end, stop_level,
                                    float(tp_level), r["direction"], ep)
    if not cands:
        # walk produced nothing (exit sits past the end of candle data):
        # degrade to the ENVELOPE, never silently to the actual outcome
        stat("sl_cont_unresolved_empty")
        return None
    stat("sl_cont_resolved")
    return cands


def sweep_sl(rows, values, current, args, cohort_c_mode="unaffected",
             quiet=False, label=""):
    STATS.clear()
    ok, excluded = prepare_sl(rows, cohort_c_mode)
    loga(f"cohort_c_mode={cohort_c_mode}: n={len(ok)} trades in engine; "
         f"excluded: {excluded}")
    from collections import Counter
    coh = Counter(r["_sl_cohort"] for r in ok)
    loga(f"cohort mix: {dict(coh)}  "
         f"(A = initial stop pinned at a floor value; B_above_floor = "
         f"sl_distance above floor; B_evidence = non-trailed stop-out whose "
         f"FIRED stop level is above the floor — conclusive proof the floor "
         f"did not bind; C = below every floor — explicit-SL / A/B-group paths)")

    atr_cache = {}
    for r in ok:
        if r["_sl_cohort"].startswith("A") or r["_sl_cohort"].startswith("C"):
            if r["_sl_cohort"].startswith("C") and cohort_c_mode != "pinned":
                continue
            atr_cache[r["id"]] = atr_component(r)
    n_atr = sum(1 for v in atr_cache.values() if v is not None)
    loga(f"entry_atr_14 reconstructable for {n_atr}/{len(atr_cache)} "
         f"floor-pinned trades (others use the [v, d] envelope).")

    candles_by_id = {}

    # actual book (reference) and engine-at-current (model + era gap)
    actual_net = sum(r["_pnl"] for r in ok)
    n_mismatch = 0
    mismatch_delta = 0.0
    per_v = {}
    for v in values:
        book_lo = book_hi = 0.0
        wr_lo_n = wr_hi_n = 0
        changed_vs_actual = 0
        dicts = []
        for r in ok:
            ns_cands = sl_new_sl_candidates(r, v, atr_cache)
            cdict = {}
            for ns in ns_cands:
                if ns is None:                  # evidence-cohort actual arm
                    cdict.setdefault("actual", []).append(r["_pnl"])
                    continue
                sub = sl_outcome_candidates(r, ns, candles_by_id, args,
                                            atr_cache)
                for k, vs in sub.items():
                    lst = cdict.setdefault(k, [])
                    for x in vs:
                        if x not in lst:
                            lst.append(x)
            if not cdict:
                cdict = {"actual": [r["_pnl"]]}
            dicts.append(cdict)
            vals = [x for vs in cdict.values() for x in vs]
            lo, hi = min(vals), max(vals)
            book_lo += lo
            book_hi += hi
            if all(p > 0 for p in vals):
                wr_lo_n += 1
            if any(p > 0 for p in vals):
                wr_hi_n += 1
            if len(vals) > 1 or abs(lo - r["_pnl"]) > 1e-9:
                changed_vs_actual += 1
        per_v[v] = dict(dicts=dicts, lo=book_lo, hi=book_hi,
                        wr_lo=100.0 * wr_lo_n / len(ok) if ok else 0.0,
                        wr_hi=100.0 * wr_hi_n / len(ok) if ok else 0.0,
                        n_book=len(ok), n_changed=changed_vs_actual)
    # paired deltas vs current (only trades whose counterfactual worlds differ
    # contribute; identical candidate dicts cancel exactly)
    cur_dicts = per_v[current]["dicts"] if current in per_v else None
    for v in values:
        p = per_v[v]
        if v == current:
            p["n_swung"] = 0
            p["d_lo"] = p["d_hi"] = 0.0
            continue
        if cur_dicts is None:
            p["n_swung"] = p["n_changed"]
            p["d_lo"] = p["d_hi"] = 0.0
            continue
        dlo = dhi = 0.0
        sw = 0
        for a, b in zip(p["dicts"], cur_dicts):
            if a == b:
                continue
            sw += 1
            lo, hi = delta_range(a, b)
            dlo += lo
            dhi += hi
        p["n_swung"] = sw
        p["d_lo"] = dlo
        p["d_hi"] = dhi
    # engine-vs-actual gap at the current value (audit)
    if current in per_v:
        cp = per_v[current]
        n_mismatch = 0
        for r, dd in zip(ok, cp["dicts"]):
            vals = [x for vs in dd.values() for x in vs]
            if len(vals) == 1 and abs(vals[0] - r["_pnl"]) > 0.02:
                n_mismatch += 1
        mismatch_delta = (cp["lo"] + cp["hi"]) / 2 - actual_net

    log("")
    log(f"  {'value':>8} {'n_book':>7} {'n_swung':>8} {'net lo':>9} "
        f"{'net hi':>9} {'net mid':>9} {'d_lo':>9} {'d_hi':>9} "
        f"{'WR lo%':>7} {'WR hi%':>7}")
    log("  " + "-" * 90)
    points = {}
    for v in values:
        p = per_v[v]
        mid = (p["lo"] + p["hi"]) / 2
        log(f"  {v:>8.4f} {p['n_book']:>7} {p['n_swung']:>8} "
            f"{money(p['lo']):>9} {money(p['hi']):>9} {money(mid):>9} "
            f"{money(p['d_lo']):>9} {money(p['d_hi']):>9} "
            f"{p['wr_lo']:>6.1f}% {p['wr_hi']:>6.1f}%")
        points[v] = dict(lo=p["lo"], hi=p["hi"], mid=mid,
                         d_lo=p["d_lo"], d_hi=p["d_hi"],
                         n_book=p["n_book"], n_swung=p["n_swung"],
                         wr_lo=p["wr_lo"], wr_hi=p["wr_hi"])
    log("")
    loga(f"REFERENCE actual book over engine cohort: n={len(ok)} "
         f"net={money(actual_net)} USDT")
    if current in per_v:
        loga(f"ENGINE at v=current({current:g}) vs ACTUAL book: "
             f"delta={money(mismatch_delta)} USDT over {n_mismatch} trades "
             f"differing by >$0.02 — era effect (history ran floors "
             f"1.2/1.3 before Oct-16; the sweep applies one uniform value by "
             f"design) plus model error. The deltas below are MODEL-"
             f"CONDITIONAL: they compare grid points inside the same model, "
             f"so the era component is common-mode; the residual model error "
             f"is validated separately (in-era re-run) and reported in the "
             f"result file.")
    loga(f"candles fetched: {len([c for c in candles_by_id.values() if c])} "
         f"trade windows (continuation for wider-stop survivors); "
         f"tf_used={args.candles.tf_used if args.candles else {}} "
         f"queries={args.candles.n_queries if args.candles else 0}")
    loga(f"resolution stats: {stat_block('sl_')}")
    log("")
    loga("Approximations: [bias direction]")
    loga("  * trailing/PM_TRAIL unaffected by a changed initial floor "
         "[widening: overstates profit locking; narrowing: understates it].")
    loga("  * uniform floor across the window, though history ran 1.2/1.3 "
         "[by design — 'set the constant to v' means exactly this].")
    loga("  * below-floor explicit-SL trades unaffected "
         f"[primary model; sensitivity mode={cohort_c_mode} printed separately].")
    loga("  * sl_distance is an A/B-group field (brain.py:594-597), not a "
         "guaranteed initial-stop record — non-stop-out trades take their "
         "initial stop from it, so where the ATR stop actually exceeded the "
         "floor this overstates the floor's reach. Non-trailed stop-outs "
         "carry conclusive evidence (the fired stop level) and are classified "
         "B_evidence instead [residual bias: trail/other exits whose initial "
         "stop exceeded the floor, direction unknown].")
    loga("  * widened-stop continuation replicates only {stop, TP, horizon} "
         "barriers — no trailing, no hard exits [widens dispersion].")
    loga("  * mae >= new_stop -> dies at -stop (first-barrier argument; the "
         "same-candle tie at the finest available resolution (1m-15m "
         "tiered, mix printed) is ignored) [slightly optimistic for stops].")
    loga("  * ATR_SL_MIN also feeds the ENTRY R:R gate "
         "(risk_reward_engine.py:604,640,753) — admission-side effects of a "
         "changed floor (blocked/extra trades) are NOT part of this "
         "counterfactual [missing blocked-cohort PnL, direction unknown].")
    verdict, reasons = classify_verdict(current, points, args.min_n)
    if current in per_v:
        reasons.append(
            f"model-conditional: engine-vs-actual reproduction gap at "
            f"current = {money(mismatch_delta)} USDT (era effect + model "
            f"error; see audit line above) — d intervals do not include it")
    print_verdict(f"ATR_SL_MIN{label}", verdict, reasons)
    return dict(points=points, verdict=verdict, reasons=reasons,
                actual_net=actual_net, engine_gap=mismatch_delta,
                n=len(ok), excluded=excluded, cohort=dict(coh))


# ── Sweep: ATR_TP_K_MULT ──────────────────────────────────────────────────────
def prepare_tp(rows, quiet=False):
    excluded = {"no_target": 0, "no_mfe": 0, "no_prices": 0, "no_pnl": 0}
    ok = []
    for r in rows:
        if r["target"] is None:
            excluded["no_target"] += 1
            continue
        T = row_dist(r["target"], r)              # recorded target distance
        r["_T"] = T
        if r["mfe_pct"] is None:
            excluded["no_mfe"] += 1
            continue
        r["_mfe_f"] = float(r["mfe_pct"]) / 100.0
        r["_mae_f"] = None if r["mae_pct"] is None else float(r["mae_pct"]) / 100.0
        f_act = row_frac_act(r)
        if f_act is None:
            excluded["no_prices"] += 1
            continue
        r["_f_act"] = f_act
        if r["pnl_usdt"] is None or r["amount_usdt"] is None:
            excluded["no_pnl"] += 1
            continue
        r["_pnl"] = float(r["pnl_usdt"])
        r["_amt"] = float(r["amount_usdt"])
        r["_tp_fire"] = r["close_reason"] in TP_FIRE_REASONS
        r["_sl_distance"] = None if r["sl_distance"] is None else float(r["sl_distance"])
        # enforcement gap: crossed the recorded target without a TP exit —
        # target was NOT a hard barrier for this trade (drift/structural).
        r["_target_violation"] = (not r["_tp_fire"]
                                  and r["_mfe_f"] > T + 1e-6)
        ok.append(r)
    return ok, excluded


def tp_new_targets(r, t, k_cur, bypass_mode="unaffected"):
    """Candidate counterfactual target distances at multiplier t, from the
    recorded target T. Exact for interior targets; envelopes at the floor/cap
    (placement of the ATR component is unknown there). Returns (lo, hi).

    Targets OUTSIDE [ATR_TP_MIN, ATR_TP_MAX] cannot be ATR-clamped placements:
      * above the cap: ATR placement can never exceed ATR_TP_MAX, so these are
        structural (rr_engine) targets — K never binds (both modes);
      * below the floor: a MIXTURE of era-clamped ATR targets (ATR_TP_MIN was
        0.8 then 1.3 inside the window — K DID bind) and structural targets (K
        does not). The population cannot be separated from the DB, so:
          bypass_mode='unaffected'   -> K does not bind (primary model)
          bypass_mode='proportional' -> new = T * t / k_cur (sensitivity)
    """
    T, floor, cap = r["_T"], hc.ATR_TP_MIN, hc.ATR_TP_MAX
    eps = 1e-6   # T is derived by division on 8-decimal prices (~1e-8 noise)
    if T > cap + eps:
        return (T, T)                        # structural: above ATR cap
    if T < floor - eps:
        if bypass_mode == "proportional":
            return (T * t / k_cur, T * t / k_cur)
        return (T, T)                        # bypass path: unaffected by K
    if T <= floor + eps:                          # floor-bound placement
        if t <= k_cur + 1e-12:
            return (floor, floor)                 # exact: k_atr*t <= floor
        hi = min(cap, floor * t / k_cur)
        return (floor, hi)
    if T >= cap - eps:                            # cap-bound placement
        if t >= k_cur - 1e-12:
            return (cap, cap)                     # exact: k_atr*t >= cap
        lo = max(floor, cap * t / k_cur)
        return (lo, cap)
    # interior: k_atr = T / k_cur exactly (ATR-derived assumption)
    nt = max(floor, min(cap, T * t / k_cur))
    return (nt, nt)


def tp_outcome_candidates(r, nt, candles_by_id, args):
    """dict world_label -> [pnl_usdt] with target = nt. Ordering of the TP
    touch vs the actual exit is resolved from candles (finest available,
    1m-15m tiered); same-candle ties
    and missing candles fall into the envelope."""
    pnl, amt, f_act = r["_pnl"], r["_amt"], r["_f_act"]
    if r["_target_violation"]:
        return {"actual": [pnl]}                     # barrier not enforced here
    if r["_tp_fire"]:
        T = r["_T"]
        if nt <= T + 1e-12:
            # TP fired first at T; a nearer target fires no later than T
            return {"tp": [pnl + amt * (nt - f_act)]}
        # wider target survives the actual TP exit -> extend path
        cands = tp_continuation(r, nt, candles_by_id, args)
        if cands is None:
            out = {"actual": [pnl],                  # pessimistic: never reached
                   "ride_mfe": [pnl + amt * (r["_mfe_f"] - f_act)]}
            sd = r["_sl_distance"]
            if sd is not None:
                # a wider target can lose the trade after the actual TP exit
                # (falls to the stop) -> the true value may lie BELOW actual
                out["die"] = [pnl + amt * ((-sd) - f_act)]
            return out
        out = {}
        for label, frac in cands:
            out.setdefault(label, []).append(pnl + amt * (frac - f_act))
        return out
    mfe = r["_mfe_f"]
    if mfe < nt - 1e-12:
        return {"actual": [pnl]}                     # TP never touched
    # TP level touched at or before the actual close -> ordering decides
    touch, tie = tp_touch(r, nt, candles_by_id, args)
    if touch is None or tie:
        # unresolved ordering (same-candle tie or no candle data):
        # both worlds stay in the envelope
        return {"actual": [pnl], "tp": [pnl + amt * (nt - f_act)]}
    return {"tp": [pnl + amt * (nt - f_act)]}


def tp_touch(r, nt, candles_by_id, args):
    """First-touch candle ts of the favourable nt level inside the trade's
    life. Returns (ts_or_None, tie). tie=True when the touch lands in the
    same candle as the actual exit (order within that candle unknowable;
    candle width is 1m-15m depending on era — tf mix is printed)."""
    if args.no_candles or r["open_time"] is None or r["close_time"] is None:
        stat("tp_touch_unresolved_notime")
        return (None, True)
    candles = candles_by_id.get(r["id"])
    if candles is None:
        ts0 = ts_of(r["open_time"])
        # same range as the continuation walk so one fetch serves both
        ts1 = ts_of(r["close_time"]) + args.horizon_hours * 3600
        candles = args.candles.series(r["token"], ts0, ts1)
        candles_by_id[r["id"]] = candles if candles else None
        if not candles:
            stat("tp_touch_unresolved_nocandle")
            return (None, True)
    ep = float(r["entry_price"])
    level = ep * (1 + nt) if r["direction"] == "LONG" else ep * (1 - nt)
    ts_close_c = close_candle_ts(candles, ts_of(r["close_time"]))
    ts = first_touch_ts(candles, ts_of(r["open_time"]), ts_of(r["close_time"]),
                        level, r["direction"])
    if ts is None:
        # mfe says it was touched but no candle shows it (rounding) -> tie
        stat("tp_touch_unresolved_rounding")
        return (None, True)
    if ts == ts_close_c:
        stat("tp_touch_tie_same_minute")
        return (ts, True)
    stat("tp_touch_resolved")
    return (ts, False)


def tp_continuation(r, nt, candles_by_id, args):
    stat("tp_cont_attempt")
    if args.no_candles or r["open_time"] is None or r["close_time"] is None:
        stat("tp_cont_unresolved_notime")
        return None
    candles = candles_by_id.get(r["id"])
    if candles is None:
        ts0 = ts_of(r["open_time"])
        ts1 = ts_of(r["close_time"]) + args.horizon_hours * 3600
        candles = args.candles.series(r["token"], ts0, ts1)
        candles_by_id[r["id"]] = candles if candles else None
        if not candles:
            stat("tp_cont_unresolved_nocandle")
            return None
    ep = float(r["entry_price"])
    d = r["_sl_distance"]
    if d is None:
        stat("tp_cont_unresolved_nodistance")
        return None
    if r["direction"] == "LONG":
        stop_level = ep * (1 - d)
        tp_level = ep * (1 + nt)
    else:
        stop_level = ep * (1 + d)
        tp_level = ep * (1 - nt)
    ts_start = ts_of(r["close_time"])
    horizon_end = ts_start + args.horizon_hours * 3600
    cands = continuation_candidates(candles, ts_start, horizon_end, stop_level,
                                    tp_level, r["direction"], ep)
    if not cands:
        stat("tp_cont_unresolved_empty")
        return None
    stat("tp_cont_resolved")
    return cands


def sweep_tpk(rows, values, current, args, quiet=False,
              bypass_mode="unaffected", label=""):
    STATS.clear()
    loga(f"bypass_mode={bypass_mode} (below-floor targets: "
         f"{'K does not bind — primary model' if bypass_mode == 'unaffected' else 'K binds proportionally — sensitivity'})")
    ok, excluded = prepare_tp(rows)
    loga(f"n={len(ok)} trades in engine; excluded: {excluded}")
    viol = sum(1 for r in ok if r["_target_violation"])
    loga(f"enforcement gap: {viol} trades crossed their recorded target "
         f"WITHOUT a TP exit (target not a hard barrier for them) — kept at "
         f"actual outcome at every grid point.")
    from collections import Counter
    placement = Counter()
    for r in ok:
        T = r["_T"]
        if T < hc.ATR_TP_MIN - 1e-6 or T > hc.ATR_TP_MAX + 1e-6:
            placement["outside_clamps_bypass"] += 1
        elif T <= hc.ATR_TP_MIN + 1e-6:
            placement["at_floor"] += 1
        elif T >= hc.ATR_TP_MAX - 1e-6:
            placement["at_cap"] += 1
        else:
            placement["interior"] += 1
    loga(f"recorded-target placement: {dict(placement)} "
         f"(interior => exact k_atr reconstruction; floor/cap => envelope; "
         f"outside clamps => bypass path, K not binding)")

    candles_by_id = {}
    actual_net = sum(r["_pnl"] for r in ok)
    k_cur = hc.ATR_TP_K_MULT
    per_v = {}
    for t in values:
        book_lo = book_hi = 0.0
        wr_lo_n = wr_hi_n = 0
        n_changed = 0
        dicts = []
        for r in ok:
            lo_nt, hi_nt = tp_new_targets(r, t, k_cur, bypass_mode)
            nt_cands = sorted({lo_nt, hi_nt})
            mfe = r["_mfe_f"]
            if lo_nt < mfe < hi_nt:
                nt_cands.append(mfe)              # piecewise breakpoint
            cdict = {}
            for nt in nt_cands:
                sub = tp_outcome_candidates(r, nt, candles_by_id, args)
                for k, vs in sub.items():
                    lst = cdict.setdefault(k, [])
                    for x in vs:
                        if x not in lst:
                            lst.append(x)
            if not cdict:
                cdict = {"actual": [r["_pnl"]]}
            dicts.append(cdict)
            vals = [x for vs in cdict.values() for x in vs]
            lo, hi = min(vals), max(vals)
            book_lo += lo
            book_hi += hi
            if all(p > 0 for p in vals):
                wr_lo_n += 1
            if any(p > 0 for p in vals):
                wr_hi_n += 1
            if len(vals) > 1 or abs(lo - r["_pnl"]) > 1e-9:
                n_changed += 1
        per_v[t] = dict(dicts=dicts, lo=book_lo, hi=book_hi,
                        wr_lo=100.0 * wr_lo_n / len(ok) if ok else 0.0,
                        wr_hi=100.0 * wr_hi_n / len(ok) if ok else 0.0,
                        n_book=len(ok), n_changed=n_changed)
    cur_dicts = per_v[current]["dicts"] if current in per_v else None
    for t in values:
        p = per_v[t]
        if t == current:
            p["n_swung"] = 0
            p["d_lo"] = p["d_hi"] = 0.0
            continue
        if cur_dicts is None:
            p["n_swung"] = p["n_changed"]
            p["d_lo"] = p["d_hi"] = 0.0
            continue
        dlo = dhi = 0.0
        sw = 0
        for a, b in zip(p["dicts"], cur_dicts):
            if a == b:
                continue
            sw += 1
            lo, hi = delta_range(a, b)
            dlo += lo
            dhi += hi
        p["n_swung"] = sw
        p["d_lo"] = dlo
        p["d_hi"] = dhi

    log("")
    log(f"  {'K':>6} {'n_book':>7} {'n_swung':>8} {'net lo':>9} {'net hi':>9} "
        f"{'net mid':>9} {'d_lo':>9} {'d_hi':>9} {'WR lo%':>7} {'WR hi%':>7}")
    log("  " + "-" * 88)
    points = {}
    for t in values:
        p = per_v[t]
        mid = (p["lo"] + p["hi"]) / 2
        log(f"  {t:>6.3f} {p['n_book']:>7} {p['n_swung']:>8} "
            f"{money(p['lo']):>9} {money(p['hi']):>9} {money(mid):>9} "
            f"{money(p['d_lo']):>9} {money(p['d_hi']):>9} "
            f"{p['wr_lo']:>6.1f}% {p['wr_hi']:>6.1f}%")
        points[t] = dict(lo=p["lo"], hi=p["hi"], mid=mid,
                         d_lo=p["d_lo"], d_hi=p["d_hi"],
                         n_book=p["n_book"], n_swung=p["n_swung"],
                         wr_lo=p["wr_lo"], wr_hi=p["wr_hi"])
    log("")
    loga(f"REFERENCE actual book: n={len(ok)} net={money(actual_net)} USDT")
    if current in per_v:
        cp = per_v[current]
        mid = (cp["lo"] + cp["hi"]) / 2
        loga(f"ENGINE at K=current({current:g}): net mid={money(mid)} "
             f"(envelope width {money(cp['hi'] - cp['lo'])}) — at the current "
             f"value the engine should be near-identical to the actual book; "
             f"the gap is model error (era effect does not apply to K). The "
             f"deltas below are MODEL-CONDITIONAL.")
    loga(f"candles fetched: {len([c for c in candles_by_id.values() if c])} "
         f"trade windows (first-touch ordering + continuation); "
         f"tf_used={args.candles.tf_used if args.candles else {}} "
         f"queries={args.candles.n_queries if args.candles else 0}")
    loga(f"resolution stats: {stat_block('tp_')}")
    log("")
    loga("Approximations: [bias direction]")
    loga("  * interior targets treated as ATR-derived (structural rr_engine "
         "targets misread) [direction unknown; affects placement of interior "
         "targets only].")
    loga("  * TP-first ordering from candle data (finest available, "
         "1m-15m tiered, mix printed); same-candle ties resolved "
         "pessimistically in one arm and optimistically in the other "
         "[true value inside the envelope].")
    loga("  * continuation past an actual TP exit replicates {stop, TP, "
         "horizon} only — no trailing [widens dispersion].")
    loga("  * grep-verified: ATR_TP_K_MULT has NO consumer in the admission "
         "path (decider_run.py, risk_reward_engine.py, signal_compactor.py, "
         "signals/*) — every consumer is exit placement, so this exit-side "
         "counterfactual covers K's whole effect surface.")
    verdict, reasons = classify_verdict(current, points, args.min_n)
    if current in per_v:
        reasons.append(
            f"model-conditional: engine-vs-actual reproduction gap at "
            f"current = {money((per_v[current]['lo'] + per_v[current]['hi']) / 2 - actual_net)} "
            f"USDT (model error) — d intervals do not include it")
    print_verdict(f"ATR_TP_K_MULT{label}", verdict, reasons)
    return dict(points=points, verdict=verdict, reasons=reasons,
                actual_net=actual_net, n=len(ok), excluded=excluded,
                placement=dict(placement), violations=viol)


# ── Verdict classification (rules printed with every verdict) ─────────────────
VERDICT_RULES = """\
verdict rules (identical for all three constants; d = neighbour metric minus
current metric, so d<0 means the neighbour is worse):
  n gate   : mode=exact (SPEED, a statistical recount) requires n_swung >=
             min_n per ±1 neighbour, else INDETERMINATE. mode=bound (SL/TPK)
             has no n gate: its d interval is a hard envelope over the
             per-trade counterfactual worlds (matched-arm pairing), so a small
             n_swung with a tight envelope is itself the evidence.
  SPIKE    : some ±1 neighbour has d_hi < 0 AND d_hi < -0.5*|current metric|
             -> the neighbour collapses -> only the exact value works.
  HILL     : every ±1 neighbour has d_lo >= -0.5*|current metric|
             -> no neighbour can be substantially worse -> hill/plateau.
  otherwise: INDETERMINATE (degradation possible but not shown to be a
             collapse, or the interval is too wide to rank)."""


def classify_verdict(current, points, min_n, mode="bound"):
    reasons = []
    if current not in points:
        return "INDETERMINATE", ["current value missing from grid"]
    cp = points[current]
    if cp["n_book"] < min_n:
        return "INDETERMINATE", [
            f"n_book={cp['n_book']} at current value < min_n={min_n}"]

    ordered = sorted(points)
    idx = ordered.index(current)
    neigh = []
    if idx - 1 >= 0:
        neigh.append(ordered[idx - 1])
    if idx + 1 < len(ordered):
        neigh.append(ordered[idx + 1])
    if not neigh:
        return "INDETERMINATE", ["grid has no neighbour of the current value"]

    metric = cp.get("mid", cp.get("net", 0.0))
    # $1 floor: without it the bar degenerates to ~0 whenever the book net is
    # near zero (any negative d_hi would then be a "spike")
    substantial = max(0.5 * abs(metric), 1.0)
    reasons.append(
        f"current metric={money(metric)} USDT; collapse bar = "
        f"max(0.5*|metric|, $1) = {money(substantial)} USDT")

    if mode == "exact":
        # statistical recount: the identifying sample must be big enough
        for nv in neigh:
            if points[nv]["n_swung"] < min_n:
                reasons.append(
                    f"identifying sample n_swung={points[nv]['n_swung']} at "
                    f"value {nv:g} < min_n={min_n} — too few trades differ "
                    f"between this grid point and the current value")
        if any(r.startswith("identifying sample") for r in reasons):
            return "INDETERMINATE", reasons

    def _bounds(np_):
        # bound mode: the hard envelope IS the interval. exact mode (SPEED):
        # the bootstrap CI is the interval — a point estimate alone must not
        # be treated as certainty (THE PATTERN: significance).
        if mode == "exact":
            ci = np_.get("d_ci")
            if ci:
                return ci[0], ci[1]
        return np_["d_lo"], np_["d_hi"]

    # spike test
    for nv in neigh:
        np_ = points[nv]
        _lo, _hi = _bounds(np_)
        if _hi < 0 and _hi < -substantial:
            reasons.append(
                f"±1 neighbour {nv:g} collapses: d_hi={money(_hi)} "
                f"is below zero and below {money(-substantial)} — only the "
                f"exact current value works")
            return "SPIKE", reasons

    # hill test
    notes = []
    ok_hill = True
    for nv in neigh:
        np_ = points[nv]
        _lo, _hi = _bounds(np_)
        if _lo < -substantial:
            ok_hill = False
            notes.append(
                f"neighbour {nv:g}: d interval [{money(_lo)}, "
                f"{money(_hi)}] reaches below {money(-substantial)} "
                f"— a substantial degradation cannot be ruled out "
                f"(n_swung={np_['n_swung']})")
        if _lo > 0:
            notes.append(
                f"neighbour {nv:g} is model-conditional BETTER than current "
                f"(d_lo={money(_lo)} > 0 inside the counterfactual model) — "
                f"peak is shifted; still not a spike")
    if ok_hill:
        reasons.append(
            f"every ±1 neighbour's worst case stays above "
            f"{money(-substantial)} — no collapse away from the current "
            f"value (hill/plateau)")
        for nv in neigh:
            np_ = points[nv]
            _lo, _hi = _bounds(np_)
            kind = "CI" if (mode == "exact" and np_.get("d_ci")) else "envelope"
            reasons.append(
                f"neighbour {nv:g}: d {kind} [{money(_lo)}, "
                f"{money(_hi)}], n_swung={np_['n_swung']}")
        reasons.extend(notes)
        if metric <= 0:
            reasons.append(
                "note: the current value's book is not positive — HILL here "
                "means 'no neighbour collapse', not 'profitable'")
        return "HILL", reasons

    reasons.append(
        "degradation is possible but not shown to be a collapse, or the "
        "interval is too wide to rank the current value against its "
        "neighbours")
    reasons.extend(notes)
    return "INDETERMINATE", reasons


def print_verdict(name, verdict, reasons):
    log("")
    log(f"VERDICT [{name}]: {verdict}")
    for r in reasons:
        log(f"    - {r}")
    log("")


# ── main ──────────────────────────────────────────────────────────────────────
def sanity_checks(rows, quiet):
    if quiet:
        return
    from collections import Counter
    loga(f"rows={len(rows)}")
    cr = Counter(r["close_reason"] for r in rows)
    loga(f"close_reason top10: {cr.most_common(10)}")
    cov = {
        "sl_distance": sum(1 for r in rows if r["sl_distance"] is not None),
        "mae_pct": sum(1 for r in rows if r["mae_pct"] is not None),
        "mfe_pct": sum(1 for r in rows if r["mfe_pct"] is not None),
        "target": sum(1 for r in rows if r["target"] is not None),
        "speed_percentile": sum(1 for r in rows if r["_speed"] is not None),
        "entry_atr_14": sum(1 for r in rows if r.get("entry_atr_14") is not None),
    }
    loga(f"field coverage: {cov}")
    # pnl_usdt sensitivity check: pnl_usdt ~= amount_usdt * price_fraction
    errs = []
    for r in rows[:1500]:
        f = row_frac_act(r)
        if f is None or r["amount_usdt"] is None or r["pnl_usdt"] is None:
            continue
        errs.append(abs(float(r["amount_usdt"]) * f - float(r["pnl_usdt"])))
    if errs:
        errs.sort()
        loga(f"pnl sensitivity check |amount*frac - pnl_usdt|: "
             f"median={errs[len(errs)//2]:.4f} p95={errs[int(0.95*len(errs))]:.4f} "
             f"(confirms pnl_usdt ~ amount_usdt * price fraction; counterfactual "
             f"deltas use this sensitivity)")


def parse_dt(s, flag):
    """Accept YYYY-MM-DD or a full ISO datetime (UTC if naive). Full ISO in
    --since/--until is what makes a run exactly reproducible (the REPRODUCE
    line prints it)."""
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        raise SystemExit(f"ERROR: cannot parse {flag} value {s!r} "
                         f"(use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")


def main(argv=None):
    args = build_parser().parse_args(argv)
    for a in (args.sl_step, args.speed_step, args.tpk_step):
        if a <= 0:
            log("ERROR: step sizes must be > 0")
            return 2
    for name in ("sl_depth", "speed_depth", "tpk_depth"):
        if getattr(args, name) < 1:
            log(f"ERROR: --{name.replace('_', '-')} must be >= 1 "
                 f"(a grid needs the current value plus neighbours)")
            return 2
    if args.bootstrap < 1:
        log("ERROR: --bootstrap must be >= 1")
        return 2
    if args.days <= 0 and not args.since:
        log("ERROR: need --days > 0 or --since")
        return 2

    now = datetime.now(timezone.utc)
    if args.since:
        since = parse_dt(args.since, "--since")
    else:
        since = (now - timedelta(days=args.days)).replace(
            hour=0, minute=0, second=0, microsecond=0)
    until = parse_dt(args.until, "--until") if args.until else now

    consts = {c.strip().lower() for c in args.constants.split(",")}
    if "all" in consts:
        consts = {"speed", "sl", "tpk"}
    bad = consts - {"speed", "sl", "tpk"}
    if bad:
        log(f"ERROR: unknown constants {sorted(bad)} (choose from speed,sl,tpk)")
        return 2

    log(BANNER)
    log("neighbor_step_sweep.py — ±step neighbour sweep (hill vs spike)")
    log(BANNER)
    log(f"run at (UTC)      : {now.isoformat(timespec='seconds')}")
    log(f"window             : [{since.isoformat()}, {until.isoformat()})  "
        f"(--days {args.days} unless --since given)")
    log(f"constants requested: {sorted(consts)}")
    log(f"current values     : ATR_SL_MIN={hc.ATR_SL_MIN}  "
        f"SIGNAL_FILTER_SPEED_MIN={hc.SIGNAL_FILTER_SPEED_MIN}  "
        f"ATR_TP_K_MULT={hc.ATR_TP_K_MULT}  "
        f"(read from hermes_constants.py at runtime)")
    log(f"grids              : speed ±{args.speed_depth}×{args.speed_step:g}  "
        f"sl ±{args.sl_depth}×{args.sl_step:g}  "
        f"tpk ±{args.tpk_depth}×{args.tpk_step:g}")
    log(f"min_n={args.min_n}  bootstrap={args.bootstrap}  seed={args.seed}  "
        f"horizon={args.horizon_hours:g}h  candles={'OFF' if args.no_candles else 'ON'}")
    log("mode               : READ-ONLY analysis — no DB writes, no API calls, "
        "no trading-path changes")
    log("")
    log(VERDICT_RULES)
    log("")

    t0 = time.time()
    rows = fetch_trades(since, until, args.quiet)
    # derived fields used by every sweep
    for r in rows:
        sp = r.get("speed_percentile")
        try:
            r["_speed"] = float(sp) if sp is not None else None
        except (TypeError, ValueError):
            r["_speed"] = None
    sanity_checks(rows, args.quiet)
    metadata_inventory(args.quiet)

    results = dict(
        run_at=now.isoformat(timespec="seconds"),
        window=[since.isoformat(), until.isoformat()],
        params=dict(min_n=args.min_n, bootstrap=args.bootstrap,
                    seed=args.seed, horizon_hours=args.horizon_hours,
                    sl_step=args.sl_step, sl_depth=args.sl_depth,
                    speed_step=args.speed_step, speed_depth=args.speed_depth,
                    tpk_step=args.tpk_step, tpk_depth=args.tpk_depth,
                    candles=not args.no_candles),
        current=dict(ATR_SL_MIN=hc.ATR_SL_MIN,
                     SIGNAL_FILTER_SPEED_MIN=hc.SIGNAL_FILTER_SPEED_MIN,
                     ATR_TP_K_MULT=hc.ATR_TP_K_MULT),
        sql=TRADES_SQL.strip(),
        sql_params={"since": since.strftime("%Y-%m-%d %H:%M:%S"),
                    "until": until.strftime("%Y-%m-%d %H:%M:%S")},
    )

    candles = None
    try:
        if not args.no_candles:
            if not os.path.exists(CANDLES_DB):
                log(f"WARNING: candles DB not found at {CANDLES_DB} — "
                    f"ordering/continuation degrade to envelopes")
                args.no_candles = True
                args.candles = None
            else:
                candles = CandleStore(CANDLES_DB, args.quiet)
                candles.open()
                args.candles = candles
                loga(f"candles DB open: {CANDLES_DB} (read-only, tiered "
                     f"1m/5m/15m/1h/4h fallback)")
        else:
            args.candles = None

        if "speed" in consts:
            thr = parse_grid(float(hc.SIGNAL_FILTER_SPEED_MIN),
                             args.speed_step, args.speed_depth, lo=0.0)
            results["speed"] = sweep_speed(rows, thr,
                                           float(hc.SIGNAL_FILTER_SPEED_MIN),
                                           args, args.quiet)
        if "sl" in consts:
            vals = parse_grid(float(hc.ATR_SL_MIN), args.sl_step,
                              args.sl_depth, lo=1e-4)
            results["sl"] = sweep_sl(rows, vals, float(hc.ATR_SL_MIN), args,
                                     cohort_c_mode="unaffected",
                                     quiet=args.quiet)
            # sensitivity: below-floor explicit-SL trades treated as pinned
            sens = sweep_sl(rows, vals, float(hc.ATR_SL_MIN), args,
                            cohort_c_mode="pinned", quiet=True,
                            label=" [sensitivity: C-pinned]")
            results["sl_sensitivity"] = dict(
                points=sens["points"], verdict=sens["verdict"],
                reasons=sens["reasons"], cohort=sens["cohort"])
        if "tpk" in consts:
            kvals = parse_grid(float(hc.ATR_TP_K_MULT), args.tpk_step,
                               args.tpk_depth, lo=1e-4)
            results["tpk"] = sweep_tpk(rows, kvals, float(hc.ATR_TP_K_MULT),
                                       args, args.quiet,
                                       bypass_mode="unaffected")
            # sensitivity: below-floor targets treated as K-proportional
            # (era-clamped ATR targets where K did bind)
            sens = sweep_tpk(rows, kvals, float(hc.ATR_TP_K_MULT), args,
                             bypass_mode="proportional",
                             label=" [sensitivity: below-floor K-proportional]")
            results["tpk_sensitivity"] = dict(
                points=sens["points"], verdict=sens["verdict"],
                reasons=sens["reasons"])
    finally:
        if candles is not None:
            candles.close()

    log(BANNER)
    log(f"done in {time.time()-t0:.1f}s  "
        f"(read-only; nothing was written to any database)")
    repro = (f"python3 scripts/neighbor_step_sweep.py "
             f"--since {since.isoformat()} "
             f"--until {until.isoformat()} "
             f"--min-n {args.min_n} --bootstrap {args.bootstrap} "
             f"--seed {args.seed} --horizon-hours {args.horizon_hours:g} "
             f"--sl-step {args.sl_step:g} --sl-depth {args.sl_depth} "
             f"--speed-step {args.speed_step:g} --speed-depth {args.speed_depth} "
             f"--tpk-step {args.tpk_step:g} --tpk-depth {args.tpk_depth} "
             f"--constants {','.join(sorted(consts))}")
    log(f"REPRODUCE (same numbers): {repro}")
    results["reproduce"] = repro

    if args.json_out:
        def enc(o):
            if isinstance(o, set):
                return sorted(o)
            if isinstance(o, datetime):
                return o.isoformat()
            return str(o)
        with open(args.json_out, "w") as f:
            json.dump(results, f, indent=2, default=enc)
        log(f"JSON written: {args.json_out}")

    log("")
    log("FINAL VERDICTS:")
    for key, name in (("speed", "SIGNAL_FILTER_SPEED_MIN"),
                      ("sl", "ATR_SL_MIN"),
                      ("tpk", "ATR_TP_K_MULT")):
        if key in results:
            log(f"  {name:26s} {results[key]['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
