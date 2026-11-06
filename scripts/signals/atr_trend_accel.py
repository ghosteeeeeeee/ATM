#!/usr/bin/env python3
"""
atr_trend_accel.py — ATR expansion marks trend ACCELERATION onset.

Thesis (CEO 2026-11-06; backtested 30d x 12 coins; audit #2 + own-conclusions
verified, no lookahead proven):

    ATR(14, 1m) crossing UP through the expansion threshold = the moment a
    lagging trend signal is freshest. Direction comes from the ESTABLISHED
    higher-TF trend (15m EMA20/50 AND 4h EMA20/50 must agree) — NOT from the
    1m MACD/RSI at the spike (that was refuted: coin flip, and entering at the
    cross loses the first 15-30 min).

Evidence (pooled 12-coin, 24h direction-aligned ev vs ATR-state baseline):
    +0.77% day-block CI [+0.15,+1.34], WR 58.8%, nulls p=0.003-0.015.
    NO edge before 4h — first-hour whipsaw applies (handled by exits/downstream).

Data: candles_1m (ATR cross + armed/decluster state), candles_15m + candles_4h
(completed bars only, EMA converged over TREND_BARS window).
Signal type: atr_trend_accel_long / atr_trend_accel_short
Source tags: atr-trend+ / atr-trend-
"""
import sys
import os
import time
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from signal_schema import add_signal, get_cooldown, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    ATR_TREND_ACCEL_ENABLED,
    ATR_TREND_ACCEL_PLUS_ENABLED,
    ATR_TREND_ACCEL_MINUS_ENABLED,
    ATR_TREND_ACCEL_ATR_PERIOD,
    ATR_TREND_ACCEL_ATR_PCT_THRESHOLD,
    ATR_TREND_ACCEL_HYSTERESIS,
    ATR_TREND_ACCEL_TREND_TF_1,
    ATR_TREND_ACCEL_TREND_TF_2,
    ATR_TREND_ACCEL_EMA_FAST,
    ATR_TREND_ACCEL_EMA_SLOW,
    ATR_TREND_ACCEL_MIN_BARS,
    ATR_TREND_ACCEL_TREND_BARS,
    ATR_TREND_ACCEL_TF1_MAX_AGE_MIN,
    ATR_TREND_ACCEL_TF2_MAX_AGE_MIN,
    ATR_TREND_ACCEL_BAR_MAX_AGE_MIN,
    ATR_TREND_ACCEL_FORMING_WINDOW_S,
    ATR_TREND_ACCEL_SCAN_BARS,
    ATR_TREND_ACCEL_COOLDOWN_HOURS,
    ATR_TREND_ACCEL_CONF_BASE,
    ATR_TREND_ACCEL_CONF_BONUS,
    ATR_TREND_ACCEL_CONF_BONUS_MULT,
    ATR_TREND_ACCEL_CONF_CAP,
    ATR_TREND_ACCEL_CONF_FLOOR,
    ATR_TREND_ACCEL_CROSS_LOOKBACK_MIN,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'atr_trend_accel_long'
SIGNAL_TYPE_SHORT = 'atr_trend_accel_short'
SOURCE_LONG = 'atr-trend+'
SOURCE_SHORT = 'atr-trend-'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')

_TF_SPEC = {
    '15m': (900, ATR_TREND_ACCEL_TF1_MAX_AGE_MIN),
    '1h': (3600, 120),
    '4h': (14400, ATR_TREND_ACCEL_TF2_MAX_AGE_MIN),
}


def _fetch_1m(token, limit):
    """Last `limit` 1m bars, oldest-first: (ts, high, low, close).

    Bind the token EXACTLY as it is stored in candles_1m first: the 1m writer
    keeps the Hyperliquid k-tokens with a lowercase 'k' (kBONK/kFLOKI/kLUNC/
    kNEIRO/kPEPE/kSHIB) while every other table uses the upper-case form, so a
    blind token.upper() returns 0 rows for them and the token is silently
    excluded (bug_hunter BUG-093). Upper-case is the fallback for callers that
    pass the normalised form."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        rows = conn.execute(
            "SELECT ts, high, low, close FROM candles_1m "
            "WHERE token = ? ORDER BY ts DESC LIMIT ?",
            (token, limit)).fetchall()
        if not rows:
            rows = conn.execute(
                "SELECT ts, high, low, close FROM candles_1m "
                "WHERE token = ? ORDER BY ts DESC LIMIT ?",
                (token.upper(), limit)).fetchall()
        return [tuple(r) for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _fetch_htf_closes(token, timeframe, limit):
    """Completed higher-TF closes, oldest-first: (ts, close). Completed =
    bar started far enough back that it must be finished by now."""
    iv, _max_age = _TF_SPEC[timeframe]
    now = int(time.time())
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        rows = conn.execute(
            f"SELECT ts, close FROM candles_{timeframe} "
            "WHERE token = ? AND ts <= ? ORDER BY ts DESC LIMIT ?",
            (token.upper(), now - iv, limit)).fetchall()
        return [(int(r[0]), float(r[1])) for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _atr_pct_series(rows, period):
    """Wilder/RMA ATR as % of close (matches backtest tv_atr / talib exactly).
    rows: (ts, high, low, close) oldest-first. Returns list aligned to rows."""
    n = len(rows)
    res = [None] * n
    if n < period + 1:
        return res
    trs = []
    for i in range(1, n):
        h, l, prev_c = rows[i][1], rows[i][2], rows[i - 1][3]
        trs.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
    atr = sum(trs[:period]) / period
    res[period] = atr
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
        res[i + 1] = atr
    # to percent of close
    out = [None] * n
    for i, a in enumerate(res):
        c = rows[i][3]
        if a is not None and c and c > 0:
            out[i] = a / c * 100.0
    return out


def _ema(vals, period):
    """EMA seeded with SMA(period) at index period-1 (backtest convention)."""
    k = 2.0 / (period + 1)
    if len(vals) < period:
        return None
    seed = sum(vals[:period]) / period
    prev = seed
    for v in vals[period:]:
        prev = v * k + prev * (1 - k)
    return prev


def _trend_direction(token):
    """Established trend: EMA_FAST vs EMA_SLOW on completed 15m AND 4h bars.
    Both TFs must agree. Returns +1 (LONG), -1 (SHORT), 0 (skip)."""
    now = int(time.time())
    dirs = []
    for tf, max_age_min in ((ATR_TREND_ACCEL_TREND_TF_1, ATR_TREND_ACCEL_TF1_MAX_AGE_MIN),
                            (ATR_TREND_ACCEL_TREND_TF_2, ATR_TREND_ACCEL_TF2_MAX_AGE_MIN)):
        bars = _fetch_htf_closes(token, tf, ATR_TREND_ACCEL_TREND_BARS)
        if len(bars) < ATR_TREND_ACCEL_MIN_BARS:
            return 0
        # freshness: newest completed bar must not be stale
        if (now - bars[-1][0]) / 60.0 > max_age_min:
            return 0
        closes = [b[1] for b in bars]
        fast = _ema(closes, ATR_TREND_ACCEL_EMA_FAST)
        slow = _ema(closes, ATR_TREND_ACCEL_EMA_SLOW)
        if fast is None or slow is None:
            return 0
        dirs.append(1 if fast > slow else -1)
    if dirs[0] == dirs[1]:
        return dirs[0]
    return 0


def _armed(atr_pct, cross_i, threshold):
    """Hysteresis decluster (matches audited backtest find_events): armed iff
    walking back from the bar BEFORE the cross, the first marker bar seen has
    ATR% < threshold*HYSTERESIS (re-arm) rather than >= threshold (still in
    an un-rearmed episode)."""
    rearm = threshold * ATR_TREND_ACCEL_HYSTERESIS
    for j in range(cross_i - 1, -1, -1):
        a = atr_pct[j]
        if a is None:
            continue
        if a < rearm:
            return True
        if a >= threshold:
            return False
    return False  # no re-arm seen in window — conservative


def detect(token):
    """Return {direction, confidence, value, price} or None."""
    rows = _fetch_1m(token, ATR_TREND_ACCEL_SCAN_BARS)
    if len(rows) < ATR_TREND_ACCEL_ATR_PERIOD + 2:
        return None

    now = int(time.time())
    last = len(rows) - 1
    if (now - rows[last][0]) / 60.0 > ATR_TREND_ACCEL_BAR_MAX_AGE_MIN:
        return None  # 1m feed stale for this token
    # The collector writes the in-progress minute — that bar's OHLC is partial
    # and must never be used, so step back to the last COMPLETED bar.
    if (now - rows[last][0]) < ATR_TREND_ACCEL_FORMING_WINDOW_S:
        last -= 1
    if last < ATR_TREND_ACCEL_ATR_PERIOD + 1:
        return None

    atr_pct = _atr_pct_series(rows, ATR_TREND_ACCEL_ATR_PERIOD)
    thr = ATR_TREND_ACCEL_ATR_PCT_THRESHOLD

    # A cross-up is a SINGLE-BAR event (a0 < thr <= a1 holds for exactly one
    # bar), and with the forming-minute step-back the newest completed bar is
    # only ever observable during the ~60s after it closes. Slow signals run
    # on a 300s cadence (run_pipeline STEPS_EVERY_5M), so evaluating only that
    # bar exposed each cross for one 1-minute window out of five and silently
    # dropped ~4 of every 5 audited events — measured 12-32% capture over 7d of
    # BTC crosses at every scan phase (bug_hunter BUG-091). Walk back over the
    # fetched window instead and take the MOST RECENT armed cross: the same
    # event set find_events() records, just observed up to CROSS_LOOKBACK_MIN
    # late. A lookback of 2 restores newest-completed-bar-only behaviour.
    cross_i = None
    a_cross = None
    # Never scan back less than two forming windows: the newest completed bar is
    # always 1-2 FORMING_WINDOW_S old, so this keeps it eligible even if
    # CROSS_LOOKBACK_MIN is mis-set to 0/1 (which would otherwise make detect()
    # return None for every token on every cycle — silent never-fire).
    lookback_min = max(ATR_TREND_ACCEL_CROSS_LOOKBACK_MIN,
                       2.0 * ATR_TREND_ACCEL_FORMING_WINDOW_S / 60.0)
    for i in range(last, ATR_TREND_ACCEL_ATR_PERIOD, -1):
        if (now - rows[i][0]) / 60.0 > lookback_min:
            break  # rows only get older going back — nothing further is eligible
        a0, a1 = atr_pct[i - 1], atr_pct[i]
        if a0 is None or a1 is None:
            continue
        if not (a0 < thr <= a1):
            continue  # no cross-up on this bar
        if not _armed(atr_pct, i, thr):
            continue  # still inside a previous expansion episode (decluster)
        cross_i, a_cross = i, a1
        break
    if cross_i is None:
        return None

    direction = _trend_direction(token)
    if direction == 0:
        # rare (one line per actual armed cross, not per token) — without it a
        # stale 15m/4h feed or unaligned trend is completely invisible in logs
        print(f"[atr_trend_accel] {token}: armed ATR cross at ts={rows[cross_i][0]} "
              f"but 15m/4h EMA trend not aligned (or HTF stale/insufficient) — skipped",
              flush=True)
        return None

    price = rows[cross_i][3]
    if not price or price <= 0:
        return None

    conf = ATR_TREND_ACCEL_CONF_BASE
    if a_cross >= thr * ATR_TREND_ACCEL_CONF_BONUS_MULT:
        conf += ATR_TREND_ACCEL_CONF_BONUS
    conf = max(ATR_TREND_ACCEL_CONF_FLOOR, min(ATR_TREND_ACCEL_CONF_CAP, conf))

    return {
        'direction': 'LONG' if direction == 1 else 'SHORT',
        'confidence': conf,
        'value': round(a_cross, 4),
        'price': price,
    }


def scan_signals():
    """Scan all recently-active tokens for the ATR↑ cross + trend alignment."""
    added = 0
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        cutoff = int(time.time()) - 600
        tokens = [r[0] for r in conn.execute(
            "SELECT DISTINCT token FROM candles_1m WHERE ts >= ?",
            (cutoff,)).fetchall()]
    except Exception as e:
        print(f"[atr_trend_accel] token scan failed: {e}", flush=True)
        return 0
    finally:
        if conn:
            conn.close()

    for token in tokens:
        if not ATR_TREND_ACCEL_ENABLED:
            return added
        # Whole per-token body is guarded: add_signal()/get_cooldown()/
        # set_cooldown() sit OUTSIDE detect()'s own try, so one bad token
        # (locked DB, PG hiccup, malformed row) must not abort the rest of the
        # scan (bug_hunter BUG-092).
        try:
            sig = detect(token)
            if not sig:
                continue

            direction = sig['direction']

            # Layer 1: per-direction kill-switch
            if direction == 'LONG' and not ATR_TREND_ACCEL_PLUS_ENABLED:
                continue
            if direction == 'SHORT' and not ATR_TREND_ACCEL_MINUS_ENABLED:
                continue

            # Layer 1: blacklists
            if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
                continue
            if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
                continue

            # Layer 1: cooldown (hysteresis is the primary decluster; this is a
            # per token+direction safety net — with the cross lookback the same
            # cross is visible to two consecutive scans, so this is also the
            # duplicate-fire guard)
            if get_cooldown(token, direction=direction):
                continue

            sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
            source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

            sid = add_signal(
                token=token.upper(),
                direction=direction,
                signal_type=sig_type,
                source=source,
                confidence=sig['confidence'],
                value=sig.get('value'),
                price=sig['price'],
                exchange='hyperliquid',
                timeframe='1m',
            )
            if sid:
                added += 1
                set_cooldown(token, direction,
                             hours=ATR_TREND_ACCEL_COOLDOWN_HOURS)
        except Exception as e:
            print(f"[atr_trend_accel] processing failed for {token}: {e}", flush=True)
            continue
    return added


def run():
    """Entry point for signals_runner (reads candles directly — no prices_dict)."""
    if not ATR_TREND_ACCEL_ENABLED:
        return 0
    return scan_signals()


if __name__ == '__main__':
    # dry run: report candidates without writing signals
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        cutoff = int(time.time()) - 600
        toks = [r[0] for r in conn.execute(
            "SELECT DISTINCT token FROM candles_1m WHERE ts >= ?",
            (cutoff,)).fetchall()]
    except Exception as e:
        # a missing/locked candles.db must not traceback + NameError on `toks`
        # (bug_hunter BUG-095)
        print(f'dry run: token scan failed: {e}')
        toks = []
    finally:
        if conn:
            conn.close()
    hits = 0
    for tk in toks:
        try:
            s = detect(tk)
        except Exception as e:
            print(f'{tk}: detect error {e}')
            continue
        if s:
            hits += 1
            print(f"DRY {tk}: {s['direction']} conf={s['confidence']} "
                  f"atr%={s['value']} price={s['price']}")
    print(f'dry run: {hits} candidate(s) of {len(toks)} tokens '
          f'(no signals written)')
