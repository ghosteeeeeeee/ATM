#!/usr/bin/env python3
"""
continuum_engine.py — BTC Continuum State Engine

Tracks BTC as a living state machine. Instead of event-based signals,
we watch states evolve in real-time. When enough states align, we enter.
When states degrade, we exit.

Data sources:
  - hl_cache.json (allMids) — live price every 30s
  - candles.db (1m, 5m, 15m, 1h) — historical candles
  - continuum.db — persistent state table

Run: python3 continuum_engine.py
"""

import sys
import os
import time
import json
import math
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

sys.path.insert(0, os.path.dirname(__file__))
from paths import HERMES_DATA, WWW_DATA
from continuum_constants import (
    HYSTERESIS, EMA300_PERIOD, EMA300_ABOVE_BUFFER, EMA300_BELOW_BUFFER,
    ZSCORE_LOOKBACK, ZSCORE_STRONG_NEG, ZSCORE_NEG, ZSCORE_POS, ZSCORE_STRONG_POS,
    VOLUME_AVG_PERIOD, VOLUME_LOW_THRESHOLD, VOLUME_HIGH_THRESHOLD, VOLUME_PARABOLIC_THRESHOLD,
    VELOCITY_FALLING, VELOCITY_SLOW_LOW, VELOCITY_SLOW_HIGH, VELOCITY_RISING, VELOCITY_FAST,
    ACCEL_NEGATIVE, ACCEL_POSITIVE,
    LINREG_1M_PERIOD, LINREG_5M_PERIOD, LINREG_15M_PERIOD, LINREG_1H_PERIOD,
    LINREG_STEEP_UP, LINREG_UP, LINREG_FLAT_LOW, LINREG_FLAT_HIGH,
    LINREG_DOWN, LINREG_STEEP_DOWN,
    ENTRY_CROSS_MIN_DURATION, ENTRY_CONFIRM_MIN_DURATION,
    SCORE_WEIGHTS, SCORE_EXIT_THRESHOLD,
    EXIT_TIER3_EMA_BREAK,
    POSITION_TAG, POSITION_FILE,
    TICK_INTERVAL, SCORE_SMOOTHING,
)

# ── Derived paths ──────────────────────────────────────────────────────────────
CONTINUUM_DB = os.path.join(HERMES_DATA, 'continuum.db')
HL_CACHE_FILE = os.path.join(WWW_DATA, 'hl_cache.json')
CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')

# ── Enums ──────────────────────────────────────────────────────────────────────

class EMA300Position(Enum):
    ABOVE = 'ABOVE'
    BELOW = 'BELOW'
    AT = 'AT'

class ZScoreTier(Enum):
    STRONG_NEG = 'STRONG_NEG'   # z < -1.5
    NEG = 'NEG'                 # -1.5 < z < -0.5
    NEUTRAL = 'NEUTRAL'         # -0.5 < z < 0.5
    POS = 'POS'                 # 0.5 < z < 1.5
    STRONG_POS = 'STRONG_POS'  # z > 1.5

class VolumeRegime(Enum):
    LOW = 'LOW'                 # < 0.5x avg
    NORMAL = 'NORMAL'           # 0.5x - 1.5x avg
    HIGH = 'HIGH'               # 1.5x - 3x avg
    PARABOLIC = 'PARABOLIC'    # > 3x avg

class Velocity(Enum):
    FALLING = 'FALLING'         # < -0.3%
    SLOW = 'SLOW'               # -0.3% to +0.3%
    RISING = 'RISING'           # +0.3% to +1.0%
    FAST = 'FAST'               # > +1.0%

class Acceleration(Enum):
    NEGATIVE = 'NEGATIVE'
    FLAT = 'FLAT'
    POSITIVE = 'POSITIVE'

class WyckoffPhase(Enum):
    ACCUMULATION = 'ACCUMULATION'
    MARKUP = 'MARKUP'
    DISTRIBUTION = 'DISTRIBUTION'
    MARKDOWN = 'MARKDOWN'
    UNKNOWN = 'UNKNOWN'

class EWaveCount(Enum):
    W1 = 'W1'
    W2 = 'W2'
    W3 = 'W3'
    W4 = 'W4'
    W5 = 'W5'
    CA = 'CA'
    CB = 'CB'
    CC = 'CC'
    UNKNOWN = 'UNKNOWN'

class TrendQuality(Enum):
    STRONG_UP = 'STRONG_UP'
    UP = 'UP'
    WEAK = 'WEAK'
    DOWN = 'DOWN'
    STRONG_DOWN = 'STRONG_DOWN'

class MarketPhase(Enum):
    CALM = 'CALM'
    STORMY = 'STORMY'
    RECOVERY = 'RECOVERY'
    DECLINING = 'DECLINING'

class LinregSlope(Enum):
    STEEP_UP = 'STEEP_UP'       # > 0.10% per candle
    UP = 'UP'                   # 0.02% - 0.10%
    FLAT = 'FLAT'               # -0.02% to 0.02%
    DOWN = 'DOWN'               # -0.10% to -0.02%
    STEEP_DOWN = 'STEEP_DOWN'   # < -0.10%

# ── Indicator Functions ────────────────────────────────────────────────────────

def ema(values: List[float], period: int) -> float:
    """Exponential moving average."""
    if not values or len(values) < period:
        return None
    k = 2 / (period + 1)
    e = sum(values[:period]) / period
    for v in values[period:]:
        e = v * k + e * (1 - k)
    return e

def zscore(values: List[float], lookback: int = 120) -> Optional[float]:
    """Z-score of current price vs rolling window."""
    if len(values) < lookback:
        return None
    window = values[-lookback:]
    mean = sum(window) / len(window)
    variance = sum((x - mean) ** 2 for x in window) / len(window)
    std = math.sqrt(variance) if variance > 0 else 1e-10
    return (values[-1] - mean) / std

def velocity_5m(closes: List[float]) -> Optional[float]:
    """Price velocity over 5 minutes (% change)."""
    if len(closes) < 6:
        return None
    return (closes[-1] - closes[-6]) / closes[-6] * 100

def acceleration(closes: List[float]) -> Optional[float]:
    """Rate of change of velocity. Positive = velocity increasing."""
    if len(closes) < 12:
        return None
    vel_now = (closes[-1] - closes[-6]) / closes[-6] * 100
    vel_prev = (closes[-6] - closes[-12]) / closes[-12] * 100
    return vel_now - vel_prev

def volume_ratio(volumes: List[float], avg_period: int = 60) -> Optional[float]:
    """Current volume vs rolling average."""
    if len(volumes) < avg_period:
        return None
    avg = sum(volumes[-avg_period:]) / avg_period
    if avg == 0:
        return None
    return volumes[-1] / avg

def rsi(closes: List[float], period: int = 14) -> Optional[float]:
    """Relative Strength Index."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i - 1] - closes[i]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def linreg_slope(values: List[float], period: int) -> Optional[float]:
    """
    Linear regression slope (% per candle).
    Returns slope as percentage change per candle.
    Positive = uptrend, Negative = downtrend.
    """
    if len(values) < period:
        return None
    
    window = values[-period:]
    n = len(window)
    
    # Simple linear regression: y = mx + b
    # m = (n*sum(xy) - sum(x)*sum(y)) / (n*sum(x²) - (sum(x))²)
    sum_x = sum(range(n))
    sum_y = sum(window)
    sum_xy = sum(i * window[i] for i in range(n))
    sum_x2 = sum(i * i for i in range(n))
    
    denominator = n * sum_x2 - sum_x * sum_x
    if denominator == 0:
        return 0.0
    
    slope = (n * sum_xy - sum_x * sum_y) / denominator
    
    # Normalize to % per candle relative to mean price
    mean_price = sum_y / n
    if mean_price == 0:
        return 0.0
    
    return (slope / mean_price) * 100

def linreg_slope_multi_tf(closes_1m: List[float], closes_5m: List[float] = None,
                          closes_15m: List[float] = None, closes_1h: List[float] = None) -> dict:
    """
    Compute linear regression slope across multiple timeframes.
    Returns dict with slope values and alignment score.
    """
    slopes = {}
    
    # 1m slope (1-hour lookback)
    s1m = linreg_slope(closes_1m, LINREG_1M_PERIOD)
    if s1m is not None:
        slopes['1m'] = s1m
    
    # 5m slope (1-hour lookback = 12 candles)
    if closes_5m and len(closes_5m) >= LINREG_5M_PERIOD:
        s5m = linreg_slope(closes_5m, LINREG_5M_PERIOD)
        if s5m is not None:
            slopes['5m'] = s5m
    
    # 15m slope (2-hour lookback = 8 candles)
    if closes_15m and len(closes_15m) >= LINREG_15M_PERIOD:
        s15m = linreg_slope(closes_15m, LINREG_15M_PERIOD)
        if s15m is not None:
            slopes['15m'] = s15m
    
    # 1h slope (6-hour lookback = 6 candles)
    if closes_1h and len(closes_1h) >= LINREG_1H_PERIOD:
        s1h = linreg_slope(closes_1h, LINREG_1H_PERIOD)
        if s1h is not None:
            slopes['1h'] = s1h
    
    # Compute alignment: how many timeframes agree on direction?
    if not slopes:
        return {'slopes': {}, 'alignment': 0, 'direction': 'NEUTRAL'}
    
    positive = sum(1 for s in slopes.values() if s > 0.01)
    negative = sum(1 for s in slopes.values() if s < -0.01)
    total = len(slopes)
    
    if positive == total:
        alignment = 1.0  # All timeframes bullish
        direction = 'BULL'
    elif negative == total:
        alignment = 1.0  # All timeframes bearish
        direction = 'BEAR'
    elif positive > negative:
        alignment = positive / total
        direction = 'LEAN_BULL'
    elif negative > positive:
        alignment = negative / total
        direction = 'LEAN_BEAR'
    else:
        alignment = 0.0
        direction = 'NEUTRAL'
    
    return {
        'slopes': slopes,
        'alignment': alignment,
        'direction': direction,
    }


# ── State Classification Functions ─────────────────────────────────────────────

def classify_ema300_position(price: float, ema300: float) -> EMA300Position:
    """Classify price relative to EMA300."""
    if price > ema300 * (1 + EMA300_ABOVE_BUFFER):  # buffer to avoid noise
        return EMA300Position.ABOVE
    elif price < ema300 * (1 - EMA300_BELOW_BUFFER):
        return EMA300Position.BELOW
    else:
        return EMA300Position.AT

def classify_zscore(z: float) -> ZScoreTier:
    """Classify z-score into tiers."""
    if z < ZSCORE_STRONG_NEG:
        return ZScoreTier.STRONG_NEG
    elif z < ZSCORE_NEG:
        return ZScoreTier.NEG
    elif z < ZSCORE_POS:
        return ZScoreTier.NEUTRAL
    elif z < ZSCORE_STRONG_POS:
        return ZScoreTier.POS
    else:
        return ZScoreTier.STRONG_POS

def classify_volume(ratio: float) -> VolumeRegime:
    """Classify volume ratio into regimes."""
    if ratio < VOLUME_LOW_THRESHOLD:
        return VolumeRegime.LOW
    elif ratio < VOLUME_HIGH_THRESHOLD:
        return VolumeRegime.NORMAL
    elif ratio < VOLUME_PARABOLIC_THRESHOLD:
        return VolumeRegime.HIGH
    else:
        return VolumeRegime.PARABOLIC

def classify_velocity(vel: float) -> Velocity:
    """Classify price velocity."""
    if vel < -0.3:
        return Velocity.FALLING
    elif vel < 0.3:
        return Velocity.SLOW
    elif vel < 1.0:
        return Velocity.RISING
    else:
        return Velocity.FAST

def classify_acceleration(acc: float) -> Acceleration:
    """Classify acceleration."""
    if acc < -0.05:
        return Acceleration.NEGATIVE
    elif acc > 0.05:
        return Acceleration.POSITIVE
    else:
        return Acceleration.FLAT


# ── State with Hysteresis ──────────────────────────────────────────────────────

class HysteresisState:
    """
    A state value with hysteresis (asymmetric ON/OFF thresholds).
    
    ON requires `on_threshold` consecutive matching values.
    OFF requires `off_threshold` consecutive non-matching values.
    """
    
    def __init__(self, name: str, on_threshold: int = 3, off_threshold: int = 3):
        self.name = name
        self.on_threshold = on_threshold
        self.off_threshold = off_threshold
        self.current_value = None
        self.confirmed_value = None
        self.consecutive_match = 0
        self.consecutive_mismatch = 0
    
    def update(self, raw_value) -> Tuple[bool, bool]:
        """
        Update with new raw value.
        Returns (changed, is_confirmed).
        changed = True if confirmed_value changed
        is_confirmed = current confirmed state
        """
        changed = False
        
        if raw_value == self.current_value:
            # Same direction — count up
            self.consecutive_match += 1
            self.consecutive_mismatch = 0
            
            # Check if we should confirm (turn ON)
            if self.confirmed_value != self.current_value:
                if self.consecutive_match >= self.on_threshold:
                    self.confirmed_value = self.current_value
                    changed = True
        else:
            # Different direction — count mismatch
            self.current_value = raw_value
            self.consecutive_match = 0
            self.consecutive_mismatch += 1
            
            # Check if we should deconfirm (turn OFF)
            if self.consecutive_mismatch >= self.off_threshold:
                if self.confirmed_value is not None:
                    self.confirmed_value = None
                    changed = True
        
        return changed, self.confirmed_value is not None
    
    def get_confirmed(self):
        """Get the confirmed state value."""
        return self.confirmed_value
    
    def get_raw(self):
        """Get the raw (unconfirmed) current value."""
        return self.current_value


# ── Core State Tracker ─────────────────────────────────────────────────────────

@dataclass
class ContinuumState:
    """Complete state snapshot for one timeframe."""
    token: str
    timeframe: str
    ts: int
    
    # Raw indicators
    price: float = 0.0
    ema300: float = 0.0
    zscore_val: float = 0.0
    velocity_val: float = 0.0
    acceleration_val: float = 0.0
    volume_ratio_val: float = 0.0
    linreg_1m_slope: float = 0.0
    linreg_5m_slope: float = 0.0
    linreg_15m_slope: float = 0.0
    linreg_1h_slope: float = 0.0
    linreg_alignment: float = 0.0
    
    # Classified states
    ema300_position: str = 'AT'
    ema300_duration: int = 0  # minutes above/below
    zscore_tier: str = 'NEUTRAL'
    volume_regime: str = 'NORMAL'
    velocity_state: str = 'SLOW'
    acceleration_state: str = 'FLAT'
    linreg_slope_state: str = 'FLAT'
    linreg_direction: str = 'NEUTRAL'
    
    # Extended states
    wyckoff_phase: str = 'UNKNOWN'
    ewave_count: str = 'UNKNOWN'
    trend_quality: str = 'WEAK'
    market_phase: str = 'NEUTRAL'
    
    # Compound score
    state_score: float = 50.0
    
    # Entry state machine
    entry_phase: int = 0  # 0-4
    position_side: str = 'NONE'
    position_size_pct: float = 0.0
    
    # Tracking
    consecutive_above: int = 0
    consecutive_below: int = 0
    last_cross_ts: int = 0


class ContinuumEngine:
    """
    Core continuum engine — tracks BTC state across multiple timeframes.
    """
    
    def __init__(self, token: str = 'BTC'):
        self.token = token
        self.db = None
        self._init_db()
        
        # Hysteresis states for 1m
        self.hysteresis = {
            'ema300_position': HysteresisState('ema300_position', 5, 3),
            'zscore_tier': HysteresisState('zscore_tier', 3, 5),
            'volume_regime': HysteresisState('volume_regime', 3, 5),
            'velocity': HysteresisState('velocity', 3, 3),
            'acceleration': HysteresisState('acceleration', 3, 3),
            'linreg_slope': HysteresisState('linreg_slope', 5, 5),
        }
        
        # Duration tracking
        self.ema300_direction = None  # 'ABOVE' or 'BELOW'
        self.ema300_duration = 0
        self.last_ema300_price = None
        self.last_cross_ts = 0
        
        # Entry state machine
        self.entry_phase = 0
        self.position_side = 'NONE'
        self.position_size_pct = 0.0
        self.entry_ts = 0
        
        # Score smoothing
        self.smoothed_score = 50.0  # Start neutral
        
        # Phase reset tracking
        self._below_count = 0  # Consecutive candles below EMA300
        
        # History for multi-TF
        self.state_history: List[ContinuumState] = []
    
    def _init_db(self):
        """Initialize SQLite state table."""
        os.makedirs(os.path.dirname(CONTINUUM_DB), exist_ok=True)
        self.db = sqlite3.connect(CONTINUUM_DB)
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS continuum_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                ts INTEGER NOT NULL,
                price REAL,
                ema300 REAL,
                zscore_val REAL,
                velocity_val REAL,
                acceleration_val REAL,
                volume_ratio_val REAL,
                linreg_1m_slope REAL,
                linreg_5m_slope REAL,
                linreg_15m_slope REAL,
                linreg_1h_slope REAL,
                linreg_alignment REAL,
                ema300_position TEXT,
                ema300_duration INTEGER,
                zscore_tier TEXT,
                volume_regime TEXT,
                velocity_state TEXT,
                acceleration_state TEXT,
                linreg_slope_state TEXT,
                linreg_direction TEXT,
                wyckoff_phase TEXT,
                ewave_count TEXT,
                trend_quality TEXT,
                market_phase TEXT,
                state_score REAL,
                entry_phase INTEGER,
                position_side TEXT,
                position_size_pct REAL,
                consecutive_above INTEGER,
                consecutive_below INTEGER,
                last_cross_ts INTEGER,
                updated_at INTEGER DEFAULT (strftime('%s','now')),
                UNIQUE(token, timeframe, ts)
            )
        ''')
        self.db.execute('CREATE INDEX IF NOT EXISTS idx_ctoken_ts ON continuum_states(token, ts)')
        self.db.execute('CREATE INDEX IF NOT EXISTS idx_ctf_ts ON continuum_states(timeframe, ts)')
        self.db.commit()
    
    def _read_candles(self, timeframe: str, limit: int = 400) -> List[dict]:
        """Read recent candles from DB."""
        # Validate timeframe to prevent SQL injection
        assert timeframe in ('1m', '5m', '15m', '1h', '4h'), f"Invalid timeframe: {timeframe}"
        table = f'candles_{timeframe}'
        conn = None
        try:
            conn = sqlite3.connect(CANDLES_DB)
            cur = conn.execute(
                f"SELECT ts, open, high, low, close, volume FROM {table} "
                f"WHERE token=? ORDER BY ts DESC LIMIT ?",
                (self.token, limit)
            )
            rows = cur.fetchall()
            cur.close()
            # Return oldest-first, ensure numeric types
            return [{'ts': int(r[0]), 'open': float(r[1]), 'high': float(r[2]), 
                     'low': float(r[3]), 'close': float(r[4]), 
                     'volume': float(r[5])} for r in reversed(rows)]
        except Exception as e:
            print(f"Error reading candles: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def _read_live_price(self) -> Optional[float]:
        """Read live price from hl_cache.json."""
        try:
            with open(HL_CACHE_FILE) as f:
                cache = json.load(f)
            price = cache.get('allMids', {}).get(self.token)
            return float(price) if price is not None else None
        except Exception:
            return None
    
    def compute_states(self, timeframe: str = '1m') -> ContinuumState:
        """
        Compute all states for a given timeframe.
        Returns a ContinuumState with all dimensions classified.
        """
        # Read candles
        candles = self._read_candles(timeframe, limit=400)
        if len(candles) < 300:
            print(f"Not enough candles for {timeframe}: {len(candles)}")
            return None
        
        closes = [c['close'] for c in candles]
        volumes = [c['volume'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        
        # Use live price if available, otherwise last candle close
        live_price = self._read_live_price()
        if live_price:
            price = live_price
        else:
            price = closes[-1]
        
        # Compute indicators
        ema300_val = ema(closes, 300)
        if ema300_val is None:
            print("Not enough data for EMA300")
            return None
        
        z = zscore(closes, lookback=ZSCORE_LOOKBACK)
        vel = velocity_5m(closes)
        acc = acceleration(closes)
        vol_ratio = volume_ratio(volumes, avg_period=60)
        
        # Classify raw states
        raw_ema300 = classify_ema300_position(price, ema300_val)
        raw_zscore = classify_zscore(z) if z is not None else ZScoreTier.NEUTRAL
        raw_volume = classify_volume(vol_ratio) if vol_ratio is not None else VolumeRegime.NORMAL
        raw_velocity = classify_velocity(vel) if vel is not None else Velocity.SLOW
        raw_accel = classify_acceleration(acc) if acc is not None else Acceleration.FLAT
        
        # Apply hysteresis
        _, ema_confirmed = self.hysteresis['ema300_position'].update(raw_ema300)
        _, zscore_confirmed = self.hysteresis['zscore_tier'].update(raw_zscore)
        _, volume_confirmed = self.hysteresis['volume_regime'].update(raw_volume)
        _, velocity_confirmed = self.hysteresis['velocity'].update(raw_velocity)
        _, accel_confirmed = self.hysteresis['acceleration'].update(raw_accel)
        
        # Get confirmed values (or raw if not confirmed yet)
        ema300_pos = self.hysteresis['ema300_position'].get_confirmed() or raw_ema300
        zscore_tier = self.hysteresis['zscore_tier'].get_confirmed() or raw_zscore
        volume_reg = self.hysteresis['volume_regime'].get_confirmed() or raw_volume
        vel_state = self.hysteresis['velocity'].get_confirmed() or raw_velocity
        accel_state = self.hysteresis['acceleration'].get_confirmed() or raw_accel
        
        # Track EMA300 duration
        current_ema_direction = 'ABOVE' if price > ema300_val else 'BELOW'
        if current_ema_direction == self.ema300_direction:
            self.ema300_duration += 1  # +1 candle
        else:
            # Direction changed
            if self.ema300_direction is not None:
                self.last_cross_ts = candles[-1]['ts']
            self.ema300_direction = current_ema_direction
            self.ema300_duration = 1
        
        # Compute trend quality (multi-EMA alignment)
        ema_9 = ema(closes, 9) if len(closes) >= 9 else None
        ema_20 = ema(closes, 20) if len(closes) >= 20 else None
        ema_50 = ema(closes, 50) if len(closes) >= 50 else None
        
        trend_score = 0
        if ema_9 and ema_20 and ema_50:
            if ema_9 > ema_20 > ema_50:
                trend_score = 2  # STRONG_UP
            elif ema_9 > ema_20 or ema_20 > ema_50:
                trend_score = 1  # UP
            elif ema_9 < ema_20 < ema_50:
                trend_score = -2  # STRONG_DOWN
            elif ema_9 < ema_20 or ema_20 < ema_50:
                trend_score = -1  # DOWN
        
        trend_map = {-2: 'STRONG_DOWN', -1: 'DOWN', 0: 'WEAK', 1: 'UP', 2: 'STRONG_UP'}
        trend = trend_map.get(trend_score, 'WEAK')
        
        # Simple Wyckoff detection (price action based)
        wyckoff = self._detect_wyckoff(closes, volumes)
        
        # Simple Elliott wave count
        ewave = self._detect_ewave(closes)
        
        # Market phase from RSI and volatility
        rsi_val = rsi(closes)
        atr_val = self._atr_pct(highs, lows, closes)
        market = self._detect_market_phase(rsi_val, atr_val, vol_ratio)
        
        # Linear regression slope (multi-timeframe)
        closes_1m = closes
        closes_5m = None
        closes_15m = None
        closes_1h = None
        
        # Read higher timeframe candles for linreg
        try:
            candles_5m = self._read_candles('5m', limit=50)
            if candles_5m:
                closes_5m = [c['close'] for c in candles_5m]
        except:
            pass
        try:
            candles_15m = self._read_candles('15m', limit=50)
            if candles_15m:
                closes_15m = [c['close'] for c in candles_15m]
        except:
            pass
        try:
            candles_1h = self._read_candles('1h', limit=50)
            if candles_1h:
                closes_1h = [c['close'] for c in candles_1h]
        except:
            pass
        
        linreg_result = linreg_slope_multi_tf(closes_1m, closes_5m, closes_15m, closes_1h)
        linreg_slopes = linreg_result['slopes']
        linreg_alignment = linreg_result['alignment']
        linreg_direction = linreg_result['direction']
        
        # Classify 1m linreg slope
        slope_1m = linreg_slopes.get('1m', 0)
        if slope_1m > LINREG_STEEP_UP:
            raw_linreg = LinregSlope.STEEP_UP
        elif slope_1m > LINREG_UP:
            raw_linreg = LinregSlope.UP
        elif slope_1m < LINREG_STEEP_DOWN:
            raw_linreg = LinregSlope.STEEP_DOWN
        elif slope_1m < LINREG_DOWN:
            raw_linreg = LinregSlope.DOWN
        else:
            raw_linreg = LinregSlope.FLAT
        
        # Apply hysteresis to linreg
        _, linreg_confirmed = self.hysteresis['linreg_slope'].update(raw_linreg)
        linreg_state = self.hysteresis['linreg_slope'].get_confirmed() or raw_linreg
        
        # Build state
        state = ContinuumState(
            token=self.token,
            timeframe=timeframe,
            ts=int(time.time()),
            price=price,
            ema300=ema300_val,
            zscore_val=z if z is not None else 0,
            velocity_val=vel if vel is not None else 0,
            acceleration_val=acc if acc is not None else 0,
            volume_ratio_val=vol_ratio if vol_ratio is not None else 1,
            linreg_1m_slope=linreg_slopes.get('1m', 0),
            linreg_5m_slope=linreg_slopes.get('5m', 0),
            linreg_15m_slope=linreg_slopes.get('15m', 0),
            linreg_1h_slope=linreg_slopes.get('1h', 0),
            linreg_alignment=linreg_alignment,
            ema300_position=ema300_pos.value,
            ema300_duration=self.ema300_duration,
            zscore_tier=zscore_tier.value,
            volume_regime=volume_reg.value,
            velocity_state=vel_state.value,
            acceleration_state=accel_state.value,
            linreg_slope_state=linreg_state.value,
            linreg_direction=linreg_direction,
            wyckoff_phase=wyckoff,
            ewave_count=ewave,
            trend_quality=trend,
            market_phase=market,
            consecutive_above=self.ema300_duration if current_ema_direction == 'ABOVE' else 0,
            consecutive_below=self.ema300_duration if current_ema_direction == 'BELOW' else 0,
            last_cross_ts=self.last_cross_ts,
        )
        
        # Compute raw score and apply smoothing
        raw_score = self._compute_score(state)
        self.smoothed_score = SCORE_SMOOTHING * raw_score + (1 - SCORE_SMOOTHING) * self.smoothed_score
        state.state_score = self.smoothed_score
        
        # Update entry state machine
        self._update_entry_machine(state)
        
        # Sync state with engine's internal phase
        state.entry_phase = self.entry_phase
        state.position_side = self.position_side
        
        # Debug: log phase changes
        if hasattr(self, '_last_phase') and self._last_phase != self.entry_phase:
            print(f"[CONTINUUM] Phase changed: {self._last_phase} → {self.entry_phase}")
        self._last_phase = self.entry_phase
        
        return state
    
    def _detect_wyckoff(self, closes: List[float], volumes: List[float]) -> str:
        """Simple Wyckoff phase detection."""
        if len(closes) < 100:
            return 'UNKNOWN'
        
        # Look at recent price action (last 100 candles)
        recent = closes[-100:]
        first_25 = sum(recent[:25]) / 25
        mid_50 = sum(recent[25:75]) / 50
        last_25 = sum(recent[75:]) / 25
        
        vol_first = sum(volumes[-100:-75]) / 25 if len(volumes) >= 100 else 1
        vol_last = sum(volumes[-25:]) / 25 if len(volumes) >= 25 else 1
        
        # Markup: price rising, volume increasing
        if last_25 > mid_50 > first_25 and vol_last > vol_first * 1.2:
            return 'MARKUP'
        # Accumulation: price flat/slightly rising, volume increasing
        elif abs(last_25 - first_25) / first_25 < 0.005 and vol_last > vol_first * 1.1:
            return 'ACCUMULATION'
        # Distribution: price flat/slightly falling, volume high
        elif abs(last_25 - first_25) / first_25 < 0.005 and vol_last > vol_first:
            return 'DISTRIBUTION'
        # Markdown: price falling, volume increasing
        elif last_25 < mid_50 < first_25 and vol_last > vol_first * 1.2:
            return 'MARKDOWN'
        else:
            return 'UNKNOWN'
    
    def _detect_ewave(self, closes: List[float]) -> str:
        """Simple Elliott wave detection based on swing highs/lows."""
        if len(closes) < 50:
            return 'UNKNOWN'
        
        # Find pivots in last 50 candles
        recent = closes[-50:]
        pivots = []
        for i in range(2, len(recent) - 2):
            if recent[i] > recent[i-1] and recent[i] > recent[i+1]:
                pivots.append(('H', recent[i]))
            elif recent[i] < recent[i-1] and recent[i] < recent[i+1]:
                pivots.append(('L', recent[i]))
        
        if len(pivots) < 4:
            return 'UNKNOWN'
        
        # Count swings
        highs = [p for p in pivots if p[0] == 'H']
        lows = [p for p in pivots if p[0] == 'L']
        
        if len(highs) >= 2 and len(lows) >= 2:
            # Uptrend: higher highs and higher lows
            if highs[-1][1] > highs[-2][1] and lows[-1][1] > lows[-2][1]:
                return 'W3'  # Impulse wave
            # Downtrend: lower highs and lower lows
            elif highs[-1][1] < highs[-2][1] and lows[-1][1] < lows[-2][1]:
                return 'CA'  # Corrective wave
            else:
                return 'W4'  # Consolidation
        
        return 'UNKNOWN'
    
    def _atr_pct(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
        """ATR as percentage of price."""
        if len(closes) < period + 1:
            return None
        trs = []
        for i in range(1, len(closes)):
            h, l, prev = highs[i], lows[i], closes[i-1]
            tr = max(h - l, abs(h - prev), abs(l - prev))
            trs.append(tr)
        if len(trs) < period:
            return None
        atr_val = sum(trs[-period:]) / period
        return (atr_val / closes[-1]) * 100 if closes[-1] > 0 else None
    
    def _detect_market_phase(self, rsi_val, atr_pct, vol_ratio) -> str:
        """Detect overall market phase."""
        if rsi_val is None or atr_pct is None:
            return 'NEUTRAL'
        
        if rsi_val > 60 and atr_pct > 0.5 and (vol_ratio if vol_ratio is not None else 1) > 1.5:
            return 'STORMY'
        elif rsi_val < 40 and atr_pct > 0.5:
            return 'STORMY'
        elif 45 < rsi_val < 55 and atr_pct < 0.5:
            return 'CALM'
        elif rsi_val > 55:
            return 'RECOVERY'
        elif rsi_val < 45:
            return 'DECLINING'
        else:
            return 'NEUTRAL'
    
    def _compute_score(self, state: ContinuumState) -> float:
        """
        Compute compound state score 0-100.
        50 = neutral. Higher = more bullish. Lower = more bearish.
        """
        score = 50.0
        
        # EMA300 position (+/- 15 points)
        if state.ema300_position == 'ABOVE':
            score += 15
        elif state.ema300_position == 'BELOW':
            score -= 15
        
        # EMA300 duration (logarithmic, +/- 10 points max)
        if state.ema300_duration > 0:
            duration_pts = min(10, math.log2(state.ema300_duration + 1))
            if state.ema300_position == 'ABOVE':
                score += duration_pts
            else:
                score -= duration_pts
        
        # Z-score tier (+/- 15 points)
        zscore_pts = {
            'STRONG_NEG': -15, 'NEG': -5, 'NEUTRAL': 0, 'POS': 5, 'STRONG_POS': 15
        }
        score += zscore_pts.get(state.zscore_tier, 0)
        
        # Volume regime (+/- 12 points)
        vol_pts = {
            'LOW': -8, 'NORMAL': 0, 'HIGH': 8, 'PARABOLIC': 15
        }
        score += vol_pts.get(state.volume_regime, 0)
        
        # Velocity (+/- 10 points)
        vel_pts = {
            'FALLING': -10, 'SLOW': 0, 'RISING': 8, 'FAST': 12
        }
        score += vel_pts.get(state.velocity_state, 0)
        
        # Acceleration (+/- 8 points)
        accel_pts = {
            'NEGATIVE': -8, 'FLAT': 0, 'POSITIVE': 8
        }
        score += accel_pts.get(state.acceleration_state, 0)
        
        # Linear regression slope (+/- 14 points) — highest weight
        linreg_pts = {
            'STEEP_UP': 14, 'UP': 7, 'FLAT': 0, 'DOWN': -7, 'STEEP_DOWN': -14
        }
        score += linreg_pts.get(state.linreg_slope_state, 0)
        
        # Linear regression alignment (+/- 10 points)
        # alignment = fraction of timeframes agreeing on direction
        if state.linreg_direction == 'BULL':
            score += 10 * state.linreg_alignment
        elif state.linreg_direction == 'BEAR':
            score -= 10 * state.linreg_alignment
        elif state.linreg_direction == 'LEAN_BULL':
            score += 5 * state.linreg_alignment
        elif state.linreg_direction == 'LEAN_BEAR':
            score -= 5 * state.linreg_alignment
        
        # Trend quality (+/- 8 points)
        trend_pts = {
            'STRONG_DOWN': -10, 'DOWN': -5, 'WEAK': 0, 'UP': 5, 'STRONG_UP': 10
        }
        score += trend_pts.get(state.trend_quality, 0)
        
        # Wyckoff phase (+/- 8 points)
        wyckoff_pts = {
            'MARKUP': 8, 'ACCUMULATION': 5, 'DISTRIBUTION': -5, 'MARKDOWN': -8, 'UNKNOWN': 0
        }
        score += wyckoff_pts.get(state.wyckoff_phase, 0)
        
        # Elliott wave (+/- 6 points)
        ewave_pts = {
            'W3': 8, 'W1': 5, 'W2': 3, 'W4': 0, 'W5': -3,
            'CA': -5, 'CB': -3, 'CC': 0, 'UNKNOWN': 0
        }
        score += ewave_pts.get(state.ewave_count, 0)
        
        # Market phase (+/- 5 points)
        market_pts = {
            'RECOVERY': 5, 'CALM': 2, 'NEUTRAL': 0, 'DECLINING': -3, 'STORMY': -5
        }
        score += market_pts.get(state.market_phase, 0)
        
        return max(0, min(100, score))
    
    def _update_entry_machine(self, state: ContinuumState):
        """
        Update the entry state machine.
        
        Phases:
        0: No position, watching
        1: EMA300 cross detected (5+ candles above/below)
        2: Confirmed above/below (60+ minutes)
        3: Z-score aligning
        4: ENTRY SIGNAL (all states aligned)
        """
        side = 'LONG' if state.ema300_position == 'ABOVE' else 'SHORT'
        
        # Debug: log entry to update method
        print(f"[CONTINUUM] _update: phase={self.entry_phase}, side={side}, dur={state.ema300_duration}, z={state.zscore_tier}")
        
        # Track consecutive candles below EMA300 (for phase reset logic)
        if state.ema300_position == 'BELOW':
            self._below_count += 1
        else:
            self._below_count = 0
        
        # Phase 0 → 1: EMA300 cross detected
        if self.entry_phase == 0:
            if state.ema300_duration >= ENTRY_CROSS_MIN_DURATION:
                self.entry_phase = 1
                print(f"[CONTINUUM] Phase 1: {side} EMA300 cross detected, duration={state.ema300_duration}")
        
        # Phase 1 → 2: Confirmed above/below (60+ minutes)
        if self.entry_phase == 1:
            if state.ema300_duration >= ENTRY_CONFIRM_MIN_DURATION:
                self.entry_phase = 2
                print(f"[CONTINUUM] Phase 2: {side} confirmed, duration={state.ema300_duration}")
            # No reset — once in Phase 1, stay until confirmed or exit condition breaks
        
        # Phase 2 → 3: Z-score aligning
        if self.entry_phase == 2:
            if side == 'LONG' and state.zscore_tier in ('POS', 'STRONG_POS'):
                self.entry_phase = 3
                print(f"[CONTINUUM] Phase 3: LONG z-score aligning: {state.zscore_tier}")
            elif side == 'SHORT' and state.zscore_tier in ('NEG', 'STRONG_NEG'):
                self.entry_phase = 3
                print(f"[CONTINUUM] Phase 3: SHORT z-score aligning: {state.zscore_tier}")
            # No reset — once confirmed, stay until z-score aligns or exit
        
        # Phase 3 → 4: Volume confirmation (optional but boosts confidence)
        if self.entry_phase == 3:
            if state.volume_regime in ('HIGH', 'PARABOLIC'):
                self.entry_phase = 4
                self.position_side = side
                self.position_size_pct = 100 if state.volume_regime == 'PARABOLIC' else 75
                self.entry_ts = state.ts
                print(f"[CONTINUUM] *** ENTRY SIGNAL *** {side} | Score={state.state_score:.1f} | Volume={state.volume_regime}")
            elif state.ema300_duration < 3 or state.zscore_tier == 'NEUTRAL':
                self.entry_phase = 2  # Step back but don't reset fully
        
        # Exit checks (if we have a position)
        if self.position_side != 'NONE':
            self._check_exits(state)
    
    def _check_exits(self, state: ContinuumState):
        """
        Tiered exit system.
        
        Tier 1: Single state degradation → tighten stop
        Tier 2: Compound degradation → close 50%
        Tier 3: Entry state machine breaks → close all
        """
        # Tier 3: Entry state machine breaks
        if self.position_side == 'LONG' and state.ema300_position == 'BELOW':
            if state.ema300_duration >= EXIT_TIER3_EMA_BREAK:  # Below for N candles
                print(f"[CONTINUUM] *** EXIT SIGNAL *** {self.position_side} → Tier 3: EMA300 break (below for {state.ema300_duration} candles)")
                self.position_side = 'NONE'
                self.position_size_pct = 0
                self.entry_phase = 0
                return
        
        if self.position_side == 'SHORT' and state.ema300_position == 'ABOVE':
            if state.ema300_duration >= EXIT_TIER3_EMA_BREAK:
                print(f"[CONTINUUM] *** EXIT SIGNAL *** {self.position_side} → Tier 3: EMA300 break (above for {state.ema300_duration} candles)")
                self.position_side = 'NONE'
                self.position_size_pct = 0
                self.entry_phase = 0
                return
        
        # Score-based exit
        if state.state_score < SCORE_EXIT_THRESHOLD:
            print(f"[CONTINUUM] *** EXIT SIGNAL *** {self.position_side} → Score below 20: {state.state_score:.1f}")
            self.position_side = 'NONE'
            self.position_size_pct = 0
            self.entry_phase = 0
    
    def save_state(self, state: ContinuumState):
        """Save state to SQLite."""
        try:
            self.db.execute('''
                INSERT OR REPLACE INTO continuum_states
                (token, timeframe, ts, price, ema300, zscore_val, velocity_val,
                 acceleration_val, volume_ratio_val, linreg_1m_slope, linreg_5m_slope,
                 linreg_15m_slope, linreg_1h_slope, linreg_alignment,
                 ema300_position, ema300_duration,
                 zscore_tier, volume_regime, velocity_state, acceleration_state,
                 linreg_slope_state, linreg_direction,
                 wyckoff_phase, ewave_count, trend_quality, market_phase,
                 state_score, entry_phase, position_side, position_size_pct,
                 consecutive_above, consecutive_below, last_cross_ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                state.token, state.timeframe, state.ts, state.price, state.ema300,
                state.zscore_val, state.velocity_val, state.acceleration_val,
                state.volume_ratio_val, state.linreg_1m_slope, state.linreg_5m_slope,
                state.linreg_15m_slope, state.linreg_1h_slope, state.linreg_alignment,
                state.ema300_position, state.ema300_duration,
                state.zscore_tier, state.volume_regime, state.velocity_state,
                state.acceleration_state, state.linreg_slope_state, state.linreg_direction,
                state.wyckoff_phase, state.ewave_count,
                state.trend_quality, state.market_phase, state.state_score,
                state.entry_phase, state.position_side, state.position_size_pct,
                state.consecutive_above, state.consecutive_below, state.last_cross_ts
            ))
            self.db.commit()
        except Exception as e:
            print(f"Error saving state: {e}")
    
    def get_latest_state(self) -> Optional[ContinuumState]:
        """Get the most recent state from DB."""
        try:
            cur = self.db.execute(
                "SELECT * FROM continuum_states WHERE token=? ORDER BY ts DESC LIMIT 1",
                (self.token,)
            )
            row = cur.fetchone()
            cur.close()
            if row:
                return ContinuumState(
                    token=row[1], timeframe=row[2], ts=row[3],
                    price=row[4], ema300=row[5], zscore_val=row[6],
                    velocity_val=row[7], acceleration_val=row[8],
                    volume_ratio_val=row[9],
                    linreg_1m_slope=row[10], linreg_5m_slope=row[11],
                    linreg_15m_slope=row[12], linreg_1h_slope=row[13],
                    linreg_alignment=row[14],
                    ema300_position=row[15], ema300_duration=row[16],
                    zscore_tier=row[17], volume_regime=row[18],
                    velocity_state=row[19], acceleration_state=row[20],
                    linreg_slope_state=row[21], linreg_direction=row[22],
                    wyckoff_phase=row[23], ewave_count=row[24],
                    trend_quality=row[25], market_phase=row[26],
                    state_score=row[27], entry_phase=row[28],
                    position_side=row[29], position_size_pct=row[30],
                    consecutive_above=row[31], consecutive_below=row[32],
                    last_cross_ts=row[33],
                )
        except Exception as e:
            print(f"Error reading state: {e}")
        return None
    
    def run_tick(self):
        """Run one tick of the continuum engine."""
        state = self.compute_states('1m')
        if state:
            self.save_state(state)
            self.state_history.append(state)
            
            # Keep history bounded
            if len(self.state_history) > 1000:
                self.state_history = self.state_history[-500:]
            
            return state
        return None
    
    def run(self):
        """Run the continuum engine continuously."""
        print(f"[CONTINUUM] Starting {self.token} continuum engine (tick every {TICK_INTERVAL}s)")
        
        while True:
            try:
                state = self.run_tick()
                if state:
                    print(f"[CONTINUUM] {state.ts} | "
                          f"Price:{state.price:.1f} | "
                          f"EMA300:{state.ema300_position}({state.ema300_duration}m) | "
                          f"Z:{state.zscore_tier}({state.zscore_val:+.2f}) | "
                          f"Vol:{state.volume_regime} | "
                          f"LinReg:{state.linreg_slope_state}({state.linreg_direction}) | "
                          f"Score:{state.state_score:.1f} | "
                          f"Phase:{self.entry_phase} | "
                          f"Pos:{self.position_side}")
                
                time.sleep(TICK_INTERVAL)
                
            except KeyboardInterrupt:
                print("\n[CONTINUUM] Shutting down")
                break
            except Exception as e:
                print(f"[CONTINUUM] Error: {e}")
                time.sleep(5)


# ── Backtest Mode ──────────────────────────────────────────────────────────────

def backtest(token: str = 'BTC', date_str: str = '2026-09-03'):
    """
    Backtest the continuum engine on historical data.
    """
    print(f"\n[BACKTEST] Running {token} continuum engine on {date_str}")
    
    engine = ContinuumEngine(token)
    
    # Try to load from Binance JSON first (has volume data)
    import glob
    json_files = glob.glob(os.path.join(HERMES_DATA, 'btc_1m_*.json'))
    
    if json_files:
        with open(json_files[0]) as f:
            target_candles = json.load(f)
        print(f"[BACKTEST] Loaded {len(target_candles)} candles from {json_files[0]}")
    else:
        # Fall back to DB
        candles = engine._read_candles('1m', limit=2000)
        if not candles:
            print("No candle data available")
            return
        
        target_dt = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        target_candles = []
        for c in candles:
            candle_dt = datetime.fromtimestamp(c['ts'], tz=timezone.utc).date()
            if candle_dt == target_dt:
                target_candles.append(c)
        
        if not target_candles:
            print(f"No candles for {date_str}")
            return
        
        print(f"[BACKTEST] Loaded {len(target_candles)} candles from DB")
    
    # Simulate
    closes = []
    volumes = []
    score = 50.0  # Initialize in case < 300 candles
    
    for i, candle in enumerate(target_candles):
        closes.append(candle['close'])
        volumes.append(candle['volume'])
        
        if len(closes) < 300:
            continue
        
        # Compute indicators directly (not from DB)
        ema300_val = ema(closes, 300)
        z = zscore(closes, lookback=ZSCORE_LOOKBACK)
        vel = velocity_5m(closes)
        acc = acceleration(closes)
        
        # Volume ratio: current candle vs 60-candle average BEFORE this candle
        if len(volumes) > 60:
            # Use the last 60 candles BEFORE the current one
            prev_60 = volumes[-61:-1]
            avg_60 = sum(prev_60) / len(prev_60) if prev_60 else 1.0
            vol_ratio = volumes[-1] / avg_60 if avg_60 > 0 else 1.0
        else:
            vol_ratio = 1.0
        
        # Debug: print volume ratio at key times (disabled in production)
        # if len(target_candles) > 0:
        #     dt = datetime.fromtimestamp(candle['ts'], tz=timezone.utc)
        #     if dt.hour in [12, 13, 14, 15] and dt.minute % 15 == 0:
        #         print(f"  DEBUG {dt.strftime('%H:%M')} | Vol:{volumes[-1]:.2f} Avg60:{avg_60:.2f} Ratio:{vol_ratio:.2f}x")
        
        if ema300_val is None:
            continue
        
        price = closes[-1]
        
        # Classify
        raw_ema = classify_ema300_position(price, ema300_val)
        raw_z = classify_zscore(z) if z is not None else ZScoreTier.NEUTRAL
        raw_vol = classify_volume(vol_ratio) if vol_ratio is not None else VolumeRegime.NORMAL
        raw_vel = classify_velocity(vel) if vel is not None else Velocity.SLOW
        raw_acc = classify_acceleration(acc) if acc is not None else Acceleration.FLAT
        
        # Linear regression slope (1m only for backtest)
        slope_1m = linreg_slope(closes, LINREG_1M_PERIOD)
        if slope_1m is not None:
            if slope_1m > LINREG_STEEP_UP:
                raw_linreg = LinregSlope.STEEP_UP
            elif slope_1m > LINREG_UP:
                raw_linreg = LinregSlope.UP
            elif slope_1m < LINREG_STEEP_DOWN:
                raw_linreg = LinregSlope.STEEP_DOWN
            elif slope_1m < LINREG_DOWN:
                raw_linreg = LinregSlope.DOWN
            else:
                raw_linreg = LinregSlope.FLAT
        else:
            raw_linreg = LinregSlope.FLAT
            slope_1m = 0
        
        # Apply hysteresis
        _, ema_conf = engine.hysteresis['ema300_position'].update(raw_ema)
        _, z_conf = engine.hysteresis['zscore_tier'].update(raw_z)
        _, vol_conf = engine.hysteresis['volume_regime'].update(raw_vol)
        _, vel_conf = engine.hysteresis['velocity'].update(raw_vel)
        _, acc_conf = engine.hysteresis['acceleration'].update(raw_acc)
        _, linreg_conf = engine.hysteresis['linreg_slope'].update(raw_linreg)
        
        ema_pos = engine.hysteresis['ema300_position'].get_confirmed() or raw_ema
        
        # Track duration
        current_dir = 'ABOVE' if price > ema300_val else 'BELOW'
        if current_dir == engine.ema300_direction:
            engine.ema300_duration += 1
        else:
            engine.ema300_direction = current_dir
            engine.ema300_duration = 1
        
        # Compute score manually for backtest
        score = 50.0
        if ema_pos.value == 'ABOVE':
            score += 15
        elif ema_pos.value == 'BELOW':
            score -= 15
        
        if engine.ema300_duration > 0:
            dur_pts = min(10, math.log2(engine.ema300_duration + 1))
            if current_dir == 'ABOVE':
                score += dur_pts
            else:
                score -= dur_pts
        
        z_pts = {'STRONG_NEG': -15, 'NEG': -5, 'NEUTRAL': 0, 'POS': 5, 'STRONG_POS': 15}
        score += z_pts.get(raw_z.value, 0)
        
        vol_pts = {'LOW': -8, 'NORMAL': 0, 'HIGH': 8, 'PARABOLIC': 15}
        score += vol_pts.get(raw_vol.value, 0)
        
        vel_pts = {'FALLING': -10, 'SLOW': 0, 'RISING': 8, 'FAST': 12}
        score += vel_pts.get(raw_vel.value, 0)
        
        acc_pts = {'NEGATIVE': -8, 'FLAT': 0, 'POSITIVE': 8}
        score += acc_pts.get(raw_acc.value, 0)
        
        # Linear regression slope (+/- 14 points)
        linreg_pts = {'STEEP_UP': 14, 'UP': 7, 'FLAT': 0, 'DOWN': -7, 'STEEP_DOWN': -14}
        score += linreg_pts.get(raw_linreg.value, 0)
        
        score = max(0, min(100, score))
        
        # Entry machine
        engine._update_entry_machine(ContinuumState(
            token=token, timeframe='1m', ts=candle['ts'],
            price=price, ema300=ema300_val,
            zscore_val=z if z is not None else 0,
            velocity_val=vel if vel is not None else 0,
            acceleration_val=acc if acc is not None else 0,
            volume_ratio_val=vol_ratio if vol_ratio is not None else 1,
            ema300_position=ema_pos.value,
            ema300_duration=engine.ema300_duration,
            zscore_tier=raw_z.value,
            volume_regime=raw_vol.value,
            velocity_state=raw_vel.value,
            acceleration_state=raw_acc.value,
            state_score=score,
        ))
        
        # Print every 15 minutes
        if i % 15 == 0:
            dt = datetime.fromtimestamp(candle['ts'], tz=timezone.utc)
            print(f"  {dt.strftime('%H:%M')} | "
                  f"P:{price:.1f} EMA:{ema300_val:.1f} | "
                  f"{ema_pos.value}({engine.ema300_duration}m) | "
                  f"Z:{raw_z.value}({z:+.2f}) | "
                  f"V:{raw_vol.value} | "
                  f"LR:{raw_linreg.value}({slope_1m:+.3f}) | "
                  f"Sc:{score:.1f} | "
                  f"Ph:{engine.entry_phase} | "
                  f"Pos:{engine.position_side}")
    
    print(f"\n[BACKTEST] Final: Phase={engine.entry_phase}, Position={engine.position_side}, Score={score:.1f}")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'backtest':
        date = sys.argv[2] if len(sys.argv) > 2 else '2026-09-03'
        backtest('BTC', date)
    else:
        engine = ContinuumEngine('BTC')
        engine.run()
