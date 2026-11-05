#!/usr/bin/env python3
"""
linreg_fade.py — RenTech-style univariate regression fade on 1m candles.

THESIS (Nick Patterson, Renaissance Technologies): "our most important
statistical tool was simple regression with one target and one independent
variable... nobody tells you what the variables you should be regressing.
What's the target? Should you do a nonlinear transform before you regress?
Should you clean your data? Do you notice when your results are obviously
rubbish?"

This signal is built exactly that way (research: scripts/analysis/
linreg_forecast_research.py + linreg_fade_backtest.py, results in
brain/linreg-fade-research.md):

  TARGET    : 8h forward return (the horizon where the IC is stable).
  PREDICTOR : ONE variable — the 1m OLS slope (% of price per bar) over the
              last 20 bars, compared against the token's OWN trailing P10/P90
              of the previous 4320 slopes (3 days, no lookahead).
  TRANSFORM : nonlinear — we trade the DECILE EXTREMES, not the linear fit
              (decile shape showed the edge lives only in the tails).
  CLEANING  : closed candles only, positive prices, finite volume, minimum
              history, dead-token guard (volume must be live), winsorized
              thresholds come from the token's own history (no cross-token
              outliers).
  RUBBISH   : R²/RSI/BB/momentum stacking was tested and REJECTED — R² IC ~0,
              momentum flips sign IS->OOS. One variable, no decoration.

VALIDATION (event-level, entry at next bar open, 0.09% round-trip fees):
  1m (Oct-Nov 2026, user's trading TF): SHORT WR 54.7%, avg +0.217%/trade,
  n=6138, positive in IS, OOS, and both months, both slope windows tested.
  15m (Aug-Nov): SHORT positive in every down-regime month, LONG positive in
  up-regime months (see research doc). Selection alpha for the fade is stable
  +0.26%/trade vs blind-long in ALL four period slices.

EXIT: time-based 8h (production UNIVERSAL_MAX_HOLD_MINUTES=480 already hard-
closes every position at 8h). Stop-based and trailing exits DESTROY this
edge — tested V2 (ATR 1.5/2.25), V6 (2%/2%+trail), V7 (6%/trail): all lose
(WR 37-44% < breakeven). The decider branch for this source must disable the
trailing stop (explicit never-arming activation) and use a wide SL.

Signal type: linreg_fade_long / linreg_fade_short
Source:      linreg-fade+ / linreg-fade-
"""

import sys
import os
import sqlite3

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    LINREG_FADE_ENABLED,
    LINREG_FADE_PLUS_ENABLED,
    LINREG_FADE_MINUS_ENABLED,
    LINREG_FADE_COOLDOWN_HOURS,
    LINREG_FADE_SLOPE_WINDOW,
    LINREG_FADE_TRAIL_WIN,
    LINREG_FADE_PCT_LOW,
    LINREG_FADE_PCT_HIGH,
    LINREG_FADE_MIN_BARS,
    LINREG_FADE_MAX_AGE_MIN,
    LINREG_FADE_MIN_LIVE_BARS,
    LINREG_FADE_MIN_HIST_RATIO,
    LINREG_FADE_CONF_BASE,
    LINREG_FADE_CONF_FLOOR,
    LINREG_FADE_CONF_CAP,
    LINREG_FADE_CONF_EXTREME_BONUS_MAX,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'linreg_fade_long'
SIGNAL_TYPE_SHORT = 'linreg_fade_short'
SOURCE_LONG = 'linreg-fade+'
SOURCE_SHORT = 'linreg-fade-'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')


def _get_closes_volume(token, limit):
    """Last `limit` closed 1m candles. Returns (closes, volumes) oldest-first.

    DB hygiene: single connection, closed in finally, empty on any error.
    """
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute(
            "SELECT close, volume FROM candles_1m "
            "WHERE token = ? AND is_closed = 1 AND close > 0 "
            "ORDER BY ts DESC LIMIT ?",
            (token.upper(), limit))
        rows = cur.fetchall()
        if not rows:
            return [], []
        rows.reverse()
        closes = np.array([r[0] for r in rows], dtype=np.float64)
        vols = np.array([r[1] if r[1] is not None else 0.0 for r in rows],
                        dtype=np.float64)
        # cleaning: finite only
        bad = ~np.isfinite(closes) | ~np.isfinite(vols)
        if bad.any():
            closes = closes[~bad]
            vols = vols[~bad]
        return closes, vols
    except Exception as e:
        print(f'  [linreg_fade] WARN: candles read failed for {token}: {e}')
        return [], []
    finally:
        try:
            if 'cur' in dir() and cur is not None:
                cur.close()
        except Exception:
            pass
        if conn:
            conn.close()


def _rolling_slope_pct(closes, w):
    """OLS slope of closes over trailing window w, normalized as % of the
    window mean. Index i corresponds to the window ending at bar i+w-1.

    Vectorized (sliding windows) — 4360 closes x 177 tokens per scan must
    stay well under a second.
    """
    from numpy.lib.stride_tricks import sliding_window_view
    win = sliding_window_view(closes, w)
    x = np.arange(w, dtype=np.float64)
    dx = x - x.mean()
    denom = float((dx * dx).sum())
    if denom <= 0:
        return np.array([], dtype=np.float64)
    ym = win.mean(axis=1)
    slope = (win @ dx) / denom
    with np.errstate(divide='ignore', invalid='ignore'):
        pct = slope / ym * 100.0
    pct[~np.isfinite(pct)] = np.nan
    return pct


def detect(token, price):
    """Return {direction, confidence, slope_pct, p10, p90, price} or None.

    ONE predictor: slope_pct vs the token's own trailing P10/P90.
    No R² / RSI / BB stacking (research: those add nothing or flip sign).
    """
    w = LINREG_FADE_SLOPE_WINDOW
    # fetch enough for BOTH the trailing window and the MIN_BARS gate
    # (bug: fetching TRAIL+w+5=4345 while MIN_BARS=4400 self-filtered everything)
    need = max(LINREG_FADE_MIN_BARS, LINREG_FADE_TRAIL_WIN + w + 5)
    closes, vols = _get_closes_volume(token, need)
    if len(closes) < LINREG_FADE_MIN_BARS:
        return None

    # dead-token guard: most recent bars must actually trade (cleaning)
    recent_vol = vols[-w:]
    if int((recent_vol > 0).sum()) < LINREG_FADE_MIN_LIVE_BARS:
        return None

    slopes = _rolling_slope_pct(closes, w)
    if slopes.size < LINREG_FADE_TRAIL_WIN + 1:
        return None

    hist = slopes[:-1]                    # trailing only — NO lookahead
    hist = hist[np.isfinite(hist)]
    if len(hist) < LINREG_FADE_TRAIL_WIN * LINREG_FADE_MIN_HIST_RATIO:
        return None
    cur = slopes[-1]
    if not np.isfinite(cur):
        return None

    p10 = float(np.percentile(hist, LINREG_FADE_PCT_LOW))
    p90 = float(np.percentile(hist, LINREG_FADE_PCT_HIGH))

    if cur <= p10:
        direction = 'LONG'
        # extremeness: rank within [0, PCT_LOW] mapped to [0, 1]
        rank = float(np.searchsorted(np.sort(hist), cur)) / len(hist)
        frac = (LINREG_FADE_PCT_LOW / 100.0 - rank) / (LINREG_FADE_PCT_LOW / 100.0)
    elif cur >= p90:
        direction = 'SHORT'
        rank = float(np.searchsorted(np.sort(hist), cur)) / len(hist)
        frac = (rank - LINREG_FADE_PCT_HIGH / 100.0) / (
            1.0 - LINREG_FADE_PCT_HIGH / 100.0)
    else:
        return None

    bonus = max(0.0, min(1.0, frac)) * LINREG_FADE_CONF_EXTREME_BONUS_MAX
    confidence = min(LINREG_FADE_CONF_CAP,
                     max(LINREG_FADE_CONF_FLOOR, LINREG_FADE_CONF_BASE + bonus))

    return {
        'direction': direction,
        'confidence': round(float(confidence)),
        'slope_pct': float(cur),
        'p10': p10,
        'p90': p90,
        'price': float(closes[-1]) if price is None or price <= 0 else float(price),
    }


def scan_signals() -> int:
    if not LINREG_FADE_ENABLED:
        return 0

    from signal_schema import get_all_latest_prices
    prices = get_all_latest_prices()
    added = 0

    for token, data in prices.items():
        price = data.get('price')
        if not price or price <= 0:
            continue

        # Layer 1: staleness — 1m candles, per add-signal staleness rule
        if price_age_minutes(token) > LINREG_FADE_MAX_AGE_MIN:
            continue

        sig = detect(token, price)
        if sig is None:
            continue

        direction = sig['direction']

        # Layer 1: per-direction kill-switch
        if direction == 'LONG' and not LINREG_FADE_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not LINREG_FADE_MINUS_ENABLED:
            continue

        # Layer 1: blacklists
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        # Layer 1: cooldown (position runs ~8h, so >8h cooldown)
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
            value=sig['slope_pct'],
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='1m',
            z_score=None,
            z_score_tier=None,
        )
        if sid:
            added += 1
            set_cooldown(token, direction, hours=LINREG_FADE_COOLDOWN_HOURS)
            edge = sig['p10'] if direction == 'LONG' else sig['p90']
            print(f'  {direction:6s} {token.upper():8s} conf={sig["confidence"]}% '
                  f'slope={sig["slope_pct"]:+.5f}% thr={edge:+.5f}% '
                  f'price={sig["price"]:.6g} [{source}]')

    return added


def run():
    """Entry point for signals_runner. Reads candles.db + latest prices
    directly (needs prices for the add_signal price field)."""
    return scan_signals()


if __name__ == '__main__':
    n = run()
    print(f'[linreg_fade] Done. {n} signals emitted.')
