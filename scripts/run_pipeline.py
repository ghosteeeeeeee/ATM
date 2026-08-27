#!/usr/bin/env python3
"""
run_pipeline.py — Hermes Trading Pipeline
Runs every 1 minute via cron. A/B optimizer every 10 minutes.
"""
from paths import *
import sys, subprocess, time, os, argparse, os, fcntl, json
from _secrets import BRAIN_DB_DICT

from hermes_log import log
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
LOG     = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'pipeline.log')
LOCK    = '/tmp/hermes-pipeline.lock'

# Which steps run every minute vs every N minutes
#
# ai_decider: DEFUNCT (removed 2026-04-16)
#   - Was: LLM-based hot-set compactor running every 10 min via ai-decider.timer
#   - Problem: update_open_positions_skipped() marked every open-position token
#     SKIPPED every 10 min → 50+ duplicate SKIPPED entries, corrupted signal lifecycle
#   - Replaced by: signal_compactor.py (in STEPS_EVERY_MIN) — deterministic, LLM-free
#   - ai-decider.timer + ai-decider.service: STOPPED and DISABLED
#   - brain.py still has ai_decider import for backward compat only

# 4h_regime_scanner: runs via 4h-regime-scanner.timer (OnUnitActiveSec=4h)
# 15m_regime_scanner: runs via hermes-15m-regime-scanner.timer (OnCalendar=*:0/15:00)
# Both were incorrectly in STEPS_EVERY_MIN — removed 2026-04-25 (were firing every minute,
# burning Binance API calls and producing duplicate stale results).
# Both scanners now read from local candles.db (primary) with Binance fallback.
# signal_gen removed 2026-05-06 — inline signals migrated to signals_runner (scripts/signals/).
# All master *_ENABLED flags in hermes_constants.py are False; signal_gen was doing
# expensive computation (get_all_latest_prices, compute_regime, get_momentum_stats)
# for zero signal output. signals_runner is now the canonical path.
STEPS_EVERY_MIN  = ['signal_compactor', 'signal_analyst', 'breakout_engine', 'signals_runner', 'decider_run', 'position_manager', 'hermes-trades-api']
# price_collector: removed 2026-04-25
#   - Was firing BOTH via run_pipeline.py AND via hermes-price-collector.timer
#   - Lock caused ~0.3% skip rate from collision
#   - Now runs exclusively via hermes-price-collector.timer (standalone, every 1 min)
#   - Pipeline no longer blocked by ~26s aggregation; other steps get faster execution
STEPS_EVERY_5M   = ['signals_runner_slow']  # slow signals: momentum, mtf_momentum (>60s per run)
STEPS_EVERY_10M  = ['strategy_optimizer', 'ab_optimizer']

# Per-step timeouts (seconds)
STEP_TIMEOUTS = {
    'signal_gen': 180,
    'signals_runner': 300,
    'signals_runner_slow': 240,
    'breakout_engine': 60,
    'decider_run': 360,
    'signal_compactor': 60,   # deterministic — must be fast (<2s typical)
    'signal_analyst': 30,     # score hotset signals, must be fast
    'position_manager': 120,
    'strategy_optimizer': 300,
    'ab_optimizer': 300,
    'live_decider': 240,
    'hermes-trades-api': 60,
}
DEFAULT_TIMEOUT = 300


def run(name, args=None):
    # Slow signals runner uses --slow flag
    if name == 'signals_runner_slow':
        name = 'signals_runner'
        args = ['--slow']
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
            if name in ('position_manager', 'decider_run', 'live-decider'):
                # ai_decider: DEFUNCT — removed 2026-04-16.
                # Replaced by signal_compactor.py (STEPS_EVERY_5M) which is deterministic
                # and LLM-free. signal_compactor runs every minute in STEPS_EVERY_MIN.
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


def run_bg(name, args=None):
    """Run a step in the background so the pipeline is not blocked.
    Used for slow steps (>30s) like signals_runner.
    stdout/stderr go to the pipeline log directly.
    """
    if name == 'signals_runner_slow':
        name = 'signals_runner'
        args = ['--slow']
    script = f'{SCRIPTS}/{name}.py'
    cmd = [sys.executable, script] + (args or [])
    log(f'Running {name} [BACKGROUND]...')
    try:
        # Open log file for this step's output
        log_file = LOG
        with open(log_file, 'a') as lf:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=lf,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
        log(f'  {name} forked as PID {proc.pid}')
    except Exception as e:
        log(f'ERROR {name}: failed to fork: {e}')


def main():
    args = sys.argv[1:]
    is_live = '--live' in args
    # Also check hype_live_trading.json for live mode
    try:
        with open(LIVESWITCH_FILE) as f:
            flags = json.load(f)
            if flags.get('live_trading'):
                is_live = True
    except Exception:
        pass
    mode = 'LIVE' if is_live else 'PAPER'

    minute = int(time.strftime('%M'))
    every_5  = (minute % 5 == 0)
    every_10 = (minute % 10 == 0)

    # Prevent overlapping pipeline runs (systemd can fire twice)
    try:
        lock_fd = os.open(LOCK, os.O_CREAT | os.O_RDWR)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (IOError, OSError):
        log(f'=== Pipeline skipped (already running) ===')
        sys.exit(0)

    # Explicitly close lock fd — otherwise the lock persists until this process
    # exits. Since signals_runner is forked (run_bg with start_new_session=True),
    # the fd is duplicated into the child. Closing it here releases the lock
    # immediately so subsequent pipeline runs are not blocked.
    try:
        os.close(lock_fd)
    except OSError:
        pass

    log(f'=== Pipeline {mode} ({"1m+5m+10m" if every_5 else ("1m+10m" if every_10 else "1m")}) ===')

    # Step 0: Coin tracker (collect per-coin intelligence, export JSON for dashboard)
    try:
        from coin_tracker import collect as coin_collect
        from coin_tracker_api import export_all as coin_export
        coin_collect()
        coin_export()
    except Exception as e:
        log(f'  [coin_tracker] error: {e}')

    # Increment pipeline cycle counter (used for cascade-flip eviction tracking)
    try:
        sys.path.insert(0, SCRIPTS)
        from cascade_flip_helpers import increment_pipeline_cycle
        new_cycle = increment_pipeline_cycle()
        log(f'  [Cycle] #{new_cycle}')
    except Exception as e:
        log(f'  [Cycle] ⚠️ Could not increment cycle: {e}')

    # Increment post-flip cycle counters (v2 anti-whipsaw window)
    try:
        from cascade_flip_helpers import increment_post_flip_cycles, cleanup_post_flip_state
        increment_post_flip_cycles()
        cleanup_post_flip_state()
    except Exception:
        pass  # Best-effort — v2 not critical

    import time as _t
    start = _t.time()
    # Every minute
    for step in STEPS_EVERY_MIN:
        # NOTE: --live is NOT passed to step scripts.
        # All scripts check LIVESWITCH_FILE (hype_live_trading.json) for live mode.
        # Some scripts (breakout_engine, price_collector, etc.) do not accept --live.
        if step == 'signals_runner':
            run(step)  # signals_runner ~3s — run synchronously so decider_run sees fresh signals
        else:
            run(step)

    # Every 5 minutes: slow signals (momentum, mtf_momentum)
    if every_5:
        for step in STEPS_EVERY_5M:
            run(step)

    # Every 10 minutes: strategy_optimizer, ab_optimizer
    if every_10:
        for step in STEPS_EVERY_10M:
            run(step)

    elapsed = _t.time() - start
    log(f'=== Pipeline done ({mode}) ===')

    # Write heartbeat for watchdog monitoring
    try:
        heartbeat_file = os.path.join(HERMES_DATA, 'pipeline_heartbeat.json')
        os.makedirs(os.path.dirname(heartbeat_file), exist_ok=True)
        with open(heartbeat_file, 'w') as f:
            json.dump({'timestamp': time.time(), 'mode': mode, 'elapsed': round(elapsed, 1)}, f)
    except Exception:
        pass

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
