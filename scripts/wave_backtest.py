#!/usr/bin/env python3
"""
wave_backtest.py — Bidirectional Wave Rider Backtest Engine

Tests MACD wave-based entry/exit/sizing strategies against historical candles.
Tracks reversals separately from stops. Tests failure-mode guards empirically.

Usage:
  python3 wave_backtest.py                    # quick BTC 4H validation (30s)
  python3 wave_backtest.py --full-grid       # all 677K configs (hours)
  python3 wave_backtest.py --tokens BTC ETH SOL --timeframes 4h 1h
"""
import sqlite3, json, time, hashlib, argparse, sys, math
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

# ── Paths ────────────────────────────────────────────────────────────────────
CANDLES_DB = '/root/.hermes/data/candles.db'
RESULTS_DB = '/root/.hermes/data/wave_results.db'

# ── MACD Parameters ──────────────────────────────────────────────────────────
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9

# ── ATR Period ────────────────────────────────────────────────────────────────
ATR_PERIOD = 14


# ═══════════════════════════════════════════════════════════════════════════════
#  MATH HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def ema(data, period):
    if len(data) < period:
        return None
    k = 2 / (period + 1)
    val = sum(data[:period]) / period
    for price in data[1:]:
        val = price * k + val * (1 - k)
    return val


def compute_macd_state(closes: list) -> Optional[dict]:
    """
    Compute MACD state for a list of close prices.
    Returns dict with all wave/velocity fields or None if insufficient data.
    """
    n = len(closes)
    if n < MACD_SLOW + MACD_SIGNAL + 5:
        return None

    # EMA series
    ema_fast = [None] * n
    ema_slow = [None] * n
    macd_series = [None] * n

    for i in range(n):
        ef = ema(closes[:i+1], MACD_FAST)
        es = ema(closes[:i+1], MACD_SLOW)
        if ef is not None and es is not None:
            ema_fast[i] = ef
            ema_slow[i] = es
            macd_series[i] = ef - es

    # Signal line (EMA9 of MACD)
    signal_series = [None] * n
    for i in range(n):
        if i >= 9 and macd_series[i] is not None:
            window = [m for m in macd_series[max(0,i-8):i+1] if m is not None]
            if len(window) >= 9:
                signal_series[i] = ema(window, 9)

    # Diff series (histogram = MACD - Signal)
    diff_series = [None] * n
    for i in range(n):
        if macd_series[i] is not None and signal_series[i] is not None:
            diff_series[i] = macd_series[i] - signal_series[i]

    # Current values (last complete candle)
    curr_macd = macd_series[-1]
    curr_signal = signal_series[-1]
    curr_diff = diff_series[-1]
    prev_macd = macd_series[-2]
    prev_signal = signal_series[-2]
    prev_diff = diff_series[-2]

    if curr_macd is None or curr_signal is None or prev_diff is None:
        return None

    # Regime
    if curr_macd > 0.0001:
        regime = 1   # BULL
    elif curr_macd < -0.0001:
        regime = -1  # BEAR
    else:
        regime = 0   # NEUTRAL

    # MACD above/below signal
    macd_above = curr_macd > curr_signal
    hist_positive = curr_diff > 0

    # Velocity: rate of change of MACD line
    # Floor: don't divide by values near zero (causes velocity explosions at MACD crossings)
    MACD_VEL_FLOOR = 0.5  # minimum |MACD| value for velocity calc
    if prev_macd is not None and abs(prev_macd) > 1e-10:
        denom = max(abs(prev_macd), MACD_VEL_FLOOR)
        velocity = (curr_macd - prev_macd) / denom
    else:
        velocity = 0.0

    # Histogram rate (acceleration)
    HIST_RATE_FLOOR = 0.1
    if prev_diff is not None and abs(prev_diff) > 1e-10:
        denom = max(abs(prev_diff), HIST_RATE_FLOOR)
        hist_rate = (curr_diff - prev_diff) / denom
    else:
        hist_rate = 0.0

    # Crossover detection + age
    crossover_age = 0
    crossover_type = 'none'  # 'cross_over', 'cross_under', 'none'
    lookback = min(20, len(diff_series) - 1)
    for i in range(1, lookback + 1):
        d_now = diff_series[-i]
        d_prev = diff_series[-(i+1)]
        if d_now is None or d_prev is None:
            break
        if d_prev > 0 and d_now < 0:
            crossover_age = i
            crossover_type = 'cross_under'
            break
        elif d_prev < 0 and d_now > 0:
            crossover_age = i
            crossover_type = 'cross_over'
            break

    # Wave counting (sign changes in diff_series over lookback)
    bull_crosses = 0
    bear_crosses = 0
    last_cross_was_bull = None
    for i in range(1, lookback + 1):
        dn = diff_series[-i]
        dp = diff_series[-(i+1)]
        if dn is None or dp is None:
            break
        if dp > 0 and dn < 0:
            bear_crosses += 1
            last_cross_was_bull = False
        elif dp < 0 and dn > 0:
            bull_crosses += 1
            last_cross_was_bull = True

    if last_cross_was_bull is True:
        wave_number = bull_crosses
    elif last_cross_was_bull is False:
        wave_number = bear_crosses
    else:
        wave_number = bull_crosses if curr_macd > curr_signal else bear_crosses

    # Bullish score (-3 to +3)
    score = 0
    if regime == 1: score += 1
    if macd_above: score += 1
    if hist_positive: score += 1
    if regime == -1: score -= 1
    if not macd_above: score -= 1
    if not hist_positive: score -= 1

    return {
        'close': closes[-1],
        'regime': regime,
        'macd': curr_macd,
        'signal': curr_signal,
        'histogram': curr_diff,
        'velocity': velocity,
        'hist_rate': hist_rate,
        'macd_above': macd_above,
        'hist_positive': hist_positive,
        'crossover_age': crossover_age,
        'crossover_type': crossover_type,
        'wave_number': wave_number,
        'bull_crosses': bull_crosses,
        'bear_crosses': bear_crosses,
        'bullish_score': score,
    }


def compute_atr(highs: list, lows: list, closes: list, period=14) -> float:
    """Compute ATR from OHLC lists."""
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        high = highs[i] if i < len(highs) else closes[i]
        low = lows[i] if i < len(lows) else closes[i]
        prev_close = closes[i-1]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    return sum(trs[-period:]) / period if len(trs) >= period else None


# ═══════════════════════════════════════════════════════════════════════════════
#  STRATEGY DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class WaveStrategy:
    """One strategy configuration to backtest."""
    name: str
    entry_trigger: str          # '15m_only','1h_only','4h_only','15m+1h','15m+4h','1h+4h','all_three'
    wave_min: int              # minimum wave number to enter (1,2,3,4)
    velocity_pattern: str       # 'any','stall_then_flip','increasing','decreasing','vel_pos','vel_neg'
    velocity_thresh: float     # threshold for vel_pos/vel_neg patterns
    crossover_fresh: str        # 'FRESH','STALE','ANY' — freshness requirement
    exit_rule: str             # 'wave4','vel_flip','trailing','wave4_or_vel','trailing_or_vel'
    stop_loss_pct: float       # hard stop loss % (0 = no SL)
    take_profit_rr: float      # TP as RR multiple (0 = no TP)
    guard: str                 # 'none','extended_block','regime_required','no_double','chop_cooldown','triple_confirm','all_guards'
    # Internal only
    _hash: str = field(default='', repr=False)

    def __post_init__(self):
        # Encode strategy as short hash for DB storage
        key = f"{self.name}|{self.entry_trigger}|{self.wave_min}|{self.velocity_pattern}|{self.velocity_thresh}|{self.crossover_fresh}|{self.exit_rule}|{self.stop_loss_pct}|{self.take_profit_rr}|{self.guard}"
        self._hash = hashlib.md5(key.encode()).hexdigest()[:12]


def generate_all_strategies() -> list:
    """Generate exhaustive strategy grid."""
    strategies = []
    entry_triggers = ['15m_only','1h_only','4h_only','15m+1h','15m+4h','1h+4h','all_three']
    wave_mins = [1, 2, 3, 4]
    vel_patterns = ['any','stall_then_flip','increasing','decreasing','vel_pos','vel_neg']
    vel_threshes = [0.05, 0.10, 0.15, 0.25]
    crossover_fresh_opts = ['FRESH','STALE','ANY']
    exit_rules = ['wave4','vel_flip','trailing','wave4_or_vel','trailing_or_vel','wave4_or_sl']
    sl_pcts = [0.0, 0.01, 0.015, 0.02, 0.025]
    tp_rrs = [0.0, 1.5, 2.0, 3.0]  # 0 = no TP
    guards = ['none','extended_block','regime_required','no_double','chop_cooldown','triple_confirm','all_guards']

    # For coarse grid: reduce combinations
    for et in entry_triggers:
        for wm in wave_mins:
            for vp in vel_patterns:
                for vt in vel_threshes:
                    for cf in crossover_fresh_opts:
                        for er in exit_rules:
                            for sl in sl_pcts:
                                for tp in tp_rrs:
                                    for gd in guards:
                                        name = f"{et}_w{wm}_{vp}{int(vt*100)}_cf{cf}_{er}_sl{int(sl*1000)}_tp{int(tp)}_gd{gd}"
                                        strategies.append(WaveStrategy(
                                            name=name,
                                            entry_trigger=et,
                                            wave_min=wm,
                                            velocity_pattern=vp,
                                            velocity_thresh=vt,
                                            crossover_fresh=cf,
                                            exit_rule=er,
                                            stop_loss_pct=sl,
                                            take_profit_rr=tp,
                                            guard=gd,
                                        ))
    return strategies


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY / EXIT CONDITION CHECKERS
# ═══════════════════════════════════════════════════════════════════════════════

def check_entry(s: dict, direction: str, strat: WaveStrategy,
                prev_vel: float, prev_hist_rate: float, prev_regime: int) -> bool:
    """
    Check if entry condition is met for given state s and direction.
    s = current macd state dict
    prev_vel = velocity from previous candle
    Returns True if should enter.
    """
    wave = s['wave_number']
    vel = s['velocity']
    regime = s['regime']
    crossover_age = s['crossover_age']
    hist_rate = s['hist_rate']

    # Wave filter
    if wave < strat.wave_min:
        return False

    # Crossover freshness filter
    if strat.crossover_fresh == 'FRESH' and crossover_age > 2:
        return False
    if strat.crossover_fresh == 'STALE' and crossover_age <= 2:
        return False  # want stale only

    # Velocity pattern filter
    if strat.velocity_pattern == 'stall_then_flip':
        # stall: |prev_vel| < 0.03, then flip to opposite sign
        if direction == 'LONG':
            ok = abs(prev_vel) < 0.03 and vel > 0.05
        else:  # SHORT
            ok = abs(prev_vel) < 0.03 and vel < -0.05
        if not ok:
            return False
    elif strat.velocity_pattern == 'increasing':
        if vel <= prev_vel:
            return False
        if vel < strat.velocity_thresh:
            return False
    elif strat.velocity_pattern == 'decreasing':
        if vel >= prev_vel:
            return False
        if vel > -strat.velocity_thresh:
            return False
    elif strat.velocity_pattern == 'vel_pos':
        if vel < strat.velocity_thresh:
            return False
    elif strat.velocity_pattern == 'vel_neg':
        if vel > -strat.velocity_thresh:
            return False
    elif strat.velocity_pattern == 'any':
        pass

    # Triple confirm guard
    if strat.guard in ('triple_confirm', 'all_guards'):
        # Reverse requires vel + hist_rate + (wave>=4 OR regime flip)
        if direction == 'LONG':
            if not (hist_rate > 0 and (wave >= 4 or regime == 1)):
                return False
        else:
            if not (hist_rate < 0 and (wave >= 4 or regime == -1)):
                return False

    # Regime required for reverse guard
    if strat.guard in ('regime_required', 'all_guards'):
        # For SHORT: regime must not be BULL (want BEAR or NEUTRAL)
        # For LONG: regime must not be BEAR
        if direction == 'SHORT' and regime == 1:
            return False
        if direction == 'LONG' and regime == -1:
            return False

    return True


def check_exit(position: dict, s: dict, strat: WaveStrategy,
               prev_vel: float, trailing_stop_pct: float, entry_price: float,
               highest_since_entry: float, lowest_since_entry: float) -> tuple:
    """
    Check exit condition. Returns (should_exit: bool, reason: str).
    position = {'direction': 'LONG'/'SHORT', 'entry_price': float, 'atr': float, ...}
    """
    direction = position['direction']
    vel = s['velocity']
    wave = s['wave_number']
    hist_rate = s['hist_rate']
    regime = s['regime']
    current_price = s['close']
    prev_vel = prev_vel

    # ── Hard stop loss ───────────────────────────────────────────────────────
    if strat.stop_loss_pct > 0:
        sl_dist = entry_price * strat.stop_loss_pct
        if direction == 'LONG' and current_price < entry_price - sl_dist:
            return True, 'stop_loss'
        if direction == 'SHORT' and current_price > entry_price + sl_dist:
            return True, 'stop_loss'

    # ── Take profit ─────────────────────────────────────────────────────────
    if strat.take_profit_rr > 0 and strat.stop_loss_pct > 0:
        sl_dist = entry_price * strat.stop_loss_pct
        tp_dist = sl_dist * strat.take_profit_rr
        if direction == 'LONG' and current_price >= entry_price + tp_dist:
            return True, 'take_profit'
        if direction == 'SHORT' and current_price <= entry_price - tp_dist:
            return True, 'take_profit'

    # ── Trailing stop ───────────────────────────────────────────────────────
    if strat.exit_rule in ('trailing', 'trailing_or_vel'):
        trail_pct = trailing_stop_pct
        if direction == 'LONG' and highest_since_entry > 0:
            trail_price = highest_since_entry * (1 - trail_pct)
            if current_price < trail_price:
                return True, 'trailing_stop'
        if direction == 'SHORT' and lowest_since_entry > 0:
            trail_price = lowest_since_entry * (1 + trail_pct)
            if current_price > trail_price:
                return True, 'trailing_stop'

    # ── Wave 4 exit ────────────────────────────────────────────────────────
    if strat.exit_rule in ('wave4', 'wave4_or_vel', 'wave4_or_sl'):
        if wave >= 4:
            return True, 'wave_exhaustion'

    # ── Velocity flip exit ──────────────────────────────────────────────────
    if strat.exit_rule in ('vel_flip', 'wave4_or_vel', 'trailing_or_vel'):
        if direction == 'LONG' and vel < 0:
            return True, 'velocity_reversal'
        if direction == 'SHORT' and vel > 0:
            return True, 'velocity_reversal'

    return False, None


def check_guard_block(s: dict, strat: WaveStrategy, guard_state: dict) -> tuple:
    """
    Check if any failure-mode guard blocks a reversal entry.
    Returns (blocked: bool, reason: str).
    """
    vel = s['velocity']
    wave = s['wave_number']
    regime = s['regime']
    hist_rate = s['hist_rate']
    prev_vel = guard_state.get('prev_vel', 0)
    consec_losses = guard_state.get('consec_losses', 0)
    cooldown_remaining = guard_state.get('cooldown_remaining', 0)
    last_was_reverse = guard_state.get('last_was_reverse', False)
    last_vel_confirmed = guard_state.get('last_vel_confirmed', None)

    # Chop cooldown
    if cooldown_remaining > 0:
        return True, 'chop_cooldown'

    # Extended wave block
    if strat.guard in ('extended_block', 'all_guards'):
        if wave >= 5 and abs(vel) > 0.15:
            return True, 'extended_wave'

    # No double-reverse guard
    if strat.guard in ('no_double', 'all_guards'):
        if last_was_reverse and last_vel_confirmed is not None:
            # If last reversal failed (vel did NOT confirm), don't reverse again yet
            if last_vel_confirmed == False:
                return True, 'no_double_reverse'

    return False, None


# ═══════════════════════════════════════════════════════════════════════════════
#  CORE BACKTEST LOOP
# ═══════════════════════════════════════════════════════════════════════════════

def run_backtest(token: str, tf: str, strat: WaveStrategy,
                 prices_db=CANDLES_DB) -> dict:
    """
    Run backtest for one token/timeframe/strategy.
    Returns metrics dict.
    """
    table = f'candles_{tf}'
    conn = sqlite3.connect(prices_db)
    c = conn.cursor()
    c.execute(f"SELECT ts, open, high, low, close FROM {table} WHERE token=? ORDER BY ts ASC",
              (token,))
    rows = c.fetchall()
    conn.close()

    if len(rows) < 100:
        return None

    closes = [r[4] for r in rows]
    highs = [r[2] for r in rows]
    lows = [r[3] for r in rows]

    # ── Precompute MACD states for all candles ──────────────────────────────
    states = []
    for i in range(50, len(closes)):
        s = compute_macd_state(closes[:i+1])
        if s:
            s['idx'] = i
            states.append(s)

    if len(states) < 50:
        return None

    # ── Simulation ─────────────────────────────────────────────────────────
    position = None       # None or {'direction': 'LONG'/'SHORT', 'entry_idx': int, 'entry_price': float, 'atr': float}
    trades = []           # list of trade result dicts
    guard_state = {'prev_vel': 0, 'consec_losses': 0, 'cooldown_remaining': 0,
                   'last_was_reverse': False, 'last_vel_confirmed': None}
    equity = 1.0
    peak_equity = 1.0

    MAX_HOLD = 120  # candles max hold

    trailing_pct = 0.015  # 1.5% trailing stop

    for i, s in enumerate(states[1:], start=1):
        prev_s = states[i-1] if i > 0 else s
        prev_vel = prev_s['velocity']
        prev_hist_rate = prev_s['hist_rate']
        prev_regime = prev_s['regime']

        current_price = s['close']

        # ── In position ──────────────────────────────────────────────────────
        if position:
            entry_price = position['entry_price']
            direction = position['direction']

            # Track high/low since entry
            if direction == 'LONG':
                highest = max(position.get('highest_since_entry', entry_price), current_price)
                lowest = position.get('lowest_since_entry', entry_price)
            else:
                lowest = min(position.get('lowest_since_entry', entry_price), current_price)
                highest = position.get('highest_since_entry', entry_price)

            position['highest_since_entry'] = highest
            position['lowest_since_entry'] = lowest

            # Compute PnL
            if direction == 'LONG':
                pnl_pct = (current_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - current_price) / entry_price

            # Check exit
            should_exit, exit_reason = check_exit(
                position, s, strat,
                prev_vel=prev_vel,
                trailing_stop_pct=trailing_pct,
                entry_price=entry_price,
                highest_since_entry=highest,
                lowest_since_entry=lowest,
            )

            hold_candles = s['idx'] - position['entry_idx']

            if should_exit or hold_candles >= MAX_HOLD:
                if not should_exit:
                    exit_reason = 'max_hold'
                exit_was_reverse = (exit_reason == 'velocity_reversal')

                pnl_pct_final = pnl_pct if should_exit else pnl_pct
                equity *= (1 + pnl_pct_final)
                peak_equity = max(peak_equity, equity)
                drawdown = (peak_equity - equity) / peak_equity

                trades.append({
                    'direction': direction,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'pnl_pct': pnl_pct_final,
                    'exit_reason': exit_reason,
                    'wave_at_entry': position.get('wave_at_entry', 0),
                    'vel_at_entry': position.get('vel_at_entry', 0),
                    'wave_at_exit': s['wave_number'],
                    'vel_at_exit': s['velocity'],
                    'hold_candles': hold_candles,
                    'was_reverse': exit_was_reverse,
                    'drawdown_at_exit': drawdown,
                })

                # Guard state update
                guard_state['last_was_reverse'] = exit_was_reverse
                guard_state['last_vel_confirmed'] = (exit_reason == 'velocity_reversal')

                if pnl_pct_final < 0:
                    guard_state['consec_losses'] += 1
                else:
                    guard_state['consec_losses'] = 0

                if guard_state['consec_losses'] >= 2 and strat.guard in ('chop_cooldown', 'all_guards'):
                    guard_state['cooldown_remaining'] = 5

                if guard_state['cooldown_remaining'] > 0:
                    guard_state['cooldown_remaining'] -= 1

                position = None

        # ── Not in position — check for entry ────────────────────────────────
        else:
            # Check guard blocks
            blocked, block_reason = check_guard_block(s, strat, guard_state)
            if blocked:
                guard_state['prev_vel'] = s['velocity']
                continue

            # Decrement cooldown
            if guard_state['cooldown_remaining'] > 0:
                guard_state['cooldown_remaining'] -= 1

            # Check LONG and SHORT entries
            for direction in ['LONG', 'SHORT']:
                if direction == 'LONG':
                    # Want regime != BEAR for longs
                    if s['regime'] == -1:
                        continue
                    vel_ok = s['velocity'] > 0 or s['velocity'] >= -0.03
                else:
                    # Want regime != BULL for shorts
                    if s['regime'] == 1:
                        continue
                    vel_ok = s['velocity'] < 0 or s['velocity'] <= 0.03

                if not vel_ok:
                    continue

                can_enter = check_entry(s, direction, strat,
                                        prev_vel=prev_vel,
                                        prev_hist_rate=prev_hist_rate,
                                        prev_regime=prev_regime)
                if can_enter:
                    atr = compute_atr(highs[:s['idx']+1], lows[:s['idx']+1], closes[:s['idx']+1], ATR_PERIOD)
                    position = {
                        'direction': direction,
                        'entry_idx': s['idx'],
                        'entry_price': current_price,
                        'atr': atr or 0.02 * current_price,
                        'wave_at_entry': s['wave_number'],
                        'vel_at_entry': s['velocity'],
                        'highest_since_entry': current_price,
                        'lowest_since_entry': current_price,
                    }
                    break  # enter one direction only per candle

            guard_state['prev_vel'] = s['velocity']

    # ── Compute metrics ──────────────────────────────────────────────────────
    if not trades:
        return None

    total = len(trades)
    wins = [t for t in trades if t['pnl_pct'] > 0]
    win_rate = len(wins) / total if total > 0 else 0
    avg_pnl = sum(t['pnl_pct'] for t in trades) / total
    pnl_std = math.sqrt(sum((t['pnl_pct'] - avg_pnl)**2 for t in trades) / total) if total > 1 else 0
    sharpe = (avg_pnl / pnl_std * math.sqrt(252)) if pnl_std > 0 else 0
    max_dd = max((t['drawdown_at_exit'] for t in trades), default=0)

    reversals = [t for t in trades if t['was_reverse']]
    reversal_wr = len([t for t in reversals if t['pnl_pct'] > 0]) / len(reversals) if reversals else 0
    avg_reversal_pnl = sum(t['pnl_pct'] for t in reversals) / len(reversals) if reversals else 0

    longs = [t for t in trades if t['direction'] == 'LONG']
    shorts = [t for t in trades if t['direction'] == 'SHORT']
    longs_won = len([t for t in longs if t['pnl_pct'] > 0])
    shorts_won = len([t for t in shorts if t['pnl_pct'] > 0])

    avg_hold = sum(t['hold_candles'] for t in trades) / total
    avg_wave_entry = sum(t['wave_at_entry'] for t in trades) / total
    avg_vel_entry = sum(t['vel_at_entry'] for t in trades) / total

    exit_reasons = {}
    for t in trades:
        exit_reasons[t['exit_reason']] = exit_reasons.get(t['exit_reason'], 0) + 1

    return {
        'token': token,
        'timeframe': tf,
        'strategy_hash': strat._hash,
        'strategy_name': strat.name,
        'entry_trigger': strat.entry_trigger,
        'wave_min': strat.wave_min,
        'velocity_pattern': strat.velocity_pattern,
        'velocity_thresh': strat.velocity_thresh,
        'crossover_fresh': strat.crossover_fresh,
        'exit_rule': strat.exit_rule,
        'stop_loss_pct': strat.stop_loss_pct,
        'take_profit_rr': strat.take_profit_rr,
        'guard': strat.guard,
        'total_trades': total,
        'win_rate': win_rate,
        'avg_pnl_pct': avg_pnl,
        'sharpe': sharpe,
        'max_drawdown': max_dd,
        'avg_hold_candles': avg_hold,
        'reversal_count': len(reversals),
        'reversal_win_rate': reversal_wr,
        'avg_reversal_pnl': avg_reversal_pnl,
        'longs_won': longs_won,
        'shorts_won': shorts_won,
        'avg_vel_at_entry': avg_vel_entry,
        'avg_wave_at_entry': avg_wave_entry,
        'exit_wave4_pct': exit_reasons.get('wave_exhaustion', 0) / total,
        'exit_vel_flip_pct': exit_reasons.get('velocity_reversal', 0) / total,
        'exit_sl_pct': exit_reasons.get('stop_loss', 0) / total,
        'exit_tp_pct': exit_reasons.get('take_profit', 0) / total,
        'exit_trailing_pct': exit_reasons.get('trailing_stop', 0) / total,
        'exit_max_hold_pct': exit_reasons.get('max_hold', 0) / total,
        'guard_extended_skipped': 0,
        'guard_chop_cooldown': 0,
        'guard_no_double': 0,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

def init_results_db():
    conn = sqlite3.connect(RESULTS_DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS wave_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT,
            timeframe TEXT,
            strategy_hash TEXT,
            strategy_name TEXT,
            entry_trigger TEXT,
            wave_min INTEGER,
            velocity_pattern TEXT,
            velocity_thresh REAL,
            crossover_fresh TEXT,
            exit_rule TEXT,
            stop_loss_pct REAL,
            take_profit_rr REAL,
            guard TEXT,
            total_trades INTEGER,
            win_rate REAL,
            avg_pnl_pct REAL,
            sharpe REAL,
            max_drawdown REAL,
            avg_hold_candles REAL,
            reversal_count INTEGER,
            reversal_win_rate REAL,
            avg_reversal_pnl REAL,
            longs_won INTEGER,
            shorts_won INTEGER,
            avg_vel_at_entry REAL,
            avg_wave_at_entry REAL,
            exit_wave4_pct REAL,
            exit_vel_flip_pct REAL,
            exit_sl_pct REAL,
            exit_tp_pct REAL,
            exit_trailing_pct REAL,
            exit_max_hold_pct REAL,
            guard_extended_skipped INTEGER,
            guard_chop_cooldown INTEGER,
            guard_no_double INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_sharpe ON wave_results(sharpe DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_reversal_wr ON wave_results(reversal_win_rate DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_token_tf ON wave_results(token, timeframe)")
    conn.commit()
    conn.close()


def save_results(results: list):
    if not results:
        return
    conn = sqlite3.connect(RESULTS_DB)
    c = conn.cursor()
    for r in results:
        c.execute("""
            INSERT INTO wave_results (
                token, timeframe, strategy_hash, strategy_name,
                entry_trigger, wave_min, velocity_pattern, velocity_thresh,
                crossover_fresh, exit_rule, stop_loss_pct, take_profit_rr, guard,
                total_trades, win_rate, avg_pnl_pct, sharpe, max_drawdown,
                avg_hold_candles, reversal_count, reversal_win_rate, avg_reversal_pnl,
                longs_won, shorts_won, avg_vel_at_entry, avg_wave_at_entry,
                exit_wave4_pct, exit_vel_flip_pct, exit_sl_pct, exit_tp_pct,
                exit_trailing_pct, exit_max_hold_pct,
                guard_extended_skipped, guard_chop_cooldown, guard_no_double
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            r['token'], r['timeframe'], r['strategy_hash'], r['strategy_name'],
            r['entry_trigger'], r['wave_min'], r['velocity_pattern'], r['velocity_thresh'],
            r['crossover_fresh'], r['exit_rule'], r['stop_loss_pct'], r['take_profit_rr'],
            r['guard'],
            r['total_trades'], r['win_rate'], r['avg_pnl_pct'], r['sharpe'],
            r['max_drawdown'], r['avg_hold_candles'], r['reversal_count'],
            r['reversal_win_rate'], r['avg_reversal_pnl'],
            r['longs_won'], r['shorts_won'], r['avg_vel_at_entry'], r['avg_wave_at_entry'],
            r['exit_wave4_pct'], r['exit_vel_flip_pct'], r['exit_sl_pct'], r['exit_tp_pct'],
            r['exit_trailing_pct'], r['exit_max_hold_pct'],
            r.get('guard_extended_skipped', 0),
            r.get('guard_chop_cooldown', 0),
            r.get('guard_no_double', 0),
        ))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  QUICK VALIDATION TEST (BTC 4H, single strategy)
# ═══════════════════════════════════════════════════════════════════════════════

def quick_btc_validation():
    """Run the core stall_then_flip thesis test on BTC 4H."""
    print("\n" + "="*70)
    print("BTC 4H WAVE RIDER VALIDATION — STALL-THEN-FLIP THESIS")
    print("="*70)

    strat = WaveStrategy(
        name="btc_validation_stall_then_flip",
        entry_trigger='4h_only',
        wave_min=3,
        velocity_pattern='stall_then_flip',
        velocity_thresh=0.05,
        crossover_fresh='ANY',
        exit_rule='wave4_or_vel',
        stop_loss_pct=0.02,
        take_profit_rr=2.0,
        guard='none',
    )

    result = run_backtest('BTC', '4h', strat)

    if result is None:
        print("ERROR: No data returned")
        return

    print(f"\nStrategy: stall_then_flip | wave>=3 | 4h | exit=wave4_or_vel | SL=2% | TP=2RR")
    print(f"\n{'─'*50}")
    print(f"  Total trades:        {result['total_trades']}")
    print(f"  Win rate:            {result['win_rate']:.1%}")
    print(f"  Avg PnL:             {result['avg_pnl_pct']:.3%}")
    print(f"  Sharpe:              {result['sharpe']:.2f}")
    print(f"  Max drawdown:        {result['max_drawdown']:.1%}")
    print(f"  Avg hold (candles):  {result['avg_hold_candles']:.1f}")
    print(f"\n{'─'*50}")
    print(f"  Reversals:           {result['reversal_count']}")
    print(f"  Reversal win rate:   {result['reversal_win_rate']:.1%}")
    print(f"  Avg reversal PnL:    {result['avg_reversal_pnl']:.3%}")
    print(f"\n{'─'*50}")
    print(f"  LONGs won:           {result['longs_won']}")
    print(f"  SHORTs won:          {result['shorts_won']}")
    print(f"  Avg wave at entry:   {result['avg_wave_at_entry']:.1f}")
    print(f"  Avg vel at entry:    {result['avg_vel_at_entry']:+.3f}")
    print(f"\n{'─'*50}")
    print(f"  Exit reasons:")
    print(f"    wave exhaustion:   {result['exit_wave4_pct']:.1%}")
    print(f"    velocity reversal: {result['exit_vel_flip_pct']:.1%}")
    print(f"    stop loss:         {result['exit_sl_pct']:.1%}")
    print(f"    take profit:       {result['exit_tp_pct']:.1%}")
    print(f"    trailing stop:     {result['exit_trailing_pct']:.1%}")
    print(f"    max hold:          {result['exit_max_hold_pct']:.1%}")

    print(f"\n{'='*70}")
    if result['win_rate'] >= 0.50 and result['sharpe'] > 0.5:
        print("✅ THESIS CONFIRMED — positive Sharpe + 50%+ win rate")
    elif result['win_rate'] >= 0.45:
        print("⚠️  MARGINAL — positive but needs guard tuning")
    else:
        print("❌ THESIS WEAK — high loss rate, check failure modes")
    print(f"{'='*70}\n")

    return result


def run_guard_comparison():
    """Run same base strategy with different guards to see which helps."""
    print("\n" + "="*70)
    print("GUARD COMPARISON — BTC 4H")
    print("="*70)

    base = dict(
        entry_trigger='4h_only',
        wave_min=3,
        velocity_pattern='stall_then_flip',
        velocity_thresh=0.05,
        crossover_fresh='ANY',
        exit_rule='wave4_or_vel',
        stop_loss_pct=0.02,
        take_profit_rr=2.0,
    )

    guards_to_test = ['none', 'extended_block', 'regime_required',
                      'no_double', 'chop_cooldown', 'triple_confirm', 'all_guards']

    results = []
    for guard in guards_to_test:
        strat = WaveStrategy(name=f"guard_test_{guard}", guard=guard, **base)
        r = run_backtest('BTC', '4h', strat)
        if r:
            print(f"\n  [{guard:20s}] trades={r['total_trades']:3d}  "
                  f"WR={r['win_rate']:.1%}  "
                  f"Sharpe={r['sharpe']:+.2f}  "
                  f"RevWR={r['reversal_win_rate']:.1%}  "
                  f"RevPnL={r['avg_reversal_pnl']:+.3f}")
            results.append(r)

    if results:
        best = max(results, key=lambda x: x['sharpe'])
        best_guard = next(r['guard'] for r in results if r['sharpe'] == best['sharpe'])
        print(f"\nBest guard: {best_guard} (Sharpe={best['sharpe']:.2f})")

    return results


# ═══════════════════════════════════════════════════════════════════════════════
#  FULL GRID RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

def run_full_grid(tokens, timeframes, save_every=100):
    """Run the full strategy grid."""
    init_results_db()
    strategies = generate_all_strategies()
    total_strats = len(strategies)
    total_runs = total_strats * len(tokens) * len(timeframes)
    print(f"\nFull grid: {total_strats} strategies × {len(tokens)} tokens × {len(timeframes)} TFs = {total_runs:,} runs")
    print(f"Estimated time: {total_runs * 0.01 / 60:.0f}-{total_runs * 0.05 / 60:.0f} min (assuming 10-50ms/run)")

    saved = 0
    start = time.time()

    for tf in timeframes:
        for token in tokens:
            print(f"\n[{token} {tf}] {len(strategies)} strategies...", end='', flush=True)
            count = 0
            batch = []
            for strat in strategies:
                r = run_backtest(token, tf, strat)
                if r:
                    batch.append(r)
                    saved += 1
                count += 1
                if count % 500 == 0:
                    print(f" {count}/{total_strats}...", end='', flush=True)

            if batch:
                save_results(batch)
            elapsed = time.time() - start
            print(f" done ({len(batch)} results, {saved} total saved, {elapsed:.0f}s elapsed)")

    print(f"\nTotal time: {time.time() - start:.0f}s | Results saved to {RESULTS_DB}")


def show_top_results(limit=20):
    """Print top strategies by sharpe."""
    conn = sqlite3.connect(RESULTS_DB)
    c = conn.cursor()
    c.execute("""
        SELECT token, timeframe, entry_trigger, wave_min, velocity_pattern,
               velocity_thresh, exit_rule, stop_loss_pct, guard,
               total_trades, win_rate, sharpe, max_drawdown,
               reversal_count, reversal_win_rate, avg_reversal_pnl,
               longs_won, shorts_won, avg_wave_at_entry, avg_vel_at_entry
        FROM wave_results
        WHERE total_trades >= 5
        ORDER BY sharpe DESC
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()

    print(f"\n{'─'*120}")
    print(f"{'TOKEN':8s} {'TF':4s} {'ENTRY':12s} {'W':1s} {'VEL_PAT':16s} {'VEL':5s} {'EXIT':16s} {'SL':5s} {'GUARD':14s} "
          f"{'N':3s} {'WR':6s} {'SHARPE':7s} {'MAXDD':7s} {'REV':3s} {'REV_WR':7s} {'REV_PNL':8s} {'L_W':4s} {'S_W':4s} {'W_ENT':6s} {'V_ENT':7s}")
    print(f"{'─'*120}")
    for r in rows:
        print(f"{r[0]:8s} {r[1]:4s} {r[2]:12s} {r[3]}  {r[4]:16s} {r[5]:5.2f} {r[6]:16s} {r[7]:5.3f} {r[8]:14s} "
              f"{r[9]:3d} {r[10]:6.1%} {r[11]:+7.2f} {r[12]:7.1%} {r[13]:3d} {r[14]:7.1%} {r[15]:+8.3f} {r[16]:4d} {r[17]:4d} {r[18]:6.1f} {r[19]:+7.3f}")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Wave Rider Backtest Engine')
    parser.add_argument('--tokens', nargs='+', default=['BTC', 'ETH', 'SOL', 'LINK', 'AAVE'])
    parser.add_argument('--timeframes', nargs='+', default=['4h', '1h'])
    parser.add_argument('--full-grid', action='store_true')
    parser.add_argument('--guard-comparison', action='store_true')
    parser.add_argument('--top', type=int, default=0, help='Show top N results')
    parser.add_argument('--quick', action='store_true', help='Quick BTC 4H validation')
    args = parser.parse_args()

    if args.quick:
        quick_btc_validation()
    elif args.guard_comparison:
        run_guard_comparison()
    elif args.top > 0:
        init_results_db()
        show_top_results(args.top)
    elif args.full_grid:
        run_full_grid(args.tokens, args.timeframes)
    else:
        # Default: quick validation + guard comparison
        init_results_db()
        quick_btc_validation()
        run_guard_comparison()
        print("\nTo run full grid: python3 wave_backtest.py --full-grid --tokens BTC ETH SOL --timeframes 4h 1h")
        print("To see results:   python3 wave_backtest.py --top 30")
