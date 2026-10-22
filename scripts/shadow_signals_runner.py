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

# Maps signal keys to their ENABLED flag name
ENABLED_FLAG_MAP = {
    'bb-squeeze-': 'BOLLINGER_SQUEEZE_MINUS_ENABLED',
    'bb-bounce-v3-long': 'BB_BOUNCE_V3_LONG_ENABLED',
    'volume-breakout-long': 'VOLUME_BREAKOUT_LONG_ENABLED',
    'hmacd_mtf-+': 'HMACD_MTF_PLUS_ENABLED',
    'doji-bottom-long': 'DOJI_BOTTOM_LONG_ENABLED',
    'open-skies+': 'OPEN_SKIES_PLUS_ENABLED',
    'squeeze-cross+': 'SQUEEZE_CROSS_PLUS_ENABLED',
    'squeeze-cross-': 'SQUEEZE_CROSS_MINUS_ENABLED',
    'rs-broken-short': 'RS_BROKEN_SHORT_ENABLED',
    'rs-broken-resistance-long': 'RS_BROKEN_RESISTANCE_LONG_ENABLED',
    'vel-hermes+': 'VEL_HERMES_PLUS_ENABLED',
    'vel-hermes-': 'VEL_HERMES_MINUS_ENABLED',
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


def run_shadow_signal(signal_key, module_path, flag_name, stage, reason):
    """Run a single signal detector in shadow mode."""
    try:
        # Import the signal module
        mod = importlib.import_module(module_path)
        
        # Get the original flag value
        original_flag = getattr(mod, flag_name, None)
        if original_flag is None:
            # Flag might be in hermes_constants, not in the module
            import hermes_constants as hc
            original_flag = getattr(hc, flag_name, None)
        
        # Override the flag to True
        if hasattr(mod, flag_name):
            setattr(mod, flag_name, True)
        
        # Monkey-patch add_signal to capture instead of writing to live DB
        import signal_schema
        original_add_signal = signal_schema.add_signal
        captured_signals = []
        
        def capture_add_signal(**kwargs):
            """Capture signal instead of writing to live DB."""
            shadow_id = f"shadow_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{kwargs.get('token', 'unknown')}"
            captured_signals.append({
                'shadow_id': shadow_id,
                'token': kwargs.get('token'),
                'direction': kwargs.get('direction'),
                'signal_type': kwargs.get('signal_type'),
                'source': kwargs.get('source'),
                'confidence': kwargs.get('confidence'),
                'created_at': datetime.now(timezone.utc).isoformat(),
            })
            return shadow_id  # Return fake ID
        
        signal_schema.add_signal = capture_add_signal
        
        # Also patch the module's reference if it imported add_signal directly
        if hasattr(mod, 'add_signal'):
            mod.add_signal = capture_add_signal
        
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
        
        # Record captured signals to shadow
        n_recorded = 0
        for sig in captured_signals:
            if record_to_shadow(sig, stage, reason):
                n_recorded += 1
        
        # Restore original add_signal
        signal_schema.add_signal = original_add_signal
        if hasattr(mod, 'add_signal'):
            mod.add_signal = original_add_signal
        
        # Restore original flag
        if hasattr(mod, flag_name) and original_flag is not None:
            setattr(mod, flag_name, original_flag)
        
        if n_recorded > 0:
            log(f"  {signal_key}: ✅ {n_recorded} signals recorded to shadow")
        else:
            log(f"  {signal_key}: 0 signals (detector ran but found nothing)")
        
        return n_recorded
        
    except ImportError as e:
        log(f"  {signal_key}: Could not import {module_path}: {e}")
        return 0
    except Exception as e:
        log(f"  {signal_key}: ERROR: {e}")
        return 0


def main():
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
    
    for signal_key, info in registry.items():
        stage = info.get('stage', '?')
        reason = info.get('reason', '')
        direction = info.get('direction', '')
        
        # Filter by stage
        if args.stage and stage != args.stage:
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
        
        n = run_shadow_signal(signal_key, module_path, flag_name, stage, reason)
        total_recorded += n
        if n == 0:
            total_errors += 1
    
    if args.dry_run:
        log("\n(dry-run — no signals executed)")
    else:
        log("\n" + "=" * 60)
        log(f"DONE: {total_recorded} signals recorded, {total_skipped} skipped, {total_errors} errors")
        log("=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
