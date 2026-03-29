#!/usr/bin/env python3
"""AI-Powered Signal Decider - Signal evaluation and routing"""
import sys, os, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import get_confluence_signals, approve_signal, mark_signal_executed, set_cooldown, get_cooldown, init_db
import requests
from datetime import datetime

LOG_FILE = '/root/.hermes/logs/signal-decider.log'

def log(msg, level='INFO'):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{timestamp}] [{level}] [signal-decider] {msg}')
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(f'[{timestamp}] [{level}] {msg}\n')
    except: pass

def get_market_context():
    ctx = []
    try:
        r = requests.get('https://api.alternative.me/fng/?limit=1', timeout=5)
        fear = r.json()['data'][0]
        ctx.append(f"Fear & Greed: {fear['value']} ({fear['value_classification']})")
    except Exception as e:
        log(f'get_fear error: {e}', 'WARN')
    
    try:
        r = requests.get('https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair=BTC_USDT&interval=4h&limit=10', timeout=10)
        candles = r.json()
        if len(candles) >= 2:
            change = (float(candles[-1][2]) - float(candles[0][2])) / float(candles[0][2]) * 100
            ctx.append(f"BTC 4h trend: {change:+.1f}%")
    except Exception as e:
        log(f'gateio_btc_trend error: {e}', 'WARN')
    
    # Get Z-score market trend for Hyperliquid tokens
    try:
        with open('/root/.openclaw/workspace/data/zscore_exports/latest_signals.txt', 'r') as f:
            content = f.read()
        
        # Count negative vs positive z-scores for key tokens
        tokens = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOT', 'AVAX', 'UNI', 'ATOM']
        neg_count = 0
        pos_count = 0
        
        for token in tokens:
            # Look for token in signals (format: 📉 SELL SIGNAL: TOKENUSDT z=-2.33)
            import re
            match = re.search(rf'{token}USDT.*z=([-+]?\d+\.?\d*)', content)
            if match:
                z = float(match.group(1))
                if z < 0:
                    neg_count += 1
                else:
                    pos_count += 1
        
        total = neg_count + pos_count
        if total > 0:
            down_pct = neg_count / total * 100
            trend_status = "DOWNTREND (favorable for SHORT)" if down_pct >= 60 else "UPTREND (risky for SHORT)" if down_pct <= 40 else "NEUTRAL"
            ctx.append(f"Market Z-Score: {neg_count}/{total} negative - {trend_status}")
    except Exception as e:
        log(f'market_zscore error: {e}', 'WARN')
    
    return "\n".join(ctx)

def ask_ai(token, direction, signals, market, confidence, z_score_tier=None, z_score=None):
    """Ask AI for trading decision via Ollama."""
    import re
    momentum_context = ""
    if z_score_tier:
        momentum_context = f"\nZ-Score Momentum State: {z_score_tier}"
        if z_score is not None:
            momentum_context += f" (current z={z_score:.2f})"
            
            # Add tier-specific trading guidance
            if z_score_tier == "accelerating_long":
                momentum_context += " - Momentum ACCELERATING → Strong LONG signal"
            elif z_score_tier == "accelerating_short":
                momentum_context += " - Momentum ACCELERATING → Strong SHORT signal"
            elif z_score_tier == "momentum_tracking":
                momentum_context += " - Above 2.0 but not yet entered → Track for entry"
            elif z_score_tier == "momentum_tracking_short":
                momentum_context += " - Below -2.0 but not yet entered → Track for entry"
            elif z_score_tier == "decelerating_from_long":
                momentum_context += " - Z dropped from >2.0 to <1.5 → SHORT opportunity (momentum fading)"
            elif z_score_tier == "decelerating_from_short":
                momentum_context += " - Z rose from <-2.0 to >-1.5 → LONG opportunity (momentum fading)"
            elif z_score_tier == "exhaustion":
                momentum_context += " - Z > 3.0 EXHAUSTION → Look for exit/SHORT counter-trend"
            elif z_score_tier == "exhaustion_short_only":
                momentum_context += " - Z > 3.5 EXTREME → Short only (counter-trend)"
            elif z_score_tier == "exhaustion_long":
                momentum_context += " - Z < -3.0 EXHAUSTION → Look for exit/LONG counter-trend"
            elif z_score_tier == "exhaustion_long_only":
                momentum_context += " - Z < -3.5 EXTREME → Long only (counter-trend)"
    
    prompt = f"""DECISION ONLY. No analysis.

Token: {token}
Direction: {direction}
Confidence: {confidence}%
Signals: {signals[:100]}
{momentum_context}

Market: {market[:80]}

RULES:
- {confidence}%+ confidence = APPROVE unless price already moved 5% in trade direction
- Market is in +5.8% uptrend (bullish)
- Z-Score > 2.5 or < -2.5 = Accelerating momentum (favorable)
- Z-Score > 3.0 or < -3.0 = Exhaustion zone (caution - possible reversal)
- Just say YES or NO, then one word reason

OUTPUT FORMAT:
DECISION: YES
REASON: [one word]
"""
    try:
        resp = requests.post('http://127.0.0.1:11434/api/chat', json={
            "model": "qwen2.5:1.5b",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }, timeout=30)
        if resp.status_code == 200:
            return resp.json().get('message', {}).get('content', "DECISION: NO")
    except requests.exceptions.Timeout:
        log(f'ask_ai: timeout after 30s', 'WARN')
    except Exception as e:
        log(f'ask_ai error: {e}', 'WARN')
    return "DECISION: NO"

def run():
    log("=== Signal Decider Started ===")
    market = get_market_context()
    log(f"Context: {market[:100]}...")

    # Get signals from signal_schema (single source of truth)
    init_db()
    confluence = get_confluence_signals(hours=24)

    log(f"Evaluating {len(confluence)} signals")

    # Auto-approve threshold - skip AI for high confidence
    AUTO_APPROVE_THRESHOLD = 80

    # Track repeated signals - if same token keeps appearing, increase confidence
    token_signal_count = {}

    for sig in confluence:
        token = sig['token']
        direction = sig['direction']
        confidence = sig['final_confidence']

        # Track signal count for repeated signals
        key = f"{token}:{direction}"
        token_signal_count[key] = token_signal_count.get(key, 0) + 1

        # If signal keeps coming, that's CONFLUENCE - boost confidence
        if token_signal_count[key] >= 2:
            confidence = min(95, confidence + token_signal_count[key] * 5)
            sig['final_confidence'] = confidence
            log(f"🔄 {token} signal #{token_signal_count[key]} - boosting confidence to {confidence:.0f}%")

        # Check cooldown only for FIRST signal
        if token_signal_count[key] == 1 and get_cooldown(token, direction):
            log(f"Skip {token} - cooldown active")
            continue

        signal_types = ', '.join(sig.get('signal_types', []))
        z_tier = sig.get('z_score_tier')
        z = sig.get('z_score')
        log(f"\n--- {token} {direction} ({confidence:.0f}%) ---")
        log(f"  Signals: {signal_types}")
        if z_tier:
            log(f"  Z-Score Tier: {z_tier} (z={z})")

        # Auto-approve high confidence, skip slow AI call
        if confidence >= AUTO_APPROVE_THRESHOLD:
            log(f"✅ AUTO-APPROVED: {token} (confidence {confidence:.0f}% >= {AUTO_APPROVE_THRESHOLD}%)")
            # Mark as approved in DB so decider-run picks it up
            approve_signal(token, direction)
            log(f"   → {token} {direction} ready for execution")
            continue

        response = ask_ai(token, direction, signal_types, market, confidence, z_tier, z)
        log(f"AI: {response[:100]}...")

        if "YES" in response.upper():
            log(f"✅ APPROVED: {token}")
            approve_signal(token, direction)
            log(f"   → {token} {direction} ready for execution")
        else:
            log(f"❌ REJECTED: {token}")

    log("=== Done ===")

if __name__ == '__main__':
    run()
