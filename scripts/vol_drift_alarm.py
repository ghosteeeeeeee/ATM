#!/usr/bin/env python3
"""
vol_drift_alarm.py — Shadow-only drift alarm for volatility regime labels.

Alerts when the EXTREME(+MAXXED) share of the live universe leaves its own
trailing historical band. Catches miscalibration and regime shifts that would
otherwise silently degrade every regime-keyed gate (SIGNAL_TYPE_OVERRIDES,
VOL_PHASE_MULTS, etc).

Status: SHADOW-ONLY / READ-ONLY. Zero enforcement. Zero trading impact.
Approved: plans/t-vacation-mode-2026-10-14.md CEO Brief item #1
("SHIP as shadow-only during vacation"). Evidence: brain/vol-regime-multiyear-audit-2026-10-13.md.

Design:
  - Every run: classify all tokens with recent 1h candles into FLAT/NORMAL/HIGH/EXTREME
    (reusing volatility_gate_v2.get_atr_pct + classify_volatility + is_maxxed).
  - Append (ts, extreme_share, maxx_share, n) to data/vol_drift_history.json.
  - After bootstrap (>= BOOTSTRAP_READINGS), compute p10/p90 of extreme_share
    over the trailing window. If current share falls outside the band, write an
    alert to automation/ceo/vacation_alerts.json (same sink as vacation_guardrail).
  - When the relative-regime work gets full approval, tuning params move to
    hermes_constants.py. Kept here because constants are frozen during vacation
    and this is instrumentation, not a trading gate.

Runs hourly via hermes-vol-drift-alarm.timer.
"""
import sys
import os
import json
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sqlite3
from paths import HERMES_DATA
from hermes_log import log
from volatility_gate_v2 import get_atr_pct, classify_volatility, is_maxxed

# ── Tuning (instrumentation params — not trading gates; see module docstring) ──
HISTORY_PATH = os.path.join(HERMES_DATA, 'vol_drift_history.json')
ALERT_PATH = os.path.join(HERMES_DATA, '..', 'automation', 'ceo', 'vacation_alerts.json')
HISTORY_MAX_READINGS = 720       # 30d of hourly readings
BOOTSTRAP_READINGS = 168         # 7d before alerting (band needs a baseline)
P10, P90 = 10, 90                # historical band percentiles
CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
TOKEN_FRESHNESS_SEC = 86400      # token must have a 1h candle in last 24h


def _live_tokens():
    """Tokens with at least one 1h candle in the last 24h."""
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
    """Nearest-rank percentile on a pre-sorted list. Empty -> None."""
    if not sorted_vals:
        return None
    k = max(0, min(len(sorted_vals) - 1, int(round((pct / 100.0) * (len(sorted_vals) - 1)))))
    return sorted_vals[k]


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


def _write_alert(level, message, data):
    """Append alert to vacation_alerts.json (same sink as vacation_guardrail)."""
    try:
        os.makedirs(os.path.dirname(ALERT_PATH), exist_ok=True)
        alerts = []
        if os.path.exists(ALERT_PATH):
            with open(ALERT_PATH) as f:
                alerts = json.load(f)
        alerts.append({
            'ts': datetime.now(timezone.utc).isoformat(),
            'source': 'vol_drift_alarm',
            'level': level,
            'message': message,
            'data': data,
        })
        with open(ALERT_PATH, 'w') as f:
            json.dump(alerts[-50:], f, indent=2)
    except Exception as e:
        log(f"  ⚠️ [VOL-DRIFT] alert write failed: {e}")


def main():
    tokens = _live_tokens()
    if not tokens:
        log("  ⚠️ [VOL-DRIFT] no live tokens found — skipping")
        return

    regimes = {}
    extreme_n = 0
    maxx_n = 0
    classified = 0
    for tok in tokens:
        try:
            atr = get_atr_pct(tok)
        except Exception:
            atr = None
        if atr is None:
            continue
        classified += 1
        reg = classify_volatility(atr)
        regimes[reg] = regimes.get(reg, 0) + 1
        if reg == 'EXTREME':
            extreme_n += 1
        if is_maxxed(atr):
            maxx_n += 1

    if classified == 0:
        log("  ⚠️ [VOL-DRIFT] zero tokens classified — skipping")
        return

    extreme_share = 100.0 * extreme_n / classified
    maxx_share = 100.0 * maxx_n / classified

    history = _load_history()
    history.append({
        'ts': datetime.now(timezone.utc).isoformat(),
        'n': classified,
        'extreme_share': round(extreme_share, 2),
        'maxx_share': round(maxx_share, 2),
        'regimes': regimes,
    })
    _save_history(history)

    dist = ' '.join(f"{k}={v}" for k, v in sorted(regimes.items()))
    log(f"  📊 [VOL-DRIFT] n={classified} EXTREME={extreme_share:.1f}% MAXXED={maxx_share:.1f}% | {dist}")

    # Bootstrap: collect only, no alerting
    if len(history) < BOOTSTRAP_READINGS:
        log(f"  ℹ️ [VOL-DRIFT] bootstrap {len(history)}/{BOOTSTRAP_READINGS} — collecting, no band yet")
        return

    # Trailing band on EXTREME share
    trailing = sorted(h['extreme_share'] for h in history[-BOOTSTRAP_READINGS:])
    p10_val = _percentile(trailing, P10)
    p90_val = _percentile(trailing, P90)
    median_val = _percentile(trailing, 50)

    in_band = p10_val <= extreme_share <= p90_val
    log(f"  📏 [VOL-DRIFT] band p10={p10_val:.1f}% median={median_val:.1f}% p90={p90_val:.1f}% → "
        f"{'IN BAND' if in_band else '⚠️ OUT OF BAND'}")

    if not in_band:
        direction = 'HIGH' if extreme_share > p90_val else 'LOW'
        msg = (f"VOL-DRIFT {direction}: EXTREME share {extreme_share:.1f}% outside "
               f"historical band [{p10_val:.1f}%, {p90_val:.1f}%] over {BOOTSTRAP_READINGS}h")
        log(f"  🚨 [VOL-DRIFT] {msg}")
        _write_alert('WARN', msg, {
            'extreme_share': round(extreme_share, 2),
            'maxx_share': round(maxx_share, 2),
            'band_p10': round(p10_val, 2),
            'band_median': round(median_val, 2),
            'band_p90': round(p90_val, 2),
            'n_classified': classified,
            'regimes': regimes,
        })


if __name__ == '__main__':
    main()
