#!/usr/bin/env python3
"""
MTF-MACD Backtester v6 — 90%+ WR Optimization Sprint
====================================================
Expanded variable space + more tokens + smarter exit strategies.

NEW V6 VARIABLES (vs v5):
  - min_bullish_score: [2, 3]         entry quality filter
  - require_fresh_xover: [True, False] require FRESH crossover (age<=2)
  - entry_regime_filter: [True, False] require 4H regime = direction
  - macd_distance_min: [0.0, 0.05, 0.1, 0.2] MACD must be N% above signal
  - hist_rate_min: [0.0, 0.1, 0.2]    histogram momentum minimum
  - macd_zero_filter: [True, False]    MACD line must be above/below zero
  - exit_strategy: ['any_flip', '4h_regime', 'histogram_flip', 'both_4h1h']

NEW: Wider token scan (20 tokens) + extended candles (500 TFs)
NEW: Scoring optimized for WR% (90%+ WR target)

Usage:
  python3 mtf_macd_backtest.py --sweep --tokens BTC,ETH,SOL,XRP,LINK,AVAX,ATOM,ADA,DOT,DOGE,UNI,LTC,BCH,ARB,OP,NEAR,APT,VET,ALGO,ICP --workers 10
  python3 mtf_macd_backtest.py --token BTC --per-trade --entry-variant
  python3 mtf_macd_backtest.py --token SOL --exit-variant
"""

import os, sys, json, time, warnings, argparse
from datetime import datetime
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Optional, List, Dict, Any

warnings.filterwarnings('ignore')

ARCHIVE_DIR = Path('/root/.hermes/data/candles')
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

# ─── Default params ────────────────────────────────────────────────────────
HOLD_WINDOWS    = [60, 120, 240]  # 120m is optimal for SOL (87.7% WR)
THRESHOLDS      = [0.001, 0.002]
MIN_SIGNALS     = 20          # lowered for broader scan (was 30)
STRENGTH_FILTERS = [0.0]

# ─── V6 EXPANDED PARAM GRID ────────────────────────────────────────────────
PARAM_GRID = {
    'fast':   [6, 8, 12, 16, 20, 25],
    'slow':   [26, 34, 55, 65, 80],
    'signal': [7, 9, 12, 15, 20],
}

# NEW V6 entry filters
MIN_BULLISH_SCORE      = [2, 3]
REQUIRE_FRESH_XOVER    = [True, False]
ENTRY_REGIME_FILTER    = [True, False]
MACD_DISTANCE_MIN      = [0.0, 0.05, 0.1, 0.2]
HIST_RATE_MIN          = [0.0, 0.1, 0.2]
MACD_ZERO_FILTER       = [True, False]

# Exit strategies
EXIT_STRATEGIES = [
    'any_flip',      # original: exit on any TF flip
    '4h_regime',     # exit only on 4H regime flip
    'histogram_flip',# exit when histogram crosses zero
    'both_4h1h',     # exit when BOTH 4H and 1H flip
]

_token_cache = {}

# ─── Archive ────────────────────────────────────────────────────────────────

def load_archive(token, interval):
    path = ARCHIVE_DIR / f"{token}_{interval}.json"
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_archive(token, interval, candles):
    with open(ARCHIVE_DIR / f"{token}_{interval}.json", 'w') as f:
        json.dump(candles, f)

# ─── Data ───────────────────────────────────────────────────────────────────

def fetch_candles(token, interval, limit=500):
    import requests
    cached = load_archive(token, interval)
    if cached and len(cached) >= limit * 0.9:
        return cached
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={token}USDT&interval={interval}&limit={limit}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        klines = resp.json()
        if len(klines) < 30:
            return None
        candles = [{'O': float(k[1]), 'H': float(k[2]),
                    'L': float(k[3]), 'C': float(k[4]),
                    'V': float(k[5]), 'T': int(k[0])} for k in klines]
        save_archive(token, interval, candles)
        return candles
    except Exception:
        return None

def get_token_data(token):
    global _token_cache
    if token in _token_cache:
        return _token_cache[token]
    tfs = {}
    for tf in ['4h', '1h', '15m']:
        c = fetch_candles(token, tf, limit=500)
        if c:
            tfs[tf] = c
    result = {'4h': tfs.get('4h', []), '1h': tfs.get('1h', []), '15m': tfs.get('15m', [])}
    _token_cache[token] = result
    return result

# ─── MACD Math ───────────────────────────────────────────────────────────────

def ema(data, period):
    if len(data) < period:
        return []
    m = 2.0 / (period + 1)
    e = sum(data[:period]) / period
    out = [e]
    for v in data[period:]:
        e = (v - e) * m + e
        out.append(e)
    return out

def compute_macd_state(candles, fast, slow, signal):
    """
    Returns dict with:
      regime: 'BULL'/'BEAR'/'NEUTRAL'
      macd_dir: 1 (above signal) / -1 (below signal) / 0 (near zero)
      hist_dir: 1 (positive) / -1 (negative) / 0 (near zero)
      hist_rate: histogram rate of change
      bullish_score: -3 to +3
      macd_line, signal_line, histogram values
      macd_distance_pct: macd line distance from signal as % of price
      crossover_age: candles since last crossover (0=just now, 1=1 candle ago, etc.)
    """
    closes = [c['C'] for c in candles]
    if len(closes) < slow + signal + 5:
        return None

    fast_series = ema(closes, fast)
    slow_series = ema(closes, slow)
    if len(fast_series) < slow:
        return None

    offset = slow - fast
    macd_line = []
    for i in range(len(slow_series)):
        fi = i + offset
        if fi < len(fast_series):
            macd_line.append(fast_series[i] - slow_series[i])

    if len(macd_line) < signal + 2:
        return None

    sig_series = ema(macd_line, signal)
    if len(sig_series) < 2:
        return None

    curr_macd = macd_line[-1]
    prev_macd = macd_line[-2]
    curr_sig  = sig_series[-1]
    prev_sig  = sig_series[-2]
    curr_hist = curr_macd - curr_sig
    prev_hist = prev_macd - prev_sig
    prev2_hist = macd_line[-3] - sig_series[-3] if len(macd_line) >= 3 else prev_hist

    # Regime
    regime = 'BULL' if curr_macd > 0 else ('BEAR' if curr_macd < 0 else 'NEUTRAL')

    # MACD direction vs signal
    if curr_macd > curr_sig:
        macd_dir = 1
    elif curr_macd < curr_sig:
        macd_dir = -1
    else:
        macd_dir = 0

    # Histogram direction
    if curr_hist > 0:
        hist_dir = 1
    elif curr_hist < 0:
        hist_dir = -1
    else:
        hist_dir = 0

    # Histogram rate
    if abs(prev_hist) > 1e-10:
        hist_rate = (curr_hist - prev_hist) / abs(prev_hist)
    else:
        hist_rate = 0.0

    # MACD distance from signal as % of price (momentum strength)
    price = closes[-1]
    macd_distance_pct = abs(curr_hist) / price if price > 0 else 0.0

    # Score
    score = 0
    if macd_dir == 1:   score += 1
    if hist_dir == 1:   score += 1
    if regime == 'BULL': score += 1
    if hist_rate > 0.1:  score += 1
    if macd_dir == -1:  score -= 1
    if hist_dir == -1:  score -= 1
    if regime == 'BEAR': score -= 1
    if hist_rate < -0.1: score -= 1

    bullish_score = max(-3, min(3, score))

    # Direction: 1=long setup, -1=short setup, 0=no setup
    direction = 0
    if regime == 'BULL' and macd_dir == 1 and hist_dir == 1 and bullish_score >= 2:
        direction = 1
    elif regime == 'BEAR' and macd_dir == -1 and hist_dir == -1 and bullish_score <= -2:
        direction = -1

    # Crossover age: count candles since macd crossed signal
    # sig_series is shorter than macd_line, so cap the loop
    crossover_age = 999
    macd_len = len(macd_line)
    sig_len = len(sig_series)
    for i in range(macd_len - 1, -1, -1):
        if i >= 1 and i - 1 < sig_len and i < sig_len:
            prev_m = macd_line[i-1] - sig_series[i-1]
            curr_m = macd_line[i] - sig_series[i]
            if prev_m <= 0 < curr_m or prev_m >= 0 > curr_m:
                crossover_age = macd_len - 1 - i
                break

    return {
        'regime': regime,
        'macd_dir': macd_dir,
        'hist_dir': hist_dir,
        'hist_rate': hist_rate,
        'bullish_score': bullish_score,
        'direction': direction,
        'macd_line': curr_macd,
        'signal_line': curr_sig,
        'histogram': curr_hist,
        'macd_distance_pct': macd_distance_pct,
        'crossover_age': crossover_age,
        'prev_histogram': prev_hist,
        'prev2_histogram': prev2_hist,
    }

def tf_direction(tf_candles, fast, slow, signal):
    state = compute_macd_state(tf_candles, fast, slow, signal)
    return state['direction'] if state else 0

def get_tf_macd_state(tf_candles, fast, slow, signal):
    state = compute_macd_state(tf_candles, fast, slow, signal)
    if state is None:
        return None
    return {
        'macd_above_signal': state['macd_dir'] == 1,
        'histogram_positive': state['hist_dir'] == 1,
        'regime': state['regime'],
        'macd_distance_pct': state['macd_distance_pct'],
        'crossover_age': state['crossover_age'],
        'hist_rate': state['hist_rate'],
        'bullish_score': state['bullish_score'],
        'macd_line': state['macd_line'],
        'signal_line': state['signal_line'],
        'histogram': state['histogram'],
        'prev_histogram': state['prev_histogram'],
    }

# ─── Entry Quality Checks (V6 new) ─────────────────────────────────────────

def passes_entry_filters(tf_states, params, filters):
    """
    Check all entry quality filters.
    tf_states: {tf: get_tf_macd_state() result}
    params: {fast, slow, signal}
    filters: {min_bullish_score, require_fresh_xover, entry_regime_filter,
              macd_distance_min, hist_rate_min, macd_zero_filter}
    Returns (bool, reason_str)
    """
    # Get 4H state for regime filter
    s4h = tf_states.get('4h')
    s1h = tf_states.get('1h')
    s15m = tf_states.get('15m')
    if not all([s4h, s1h, s15m]):
        return False, "missing_tf_state"

    direction = 1 if (s15m['macd_above_signal'] and s15m['histogram_positive']) else -1
    is_bull = direction == 1

    # 1. Regime filter: 4H regime must match direction
    if filters.get('entry_regime_filter', False):
        if is_bull and s4h['regime'] != 'BULL':
            return False, "regime_mismatch"
        if not is_bull and s4h['regime'] != 'BEAR':
            return False, "regime_mismatch"

    # 2. Fresh crossover filter: all TFs must have FRESH crossover (age <= 2)
    if filters.get('require_fresh_xover', False):
        for tf_name, s in [('4h', s4h), ('1h', s1h), ('15m', s15m)]:
            if s['crossover_age'] > 2:
                return False, f"{tf_name}_xover_stale"

    # 3. MACD distance filter: MACD line must be N% above signal
    dist_min = filters.get('macd_distance_min', 0.0)
    if dist_min > 0:
        for tf_name, s in [('4h', s4h), ('1h', s1h), ('15m', s15m)]:
            if s['macd_distance_pct'] < dist_min:
                return False, f"{tf_name}_dist_too_small"

    # 4. Histogram rate filter: all TFs must have hist_rate >= min
    hist_min = filters.get('hist_rate_min', 0.0)
    if hist_min > 0:
        for tf_name, s in [('4h', s4h), ('1h', s1h), ('15m', s15m)]:
            if s['hist_rate'] < hist_min:
                return False, f"{tf_name}_hist_rate_low"

    # 5. MACD zero filter: MACD line must be above zero (bull) or below (bear)
    if filters.get('macd_zero_filter', False):
        for tf_name, s in [('4h', s4h), ('1h', s1h), ('15m', s15m)]:
            if is_bull and s['macd_line'] <= 0:
                return False, f"{tf_name}_macd_below_zero"
            if not is_bull and s['macd_line'] >= 0:
                return False, f"{tf_name}_macd_above_zero"

    # 6. Min bullish score across TFs
    min_score = filters.get('min_bullish_score', 2)
    for tf_name, s in [('4h', s4h), ('1h', s1h), ('15m', s15m)]:
        score = s['bullish_score']
        if is_bull and score < min_score:
            return False, f"{tf_name}_score_low"
        if not is_bull and score > -min_score:
            return False, f"{tf_name}_score_low"

    return True, "pass"

# ─── Signal Generation ─────────────────────────────────────────────────────

TF_ORDER = ['15m', '1h', '4h']
TF_OFFSET = {'4h': 16, '1h': 4, '15m': 0}

def generate_signal_at_idx(idx, c15, tfs_data, params, filters, min_str, min_tf_agreement=3):
    """
    V6 signal generation with configurable entry filters.
    """
    fast = params['fast']
    slow = params['slow']
    signal = params['signal']
    tf_offset = {'4h': 16, '1h': 4, '15m': 0}

    dirs = {}
    tf_states = {}
    for tf in ['4h', '1h', '15m']:
        tf_candles = tfs_data.get(tf, [])
        off = tf_offset.get(tf, 0)
        snap_i = max(0, idx - off)
        if snap_i < 10 or snap_i >= len(tf_candles):
            return None
        state = compute_macd_state(tf_candles[:snap_i + 1], fast, slow, signal)
        if state is None:
            return None
        tf_states[tf] = get_tf_macd_state(tf_candles[:snap_i + 1], fast, slow, signal)
        dirs[tf] = state['direction']  # v5-compatible: requires bullish_score>=2 AND regime match

    if len(dirs) < 3:
        return None

    # Count TFs agreeing in each direction
    bullish_tfs = [tf for tf, d in dirs.items() if d == 1]
    bearish_tfs = [tf for tf, d in dirs.items() if d == -1]

    # Determine direction: need min_tf_agreement TFs in same direction
    common_dir = 0
    agreeing_tfs = []
    if len(bullish_tfs) >= min_tf_agreement:
        common_dir = 1
        agreeing_tfs = bullish_tfs
    elif len(bearish_tfs) >= min_tf_agreement:
        common_dir = -1
        agreeing_tfs = bearish_tfs

    if common_dir == 0:
        return None

    # Apply entry quality filters
    ok, reason = passes_entry_filters(tf_states, params, filters)
    if not ok:
        return None

    # Strength = fraction of TFs that agree
    strength = len(agreeing_tfs) / 3.0
    if min_str > 0 and strength < min_str:
        return None

    return {
        'direction': 'long' if common_dir == 1 else 'short',
        'strength': strength,
        'tf_dirs': dirs,
        'entry_price': c15[idx]['C'],
        'idx': idx,
        'timestamp': c15[idx]['T'],
        'filters': filters,
    }

# ─── Exit Strategies (V6 new) ───────────────────────────────────────────────

def check_exit_any_flip(c15, entry_idx, direction, params, tfs_data, max_candles):
    """Exit as soon as ANY TF flips direction (uses state['direction'], v5-compatible)."""
    entry_dirs = None
    for c in range(entry_idx, min(entry_idx + max_candles, len(c15))):
        dirs = {}
        for tf in ['4h', '1h', '15m']:
            tf_candles = tfs_data.get(tf, [])
            off = TF_OFFSET.get(tf, 0)
            snap_i = max(0, c - off)
            if snap_i < 10 or snap_i >= len(tf_candles):
                continue
            state = compute_macd_state(tf_candles[:snap_i + 1], params['fast'], params['slow'], params['signal'])
            if state is None:
                continue
            dirs[tf] = state['direction']

        if len(dirs) < 3:
            continue
        if entry_dirs is None:
            entry_dirs = dirs
            continue

        for tf, d in entry_dirs.items():
            if dirs.get(tf, d) != d:
                return c
    return None

def check_exit_4h_regime(c15, entry_idx, direction, params, tfs_data, max_candles):
    """Exit only on 4H regime flip."""
    entry_4h_state = None
    for c in range(entry_idx, min(entry_idx + max_candles, len(c15))):
        tf_candles = tfs_data.get('4h', [])
        snap_i = max(0, c - TF_OFFSET['4h'])
        if snap_i < 10 or snap_i >= len(tf_candles):
            continue
        state = compute_macd_state(tf_candles[:snap_i + 1], params['fast'], params['slow'], params['signal'])
        if state is None:
            continue

        curr_regime = state['regime']
        if entry_4h_state is None:
            entry_4h_state = curr_regime
            continue

        if curr_regime != entry_4h_state:
            return c
    return None

def check_exit_histogram_flip(c15, entry_idx, direction, params, tfs_data, max_candles):
    """Exit when 4H histogram crosses zero (sign change)."""
    entry_hist_sign = None
    for c in range(entry_idx, min(entry_idx + max_candles, len(c15))):
        tf_candles = tfs_data.get('4h', [])
        snap_i = max(0, c - TF_OFFSET['4h'])
        if snap_i < 10 or snap_i >= len(tf_candles):
            continue
        state = compute_macd_state(tf_candles[:snap_i + 1], params['fast'], params['slow'], params['signal'])
        if state is None:
            continue

        curr_sign = 1 if state['histogram'] > 0 else (-1 if state['histogram'] < 0 else 0)
        if entry_hist_sign is None:
            entry_hist_sign = curr_sign
            continue

        if curr_sign != entry_hist_sign and curr_sign != 0:
            return c
    return None

def check_exit_both_4h1h(c15, entry_idx, direction, params, tfs_data, max_candles):
    """Exit when BOTH 4H and 1H flip direction (using state['direction'])."""
    entry_4h_dir = entry_1h_dir = None
    for c in range(entry_idx, min(entry_idx + max_candles, len(c15))):
        dirs = {}
        for tf in ['4h', '1h']:
            tf_candles = tfs_data.get(tf, [])
            off = TF_OFFSET.get(tf, 0)
            snap_i = max(0, c - off)
            if snap_i < 10 or snap_i >= len(tf_candles):
                continue
            state = compute_macd_state(tf_candles[:snap_i + 1], params['fast'], params['slow'], params['signal'])
            if state is None:
                continue
            dirs[tf] = state['direction']

        if len(dirs) < 2:
            continue
        if entry_4h_dir is None:
            entry_4h_dir = dirs.get('4h')
            entry_1h_dir = dirs.get('1h')
            continue

        flipped_4h = dirs.get('4h', entry_4h_dir) != entry_4h_dir
        flipped_1h = dirs.get('1h', entry_1h_dir) != entry_1h_dir
        if flipped_4h and flipped_1h:
            return c
    return None

def check_exit(c15, entry_idx, direction, params, tfs_data, max_candles, strategy='any_flip'):
    if strategy == '4h_regime':
        return check_exit_4h_regime(c15, entry_idx, direction, params, tfs_data, max_candles)
    elif strategy == 'histogram_flip':
        return check_exit_histogram_flip(c15, entry_idx, direction, params, tfs_data, max_candles)
    elif strategy == 'both_4h1h':
        return check_exit_both_4h1h(c15, entry_idx, direction, params, tfs_data, max_candles)
    else:
        return check_exit_any_flip(c15, entry_idx, direction, params, tfs_data, max_candles)

# ─── Backtest ────────────────────────────────────────────────────────────────

def run_backtest(token, params, hold_mins, thresholds, filters,
                 min_strength=0.0, per_trade_out=None, min_tf_agreement=3,
                 exit_strategy='any_flip'):
    """
    V6 backtest with all new entry/exit filters.
    """
    tfs_data = get_token_data(token)
    c15 = tfs_data.get('15m', [])
    if len(c15) < 200:
        return None

    signals = []
    max_hold = max(hold_mins) // 15

    for i in range(30, len(c15) - max_hold - 10):
        sig = generate_signal_at_idx(i, c15, tfs_data, params, filters, min_strength, min_tf_agreement)
        if sig:
            sig['exit_strategy'] = exit_strategy
            signals.append(sig)

    n = len(signals)
    if n < 5:
        return None

    results = {
        'token': token, 'params': params, 'filters': filters,
        'min_strength': min_strength, 'n_signals': n,
        'min_tf_agreement': min_tf_agreement,
        'exit_strategy': exit_strategy,
        'combined': {},
    }

    for hold in hold_mins:
        hold_c = hold // 15
        for thresh in thresholds:
            wins = losses = 0
            win_pnl = loss_pnl = 0.0
            exit_reasons = {'timeout': 0, 'exit_signal': 0, '4h_regime': 0, 'hist_flip': 0, 'both_4h1h': 0}

            for sig in signals:
                entry_i = sig['idx']
                entry_p = sig['entry_price']
                direction = sig['direction']
                ts = sig['timestamp']

                exit_i = check_exit(c15, entry_i, direction, params, tfs_data, hold_c, exit_strategy)
                if exit_i is None:
                    exit_i = min(entry_i + hold_c, len(c15) - 1)
                    exit_reason = 'timeout'
                else:
                    exit_reason = exit_strategy

                exit_p = c15[exit_i]['C']
                pnl = (exit_p - entry_p) / entry_p
                if direction == 'short':
                    pnl = -pnl

                if per_trade_out is not None:
                    per_trade_out.append({
                        'token': token,
                        'direction': direction,
                        'entry_p': entry_p,
                        'exit_p': exit_p,
                        'pnl_pct': pnl * 100,
                        'exit_reason': exit_reason,
                        'hold_min': (exit_i - entry_i) * 15 / 60,
                        'timestamp': ts,
                        'params': params,
                        'filters': filters,
                    })

                if pnl >= thresh:
                    wins += 1
                    win_pnl += pnl
                else:
                    losses += 1
                    loss_pnl += abs(pnl)

                exit_reasons[exit_reason] = exit_reasons.get(exit_reason, 0) + 1

            total = wins + losses
            wr = wins / total * 100 if total else 0
            avg_win = win_pnl / wins if wins else 0
            avg_loss = loss_pnl / losses if losses else 0
            pf = avg_win / avg_loss if avg_loss > 0 else float('inf')
            total_pnl = (win_pnl - loss_pnl) * 100

            key = f"{hold}m_{int(thresh*1000)}"
            results['combined'][key] = {
                'hold': hold, 'thresh': thresh, 'signals': total,
                'wins': wins, 'losses': losses, 'win_rate': wr,
                'avg_win_pct': avg_win * 100, 'avg_loss_pct': avg_loss * 100,
                'profit_factor': pf, 'total_pnl_pct': total_pnl,
                'exit_reasons': exit_reasons,
            }

    return results

# ─── Sweep ─────────────────────────────────────────────────────────────────

def build_filter_grid():
    """Build all filter combinations for V6."""
    from itertools import product
    combos = []
    for min_bs in MIN_BULLISH_SCORE:
        for fresh in REQUIRE_FRESH_XOVER:
            for regime_f in ENTRY_REGIME_FILTER:
                for dist in MACD_DISTANCE_MIN:
                    for hist_r in HIST_RATE_MIN:
                        for zero_f in MACD_ZERO_FILTER:
                            f = {
                                'min_bullish_score': min_bs,
                                'require_fresh_xover': fresh,
                                'entry_regime_filter': regime_f,
                                'macd_distance_min': dist,
                                'hist_rate_min': hist_r,
                                'macd_zero_filter': zero_f,
                            }
                            combos.append(f)
    return combos

FILTER_GRID = build_filter_grid()

def sweep_worker(args):
    token, fast, slow, signal, filters, exit_strategy = args
    params = {'fast': fast, 'slow': slow, 'signal': signal}
    best = None
    best_score = -999
    for min_str in STRENGTH_FILTERS:
        res = run_backtest(token, params, HOLD_WINDOWS, THRESHOLDS, filters,
                          min_str, min_tf_agreement=3, exit_strategy=exit_strategy)
        if res and res.get('n_signals', 0) >= MIN_SIGNALS:
            for key, v in res.get('combined', {}).items():
                if v['signals'] < MIN_SIGNALS:
                    continue
                # Score: heavily weight WR, then PF, then PnL
                score = v['win_rate'] * 5.0 + min(v['profit_factor'], 5) * 20 + v['total_pnl_pct'] * 2.0
                if v['win_rate'] >= 90:  score += 200
                elif v['win_rate'] >= 80: score += 100
                elif v['win_rate'] >= 70: score += 40
                if score > best_score:
                    best_score = score
                    best = {
                        'result': res, 'score': score, 'filters': filters,
                        'exit_strategy': exit_strategy,
                    }
    return best

def run_sweep(token, n_workers=4, exit_strategies=None):
    if exit_strategies is None:
        exit_strategies = EXIT_STRATEGIES
    print(f"[*] Sweep for {token} ({len(FILTER_GRID)} filter combos × {len(EXIT_STRATEGIES)} exit strategies)")
    tasks = []
    for fast in PARAM_GRID['fast']:
        for slow in PARAM_GRID['slow']:
            if slow <= fast:
                continue
            for signal in PARAM_GRID['signal']:
                for filters in FILTER_GRID:
                    for exit_str in exit_strategies:
                        tasks.append((token, fast, slow, signal, filters, exit_str))

    print(f"  Total combos: {len(tasks)}")
    results = []
    with ProcessPoolExecutor(max_workers=n_workers) as exe:
        futures = {exe.submit(sweep_worker, t): t for t in tasks}
        done = 0
        for fut in as_completed(futures):
            done += 1
            if done % 50 == 0:
                print(f"  [{token}] {done}/{len(tasks)}")
            try:
                r = fut.result(timeout=120)
                if r and r.get('score', 0) > 0:
                    results.append(r)
            except Exception:
                pass

    print(f"  [{token}] {len(results)} valid results")
    return results

# ─── Analysis ───────────────────────────────────────────────────────────────

def analyze(all_results, top_n=30):
    scored = []
    for r in all_results:
        res = r['result']
        for key, v in res.get('combined', {}).items():
            if v['signals'] < MIN_SIGNALS:
                continue
            score = 0
            score += v['win_rate'] * 5.0
            score += min(v['profit_factor'], 5) * 20
            score += v['total_pnl_pct'] * 2.0
            if v['win_rate'] >= 90:   score += 200
            elif v['win_rate'] >= 80: score += 100
            elif v['win_rate'] >= 70: score += 40
            elif v['win_rate'] >= 60: score += 15

            scored.append({
                'token': res['token'],
                'params': res['params'],
                'filters': res['filters'],
                'exit_strategy': res['exit_strategy'],
                'hold': v['hold'],
                'thresh': v['thresh'],
                'signals': v['signals'],
                'win_rate': v['win_rate'],
                'avg_win': v['avg_win_pct'],
                'avg_loss': v['avg_loss_pct'],
                'pf': v['profit_factor'],
                'total_pnl': v['total_pnl_pct'],
                'exit_reasons': v.get('exit_reasons', {}),
                'score': score,
            })

    scored.sort(key=lambda x: -x['score'])
    return scored[:top_n]

def print_leaderboard(scored):
    print(f"\n{'='*160}")
    print(f"MTF-MACD v6 LEADERBOARD — 90%+ WR OPTIMIZATION")
    print(f"{'='*160}")
    print(f"{'Rk':>3} {'Tok':>5} {'F':>3} {'Sl':>4} {'Sg':>3} {'Exit':>12} {'Hold':>5} {'Sigs':>5} {'WR%':>7} {'AvgWin':>8} {'AvgLoss':>9} {'PF':>6} {'PnL%':>8} {'Score':>8}")
    print(f"{' ':<79} {'min_bs':>7} {'fresh':>6} {'regime':>6} {'dist':>6} {'hist_r':>6} {'zero':>5}")
    print(f"{'-'*160}")
    for i, s in enumerate(scored, 1):
        f = s['filters']
        print(f"{i:>2}  {s['token']:>5} {s['params']['fast']:>3} {s['params']['slow']:>4} "
              f"{s['params']['signal']:>3} {s['exit_strategy']:>12} {s['hold']:>4}m "
              f"{s['signals']:>5} {s['win_rate']:>6.1f}% "
              f"{s['avg_win']:>+7.3f}% {s['avg_loss']:>+8.3f}% "
              f"{s['pf']:>5.2f} {s['total_pnl']:>+7.3f}% {s['score']:>7.1f}")
        print(f"  {' ':<75} bs={f['min_bullish_score']} fresh={f['require_fresh_xover']} regime={f['entry_regime_filter']} dist={f['macd_distance_min']} hist={f['hist_rate_min']} zero={f['macd_zero_filter']}")
    print(f"{'='*160}")

def print_per_trade_analysis(per_trades, token):
    if not per_trades:
        return
    losses = [t for t in per_trades if t['pnl_pct'] < 0]
    wins    = [t for t in per_trades if t['pnl_pct'] >= 0]
    total = len(per_trades)
    wr = len(wins) / total * 100 if total else 0

    print(f"\n{'='*80}")
    print(f"PER-TRADE DEEP DIVE — {token} ({total} trades, WR={wr:.1f}%)")
    print(f"{'='*80}")

    print(f"\n--- WORST 20 LOSSES ---")
    losses.sort(key=lambda x: x['pnl_pct'])
    print(f"{'#':>3} {'Dir':>5} {'PnL%':>8} {'Hold':>6} {'Exit':>15} {'Params'}")
    for i, t in enumerate(losses[:20], 1):
        p = t['params']
        ts_str = datetime.fromtimestamp(t['timestamp']/1000).strftime('%m-%d %H:%M') if t['timestamp'] else 'N/A'
        print(f"{i:>3} {t['direction']:>5} {t['pnl_pct']:>+7.3f}% {t['hold_min']:>5.1f}m {t['exit_reason']:>15} {p['fast']}/{p['slow']}/{p['signal']} {ts_str}")

    print(f"\n--- CLOSEST LOSSES (barely lost) ---")
    close_loss = [t for t in losses if t['pnl_pct'] > -0.3]
    close_loss.sort(key=lambda x: x['pnl_pct'], reverse=True)
    print(f"{'#':>3} {'Dir':>5} {'PnL%':>8} {'Hold':>6} {'Exit':>15} {'Params'}")
    for i, t in enumerate(close_loss[:10], 1):
        p = t['params']
        print(f"{i:>3} {t['direction']:>5} {t['pnl_pct']:>+7.3f}% {t['hold_min']:>5.1f}m {t['exit_reason']:>15} {p['fast']}/{p['slow']}/{p['signal']}")

    print(f"\n--- EXIT REASON STATS ---")
    from collections import Counter
    exit_counts = Counter(t['exit_reason'] for t in per_trades)
    for reason, cnt in exit_counts.most_common():
        r_wins = [t for t in per_trades if t['exit_reason'] == reason and t['pnl_pct'] >= 0]
        r_wr = len(r_wins) / cnt * 100 if cnt else 0
        r_pnl = sum(t['pnl_pct'] for t in per_trades if t['exit_reason'] == reason) / cnt
        print(f"  {reason:20s}: {cnt:3d} trades, WR={r_wr:.1f}%, avg_pnl={r_pnl:+.3f}%")

    print(f"\n--- HOLD DURATION STATS ---")
    for bucket in [(0, 20), (20, 40), (40, 60), (60, 999)]:
        bucket_trades = [t for t in per_trades if bucket[0] <= t['hold_min'] < bucket[1]]
        if not bucket_trades:
            continue
        w = [t for t in bucket_trades if t['pnl_pct'] >= 0]
        print(f"  {bucket[0]}-{bucket[1]}m: {len(bucket_trades):3d} trades, WR={len(w)/len(bucket_trades)*100:.1f}%, avg_pnl={sum(t['pnl_pct'] for t in bucket_trades)/len(bucket_trades):+.3f}%")

    print(f"\n--- DIRECTION STATS ---")
    for direction in ['long', 'short']:
        d_trades = [t for t in per_trades if t['direction'] == direction]
        if not d_trades:
            continue
        w = [t for t in d_trades if t['pnl_pct'] >= 0]
        print(f"  {direction:6s}: {len(d_trades):3d} trades, WR={len(w)/len(d_trades)*100:.1f}%, avg_pnl={sum(t['pnl_pct'] for t in d_trades)/len(d_trades):+.3f}%")

# ─── CLI ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', default='BTC')
    parser.add_argument('--tokens', default=None)
    parser.add_argument('--sweep', action='store_true')
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--per-trade', action='store_true')
    parser.add_argument('--exit-strategy', default='any_flip',
                        choices=EXIT_STRATEGIES)
    parser.add_argument('--min-tf-agreement', type=int, default=3)
    parser.add_argument('--top-tokens', action='store_true',
                        help='Run sweep on top 20 tokens by signal count')
    args = parser.parse_args()

    if args.top_tokens:
        tokens = ['BTC','ETH','SOL','XRP','LINK','AVAX','ATOM','ADA','DOT','DOGE',
                  'UNI','LTC','BCH','ARB','OP','NEAR','APT','VET','ALGO','ICP']
    elif args.tokens:
        tokens = [t.strip() for t in args.tokens.split(',')]
    else:
        tokens = [args.token]

    print(f"[*] MTF-MACD v6 — 90%+ WR Optimization Sprint")
    print(f"[*] Tokens: {tokens}")
    print(f"[*] Filter grid: {len(FILTER_GRID)} combos")
    print(f"[*] Exit strategies: {EXIT_STRATEGIES}")
    print(f"[*] Hold windows: {HOLD_WINDOWS} min")
    print()

    all_results = []

    if args.per_trade:
        # Per-token analysis with best-known params + entry variants
        best_params = {
            'BTC': {'fast': 20, 'slow': 65, 'signal': 7},
            'SOL': {'fast': 12, 'slow': 55, 'signal': 15},
            'ETH': {'fast': 16, 'slow': 55, 'signal': 9},
        }
        per_trade_all = []
        for token in tokens:
            p = best_params.get(token, {'fast': 12, 'slow': 55, 'signal': 12})
            params = {**p, 'timeframes': ['4h', '1h', '15m']}
            filters = {
                'min_bullish_score': 3,
                'require_fresh_xover': True,
                'entry_regime_filter': True,
                'macd_distance_min': 0.1,
                'hist_rate_min': 0.1,
                'macd_zero_filter': True,
            }
            per_trades = []
            res = run_backtest(token, params, HOLD_WINDOWS, THRESHOLDS, filters,
                              min_strength=0.0, per_trade_out=per_trades,
                              min_tf_agreement=3, exit_strategy=args.exit_strategy)
            if res:
                all_results.append(res)
                per_trade_all.extend(per_trades)

        if per_trade_all:
            for token in tokens:
                token_trades = [t for t in per_trade_all if t['token'] == token]
                if token_trades:
                    print_per_trade_analysis(token_trades, token)
        return

    if args.sweep:
        for token in tokens:
            results = run_sweep(token, n_workers=args.workers)
            all_results.extend(results)
    else:
        # Single run with defaults
        params = {'fast': 12, 'slow': 55, 'signal': 15}
        filters = {
            'min_bullish_score': 2,
            'require_fresh_xover': False,
            'entry_regime_filter': False,
            'macd_distance_min': 0.0,
            'hist_rate_min': 0.0,
            'macd_zero_filter': False,
        }
        for token in tokens:
            res = run_backtest(token, params, HOLD_WINDOWS, THRESHOLDS, filters,
                               min_tf_agreement=3, exit_strategy=args.exit_strategy)
            if res:
                all_results.append(res)

    if not all_results:
        print("[!] No results.")
        return

    leaderboard = analyze(all_results)
    print_leaderboard(leaderboard)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = f"/root/.hermes/data/backtest_v6_{ts}.json"
    with open(path, 'w') as f:
        json.dump({'leaderboard': leaderboard,
                   'filter_grid_size': len(FILTER_GRID),
                   'exit_strategies': EXIT_STRATEGIES,
                   'params': {
                       'hold_windows': HOLD_WINDOWS,
                       'thresholds': THRESHOLDS,
                       'min_tf_agreement': 3,
                   }}, f, indent=2, default=str)
    print(f"\n[*] Saved to {path}")

if __name__ == '__main__':
    main()
