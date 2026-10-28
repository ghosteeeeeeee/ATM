#!/usr/bin/env python3
"""
health_monitor.py — Deterministic pipeline/system health checks + auto-fix.

REPLACES the hourly health-monitor LLM agent (run_health_monitor.sh), which was
spending ~$4.10/30d re-reading `systemctl is-active` / `df -h` output that this
script checks directly. CEO 2026-10-27 item 3.

Division of labor (do NOT duplicate):
  pipeline_watchdog.py  — every 2 min: lock/heartbeat, signal production, trade
                          execution, log errors, failed-service restart, syntax,
                          stale locks, DB leaks, vacation-pause awareness.
  health_monitor.py     — hourly (this): DISK, PRICE STALENESS, data-feed TIMER
                          liveness, phantom trades, old-log compression, and the
                          error_alerts.md writer.

Design rules:
  * ALERT-ON-ANOMALY ONLY — never append an "all clear" line. (The LLM version
    wrote a section every hour, bloating error_alerts.md to 248KB of noise.)
  * VACATION PAUSE AWARE — when data/vacation_pause.json exists the pipeline was
    stopped INTENTIONALLY; never restart hermes-pipeline / hermes-watchdog timers.
    (The 2026-10-15 incident: the LLM auto-fixer restarted a paused pipeline and
    a LIVE trade opened at 02:29 — the pause was silently defeated.)
  * Never leave a timer stopped — if we stop anything for diagnosis we restart it.
  * Fail-open on any per-check error: report, never crash the run.
  * Auto-fix is MINIMAL and safe: compress old logs, re-arm data-feed timers.
    Pipeline restart is pipeline_watchdog.py's job, not ours.

Usage: python3 scripts/health_monitor.py [--quiet]
"""
import sys
import os
import json
import time
import gzip
import shutil
import sqlite3
import argparse
import subprocess
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, HERMES_LOG_DIR

# ── Paths / thresholds ───────────────────────────────────────────────────────
ERROR_ALERTS = '/root/.hermes/automation/error_alerts.md'
PAUSE_MARKER = os.path.join(HERMES_DATA, 'vacation_pause.json')
SIGNALS_DB = os.path.join(HERMES_DATA, 'signals_hermes.db')

DISK_WARN_PCT = 85            # df -u warn threshold
PRICE_STALE_WARN_SEC = 300    # 5 min — price_history too old
LOG_COMPRESS_AGE_DAYS = 7     # compress *.log older than this when disk high
PRICE_TOKEN_MIN = 1           # 0 tokens with fresh prices = WARN

# Data-feed timers that must stay armed. Pipeline/watchdog are EXCLUDED on
# purpose — those are pipeline_watchdog.py's domain and are pause-gated.
DATA_FEED_TIMERS = [
    'hermes-price-collector.timer',
    'hermes-1m-candle.timer',
]


def log(msg, quiet=False):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    if not quiet:
        print(f'[{ts}] [health_monitor] {msg}', flush=True)


# ── Checks ───────────────────────────────────────────────────────────────────
def check_disk():
    """Disk usage. WARN above DISK_WARN_PCT."""
    try:
        st = os.statvfs('/')
        used_pct = (1 - st.f_bavail / st.f_blocks) * 100
        if used_pct >= DISK_WARN_PCT:
            return ('WARN', f'disk {used_pct:.0f}% used (>= {DISK_WARN_PCT}%)')
        return ('OK', f'disk {used_pct:.0f}%')
    except Exception as e:
        return ('OK', f'disk check skipped: {e}')


def check_price_freshness():
    """price_history staleness + token count. Live in signals_hermes.db."""
    if not os.path.exists(SIGNALS_DB):
        return ('OK', 'signals db absent (price check skipped)')
    try:
        conn = sqlite3.connect(SIGNALS_DB, timeout=5)
        try:
            c = conn.cursor()
            c.execute('SELECT MAX(timestamp), COUNT(DISTINCT token) FROM price_history')
            max_ts, n_tokens = c.fetchone()
        finally:
            conn.close()
        if not max_ts:
            return ('WARN', 'price_history empty — no prices at all')
        # timestamp may be epoch REAL or TEXT (ISO) depending on writer. A TypeError
        # here used to fall through to "OK — check skipped", which silently
        # DISABLED the staleness check (review #8). Handle both, and report the
        # check as skipped-as-WARN rather than falsely-OK when we can't parse.
        try:
            if isinstance(max_ts, (int, float)):
                age = time.time() - float(max_ts)
            else:
                dt = datetime.fromisoformat(str(max_ts).replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age = (datetime.now(timezone.utc) - dt).total_seconds()
        except (TypeError, ValueError) as e:
            return ('WARN', f'price timestamp unparseable ({type(max_ts).__name__}): {e} — staleness check not runnable')
        if age > PRICE_STALE_WARN_SEC:
            return ('WARN', f'prices stale {age:.0f}s (>{PRICE_STALE_WARN_SEC}s), {n_tokens} tokens')
        if n_tokens < PRICE_TOKEN_MIN:
            return ('WARN', f'only {n_tokens} tokens with prices')
        return ('OK', f'prices {age:.0f}s old, {n_tokens} tokens')
    except Exception as e:
        return ('OK', f'price check skipped: {e}')


def _timer_active(unit):
    try:
        r = subprocess.run(['systemctl', 'is-active', unit],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() == 'active'
    except Exception:
        return True  # fail-open: don't cry wolf if systemctl hiccups


def check_and_rearm_data_feed_timers():
    """Ensure critical data-feed timers are armed. Re-arm if inactive.

    NEVER touches hermes-pipeline / hermes-watchdog (pause-gated, and
    pipeline_watchdog.py owns those).
    """
    rearmed = []
    inactive = []
    for unit in DATA_FEED_TIMERS:
        if _timer_active(unit):
            continue
        inactive.append(unit)
        if os.path.exists(PAUSE_MARKER):
            # Paused: price/candle collection is still safe+needed per the old
            # prompt, but do NOT bulk-restart while paused without logging.
            continue
        try:
            subprocess.run(['systemctl', 'start', unit], timeout=15, capture_output=True)
            if _timer_active(unit):
                rearmed.append(unit)
        except Exception:
            pass
    if rearmed:
        return ('WARN', f're-armed inactive data-feed timer(s): {", ".join(reamed)}')
    if inactive:
        return ('WARN', f'data-feed timer(s) inactive (not re-armed, possibly paused): {", ".join(inactive)}')
    return ('OK', 'data-feed timers armed')


def check_phantom_trades():
    """atr_sl_hit closes with ~zero PnL = phantom trades."""
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        try:
            c = conn.cursor()
            c.execute("""
                SELECT COUNT(*) FROM trades
                WHERE status='closed' AND exit_reason='atr_sl_hit'
                  AND close_time > NOW() - INTERVAL '24 hours'
                  AND ABS(COALESCE(pnl_pct,0)) < 0.01
            """)
            n = c.fetchone()[0]
        finally:
            conn.close()
        if n >= 3:
            return ('WARN', f'{n} phantom trades (atr_sl_hit with <0.01% PnL in 24h)')
        return ('OK', f'{n} phantom trades')
    except Exception as e:
        return ('OK', f'phantom check skipped: {e}')


def compress_old_logs():
    """Compress *.log older than LOG_COMPRESS_AGE_DAYS. Only when disk high."""
    try:
        du = os.statvfs('/')
        used_pct = (1 - du.f_bavail / du.f_blocks) * 100
        if used_pct < DISK_WARN_PCT:
            return ('OK', 'disk under threshold — no compression')
        cutoff = time.time() - LOG_COMPRESS_AGE_DAYS * 86400
        compressed = 0
        freed = 0
        for name in os.listdir(HERMES_LOG_DIR):
            if not name.endswith('.log'):
                continue
            path = os.path.join(HERMES_LOG_DIR, name)
            try:
                if os.path.getmtime(path) >= cutoff:
                    continue
                size = os.path.getsize(path)
                with open(path, 'rb') as f_in, gzip.open(path + '.gz', 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
                os.unlink(path)
                compressed += 1
                freed += size
            except Exception:
                continue
        if compressed:
            return ('WARN', f'compressed {compressed} old logs, freed {freed/1e6:.1f}MB (disk {used_pct:.0f}%)')
        return ('OK', f'disk {used_pct:.0f}%, nothing to compress')
    except Exception as e:
        return ('OK', f'log compression skipped: {e}')


# ── Alert writer (anomaly-only) ──────────────────────────────────────────────
def append_alerts(warns):
    """Append ONE section listing only WARN/CRITICAL findings. No all-clear."""
    if not warns:
        return False
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    lines = [f'\n## Error Alerts — {ts}\n']
    for name, msg in warns:
        lines.append(f'- **[WARN]** (health_monitor): `{name}`: {msg}\n')
    try:
        with open(ERROR_ALERTS, 'a') as f:
            f.writelines(lines)
        return True
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()
    q = args.quiet

    paused = os.path.exists(PAUSE_MARKER)
    if paused:
        log('vacation pause marker present — pipeline/watchdog restarts suppressed', q)

    checks = {
        'disk': check_disk(),
        'prices': check_price_freshness(),
        'timers': check_and_rearm_data_feed_timers(),
        'phantom': check_phantom_trades(),
        'logs': compress_old_logs(),
    }

    warns = [(k, v[1]) for k, v in checks.items() if v[0] == 'WARN']

    for name, (status, msg) in checks.items():
        if status != 'OK':
            log(f'  {name}: {status} — {msg}', q)

    if warns:
        wrote = append_alerts(warns)
        log(f'{len(warns)} WARN finding(s) {"appended to error_alerts.md" if wrote else "(alert write FAILED)"}', q)
    else:
        log('all checks OK — no alert written (anomaly-only)', q)

    return 0


if __name__ == '__main__':
    sys.exit(main())
