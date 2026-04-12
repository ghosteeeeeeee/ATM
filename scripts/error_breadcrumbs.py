#!/usr/bin/env python3
"""
error_breadcrumbs.py — Structured error tracing for Hermes pipeline.

Every pipeline step emits a breadcrumb at entry and exit.
If something breaks, the full call chain is visible in the log.

Usage:
    from error_breadcrumbs import BREADCRUMB, breadcrumb_trace

    def my_pipeline_step():
        BREADCRUMB("step_name", "enter", extra={"token": "BTC"})
        try:
            result = do_work()
            BREADCRUMB("step_name", "ok", extra={"result_count": len(result)})
            return result
        except Exception as e:
            BREADCRUMB("step_name", "ERROR", extra={"error": str(e)})
            raise

Format in trading.log:
    [TIMESTAMP] [BREAD] step_name | enter | {extra}
    [TIMESTAMP] [BREAD] step_name | ok  | {extra}
    [TIMESTAMP] [BREAD] step_name | ERROR | {extra="error message"}
"""
import time, json, os, traceback
from datetime import datetime

LOG_FILE = '/var/www/hermes/logs/trading.log'
BREADCRUMB_FILE = '/var/www/hermes/data/breadcrumbs.json'
ENABLED = True  # Set to False to disable without removing code

def BREADCRUMB(step: str, status: str, extra: dict = None):
    """
    Emit a structured breadcrumb for pipeline tracing.
    
    Args:
        step: Name of the step (e.g. "signal_gen.mtf_macd", "ai_decider.compaction")
        status: "enter" | "ok" | "ERROR" | "SKIP" | "WARN"
        extra: Optional dict with step-specific data (token count, signal type, etc.)
    """
    if not ENABLED:
        return
    
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entry = {
        'ts': ts,
        'step': step,
        'status': status,
        'unixtime': time.time(),
    }
    if extra:
        entry['extra'] = extra
    
    # Log to trading.log
    extra_str = json.dumps(extra) if extra else ''
    log_line = f"[{ts}] [BREAD] {step} | {status} | {extra_str}"
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(log_line + '\n')
    except Exception:
        pass
    
    # Append to breadcrumbs.json for programmatic access
    try:
        crumbs = []
        if os.path.exists(BREADCRUMB_FILE):
            try:
                with open(BREADCRUMB_FILE) as f:
                    crumbs = json.load(f)
            except Exception:
                pass
        
        crumbs.append(entry)
        
        # Keep last 200 breadcrumbs (prune old ones to prevent file growth)
        if len(crumbs) > 200:
            crumbs = crumbs[-200:]
        
        with open(BREADCRUMB_FILE, 'w') as f:
            json.dump(crumbs, f, indent=2)
    except Exception:
        pass

def breadcrumb_trace(step_name: str):
    """
    Decorator for tracing function entry/exit.
    
    Usage:
        @breadcrumb_trace("my_function")
        def my_function(arg):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            BREADCRUMB(step_name, "enter", extra={'args': str(args)[:100]})
            try:
                result = func(*args, **kwargs)
                BREADCRUMB(step_name, "ok")
                return result
            except Exception as e:
                BREADCRUMB(step_name, "ERROR", extra={'error': str(e)[:200], 'trace': traceback.format_exc()[-300:]})
                raise
        return wrapper
    return decorator

def get_last_breadcrumbs(n: int = 20) -> list:
    """Get the last N breadcrumbs for inspection."""
    try:
        if os.path.exists(BREADCRUMB_FILE):
            with open(BREADCRUMB_FILE) as f:
                crumbs = json.load(f)
            return crumbs[-n:]
    except Exception:
        pass
    return []

def get_breadcrumbs_for_step(step_prefix: str, n: int = 10) -> list:
    """Get last N breadcrumbs for a step prefix (e.g. 'signal_gen')."""
    crumbs = get_last_breadcrumbs(100)
    return [c for c in crumbs if c.get('step', '').startswith(step_prefix)][-n:]

def check_step_health(step_prefix: str, max_age_seconds: int = 120) -> dict:
    """
    Check if a pipeline step ran recently.
    
    Returns:
        {'healthy': bool, 'last_run': unixtime, 'age_seconds': float, 'status': str}
    """
    crumbs = get_last_breadcrumbs(100)
    matching = [c for c in crumbs if c.get('step', '').startswith(step_prefix)]
    if not matching:
        return {'healthy': False, 'last_run': None, 'age_seconds': None, 'status': 'NO_BREADCRUMBS'}
    
    last = matching[-1]
    age = time.time() - last.get('unixtime', 0)
    return {
        'healthy': age < max_age_seconds,
        'last_run': last.get('ts'),
        'age_seconds': age,
        'status': last.get('status'),
        'step': last.get('step'),
    }
