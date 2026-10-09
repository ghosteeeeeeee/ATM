import time

FP = '/root/.hermes/logs/pipeline.log'

# AUDIT 2026-10-09: last non-empty message logged by this process. Lets
# mark_signal_executed() persist WHY a signal was skipped without editing the
# 44 decider_run.py call sites — every block path there does log(reason)
# immediately before the mark_signal_executed() call, so this captures the
# exact reason string. Long-running daemons (hl-sync-guardian.py) must pass
# reason= explicitly, since a stale fallback would write a wrong message.
_LAST_LOG_MSG = ''

def log(msg, level=None):
    global _LAST_LOG_MSG
    if msg:
        _LAST_LOG_MSG = str(msg)
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'{ts} {msg}' if level is None else f'{ts} [{level}] {msg}'
    print(line, flush=True)
    try:
        with open(FP, 'a') as f:
            f.write(line + '\n')
    except:
        pass


def get_last_log_msg():
    """Return the last message passed to log() by this process (may be '')."""
    return _LAST_LOG_MSG
