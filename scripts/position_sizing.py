#!/usr/bin/env python3
"""
position_sizing.py — Kelly criterion, walk-forward testing, and Phase 1 extensions for Hermes.

Provides:
1. Half-Kelly position sizing based on signal win rate
2. Walk-forward testing with rolling windows
3. Liquidity-adjusted sizing
4. Signal weighting by quality score
5. Drawdown-responsive sizing
6. Portfolio heat limit
7. Conservative mode toggle

Usage:
    from position_sizing import calculate_kelly_size, walk_forward_test, get_signal_weight
"""

import psycopg2
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from _secrets import BRAIN_DB_DICT

# ── Account Equity from HL ───────────────────────────────────────────────────

def get_hl_account_equity() -> float:
    """
    Get current account equity from Hyperliquid API.
    
    Returns:
        Account value in USDT, or 0.0 if unavailable
    """
    try:
        import requests
        from _secrets import HL_MAIN_ACCOUNT as MAIN_ACCOUNT_ADDRESS
        
        resp = requests.post(
            'https://api.hyperliquid.xyz/info',
            json={'type': 'clearinghouseState', 'user': MAIN_ACCOUNT_ADDRESS},
            timeout=10
        )
        if resp.status_code != 200:
            return 0.0
        
        state = resp.json()
        account_value = float(state.get('marginSummary', {}).get('accountValue', 0))
        return account_value
    except Exception as e:
        print(f"[position_sizing] Error getting HL equity: {e}")
        return 0.0


def get_open_positions_value() -> float:
    """
    Get total value of open positions from Hyperliquid.
    
    Returns:
        Total position value in USDT
    """
    try:
        import requests
        from _secrets import HL_MAIN_ACCOUNT as MAIN_ACCOUNT_ADDRESS
        
        resp = requests.post(
            'https://api.hyperliquid.xyz/info',
            json={'type': 'clearinghouseState', 'user': MAIN_ACCOUNT_ADDRESS},
            timeout=10
        )
        if resp.status_code != 200:
            return 0.0
        
        state = resp.json()
        positions = state.get('assetPositions', [])
        
        total_value = 0.0
        for p in positions:
            pos = p.get('position', {})
            szi = float(pos.get('szi', 0))
            entry_px = float(pos.get('entryPx', 0))
            leverage = float(pos.get('leverage', {}).get('value', 1))
            
            if szi != 0 and entry_px > 0:
                # Position value = |size| * entry_price / leverage
                position_value = abs(szi) * entry_px / leverage
                total_value += position_value
        
        return total_value
    except Exception as e:
        print(f"[position_sizing] Error getting positions value: {e}")
        return 0.0


# ── Kelly Criterion ───────────────────────────────────────────────────────────

def calculate_kelly_fraction(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    Calculate Kelly fraction for position sizing.
    
    Formula (from Wikipedia/Kelly criterion):
        f* = p/l - q/g
    
    Where:
        p = probability of winning
        q = probability of losing (1 - p)
        g = gain on win (as decimal, e.g., 0.02 for 2%)
        l = loss on loss (as decimal, e.g., 0.01 for 1%)
    
    Returns: fraction of bankroll to risk (0.0 to 1.0)
    """
    if win_rate <= 0 or win_rate >= 1:
        return 0.0
    if avg_win <= 0 or avg_loss <= 0:
        return 0.0
    
    p = win_rate
    q = 1 - p
    g = avg_win / 100  # Convert from percentage to decimal
    l = avg_loss / 100  # Convert from percentage to decimal (already positive)
    
    # Kelly fraction
    kelly = (p / l) - (q / g)
    
    # Clamp to valid range
    return max(0.0, min(kelly, 1.0))


def calculate_half_kelly(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    Calculate half-Kelly fraction (safer, 50% of full Kelly).
    
    Half-Kelly captures ~75% of the growth rate with ~50% of the volatility.
    """
    full_kelly = calculate_kelly_fraction(win_rate, avg_win, avg_loss)
    return full_kelly * 0.5


def calculate_kelly_size(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    bankroll: float,
    max_position_pct: float = 0.05,  # Max 5% of bankroll per trade
    kelly_fraction: float = 0.25,     # Quarter-Kelly by default
    min_size: float = 11.0,           # HL minimum notional
    max_size: float = 20.0,           # Hard cap
) -> float:
    """
    Calculate position size in USDT using Kelly criterion.
    
    Args:
        win_rate: Win rate as decimal (0.0 to 1.0)
        avg_win: Average winning trade PnL %
        avg_loss: Average losing trade PnL %
        bankroll: Total bankroll in USDT
        max_position_pct: Maximum position size as % of bankroll
        kelly_fraction: Fraction of Kelly to use (0.25 = quarter-Kelly)
        min_size: Minimum position size in USDT (HL minimum = $11)
        max_size: Maximum position size in USDT
    
    Returns:
        Position size in USDT
    """
    kelly = calculate_kelly_fraction(win_rate, avg_win, avg_loss)
    fractional_kelly = kelly * kelly_fraction
    
    # Calculate size
    size = bankroll * fractional_kelly
    
    # Apply constraints
    if bankroll <= 0:
        return 0.0
    max_size = bankroll * max_position_pct
    size = max(min_size, min(size, max_size))
    
    return round(size, 2)


# ── Signal Performance Tracking ──────────────────────────────────────────────

def get_signal_performance(
    signal: str,
    lookback_days: int = 30,
    min_trades: int = 10,
) -> Optional[Dict]:
    """
    Calculate performance metrics for a signal from trade history.
    
    Returns:
        Dict with win_rate, avg_win, avg_loss, total_trades, profit_factor
        or None if insufficient data
    """
    conn = None
    try:
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT pnl_pct, close_time
            FROM trades
            WHERE signal = %s
              AND status = 'closed'
              AND close_time > NOW() - INTERVAL '1 day' * %s
            ORDER BY close_time DESC
        """, (signal, lookback_days))
        
        rows = cur.fetchall()
        
        if len(rows) < min_trades:
            return None
        
        pnls = [float(r[0]) for r in rows]
        wins = [p for p in pnls if p > 0]
        losses = [abs(p) for p in pnls if p < 0]  # Make losses positive
        
        if not wins or not losses:
            return None
        
        win_rate = len(wins) / len(pnls)
        avg_win = np.mean(wins)
        avg_loss = np.mean(losses)  # Now positive
        
        # Profit factor
        total_wins = sum(wins)
        total_losses = sum(losses)
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        return {
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_trades': len(pnls),
            'profit_factor': profit_factor,
            'sharpe': np.mean(pnls) / np.std(pnls) if np.std(pnls) > 0 else 0,
        }
    except Exception as e:
        print(f"[position_sizing] Error getting signal performance: {e}")
        return None
    finally:
        if conn:
            conn.close()


# ── Walk-Forward Testing ─────────────────────────────────────────────────────

def walk_forward_test(
    trades: List[Dict],
    train_pct: float = 0.8,
    step_pct: float = 0.1,
    min_train: int = 30,
    min_test: int = 10,
) -> Dict:
    """
    Walk-forward test with rolling windows.
    
    Splits trades into sequential train/test windows.
    Trains on train_pct, tests on remaining.
    
    Args:
        trades: List of trade dicts with 'pnl_pct' and 'open_time'
        train_pct: Percentage of data for training
        step_pct: Step size for rolling window
        min_train: Minimum trades for training
        min_test: Minimum trades for testing
    
    Returns:
        Dict with per-window results and aggregate metrics
    """
    if len(trades) < min_train + min_test:
        return {'error': 'Insufficient trades', 'total': len(trades)}
    
    # Sort by time
    trades = sorted(trades, key=lambda t: t.get('open_time', ''))
    
    results = []
    n = len(trades)
    window_size = int(n * train_pct)
    step_size = max(1, int(n * step_pct))
    
    for start in range(0, n - window_size - min_test + 1, step_size):
        train = trades[start:start + window_size]
        test_end = min(start + window_size + int(n * (1 - train_pct)), n)
        test = trades[start + window_size:test_end]
        
        if len(test) < min_test:
            continue
        
        # Calculate metrics for train and test
        train_pnls = [t['pnl_pct'] for t in train]
        test_pnls = [t['pnl_pct'] for t in test]
        
        train_wr = sum(1 for p in train_pnls if p > 0) / len(train_pnls)
        test_wr = sum(1 for p in test_pnls if p > 0) / len(test_pnls)
        
        train_sharpe = np.mean(train_pnls) / np.std(train_pnls) if np.std(train_pnls) > 0 else 0
        test_sharpe = np.mean(test_pnls) / np.std(test_pnls) if np.std(test_pnls) > 0 else 0
        
        results.append({
            'window': len(results) + 1,
            'train_size': len(train),
            'test_size': len(test),
            'train_wr': round(train_wr, 3),
            'test_wr': round(test_wr, 3),
            'train_sharpe': round(train_sharpe, 3),
            'test_sharpe': round(test_sharpe, 3),
            'wr_decay': round(train_wr - test_wr, 3),
            'overfitting': test_wr < train_wr * 0.7,  # >30% WR decay = overfitting
        })
    
    if not results:
        return {'error': 'No valid windows'}
    
    # Aggregate
    avg_test_wr = np.mean([r['test_wr'] for r in results])
    avg_test_sharpe = np.mean([r['test_sharpe'] for r in results])
    overfit_pct = sum(1 for r in results if r['overfitting']) / len(results)
    
    return {
        'windows': results,
        'avg_test_wr': round(avg_test_wr, 3),
        'avg_test_sharpe': round(avg_test_sharpe, 3),
        'overfitting_pct': round(overfit_pct, 2),
        'robust': overfit_pct < 0.3,  # <30% overfitting windows = robust
    }


# ── Liquidity-Adjusted Sizing ────────────────────────────────────────────────

def liquidity_adjusted_size(
    base_size: float,
    volume_24h: float,
    min_volume: float = 100000,
    max_reduction: float = 0.5,  # Max 50% reduction
) -> float:
    """
    Adjust position size based on 24h trading volume.
    
    Reduces size for illiquid tokens to minimize slippage.
    
    Args:
        base_size: Base position size in USDT
        volume_24h: 24h trading volume in USDT
        min_volume: Minimum volume threshold
        max_reduction: Maximum size reduction (0.5 = 50%)
    
    Returns:
        Adjusted position size
    """
    if volume_24h >= min_volume:
        return base_size
    
    # Linear reduction
    reduction = 1 - (volume_24h / min_volume)
    reduction = min(reduction, max_reduction)
    
    return round(base_size * (1 - reduction), 2)


# ── Combined Position Sizing ─────────────────────────────────────────────────

def calculate_optimal_size(
    signal: str,
    bankroll: float = None,
    volume_24h: float = 100000,
    lookback_days: int = 30,
    use_hl_equity: bool = True,
) -> float:
    """
    Calculate optimal position size using all factors:
    1. Real account equity from HL API
    2. Kelly criterion based on signal history
    3. Liquidity adjustment
    4. Hard safety limits
    
    Args:
        signal: Signal name
        bankroll: Total bankroll (if None, queries HL API)
        volume_24h: 24h volume
        lookback_days: Days to look back for performance
        use_hl_equity: Whether to query HL for real equity
    
    Returns:
        Optimal position size in USDT
    """
    from hermes_constants import DEFAULT_TRADE_SIZE_USDT
    
    # Get real bankroll from HL if not provided
    if bankroll is None or bankroll <= 0:
        if use_hl_equity:
            bankroll = get_hl_account_equity()
            if bankroll <= 0:
                return DEFAULT_TRADE_SIZE_USDT
        else:
            return DEFAULT_TRADE_SIZE_USDT
    
    # Get signal performance
    perf = get_signal_performance(signal, lookback_days)
    
    # Safety: need enough history for Kelly
    if perf and perf['total_trades'] >= 20:
        # Use Kelly sizing
        kelly_size = calculate_kelly_size(
            win_rate=perf['win_rate'],
            avg_win=perf['avg_win'],
            avg_loss=perf['avg_loss'],
            bankroll=bankroll,
        )
        
        # Apply liquidity adjustment
        adjusted_size = liquidity_adjusted_size(kelly_size, volume_24h)
        
        return adjusted_size
    else:
        # Fall back to default with liquidity adjustment
        return liquidity_adjusted_size(DEFAULT_TRADE_SIZE_USDT, volume_24h)


# ── Phase 1 Extensions ────────────────────────────────────────────────────────

# 1. Signal Weighting by Quality Score
def get_signal_weight(grade: str) -> float:
    """
    Get position size multiplier based on signal quality grade.
    
    Grades from signal_quality.py:
    - A: 80+ score (strong edge)
    - B: 65-79 score (good edge)
    - C: 50-64 score (moderate edge)
    - D: 35-49 score (weak edge)
    - F: <35 score (no edge)
    
    Returns:
        Multiplier (0.5 to 1.5)
    """
    weights = {
        'A': 1.5,   # Strong edge — full position
        'B': 1.2,   # Good edge — slight boost
        'C': 1.0,   # Moderate — standard size
        'D': 0.8,   # Weak — reduce size
        'F': 0.5,   # No edge — minimal size
    }
    return weights.get(grade, 1.0)


def get_signal_quality(signal: str) -> str:
    """
    Get signal quality grade from signal_quality module.
    
    Returns:
        Grade (A-F) or 'C' if unavailable
    """
    try:
        from signal_quality import score_signal
        result = score_signal(signal)
        return result.get('grade', 'C')
    except Exception:
        return 'C'


# 2. Drawdown-Responsive Sizing
def get_peak_equity() -> float:
    """
    Get peak equity from HL API.
    
    Returns:
        Peak equity in USDT
    """
    try:
        import requests
        from _secrets import HL_MAIN_ACCOUNT as MAIN_ACCOUNT_ADDRESS
        
        # For now, use current equity as peak
        # TODO: Store peak_equity in database
        return get_hl_account_equity()
    except Exception:
        return 0.0


def get_drawdown_multiplier(equity: float, peak_equity: float) -> float:
    """
    Calculate position size multiplier based on drawdown.
    
    Tiers:
    - <5% drawdown: full size (1.0x)
    - 5-10% drawdown: half size (0.5x)
    - >10% drawdown: quarter size (0.25x)
    
    Returns:
        Multiplier (0.25 to 1.0)
    """
    if peak_equity <= 0:
        return 1.0
    
    drawdown = (peak_equity - equity) / peak_equity
    
    if drawdown > 0.10:  # 10% drawdown
        return 0.25
    elif drawdown > 0.05:  # 5% drawdown
        return 0.50
    return 1.0


# 3. Portfolio Heat Limit
def calculate_portfolio_heat(positions: list) -> float:
    """
    Calculate total portfolio risk (heat).
    
    Heat = sum of (size * stop_distance_pct) for all positions.
    
    Args:
        positions: List of position dicts with 'size', 'entry', 'stop_loss'
    
    Returns:
        Total heat as decimal (0.0 to 1.0)
    """
    total_heat = 0.0
    
    for pos in positions:
        size = pos.get('size', 0)
        entry = pos.get('entry', 0)
        stop_loss = pos.get('stop_loss', 0)
        
        if entry > 0 and stop_loss > 0 and size > 0:
            stop_distance = abs(entry - stop_loss) / entry
            total_heat += size * stop_distance
    
    return total_heat


def can_open_position(
    new_size: float,
    new_stop_distance: float,
    current_heat: float,
    max_heat: float = 0.15,
) -> bool:
    """
    Check if we can open a new position without exceeding heat limit.
    
    Args:
        new_size: Size of new position
        new_stop_distance: Stop distance as decimal (e.g., 0.02 for 2%)
        current_heat: Current portfolio heat
        max_heat: Maximum allowed heat (default 15%)
    
    Returns:
        True if position can be opened
    """
    new_heat = new_size * new_stop_distance
    return (current_heat + new_heat) <= max_heat


# 4. Conservative Mode Toggle
def apply_conservative_mode(size: float) -> float:
    """
    Apply conservative mode multiplier if enabled.
    
    Conservative mode reduces all position sizes by 50%.
    Useful during uncertainty periods or high volatility.
    
    Returns:
        Adjusted size
    """
    try:
        from hermes_constants import CONSERVATIVE_MODE_ENABLED, CONSERVATIVE_MODE_MULTIPLIER
        if CONSERVATIVE_MODE_ENABLED:
            return size * CONSERVATIVE_MODE_MULTIPLIER
    except ImportError:
        pass
    return size


# ── Combined Position Sizing (Updated) ────────────────────────────────────────

def calculate_optimal_size_v2(
    signal: str,
    volume_24h: float = 100000,
    positions: list = None,
    lookback_days: int = 30,
) -> Dict:
    """
    Calculate optimal position size using all Phase 1 factors:
    1. Kelly criterion based on signal history
    2. Signal quality weighting
    3. Drawdown-responsive sizing
    4. Portfolio heat limit
    5. Liquidity adjustment
    6. Conservative mode
    
    Returns:
        Dict with size, factors, and whether position can be opened
    """
    from hermes_constants import (
        DEFAULT_TRADE_SIZE_USDT, KELLY_ENABLED,
        KELLY_MIN_POSITION_USDT, KELLY_MAX_POSITION_USDT,
        MAX_PORTFOLIO_HEAT,
    )
    
    # Get base size
    if KELLY_ENABLED:
        base_size = calculate_optimal_size(signal, volume_24h=volume_24h, lookback_days=lookback_days)
    else:
        base_size = DEFAULT_TRADE_SIZE_USDT
    
    # Get signal quality grade
    grade = get_signal_quality(signal)
    quality_weight = get_signal_weight(grade)
    
    # Apply quality weighting
    size = base_size * quality_weight
    
    # Apply drawdown-responsive sizing
    equity = get_hl_account_equity()
    peak = get_peak_equity()
    dd_multiplier = get_drawdown_multiplier(equity, peak)
    size *= dd_multiplier
    
    # Apply liquidity adjustment
    size = liquidity_adjusted_size(size, volume_24h)
    
    # Apply conservative mode
    size = apply_conservative_mode(size)
    
    # Apply hard limits
    size = max(KELLY_MIN_POSITION_USDT, min(size, KELLY_MAX_POSITION_USDT))
    
    # Check portfolio heat
    can_open = True
    current_heat = 0.0
    if positions:
        current_heat = calculate_portfolio_heat(positions)
        # Estimate stop distance (default 2%)
        stop_distance = 0.02
        can_open = can_open_position(size, stop_distance, current_heat, MAX_PORTFOLIO_HEAT)
    
    return {
        'size': round(size, 2),
        'grade': grade,
        'quality_weight': quality_weight,
        'dd_multiplier': dd_multiplier,
        'current_heat': round(current_heat, 4),
        'can_open': can_open,
        'equity': round(equity, 2),
    }


# ── CLI Test ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    # Test Kelly calculation
    print("=== Kelly Criterion Tests ===")
    print(f"Win rate 60%, avg win 2%, avg loss 1%: {calculate_kelly_fraction(0.6, 2.0, 1.0):.3f}")
    print(f"Win rate 55%, avg win 1.5%, avg loss 1%: {calculate_kelly_fraction(0.55, 1.5, 1.0):.3f}")
    print(f"Win rate 50%, avg win 1%, avg loss 1%: {calculate_kelly_fraction(0.5, 1.0, 1.0):.3f}")
    
    print("\n=== Half-Kelly Size Tests ===")
    print(f"$1000 bankroll, 60% WR, 2% avg win, 1% avg loss: ${calculate_kelly_size(0.6, 2.0, 1.0, 1000)}")
    print(f"$1000 bankroll, 55% WR, 1.5% avg win, 1% avg loss: ${calculate_kelly_size(0.55, 1.5, 1.0, 1000)}")
    
    print("\n=== Liquidity Adjustment ===")
    print(f"$10 base, $100k volume: ${liquidity_adjusted_size(10, 100000)}")
    print(f"$10 base, $50k volume: ${liquidity_adjusted_size(10, 50000)}")
    print(f"$10 base, $10k volume: ${liquidity_adjusted_size(10, 10000)}")
    
    print("\n=== Signal Weighting ===")
    for grade in ['A', 'B', 'C', 'D', 'F']:
        print(f"Grade {grade}: {get_signal_weight(grade)}x")
    
    print("\n=== Drawdown Multiplier ===")
    print(f"$100 equity, $100 peak (0% DD): {get_drawdown_multiplier(100, 100)}")
    print(f"$95 equity, $100 peak (5% DD): {get_drawdown_multiplier(95, 100)}")
    print(f"$85 equity, $100 peak (15% DD): {get_drawdown_multiplier(85, 100)}")
    
    print("\n=== Portfolio Heat ===")
    positions = [
        {'size': 11, 'entry': 100, 'stop_loss': 98},  # 2% stop
        {'size': 11, 'entry': 50, 'stop_loss': 49},   # 2% stop
    ]
    heat = calculate_portfolio_heat(positions)
    print(f"2 positions, 2% stops: heat={heat:.4f}")
    print(f"Can open $11 more (2% stop)? {can_open_position(11, 0.02, heat)}")
    
    print("\n=== Conservative Mode ===")
    print(f"$11 base, conservative OFF: ${apply_conservative_mode(11)}")
