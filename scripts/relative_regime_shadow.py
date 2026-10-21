#!/usr/bin/env python3
"""
relative_regime_shadow.py — Shadow-only per-asset relative volatility regimes.

Computes BOTH absolute (current classify_volatility) and relative (per-asset
percentile vs own trailing window) regime labels for the live universe, and
logs every would-be disagreement. ZERO enforcement — this never touches any
trading gate, score, or block. Pure counterfactual data collection.

Status: SHADOW-ONLY during vacation (plans/t-vacation-mode-2026-10-14.md CEO
Brief item #2: "START shadow during vacation (zero enforcement)"). Full rollout
requires >=7d shadow + own-conclusions out-of-sample verification + T/CEO
sign-off behind a VOL_REGIME_MODE flag (plans/vol-regime-relative-thresholds-
2026-10-13.md). Evidence: brain/vol-regime-multiyear-audit-2026-10-13.md.

Design:
  - Per token: current ATR(14)% from volatility_gate_v2.get_atr_pct (same
    source as the live gate — no drift).
  - Relative label: rank current ATR% against a trailing 180d distribution of
    daily-sampled ATR(14)% from candles_1h. Bands: FLAT <p25, NORMAL p25-p75,
    HIGH p75-p95, EXTREME >=p95.
  - MAXXED stays ABSOLUTE (is_maxxed layered on top) — plan section B: the
    >=4% tail is genuinely bad both directions regardless of asset baseline.
  - Sparse-history fallback: <60 daily samples -> relative label = absolute
    (plan section D).
  - Append per-run diff summary to data/relative_regime_shadow.json.

Tuning params live here, not hermes_constants.py — constants are frozen
during vacation and this is instrumentation, not a trading gate. Move them
when relative-regime gets full approval.
"""
import sys
import os
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sqlite3
from paths import HERMES_DATA
from hermes_log import log
from volatility_gate_v2 import get_atr_pct, classify_volatility, is_maxxed

# ── Tuning (instrumentation — see module docstring) ─────────────────────────
HISTORY_PATH = os.path.join(HERMES_DATA, 'relative_regime_shadow.json')
HISTORY_MAX_READINGS = 336        # 14d of hourly readings
CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
TOKEN_FRESHNESS_SEC = 86400       # token must have a 1h candle in last 24h
TRAILING_DAYS = 180               # per-asset history window (plan section A)
MIN_SAMPLES = 60                  # below this -> fall back to absolute (plan D)
DAILY_SAMPLE_BARS = 24            # sample ATR(14) once per day of 1h bars
# Relative bands (percentile cut points on own history)
REL_P25, REL_P75, REL_P95 = 25, 75, 95


def _live_tokens():
    conn = sqlite3.connect(CANDLES_DB, timeout=10)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT token FROM candles_1h "
            "WHERE ts > strftime('%s','now') - ?",
            (TOKEN_FRESHNESS_SEC,),
        )
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def _percentile(sorted_vals, pct):
    if not sorted_vals:
        return None
    k = max(0, min(len(sorted_vals) - 1, int(round((pct / 100.0) * (len(sorted_vals) - 1)))))
    return sorted_vals[k]


def _atr_history_pct(token):
    """Daily-sampled ATR(14)% over the trailing window, oldest-first.

    Returns (current_atr_pct, history_pct_list). Either may be None.
    """
    conn = sqlite3.connect(CANDLES_DB, timeout=10)
    try:
        cur = conn.cursor()
        limit = TRAILING_DAYS * DAILY_SAMPLE_BARS + 20
        cur.execute(
            "SELECT high, low, close FROM candles_1h "
            "WHERE token = ? AND is_closed = 1 ORDER BY ts DESC LIMIT ?",
            (token.upper(), limit),
        )
        rows = cur.fetchall()
    finally:
        conn.close()
    if len(rows) < MIN_SAMPLES + 14:
        return None, None
    candles = list(reversed(rows))  # oldest-first
    # True ranges for every bar
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i][0], candles[i][1], candles[i - 1][2]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    # Daily-sample ATR(14)%: every DAILY_SAMPLE_BARS bars from the end
    history = []
    # sample indices in candles space (need 14 TRs before each sample point)
    n = len(candles)
    idx = n - 1
    while idx >= 14:
        atr14 = sum(trs[idx - 14:idx]) / 14
        close = candles[idx][2]
        if close > 0:
            history.append((atr14 / close) * 100)
        idx -= DAILY_SAMPLE_BARS
    history.reverse()  # oldest-first
    current = history[-1] if history else None
    return current, history


def _relative_label(current, history_sorted):
    """Percentile label on own history. None -> fall back to absolute."""
    if current is None or len(history_sorted) < MIN_SAMPLES:
        return None
    below = sum(1 for v in history_sorted if v < current)
    pct = 100.0 * below / len(history_sorted)
    if pct < REL_P25:
        return 'FLAT'
    if pct < REL_P75:
        return 'NORMAL'
    if pct < REL_P95:
        return 'HIGH'
    return 'EXTREME'


def _load_history():
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH) as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save_history(history):
    tmp = HISTORY_PATH + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(history[-HISTORY_MAX_READINGS:], f)
    os.replace(tmp, HISTORY_PATH)


def main():
    tokens = _live_tokens()
    if not tokens:
        log("  ⚠️ [REL-REGIME] no live tokens found — skipping")
        return

    abs_dist, rel_dist = {}, {}
    flips = []           # (token, abs, rel, atr, pct_rank)
    n_classified = 0
    n_rel = 0            # tokens with enough history for a relative label
    n_maxxed = 0

    for tok in tokens:
        try:
            atr = get_atr_pct(tok)
        except Exception:
            atr = None
        if atr is None:
            continue
        n_classified += 1
        abs_reg = classify_volatility(atr)
        abs_dist[abs_reg] = abs_dist.get(abs_reg, 0) + 1
        if is_maxxed(atr):
            n_maxxed += 1

        hist_atr, hist = _atr_history_pct(tok)
        rel_reg = None
        if hist:
            hist_sorted = sorted(hist)
            rel_reg = _relative_label(hist_atr, hist_sorted)
        if rel_reg:
            n_rel += 1
            rel_dist[rel_reg] = rel_dist.get(rel_reg, 0) + 1
            if rel_reg != abs_reg:
                below = sum(1 for v in hist_sorted if v < hist_atr)
                pct_rank = round(100.0 * below / len(hist_sorted), 1)
                flips.append((tok, abs_reg, rel_reg, round(atr, 2), pct_rank))

    if n_classified == 0:
        log("  ⚠️ [REL-REGIME] zero tokens classified — skipping")
        return

    n_flips = len(flips)
    flip_pct = 100.0 * n_flips / n_rel if n_rel else 0.0

    abs_str = ' '.join(f"{k}={v}" for k, v in sorted(abs_dist.items()))
    rel_str = ' '.join(f"{k}={v}" for k, v in sorted(rel_dist.items())) or 'n/a'
    log(f"  📊 [REL-REGIME] n={n_classified} (rel-available={n_rel}) MAXXED={n_maxxed} | abs: {abs_str} | rel: {rel_str}")
    log(f"  📊 [REL-REGIME] would-flip {n_flips}/{n_rel} ({flip_pct:.1f}%) labels vs absolute")

    # Detail: up to 15 flips (sorted by |absolute rank - 50| extremity ignored — just stable order)
    for tok, a, r, atr, pct in sorted(flips, key=lambda x: x[0])[:15]:
        log(f"    ↔️ [REL-REGIME] {tok}: abs={a} rel={r} atr%={atr} own-pct={pct}")

    history = _load_history()
    history.append({
        'ts': datetime.now(timezone.utc).isoformat(),
        'n': n_classified,
        'n_rel': n_rel,
        'n_flips': n_flips,
        'flip_pct': round(flip_pct, 2),
        'n_maxxed': n_maxxed,
        'abs_dist': abs_dist,
        'rel_dist': rel_dist,
        'flips': flips[:50],
    })
    _save_history(history)
    log(f"  💾 [REL-REGIME] reading {len(history)} saved → {HISTORY_PATH}")


if __name__ == '__main__':
    main()
