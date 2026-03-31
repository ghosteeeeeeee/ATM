#!/usr/bin/env python3
"""
Candle Predictor for Hermes Trading System
Uses local Ollama LLM to predict next 4h candle direction per token.
Integrated into signal pipeline — reads from signal_gen momentum data,
writes predictions to signals_hermes_runtime.db for scoring integration.
"""
import sqlite3, json, time, os, sys, subprocess, statistics

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
TOP_TOKENS   = ['BTC','ETH','SOL','BNB','XRP','ADA','DOGE','AVAX','LINK','DOT',
                'MATIC','LTC','UNI','ATOM','XLM','ETC','ALGO','VET','FIL','THETA',
                'AAVE','MKR','COMP','SNX','YFI','SUSHI','CRV','RUNE','KAVA','BAT']


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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_token_time ON predictions(token, prediction_time)")
    conn.commit()
    return conn


# ── Data fetching (from signal_gen) ──────────────────────────────────────────
def get_token_data_for_prediction(token):
    """
    Fetch last 10 data points for token from signal_gen price history.
    Returns list of dicts with price, z_score, momentum_state, regime, phase, velocity.
    """
    conn = get_runtime_db()
    cur = conn.cursor()
    # Get momentum state from latest cache
    cur.execute("""
        SELECT momentum_state, state_confidence, percentile_short,
               percentile_long, avg_z, phase, z_direction
        FROM momentum_cache WHERE token=?
    """, (token,))
    row = cur.fetchone()
    conn.close()
    
    # Get price history
    conn2 = get_prices_db()
    cur2 = conn2.cursor()
    cur2.execute("""
        SELECT timestamp, price FROM price_history
        WHERE token=? ORDER BY timestamp DESC LIMIT 50
    """, (token,))
    rows = cur2.fetchall()
    conn2.close()
    
    if not rows:
        return None
    
    # Compute indicators from price history
    prices = [r[1] for r in rows]
    timestamps = [r[0] for r in rows]
    
    # RSI
    def _rsi(prices, period=14):
        if len(prices) < period + 1:
            return None
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d for d in deltas[-period:] if d > 0]
        losses = [-d for d in deltas[-period:] if d < 0]
        avg_gain = statistics.mean(gains) if gains else 0
        avg_loss = statistics.mean(losses) if losses else 0
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    # Latest price
    latest_price = prices[0]
    
    # Price change
    chg_1h  = ((prices[0] - prices[min(6, len(prices)-1)]) / prices[min(6, len(prices)-1)]) * 100 if len(prices) > 6 else 0
    chg_4h  = ((prices[0] - prices[min(24, len(prices)-1)]) / prices[min(24, len(prices)-1)]) * 100 if len(prices) > 24 else 0
    chg_24h = ((prices[0] - prices[min(144, len(prices)-1)]) / prices[min(144, len(prices)-1)]) * 100 if len(prices) > 144 else 0
    
    # MACD histogram (quick compute)
    def _ema(data, period):
        k = 2 / (period + 1)
        ema_val = data[0]
        for v in data[1:]:
            ema_val = v * k + ema_val * (1 - k)
        return ema_val
    
    def _macd_hist(prices):
        if len(prices) < 26:
            return None
        ema_fast = _ema(prices, 12)
        ema_slow = _ema(prices, 26)
        signal = _ema(prices, 9)  # approximate
        return ema_fast - ema_slow
    
    # Z-score
    recent = prices[:20]
    avg_price = statistics.mean(recent)
    std_price = statistics.stdev(recent) if len(recent) > 1 else 1
    z = (prices[0] - avg_price) / std_price if std_price > 0 else 0
    
    momentum_state = row[0] if row else 'neutral'
    state_conf     = row[1] if row else 0.3
    pct_short      = row[2] if row else 50
    pct_long       = row[3] if row else 50
    avg_z          = row[4] if row else 0
    phase          = row[5] if row else 'quiet'
    z_dir          = row[6] if row else 'neutral'
    rsi_val        = _rsi(prices)
    macd_hist      = _macd_hist(prices)
    
    # Regime: derive from momentum state (no regime_log table)
    regime = 'neutral'
    if momentum_state == 'bullish' and pct_short < 40:
        regime = 'bullish'
    elif momentum_state == 'bearish' and pct_short > 60:
        regime = 'bearish'
    elif z_dir == 'rising' and phase in ('accelerating', 'exhaustion'):
        regime = 'bullish'
    elif z_dir == 'falling' and phase == 'accelerating':
        regime = 'bearish'
    # Also try decisions table for recent signal direction
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
    
    return {
        'token': token,
        'price': latest_price,
        'price_4h_ago': prices[min(24, len(prices)-1)] if len(prices) > 24 else prices[-1],
        'chg_1h': chg_1h,
        'chg_4h': chg_4h,
        'chg_24h': chg_24h,
        'rsi': round(rsi_val, 1) if rsi_val else 50,
        'macd_hist': round(macd_hist, 4) if macd_hist else 0,
        'z_score': round(z, 3),
        'avg_z': round(avg_z, 3),
        'pct_short': round(pct_short, 1),
        'pct_long': round(pct_long, 1),
        'momentum_state': momentum_state,
        'state_confidence': state_conf,
        'phase': phase,
        'z_direction': z_dir,
        'regime': regime,
        'price_history': prices[:20],  # last 20 candles for trend
    }


def build_prediction_prompt(token_data):
    """Build Ollama prompt with momentum data."""
    d = token_data
    if not d:
        return None
    
    # Build price trend
    ph = d['price_history']
    price_trend = ' → '.join([f"${p:.4f}" for p in ph[:5][::-1]])
    
    # Regime context
    regime_emoji = {'bullish': '📈', 'bearish': '📉', 'neutral': '↔️'}.get(d['regime'], '?')
    
    # Direction bias based on momentum state
    if d['momentum_state'] == 'bullish':
        bias = 'LONG bias (suppressed price catching bid)'
    elif d['momentum_state'] == 'bearish':
        bias = 'SHORT bias (elevated price ripe for reversal)'
    else:
        bias = 'neutral / ranging'
    
    return f"""You are a crypto 4-hour candle direction predictor.

{d['pct_short']:.0f} 4h candles of {d['token']} history + momentum indicators:

LAST PRICE: ${d['price']:.6f}
{d['chg_1h']:+.2f}% in 1h | {d['chg_4h']:+.2f}% in 4h | {d['chg_24h']:+.2f}% in 24h
Price trend (oldest→newest): {price_trend}

MOMENTUM INDICATORS:
- RSI(14): {d['rsi']:.1f} (overbought>70, oversold<30)
- MACD Histogram: {d['macd_hist']:+.4f} (positive=bullish momentum)
- Z-score: {d['z_score']:+.2f} (price vs 20-candle mean; +2=elevated, -2=suppressed)
- Avg Z (multi-TF): {d['avg_z']:+.2f}

HERMES MOMENTUM STATE: {d['momentum_state']} ({d['state_confidence']:.0%} confidence)
Regime: {d['regime']} {regime_emoji}
Phase: {d['phase']} | Z-direction: {d['z_direction']}
Percentile: short={d['pct_short']:.0f}% long={d['pct_long']:.0f}%

Trading bias from Hermes momentum model: {bias}

TASK: Predict whether the NEXT 4-hour candle will close UP or DOWN.
Consider: current momentum, regime, momentum_state, z-score direction, RSI level.

Respond STRICTLY in this format (one line each):
DIRECTION: [UP or DOWN]
CONFIDENCE: [0-100]
MOVE_PCT: [estimated % move, e.g. +1.5 or -0.8]
REASON: [one sentence]
"""


def query_llm(prompt):
    """Query local Ollama."""
    try:
        result = subprocess.run(
            ['curl', '-s', OLLAMA_URL, '-d', json.dumps({
                'model': MODEL,
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0.3, 'num_predict': 80}
            })],
            capture_output=True, text=True, timeout=60
        )
        response = json.loads(result.stdout)
        return response.get('response', '').strip()
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
        'candle_time': int(time.time()) + 14400,  # +4 hours
    }


def store_prediction(conn, pred, token_data):
    """Store prediction in predictions DB."""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO predictions
          (token, direction, confidence, predicted_move_pct, prediction_time,
           candle_time, price_at_prediction, momentum_state, regime)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (pred['token'], pred['direction'], pred['confidence'],
          pred.get('predicted_move_pct'), pred['prediction_time'],
          pred['candle_time'], token_data['price'],
          token_data['momentum_state'], token_data['regime']))
    conn.commit()
    log(f"  → {pred['token']}: {pred['direction']} conf={pred['confidence']} "
        f"move={pred.get('predicted_move_pct', '?')} "
        f"(state={token_data['momentum_state']} regime={token_data['regime']})")


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
    
    # Get current prices
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
        # Log accuracy
        cur.execute("""
            SELECT COUNT(*), SUM(CASE WHEN correct THEN 1 ELSE 0 END)
            FROM predictions WHERE correct IS NOT NULL
        """)
        total, correct = cur.fetchone()
        if total and total > 0:
            acc = correct / total * 100
            log(f"  Overall accuracy: {correct}/{total} = {acc:.1f}%")


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
    
    log("=== Candle Predictor Starting ===")
    
    conn = init_predictions_db()
    
    # 1. Validate old predictions
    validate_predictions(conn)
    
    # 2. Generate new predictions
    predicted = 0
    for token in TOP_TOKENS:
        # Get data
        token_data = get_token_data_for_prediction(token)
        if not token_data:
            log(f"  {token}: no price data, skipping", 'WARN')
            continue
        
        # Check accuracy - skip if model is cold for this token
        acc, n = get_prediction_accuracy(conn, token)
        if acc is not None and acc < 45 and n >= 10:
            log(f"  {token}: low accuracy ({acc:.0f}%/{n}), skipping this round")
            time.sleep(1)
            continue
        
        # Build prompt
        prompt = build_prediction_prompt(token_data)
        if not prompt:
            continue
        
        # Query LLM
        response = query_llm(prompt)
        
        if response:
            pred = parse_prediction(response, token)
            if pred:
                store_prediction(conn, pred, token_data)
                predicted += 1
        
        time.sleep(1.0)  # Ollama rate limit
    
    log(f"=== Predicted {predicted} tokens ===")
    conn.close()
    
    try:
        os.remove(LOCK_FILE)
    except:
        pass


if __name__ == '__main__':
    main()
