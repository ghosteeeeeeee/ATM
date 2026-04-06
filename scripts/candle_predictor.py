#!/usr/bin/env python3
"""
Candle Predictor for Hermes Trading System
Uses local Ollama LLM to predict next 4h candle direction per token.
Integrated into signal pipeline — reads from signal_gen momentum data,
writes predictions to signals_hermes_runtime.db for scoring integration.

FIXED v2 (2026-04-02):
  - Added HL funding rates to prompt context
  - Added predictions.db accuracy stats per token and momentum_state
  - Added INVERSION LOGIC: invert DOWN predictions when direction accuracy < 45%
  - Fixed RSI/MACD to use proper candle OHLC data (aggregated from price_history)
  - Added volume estimation from price_history timestamp clustering + HL recentTrades
  - Added momentum_state accuracy bias to prompt
  - Added HL bid-ask spread from orderbook
  - Proper candle-aggregated close prices for all technical indicators
"""
import sqlite3, json, time, os, sys, subprocess, statistics, argparse
from collections import defaultdict
import wandb

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
HERMES_DIR   = os.path.dirname(SCRIPT_DIR)
RUNTIME_DB   = os.path.join(HERMES_DIR, 'data', 'signals_hermes_runtime.db')
PRICES_DB    = os.path.join(HERMES_DIR, 'data', 'signals_hermes.db')
PREDICTIONS_DB = os.path.join(HERMES_DIR, 'data', 'predictions.db')
LOCK_FILE    = '/tmp/candle-predictor.lock'
LOG_FILE     = '/var/log/candle-predictor.log'
OLLAMA_URL   = 'http://127.0.0.1:11434/api/generate'
MODEL        = 'qwen2.5:1.5b'
TOP_TOKENS=['BTC','ETH','SOL','AVAX','DOGE','XRP','ADA','DOT','LINK','MATIC',
                'MATIC','LTC','UNI','ATOM','XLM','ETC','ALGO','VET','FIL','THETA',
                'AAVE','MKR','COMP','SNX','YFI','SUSHI','CRV','RUNE','KAVA','BAT']
# ── Runtime config (set by CLI args) ──────────────────────────────────────────
CANDLE_MINUTES = 240   # default 4h; override with --interval 15/60/240
MINIMAX_CHECK   = False  # enable with --minimax (post-prediction check with minimax API)
INVERSION_THRESHOLD = 0.40  # invert if direction accuracy < 40% in this momentum_state

# Token watch list: coins added when traded, persisted to this file
WATCH_LIST_FILE = '/root/.hermes/data/candle-watched-tokens.json'

# Token-specific overrides discovered by candle_tuner.py (auto-updated hourly)
# Format: {TOKEN: {'direction': X, 'threshold': Y}} — applies token-specific inversion
TOKEN_ACC_OVERRIDES={
    # 'MATIC': {'direction': 'DOWN', 'always_invert': True},  # 0% accuracy on 58 predictions
    'MATIC': {'direction': 'DOWN', 'always_invert': True},
    'MKR': {'direction': 'DOWN', 'always_invert': True},
}

# Regime-specific DOWN accuracy (from 4188 predictions, 2026-04-05)
# Used to set dynamic inversion thresholds per state
REGIME_DOWN_ACCURACY = {
    'bullish':  89.0,  # DOWN is great in bullish
    'bearish':  38.0,  # DOWN is weak in bearish
    'neutral':  37.0,  # DOWN is weak in neutral
}


def log(msg, level='INFO'):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] [{level}] {msg}")
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{ts}] [{level}] {msg}\n")
    except:
        pass


def acquire_lock():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return False
        except:
            pass
    with open(LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))
    return True


# ── DB helpers ────────────────────────────────────────────────────────────────
def get_runtime_db():
    return sqlite3.connect(RUNTIME_DB, timeout=10)

def get_prices_db():
    return sqlite3.connect(PRICES_DB, timeout=10)


def init_predictions_db():
    """Create predictions table if not exists."""
    os.makedirs(os.path.dirname(PREDICTIONS_DB), exist_ok=True)
    conn = sqlite3.connect(PREDICTIONS_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT NOT NULL,
            direction TEXT NOT NULL,
            confidence INTEGER,
            predicted_move_pct REAL,
            actual_move_pct REAL,
            correct BOOLEAN,
            prediction_time INTEGER,
            candle_time INTEGER,
            price_at_prediction REAL,
            momentum_state TEXT,
            regime TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Migration: add was_inverted column if upgrading from old schema
    try:
        cur.execute("ALTER TABLE predictions ADD COLUMN was_inverted BOOLEAN DEFAULT 0")
        conn.commit()
        log("  [migration] added was_inverted column")
    except sqlite3.OperationalError:
        pass  # column already exists
    cur.execute("CREATE INDEX IF NOT EXISTS idx_token_time ON predictions(token, prediction_time)")
    return conn


# ── Hyperliquid Data Helpers (parallelized) ───────────────────────────────────
def _fetch_funding(token):
    """Worker: fetch funding rate for one token."""
    try:
        from hyperliquid_exchange import _hl_info
        end = int(time.time() * 1000)
        start = end - (8 * 3600 * 1000)
        fh = _hl_info({"type": "fundingHistory", "coin": token, "startTime": start, "endTime": end})
        if fh and isinstance(fh, list) and len(fh) > 0:
            last = fh[-1]
            return token, float(last.get('fundingRate', 0) or 0)
    except Exception:
        pass
    return token, None


def _fetch_orderbook(token):
    """Worker: fetch l2Book spread for one token."""
    try:
        from hyperliquid_exchange import _hl_info
        ob = _hl_info({"type": "l2Book", "coin": token})
        if ob and 'levels' in ob and len(ob['levels']) >= 2:
            asks = ob['levels'][0] or []
            bids = ob['levels'][1] or []
            if asks and bids:
                ask_px = float(asks[0][0])
                bid_px = float(bids[0][0])
                mid = (ask_px + bid_px) / 2
                spread_bps = (ask_px - bid_px) / mid * 10000 if mid > 0 else 0
                return token, round(spread_bps, 2), mid
    except Exception:
        pass
    return token, None, None


def _fetch_volume(token):
    """Worker: estimate volume ratio from recentTrades."""
    try:
        from hyperliquid_exchange import _hl_info
        trades = _hl_info({"type": "recentTrades", "coin": token})
        if trades and isinstance(trades, list) and len(trades) >= 4:
            sizes = [abs(float(t.get('sz', 0))) for t in trades[:8]]
            recent = sum(sizes[:4]) / 4
            older = sum(sizes[4:]) / max(len(sizes[4:]), 1)
            return token, round(recent / older, 2) if older > 0 else 1.0
    except Exception:
        pass
    return token, None


def get_hl_data():
    """
    Fetch HL market data in parallel: funding rates, orderbook spread, volume.
    All network calls run concurrently — total time ~= slowest single call (~1-2s).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    funding_tokens = ['BTC', 'ETH', 'SOL', 'AVAX', 'XRP', 'ADA', 'DOGE', 'DOT', 'LINK']
    orderbook_tokens = ['BTC', 'ETH', 'SOL']

    result = {}

    with ThreadPoolExecutor(max_workers=12) as pool:
        # Submit all tasks
        funding_futs = {pool.submit(_fetch_funding, t): t for t in funding_tokens}
        ob_futs = {pool.submit(_fetch_orderbook, t): t for t in orderbook_tokens}
        vol_futs = {pool.submit(_fetch_volume, t): t for t in funding_tokens}

        for fut in as_completed(funding_futs):
            tok, rate = fut.result()
            if rate is not None:
                result[tok] = result.get(tok, {})
                result[tok]['funding_rate'] = rate

        for fut in as_completed(ob_futs):
            tok, spread, mid = fut.result()
            if spread is not None:
                result[tok] = result.get(tok, {})
                result[tok]['spread_bps'] = spread
                result[tok]['mid_price'] = mid

        for fut in as_completed(vol_futs):
            tok, vol_ratio = fut.result()
            if vol_ratio is not None:
                result[tok] = result.get(tok, {})
                result[tok]['volume_ratio'] = vol_ratio

    return result


# ── OHLCV Aggregation from price_history ───────────────────────────────────────
def build_ohlcv(token, candle_minutes=240):
    """
    Aggregate price_history (timestamp, price) into OHLCV candles.
    Groups rows into [candle_minutes]-minute buckets.
    Returns list of (open, high, low, close, volume) tuples, oldest first.
    """
    conn = get_prices_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT timestamp, price FROM price_history
        WHERE token=? ORDER BY timestamp ASC
    """, (token,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return []

    # Group into candle_minutes buckets
    candles = {}
    for ts, price in rows:
        bucket = int(ts // (candle_minutes * 60)) * (candle_minutes * 60)
        if bucket not in candles:
            candles[bucket] = {'open': price, 'high': price, 'low': price, 'close': price, 'count': 1}
        else:
            c = candles[bucket]
            c['high'] = max(c['high'], price)
            c['low'] = min(c['low'], price)
            c['close'] = price
            c['count'] += 1

    result = sorted([
        (v['open'], v['high'], v['low'], v['close'], v['count'])
        for v in candles.values()
    ])
    return result


def estimate_volume(token):
    """
    Estimate volume from price_history timestamp clustering.
    Groups ticks into 1-minute buckets and counts ticks as proxy for volume.
    Returns: (recent_avg_ticks_per_min, older_avg_ticks_per_min, volume_ratio)
    """
    conn = get_prices_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT timestamp FROM price_history
        WHERE token=? ORDER BY timestamp DESC LIMIT 480
    """, (token,))
    rows = cur.fetchall()
    conn.close()

    if not rows or len(rows) < 30:
        return None, None, None

    timestamps = [r[0] for r in rows]

    # Count ticks per minute for last 60 minutes vs previous 60 minutes
    now = timestamps[0]
    bucket_size = 60  # 1-minute buckets

    def ticks_per_min(ts_list, window_min):
        buckets = defaultdict(int)
        for ts in ts_list:
            if now - ts <= window_min * 60:
                bucket = int(ts // bucket_size) * bucket_size
                buckets[bucket] += 1
        if not buckets:
            return 0
        return sum(buckets.values()) / len(buckets)

    recent_avg = ticks_per_min(timestamps, 60)
    older_avg  = ticks_per_min(timestamps, 120)
    if older_avg > 0:
        ratio = recent_avg / older_avg
    else:
        ratio = 1.0

    return round(recent_avg, 2), round(older_avg, 2), round(ratio, 2)


# ── Technical Indicators (correct OHLCV-based) ───────────────────────────────
def compute_rsi_ohlc(closes, period=14):
    """RSI using proper OHLCV close prices (Wilder smoothing)."""
    if len(closes) < period + 2:
        return None
    deltas = [closes[i+1] - closes[i] for i in range(len(closes)-1)]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period-1) + gains[i]) / period
        avg_loss = (avg_loss * (period-1) + losses[i]) / period
    if avg_loss == 0:
        return 85.0
    return round(100 - (100 / (1 + avg_gain / avg_loss)), 2)


def compute_macd_ohlc(closes, fast=12, slow=26, signal=9):
    """
    Proper MACD using EMA of OHLCV close prices.
    Returns (macd_line, signal_line, histogram)
    """
    if len(closes) < slow + signal:
        return None, None, None

    def ema(data, period):
        k = 2 / (period + 1)
        val = sum(data[:period]) / period
        for p in data[period:]:
            val = p * k + val * (1 - k)
        return val

    ef = ema(closes, fast)
    es = ema(closes, slow)
    macd_line = ef - es

    # Compute signal line (EMA of MACD values)
    macd_values = []
    for i in range(slow, len(closes)):
        ef_i = ema(closes[max(0, i-fast+1):i+1], fast) if i+1 >= fast else None
        es_i = ema(closes[max(0, i-slow+1):i+1], slow) if i+1 >= slow else None
        if ef_i is not None and es_i is not None:
            macd_values.append(ef_i - es_i)

    if len(macd_values) < signal:
        return round(macd_line, 6), None, None

    signal_line = ema(macd_values[-signal:], signal) if len(macd_values) >= signal else ema(macd_values, len(macd_values))
    hist = macd_line - signal_line
    return round(macd_line, 6), round(signal_line, 6), round(hist, 6)


# ── Multi-Timeframe MACD Crossover Detection ──────────────────────────────────
def _macd_crossover_worker(args):
    """Worker: compute MACD on one timeframe. Returns (tf_name, macd, signal, hist, direction)."""
    tf_name, token, candle_minutes = args
    try:
        ohlcv = build_ohlcv(token, candle_minutes=candle_minutes)
        if len(ohlcv) < 40:
            return tf_name, None, None, None, None
        closes = [c[3] for c in ohlcv]
        macd_line, sig, hist = compute_macd_ohlc(closes)
        if macd_line is None or sig is None:
            return tf_name, None, None, None, None
        direction = 'BULLISH' if hist > 0 else 'BEARISH'
        return tf_name, macd_line, sig, hist, direction
    except Exception:
        return tf_name, None, None, None, None


def compute_mtf_macd(token):
    """
    Compute MACD across 3 timeframes in parallel and detect crossovers.
    Returns dict with per-TF data and crossover signals.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    timeframes = [
        ('4H',  token, 240),
        ('1H',  token, 60),
        ('15M', token, 15),
    ]

    tf_data = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(_macd_crossover_worker, tf): tf[0] for tf in timeframes}
        for fut in as_completed(futures):
            tf_name, macd_line, sig, hist, direction = fut.result()
            if macd_line is not None:
                tf_data[tf_name] = {
                    'macd': macd_line,
                    'signal': sig,
                    'hist': hist,
                    'direction': direction,
                }

    # Detect crossovers between timeframes
    crossovers = []
    signals = []

    # Check if higher TF MACD aligns with lower TF
    tf_order = ['15M', '1H', '4H']
    bullish_align = 0
    bearish_align = 0
    for tf in tf_order:
        if tf in tf_data and tf_data[tf]['direction']:
            if tf_data[tf]['direction'] == 'BULLISH':
                bullish_align += 1
            else:
                bearish_align += 1

    # Cross-up: lower TF histogram crosses above signal while higher TF is already bullish
    # Cross-down: lower TF histogram crosses below signal while higher TF is already bearish
    if '1H' in tf_data and '4H' in tf_data:
        h4 = tf_data['4H']['hist']
        h1 = tf_data['1H']['hist']
        if h4 > 0 and h1 > 0:
            signals.append('BULLISH_CONFIRMED')
        elif h4 < 0 and h1 < 0:
            signals.append('BEARISH_CONFIRMED')
        elif h4 > 0 > h1:
            signals.append('1H_MACD_BEARISH_DIVERGENCE')
        elif h4 < 0 < h1:
            signals.append('1H_MACD_BULLISH_DIVERGENCE')

    if '15M' in tf_data and '1H' in tf_data:
        h15 = tf_data['15M']['hist']
        h1 = tf_data['1H']['hist']
        if h1 > 0 and h15 > 0:
            signals.append('MTF_BULLISH_ALIGN')
        elif h1 < 0 and h15 < 0:
            signals.append('MTF_BEARISH_ALIGN')
        elif h1 > 0 > h15:
            signals.append('15M_MACD_PULLBACK')
        elif h1 < 0 < h15:
            signals.append('15M_MACD_RALLY')

    # Strength: how many TFs agree
    alignment = f"{bullish_align}/3 bullish TFs" if bullish_align > bearish_align else \
                f"{bearish_align}/3 bearish TFs" if bearish_align > bullish_align else "MIXED/NEUTRAL"

    return {
        'timeframes': tf_data,
        'signals': signals if signals else ['NO_SIGNAL'],
        'alignment': alignment,
        'bullish_count': bullish_align,
        'bearish_count': bearish_align,
    }


def _get_mtf_macd_summary(mtf):
    """Format MTF MACD data into a readable string for the prompt."""
    if not mtf or not mtf.get('timeframes'):
        return "MTF MACD: insufficient data"

    lines = ["MTF MACD (per timeframe):"]
    for tf in ['4H', '1H', '15M']:
        if tf in mtf['timeframes']:
            d = mtf['timeframes'][tf]
            sign = '+' if d['hist'] >= 0 else ''
            lines.append(
                f"  {tf}: MACD={d['macd']:+.4f} Signal={d['signal']:+.4f} "
                f"Hist={sign}{d['hist']:+.4f} → {d['direction']}"
            )

    signals_str = ', '.join(mtf['signals']) if mtf['signals'] else 'NONE'
    lines.append(f"MTF Alignment: {mtf['alignment']}")
    lines.append(f"Crossover Signals: {signals_str}")

    return '\n'.join(lines)


# ── Learning Loop: Read predictions.db for accuracy stats ───────────────────
def get_accuracy_stats(conn, token, momentum_state=None):
    """
    Get direction-specific accuracy for a token, optionally filtered by momentum_state.
    Returns dict: {direction: (accuracy, total_predictions, correct_count)}
    """
    cur = conn.cursor()

    # Overall per-token accuracy
    cur.execute("""
        SELECT direction,
               COUNT(*) as n,
               SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END) as correct,
               SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as acc
        FROM predictions
        WHERE token=? AND correct IS NOT NULL
        GROUP BY direction
    """, (token,))
    overall = {r[0]: {'n': r[1], 'correct': r[2], 'acc': r[3]} for r in cur.fetchall()}

    # Per-momentum_state accuracy
    state_stats = {}
    if momentum_state:
        cur.execute("""
            SELECT direction,
                   COUNT(*) as n,
                   SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END) as correct,
                   SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as acc
            FROM predictions
            WHERE token=? AND correct IS NOT NULL AND momentum_state=?
            GROUP BY direction
        """, (token, momentum_state))
        state_stats = {r[0]: {'n': r[1], 'correct': r[2], 'acc': r[3]} for r in cur.fetchall()}

    return {'overall': overall, 'by_state': state_stats}


def decide_inversion(token, direction, momentum_state, conn):
    """
    Decide whether to INVERT a prediction based on historical accuracy.
    Returns (final_direction, was_inverted, reason).

    FIX (2026-04-06): Use INVERSION_THRESHOLD properly, fix UP inversion logic.
    - INVERSION_THRESHOLD (0.40): invert if direction accuracy < this threshold
    - UP: invert only if token-specific UP accuracy is < 40% with 20+ predictions
    - DOWN: invert if state-specific or overall DOWN accuracy < threshold
    - TOKEN_ACC_OVERRIDES: per-token discovered accuracy problems (from candle_tuner)
    - REGIME_DOWN_ACCURACY: data-backed state-specific DOWN accuracy
    """
    # ── TOKEN-SPECIFIC OVERRIDE ──────────────────────────────────────────────
    # candle_tuner.py discovers tokens with <35% accuracy on 30+ predictions
    # and adds them here. This overrides all other logic.
    override = TOKEN_ACC_OVERRIDES.get(token.upper())
    if override and override.get('always_invert') and direction == override.get('direction'):
        return 'UP' if direction == 'DOWN' else 'DOWN', True, \
               f"TOKEN_OVERRIDE: {token} has historically terrible accuracy — always invert"

    stats = get_accuracy_stats(conn, token, momentum_state)
    state_data = stats.get('by_state', {})
    overall_data = stats.get('overall', {})

    state_acc = state_data.get(direction, {}).get('acc', None)
    overall_dir_acc = overall_data.get(direction, {}).get('acc', None)
    state_sample = state_data.get(direction, {}).get('n', 0)
    overall_sample = overall_data.get(direction, {}).get('n', 0)

    # Use configurable INVERSION_THRESHOLD instead of hardcoded values
    threshold_pct = int(INVERSION_THRESHOLD * 100)  # 0.40 -> 40

    # ── RULE 1: INVERT UP only if historically terrible ──────────────────────
    # "Never invert UP" was too aggressive — per-token UP can be 0%
    # Only invert UP if we have enough data showing it's genuinely bad
    if direction == 'UP':
        # Check state-specific UP accuracy
        if state_acc is not None and state_sample >= 20 and state_acc < threshold_pct:
            return 'DOWN', True, f"UP in {momentum_state}: acc={state_acc:.1f}% < {threshold_pct}% (n={state_sample}), invert to DOWN"
        # Check overall UP accuracy
        if overall_dir_acc is not None and overall_sample >= 20 and overall_dir_acc < threshold_pct:
            return 'DOWN', True, f"UP overall: acc={overall_dir_acc:.1f}% < {threshold_pct}% (n={overall_sample}), invert to DOWN"
        # Not enough data or accuracy is OK — keep UP
        return 'UP', False, f"UP acc={overall_dir_acc:.1f}% >= {threshold_pct}% or n={overall_sample} < 20, keep UP"

    # ── RULE 2: INVERT DOWN if accuracy is below threshold ─────────────────────
    if direction == 'DOWN':
        # Get regime-specific DOWN accuracy (data-backed)
        regime_acc = REGIME_DOWN_ACCURACY.get(momentum_state, 35.0)

        # Dynamic threshold: if state data exists, weight it
        if state_acc is not None and state_sample >= 10:
            # Blend regime baseline with state-specific data
            blend = min(0.8, state_sample / 100)
            effective_acc = regime_acc * (1 - blend) + state_acc * blend
            # Adjust threshold based on delta from regime baseline
            threshold = threshold_pct - (effective_acc - regime_acc) / 2
            threshold = max(25, min(55, threshold))  # clamp 25-55%
        else:
            threshold = threshold_pct

        # Invert if state accuracy is below threshold
        if state_acc is not None and state_sample >= 10:
            if state_acc < threshold:
                return 'UP', True, f"DOWN in {momentum_state}: acc={state_acc:.1f}% < {threshold:.0f}%, invert to UP"
            return 'DOWN', False, f"DOWN in {momentum_state}: acc={state_acc:.1f}% >= {threshold:.0f}%, keep DOWN"
        # Fall back to overall accuracy
        elif overall_dir_acc is not None and overall_dir_acc < threshold_pct:
            return 'UP', True, f"DOWN overall: acc={overall_dir_acc:.1f}% < {threshold_pct}% — invert to UP"
        elif overall_dir_acc is not None:
            return 'DOWN', False, f"DOWN overall: acc={overall_dir_acc:.1f}% >= {threshold_pct}%, keep DOWN"

    return direction, False, "insufficient data to decide inversion"


# ── Data fetching (from signal_gen) ──────────────────────────────────────────
def get_token_data_for_prediction(token):
    """
    Fetch data for token from signal_gen price history + OHLCV aggregation.
    Returns dict with price, OHLCV-based indicators, HL data, accuracy stats.
    """
    conn = get_runtime_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT momentum_state, state_confidence, percentile_short,
               percentile_long, avg_z, phase, z_direction
        FROM momentum_cache WHERE token=?
    """, (token,))
    row = cur.fetchone()
    conn.close()

    # Get price history with timestamps for OHLCV aggregation
    conn2 = get_prices_db()
    cur2 = conn2.cursor()
    cur2.execute("""
        SELECT timestamp, price FROM price_history
        WHERE token=? ORDER BY timestamp DESC LIMIT 200
    """, (token,))
    rows = cur2.fetchall()
    conn2.close()

    if not rows:
        return None

    # Build OHLCV candles using runtime interval (default 4h, configurable via --interval)
    ohlcv = build_ohlcv(token, candle_minutes=CANDLE_MINUTES)
    if not ohlcv or len(ohlcv) < 30:
        # Fallback: use raw ticks
        prices = [r[1] for r in rows]
        timestamps = [r[0] for r in rows]
    else:
        # Use close prices from OHLCV candles for all indicators
        prices = [c[3] for c in ohlcv]  # close prices only

    latest_price = prices[0] if prices else None

    # RSI from OHLCV closes
    rsi_val = compute_rsi_ohlc(prices)

    # MACD from OHLCV closes
    macd_line, macd_signal, macd_hist = compute_macd_ohlc(prices)

    # Z-score (still from price_history, but now using candle close)
    recent = prices[:20]
    avg_price = statistics.mean(recent) if len(recent) >= 20 else statistics.mean(prices)
    std_price = statistics.stdev(recent) if len(recent) > 1 else 1
    z = (prices[0] - avg_price) / std_price if std_price > 0 else 0

    # Volume estimation
    recent_vol, older_vol, vol_ratio = estimate_volume(token)

    # Price changes from OHLCV close
    chg_1h  = 0
    chg_4h  = 0
    chg_24h = 0
    if len(ohlcv) >= 60:  # 1h = 1 candle (4h candles)
        chg_1h  = ((ohlcv[-1][3] - ohlcv[-4][3]) / ohlcv[-4][3]) * 100
        chg_4h  = ((ohlcv[-1][3] - ohlcv[-2][3]) / ohlcv[-2][3]) * 100
        chg_24h = ((ohlcv[-1][3] - ohlcv[-7][3]) / ohlcv[-7][3]) * 100
    elif len(prices) >= 144:
        chg_1h  = ((prices[0] - prices[min(15, len(prices)-1)]) / prices[min(15, len(prices)-1)]) * 100
        chg_4h  = ((prices[0] - prices[min(60, len(prices)-1)]) / prices[min(60, len(prices)-1)]) * 100
        chg_24h = ((prices[0] - prices[min(144, len(prices)-1)]) / prices[min(144, len(prices)-1)]) * 100

    momentum_state = row[0] if row else 'neutral'
    state_conf     = row[1] if row else 0.3
    pct_short      = row[2] if row else 50
    pct_long       = row[3] if row else 50
    avg_z          = row[4] if row else 0
    phase          = row[5] if row else 'quiet'
    z_dir          = row[6] if row else 'neutral'

    # Regime
    regime = 'neutral'
    if momentum_state == 'bullish' and pct_short < 40:
        regime = 'bullish'
    elif momentum_state == 'bearish' and pct_short > 60:
        regime = 'bearish'
    elif z_dir == 'rising' and phase in ('accelerating', 'exhaustion'):
        regime = 'bullish'
    elif z_dir == 'falling' and phase == 'accelerating':
        regime = 'bearish'
    try:
        conn3 = get_runtime_db()
        cur3 = conn3.cursor()
        cur3.execute("SELECT direction FROM decisions WHERE token=? ORDER BY created_at DESC LIMIT 1", (token,))
        r = cur3.fetchone()
        if r:
            regime = 'bullish' if r[0].upper() == 'LONG' else 'bearish'
        conn3.close()
    except:
        pass

    # MTF MACD crossover (parallel across 3 timeframes)
    mtf_macd = compute_mtf_macd(token)

    return {
        'token': token,
        'price': latest_price,
        'chg_1h': round(chg_1h, 2),
        'chg_4h': round(chg_4h, 2),
        'chg_24h': round(chg_24h, 2),
        'rsi': rsi_val if rsi_val else 50,
        'macd_hist': macd_hist if macd_hist is not None else 0,
        'macd_line': macd_line,
        'z_score': round(z, 3),
        'avg_z': round(avg_z, 3),
        'pct_short': round(pct_short, 1),
        'pct_long': round(pct_long, 1),
        'momentum_state': momentum_state,
        'state_confidence': state_conf,
        'phase': phase,
        'z_direction': z_dir,
        'regime': regime,
        'price_history': prices[:10],  # last 10 candle closes
        'volume_ratio': vol_ratio,
        'recent_vol': recent_vol,
        'ohlcv': ohlcv[-20:] if ohlcv else [],  # last 20 OHLCV candles
        'mtf_macd': mtf_macd,  # multi-timeframe MACD crossover data
    }


def build_prediction_prompt(token_data, hl_data, accuracy_stats):
    """Build Ollama prompt — pure text categories, no numeric values.

    Research findings (2026-04-06):
    - LLM does NOT compute with numbers — RSI=55.3 behaves same as RSI=overbought
    - Only text categories work reliably: RSI=(overbought/neutral/oversold)
    - Z-score also works as category: elevated/normal/suppressed
    - Regime and momentum: strong levers (bearish regime flips trend)
    - Prev 3 candles: strong micro-momentum signal
    - MACD, raw numbers: skip — no improvement or hurts
    """
    d = token_data
    if not d:
        return None

    # ── Compute indicators from price_history ───────────────────────
    ph = d.get('price_history', [])

    # 5-candle trend
    if len(ph) >= 5:
        trend = 'UP' if ph[-1] > ph[-5] else 'DOWN' if ph[-1] < ph[-5] else 'FLAT'
    else:
        trend = 'FLAT'

    # 3-candle micro-momentum
    if len(ph) >= 4:
        prev3 = [('UP' if ph[i] > ph[i-1] else 'DOWN') for i in range(-4, -1)]
        prev3_str = ','.join(prev3)
        prev3_all = len(set(prev3)) == 1  # all same direction
    else:
        prev3_str = None
        prev3_all = False

    # RSI category (not numeric — LLM doesn't compute with numbers)
    rsi = d.get('rsi', 50)
    rsi_cat = 'overbought' if rsi > 65 else 'oversold' if rsi < 35 else 'neutral'

    # Z-score category
    z = d.get('z_score', 0)
    z_cat = 'elevated' if z > 1.5 else 'suppressed' if z < -1.5 else 'normal'

    # Regime and momentum (from Hermes momentum_cache)
    regime = d.get('regime', 'neutral')
    momentum = d.get('momentum_state', 'neutral')

    # ── Build parts (pure text only) ─────────────────────────────────
    parts = ["BTC:"]
    parts.append(f"RSI={rsi_cat}")          # no numeric value
    parts.append(f"Z={z_cat}")              # no numeric value
    if prev3_str:
        parts.append(f"prev3=[{prev3_str}]")
    parts.append(f"trend={trend}")
    if regime != 'neutral':
        parts.append(f"regime={regime}")
    if momentum != 'neutral':
        parts.append(f"momentum={momentum}")

    prompt = ', '.join(parts) + '. Reply ONLY UP or DOWN:\n\nDIRECTION:'
    return prompt


def query_llm(prompt):
    """Query local Ollama via requests (replaces curl subprocess)."""
    try:
        import requests as _req
        resp = _req.post(
            OLLAMA_URL,
            json={
                'model': MODEL,
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0.3, 'num_predict': 150}
            },
            timeout=30
        )
        data = resp.json()
        return data.get('response', '').strip()
    except Exception as e:
        log(f"LLM error: {e}", 'ERROR')
        return None


def parse_prediction(response, token):
    """Parse LLM response into structured dict.

    Supports two formats:
    - Minimal (new): plain "UP" or "DOWN" as first word
    - Structured (legacy): DIRECTION: UP, CONFIDENCE: 70, MOVE_PCT: +1.5
    """
    if not response:
        return None
    direction = None
    confidence = None
    move_pct = None

    t = response.upper().strip()

    # Try minimal format first: standalone UP or DOWN as first word
    first_word = t.split()[0] if t.split() else ''
    if first_word in ('UP', 'DOWN'):
        direction = first_word
        # For minimal format, set default confidence based on signal strength
        # (override via parse of numeric lines if present)
        confidence = 55  # default for minimal format

    # Try structured format lines
    for line in response.split('\n'):
        line = line.strip()
        if 'DIRECTION:' in line.upper():
            d = line.upper().split('DIRECTION:')[1].strip().split()[0]
            direction = d if d in ('UP', 'DOWN') else direction
        if 'CONFIDENCE:' in line.upper():
            try:
                confidence = int(line.upper().split('CONFIDENCE:')[1].strip().replace('%','').split()[0])
            except:
                pass
        if 'MOVE_PCT:' in line.upper():
            try:
                move_pct = float(line.upper().split('MOVE_PCT:')[1].strip().replace('%','').split()[0])
            except:
                pass

    if not direction:
        log(f"Could not parse direction from response: {response[:100]}", 'WARN')
        return None

    return {
        'token': token,
        'direction': direction,
        'confidence': confidence or 50,
        'predicted_move_pct': move_pct,
        'prediction_time': int(time.time()),
        'candle_time': int(time.time()) + 14400,
    }


def store_prediction(conn, pred, token_data, was_inverted=False, inversion_reason=""):
    """Store prediction in predictions DB (with inversion tracking)."""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO predictions
          (token, direction, confidence, predicted_move_pct, prediction_time,
           candle_time, price_at_prediction, momentum_state, regime, was_inverted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (pred['token'], pred['direction'], pred['confidence'],
          pred.get('predicted_move_pct'), pred['prediction_time'],
          pred['candle_time'], token_data['price'],
          token_data['momentum_state'], token_data['regime'], 1 if was_inverted else 0))
    conn.commit()

    inv_tag = " [INVERTED]" if was_inverted else ""
    log(f"  → {pred['token']}: {pred['direction']}{inv_tag} conf={pred['confidence']} "
        f"move={pred.get('predicted_move_pct', '?')} "
        f"(state={token_data['momentum_state']} regime={token_data['regime']}) "
        f"{inversion_reason}")


def validate_predictions(conn):
    """Validate predictions that have had 4 hours to resolve."""
    cur = conn.cursor()
    four_hours_ago = int(time.time()) - (4 * 60 * 60)

    cur.execute("""
        SELECT id, token, direction, price_at_prediction, predicted_move_pct
        FROM predictions
        WHERE prediction_time < ? AND correct IS NULL
        ORDER BY prediction_time DESC LIMIT 30
    """, (four_hours_ago,))

    predictions = cur.fetchall()
    if not predictions:
        return

    log(f"Validating {len(predictions)} resolved predictions...")

    conn2 = get_prices_db()
    validated = 0
    for pred_id, token, direction, entry_price, predicted_move in predictions:
        if not entry_price or entry_price == 0:
            continue
        cur2 = conn2.cursor()
        cur2.execute("""
            SELECT price FROM price_history
            WHERE token=? ORDER BY timestamp DESC LIMIT 1
        """, (token,))
        row = cur2.fetchone()
        if not row or not row[0]:
            continue

        current_price = row[0]
        actual_move = ((current_price - entry_price) / entry_price) * 100

        if direction == 'UP':
            correct = actual_move > 0
        else:
            correct = actual_move < 0

        cur.execute("""
            UPDATE predictions
            SET actual_move_pct = ?, correct = ?
            WHERE id = ?
        """, (round(actual_move, 4), correct, pred_id))
        validated += 1

    conn2.close()
    conn.commit()

    if validated:
        log(f"Validated {validated} predictions")
        cur.execute("""
            SELECT COUNT(*), SUM(CASE WHEN correct THEN 1 ELSE 0 END)
            FROM predictions WHERE correct IS NOT NULL
        """)
        total, correct = cur.fetchone()
        if total and total > 0:
            acc = correct / total * 100
            log(f"  Overall accuracy: {correct}/{total} = {acc:.1f}%")

        # Inversion stats
        cur.execute("""
            SELECT COUNT(*), SUM(CASE WHEN correct THEN 1 ELSE 0 END)
            FROM predictions WHERE was_inverted = 1 AND correct IS NOT NULL
        """)
        inv_total, inv_correct = cur.fetchone()
        if inv_total and inv_total > 0:
            inv_acc = inv_correct / inv_total * 100
            log(f"  Inverted predictions: {inv_correct}/{inv_total} = {inv_acc:.1f}% accuracy")


def get_prediction_accuracy(conn, token):
    """Get per-token prediction accuracy for the last 20 predictions."""
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*), SUM(CASE WHEN correct THEN 1 ELSE 0 END)
        FROM predictions
        WHERE token=? AND correct IS NOT NULL
        ORDER BY prediction_time DESC LIMIT 20
    """, (token,))
    total, correct = cur.fetchone()
    if total and total >= 3:
        return round(correct / total * 100, 1), total
    return None, total or 0


def run_with_wandb(args=None):
    """Main entry wrapped for wandb tracking — parse args before wandb.init."""
    parser = argparse.ArgumentParser(description='Candle Predictor')
    parser.add_argument('--wandb-project', default='candle-predictor')
    parser.add_argument('--wandb-entity', default=None)
    parsed, _ = parser.parse_known_args(args or [])
    return parsed, main_loop()

def main_loop():
    """
    Core prediction loop (extracted from main() so wandb can wrap it).
    Returns dict with run stats: {predicted, inverted_total, tokens_processed, errors}
    """
    # ── Hyperparameters (for wandb config) ─────────────────────────────────
    hyperparams = {
        'model': MODEL,
        'ollama_url': OLLAMA_URL,
        'top_tokens_count': len(TOP_TOKENS),
        'inversion_threshold': INVERSION_THRESHOLD,
        'candle_minutes': 240,
    }

    log("=== Candle Predictor Starting (v2 - with HL data + inversion) ===")

    conn = init_predictions_db()

    stats = {'predicted': 0, 'inverted_total': 0, 'tokens_processed': 0, 'errors': 0}

    # 1. Validate old predictions
    validate_predictions(conn)

    # 2. Fetch HL data for all top tokens
    log("Fetching HL market data (funding rates, orderbook, volume)...")
    hl_data = get_hl_data()
    log(f"  HL data for {len(hl_data)} tokens: {list(hl_data.keys())}")

    # 3. Generate new predictions
    tokens_to_predict = get_effective_tokens()
    log(f"  Predicting {len(tokens_to_predict)} tokens (base={len(TOP_TOKENS)}, watched={len(tokens_to_predict)-len(TOP_TOKENS)})")
    for token in tokens_to_predict:
        stats['tokens_processed'] += 1
        token_data = get_token_data_for_prediction(token)
        if not token_data:
            log(f"  {token}: no price data, skipping", 'WARN')
            continue

        # Check accuracy - skip if model is performing near-random on this token
        # NOTE: lowered from 40→25 on 2026-04-06 to let new prompt variants accumulate
        # predictions. If acc stays <25% across 50+ predictions, the prompt needs work.
        acc, n = get_prediction_accuracy(conn, token)
        if acc is not None and acc < 25 and n >= 50:
            log(f"  {token}: very low accuracy ({acc:.0f}%/{n}), skipping this round")
            time.sleep(0.5)
            continue

        # Get accuracy stats for prompt
        accuracy_stats = get_accuracy_stats(conn, token)

        # Build prompt with HL data and accuracy context
        prompt = build_prediction_prompt(token_data, hl_data, accuracy_stats)
        if not prompt:
            continue

        # Query LLM
        response = query_llm(prompt)
        if not response:
            stats['errors'] += 1
            continue

        pred = parse_prediction(response, token)
        if pred:
            # Apply inversion logic
            final_dir, was_inverted, inv_reason = decide_inversion(
                token, pred['direction'], token_data['momentum_state'], conn
            )

            if was_inverted:
                pred['direction'] = final_dir
                stats['inverted_total'] += 1

            # Minimax final-check (if enabled)
            if MINIMAX_CHECK:
                mx = minimax_check(token, pred['direction'], prompt, pred.get('confidence', 50))
                if not mx['agree']:
                    prev = pred['direction']
                    pred['direction'] = mx['minimax_direction']
                    inv_reason = f"MINIMAX OVERRIDE: {mx['reason'][:80]}"
                    log(f"  {token}: MINIMAX overrode {prev} → {pred['direction']}: {mx['reason'][:60]}")
                else:
                    log(f"  {token}: MINIMAX agreed {pred['direction']}")

            store_prediction(conn, pred, token_data, was_inverted, inv_reason)
            stats['predicted'] += 1

        time.sleep(1.0)

    log(f"=== Predicted {stats['predicted']} tokens, {stats['inverted_total']} inverted ===")
    conn.close()
    return stats


# ── Watch list management ───────────────────────────────────────────────────────
def load_watch_list():
    """Load dynamically-added tokens (from traded coins)."""
    try:
        if os.path.exists(WATCH_LIST_FILE):
            with open(WATCH_LIST_FILE) as f:
                data = json.load(f)
                return set(data.get('tokens', []))
    except Exception:
        pass
    return set()

def add_to_watch_list(token):
    """Add a token to the watch list (called when a coin is traded)."""
    watched = load_watch_list()
    watched.add(token.upper())
    try:
        os.makedirs(os.path.dirname(WATCH_LIST_FILE), exist_ok=True)
        with open(WATCH_LIST_FILE, 'w') as f:
            json.dump({'tokens': sorted(watched)}, f)
    except Exception as e:
        log(f"Failed to save watch list: {e}", 'WARN')

def get_effective_tokens():
    """TOP_TOKENS + dynamically watched tokens (recently traded)."""
    base = set(TOP_TOKENS)
    watched = load_watch_list()
    return sorted(base | watched)

# ── Minimax final check ────────────────────────────────────────────────────────
MINIMAX_API = 'https://api.minimaxi.chat/v1/text/chatcompletion_v2'
MINIMAX_MODEL = 'MiniMax-Text-01'

def minimax_check(token, direction, prompt_used, conf) -> dict:
    """
    Second-opinion check via Minimax API.
    Returns {'agree': bool, 'minimax_direction': str, 'reason': str}
    Falls back to agree=True if API fails (never override on error).
    """
    if not MINIMAX_CHECK:
        return {'agree': True, 'minimax_direction': direction, 'reason': 'disabled'}

    # Build a concise summary for minimax
    interval_label = f"{CANDLE_MINUTES // 60}h" if CANDLE_MINUTES >= 60 else f"{CANDLE_MINUTES}m"
    summary = (
        f"{token} {interval_label} candle prediction:\n"
        f"  Local model (qwen2.5) predicted: {direction} (confidence: {conf})\n"
        f"  Prompt used: {prompt_used[:200]}\n"
        f"Should we trust this prediction? Answer YES or NO and explain briefly."
    )

    try:
        import yaml
        with open('/root/.hermes/config.yaml') as f:
            cfg = yaml.safe_load(f)
        api_key = cfg.get('minimax_api_key') or os.environ.get('MINIMAX_API_KEY', '')
    except Exception:
        api_key = os.environ.get('MINIMAX_API_KEY', '')

    if not api_key:
        log("Minimax check skipped: no API key found", 'WARN')
        return {'agree': True, 'minimax_direction': direction, 'reason': 'no_api_key'}

    try:
        import urllib.request, json as _json
        req_body = {
            'model': MINIMAX_MODEL,
            'messages': [
                {'role': 'user', 'content': summary}
            ],
            'max_tokens': 100,
            'temperature': 0.3,
        }
        req = urllib.request.Request(
            MINIMAX_API,
            data=_json.dumps(req_body).encode(),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = _json.loads(resp.read())
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            t = content.upper()
            agree = 'YES' in t or 'AGREE' in t or 'TRUST' in t
            return {
                'agree': agree,
                'minimax_direction': direction if agree else ('UP' if direction == 'DOWN' else 'DOWN'),
                'reason': content[:150]
            }
    except Exception as e:
        log(f"Minimax check failed: {e} — defaulting to agree", 'WARN')
        return {'agree': True, 'minimax_direction': direction, 'reason': f'error: {e}'}


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    """CLI: candle_predictor.py [--nowandb] [--interval 15|60|240] [--minimax]"""
    import sys
    use_wandb = '--nowandb' not in sys.argv

    # Parse interval arg
    global CANDLE_MINUTES, MINIMAX_CHECK
    for arg in sys.argv:
        if arg.startswith('--interval='):
            mins = int(arg.split('=')[1])
            if mins not in (15, 60, 240):
                print(f"ERROR: --interval must be 15, 60, or 240. Got {mins}")
                sys.exit(1)
            CANDLE_MINUTES = mins
        if arg == '--minimax':
            MINIMAX_CHECK = True

    interval_label = f"{CANDLE_MINUTES // 60}h" if CANDLE_MINUTES >= 60 else f"{CANDLE_MINUTES}m"
    log(f"=== Candle Predictor Starting ({interval_label} candles, minimax={'ON' if MINIMAX_CHECK else 'off'}) ===")

    if not acquire_lock():
        log("Already running, exiting")
        sys.exit(0)

    if use_wandb:
        # Try to get wandb API key from env or _secrets
        wandb_key = os.environ.get('WANDB_API_KEY', '')
        try:
            from _secrets import WANDB_API_KEY
            wandb_key = WANDB_API_KEY
        except ImportError:
            pass

        # W&B offline/anonymous — runs queued locally, synced later with `wandb sync`
        wandb.init(
            project='hermes-ai',
            entity=None,
            mode='offline',
            config={
                'model': MODEL,
                'ollama_url': OLLAMA_URL,
                'top_tokens': TOP_TOKENS,
                'inversion_threshold': INVERSION_THRESHOLD,
                'candle_minutes': CANDLE_MINUTES,
                'minimax_check': MINIMAX_CHECK,
            },
            settings=wandb.Settings(anonymous='allow'),
        )
        log("W&B tracking enabled (offline, project=hermes-ai)")

    try:
        stats = main_loop()
        if use_wandb:
            wandb.log({
                'run_predicted': stats['predicted'],
                'run_inverted': stats['inverted_total'],
                'run_tokens_processed': stats['tokens_processed'],
                'run_errors': stats['errors'],
                'run_success': 1,
            })
            # Local backup — always saved regardless of W&B sync state
            import json
            from datetime import datetime
            local_path = f'/root/.hermes/wandb-local/candle-predictor-{datetime.utcnow().strftime("%Y%m%d-%H%M%S")}.json'
            os.makedirs('/root/.hermes/wandb-local', exist_ok=True)
            with open(local_path, 'w') as f:
                json.dump({
                    'timestamp': datetime.utcnow().isoformat(),
                    'model': MODEL,
                    'top_tokens': TOP_TOKENS,
                    'inversion_threshold': INVERSION_THRESHOLD,
                    'predicted': stats['predicted'],
                    'inverted_total': stats['inverted_total'],
                    'tokens_processed': stats['tokens_processed'],
                    'errors': stats['errors'],
                }, f, indent=2)
            log(f"Local W&B backup saved: {local_path}")
    finally:
        if use_wandb:
            wandb.finish()
            log("W&B run finished")

    try:
        os.remove(LOCK_FILE)
    except:
        pass


if __name__ == '__main__':
    main()