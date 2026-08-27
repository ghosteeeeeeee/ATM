#!/usr/bin/env python3
"""
volatility_gate — Surf the right waves with the right signals.

Thesis: Different signals work in different volatility regimes.
        Mean reversion works in FLAT (range-bound).
        Trend following works in NORMAL (steady waves).
        Breakout works in HIGH (big moves).
        Continuation works in EXTREME (ride the storm).

Classification (from 30d ATR distribution across 143 tokens):
  FLAT:    ATR% < 0.48  (P25)  → Mean reversion signals
  NORMAL:  ATR% 0.48-1.0 (P25-P75) → Trend following signals
  HIGH:    ATR% 1.0-1.5 (P75-P90) → Breakout signals
  EXTREME: ATR% > 1.5 (P90)  → Continuation signals (or skip)

Data: candles_1h from candles.db
"""

import sys, os
import re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from paths import HERMES_DATA
import sqlite3

# Signals that work in each regime (from 30d backtest, 861 trades)
# Source: correlated trade outcomes with volatility regime at entry time
# ONLY signals with positive PnL in that regime are included
# Updated: 2026-08-11 from 30d backtest
REGIME_SIGNALS = {
    'FLAT': {
        # Mean reversion works in range-bound markets
        'bb_bounce', 'bb_bounce+',
        'bb_bounce+,range_finder+',  # 60.4% WR all-time, star signal
        'trend_momentum_near_sma',
        'hzscore', 'range_finder',  # individual parts for single-source signals
        'accel-300', 'accel-300-',  # SHORT: catches slow grinds down in quiet markets
        'slow-grind-',  # slow grinding downtrend — ideal for low-volatility FLAT markets
        'hl_copy_trader',  # pro trader copy — works in all regimes
        'stop_hunt_reversal_long', 'stop_hunt_reversal_long+',  # stop hunt reversal
        'return_exhaustion_long',  # extreme negative return reversal
        'spike_exhaustion_short', 'spike_exhaustion_short-',  # spike fade SHORT
        'liq-hunt', 'liq-hunt+', 'liq-hunt-',  # liquidation cluster contrarian — structural, regime-agnostic
        'macd-div', 'macd-div+', 'macd-div-',  # MACD divergence — counter-trend, works in range-bound
        'confluence+', 'confluence-',  # meta-signal — persistence + compounding, regime-agnostic
    },
    'NORMAL': {
        # pump_catcher — momentum breakout (velocity + acceleration)
        'pump-catcher+', 'pump-catcher-',
        # Trend following + mean reversion in steady markets
        'bb_bounce', 'bb_bounce+',  # standalone parts — compound forms already below
        'bb_bounce+,range_finder+', 'bb_bounce+,hzscore+',
        'bb-bounce-short,hzscore-',  # 58.8% WR all-time
        'bb-bounce-short',  # standalone SHORT bounce signal
        'atr-spike+', 'atr-spike-',  # ATR compression spike
        'tl_break', 'tl_break_long', 'tl_break_short',  # trendline breaks
        'trend_momentum_near_sma',
        'hzscore', 'range_finder', 'range_breakout',  # individual parts
        'rs',  # support/resistance — structural
        'accel-300', 'accel-300-',  # SHORT: works in steady markets
        'range_breakout+', 'range_breakout_short',  # LONG/SHORT breakout
        'r2-trend-long', 'r2l',  # R² trend LONG (slow grinds)
        'r2-trend-short',  # R² downtrend SHORT detector
        'slow-grind-',  # slow grinding downtrend detector
        'wave_catcher', 'wave_catcher+', 'wave_catcher-',  # velocity spike detector
        'mover', 'mover+', 'mover-',  # momentum spike detector
        'ct-hot', 'ct-hot+', 'ct-hot-',  # coin_tracker_hot momentum
        'hl_copy_trader',  # pro trader copy — works in all regimes
        'continuation', 'continuation+',  # re-entry after close
        'stop_hunt_reversal_long', 'stop_hunt_reversal_long+',  # stop hunt reversal
        'return_exhaustion_long',  # extreme negative return reversal
        'spike_exhaustion_short', 'spike_exhaustion_short-',  # spike fade SHORT
        'liq-hunt', 'liq-hunt+', 'liq-hunt-',  # liquidation cluster contrarian — structural, regime-agnostic
        'macd-div', 'macd-div+', 'macd-div-',  # MACD divergence — trend exhaustion detector
        'confluence+', 'confluence-',  # meta-signal — persistence + compounding, regime-agnostic
    },
    'HIGH': {
        # Breakout works in big moves
        'pump-catcher+', 'pump-catcher-',  # momentum breakout — catches explosive moves
        'bb_bounce', 'bb_bounce+',  # standalone parts
        'bb_bounce+,range_finder+', 'bb_bounce+,hzscore+',
        'tl_break', 'tl_break_long', 'tl_break_short',  # trendline breaks
        'accel-300-vel',
        'continuation', 'continuation+',  # re-entry after close
        'hzscore', 'range_finder',  # individual parts
        'rs', 'rs-s', 'rs-r',  # support/resistance — structural
        'accel-300', 'accel-300-',  # SHORT: catches sharp reversals
        'range_breakout+', 'range_breakout_short',  # LONG/SHORT breakout
        'wave_catcher', 'wave_catcher+', 'wave_catcher-',  # catches velocity spikes in big moves
        'r2-trend-long', 'r2-trend-short',  # R² trend detectors
        'slow-grind-',  # slow grinding downtrend detector
        'mover', 'mover+', 'mover-',  # momentum spike detector
        'ct-hot', 'ct-hot+', 'ct-hot-',  # coin_tracker_hot momentum
        'hl_copy_trader',  # pro trader copy — works in all regimes
        'stop_hunt_reversal_long', 'stop_hunt_reversal_long+',  # stop hunt reversal
        'return_exhaustion_long',  # extreme negative return reversal
        'spike_exhaustion_short', 'spike_exhaustion_short-',  # spike fade SHORT
        'liq-hunt', 'liq-hunt+', 'liq-hunt-',  # liquidation cluster contrarian — structural, regime-agnostic
        'confluence+', 'confluence-',  # meta-signal — persistence + compounding, regime-agnostic
        'macd-div', 'macd-div+', 'macd-div-',  # MACD divergence — counter-trend
    },
    'EXTREME': {
        # Continuation works in storms
        'continuation+,hzscore+', 'hzscore+,mover+',
        'mover+', 'mover-',  # momentum spike detector
        'bb_bounce',
        'wave_catcher', 'wave_catcher+', 'wave_catcher-',  # catches violent spikes in extreme vol
        'ct-hot', 'ct-hot+', 'ct-hot-',  # coin_tracker_hot — EXTREME only (stormy)
        'hl_copy_trader',  # pro trader copy — works in all regimes
        'liq-hunt', 'liq-hunt+', 'liq-hunt-',  # liquidation cluster contrarian — structural, regime-agnostic
        'tl_break', 'tl_break_long', 'tl_break_short',  # trendline breaks — structural
        'confluence+', 'confluence-',  # meta-signal — persistence + compounding, regime-agnostic
        'macd-div', 'macd-div+', 'macd-div-',  # MACD divergence — counter-trend
        'pump-catcher+', 'pump-catcher-',  # momentum breakout — works in storms
        'atr-spike+', 'atr-spike-',  # ATR compression spike
        'rs',  # support/resistance — structural
    },
}


def get_atr_pct(token):
    """Get current ATR(14) as percentage of close price for a token."""
    conn = None
    try:
        conn = sqlite3.connect(f'{HERMES_DATA}/candles.db', timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT open, high, low, close
            FROM candles_1h
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC
            LIMIT 20
        """, (token.upper(),))
        rows = cur.fetchall()
        if len(rows) < 15:
            return None
    except Exception:
        return None
    finally:
        if conn:
            conn.close()

    # rows are newest-first, reverse for chronological
    candles = list(reversed(rows))

    # Compute true ranges
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i][1], candles[i][2], candles[i-1][3]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)

    if len(trs) < 14:
        return None

    atr14 = sum(trs[-14:]) / 14
    close = candles[-1][3]
    if close <= 0:
        return None

    return (atr14 / close) * 100


def classify_volatility(atr_pct):
    """Classify volatility regime from ATR% (as percentage, e.g. 0.5 = 0.5%)."""
    if atr_pct < 0.48:    # <0.48% — flat
        return 'FLAT'
    elif atr_pct < 1.0:   # 0.48-1.0% — normal
        return 'NORMAL'
    elif atr_pct < 1.5:   # 1.0-1.5% — high
        return 'HIGH'
    else:                  # >1.5% — extreme
        return 'EXTREME'


def should_trade(token, signal=None):
    """Main entry point: should we trade this token based on volatility + signal?
    Returns: ('TRADE', regime) or ('SKIP', reason)
    """
    atr_pct = get_atr_pct(token)
    if atr_pct is None:
        return ('SKIP', 'no_data')

    regime = classify_volatility(atr_pct)

    # If signal is provided, check if it works in this regime
    if signal:
        regime_sigs = REGIME_SIGNALS.get(regime, set())
        # Check full signal string first (e.g., 'bb_bounce+,hzscore+')
        if signal in regime_sigs:
            return ('TRADE', regime)
        # Check individual parts
        sig_parts = signal.split(',')
        works_in_regime = False
        for part in sig_parts:
            part = part.strip()
            if part in regime_sigs:
                works_in_regime = True
                break
            base = part.rstrip('+-')
            if base in regime_sigs:
                works_in_regime = True
                break
            # Strip trailing numbers (e.g., r2-trend-long0 → r2-trend-long)
            base_no_num = re.sub(r'\d+$', '', base)
            if base_no_num in regime_sigs:
                works_in_regime = True
                break

        if works_in_regime:
            return ('TRADE', regime)
        elif regime == 'EXTREME':
            return ('SKIP', f'storm: ATR={atr_pct:.4f}% > 1.5% (signal not suited)')
        else:
            return ('SKIP', f'{signal} not suited for {regime} (ATR={atr_pct:.4f}%)')

    # No signal-specific filter — use generic regime rules
    if regime == 'EXTREME':
        return ('SKIP', f'storm: ATR={atr_pct:.4f}% > 1.5%')

    return ('TRADE', regime)


def get_sl_multiplier(atr_pct):
    """Return SL multiplier based on volatility (percentage)."""
    if atr_pct < 0.48:
        return 0  # don't trade
    elif atr_pct < 0.8:
        return 1.0  # normal
    elif atr_pct < 1.0:
        return 1.2  # slightly wider
    elif atr_pct < 1.5:
        return 1.5  # wide
    else:
        return 0  # don't trade


def update_regime_performance(token, signal, direction, pnl_pct, atr_pct):
    """Track signal performance by regime for auto-learning.
    Called after each trade closes. Updates a local JSON file.
    """
    import json
    from datetime import datetime

    regime = classify_volatility(atr_pct)
    key = f'{signal}:{direction}'
    perf_file = f'{HERMES_DATA}/volatility_regime_perf.json'

    try:
        with open(perf_file) as f:
            perf = json.load(f)
    except Exception:
        perf = {}

    if key not in perf:
        perf[key] = {}
    if regime not in perf[key]:
        perf[key][regime] = {'wins': 0, 'losses': 0, 'pnl': 0}

    if pnl_pct > 0:
        perf[key][regime]['wins'] += 1
    else:
        perf[key][regime]['losses'] += 1
    perf[key][regime]['pnl'] += round(pnl_pct, 4)
    perf[key][regime]['updated'] = datetime.now().isoformat()

    try:
        with open(perf_file, 'w') as f:
            json.dump(perf, f, indent=2)
    except Exception:
        pass


if __name__ == '__main__':
    # Test on a few tokens
    test_tokens = ['BTC', 'ETH', 'SOL', 'ALGO', 'CC', 'AVNT']
    for tok in test_tokens:
        result = should_trade(tok)
        atr = get_atr_pct(tok)
        atr_str = f'{atr:.4f}%' if atr is not None else 'N/A'
        print(f'{tok}: ATR={atr_str} → {result}')
