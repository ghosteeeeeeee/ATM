#!/usr/bin/env python3
"""
Parameter Auto-Tuner: adjusts SL/TP/trailing from MFE/MAE analysis of recent trades.

Data source: PostgreSQL brain DB (trades table) — computes MFE/MAE from price history.
Output: modifies hermes_constants.py with safety bounds.
Timer: every 12 hours (hermes-param-auto-tuner.timer)

Usage:
  python3 param_auto_tuner.py           # Full run: analyze → decide → apply
  python3 param_auto_tuner.py --dry     # Dry run: show what would change
"""

import sys, os, re, fcntl, shutil, json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _secrets import BRAIN_DB_DICT

DRY_RUN = '--dry' in sys.argv
LOCK_FILE = '/tmp/hermes-param-tuner.lock'
CONSTANTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hermes_constants.py')
TUNE_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'automation', 'tuner_log.md')

# Safety constraints
MAX_CHANGES_PER_CYCLE = 2
MAX_PCT_CHANGE = 0.10  # 10% max change per param per cycle

# Tuning thresholds
MAE_MFE_RATIO_THRESHOLD = 1.2   # avg MAE/avg MFE — SL too tight if above
MFE_SL_RATIO_THRESHOLD = 2.0    # avg MFE/avg SL — TP too loose if above
WHIPSAW_THRESHOLD = 0.40        # >40% whipsaw → trailing too tight
MIN_TRADES = 20                 # need at least 20 trades for meaningful analysis


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    line = f"[{ts}] {msg}"
    print(line)
    try:
        os.makedirs(os.path.dirname(TUNE_LOG), exist_ok=True)
        with open(TUNE_LOG, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass


def get_closed_trades():
    """Fetch last N closed trades from brain DB with price data for MFE/MAE."""
    import psycopg2
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    try:
        c = conn.cursor()
        c.execute("""
            SELECT token, direction, entry_price, highest_price, lowest_price,
                   stop_loss, target, pnl_pct, close_time
            FROM trades
            WHERE status = 'closed'
              AND entry_price > 0
              AND highest_price > 0
              AND lowest_price IS NOT NULL
              AND lowest_price > 0
              AND stop_loss > 0
              AND target > 0
            ORDER BY close_time DESC
            LIMIT 50
        """)
        return c.fetchall()
    finally:
        conn.close()


def compute_mfe_mae(trades):
    """Compute MFE and MAE for each trade. Returns list of dicts."""
    results = []
    for token, direction, entry, high, low, sl, tp, pnl_pct, close_time in trades:
        if direction == 'LONG':
            mfe = (high - entry) / entry if entry else 0
            mae = (entry - low) / entry if entry else 0
        else:  # SHORT
            mfe = (entry - low) / entry if entry else 0
            mae = (high - entry) / entry if entry else 0

        results.append({
            'token': token,
            'direction': direction,
            'entry': entry,
            'mfe': max(mfe, 0),
            'mae': max(mae, 0),
            'sl_pct': abs(entry - sl) / entry if sl and entry else 0,
            'tp_pct': abs(tp - entry) / entry if tp and entry else 0,
            'pnl_pct': pnl_pct or 0,
        })
    return results


def analyze_distribution(trades_data):
    """Analyze MFE/MAE distribution and return tuning recommendations."""
    n = len(trades_data)
    if n < MIN_TRADES:
        return {'error': f'Only {n} trades (need {MIN_TRADES})', 'changes': []}

    avg_mfe = sum(t['mfe'] for t in trades_data) / n
    avg_mae = sum(t['mae'] for t in trades_data) / n
    avg_sl = sum(t['sl_pct'] for t in trades_data) / n
    avg_tp = sum(t['tp_pct'] for t in trades_data) / n

    # MFE/MAE ratios
    mae_mfe_ratio = avg_mae / avg_mfe if avg_mfe > 0 else 999
    mfe_sl_ratio = avg_mfe / avg_sl if avg_sl > 0 else 0

    # Whipsaw: trades that went profitable then closed at loss
    whipsaw_count = sum(
        1 for t in trades_data
        if t['mfe'] > 0.002 and t['pnl_pct'] < 0  # had >0.2% MFE but lost
    )
    whipsaw_rate = whipsaw_count / n

    # Win rate
    win_count = sum(1 for t in trades_data if t['pnl_pct'] > 0)
    win_rate = win_count / n

    stats = {
        'trades': n,
        'avg_mfe': avg_mfe,
        'avg_mae': avg_mae,
        'avg_sl': avg_sl,
        'avg_tp': avg_tp,
        'mae_mfe_ratio': mae_mfe_ratio,
        'mfe_sl_ratio': mfe_sl_ratio,
        'whipsaw_rate': whipsaw_rate,
        'win_rate': win_rate,
    }

    changes = []

    # Rule 1: MAE > MFE → SL too tight (stops hit before targets)
    if mae_mfe_ratio > MAE_MFE_RATIO_THRESHOLD:
        # Widen ATR_SL_MIN by 5-10%
        current = _read_const('ATR_SL_MIN')
        if current is not None:
            delta = min(current * 0.08, current * (mae_mfe_ratio - 1) * 0.1)
            new_val = round(current + delta, 5)
            if new_val <= current * (1 + MAX_PCT_CHANGE):
                changes.append({
                    'param': 'ATR_SL_MIN',
                    'old': current,
                    'new': new_val,
                    'reason': f'SL too tight: MAE/MFE={mae_mfe_ratio:.2f} (>{MAE_MFE_RATIO_THRESHOLD})',
                })

    # Rule 2: MFE >> SL → TP too loose (giving back profits)
    if mfe_sl_ratio > MFE_SL_RATIO_THRESHOLD and avg_tp > 0:
        current = _read_const('ATR_TP_MAX')
        if current is not None:
            delta = min(current * 0.08, current * (mfe_sl_ratio - MFE_SL_RATIO_THRESHOLD) * 0.05)
            new_val = round(current - delta, 5)
            if new_val >= current * (1 - MAX_PCT_CHANGE):
                changes.append({
                    'param': 'ATR_TP_MAX',
                    'old': current,
                    'new': new_val,
                    'reason': f'TP too loose: MFE/SL={mfe_sl_ratio:.2f} (>{MFE_SL_RATIO_THRESHOLD})',
                })

    # Rule 3: High whipsaw → trailing too tight (exits prematurely)
    if whipsaw_rate > WHIPSAW_THRESHOLD:
        current = _read_const('TRAILING_DISTANCE_PCT')
        if current is not None:
            delta = min(current * 0.08, current * (whipsaw_rate - WHIPSAW_THRESHOLD) * 0.2)
            new_val = round(current + delta, 5)
            if new_val <= current * (1 + MAX_PCT_CHANGE):
                changes.append({
                    'param': 'TRAILING_DISTANCE_PCT',
                    'old': current,
                    'new': new_val,
                    'reason': f'Whipsaw rate {whipsaw_rate:.0%} (>{WHIPSAW_THRESHOLD:.0%}), widening trail',
                })

    # Rule 4: Win rate very low → tighten everything proportionally
    if win_rate < 0.35 and not changes:
        # Widen SL slightly to survive volatility
        current = _read_const('ATR_SL_MAX')
        if current is not None:
            new_val = round(min(current * 1.05, 0.025), 5)  # cap at 2.5%
            if new_val <= current * (1 + MAX_PCT_CHANGE):
                changes.append({
                    'param': 'ATR_SL_MAX',
                    'old': current,
                    'new': new_val,
                    'reason': f'Low WR {win_rate:.0%}, widening SL cap for survival',
                })

    return {'stats': stats, 'changes': changes[:MAX_CHANGES_PER_CYCLE]}


def _read_const(name):
    """Read a constant value from hermes_constants.py."""
    try:
        with open(CONSTANTS_FILE) as f:
            content = f.read()
        match = re.search(rf'^{name}\s*=\s*([0-9.]+)', content, re.MULTILINE)
        if match:
            return float(match.group(1))
    except Exception as e:
        log(f"Error reading {name}: {e}")
    return None


# CEO freeze — never auto-write these until date passes (defense if timer re-enabled)
_CEO_FREEZE_UNTIL = datetime(2026, 8, 4, 23, 15, tzinfo=timezone.utc)
_CEO_FROZEN_PARAMS = frozenset({
    'ATR_SL_MIN_INIT', 'ATR_SL_MAX_INIT', 'SL_PCT_FALLBACK', 'STOP_LOSS_DEFAULT',
    'TRAILING_ACTIVATION_PCT', 'TRAILING_DISTANCE_PCT', 'SIGNAL_FILTER_SPEED_MIN',
    'ATR_SL_MIN', 'ATR_SL_MAX',
})


def _apply_changes(changes):
    """Apply parameter changes to hermes_constants.py."""
    if not changes:
        return []

    frozen = datetime.now(timezone.utc) < _CEO_FREEZE_UNTIL
    if frozen:
        blocked = [c for c in changes if c.get('param') in _CEO_FROZEN_PARAMS]
        changes = [c for c in changes if c.get('param') not in _CEO_FROZEN_PARAMS]
        for c in blocked:
            log(f"CEO FREEZE: skip {c.get('param')} until {_CEO_FREEZE_UNTIL.isoformat()}")
        if not changes:
            return []

    # Backup
    shutil.copy2(CONSTANTS_FILE, CONSTANTS_FILE + '.bak')

    with open(CONSTANTS_FILE) as f:
        content = f.read()

    # Strip prior auto-tune comments to prevent stacking
    content = re.sub(r'\s*#\s*AUTO-TUNED\s*\d{4}-\d{2}-\d{2}\s*', ' ', content)

    applied = []
    for ch in changes:
        param, old_val, new_val = ch['param'], ch['old'], ch['new']
        # Match full numeric token (not str(float) which drops trailing zeros)
        pattern = rf'({re.escape(param)}\s*=\s*)([0-9]*\.?[0-9]+)'
        replacement = f'\\g<1>{new_val}  # AUTO-TUNED {datetime.now(timezone.utc).strftime("%Y-%m-%d")}'
        new_content = re.sub(pattern, replacement, content, count=1)

        if new_content != content:
            content = new_content
            applied.append(ch)
            log(f"Applied: {param} {old_val} → {new_val} ({ch['reason']})")
        else:
            log(f"No match for {param}={old_val}")

    if applied and not DRY_RUN:
        # Validate Python syntax before writing
        try:
            compile(content, CONSTANTS_FILE, 'exec')
        except SyntaxError as e:
            log(f"FATAL: Corrupted constants file, restoring backup: {e}")
            shutil.copy2(CONSTANTS_FILE + '.bak', CONSTANTS_FILE)
            return []
        with open(CONSTANTS_FILE, 'w') as f:
            f.write(content)

    return applied


def _log_session(stats, applied):
    """Append session summary to tuner_log.md."""
    os.makedirs(os.path.dirname(TUNE_LOG), exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    with open(TUNE_LOG, 'a') as f:
        f.write(f"\n## Tuner Run — {ts}\n")
        f.write(f"- Trades analyzed: {stats.get('trades', 0)}\n")
        f.write(f"- Win rate: {stats.get('win_rate', 0):.0%}\n")
        f.write(f"- Avg MFE: {stats.get('avg_mfe', 0):.4f}%\n")
        f.write(f"- Avg MAE: {stats.get('avg_mae', 0):.4f}%\n")
        f.write(f"- MAE/MFE ratio: {stats.get('mae_mfe_ratio', 0):.2f}\n")
        f.write(f"- MFE/SL ratio: {stats.get('mfe_sl_ratio', 0):.2f}\n")
        f.write(f"- Whipsaw rate: {stats.get('whipsaw_rate', 0):.0%}\n")
        if applied:
            for ch in applied:
                f.write(f"- **Changed**: {ch['param']} {ch['old']} → {ch['new']} ({ch['reason']})\n")
        else:
            f.write(f"- No changes needed\n")
        f.write(f"\n")


def main():
    log(f"{'[DRY RUN] ' if DRY_RUN else ''}=== Parameter Auto-Tuner ===")

    # Lock
    lock_fd = open(LOCK_FILE, 'w')
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_fd.close()
        log("Another instance running, exiting")
        return

    try:
        # Fetch trades
        trades = get_closed_trades()
        log(f"Fetched {len(trades)} closed trades")

        if len(trades) < MIN_TRADES:
            log(f"Not enough trades ({len(trades)} < {MIN_TRADES}), skipping")
            return

        # Compute MFE/MAE
        trades_data = compute_mfe_mae(trades)

        # Analyze
        result = analyze_distribution(trades_data)
        stats = result.get('stats', {})
        changes = result.get('changes', [])

        log(f"Stats: WR={stats.get('win_rate', 0):.0%}, "
            f"MFE={stats.get('avg_mfe', 0):.4f}, MAE={stats.get('avg_mae', 0):.4f}, "
            f"MAE/MFE={stats.get('mae_mfe_ratio', 0):.2f}, "
            f"Whipsaw={stats.get('whipsaw_rate', 0):.0%}")

        if not changes:
            log("No parameter changes needed")
        else:
            log(f"{len(changes)} changes recommended:")
            for ch in changes:
                log(f"  {ch['param']}: {ch['old']} → {ch['new']} ({ch['reason']})")

            applied = _apply_changes(changes)
            log(f"{len(applied)} changes applied")

        _log_session(stats, applied if changes else [])

    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


if __name__ == '__main__':
    main()
