"""
btc_crash_filter.py — Multi-layer BTC crash detection and entry protection.

Detects crashes BEFORE they happen using leading indicators:
  Layer 1: Dynamic price crash threshold (ATR-scaled, not fixed %)
  Layer 2: Volume spike detection (selling pressure before price breaks)
  Layer 3: Multi-asset contagion (ETH leading BTC down = early warning)
  Layer 4: Price acceleration (velocity increasing downward)
  Layer 5: Position protection (ATR-aware MAE guard for existing LONGs)

Data sources:
  - candles_1m (BTC, ETH, SOL) for price + volume
  - atr_cache.json for dynamic thresholds
  - volatility_gate for ATR%

Usage:
  from btc_crash_filter import check_crash, check_position_protection
  result = check_crash()  # returns CrashSignal
  if result.blocked:
      log(f'Crash detected: {result.reason}')
  protection = check_position_protection(positions)  # returns list of positions to cut
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from paths import HERMES_DATA, CANDLES_DB


# ── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class CrashSignal:
    """Result of crash detection check."""
    blocked: bool = False
    reason: str = ''
    severity: str = ''       # 'WARNING', 'CRITICAL', 'EMERGENCY'
    layer: str = ''          # which layer triggered
    blocked_direction: str = ''  # '' = all directions, 'LONG' = only LONG blocked, 'SHORT' = only SHORT blocked
    price_chg_5m: float = 0.0
    price_chg_1m: float = 0.0
    volume_spike: float = 0.0
    eth_divergence: float = 0.0
    btc_atr_pct: float = 0.0
    dynamic_threshold: float = 0.0
    block_duration_sec: int = 0
    block_until: float = 0.0
    raw: dict = field(default_factory=dict)


@dataclass
class PositionProtection:
    """Result of position protection check for a single position."""
    token: str = ''
    direction: str = ''
    should_cut: bool = False
    reason: str = ''
    mae_from_peak: float = 0.0
    atr_scaled_threshold: float = 0.0


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_candles(token: str, tf: str = '1m', limit: int = 30) -> list:
    """Fetch candles from local DB. Returns list of (ts, open, high, low, close, volume)."""
    table_map = {'1m': 'candles_1m', '5m': 'candles_5m', '15m': 'candles_15m', '1h': 'candles_1h'}
    table = table_map.get(tf, 'candles_1m')
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT ts, open, high, low, close, volume
            FROM {table}
            WHERE token = ?
            ORDER BY ts DESC LIMIT ?
        """, (token.upper(), limit))
        rows = cur.fetchall()
        # Reverse to oldest-first
        rows.reverse()
        return rows
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _get_atr_pct(token: str) -> Optional[float]:
    """Get ATR% from volatility_gate or atr_cache."""
    try:
        from volatility_gate import get_atr_pct
        return get_atr_pct(token)
    except Exception:
        pass
    # Fallback: try atr_cache
    try:
        from atr_cache import get_atr
        atr = get_atr(token)
        if atr:
            # Need close price to convert to %
            candles = _get_candles(token, '1h', 5)
            if candles:
                close = candles[-1][4]
                if close > 0:
                    return (atr / close) * 100
    except Exception:
        pass
    return None


def _compute_volume_spike(volumes: list, window: int = 20) -> float:
    """Compute volume spike ratio: current volume / average of last N candles.
    Returns ratio (e.g. 3.5 = current volume is 3.5x average).
    """
    if len(volumes) < window + 1:
        return 1.0
    avg_vol = sum(volumes[-(window+1):-1]) / window
    if avg_vol <= 0:
        return 1.0
    return volumes[-1] / avg_vol


def _compute_velocity(closes: list, lookback: int = 1) -> float:
    """Compute price velocity (% change per candle).
    Positive = rising, negative = falling.
    """
    if len(closes) < lookback + 1:
        return 0.0
    prev = closes[-(lookback + 1)]
    curr = closes[-1]
    if prev <= 0:
        return 0.0
    return (curr - prev) / prev * 100


def _compute_eth_btc_divergence(btc_closes: list, eth_closes: list, window: int = 5) -> float:
    """Compute ETH/BTC divergence.
    Positive = ETH leading BTC down (ETH fell more than BTC = contagion risk).
    Negative = ETH leading BTC up (bullish).
    """
    if len(btc_closes) < window + 1 or len(eth_closes) < window + 1:
        return 0.0

    btc_chg = (btc_closes[-1] - btc_closes[-(window+1)]) / btc_closes[-(window+1)] * 100 if btc_closes[-(window+1)] > 0 else 0
    eth_chg = (eth_closes[-1] - eth_closes[-(window+1)]) / eth_closes[-(window+1)] * 100 if eth_closes[-(window+1)] > 0 else 0

    # ETH falling more than BTC = contagion risk
    # Positive = ETH fell more than BTC = contagion risk
    return btc_chg - eth_chg


# ── Layer 1: Dynamic Price Crash Threshold ───────────────────────────────────

def _check_price_crash(btc_closes: list, atr_pct: float) -> Tuple[bool, float, float]:
    """Check if BTC price dropped more than ATR-scaled threshold in 5 minutes.

    Dynamic threshold: base_threshold * (atr_pct / baseline_atr)
    - Normal vol (ATR ~0.8%): threshold ≈ -1.5% (same as current)
    - Low vol (ATR ~0.5%): threshold ≈ -1.2% (tighter, crashes hurt more in low vol)
    - High vol (ATR ~1.2%): threshold ≈ -2.2% (wider, normal swings)

    Returns: (blocked, chg_5m, dynamic_threshold)
    """
    from hermes_constants import (
        BTC_CRASH_BLOCK_BASE_THRESHOLD,
        BTC_CRASH_BLOCK_BASELINE_ATR,
        BTC_CRASH_BLOCK_MIN_THRESHOLD,
        BTC_CRASH_BLOCK_MAX_THRESHOLD,
    )

    if len(btc_closes) < 6:
        return False, 0.0, BTC_CRASH_BLOCK_BASE_THRESHOLD

    btc_now = btc_closes[-1]
    btc_5m_ago = btc_closes[-6]

    if btc_5m_ago <= 0:
        return False, 0.0, BTC_CRASH_BLOCK_BASE_THRESHOLD

    chg_5m = (btc_now - btc_5m_ago) / btc_5m_ago * 100

    # Scale threshold with ATR
    if atr_pct is not None and atr_pct > 0:
        atr_ratio = atr_pct / BTC_CRASH_BLOCK_BASELINE_ATR
        dynamic_threshold = BTC_CRASH_BLOCK_BASE_THRESHOLD * atr_ratio
    else:
        dynamic_threshold = BTC_CRASH_BLOCK_BASE_THRESHOLD

    # Clamp to min/max
    dynamic_threshold = max(BTC_CRASH_BLOCK_MIN_THRESHOLD,
                           min(BTC_CRASH_BLOCK_MAX_THRESHOLD, dynamic_threshold))

    blocked = chg_5m < dynamic_threshold
    return blocked, chg_5m, dynamic_threshold


# ── Layer 2: Volume Spike Detection ──────────────────────────────────────────

def _check_volume_spike(btc_candles: list) -> Tuple[bool, float]:
    """Check for volume spike on BTC 1m candles.

    Crashes start with volume surge BEFORE price breaks. A 3x+ volume spike
    on a red candle is a strong leading indicator.

    Returns: (is_spike, volume_ratio)
    """
    from hermes_constants import BTC_CRASH_VOL_SPIKE_THRESHOLD

    if len(btc_candles) < 22:  # need 20 for average + 2 current
        return False, 1.0

    volumes = [c[5] for c in btc_candles]  # volume is index 5
    vol_ratio = _compute_volume_spike(volumes, window=20)

    # Check if current candle is RED (close < open) + volume spike
    last = btc_candles[-1]
    is_red = last[4] < last[1]  # close < open

    is_spike = vol_ratio >= BTC_CRASH_VOL_SPIKE_THRESHOLD and is_red
    return is_spike, vol_ratio


# ── Layer 3: Multi-Asset Contagion ───────────────────────────────────────────

def _check_contagion(btc_closes: list, eth_closes: list, sol_closes: list) -> Tuple[bool, float, float]:
    """Check if ETH/SOL are leading BTC down (contagion early warning).

    ETH typically leads BTC by 1-3 minutes in crashes. If ETH dropped
    significantly more than BTC in the last 5 minutes, expect BTC to follow.

    Returns: (is_contagion, eth_divergence, sol_divergence)
    """
    from hermes_constants import BTC_CRASH_CONTAGION_THRESHOLD

    eth_div = _compute_eth_btc_divergence(btc_closes, eth_closes, window=5)
    sol_div = _compute_eth_btc_divergence(btc_closes, sol_closes, window=5)

    # If ETH fell 0.3%+ more than BTC in 5 minutes → contagion risk
    is_contagion = eth_div > BTC_CRASH_CONTAGION_THRESHOLD

    return is_contagion, eth_div, sol_div


# ── Layer 4: Price Acceleration ──────────────────────────────────────────────

def _check_acceleration(btc_closes: list) -> Tuple[bool, float, float]:
    """Check if BTC price is accelerating downward.

    Velocity now < velocity prev = accelerating down.
    More sensitive than the current fixed threshold approach.

    Returns: (is_accelerating, vel_now, vel_prev)
    """
    from hermes_constants import BTC_ACCEL_VEL_THRESHOLD

    if len(btc_closes) < 3:
        return False, 0.0, 0.0

    vel_now = _compute_velocity(btc_closes, lookback=1)
    vel_prev = _compute_velocity(btc_closes[:-1], lookback=1) if len(btc_closes) >= 4 else 0.0

    # Accelerating down: velocity negative AND getting more negative
    is_accel = (vel_now < BTC_ACCEL_VEL_THRESHOLD and vel_now < vel_prev)

    return is_accel, vel_now, vel_prev


# ── Layer 6: Multi-Alt Divergence ──────────────────────────────────────────

def _check_multi_alt_divergence(btc_closes: list) -> Tuple[bool, int, list]:
    """Check if multiple alts are weak while BTC is falling.

    When 3+ alts show >0.3% 5m divergence below BTC, it signals
    alt-specific selling pressure that could cascade into BTC.

    Returns: (is_weak, weak_count, weak_alts_list)
    """
    from hermes_constants import (
        MULTI_ALT_DIVERGENCE_ENABLED,
        MULTI_ALT_BTC_5M_THRESHOLD,
        MULTI_ALT_DIVERGENCE_THRESHOLD,
        MULTI_ALT_MIN_WEAK_ALTS,
        MULTI_ALT_REFERENCE_ALTS,
    )

    if not MULTI_ALT_DIVERGENCE_ENABLED:
        return False, 0, []

    if len(btc_closes) < 6:
        return False, 0, []

    # Only activate when BTC is falling
    btc_chg_5m = (btc_closes[-1] - btc_closes[-6]) / btc_closes[-6] * 100
    if btc_chg_5m > MULTI_ALT_BTC_5M_THRESHOLD:
        return False, 0, []

    weak_alts = []
    for alt in MULTI_ALT_REFERENCE_ALTS:
        alt_candles = _get_candles(alt, '1m', 10)
        alt_closes = [c[4] for c in alt_candles]
        if len(alt_closes) < 6:
            continue

        alt_chg_5m = (alt_closes[-1] - alt_closes[-6]) / alt_closes[-6] * 100
        divergence = alt_chg_5m - btc_chg_5m

        if divergence < MULTI_ALT_DIVERGENCE_THRESHOLD:
            weak_alts.append(f"{alt}({divergence:+.2f}%)")

    is_weak = len(weak_alts) >= MULTI_ALT_MIN_WEAK_ALTS
    return is_weak, len(weak_alts), weak_alts


# ── Layer 7: BTC 30m Momentum Filter ───────────────────────────────────────

def _check_btc_momentum() -> Tuple[bool, str, float]:
    """Check BTC 30m momentum to block entries during rapid regime shifts.

    When BTC 30m momentum is rising fast, SHORT entries get destroyed by V-reversals.
    When BTC 30m momentum is falling fast, LONG entries get destroyed by cascades.

    Returns: (should_block, direction_blocked, momentum_pct)
    """
    from hermes_constants import (
        BTC_MOMENTUM_FILTER_ENABLED,
        BTC_MOMENTUM_WINDOW,
        BTC_MOMENTUM_RISING_THRESHOLD,
        BTC_MOMENTUM_FALLING_THRESHOLD,
    )

    if not BTC_MOMENTUM_FILTER_ENABLED:
        return False, '', 0.0

    # Fetch 1m BTC candles — need enough for 30m window
    btc_candles = _get_candles('BTC', '1m', BTC_MOMENTUM_WINDOW + 5)
    if len(btc_candles) < BTC_MOMENTUM_WINDOW:
        return False, '', 0.0

    closes = [c[4] for c in btc_candles]
    # Momentum = % change over the window
    momentum_pct = (closes[-1] - closes[-BTC_MOMENTUM_WINDOW]) / closes[-BTC_MOMENTUM_WINDOW] * 100

    if momentum_pct > BTC_MOMENTUM_RISING_THRESHOLD:
        return True, 'SHORT', momentum_pct
    elif momentum_pct < BTC_MOMENTUM_FALLING_THRESHOLD:
        return True, 'LONG', momentum_pct

    return False, '', momentum_pct


# ── Layer 8: BTC Level Filter ────────────────────────────────────────────────

def _check_btc_level() -> Tuple[bool, str, float, float]:
    """Check BTC price level relative to session high/low (mean reversion risk).

    When BTC is near session lows, SHORT entries risk getting caught in bounces.
    When BTC is near session highs, LONG entries risk getting caught in pullbacks.

    Returns: (should_block, direction_blocked, pct_from_high, pct_from_low)
    """
    from hermes_constants import (
        BTC_LEVEL_FILTER_ENABLED,
        BTC_LEVEL_SHORT_BLOCK_PCT,
        BTC_LEVEL_LONG_BLOCK_PCT,
        BTC_LEVEL_LOOKBACK_MIN,
    )

    if not BTC_LEVEL_FILTER_ENABLED:
        return False, '', 0.0, 0.0

    # Fetch 1m BTC candles — need enough for lookback window
    btc_candles = _get_candles('BTC', '1m', BTC_LEVEL_LOOKBACK_MIN + 5)
    if len(btc_candles) < BTC_LEVEL_LOOKBACK_MIN:
        return False, '', 0.0, 0.0

    closes = [c[4] for c in btc_candles]
    current = closes[-1]
    session_high = max(closes[-BTC_LEVEL_LOOKBACK_MIN:])
    session_low = min(closes[-BTC_LEVEL_LOOKBACK_MIN:])

    # Calculate distance from high and low
    pct_from_high = ((current - session_high) / session_high * 100) if session_high > 0 else 0
    pct_from_low = ((current - session_low) / session_low * 100) if session_low > 0 else 0

    # Block SHORT when BTC is near session lows (bounce risk)
    if pct_from_high < BTC_LEVEL_SHORT_BLOCK_PCT:
        return True, 'SHORT', pct_from_high, pct_from_low

    # Block LONG when BTC is near session highs (pullback risk)
    if pct_from_low > BTC_LEVEL_LONG_BLOCK_PCT:
        return True, 'LONG', pct_from_high, pct_from_low

    return False, '', pct_from_high, pct_from_low


# ── Main Crash Check ─────────────────────────────────────────────────────────

def check_crash() -> CrashSignal:
    """
    Multi-layer BTC crash detection.

    Returns CrashSignal with:
      - blocked: True if entries should be blocked
      - severity: WARNING / CRITICAL / EMERGENCY
      - layer: which layer(s) triggered
      - All raw data for logging
    """
    from hermes_constants import (
        BTC_CRASH_BLOCK_ENABLED,
        BTC_ACCEL_ENABLED,
        BTC_CRASH_VOL_SPIKE_ENABLED,
        BTC_CRASH_CONTAGION_ENABLED,
    )

    if not BTC_CRASH_BLOCK_ENABLED:
        return CrashSignal()

    # Fetch BTC candles (1m, need 30 for volume analysis)
    btc_candles = _get_candles('BTC', '1m', 30)
    btc_closes = [c[4] for c in btc_candles]  # close prices

    if len(btc_closes) < 6:
        return CrashSignal()

    # Get ATR for dynamic thresholds
    atr_pct = _get_atr_pct('BTC')

    # Fetch ETH and SOL for contagion check
    eth_candles = _get_candles('ETH', '1m', 10)
    eth_closes = [c[4] for c in eth_candles]
    sol_candles = _get_candles('SOL', '1m', 10)
    sol_closes = [c[4] for c in sol_candles]

    signal = CrashSignal(
        btc_atr_pct=atr_pct or 0.0,
        raw={'btc_candles': len(btc_candles), 'eth_candles': len(eth_candles)},
    )

    triggered_layers = []

    # Safe defaults for layer data (used in reason strings even if layers disabled)
    vol_ratio = 1.0
    eth_div = 0.0
    sol_div = 0.0

    # Layer 1: Price crash
    price_blocked, chg_5m, dyn_thresh = _check_price_crash(btc_closes, atr_pct)
    signal.price_chg_5m = chg_5m
    signal.dynamic_threshold = dyn_thresh
    if price_blocked:
        triggered_layers.append('PRICE')

    # Layer 2: Volume spike
    if BTC_CRASH_VOL_SPIKE_ENABLED:
        is_vol_spike, vol_ratio = _check_volume_spike(btc_candles)
        signal.volume_spike = vol_ratio
        if is_vol_spike:
            triggered_layers.append('VOLUME')

    # Layer 3: Contagion
    if BTC_CRASH_CONTAGION_ENABLED:
        is_contagion, eth_div, sol_div = _check_contagion(btc_closes, eth_closes, sol_closes)
        signal.eth_divergence = eth_div
        if is_contagion:
            triggered_layers.append('CONTAGION')

    # Layer 4: Acceleration
    if BTC_ACCEL_ENABLED:
        accel, vel_now, vel_prev = _check_acceleration(btc_closes)
        signal.price_chg_1m = vel_now
        signal.raw['vel_now'] = vel_now
        signal.raw['vel_prev'] = vel_prev
        if accel:
            triggered_layers.append('ACCEL')

    # Layer 6: Multi-Alt Divergence (cascade early warning)
    multi_alt_blocked, weak_count, weak_alts = _check_multi_alt_divergence(btc_closes)
    if multi_alt_blocked:
        triggered_layers.append('MULTI_ALT')
        signal.raw['weak_alt_count'] = weak_count
        signal.raw['weak_alts'] = weak_alts

    # Layer 7: BTC 30m Momentum Filter (regime-transition detection)
    momentum_blocked, momentum_dir, momentum_pct = _check_btc_momentum()
    signal.raw['btc_30m_momentum'] = momentum_pct
    if momentum_blocked:
        triggered_layers.append('MOMENTUM')
        signal.raw['momentum_dir'] = momentum_dir

    # Layer 8: BTC Level Filter (mean reversion risk)
    level_blocked, level_dir, pct_from_high, pct_from_low = _check_btc_level()
    signal.raw['btc_pct_from_high'] = pct_from_high
    signal.raw['btc_pct_from_low'] = pct_from_low
    if level_blocked:
        triggered_layers.append('BTC_LEVEL')
        signal.raw['level_dir'] = level_dir

    # ── Severity Assessment ──────────────────────────────────────────────
    # EMERGENCY: Price crash + volume spike + contagion = confirmed cascade
    # CRITICAL:  Price crash + any 1 other layer
    # WARNING:   Any 2 non-price layers, or price alone

    n_layers = len(triggered_layers)

    if 'PRICE' in triggered_layers and 'VOLUME' in triggered_layers and 'CONTAGION' in triggered_layers:
        signal.severity = 'EMERGENCY'
        signal.blocked = True
        signal.reason = (f'BTC EMERGENCY: {chg_5m:+.2f}% in 5m (threshold {dyn_thresh:.2f}%) '
                        f'| vol {vol_ratio:.1f}x | ETH lead {eth_div:+.2f}%')
        signal.layer = '+'.join(triggered_layers)
        signal.block_duration_sec = 600  # 10 min

    elif 'PRICE' in triggered_layers and n_layers >= 2:
        signal.severity = 'CRITICAL'
        signal.blocked = True
        signal.reason = (f'BTC CRITICAL: {chg_5m:+.2f}% in 5m (threshold {dyn_thresh:.2f}%) '
                        f'| layers: {",".join(triggered_layers)}')
        signal.layer = '+'.join(triggered_layers)
        signal.block_duration_sec = 300  # 5 min

    elif n_layers >= 2:
        signal.severity = 'WARNING'
        signal.blocked = True
        signal.reason = (f'BTC WARNING: {chg_5m:+.2f}% | layers: {",".join(triggered_layers)} '
                        f'| vol={vol_ratio:.1f}x eth_div={eth_div:+.2f}%')
        signal.layer = '+'.join(triggered_layers)
        signal.block_duration_sec = 180  # 3 min

    elif 'PRICE' in triggered_layers:
        # Price alone — still block (matches current behavior)
        signal.severity = 'WARNING'
        signal.blocked = True
        signal.reason = f'BTC CRASH: {chg_5m:+.2f}% in 5m (threshold {dyn_thresh:.2f}%)'
        signal.layer = 'PRICE'
        signal.block_duration_sec = 300  # 5 min

    # ── MULTI_ALT independent block (Layer 6) ────────────────────────────
    # MULTI_ALT blocks independently with 10-minute duration.
    # If PRICE also triggered, use the LONGER block duration.
    if multi_alt_blocked:
        from hermes_constants import MULTI_ALT_BLOCK_DURATION_MIN
        multi_alt_block_sec = MULTI_ALT_BLOCK_DURATION_MIN * 60  # 10 min

        if not signal.blocked:
            # MULTI_ALT alone — set block
            signal.blocked = True
            signal.severity = 'WARNING'
            signal.layer = 'MULTI_ALT'
            signal.block_duration_sec = multi_alt_block_sec
            signal.reason = (f'Multi-alt weakness: {weak_count} alts diverging '
                           f'{MULTI_ALT_DIVERGENCE_THRESHOLD}%+ below BTC')
        else:
            # PRICE + MULTI_ALT — use longer block duration
            if multi_alt_block_sec > signal.block_duration_sec:
                signal.block_duration_sec = multi_alt_block_sec
                signal.layer = '+'.join(triggered_layers)
                signal.reason += f' | MULTI_ALT: {weak_count} weak alts'

    # ── MOMENTUM independent block (Layer 7) ──────────────────────────────
    # BTC 30m momentum blocks entries in ONE direction only.
    # Rising momentum → block SHORT; falling momentum → block LONG.
    # Independent of other layers — applies its own block duration.
    if momentum_blocked:
        from hermes_constants import BTC_MOMENTUM_BLOCK_DURATION_MIN
        momentum_block_sec = BTC_MOMENTUM_BLOCK_DURATION_MIN * 60  # 10 min

        if not signal.blocked:
            signal.blocked = True
            signal.severity = 'WARNING'
            signal.layer = 'MOMENTUM'
            signal.blocked_direction = momentum_dir  # block SHORT when rising, LONG when falling
            signal.block_duration_sec = momentum_block_sec
            signal.reason = (f'BTC 30m momentum {momentum_pct:+.2f}% — '
                           f'blocking {momentum_dir} entries')
        else:
            if momentum_block_sec > signal.block_duration_sec:
                signal.block_duration_sec = momentum_block_sec
                signal.blocked_direction = momentum_dir
                signal.layer = '+'.join(triggered_layers)
                signal.reason += f' | MOMENTUM: {momentum_pct:+.2f}% ({momentum_dir} blocked)'

    # ── BTC_LEVEL independent block (Layer 8) ─────────────────────────────
    # BTC level blocks entries in ONE direction only.
    # Near session low → block SHORT (bounce risk); near session high → block LONG (pullback risk).
    # Independent of other layers — applies its own block duration.
    if level_blocked:
        from hermes_constants import BTC_LEVEL_BLOCK_DURATION_MIN
        level_block_sec = BTC_LEVEL_BLOCK_DURATION_MIN * 60  # 10 min

        if not signal.blocked:
            signal.blocked = True
            signal.severity = 'WARNING'
            signal.layer = 'BTC_LEVEL'
            signal.blocked_direction = level_dir
            signal.block_duration_sec = level_block_sec
            signal.reason = (f'BTC level: {pct_from_high:+.2f}% from high, '
                           f'{pct_from_low:+.2f}% from low — '
                           f'blocking {level_dir} entries')
        else:
            if level_block_sec > signal.block_duration_sec:
                signal.block_duration_sec = level_block_sec
                signal.blocked_direction = level_dir
                signal.layer = '+'.join(triggered_layers)
                signal.reason += f' | BTC_LEVEL: {level_dir} blocked ({pct_from_high:+.2f}% from high)'

    if signal.blocked:
        signal.block_until = time.time() + signal.block_duration_sec

    return signal


# ── Position Protection (Layer 5) ───────────────────────────────────────────

def check_position_protection(positions: list) -> List[PositionProtection]:
    """
    ATR-aware MAE guard for existing LONG positions.

    Unlike the old fixed-threshold MAE guard:
    - Threshold scales with ATR (wider in high vol, tighter in low vol)
    - Considers BTC regime (if BTC is crashing, tighten thresholds)
    - Only cuts if drop is significant relative to current volatility

    Args:
        positions: list of position dicts with token, direction, highest_price,
                   current_price, entry_price

    Returns:
        List of PositionProtection for positions that should be cut
    """
    from hermes_constants import (
        CL_MAE_GUARD_ENABLED,
        CL_MAE_GUARD_BASE_THRESHOLD,
        CL_MAE_GUARD_BTC_CRASH_MULTIPLIER,
    )

    if not CL_MAE_GUARD_ENABLED:
        return []

    cuts = []

    # Check if BTC is in crash mode (tighten all thresholds)
    btc_candles = _get_candles('BTC', '1m', 10)
    btc_closes = [c[4] for c in btc_candles]
    btc_chg_5m = 0.0
    if len(btc_closes) >= 6:
        btc_chg_5m = (btc_closes[-1] - btc_closes[-6]) / btc_closes[-6] * 100 if btc_closes[-6] > 0 else 0

    btc_in_crash = btc_chg_5m < -0.5  # BTC dropped 0.5%+ in 5 min

    for pos in positions:
        token = pos.get('token', '')
        direction = pos.get('direction', '')
        highest = pos.get('highest_price', 0)
        current = pos.get('current_price', 0)
        entry = pos.get('entry_price', 0)

        if direction != 'LONG' or highest <= 0 or current <= 0:
            continue

        # Compute MAE from peak
        mae_from_peak = (highest - current) / highest

        # Get token's ATR for dynamic threshold
        atr_pct = _get_atr_pct(token)
        if atr_pct is not None and atr_pct > 0:
            # Dynamic threshold: base * (atr / baseline)
            from hermes_constants import BTC_CRASH_BLOCK_BASELINE_ATR
            atr_ratio = atr_pct / BTC_CRASH_BLOCK_BASELINE_ATR
            threshold = CL_MAE_GUARD_BASE_THRESHOLD * atr_ratio
        else:
            threshold = CL_MAE_GUARD_BASE_THRESHOLD

        # If BTC is crashing, tighten threshold (cut faster)
        if btc_in_crash:
            threshold *= CL_MAE_GUARD_BTC_CRASH_MULTIPLIER

        # Minimum threshold: never cut tighter than 1%
        threshold = max(0.01, threshold)

        if mae_from_peak >= threshold:
            protection = PositionProtection(
                token=token,
                direction=direction,
                should_cut=True,
                reason=(f'MAE {mae_from_peak*100:.2f}% from peak > '
                       f'threshold {threshold*100:.1f}%'
                       f'{" (BTC crash)" if btc_in_crash else ""}'),
                mae_from_peak=mae_from_peak,
                atr_scaled_threshold=threshold,
            )
            cuts.append(protection)

    return cuts


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import json

    print("=== BTC Crash Filter — Diagnostic ===\n")

    # Run crash check
    signal = check_crash()
    print(f"Blocked: {signal.blocked}")
    print(f"Severity: {signal.severity or 'NONE'}")
    print(f"Layer: {signal.layer or 'NONE'}")
    print(f"Reason: {signal.reason or 'All clear'}")
    print(f"\nRaw data:")
    print(f"  BTC 5m change: {signal.price_chg_5m:+.3f}%")
    print(f"  BTC 1m velocity: {signal.price_chg_1m:+.3f}%")
    print(f"  Dynamic threshold: {signal.dynamic_threshold:.3f}%")
    print(f"  BTC ATR%: {signal.btc_atr_pct:.4f}%")
    print(f"  Volume spike: {signal.volume_spike:.2f}x")
    print(f"  ETH divergence: {signal.eth_divergence:+.3f}%")
    print(f"  Block duration: {signal.block_duration_sec}s")

    if signal.blocked:
        print(f"\n  🚨 BLOCKING ALL ENTRIES — {signal.severity}")
    else:
        print(f"\n  ✅ All clear — entries allowed")

    # Show BTC candle context
    btc_candles = _get_candles('BTC', '1m', 10)
    if btc_candles:
        print(f"\nBTC 1m candles (last 10):")
        for c in btc_candles[-5:]:
            ts_str = time.strftime('%H:%M', time.localtime(c[0]))
            chg = (c[4] - c[1]) / c[1] * 100 if c[1] > 0 else 0
            print(f"  {ts_str} O={c[1]:.1f} H={c[2]:.1f} L={c[3]:.1f} C={c[4]:.1f} V={c[5]:.0f} ({chg:+.3f}%)")
