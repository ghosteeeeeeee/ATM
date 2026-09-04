#!/usr/bin/env python3
"""
continuum_constants.py — All tunable parameters for the Continuum Engine.

DO NOT hardcode magic numbers in continuum_engine.py or continuum_trader.py.
Everything lives here. Import with: from continuum_constants import *
"""

# ── Hysteresis (per-state ON/OFF thresholds) ──────────────────────────────────
# Format: (candles_to_turn_ON, candles_to_turn_OFF)

HYSTERESIS = {
    'ema300_position':   (5, 3),    # 5 candles above to confirm, 3 below to deconfirm
    'zscore_tier':       (3, 5),    # 3 candles to confirm z-score tier, 5 to deconfirm
    'volume_regime':     (3, 5),    # 3 candles of high vol to confirm
    'velocity':          (3, 3),    # symmetric
    'acceleration':      (3, 3),    # symmetric
    'linreg_slope':      (5, 5),    # 5 candles to confirm slope change
}

# ── EMA300 ────────────────────────────────────────────────────────────────────
EMA300_PERIOD = 300
EMA300_ABOVE_BUFFER = 0.001   # 0.1% above EMA300 = "ABOVE"
EMA300_BELOW_BUFFER = 0.001   # 0.1% below EMA300 = "BELOW"

# ── Z-Score ───────────────────────────────────────────────────────────────────
ZSCORE_LOOKBACK = 120         # candles for rolling mean/std
ZSCORE_STRONG_NEG = -1.5
ZSCORE_NEG = -0.5
ZSCORE_POS = 0.5
ZSCORE_STRONG_POS = 1.5

# ── Volume ────────────────────────────────────────────────────────────────────
VOLUME_AVG_PERIOD = 60        # candles for rolling volume average
VOLUME_LOW_THRESHOLD = 0.5    # < 0.5x avg = LOW
VOLUME_HIGH_THRESHOLD = 1.5   # > 1.5x avg = HIGH
VOLUME_PARABOLIC_THRESHOLD = 3.0  # > 3x avg = PARABOLIC

# ── Velocity ──────────────────────────────────────────────────────────────────
VELOCITY_FALLING = -0.3       # % per 5 candles
VELOCITY_SLOW_LOW = -0.3
VELOCITY_SLOW_HIGH = 0.3
VELOCITY_RISING = 0.3
VELOCITY_FAST = 1.0           # > 1% per 5 candles = FAST

# ── Acceleration ──────────────────────────────────────────────────────────────
ACCEL_NEGATIVE = -0.05        # % change in velocity
ACCEL_POSITIVE = 0.05

# ── Linear Regression Slope ──────────────────────────────────────────────────
LINREG_1M_PERIOD = 60         # 1-hour lookback on 1m candles
LINREG_5M_PERIOD = 12         # 1-hour lookback on 5m candles
LINREG_15M_PERIOD = 8         # 2-hour lookback on 15m candles
LINREG_1H_PERIOD = 6          # 6-hour lookback on 1h candles

LINREG_STEEP_UP = 0.10       # % per candle = STEEP_UP
LINREG_UP = 0.02              # % per candle = UP
LINREG_FLAT_LOW = -0.02       # % per candle = FLAT range low
LINREG_FLAT_HIGH = 0.02       # % per candle = FLAT range high
LINREG_DOWN = -0.02           # % per candle = DOWN
LINREG_STEEP_DOWN = -0.10     # % per candle = STEEP_DOWN

# ── Entry State Machine ───────────────────────────────────────────────────────
ENTRY_CROSS_MIN_DURATION = 5      # candles above/below EMA300 to detect cross
ENTRY_CONFIRM_MIN_DURATION = 60   # candles (minutes) to confirm trend
ENTRY_ZSCORE_ALIGN = True         # require z-score to align with direction
ENTRY_VOLUME_CONFIRM = True       # volume confirmation boosts confidence

# ── Score Thresholds ──────────────────────────────────────────────────────────
SCORE_NO_TRADE = 30           # below this = no position
SCORE_SMALL_POSITION = 40     # 25% position size
SCORE_NORMAL_POSITION = 50    # 50% position size
SCORE_FULL_POSITION = 70      # 75% position size
SCORE_MAX_POSITION = 85       # 100% position size

SCORE_EXIT_THRESHOLD = 20     # below this = exit

# ── Score Weights ─────────────────────────────────────────────────────────────
SCORE_WEIGHTS = {
    'ema300_position':     0.12,
    'ema300_duration':     0.08,
    'zscore_tier':         0.12,
    'volume_regime':       0.10,
    'velocity':            0.08,
    'acceleration':        0.06,
    'linreg_slope':        0.14,   # highest weight — directional conviction
    'linreg_alignment':    0.10,   # multi-TF slope agreement
    'wyckoff_phase':       0.06,
    'ewave_count':         0.04,
    'trend_quality':       0.05,
    'market_phase':        0.05,
}

# ── Exit Thresholds ───────────────────────────────────────────────────────────
EXIT_TIER1_SCORE_DROP = 10    # score drops this much = tighten stop
EXIT_TIER2_STATES_DEGRADED = 2  # 2+ states degrade = close 50%
EXIT_TIER3_EMA_BREAK = 3     # candles below EMA300 = close all

# ── Position Sizing ───────────────────────────────────────────────────────────
MAX_POSITION_USD = 11          # HL minimum — start with one tiny position
LEVERAGE = 10                  # leverage multiplier
MAX_CONTINUUM_POSITIONS = 1    # ONLY 1 position at a time — no accumulation

# ── Rate Limiting (anti pump_hunter) ──────────────────────────────────────────
MIN_TIME_BETWEEN_TRADES = 3600   # 1 hour minimum between any trade (entry or exit)
MIN_TIME_BETWEEN_ENTRIES = 7200   # 2 hours minimum between new entries
MIN_TIME_BETWEEN_EXITS = 600      # 10 minutes minimum between exits
MAX_TRADES_PER_DAY = 6            # max 6 trades per day (3 round trips)
COOLDOWN_AFTER_LOSS = 7200        # 2 hour cooldown after a losing trade

# ── Tick Interval ─────────────────────────────────────────────────────────────
TICK_INTERVAL = 30            # seconds between state updates

# ── System Isolation ──────────────────────────────────────────────────────────
POSITION_TAG = "CONTINUUM"    # prefix for order tags to identify our positions
POSITION_FILE = "continuum_positions.json"
