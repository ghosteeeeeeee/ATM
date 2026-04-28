#!/usr/bin/env python3
"""
zscore_momentum.py — Price z-score momentum signals for Hermes.

Signal philosophy:
  Z-score measures how far current price deviates from its recent average.
  +threshold = strong established UPWARD momentum (price significantly above average)
  -threshold = strong established DOWNWARD momentum (price significantly below average)

Unlike mean-reversion (where |z| high = revert), here we treat high |z| as
CONFIRMATION of momentum direction — the move has inertia.

Architecture:
  backtest sweep  →  token_best_zscore_config  →  _run_zscore_momentum_signals()
  price_history (1m)                            signals_hermes_runtime.db

Per-token tuned lookback window (10-60 bars default range).
"""

import sys, os, sqlite3, time, math, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hermes_file_lock import FileLock

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'data')
sys.path.insert(0, SCRIPT_DIR)
from paths import CANDLES_DB  # price_history.db (candles.db is a symlink/alias)
_RUNTIME_DB = os.path.join(DATA_DIR, 'signals_hermes_runtime.db')
_TUNER_DB   = os.path.join(DATA_DIR, 'zscore_momentum_tuner.db')

# ── Default params (overridden by per-token tuned values) ────────────────────
DEFAULT_LOOKBACK  = 24       # bars for z-score window
DEFAULT_THRESHOLD = 2.0      # |z| threshold for signal
MIN_LOOKBACK      = 10
MAX_LOOKBACK      = 60
MIN_THRESHOLD     = 1.5
MAX_THRESHOLD     = 4.0
STEP_LOOKBACK     = 2
STEP_THRESHOLD    = 0.25
MIN_SIGNALS_FOR_TUNED = 15    # require this many historical signals before trusting tuned params
                                      # tokens with <15 get default params (conservative fallback)

# ── Volatility + momentum quality filters ─────────────────────────────────────
MIN_ATR_PCT_SIGNAL = 0.04     # block zscore signals when 14-bar ATR < 0.04% of price (too quiet)
                                      # 0.15 was too high for 1m data — would block ~86% of tokens incl. BTC/ETH/SOL
                                      # 0.04 allows BTC-class vol through while still blocking flat chop
MIN_SUSTAINED_BARS = 2        # |z| must exceed threshold on current bar AND at least 1 of prior 2 bars

# ── Signal source tag ─────────────────────────────────────────────────────────
SOURCE_TAG_LONG  = 'zscore-momentum+'
SOURCE_TAG_SHORT = 'zscore-momentum-'
SIGNAL_TYPE      = 'zscore_momentum'

# ─────────────────────────────────────────────────────────────────────────────
# Core z-score computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_zscore(values):
    """Compute rolling z-score. Returns (z_score, mean, std)."""
    if len(values) < 2:
        return None, None, None
    mean = statistics.mean(values)
    std = statistics.stdev(values)  # sample stdev
    if std == 0:
        return None, None, None
    z = (values[-1] - mean) / std
    return z, mean, std


def _fast_zscore(values):
    """Lightweight z-score (just the score). Returns None if insufficient data."""
    if len(values) < 2:
        return None
    mean = statistics.mean(values)
    std = statistics.stdev(values)
    if std == 0:
        return None
    return (values[-1] - mean) / std


# ─────────────────────────────────────────────────────────────────────────────
# ── DB: get price history from price_history (signals_hermes.db)
# ─────────────────────────────────────────────────────────────────────────────

_PRICE_DB = '/root/.hermes/data/signals_hermes.db'

def _get_1m_atr(token: str) -> float:
    """Fetch 14-bar 1m ATR as a percentage of current price. Returns 0 on error."""
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT open, high, low, close FROM candles_1m
            WHERE token = ? ORDER BY ts DESC LIMIT 14
        """, (token.upper(),))
        rows = cur.fetchall()
        conn.close()
        if len(rows) < 2:
            return 0.0
        closes = [r[3] for r in rows[::-1]]
        trs = []
        for o, h, l, c in rows[::-1]:
            tr = max(h - l, abs(h - o), abs(l - o))
            trs.append(tr)
        atr = sum(trs) / len(trs)
        last_close = closes[-1]
        return (atr / last_close * 100) if last_close else 0.0
    except Exception:
        return 0.0


def get_price_history(token: str, lookback_bars: int = 120) -> list:
    """Fetch recent close prices for token from price_history. Returns list of floats.
    price_history is updated every minute with live prices.
    Freshness guard: skip tokens with stale data (>2 min old).
    """
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=5)
        cur = conn.cursor()
        # Freshness check on price_history timestamp (seconds)
        cur.execute("SELECT MAX(timestamp) FROM price_history WHERE token = ?", (token.upper(),))
        row = cur.fetchone()
        if row and row[0] and (time.time() - row[0]) > 120:
            conn.close()
            return []
        # Get most recent lookback_bars prices, return oldest-first
        cur.execute("""
            SELECT price, timestamp FROM (
                SELECT price, timestamp FROM price_history
                WHERE token = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ) sub
            ORDER BY timestamp ASC
        """, (token.upper(), lookback_bars))
        rows = cur.fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []


def get_all_token_prices(lookback_bars: int = 200) -> dict:
    """Fetch price history for all tokens in price_history. Returns {token: [prices]}.
    Pre-loads all closes in one query for sweep speed.
    Freshness guard: skip stale tokens (>2 min old).
    """
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        cur = conn.cursor()
        cutoff = int(time.time()) - 120  # 2 min cutoff
        cur.execute("""
            SELECT token, price FROM price_history
            WHERE timestamp > ?
            ORDER BY token, timestamp ASC
        """, (cutoff,))
        rows = cur.fetchall()
        conn.close()
        result = {}
        for token, price in rows:
            if token not in result:
                result[token] = []
            result[token].append(price)
        return result
    except Exception as e:
        print(f"[zscore_momentum] get_all_token_prices error: {e}")
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# DB: tuner — store/load per-token best config
# ─────────────────────────────────────────────────────────────────────────────

def init_tuner_db():
    """Create the tuner DB table if it doesn't exist."""
    conn = sqlite3.connect(_TUNER_DB, timeout=10)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS token_best_zscore_config (
            token        TEXT PRIMARY KEY,
            lookback     INTEGER NOT NULL,
            threshold    REAL    NOT NULL,
            win_rate     REAL    NOT NULL,
            avg_pnl_pct  REAL    NOT NULL,
            signal_count INTEGER NOT NULL,
            total_long   INTEGER NOT NULL DEFAULT 0,
            total_short  INTEGER NOT NULL DEFAULT 0,
            updated_at   INTEGER NOT NULL
        )
    """)
    # Migration: add total_long/total_short if they don't exist (pre-existing table)
    try:
        cur.execute("""
            ALTER TABLE token_best_zscore_config
            ADD COLUMN total_long INTEGER NOT NULL DEFAULT 0
        """)
    except Exception:
        pass
    try:
        cur.execute("""
            ALTER TABLE token_best_zscore_config
            ADD COLUMN total_short INTEGER NOT NULL DEFAULT 0
        """)
    except Exception:
        pass
    conn.commit()
    conn.close()


def load_token_params() -> dict:
    """Load per-token tuned params from tuner DB. Returns {TOKEN: {lookback, threshold, ...}}."""
    init_tuner_db()
    try:
        conn = sqlite3.connect(_TUNER_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT token, lookback, threshold, win_rate, avg_pnl_pct, signal_count
            FROM token_best_zscore_config
        """)
        rows = cur.fetchall()
        conn.close()
        params = {}
        for row in rows:
            token, lb, th, wr, ap, sc = row
            params[token.upper()] = {
                'lookback': lb,
                'threshold': th,
                'win_rate': wr,
                'avg_pnl_pct': ap,
                'signal_count': sc,
            }
        return params
    except Exception as e:
        print(f"[zscore_momentum] load_token_params error: {e}")
        return {}


def save_token_params(token: str, lookback: int, threshold: float,
                      win_rate: float, avg_pnl_pct: float, signal_count: int,
                      total_long: int = 0, total_short: int = 0):
    """Save (or update) best config for a token."""
    init_tuner_db()
    try:
        conn = sqlite3.connect(_TUNER_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO token_best_zscore_config
              (token, lookback, threshold, win_rate, avg_pnl_pct, signal_count,
               total_long, total_short, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (token.upper(), lookback, threshold, win_rate, avg_pnl_pct, signal_count,
              total_long, total_short, int(time.time())))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[zscore_momentum] save_token_params error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Backtest sweep — find best lookback/threshold per token
# ─────────────────────────────────────────────────────────────────────────────

def _backtest_params(token: str, closes: list, lookback: int, threshold: float) -> dict:
    """
    Backtest z-score momentum signals on historical close data.
    Returns win_rate, avg_pnl_pct, signal_count.
    
    Strategy: 
      LONG  when z_score > +threshold
      SHORT when z_score < -threshold
      Exit: opposite signal OR fixed hold (lookback * 2 bars max)
    """
    if len(closes) < lookback + 10:
        return None
    
    wins_long = 0
    wins_short = 0
    total_long = 0
    total_short = 0
    pnl_long = 0.0
    pnl_short = 0.0
    
    # We need at least 2*lookback for meaningful backtest
    window = closes
    n = len(window)
    
    for i in range(lookback, n - 1):
        chunk = window[i - lookback:i]
        if len(chunk) < lookback:
            continue
        z, _, _ = compute_zscore(chunk)
        if z is None:
            continue
        
        signal = None
        if z > threshold:
            signal = 'LONG'
            total_long += 1
        elif z < -threshold:
            signal = 'SHORT'
            total_short += 1
        
        if signal is None:
            continue
        
        # Compute PnL: compare price at signal to price lookback bars later
        entry_price = window[i]
        hold = min(lookback * 2, n - i - 1)
        if hold < 1:
            continue
        exit_price = window[i + hold]
        
        if signal == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price * 100
            pnl_long += pnl_pct
            if pnl_pct > 0:
                wins_long += 1
        else:  # SHORT
            pnl_pct = (entry_price - exit_price) / entry_price * 100
            pnl_short += pnl_pct
            if pnl_pct > 0:
                wins_short += 1
    
    total = total_long + total_short
    if total == 0:
        return None
    
    wins = wins_long + wins_short
    wr = (wins / total) * 100 if total > 0 else 0
    avg_pnl = (pnl_long + pnl_short) / total if total > 0 else 0
    signal_count = total
    
    return {
        'lookback': lookback,
        'threshold': threshold,
        'win_rate': wr,
        'avg_pnl_pct': avg_pnl,
        'signal_count': signal_count,
        'total_long': total_long,
        'total_short': total_short,
    }


def run_sweep(token: str = None, lookbacks = None, thresholds = None) -> dict:
    """
    Run full param sweep. If token is None, sweep all tokens in price_history.
    
    Returns dict of best params per token: {TOKEN: {lookback, threshold, win_rate, ...}}
    """
    if lookbacks is None:
        lookbacks = list(range(MIN_LOOKBACK, MAX_LOOKBACK + 1, STEP_LOOKBACK))
    if thresholds is None:
        thresholds = [round(x, 2) for x in 
                      [round(x, 2) for x in 
                       [t * STEP_THRESHOLD for t in range(int(MIN_THRESHOLD/STEP_THRESHOLD), 
                                                           int(MAX_THRESHOLD/STEP_THRESHOLD) + 1)]]]
    
    init_tuner_db()
    
    # Load all price data
    all_prices = get_all_token_prices(lookback_bars=MAX_LOOKBACK * 4)
    if not all_prices:
        print("[zscore_momentum] No price data found in price_history")
        return {}
    
    targets = {token.upper(): all_prices[token]} if token else all_prices
    
    results = {}
    for tok, closes in targets.items():
        if len(closes) < MAX_LOOKBACK + 10:
            continue
        
        best = None
        for lb in lookbacks:
            for th in thresholds:
                res = _backtest_params(tok, closes, lb, th)
                if res is None:
                    continue
                sc = res['signal_count']
                # Score: prioritize WR >= 55% AND avg_pnl > 0, then by signal count
                # Require minimum 15 signals for reliability
                if sc < MIN_SIGNALS_FOR_TUNED:
                    continue
                score = res['win_rate'] + (25 if res['avg_pnl_pct'] > 0 else 0)
                if best is None or score > best['_score']:
                    res['_score'] = score
                    best = res
        
        if best:
            # Save to tuner DB with LONG/SHORT breakdown
            save_token_params(tok, best['lookback'], best['threshold'],
                              best['win_rate'], best['avg_pnl_pct'], best['signal_count'],
                              total_long=best.get('total_long', 0),
                              total_short=best.get('total_short', 0))
            results[tok] = best
            print(f"  {tok}: lookback={best['lookback']}, thresh={best['threshold']}, "
                  f"WR={best['win_rate']:.1f}%, avg_pnl={best['avg_pnl_pct']:.2f}%, "
                  f"n={best['signal_count']}")
    
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Standalone signal generation (called from signal_gen.py or pipeline)
# ─────────────────────────────────────────────────────────────────────────────

# Module-level cache — reset each run
_TOKEN_PARAMS_CACHE = None

def _load_token_params_cached():
    global _TOKEN_PARAMS_CACHE
    if _TOKEN_PARAMS_CACHE is not None:
        return _TOKEN_PARAMS_CACHE
    _TOKEN_PARAMS_CACHE = load_token_params()
    return _TOKEN_PARAMS_CACHE


def clear_cache():
    """Call this at the start of each pipeline run to force re-load from DB."""
    global _TOKEN_PARAMS_CACHE
    _TOKEN_PARAMS_CACHE = None


def _get_open_positions():
    """Get open positions from runtime DB."""
    try:
        conn = sqlite3.connect(_RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT token, direction FROM positions 
            WHERE status = 'OPEN'
        """)
        rows = cur.fetchall()
        conn.close()
        return {(r[0].upper() if r[0] else ''): r[1].upper() for r in rows}
    except Exception:
        return {}


def _recent_signal_exists(token: str, minutes: int = 15) -> bool:
    """Check if a zscore_momentum signal was emitted for this token recently."""
    try:
        conn = sqlite3.connect(_RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT 1 FROM signals
            WHERE token = ? AND signal_type = ?
            AND created_at > datetime('now', '-? minutes')
            LIMIT 1
        """, (token.upper(), SIGNAL_TYPE, minutes))
        exists = cur.fetchone() is not None
        conn.close()
        return exists
    except Exception:
        return False


def _is_delisted_or_blacklist(token: str) -> bool:
    """Quick check for delisted/blacklist — tries to avoid heavy imports."""
    try:
        from hyperliquid_exchange import is_delisted
        return is_delisted(token.upper())
    except Exception:
        return False


def _get_latest_prices() -> dict:
    """Get latest prices from signal_schema (same source as other scanners)."""
    try:
        from signal_schema import get_all_latest_prices
        prices = get_all_latest_prices()
        return prices if prices else {}
    except Exception:
        return {}


def _run_zscore_momentum_signals(prices_dict: dict = None) -> int:
    """
    Generate z-score momentum signals.
    
    LONG:  z_score > +threshold  (price significantly above average — upward momentum)
    SHORT: z_score < -threshold (price significantly below average — downward momentum)
    
    Returns: number of signals written to DB.
    
    Usage:
        from zscore_momentum import _run_zscore_momentum_signals
        added = _run_zscore_momentum_signals()
    """
    clear_cache()
    token_params = _load_token_params_cached()
    
    # Use passed prices_dict or fetch fresh
    if prices_dict is None:
        prices_dict = _get_latest_prices()
    
    open_pos = _get_open_positions()
    added = 0
    
    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue
        price = data.get('price')
        if not price or price <= 0:
            continue
        
        # Skip if already in a position
        if token.upper() in open_pos:
            continue
        
        # Skip if recently signaled
        if _recent_signal_exists(token, minutes=15):
            continue
        
        # Skip blacklist/delisted
        if _is_delisted_or_blacklist(token):
            continue

        # Get per-token params (or defaults)
        p = token_params.get(token.upper())
        tok_signal_count = 0
        if p is not None:
            tok_signal_count = p.get('signal_count', 0)

        # Fall back to defaults for tokens without enough history
        if p is None or tok_signal_count < MIN_SIGNALS_FOR_TUNED:
            lookback = DEFAULT_LOOKBACK
            threshold = DEFAULT_THRESHOLD
            wr = 50.0
            confidence = 85.0  # standalone — no confluence to boost it, needs high confidence
        else:
            lookback = p.get('lookback', DEFAULT_LOOKBACK)
            threshold = p.get('threshold', DEFAULT_THRESHOLD)
            wr = p.get('win_rate', 50.0)
            confidence = min(95.0, max(80.0, wr))  # 80-95 range — standalone strength

        # Fetch price history
        closes = get_price_history(token, lookback_bars=lookback + 10)
        if len(closes) < lookback + 2:
            continue

        # ── Filter (A): Volatility floor — block in ultra-low vol conditions ──────
        atr_pct = _get_1m_atr(token)
        if atr_pct < MIN_ATR_PCT_SIGNAL:
            continue  # market too quiet — z-score is noise

        # Compute z-score on the lookback window
        chunk = closes[-lookback:]
        z, mean, std = compute_zscore(chunk)
        if z is None:
            continue

        # ── Filter (B): Sustained momentum — require |z| > threshold on current bar
        # AND at least one of the prior (MIN_SUSTAINED_BARS - 1) bars as well
        # This filters out one-bar spikes in choppy markets
        if abs(z) > threshold:
            has_prior = False
            for offset in range(1, MIN_SUSTAINED_BARS):
                if len(closes) >= lookback + offset:
                    # prev_chunk = the [lookback]-bar window ending at bar -(offset+1)
                    # e.g. offset=1 → closes[-lookback-1:-1] = bars ending at closes[-2] (bar immediately before current)
                    prev_chunk = closes[-lookback - offset:-offset]
                    if len(prev_chunk) == lookback:
                        prev_z, _, _ = compute_zscore(prev_chunk)
                        if prev_z is not None and abs(prev_z) > threshold:
                            has_prior = True
                            break
            if not has_prior:
                continue  # one-bar spike — not sustained enough

        # Determine direction
        direction = None
        source = None

        if z > threshold:
            direction = 'LONG'
            source = SOURCE_TAG_LONG
        elif z < -threshold:
            direction = 'SHORT'
            source = SOURCE_TAG_SHORT

        if direction is None:
            continue

        # Import add_signal locally to avoid circular issues
        try:
            from signal_schema import add_signal, price_age_minutes
            age = price_age_minutes(token)
            if age > 10:
                continue
        except Exception as e:
            print(f"[zscore_momentum] signal_schema import error: {e}")
            continue
        
        # Write signal
        try:
            from signal_schema import add_signal as _add_sig
            sid = _add_sig(
                token=token,
                direction=direction,
                signal_type=SIGNAL_TYPE,
                source=source,
                confidence=round(confidence, 1),
                value=float(abs(z)),
                price=price,
                exchange='hyperliquid',
                timeframe='1m',
                z_score=float(z),
                z_score_tier=None,
            )
            if sid:
                added += 1
                # Set a short cooldown to avoid spam
                try:
                    from signal_schema import set_cooldown as _set_cd
                    _set_cd(token, direction, hours=0.5)
                except Exception:
                    pass
        except Exception as e:
            print(f"[zscore_momentum] add_signal error for {token}: {e}")
    
    return added


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point (for running the tuner sweep standalone)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Z-score momentum signal tuner + runner')
    parser.add_argument('--sweep', action='store_true', help='Run parameter sweep for all tokens')
    parser.add_argument('--token', type=str, default=None, help='Sweep a specific token only')
    parser.add_argument('--run-signals', action='store_true', help='Run signal generation')
    parser.add_argument('--lookback', type=int, default=DEFAULT_LOOKBACK, help='Lookback window (bars)')
    parser.add_argument('--threshold', type=float, default=DEFAULT_THRESHOLD, help='Z-score threshold')
    args = parser.parse_args()
    
    if args.sweep:
        print(f"[zscore_momentum] Starting sweep... (lookbacks {MIN_LOOKBACK}-{MAX_LOOKBACK}, "
              f"thresholds {MIN_THRESHOLD}-{MAX_THRESHOLD})")
        results = run_sweep(token=args.token)
        print(f"[zscore_momentum] Sweep complete. Tuned {len(results)} tokens.")
    
    if args.run_signals:
        print("[zscore_momentum] Running signal generation...")
        added = _run_zscore_momentum_signals()
        print(f"[zscore_momentum] Signals generated: {added}")
