#!/usr/bin/env python3
"""
pattern_recognition.py — Shared pattern detection for signal quality filtering.

Detects high-probability reversal setups like the AXS 2026-08-05 trade:
  1. Extended move before bounce (mean reversion opportunity)
  2. Capitulation candle (long wick at support)
  3. Higher low formation (bullish divergence)
  4. Sharp reversal candle (strong momentum shift)

Usage from other signals:
    from pattern_recognition import detect_reversal_quality
    quality = detect_reversal_quality(candles)
    if quality['score'] >= 3:  # 3+ signals = high quality
        # Fire signal
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))


def detect_extended_move(candles, min_pct=0.3, min_bars=18):
    """Detect if price has moved significantly before the current candle.
    
    Returns dict with:
      - moved: bool (True if extended move detected)
      - direction: 'DOWN' or 'UP' (direction of the move)
      - pct: float (percentage move)
      - bars: int (number of bars in the move)
    """
    if len(candles) < min_bars + 1:
        return {'moved': False, 'direction': None, 'pct': 0, 'bars': 0}

    # Look back from current candle
    recent_high = max(c['high'] for c in candles[-min_bars-1:])
    recent_low = min(c['low'] for c in candles[-min_bars-1:])
    current = candles[-1]['close']
    start_price = candles[-min_bars-1]['close']

    # Check for extended DOWN move (buying opportunity)
    if start_price > 0:
        down_pct = (start_price - current) / start_price * 100
        if down_pct >= min_pct:
            return {
                'moved': True,
                'direction': 'DOWN',
                'pct': round(down_pct, 3),
                'bars': min_bars,
            }

    # Check for extended UP move (shorting opportunity)
    if start_price > 0:
        up_pct = (current - start_price) / start_price * 100
        if up_pct >= min_pct:
            return {
                'moved': True,
                'direction': 'UP',
                'pct': round(up_pct, 3),
                'bars': min_bars,
            }

    return {'moved': False, 'direction': None, 'pct': 0, 'bars': 0}


def detect_capitulation(candles, lookback=5):
    """Detect capitulation candle (long wick at support/resistance).
    
    A capitulation candle has:
      - A wick that is 2x+ the body size, OR
      - A doji (near-zero body) at the extreme of a move
      - Occurs after an extended move
      - Price closes near the open (indecision at extreme)
    
    Returns dict with:
      - capitulation: bool
      - type: 'bottom' or 'top' (where the wick is)
      - wick_ratio: float (wick size / body size)
    """
    if len(candles) < lookback + 1:
        return {'capitulation': False, 'type': None, 'wick_ratio': 0}

    # Check the last `lookback` candles for any capitulation pattern
    for i in range(max(0, len(candles) - lookback), len(candles)):
        candle = candles[i]
        body = abs(candle['close'] - candle['open'])
        full_range = candle['high'] - candle['low']

        if full_range == 0:
            continue

        # Doji detection: body < 10% of range = indecision at extreme
        if body < full_range * 0.1:
            recent_lows = [c['low'] for c in candles[max(0, i-10):i+1]]
            recent_highs = [c['high'] for c in candles[max(0, i-10):i+1]]
            if candle['low'] <= min(recent_lows) * 1.001:
                return {'capitulation': True, 'type': 'bottom', 'wick_ratio': round(full_range / max(body, 0.0001), 2)}
            if candle['high'] >= max(recent_highs) * 0.999:
                return {'capitulation': True, 'type': 'top', 'wick_ratio': round(full_range / max(body, 0.0001), 2)}

        if body == 0:
            body = 0.0001  # avoid division by zero

        # Bottom wick (bullish capitulation)
        bottom_wick = min(candle['open'], candle['close']) - candle['low']
        top_wick = candle['high'] - max(candle['open'], candle['close'])

        if bottom_wick > body * 2 and bottom_wick > top_wick:
            return {
                'capitulation': True,
                'type': 'bottom',
                'wick_ratio': round(bottom_wick / body, 2),
            }

        # Top wick (bearish capitulation)
        if top_wick > body * 2 and top_wick > bottom_wick:
            return {
                'capitulation': True,
                'type': 'top',
                'wick_ratio': round(top_wick / body, 2),
            }

    return {'capitulation': False, 'type': None, 'wick_ratio': 0}


def detect_higher_low(candles, lookback=18):
    """Detect higher low formation (bullish divergence after downtrend).
    
    Looks for:
      - Recent low is higher than previous low
      - Both lows occur within the lookback window
      - Price is bouncing from the second low
    
    Returns dict with:
      - higher_low: bool
      - prev_low: float
      - current_low: float
      - bounce_pct: float (% from low to current price)
    """
    if len(candles) < lookback + 1:
        return {'higher_low': False, 'prev_low': 0, 'current_low': 0, 'bounce_pct': 0}

    # Find the two most recent significant lows
    lows = [(i, c['low']) for i, c in enumerate(candles[-lookback-1:])]
    if len(lows) < 2:
        return {'higher_low': False, 'prev_low': 0, 'current_low': 0, 'bounce_pct': 0}

    # Find the lowest point in first half and second half
    mid = len(lows) // 2
    first_half = lows[:mid]
    second_half = lows[mid:]

    if not first_half or not second_half:
        return {'higher_low': False, 'prev_low': 0, 'current_low': 0, 'bounce_pct': 0}

    prev_low = min(c[1] for c in first_half)
    current_low = min(c[1] for c in second_half)
    current_price = candles[-1]['close']

    if prev_low > 0 and current_low > prev_low:
        bounce_pct = (current_price - current_low) / current_low * 100
        return {
            'higher_low': True,
            'prev_low': round(prev_low, 6),
            'current_low': round(current_low, 6),
            'bounce_pct': round(bounce_pct, 3),
        }

    return {'higher_low': False, 'prev_low': 0, 'current_low': 0, 'bounce_pct': 0}


def detect_sharp_reversal(candles, min_pct=0.15):
    """Detect sharp reversal candle (strong momentum shift).
    
    A sharp reversal has:
      - A large body (>min_pct) in one direction
      - Closes near the high/low (little wick on the reversal side)
      - Follows a move in the opposite direction
    
    Returns dict with:
      - reversal: bool
      - direction: 'LONG' or 'SHORT'
      - strength: float (% move in the reversal candle)
      - follow_through: bool (next candle confirms)
    """
    if len(candles) < 3:
        return {'reversal': False, 'direction': None, 'strength': 0, 'follow_through': False}

    current = candles[-1]
    prev = candles[-2]
    body = current['close'] - current['open']

    if current['open'] == 0:
        return {'reversal': False, 'direction': None, 'strength': 0, 'follow_through': False}

    strength_pct = abs(body) / current['open'] * 100

    if strength_pct < min_pct:
        return {'reversal': False, 'direction': None, 'strength': 0, 'follow_through': False}

    # Determine direction
    if body > 0:  # Green candle (bullish reversal)
        direction = 'LONG'
        # Strong close: close > 70% of range (closed near high)
        candle_range = current['high'] - current['low']
        if candle_range > 0:
            close_position = (current['close'] - current['low']) / candle_range
            follow_through = close_position > 0.7
        else:
            follow_through = True
    else:  # Red candle (bearish reversal)
        direction = 'SHORT'
        # Strong close: close < 30% of range (closed near low)
        candle_range = current['high'] - current['low']
        if candle_range > 0:
            close_position = (current['close'] - current['low']) / candle_range
            follow_through = close_position < 0.3
        else:
            follow_through = True

    return {
        'reversal': True,
        'direction': direction,
        'strength': round(strength_pct, 3),
        'follow_through': follow_through,
    }


def detect_reversal_quality(candles, extended_min_pct=0.3, reversal_min_pct=0.15):
    """Master function: detect high-probability reversal setups.
    
    Combines all pattern detectors into a quality score.
    Score 0-5: 0=low quality, 5=perfect setup.
    
    The AXS trade scored:
      - extended_move: +1 (DOWN 0.89%)
      - capitulation: +1 (bottom wick at 01:30)
      - higher_low: +1 (01:30 low > 01:15 low)
      - sharp_reversal: +1 (+0.42% green candle)
      - follow_through: +1 (next candle confirmed)
      = TOTAL: 5/5
    
    Returns dict with:
      - score: int (0-5)
      - direction: 'LONG' or 'SHORT' or None
      - signals: list of detected patterns
      - extended_move: dict
      - capitulation: dict
      - higher_low: dict
      - sharp_reversal: dict
    """
    if len(candles) < 20:
        return {
            'score': 0, 'direction': None, 'signals': [],
            'extended_move': {}, 'capitulation': {},
            'higher_low': {}, 'sharp_reversal': {},
        }

    signals = []
    score = 0
    direction = None

    # 1. Extended move
    ext = detect_extended_move(candles, min_pct=extended_min_pct)
    if ext['moved']:
        score += 1
        signals.append(f"extended_{ext['direction'].lower()}_{ext['pct']:.1f}%")
        direction = 'LONG' if ext['direction'] == 'DOWN' else 'SHORT'

    # 2. Capitulation candle
    cap = detect_capitulation(candles)
    if cap['capitulation']:
        score += 1
        signals.append(f"capitulation_{cap['type']}")

    # 3. Higher low / lower high
    hl = detect_higher_low(candles)
    if hl['higher_low']:
        score += 1
        signals.append(f"higher_low_{hl['bounce_pct']:.1f}%")

    # 4. Sharp reversal
    rev = detect_sharp_reversal(candles, min_pct=reversal_min_pct)
    if rev['reversal']:
        score += 1
        signals.append(f"reversal_{rev['direction']}_{rev['strength']:.1f}%")
        if direction is None:
            direction = rev['direction']

    # 5. Follow-through (next candle confirms)
    if rev.get('follow_through') and direction:
        score += 1
        signals.append("follow_through")

    return {
        'score': score,
        'direction': direction,
        'signals': signals,
        'extended_move': ext,
        'capitulation': cap,
        'higher_low': hl,
        'sharp_reversal': rev,
    }


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sqlite3

    # Load AXS candles around the signal time
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'candles.db')
    conn = sqlite3.connect(db_path)
    rows = conn.execute("""
        SELECT ts, open, high, low, close, volume
        FROM candles_5m WHERE token = 'AXS'
        ORDER BY ts ASC
    """).fetchall()
    conn.close()

    candles = [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3],
                'close': r[4], 'volume': r[5]} for r in rows]

    # Find the signal candle (around 01:40 UTC on Aug 5)
    # Signal was at entry price 0.8219
    for i, c in enumerate(candles):
        if abs(c['close'] - 0.8219) < 0.005:
            # Check quality around this candle
            window = candles[max(0, i-20):i+1]
            quality = detect_reversal_quality(window)
            print(f"Candle {i} (ts={c['ts']}): score={quality['score']}/5")
            print(f"  Signals: {quality['signals']}")
            print(f"  Direction: {quality['direction']}")
            print(f"  Extended: {quality['extended_move']}")
            print(f"  Capitulation: {quality['capitulation']}")
            print(f"  Higher low: {quality['higher_low']}")
            print(f"  Reversal: {quality['sharp_reversal']}")
            print()
