#!/usr/bin/env python3
"""
run_pipeline.py — Hermes Trading Pipeline
Runs every 1 minute via cron. A/B optimizer every 10 minutes.
"""
import sys, subprocess, time, os, argparse, os

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
LOG     = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'pipeline.log')

# Which steps run every minute vs every N minutes
STEPS_EVERY_MIN  = ['price_collector', 'signal_gen', 'ai_decider', 'decider-run', 'position_manager', 'hermes-trades-api']
STEPS_EVERY_10M  = ['strategy_optimizer', 'ab_optimizer', 'ab_learner']


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


def run(name, args=None):
    script = f'{SCRIPTS}/{name}.py'
    cmd = [sys.executable, script] + (args or [])
    log(f'Running {name}...')
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        out = (r.stdout or '').strip()
        err = (r.stderr or '').strip()
        # Log step output
        if out:
            for line in out.split('\n')[-5:]:
                if line.strip():
                    log(f'  {line.strip()}')
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
    mode = 'LIVE' if is_live else 'PAPER'

    minute = int(time.strftime('%M'))
    every_10 = (minute % 10 == 0)

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
        conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres', password='Brain123')
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
