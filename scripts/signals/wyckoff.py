#!/usr/bin/env python3
"""
wyckoff.py — Wyckoff Accumulation/Distribution Pattern Recognition.

Detects Wyckoff accumulation springs (LONG) and distribution upthrusts (SHORT)
using volume and price structure analysis on 5m candles.

Wyckoff Accumulation (LONG signal):
  Phase A: Selling climax (SC) — high volume + sharp drop
  Phase B: Trading range builds
  Phase C: Spring — false breakdown below support on low volume
  Phase D: Sign of strength (SOS) — price breaks above resistance
  → LONG entry on SOS confirmation

Wyckoff Distribution (SHORT signal):
  Phase A: Buying climax (BC) — high volume + sharp rise
  Phase B: Trading range builds
  Phase C: Upthrust — false breakout above resistance on low volume
  Phase D: Sign of weakness (SOW) — price breaks below support
  → SHORT entry on SOW confirmation

Data source: candles_5m from candles.db
Timer: runs every minute via signals_runner (fast signal)
"""

import sys
import os
import time
import sqlite3
from typing import Optional, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from paths import CANDLES_DB, RUNTIME_DB
from signal_schema import add_signal

# Pattern recognition for mean-reversion quality filtering
try:
    from pattern_recognition import detect_extended_move, detect_capitulation, detect_higher_low, detect_sharp_reversal
    HAS_PATTERN_RECOGNITION = True
except ImportError:
    HAS_PATTERN_RECOGNITION = False

# ── Config ──────────────────────────────────────────────────────────────────

WYCKOFF_LOOKBACK = 100       # candles to analyze (~8h at 5m)
WYCKOFF_MIN_BARS = 60        # minimum candles for analysis
WYCKOFF_ATR_PERIOD = 14

# Volume analysis
VOLUME_SPIKE_MULT = 1.8      # volume > 1.8x average = climax candidate (was 2.0)
VOLUME_LOW_MULT = 0.5        # volume < 0.5x average = low volume (spring/upthrust)

# Price structure
RANGE_MIN_BARS = 20          # minimum bars to establish trading range
SPRING_THRESHOLD = 0.2       # spring: price drops 0.2% below range low (was 0.3)
UPTHRUST_THRESHOLD = 0.3     # upthrust: price rises 0.3% above range high
SOS_THRESHOLD = 0.4          # sign of strength: price rises 0.4% above range high (was 0.5)
SOW_THRESHOLD = 0.5          # sign of weakness: price drops 0.5% below range low

# Confirmation
CONFIRMATION_BARS = 3        # bars confirming breakout
MIN_CLIMAX_VOLUME = 2.0      # climax volume must be > 2.0x average (was 2.5)

# Confidence scoring
BASE_CONFIDENCE = 60
CLIMAX_BONUS = 5             # per climax detected
SPRING_BONUS = 8             # spring/upthrust detected
SOS_SOW_BONUS = 5            # sign of strength/weakness confirmed
VOLUME_DIVERGENCE_BONUS = 3  # volume decreases during range

MAX_CONFIDENCE = 85

# Cooldown
COOLDOWN_BARS = 30           # don't fire again within 30 bars (2.5h)


def log(msg):
    print(f"  [wyckoff] {msg}")


# ── Data Fetching ───────────────────────────────────────────────────────────

def _get_candles_5m(token: str, lookback: int = WYCKOFF_LOOKBACK) -> List[Dict]:
    """Fetch 5m OHLCV candles from candles.db, oldest first."""
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        try:
            c = conn.cursor()
            c.execute("""
                SELECT ts, open, high, low, close, volume
                FROM candles_5m
                WHERE token = ?
                ORDER BY ts DESC
                LIMIT ?
            """, (token.upper(), lookback))
            rows = c.fetchall()
        finally:
            conn.close()

        if not rows:
            return []

        # Freshness check
        if (time.time() - rows[0][0]) > 600:
            return []

        rows.reverse()
        return [
            {'ts': r[0], 'open': r[1], 'high': r[2],
             'low': r[3], 'close': r[4], 'volume': r[5]}
            for r in rows
        ]
    except Exception:
        return []


def _atr(candles: List[Dict], period: int = WYCKOFF_ATR_PERIOD) -> Optional[float]:
    """Compute ATR."""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        h, l, prev = candles[i]['high'], candles[i]['low'], candles[i-1]['close']
        tr = max(h - l, abs(h - prev), abs(l - prev))
        trs.append(tr)
    if len(trs) < period:
        return None
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


# ── Volume Analysis ─────────────────────────────────────────────────────────

def _compute_volume_sma(candles: List[Dict], period: int = 20) -> List[float]:
    """Compute volume SMA for each bar."""
    volumes = [c['volume'] for c in candles]
    sma = []
    for i in range(len(volumes)):
        start = max(0, i - period + 1)
        sma.append(sum(volumes[start:i+1]) / (i - start + 1))
    return sma


def _find_climax(candles: List[Dict], vol_sma: List[float], direction: str) -> Optional[int]:
    """Find selling/buying climax index.

    Climax: volume > MIN_CLIMAX_VOLUME * avg, with sharp price move.
    Returns index of climax bar or None.
    """
    for i in range(20, len(candles)):
        if vol_sma[i] <= 0:
            continue
        vol_ratio = candles[i]['volume'] / vol_sma[i]
        if vol_ratio < MIN_CLIMAX_VOLUME:
            continue

        # Check price move
        price_change = (candles[i]['close'] - candles[i-1]['close']) / candles[i-1]['close'] * 100

        if direction == 'accumulation' and price_change < -0.3:
            return i  # selling climax
        elif direction == 'distribution' and price_change > 0.3:
            return i  # buying climax

    # Fallback: use capitulation detection (wick-based exhaustion)
    if HAS_PATTERN_RECOGNITION:
        for i in range(20, len(candles)):
            cap = detect_capitulation(candles[max(0, i-5):i+1])
            if cap['capitulation']:
                if direction == 'accumulation' and cap['type'] == 'bottom':
                    return i  # capitulation = selling exhaustion
                elif direction == 'distribution' and cap['type'] == 'top':
                    return i  # capitulation = buying exhaustion

    return None


# ── Range Detection ─────────────────────────────────────────────────────────

def _find_trading_range(candles: List[Dict], start: int, min_bars: int = RANGE_MIN_BARS) -> Optional[Tuple[float, float, int, int]]:
    """Find trading range after climax.

    Returns (range_high, range_low, range_start, range_end) or None.
    """
    if start + min_bars >= len(candles):
        return None

    # Find range from climax onward
    range_candles = candles[start:]
    highs = [c['high'] for c in range_candles]
    lows = [c['low'] for c in range_candles]

    # Initial range from first 20 bars
    range_high = max(highs[:min_bars])
    range_low = min(lows[:min_bars])

    # Expand range if price stays within bounds
    range_end = min_bars
    for i in range(min_bars, len(range_candles)):
        if highs[i] <= range_high * 1.005 and lows[i] >= range_low * 0.995:
            range_end = i
        else:
            break

    if range_end < min_bars:
        return None

    return range_high, range_low, start, start + range_end


# ── Spring/Upthrust Detection ──────────────────────────────────────────────

def _detect_spring(candles: List[Dict], range_low: float, range_start: int,
                   range_end: int, vol_sma: List[float]) -> Optional[int]:
    """Detect Wyckoff spring (false breakdown below support).

    Spring: price drops below range_low on LOW volume, then recovers.
    Returns index of spring bar or None.
    """
    for i in range(range_end, min(range_end + 20, len(candles))):
        if vol_sma[i] <= 0:
            continue

        # Price must drop below range low
        drop_pct = (range_low - candles[i]['low']) / range_low * 100
        if drop_pct < SPRING_THRESHOLD:
            continue

        # Volume must be LOW (spring on low volume = fake breakdown)
        vol_ratio = candles[i]['volume'] / vol_sma[i]
        if vol_ratio > VOLUME_LOW_MULT * 2:
            continue

        # Next bar(s) must recover above range low (allow 1-3 bars)
        recovered = False
        for j in range(i + 1, min(i + 4, len(candles))):
            recovery = (candles[j]['close'] - range_low) / range_low * 100
            if recovery > 0:
                recovered = True
                break
        if recovered:
            return i

    return None


def _detect_upthrust(candles: List[Dict], range_high: float, range_start: int,
                     range_end: int, vol_sma: List[float]) -> Optional[int]:
    """Detect Wyckoff upthrust (false breakout above resistance).

    Upthrust: price rises above range_high on LOW volume, then reverses.
    Returns index of upthrust bar or None.
    """
    for i in range(range_end, min(range_end + 20, len(candles))):
        if vol_sma[i] <= 0:
            continue

        # Price must rise above range high
        rise_pct = (candles[i]['high'] - range_high) / range_high * 100
        if rise_pct < UPTHRUST_THRESHOLD:
            continue

        # Volume must be LOW (upthrust on low volume = fake breakout)
        vol_ratio = candles[i]['volume'] / vol_sma[i]
        if vol_ratio > VOLUME_LOW_MULT * 2:
            continue

        # Next bar(s) must reverse below range high (allow 1-3 bars)
        reversed_ok = False
        for j in range(i + 1, min(i + 4, len(candles))):
            reversal = (range_high - candles[j]['close']) / range_high * 100
            if reversal > 0:
                reversed_ok = True
                break
        if reversed_ok:
            return i

    return None


# ── Sign of Strength/Weakness ──────────────────────────────────────────────

def _detect_sos(candles: List[Dict], range_high: float, start: int,
                vol_sma: List[float]) -> Optional[int]:
    """Detect sign of strength — price breaks above resistance with volume."""
    for i in range(start, min(start + 15, len(candles))):
        break_pct = (candles[i]['close'] - range_high) / range_high * 100
        if break_pct < SOS_THRESHOLD:
            continue

        # Volume should increase
        if vol_sma[i] > 0:
            vol_ratio = candles[i]['volume'] / vol_sma[i]
            if vol_ratio >= 1.2:
                # Pattern recognition: confirm sharp reversal on breakout bar
                if HAS_PATTERN_RECOGNITION:
                    rev = detect_sharp_reversal(candles[:i+1], min_pct=0.15)
                    if rev['reversal'] and rev['direction'] == 'LONG':
                        return i  # Strong confirmation
                else:
                    return i

    return None


def _detect_sow(candles: List[Dict], range_low: float, start: int,
                vol_sma: List[float]) -> Optional[int]:
    """Detect sign of weakness — price breaks below support with volume."""
    for i in range(start, min(start + 15, len(candles))):
        break_pct = (range_low - candles[i]['close']) / range_low * 100
        if break_pct < SOW_THRESHOLD:
            continue

        # Volume should increase
        if vol_sma[i] > 0:
            vol_ratio = candles[i]['volume'] / vol_sma[i]
            if vol_ratio >= 1.2:
                return i

    return None


# ── Confirmation ────────────────────────────────────────────────────────────

def _confirm_breakout(candles: List[Dict], direction: str, breakout_idx: int,
                      level: float, bars: int = CONFIRMATION_BARS) -> bool:
    """Confirm breakout stays beyond level for N bars."""
    end = min(breakout_idx + bars, len(candles))
    if end - breakout_idx < bars:
        return False

    for i in range(breakout_idx, end):
        if direction == 'LONG' and candles[i]['close'] < level:
            return False
        if direction == 'SHORT' and candles[i]['close'] > level:
            return False

    return True


# ── Main Detection ──────────────────────────────────────────────────────────

def detect_wyckoff(token: str, candles: List[Dict]) -> Optional[Dict]:
    """Detect Wyckoff accumulation/distribution pattern.

    Returns signal dict if triggered, else None.
    """
    if len(candles) < WYCKOFF_MIN_BARS:
        return None

    # Pre-filter: only search for Wyckoff after extended move (pattern recognition)
    if HAS_PATTERN_RECOGNITION:
        ext = detect_extended_move(candles, min_pct=0.3, min_bars=18)
        if not ext['moved']:
            return None  # No extended move = no Wyckoff setup

    atr = _atr(candles)
    if atr is None:
        return None

    vol_sma = _compute_volume_sma(candles)

    # ── Try Accumulation (LONG) ─────────────────────────────────────────
    climax_idx = _find_climax(candles, vol_sma, 'accumulation')
    if climax_idx is not None:
        # Find trading range after climax
        range_result = _find_trading_range(candles, climax_idx)
        if range_result:
            range_high, range_low, range_start, range_end = range_result

            # Look for spring
            spring_idx = _detect_spring(candles, range_low, range_start, range_end, vol_sma)
            if spring_idx is not None:
                # Pattern recognition: confirm higher low after spring
                if HAS_PATTERN_RECOGNITION:
                    hl = detect_higher_low(candles[:spring_idx+1], lookback=18)
                    if hl['higher_low']:
                        pass  # Higher low confirmed — good structure
                    # Don't block, just adjust confidence later

                # Look for sign of strength after spring
                sos_idx = _detect_sos(candles, range_high, spring_idx, vol_sma)
                if sos_idx is not None:
                    # Confirm breakout
                    if _confirm_breakout(candles, 'LONG', sos_idx, range_high):
                        # Score confidence
                        conf = BASE_CONFIDENCE
                        conf += CLIMAX_BONUS
                        conf += SPRING_BONUS
                        conf += SOS_SOW_BONUS

                        # Volume divergence bonus (volume decreases in range)
                        if range_end > range_start + 10:
                            early_vol = sum(vol_sma[range_start:range_start+10]) / 10
                            late_vol = sum(vol_sma[range_end-10:range_end]) / 10
                            if late_vol < early_vol * 0.7:
                                conf += VOLUME_DIVERGENCE_BONUS

                        # Higher low confirmation bonus
                        if HAS_PATTERN_RECOGNITION and hl['higher_low']:
                            conf += 3

                        conf = min(conf, MAX_CONFIDENCE)

                        return {
                            'token': token,
                            'direction': 'LONG',
                            'signal_type': 'wyckoff_accumulation',
                            'confidence': conf,
                            'metadata': {
                                'climax_idx': climax_idx,
                                'spring_idx': spring_idx,
                                'sos_idx': sos_idx,
                                'range_high': range_high,
                                'range_low': range_low,
                            }
                        }

    # ── Try Distribution (SHORT) ────────────────────────────────────────
    climax_idx = _find_climax(candles, vol_sma, 'distribution')
    if climax_idx is not None:
        range_result = _find_trading_range(candles, climax_idx)
        if range_result:
            range_high, range_low, range_start, range_end = range_result

            # Look for upthrust
            upthrust_idx = _detect_upthrust(candles, range_high, range_start, range_end, vol_sma)
            if upthrust_idx is not None:
                # Look for sign of weakness after upthrust
                sow_idx = _detect_sow(candles, range_low, upthrust_idx, vol_sma)
                if sow_idx is not None:
                    # Confirm breakout
                    if _confirm_breakout(candles, 'SHORT', sow_idx, range_low):
                        conf = BASE_CONFIDENCE
                        conf += CLIMAX_BONUS
                        conf += SPRING_BONUS  # upthrust bonus
                        conf += SOS_SOW_BONUS

                        # Volume divergence
                        if range_end > range_start + 10:
                            early_vol = sum(vol_sma[range_start:range_start+10]) / 10
                            late_vol = sum(vol_sma[range_end-10:range_end]) / 10
                            if late_vol < early_vol * 0.7:
                                conf += VOLUME_DIVERGENCE_BONUS

                        conf = min(conf, MAX_CONFIDENCE)

                        return {
                            'token': token,
                            'direction': 'SHORT',
                            'signal_type': 'wyckoff_distribution',
                            'confidence': conf,
                            'metadata': {
                                'climax_idx': climax_idx,
                                'upthrust_idx': upthrust_idx,
                                'sow_idx': sow_idx,
                                'range_high': range_high,
                                'range_low': range_low,
                            }
                        }

    return None


# ── Signal Entry Point ──────────────────────────────────────────────────────

def run(prices_dict: Dict = None) -> int:
    """Entry point for signals_runner.

    Scans all tokens for Wyckoff accumulation/distribution patterns.
    Returns number of signals written to DB.
    """
    from signal_schema import get_all_latest_prices, price_age_minutes
    from signal_gen import is_delisted, recent_trade_exists, MIN_TRADE_INTERVAL_MINUTES
    from position_manager import get_open_positions

    if prices_dict is None:
        prices_dict = get_all_latest_prices()

    open_pos = {p['token']: p['direction'] for p in get_open_positions()}
    added = 0

    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue

        price = data.get('price')
        if not price or price <= 0:
            continue

        # Guards
        if token.upper() in open_pos:
            continue
        if is_delisted(token.upper()):
            continue
        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
            continue
        if price_age_minutes(token) > 10:
            continue

        # Get candles
        candles = _get_candles_5m(token)
        if not candles or len(candles) < WYCKOFF_MIN_BARS:
            continue

        # Detect pattern
        sig = detect_wyckoff(token, candles)
        if sig is not None:
            # ── Per-direction kill-switch ─────────────────────────────────────
            try:
                from hermes_constants import WYCKOFF_PLUS_ENABLED, WYCKOFF_MINUS_ENABLED
                if sig['direction'] == 'LONG' and not WYCKOFF_PLUS_ENABLED:
                    continue
                if sig['direction'] == 'SHORT' and not WYCKOFF_MINUS_ENABLED:
                    continue
            except ImportError:
                pass

            result = add_signal(
                token=token,
                direction=sig['direction'],
                signal_type=sig['signal_type'],
                confidence=sig['confidence'],
                source='wyckoff',
                signal_metadata=sig.get('metadata'),
            )
            if result:
                added += 1
                # Set cooldown to prevent duplicate signals
                from signal_gen import set_cooldown
                set_cooldown(token, sig['direction'], hours=COOLDOWN_BARS / 60.0)

    return added


if __name__ == '__main__':
    result = run()
    print(f"wyckoff: {result} signals")
