#!/usr/bin/env python3
"""
ema20_50_signals.py — Trend-Filtered EMA Pullback Signal on 1m prices.

Trend filter:  EMA20 > EMA50 = bullish bias only | EMA20 < EMA50 = bearish bias only.
Entry:         Pullback to EMA20 (price retraces to or slightly through EMA20).
Confirmation:  3-bar close reversal (close-only pattern) + RSI gate.
  Bullish:  pullback bar closes higher than prior bar, prior bar had lower close than its predecessor.
  Bearish:  pullback bar closes lower than prior bar, prior bar had higher close than its predecessor.
  RSI:      LONG = rising from >30 (ideal 40-55) | SHORT = falling from <70 (ideal 45-60).
Enter:        Next candle open or break above/below confirmation candle.

Signal types:
  - ema20_50_long  : bullish pullback to EMA20 with close-reversal + RSI confirmation
  - ema20_50_short : bearish pullback to EMA20 with close-reversal + RSI confirmation

Architecture:
  price_history (1m closes, fresh every minute) → EMA(20) + EMA(50) + RSI(14)
  → signal_schema.add_signal() → signals_hermes_runtime.db
  → signal_compactor → hotset.json → guardian → HL
"""

import sys
import os
import sqlite3
import time
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal

# ── Paths ─────────────────────────────────────────────────────────────────────
_RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'
_PRICE_DB   = '/root/.hermes/data/signals_hermes.db'   # price_history — live 1m closes

# ── Signal constants ──────────────────────────────────────────────────────────
PERIOD_EMA_FAST   = 20   # fast EMA period
PERIOD_EMA_SLOW   = 50   # slow EMA period
PERIOD_RSI        = 14   # RSI period
COOLDOWN_MINUTES  = 15   # minutes between signals per token
LOOKBACK_1M       = 300  # 1m prices to fetch (enough for warmup + EMA50 + RSI)
MIN_VALID_BARS    = 60   # Minimum valid bars before signals fire

# RSI entry gates
RSI_BULL_GATE    = 30   # RSI must be above this
RSI_BULL_IDEAL   = (40, 55)  # ideal RSI range for bullish entry
RSI_BEAR_GATE    = 70   # RSI must be below this
RSI_BEAR_IDEAL   = (45, 60)  # ideal RSI range for bearish entry

# Pullback tolerance: fraction of bar range to consider price "at EMA20"
# bar range = |close - prior_close| as proxy (close-only; higher = more volatile)
PULLBACK_TOL_PCT = 0.015  # 1.5% of bar-range proxy

# Signal type names
SIGNAL_TYPE_LONG  = 'ema20_50_long'
SIGNAL_TYPE_SHORT = 'ema20_50_short'
SOURCE_LONG       = 'em20-long'
SOURCE_SHORT      = 'em20-short'

# Confidence bounds
MIN_CONFIDENCE    = 52
MAX_CONFIDENCE    = 82


# ═══════════════════════════════════════════════════════════════════════════════
# Indicator helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _ema_series(values: list, period: int) -> list:
    """Return EMA series (oldest first), None for indices < period-1."""
    if len(values) < period:
        return [None] * len(values)
    k = 2.0 / (period + 1)
    result = [None] * (period - 1)
    ema_val = sum(values[:period]) / period
    result.append(ema_val)
    for price in values[period:]:
        ema_val = price * k + ema_val * (1 - k)
        result.append(ema_val)
    return result


def _rsi_at(closes: list, idx: int) -> Optional[float]:
    """
    Compute RSI(14) at index idx using closes[:idx+1].
    Returns None if insufficient data.
    """
    period = PERIOD_RSI
    if idx < period:
        return None
    relevant = closes[:idx + 1]
    if len(relevant) < period + 1:
        return None
    deltas = [relevant[i+1] - relevant[i] for i in range(len(relevant) - 1)]
    gains  = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    return 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))


# ═══════════════════════════════════════════════════════════════════════════════
# 3-bar close-based reversal pattern (no wicks needed)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Pattern logic (close-only approximation of a wick-based rejection):
#
# Bullish reversal (3-bar V-bottom):
#   Bar j-2 (index idx-2): prior bar — establishes trend was moving up before pullback
#   Bar j-1 (index idx-1): pullback bar — price drops toward EMA20
#   Bar j  (index idx)   : reversal bar — price bounces, close > prior close
#
#   Conditions:
#     - closes[idx-2] > closes[idx-1]          (momentum was up before pullback)
#     - closes[idx] > closes[idx-1]            (reversal: close higher than pullback bar)
#     - closes[idx] > closes[idx-2] - (closes[idx-2] - closes[idx-1]) * 0.5
#                                              (bounce recovers > 50% of prior drop)
#
# Bearish reversal (3-bar A-top):
#   Bar j-2 (index idx-2): prior bar — establishes trend was moving down before pullback
#   Bar j-1 (index idx-1): pullback bar — price rises toward EMA20
#   Bar j  (index idx)   : reversal bar — price drops, close < prior close
#
#   Conditions:
#     - closes[idx-2] < closes[idx-1]          (momentum was down before pullback)
#     - closes[idx] < closes[idx-1]            (reversal: close lower than pullback bar)
#     - closes[idx] < closes[idx-2] - (closes[idx-2] - closes[idx-1]) * 0.5
#                                              (drop declines > 50% of prior rise)
#
# Rationale: the key signal is that price pulled back to EMA (directional move was
# exhausted) and is now reversing. With only closes, the 3-bar pattern captures a
# micro-V-bottom or micro-A-top at the EMA rather than requiring intrabar wick data.

def _is_bullish_reversal(closes: list, idx: int) -> bool:
    """
    Bullish 3-bar close reversal at index idx.
    Prior bar shows pullback (lower close), current bar closes higher (bounce).
    """
    if idx < 2:
        return False
    c0 = closes[idx]      # reversal bar
    c1 = closes[idx - 1]  # pullback bar
    c2 = closes[idx - 2]  # prior bar (trend was still up)

    # Momentum was up before pullback
    if c2 <= c1:
        return False
    # Reversal: close above pullback bar
    if c0 <= c1:
        return False
    # Recover at least 50% of the pullback drop
    drop = c2 - c1
    recovery = c0 - c1
    if drop <= 0 or recovery < drop * 0.5:
        return False

    return True


def _is_bearish_reversal(closes: list, idx: int) -> bool:
    """
    Bearish 3-bar close reversal at index idx.
    Prior bar shows pullback (higher close), current bar closes lower (drop).
    """
    if idx < 2:
        return False
    c0 = closes[idx]      # reversal bar
    c1 = closes[idx - 1]  # pullback bar
    c2 = closes[idx - 2]  # prior bar (trend was still down)

    # Momentum was down before pullback
    if c2 >= c1:
        return False
    # Reversal: close below pullback bar
    if c0 >= c1:
        return False
    # Drop at least 50% of the prior rise
    rise = c1 - c2
    decline = c1 - c0
    if rise <= 0 or decline < rise * 0.5:
        return False

    return True


# ═══════════════════════════════════════════════════════════════════════════════
# Data fetch — price_history (1m closes)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_1m_prices(token: str, lookback: int = LOOKBACK_1M) -> list:
    """
    Fetch 1m close prices from price_history (signals_hermes.db), oldest first.
    price_history is updated every minute with live prices — the ONLY reliable
    source for live signal generation. timestamps are in SECONDS (Unix time).
    Freshness guard: returns [] if most recent price is > 2 minutes old.
    """
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT timestamp, price FROM (
                SELECT timestamp, price
                FROM price_history
                WHERE token = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ) sub
            ORDER BY timestamp ASC
        """, (token.upper(), lookback))
        rows = c.fetchall()
        conn.close()

        if not rows:
            return []

        most_recent_ts = rows[-1][0]
        if (time.time() - most_recent_ts) > 120:
            print(f"  [em20-50] {token}: stale price_history (last ts {most_recent_ts}), skipping")
            return []

        # Bar-to-bar gap guard — detect internal data gaps
        bar_gaps = [rows[i][0] - rows[i-1][0] for i in range(1, len(rows))]
        if bar_gaps:
            mean_gap = sum(bar_gaps) / len(bar_gaps)
            variance = sum((g - mean_gap) ** 2 for g in bar_gaps) / len(bar_gaps)
            std_gap = variance ** 0.5
            threshold = max(150, mean_gap + 3.0 * std_gap)
            for i in range(1, len(rows)):
                bar_gap = rows[i][0] - rows[i-1][0]
                if bar_gap > threshold:
                    print(f"  [em20-50] {token}: data gap ({bar_gap:.0f}s > {threshold:.0f}s), skipping")
                    return []

        return [{'timestamp': r[0], 'price': r[1]} for r in rows]

    except Exception as e:
        print(f"  [em20-50] price_history error for {token}: {e}")
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# Detection
# ═══════════════════════════════════════════════════════════════════════════════

def _detect_one_direction(
    closes: list,
    ema20_s: list,
    ema50_s: list,
    direction: str,
) -> Optional[dict]:
    """
    Detect pullback signal in one direction only.
    Returns signal dict or None.
    """
    for j in range(3, len(closes) - 1):
        ema20 = ema20_s[j]
        ema50 = ema50_s[j]
        if ema20 is None or ema50 is None:
            continue

        # Trend filter
        if direction == 'LONG' and not (ema20 > ema50):
            continue
        if direction == 'SHORT' and not (ema20 < ema50):
            continue

        p = closes[j]

        # ── Pullback: price at or through EMA20 ─────────────────────────────
        # Use |close - prior_close| as bar-range proxy (close-only volatility estimate)
        bar_range = abs(p - closes[j - 1]) if j > 0 else 0

        at_ema20 = False
        if p == ema20:
            at_ema20 = True
        elif bar_range > 0 and abs(p - ema20) <= bar_range * PULLBACK_TOL_PCT:
            at_ema20 = True
        elif j > 0 and ((direction == 'LONG' and closes[j-1] > ema20 >= p) or
                         (direction == 'SHORT' and closes[j-1] < ema20 <= p)):
            # Special case: EMA20 is between prior close and current close
            # (price crossed through EMA20 — qualifies as pullback)
            at_ema20 = True

        if not at_ema20:
            continue

        # ── RSI gate ─────────────────────────────────────────────────────
        rsi_j    = _rsi_at(closes, j)
        rsi_prev = _rsi_at(closes, j - 1)
        if rsi_j is None:
            continue

        if direction == 'LONG':
            if rsi_j <= RSI_BULL_GATE:
                continue
            if rsi_prev is not None and rsi_j <= rsi_prev:
                continue
            in_ideal = RSI_BULL_IDEAL[0] <= rsi_j <= RSI_BULL_IDEAL[1]
        else:
            if rsi_j >= RSI_BEAR_GATE:
                continue
            if rsi_prev is not None and rsi_j >= rsi_prev:
                continue
            in_ideal = RSI_BEAR_IDEAL[0] <= rsi_j <= RSI_BEAR_IDEAL[1]

        # ── 3-bar close reversal ──────────────────────────────────────────
        if direction == 'LONG':
            if not _is_bullish_reversal(closes, j):
                continue
        else:
            if not _is_bearish_reversal(closes, j):
                continue

        # ── Confidence scoring ─────────────────────────────────────────────
        base_conf = 60
        ideal_bonus = 8 if in_ideal else 0
        if direction == 'LONG':
            rsi_strength = min(
                (rsi_j - RSI_BULL_GATE) /
                (RSI_BULL_IDEAL[1] - RSI_BULL_GATE) * 10, 10)
        else:
            rsi_strength = min(
                (RSI_BEAR_GATE - rsi_j) /
                (RSI_BEAR_GATE - RSI_BEAR_IDEAL[0]) * 10, 10)
        confidence = int(min(MAX_CONFIDENCE,
                             max(MIN_CONFIDENCE,
                                 base_conf + ideal_bonus + rsi_strength)))

        # Entry: next candle's close (or current price as fallback)
        entry_price = closes[j + 1] if j + 1 < len(closes) else p

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source   = SOURCE_LONG       if direction == 'LONG' else SOURCE_SHORT

        # For high/low of confirmation bar we only have closes — use prior close as proxy
        confirm_high = max(closes[j], closes[j - 1]) if j > 0 else closes[j]
        confirm_low  = min(closes[j], closes[j - 1]) if j > 0 else closes[j]

        return {
            'direction':       direction,
            'confidence':      confidence,
            'source':          source,
            'signal_type':     sig_type,
            'rsi':             round(rsi_j, 2),
            'ema20':           round(ema20, 6),
            'ema50':           round(ema50, 6),
            'price_at_ema20':  round(p, 6),
            'confirm_high':    round(confirm_high, 6),
            'confirm_low':     round(confirm_low, 6),
            'entry_price':     round(entry_price, 6),
            'bars_since':      max(len(closes) - 1 - j, 0),
            'value':           float(confidence),
        }

    return None


def detect_ema20_50_pullback(token: str, prices: list, price: float) -> Optional[dict]:
    """
    Detect EMA20/EMA50 pullback signal on 1m close prices.

    Bullish: EMA20 > EMA50 + price at EMA20 + 3-bar bullish reversal + RSI rising from >30.
    Bearish: EMA20 < EMA50 + price at EMA20 + 3-bar bearish reversal + RSI falling from <70.

    Returns signal dict or None.
    """
    n = len(prices)
    if n < MIN_VALID_BARS:
        return None

    closes = [p['price'] for p in prices]

    ema20_s = _ema_series(closes, PERIOD_EMA_FAST)
    ema50_s = _ema_series(closes, PERIOD_EMA_SLOW)

    valid_count = sum(1 for v in ema50_s if v is not None)
    if valid_count < 2:
        return None

    # Try LONG first
    sig = _detect_one_direction(closes, ema20_s, ema50_s, 'LONG')
    if sig is not None:
        return sig

    # Try SHORT
    return _detect_one_direction(closes, ema20_s, ema50_s, 'SHORT')


# ═══════════════════════════════════════════════════════════════════════════════
# Main scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_ema20_50_signals(prices_dict: dict) -> int:
    """
    Scan tokens for EMA20/EMA50 pullback signals.

    All guards (blacklists, open positions, cooldowns, price age) must be
    applied by the caller before passing prices_dict here.

    Args:
        prices_dict: token -> {'price': float, ...} from signal_gen

    Returns:
        Number of signals written to DB.
    """
    from signal_schema import add_signal, price_age_minutes
    from position_manager import get_open_positions as _get_open_pos
    from signal_gen import (
        recent_trade_exists, is_delisted, SHORT_BLACKLIST,
        MIN_TRADE_INTERVAL_MINUTES, set_cooldown
    )

    open_pos = {p['token']: p['direction'] for p in _get_open_pos()}
    added = 0

    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue
        price = data.get('price')
        if not price or price <= 0:
            continue
        if token.upper() in open_pos:
            continue
        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
            continue
        if is_delisted(token.upper()):
            continue
        if token.upper() in SHORT_BLACKLIST:
            continue
        if price_age_minutes(token) > 10:
            continue

        prices = _get_1m_prices(token, lookback=LOOKBACK_1M)
        if not prices or len(prices) < MIN_VALID_BARS:
            continue

        sig = detect_ema20_50_pullback(token, prices, price)
        if sig is None:
            continue

        try:
            sid = add_signal(
                token=token.upper(),
                direction=sig['direction'],
                signal_type=sig['signal_type'],
                source=sig['source'],
                confidence=sig['confidence'],
                value=sig['value'],
                price=price,
                exchange='hyperliquid',
                timeframe='1m',
                z_score=None,
                z_score_tier=None,
            )
            if sid:
                added += 1
                set_cooldown(token, sig['direction'], hours=COOLDOWN_MINUTES / 60.0)
                print(f"  {sig['direction']:5s}-ema20-50 {token:8s} "
                      f"conf={sig['confidence']:.0f}% rsi={sig['rsi']:.1f} "
                      f"ema20={sig['ema20']:.4f} ema50={sig['ema50']:.4f} "
                      f"at_ema20={sig['price_at_ema20']:.4f} [{sig['source']}]")
        except Exception as e:
            print(f"[em20-50] add_signal error for {token}: {e}")

    return added


# ═══════════════════════════════════════════════════════════════════════════════
# CLI test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from signal_schema import get_all_latest_prices, init_db

    init_db()
    prices = get_all_latest_prices()

    test_tokens = {k: v for k, v in prices.items()
                   if k in ('BTC', 'ETH', 'SOL', 'AVAX', 'LINK', 'SAGA', 'SCR', 'ARB')
                   and v.get('price')}
    if not test_tokens:
        test_tokens = dict(list(prices.items())[:10])

    print(f"[em20-50] Testing on {len(test_tokens)} tokens...")
    n = scan_ema20_50_signals(test_tokens)
    print(f"[em20-50] Done. {n} signals emitted.")


# ═══════════════════════════════════════════════════════════════════════════════
# Backtest — sequential walk with no look-ahead
# ═══════════════════════════════════════════════════════════════════════════════

def backtest_ema20_50(token: str, closes: list,
                      hold_bars: int = 60,
                      slippage_pct: float = 0.0005) -> dict:
    """
    Sequential backtest for EMA20/EMA50 pullback strategy.

    Walks through closes bar by bar. Fires signal at bar j when:
      - Trend: EMA20 > EMA50 (LONG) or EMA20 < EMA50 (SHORT)
      - Pullback: price at or through EMA20
      - RSI gate satisfied
      - 3-bar reversal confirmed
    Entry: closes[j+1] (next bar close, approximates next bar open)
    Exit:  closes[j+hold_bars] (fixed hold)

    Returns dict with per-direction stats.
    """
    if len(closes) < MIN_VALID_BARS + hold_bars + 10:
        return {}

    ema20_s = _ema_series(closes, PERIOD_EMA_FAST)
    ema50_s = _ema_series(closes, PERIOD_EMA_SLOW)

    def rsi_seq(idx):
        return _rsi_at(closes, idx)

    results = {'LONG': [], 'SHORT': []}

    for j in range(3, len(closes) - hold_bars - 1):
        ema20 = ema20_s[j]
        ema50 = ema50_s[j]
        if ema20 is None or ema50 is None:
            continue

        direction = None

        # ── Bullish ──────────────────────────────────────────────────────────
        if ema20 > ema50:
            p = closes[j]
            bar_range = abs(p - closes[j - 1]) if j > 0 else 0
            at_ema = (p == ema20) or (bar_range > 0 and abs(p - ema20) <= bar_range * PULLBACK_TOL_PCT)
            if not at_ema and j > 0 and closes[j - 1] > ema20 >= p:
                at_ema = True
            if not at_ema:
                continue

            rsi_j    = rsi_seq(j)
            rsi_prev = rsi_seq(j - 1)
            if rsi_j is None or rsi_j <= RSI_BULL_GATE:
                continue
            if rsi_prev is not None and rsi_j <= rsi_prev:
                continue
            if not _is_bullish_reversal(closes, j):
                continue

            direction = 'LONG'

        # ── Bearish ─────────────────────────────────────────────────────────
        elif ema20 < ema50:
            p = closes[j]
            bar_range = abs(p - closes[j - 1]) if j > 0 else 0
            at_ema = (p == ema20) or (bar_range > 0 and abs(p - ema20) <= bar_range * PULLBACK_TOL_PCT)
            if not at_ema and j > 0 and closes[j - 1] < ema20 <= p:
                at_ema = True
            if not at_ema:
                continue

            rsi_j    = rsi_seq(j)
            rsi_prev = rsi_seq(j - 1)
            if rsi_j is None or rsi_j >= RSI_BEAR_GATE:
                continue
            if rsi_prev is not None and rsi_j >= rsi_prev:
                continue
            if not _is_bearish_reversal(closes, j):
                continue

            direction = 'SHORT'

        if direction is None:
            continue

        # Entry: next bar close (approximates next bar open after signal bar)
        entry = closes[j + 1]
        if entry <= 0:
            continue
        exit_price = closes[j + hold_bars]
        if exit_price <= 0:
            continue

        # Slippage
        if direction == 'LONG':
            entry_with_slip = entry * (1 + slippage_pct)
            pnl_pct = (exit_price - entry_with_slip) / entry_with_slip * 100.0
        else:
            entry_with_slip = entry * (1 - slippage_pct)
            pnl_pct = (entry_with_slip - exit_price) / entry_with_slip * 100.0

        results[direction].append({
            'j': j, 'entry': entry, 'exit': exit_price,
            'pnl_pct': pnl_pct, 'hold': hold_bars,
        })

    # Aggregate
    summary = {}
    for direction, trades in results.items():
        if not trades:
            summary[direction] = {'n_signals': 0}
            continue
        pnls = [t['pnl_pct'] for t in trades]
        wins = [p for p in pnls if p > 0]
        summary[direction] = {
            'n_signals':  len(trades),
            'win_rate':   len(wins) / len(trades) * 100,
            'avg_return': sum(pnls) / len(pnls),
            'avg_bars':   sum(t['hold'] for t in trades) / len(trades),
            'best':       max(pnls),
            'worst':      min(pnls),
            '_raw':       trades,   # list of {j,entry,exit,pnl_pct,hold}
        }

    return summary


def batch_backtest(tokens: list, hold_bars: int = 60,
                   lookback_days: int = 30,
                   min_signals: int = 3) -> dict:
    """
    Run backtest across multiple tokens from live price_history.
    """
    from signal_schema import get_price_history

    all_long_pnls  = []
    all_short_pnls = []

    for token in tokens:
        rows = get_price_history(token, lookback_minutes=60 * 24 * lookback_days)
        if len(rows) < MIN_VALID_BARS + hold_bars + 50:
            continue
        closes = [r[1] for r in rows]
        result = backtest_ema20_50(token, closes, hold_bars=hold_bars)

        long_trades  = result.get('LONG',  {}).get('n_signals', 0)
        short_trades = result.get('SHORT', {}).get('n_signals', 0)

        # result['LONG'] is a dict with stats + '_raw' list of trades
        if long_trades >= min_signals:
            all_long_pnls.extend([t['pnl_pct'] for t in result['LONG'].get('_raw', [])])
        if short_trades >= min_signals:
            all_short_pnls.extend([t['pnl_pct'] for t in result['SHORT'].get('_raw', [])])

        print(f"  {token:6s}: LONG n={long_trades:3d}  SHORT n={short_trades:3d}")

    def _stats(pnls, label):
        if not pnls:
            return {label: 'no data'}
        wins = [p for p in pnls if p > 0]
        return {
            label: {
                'n_signals':  len(pnls),
                'win_rate':   f"{len(wins)/len(pnls)*100:.1f}%",
                'avg_return': f"{sum(pnls)/len(pnls):.3f}%",
                'best':       f"{max(pnls):.3f}%",
                'worst':      f"{min(pnls):.3f}%",
            }
        }

    out = {}
    out.update(_stats(all_long_pnls,  'LONG'))
    out.update(_stats(all_short_pnls, 'SHORT'))
    return out


def _print_backtest(tokens, hold_bars=60, lookback_days=30, min_signals=3):
    """Run and print batch backtest results."""
    from signal_schema import init_db
    init_db()
    print(f'[em20-50] Batch backtest — {lookback_days}d lookback, {hold_bars}-bar hold (~{hold_bars//60}h)')
    result = batch_backtest(tokens, hold_bars=hold_bars,
                           lookback_days=lookback_days, min_signals=min_signals)
    print()
    print('=== AGGREGATED ===')
    for k, v in result.items():
        if isinstance(v, str):
            print(f'{k}: {v}')
        else:
            for mk, mv in v.items():
                print(f'  {mk}: {mv}')
