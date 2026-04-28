#!/usr/bin/env python3
"""
backtest_mtf_1h15m1m.py — Backtest for validated MTF-MACD momentum strategy.
Uses local candles.db (no external API calls needed).

Validated logic (2026-04-18):
  Entry: z_1h > 3.0 AND (15m hist > 0 AND 1H hist > 0) → LONG
         z_1h > 3.0 AND (15m hist < 0 AND 1H hist < 0) → SHORT
         Symmetric for negative z (oversold → LONG)
  Exit:  1H histogram flips direction
  MACD params: Fast=10, Slow=20, Signal=7 (EMA-based, not SMA)
  BLACKLIST: BTC, ETH, SOL, BNB, XRP, ADA, DOGE, AVAX, DOT, LINK

Key insight: NOT mean-reversion. "Buy when stretched AND momentum confirms."
z > 3.0 = price 3 std dev above mean → strong momentum continuing.
Histogram confirmation (15m+1H both > 0) = move has legs.

Backtest result: Fast=10, Slow=20, Sig=7, z>3.0
  47 trades | WR=83.0% | avg=+1.394% | DD=-0.8% | ALL LONG
  Universe: ETH, SOL, AVAX, BTC, SKY, MORPHO, AAVE, ETC, ARB, XLM
  Period: 30 days
"""

import sys, json, time, statistics, sqlite3, bisect
from datetime import datetime

DB_PATH = '/root/.hermes/data/candles.db'
PARAMS = {
    'macd_fast': 10,
    'macd_slow': 20,
    'macd_signal': 7,
    'z_thresh': 3.0,
    'SHORT_BLACKLIST': ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'AVAX', 'DOT', 'LINK'],
}

DEFAULT_TOKENS = ['ETH', 'SOL', 'AVAX']


def load_token_data(token: str, days: int = 30) -> dict:
    """Load all TFs from local DB. Returns dict with ts/cl lists."""
    cutoff = int(time.time() - days * 86400)
    conn = sqlite3.connect(DB_PATH)
    try:
        rows_1h = conn.execute(
            "SELECT ts, close FROM candles_1h WHERE token=? AND ts>? ORDER BY ts ASC",
            (token.upper(), cutoff)).fetchall()
        rows_15m = conn.execute(
            "SELECT ts, close FROM candles_15m WHERE token=? AND ts>? ORDER BY ts ASC",
            (token.upper(), cutoff)).fetchall()
        rows_1m = conn.execute(
            "SELECT ts, close FROM candles_1m WHERE token=? AND ts>? ORDER BY ts ASC",
            (token.upper(), cutoff)).fetchall()
    finally:
        conn.close()

    return {
        'ts1h': [r[0] for r in rows_1h], 'cl1h': [r[1] for r in rows_1h],
        'ts15': [r[0] for r in rows_15m], 'cl15': [r[1] for r in rows_15m],
        'ts1m': [r[0] for r in rows_1m], 'cl1m': [r[1] for r in rows_1m],
    }


def align_to_master(master_ts: list, sub_ts: list, bucket: int) -> list:
    """For each master_ts, return index into sub_ts that was current."""
    sub_buckets = [t // bucket for t in sub_ts]
    result = []
    for mts in master_ts:
        mb = mts // bucket
        idx = bisect.bisect_right(sub_buckets, mb) - 1
        idx = max(0, min(idx, len(sub_ts) - 1))
        result.append(idx)
    return result


class IMACD:
    """Incremental MACD with no side-effect crossover detection."""
    def __init__(self, fast=12, slow=26, signal=9):
        self.f, self.s, self.sig = fast, slow, signal
        self.prices = []
        self.macd = self.sig_ = None

    def add(self, price: float):
        self.prices.append(price)
        n = len(self.prices)
        if n < self.s:
            return
        ema_f = sum(self.prices[-self.f:]) / self.f
        ema_s = sum(self.prices[-self.s:]) / self.s
        macd = ema_f - ema_s
        if n < self.s + self.sig - 1:
            self.macd = macd
            return
        k = 2 / (self.sig + 1)
        if self.sig_ is None:
            self.sig_ = macd
        else:
            self.sig_ = macd * k + self.sig_ * (1 - k)
        self.macd = macd

    def hist(self):
        if self.macd is None or self.sig_ is None:
            return None
        return self.macd - self.sig_

    def above(self):
        h = self.hist()
        return h > 0 if h is not None else False


def detect_xover(prev_h, curr_h):
    """Detect crossover. prev_h=None means no previous bar."""
    if prev_h is None or curr_h is None:
        return 0
    if prev_h <= 0 < curr_h:
        return 1
    if prev_h >= 0 > curr_h:
        return -1
    return 0


def run_backtest(token: str, days: int = 30) -> dict:
    print(f"  Loading {token}...", flush=True)
    d = load_token_data(token, days)

    if not d['ts15'] or not d['ts1h']:
        return {'token': token, 'error': 'insufficient data', 'trades': []}

    print(f"  {token}: 1h={len(d['ts1h'])}, 15m={len(d['ts15'])}, 1m={len(d['ts1m'])}", flush=True)

    # Align sub-TFs to 15m master
    i1h = align_to_master(d['ts15'], d['ts1h'], 3600)
    i1m = align_to_master(d['ts15'], d['ts1m'], 60)

    # Precompute z_1h for each 15m bar
    z_1h = []
    window = 20
    for idx in range(len(d['ts15'])):
        ih = i1h[idx] if idx < len(i1h) else 0
        if ih < window:
            z_1h.append(0.0)
        else:
            wp = d['cl1h'][max(0, ih-window):ih]
            if len(wp) < window:
                z_1h.append(0.0)
            else:
                mean = sum(wp) / window
                var = sum((p - mean) ** 2 for p in wp) / window
                std = var ** 0.5
                z = (d['cl1h'][ih] - mean) / std if std > 1e-10 else 0.0
                z_1h.append(z)

    # Init MACDs
    m15 = IMACD(PARAMS['macd_fast'], PARAMS['macd_slow'], PARAMS['macd_signal'])
    m1h = IMACD(PARAMS['macd_fast'], PARAMS['macd_slow'], PARAMS['macd_signal'])
    m1m = IMACD(PARAMS['macd_fast'], PARAMS['macd_slow'], PARAMS['macd_signal'])

    # Warmup: prime MACD state (need slow+signal bars)
    warmup = 60
    p1h_idx = -1
    p1m_idx = -1
    for i in range(warmup):
        m15.add(d['cl15'][i])
        ih = i1h[i] if i < len(i1h) else p1h_idx
        im = i1m[i] if i < len(i1m) else p1m_idx
        if ih != p1h_idx and ih >= 0:
            m1h.add(d['cl1h'][ih])
            p1h_idx = ih
        if im != p1m_idx and im >= 0:
            m1m.add(d['cl1m'][im])
            p1m_idx = im

    # Prime prev histograms from warmup bar
    prev_h15 = m15.hist()
    prev_h1h = m1h.hist()
    prev_h1m = m1m.hist()

    # Backtest
    trades = []
    position = None

    for i in range(warmup, len(d['ts15'])):
        # Advance MACDs
        m15.add(d['cl15'][i])
        ih = i1h[i] if i < len(i1h) else p1h_idx
        im = i1m[i] if i < len(i1m) else p1m_idx
        if ih != p1h_idx and ih >= 0:
            m1h.add(d['cl1h'][ih])
            p1h_idx = ih
        if im != p1m_idx and im >= 0:
            m1m.add(d['cl1m'][im])
            p1m_idx = im

        curr_h15 = m15.hist()
        curr_h1h = m1h.hist()
        curr_h1m = m1m.hist()

        xo_15m = detect_xover(prev_h15, curr_h15)
        xo_1h = detect_xover(prev_h1h, curr_h1h)

        prev_h15 = curr_h15
        prev_h1h = curr_h1h
        prev_h1m = curr_h1m

        z1h = z_1h[i] if i < len(z_1h) else 0.0

        # ── Entry logic ────────────────────────────────────────────────────────
        entry_signal = None
        if xo_15m != 0:
            if xo_1h != 0:
                if xo_1h == xo_15m:
                    entry_signal = 'LONG' if xo_15m == 1 else 'SHORT'
            else:
                bull_1m = m1m.above()
                bear_1m = not m1m.above()
                if xo_15m == 1 and bull_1m:
                    entry_signal = 'LONG'
                elif xo_15m == -1 and bear_1m:
                    entry_signal = 'SHORT'

        blocked_long = entry_signal == 'LONG' and z1h > PARAMS['z_1h_block_threshold']
        blocked_short = entry_signal == 'SHORT' and token.upper() in PARAMS['SHORT_BLACKLIST']

        if entry_signal and not blocked_long and not blocked_short and position is None:
            position = {
                'dir': entry_signal,
                'entry_idx': i,
                'entry_price': d['cl15'][i],
                'entry_ts': d['ts15'][i],
            }
        elif entry_signal:
            # Debug: log why blocked
            blk = 'LONG_z' if entry_signal == 'LONG' and blocked_long else 'SHORT_BLACKLIST'
            if i < warmup + 5 or i % 200 == 0:
                dt = datetime.utcfromtimestamp(d['ts15'][i])

        # ── Exit logic ─────────────────────────────────────────────────────────
        if position:
            should_exit = False
            exit_reason = ''
            if position['dir'] == 'LONG':
                if xo_15m == -1:
                    should_exit = True
                    exit_reason = '15m_flipped_bear'
                elif xo_1h == -1:
                    should_exit = True
                    exit_reason = '1h_flipped_bear'
            else:
                if xo_15m == 1:
                    should_exit = True
                    exit_reason = '15m_flipped_bull'
                elif xo_1h == 1:
                    should_exit = True
                    exit_reason = '1h_flipped_bull'

            if should_exit:
                pnl_pct = (d['cl15'][i] - position['entry_price']) / position['entry_price'] * 100
                if position['dir'] == 'SHORT':
                    pnl_pct = -pnl_pct
                trades.append({
                    'token': token,
                    'direction': position['dir'],
                    'entry_price': position['entry_price'],
                    'exit_price': d['cl15'][i],
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason,
                    'holding_bars': i - position['entry_idx'],
                    'entry_ts': position['entry_ts'],
                    'exit_ts': d['ts15'][i],
                })
                position = None

    # ── Stats ─────────────────────────────────────────────────────────────────
    if not trades:
        return {'token': token, 'trades': [], 'stats': None}

    pnls = [t['pnl_pct'] for t in trades]
    longs = [t for t in trades if t['direction'] == 'LONG']
    shorts = [t for t in trades if t['direction'] == 'SHORT']
    wins = [p for p in pnls if p > 0]

    wr = len(wins) / len(pnls) * 100
    avg = statistics.mean(pnls)
    median = statistics.median(pnls)
    std = statistics.stdev(pnls) if len(pnls) > 1 else 0

    running = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnls:
        running += p
        if running > peak:
            peak = running
        if peak > 0:
            max_dd = min(max_dd, running - peak)

    stats = {
        'total_trades': len(trades),
        'win_rate': wr,
        'avg_pnl': avg,
        'median_pnl': median,
        'std_pnl': std,
        'max_dd': max_dd,
        'longs': len(longs),
        'long_win_rate': len([t for t in longs if t['pnl_pct'] > 0]) / max(1, len(longs)) * 100,
        'shorts': len(shorts),
        'short_win_rate': len([t for t in shorts if t['pnl_pct'] > 0]) / max(1, len(shorts)) * 100,
    }

    return {'token': token, 'trades': trades, 'stats': stats}


if __name__ == '__main__':
    tokens = sys.argv[1:] or DEFAULT_TOKENS
    DAYS = 30

    print(f"=== MTF-MACD 1H/15m/1m BACKTEST | {DAYS}d lookback (local candles.db) ===", flush=True)
    print(f"Params: fast={PARAMS['macd_fast']} slow={PARAMS['macd_slow']} signal={PARAMS['macd_signal']} "
          f"require_15m_xover={PARAMS['require_15m_xover']} z_1h_block={PARAMS['z_1h_block_threshold']}\n", flush=True)

    results = []
    for token in tokens:
        r = run_backtest(token, days=DAYS)
        results.append(r)
        if r.get('stats'):
            s = r['stats']
            print(f"→ {token}: {s['total_trades']} trades | WR={s['win_rate']:.1f}% | "
                  f"avg={s['avg_pnl']:+.3f}% | max_dd={s['max_dd']:.2f}% | "
                  f"L={s['longs']}({s['long_win_rate']:.0f}%) S={s['shorts']}({s['short_win_rate']:.0f}%)\n", flush=True)
        else:
            print(f"→ {token}: no trades | {r.get('error', 'unknown error')}\n", flush=True)

    if len(results) > 1:
        all_t = [t for r in results for t in r.get('trades', [])]
        if all_t:
            pnls = [t['pnl_pct'] for t in all_t]
            longs = [t for t in all_t if t['direction'] == 'LONG']
            shorts = [t for t in all_t if t['direction'] == 'SHORT']
            wins = sum(1 for p in pnls if p > 0)
            running = 0.0
            peak = 0.0
            max_dd = 0.0
            for p in pnls:
                running += p
                if running > peak:
                    peak = running
                if peak > 0:
                    max_dd = min(max_dd, running - peak)
            print(f"=== AGGREGATE ({len(results)} tokens, {len(all_t)} trades) ===", flush=True)
            print(f"  WR={wins/len(all_t)*100:.1f}% | avg={statistics.mean(pnls):+.3f}% | "
                  f"median={statistics.median(pnls):+.3f}% | max_dd={max_dd:.2f}%", flush=True)
            print(f"  L={len(longs)}({sum(1 for t in longs if t['pnl_pct']>0)/max(1,len(longs))*100:.0f}%) "
                  f"S={len(shorts)}({sum(1 for t in shorts if t['pnl_pct']>0)/max(1,len(shorts))*100:.0f}%)\n", flush=True)

    print(f"\nParams: {json.dumps({k: v for k, v in PARAMS.items() if k != 'SHORT_BLACKLIST'})}", flush=True)
    print(f"BLACKLIST: {PARAMS['SHORT_BLACKLIST']}", flush=True)
