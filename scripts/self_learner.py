#!/usr/bin/env python3
"""Self-Learning System — automatically detect signal decay and adjust parameters.

Runs daily via systemd timer. Analyzes signal_outcomes, identifies underperforming
signals, adjusts parameters using scientific method (one variable at a time).

Flow:
1. Analyze performance per signal type (rolling 30 trades)
2. Check goals (WR > 40%, PnL > 0)
3. If failing: identify weakest parameter
4. Adjust ONE parameter (5% step)
5. Log change (before/after values)
"""
import json
import os
import re
import sys
import time
import fcntl
import sqlite3
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from paths import RUNTIME_DB

# ── Config ──────────────────────────────────────────────────────────────
LOG_FILE = '/root/.hermes/automation/self_learning_log.json'
HERMES_CONSTANTS = '/root/.hermes/scripts/hermes_constants.py'
LOCK_FILE = '/tmp/self-learner.lock'

# Import constants from hermes_constants (single source of truth)
try:
    from hermes_constants import (
        SELF_LEARNER_WR_THRESHOLD as MIN_WR,
        SELF_LEARNER_WR_TARGET as GOAL_WR,
        SELF_LEARNER_MAX_ADJUSTMENTS as MAX_ADJUSTMENTS_PER_DAY,
        SELF_LEARNER_MIN_BETWEEN as MIN_TRADES_BETWEEN,
        CEO_PROTECTED_FLAGS,
    )
except ImportError:
    MIN_WR = 0.30
    GOAL_WR = 0.40
    MAX_ADJUSTMENTS_PER_DAY = 3
    MIN_TRADES_BETWEEN = 15
    CEO_PROTECTED_FLAGS = set()

CRITICAL_WR = 0.25  # Below this = emergency disable
GOAL_PROGRESS_FILE = '/root/.hermes/data/goal_progress.json'

# ── Kill threshold config ──────────────────────────────────────────────
KILL_PNL_50 = -2.0    # 50-trade PnL below this → disable
KILL_MAX_CONSEC = 10  # consecutive losses at or above this → disable
KILL_MIN_TRADES = 50  # need at least this many trades to evaluate

# ── Combo weight tuning ────────────────────────────────────────────────
COMBO_WEIGHTS_FILE = '/root/.hermes/data/combo_weights.json'
COMBO_MIN_TRADES = 5        # minimum trades to adjust a combo
COMBO_WINDOW_DAYS = 7       # lookback window
COMBO_BOOST_WR = 0.60       # WR above this → boost
COMBO_SUPPRESS_WR = 0.40    # WR below this → suppress
COMBO_SUPPRESS_PNL = -0.10  # avg PnL below this with 10+ trades → suppress
COMBO_BOOST_MAX = 1.3
COMBO_SUPPRESS_MIN = 0.5

# Parameter config: name -> {min, max, step, tighten_dir}
# Only params that exist in hermes_constants.py
PARAM_CONFIG = {
    'TREND_FILTER_NEUTRAL_PCT': {'min': 0.20, 'max': 0.60, 'step': 0.05, 'tighten': 'down'},
    'SPEED_MIN_THRESHOLD': {'min': 20, 'max': 40, 'step': 0.05, 'tighten': 'up'},
    'MACRO_HIGH_VOL_THRESHOLD': {'min': 0.03, 'max': 0.08, 'step': 0.05, 'tighten': 'down'},
    'MACRO_LOW_WR_THRESHOLD': {'min': 20, 'max': 40, 'step': 0.05, 'tighten': 'up'},
}


def _log(msg):
    print(f"[self-learner] {msg}", flush=True)


def _load_log():
    """Load self-learning log."""
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {'changes': [], 'daily_count': 0, 'last_reset': 0}


def _save_log(data):
    """Save self-learning log atomically."""
    try:
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(LOG_FILE), suffix='.tmp')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, LOG_FILE)
        except Exception:
            os.unlink(tmp)
            raise
    except Exception as e:
        _log(f"Error saving log: {e}")


def _get_recent_trades(signal_type, limit=30):
    """Get recent trades for a signal type."""
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT token, direction, is_win, pnl_pct, pnl_usdt, created_at
            FROM signal_outcomes
            WHERE signal_type LIKE ? AND trade_id IS NOT NULL
            ORDER BY created_at DESC
            LIMIT ?
        """, (f'%{signal_type}%', limit))
        rows = cur.fetchall()
        conn.close()
        return [{'token': r[0], 'direction': r[1], 'win': r[2], 
                 'pnl_pct': r[3], 'pnl_usdt': r[4], 'created_at': r[5]} 
                for r in rows]
    except Exception:
        return []


def _calculate_wr(trades):
    """Calculate win rate from trades list."""
    if not trades:
        return 0
    wins = sum(1 for t in trades if t['win'] == 1)
    return wins / len(trades)


def _calculate_pnl(trades):
    """Calculate total PnL from trades list."""
    return sum(t['pnl_usdt'] or 0 for t in trades)


def _detect_decay(trades):
    """Detect if signal is decaying (WR dropping over time)."""
    if len(trades) < 10:
        return False
    half = len(trades) // 2
    first_wr = _calculate_wr(trades[:half])
    second_wr = _calculate_wr(trades[half:])
    return first_wr - second_wr > 0.15


def _max_consecutive_losses(trades):
    """Compute max consecutive losses in a trades list."""
    max_streak = 0
    current = 0
    for t in trades:
        if t['win'] == 0:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def _get_all_active_signal_types():
    """Get distinct base signal types from recent signal_outcomes.
    
    Filters out combo types (contains ',' or '+') to return only base signals.
    """
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT signal_type FROM signal_outcomes
            WHERE trade_id IS NOT NULL
            AND created_at > datetime('now', '-30 days')
        """)
        rows = cur.fetchall()
        conn.close()
        # Filter to base signal types only (no combos)
        seen = set()
        result = []
        for r in rows:
            st = r[0]
            # Skip combos (contain comma or plus as separator)
            if ',' in st:
                continue
            # Normalize to base: strip +/- direction suffixes
            base = st.rstrip('+-')
            if base not in seen:
                seen.add(base)
                result.append(base)
        return result
    except Exception:
        return []


def _get_trades_exact(signal_type, limit=50):
    """Get recent trades for exact signal_type match (no LIKE)."""
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT token, direction, is_win, pnl_pct, pnl_usdt, created_at
            FROM signal_outcomes
            WHERE signal_type = ? AND trade_id IS NOT NULL
            ORDER BY created_at DESC
            LIMIT ?
        """, (signal_type, limit))
        rows = cur.fetchall()
        conn.close()
        return [{'token': r[0], 'direction': r[1], 'win': r[2],
                 'pnl_pct': r[3], 'pnl_usdt': r[4], 'created_at': r[5]}
                for r in rows]
    except Exception:
        return []


def _kill_underperformers():
    """Auto-disable signals with negative 50-trade PnL or 10+ consecutive losses.
    
    Respects CEO_PROTECTED_FLAGS — won't touch protected signals.
    Returns number of signals disabled.
    """
    kills = 0
    signal_types = _get_all_active_signal_types()
    
    for signal_type in signal_types:
        # Skip already-disabled signals
        if _is_signal_disabled(signal_type):
            continue
        
        # Skip CEO-protected signals
        norm = signal_type.upper()
        norm = re.sub(r'\+$', '_PLUS', norm)
        norm = re.sub(r'-$', '_MINUS', norm)
        norm = norm.replace('-', '_')
        flag_name = f'{norm}_ENABLED'
        if flag_name in CEO_PROTECTED_FLAGS:
            _log(f"  KILL CHECK {signal_type}: PROTECTED, skipping")
            continue
        
        trades = _get_trades_exact(signal_type, limit=KILL_MIN_TRADES)
        if len(trades) < KILL_MIN_TRADES:
            continue
        
        pnl = _calculate_pnl(trades)
        max_consec = _max_consecutive_losses(trades)
        
        kill_reason = None
        if pnl < KILL_PNL_50:
            kill_reason = f"50T PnL=${pnl:+.2f} < {KILL_PNL_50}"
        elif max_consec >= KILL_MAX_CONSEC:
            kill_reason = f"{max_consec} consecutive losses >= {KILL_MAX_CONSEC}"
        
        if kill_reason:
            _log(f"  KILL {signal_type}: {kill_reason}")
            _disable_signal(signal_type)
            kills += 1
    
    return kills


def _disable_signal(signal_type):
    """Disable a signal by setting its _ENABLED flag to False in hermes_constants.py."""
    try:
        with open(HERMES_CONSTANTS) as f:
            content = f.read()
        
        # Normalize: convert trailing +/- FIRST, then hyphens to underscores
        norm = signal_type.upper()
        norm = re.sub(r'\+$', '_PLUS', norm)
        norm = re.sub(r'-$', '_MINUS', norm)
        norm = norm.replace('-', '_')
        # Try matching e.g. BB_BOUNCE_PLUS from bb_bounce+
        candidates = [f'{norm}_ENABLED']
        if not re.search(rf'^{re.escape(norm)}_ENABLED\s*=', content, re.MULTILINE):
            # Try without trailing direction variants
            base = re.sub(r'_(PLUS|MINUS|LONG|SHORT)$', '', norm)
            candidates = [f'{base}_ENABLED']
        
        for flag in candidates:
            pattern = rf'^({re.escape(flag)}\s*=\s*)(True|False)'
            match = re.search(pattern, content, re.MULTILINE)
            if match and match.group(2) == 'True':
                content = content[:match.start(1)] + f'{flag} = False' + content[match.end(2):]
                fd, tmp = tempfile.mkstemp(dir=os.path.dirname(HERMES_CONSTANTS), suffix='.tmp')
                try:
                    with os.fdopen(fd, 'w') as f:
                        f.write(content)
                    os.replace(tmp, HERMES_CONSTANTS)
                    _log(f"  DISABLED {flag}")
                except Exception:
                    os.unlink(tmp)
                    raise
                return True
        
        _log(f"  {signal_type}: no _ENABLED flag found to disable")
        return False
    except Exception as e:
        _log(f"Error disabling {signal_type}: {e}")
        return False


def _get_current_value(param_name):
    """Get current parameter value from hermes_constants.py."""
    try:
        with open(HERMES_CONSTANTS) as f:
            for line in f:
                if line.strip().startswith(f'{param_name} ='):
                    parts = line.split('=')
                    if len(parts) >= 2:
                        val_str = parts[1].split('#')[0].strip()
                        return float(val_str)
        return None
    except Exception:
        return None


def _set_param_value(param_name, new_value):
    """Update parameter value in hermes_constants.py atomically."""
    try:
        with open(HERMES_CONSTANTS) as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            if line.strip().startswith(f'{param_name} ='):
                parts = line.split('#')
                comment = f' # {parts[1].strip()}' if len(parts) > 1 else ''
                lines[i] = f'{param_name} = {new_value}{comment}\n'
                break
        
        # Atomic write
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(HERMES_CONSTANTS), suffix='.tmp')
        try:
            with os.fdopen(fd, 'w') as f:
                f.writelines(lines)
            os.replace(tmp, HERMES_CONSTANTS)
        except Exception:
            os.unlink(tmp)
            raise
        
        return True
    except Exception as e:
        _log(f"Error updating {param_name}: {e}")
        return False


def _find_weakest_param(signal_type):
    """Find the parameter most correlated with poor performance."""
    param_map = {
        'bb_bounce': ['TREND_FILTER_NEUTRAL_PCT', 'SPEED_MIN_THRESHOLD'],
        'pattern_wolf': ['SPEED_MIN_THRESHOLD'],
        'accel_300': ['SPEED_MIN_THRESHOLD'],
        'tl_break': ['TREND_FILTER_NEUTRAL_PCT', 'SPEED_MIN_THRESHOLD'],
    }
    params = param_map.get(signal_type, ['SPEED_MIN_THRESHOLD', 'TREND_FILTER_NEUTRAL_PCT'])
    return params[0] if params else None


def _adjust_param(param_name, direction):
    """Adjust parameter by 5% in given direction. Respects tighten direction."""
    config = PARAM_CONFIG.get(param_name)
    if not config:
        return None
    
    current = _get_current_value(param_name)
    if current is None:
        return None
    
    step = config['step']
    min_val = config['min']
    max_val = config['max']
    tighten_dir = config.get('tighten', 'up')
    
    # Apply direction based on tighten config
    if direction == 'tighten':
        if tighten_dir == 'down':
            new_value = current * (1 - step)  # Tighten = decrease
        else:
            new_value = current * (1 + step)  # Tighten = increase
    else:  # loosen
        if tighten_dir == 'down':
            new_value = current * (1 + step)  # Loosen = increase
        else:
            new_value = current * (1 - step)  # Loosen = decrease
    
    new_value = max(min_val, min(max_val, new_value))
    new_value = round(new_value, 4)
    
    if new_value == current:
        return None
    
    return new_value


def _log_change(signal_type, param, old_value, new_value, reason, wr_before):
    """Log parameter change to file."""
    log_data = _load_log()
    
    change = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'signal_type': signal_type,
        'parameter': param,
        'old_value': old_value,
        'new_value': new_value,
        'reason': reason,
        'wr_before': wr_before,
    }
    
    log_data['changes'].append(change)
    log_data['daily_count'] = log_data.get('daily_count', 0) + 1
    _save_log(log_data)


def _check_daily_limit():
    """Check if we've hit daily adjustment limit."""
    log_data = _load_log()
    now = datetime.now(timezone.utc)
    last_reset = log_data.get('last_reset', 0)
    
    if last_reset == 0 or now.date() != datetime.fromtimestamp(last_reset, tz=timezone.utc).date():
        log_data['daily_count'] = 0
        log_data['last_reset'] = now.timestamp()
        _save_log(log_data)
    
    return log_data.get('daily_count', 0) >= MAX_ADJUSTMENTS_PER_DAY


def _write_goal_progress():
    """Write current performance metrics + targets to goal_progress.json.
    
    CEO and self_learner read this file to understand current state.
    """
    conn = None
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        
        # Last 30 days of closed trades
        cur.execute("""
            SELECT is_win, pnl_usdt, pnl_pct
            FROM signal_outcomes
            WHERE trade_id IS NOT NULL
            AND created_at > datetime('now', '-30 days')
        """)
        trades_30d = [{'win': r[0], 'pnl_usdt': r[1], 'pnl_pct': r[2]} for r in cur.fetchall()]
        
        # Last 7 days
        cur.execute("""
            SELECT is_win, pnl_usdt, pnl_pct
            FROM signal_outcomes
            WHERE trade_id IS NOT NULL
            AND created_at > datetime('now', '-7 days')
        """)
        trades_7d = [{'win': r[0], 'pnl_usdt': r[1], 'pnl_pct': r[2]} for r in cur.fetchall()]
        
        # Last 2 days for trend
        cur.execute("""
            SELECT is_win, pnl_usdt
            FROM signal_outcomes
            WHERE trade_id IS NOT NULL
            AND created_at > datetime('now', '-2 days')
        """)
        trades_2d = [{'win': r[0], 'pnl_usdt': r[1]} for r in cur.fetchall()]
        
        conn.close()
        conn = None
        
        # Compute metrics
        wr_30d = _calculate_wr(trades_30d) if trades_30d else 0
        pnl_30d = _calculate_pnl(trades_30d) if trades_30d else 0
        pnl_7d = _calculate_pnl(trades_7d) if trades_7d else 0
        sharpe_30d = None
        if trades_30d and len(trades_30d) >= 10:
            returns = [t['pnl_pct'] for t in trades_30d if t['pnl_pct'] is not None]
            if returns:
                mean_r = sum(returns) / len(returns)
                std_r = (sum((r - mean_r)**2 for r in returns) / len(returns)) ** 0.5
                sharpe_30d = round((mean_r / std_r), 3) if std_r > 0 else 0
        
        # Consecutive losses (from most recent trades)
        recent_30 = _get_all_trades_recent(limit=100)
        consec = _max_consecutive_losses(recent_30[:30]) if recent_30 else 0
        
        # Trend deltas
        wr_2d = _calculate_wr(trades_2d) if trades_2d else 0
        wr_7d = _calculate_wr(trades_7d) if trades_7d else 0
        
        data = {
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'targets': {
                'win_rate': GOAL_WR,
                'daily_pnl': 0.05,
                'min_sharpe_30d': 1.0,
            },
            'current': {
                'win_rate_30d': round(wr_30d, 4),
                'win_rate_7d': round(wr_7d, 4),
                'daily_pnl_7d': round(pnl_7d / 7, 4) if pnl_7d else 0,
                'pnl_30d': round(pnl_30d, 4),
                'sharpe_30d': sharpe_30d,
                'total_trades_30d': len(trades_30d),
                'consecutive_losses': consec,
            },
            'trend': {
                'win_rate_delta_2d': round(wr_2d - wr_7d, 4) if trades_2d and trades_7d else None,
            },
        }
        
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(GOAL_PROGRESS_FILE), suffix='.tmp')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, GOAL_PROGRESS_FILE)
            _log(f"Wrote {GOAL_PROGRESS_FILE} — WR30d={wr_30d:.1%} PnL30d=${pnl_30d:+.2f}")
        except Exception:
            os.unlink(tmp)
            raise
    except Exception as e:
        _log(f"Error writing goal progress: {e}")
    finally:
        if conn:
            conn.close()


def _get_all_trades_recent(limit=100):
    """Get most recent trades across all signals."""
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT is_win, pnl_usdt, pnl_pct
            FROM signal_outcomes
            WHERE trade_id IS NOT NULL
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        return [{'win': r[0], 'pnl_usdt': r[1], 'pnl_pct': r[2]} for r in rows]
    except Exception:
        return []


def analyze_and_adjust():
    """Main analysis and adjustment cycle."""
    log_data = _load_log()
    
    if _check_daily_limit():
        _log("Daily adjustment limit reached")
        return 0
    
    adjustments = 0
    signal_types = ['bb_bounce', 'pattern_wolf', 'accel_300', 'tl_break']
    
    for signal_type in signal_types:
        trades = _get_recent_trades(signal_type, limit=30)
        
        if len(trades) < MIN_TRADES_BETWEEN:
            _log(f"  {signal_type}: {len(trades)} trades (need {MIN_TRADES_BETWEEN})")
            continue
        
        wr = _calculate_wr(trades)
        pnl = _calculate_pnl(trades)
        decay = _detect_decay(trades)
        
        _log(f"  {signal_type}: WR={wr:.1%} PnL=${pnl:+.2f} trades={len(trades)} decay={decay}")
        
        if wr < CRITICAL_WR:
            _log(f"  {signal_type}: CRITICAL — WR {wr:.1%} < {CRITICAL_WR:.0%}")
            continue
        
        if wr <= MIN_WR or decay:
            param = _find_weakest_param(signal_type)
            if param:
                new_value = _adjust_param(param, direction='tighten')
                if new_value:
                    old_value = _get_current_value(param)
                    if _set_param_value(param, new_value):
                        _log_change(signal_type, param, old_value, new_value, 
                                   f'WR={wr:.1%}, decay={decay}', wr)
                        _log(f"  ADJUSTED: {param} {old_value} → {new_value}")
                        adjustments += 1
        
        elif wr > 0.60 and len(trades) >= 20:
            param = _find_weakest_param(signal_type)
            if param:
                new_value = _adjust_param(param, direction='loosen')
                if new_value:
                    old_value = _get_current_value(param)
                    if _set_param_value(param, new_value):
                        _log_change(signal_type, param, old_value, new_value,
                                   f'WR={wr:.1%} (loosening)', wr)
                        _log(f"  ADJUSTED: {param} {old_value} → {new_value}")
                        adjustments += 1
    
    return adjustments


def run():
    """Entry point for pipeline/systemd."""
    lock_fd = open(LOCK_FILE, 'w')
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        _log("Another instance running, exiting")
        return 0
    try:
        _log("=== Self-learning cycle ===")
        kills = _kill_underperformers()
        adjustments = analyze_and_adjust()
        combo_changes = analyze_combo_weights()
        _write_goal_progress()
        _log(f"Completed: {kills} kills, {adjustments} param adjustments, {combo_changes} combo weight changes")
        return kills + adjustments + combo_changes
    finally:
        lock_fd.close()


# ── Combo weight tuning ────────────────────────────────────────────────

def _get_combo_stats():
    """Query signal_outcomes for combo performance (7d window, 3+ trades)."""
    conn = None
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT signal_type, COUNT(*) as n,
                   SUM(CASE WHEN is_win=1 THEN 1 ELSE 0 END)*1.0/COUNT(*) as wr,
                   SUM(pnl_usdt) as total_pnl,
                   SUM(pnl_usdt)*1.0/COUNT(*) as avg_pnl
            FROM signal_outcomes
            WHERE trade_id IS NOT NULL
            AND created_at > datetime('now', ? || ' days')
            GROUP BY signal_type
            HAVING n >= ?
            ORDER BY total_pnl DESC
        """, (f'-{COMBO_WINDOW_DAYS}', COMBO_MIN_TRADES))
        rows = cur.fetchall()
        return [(r[0], r[1], r[2], r[3], r[4]) for r in rows]
    except Exception as e:
        _log(f"Error querying combo stats: {e}")
        return []
    finally:
        if conn:
            conn.close()


def _calc_combo_weight(wr, avg_pnl, n_trades):
    """Map WR + avg PnL to a weight multiplier."""
    if wr >= COMBO_BOOST_WR and avg_pnl > 0:
        # Boost winning combos: higher WR → higher boost
        boost = 1.0 + (wr - COMBO_BOOST_WR) * 1.5  # 60%→1.0, 80%→1.3
        return min(COMBO_BOOST_MAX, round(boost, 2))
    elif wr < COMBO_SUPPRESS_WR or (avg_pnl < COMBO_SUPPRESS_PNL and n_trades >= 10):
        # Suppress losers
        if wr < 0.25:
            return COMBO_SUPPRESS_MIN  # 0.5 — heavy suppress
        elif wr < 0.35:
            return 0.6
        else:
            return 0.7
    return None  # no change needed


def _load_combo_weights():
    """Load existing combo weights from JSON."""
    if os.path.exists(COMBO_WEIGHTS_FILE):
        try:
            with open(COMBO_WEIGHTS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_combo_weights(weights):
    """Save combo weights atomically.
    
    Args:
        weights: dict of {combo_source: weight} — from signal_outcomes.signal_type
    """
    try:
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(COMBO_WEIGHTS_FILE), suffix='.tmp')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(weights, f, indent=2)
            os.replace(tmp, COMBO_WEIGHTS_FILE)
        except Exception:
            os.unlink(tmp)
            raise
    except Exception as e:
        _log(f"Error saving combo weights: {e}")


def _is_signal_disabled(signal_type):
    """Check if a signal type is disabled via hermes_constants flags."""
    try:
        with open(HERMES_CONSTANTS) as f:
            content = f.read()
        disabled_bases = set()
        disabled_variants = set()
        for match in re.finditer(r'^(\w+)_ENABLED\s*=\s*False', content, re.MULTILINE):
            flag_name = match.group(1)
            if flag_name.endswith(('_PLUS', '_MINUS')):
                disabled_variants.add(flag_name)
            else:
                disabled_bases.add(flag_name)
        # Normalize: convert trailing +/- FIRST, then hyphens to underscores
        norm = signal_type.upper()
        norm = re.sub(r'\+$', '_PLUS', norm)
        norm = re.sub(r'-$', '_MINUS', norm)
        norm = norm.replace('-', '_')
        # Strip _LONG/_SHORT direction suffix for base matching
        norm_base = re.sub(r'_(LONG|SHORT)$', '', norm)
        # Check disabled bases
        for db in disabled_bases:
            if norm_base == db or norm_base.startswith(db + '_'):
                return True
        # Check disabled variants
        for dv in disabled_variants:
            if norm == dv or norm.startswith(dv):
                return True
    except Exception:
        pass
    return False


def analyze_combo_weights():
    """Analyze combo performance and update weights JSON."""
    _log("--- Combo weight analysis ---")
    stats = _get_combo_stats()
    
    if not stats:
        _log("  No combos with enough trades")
        return 0
    
    old_weights = _load_combo_weights()
    new_weights = {}
    changes = 0
    
    for signal_type, n, wr, total_pnl, avg_pnl in stats:
        # Skip disabled signals
        if _is_signal_disabled(signal_type):
            _log(f"  {signal_type}: DISABLED, skipping")
            continue
        
        weight = _calc_combo_weight(wr, avg_pnl, n)
        old_w = old_weights.get(signal_type)
        
        if weight is not None and weight != old_w:
            new_weights[signal_type] = weight
            direction = "BOOST" if weight > 1.0 else "SUPPRESS"
            _log(f"  {signal_type}: {n}T WR={wr:.0%} avg_pnl=${avg_pnl:+.4f} → {direction} {weight}")
            changes += 1
        elif old_w is not None:
            new_weights[signal_type] = old_w  # keep existing
        else:
            _log(f"  {signal_type}: {n}T WR={wr:.0%} avg_pnl=${avg_pnl:+.4f} — no change")
    
    # Preserve old weights for signals that dropped below trade threshold
    for st, w in old_weights.items():
        if st not in new_weights:
            new_weights[st] = w
    
    if changes > 0:
        _save_combo_weights(new_weights)
        _log(f"  Wrote {len(new_weights)} weights ({changes} changed) to {COMBO_WEIGHTS_FILE}")
    else:
        _log("  No weight changes needed")
    
    return changes


if __name__ == '__main__':
    if '--dry' in sys.argv:
        _log("DRY RUN — would analyze and adjust")
        for signal_type in ['bb_bounce', 'pattern_wolf', 'accel_300', 'tl_break']:
            trades = _get_recent_trades(signal_type, limit=30)
            if trades:
                wr = _calculate_wr(trades)
                pnl = _calculate_pnl(trades)
                decay = _detect_decay(trades)
                _log(f"  {signal_type}: WR={wr:.1%} PnL=${pnl:+.2f} decay={decay}")
        _log("\n--- Combo analysis (dry) ---")
        stats = _get_combo_stats()
        for signal_type, n, wr, total_pnl, avg_pnl in stats:
            weight = _calc_combo_weight(wr, avg_pnl, n)
            status = f"→ {'BOOST' if weight and weight > 1.0 else 'SUPPRESS' if weight else 'no change'} {weight or ''}"
            _log(f"  {signal_type}: {n}T WR={wr:.0%} avg_pnl=${avg_pnl:+.4f} {status}")
        _log("\n--- Kill threshold check (dry) ---")
        all_signals = _get_all_active_signal_types()
        for signal_type in all_signals:
            if _is_signal_disabled(signal_type):
                continue
            trades = _get_trades_exact(signal_type, limit=KILL_MIN_TRADES)
            if len(trades) < KILL_MIN_TRADES:
                continue
            pnl = _calculate_pnl(trades)
            max_consec = _max_consecutive_losses(trades)
            flag = ""
            if pnl < KILL_PNL_50:
                flag = f"WOULD KILL: PnL=${pnl:+.2f}"
            elif max_consec >= KILL_MAX_CONSEC:
                flag = f"WOULD KILL: {max_consec} consec losses"
            if flag:
                _log(f"  {signal_type}: {flag}")
    else:
        run()
