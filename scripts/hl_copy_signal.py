#!/usr/bin/env python3
"""
HL Copy Trading Signal
Generates signals based on pro trader activity.
Flows into the Hermes signal pipeline.
"""
import time
import json
import os
from datetime import datetime
from hl_copy_db import get_db
from paths import HERMES_DATA
from hermes_constants import (
    HL_COPY_SIGNAL_ENABLED,
    HL_COPY_SIGNAL_MIN_SCORE,
    HL_COPY_SIGNAL_MIN_CONFIDENCE,
    HL_COPY_SIGNAL_MAX_CONFIDENCE,
    HL_COPY_SIGNAL_LOOKBACK_MINUTES,
    HL_COPY_SIGNAL_MAX_PER_CYCLE,
    HL_COPY_CLUSTER_ENABLED,
    HL_COPY_CLUSTER_BONUS_PER_TRADER,
    HL_COPY_CLUSTER_MAX_BONUS,
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
                         trade_side: str, coin: str, copy_weight: float = 1.0,
                         cluster_size: int = 1) -> float:
    """Calculate signal confidence based on trader performance, copy weight, and cluster size.

    Cluster bonus: when multiple pro traders all buy the same coin, it's higher conviction.
    E.g., 3 traders buy BTC → +6 confidence (2 extra traders × 3 each).
    """
    # Base confidence from trader score (0-100)
    base_confidence = min(trader_score, 100)

    # Win rate adjustment
    wr_adjustment = (trader_win_rate - 0.5) * 40  # ±20 points

    # Combine and apply copy weight
    confidence = (base_confidence + wr_adjustment) * copy_weight

    # Cluster bonus: +3 per additional trader beyond the first
    if HL_COPY_CLUSTER_ENABLED and cluster_size > 1:
        cluster_bonus = min(
            HL_COPY_CLUSTER_MAX_BONUS,
            (cluster_size - 1) * HL_COPY_CLUSTER_BONUS_PER_TRADER
        )
        confidence += cluster_bonus

    # Clamp to configured range
    confidence = max(HL_COPY_SIGNAL_MIN_CONFIDENCE, min(HL_COPY_SIGNAL_MAX_CONFIDENCE, confidence))

    return round(confidence, 1)

def generate_hl_signal(trade: dict, trader_score: float, cluster_size: int = 1) -> dict:
    """Generate a signal in Hermes format.

    Args:
        trade: pro trader fill dict
        trader_score: leaderboard score for this trader
        cluster_size: number of pro traders who made the same trade (coin+side)
    """
    # Get trader performance and copy weight
    perf = get_trader_performance(trade['wallet'])
    from hl_leaderboard import compute_copy_weight
    copy_weight = compute_copy_weight(trade['wallet'])

    # Calculate confidence (weighted by copy performance + cluster confluence)
    confidence = calculate_confidence(
        trader_score,
        perf['win_rate'],
        trade['side'],
        trade['coin'],
        copy_weight=copy_weight,
        cluster_size=cluster_size,
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
            'trade_pnl': trade['closed_pnl'],
            'cluster_size': cluster_size,  # how many traders agreed
        }
    }

    return signal

def get_recent_pro_trades(minutes: int = None) -> list:
    """Get recent trades from pro traders.

    FIX (2026-08-22): Deduplicate by coin+direction — only keep the MOST RECENT
    fill per coin+side. Without this, a pro trader buying BTC 3 times in 5 min
    generates 3 separate signals → 3 positions on HL (multi-fire glitch).
    """
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
        # AND deduplicate by coin+side — keep only the most recent fill per coin+direction
        seen = set()  # (coin, side) -> only keep first (most recent due to DESC order)
        tradable = []
        for t in trades:
            if t['coin'].startswith('xyz:'):
                continue
            key = (t['coin'].upper(), t['side'].upper())
            if key in seen:
                continue  # already have a more recent fill for this coin+direction
            seen.add(key)
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
        signal_metadata=signal.get('meta'),  # pass trader_wallet through to trade record
    )

def _get_open_hl_tokens() -> set:
    """Query PostgreSQL for tokens with open positions (defense-in-depth).

    Also checks guardian-closing-markers.json to block tokens the guardian
    is actively closing (same logic as signal_compactor._get_open_tokens).
    """
    tokens = set()
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("SELECT LOWER(token) FROM trades WHERE status='open' AND server='Hermes'")
        tokens = {row[0] for row in cur.fetchall()}
        cur.close(); conn.close()
    except Exception as e:
        print(f"[hl_signal] WARN: Could not query open positions from PostgreSQL: {e}")
        # Fail-open on DB error — but log it so we know the guard is disabled

    # Guardian-closing-markers: tokens the guardian is actively closing on HL
    # (HL position closed but PostgreSQL not yet updated → race window)
    try:
        import json as _json
        from paths import HERMES_DATA
        closing_file = os.path.join(HERMES_DATA, 'guardian-closing-markers.json')
        if os.path.exists(closing_file):
            with open(closing_file) as f:
                data = _json.load(f)
            if isinstance(data, dict):
                guardian_closing = {k.lower() for k in data.get('tokens', {})}
                tokens.update(guardian_closing)
    except Exception:
        pass  # non-fatal

    return tokens


def run_hl_copy_signal():
    """Main function: detect pro trades and generate pipeline signals."""
    if not HL_COPY_SIGNAL_ENABLED:
        return []

    trades = get_recent_pro_trades()

    # Defense-in-depth: skip signals for tokens already open
    open_tokens = _get_open_hl_tokens()

    signals = []
    for trade in trades:
        # Skip if too many signals (avoid noise)
        if len(signals) >= HL_COPY_SIGNAL_MAX_PER_CYCLE:
            break

        # Skip if already have an open position for this coin
        if trade['coin'].lower() in open_tokens:
            print(f"[hl_signal] SKIP {trade['coin']} — already has open position")
            continue

        # Generate signal
        signal = generate_hl_signal(trade, trade['score'])

        # ── Per-direction kill-switch ─────────────────────────────────────────
        try:
            from hermes_constants import HL_COPY_SIGNAL_PLUS_ENABLED, HL_COPY_SIGNAL_MINUS_ENABLED
            if signal['direction'] == 'LONG' and not HL_COPY_SIGNAL_PLUS_ENABLED:
                continue
            if signal['direction'] == 'SHORT' and not HL_COPY_SIGNAL_MINUS_ENABLED:
                continue
        except ImportError:
            pass

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
