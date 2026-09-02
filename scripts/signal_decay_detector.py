#!/usr/bin/env python3
"""
signal_decay_detector.py — Lightweight decay detection (delegates kill logic to self_learner).

This was originally a standalone kill system, but overlaps with self_learner.py's
_kill_underperformers(). To avoid conflicting enable/disable decisions, this script
now delegates kill logic to self_learner and only adds 24h rapid-response detection
for catastrophic failures (WR < 15% with 5+ trades in 24h).

Run via: python3 scripts/signal_decay_detector.py
Timer: hermes-signal-decay-detector.timer (every 6h)
"""
import sys, os, sqlite3, fcntl, re
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import RUNTIME_DB, HERMES_DATA

LOCK_FILE = '/tmp/hermes-signal-decay.lock'
CONSTANTS_FILE = os.path.join(os.path.dirname(__file__), 'hermes_constants.py')
LOG_FILE = os.path.join(HERMES_DATA, '..', 'automation', 'decay_log.md')

# ── Rapid-response thresholds (catches things self_learner's daily cycle misses) ──
RAPID_DISABLE_WR = 15      # catastrophic: WR < 15% with 5+ trades in 24h
RAPID_DISABLE_TRADES = 5   # minimum trades for rapid disable
SOFT_WARN_WR = 25          # warn but don't disable

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


def _get_signal_performance_24h():
    """Query signal_outcomes for 24h performance."""
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT signal_type, COUNT(*) as trades, SUM(is_win) as wins,
                   ROUND(CAST(SUM(is_win) AS FLOAT)/COUNT(*)*100, 1) as wr,
                   ROUND(SUM(pnl_pct), 2) as total_pnl
            FROM signal_outcomes
            WHERE created_at > datetime('now', '-24 hours')
              AND trade_id IS NOT NULL
            GROUP BY signal_type
            HAVING COUNT(*) >= ?
            ORDER BY wr ASC
        """, (RAPID_DISABLE_TRADES,))
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        log(f"Error querying performance: {e}")
        return []


def _is_signal_disabled(signal_type):
    """Check if a signal is already disabled in hermes_constants.py."""
    try:
        with open(CONSTANTS_FILE) as f:
            content = f.read()
        norm = signal_type.upper()
        norm = re.sub(r'\+$', '_PLUS', norm)
        norm = re.sub(r'-$', '_MINUS', norm)
        norm = norm.replace('-', '_')
        # Check various flag patterns
        for suffix in ['', '_ENABLED']:
            flag = f'{norm}{suffix}'
            if re.search(rf'^{re.escape(flag)}\s*=\s*False', content, re.MULTILINE):
                return True
        return False
    except Exception:
        return False


def _disable_signal_rapid(signal_type):
    """Disable a signal via self_learner's unified function (import and call)."""
    try:
        from self_learner import _disable_signal
        return _disable_signal(signal_type)
    except ImportError:
        log(f"  ERROR: Could not import self_learner._disable_signal")
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
    log("=== Signal Decay Detector (rapid-response) ===")
    
    # Import regime memory for habitat check
    try:
        from regime_memory import RegimeMemory
        rm = RegimeMemory()
        has_regime_memory = True
    except Exception:
        has_regime_memory = False

    performance = _get_signal_performance_24h()
    if not performance:
        log("No signals with sufficient trades in 24h window")
        return

    disabled_count = 0
    for signal_type, trades, wins, wr, total_pnl in performance:
        if _is_signal_disabled(signal_type):
            continue

        if wr < RAPID_DISABLE_WR and trades >= RAPID_DISABLE_TRADES:
            # REGIME-AWARE CHECK: Does this signal have a winning habitat?
            if has_regime_memory:
                winning = rm.get_winning_regimes(signal_type)
                if winning:
                    log(f"  🟡 RAPID DISABLE BLOCKED: {signal_type}: {wr}% WR but has winning regimes: {winning}")
                    log(f"    → Keeping alive in habitat: {', '.join(winning)}")
                    continue  # Species has a habitat — don't rapid-kill
            
            log(f"  🔴 RAPID DISABLE: {signal_type}: {trades} trades, {wr}% WR, PnL={total_pnl}")
            if _disable_signal_rapid(signal_type):
                disabled_count += 1
        elif wr < SOFT_WARN_WR and trades >= RAPID_DISABLE_TRADES:
            log(f"  🟡 WARNING: {signal_type}: {trades} trades, {wr}% WR, PnL={total_pnl}")
        else:
            log(f"  🟢 OK: {signal_type}: {trades} trades, {wr}% WR, PnL={total_pnl}")

    log(f"Done. Rapid-disabled {disabled_count} signals.")
    log("Note: Detailed kill logic runs via self_learner.py (daily at 06:00 UTC)")


if __name__ == '__main__':
    main()
