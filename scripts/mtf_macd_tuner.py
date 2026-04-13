#!/usr/bin/env python3
"""
MTF-MACD Tuner — Self-tuning MACD parameters per token.
Finds optimal (fast, slow, signal, exit, hold) combos via 90d backtest.
DB: /root/.hermes/data/mtf_macd_tuner.db

Data strategy:
  - 1H klines: paginate Binance in 1000-candle batches (3 pages ≈ 125 days)
  - 15m candles: aggregated from 1H OHLC
  - 4H klines: paginate Binance in 1000-candle batches (3 pages = 125 days)
  - All aggregation uses open_time as the grouping key (Binance ascending = oldest first)
"""
import sqlite3, requests, time, sys, functools
from datetime import datetime
from itertools import product
from multiprocessing import Pool, cpu_count

DB_PATH = '/root/.hermes/data/mtf_macd_tuner.db'
WINDOW_DAYS = 90
BINANCE_BASE = 'https://api.binance.com/api/v3/klines'

# ── Request caching ───────────────────────────────────────────────────────────
@functools.lru_cache(maxsize=4)
def _cached_request(url):
    """One request cache per URL — avoids hammering Binance for the same data.
    Returns None on connection/error so callers can break softly."""
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if attempt < 2:
                time.sleep(2 ** attempt)
            continue
    return None

# ── EMA ───────────────────────────────────────────────────────────────────────
def ema(data, period):
    if len(data) < period:
        return None
    k = 2 / (period + 1)
    val = sum(data[:period]) / period
    for price in data[period:]:
        val = price * k + val * (1 - k)
    return val

def compute_macd(closes, fast, slow, sig):
    """Compute current MACD values on a closes list.
    Returns (macd_line, signal_line, histogram) or (None, None, None) if insufficient data."""
    if len(closes) < slow + sig:
        return None, None, None
    ema_fast, ema_slow = [], []
    for i in range(slow - 1, len(closes)):
        ef = ema(closes[:i+1], fast)
        es = ema(closes[:i+1], slow)
        if ef is not None and es is not None:
            ema_fast.append(ef)
            ema_slow.append(es)
    if len(ema_fast) < sig:
        return None, None, None
    macd_series = [ema_fast[i] - ema_slow[i] for i in range(len(ema_fast))]
    sig_val = ema(macd_series, sig)
    if sig_val is None:
        return None, None, None
    return macd_series[-1], sig_val, macd_series[-1] - sig_val


class PrecomputedMACD:
    """O(1) histogram lookup for MACD series precomputed from closes.

    For closes index i (0-based):
      - macd(i)     = ema_fast[i] - ema_slow[i]         (valid for i >= slow-1)
      - histogram(i) = macd(i) - sig_ema(i)               (valid for i >= slow-1+sig)
      - sig_ema(i)   = EMA of macd values up to index i  (period = sig)
    """
    __slots__ = ('fast', 'slow', 'sig', 'closes', 'ema_fast', 'ema_slow',
                 'macd', 'sig_ema', 'warmup')

    def __init__(self, closes, fast, slow, sig):
        self.fast = fast
        self.slow = slow
        self.sig = sig
        self.closes = closes
        n = len(closes)

        k_f = 2.0 / (fast + 1)
        k_s = 2.0 / (slow + 1)
        k_g = 2.0 / (sig + 1)

        self.ema_fast = [0.0] * n
        self.ema_slow = [0.0] * n
        self.macd = [0.0] * n
        self.sig_ema = [0.0] * n

        # First valid index for EMA (slow-1)
        first = slow - 1
        # Seed: EMA of closes[:slow] with respective periods
        self.ema_fast[first] = ema(closes[:slow], fast)
        self.ema_slow[first] = ema(closes[:slow], slow)
        self.macd[first] = self.ema_fast[first] - self.ema_slow[first]

        # Incremental EMA for fast and slow
        for i in range(first + 1, n):
            self.ema_fast[i] = closes[i] * k_f + self.ema_fast[i-1] * (1 - k_f)
            self.ema_slow[i] = closes[i] * k_s + self.ema_slow[i-1] * (1 - k_s)
            self.macd[i] = self.ema_fast[i] - self.ema_slow[i]

        # First signal EMA is at closes index first+sig (need period+1 values for proper EMA)
        first_sig = first + sig  # = slow-1+sig
        # Use sig+1 values: closes indices first to first+sig (inclusive) = slow-1 to slow-1+sig
        self.sig_ema[first_sig] = ema(self.macd[first:first_sig+1], sig)

        # Incremental signal EMA
        for i in range(first_sig + 1, n):
            self.sig_ema[i] = self.macd[i] * k_g + self.sig_ema[i-1] * (1 - k_g)

        # Warmup: index at which histogram becomes valid
        self.warmup = first_sig  # = slow-1+sig

    def histogram(self, i):
        """Return histogram at closes index i, or None if not yet valid."""
        if i < self.warmup:
            return None
        return self.macd[i] - self.sig_ema[i]

    def macd_line(self, i):
        """Return MACD line at closes index i, or None if not yet valid."""
        if i < self.slow - 1:
            return None
        return self.macd[i]

    def crossover_count(self, start=None, end=None):
        """Count bullish MACD crossovers in the index range [start, end).
        A bullish crossover occurs when histogram crosses from <=0 to >0.
        """
        if start is None:
            start = self.warmup
        if end is None:
            end = len(self.closes)
        count = 0
        for i in range(start, end - 1):
            h_prev = self.histogram(i)
            h_curr = self.histogram(i + 1)
            if h_prev is not None and h_curr is not None and h_prev <= 0 < h_curr:
                count += 1
        return count


# ── Binance data fetching ───────────────────────────────────────────────────────
def fetch_1h_klines(symbol, window_days=WINDOW_DAYS):
    """Fetch N days of 1H klines from Binance via pagination.
    Returns list of [open_time, open, high, low, close, volume] (ascending, oldest→newest)."""
    limit = 1000
    now = int(time.time() * 1000)
    target_start = now - window_days * 24 * 3600 * 1000
    all_batches = []
    current_end = now

    for _ in range(4):
        current_start = current_end - (limit * 3600 * 1000)
        if current_start < target_start:
            # This batch would go before our target — trim and stop
            url = f'{BINANCE_BASE}?symbol={symbol}&interval=1h&limit={limit}&startTime={target_start}&endTime={current_end}'
        else:
            url = f'{BINANCE_BASE}?symbol={symbol}&interval=1h&limit={limit}&startTime={current_start}&endTime={current_end}'
        batch = _cached_request(url)
        if not batch:
            break
        all_batches.extend(batch)
        oldest = int(batch[0][0])
        if oldest < target_start:
            break
        current_end = oldest - 1
        if oldest < target_start and len(all_batches) >= 3000:
            break

    # Binance returns ascending (oldest first) — verify and sort
    all_batches.sort(key=lambda k: int(k[0]))
    return all_batches

def fetch_4h_klines(symbol, window_days=WINDOW_DAYS):
    """Fetch N days of 4H klines from Binance via pagination."""
    limit = 1000
    now = int(time.time() * 1000)
    target_start = now - window_days * 24 * 3600 * 1000
    all_batches = []
    current_end = now

    for _ in range(4):
        current_start = current_end - (limit * 4 * 3600 * 1000)
        if current_start < target_start:
            url = f'{BINANCE_BASE}?symbol={symbol}&interval=4h&limit={limit}&startTime={target_start}&endTime={current_end}'
        else:
            url = f'{BINANCE_BASE}?symbol={symbol}&interval=4h&limit={limit}&startTime={current_start}&endTime={current_end}'
        batch = _cached_request(url)
        if not batch:
            break
        all_batches.extend(batch)
        oldest = int(batch[0][0])
        if oldest < target_start:
            break
        current_end = oldest - 1

    all_batches.sort(key=lambda k: int(k[0]))
    return all_batches

def fetch_15m_klines(symbol, window_days=WINDOW_DAYS):
    """Fetch N days of 15m klines from Binance via backward pagination.
    Returns list of [open_time, open, high, low, close, volume] (ascending, oldest→newest)."""
    limit = 1000
    now = int(time.time() * 1000)
    target_start = now - window_days * 24 * 3600 * 1000
    all_batches = []
    current_end = now

    for _ in range(12):  # 12 * 1000 * 15min = 7200h = 300 days max
        url = f'{BINANCE_BASE}?symbol={symbol}&interval=15m&limit={limit}&endTime={current_end}'
        batch = _cached_request(url)
        if not batch:
            break
        all_batches.extend(batch)
        oldest = int(batch[0][0])
        if oldest <= target_start:
            break
        if len(batch) < limit:
            break
        current_end = oldest - 1

    all_batches.sort(key=lambda k: int(k[0]))
    return all_batches


def build_15m_candles_from_1h(klines_1h):
    """DEPRECATED — only use for lookback warmup if 15m data is unavailable.
    Aggregate 1H OHLC into 15m candles.
    klines_1h: list of [open_time, open, high, low, close, volume] (ascending).
    Returns: dict of {ts15m: [open, high, low, close]}."""
    buckets = {}
    for k in klines_1h:
        ts = int(k[0])
        bucket_ts = (ts // (15 * 60 * 1000)) * (15 * 60 * 1000)
        o, h, l, c = float(k[1]), float(k[2]), float(k[3]), float(k[4])
        if bucket_ts not in buckets:
            buckets[bucket_ts] = [o, h, l, c]
        else:
            buckets[bucket_ts][1] = max(buckets[bucket_ts][1], h)
            buckets[bucket_ts][2] = min(buckets[bucket_ts][2], l)
            buckets[bucket_ts][3] = c
    return buckets

# ── Backtest engine ────────────────────────────────────────────────────────────
def test_mtf_macd_config(token, fast, slow, signal, exit_strategy,
                         hold_minutes, score_threshold, regime_filter,
                         window_days=WINDOW_DAYS, verbose=False):
    """
    Backtest MTF-MACD strategy on a token.
    Entry: 15m MACD bullish crossover + regime filter + score threshold.
    Exit: any_flip or histogram_flip, or hold_minutes elapsed.
    Returns metrics dict or None if insufficient data.

    Uses PrecomputedMACD for O(1) histogram lookup instead of recomputing
    EMA from scratch at each candle (which was O(n^2)).
    """
    symbol = token.upper() + 'USDT'

    # ── Fetch all TF data ─────────────────────────────────────────────────────
    klines_1h = fetch_1h_klines(symbol, window_days)
    klines_4h = fetch_4h_klines(symbol, window_days)
    klines_15m = fetch_15m_klines(symbol, window_days)

    if len(klines_1h) < 100 or len(klines_4h) < 20 or len(klines_15m) < 100:
        if verbose:
            print(f'  [WARN] {token}: insufficient data ({len(klines_1h)} 1h, {len(klines_4h)} 4h, {len(klines_15m)} 15m)')
        return None

    # Build 15m candles from real Binance 15m klines
    sorted_15m_ts = sorted(int(k[0]) for k in klines_15m)
    closes_15m = [float(k[4]) for k in klines_15m]

    # 1H closes from raw klines
    closes_1h = [float(k[4]) for k in klines_1h]

    # 4H closes from raw klines
    closes_4h = [float(k[4]) for k in klines_4h]

    warmup = slow + signal + 5  # need enough for EMA convergence
    if len(closes_15m) < warmup + 1 or len(closes_1h) < warmup + 1 or len(closes_4h) < 10:
        return None

    if verbose:
        print(f'  [DATA] {token}: {len(closes_15m)} 15m, {len(closes_1h)} 1h, {len(closes_4h)} 4h candles')

    # ── Precompute MACD series for O(1) histogram lookup ───────────────────────
    pm_15m = PrecomputedMACD(closes_15m, fast, slow, signal)
    pm_1h  = PrecomputedMACD(closes_1h,  fast, slow, signal)
    pm_4h  = PrecomputedMACD(closes_4h,  fast, slow, signal)

    trades = []

    # Walk every potential entry point
    for i in range(warmup, len(closes_15m) - 1):
        # Index mapping: 15m[i] is at 1h[i//4], 4h[i//16]
        ih_1h = min(i // 4, len(closes_1h) - 1)
        ih_4h = min(i // 16, len(closes_4h) - 1)

        # ── MACD crossover on 15m (entry trigger) ─────────────────────────────
        h_prev = pm_15m.histogram(i - 1)
        h_curr = pm_15m.histogram(i)

        if h_prev is None or h_curr is None:
            continue

        # Bullish crossover: prev hist <= 0, curr hist > 0
        if not (h_prev <= 0 < h_curr):
            continue

        direction = 'LONG'

        # ── Regime filter ─────────────────────────────────────────────────────
        if regime_filter:
            # All larger TFs must have positive histogram (confirming bullish)
            h_1h = pm_1h.histogram(ih_1h)
            h_4h = pm_4h.histogram(ih_4h)
            if h_1h is None or h_4h is None:
                continue
            if h_1h <= 0 or h_4h <= 0:
                continue  # regime not bullish

        # ── Score threshold ────────────────────────────────────────────────────
        # Count TFs with hist > 0 (bullish confirmation)
        score_count = 0
        h_15m = pm_15m.histogram(i)
        h_1h  = pm_1h.histogram(ih_1h)
        h_4h  = pm_4h.histogram(ih_4h)
        if h_15m is not None and h_15m > 0:
            score_count += 1
        if h_1h is not None and h_1h > 0:
            score_count += 1
        if h_4h is not None and h_4h > 0:
            score_count += 1

        if score_count < score_threshold:
            continue

        # ── Enter trade ──────────────────────────────────────────────────────
        entry_price = closes_15m[i]
        entry_ts    = sorted_15m_ts[i]
        hold_end_ts = entry_ts + hold_minutes * 60 * 1000

        # Find exit
        exit_price = None
        exit_type  = None
        for j in range(i + 1, len(closes_15m)):
            if sorted_15m_ts[j] > hold_end_ts:
                # Hold expired — exit at close of that candle
                exit_price = closes_15m[j]
                exit_type  = 'hold'
                break

            # Histogram at j-1 and j for flip detection (O(1) lookup)
            h_prev = pm_15m.histogram(j - 1)
            h_curr = pm_15m.histogram(j)

            flip = False
            if h_prev is not None and h_curr is not None:
                flip = (h_prev <= 0 < h_curr) or (h_prev >= 0 > h_curr)

            if flip:
                if exit_strategy == 'histogram_flip':
                    exit_price = closes_15m[j]
                    exit_type  = 'hist_flip'
                    break
                elif exit_strategy == 'any_flip':
                    # Check all 3 TFs for flip at this point
                    j_1h = j // 4
                    j_4h = j // 16
                    h15m_prev = h_prev
                    h15m_curr = h_curr
                    h1h_prev  = pm_1h.histogram(j_1h - 1)
                    h1h_curr  = pm_1h.histogram(j_1h)
                    h4h_prev  = pm_4h.histogram(j_4h - 1)
                    h4h_curr  = pm_4h.histogram(j_4h)

                    any_flip = False
                    for hpr, hcu in [(h15m_prev, h15m_curr), (h1h_prev, h1h_curr), (h4h_prev, h4h_curr)]:
                        if hpr is not None and hcu is not None:
                            if (hpr <= 0 < hcu) or (hpr >= 0 > hcu):
                                any_flip = True
                                break
                    if any_flip:
                        exit_price = closes_15m[j]
                        exit_type  = 'any_flip'
                        break

        if exit_price is None:
            continue

        pnl_pct = (exit_price - entry_price) / entry_price * 100
        trades.append({
            'direction': direction, 'entry': entry_price, 'exit': exit_price,
            'pnl_pct': pnl_pct, 'exit_type': exit_type,
        })

    if not trades:
        return None

    wins       = [t for t in trades if t['pnl_pct'] > 0]
    losses     = [t for t in trades if t['pnl_pct'] <= 0]
    wr         = len(wins) / len(trades) * 100
    gross_win  = sum(t['pnl_pct'] for t in wins)
    gross_loss = abs(sum(t['pnl_pct'] for t in losses))
    pf         = gross_win / gross_loss if gross_loss > 0 else float('inf') if gross_win > 0 else 0
    total_pnl  = sum(t['pnl_pct'] for t in trades)

    # Max drawdown (rolling peak-to-trough)
    dd = 0; peak = -9999
    for t in trades:
        peak = max(peak, t['pnl_pct'])
        dd   = min(dd, t['pnl_pct'] - peak)
    max_dd = dd

    return {
        'signals':         len(trades),
        'wins':            len(wins),
        'losses':          len(losses),
        'win_rate':        round(wr, 4),
        'profit_factor':   round(pf, 4),
        'total_pnl_pct':   round(total_pnl, 4),
        'max_drawdown_pct': round(max_dd, 4),
        'avg_pnl_pct':     round(total_pnl / len(trades), 4),
    }

# ── DB helpers ─────────────────────────────────────────────────────────────────
def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    for sql in [
        """CREATE TABLE IF NOT EXISTS backtest_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_ts DATETIME DEFAULT CURRENT_TIMESTAMP,
            window_days INTEGER NOT NULL,
            tokens_tested TEXT NOT NULL,
            configs_tried INTEGER NOT NULL,
            best_token_count INTEGER NOT NULL,
            notes TEXT)""",
        """CREATE TABLE IF NOT EXISTS backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER REFERENCES backtest_runs(id),
            token TEXT NOT NULL,
            fast INTEGER NOT NULL, slow INTEGER NOT NULL, signal INTEGER NOT NULL,
            exit_strategy TEXT NOT NULL, hold_minutes INTEGER NOT NULL,
            score_threshold INTEGER NOT NULL, regime_filter INTEGER NOT NULL,
            signals INTEGER NOT NULL, wins INTEGER NOT NULL, losses INTEGER NOT NULL,
            win_rate REAL NOT NULL, profit_factor REAL NOT NULL,
            total_pnl_pct REAL NOT NULL, max_drawdown_pct REAL NOT NULL,
            avg_pnl_pct REAL NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS token_best_config (
            token TEXT PRIMARY KEY,
            fast INTEGER NOT NULL, slow INTEGER NOT NULL, signal INTEGER NOT NULL,
            exit_strategy TEXT NOT NULL, hold_minutes INTEGER NOT NULL,
            score_threshold INTEGER NOT NULL DEFAULT 2, regime_filter INTEGER NOT NULL DEFAULT 1,
            win_rate REAL NOT NULL, profit_factor REAL NOT NULL,
            total_pnl_pct REAL NOT NULL, signal_count INTEGER NOT NULL,
            backtest_run_id INTEGER REFERENCES backtest_runs(id),
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP, is_stale INTEGER NOT NULL DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS monitored_tokens (
            token TEXT PRIMARY KEY, first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            signal_count INTEGER DEFAULT 0, last_signal_at DATETIME, is_active INTEGER NOT NULL DEFAULT 1)""",
    ]:
        c.execute(sql)
    conn.commit()
    conn.close()

def register_token(token):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO monitored_tokens (token) VALUES (?)", (token.upper(),))
    conn.commit()
    conn.close()

def get_monitored_tokens():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT token FROM monitored_tokens WHERE is_active = 1")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows

def load_current_best_configs():
    """Load token_best_config into a dict keyed by token.
    Returns {token: {fast, slow, signal, exit_strategy, hold_minutes, score_threshold, regime_filter, is_stale}}."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT token, fast, slow, signal, exit_strategy, hold_minutes,
                  score_threshold, regime_filter, is_stale FROM token_best_config""")
    rows = c.fetchall()
    conn.close()
    return {r[0]: {
        'fast': r[1], 'slow': r[2], 'signal': r[3],
        'exit_strategy': r[4], 'hold_minutes': r[5],
        'score_threshold': r[6], 'regime_filter': bool(r[7]),
        'is_stale': bool(r[8]),
    } for r in rows}

# ── Param grid ─────────────────────────────────────────────────────────────────
PARAM_GRID = {
    'fast':            [8, 12],
    'slow':            [50, 55, 65],
    'signal':          [12, 15, 17, 28],
    'exit_strategy':   ['any_flip', 'histogram_flip'],
    'hold_minutes':    [60, 120, 240, 480],
    'score_threshold': [2, 3],
    'regime_filter':   [0, 1],
}

def prune_combo(fast, slow, signal):
    """True = invalid combo, skip it."""
    if slow == 50 and fast != 8:
        return True   # slow=50 only with fast=8
    if signal == 28 and slow != 65:
        return True   # signal=28 only with slow=65
    return False

def generate_grid():
    """Yield (fast, slow, signal, exit, hold, score, reg) tuples, skipping pruned combos."""
    for fast in PARAM_GRID['fast']:
        for slow in PARAM_GRID['slow']:
            for sig in PARAM_GRID['signal']:
                if prune_combo(fast, slow, sig):
                    continue
                for ex in PARAM_GRID['exit_strategy']:
                    for ho in PARAM_GRID['hold_minutes']:
                        for sc in PARAM_GRID['score_threshold']:
                            for rg in PARAM_GRID['regime_filter']:
                                yield (fast, slow, sig, ex, ho, sc, rg)

# ── Sweep ──────────────────────────────────────────────────────────────────────
def _test_config_worker(args):
    """Worker function for parallel config testing. Returns (token, params, result)."""
    token, fast, slow, sig, ex, ho, sc, rg, window_days = args
    res = test_mtf_macd_config(
        token, fast, slow, sig, ex, ho, sc, bool(rg), window_days, verbose=False
    )
    return (token, (fast, slow, sig, ex, ho, sc, rg), res)


def _test_config_worker_v2(args):
    """Fast worker: pre-fetched candles + precomputed MACD series.
    Each config gets O(1) histogram lookup instead of O(n^2) EMA recompute.
    Returns (token, params, result).
    """
    (token, fast, slow, sig, ex, ho, sc, rg,
     closes_15m, closes_1h, closes_4h, sorted_15m_ts,
     pm_15m_base, pm_1h_base, pm_4h_base, warmup, window_days) = args

    # Build PrecomputedMACD for this specific config (O(n) not O(n^2))
    pm_15m = PrecomputedMACD(closes_15m, fast, slow, sig)
    pm_1h  = PrecomputedMACD(closes_1h,  fast, slow, sig)
    pm_4h  = PrecomputedMACD(closes_4h,  fast, slow, sig)

    res = _fast_backtest(
        token, fast, slow, sig, ex, ho, sc, bool(rg),
        closes_15m, closes_1h, closes_4h, sorted_15m_ts,
        pm_15m, pm_1h, pm_4h, warmup
    )
    return (token, (fast, slow, sig, ex, ho, sc, rg), res)


def _fast_backtest(token, fast, slow, sig, exit_strategy,
                   hold_minutes, score_threshold, regime_filter,
                   closes_15m, closes_1h, closes_4h, sorted_15m_ts,
                   pm_15m, pm_1h, pm_4h, warmup):
    """Fast backtest using precomputed close arrays and PrecomputedMACD.
    Same logic as test_mtf_macd_config but avoids repeated data fetching.
    """
    trades = []
    n_15m = len(closes_15m)

    for i in range(warmup, n_15m - 1):
        ih_1h = min(i // 4, len(closes_1h) - 1)
        ih_4h = min(i // 16, len(closes_4h) - 1)

        h_prev = pm_15m.histogram(i - 1)
        h_curr = pm_15m.histogram(i)
        if h_prev is None or h_curr is None:
            continue
        if not (h_prev <= 0 < h_curr):
            continue

        if regime_filter:
            h_1h = pm_1h.histogram(ih_1h)
            h_4h = pm_4h.histogram(ih_4h)
            if h_1h is None or h_4h is None:
                continue
            if h_1h <= 0 or h_4h <= 0:
                continue

        score_count = 0
        h_15m = pm_15m.histogram(i)
        h_1h  = pm_1h.histogram(ih_1h)
        h_4h  = pm_4h.histogram(ih_4h)
        if h_15m is not None and h_15m > 0:
            score_count += 1
        if h_1h is not None and h_1h > 0:
            score_count += 1
        if h_4h is not None and h_4h > 0:
            score_count += 1
        if score_count < score_threshold:
            continue

        entry_price = closes_15m[i]
        entry_ts    = sorted_15m_ts[i]
        hold_end_ts = entry_ts + hold_minutes * 60 * 1000

        exit_price = None
        exit_type  = None
        hold_expired = False
        for j in range(i + 1, n_15m):
            if sorted_15m_ts[j] > hold_end_ts:
                # Hold expired — exit at close of that candle
                exit_price = closes_15m[j]
                exit_type  = 'hold'
                break

            h_prev = pm_15m.histogram(j - 1)
            h_curr = pm_15m.histogram(j)
            flip = False
            if h_prev is not None and h_curr is not None:
                flip = (h_prev <= 0 < h_curr) or (h_prev >= 0 > h_curr)

            if flip:
                if exit_strategy == 'histogram_flip':
                    exit_price = closes_15m[j]
                    exit_type  = 'hist_flip'
                    break
                elif exit_strategy == 'any_flip':
                    j_1h = j // 4
                    j_4h = j // 16
                    h15m_prev, h15m_curr = h_prev, h_curr
                    h1h_prev  = pm_1h.histogram(j_1h - 1)
                    h1h_curr  = pm_1h.histogram(j_1h)
                    h4h_prev  = pm_4h.histogram(j_4h - 1)
                    h4h_curr  = pm_4h.histogram(j_4h)
                    any_flip = False
                    for hpr, hcu in [(h15m_prev, h15m_curr), (h1h_prev, h1h_curr), (h4h_prev, h4h_curr)]:
                        if hpr is not None and hcu is not None:
                            if (hpr <= 0 < hcu) or (hpr >= 0 > hcu):
                                any_flip = True
                                break
                    if any_flip:
                        exit_price = closes_15m[j]
                        exit_type  = 'any_flip'
                        break

        # If hold_minutes exceeded available data without a flip signal,
        # exit at last candle rather than silently dropping the trade
        if exit_price is None:
            exit_price = closes_15m[-1]
            exit_type  = 'hold_expired'

        pnl_pct = (exit_price - entry_price) / entry_price * 100
        trades.append({
            'direction': 'LONG', 'entry': entry_price, 'exit': exit_price,
            'pnl_pct': pnl_pct, 'exit_type': exit_type,
        })

    if not trades:
        return None

    wins       = [t for t in trades if t['pnl_pct'] > 0]
    losses     = [t for t in trades if t['pnl_pct'] <= 0]
    wr         = len(wins) / len(trades) * 100
    gross_win  = sum(t['pnl_pct'] for t in wins)
    gross_loss = abs(sum(t['pnl_pct'] for t in losses))
    pf         = gross_win / gross_loss if gross_loss > 0 else float('inf') if gross_win > 0 else 0
    total_pnl  = sum(t['pnl_pct'] for t in trades)

    dd = 0; peak = -9999
    for t in trades:
        peak = max(peak, t['pnl_pct'])
        dd   = min(dd, t['pnl_pct'] - peak)
    max_dd = dd

    return {
        'signals':         len(trades),
        'wins':            len(wins),
        'losses':          len(losses),
        'win_rate':        round(wr, 4),
        'profit_factor':   round(pf, 4),
        'total_pnl_pct':   round(total_pnl, 4),
        'max_drawdown_pct': round(max_dd, 4),
        'avg_pnl_pct':     round(total_pnl / len(trades), 4),
    }


def run_full_sweep(tokens=None, window_days=WINDOW_DAYS, parallel=True, workers=None):
    """Run full parameter sweep for tokens.

    Args:
        tokens: list of token symbols (default: monitored tokens)
        window_days: backtest window (default: WINDOW_DAYS)
        parallel: if True, test all configs per token in parallel (data fetched once per token)
        workers: number of worker processes (default: cpu_count())
    """
    if tokens is None:
        tokens = get_monitored_tokens()

    init_db()
    print(f'[sweep] Starting. {len(tokens)} tokens, {window_days}d window')

    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO backtest_runs
        (window_days, tokens_tested, configs_tried, best_token_count, notes)
        VALUES (?,?,?,?,?)""",
        (window_days, ','.join(tokens), 0, 0, 'auto sweep'))
    run_id = c.lastrowid
    conn.commit()

    grid = list(generate_grid())
    total_configs = len(grid)
    print(f'[sweep] {total_configs} configs per token')

    tokens_best = {}

    for token in tokens:
        print(f'\n[sweep] === {token} ===')
        best_for_token = None

        if parallel and len(grid) > 1:
            # Pre-fetch data ONCE per token so all 544 configs share the same candles
            symbol = token.upper() + 'USDT'
            klines_1h = fetch_1h_klines(symbol, window_days)
            klines_4h = fetch_4h_klines(symbol, window_days)
            klines_15m = fetch_15m_klines(symbol, window_days)

            if len(klines_1h) < 100 or len(klines_4h) < 20 or len(klines_15m) < 100:
                print(f'  [WARN] {token}: insufficient data ({len(klines_1h)} 1h, {len(klines_4h)} 4h, {len(klines_15m)} 15m)')
                conn.commit()
                continue

            # Real 15m candles from Binance paginated fetch
            sorted_15m_ts = sorted(int(k[0]) for k in klines_15m)
            closes_15m = [float(k[4]) for k in klines_15m]
            closes_1h = [float(k[4]) for k in klines_1h]
            closes_4h = [float(k[4]) for k in klines_4h]

            warmup = 65 + 28 + 5  # slow + signal + buffer
            if len(closes_15m) < warmup + 1 or len(closes_1h) < warmup + 1 or len(closes_4h) < 10:
                print(f'  [WARN] {token}: not enough candles after warmup')
                conn.commit()
                continue

            print(f'  [DATA] {token}: {len(closes_15m)} 15m, {len(closes_1h)} 1h, {len(closes_4h)} 4h candles')

            # Precompute MACD series so config testing is fast (O(1) histogram per config)
            pm_15m = PrecomputedMACD(closes_15m, 12, 55, 15)
            pm_1h  = PrecomputedMACD(closes_1h,  12, 55, 15)
            pm_4h  = PrecomputedMACD(closes_4h,  12, 55, 15)

            # Test all configs in parallel against the SAME pre-fetched data
            worker_args = [
                (token, fast, slow, sig, ex, ho, sc, rg,
                 closes_15m, closes_1h, closes_4h, sorted_15m_ts,
                 pm_15m, pm_1h, pm_4h, warmup, window_days)
                for fast, slow, sig, ex, ho, sc, rg in grid
            ]

            with Pool(processes=workers) as pool:
                results = pool.map(_test_config_worker_v2, worker_args)

            for idx, (_, params, res) in enumerate(results):
                (fast, slow, sig, ex, ho, sc, rg) = params
                if res is None:
                    continue

                # ── Persist every result for post-hoc analysis ──────────────────────
                c.execute("""INSERT INTO backtest_results
                    (run_id, token, fast, slow, signal, exit_strategy, hold_minutes,
                     score_threshold, regime_filter, signals, wins, losses,
                     win_rate, profit_factor, total_pnl_pct, max_drawdown_pct, avg_pnl_pct)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (run_id, token, fast, slow, sig, ex, ho, sc, int(rg),
                     res['signals'], res['wins'], res['losses'],
                     res['win_rate'], res['profit_factor'], res['total_pnl_pct'],
                     res['max_drawdown_pct'], res['avg_pnl_pct']))

                # Early prune: hopeless PF
                if res['signals'] >= 15 and res['profit_factor'] < 0.3:
                    continue

                if best_for_token is None or res['win_rate'] > best_for_token['win_rate']:
                    best_for_token = {**res,
                        'fast': fast, 'slow': slow, 'signal': sig,
                        'exit_strategy': ex, 'hold_minutes': ho,
                        'score_threshold': sc, 'regime_filter': rg}
                    if best_for_token['win_rate'] > 0:
                        print(f'  [{token}] New best @ {idx}: WR={res["win_rate"]:.1f}% PF={res["profit_factor"]:.3f} '
                              f'({fast},{slow},{sig}) hold={ho}m {ex} score={sc} reg={rg} n={res["signals"]}')
        else:
            # Sequential mode (for debugging or single-config testing)
            for idx, (fast, slow, sig, ex, ho, sc, rg) in enumerate(grid):
                if idx % 50 == 0 and idx > 0:
                    print(f'  [{token}] {idx}/{total_configs} configs tested')

                res = test_mtf_macd_config(
                    token, fast, slow, sig, ex, ho, sc, bool(rg), window_days, verbose=False
                )
                if res is None:
                    continue

                # ── Persist every result ───────────────────────────────────────────
                c.execute("""INSERT INTO backtest_results
                    (run_id, token, fast, slow, signal, exit_strategy, hold_minutes,
                     score_threshold, regime_filter, signals, wins, losses,
                     win_rate, profit_factor, total_pnl_pct, max_drawdown_pct, avg_pnl_pct)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (run_id, token, fast, slow, sig, ex, ho, sc, int(rg),
                     res['signals'], res['wins'], res['losses'],
                     res['win_rate'], res['profit_factor'], res['total_pnl_pct'],
                     res['max_drawdown_pct'], res['avg_pnl_pct']))

                # Early prune: hopeless PF
                if res['signals'] >= 15 and res['profit_factor'] < 0.3:
                    continue

                if best_for_token is None or res['win_rate'] > best_for_token['win_rate']:
                    best_for_token = {**res,
                        'fast': fast, 'slow': slow, 'signal': sig,
                        'exit_strategy': ex, 'hold_minutes': ho,
                        'score_threshold': sc, 'regime_filter': rg}
                    if best_for_token['win_rate'] > 0:
                        print(f'  [{token}] New best @ {idx}: WR={res["win_rate"]:.1f}% PF={res["profit_factor"]:.3f} '
                              f'({fast},{slow},{sig}) hold={ho}m {ex} score={sc} reg={rg} n={res["signals"]}')

                # Early skip if PF is hopeless after enough signals
                if idx >= 15 and best_for_token and best_for_token['profit_factor'] < 0.25:
                    print(f'  [{token}] Early stop: PF={best_for_token["profit_factor"]:.3f} < 0.25')
                    break

        if best_for_token:
            # Mark previous configs for this token as stale before inserting new best
            c.execute("UPDATE token_best_config SET is_stale=1 WHERE token=? AND is_stale=0",
                      (token,))
            c.execute("""INSERT INTO token_best_config
                (token, fast, slow, signal, exit_strategy, hold_minutes,
                 score_threshold, regime_filter, win_rate, profit_factor,
                 total_pnl_pct, signal_count, backtest_run_id, updated_at, is_stale)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,0)""",
                (token, best_for_token['fast'], best_for_token['slow'], best_for_token['signal'],
                 best_for_token['exit_strategy'], best_for_token['hold_minutes'],
                 best_for_token['score_threshold'], best_for_token['regime_filter'],
                 best_for_token['win_rate'], best_for_token['profit_factor'],
                 best_for_token['total_pnl_pct'], best_for_token['signals'], run_id))
            tokens_best[token] = best_for_token
            print(f'  [BEST] {token}: WR={best_for_token["win_rate"]:.1f}% PF={best_for_token["profit_factor"]:.3f} '
                  f'({best_for_token["fast"]},{best_for_token["slow"]},{best_for_token["signal"]}) '
                  f'hold={best_for_token["hold_minutes"]}m {best_for_token["exit_strategy"]} n={best_for_token["signals"]}')
        else:
            print(f'  [WARN] {token}: no valid configs found')

        conn.commit()

    c.execute("UPDATE backtest_runs SET configs_tried=?, best_token_count=? WHERE id=?",
             (total_configs, len(tokens_best), run_id))
    conn.commit()
    conn.close()

    print(f'\n[sweep] DONE. Run #{run_id}. Best configs for {len(tokens_best)}/{len(tokens)} tokens.')
    return run_id, tokens_best

# ── Quick update ────────────────────────────────────────────────────────────────
def quick_update(token, top_n=10):
    """Re-test top-N prior configs for a token. Update best if new winner."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT fast, slow, signal, exit_strategy, hold_minutes,
                  score_threshold, regime_filter
                  FROM backtest_results WHERE token=? AND signals >= 5
                  ORDER BY win_rate DESC LIMIT ?""", (token.upper(), top_n))
    prior_configs = c.fetchall()
    conn.close()

    if not prior_configs:
        print(f'[quick] No prior configs for {token} — running initial backtest')
        register_token(token)
        return run_full_sweep(tokens=[token])

    print(f'[quick] Re-testing {len(prior_configs)} prior configs for {token}')
    best = None
    for (fast, slow, sig, ex, ho, sc, rg) in prior_configs:
        res = test_mtf_macd_config(token, fast, slow, sig, ex, ho, sc, bool(rg))
        if res and res['signals'] >= 3:
            if best is None or res['win_rate'] > best['win_rate']:
                best = {**res, 'fast': fast, 'slow': slow, 'signal': sig,
                       'exit_strategy': ex, 'hold_minutes': ho,
                       'score_threshold': sc, 'regime_filter': rg}

    if best:
        conn = get_conn()
        c = conn.cursor()
        c.execute("""INSERT OR REPLACE INTO token_best_config
            (token, fast, slow, signal, exit_strategy, hold_minutes,
             score_threshold, regime_filter, win_rate, profit_factor,
             total_pnl_pct, signal_count, updated_at, is_stale)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,0)""",
            (token.upper(), best['fast'], best['slow'], best['signal'],
             best['exit_strategy'], best['hold_minutes'], best['score_threshold'],
             best['regime_filter'], best['win_rate'], best['profit_factor'],
             best['total_pnl_pct'], best['signals']))
        conn.commit()
        conn.close()
        print(f'[quick] {token} updated: WR={best["win_rate"]:.1f}% PF={best["profit_factor"]:.3f} '
              f'({best["fast"]},{best["slow"]},{best["signal"]}) hold={best["hold_minutes"]}m n={best["signals"]}')

    return best

# ── Report ────────────────────────────────────────────────────────────────────────
def print_report():
    init_db()
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT token, fast, slow, signal, exit_strategy, hold_minutes,
                  score_threshold, regime_filter, win_rate, profit_factor,
                  total_pnl_pct, signal_count, is_stale, updated_at
                  FROM token_best_config ORDER BY win_rate DESC""")
    rows = c.fetchall()
    conn.close()

    if not rows:
        print('No best configs yet. Run: mtf_macd_tuner.py add BTC SOL ETH AVAX')
        return

    print(f"\n{'TOKEN':<8} {'F':<3} {'S':<3} {'SIG':<4} {'EXIT':<12} {'HOLD':<6} {'THR':<4} {'REG':<4} {'WR%':<7} {'PF':<7} {'PnL%':<8} {'N':<5} {'STALE':<6}")
    print('-' * 100)
    for r in rows:
        stale = 'YES' if r[11] else ''
        print(f"{r[0]:<8} {r[1]:<3} {r[2]:<3} {r[3]:<4} {r[4]:<12} {r[5]:<6} {r[6]:<4} {r[7]:<4} "
              f"{r[8]:<7.2f} {r[9]:<7.3f} {r[10]:<8.2f} {r[11]:<5} {stale:<6}")

# ── CLI ────────────────────────────────────────────────────────────────────────────────
def main():
    init_db()
    action = sys.argv[1] if len(sys.argv) > 1 else 'help'

    if action == 'sweep':
        tokens = [t.upper() for t in sys.argv[2:]] if len(sys.argv) > 2 else []
        if tokens:
            print(f'[sweep] Targeted: {tokens}')
            run_full_sweep(tokens)
        else:
            tokens = get_monitored_tokens()
            if not tokens:
                print('[sweep] No tokens. Add with: mtf_macd_tuner.py add BTC SOL ETH AVAX LTC')
                return
            run_full_sweep(tokens)

    elif action == 'quick':
        if len(sys.argv) < 3:
            print('Usage: mtf_macd_tuner.py quick <TOKEN>')
            return
        quick_update(sys.argv[2])

    elif action == 'add':
        if len(sys.argv) < 3:
            print('Usage: mtf_macd_tuner.py add <TOKEN> [...]')
            return
        for t in sys.argv[2:]:
            register_token(t)
            print(f'[add] {t} registered — running quick backtest...')
            quick_update(t)

    elif action == 'report':
        print_report()

    elif action == 'test':
        print('[test] SOL quick backtest (known-good: 12,55,15 any_flip 120m score=2 reg=1)')
        res = test_mtf_macd_config('SOL', fast=12, slow=55, signal=15,
                                   exit_strategy='any_flip', hold_minutes=120,
                                   score_threshold=2, regime_filter=True,
                                   verbose=True)
        if res:
            print(f'[test] SOL: WR={res["win_rate"]:.1f}% PF={res["profit_factor"]:.3f} '
                  f'PnL={res["total_pnl_pct"]:.2f}% N={res["signals"]} '
                  f'wins={res["wins"]} losses={res["losses"]}')
        else:
            print('[test] SOL: returned None (insufficient data)')

    elif action == 'grid':
        grid = list(generate_grid())
        print(f'Total configs per token: {len(grid)}')
        print('Sample (first 5):')
        for g in grid[:5]:
            print(f'  {g}')

    elif action == 'help':
        print("""Usage: mtf_macd_tuner.py <action> [args]

Actions:
  sweep [TOKEN...]   Full 90d backtest. No args = all monitored tokens.
  quick <TOKEN>      Re-test top-10 configs for one token.
  add <TOKEN>...     Add token(s) + initial backtest.
  report            Print current best configs.
  test              Sanity check on SOL with known-good params.
  grid              Show param grid size.
  help              This help.
""")
    else:
        print(f'Unknown: {action}')
        main()

if __name__ == '__main__':
    main()
