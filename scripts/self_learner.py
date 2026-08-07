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
    )
except ImportError:
    MIN_WR = 0.30
    GOAL_WR = 0.40
    MAX_ADJUSTMENTS_PER_DAY = 3
    MIN_TRADES_BETWEEN = 15

CRITICAL_WR = 0.25  # Below this = emergency disable

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
    'TREND_FILTER_NEUTRAL_PCT': {'min': 0.05, 'max': 0.20, 'step': 0.05, 'tighten': 'down'},
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
        adjustments = analyze_and_adjust()
        combo_changes = analyze_combo_weights()
        _log(f"Completed: {adjustments} param adjustments, {combo_changes} combo weight changes")
        return adjustments + combo_changes
    finally:
        lock_fd.close()


# ── Combo weight tuning ────────────────────────────────────────────────

def _get_combo_stats():
    """Query signal_outcomes for combo performance (7d window, 3+ trades)."""
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
        conn.close()
        return [(r[0], r[1], r[2], r[3], r[4]) for r in rows]
    except Exception as e:
        _log(f"Error querying combo stats: {e}")
        return []


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
        # Check SIGNAL_BLOCKED set
        if f"'{signal_type}'" in content.split('SIGNAL_BLOCKED')[1].split(']')[0] if 'SIGNAL_BLOCKED' in content else False:
            return True
        # Check *_ENABLED flags (crude but works for most)
        import re
        flag_name = signal_type.upper().replace('-', '_') + '_ENABLED'
        match = re.search(rf'{flag_name}\s*=\s*(True|False)', content)
        if match:
            return match.group(1) == 'False'
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
    else:
        run()
