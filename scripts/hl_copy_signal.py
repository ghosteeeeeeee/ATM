#!/usr/bin/env python3
"""
HL Copy Trading Signal
Generates signals based on pro trader activity.
Flows into the Hermes signal pipeline.
"""
import time
import json
from datetime import datetime
from hl_copy_db import get_db
from paths import HERMES_DATA
from hermes_constants import (
    HL_COPY_SIGNAL_ENABLED,
    HL_COPY_SIGNAL_MIN_SCORE,
    HL_COPY_SIGNAL_MIN_CONFIDENCE,
    HL_COPY_SIGNAL_MAX_CONFIDENCE,
    HL_COPY_SIGNAL_LOOKBACK_MINUTES,
    HL_COPY_SIGNAL_MAX_PER_CYCLE
)

def get_trader_performance(wallet: str) -> dict:
    """Get trader's historical performance for confidence calculation."""
    conn = get_db()
    try:
        # Get recent trades (last 100)
        trades = conn.execute("""
            SELECT closed_pnl, is_open FROM trader_fills
            WHERE wallet = ? AND closed_pnl != 0
            ORDER BY time DESC LIMIT 100
        """, (wallet,)).fetchall()
        
        if not trades:
            return {'win_rate': 0.5, 'avg_pnl': 0, 'trade_count': 0}
        
        wins = sum(1 for t in trades if t['closed_pnl'] > 0)
        total = len(trades)
        win_rate = wins / total if total > 0 else 0.5
        avg_pnl = sum(t['closed_pnl'] for t in trades) / total if total > 0 else 0
        
        return {
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'trade_count': total
        }
    finally:
        conn.close()

def calculate_confidence(trader_score: float, trader_win_rate: float, 
                         trade_side: str, coin: str) -> float:
    """Calculate signal confidence based on trader performance."""
    # Base confidence from trader score (0-100)
    base_confidence = min(trader_score, 100)
    
    # Win rate adjustment
    wr_adjustment = (trader_win_rate - 0.5) * 40  # ±20 points
    
    # Combine
    confidence = base_confidence + wr_adjustment
    
    # Clamp to configured range
    confidence = max(HL_COPY_SIGNAL_MIN_CONFIDENCE, min(HL_COPY_SIGNAL_MAX_CONFIDENCE, confidence))
    
    return round(confidence, 1)

def generate_hl_signal(trade: dict, trader_score: float) -> dict:
    """Generate a signal in Hermes format."""
    # Get trader performance
    perf = get_trader_performance(trade['wallet'])
    
    # Calculate confidence
    confidence = calculate_confidence(
        trader_score, 
        perf['win_rate'],
        trade['side'],
        trade['coin']
    )
    
    # Determine direction
    direction = 'LONG' if trade['side'] == 'B' else 'SHORT'
    
    # Create signal
    signal = {
        'coin': trade['coin'],
        'signal_type': f'hl_copy_{"plus" if direction == "LONG" else "minus"}',
        'direction': direction,
        'confidence': confidence,
        'price': trade['px'],
        'timestamp': int(time.time() * 1000),
        'source': 'hl_copy_trader',
        'meta': {
            'trader_wallet': trade['wallet'],
            'trader_score': trader_score,
            'trader_win_rate': perf['win_rate'],
            'trade_size': trade['sz'],
            'trade_pnl': trade['closed_pnl']
        }
    }
    
    return signal

def get_recent_pro_trades(minutes: int = None) -> list:
    """Get recent trades from pro traders."""
    if minutes is None:
        minutes = HL_COPY_SIGNAL_LOOKBACK_MINUTES
    
    conn = get_db()
    try:
        cutoff = int(time.time() * 1000) - (minutes * 60 * 1000)
        
        # Get all trades from pro traders
        trades = conn.execute("""
            SELECT f.*, t.score
            FROM trader_fills f
            JOIN traders t ON f.wallet = t.wallet
            WHERE f.time > ? AND t.score >= ?
            ORDER BY f.time DESC
        """, (cutoff, HL_COPY_SIGNAL_MIN_SCORE)).fetchall()
        
        # Filter to only tradable coins (exclude xyz: HIP-3 stocks)
        tradable = []
        for t in trades:
            if not t['coin'].startswith('xyz:'):
                tradable.append(dict(t))
        
        return tradable
    finally:
        conn.close()

def write_signal_to_pipeline(signal: dict):
    """Write signal to the signals database via add_signal() for pipeline processing."""
    from signal_schema import add_signal
    
    add_signal(
        token=signal['coin'],
        direction=signal['direction'],
        signal_type=signal['signal_type'],
        source=signal['source'],
        confidence=signal['confidence'],
        value=signal.get('trade_size'),
        price=signal['price'],
        exchange='hyperliquid',
        timeframe='1h',
    )

def run_hl_copy_signal():
    """Main function: detect pro trades and generate pipeline signals."""
    if not HL_COPY_SIGNAL_ENABLED:
        return []
    
    trades = get_recent_pro_trades()
    
    signals = []
    for trade in trades:
        # Skip if too many signals (avoid noise)
        if len(signals) >= HL_COPY_SIGNAL_MAX_PER_CYCLE:
            break
        
        # Generate signal
        signal = generate_hl_signal(trade, trade['score'])
        
        # Write to pipeline
        write_signal_to_pipeline(signal)
        signals.append(signal)
        
        print(f"[hl_signal] {trade['coin']} {trade['side']} | "
              f"Score: {trade['score']} | Conf: {signal['confidence']}")
    
    return signals

if __name__ == "__main__":
    print("[hl_signal] Running HL copy trading signal generator...")
    signals = run_hl_copy_signal()
    print(f"\n[hl_signal] Generated {len(signals)} signals for pipeline")
