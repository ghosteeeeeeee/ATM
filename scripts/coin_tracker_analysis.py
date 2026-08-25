#!/usr/bin/env python3
"""
coin_tracker_analysis.py — Market structure analysis for coin_tracker.

Computes:
  - Wyckoff phase (accumulation, markup, distribution, markdown)
  - Elliott Wave count (impulse 1-5, corrective A-C)
  - Support/Resistance levels from pivots
  - Trend quality (ADX-like)
  - Volume profile (POC, value area)

All functions take lists of OHLCV dicts (oldest-first) and return structured results.
No DB access — pure computation. Importable by coin_tracker.py.
"""
import json
from typing import Optional, List, Dict, Tuple

# ── Pivot Detection ──────────────────────────────────────────────────────────

def find_pivots(candles: List[Dict], left: int = 5, right: int = 5) -> List[Dict]:
    """Find pivot highs and lows. Returns list of {idx, type, price, ts}.

    Pivot high: candle[i]['high'] > all neighbors within left/right bars.
    Pivot low: candle[i]['low'] < all neighbors within left/right bars.
    """
    if len(candles) < left + right + 1:
        return []

    pivots = []
    for i in range(left, len(candles) - right):
        # Pivot high
        is_high = True
        for j in range(i - left, i + right + 1):
            if j == i:
                continue
            if candles[j]['high'] >= candles[i]['high']:
                is_high = False
                break
        if is_high:
            pivots.append({
                'idx': i,
                'type': 'high',
                'price': candles[i]['high'],
                'ts': candles[i]['ts']
            })

        # Pivot low
        is_low = True
        for j in range(i - left, i + right + 1):
            if j == i:
                continue
            if candles[j]['low'] <= candles[i]['low']:
                is_low = False
                break
        if is_low:
            pivots.append({
                'idx': i,
                'type': 'low',
                'price': candles[i]['low'],
                'ts': candles[i]['ts']
            })

    return pivots


# ── Support/Resistance Levels ────────────────────────────────────────────────

def compute_sr_levels(candles: List[Dict], merge_pct: float = 0.5) -> List[Dict]:
    """Compute support/resistance levels from pivot points.

    Returns list of {price, strength, type} sorted by strength descending.
    strength = number of touches (pivots near this level).
    merge_pct: merge pivots within this % of each other.
    """
    pivots = find_pivots(candles, left=5, right=5)
    if not pivots:
        return []

    # Sort by price
    pivots.sort(key=lambda p: p['price'])

    # Merge nearby pivots
    levels = []
    for p in pivots:
        merged = False
        for level in levels:
            pct_diff = abs(p['price'] - level['price']) / level['price'] * 100
            if pct_diff < merge_pct:
                level['touches'] += 1
                # Update price to average
                level['price'] = (level['price'] * (level['touches'] - 1) + p['price']) / level['touches']
                merged = True
                break
        if not merged:
            levels.append({
                'price': p['price'],
                'touches': 1,
                'type': p['type'],
            })

    # Classify as support or resistance based on current price
    if candles:
        current_price = candles[-1]['close']
        for level in levels:
            if level['price'] < current_price:
                level['type'] = 'support'
            else:
                level['type'] = 'resistance'

    # Sort by touches (strength)
    levels.sort(key=lambda l: l['touches'], reverse=True)

    # Return top 10 levels
    return [{'price': l['price'], 'strength': l['touches'], 'type': l['type']}
            for l in levels[:10]]


# ── Wyckoff Phase Detection ──────────────────────────────────────────────────

def _volume_sma(candles: List[Dict], period: int = 20) -> List[float]:
    """Volume SMA for each bar."""
    volumes = [c['volume'] for c in candles]
    sma = []
    for i in range(len(volumes)):
        start = max(0, i - period + 1)
        sma.append(sum(volumes[start:i+1]) / (i - start + 1))
    return sma


def _atr(candles: List[Dict], period: int = 14) -> Optional[float]:
    """ATR from candle list."""
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


def _find_climax(candles: List[Dict], vol_sma: List[float], direction: str) -> Optional[int]:
    """Find selling/buying climax index. Returns index or None."""
    min_climax_vol = 2.0
    for i in range(20, len(candles)):
        if vol_sma[i] <= 0:
            continue
        vol_ratio = candles[i]['volume'] / vol_sma[i]
        if vol_ratio < min_climax_vol:
            continue

        price_change = (candles[i]['close'] - candles[i-1]['close']) / candles[i-1]['close'] * 100

        if direction == 'accumulation' and price_change < -0.3:
            return i
        elif direction == 'distribution' and price_change > 0.3:
            return i
    return None


def _find_range(candles: List[Dict], start: int, min_bars: int = 20) -> Optional[Tuple[float, float, int, int]]:
    """Find trading range after climax. Returns (high, low, start, end) or None."""
    if start + min_bars >= len(candles):
        return None

    range_candles = candles[start:]
    highs = [c['high'] for c in range_candles]
    lows = [c['low'] for c in range_candles]

    range_high = max(highs[:min_bars])
    range_low = min(lows[:min_bars])

    range_end = min_bars
    for i in range(min_bars, len(range_candles)):
        if highs[i] <= range_high * 1.005 and lows[i] >= range_low * 0.995:
            range_end = i
        else:
            break

    if range_end < min_bars:
        return None

    return range_high, range_low, start, start + range_end


def _detect_spring(candles: List[Dict], range_low: float, range_end: int,
                   vol_sma: List[float]) -> Optional[int]:
    """Detect spring (false breakdown below support on low volume)."""
    for i in range(range_end, min(range_end + 20, len(candles))):
        if vol_sma[i] <= 0:
            continue
        drop_pct = (range_low - candles[i]['low']) / range_low * 100
        if drop_pct < 0.2:
            continue
        vol_ratio = candles[i]['volume'] / vol_sma[i]
        if vol_ratio > 1.0:
            continue
        # Check recovery within 3 bars
        for j in range(i + 1, min(i + 4, len(candles))):
            if candles[j]['close'] > range_low:
                return i
    return None


def _detect_upthrust(candles: List[Dict], range_high: float, range_end: int,
                     vol_sma: List[float]) -> Optional[int]:
    """Detect upthrust (false breakout above resistance on low volume)."""
    for i in range(range_end, min(range_end + 20, len(candles))):
        if vol_sma[i] <= 0:
            continue
        rise_pct = (candles[i]['high'] - range_high) / range_high * 100
        if rise_pct < 0.3:
            continue
        vol_ratio = candles[i]['volume'] / vol_sma[i]
        if vol_ratio > 1.0:
            continue
        for j in range(i + 1, min(i + 4, len(candles))):
            if candles[j]['close'] < range_high:
                return i
    return None


def detect_wyckoff_phase(candles: List[Dict]) -> Dict:
    """Detect current Wyckoff phase.

    Returns: {phase, confidence, details}
    phase: 'accumulation', 'markup', 'distribution', 'markdown', 'none'
    """
    if len(candles) < 60:
        return {'phase': 'none', 'confidence': 0, 'details': 'insufficient data'}

    vol_sma = _volume_sma(candles)

    # Try accumulation (selling climax → range → spring → SOS)
    climax_idx = _find_climax(candles, vol_sma, 'accumulation')
    if climax_idx is not None:
        range_result = _find_range(candles, climax_idx)
        if range_result:
            range_high, range_low, range_start, range_end = range_result
            spring_idx = _detect_spring(candles, range_low, range_end, vol_sma)

            if spring_idx is not None:
                # Check for breakout above range (SOS)
                for i in range(spring_idx + 1, min(spring_idx + 15, len(candles))):
                    if candles[i]['close'] > range_high * 1.004:
                        return {
                            'phase': 'markup',
                            'confidence': 75,
                            'details': f'accumulation complete, spring at bar {spring_idx}, markup started'
                        }
                return {
                    'phase': 'accumulation',
                    'confidence': 65,
                    'details': f'climax at bar {climax_idx}, spring at bar {spring_idx}, awaiting SOS'
                }
            else:
                return {
                    'phase': 'accumulation',
                    'confidence': 50,
                    'details': f'climax at bar {climax_idx}, in range, no spring yet'
                }

    # Try distribution (buying climax → range → upthrust → SOW)
    climax_idx = _find_climax(candles, vol_sma, 'distribution')
    if climax_idx is not None:
        range_result = _find_range(candles, climax_idx)
        if range_result:
            range_high, range_low, range_start, range_end = range_result
            upthrust_idx = _detect_upthrust(candles, range_high, range_end, vol_sma)

            if upthrust_idx is not None:
                # Check for breakdown below range (SOW)
                for i in range(upthrust_idx + 1, min(upthrust_idx + 15, len(candles))):
                    if candles[i]['close'] < range_low * 0.995:
                        return {
                            'phase': 'markdown',
                            'confidence': 75,
                            'details': f'distribution complete, upthrust at bar {upthrust_idx}, markdown started'
                        }
                return {
                    'phase': 'distribution',
                    'confidence': 65,
                    'details': f'climax at bar {climax_idx}, upthrust at bar {upthrust_idx}, awaiting SOW'
                }
            else:
                return {
                    'phase': 'distribution',
                    'confidence': 50,
                    'details': f'climax at bar {climax_idx}, in range, no upthrust yet'
                }

    # No Wyckoff pattern detected
    return {'phase': 'none', 'confidence': 0, 'details': 'no Wyckoff pattern detected'}


# ── Elliott Wave Counting ────────────────────────────────────────────────────

def _fib_ratio(a: float, b: float) -> float:
    """Fibonacci ratio between two values."""
    if a == 0:
        return 0
    return abs(b / a)


def _is_impulse_wave(waves: List[Dict], direction: str) -> bool:
    """Check if 5 waves form a valid impulse.

    Rules:
    - Waves 1, 3, 5 move with trend (same direction)
    - Waves 2, 4 retrace against trend
    - Wave 3 is typically the longest (or at least not the shortest)
    - Relaxed Fibonacci: wave 2 retraces 20-85% of wave 1
    - Relaxed Fibonacci: wave 4 retraces 15-55% of wave 3
    """
    if len(waves) < 5:
        return False

    # Check wave directions
    for i in range(0, 5, 2):  # waves 1, 3, 5
        if waves[i]['direction'] != direction:
            return False
    for i in range(1, 5, 2):  # waves 2, 4
        if waves[i]['direction'] != ('down' if direction == 'up' else 'up'):
            return False

    # Wave 3 should not be shortest
    lengths = [abs(waves[i]['high'] - waves[i]['low']) for i in [0, 2, 4]]
    if min(lengths) == lengths[1]:  # wave 3 is shortest
        return False

    # Relaxed Fibonacci retracements
    w1_len = abs(waves[0]['high'] - waves[0]['low'])
    w2_len = abs(waves[1]['high'] - waves[1]['low'])
    w3_len = abs(waves[2]['high'] - waves[2]['low'])
    w4_len = abs(waves[3]['high'] - waves[3]['low'])

    if w1_len > 0:
        w2_retrace = w2_len / w1_len
        if w2_retrace < 0.20 or w2_retrace > 0.85:
            return False

    if w3_len > 0:
        w4_retrace = w4_len / w3_len
        if w4_retrace < 0.15 or w4_retrace > 0.55:
            return False

    return True


def _label_waves_from_pivots(pivots: List[Dict]) -> List[Dict]:
    """Convert pivot points into wave segments.

    Returns list of {high, low, direction, start_idx, end_idx}.
    """
    if len(pivots) < 2:
        return []

    waves = []
    for i in range(len(pivots) - 1):
        p1 = pivots[i]
        p2 = pivots[i + 1]

        if p1['type'] == 'low' and p2['type'] == 'high':
            direction = 'up'
            low = p1['price']
            high = p2['price']
        elif p1['type'] == 'high' and p2['type'] == 'low':
            direction = 'down'
            high = p1['price']
            low = p2['price']
        else:
            continue  # skip consecutive same-type pivots

        waves.append({
            'high': high,
            'low': low,
            'direction': direction,
            'start_idx': p1['idx'],
            'end_idx': p2['idx'],
        })

    return waves


def detect_ewave_count(candles_4h: List[Dict], candles_1h: List[Dict] = None) -> Dict:
    """Detect Elliott Wave count from 4h candles, optionally confirmed by 1h.

    Returns: {wave, direction, degree, confidence, details}
    wave: 1-5 for impulse, 'A','B','C' for corrective
    direction: 'up' or 'down' (main trend direction)
    degree: 'minuette' (short-term), 'minute' (medium), 'minor' (larger)
    """
    if len(candles_4h) < 50:
        return {'wave': None, 'direction': None, 'degree': None, 'confidence': 0,
                'details': 'insufficient 4h data'}

    # Find pivots on 4h
    pivots = find_pivots(candles_4h, left=3, right=3)
    if len(pivots) < 7:
        return {'wave': None, 'direction': None, 'degree': None, 'confidence': 0,
                'details': f'only {len(pivots)} pivots found, need 7+'}

    # Label waves from pivots
    waves = _label_waves_from_pivots(pivots)
    if len(waves) < 5:
        return {'wave': None, 'direction': None, 'degree': None, 'confidence': 0,
                'details': f'only {len(waves)} waves labeled, need 5+'}

    # Determine overall trend direction from first few waves
    up_waves = sum(1 for w in waves[:6] if w['direction'] == 'up')
    down_waves = sum(1 for w in waves[:6] if w['direction'] == 'down')
    overall_direction = 'up' if up_waves > down_waves else 'down'

    # Try to fit impulse pattern (5 waves)
    best_impulse = None
    best_score = 0

    for start in range(max(0, len(waves) - 8), len(waves) - 4):
        candidate = waves[start:start + 5]
        if len(candidate) < 5:
            continue

        # Check if this is a valid impulse
        if _is_impulse_wave(candidate, overall_direction):
            # Score based on Fibonacci quality
            score = 50
            w1 = abs(candidate[0]['high'] - candidate[0]['low'])
            w3 = abs(candidate[2]['high'] - candidate[2]['low'])
            w5 = abs(candidate[4]['high'] - candidate[4]['low'])

            # Wave 3 should be 1.0-2.0x wave 1
            if w1 > 0:
                ratio_13 = w3 / w1
                if 1.0 <= ratio_13 <= 2.0:
                    score += 15
                elif 0.8 <= ratio_13 <= 2.5:
                    score += 8

            # Wave 5 should be 0.5-1.0x wave 3
            if w3 > 0:
                ratio_35 = w5 / w3
                if 0.5 <= ratio_35 <= 1.0:
                    score += 10
                elif 0.3 <= ratio_35 <= 1.2:
                    score += 5

            # Penalize if wave 5 is very extended
            if w3 > 0 and w5 > w3 * 1.5:
                score -= 10

            if score > best_score:
                best_score = score
                best_impulse = {
                    'wave': 5,  # completed 5 waves
                    'direction': overall_direction,
                    'start_idx': start,
                }

    # Try to fit corrective pattern (A-B-C)
    best_corrective = None
    best_corr_score = 0

    for start in range(max(0, len(waves) - 5), len(waves) - 2):
        candidate = waves[start:start + 3]
        if len(candidate) < 3:
            continue

        # Corrective: A and C against trend, B with trend
        a_dir = candidate[0]['direction']
        b_dir = candidate[1]['direction']
        c_dir = candidate[2]['direction']

        # In a corrective, A and C should be same direction, B opposite
        if a_dir == c_dir and b_dir != a_dir:
            # Check Fibonacci relationships
            a_len = abs(candidate[0]['high'] - candidate[0]['low'])
            b_len = abs(candidate[1]['high'] - candidate[1]['low'])
            c_len = abs(candidate[2]['high'] - candidate[2]['low'])

            score = 40
            if a_len > 0:
                b_retrace = b_len / a_len
                if 0.38 <= b_retrace <= 0.78:
                    score += 10

            if a_len > 0:
                c_ratio = c_len / a_len
                if 0.8 <= c_ratio <= 1.2:
                    score += 15  # C = A is common
                elif 0.5 <= c_ratio <= 1.5:
                    score += 8

            if score > best_corr_score:
                best_corr_score = score
                best_corrective = {
                    'wave': 'C',
                    'direction': overall_direction,
                    'start_idx': start,
                }

    # Pick the best fit
    if best_impulse and best_score > best_corr_score:
        return {
            'wave': best_impulse['wave'],
            'direction': overall_direction,
            'degree': 'minute',  # 4h timeframe = minute degree
            'confidence': min(85, best_score),
            'details': f'5-wave impulse complete, trend {overall_direction}'
        }
    elif best_corrective and best_corr_score > 30:
        return {
            'wave': best_corrective['wave'],
            'direction': overall_direction,
            'degree': 'minute',
            'confidence': min(75, best_corr_score),
            'details': f'A-B-C correction complete, trend {overall_direction}'
        }

    # Fallback: estimate wave count from last pivot
    last_pivot = pivots[-1]
    prev_pivot = pivots[-2] if len(pivots) > 1 else None

    if prev_pivot:
        if last_pivot['type'] == 'high' and prev_pivot['type'] == 'low':
            # Recent move was up — could be wave 1, 3, or 5
            # Estimate based on number of completed swings
            swing_count = len([w for w in waves if w['direction'] == overall_direction])
            if swing_count <= 1:
                wave_est = 1
            elif swing_count <= 3:
                wave_est = 3
            else:
                wave_est = 5
        else:
            # Recent move was down — could be wave 2 or 4
            swing_count = len([w for w in waves if w['direction'] != overall_direction])
            if swing_count <= 1:
                wave_est = 2
            else:
                wave_est = 4

        return {
            'wave': wave_est,
            'direction': overall_direction,
            'degree': 'minute',
            'confidence': 35,
            'details': f'estimated from {len(pivots)} pivots, {len(waves)} waves'
        }

    return {'wave': None, 'direction': None, 'degree': None, 'confidence': 0,
            'details': 'could not determine wave count'}


# ── Trend Quality ────────────────────────────────────────────────────────────

def compute_trend_quality(candles_5m: List[Dict], candles_1h: List[Dict] = None) -> Dict:
    """Compute trend quality using ADX-like measurement.

    Returns: {score (0-100), direction, adx, details}
    """
    if len(candles_5m) < 30:
        return {'score': 50, 'direction': 'NEUTRAL', 'adx': 0, 'details': 'insufficient data'}

    # Compute True Range and directional movement
    trs = []
    plus_dm = []
    minus_dm = []

    for i in range(1, len(candles_5m)):
        h = candles_5m[i]['high']
        l = candles_5m[i]['low']
        prev_h = candles_5m[i-1]['high']
        prev_l = candles_5m[i-1]['low']
        prev_c = candles_5m[i-1]['close']

        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        trs.append(tr)

        up_move = h - prev_h
        down_move = prev_l - l

        if up_move > down_move and up_move > 0:
            plus_dm.append(up_move)
        else:
            plus_dm.append(0)

        if down_move > up_move and down_move > 0:
            minus_dm.append(down_move)
        else:
            minus_dm.append(0)

    if len(trs) < 14:
        return {'score': 50, 'direction': 'NEUTRAL', 'adx': 0, 'details': 'insufficient TR data'}

    # Smoothed averages (Wilder's method)
    period = 14
    atr = sum(trs[:period]) / period
    plus_di_sum = sum(plus_dm[:period]) / period
    minus_di_sum = sum(minus_dm[:period]) / period

    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
        plus_di_sum = (plus_di_sum * (period - 1) + plus_dm[i]) / period
        minus_di_sum = (minus_di_sum * (period - 1) + minus_dm[i]) / period

    if atr == 0:
        return {'score': 50, 'direction': 'NEUTRAL', 'adx': 0, 'details': 'ATR is zero'}

    plus_di = (plus_di_sum / atr) * 100
    minus_di = (minus_di_sum / atr) * 100

    # DX and ADX
    di_sum = plus_di + minus_di
    if di_sum == 0:
        dx = 0
    else:
        dx = abs(plus_di - minus_di) / di_sum * 100

    # Smooth ADX (simplified — just use recent DX values)
    adx = dx  # For full ADX we'd smooth over multiple periods

    # Direction
    if plus_di > minus_di:
        direction = 'BULL'
    elif minus_di > plus_di:
        direction = 'BEAR'
    else:
        direction = 'NEUTRAL'

    # Score: smooth curve based on ADX (0-100 scale)
    # ADX 0 = no trend (20), ADX 20 = developing (50), ADX 40 = strong (80), ADX 60+ = very strong (95)
    score = 20 + (adx / 60) * 75
    score = max(20, min(95, score))

    # Bonus for directional clarity
    if adx > 20:
        di_diff = abs(plus_di - minus_di)
        score += min(10, di_diff / 3)

    return {
        'score': min(100, score),
        'direction': direction,
        'adx': round(adx, 1),
        'plus_di': round(plus_di, 1),
        'minus_di': round(minus_di, 1),
        'details': f'ADX={adx:.1f}, +DI={plus_di:.1f}, -DI={minus_di:.1f}'
    }


# ── Volume Profile ───────────────────────────────────────────────────────────

def compute_volume_profile(candles: List[Dict], num_bins: int = 50) -> Dict:
    """Compute volume profile from 5m candles.

    Returns: {poc, value_area_high, value_area_low, balance, details}
    poc: Point of Control (price with highest volume)
    value_area: 70% of volume centered around POC
    balance: True if price is in balanced area, False if imbalanced
    """
    if len(candles) < 10:
        return {'poc': None, 'value_area_high': None, 'value_area_low': None,
                'balance': None, 'details': 'insufficient data'}

    # Find price range
    all_highs = [c['high'] for c in candles]
    all_lows = [c['low'] for c in candles]
    price_min = min(all_lows)
    price_max = max(all_highs)

    if price_max == price_min:
        return {'poc': price_min, 'value_area_high': price_max, 'value_area_low': price_min,
                'balance': True, 'details': 'single price level'}

    # Create bins
    bin_size = (price_max - price_min) / num_bins
    bins = [0.0] * num_bins

    # Accumulate volume into bins
    for c in candles:
        avg_price = (c['high'] + c['low'] + c['close']) / 3
        bin_idx = int((avg_price - price_min) / bin_size)
        bin_idx = max(0, min(num_bins - 1, bin_idx))
        bins[bin_idx] += c['volume']

    # Find POC
    poc_idx = bins.index(max(bins))
    poc = price_min + (poc_idx + 0.5) * bin_size

    # Find value area (70% of volume centered on POC)
    total_volume = sum(bins)
    target_volume = total_volume * 0.7

    va_low_idx = poc_idx
    va_high_idx = poc_idx
    accumulated = bins[poc_idx]

    while accumulated < target_volume and (va_low_idx > 0 or va_high_idx < num_bins - 1):
        # Expand towards the side with more volume
        down_vol = bins[va_low_idx - 1] if va_low_idx > 0 else 0
        up_vol = bins[va_high_idx + 1] if va_high_idx < num_bins - 1 else 0

        if down_vol >= up_vol and va_low_idx > 0:
            va_low_idx -= 1
            accumulated += bins[va_low_idx]
        elif va_high_idx < num_bins - 1:
            va_high_idx += 1
            accumulated += bins[va_high_idx]
        else:
            break

    value_area_low = price_min + va_low_idx * bin_size
    value_area_high = price_min + (va_high_idx + 1) * bin_size

    # Balance check: is current price within value area?
    current_price = candles[-1]['close']
    balance = value_area_low <= current_price <= value_area_high

    return {
        'poc': round(poc, 8),
        'value_area_high': round(value_area_high, 8),
        'value_area_low': round(value_area_low, 8),
        'balance': balance,
        'details': f'POC={poc:.8f}, VA=[{value_area_low:.8f}, {value_area_high:.8f}], {"balanced" if balance else "imbalanced"}'
    }


# ── Main Analysis Entry Point ────────────────────────────────────────────────

def analyze_coin(candles_5m: List[Dict], candles_1h: List[Dict],
                 candles_4h: List[Dict]) -> Dict:
    """Run all analysis on a coin. Returns dict with all results.

    All candle lists are oldest-first, with keys: ts, open, high, low, close, volume.
    """
    result = {}

    # Wyckoff phase (use 1h for medium-term structure)
    result['wyckoff'] = detect_wyckoff_phase(candles_1h if candles_1h else candles_5m)

    # Elliott Wave (use 4h for primary count)
    result['ewave'] = detect_ewave_count(candles_4h, candles_1h)

    # S/R levels (use 1h)
    result['sr_levels'] = compute_sr_levels(candles_1h if candles_1h else candles_5m)

    # Trend quality (use 5m, optionally confirmed by 1h)
    result['trend'] = compute_trend_quality(candles_5m, candles_1h)

    # Volume profile (use 5m)
    result['vol_profile'] = compute_volume_profile(candles_5m)

    # Setup detection and clustering
    result['setup'] = detect_setup(candles_5m, candles_1h, candles_4h)

    return result


# ── Setup Detection ──────────────────────────────────────────────────────────

def detect_wyckoff_forming(candles: List[Dict]) -> Dict:
    """Detect Wyckoff patterns that are FORMING but not complete.

    Returns: {forming: bool, phase, confidence, details}
    """
    if len(candles) < 40:
        return {'forming': False, 'phase': 'none', 'confidence': 0, 'details': 'insufficient data'}

    vol_sma = _volume_sma(candles)

    # Check for recent climax (last 30 bars)
    climax_idx = _find_climax(candles[-30:], vol_sma[-30:], 'accumulation')
    if climax_idx is not None:
        # Climax detected — range should be forming
        return {
            'forming': True,
            'phase': 'accumulation',
            'confidence': 40,
            'details': f'selling climax detected at bar {len(candles) - 30 + climax_idx}, range forming'
        }

    # Check for range without climax (consolidation)
    recent = candles[-40:]
    highs = [c['high'] for c in recent]
    lows = [c['low'] for c in recent]
    range_pct = (max(highs) - min(lows)) / min(lows) * 100 if min(lows) > 0 else 0

    if range_pct < 3.0:  # Tight range = consolidation
        # Check for volume decline (characteristic of accumulation)
        early_vol = sum(vol_sma[-40:-20]) / 20
        late_vol = sum(vol_sma[-20:]) / 20
        vol_declining = late_vol < early_vol * 0.8

        if vol_declining:
            return {
                'forming': True,
                'phase': 'accumulation',
                'confidence': 30,
                'details': f'tight range ({range_pct:.1f}%), volume declining — potential accumulation'
            }

    # Check for distribution forming
    climax_idx_d = _find_climax(candles[-30:], vol_sma[-30:], 'distribution')
    if climax_idx_d is not None:
        return {
            'forming': True,
            'phase': 'distribution',
            'confidence': 40,
            'details': f'buying climax detected, distribution phase forming'
        }

    return {'forming': False, 'phase': 'none', 'confidence': 0, 'details': 'no pattern forming'}


def detect_ewave_forming(candles_4h: List[Dict]) -> Dict:
    """Detect Elliott Wave patterns that are FORMING.

    Returns: {forming: bool, expected_wave, confidence, details}
    """
    if len(candles_4h) < 30:
        return {'forming': False, 'expected_wave': None, 'confidence': 0, 'details': 'insufficient data'}

    pivots = find_pivots(candles_4h, left=3, right=3)
    if len(pivots) < 5:
        return {'forming': False, 'expected_wave': None, 'confidence': 0, 'details': 'insufficient pivots'}

    waves = _label_waves_from_pivots(pivots)
    if len(waves) < 3:
        return {'forming': False, 'expected_wave': None, 'confidence': 0, 'details': 'insufficient waves'}

    # Determine what wave should come next
    last_wave = waves[-1]
    prev_wave = waves[-2] if len(waves) > 1 else None

    # Count completed waves
    up_count = sum(1 for w in waves[-6:] if w['direction'] == 'up')
    down_count = sum(1 for w in waves[-6:] if w['direction'] == 'down')

    # Estimate current wave position
    if up_count > down_count:
        # We're in an uptrend — expect correction next
        expected = 4 if up_count >= 3 else 2
        confidence = 35 if expected == 2 else 45
        return {
            'forming': True,
            'expected_wave': expected,
            'confidence': confidence,
            'details': f'uptrend with {up_count} up waves, expecting wave {expected} correction'
        }
    elif down_count > up_count:
        # We're in a downtrend — expect bounce next
        expected = 4 if down_count >= 3 else 2
        confidence = 35 if expected == 2 else 45
        return {
            'forming': True,
            'expected_wave': expected,
            'confidence': confidence,
            'details': f'downtrend with {down_count} down waves, expecting wave {expected} bounce'
        }

    return {'forming': False, 'expected_wave': None, 'confidence': 0, 'details': 'no clear wave forming'}


def detect_sr_testing(candles: List[Dict], sr_levels: List[Dict]) -> Dict:
    """Detect if price is testing S/R levels.

    Returns: {testing: bool, type, level, distance_pct, details}
    """
    if not candles or not sr_levels:
        return {'testing': False, 'type': None, 'level': None, 'distance_pct': None, 'details': 'no data'}

    current_price = candles[-1]['close']
    if current_price <= 0:
        return {'testing': False, 'type': None, 'level': None, 'distance_pct': None, 'details': 'invalid price'}

    # Find nearest support and resistance
    supports = [s for s in sr_levels if s['type'] == 'support']
    resistances = [r for r in sr_levels if r['type'] == 'resistance']

    nearest_support = max(supports, key=lambda s: s['price']) if supports else None
    nearest_resistance = min(resistances, key=lambda r: r['price']) if resistances else None

    # Check if price is near a level (within 1%)
    test_threshold = 1.0  # percent

    if nearest_support:
        dist = (current_price - nearest_support['price']) / nearest_support['price'] * 100
        if 0 <= dist <= test_threshold:
            return {
                'testing': True,
                'type': 'support',
                'level': nearest_support['price'],
                'distance_pct': dist,
                'details': f'testing support at {nearest_support["price"]:.8f} ({dist:.2f}% away)'
            }

    if nearest_resistance:
        dist = (nearest_resistance['price'] - current_price) / current_price * 100
        if 0 <= dist <= test_threshold:
            return {
                'testing': True,
                'type': 'resistance',
                'level': nearest_resistance['price'],
                'distance_pct': dist,
                'details': f'testing resistance at {nearest_resistance["price"]:.8f} ({dist:.2f}% away)'
            }

    return {'testing': False, 'type': None, 'level': None, 'distance_pct': None, 'details': 'not near any level'}


def compute_recency_weight(candles: List[Dict], lookback: int = 20) -> float:
    """Compute recency weight based on recent price action consistency.

    Returns 0.0-1.0. Higher = more consistent recent action = more reliable.
    """
    if len(candles) < lookback:
        return 0.5

    recent = candles[-lookback:]
    closes = [c['close'] for c in recent if c['close']]

    if len(closes) < 5:
        return 0.5

    # Count direction changes (fewer = more consistent)
    changes = 0
    for i in range(1, len(closes)):
        if closes[i] != closes[i-1]:
            changes += 1

    # Normalize: 0 changes = perfect consistency (1.0), many changes = noisy (0.3)
    consistency = max(0.3, 1.0 - (changes / len(closes)) * 0.7)

    # Recent momentum (last 5 bars vs previous 5)
    if len(closes) >= 10:
        recent_momentum = closes[-1] - closes[-5]
        earlier_momentum = closes[-5] - closes[-10]
        if recent_momentum * earlier_momentum > 0:  # Same direction
            consistency = min(1.0, consistency + 0.15)

    return consistency


def compute_clustering_score(wyckoff: Dict, ewave: Dict, trend: Dict, sr_testing: Dict) -> Dict:
    """Compute clustering score — how many indicators align.

    Returns: {score: 0-100, bullish_clusters: int, bearish_clusters: int, details}
    """
    bullish = 0
    bearish = 0

    # Wyckoff signals
    if wyckoff.get('phase') == 'accumulation':
        bullish += 1
    elif wyckoff.get('phase') == 'distribution':
        bearish += 1
    if wyckoff.get('forming') and wyckoff.get('phase') == 'accumulation':
        bullish += 0.5

    # Elliott Wave signals
    if ewave.get('wave') in [1, 2, 3] and ewave.get('direction') == 'up':
        bullish += 1
    elif ewave.get('wave') in [1, 2, 3] and ewave.get('direction') == 'down':
        bearish += 1
    if ewave.get('forming'):
        if ewave.get('expected_wave') in [2, 4]:  # Correction = entry opportunity
            bullish += 0.5

    # Trend signals
    if trend.get('direction') == 'BULL':
        bullish += 1
    elif trend.get('direction') == 'BEAR':
        bearish += 1

    # S/R testing
    if sr_testing.get('testing'):
        if sr_testing.get('type') == 'support':
            bullish += 1
        elif sr_testing.get('type') == 'resistance':
            bearish += 1

    # Compute score
    total = bullish + bearish
    if total == 0:
        score = 50
    else:
        score = (bullish / total) * 100 if bullish > bearish else (bearish / total) * 100
        # Boost for higher total clusters
        score = min(100, score + total * 5)

    return {
        'score': score,
        'bullish_clusters': bullish,
        'bearish_clusters': bearish,
        'details': f'{bullish:.1f} bullish, {bearish:.1f} bearish clusters'
    }


def compute_setup_strength(wyckoff: Dict, ewave: Dict, trend: Dict, sr_testing: Dict,
                           clustering: Dict, recency: float) -> Dict:
    """Compute overall setup strength — is a trade setup forming?

    Returns: {score: 0-100, setup_type, confidence, details}
    """
    score = 0
    factors = []

    # Wyckoff contribution
    if wyckoff.get('phase') in ('accumulation', 'markup'):
        score += 25
        factors.append(f'wyckoff={wyckoff["phase"]}')
    elif wyckoff.get('forming'):
        score += 15
        factors.append(f'wyckoff_forming={wyckoff.get("phase")}')

    # Elliott Wave contribution
    if ewave.get('wave') in [2, 3]:  # Best entry points
        score += 20
        factors.append(f'ewave={ewave["wave"]}')
    elif ewave.get('forming') and ewave.get('expected_wave') in [2, 4]:
        score += 12
        factors.append(f'ewave_forming={ewave.get("expected_wave")}')

    # Trend contribution
    if trend.get('score', 0) > 60:
        score += 15
        factors.append(f'trend={trend.get("direction")}')

    # S/R testing
    if sr_testing.get('testing') and sr_testing.get('type') == 'support':
        score += 15
        factors.append('at_support')

    # Clustering boost
    if clustering.get('bullish_clusters', 0) >= 3 or clustering.get('bearish_clusters', 0) >= 3:
        score += 15
        factors.append('strong_clustering')

    # Count full-weight confirming analyses per direction
    bullish_conf = 0
    bearish_conf = 0
    if wyckoff.get('phase') in ('accumulation', 'markup'):
        bullish_conf += 1
    elif wyckoff.get('phase') in ('distribution', 'markdown'):
        bearish_conf += 1
    if ewave.get('direction') == 'up' and ewave.get('wave') in [1, 2, 3]:
        bullish_conf += 1
    elif ewave.get('direction') == 'down' and ewave.get('wave') in [1, 2, 3]:
        bearish_conf += 1
    if trend.get('direction') == 'BULL':
        bullish_conf += 1
    elif trend.get('direction') == 'BEAR':
        bearish_conf += 1

    # Require 2+ confirming analyses for non-NEUTRAL setups
    MIN_CONFIRMATIONS = 2
    max_conf = max(bullish_conf, bearish_conf)
    if max_conf < MIN_CONFIRMATIONS:
        score *= 0.5  # penalize weak single-indicator setups
        factors.append(f'weak_confirmations({bullish_conf}B/{bearish_conf}R)')

    # Recency multiplier
    score = score * (0.7 + 0.3 * recency)

    # Determine setup type
    if clustering.get('bullish_clusters', 0) > clustering.get('bearish_clusters', 0):
        setup_type = 'LONG'
    elif clustering.get('bearish_clusters', 0) > clustering.get('bullish_clusters', 0):
        setup_type = 'SHORT'
    else:
        setup_type = 'NEUTRAL'

    # Force NEUTRAL if insufficient confirmations
    if max_conf < MIN_CONFIRMATIONS and setup_type != 'NEUTRAL':
        setup_type = 'NEUTRAL'
        factors.append('forced_neutral_insufficient_confirmations')

    return {
        'score': min(100, score),
        'setup_type': setup_type,
        'confidence': min(100, score * 0.8),
        'details': ', '.join(factors) if factors else 'no setup'
    }


def detect_setup(candles_5m: List[Dict], candles_1h: List[Dict],
                 candles_4h: List[Dict]) -> Dict:
    """Full setup detection — combines all analysis into actionable intelligence.

    Returns: {setup_score, setup_type, forming_patterns, clustering, recency, details}
    """
    # Run all detection
    wyckoff_forming = detect_wyckoff_forming(candles_1h if candles_1h else candles_5m)
    ewave_forming = detect_ewave_forming(candles_4h)
    sr_levels = compute_sr_levels(candles_1h if candles_1h else candles_5m)
    sr_testing = detect_sr_testing(candles_5m, sr_levels)
    trend = compute_trend_quality(candles_5m, candles_1h)
    recency = compute_recency_weight(candles_5m)

    # Get existing analysis if available
    wyckoff = detect_wyckoff_phase(candles_1h if candles_1h else candles_5m)
    ewave = detect_ewave_count(candles_4h, candles_1h)

    # Compute clustering
    clustering = compute_clustering_score(wyckoff, ewave, trend, sr_testing)

    # Compute setup strength
    setup = compute_setup_strength(wyckoff, ewave, trend, sr_testing, clustering, recency)

    return {
        'setup_score': setup['score'],
        'setup_type': setup['setup_type'],
        'setup_details': setup['details'],
        'wyckoff_forming': wyckoff_forming,
        'ewave_forming': ewave_forming,
        'sr_testing': sr_testing,
        'clustering': clustering,
        'recency': recency,
    }
