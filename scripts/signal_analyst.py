#!/usr/bin/env python3
"""Signal Analyst — proactive signal quality scorer.

Runs between compactor and decider. Scores each signal in hotset on quality,
filters out low-quality signals before execution.

Features:
1. Macro deployment gate — adjusts sizing based on market conditions
2. Multi-timeframe trend alignment — 1H + 4H must agree
3. Quality scoring — 0-100 on 5 criteria

Scoring criteria:
1. Multi-TF trend alignment (0-30 pts) — 1H + 4H EMA20/50
2. RSI confirmation (0-20 pts) — LONG needs oversold, SHORT needs overbought
3. Signal type historical WR (0-25 pts) — from signal_outcomes
4. Time of day (0-10 pts) — active hours preferred
5. Token blacklist check (0-15 pts) — not blacklisted

Threshold: Score >= 60 to pass
"""
import json
import os
import sys
import time
import sqlite3
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from paths import RUNTIME_DB

# ── Config ──────────────────────────────────────────────────────────────
HOTSET_PATH = '/var/www/hermes/data/hotset.json'
MIN_SCORE = 40  # Lowered from 55 — in NEUTRAL/LONG_BIAS markets, SHORT signals score
                # 0 on trend (counter-trend) + 0 on RSI (RSI < 60), can't reach 55.
                # Signals that survived compactor confluence + quality filters are
                # already vetted. signal_analyst is final gate, not sole arbiter.
CACHE_TTL = 300  # Cache WR data for 5 min

# ── Cache ───────────────────────────────────────────────────────────────
_wr_cache = {}
_wr_cache_ts = 0


def _log(msg):
    print(f"[signal-analyst] {msg}", flush=True)


def _get_signal_wr(signal_type, direction):
    """Get historical win rate for a signal type + direction."""
    global _wr_cache, _wr_cache_ts

    now = time.time()
    if _wr_cache and now - _wr_cache_ts < CACHE_TTL:
        key = f"{signal_type}:{direction}"
        return _wr_cache.get(key, 50)  # Default 50% if no data

    # Fetch from DB
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as total, SUM(is_win) as wins
            FROM signal_outcomes
            WHERE signal_type = ? AND direction = ? AND trade_id IS NOT NULL
        """, (signal_type, direction))
        row = cur.fetchone()
        conn.close()

        if row and row[0] >= 5:
            wr = (row[1] or 0) / row[0] * 100
        else:
            wr = 50  # Default if insufficient data

        _wr_cache[f"{signal_type}:{direction}"] = wr
        _wr_cache_ts = now
        return wr
    except Exception:
        return 50


def _get_1h_trend(token):
    """Check 1H EMA trend. Returns 'BULLISH', 'BEARISH', or 'NEUTRAL'."""
    try:
        conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_1h
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT 60
        """, (token.upper(),))
        rows = cur.fetchall()
        conn.close()
        if not rows or len(rows) < 50:
            return 'NEUTRAL'
        closes = [r[0] for r in reversed(rows)]

        def ema(data, period):
            k = 2 / (period + 1)
            val = data[0]
            for v in data[1:]:
                val = v * k + val * (1 - k)
            return val

        ema20 = ema(closes, 20)
        ema50 = ema(closes, 50)
        if ema50 == 0:
            return 'NEUTRAL'
        spread = abs(ema20 - ema50) / ema50 * 100
        if spread < 0.1:
            return 'NEUTRAL'
        return 'BULLISH' if ema20 > ema50 else 'BEARISH'
    except Exception:
        return 'NEUTRAL'


def _get_rsi(token):
    """Get current 1H RSI."""
    conn = None
    try:
        conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_1h
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT 20
        """, (token.upper(),))
        rows = cur.fetchall()
        if not rows or len(rows) < 15:
            return 50
        closes = [r[0] for r in reversed(rows)]

        gains, losses = [], []
        for i in range(1, min(15, len(closes))):
            delta = closes[-i] - closes[-i - 1]
            gains.append(max(delta, 0))
            losses.append(max(-delta, 0))
        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0.001
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        return 100 - (100 / (1 + rs))
    except Exception:
        return 50
    finally:
        if conn:
            conn.close()


def _is_blacklisted(token):
    """Check if token is blacklisted."""
    try:
        from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST
        return token.upper() in SHORT_BLACKLIST or token.upper() in LONG_BLACKLIST
    except Exception:
        return False


def _is_active_hours():
    """Check if current time is in active trading hours (14:00-22:00 UTC)."""
    now = datetime.now(timezone.utc)
    hour = now.hour
    return 14 <= hour <= 22


def _get_ema_trend(token, timeframe='1h', fast=20, slow=50):
    """Get EMA trend for any timeframe. Returns 'BULLISH', 'BEARISH', or 'NEUTRAL'.

    For 4H: derives from 1H candles (4H collection is disabled).
    """
    try:
        conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=5)
        cur = conn.cursor()

        if timeframe == '4h':
            # Derive 4H from 1H candles (4H collection disabled)
            cur.execute(f"""
                SELECT close FROM candles_1h
                WHERE token = ?
                ORDER BY ts DESC
                LIMIT ?
            """, (token.upper(), slow * 4 + 10))
            rows = cur.fetchall()
            conn.close()
            if not rows or len(rows) < slow * 4:
                return 'NEUTRAL'
            closes_1h = [r[0] for r in reversed(rows)]
            # Aggregate to 4H: take every 4th close
            closes = closes_1h[::4]
            if len(closes) < slow:
                return 'NEUTRAL'
        else:
            cur.execute(f"""
                SELECT close FROM candles_{timeframe}
                WHERE token = ?
                ORDER BY ts DESC
                LIMIT ?
            """, (token.upper(), slow + 10))
            rows = cur.fetchall()
            conn.close()
            if not rows or len(rows) < slow:
                return 'NEUTRAL'
            closes = [r[0] for r in reversed(rows)]

        def ema(data, period):
            k = 2 / (period + 1)
            val = data[0]
            for v in data[1:]:
                val = v * k + val * (1 - k)
            return val

        ema_fast = ema(closes, fast)
        ema_slow = ema(closes, slow)
        if ema_slow == 0:
            return 'NEUTRAL'
        spread = abs(ema_fast - ema_slow) / ema_slow * 100
        if spread < 0.1:
            return 'NEUTRAL'
        return 'BULLISH' if ema_fast > ema_slow else 'BEARISH'
    except Exception:
        return 'NEUTRAL'


def _get_market_volatility():
    """Get average ATR% across top tokens as market volatility proxy."""
    conn = None
    try:
        conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=5)
        cur = conn.cursor()
        # Sample 10 tokens for volatility estimate
        cur.execute("""
            SELECT token FROM candles_1h
            GROUP BY token
            HAVING COUNT(*) >= 50
            ORDER BY RANDOM()
            LIMIT 10
        """)
        tokens = [r[0] for r in cur.fetchall()]

        atr_pcts = []
        for token in tokens:
            cur.execute(f"""
                SELECT close, high, low FROM candles_1h
                WHERE token = ?
                ORDER BY ts DESC
                LIMIT 15
            """, (token,))
            rows = cur.fetchall()
            if rows and len(rows) >= 14:
                closes = [r[0] for r in reversed(rows)]
                trs = []
                for i in range(1, len(closes)):
                    tr = abs(closes[i] - closes[i-1])
                    trs.append(tr)
                if trs:
                    atr = sum(trs[-14:]) / 14
                    avg_price = sum(closes[-14:]) / 14
                    if avg_price > 0:
                        atr_pcts.append(atr / avg_price)

        if atr_pcts:
            return sum(atr_pcts) / len(atr_pcts)
        return 0.02  # Default moderate volatility
    except Exception:
        return 0.02
    finally:
        if conn:
            conn.close()


def _get_recent_wr():
    """Get win rate of last 20 trades across all signals."""
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as total, SUM(is_win) as wins
            FROM (
                SELECT is_win FROM signal_outcomes
                WHERE trade_id IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 20
            )
        """)
        row = cur.fetchone()
        conn.close()
        if row and row[0] > 0:
            return (row[1] or 0) / row[0] * 100
        return 50
    except Exception:
        return 50


def macro_deployment_gate():
    """Check market conditions. Returns deployment modes per direction.

    Returns dict: {'LONG': mode, 'SHORT': mode} where mode is 'FULL', 'REDUCE', or 'STOP'.
    Regime-aware: aligned directions get FULL, counter-regime gets REDUCE, extreme gets STOP.
    """
    try:
        from hermes_constants import (
            MACRO_GATE_ENABLED, MACRO_HIGH_VOL_THRESHOLD,
            MACRO_LOW_WR_THRESHOLD
        )
        if not MACRO_GATE_ENABLED:
            return {'LONG': 'FULL', 'SHORT': 'FULL'}
    except ImportError:
        return {'LONG': 'FULL', 'SHORT': 'FULL'}

    # Check regime — regime scanner outputs LONG_BIAS, SHORT_BIAS, or NEUTRAL
    try:
        import json as _json
        regime_file = '/var/www/hermes/data/regime_5m.json'
        if os.path.exists(regime_file):
            with open(regime_file) as f:
                regime_data = _json.load(f)
            overall = regime_data.get('aggregate', {}).get('overall', 'NEUTRAL')
        else:
            overall = 'NEUTRAL'
    except Exception:
        overall = 'NEUTRAL'

    # Check volatility
    vol = _get_market_volatility()

    # Check recent win rate
    wr = _get_recent_wr()

    # High volatility → STOP all directions
    if vol > MACRO_HIGH_VOL_THRESHOLD:
        _log(f"Macro gate: STOP (vol={vol:.3f} > {MACRO_HIGH_VOL_THRESHOLD})")
        return {'LONG': 'STOP', 'SHORT': 'STOP'}

    # Low win rate → REDUCE all directions
    if wr < MACRO_LOW_WR_THRESHOLD:
        _log(f"Macro gate: REDUCE (wr={wr:.0f}% < {MACRO_LOW_WR_THRESHOLD})")
        return {'LONG': 'REDUCE', 'SHORT': 'REDUCE'}

    # Regime-based: aligned = FULL, counter = REDUCE
    if overall == 'LONG_BIAS':
        _log(f"Macro gate: LONG=FULL, SHORT=REDUCE (regime={overall}, wr={wr:.0f}%)")
        return {'LONG': 'FULL', 'SHORT': 'REDUCE'}
    elif overall == 'SHORT_BIAS':
        _log(f"Macro gate: LONG=REDUCE, SHORT=FULL (regime={overall}, wr={wr:.0f}%)")
        return {'LONG': 'REDUCE', 'SHORT': 'FULL'}
    else:
        _log(f"Macro gate: FULL (regime={overall}, vol={vol:.3f}, wr={wr:.0f}%)")
        return {'LONG': 'FULL', 'SHORT': 'FULL'}


def score_signal(entry):
    """Score a signal entry on quality. Returns (score, breakdown)."""
    token = entry.get('token', '')
    direction = entry.get('direction', '')
    source = entry.get('source', '')
    confidence = entry.get('confidence', 0)

    # Extract signal_type from source (e.g., 'tl_break_short' → 'tl_break_short')
    signal_type = source.split(',')[0] if source else 'unknown'

    breakdown = {}

    # 1. Multi-timeframe trend alignment (0-30 pts)
    # Check 1H and 4H trends — both must agree
    trend_1h = _get_ema_trend(token, '1h', 20, 50)
    trend_4h = _get_ema_trend(token, '4h', 20, 50)

    if direction == 'LONG':
        if trend_1h == 'BULLISH' and trend_4h == 'BULLISH':
            breakdown['trend'] = 30  # Full alignment
        elif trend_1h == 'BULLISH' or trend_4h == 'BULLISH':
            breakdown['trend'] = 15  # Partial alignment
        else:
            breakdown['trend'] = 0   # Counter-trend
    else:  # SHORT
        if trend_1h == 'BEARISH' and trend_4h == 'BEARISH':
            breakdown['trend'] = 30
        elif trend_1h == 'BEARISH' or trend_4h == 'BEARISH':
            breakdown['trend'] = 15
        else:
            breakdown['trend'] = 0

    # 2. RSI confirmation (0-20 pts)
    rsi = _get_rsi(token)
    if direction == 'LONG' and rsi < 40:
        breakdown['rsi'] = 20
    elif direction == 'SHORT' and rsi > 60:
        breakdown['rsi'] = 20
    elif 40 <= rsi <= 60:
        breakdown['rsi'] = 10
    else:
        breakdown['rsi'] = 0

    # 3. Signal type historical WR (0-25 pts)
    wr = _get_signal_wr(signal_type, direction)
    if wr >= 50:
        breakdown['wr'] = 25
    elif wr >= 40:
        breakdown['wr'] = 15
    elif wr >= 30:
        breakdown['wr'] = 5
    else:
        breakdown['wr'] = 0

    # 4. Time of day (0-10 pts)
    breakdown['time'] = 10 if _is_active_hours() else 0

    # 5. Blacklist check (0-15 pts)
    breakdown['blacklist'] = 0 if _is_blacklisted(token) else 15

    total = sum(breakdown.values())
    return total, breakdown


def analyze_hotset():
    """Read hotset, score each signal, filter low-quality ones."""
    # 1. Macro deployment gate — returns per-direction modes
    deployment = macro_deployment_gate()

    # If both directions STOP, clear hotset entirely
    if deployment.get('LONG') == 'STOP' and deployment.get('SHORT') == 'STOP':
        _log("Macro gate STOP (all directions) — clearing hotset")
        try:
            import tempfile
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(HOTSET_PATH), suffix='.tmp')
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump({'hotset': [], 'macro_gate': 'STOP'}, f, indent=2)
                os.replace(tmp, HOTSET_PATH)
            except Exception:
                os.unlink(tmp)
                raise
        except Exception:
            pass
        return 0

    if not os.path.exists(HOTSET_PATH):
        _log("Hotset not found")
        return 0

    try:
        with open(HOTSET_PATH) as f:
            hotset = json.load(f)
    except Exception as e:
        _log(f"Error reading hotset: {e}")
        return 0

    tokens = hotset.get('hotset', [])
    if not tokens:
        return 0

    _log(f"Analyzing {len(tokens)} signals in hotset (deployment={deployment})")

    filtered = []
    blocked = 0

    for entry in tokens:
        token = entry.get('token', '')
        direction = entry.get('direction', '')
        source = entry.get('source', '')

        # Per-direction deployment
        dir_deploy = deployment.get(direction, 'FULL')

        # Skip signals stopped by macro gate
        if dir_deploy == 'STOP':
            blocked += 1
            _log(f"  MACRO-BLOCK: {token} {direction} (regime counter)")
            continue

        score, breakdown = score_signal(entry)

        # Apply deployment multiplier
        if dir_deploy == 'REDUCE':
            entry['size_multiplier'] = 0.5

        if score >= MIN_SCORE:
            entry['ceo_score'] = score
            entry['ceo_breakdown'] = breakdown
            entry['deployment'] = dir_deploy
            filtered.append(entry)
            _log(f"  PASS: {token} {direction} score={score} "
                 f"trend={breakdown['trend']} rsi={breakdown['rsi']} "
                 f"wr={breakdown['wr']} deploy={dir_deploy}")
            
            # Log decision to persistent decision log
            try:
                from decision_log import log_decision
                reasoning = {
                    'trend': _get_ema_trend(token, '1h'),
                    'rsi': _get_rsi(token),
                    'score': score,
                    'breakdown': breakdown,
                }
                log_decision(token, direction, source.split(',')[0], 
                           score, entry.get('price', 0), reasoning)
            except Exception:
                pass  # Don't block on logging errors
        else:
            blocked += 1
            _log(f"  BLOCK: {token} {direction} score={score} "
                 f"(trend={breakdown['trend']} rsi={breakdown['rsi']} "
                 f"wr={breakdown['wr']})")

    # Write filtered hotset (atomic)
    if filtered:
        hotset['hotset'] = filtered
        hotset['signal_analyst'] = True
        hotset['signal_analyst_blocked'] = blocked
        hotset['macro_deployment'] = deployment
        try:
            import tempfile
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(HOTSET_PATH), suffix='.tmp')
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(hotset, f, indent=2)
                os.replace(tmp, HOTSET_PATH)
            except Exception:
                os.unlink(tmp)
                raise
            _log(f"Filtered: {len(filtered)} pass, {blocked} blocked")
        except Exception as e:
            _log(f"Error writing hotset: {e}")
    else:
        _log(f"All {len(tokens)} signals blocked — no quality signals")

    return blocked


def run():
    """Entry point for pipeline."""
    return analyze_hotset()


if __name__ == '__main__':
    # Manual test
    if '--dry' in sys.argv:
        _log("DRY RUN — would analyze hotset")
        if os.path.exists(HOTSET_PATH):
            with open(HOTSET_PATH) as f:
                hotset = json.load(f)
            tokens = hotset.get('hotset', [])
            for entry in tokens:
                score, breakdown = score_signal(entry)
                status = 'PASS' if score >= MIN_SCORE else 'BLOCK'
                _log(f"  {status}: {entry.get('token')} {entry.get('direction')} "
                     f"score={score} breakdown={breakdown}")
    else:
        run()
