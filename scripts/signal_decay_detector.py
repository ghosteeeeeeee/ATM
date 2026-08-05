#!/usr/bin/env python3
"""
signal_decay_detector.py — Auto-detect and disable decaying signals.

Queries signal_outcomes for each signal type (24h, dedup).
If WR drops below threshold with sufficient sample size → auto-disables.

Run via: python3 scripts/signal_decay_detector.py
Timer: hermes-signal-decay-detector.timer (every 6h)
"""
import sys, os, sqlite3, fcntl, shutil
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import RUNTIME_DB, HERMES_DATA

LOCK_FILE = '/tmp/hermes-signal-decay.lock'

# ── Thresholds ─────────────────────────────────────────────────────────────────
WR_HARD_BLOCK = 20      # disable immediately if WR < 20% AND trades >= 3
WR_SOFT_BLOCK = 30      # flag for disable if WR < 30% AND trades >= 5
MIN_TRADES = 3           # minimum trades before decay detection applies
LOG_FILE = os.path.join(HERMES_DATA, '..', 'automation', 'decay_log.md')

def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    line = f"[{ts}] {msg}"
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass

def get_signal_performance():
    """Query signal_outcomes for 24h performance (dedup, trade_id IS NOT NULL)."""
    conn = sqlite3.connect(RUNTIME_DB)
    c = conn.cursor()
    c.execute("""
        SELECT signal_type, COUNT(*) as trades, SUM(is_win) as wins,
               ROUND(CAST(SUM(is_win) AS FLOAT)/COUNT(*)*100, 1) as wr,
               ROUND(SUM(pnl_pct), 2) as total_pnl
        FROM signal_outcomes
        WHERE created_at > datetime('now', '-24 hours')
          AND trade_id IS NOT NULL
        GROUP BY signal_type
        HAVING COUNT(*) >= ?
        ORDER BY wr ASC
    """, (MIN_TRADES,))
    results = c.fetchall()
    conn.close()
    return results

def disable_signal(signal_type):
    """Disable a signal by setting its flag to False in hermes_constants.py."""
    const_file = os.path.join(os.path.dirname(__file__), 'hermes_constants.py')

    # Map signal_type to hermes_constants flag name
    flag_map = {
        'inv-accel-300-': 'INVERSE_ACCEL_300_MINUS_ENABLED',
        'inv-accel-300+': 'INVERSE_ACCEL_300_PLUS_ENABLED',
        'accel-300-': 'ACCEL_300_MINUS_ENABLED',
        'accel-300+': 'ACCEL_300_PLUS_ENABLED',
        'accel-300-vel+': 'ACCEL_300_VELOCITY_PLUS_ENABLED',
        'accel-300-vel-': 'ACCEL_300_VELOCITY_MINUS_ENABLED',
        'accel-300-breakout': 'ACCEL_300_BREAKOUT_ENABLED',
        'bb-squeeze-': 'BOLLINGER_SQUEEZE_MINUS_ENABLED',
        'bb-squeeze+': 'BOLLINGER_SQUEEZE_PLUS_ENABLED',
        'bb-squeeze': 'BOLLINGER_SQUEEZE_ENABLED',
        'tl_break_long': 'TL_BREAK_PLUS_ENABLED',
        'tl_break_short': 'TL_BREAK_MINUS_ENABLED',
        'tl_break': 'TL_BREAK_ENABLED',
        'vel-hermes+': 'VEL_HERMES_PLUS_ENABLED',
        'vel-hermes-': 'VEL_HERMES_MINUS_ENABLED',
        'pct-hermes+': 'PCT_HERMES_PLUS_ENABLED',
        'pct-hermes-': 'PCT_HERMES_MINUS_ENABLED',
        'fast-momentum+': 'FAST_MOMENTUM_PLUS_ENABLED',
        'fast-momentum-': 'FAST_MOMENTUM_MINUS_ENABLED',
        'zscore-rising+': 'ZSCORE_RISING_ENABLED',
        'zscore-rising-': 'ZSCORE_RISING_ENABLED',
    }

    flag = flag_map.get(signal_type)
    if not flag:
        log(f"  SKIP: No flag mapping for {signal_type}")
        return False

    try:
        shutil.copy2(const_file, const_file + '.bak')

        with open(const_file) as f:
            content = f.read()

        # Check if already disabled
        if f'{flag} = False' in content or f'{flag}=False' in content:
            log(f"  SKIP: {flag} already False")
            return False

        # Replace True with False
        old = f'{flag} = True'
        new = f'{flag} = False  # AUTO-DISABLED by signal_decay_detector'
        if old in content:
            content = content.replace(old, new, 1)
            with open(const_file, 'w') as f:
                f.write(content)
            log(f"  DISABLED: {flag}")
            return True
        else:
            log(f"  SKIP: {flag} not found as True in constants")
            return False
    except Exception as e:
        log(f"  ERROR disabling {signal_type}: {e}")
        return False

def main():
    lock_fd = open(LOCK_FILE, 'w')
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("Another instance running, exiting")
        return

    try:
        _main_impl()
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()

def _main_impl():
    log("=== Signal Decay Detector ===")

    performance = get_signal_performance()
    if not performance:
        log("No signals with sufficient trades in 24h window")
        return

    disabled_count = 0
    for signal_type, trades, wins, wr, total_pnl in performance:
        status = "OK"
        action = ""

        if wr < WR_HARD_BLOCK and trades >= MIN_TRADES:
            status = "CRITICAL"
            action = disable_signal(signal_type)
        elif wr < WR_SOFT_BLOCK and trades >= 5:
            status = "WARNING"
            # Don't auto-disable at soft threshold, just log

        marker = "🔴" if status == "CRITICAL" else "🟡" if status == "WARNING" else "🟢"
        log(f"  {marker} {signal_type}: {trades} trades, {wr}% WR, PnL={total_pnl}")
        if action:
            disabled_count += 1

    log(f"Done. Disabled {disabled_count} signals.")
    return disabled_count

if __name__ == '__main__':
    main()
    # ponytail: lock file at /tmp/hermes-signal-decay.lock, removed when done
