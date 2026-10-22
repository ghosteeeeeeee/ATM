#!/usr/bin/env python3
"""shadow_signals_runner.py — Run disabled signal detectors in shadow mode.

T directive 2026-10-21: "turn on all our old signals in shadow-mode."
CEO approved: shadow-only, staged rollout, zero live-flag changes.

This runner:
1. Reads SHADOW_BYPASS_SIGNALS registry (Stage A/C disabled signals)
2. For each signal, imports the detector module
3. Temporarily overrides the *_ENABLED flag to True
4. Monkey-patches add_signal() to capture instead of writing to live DB
5. Runs the detector
6. Records captured signals to shadow_trader with shadow_bypass=true tag
7. Restores everything

ZERO impact on live trading — no flags changed in hermes_constants.py,
no writes to the live signals DB.

Usage:
  python3 scripts/shadow_signals_runner.py              # Run all Stage A+C
  python3 scripts/shadow_signals_runner.py --stage A    # Run only Stage A
  python3 scripts/shadow_signals_runner.py --stage C    # Run only Stage C
  python3 scripts/shadow_signals_runner.py --dry-run    # Show what would run
"""
import sys
import os
import json
import argparse
import importlib
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

SHADOW_DB = os.path.join(os.path.dirname(HERMES_DATA), 'brain', 'shadow_trades.db')

def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [shadow_signals_runner] {msg}', flush=True)


# ── Signal module mapping ─────────────────────────────────────────────────────
# Maps SHADOW_BYPASS_SIGNALS keys to their signal module files
SIGNAL_MODULE_MAP = {
    # Stage A
    'bb-squeeze-': 'signals.bollinger_squeeze',
    'bb-bounce-v3-long': 'signals.bb_bounce_v3_long',
    'volume-breakout-long': 'signals.volume_breakout',
    'hmacd_mtf-+': 'signals.mtf_macd',
    'doji-bottom-long': 'signals.doji_bottom',
    # Stage B (already firing — skip)
    'ichimoku-': None,
    'ichimoku+': None,
    'rs-r': None,
    'rs-s': None,
    # Stage C
    'open-skies+': 'signals.open_skies',
    'squeeze-cross+': 'signals.squeeze_cross',
    'squeeze-cross-': 'signals.squeeze_cross',
    'rs-broken-short': 'signals.rs',
    'rs-broken-resistance-long': 'signals.rs',
    'vel-hermes+': None,  # Module removed — no detector to run
    'vel-hermes-': None,  # Module removed — no detector to run
}

# bug_hunter HIGH-5: only record signals that match the registry key's
# expected source path + direction. Whole-module runs also emit LIVE-enabled
# paths (e.g. rs.py emits rs-s126 alongside rs-s-broken) — without this
# filter those pollute the shadow-bypass cohort with live-eligible signals.
# Match rule: direction must equal registry direction AND some comma-part of
# source must contain one of the listed substrings. Empty tuple = any source.
SOURCE_FILTERS = {
    'bb-squeeze-': ('bb-squeeze-',),
    'bb-bounce-v3-long': ('bb-bounce-v3-long',),
    'volume-breakout-long': ('volume-breakout-long+',),
    'hmacd_mtf-+': ('hmacd_mtf-+',),
    'doji-bottom-long': ('doji-bottom-long',),
    'open-skies+': ('open-skies+',),
    'squeeze-cross+': ('sqx+', 'squeeze-cross+'),
    'squeeze-cross-': ('sqx-', 'squeeze-cross-'),
    'rs-broken-short': ('rs-s-broken',),
    'rs-broken-resistance-long': ('rs-r-broken',),
}

# Maps signal keys to their ENABLED flag name
ENABLED_FLAG_MAP = {
    'bb-squeeze-': 'BOLLINGER_SQUEEZE_MINUS_ENABLED',
    'bb-bounce-v3-long': 'BB_BOUNCE_V3_LONG_ENABLED',
    'volume-breakout-long': 'VOLUME_BREAKOUT_PLUS_ENABLED',  # bug_hunter: correct flag name
    'hmacd_mtf-+': 'HMACD_MTF_PLUS_ENABLED',
    'doji-bottom-long': 'DOJI_BOTTOM_ENABLED',  # bug_hunter: correct flag name
    'open-skies+': 'OPEN_SKIES_PLUS_ENABLED',
    'squeeze-cross+': 'SQUEEZE_CROSS_PLUS_ENABLED',
    'squeeze-cross-': 'SQUEEZE_CROSS_MINUS_ENABLED',
    'rs-broken-short': 'RS_BROKEN_SHORT_ENABLED',
    'rs-broken-resistance-long': 'RS_BROKEN_RESISTANCE_LONG_ENABLED',
    'vel-hermes+': None,  # Module removed
    'vel-hermes-': None,  # Module removed
}


def get_shadow_registry():
    """Load SHADOW_BYPASS_SIGNALS from hermes_constants."""
    try:
        from hermes_constants import SHADOW_BYPASS_SIGNALS, SHADOW_BYPASS_ENABLED
        if not SHADOW_BYPASS_ENABLED:
            log("SHADOW_BYPASS_ENABLED is False — exiting")
            return {}
        return SHADOW_BYPASS_SIGNALS
    except ImportError:
        log("ERROR: Could not load SHADOW_BYPASS_SIGNALS")
        return {}


def record_to_shadow(signal_data, stage, reason):
    """Record a signal to shadow_trades.db with shadow_bypass=true tag."""
    import sqlite3
    conn = sqlite3.connect(SHADOW_DB, timeout=30)
    try:
        cur = conn.cursor()
        
        # Check if already recorded
        existing = cur.execute(
            "SELECT id FROM shadow_trades WHERE signal_id = ?",
            (signal_data.get('shadow_id'),)
        ).fetchone()
        if existing:
            return False
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Build context with shadow_bypass tag
        context = {
            'shadow_bypass': True,
            'shadow_bypass_reason': reason,
            'shadow_bypass_stage': stage,
            'shadow_signals_runner': True,
            'context_computed_at': now,
            'vol_regime': 'UNKNOWN',  # Will be filled by close_events
            'atr_pct': None,
        }
        
        cur.execute("""
            INSERT OR IGNORE INTO shadow_trades 
            (signal_id, token, direction, signal_type, source, confidence,
             created_at, recorded_at, context_computed_at, context,
             decision, decision_reason, gate_blocked, gate_name)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            signal_data.get('shadow_id'),
            signal_data.get('token'),
            signal_data.get('direction'),
            signal_data.get('signal_type'),
            signal_data.get('source'),
            signal_data.get('confidence'),
            signal_data.get('created_at', now),
            now, now, json.dumps(context),
            'SHADOW_BYPASS',  # decision
            f'shadow_bypass:{reason[:100]}',  # decision_reason
            0,  # gate_blocked (shadow signals bypass gates)
            'SHADOW-BYPASS',  # gate_name
        ))
        
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        log(f"ERROR recording to shadow: {e}")
        return False
    finally:
        conn.close()


def _sig_matches_registry(sig, signal_key, expected_direction):
    """bug_hunter HIGH-5: direction + source-path filter before shadow record."""
    exp_dir = (expected_direction or '').upper()
    got_dir = (sig.get('direction') or '').upper()
    if exp_dir and got_dir != exp_dir:
        return False
    filters = SOURCE_FILTERS.get(signal_key)
    if not filters:
        return True
    src = (sig.get('source') or '').lower()
    parts = [p.strip().lower() for p in src.split(',') if p.strip()]
    for part in parts:
        for needle in filters:
            if needle in part:
                return True
    return False


def run_shadow_signal(signal_key, module_path, flag_name, stage, reason, direction=''):
    """Run a single signal detector in shadow mode."""
    # bug_hunter fixes:
    # HIGH-1: no-op set_cooldown/clear_cooldown during run (prevent live writes)
    # HIGH-3: created_at must match shadow_trader format ('%Y-%m-%d %H:%M:%S')
    # MEDIUM: try/finally around all patches
    
    import signal_schema
    
    # Store originals
    original_add_signal = signal_schema.add_signal
    original_set_cooldown = getattr(signal_schema, 'set_cooldown', None)
    original_clear_cooldown = getattr(signal_schema, 'clear_cooldown', None)
    captured_signals = []
    
    # No-op cooldown functions (bug_hunter HIGH-1)
    def noop_set_cooldown(*args, **kwargs):
        pass  # Do not write live cooldowns
    
    def noop_clear_cooldown(*args, **kwargs):
        pass  # Do not clear live cooldowns
    
    def capture_add_signal(**kwargs):
        """Capture signal instead of writing to live DB."""
        shadow_id = f"shadow_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{kwargs.get('token', 'unknown')}"
        # bug_hunter HIGH-3: use consistent date format
        now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        captured_signals.append({
            'shadow_id': shadow_id,
            'token': kwargs.get('token'),
            'direction': kwargs.get('direction'),
            'signal_type': kwargs.get('signal_type'),
            'source': kwargs.get('source'),
            'confidence': kwargs.get('confidence'),
            'created_at': now_str,  # Fixed: matches shadow_trader's strptime
        })
        return shadow_id  # Return fake ID
    
    mod = None
    original_flag = None
    original_master_flag = None
    master_flag_name = None
    
    try:
        # Import the signal module
        mod = importlib.import_module(module_path)
        
        # Get the original flag value
        original_flag = getattr(mod, flag_name, None)
        if original_flag is None:
            import hermes_constants as hc
            original_flag = getattr(hc, flag_name, None)
        
        # bug_hunter HIGH-2: also override master flag if it exists
        # Map to master flag name
        MASTER_FLAG_MAP = {
            'bb-squeeze-': 'BOLLINGER_SQUEEZE_ENABLED',
            'volume-breakout-long': 'VOLUME_BREAKOUT_ENABLED',
            'doji-bottom-long': 'DOJI_BOTTOM_ENABLED',  # bug_hunter: correct master flag
            'open-skies+': 'OPEN_SKIES_ENABLED',
            'squeeze-cross+': 'SQUEEZE_CROSS_ENABLED',
            'squeeze-cross-': 'SQUEEZE_CROSS_ENABLED',
        }
        master_flag_name = MASTER_FLAG_MAP.get(signal_key)
        if master_flag_name:
            import hermes_constants as hc
            original_master_flag = getattr(hc, master_flag_name, None)
            # Also check module
            if hasattr(mod, master_flag_name):
                setattr(mod, master_flag_name, True)
            # Also set in hermes_constants (module may read from there)
            if original_master_flag is not None:
                setattr(hc, master_flag_name, True)
        
        # Override the specific flag
        if hasattr(mod, flag_name):
            setattr(mod, flag_name, True)
        
        # Also override in hermes_constants if flag exists there
        import hermes_constants as hc
        if getattr(hc, flag_name, None) is not None:
            setattr(hc, flag_name, True)
        
        # Apply all patches
        signal_schema.add_signal = capture_add_signal
        if original_set_cooldown:
            signal_schema.set_cooldown = noop_set_cooldown
        if original_clear_cooldown:
            signal_schema.clear_cooldown = noop_clear_cooldown
        
        # Also patch module's references if it imported them directly
        if hasattr(mod, 'add_signal'):
            mod.add_signal = capture_add_signal
        if hasattr(mod, 'set_cooldown'):
            mod.set_cooldown = noop_set_cooldown
        
        # Run the signal detector
        try:
            if hasattr(mod, 'run'):
                result = mod.run()
            elif hasattr(mod, 'scan'):
                result = mod.scan()
            else:
                log(f"  {signal_key}: No run() or scan() function found")
                result = None
        except Exception as e:
            log(f"  {signal_key}: ERROR running detector: {e}")
            result = None
        
        # Record captured signals to shadow (HIGH-5: filter to registry path+dir)
        n_recorded = 0
        n_filtered = 0
        for sig in captured_signals:
            if not _sig_matches_registry(sig, signal_key, direction):
                n_filtered += 1
                continue
            if record_to_shadow(sig, stage, reason):
                n_recorded += 1

        if n_recorded > 0:
            log(f"  {signal_key}: ✅ {n_recorded} signals recorded to shadow"
                + (f" ({n_filtered} filtered as wrong source/dir)" if n_filtered else ""))
        elif n_filtered:
            log(f"  {signal_key}: 0 signals ({n_filtered} captured but filtered — "
                f"wrong source/dir for this registry key)")
        else:
            log(f"  {signal_key}: 0 signals (detector ran but found nothing)")

        return ('recorded', n_recorded) if n_recorded else (
            ('filtered', 0) if n_filtered else ('empty', 0))

    except ImportError as e:
        log(f"  {signal_key}: Could not import {module_path}: {e}")
        return ('import_error', 0)
    except Exception as e:
        log(f"  {signal_key}: ERROR: {e}")
        return ('run_error', 0)
    finally:
        # bug_hunter MEDIUM: try/finally ensures all patches are restored
        signal_schema.add_signal = original_add_signal
        if original_set_cooldown:
            signal_schema.set_cooldown = original_set_cooldown
        if original_clear_cooldown:
            signal_schema.clear_cooldown = original_clear_cooldown
        
        if mod:
            if hasattr(mod, 'add_signal'):
                mod.add_signal = original_add_signal
            if original_flag is not None and hasattr(mod, flag_name):
                setattr(mod, flag_name, original_flag)
            if master_flag_name and original_master_flag is not None and hasattr(mod, master_flag_name):
                setattr(mod, master_flag_name, original_master_flag)
        
        # Restore hermes_constants flags
        import hermes_constants as hc
        if original_flag is not None and getattr(hc, flag_name, None) is not None:
            setattr(hc, flag_name, original_flag)
        if master_flag_name and original_master_flag is not None:
            setattr(hc, master_flag_name, original_master_flag)


def main():
    # Check shadow-mode flag first (T directive 2026-10-22)
    # bug_hunter LOW: fail CLOSED if flag cannot be resolved (was pass = fail-open)
    try:
        from hermes_constants import SHADOW_SIGNALS_RUNNER_ENABLED
        if not SHADOW_SIGNALS_RUNNER_ENABLED:
            log("SHADOW_SIGNALS_RUNNER_ENABLED is False — exiting")
            return 0
    except ImportError:
        log("ERROR: SHADOW_SIGNALS_RUNNER_ENABLED not found — fail-closed, exiting")
        return 0
    
    # bug_hunter MEDIUM: use SHADOW_SIGNALS_RUNNER_STAGES config
    try:
        from hermes_constants import SHADOW_SIGNALS_RUNNER_STAGES
        allowed_stages = SHADOW_SIGNALS_RUNNER_STAGES
    except ImportError:
        allowed_stages = ('A', 'C')  # Default
    
    ap = argparse.ArgumentParser(description='Shadow Signals Runner')
    ap.add_argument('--stage', choices=['A', 'B', 'C'], help='Run only this stage')
    ap.add_argument('--dry-run', action='store_true', help='Show what would run')
    args = ap.parse_args()
    
    registry = get_shadow_registry()
    if not registry:
        return 1
    
    log("=" * 60)
    log("SHADOW SIGNALS RUNNER")
    log(f"Registry: {len(registry)} signals")
    log("=" * 60)
    
    total_recorded = 0
    total_skipped = 0
    total_errors = 0
    total_empty = 0
    total_filtered = 0

    for signal_key, info in registry.items():
        stage = info.get('stage', '?')
        reason = info.get('reason', '')
        direction = info.get('direction', '')

        # Filter by stage (CLI arg overrides config)
        if args.stage:
            if stage != args.stage:
                continue
        elif stage not in allowed_stages:
            total_skipped += 1
            continue

        # Skip Stage B (already firing)
        if stage == 'B':
            total_skipped += 1
            continue

        module_path = SIGNAL_MODULE_MAP.get(signal_key)
        flag_name = ENABLED_FLAG_MAP.get(signal_key)

        if not module_path or not flag_name:
            log(f"  {signal_key}: No module or flag mapping — skipped")
            total_skipped += 1
            continue

        if args.dry_run:
            log(f"  Stage {stage} | {signal_key:25} -> {module_path} ({flag_name})")
            continue

        status, n = run_shadow_signal(signal_key, module_path, flag_name, stage, reason, direction)
        total_recorded += n
        if status == 'run_error' or status == 'import_error':
            total_errors += 1
        elif status == 'empty':
            total_empty += 1
        elif status == 'filtered':
            total_filtered += 1

    if args.dry_run:
        log("\n(dry-run — no signals executed)")
    else:
        log("\n" + "=" * 60)
        log(f"DONE: {total_recorded} recorded, {total_skipped} skipped, "
            f"{total_empty} empty, {total_filtered} filtered, {total_errors} errors")
        log("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
