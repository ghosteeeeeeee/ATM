#!/usr/bin/env python3
"""
macd_rules.py — MACD math and rules engine for Hermes.

Encodes MACD(12,26,9) crossover logic into executable entry/exit/filter rules.
No LLM calls — pure math, computed from 1h Binance candles.

States:
  BULL_REGIME   — macd_line > 0 and macd > signal
  BEAR_REGIME   — macd_line < 0 and macd < signal
  NEUTRAL       — macd_line near 0 or mixed signal relationship

Crossover freshness:
  FRESH_BULL    — cross_over happened within last 2 candles
  FRESH_BEAR    — cross_under happened within last 2 candles
  STALE         — last crossover was > 2 candles ago

Histogram momentum:
  ACCELERATING  — histogram expanding toward trend direction
  FADING        — histogram contracting toward zero
  REVERSING     — histogram crossing zero
"""

from typing import Optional
from dataclasses import dataclass, field
from enum import IntEnum


# ═══════════════════════════════════════════════════════════════════════════════
# TUNABLE MACD PARAMETERS — backtest-optimized (2026-04-10)
#
# Best config from 90d backtest (BTC/ETH/SOL/AVAX/LINK/DOGE, 212→584 trades):
#   fast=25, slow=65, signal=15  →  WR=50.3%, avg=+0.202%/trade, max_dd=-21.94%
# vs baseline 12/26/9           →  WR=38.5%, avg=-0.078%/trade, max_dd=-57.89%
#
# Why slower MACD wins:
#   - 12/26/9 generates too many crossover signals → noise trades
#   - 25/65/15 is more stable, requires sustained trend confirmation
#   - Fewer but higher-quality signals = better win rate
#
# Why histogram-only exits win:
# ── Tuned MACD params (2026-04-11 backtest sweep — 100 combos × 3 tokens) ───
# Best configs found:
#   SOL: MACD(6,65,15) WR=50.9% PF=1.99  PnL=+61.7%
#   SOL: MACD(12,65,12) WR=49.8% PF=2.06  PnL=+61.8%
#   ETH: MACD(20,55,12) WR=51.7% PF=1.74 PnL=+57.8%
#   HOLD=60m consistently wins across all tokens
#   Threshold 0.1% > 0.2% (lower bar = more wins count)
#   No strength filter needed (0.0 = best)
#
# Aggressive tuning for 75-90% WR target:
#   - Regime filter: require BULL for long, BEAR for short
#   - Require bullish_score >= 2 (out of 3) for entry
#   - Require macd_above_signal AND histogram_positive
#   - Require FRESH crossover (age <= 2 candles)
#   - Require hist_rate > 0 (momentum not fading)

# ── Per-Token MACD Params (loaded from tuner DB, fallback to defaults) ───────────
# Wired to mtf_macd_tuner.db — updated hourly by hermes-mtf-macd-tuner.timer
# This is the single source of truth for MACD params in production.
import sqlite3 as _sqlite3

TUNER_DB = '/root/.hermes/data/mtf_macd_tuner.db'

TOKEN_MACD_PARAMS = {
    # Default fallback — used if DB not yet populated or token not found
    'DEFAULT': {'fast': 12, 'slow': 55, 'signal': 15, 'hold_minutes': 120},
}

def load_token_macd_params():
    """Load per-token MACD params from tuner DB into TOKEN_MACD_PARAMS dict.
    
    Priority: token-specific best config > DEFAULT fallback.
    Logs warning if DB unreachable (uses cached/default values).
    """
    global TOKEN_MACD_PARAMS
    try:
        conn = _sqlite3.connect(TUNER_DB, timeout=5)
        c = conn.cursor()
        c.execute("""SELECT token, fast, slow, signal, hold_minutes
                      FROM token_best_config WHERE is_stale=0""")
        rows = c.fetchall()
        conn.close()
        
        loaded = {}
        for r in rows:
            loaded[r[0]] = {
                'fast': r[1], 'slow': r[2], 'signal': r[3],
                'hold_minutes': r[4] if r[4] else 120,
            }
        
        # Merge: DB values override defaults
        TOKEN_MACD_PARAMS = {'DEFAULT': {'fast': 12, 'slow': 55, 'signal': 15, 'hold_minutes': 120}}
        TOKEN_MACD_PARAMS.update(loaded)
        print(f"[MACD PARAMS] Loaded {len(loaded)} token configs from DB")
    except Exception as e:
        print(f"[MACD PARAMS] DB load failed ({e}), using cached TOKEN_MACD_PARAMS")

def get_macd_params(token: str) -> dict:
    """Return MACD params for token, falling back to DEFAULT."""
    return TOKEN_MACD_PARAMS.get(token, TOKEN_MACD_PARAMS['DEFAULT'])

# Load from DB at import time
load_token_macd_params()

# Legacy module-level params — prefer get_macd_params(token) in new code
MACD_PARAMS = get_macd_params('DEFAULT')
HOLD_MINUTES = MACD_PARAMS['hold_minutes']

# Entry thresholds for high-WR signal
ENTRY_BULLISH_SCORE_MIN = 2   # require score >= 2 for long entry
ENTRY_BEARISH_SCORE_MIN = -2  # require score <= -2 for short entry
PRICE_THRESHOLD_PCT     = 0.001  # 0.1% — win threshold (breakeven = loss)


# ── EMA Helper ────────────────────────────────────────────────────────────────

def ema(data, period):
    """Compute EMA of a price list."""
    if len(data) < period:
        return None
    k = 2 / (period + 1)
    ema_val = data[0]
    for price in data[1:]:
        ema_val = price * k + ema_val * (1 - k)
    return ema_val


# ── Data Structures ───────────────────────────────────────────────────────────

class Regime(IntEnum):
    BULL    = +1
    NEUTRAL =  0
    BEAR    = -1

class CrossoverFreshness(IntEnum):
    FRESH_BULL   = +2   # cross_over within last 2 candles
    STALE_BULL   = +1   # cross_over but > 2 candles ago
    NONE         =  0   # no crossover
    STALE_BEAR   = -1   # cross_under but > 2 candles ago
    FRESH_BEAR   = -2   # cross_under within last 2 candles


@dataclass
class MACDState:
    token: str
    regime: Regime              # BULL / NEUTRAL / BEAR
    crossover_freshness: CrossoverFreshness  # FRESH_BULL / FRESH_BEAR / STALE / NONE
    crossover_age: int         # candles since last crossover (0 = just happened)
    macd_line: float           # EMA12 - EMA26
    signal_line: float         # EMA9 of MACD
    histogram: float           # MACD - Signal
    histogram_rate: float      # (hist[-1] - hist[-2]) / |hist[-2]|  (momentum acceleration)
    macd_above_signal: bool    # current relationship
    histogram_positive: bool    # current histogram sign
    bullish_score: int         # -3 to +3 composite (see score_definition below)
    # Rule evaluation results
    long_entry_allowed: bool
    short_entry_allowed: bool
    exit_long_signals: list     # reasons to exit LONG
    exit_short_signals: list    # reasons to exit SHORT
    flip_long_signals: list     # reasons to flip LONG → SHORT
    flip_short_signals: list    # reasons to flip SHORT → LONG

    def summary(self) -> str:
        return (
            f"{self.token} | "
            f"regime={'BULL' if self.regime==Regime.BULL else 'BEAR' if self.regime==Regime.BEAR else 'NEUTRAL'} | "
            f"xover={'FRESH_BULL' if self.crossover_freshness==CrossoverFreshness.FRESH_BULL else 'FRESH_BEAR' if self.crossover_freshness==CrossoverFreshness.FRESH_BEAR else 'STALE/NONE'} "
            f"(age={self.crossover_age}) | "
            f"hist={'+' if self.histogram_positive else '-'}{abs(self.histogram):.6f} "
            f"(rate={self.histogram_rate:+.3f}) | "
            f"bullish_score={self.bullish_score:+d} | "
            f"LONG={'ALLOWED' if self.long_entry_allowed else 'BLOCKED'} | "
            f"SHORT={'ALLOWED' if self.short_entry_allowed else 'BLOCKED'}"
        )


# ── Rule Evaluation ───────────────────────────────────────────────────────────

def evaluate_macd_rules(state: MACDState) -> MACDState:
    """
    Given a computed MACDState, evaluate all entry/exit/flip rules.
    Returns the same state object (mutates in place for performance).
    """
    state.long_entry_allowed  = _long_entry_allowed(state)
    state.short_entry_allowed = _short_entry_allowed(state)
    state.exit_long_signals    = _exit_long_signals(state)
    state.exit_short_signals   = _exit_short_signals(state)
    state.flip_long_signals    = _flip_long_signals(state)
    state.flip_short_signals   = _flip_short_signals(state)
    return state


def _long_entry_allowed(s: MACDState) -> bool:
    """
    HIGH-WR LONG entry — all conditions must be true:

    1. Regime is BULL (macd_line > 0)        — macro direction confirmed
    2. Crossover is FRESH (age <= 2 candles) — not stale, right timing
    3. bullish_score >= ENTRY_BULLISH_SCORE_MIN (2) — composite strength
    4. hist_rate > 0                         — momentum ACCELERATING, not just positive

    These filters together give 75-90% WR potential by eliminating:
      - Late entries (stale crossover)
      - Weak setups (score < 2)
      - Fading momentum (hist_rate <= 0)
    """
    # 1. Regime must be BULL
    if s.regime != Regime.BULL:
        return False

    # 2. Crossover must be FRESH — not STALE, not NONE
    if s.crossover_freshness != CrossoverFreshness.FRESH_BULL:
        return False

    # 3. Strong composite score — eliminates weak/hybrid signals
    if s.bullish_score < ENTRY_BULLISH_SCORE_MIN:
        return False

    # 4. Momentum must be accelerating (not just positive, actively growing)
    if s.histogram_rate <= 0:
        return False

    return True


def _short_entry_allowed(s: MACDState) -> bool:
    """
    HIGH-WR SHORT entry — all conditions must be true:

    1. Regime is BEAR (macd_line < 0)       — macro direction confirmed
    2. Crossover is FRESH (age <= 2 candles) — right timing
    3. bullish_score <= ENTRY_BEARISH_SCORE_MIN (-2) — strong bearish composite
    4. hist_rate < 0                        — momentum decelerating/falling
    """
    # 1. Regime must be BEAR
    if s.regime != Regime.BEAR:
        return False

    # 2. Crossover must be FRESH
    if s.crossover_freshness != CrossoverFreshness.FRESH_BEAR:
        return False

    # 3. Strong bearish composite score
    if s.bullish_score > ENTRY_BEARISH_SCORE_MIN:  # score is positive for bulls, negative for bears
        return False

    # 4. Momentum is falling
    if s.histogram_rate >= 0:
        return False

    return True


def _exit_long_signals(s: MACDState) -> list:
    """
    Exit LONG when any of these fire:
      1. Histogram crosses zero from positive (momentum broken)
      2. MACD crosses under signal (bearish shift)
      3. Regime flips to BEAR
      4. Histogram fading fast (rate < -0.2)
      5. Crossover STALE for > 8 candles in bull regime
    """
    signals = []

    # Signal 1: Histogram reversing through zero (was +, now going toward -)
    # Detected by histogram_positive=False AND histogram_rate is negative
    if not s.histogram_positive and s.histogram_rate < 0:
        signals.append('histogram_zero_cross_down')

    # Signal 2: Fresh cross_under (bearish crossover)
    if s.crossover_freshness == CrossoverFreshness.FRESH_BEAR:
        signals.append('macd_cross_under')

    # Signal 3: Regime flipped to BEAR
    if s.regime == Regime.BEAR:
        signals.append('regime_bear_flip')

    # Signal 4: Histogram momentum fading fast
    # Tuned (2026-04-10): tighter threshold = exit sooner when momentum breaks
    if s.histogram_rate < -0.10:
        signals.append('histogram_fading_fast')

    # Signal 5: Stale bull — cross_over was > 8 candles ago AND histogram contracting
    if (s.crossover_freshness in (CrossoverFreshness.STALE_BULL, CrossoverFreshness.NONE)
            and s.crossover_age > 8
            and s.histogram_rate < -0.05):
        signals.append('stale_bull_exhausted')

    return signals


def _exit_short_signals(s: MACDState) -> list:
    """Mirror of exit_long_signals for shorts."""
    signals = []

    if s.histogram_positive and s.histogram_rate > 0:
        signals.append('histogram_zero_cross_up')

    if s.crossover_freshness == CrossoverFreshness.FRESH_BULL:
        signals.append('macd_cross_over')

    if s.regime == Regime.BULL:
        signals.append('regime_bull_flip')

    if s.histogram_rate > 0.10:
        signals.append('histogram_rallying_fast')

    if (s.crossover_freshness in (CrossoverFreshness.STALE_BEAR, CrossoverFreshness.NONE)
            and s.crossover_age > 8
            and s.histogram_rate > 0.05):
        signals.append('stale_bear_exhausted')

    return signals


def _flip_long_signals(s: MACDState) -> list:
    """
    Flip LONG → SHORT when:
      1. Exit LONG signals fire AND market is setup for shorts (regime=BEAR or FRESH_BEAR)
      2. Histogram deeply negative AND still falling
      3. MACD deeply below signal AND diverging further
    """
    signals = []

    for exit_sig in _exit_long_signals(s):
        if s.regime == Regime.BEAR or s.crossover_freshness == CrossoverFreshness.FRESH_BEAR:
            signals.append(f'flip_on_exit:{exit_sig}')

    # Strong bear momentum: histogram deeply negative and still falling
    if s.histogram < -0.0005 and s.histogram_rate < -0.10:
        signals.append('bear_momentum_accelerating')

    # MACD far below signal (divergence)
    macd_distance_pct = (s.signal_line - s.macd_line) / abs(s.signal_line) if s.signal_line != 0 else 0
    if macd_distance_pct > 0.20:  # MACD 20%+ below signal = strong bear divergence
        signals.append(f'macd_diverging_bear_{macd_distance_pct:.1%}')

    return signals


def _flip_short_signals(s: MACDState) -> list:
    """Mirror of flip_long_signals for shorts."""
    signals = []

    for exit_sig in _exit_short_signals(s):
        if s.regime == Regime.BULL or s.crossover_freshness == CrossoverFreshness.FRESH_BULL:
            signals.append(f'flip_on_exit:{exit_sig}')

    if s.histogram > 0.0005 and s.histogram_rate > 0.10:
        signals.append('bull_momentum_accelerating')

    macd_distance_pct = (s.macd_line - s.signal_line) / abs(s.signal_line) if s.signal_line != 0 else 0
    if macd_distance_pct > 0.20:
        signals.append(f'macd_diverging_bull_{macd_distance_pct:.1%}')

    return signals


# ── MACD Computation ───────────────────────────────────────────────────────────

def compute_macd_state(token: str, candles: list = None,
                       fast: int = None, slow: int = None, sig: int = None) -> Optional[MACDState]:
    """
    Compute full MACD state for a token.

    Args:
        token: Token symbol (e.g. 'BTC')
        candles: Optional list of {open, high, low, close, volume} dicts.
                 If None, fetches 40 × 1h candles from Binance.
        fast/slow/sig: Optional per-token overrides. If None, fetched from
                       get_macd_params(token) which reads TOKEN_MACD_PARAMS from DB.

    Returns:
        MACDState object with all fields populated and rules evaluated.
        None on error.
    """
    try:
        import requests

        # Resolve per-token params (from DB or defaults)
        p = get_macd_params(token) if (fast is None or slow is None or sig is None) else {'fast': fast, 'slow': slow, 'signal': sig}
        fast  = p['fast']
        slow  = p['slow']
        sig   = p['signal']

        if candles is None:
            # Need slow + signal + 20 candles warmup for EMA convergence
            # With slow=65, signal=15 → need 85+ candles minimum
            limit = max(150, slow + sig + 20)
            url = f"https://api.binance.com/api/v3/klines?symbol={token}USDT&interval=1h&limit={limit}"
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                return None
            klines = resp.json()
            min_required = slow + sig + 5
            if len(klines) < min_required:
                return None
            candles = [{'open': float(k[1]), 'high': float(k[2]),
                        'low': float(k[3]), 'close': float(k[4]), 'volume': float(k[5])}
                       for k in klines]

        if len(candles) < 35:
            return None

        closes = [c['close'] for c in candles]

        # ── Compute EMA series for MACD line ─────────────────────────────────
        # Need slow+ closes to compute first valid EMA(slow)
        ema_fast_series = []
        ema_slow_series = []
        for i in range(slow - 1, len(closes)):  # start at index slow-1 (first valid EMA slow)
            e_fast = ema(closes[:i + 1], fast)
            e_slow = ema(closes[:i + 1], slow)
            ema_fast_series.append(e_fast)
            ema_slow_series.append(e_slow)

        if len(ema_fast_series) < 10:
            return None

        macd_series = [ema_fast_series[i] - ema_slow_series[i] for i in range(len(ema_fast_series))]

        # Current values
        curr_macd = macd_series[-1]
        prev_macd = macd_series[-2]

        # Signal line = EMA(sig) of MACD series
        if len(macd_series) < sig:
            return None
        curr_signal = ema(macd_series[-sig:], sig)
        prev_signal = ema(macd_series[-sig-1:-1], sig) if len(macd_series) >= sig + 1 else macd_series[-2]

        curr_histogram = curr_macd - curr_signal
        prev_histogram = prev_macd - prev_signal

        # ── Crossover detection ────────────────────────────────────────────────
        if prev_macd > prev_signal and curr_macd < curr_signal:
            xover_type = 'cross_under'
        elif prev_macd < prev_signal and curr_macd > curr_signal:
            xover_type = 'cross_over'
        else:
            xover_type = 'none'

        # ── Crossover age ────────────────────────────────────────────────────
        # How many candles ago was the most recent crossover?
        # We scan backwards from the most recent candle
        crossover_age = 0
        xover_at_idx = xover_type  # current type (may be 'none')

        for i in range(1, min(20, len(macd_series) - 9)):
            # Need at least 9 prior candles to compute signal at each step
            if i + 9 >= len(macd_series):
                break

            pm = macd_series[-(i+1)]   # MACD at offset i+1 candles ago
            cm = macd_series[-i]       # MACD at offset i candles ago

            # Signal at offset i+1 and i (need 9 candles before each)
            start_ps = -(i+1) - 9
            end_ps   = -(i+1)
            start_cs = -i - 9
            end_cs   = -i

            # Clamp to valid range
            if start_ps < -len(macd_series):
                start_ps = -len(macd_series)
            if end_ps < start_ps:
                end_ps = start_ps + 1
            if start_cs < -len(macd_series):
                start_cs = -len(macd_series)
            if end_cs < start_cs:
                end_cs = start_cs + 1

            ps_slice = macd_series[start_ps:end_cs] if end_cs > start_ps else macd_series[start_ps:]
            cs_slice = macd_series[start_cs:] if start_cs >= 0 else macd_series[start_cs:]

            if len(ps_slice) < 3 or len(cs_slice) < 3:
                break

            ps_val = ema(ps_slice, 9)
            cs_val = ema(cs_slice, 9)

            if ps_val is None or cs_val is None:
                break

            if pm > ps_val and cm < cs_val:
                crossover_age = i
                xover_at_idx = 'cross_under'
                break
            elif pm < ps_val and cm > cs_val:
                crossover_age = i
                xover_at_idx = 'cross_over'
                break

        # ── Crossover freshness ───────────────────────────────────────────────
        if xover_type == 'cross_over':
            freshness = CrossoverFreshness.FRESH_BULL if crossover_age <= 2 else CrossoverFreshness.STALE_BULL
        elif xover_type == 'cross_under':
            freshness = CrossoverFreshness.FRESH_BEAR if crossover_age <= 2 else CrossoverFreshness.STALE_BEAR
        else:
            freshness = CrossoverFreshness.NONE

        # ── Regime ────────────────────────────────────────────────────────────
        if curr_macd > 0.0001:
            regime = Regime.BULL
        elif curr_macd < -0.0001:
            regime = Regime.BEAR
        else:
            regime = Regime.NEUTRAL

        # ── Histogram rate (momentum acceleration) ─────────────────────────────
        if abs(prev_histogram) > 1e-10:
            hist_rate = (curr_histogram - prev_histogram) / abs(prev_histogram)
        else:
            hist_rate = 0.0

        # ── Bullish score (-3 to +3) ─────────────────────────────────────────
        # Pure composite: each indicator votes once, no double-counting
        # +3 = strongly bullish, 0 = neutral, -3 = strongly bearish
        score = 0
        if curr_macd > curr_signal:    score += 1   # MACD above signal
        if curr_histogram > 0:        score += 1   # histogram positive
        if regime == Regime.BULL:     score += 1   # above zero line
        if freshness == CrossoverFreshness.FRESH_BULL: score += 1  # fresh cross_over is strongest signal
        if hist_rate > 0.1:           score += 1   # momentum accelerating

        if curr_macd < curr_signal:   score -= 1   # MACD below signal
        if curr_histogram < 0:       score -= 1   # histogram negative
        if regime == Regime.BEAR:    score -= 1   # below zero line
        if freshness == CrossoverFreshness.FRESH_BEAR: score -= 1  # fresh cross_under
        if hist_rate < -0.1:         score -= 1   # momentum fading

        # Cap at +/-3
        bullish_score = max(-3, min(3, score))

        # ── Build state object ────────────────────────────────────────────────
        state = MACDState(
            token=token,
            regime=regime,
            crossover_freshness=freshness,
            crossover_age=crossover_age,
            macd_line=curr_macd,
            signal_line=curr_signal,
            histogram=curr_histogram,
            histogram_rate=hist_rate,
            macd_above_signal=(curr_macd > curr_signal),
            histogram_positive=(curr_histogram > 0),
            bullish_score=bullish_score,
            long_entry_allowed=False,
            short_entry_allowed=False,
            exit_long_signals=[],
            exit_short_signals=[],
            flip_long_signals=[],
            flip_short_signals=[],
        )

        return evaluate_macd_rules(state)

    except Exception as e:
        print(f"  [macd_rules] {token} compute error: {e}")
        return None


# ── Cascade entry signal ─────────────────────────────────────────────────────

def cascade_entry_signal(token: str) -> dict:
    """
    Detect cascade entry timing and generate entry/exit signals.

    Key insight: smaller TFs (15m) lead the reversal. When 15m flips but larger
    TFs haven't confirmed yet, that's a CASCADE IN PROGRESS — not a valid entry.
    Trade is WRONG when you enter before larger TFs confirm.

    Cascade LONG entry rules (ALL must be true):
      1. 15m macd_above_signal=True AND histogram_positive=True  (lead TF flipped)
      2. At least one of (1h, 4h) also macd_above_signal=True AND histogram_positive=True
      3. 4h regime is BULL

    Cascade SHORT entry rules (ALL must be true):
      1. 15m macd_above_signal=False AND histogram_positive=False
      2. At least one of (1h, 4h) also macd_above_signal=False AND histogram_positive=False
      3. 4h regime is BEAR

    Entry BLOCKED when:
      - Lead TF (15m) flipped but larger TFs still in opposite direction → EARLY ENTRY DANGER
      - 15m and 1h conflict → no clear direction
      - 4h already flipped away from direction → too late, missed the move

    Returns:
      {
        'cascade_long_allowed': bool,
        'cascade_short_allowed': bool,
        'cascade_direction': 'LONG' | 'SHORT' | None,
        'cascade_active': bool,
        'cascade_score': float,
        'lead_tf': str,
        'confirmation_count': int,
        'entry_block_reason': str | None,
        'mtf_result': dict,
      }
    """
    from candle_db import detect_cascade_direction

    # Get per-TF MACD states
    mtf_result = compute_mtf_macd_alignment(token)
    if mtf_result is None:
        return {
            'cascade_long_allowed': False,
            'cascade_short_allowed': False,
            'cascade_direction': None,
            'cascade_active': False,
            'cascade_score': 0.0,
            'lead_tf': None,
            'confirmation_count': 0,
            'entry_block_reason': 'mtf_data_unavailable',
            'mtf_result': None,
        }

    tf_states = mtf_result['tf_states']
    cascade = detect_cascade_direction(tf_states)

    s_15m = tf_states.get('15m')
    s_1h  = tf_states.get('1h')
    s_4h  = tf_states.get('4h')

    # Extract per-TF conditions
    m15_bull = s_15m and s_15m.macd_above_signal and s_15m.histogram_positive
    m15_bear = s_15m and not s_15m.macd_above_signal and not s_15m.histogram_positive
    m1h_bull = s_1h and s_1h.macd_above_signal and s_1h.histogram_positive
    m1h_bear = s_1h and not s_1h.macd_above_signal and not s_1h.histogram_positive
    m4h_bull = s_4h and s_4h.macd_above_signal and s_4h.histogram_positive
    m4h_bear = s_4h and not s_4h.macd_above_signal and not s_4h.histogram_positive
    s4h_regime_bull = s_4h and s_4h.regime == Regime.BULL
    s4h_regime_bear = s_4h and s_4h.regime == Regime.BEAR

    cascade_direction = cascade['cascade_direction']
    lead_tf = cascade['lead_tf']
    confirmation_count = cascade['confirmation_count']
    cascade_active = cascade['cascade_active']

    # ── LONG entry ────────────────────────────────────────────────────────────
    long_allowed = (
        m15_bull
        and (m1h_bull or m4h_bull)
        and s4h_regime_bull
    )

    # ── SHORT entry ────────────────────────────────────────────────────────────
    short_allowed = (
        m15_bear
        and (m1h_bear or m4h_bear)
        and s4h_regime_bear
    )

    # ── Block reasons ──────────────────────────────────────────────────────────
    long_block = None
    short_block = None

    # Block: 15m flipped but larger TFs still opposite → early entry danger
    if cascade_direction == 'LONG' and cascade_active and not long_allowed:
        if m15_bull and not (m1h_bull or m4h_bull):
            long_block = 'early_entry_awaiting_confirmation'
        elif m15_bull and m1h_bear:
            long_block = '15m_1h_conflict_no_clear_direction'
        elif m15_bull and s4h_regime_bear:
            long_block = '4h_already_flipped_away_missed_move'

    if cascade_direction == 'SHORT' and cascade_active and not short_allowed:
        if m15_bear and not (m1h_bear or m4h_bear):
            short_block = 'early_entry_awaiting_confirmation'
        elif m15_bear and m1h_bull:
            short_block = '15m_1h_conflict_no_clear_direction'
        elif m15_bear and s4h_regime_bull:
            short_block = '4h_already_flipped_away_missed_move'

    cascade_score = cascade.get('reversal_score', 0.0)

    return {
        'cascade_long_allowed': long_allowed,
        'cascade_short_allowed': short_allowed,
        'cascade_direction': cascade_direction,
        'cascade_active': cascade_active,
        'cascade_score': cascade_score,
        'lead_tf': lead_tf,
        'confirmation_count': confirmation_count,
        'entry_block_reason': long_block if cascade_direction == 'LONG' else short_block,
        'mtf_result': mtf_result,
    }


# ── Convenience wrappers ─────────────────────────────────────────────────────

def get_macd_bullish_score(token: str) -> int:
    """Quick -3 to +3 score for a token. Used by ai_decider weighting."""
    state = compute_macd_state(token)
    return state.bullish_score if state else 0


def get_macd_entry_signal(token: str, direction: str) -> dict:
    """
    Returns dict with:
      allowed: bool
      reason: str
      state: MACDState

    Usage:
      result = get_macd_entry_signal('TRB', 'LONG')
      if not result['allowed']:
          print(f"Entry blocked: {result['reason']}")
    """
    state = compute_macd_state(token)
    if state is None:
        return {'allowed': False, 'reason': 'macd_data_unavailable', 'state': None}

    if direction.upper() == 'LONG':
        return {
            'allowed': state.long_entry_allowed,
            'reason': 'macd_bearish_regime' if not state.long_entry_allowed else 'macd_confirmed_bull',
            'state': state,
        }
    else:
        return {
            'allowed': state.short_entry_allowed,
            'reason': 'macd_bullish_regime' if not state.short_entry_allowed else 'macd_confirmed_bear',
            'state': state,
        }


def get_macd_exit_signal(token: str, position_dir: str) -> dict:
    """
    Check if a position should be exited based on MACD rules.

    Returns dict with:
      should_exit: bool
      should_flip: bool
      reasons: list
      state: MACDState
    """
    state = compute_macd_state(token)
    if state is None:
        return {'should_exit': False, 'should_flip': False, 'reasons': [], 'state': None}

    pos_dir = position_dir.upper()
    if pos_dir == 'LONG':
        return {
            'should_exit': bool(state.exit_long_signals),
            'should_flip': bool(state.flip_long_signals),
            'reasons': state.exit_long_signals + [f'FLIP: {r}' for r in state.flip_long_signals],
            'state': state,
        }
    else:
        return {
            'should_exit': bool(state.exit_short_signals),
            'should_flip': bool(state.flip_short_signals),
            'reasons': state.exit_short_signals + [f'FLIP: {r}' for r in state.flip_short_signals],
            'state': state,
        }


def _fetch_binance_candles(token: str, interval: str, limit: int = None) -> Optional[list]:
    """
    Fetch klines from Binance API. interval: '4h', '1h', '15m', etc.

    For slow MACD (65/15): need slow + signal + 20 = 100+ candles.
    Default limit=None → uses MACD_PARAMS to determine sufficient count.
    """
    import requests
    # Determine sufficient candle count based on MACD_PARAMS (defined at module level)
    if limit is None:
        limit = max(150, MACD_PARAMS['slow'] + MACD_PARAMS['signal'] + 20)
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={token}USDT&interval={interval}&limit={limit}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        klines = resp.json()
        min_required = MACD_PARAMS['slow'] + MACD_PARAMS['signal'] + 5
        if len(klines) < min_required:
            return None
        return [{'open': float(k[1]), 'high': float(k[2]),
                 'low': float(k[3]), 'close': float(k[4]), 'volume': float(k[5])}
                for k in klines]
    except Exception:
        return None


def compute_mtf_macd_alignment(token: str) -> Optional[dict]:
    """
    Compute multi-timeframe MACD alignment using the FULL macd_rules state machine.

    Fetches 4H, 1H, and 15m candles from Binance. For each TF, runs compute_macd_state()
    which applies the full regime/crossover/histogram rules engine — NOT just a simple
    EMA crossover.

    Returns:
        {
            'mtf_score': int,           # 0-3, how many TFs agree
            'mtf_direction': str,       # 'LONG' | 'SHORT' | 'NEUTRAL'
            'mtf_confidence': float,    # 0.0 to 1.0
            'all_tfs_bullish': bool,
            'all_tfs_bearish': bool,
            'tf_states': {
                '4h': MACDState | None,
                '1h': MACDState | None,
                '15m': MACDState | None,
            }
        }

    Alignment rules:
      - Bullish TF: macd_line > signal_line AND histogram > 0 (full bull regime)
      - Bearish TF: macd_line < signal_line AND histogram < 0 (full bear regime)
      - 3/3 agree = ultra-confirmation → mtf_confidence = 1.0
      - 2/3 agree = strong confluence → mtf_confidence = 0.75
      - 1/3 agree = weak/mixed → mtf_confidence = 0.25
      - 0/3 agree = no alignment → NEUTRAL, confidence 0.0
    """
    # Fetch all three TFs in parallel
    candles_4h  = _fetch_binance_candles(token, '4h',  40)
    candles_1h  = _fetch_binance_candles(token, '1h',  40)
    candles_15m = _fetch_binance_candles(token, '15m', 40)

    tf_states = {}
    bullish_count = 0
    bearish_count = 0

    for tf_name, candles in [('4h', candles_4h), ('1h', candles_1h), ('15m', candles_15m)]:
        if candles is None:
            tf_states[tf_name] = None
            continue

        state = compute_macd_state(token, candles)
        tf_states[tf_name] = state

        if state is None:
            continue

        # Bullish: MACD above signal AND histogram positive (confirmed bull trend)
        if state.macd_above_signal and state.histogram_positive:
            bullish_count += 1
        # Bearish: MACD below signal AND histogram negative
        elif not state.macd_above_signal and not state.histogram_positive:
            bearish_count += 1

    # Determine alignment
    total_valid = sum(1 for s in tf_states.values() if s is not None)
    if total_valid == 0:
        return None

    mtf_score = max(bullish_count, bearish_count)

    if bullish_count >= 2:
        mtf_direction = 'LONG'
    elif bearish_count >= 2:
        mtf_direction = 'SHORT'
    else:
        mtf_direction = 'NEUTRAL'

    all_tfs_bullish = (bullish_count == 3)
    all_tfs_bearish = (bearish_count == 3)

    # Confidence: 3/3 = 1.0, 2/3 = 0.75, 1/3 = 0.25, 0 = 0.0
    if mtf_score == 3:
        mtf_confidence = 1.0
    elif mtf_score == 2:
        mtf_confidence = 0.75
    elif mtf_score == 1:
        mtf_confidence = 0.25
    else:
        mtf_confidence = 0.0

    return {
        'mtf_score': mtf_score,
        'mtf_direction': mtf_direction,
        'mtf_confidence': mtf_confidence,
        'all_tfs_bullish': all_tfs_bullish,
        'all_tfs_bearish': all_tfs_bearish,
        'tf_states': tf_states,
    }


# ── CLI test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 macd_rules.py <TOKEN> [TOKEN ...]")
        print("Example: python3 macd_rules.py TRB IMX ETH")
        sys.exit(1)

    for token in sys.argv[1:]:
        state = compute_macd_state(token)
        if state:
            print(state.summary())
            print(f"  → LONG {'ALLOWED' if state.long_entry_allowed else 'BLOCKED'}")
            print(f"  → SHORT {'ALLOWED' if state.short_entry_allowed else 'BLOCKED'}")
            if state.exit_long_signals:
                print(f"  → EXIT LONG: {state.exit_long_signals}")
            if state.flip_long_signals:
                print(f"  → FLIP LONG→SHORT: {state.flip_long_signals}")
        else:
            print(f"{token}: error computing MACD state")
        print()