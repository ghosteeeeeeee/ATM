#!/usr/bin/env python3
"""
run_pipeline.py — Hermes Trading Pipeline
Runs every 1 minute via cron. A/B optimizer every 10 minutes.
"""
import sys, subprocess, time, os, argparse, os, fcntl, json
from _secrets import BRAIN_DB_DICT

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
LOG     = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'pipeline.log')
LOCK    = '/tmp/hermes-pipeline.lock'

# Which steps run every minute vs every N minutes
STEPS_EVERY_MIN  = ['price_collector', '4h_regime_scanner', 'signal_gen', 'hermes-trades-api', 'decider_run', 'position_manager']
STEPS_EVERY_10M  = ['ai_decider', 'strategy_optimizer', 'ab_optimizer', 'ab_learner']


def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, 'a') as f:
            f.write(line + '\n')
    except:
        pass


# Per-step timeouts (seconds)
STEP_TIMEOUTS = {
    'signal_gen': 180,
    'decider_run': 360,
    'ai_decider': 240,
    'position_manager': 120,
    'strategy_optimizer': 300,
    'ab_optimizer': 300,
    'ab_learner': 300,
    'live_decider': 240,
    'hermes-trades-api': 60,
}
DEFAULT_TIMEOUT = 300


def run(name, args=None):
    script = f'{SCRIPTS}/{name}.py'
    cmd = [sys.executable, script] + (args or [])
    timeout = STEP_TIMEOUTS.get(name, DEFAULT_TIMEOUT)
    log(f'Running {name}...')
    try:
        r = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)
        out = (r.stdout or b'').decode(errors='replace').strip()
        err = (r.stderr or b'').decode(errors='replace').strip()

        # Always log last 5 lines of output for position_manager, decider-run, signal_gen
        # This is critical for monitoring trade decisions in real-time
        if out:
            lines = out.split('\n')
            # For noisy steps (price_collector etc.) only log errors
            if name in ('position_manager', 'decider_run', 'signal_gen', 'ai_decider', 'live-decider'):
                log_lines = [l.strip() for l in lines if l.strip()]
                if log_lines:
                    for l in log_lines[-8:]:
                        log(f'  {l}')
            else:
                # For other steps, just tail the output
                tail = [l.strip() for l in lines[-3:] if l.strip()]
                for l in tail:
                    log(f'  {l}')

        if r.returncode != 0 and err:
            for line in err.strip().split('\n')[:2]:
                if line.strip():
                    log(f'  ERR {name}: {line.strip()}')
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        log(f'ERROR {name}: timed out')
        return False
    except Exception as e:
        log(f'ERROR {name}: {e}')
        return False


def main():
    args = sys.argv[1:]
    is_live = '--live' in args
    # Also check hype_live_trading.json for live mode
    try:
        with open('/var/www/hermes/data/hype_live_trading.json') as f:
            flags = json.load(f)
            if flags.get('live_trading'):
                is_live = True
    except Exception:
        pass
    mode = 'LIVE' if is_live else 'PAPER'

    minute = int(time.strftime('%M'))
    every_10 = (minute % 10 == 0)

    # Prevent overlapping pipeline runs (systemd can fire twice)
    try:
        lock_fd = os.open(LOCK, os.O_CREAT | os.O_RDWR)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (IOError, OSError):
        log(f'=== Pipeline skipped (already running) ===')
        sys.exit(0)

    log(f'=== Pipeline {mode} ({"1m+10m" if every_10 else "1m"}) ===')

    import time as _t
    start = _t.time()
    # Every minute
    for step in STEPS_EVERY_MIN:
        # Pass --live to step scripts only when in live mode
        extra = ['--live'] if is_live else []
        run(step, extra)

    # Every 10 minutes
    if every_10:
        log('Running 10-min steps...')
        for step in STEPS_EVERY_10M:
            run(step)

    elapsed = _t.time() - start
    log(f'=== Pipeline done ({mode}) ===')

    # Quick summary
    try:
        import psycopg2
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trades WHERE server='Hermes' AND status='open'")
        open_c = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*), COALESCE(SUM(pnl_pct),0) FROM trades WHERE server='Hermes' AND status='closed' AND close_time > NOW() - INTERVAL '24 hours'")
        closed_today, closed_pnl = cur.fetchone()
        cur.execute("SELECT COUNT(*), COALESCE(SUM(pnl_pct),0) FROM trades WHERE server='Hermes' AND status='open'")
        open_c, open_pnl = cur.fetchone()
        total_pnl = closed_pnl + open_pnl
        log(f'Portfolio: {open_c} open | {closed_today} closed today | {total_pnl:+.2f}% PnL')
    except:
        pass


if __name__ == '__main__':
    main()
