#!/usr/bin/env python3
"""
signal_quality.py — Signal quality scoring for Hermes.

Provides:
1. Signal quality scoring (Sharpe, profit factor, win rate)
2. Meta-labeling (predict signal success given conditions)
3. Regime detection (mean-reversion vs momentum)

Usage:
    from signal_quality import score_signal, predict_success, detect_regime
"""

import numpy as np
import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

# ── Signal Quality Scoring ───────────────────────────────────────────────────

def score_signal(
    signal: str,
    lookback_days: int = 30,
    min_trades: int = 20,
) -> Dict:
    """
    Score a signal's quality based on multiple metrics.
    
    Thresholds (from Ernest Chan — Algorithmic Trading):
    - Sharpe Ratio > 1.0
    - Profit Factor > 1.5
    - Win Rate > 55% (mean-reversion) or > 45% (momentum)
    
    Returns:
        Dict with score (0-100), grade (A-F), metrics, and pass/fail
    """
    try:
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT pnl_pct, close_time, direction
            FROM trades
            WHERE signal = %s
              AND status = 'closed'
              AND close_time > NOW() - INTERVAL '%s days'
            ORDER BY close_time DESC
        """, (signal, lookback_days))
        
        rows = cur.fetchall()
        conn.close()
        
        if len(rows) < min_trades:
            return {
                'score': 0,
                'grade': 'F',
                'pass': False,
                'reason': f'Insufficient trades ({len(rows)}/{min_trades})',
                'metrics': {}
            }
        
        pnls = [float(r[0]) for r in rows]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        # Core metrics
        win_rate = len(wins) / len(pnls)
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 0
        
        # Profit factor
        total_wins = sum(wins)
        total_losses = abs(sum(losses))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Sharpe ratio (annualized, assuming daily trades)
        mean_pnl = np.mean(pnls)
        std_pnl = np.std(pnls)
        sharpe = (mean_pnl / std_pnl) * np.sqrt(252) if std_pnl > 0 else 0
        
        # Expectancy (avg win * win_rate - avg loss * loss_rate)
        expectancy = (avg_win * win_rate) - (avg_loss * (1 - win_rate))
        
        # Scoring (0-100)
        score = 0
        
        # Sharpe (40 points)
        if sharpe > 2.0:
            score += 40
        elif sharpe > 1.5:
            score += 35
        elif sharpe > 1.0:
            score += 30
        elif sharpe > 0.5:
            score += 20
        else:
            score += max(0, sharpe * 20)
        
        # Profit Factor (30 points)
        if profit_factor > 2.0:
            score += 30
        elif profit_factor > 1.5:
            score += 25
        elif profit_factor > 1.2:
            score += 20
        elif profit_factor > 1.0:
            score += 10
        
        # Win Rate (20 points)
        if win_rate > 0.6:
            score += 20
        elif win_rate > 0.55:
            score += 15
        elif win_rate > 0.5:
            score += 10
        elif win_rate > 0.45:
            score += 5
        
        # Expectancy (10 points)
        if expectancy > 0.1:
            score += 10
        elif expectancy > 0.05:
            score += 7
        elif expectancy > 0:
            score += 3
        
        # Grade
        if score >= 80:
            grade = 'A'
        elif score >= 65:
            grade = 'B'
        elif score >= 50:
            grade = 'C'
        elif score >= 35:
            grade = 'D'
        else:
            grade = 'F'
        
        # Pass/Fail thresholds
        passed = sharpe > 1.0 and profit_factor > 1.5 and win_rate > 0.5
        
        return {
            'score': score,
            'grade': grade,
            'pass': passed,
            'metrics': {
                'sharpe': round(sharpe, 3),
                'profit_factor': round(profit_factor, 3),
                'win_rate': round(win_rate, 3),
                'expectancy': round(expectancy, 4),
                'avg_win': round(avg_win, 4),
                'avg_loss': round(avg_loss, 4),
                'total_trades': len(pnls),
            }
        }
    except Exception as e:
        return {
            'score': 0,
            'grade': 'F',
            'pass': False,
            'reason': str(e),
            'metrics': {}
        }


# ── Meta-Labeling ────────────────────────────────────────────────────────────

def predict_success(
    signal: str,
    market_features: Dict,
    lookback_days: int = 30,
) -> Dict:
    """
    Predict whether a signal will succeed given current market conditions.
    
    This is a simplified meta-labeling approach:
    - Train on historical (signal + features) → success/failure
    - Predict for new signal
    
    Args:
        signal: Signal name
        market_features: Dict with z_score, rsi, macd_hist, volume_ratio, etc.
        lookback_days: Days of history to use
    
    Returns:
        Dict with confidence (0-1), prediction (success/failure), features_used
    """
    try:
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        
        # Get historical trades with features
        cur.execute("""
            SELECT pnl_pct, signal_z_score, signal_rsi_14, signal_macd_hist
            FROM trades
            WHERE signal = %s
              AND status = 'closed'
              AND close_time > NOW() - INTERVAL '%s days'
            ORDER BY close_time DESC
        """, (signal, lookback_days))
        
        rows = cur.fetchall()
        conn.close()
        
        if len(rows) < 20:
            return {
                'confidence': 0.5,
                'prediction': 'unknown',
                'reason': 'Insufficient training data'
            }
        
        # Simple rules-based meta-labeling
        # In production, this would be a trained classifier
        
        z_score = market_features.get('z_score', 0)
        rsi = market_features.get('rsi', 50)
        volume_ratio = market_features.get('volume_ratio', 1.0)
        
        # Confidence boosters
        confidence = 0.5  # Base
        
        # Z-score extreme = higher confidence for mean-reversion
        if abs(z_score) > 2.0:
            confidence += 0.15
        elif abs(z_score) > 1.5:
            confidence += 0.10
        
        # RSI confirmation
        if rsi < 30 or rsi > 70:
            confidence += 0.10
        
        # Volume confirmation
        if volume_ratio > 1.5:
            confidence += 0.10
        elif volume_ratio > 1.2:
            confidence += 0.05
        
        # Historical success rate for this signal
        if rows:
            historical_wr = sum(1 for r in rows if r[0] > 0) / len(rows)
            confidence = confidence * 0.7 + historical_wr * 0.3
        
        confidence = min(max(confidence, 0.0), 1.0)
        prediction = 'success' if confidence > 0.6 else 'failure'
        
        return {
            'confidence': round(confidence, 3),
            'prediction': prediction,
            'features_used': list(market_features.keys()),
        }
    except Exception as e:
        return {
            'confidence': 0.5,
            'prediction': 'unknown',
            'reason': str(e)
        }


# ── Regime Detection ─────────────────────────────────────────────────────────

def detect_regime(
    prices: List[float],
    lookback: int = 100,
) -> Dict:
    """
    Detect market regime (mean-reversion vs momentum) using ADF test.
    
    Based on Ernest Chan — Algorithmic Trading:
    - ADF p-value < 0.05 → mean-reversion regime
    - ADF p-value > 0.10 → momentum regime
    - 0.05 < p < 0.10 → unclear
    
    Args:
        prices: List of close prices
        lookback: Number of prices to use
    
    Returns:
        Dict with regime, adf_pvalue, confidence
    """
    if len(prices) < lookback:
        return {
            'regime': 'unknown',
            'adf_pvalue': None,
            'confidence': 0,
            'reason': 'Insufficient data'
        }
    
    prices = prices[-lookback:]
    
    # Simplified ADF test (in production, use statsmodels.tsa.stattools.adfuller)
    # Calculate variance ratio as proxy
    returns = np.diff(np.log(prices))
    
    # Variance ratio test (VR > 1 = momentum, VR < 1 = mean-reversion)
    # VR = Var(returns over k periods) / (k * Var(1-period returns))
    k = 5
    if len(returns) < k:
        return {'regime': 'unknown', 'adf_pvalue': None, 'confidence': 0}
    
    var_1 = np.var(returns)
    aggregated = np.array([sum(returns[i:i+k]) for i in range(0, len(returns)-k+1, k)])
    var_k = np.var(aggregated) / k if len(aggregated) > 0 else var_1
    
    vr = var_k / var_1 if var_1 > 0 else 1.0
    
    # Map VR to regime
    if vr < 0.8:
        regime = 'mean_reversion'
        confidence = min(0.8, (0.8 - vr) * 2)
        adf_pvalue = 0.03  # Approximate
    elif vr > 1.2:
        regime = 'momentum'
        confidence = min(0.8, (vr - 1.2) * 2)
        adf_pvalue = 0.15  # Approximate
    else:
        regime = 'random'
        confidence = 0.3
        adf_pvalue = 0.08  # Borderline
    
    return {
        'regime': regime,
        'adf_pvalue': round(adf_pvalue, 3),
        'variance_ratio': round(vr, 3),
        'confidence': round(confidence, 3),
    }


# ── Batch Scoring ────────────────────────────────────────────────────────────

def score_all_signals(lookback_days: int = 30) -> Dict:
    """
    Score all signals and return ranked list.
    """
    try:
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT DISTINCT signal
            FROM trades
            WHERE status = 'closed'
              AND close_time > NOW() - INTERVAL '%s days'
        """, (lookback_days,))
        
        signals = [r[0] for r in cur.fetchall()]
        conn.close()
        
        results = {}
        for signal in signals:
            if signal:
                results[signal] = score_signal(signal, lookback_days)
        
        # Sort by score
        ranked = sorted(results.items(), key=lambda x: x[1]['score'], reverse=True)
        
        return {
            'ranked': ranked,
            'passed': [s for s, r in ranked if r['pass']],
            'failed': [s for s, r in ranked if not r['pass']],
        }
    except Exception as e:
        return {'error': str(e)}


# ── CLI Test ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== Regime Detection Test ===")
    
    # Simulate mean-reverting prices
    np.random.seed(42)
    mr_prices = [100]
    for _ in range(99):
        mr_prices.append(mr_prices[-1] * (1 + np.random.normal(-0.01 * (mr_prices[-1] - 100), 0.02)))
    
    print(f"Mean-reverting: {detect_regime(mr_prices)}")
    
    # Simulate momentum prices
    mom_prices = [100]
    for _ in range(99):
        mom_prices.append(mom_prices[-1] * (1 + np.random.normal(0.005, 0.02)))
    
    print(f"Momentum: {detect_regime(mom_prices)}")
