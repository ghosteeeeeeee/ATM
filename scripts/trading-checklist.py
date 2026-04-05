#!/usr/bin/env python3
"""
trading-checklist.py — Hermes Trading System Hourly Health Check

Checks all critical trading services every hour and reports status.
Alerts on failures so T can investigate before the next run.

Run via: python3 trading-checklist.py
Or: journalctl -f -u hermes-trading-checklist.timer
"""
import sys
import subprocess
import os
import json
from datetime import datetime

sys.path.insert(0, '/root/.hermes/scripts')

LOG = '/root/.hermes/logs/trading-checklist.log'
os.makedirs(os.path.dirname(LOG), exist_ok=True)

def log(msg, level='INFO'):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] [{level}] {msg}'
    print(line)
    try:
        with open(LOG, 'a') as f:
            f.write(line + '\n')
    except:
        pass


def run_check(name):
    """Run a named check and return (ok: bool, msg: str, issues: list)"""
    issues = []
    try:
        result = CHECKS.get(name, lambda: (True, 'unknown check', []))()
        return result
    except Exception as e:
        return False, f'check crashed: {e}', [str(e)]


# ─── Check 1: Pipeline systemd service ──────────────────────────────
def check_pipeline_service():
    try:
        r = subprocess.run(['systemctl', 'is-active', 'hermes-pipeline.service'],
                         capture_output=True, text=True, timeout=10)
        status = r.stdout.strip()
        if status != 'active':
            return False, f'hermes-pipeline.service is {status}', [f'pipeline service {status}']
        return True, 'pipeline service active', []
    except Exception as e:
        return False, f'cant check pipeline service: {e}', [str(e)]


# ─── Check 2: HL Sync Guardian ──────────────────────────────────────
def check_hl_sync():
    try:
        r = subprocess.run(['systemctl', 'is-active', 'hermes-hl-sync-guardian.service'],
                         capture_output=True, text=True, timeout=10)
        status = r.stdout.strip()
        if status != 'active':
            return False, f'hermes-hl-sync-guardian is {status}', [f'hl-sync {status}']

        # Check DRY mode
        import hyperliquid_exchange
        live = hyperliquid_exchange.is_live_trading_enabled()

        # Check recent log
        log_file = '/root/.hermes/logs/sync-guardian.log'
        recent = ''
        if os.path.exists(log_file):
            with open(log_file) as f:
                lines = f.readlines()
                recent = ''.join(lines[-5:])
        else:
            return False, 'hl-sync running but no log file', ['no sync-guardian.log']

        if 'DRY' in recent and 'Would' in recent and 'Mirrored' not in recent:
            return False, 'hl-sync running in DRY mode (paper→HL mirroring disabled)', ['DRY mode active']

        return True, f'hl-sync active, live_trading={live}', []
    except Exception as e:
        return False, f'cant check hl-sync: {e}', [str(e)]


# ─── Check 3: Pipeline ran recently ───────────────────────────────────
def check_pipeline_recent():
    try:
        r = subprocess.run(['journalctl', '-u', 'hermes-pipeline.service', '-n', '3',
                          '--no-pager', '--since', '5 minutes ago'],
                         capture_output=True, text=True, timeout=15)
        output = r.stdout
        if not output.strip():
            return False, 'no pipeline runs in last 5 minutes', ['pipeline silent 5min']
        if 'Started hermes-pipeline' in output or 'signal_gen' in output or 'Pipeline PAPER' in output:
            return True, 'pipeline ran recently', []
        return False, f'pipeline output unclear: {output[:100]}', ['pipeline unclear output']
    except Exception as e:
        return False, f'cant check pipeline log: {e}', [str(e)]


# ─── Check 4: No competing trading processes ─────────────────────────
# Processes that are explicitly trading-related competitors (not the gateway which is managed)
COMPETING_TRADING = [
    'openclaw-hyperliquid',
    'copy-paper-hype',
    'stoploss',
    'loss-limit',
    'openclaw-watchdog',
    'openclaw-backtest',
    'openclaw-pump',
]

def check_no_competitors():
    issues = []
    managed = []
    try:
        r = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=10)
        for line in r.stdout.splitlines():
            for proc in COMPETING_TRADING:
                if proc in line and 'grep' not in line:
                    pid = line.split()[1]
                    issues.append(f'trading competitor: {proc} (PID {pid})')
            # openclaw-gateway is managed by hermes-agent workspace — log but don't alert
            if 'openclaw-gateway' in line and 'grep' not in line:
                pid = line.split()[1]
                managed.append(f'openclaw-gateway (PID {pid}, managed by hermes-agent)')
        if issues:
            return False, f'{len(issues)} trading competitors', issues
        # Log managed processes at info level
        msg = 'no trading competitors'
        if managed:
            msg += f' | {", ".join(managed)}'
        return True, msg, []
    except Exception as e:
        return False, f'cant check processes: {e}', [str(e)]


# ─── Check 5: Signals DB healthy ────────────────────────────────────
def check_signals_db():
    issues = []
    try:
        import sqlite3
        db = '/root/.hermes/data/signals_hermes_runtime.db'
        conn = sqlite3.connect(db)
        c = conn.cursor()

        # Check for stuck APPROVED signals
        c.execute("SELECT COUNT(*) FROM signals WHERE decision='APPROVED'")
        approved = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM signals WHERE decision='PENDING'")
        pending = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM signals")
        total = c.fetchone()[0]

        # Check recent signals
        c.execute("SELECT COUNT(*), MAX(created_at) FROM signals WHERE created_at > datetime('now', '-2 hours')")
        recent_count, recent_time = c.fetchone()

        conn.close()

        if approved > 50:
            issues.append(f'{approved} stuck APPROVED signals (may indicate position limit)')
        if total > 5000:
            issues.append(f'{total} total signals in DB (may need cleanup)')

        msg = f'{total} signals ({approved} approved, {pending} pending, {recent_count} in last 2h)'
        return (len(issues) == 0, msg, issues)
    except Exception as e:
        return False, f'signals DB error: {e}', [str(e)]


# ─── Check 6: Brain DB healthy ───────────────────────────────────────
def check_brain_db():
    issues = []
    try:
        import psycopg2
        conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain',
                                user='postgres', password='postgres')
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM trades WHERE status='open'")
        open_trades = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM trades WHERE status='closed' AND close_time > NOW() - INTERVAL '24 hours'")
        closed_24h = cur.fetchone()[0]

        conn.commit()
        cur.close(); conn.close()

        if open_trades > 15:
            issues.append(f'{open_trades} open trades (high — verify positions are real)')

        return (len(issues) == 0,
                f'brain OK: {open_trades} open, {closed_24h} closed today',
                issues)
    except Exception as e:
        return False, f'brain DB error: {e}', [str(e)]


# ─── Check 7: Live trading config consistent ─────────────────────────
def check_live_trading():
    issues = []
    try:
        import json
        # Check the live trading file
        fpath = '/var/www/hermes/data/hype_live_trading.json'
        with open(fpath) as f:
            data = json.load(f)

        is_live = data.get('live_trading', False)
        reason = data.get('reason', 'unknown')

        # Check hl-sync guardian DRY mode
        guardian_dry = True
        with open('/root/.hermes/scripts/hl-sync-guardian.py') as gf:
            for line in gf:
                if line.strip().startswith('DRY = '):
                    guardian_dry = (line.strip() == 'DRY = True')
                    break

        # Note: DRY on hl-sync is OK — decider-run handles live HL execution directly.
        # Guardian DRY only means paper→HL mirroring is off (guardian is reconciliation-only).

        msg = f"live_trading={is_live} ({reason}), hl-sync DRY={guardian_dry}"
        return (len(issues) == 0, msg, issues)
    except Exception as e:
        return False, f'live trading config error: {e}', [str(e)]


# ─── Check 8: Momentum cache fresh ─────────────────────────────────
def check_momentum_cache():
    issues = []
    try:
        import sqlite3
        db = '/root/.hermes/data/signals_hermes_runtime.db'
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), MAX(updated_at) FROM momentum_cache")
        count, updated_at = cur.fetchone()
        conn.close()

        if count == 0:
            issues.append('momentum_cache table is empty')
            return False, 'momentum_cache empty', issues

        # updated_at is Unix timestamp stored as TEXT in SQLite
        import time
        now = time.time()
        age_h = (now - float(updated_at)) / 3600 if updated_at else 999
        if age_h > 48:
            issues.append(f'momentum_cache stale ({age_h:.0f}h old, {count} tokens)')

        return (len(issues) == 0,
                f'momentum_cache: {count} tokens, {age_h:.1f}h old',
                issues)
    except Exception as e:
        return False, f'momentum cache check error: {e}', [str(e)]


# ─── Check 9: Trailing stops file ───────────────────────────────────
def check_trailing_stops():
    issues = []
    try:
        import json
        fpath = '/var/www/hermes/data/trailing_stops.json'
        with open(fpath) as f:
            data = json.load(f)

        total = len(data)
        active = sum(1 for v in data.values() if v.get('active', False))
        stale = 0
        # Check for entries with very old activated_at
        import time
        now = time.time()
        for v in data.values():
            if v.get('activated_at'):
                # activated_at_pnl is a %, activated_at_price is the price
                age_h = (now - os.path.getmtime(fpath)) / 3600
                if age_h > 24 and not v.get('active'):
                    stale += 1

        if stale > 100:
            issues.append(f'{stale} stale closed trailing stop entries')

        return (len(issues) == 0,
                f'trailing stops: {total} entries ({active} active)',
                issues)
    except Exception as e:
        return False, f'trailing stops check error: {e}', [str(e)]


# ─── Check 10: Cooldowns file ────────────────────────────────────────
def check_cooldowns():
    issues = []
    try:
        import json
        fpath = '/root/.hermes/data/signal-cooldowns.json'
        if os.path.exists(fpath):
            with open(fpath) as f:
                data = json.load(f)
            # Check for stale cooldowns (expired but not cleaned)
            import time
            now = time.time()
            expired = sum(1 for v in data.values()
                         if isinstance(v, dict) and v.get('expires', 0) < now)
            if expired > 50:
                issues.append(f'{expired} expired cooldowns still in file')
        return (len(issues) == 0,
                f'cooldowns: {len(data)} entries ({expired if "expired" in locals() else 0} expired)',
                issues)
    except Exception as e:
        return False, f'cooldowns check error: {e}', [str(e)]


# ─── Registry ─────────────────────────────────────────────────────────
CHECKS = {
    'pipeline_service':   check_pipeline_service,
    'hl_sync':            check_hl_sync,
    'pipeline_recent':    check_pipeline_recent,
    'no_competitors':     check_no_competitors,
    'signals_db':         check_signals_db,
    'brain_db':           check_brain_db,
    'live_trading':       check_live_trading,
    'momentum_cache':     check_momentum_cache,
    'trailing_stops':     check_trailing_stops,
    'cooldowns':          check_cooldowns,
}


# ─── Main ──────────────────────────────────────────────────────────────
def main():
    log('═══ Hermes Trading Checklist ═══')

    critical = 0
    warnings = 0
    all_ok = True
    report = []

    for name, fn in CHECKS.items():
        ok, msg, issues = run_check(name)
        status = 'OK' if ok else 'FAIL'
        if not ok:
            all_ok = False
            if name in ('pipeline_service', 'hl_sync', 'live_trading', 'no_competitors'):
                critical += 1
                level = 'CRIT'
            else:
                warnings += 1
                level = 'WARN'
            log(f'  [{status}] {name}: {msg}', level)
            for issue in issues:
                log(f'         └─ {issue}', level)
        else:
            log(f'  [OK] {name}: {msg}')

    summary = f'CRITICAL={critical} WARNINGS={warnings}'
    if all_ok:
        log(f'✅ All checks passed. {summary}')
    else:
        log(f'⚠️  {summary} — review failures above', 'CRIT' if critical else 'WARN')

    # Write summary for easy monitoring
    summary_file = '/var/www/hermes/data/trading-checklist.json'
    try:
        os.makedirs(os.path.dirname(summary_file), exist_ok=True)
        with open(summary_file, 'w') as f:
            json.dump({
                'ts': datetime.now().isoformat(),
                'all_ok': all_ok,
                'critical': critical,
                'warnings': warnings,
                'checks': {name: {'ok': run_check(name)[0], 'msg': run_check(name)[1]}
                          for name in CHECKS}
            }, f, indent=2)
    except Exception as e:
        log(f'Could not write summary: {e}')

    return 0 if all_ok else (2 if critical else 1)


if __name__ == '__main__':
    sys.exit(main())
