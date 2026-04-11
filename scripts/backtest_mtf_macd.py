#!/usr/bin/env python3
"""
backtest_mtf_macd.py — Historical signal logic backtest for MTF-MACD.
O(n) batch precomputation + O(1) entry/exit lookups.

Data sources (HYBRID):
  - 1h, 4h  → local candles.db (already populated)
  - 15m     → Binance paginated fetch (90 days, backward pagination)

Entry logic mirrors signal_gen.py _run_mtf_macd_signals():
  - LONG:  15m macd_above_signal=True AND histogram_positive=True
           AND at least one of (1h,4h) also bull
           AND 4h regime = BULL
  - SHORT: mirror
  - BLOCKED if 4H or 1H crossover DIRECTLY opposes 15m direction

Exit logic: 15m flips bear/bull OR 4h regime flips OR histogram fading fast
"""

import sys, json, time, statistics, requests
from datetime import datetime
from typing import Optional

# ── Default tokens ────────────────────────────────────────────────────────────
DEFAULT_TOKENS = ['BTC', 'ETH']
PARAMS = {
    'macd_fast':   12,
    'macd_slow':   26,
    'macd_signal':  9,
    'crossover_fresh_max': 2,
    'regime_threshold':     0.0001,
    'hist_rate_floor':     -0.15,   # histogram rate threshold for LONG entry
    'hist_rate_ceil':       0.15,   # histogram rate threshold for SHORT entry
    'require_15m_xover':   True,    # require 15m crossover trigger
    'step':               4,       # check entry every N 15m candles (1h = step 4)
}

# ═══════════════════════════════════════════════════════════════════════════════
# DATA FETCHING
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_binance_backward(token: str, interval: str = '15m',
                           days: int = 90, limit: int = 1000,
                           sleep: float = 0.08) -> list:
    """
    Fetch `days` of Binance candles using BACKWARD pagination.
    Binance always returns most recent candles first.
    We walk backward from now to build up historical data.

    Returns: list of candles, sorted oldest→newest.
    """
    now_ms = int(time.time() * 1000)
    all_candles = []
    current_end = now_ms

    while True:
        url = (f"https://api.binance.com/api/v3/klines"
               f"?symbol={token}USDT&interval={interval}"
               f"&endTime={current_end}&limit={limit}")
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 429:
                time.sleep(3.0)
                continue
            resp.raise_for_status()
            batch = resp.json()
        except Exception as e:
            print(f"  [WARN] {token}/{interval} fetch: {e}")
            break

        if not batch:
            break

        for k in batch:
            all_candles.append({
                'open_time':  k[0],
                'open':       float(k[1]),
                'high':       float(k[2]),
                'low':        float(k[3]),
                'close':      float(k[4]),
                'volume':     float(k[5]),
                'close_time': k[6],
                'ts':         k[0] // 1000,
            })

        first_ts = batch[0][0]
        oldest_allowed_ms = now_ms - days * 86400 * 1000
        if first_ts <= oldest_allowed_ms:
            break
        if len(batch) < limit:
            break

        current_end = first_ts - 1  # walk backward
        time.sleep(sleep)

    # Deduplicate and sort oldest→newest
    seen = set()
    unique = []
    for c in all_candles:
        if c['open_time'] not in seen:
            seen.add(c['open_time'])
            unique.append(c)
    unique.sort(key=lambda x: x['open_time'])
    return unique


def load_local_candles(token: str, tf: str) -> list:
    """Load 1h or 4h candles from local candles.db."""
    table = {'1h': 'candles_1h', '4h': 'candles_4h'}.get(tf)
    if not table:
        return []
    import sqlite3
    conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=10)
    cur = conn.cursor()
    cur.execute(f"SELECT ts, open, high, low, close, volume FROM {table} "
                f"WHERE token = ? ORDER BY ts ASC", (token,))
    rows = cur.fetchall()
    conn.close()
    return [{'ts': r[0], 'open': r[1], 'high': r[2],
             'low': r[3], 'close': r[4], 'volume': r[5]} for r in rows]


def fetch_token_candles(token: str, days: int = 90, sleep: float = 0.05) -> tuple:
    """
    Fetch all 3 TFs for a token from Binance (paginated).
    Returns (c15, c1h, c4h) — all sorted oldest→newest.
    Uses backward pagination for full history.
    """
    c15  = fetch_binance_backward(token, '15m', days=days, sleep=sleep)
    c1h  = fetch_binance_backward(token, '1h',  days=days, sleep=sleep)
    c4h  = fetch_binance_backward(token, '4h',  days=days, sleep=sleep)
    return c15, c1h, c4h


# ═══════════════════════════════════════════════════════════════════════════════
# INCREMENTAL MACD COMPUTATION — O(n) single pass
# ═══════════════════════════════════════════════════════════════════════════════

class IncrementalMACD:
    """
    Compute MACD(12,26,9) for a price series in a single O(n) pass.
    Call add_price() for each new candle close, then:
      - macd_line     = current MACD line value
      - signal_line   = current signal line value
      - histogram     = MACD - signal
      - macd_above    = macd_line > signal_line
      - hist_positive  = histogram > 0

    For crossover detection, call crossover_age() to scan backward.
    """
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast   = fast
        self.slow   = slow
        self.signal = signal
        self.ema12   = None
        self.ema26   = None
        self.sig    = None   # signal line EMA
        self.n      = 0      # number of prices processed

        self.macd_series  = []
        self.signal_series = []
        self.hist_series  = []

    def add_price(self, price: float) -> dict:
        """
        Update MACD with a new closing price.
        Returns current state dict.
        """
        f, s, sig = self.fast, self.slow, self.signal
        self.n += 1

        # EMA12
        if self.ema12 is None:
            self.ema12 = price
        else:
            k = 2 / (f + 1)
            self.ema12 = price * k + self.ema12 * (1 - k)

        # EMA26
        if self.ema26 is None:
            self.ema26 = price
        else:
            k = 2 / (s + 1)
            self.ema26 = price * k + self.ema26 * (1 - k)

        macd_line = self.ema12 - self.ema26
        self.macd_series.append(macd_line)

        # Signal line EMA9 — needs at least 9 MACD values
        if len(self.macd_series) < sig:
            self.signal_series.append(None)
            self.hist_series.append(None)
            return self._state(macd_line, None, None)
        elif self.sig is None:
            # Initialize signal with SMA of first 9 MACD values
            self.sig = sum(self.macd_series[-sig:]) / sig
            self.signal_series.append(self.sig)
        else:
            k = 2 / (sig + 1)
            self.sig = macd_line * k + self.sig * (1 - k)
            self.signal_series.append(self.sig)

        hist = macd_line - self.sig
        self.hist_series.append(hist)
        return self._state(macd_line, self.sig, hist)

    def _state(self, macd_line, signal_line, hist) -> dict:
        return {
            'macd_line':  macd_line,
            'signal_line': signal_line,
            'histogram':  hist,
            'macd_above':  macd_line > signal_line if signal_line else False,
            'hist_positive': hist > 0 if hist else False,
        }

    def current(self) -> dict:
        """Return current MACD state."""
        if not self.macd_series:
            return self._state(None, None, None)
        return self._state(self.macd_series[-1],
                          self.signal_series[-1] if self.signal_series else None,
                          self.hist_series[-1] if self.hist_series else None)

    def crossover_age(self) -> tuple:
        """
        Scan backward through stored series to find last crossover.
        Returns (age: int, direction: 'cross_over'|'cross_under'|'none')
        """
        n = len(self.macd_series)
        if n < 12:  # need enough for signal EMA + some history
            return 0, 'none'

        for i in range(2, min(n - 9, 30)):  # scan up to 30 candles back
            prev = n - i - 1
            curr = n - i
            pm, cm = self.macd_series[prev], self.macd_series[curr]
            ps = self.signal_series[prev] if self.signal_series and self.signal_series[prev] is not None else pm
            cs = self.signal_series[curr] if self.signal_series and self.signal_series[curr] is not None else cm

            if ps is None or cs is None:
                break
            if pm > ps and cm < cs:
                return i, 'cross_under'
            elif pm < ps and cm > cs:
                return i, 'cross_over'
        return 0, 'none'


class MultiTimeFrameMACD:
    """
    Precompute MACD states for all 3 TFs for the full price series.
    Walks the master timeline (15m candles) and updates each TF's
    IncrementalMACD each time we pass a new candle boundary.

    At each master index i, gives you the MACD state for 15m, 1h, 4h
    as of that point in time.
    """
    def __init__(self, candles_15m: list, candles_1h: list, candles_4h: list,
                 params: dict):
        self.c15 = candles_15m
        self.c1h = candles_1h
        self.c4h = candles_4h
        self.p   = params

        # Map 1h candle index in c1h to corresponding c15 index
        # Map 4h candle index in c4h to corresponding c15 index
        self.i1h_at_15m = []  # for each 15m candle, the c1h index we should use
        self.i4h_at_15m = []

        # Build the alignment
        self._build_alignment()

        # Per-TF MACD state arrays (populated in compute())
        self.states_15m = []
        self.states_1h  = []
        self.states_4h  = []

    def _build_alignment(self):
        """
        For each 15m candle, find which 1h/4h candle is "current".
        A 1h candle is current if its ts_bucket <= 15m_ts < (ts_bucket + 1h)
        """
        if not self.c15:
            return
        # 1h bucket = ts // 3600 * 3600
        # Build i1h_lookup: at c15 index i, what is the c1h index?
        # We walk through c1h and track the latest c15 index we've seen
        c15_idx = 0
        for i in range(len(self.c15)):
            ts15 = self.c15[i]['ts']
            bucket1h = ts15 // 3600
            # Advance c1h pointer while c1h[j]['ts'] // 3600 <= bucket1h
            while c15_idx < len(self.c1h) and self.c1h[c15_idx]['ts'] // 3600 <= bucket1h:
                c15_idx += 1
            self.i1h_at_15m.append(c15_idx - 1 if c15_idx > 0 else 0)

        c4h_idx = 0
        for i in range(len(self.c15)):
            ts15 = self.c15[i]['ts']
            bucket4h = ts15 // 14400
            while c4h_idx < len(self.c4h) and self.c4h[c4h_idx]['ts'] // 14400 <= bucket4h:
                c4h_idx += 1
            self.i4h_at_15m.append(c4h_idx - 1 if c4h_idx > 0 else 0)

    def compute(self) -> None:
        """
        Run the O(n) single-pass computation for all TFs.
        Populates self.states_15m, states_1h, states_4h as lists of dicts.
        """
        macd15 = IncrementalMACD(self.p['macd_fast'], self.p['macd_slow'],
                                  self.p['macd_signal'])
        macd1h = IncrementalMACD(self.p['macd_fast'], self.p['macd_slow'],
                                  self.p['macd_signal'])
        macd4h = IncrementalMACD(self.p['macd_fast'], self.p['macd_slow'],
                                  self.p['macd_signal'])

        prev_1h_idx = -1
        prev_4h_idx = -1

        for i in range(len(self.c15)):
            # Update 15m
            c15_state = macd15.add_price(self.c15[i]['close'])

            # Update 1h when we cross a new 1h candle boundary
            ih = self.i1h_at_15m[i] if i < len(self.i1h_at_15m) else prev_1h_idx
            if ih != prev_1h_idx and ih >= 0:
                macd1h.add_price(self.c1h[ih]['close'])
                prev_1h_idx = ih
            c1h_state = macd1h.current()

            # Update 4h when we cross a new 4h candle boundary
            ih4 = self.i4h_at_15m[i] if i < len(self.i4h_at_15m) else prev_4h_idx
            if ih4 != prev_4h_idx and ih4 >= 0:
                macd4h.add_price(self.c4h[ih4]['close'])
                prev_4h_idx = ih4
            c4h_state = macd4h.current()

            # Also compute regime and crossover info
            self.states_15m.append(self._enrich(macd15, c15_state))
            self.states_1h.append(self._enrich(macd1h, c1h_state))
            self.states_4h.append(self._enrich(macd4h, c4h_state))

    def _enrich(self, macd: IncrementalMACD, base_state: dict) -> dict:
        """Add regime, crossover_age, histogram_rate to base state."""
        thr = self.p['regime_threshold']
        macd_line = base_state['macd_line']
        signal    = base_state['signal_line']
        hist      = base_state['histogram']

        # Regime
        if macd_line is not None and signal is not None:
            if macd_line > thr:
                regime = 'BULL'
            elif macd_line < -thr:
                regime = 'BEAR'
            else:
                regime = 'NEUTRAL'
        else:
            regime = 'NEUTRAL'

        # Crossover age
        age, xo_dir = macd.crossover_age()

        # Histogram rate
        if hist is not None and len(macd.hist_series) >= 2:
            prev_hist = macd.hist_series[-2]
            if prev_hist is not None and abs(prev_hist) > 1e-10:
                hist_rate = (hist - prev_hist) / abs(prev_hist)
            else:
                hist_rate = 0.0
        else:
            hist_rate = 0.0

        return {
            **base_state,
            'regime':      regime,
            'xover_age':   age,
            'xover_dir':   xo_dir,
            'hist_rate':   hist_rate,
            'macd_line':   macd_line,
            'signal_line': signal,
            'histogram':   hist,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY / EXIT RULES
# ═══════════════════════════════════════════════════════════════════════════════

def evaluate_entry_at(states15, states1h, states4h, idx: int,
                      params: dict) -> Optional[dict]:
    """
    Evaluate MTF-MACD entry at master timeline index `idx`.
    All states are precomputed lists, states15[idx], states1h[idx], states4h[idx]
    are the state dicts at that point in time.
    """
    if idx >= len(states15) or idx >= len(states1h) or idx >= len(states4h):
        return None

    s15 = states15[idx]
    s1h = states1h[idx]
    s4h = states4h[idx]

    # Warmup: need valid histogram (signal line computed)
    if s15.get('histogram') is None or s1h.get('histogram') is None or s4h.get('histogram') is None:
        return None

    xo15_dir = 1 if s15.get('xover_dir') == 'cross_over' else -1 if s15.get('xover_dir') == 'cross_under' else 0
    xo1h_dir = 1 if s1h.get('xover_dir') == 'cross_over' else -1 if s1h.get('xover_dir') == 'cross_under' else 0
    xo4h_dir = 1 if s4h.get('xover_dir') == 'cross_over' else -1 if s4h.get('xover_dir') == 'cross_under' else 0

    # ── Trigger direction from 15m ───────────────────────────────────────
    if xo15_dir == 1:
        trigger_dir = 'LONG'
    elif xo15_dir == -1:
        trigger_dir = 'SHORT'
    elif not params.get('require_15m_xover', True):
        # Histogram majority fallback
        bull_count = sum(1 for s in [s15, s1h, s4h]
                         if s.get('hist_positive', False))
        trigger_dir = 'LONG' if bull_count >= 2 else 'SHORT'
    else:
        return None  # no 15m xover, and require_15m_xover=True

    # ── Regime filter: block if 4H or 1H crossover opposes ──────────────
    if xo4h_dir == -1 and xo15_dir == 1:
        return None
    if xo1h_dir == -1 and xo15_dir == 1:
        return None
    if xo4h_dir == 1 and xo15_dir == -1:
        return None
    if xo1h_dir == 1 and xo15_dir == -1:
        return None

    # ── Entry conditions ─────────────────────────────────────────────────
    m15_bull = s15['macd_above'] and s15['hist_positive']
    m15_bear = not s15['macd_above'] and not s15['hist_positive']
    m1h_bull = s1h['macd_above'] and s1h['hist_positive']
    m1h_bear = not s1h['macd_above'] and not s1h['hist_positive']
    m4h_bull = s4h['macd_above'] and s4h['hist_positive']
    m4h_bear = not s4h['macd_above'] and not s4h['hist_positive']

    if trigger_dir == 'LONG':
        if m15_bull and (m1h_bull or m4h_bull) and s4h['regime'] == 'BULL':
            return {
                'direction': 'LONG',
                'confidence': 85,
                'reason': f"mtf_macd_15mxo_age{s15.get('xover_age',0)}",
            }
    elif trigger_dir == 'SHORT':
        if m15_bear and (m1h_bear or m4h_bear) and s4h['regime'] == 'BEAR':
            return {
                'direction': 'SHORT',
                'confidence': 85,
                'reason': f"mtf_macd_15mxo_age{s15.get('xover_age',0)}",
            }
    return None


def evaluate_exit_at(states15, states4h, position_dir: str,
                      idx: int, params: dict) -> list:
    """Evaluate exit signals. Returns list of reason strings (empty=hold)."""
    if idx >= len(states15) or idx >= len(states4h):
        return []
    s15 = states15[idx]
    s4h = states4h[idx]
    exits = []

    hist_only = params.get('hist_only_exits', False)

    if position_dir == 'LONG':
        if not hist_only:
            if not s15['macd_above'] or not s15['hist_positive']:
                exits.append('15m_macd_flipped_bear')
            if s4h['regime'] == 'BEAR':
                exits.append('4h_regime_flipped_bear')
        if s15.get('hist_rate', 0) < params.get('hist_rate_floor', -0.15):
            exits.append('histogram_fading_fast')
    else:
        if not hist_only:
            if s15['macd_above'] or s15['hist_positive']:
                exits.append('15m_macd_flipped_bull')
            if s4h['regime'] == 'BULL':
                exits.append('4h_regime_flipped_bull')
        if s15.get('hist_rate', 0) > abs(params.get('hist_rate_ceil', 0.15)):
            exits.append('histogram_rallying_fast')
    return exits


# ═══════════════════════════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def backtest_token(token: str, days: int = 90,
                   params: dict = PARAMS, verbose: bool = True) -> dict:
    """
    Run MTF-MACD backtest for one token.
    Returns: {'token', 'trades', 'stats', 'errors', 'n15', 'n1h', 'n4h'}
    """
    if verbose:
        print(f"  Loading {token}...", flush=True)

    # ── Load candles from Binance (all 3 TFs, fully paginated) ─────────────
    c15, c1h, c4h = fetch_token_candles(token, days=days, sleep=0.06)

    if verbose:
        print(f"  {token}: 4h={len(c4h)}, 1h={len(c1h)}, 15m={len(c15)}", flush=True)

    if len(c15) < 100 or len(c1h) < 20 or len(c4h) < 10:
        return {'token': token, 'trades': [], 'stats': {},
                'errors': [f"Insufficient data: 4h={len(c4h)} 1h={len(c1h)} 15m={len(c15)}"],
                'n15': len(c15), 'n1h': len(c1h), 'n4h': len(c4h)}

    # ── Precompute MACD states (O(n) single pass) ────────────────────────────
    mtf = MultiTimeFrameMACD(c15, c1h, c4h, params)
    mtf.compute()
    states15 = mtf.states_15m
    states1h = mtf.states_1h
    states4h = mtf.states_4h

    # Verify warmup
    WARMUP = max(50, params['macd_slow'] + params['macd_signal'] + 5)

    # ── Backtest loop ───────────────────────────────────────────────────────
    STEP   = params.get('step', 4)  # check entry every N 15m candles
    trades = []
    position = None

    # Also build quick-lookup: at each 15m index i, what's the close price
    closes15 = [c['close'] for c in c15]

    for i in range(WARMUP, len(c15), STEP):
        if i >= len(states15) or i >= len(states1h) or i >= len(states4h):
            break

        # ── Entry ───────────────────────────────────────────────────────────
        if position is None:
            entry = evaluate_entry_at(states15, states1h, states4h, i, params)
            if entry:
                position = {
                    'direction':  entry['direction'],
                    'entry_price': c15[i]['close'],
                    'entry_ts':    c15[i]['ts'],
                    'entry_idx':   i,
                    'reason':      entry['reason'],
                }

        # ── Exit ────────────────────────────────────────────────────────────
        else:
            exits = evaluate_exit_at(states15, states4h, position['direction'],
                                     i, params)
            if exits:
                exit_price = c15[i]['close']
                pnl = (exit_price - position['entry_price']) / position['entry_price'] * 100
                if position['direction'] == 'SHORT':
                    pnl = -pnl
                hold = i - position['entry_idx']
                trades.append({
                    'direction':   position['direction'],
                    'entry_price':  position['entry_price'],
                    'exit_price':  exit_price,
                    'entry_ts':    position['entry_ts'],
                    'exit_ts':     c15[i]['ts'],
                    'entry_time':  datetime.fromtimestamp(position['entry_ts']).isoformat(),
                    'exit_time':   datetime.fromtimestamp(c15[i]['ts']).isoformat(),
                    'hold_candles': hold,
                    'hold_hours':  round(hold * 15 / 60, 1),
                    'pnl_pct':     round(pnl, 3),
                    'exit_reason': exits[0],
                    'exit_reasons': exits,
                })
                position = None

    # Close open position at end
    if position:
        exit_price = c15[-1]['close']
        pnl = (exit_price - position['entry_price']) / position['entry_price'] * 100
        if position['direction'] == 'SHORT':
            pnl = -pnl
        hold = len(c15) - position['entry_idx']
        trades.append({
            'direction':   position['direction'],
            'entry_price': position['entry_price'],
            'exit_price':  exit_price,
            'entry_ts':    position['entry_ts'],
            'exit_ts':     c15[-1]['ts'],
            'entry_time':  datetime.fromtimestamp(position['entry_ts']).isoformat(),
            'exit_time':   datetime.fromtimestamp(c15[-1]['ts']).isoformat(),
            'hold_candles': hold,
            'hold_hours':  round(hold * 15 / 60, 1),
            'pnl_pct':     round(pnl, 3),
            'exit_reason': 'end_of_data',
            'exit_reasons': ['end_of_data'],
        })
        position = None

    # ── Stats ───────────────────────────────────────────────────────────────
    if not trades:
        return {'token': token, 'trades': [], 'stats': {},
                'errors': [], 'n15': len(c15), 'n1h': len(c1h), 'n4h': len(c4h)}

    wins   = [t for t in trades if t['pnl_pct'] > 0]
    longs  = [t for t in trades if t['direction'] == 'LONG']
    shorts = [t for t in trades if t['direction'] == 'SHORT']
    pnls   = [t['pnl_pct'] for t in trades]

    # Max drawdown (cumulative peak)
    running = 0.0; peak = 0.0; max_dd = 0.0
    for p in pnls:
        running += p
        if running > peak: peak = running
        if peak > 0: max_dd = min(max_dd, running - peak)

    stats = {
        'total_trades':  len(trades),
        'wins':          len(wins),
        'losses':        len(trades) - len(wins),
        'win_rate':      round(len(wins) / len(trades) * 100, 1),
        'avg_pnl':       round(sum(pnls) / len(pnls), 3),
        'median_pnl':    round(statistics.median(pnls), 3),
        'max_win':       round(max(pnls), 3),
        'max_loss':      round(min(pnls), 3),
        'max_drawdown':  round(max_dd, 3),
        'avg_hold_hours': round(sum(t['hold_candles'] for t in trades) * 15 / 60 / len(trades), 1),
        'longs':         len(longs),
        'shorts':        len(shorts),
        'long_win_rate': round(len([t for t in longs if t['pnl_pct'] > 0]) / len(longs) * 100, 1) if longs else 0,
        'short_win_rate': round(len([t for t in shorts if t['pnl_pct'] > 0]) / len(shorts) * 100, 1) if shorts else 0,
        'avg_long_pnl':  round(sum(t['pnl_pct'] for t in longs) / len(longs), 3) if longs else 0,
        'avg_short_pnl': round(sum(t['pnl_pct'] for t in shorts) / len(shorts), 3) if shorts else 0,
    }

    if verbose:
        print(f"  {token}: {stats['total_trades']} trades | WR={stats['win_rate']}% | "
              f"avg={stats['avg_pnl']:+.3f}% | max_dd={stats['max_drawdown']:.2f}% | "
              f"L={stats['longs']}({stats['long_win_rate']}%) S={stats['shorts']}({stats['short_win_rate']}%)",
              flush=True)

    return {'token': token, 'trades': trades, 'stats': stats,
            'errors': [], 'n15': len(c15), 'n1h': len(c1h), 'n4h': len(c4h)}


# ═══════════════════════════════════════════════════════════════════════════════
# PARAM SWEEP
# ═══════════════════════════════════════════════════════════════════════════════

def param_sweep(tokens: list, sweeps: list, days: int = 90) -> None:
    """Run backtest across multiple param configs, print comparison table."""
    import itertools

    base = dict(PARAMS)
    print(f"\n{'='*80}", flush=True)
    print(f"PARAM SWEEP | {len(sweeps)} configs | {len(tokens)} tokens | {days}d", flush=True)
    print(f"{'='*80}", flush=True)
    print(f"{'Config':<35} {'Trades':>6} {'WR%':>5} {'Avg%':>7} {'MaxDD%':>7} "
          f"{'L_WRs%':>6} {'S_WR%':>6} {'L':>4} {'S':>4}", flush=True)
    print(f"{'-'*80}", flush=True)

    results = []
    for sweep in sweeps:
        name = sweep['name']
        p = dict(base, **{k: v for k, v in sweep.items() if k != 'name'})
        total_trades = 0
        total_pnl_acc = 0.0
        total_wr_acc  = 0.0
        all_stats     = []

        for token in tokens:
            r = backtest_token(token, days=days, params=p, verbose=False)
            s = r.get('stats', {})
            if s and s['total_trades'] > 0:
                total_trades += s['total_trades']
                total_pnl_acc += s['avg_pnl'] * s['total_trades']
                total_wr_acc  += s['win_rate'] * s['total_trades']
                all_stats.append(s)

        if total_trades == 0:
            print(f"{name:<35} {'N/A':>6}")
            continue

        agg_wr  = total_wr_acc  / len(all_stats) if all_stats else 0
        agg_avg = total_pnl_acc / total_trades if total_trades else 0
        agg_dd  = max(s['max_drawdown'] for s in all_stats) if all_stats else 0
        l_wr    = sum(s['long_win_rate'] * s['longs'] for s in all_stats) / max(1, sum(s['longs'] for s in all_stats))
        s_wr    = sum(s['short_win_rate'] * s['shorts'] for s in all_stats) / max(1, sum(s['shorts'] for s in all_stats))
        l_cnt   = sum(s['longs']  for s in all_stats)
        s_cnt   = sum(s['shorts'] for s in all_stats)

        results.append((name, total_trades, agg_wr, agg_avg, agg_dd, l_wr, s_wr, l_cnt, s_cnt))
        print(f"{name:<35} {total_trades:>6} {agg_wr:>5.1f} {agg_avg:>+7.3f} "
              f"{agg_dd:>7.2f} {l_wr:>6.1f} {s_wr:>6.1f} {l_cnt:>4} {s_cnt:>4}", flush=True)

    # Mark best by win rate
    if results:
        best = max(results, key=lambda x: x[2])
        print(f"\n→ Best WR: {best[0]} at {best[2]:.1f}%  "
              f"(Avg: {best[3]:+.3f}%, MaxDD: {best[4]:.2f}%)", flush=True)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    tokens = sys.argv[1:] or DEFAULT_TOKENS
    DAYS   = 90

    print(f"=== MTF-MACD BACKTEST | {DAYS}d lookback ===", flush=True)
    print(f"Params: fast={PARAMS['macd_fast']} slow={PARAMS['macd_slow']} "
          f"signal={PARAMS['macd_signal']} require_15m_xover={PARAMS['require_15m_xover']} "
          f"step={PARAMS['step']}\n", flush=True)

    results = []
    for token in tokens:
        r = backtest_token(token, days=DAYS, params=PARAMS)
        results.append(r)
        if r.get('stats'):
            s = r['stats']
            print(f"→ {token}: {s['total_trades']} trades | WR={s['win_rate']}% | "
                  f"avg={s['avg_pnl']:+.3f}% | L={s['longs']}({s['long_win_rate']}%) "
                  f"S={s['shorts']}({s['short_win_rate']}%)\n", flush=True)
        else:
            print(f"→ {token}: no trades | errors={r.get('errors',[])}\n", flush=True)

    if len(results) > 1:
        all_t = [t for r in results for t in r.get('trades', [])]
        if all_t:
            import statistics as statmod
            pnls = [t['pnl_pct'] for t in all_t]
            wins = sum(1 for p in pnls if p > 0)
            longs = [t for t in all_t if t['direction'] == 'LONG']
            shorts = [t for t in all_t if t['direction'] == 'SHORT']
            running = 0.0; peak = 0.0; max_dd = 0.0
            for p in pnls:
                running += p
                if running > peak: peak = running
                if peak > 0: max_dd = min(max_dd, running - peak)
            print(f"=== AGGREGATE ({len(results)} tokens, {len(all_t)} trades) ===", flush=True)
            print(f"  WR={wins/len(all_t)*100:.1f}% | avg={statmod.mean(pnls):+.3f}% | "
                  f"median={statmod.median(pnls):+.3f}% | max_dd={max_dd:.2f}%", flush=True)
            print(f"  L={len(longs)}({sum(1 for t in longs if t['pnl_pct']>0)/max(1,len(longs))*100:.0f}%) "
                  f"S={len(shorts)}({sum(1 for t in shorts if t['pnl_pct']>0)/max(1,len(shorts))*100:.0f}%)", flush=True)

    print(f"\nParams: {json.dumps(PARAMS)}", flush=True)
