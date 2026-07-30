"""
tpsl_utils.py — Sole authority for ATR-based SL/TP management.

Moved from position_manager._collect_atr_updates() (2026-05-15).
All ATR SL/TP computations flow through here. Guardian and decider_run
read SL/TP values written to DB by position_manager, which computes
them via this module.

Single source of truth. No duplicated logic, no inline ATR math elsewhere.

Canonical trailing behaviour:
  LONG  → SL anchored to highest_price (peak). Tightens as price rises.
          TP anchored to highest_price. Tightens as TP rises.
  SHORT → SL anchored to lowest_price (nadir).  Tightens as price falls.
          TP anchored to lowest_price.  Tightens as TP falls.

Phase-based k scaling: ACCELERATING/EXHAUSTION/EXTREME phase reduces k
to snap out faster on first reversal. New trades get INIT floor (wider).

All constants sourced from hermes_constants — no hardcoding.
"""
from __future__ import annotations

import sys
sys.path.insert(0, '/root/.hermes/scripts')

from typing import Optional

from atr_cache import get_atr
from paths import RUNTIME_DB
from hermes_constants import (

    # SL floor/cap
    ATR_SL_MIN, ATR_SL_MAX,
    # Initial entry SL (new trades only)
    ATR_SL_MIN_INIT, ATR_SL_MAX_INIT,
    # Acceleration-phase SL (established trades)
    ATR_SL_MIN_ACCEL,
    # Trailing stop
    TRAILING_DISTANCE_PCT,
    # TP floor/cap
    ATR_TP_MIN, ATR_TP_MAX,
    # Acceleration-phase TP (established trades)
    ATR_TP_MIN_ACCEL,
    # TP multiplier (TP tighter than SL by this factor)
    ATR_TP_K_MULT,
    # k tier thresholds
    ATR_PCT_LOW_THRESH, ATR_PCT_HIGH_THRESH,
    # k tier values
    ATR_K_LOW_VOL, ATR_K_NORMAL_VOL, ATR_K_HIGH_VOL,
    # Phase tiers
    PHASE_TIER_NEUTRAL, PHASE_TIER_BUILDING,
    PHASE_TIER_ACCELERATING, PHASE_TIER_EXHAUSTION, PHASE_TIER_EXTREME,
    # Phase-to-k multipliers
    K_PHASE_ACCEL_STALL, K_PHASE_ACCEL_FAST, K_PHASE_ACCEL_SLOW,
    K_PHASE_EXH_STALL, K_PHASE_EXH_FAST, K_PHASE_EXH_SLOW,
    K_PHASE_EXT_STALL, K_PHASE_EXT_FAST,
    # Phase percentile thresholds (consistent with signal_gen.detect_phase)
    PHASE_BUILDING, PHASE_ACCELERATING, PHASE_EXHAUSTION, PHASE_EXTREME,
    PHASE_NEUTRAL, PHASE_VEL_STALL_THRESH, PHASE_ACCEL_FAST_THRESH,
    # Fallback
    ATR_PCT_FALLBACK,
)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _atr_tier(atr_pct: float) -> float:
    """
    Base k multiplier from ATR%.
    Matches position_manager._atr_multiplier exactly.
    """
    if atr_pct < ATR_PCT_LOW_THRESH:
        return ATR_K_LOW_VOL    # <1%: tight SL
    elif atr_pct > ATR_PCT_HIGH_THRESH:
        return ATR_K_HIGH_VOL   # >1.5%: wide SL
    return ATR_K_NORMAL_VOL     # 0.5-1.5%: balanced


def _phase_from_pct(pct: float, velocity: float) -> str:
    """
    Map speed percentile + velocity → phase string.
    Mirrors signal_gen.detect_phase() exactly — uses same thresholds.
    """
    if pct < PHASE_BUILDING and abs(velocity) < PHASE_VEL_STALL_THRESH:
        return 'quiet'
    if pct >= PHASE_EXTREME:
        return 'extreme'
    if pct >= PHASE_EXHAUSTION:
        return 'exhaustion'
    if pct >= PHASE_ACCELERATING:
        return 'accelerating'
    if pct >= PHASE_BUILDING:
        return 'building'
    return 'quiet'


def _get_current_phase(token: str) -> Optional[str]:
    """Get current market phase for token from token_speeds cache.
    
    Reads speed_percentile and price_velocity_5m from token_speeds table,
    then calls _phase_from_pct() to get phase string.
    
    Returns None if data not available (fail-open for signal filters).
    """
    import sqlite3
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        c = conn.cursor()
        c.execute("""
            SELECT speed_percentile, price_velocity_5m
            FROM token_speeds
            WHERE token = ?
            ORDER BY updated_at DESC LIMIT 1
        """, (token.upper(),))
        row = c.fetchone()
        conn.close()
        if not row:
            return None
        pct = float(row[0] or 50)
        velocity = float(row[1] or 0)
        return _phase_from_pct(pct, velocity)
    except Exception:
        return None


def _atr_sl_k_scaled(
    token: str,
    direction: str,
    atr_pct: float,
    speed_percentile: float,
    momentum_stats: Optional[dict],
) -> float:
    """
    Scale k_SL by phase + velocity stall + speed.
    Phase is computed from direction-specific percentile (not overall).

    base_k → phase_mult → final k.
    ACCELERATING phase: mult < 1.0 → tighter SL (snap out on first reversal).
    EXTREME phase: mult = 0.05-0.10 → tightest.
    """
    base_k = _atr_tier(atr_pct)

    if momentum_stats is None:
        return base_k

    if direction == 'LONG':
        pct = momentum_stats.get('percentile_long', 50)
    else:
        pct = momentum_stats.get('percentile_short', 50)

    velocity = momentum_stats.get('velocity', 0)
    phase_str = _phase_from_pct(pct, velocity)

    phase_tier_map = {
        'neutral':      PHASE_TIER_NEUTRAL,
        'building':     PHASE_TIER_BUILDING,
        'accelerating': PHASE_TIER_ACCELERATING,
        'exhaustion':   PHASE_TIER_EXHAUSTION,
        'extreme':      PHASE_TIER_EXTREME,
    }
    phase_tier = phase_tier_map.get(phase_str, PHASE_TIER_NEUTRAL)

    # Velocity stall: negative velocity at accel+ phase = momentum fading
    stalling = (velocity < 0) and (phase_tier >= PHASE_TIER_ACCELERATING)

    # Phase multiplier
    if phase_tier < PHASE_TIER_ACCELERATING:
        return base_k  # neutral/building — no acceleration
    elif phase_tier == PHASE_TIER_ACCELERATING:
        if stalling:
            mult = K_PHASE_ACCEL_STALL
        elif speed_percentile >= PHASE_ACCEL_FAST_THRESH:
            mult = K_PHASE_ACCEL_FAST
        else:
            mult = K_PHASE_ACCEL_SLOW
    elif phase_tier == PHASE_TIER_EXHAUSTION:
        if stalling:
            mult = K_PHASE_EXH_STALL
        elif speed_percentile >= PHASE_ACCEL_FAST_THRESH:
            mult = K_PHASE_EXH_FAST
        else:
            mult = K_PHASE_EXH_SLOW
    else:  # EXTREME
        if stalling:
            mult = K_PHASE_EXT_STALL
        else:
            mult = K_PHASE_EXT_FAST

    return base_k * mult


# ── Public API ────────────────────────────────────────────────────────────────

def get_fresh_atr(token: str) -> float | None:
    """
    Best available ATR for a token (15m primary, 1h fallback).
    Returns None only if never cached — caller falls back to ATR_PCT_FALLBACK.
    """
    atr = get_atr(token, interval='15m')
    if atr is not None:
        return atr
    return get_atr(token, interval='1h')


def compute_atr_sl_price(
    token: str,
    direction: str,
    entry_price: float,
    current_price: float,
    highest_price: float = 0.0,
    lowest_price: float = 0.0,
) -> float:
    """
    Standalone SL price — no position context needed.
    Uses highest_price (LONG) or lowest_price (SHORT) as anchor if available,
    otherwise falls back to current_price. No trailing, no phase scaling.
    For full trailing SL with phase logic, use compute_atr_sl_tp().
    """
    atr = get_fresh_atr(token)
    if atr is None:
        from hermes_constants import SL_PCT_FALLBACK
        if direction == 'LONG':
            return current_price * (1 - SL_PCT_FALLBACK)
        return current_price * (1 + SL_PCT_FALLBACK)

    atr_pct = atr / current_price
    k = _atr_tier(atr_pct)
    from hermes_constants import ATR_SL_MIN as _min, ATR_SL_MAX as _max
    eff = min(max(k * atr_pct, _min), _max)

    if direction == 'LONG':
        anchor = highest_price if highest_price > 0 else current_price
        return round(anchor * (1 - eff), 8)
    else:
        anchor = lowest_price if lowest_price > 0 else current_price
        return round(anchor * (1 + eff), 8)


def compute_atr_tp_price(
    token: str,
    direction: str,
    entry_price: float,
    current_price: float,
    highest_price: float = 0.0,
    lowest_price: float = 0.0,
) -> float:
    """
    Standalone TP price — no position context needed.
    Uses highest_price (LONG) or lowest_price (SHORT) as anchor if available,
    otherwise falls back to current_price. No trailing, no phase scaling.
    For full trailing TP with phase logic, use compute_atr_sl_tp().
    """
    atr = get_fresh_atr(token)
    if atr is None:
        from hermes_constants import TP_PCT_FALLBACK
        if direction == 'LONG':
            return current_price * (1 + TP_PCT_FALLBACK)
        return current_price * (1 - TP_PCT_FALLBACK)

    atr_pct = atr / current_price
    k = _atr_tier(atr_pct)
    k_tp = k * ATR_TP_K_MULT
    from hermes_constants import ATR_TP_MIN as _min, ATR_TP_MAX as _max
    eff = min(max(k_tp * atr_pct, _min), _max)

    if direction == 'LONG':
        anchor = highest_price if highest_price > 0 else current_price
        return round(anchor * (1 + eff), 8)
    else:
        anchor = lowest_price if lowest_price > 0 else current_price
        return round(anchor * (1 - eff), 8)


def compute_atr_sl_tp(
    token: str,
    direction: str,
    entry_price: float,
    current_price: float,
    highest_price: float = 0.0,
    lowest_price: float = 0.0,
    pnl_pct: float = 0.0,
    current_sl: float = 0.0,
    current_tp: float = 0.0,
    momentum_stats: Optional[dict] = None,
    speed_percentile: float = 50.0,
    flip_k_override: Optional[float] = None,
    trade_open_time: Optional[str] = None,
) -> dict:
    """
    Compute trailing ATR SL and TP for a position.

    SL trailing (canonical):
      LONG  → anchored to highest_price (peak). new_sl > current_sl → tighten.
      SHORT → anchored to lowest_price  (nadir). new_sl < current_sl → tighten.

    TP trailing (canonical — only tighten, never loosen):
      LONG  → anchored to highest_price. new_tp > current_tp → tighten.
      SHORT → anchored to lowest_price.  new_tp < current_tp → tighten.

    Phase-based k: ACCELERATING/EXHAUSTION/EXTREME reduces k → tighter SL/TP.
# New trade (peak≈entry): uses INIT floor (wider for TP, tighter for SL).

    Returns dict:
      {
        'new_sl', 'new_tp',           # computed values
        'needs_sl', 'needs_tp',        # bool — should this be written to DB?
        'anchor': str,                 # debug: what ref_price was used
        'state': str,                  # debug: NEW_TRADE / IN_PROFIT / ESTABLISHED
        'is_new_trade': bool,
        'in_profit': bool,
        'eff_sl_pct', 'eff_tp_pct',   # debug: effective percentages used
        'sl_entry_dist_pct': float,    # debug: SHORT SL distance from entry %
        'k': float,                    # debug: k multiplier used
        'atr', 'atr_pct',              # debug: ATR values used
        'is_init_to_accel_migration': bool,  # debug: INIT→ACCEL migration detected
      }

    Caller (position_manager) writes new_sl/new_tp to DB via _persist_atr_levels.
    Caller applies the needs_sl/needs_tp flags to determine if write is needed.
    """
    # ── Resolve anchor price (peak/low for trailing) ───────────────────────────
    # FIX 2026-07-19: anchor the INITIAL SL to entry_price, not to highest/lowest.
    # Legacy code used highest_price/lowest_price as the anchor for the very first
    # write too — which means if price spikes 1 tick against the position and then
    # reverses, the SL ends up at the spike peak * (1 - k*atr_pct), i.e. ABOVE the
    # current price, immediately on the wrong side of the trade. Reproduced as
    # MORPHO #12522/#12523, LINK #12500, AVAX #12503, etc. (11/26 sub-60s trades
    # in 14d had wrong-side SL; another 10 had SL < 0.10% from entry).
    #
    # Once the initial SL has been written (current_sl > 0) and the trade is in
    # profit, the canonical peak-anchored trailing behavior takes over.
    is_initial_write = (not current_sl or float(current_sl) <= 0)

    # ── BRAND-NEW TRADE GUARD (FIX 2026-07-20) ──────────────────────────────────
    # If the pipeline lock is released immediately (run_pipeline.py:176), two
    # position_manager runs can overlap. The first sets SL correctly anchored to
    # entry_price. The second sees current_sl > 0 (is_initial_write=False) and
    # re-anchors to lowest_price/highest_price — which for SHORT trades with
    # hl_fill < entry produces a SL below entry, triggering instantly.
    # Fix: if the trade was opened within the last 2 minutes, still treat as
    # initial write regardless of current_sl value, and treat as new trade
    # (INIT floor + breakeven guard bypass).
    _brand_new = False
    if trade_open_time:
        try:
            from datetime import datetime, timezone
            _now = datetime.now(timezone.utc)
            if isinstance(trade_open_time, str):
                _open = datetime.fromisoformat(trade_open_time.replace('Z', '+00:00'))
            else:
                _open = trade_open_time
            if _open.tzinfo is None:
                _open = _open.replace(tzinfo=timezone.utc)
            _age_s = (_now - _open).total_seconds()
            if _age_s < 120:
                _brand_new = True
                if not is_initial_write:
                    is_initial_write = True
                    print(f"  [TPSL] {token}: BRAND-NEW TRADE GUARD — trade opened {_age_s:.0f}s ago, "
                          f"forcing is_initial_write=True (prevents wrong-anchor overwrite)")
        except Exception:
            pass

    if direction == 'LONG':
        if is_initial_write and entry_price > 0:
            ref_price = float(entry_price)
        elif highest_price > 0:
            # For LONG: trail from highest_price (best price seen).
            # But ONLY if highest_price > entry (trade is in profit).
            # If highest_price <= entry (trade in loss), use current_price
            # to allow SL to tighten as price drops (protect against further loss).
            if float(highest_price) > float(entry_price):
                ref_price = float(highest_price)
            elif current_price and current_price > 0:
                ref_price = float(current_price)
            else:
                ref_price = float(entry_price)
        elif current_price and current_price > 0:
            ref_price = float(current_price)
        else:
            ref_price = float(entry_price)
    elif direction == 'SHORT':
        if is_initial_write and entry_price > 0:
            ref_price = float(entry_price)
        elif lowest_price > 0:
            # For SHORT: trail from lowest_price (best price seen).
            # But ONLY if lowest_price < entry (trade is in profit).
            # If lowest_price >= entry (trade in loss), use current_price
            # to allow SL to tighten as price rises (protect against further loss).
            if float(lowest_price) < float(entry_price):
                ref_price = float(lowest_price)
            elif current_price and current_price > 0:
                ref_price = float(current_price)
            else:
                ref_price = float(entry_price)
        elif current_price and current_price > 0:
            ref_price = float(current_price)
        else:
            ref_price = float(entry_price)
    else:
        ref_price = current_price if (current_price and current_price > 0) else float(entry_price)

    # ── Fetch ATR ───────────────────────────────────────────────────────────────
    atr = get_fresh_atr(token)

    result = {
        'new_sl': current_sl,
        'new_tp': current_tp,
        'needs_sl': False,
        'needs_tp': False,
        'anchor': '',
        'state': 'UNKNOWN',
        'is_new_trade': False,
        'in_profit': False,
        'eff_sl_pct': 0.0,
        'eff_tp_pct': 0.0,
        'sl_entry_dist_pct': 0.0,
        'k': 1.0,
        'atr': atr or 0.0,
        'atr_pct': 0.0,
        'is_init_to_accel_migration': False,
    }

    if not ref_price or ref_price <= 0:
        return result

    # ── ATR% from effective entry ───────────────────────────────────────────────
    if atr is None or atr <= 0:
        # No ATR — use fallback percentages
        # Use TRAILING_DISTANCE_PCT as the floor (not ATR_SL_MIN_ACCEL)
        # This ensures SL is at least TRAILING_DISTANCE_PCT from entry
        atr_pct = 0.0
        k = _atr_tier(ATR_PCT_FALLBACK)
        # Override MIN_SL_PCT to use trailing distance when ATR is unavailable
        MIN_SL_PCT = TRAILING_DISTANCE_PCT
    else:
        atr_pct = atr / entry_price
        k = _atr_sl_k_scaled(token, direction, atr_pct, speed_percentile, momentum_stats)

    if flip_k_override is not None:
        k = flip_k_override

    sl_pct = k * atr_pct
    tp_pct = k * ATR_TP_K_MULT * atr_pct

    # ── New-trade gate: give fresh positions breathing room ─────────────────────
    # If peak/low price == entry price, trade just opened — no acceleration squeeze.
    # Applying phase multipliers (k=0.05-0.25) would squeeze SL to near-zero.
    # Use base_k + INIT floor instead.
    #
    # NOTE: Removed the `in_profit` requirement — a fresh trade at entry with
    # pnl_pct=0 should also get INIT treatment. The `highest_price ≈ entry`
    # check is the definitive new-trade signal regardless of profit state.
    entry_f = float(entry_price)
    is_new_trade = False

    if direction == 'LONG' and highest_price > 0:
        if abs(highest_price - entry_f) / entry_f < 0.001 and _brand_new:
            is_new_trade = True
    elif direction == 'SHORT' and lowest_price > 0:
        if abs(lowest_price - entry_f) / entry_f < 0.001 and _brand_new:
            is_new_trade = True

    # ── BRAND-NEW TRADE: also force is_new_trade ────────────────────────────────
    # Use the _brand_new flag computed in the guard above (avoids duplicate parsing).
    if not is_new_trade and _brand_new:
        is_new_trade = True

    # ── Determine MIN floor for this trade state ────────────────────────────────
    if is_new_trade:
        if flip_k_override is None:
            k = _atr_tier(atr_pct)  # reset to base k — no acceleration squeeze
        # else: preserve flip_k_override (set above, don't overwrite)
        sl_pct = k * atr_pct
        if atr is not None and atr > 0:
            MIN_SL_PCT = ATR_SL_MIN_INIT   # 0.5% — wider for new trades (breathing room)
        # else: MIN_SL_PCT already set to TRAILING_DISTANCE_PCT above
        MIN_TP_PCT = ATR_TP_MIN         # 1.5% — wider for new trades
    else:
        if atr is not None and atr > 0:
            MIN_SL_PCT = ATR_SL_MIN_ACCEL   # 0.5% — established trade floor (phase scaling bites)
        # else: MIN_SL_PCT already set to TRAILING_DISTANCE_PCT above
        MIN_TP_PCT = ATR_TP_MIN_ACCEL   # 1.0% — tighter for established trades

    # ── Clamp effective percentages ─────────────────────────────────────────────
    # Initial SL set (current_sl is 0/None): also cap at ATR_SL_MAX_INIT
    if not current_sl or current_sl <= 0:
        sl_pct = min(sl_pct, ATR_SL_MAX_INIT)

    eff_sl_pct = min(max(sl_pct, MIN_SL_PCT), ATR_SL_MAX)
    eff_tp_pct = min(max(tp_pct, MIN_TP_PCT), ATR_TP_MAX)

    # For established trades: cap SL at TRAILING_DISTANCE_PCT so trailing can lock profits
    # Without this, the ATR-based floor (0.15-0.50%) overrides the trailing distance (0.20%)
    if not is_new_trade:
        eff_sl_pct = min(eff_sl_pct, TRAILING_DISTANCE_PCT)

    # ── Compute raw SL/TP from anchor price ───────────────────────────────────────
    if direction == 'LONG':
        new_sl = round(ref_price * (1 - eff_sl_pct), 8)
        new_tp = round(ref_price * (1 + eff_tp_pct), 8)
        anchor_label = 'highest_price' if highest_price > 0 else ('current_price' if current_price > 0 else 'entry')
    elif direction == 'SHORT':
        new_sl = round(ref_price * (1 + eff_sl_pct), 8)
        new_tp = round(ref_price * (1 - eff_tp_pct), 8)
        anchor_label = 'lowest_price' if lowest_price > 0 else ('current_price' if current_price > 0 else 'entry')
    else:
        return result

    # ── MINIMUM SL DISTANCE (FIX 2026-07-30) ──────────────────────────────────────
    # Three independent checks, each can raise the SL:
    #   1. From entry: SL >= entry - 0.5% (new trade protection)
    #   2. From peak: SL >= peak - TRAILING_DISTANCE_PCT (trailing floor)
    #   3. From current: SL >= current - 0.5% (breathing room for pullbacks)
    MIN_FROM_CURRENT = 0.004  # 0.4% gap from current price (0.3-0.5% range)
    _force_min_distance = False
    if entry_f > 0:
        if direction == 'LONG' and highest_price > 0:
            moved_pct = (highest_price - entry_f) / entry_f
            # Check 1: from peak (trailing floor)
            if moved_pct > 0.003:
                trail_floor = round(highest_price * (1 - TRAILING_DISTANCE_PCT), 8)
                if new_sl < trail_floor:
                    new_sl = trail_floor
                    _force_min_distance = True
                # SL must never go below previous SL (one-way only)
                if current_sl > 0 and new_sl < current_sl:
                    new_sl = current_sl
                    _force_min_distance = True
            # Check 2: ABSOLUTE FLOOR — SL never drops below entry - 0.5%
            entry_floor = round(entry_f * (1 - ATR_SL_MIN), 8)
            if new_sl > entry_floor:
                new_sl = entry_floor
                _force_min_distance = True
            # Check 3: from current price — ONLY when in profit (trailing)
            # When in loss, entry floor (check 2) is the absolute floor.
            in_profit = current_price > entry_f
            if in_profit:
                current_floor = round(current_price * (1 - MIN_FROM_CURRENT), 8)
                if new_sl > current_floor:
                    new_sl = current_floor
                    _force_min_distance = True
            # When in loss: enforce entry floor as ABSOLUTE (nothing overrides it)
            else:
                entry_floor = round(entry_f * (1 - ATR_SL_MIN), 8)
                if new_sl > entry_floor:
                    new_sl = entry_floor
                    _force_min_distance = True
        elif direction == 'SHORT' and lowest_price > 0:
            moved_pct = (entry_f - lowest_price) / entry_f
            # Check 1: from nadir (trailing floor)
            if moved_pct > 0.003:
                trail_ceil = round(lowest_price * (1 + TRAILING_DISTANCE_PCT), 8)
                if new_sl > trail_ceil:
                    new_sl = trail_ceil
                    _force_min_distance = True
                # SL must never go above previous SL (one-way only)
                if current_sl > 0 and new_sl > current_sl:
                    new_sl = current_sl
                    _force_min_distance = True
            # Check 2: ABSOLUTE CEILING — SL never rises above entry + 0.5%
            entry_ceil = round(entry_f * (1 + ATR_SL_MIN), 8)
            if new_sl < entry_ceil:
                new_sl = entry_ceil
                _force_min_distance = True
            # NOTE: MIN_FROM_CURRENT not applied for SHORT — trailing from nadir
            # handles it. MIN_FROM_CURRENT causes wrong-direction pushes on bounces.

    # ── INIT-to-ACCEL migration ──────────────────────────────────────────────────
    # Detect stale accel-floor SLs on new trades (INIT floor was too tight on entry).
    # Save the ATR-computed value BEFORE trailing gate modifies it.
    # The migration write needs the wide INIT value, not the post-gate value.
    is_init_to_accel_migration = False
    _atr_computed_sl = new_sl  # always save this before trailing gate
    if is_new_trade and current_sl and current_sl > 0:
        old_sl_pct = abs(float(current_sl) - entry_f) / entry_f
        if old_sl_pct < ATR_SL_MIN_INIT * 0.95:  # old SL was < 0.475% — stale accel floor
            is_init_to_accel_migration = True

    # ── WRONG-SIDE SAFETY NET (FIX 2026-07-19) ──────────────────────────────────
    # Last-line guard: if any other code path or future regression produces a
    # new_sl that is on the wrong side of current_price, snap it to a safe
    # distance instead of writing a guaranteed-stop-out.
    # FIX (2026-07-24): When price is deep in loss, don't let the guard create
    # SL that's 3%+ below entry. Use tighter of entry-based and current-price-based.
    # If price is already far below entry, the ATR-based SL (which ran before this
    # guard) is usually correct — only snap if the ATR SL itself was wrong.
    if current_price and current_price > 0 and new_sl and new_sl > 0:
        if direction == 'LONG' and new_sl >= current_price:
            # Only snap if SL is below entry — that's truly wrong-side.
            if new_sl < entry_f:
                # How far is current price from entry?
                loss_from_entry = (entry_f - current_price) / entry_f
                _snap_dist = max(0.002, k * atr_pct) if k and atr_pct else 0.002
                if loss_from_entry > 0.015:
                    # Deep loss: use entry-based SL, not current-price chase.
                    snapped = round(entry_f * (1 - max(ATR_SL_MIN_INIT, _snap_dist)), 8)
                    if snapped >= current_price:
                        snapped = round(current_price * (1 - _snap_dist * 2), 8)
                    print(f"  [TPSL] {token} {direction}: WRONG-SIDE GUARD — deep loss "
                          f"({loss_from_entry*100:.1f}% from entry), proposed SL {new_sl:.6f} "
                          f">= current {current_price:.6f}; entry-anchored → {snapped:.6f}")
                else:
                    # Price close to entry — snap to ATR_SL_MIN_INIT below entry
                    snapped = round(entry_f * (1 - max(ATR_SL_MIN_INIT, 0.003)), 8)
                    # Ensure below current price
                    if snapped >= current_price:
                        snapped = round(current_price * (1 - _snap_dist), 8)
                    print(f"  [TPSL] {token} {direction}: WRONG-SIDE GUARD — proposed SL {new_sl:.6f} "
                          f">= current {current_price:.6f} but below entry {entry_f:.6f}; snapping to {snapped:.6f}")
                new_sl = snapped
                # ABSOLUTE FLOOR: SL never drops below entry - 0.5% for LONG
                _abs_floor = round(entry_f * (1 - ATR_SL_MIN), 8)
                if new_sl < _abs_floor:
                    new_sl = _abs_floor
                if current_sl > 0 and new_sl <= current_sl:
                    result['_force_write'] = False
                else:
                    result['_force_write'] = True
            else:
                # new_sl >= current_price AND new_sl >= entry_f
                # Still wrong-side for LONG — snap below current with ATR buffer
                _snap_dist = max(0.002, k * atr_pct) if k and atr_pct else 0.002
                snapped = round(current_price * (1 - _snap_dist), 8)
                print(f"  [TPSL] {token} {direction}: WRONG-SIDE GUARD — SL {new_sl:.6f} "
                      f">= current {current_price:.6f} and >= entry; snapping to {_snap_dist*100:.2f}% below current → {snapped:.6f}")
                new_sl = snapped
                # ABSOLUTE FLOOR: SL never drops below entry - 0.5% for LONG
                _abs_floor = round(entry_f * (1 - ATR_SL_MIN), 8)
                if new_sl < _abs_floor:
                    new_sl = _abs_floor
                if current_sl > 0 and new_sl <= current_sl:
                    result['_force_write'] = False
                else:
                    result['_force_write'] = True
        elif direction == 'SHORT' and new_sl <= current_price:
            if new_sl > entry_f:
                loss_from_entry = (current_price - entry_f) / entry_f
                _snap_dist = max(0.002, k * atr_pct) if k and atr_pct else 0.002
                if loss_from_entry > 0.015:
                    # Deep loss: use entry-based SL, not current-price chase.
                    # Anchoring to entry prevents "SL perpetually 0.3% above current" pattern.
                    snapped = round(entry_f * (1 + max(ATR_SL_MIN_INIT, _snap_dist)), 8)
                    if snapped <= current_price:
                        # If entry-based SL is still below current, use wider buffer
                        snapped = round(current_price * (1 + _snap_dist * 2), 8)
                    print(f"  [TPSL] {token} {direction}: WRONG-SIDE GUARD — deep loss "
                          f"({loss_from_entry*100:.1f}% from entry), proposed SL {new_sl:.6f} "
                          f"<= current {current_price:.6f}; entry-anchored → {snapped:.6f}")
                else:
                    snapped = round(entry_f * (1 + max(ATR_SL_MIN_INIT, 0.003)), 8)
                    if snapped <= current_price:
                        snapped = round(current_price * (1 + _snap_dist), 8)
                    print(f"  [TPSL] {token} {direction}: WRONG-SIDE GUARD — proposed SL {new_sl:.6f} "
                          f"<= current {current_price:.6f} but above entry {entry_f:.6f}; snapping to {snapped:.6f}")
                new_sl = snapped
                # ABSOLUTE CEILING: SL never rises above entry + 0.5% for SHORT
                _abs_ceil = round(entry_f * (1 + ATR_SL_MIN), 8)
                if new_sl > _abs_ceil:
                    new_sl = _abs_ceil
                # Only force write if snapped SL is actually tighter than current SL.
                # If snapped >= current_sl, the guard is loosening — let trailing gate decide.
                if current_sl > 0 and snapped >= current_sl:
                    result['_force_write'] = False  # trailing gate will block
                else:
                    result['_force_write'] = True
            else:
                # new_sl <= entry_f — SL below entry AND below current price.
                # Would trigger immediate stop-out for SHORT. Snap to safe distance above current.
                _snap_dist = max(0.002, k * atr_pct) if k and atr_pct else 0.002
                snapped = round(current_price * (1 + _snap_dist), 8)
                print(f"  [TPSL] {token} {direction}: WRONG-SIDE GUARD — SL below entry "
                      f"({new_sl:.6f} <= entry {entry_f:.6f}) and below current "
                      f"({current_price:.6f}); snapping to {_snap_dist*100:.2f}% above current → {snapped:.6f}")
                new_sl = snapped
                # ABSOLUTE CEILING: SL never rises above entry + 0.5% for SHORT
                _abs_ceil = round(entry_f * (1 + ATR_SL_MIN), 8)
                if new_sl > _abs_ceil:
                    new_sl = _abs_ceil
                if current_sl > 0 and snapped >= current_sl:
                    result['_force_write'] = False
                else:
                    result['_force_write'] = True

    # ── Trailing SL gate ────────────────────────────────────────────────────────
    # LONG:  SL must trail UP as price rises — only tighten if new_sl > current_sl.
    #        new_sl BELOW current price = in loss territory = WRONG SIDE.
    # SHORT: SL must trail DOWN as price falls — only tighten if new_sl < current_sl.
    #        new_sl ABOVE current price = in loss territory = WRONG SIDE.
    #
    # BUG FIX (2026-05-18): The gate logic was INVERTED for LONG.
    #   - Old (WRONG): `new_sl > current_sl` = tighten → blocked
    #   - Old (WRONG): `new_sl < current_sl` = tighten → allowed (but blocked valid tightening!)
    #   - New: LONG: tighten = new_sl RAISES (higher number) = further from current price
    #          SHORT: tighten = new_sl LOWERS (lower number) = further from current price
    #
    # ── TRAILING GATE: SL NEVER LOOSENS ──────────────────────────────────────
    # Core rule: SL only tightens, never loosens.
    # LONG: SL only goes UP (new_sl > current_sl)
    # SHORT: SL only goes DOWN (new_sl < current_sl)
    # Exception: wrong-side correction (current_sl on wrong side of entry)
    # Exception: _force_min_distance (minimum distance guard snapped SL)
    if _force_min_distance:
        # Minimum distance guard snapped SL — force write regardless of gate logic
        result['needs_sl'] = True
        result['_force_write'] = True
    elif direction == 'LONG':
        if current_sl > 0:
            current_above_entry = (current_sl > entry_f) if entry_f > 0 else False
            if new_sl > current_sl:
                # new_sl RAISES = tighten upward — correct, allow
                result['needs_sl'] = True
            elif current_above_entry:
                # current_sl is above entry (wrong side for LONG).
                # Force update to correct it — this is a correction, not loosening.
                result['needs_sl'] = True
                result['_force_write'] = True
            else:
                # new_sl would loosen — block it
                new_sl = current_sl
                result['needs_sl'] = False
        else:
            result['needs_sl'] = True

    elif direction == 'SHORT':
        if current_sl > 0:
            current_below_entry = (current_sl < entry_f) if entry_f > 0 else False
            if new_sl < current_sl:
                # new_sl LOWERS = tighten downward — correct, allow
                result['needs_sl'] = True
            elif current_below_entry:
                # current_sl is below entry (wrong side for SHORT).
                # Force update to correct it — this is a correction, not loosening.
                result['needs_sl'] = True
                result['_force_write'] = True
            elif new_sl > current_sl and not _force_min_distance:
                # Bug-fix: new_sl is higher than current_sl
                # For SHORT, higher SL = more protection (SL above entry is correct)
                # Allow if new_sl is at TRAILING_DISTANCE_PCT from entry (correct trailing)
                sl_distance = abs(new_sl - entry_f) / entry_f if entry_f > 0 else 0
                if abs(sl_distance - TRAILING_DISTANCE_PCT) < 0.001:  # within 0.1% of trailing distance
                    result['needs_sl'] = True
                    result['_force_write'] = True
                else:
                    # new_sl would loosen — block it
                    new_sl = current_sl
                    result['needs_sl'] = False
            else:
                # new_sl would loosen — block it
                new_sl = current_sl
                result['needs_sl'] = False
        else:
            result['needs_sl'] = True

    # ── POST-GATE MINIMUM SL DISTANCE (FIX 2026-07-30) ──────────────────────────
    # Safety net: same three checks as pre-gate guard.
    MIN_FROM_CURRENT = 0.004
    if entry_f > 0:
        if direction == 'LONG' and highest_price > 0:
            moved_pct = (highest_price - entry_f) / entry_f
            if moved_pct > 0.003:
                trail_floor = round(highest_price * (1 - TRAILING_DISTANCE_PCT), 8)
                if new_sl < trail_floor:
                    new_sl = trail_floor
                    result['needs_sl'] = True
            else:
                entry_floor = round(entry_f * (1 - ATR_SL_MIN), 8)
                if new_sl > entry_floor:
                    new_sl = entry_floor
                    result['needs_sl'] = True
            if in_profit:
                current_floor = round(current_price * (1 - MIN_FROM_CURRENT), 8)
                if new_sl > current_floor:
                    new_sl = current_floor
                    result['needs_sl'] = True
            else:
                entry_floor = round(entry_f * (1 - ATR_SL_MIN), 8)
                if new_sl > entry_floor:
                    new_sl = entry_floor
                    result['needs_sl'] = True
        elif direction == 'SHORT' and lowest_price > 0:
            moved_pct = (entry_f - lowest_price) / entry_f
            if moved_pct > 0.003:
                trail_ceil = round(lowest_price * (1 + TRAILING_DISTANCE_PCT), 8)
                if new_sl > trail_ceil:
                    new_sl = trail_ceil
                    result['needs_sl'] = True
            else:
                entry_ceil = round(entry_f * (1 + ATR_SL_MIN), 8)
                if new_sl < entry_ceil:
                    new_sl = entry_ceil
                    result['needs_sl'] = True

    # ── BREAKEVEN GUARD (REMOVED 2026-07-26) ──────────────────────────────────
    # Previously snapped SL to entry when trade was in profit (pnl_pct >= 0).
    # Removed because: (1) ATR SL with 0.15% floor already trails tightly,
    # (2) guard killed short-lived mean-reversion trades (inv-accel-300) by
    # snapping SL to entry on first tick of profit before signal could develop.
    # ATR_SL_MIN_ACCEL anchored to peak naturally keeps SL near entry for
    # low-vol tokens — explicit guard is redundant and harmful.

    # ── Trailing TP gate (only tighten, never loosen) ──────────────────────────
    # LONG:  TP only increases (numerically higher = further from entry).
    # SHORT: TP only decreases (numerically lower = further from entry).
    if direction == 'LONG':
        if current_tp > 0:
            tp_at_ref = round(ref_price * (1 + eff_tp_pct), 8)  # floored (matches SHORT)
            if tp_at_ref < current_tp:
                new_tp = current_tp  # would loosen — block
                result['needs_tp'] = False
            else:
                new_tp = tp_at_ref  # tighten
                result['needs_tp'] = True
        else:
            new_tp = round(ref_price * (1 + eff_tp_pct), 8)  # floored first set
            result['needs_tp'] = True

    elif direction == 'SHORT':
        if current_tp > 0:
            tp_at_ref = round(ref_price * (1 - eff_tp_pct), 8)
            if tp_at_ref >= current_tp:
                new_tp = current_tp  # would loosen — block
                result['needs_tp'] = False
            else:
                new_tp = tp_at_ref  # tighten
                result['needs_tp'] = True
        else:
            new_tp = round(ref_price * (1 - eff_tp_pct), 8)  # floored first set
            result['needs_tp'] = True

# ── Determine state label ────────────────────────────────────────────────────
    if is_new_trade:
        state = 'NEW_TRADE'
    elif pnl_pct > 0:
        state = 'IN_PROFIT'
    else:
        state = 'ESTABLISHED'

    # ── Debug distances ─────────────────────────────────────────────────────────
    # Bug-12 fix: compute sl_entry_dist for both directions
    if direction == 'SHORT':
        sl_entry_dist = ((new_sl - entry_f) / entry_f) * 100 if entry_f > 0 else 0.0
    else:  # LONG
        sl_entry_dist = ((entry_f - new_sl) / entry_f) * 100 if entry_f > 0 else 0.0

    # ── Debug print ─────────────────────────────────────────────────────────────
    print(f"  [TPSL] {token} {direction}: k={k:.3f} ATR={atr or 0:.4f} ({atr_pct*100:.2f}%) "
          f"→ SL={new_sl:.6f} TP={new_tp:.6f} "
          f"[anchor={anchor_label} ref={ref_price:.6f} "
          f"highest={highest_price:.6f} lowest={lowest_price:.6f} "
          f"entry={entry_f:.6f} current={current_price:.6f} "
          f"state={state} is_new={is_new_trade} pnl_pct={pnl_pct:.4f} "
          f"eff_sl={eff_sl_pct*100:.3f}% eff_tp={eff_tp_pct*100:.3f}%] "
          f"SL_entry_dist={sl_entry_dist:.2f}%")

    if is_init_to_accel_migration:
        print(f"  [TPSL] {token}: INIT→ACCEL migration detected (old SL={current_sl:.6f}, new={new_sl:.6f})")

    # ── Assemble result ───────────────────────────────────────────────────────────
    result.update({
        'new_sl': new_sl,
        'new_tp': new_tp,
        '_atr_computed_new_sl': _atr_computed_sl,  # pre-gate value for INIT→ACCEL migration
        'anchor': anchor_label,
        'state': state,
        'is_new_trade': is_new_trade,
        'in_profit': pnl_pct > 0,
        'eff_sl_pct': eff_sl_pct,
        'eff_tp_pct': eff_tp_pct,
        'sl_entry_dist_pct': sl_entry_dist,
        'k': k,
        'atr': atr or 0.0,
        'atr_pct': atr_pct,
        'is_init_to_accel_migration': is_init_to_accel_migration,
    })

    # needs_sl/needs_tp already set in trailing gate above
    return result


# ── Standalone helpers (no position context needed) ───────────────────────────

def compute_atr_sl_pct(atr_pct: float) -> float:
    """
    Effective SL % for a given raw ATR%.
    Use when you have ATR% and just want the SL %.
    """
    k = _atr_tier(atr_pct)
    eff = k * atr_pct
    return max(ATR_SL_MIN, min(ATR_SL_MAX, eff))


def compute_atr_tp_pct(atr_pct: float) -> float:
    """
    Effective TP % for a given raw ATR%.
    """
    k = _atr_tier(atr_pct)
    k_tp = k * ATR_TP_K_MULT
    eff = k_tp * atr_pct
    return max(ATR_TP_MIN, min(ATR_TP_MAX, eff))


def compute_fallback_sl(current_price: float, direction: str) -> float:
    """
    Fallback SL when ATR is unavailable.
    Uses ATR_SL_MIN as the buffer (lowest-vol assumption).
    """
    if direction == 'LONG':
        return current_price * (1 - ATR_SL_MIN)
    return current_price * (1 + ATR_SL_MIN)


def compute_fallback_tp(current_price: float, direction: str) -> float:
    """
    Fallback TP when ATR is unavailable.
    Uses ATR_TP_MIN as the target (lowest-vol assumption).
    """
    if direction == 'LONG':
        return current_price * (1 + ATR_TP_MIN)
    return current_price * (1 - ATR_TP_MIN)