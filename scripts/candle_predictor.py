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
import sqlite3, json, time, os, sys, subprocess, statistics
from collections import defaultdict

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
INVERSION_THRESHOLD = 0.40  # invert if direction accuracy < 40% in this momentum_state


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

    FIX (2026-04-05): Complete rewrite based on real prediction.db stats:
    - UP is 60.5% accurate overall — NEVER invert UP (regardless of state)
    - DOWN is 35% accurate overall — invert when down_performance < 40% in state
    - The inversion must IMPROVE accuracy, not make it worse

    Data-backed rules:
    - UP: 64% bullish, 56% neutral, 0% bearish → always keep UP
    - DOWN: 37% neutral, 38% bearish, 89% bullish → invert only in neutral/bearish
    """
    stats = get_accuracy_stats(conn, token, momentum_state)
    state_data = stats.get('by_state', {})
    overall_data = stats.get('overall', {})

    # Get accuracy for this direction in this momentum_state
    state_acc = state_data.get(direction, {}).get('acc', None)
    overall_dir_acc = overall_data.get(direction, {}).get('acc', None)
    state_sample = state_data.get(direction, {}).get('n', 0)

    # ── RULE 1: NEVER INVERT UP ──────────────────────────────────────────────
    # UP predictions are 60.5% accurate overall, 64% in bullish, 56% in neutral.
    # Even in bearish (0% on 3 samples), the sample size is too small to justify inversion.
    # The model should predict UP more often, not less.
    if direction == 'UP':
        return 'UP', False, "UP predictions are 60.5% accurate — never invert"

    # ── RULE 2: INVERT DOWN only when statistically justified ────────────────
    # DOWN predictions: 35% overall, 38% in bearish, 37% in neutral, 89% in bullish
    # Inverting DOWN→UP in bearish/neutral gives 63% accuracy (vs 35% raw).
    # Only invert when:
    #   a) We have enough samples (>=10) in this state to trust the accuracy
    #   b) State accuracy is below 42% (improvement threshold)
    #   c) Overall direction accuracy is also below 45% (confirm it's not just state noise)
    if direction == 'DOWN':
        if state_acc is not None and state_sample >= 10:
            # Enough samples — use state-specific accuracy
            if state_acc < 42 and (overall_dir_acc is None or overall_dir_acc < 45):
                return 'UP', True, f"DOWN in {momentum_state}: acc={state_acc:.1f}% < 42%, overall_dir={overall_dir_acc:.1f}% — invert to UP"
            return 'DOWN', False, f"DOWN in {momentum_state}: acc={state_acc:.1f}% >= 42% (n={state_sample})"
        elif overall_dir_acc is not None and overall_dir_acc < 42:
            # No state data — use overall DOWN accuracy
            return 'UP', True, f"DOWN overall: acc={overall_dir_acc:.1f}% < 42% — invert to UP"
        elif overall_dir_acc is not None and overall_dir_acc >= 42:
            return 'DOWN', False, f"DOWN overall: acc={overall_dir_acc:.1f}% >= 42%, keep DOWN"

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

    # Build OHLCV 4h candles (240 min)
    ohlcv = build_ohlcv(token, candle_minutes=240)
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
    """Build Ollama prompt with momentum data, HL context, and accuracy stats."""
    d = token_data
    if not d:
        return None

    # Price trend from candle closes
    ph = d['price_history']
    price_trend = ' → '.join([f"${p:.4f}" for p in ph[:5][::-1]])

    # Regime context
    regime_emoji = {'bullish': '📈', 'bearish': '📉', 'neutral': '↔️'}.get(d['regime'], '?')

    # Bias from momentum state
    if d['momentum_state'] == 'bullish':
        bias = 'LONG bias (suppressed price catching bid)'
    elif d['momentum_state'] == 'bearish':
        bias = 'SHORT bias (elevated price ripe for reversal)'
    else:
        bias = 'neutral / ranging'

    # Accuracy context from predictions.db
    acc_lines = []
    token = d['token']
    if accuracy_stats:
        overall = accuracy_stats.get('overall', {})
        by_state = accuracy_stats.get('by_state', {})

        # Overall per-direction accuracy
        for direction in ('UP', 'DOWN'):
            if direction in overall:
                info = overall[direction]
                acc_lines.append(
                    f"- Overall {direction}: {info['acc']:.1f}% accuracy ({info['correct']}/{info['n']} correct)"
                )

        # Momentum_state-specific accuracy
        state = d['momentum_state']
        if state in by_state:
            for direction in ('UP', 'DOWN'):
                if direction in by_state:
                    info = by_state[direction]
                    acc_lines.append(
                        f"- In {state} regime, {direction}: {info['acc']:.1f}% accuracy ({info['correct']}/{info['n']})"
                    )

    acc_context = ""
    if acc_lines:
        acc_context = "\nPREDICTION HISTORY (learn from this):\n" + "\n".join(acc_lines)

    # HL data context
    hl_ctx = []
    token_hl = hl_data.get(d['token'], {})
    if 'funding_rate' in token_hl:
        fr = token_hl['funding_rate']
        sign = '+' if fr >= 0 else ''
        hl_ctx.append(f"- Funding rate (8h): {sign}{fr*100:.4f}%")
    if 'spread_bps' in token_hl:
        hl_ctx.append(f"- Bid-ask spread: {token_hl['spread_bps']:.2f} bps")
    if 'volume_ratio' in token_hl:
        vr = token_hl['volume_ratio']
        direction = "INCREASING" if vr > 1.2 else "DECREASING" if vr < 0.8 else "STABLE"
        hl_ctx.append(f"- Volume: {direction} (ratio: {vr}x)")

    # Volume context
    vol_ctx = ""
    if d.get('volume_ratio') is not None:
        vr = d['volume_ratio']
        direction = "INCREASING" if vr > 1.2 else "DECREASING" if vr < 0.8 else "STABLE"
        vol_ctx = f"- Volume trend: {direction} (ratio: {vr}x vs prior period)\n"

    # MTF MACD crossover context
    mtf_macd_ctx = ""
    if d.get('mtf_macd'):
        mtf_macd_ctx = "\n" + _get_mtf_macd_summary(d['mtf_macd']) + "\n"

    # Build HL context for other top tokens (contextual awareness)
    top_token_fr=[]
    for t in ['BTC', 'ETH', 'SOL', 'AVAX', 'XRP']:
        if t in hl_data and 'funding_rate' in hl_data[t]:
            fr = hl_data[t]['funding_rate']
            sign = '+' if fr >= 0 else ''
            top_token_fr.append(f"{t}: {sign}{fr*100:.4f}%")
    fr_context = ""
    if top_token_fr:
        fr_context = "\nMARKET FUNDING RATES (8h):\n  " + " | ".join(top_token_fr)

    return f"""You are a crypto 4-hour candle direction predictor.

{d['pct_short']:.0f} 4h candles of {d['token']} history + momentum indicators:

LAST PRICE: ${d['price']:.6f}
{d['chg_1h']:+.2f}% in 1h | {d['chg_4h']:+.2f}% in 4h | {d['chg_24h']:+.2f}% in 24h
Price trend (oldest→newest): {price_trend}

MOMENTUM INDICATORS (computed from OHLCV candle closes):
- RSI(14): {d['rsi']:.1f} (overbought>70, oversold<30)
- MACD Histogram: {d['macd_hist']:+.6f} (positive=bullish momentum)
- Z-score: {d['z_score']:+.2f} (price vs 20-candle mean; +2=elevated, -2=suppressed)
- Avg Z (multi-TF): {d['avg_z']:+.2f}
{mtf_macd_ctx}

HERMES MOMENTUM STATE: {d['momentum_state']} ({d['state_confidence']:.0%} confidence)
Regime: {d['regime']} {regime_emoji}
Phase: {d['phase']} | Z-direction: {d['z_direction']}
Percentile: short={d['pct_short']:.0f}% long={d['pct_long']:.0f}%

Trading bias from Hermes momentum model: {bias}
{vol_ctx}{acc_context}{fr_context}

MARKET CONTEXT (Hyperliquid orderbook):
{chr(10).join(hl_ctx) if hl_ctx else "  (no live data available)"}

TASK: Predict whether the NEXT 4-hour candle will close UP or DOWN.
Consider: current momentum, regime, momentum_state, z-score direction, RSI level,
historical accuracy patterns, funding rates, volume.

FEW-SHOT EXAMPLES (learn from these patterns):
- bullish + RSI < 35 → UP (oversold bounce, continuation bias)
- bearish + RSI > 65 → DOWN (overbought rejection, continuation bias)
- bullish regime + DOWN predicted → KEEP DOWN (DOWN is 89% accurate in bullish!)
- neutral/bearish + DOWN predicted → consider inversion (DOWN is only 37% accurate)
- RSI near 50 in neutral → consider UP (markets mean-revert)

IMPORTANT: Your historical accuracy varies by regime and momentum_state.
Real data from prediction.db:
- UP: 60.5% overall, 64% bullish, 56% neutral — predict UP freely
- DOWN: 35% overall, BUT 89% in bullish, 38% in bearish, 37% in neutral
- When momentum is bearish/neutral AND you predict DOWN → the inversion (UP) is 63% accurate
Trust momentum_state guidance — bearish means bearish continuation, not reversal.

Respond STRICTLY in this format (one line each):
DIRECTION: [UP or DOWN]
CONFIDENCE: [0-100]
MOVE_PCT: [estimated % move, e.g. +1.5 or -0.8]
REASON: [one sentence]
"""


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
                'options': {'temperature': 0.3, 'num_predict': 80}
            },
            timeout=30
        )
        data = resp.json()
        return data.get('response', '').strip()
    except Exception as e:
        log(f"LLM error: {e}", 'ERROR')
        return None


def parse_prediction(response, token):
    """Parse LLM response into structured dict."""
    if not response:
        return None
    direction = None
    confidence = None
    move_pct = None

    for line in response.split('\n'):
        line = line.strip()
        if 'DIRECTION:' in line.upper():
            d = line.upper().split('DIRECTION:')[1].strip().split()[0]
            direction = d if d in ('UP', 'DOWN') else None
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


def main():
    if not acquire_lock():
        log("Already running, exiting")
        sys.exit(0)

    log("=== Candle Predictor Starting (v2 - with HL data + inversion) ===")

    conn = init_predictions_db()

    # 1. Validate old predictions
    validate_predictions(conn)

    # 2. Fetch HL data for all top tokens
    log("Fetching HL market data (funding rates, orderbook, volume)...")
    hl_data = get_hl_data()
    log(f"  HL data for {len(hl_data)} tokens: {list(hl_data.keys())}")

    # 3. Generate new predictions
    predicted = 0
    inverted_total = 0

    for token in TOP_TOKENS:
        token_data = get_token_data_for_prediction(token)
        if not token_data:
            log(f"  {token}: no price data, skipping", 'WARN')
            continue

        # Check accuracy - skip if model is cold for this token
        acc, n = get_prediction_accuracy(conn, token)
        if acc is not None and acc < 40 and n >= 15:
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

        if response:
            pred = parse_prediction(response, token)
            if pred:
                # Apply inversion logic
                final_dir, was_inverted, inv_reason = decide_inversion(
                    token, pred['direction'], token_data['momentum_state'], conn
                )

                original_dir = pred['direction']
                if was_inverted:
                    pred['direction'] = final_dir
                    inverted_total += 1

                store_prediction(conn, pred, token_data, was_inverted, inv_reason)
                predicted += 1

        time.sleep(1.0)

    log(f"=== Predicted {predicted} tokens, {inverted_total} inverted ===")
    conn.close()

    try:
        os.remove(LOCK_FILE)
    except:
        pass


if __name__ == '__main__':
    main()