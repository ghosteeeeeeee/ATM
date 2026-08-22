#!/usr/bin/env python3
"""Entry Gate Utilities — quality filters applied before signal emission.

Five shared gates that every signal calls before add_signal().
All gates are fail-open: missing data = pass (don't kill the pipeline).

Usage in signals:
    from entry_gates import rr_gate, volume_gate, candle_close_gate, session_timing_gate, hebbian_gate

    if not session_timing_gate():
        continue
    candles = candle_close_gate(raw_candles, timeframe_seconds=60)
    if not volume_gate(candles):
        continue
    rr_pass, sl, tp, rr = rr_gate(token, direction, price)
    if not rr_pass:
        continue
    hebbian_ok, conf_adj = hebbian_gate(token, signal, direction)
    if not hebbian_ok:
        continue
"""
import time
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, ATR_CACHE_FILE

# ── Constants (single source) ────────────────────────────────────────────────
ENTRY_RR_MIN_RATIO = 2.0       # minimum R:R to allow entry (9/15 books)
ENTRY_RR_SL_ATR_MULT = 1.0     # SL = 1.0 × ATR
ENTRY_RR_USE_S_R = True        # prefer nearest S/R as TP target

ENTRY_VOLUME_MIN_RATIO = 1.2   # current vol must be 1.2× average (10/15 books)
ENTRY_VOLUME_LOOKBACK = 20     # candles for average

ENTRY_CANDLE_CLOSE_ENABLED = True
ENTRY_CANDLE_CLOSE_BUFFER_SEC = 10  # extra seconds after close

ENTRY_SESSION_FILTER_ENABLED = True
ENTRY_SESSION_BLOCK_SUNDAY_HOURS = (0, 6)  # block Sunday 00:00-06:00 UTC


def _log(msg):
    print(f"[entry-gates] {msg}", flush=True)


# ── Gate 1: R:R Pre-Check ────────────────────────────────────────────────────

def _get_cached_atr(token):
    """Fetch ATR% from atr_cache.json. Returns float (e.g. 0.03 = 3%) or None."""
    try:
        if not os.path.exists(ATR_CACHE_FILE):
            return None
        with open(ATR_CACHE_FILE) as f:
            cache = json.load(f)
        entry = cache.get(token.upper())
        if not entry:
            return None
        # ponytail: ATR cache stores 'atr', not 'atr_pct'. Use explicit fallback.
        return entry.get('atr_pct', entry.get('atr'))
    except Exception:
        return None


def _find_nearest_sr(token, price, direction, candles_5m):
    """Find nearest S/R level from recent swing highs/lows in 5m candles.

    Returns distance to nearest level in same direction as trade (reward side),
    or None if no level found.
    """
    if not candles_5m or len(candles_5m) < 30:
        return None

    # Sort by timestamp to ensure chronological order
    def _get_ts(c):
        if isinstance(c, dict):
            return c.get('ts') or c.get('timestamp', 0)
        return 0
    sorted_candles = sorted(candles_5m, key=_get_ts)

    # Extract close prices
    closes = [c['close'] if isinstance(c, dict) else c for c in sorted_candles]

    # Detect local swing highs and lows (simple N-bar detection)
    swing_highs = []
    swing_lows = []
    n = 3  # bars each side
    for i in range(n, len(closes) - n):
        window = closes[i - n:i + n + 1]
        if closes[i] == max(window):
            swing_highs.append(closes[i])
        if closes[i] == min(window):
            swing_lows.append(closes[i])

    if not swing_highs and not swing_lows:
        return None

    # Find nearest level on the REWARD side
    if direction == 'LONG':
        # Reward = above entry → nearest swing high above price
        targets = [h for h in swing_highs if h > price]
        if not targets:
            return None
        return min(targets) - price
    else:
        # Reward = below entry → nearest swing low below price
        targets = [l for l in swing_lows if l < price]
        if not targets:
            return None
        return price - max(targets)


def rr_gate(token, direction, price, candles_5m=None):
    """R:R pre-check gate.

    Returns (pass, sl_price, tp_price, rr_ratio).
    pass=True → signal should emit. pass=False → suppress.
    """
    try:
        if price <= 0:
            return False, 0, 0, 0  # reject degenerate prices

        from hermes_constants import ATR_SL_MIN, ATR_TP_MIN, ATR_PCT_FALLBACK

        # Get ATR%
        atr_pct = _get_cached_atr(token)
        if atr_pct is None:
            atr_pct = ATR_PCT_FALLBACK

        # SL distance (reward side is fixed)
        sl_distance = price * ATR_SL_MIN * ENTRY_RR_SL_ATR_MULT

        # TP distance: prefer S/R level, fallback to ATR TP
        tp_distance = price * ATR_TP_MIN
        if ENTRY_RR_USE_S_R and candles_5m:
            sr_dist = _find_nearest_sr(token, price, direction, candles_5m)
            if sr_dist and sr_dist > 0:
                # Use S/R if it's between TP_MIN and TP_MAX
                tp_max = price * 0.025  # 2.5% cap
                if sr_dist >= price * ATR_TP_MIN and sr_dist <= tp_max:
                    tp_distance = sr_dist

        # R:R ratio
        if sl_distance <= 0:
            _log(f"RR FAIL-OPEN: sl_distance={sl_distance} for {token} (ATR misconfigured?)")
            return True, 0, 0, 999  # fail-open

        rr = tp_distance / sl_distance

        if rr < ENTRY_RR_MIN_RATIO:
            _log(f"RR BLOCKED: {token} {direction} rr={rr:.2f} < {ENTRY_RR_MIN_RATIO}")
            return False, 0, 0, rr

        sl = price - sl_distance if direction == 'LONG' else price + sl_distance
        tp = price + tp_distance if direction == 'LONG' else price - tp_distance
        return True, sl, tp, rr

    except Exception:
        return True, 0, 0, 999  # fail-open


# ── Gate 2: Volume Confirmation ──────────────────────────────────────────────

def volume_gate(candles, min_ratio=None, lookback=None):
    """Require above-average volume on current candle.

    Returns True if volume confirms (or data missing → fail-open).
    candles: list of dicts with 'volume' key, or list of tuples with volume at index.
    """
    if min_ratio is None:
        min_ratio = ENTRY_VOLUME_MIN_RATIO
    if lookback is None:
        lookback = ENTRY_VOLUME_LOOKBACK

    try:
        if not candles or len(candles) < 5:
            return True  # not enough data, fail-open

        # Extract volume from candles
        volumes = []
        for c in candles:
            if isinstance(c, dict):
                v = c.get('volume', 0)
            elif isinstance(c, (list, tuple)):
                v = c[4] if len(c) > 4 else 0  # OHLCV format
            else:
                v = 0
            volumes.append(v or 0)

        # Current candle volume (last)
        current_vol = volumes[-1]
        if current_vol <= 0:
            return True  # no volume data, fail-open

        # Average of prior candles (exclude current)
        prior = volumes[-(lookback + 1):-1] if len(volumes) > lookback else volumes[:-1]
        prior_nonzero = [v for v in prior if v > 0]
        if not prior_nonzero:
            return True  # no prior volume data, fail-open

        avg_vol = sum(prior_nonzero) / len(prior_nonzero)
        if avg_vol <= 0:
            return True

        ratio = current_vol / avg_vol
        if ratio < min_ratio:
            _log(f"VOL BLOCKED: ratio={ratio:.2f} < {min_ratio}")
            return False

        return True

    except Exception:
        return True  # fail-open


def volume_dryup_gate(candles, lookback=5):
    """Check if volume is declining (Wyckoff continuation signal).

    Returns True if volume is declining (good for continuation).
    """
    try:
        if not candles or len(candles) < lookback + 1:
            return True  # fail-open

        volumes = []
        for c in candles:
            if isinstance(c, dict):
                v = c.get('volume', 0)
            elif isinstance(c, (list, tuple)):
                v = c[4] if len(c) > 4 else 0
            else:
                v = 0
            volumes.append(v or 0)

        recent = volumes[-lookback:]
        return all(recent[i] <= recent[i - 1] for i in range(1, len(recent)))

    except Exception:
        return True  # fail-open


# ── Gate 3: Candle Close Confirmation ────────────────────────────────────────

def is_candle_closed(candle, timeframe_seconds=60):
    """Check if a single candle is old enough to be confirmed closed.

    candle: dict with 'timestamp' or 'ts' key (unix seconds), or int timestamp.
    """
    try:
        if isinstance(candle, dict):
            ts = candle.get('timestamp') or candle.get('ts', 0)
        elif isinstance(candle, (int, float)):
            ts = candle
        else:
            return True  # can't determine, fail-open

        if ts <= 0:
            return True

        age = time.time() - ts
        return age >= (timeframe_seconds + ENTRY_CANDLE_CLOSE_BUFFER_SEC)

    except Exception:
        return True  # fail-open


def candle_close_gate(candles, timeframe_seconds=60):
    """Return only confirmed-closed candles (skip the one still forming).

    candles: list of OHLCV dicts or tuples, oldest-first.
    Returns: candles[:-1] if last is still forming, else original list.
    """
    if not ENTRY_CANDLE_CLOSE_ENABLED:
        return candles

    try:
        if not candles or len(candles) < 2:
            return candles

        last = candles[-1]
        if not is_candle_closed(last, timeframe_seconds):
            return candles[:-1]

        return candles

    except Exception:
        return candles  # fail-open


# ── Gate 4: Session Timing ──────────────────────────────────────────────────

def session_timing_gate():
    """Block signals during low-quality time windows.

    Returns True if OK to trade, False if we should skip.
    """
    if not ENTRY_SESSION_FILTER_ENABLED:
        return True

    try:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        # Sunday early morning = low liquidity in crypto
        if now.weekday() == 6:  # Sunday
            block_start, block_end = ENTRY_SESSION_BLOCK_SUNDAY_HOURS
            if block_start <= now.hour < block_end:
                _log(f"SESSION BLOCKED: Sunday {now.hour}:00 UTC (low liquidity)")
                return False

        return True

    except Exception:
        return True  # fail-open


# ── Gate 5: Hebbian Memory Gate ─────────────────────────────────────────────

# Lazy-load hebbian engine to avoid import overhead on every call
_hebbian_engine = None

def _get_hebbian():
    """Lazy-load HebbianEngine singleton."""
    global _hebbian_engine
    if _hebbian_engine is None:
        try:
            from hebbian_engine import HebbianEngine
            _hebbian_engine = HebbianEngine()
        except Exception as e:
            _log(f"HEBBIAN GATE: Could not load HebbianEngine: {e}")
            return None
    return _hebbian_engine


def hebbian_gate(token, signal, direction):
    """Hebbian associative memory gate — uses learned trade history to filter signals.

    Queries the hebbian network for (token, signal) performance history.
    Uses composite_score() which blends: decayed WR, exit quality, token WR,
    combo part WR, and hour-of-day patterns.

    Returns (allow_trade: bool, confidence_adjustment: float).
    - allow_trade=False → suppress (signal historically bad for this token)
    - confidence_adjustment: multiplier to apply to signal confidence
      (0.7 = reduce confidence, 1.0 = no change, 1.2 = boost confidence)

    Fail-open: any error → (True, 1.0).
    """
    engine = _get_hebbian()
    if engine is None:
        return True, 1.0  # fail-open

    try:
        score, breakdown = engine.composite_score(token, signal)

        # Thresholds from composite_score docs:
        # > 0.65 → strong positive history (auto-approve zone)
        # < 0.35 → strong negative history (auto-reject zone)
        if score < 0.30:
            _log(f"HEBBIAN BLOCKED: {token} {signal} score={score:.2f} < 0.30")
            return False, 0.0
        elif score < 0.45:
            # Weak signal — reduce confidence but allow
            conf_adj = 0.7
            _log(f"HEBBIAN REDUCE: {token} {signal} score={score:.2f} → conf×{conf_adj}")
            return True, conf_adj
        elif score > 0.70:
            # Strong signal — boost confidence
            conf_adj = 1.2
            return True, conf_adj
        else:
            # Neutral zone — no adjustment
            return True, 1.0

    except Exception as e:
        _log(f"HEBBIAN GATE ERROR (fail-open): {e}")
        return True, 1.0  # fail-open


# ── CLI test harness ────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: entry_gates.py <rr|volume|close|session> [token] [direction] [price]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'rr':
        token = sys.argv[2] if len(sys.argv) > 2 else 'ETH'
        direction = sys.argv[3] if len(sys.argv) > 3 else 'LONG'
        price = float(sys.argv[4]) if len(sys.argv) > 4 else 3500.0
        passed, sl, tp, rr = rr_gate(token, direction, price)
        print(f"RR: passed={passed} sl={sl:.2f} tp={tp:.2f} rr={rr:.2f}")

    elif cmd == 'volume':
        token = sys.argv[2] if len(sys.argv) > 2 else 'ETH'
        # Fake candle data for testing
        candles = [{'volume': 100 + i * 10} for i in range(25)]
        candles[-1] = {'volume': 50}  # low volume → should block
        passed = volume_gate(candles)
        print(f"Volume: passed={passed}")

    elif cmd == 'close':
        import time as _time
        # Test with fresh candle (should strip) and old candle (should keep)
        fresh = {'timestamp': _time.time() - 10, 'close': 100}
        old = {'timestamp': _time.time() - 120, 'close': 100}
        print(f"is_candle_closed(fresh, 60) = {is_candle_closed(fresh, 60)}")
        print(f"is_candle_closed(old, 60) = {is_candle_closed(old, 60)}")
        print(f"candle_close_gate([old, fresh]) = {len(candle_close_gate([old, fresh]))} candles")

    elif cmd == 'session':
        passed = session_timing_gate()
        print(f"Session: passed={passed}")

    elif cmd == 'hebbian':
        token = sys.argv[2] if len(sys.argv) > 2 else 'ETH'
        signal = sys.argv[3] if len(sys.argv) > 3 else 'bb_bounce+'
        direction = sys.argv[4] if len(sys.argv) > 4 else 'LONG'
        passed, conf_adj = hebbian_gate(token, signal, direction)
        print(f"Hebbian: passed={passed} conf_adj={conf_adj}")
        # Show raw score
        engine = _get_hebbian()
        if engine:
            score, breakdown = engine.composite_score(token, signal)
            print(f"  composite_score={score:.3f} breakdown={breakdown}")

    else:
        print(f"Unknown command: {cmd}")
