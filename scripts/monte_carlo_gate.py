#!/usr/bin/env python3
"""Monte Carlo Signal Gate — detects signal decay and blocks unprofitable signal types.

Uses resampled trade history to estimate P(profitability) for each
(signal_type, direction) pair. Blocks signals when the edge is gone.

Data source: signal_outcomes table (signals_hermes_runtime.db)
"""
import sqlite3
import time
import random
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from paths import RUNTIME_DB

# ── Config ──────────────────────────────────────────────────────────────
MC_SAMPLE_SIZE = 25          # last N trades per signal type
MC_N_RESAMPLES = 1000        # Monte Carlo iterations
MC_MIN_TRADES = 10           # below this, allow (insufficient history)
MC_PROFIT_THRESHOLD = 0.35    # P(profit) must exceed 35%
MC_CACHE_TTL = 300           # cache stats for 5 min per key

# ── Cache ───────────────────────────────────────────────────────────────
_cache = {}  # key -> (timestamp, result_dict)


def _get_returns(signal_type: str, direction: str, limit: int = MC_SAMPLE_SIZE) -> list:
    """Fetch last N trade returns from signal_outcomes."""
    conn = None
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT pnl_usdt
            FROM signal_outcomes
            WHERE signal_type = ? AND direction = ? AND trade_id IS NOT NULL
            ORDER BY created_at DESC
            LIMIT ?
        """, (signal_type, direction, limit))
        rows = cur.fetchall()
        return [float(r[0]) if r[0] is not None else 0.0 for r in rows]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def monte_carlo_gate(signal_type: str, direction: str) -> tuple:
    """Run Monte Carlo simulation to estimate if a signal type is still profitable.

    Returns:
        (allow_trade: bool, stats: dict)
        stats contains: p_profit, expected_return, ci_lower, ci_upper, sample_size
    """
    cache_key = f"{signal_type}:{direction}"

    # Check cache
    if cache_key in _cache:
        cached_ts, cached_result = _cache[cache_key]
        if time.time() - cached_ts < MC_CACHE_TTL:
            return cached_result.get('allow', True), cached_result

    # Fetch returns
    returns = _get_returns(signal_type, direction, MC_SAMPLE_SIZE)
    n = len(returns)

    # Insufficient data — allow (can't judge yet)
    if n < MC_MIN_TRADES:
        result = {
            'allow': True,
            'p_profit': None,
            'expected_return': None,
            'ci_lower': None,
            'ci_upper': None,
            'sample_size': n,
            'reason': 'insufficient_data'
        }
        _cache[cache_key] = (time.time(), result)
        return True, result

    # Monte Carlo resampling (local RNG — no global state mutation)
    _rng = random.Random(42)
    portfolio_returns = []
    profitable_count = 0

    for _ in range(MC_N_RESAMPLES):
        # Sample with replacement (same length as original)
        sample = _rng.choices(returns, k=n)
        total_return = sum(sample)
        portfolio_returns.append(total_return)
        if total_return > 0:
            profitable_count += 1

    # Compute stats
    p_profit = profitable_count / MC_N_RESAMPLES
    portfolio_returns.sort()
    expected_return = portfolio_returns[MC_N_RESAMPLES // 2]  # median
    ci_lower = portfolio_returns[int(MC_N_RESAMPLES * 0.05)]   # 5th percentile
    ci_upper = portfolio_returns[int(MC_N_RESAMPLES * 0.95)]   # 95th percentile

    allow = p_profit >= MC_PROFIT_THRESHOLD
    result = {
        'allow': allow,
        'p_profit': round(p_profit, 3),
        'expected_return': round(expected_return, 4),
        'ci_lower': round(ci_lower, 4),
        'ci_upper': round(ci_upper, 4),
        'sample_size': n,
        'reason': 'below_threshold' if not allow else 'passed'
    }

    # Cache
    _cache[cache_key] = (time.time(), result)
    return allow, result


def monte_carlo_gate_oracle(signal_type: str, direction: str, force: bool = False) -> tuple:
    """Shadow-mode wrapper — always allows but logs what WOULD have been blocked.

    Use during rollout to validate thresholds before enforcing.
    Set force=True to actually block (switch to enforcement mode).
    """
    allow, stats = monte_carlo_gate(signal_type, direction)

    if not allow:
        tag = 'BLOCK' if force else 'SHADOW'
        print(f"[mc_gate] {tag} {signal_type} {direction} "
              f"p_profit={stats['p_profit']:.2f} "
              f"ci=[{stats['ci_lower']:.2f}, {stats['ci_upper']:.2f}] "
              f"n={stats['sample_size']}", flush=True)

    if force:
        return allow, stats
    else:
        # Shadow mode — always allow
        return True, stats


# ── Standalone test ─────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys as _sys
    if len(_sys.argv) >= 3:
        sig_type = _sys.argv[1]
        direc = _sys.argv[2].upper()
        allow, stats = monte_carlo_gate(sig_type, direc)
        print(f"Signal: {sig_type} {direc}")
        print(f"  Allow: {allow}")
        print(f"  P(profit): {stats.get('p_profit', 'N/A')}")
        print(f"  Expected return: {stats.get('expected_return', 'N/A')}")
        print(f"  95% CI: [{stats.get('ci_lower', 'N/A')}, {stats.get('ci_upper', 'N/A')}]")
        print(f"  Sample size: {stats.get('sample_size', 'N/A')}")
    else:
        print("Usage: python3 monte_carlo_gate.py <signal_type> <direction>")
        print("  e.g.: python3 monte_carlo_gate.py tl_break SHORT")
