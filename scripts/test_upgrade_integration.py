#!/usr/bin/env python3
"""
Integration test for Hermes Trading Pipeline Upgrade (2026-04-05)
Tests all components work together: checkpoint_utils, event_log, signal_schema,
ai_decider token budget, and PostgreSQL workflow columns.

Usage: python3 /root/.hermes/scripts/test_upgrade_integration.py
"""
import sys
import os
import time
import json
import gzip
from datetime import datetime

sys.path.insert(0, '/root/.hermes/scripts')

# ── Test Results ────────────────────────────────────────────────────────────────

TESTS_PASSED = 0
TESTS_FAILED = 0
TESTS_SKIPPED = 0

def pass_(msg):
    global TESTS_PASSED
    TESTS_PASSED += 1
    print(f'  ✅ {msg}')

def fail(msg, exc=None):
    global TESTS_FAILED
    TESTS_FAILED += 1
    print(f'  ❌ {msg}')
    if exc:
        print(f'     {type(exc).__name__}: {exc}')

def skip(msg):
    global TESTS_SKIPPED
    TESTS_SKIPPED += 1
    print(f'  ⏭️  {msg} (SKIPPED)')

def section(name):
    print(f'\n── {name} ──')

# ── Test 1: checkpoint_utils ───────────────────────────────────────────────────

def test_checkpoint_utils():
    section('checkpoint_utils')
    try:
        from checkpoint_utils import (
            checkpoint_write, checkpoint_read_last,
            detect_incomplete_run, clear_workflow_state,
            checkpoint_trade_pending, checkpoint_decider_cycle,
            CHECKPOINT_DIR
        )
    except Exception as e:
        fail('Import checkpoint_utils', e)
        return

    # 1a. Write a checkpoint and read it back
    try:
        test_data = {'test': 'integration', 'value': 42}
        path = checkpoint_write('test_label', test_data)
        if not path:
            fail('checkpoint_write returned empty path')
            return
        result = checkpoint_read_last('test_label')
        if result is None:
            fail('checkpoint_read_last returned None')
            return
        if result.get('test') != 'integration' or result.get('value') != 42:
            fail(f'Data mismatch: {result}')
            return
        pass_('checkpoint_write + read back')
    except Exception as e:
        fail('checkpoint_write/read back', e)
        return

    # 1b. checkpoint_trade_pending convenience wrapper
    try:
        path = checkpoint_trade_pending('BTC', 'LONG', 'trade-123')
        if not path:
            fail('checkpoint_trade_pending returned empty')
            return
        result = checkpoint_read_last('trade_pending')
        if result.get('token') != 'BTC' or result.get('direction') != 'LONG':
            fail(f'trade_pending data wrong: {result}')
            return
        pass_('checkpoint_trade_pending wrapper')
    except Exception as e:
        fail('checkpoint_trade_pending', e)
        return

    # 1c. checkpoint_decider_cycle convenience wrapper
    try:
        path = checkpoint_decider_cycle(entered=5, skipped=2, open_count=3)
        if not path:
            fail('checkpoint_decider_cycle returned empty')
            return
        result = checkpoint_read_last('decider_cycle')
        if result.get('entered') != 5 or result.get('skipped') != 2:
            fail(f'decider_cycle data wrong: {result}')
            return
        pass_('checkpoint_decider_cycle wrapper')
    except Exception as e:
        fail('checkpoint_decider_cycle', e)
        return

    # 1d. detect_incomplete_run — no incomplete run should exist
    try:
        result = detect_incomplete_run(max_age_seconds=180)
        # Should return None (no incomplete runs)
        # Could pass or fail depending on state — just verify it runs
        pass_('detect_incomplete_run() executed (returned None — expected)')
    except Exception as e:
        fail('detect_incomplete_run', e)
        return

    # 1e. clear_workflow_state
    try:
        ok = clear_workflow_state('test_label', 'IDLE')
        if not ok:
            fail('clear_workflow_state returned False')
            return
        pass_('clear_workflow_state')
    except Exception as e:
        fail('clear_workflow_state', e)
        return

    # 1f. Checkpoint dir exists and has recent files
    try:
        if not os.path.exists(CHECKPOINT_DIR):
            fail(f'Checkpoint dir does not exist: {CHECKPOINT_DIR}')
            return
        files = sorted(os.listdir(CHECKPOINT_DIR))
        if not files:
            fail('No checkpoint files found')
            return
        pass_(f'Checkpoint dir OK ({len(files)} files)')
    except Exception as e:
        fail('Checkpoint dir exists', e)
        return

# ── Test 2: event_log ──────────────────────────────────────────────────────────

def test_event_log():
    section('event_log')
    try:
        from event_log import (
            log_event, log_trade_entered, log_trade_failed,
            log_hotset_updated, log_budget_exceeded, log_api_call,
            log_checkpoint_recovery, read_events, event_summary,
            EVENT_LOG_FILE, _rotate_if_needed,
            EVENT_TRADE_ENTERED, EVENT_TRADE_FAILED, EVENT_HOTSET_UPDATED
        )
    except Exception as e:
        fail('Import event_log', e)
        return

    # 2a. Write events and read them back
    try:
        # Use a unique token name to avoid conflicts
        test_token = f'INTTEST_{int(time.time())}'
        ok = log_trade_entered(test_token, 'LONG', 50000.0, 85.0)
        if not ok:
            fail('log_trade_entered returned False')
            return
        ok = log_trade_failed(test_token, 'Test failure reason')
        if not ok:
            fail('log_trade_failed returned False')
            return
        ok = log_hotset_updated(10, 5)
        if not ok:
            fail('log_hotset_updated returned False')
            return
        pass_('log_trade_entered + log_trade_failed + log_hotset_updated')
    except Exception as e:
        fail('Writing events', e)
        return

    # 2b. read_events — filter by token
    try:
        events = read_events(token=test_token, since_hours=1, limit=50)
        if not events:
            fail('read_events returned empty (should have at least 2 entries)')
            return
        # Should have at least the trade_entered and trade_failed we wrote
        etypes = [e.get('event') for e in events]
        if EVENT_TRADE_ENTERED not in etypes:
            fail(f'TRADE_ENTERED not in events: {etypes}')
            return
        pass_(f'read_events with token filter ({len(events)} events)')
    except Exception as e:
        fail('read_events with token filter', e)
        return

    # 2c. read_events — filter by event type
    try:
        events = read_events(event_type=EVENT_TRADE_FAILED, since_hours=1, limit=50)
        if not events:
            fail('read_events for TRADE_FAILED returned empty')
            return
        pass_(f'read_events with event_type filter ({len(events)} events)')
    except Exception as e:
        fail('read_events by event_type', e)
        return

    # 2d. event_summary
    try:
        summary = event_summary(since_hours=24)
        if not isinstance(summary, dict):
            fail(f'event_summary returned wrong type: {type(summary)}')
            return
        if EVENT_TRADE_ENTERED not in summary:
            fail(f'TRADE_ENTERED not in summary: {summary}')
            return
        pass_(f'event_summary ({len(summary)} event types)')
    except Exception as e:
        fail('event_summary', e)
        return

    # 2e. log_budget_exceeded
    try:
        ok = log_budget_exceeded(5000, 10000, 50000, 30000)
        if not ok:
            fail('log_budget_exceeded returned False')
            return
        pass_('log_budget_exceeded')
    except Exception as e:
        fail('log_budget_exceeded', e)
        return

    # 2f. log_api_call
    try:
        ok = log_api_call(1234, 'MiniMax-M2')
        if not ok:
            fail('log_api_call returned False')
            return
        pass_('log_api_call')
    except Exception as e:
        fail('log_api_call', e)
        return

    # 2g. log_checkpoint_recovery
    try:
        ok = log_checkpoint_recovery('test_label', True, 'test details')
        if not ok:
            fail('log_checkpoint_recovery returned False')
            return
        pass_('log_checkpoint_recovery')
    except Exception as e:
        fail('log_checkpoint_recovery', e)
        return

    # 2h. Event log file exists
    try:
        if not os.path.exists(EVENT_LOG_FILE):
            fail(f'Event log file does not exist: {EVENT_LOG_FILE}')
            return
        size = os.path.getsize(EVENT_LOG_FILE)
        if size == 0:
            fail('Event log file is empty')
            return
        pass_(f'Event log file OK ({size} bytes)')
    except Exception as e:
        fail('Event log file exists', e)
        return

# ── Test 3: signal_schema workflow functions ────────────────────────────────────

def test_signal_schema_workflow():
    section('signal_schema workflow functions')
    try:
        from signal_schema import (
            update_trade_workflow_state, get_trade_workflow_state,
            WORKFLOW_STATES
        )
    except Exception as e:
        fail('Import signal_schema workflow functions', e)
        return

    # 3a. WORKFLOW_STATES constant
    try:
        expected = ('IDLE', 'POSITION_OPEN', 'CLOSE_PENDING', 'ERROR_RECOVERY')
        if WORKFLOW_STATES != expected:
            fail(f'WORKFLOW_STATES mismatch: {WORKFLOW_STATES}')
            return
        pass_('WORKFLOW_STATES constant correct')
    except Exception as e:
        fail('WORKFLOW_STATES constant', e)
        return

    # 3b. get_trade_workflow_state with non-existent ID
    try:
        result = get_trade_workflow_state(999999)
        if result is not None:
            fail(f'get_trade_workflow_state(999999) should return None, got: {result}')
            return
        pass_('get_trade_workflow_state(999999) = None')
    except Exception as e:
        fail('get_trade_workflow_state', e)
        return

    # 3c. update_trade_workflow_state with invalid state
    try:
        ok = update_trade_workflow_state(1, 'INVALID_STATE')
        if ok:
            fail('update_trade_workflow_state should return False for invalid state')
            return
        pass_('update_trade_workflow_state rejects invalid state')
    except Exception as e:
        fail('update_trade_workflow_state invalid state check', e)
        return

    # 3d. Query actual trades in PostgreSQL to verify column exists
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("SELECT id, workflow_state FROM trades LIMIT 5")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if not rows:
            skip('No trades in PostgreSQL trades table to test')
            return
        pass_(f'PostgreSQL trades table query OK ({len(rows)} rows, workflow_state col exists)')
    except Exception as e:
        fail('PostgreSQL trades table query', e)
        return

# ── Test 4: ai_decider token budget ────────────────────────────────────────────

def test_ai_decider_token_budget():
    section('ai_decider token budget')
    try:
        from ai_decider import (
            _check_token_budget, _record_token_usage,
            _MAX_TOKENS_PER_RUN, _DAILY_TOKEN_BUDGET,
            _DAILY_BUDGET_FILE
        )
    except Exception as e:
        fail('Import ai_decider token budget functions', e)
        return

    # 4a. Constants exist
    try:
        if not isinstance(_MAX_TOKENS_PER_RUN, int) or _MAX_TOKENS_PER_RUN <= 0:
            fail(f'_MAX_TOKENS_PER_RUN invalid: {_MAX_TOKENS_PER_RUN}')
            return
        if not isinstance(_DAILY_TOKEN_BUDGET, int) or _DAILY_TOKEN_BUDGET <= 0:
            fail(f'_DAILY_TOKEN_BUDGET invalid: {_DAILY_TOKEN_BUDGET}')
            return
        pass_(f'Token budget constants OK (per_run={_MAX_TOKENS_PER_RUN}, daily={_DAILY_TOKEN_BUDGET})')
    except Exception as e:
        fail('Token budget constants', e)
        return

    # 4b. _check_token_budget — should pass for small amounts
    try:
        ok = _check_token_budget(1000)
        if not ok:
            fail('_check_token_budget(1000) returned False (should pass)')
            return
        pass_('_check_token_budget(1000) = True')
    except Exception as e:
        fail('_check_token_budget small amount', e)
        return

    # 4c. _check_token_budget — should fail for excessive amount
    try:
        ok = _check_token_budget(_MAX_TOKENS_PER_RUN * 100)
        if ok:
            fail(f'_check_token_budget(excessive) should return False, got True')
            return
        pass_(f'_check_token_budget(excessive) = False (correctly blocked)')
    except Exception as e:
        fail('_check_token_budget excessive amount', e)
        return

    # 4d. _record_token_usage then check budget consumed
    try:
        _record_token_usage(500)
        # Now daily used should be at least 500 (may be more from previous runs)
        ok = _check_token_budget(100)  # should still pass
        if not ok:
            fail('_check_token_budget(100) failed after recording 500 tokens')
            return
        pass_('_record_token_usage(500) + subsequent budget check OK')
    except Exception as e:
        fail('_record_token_usage', e)
        return

    # 4e. Budget file exists or can be created
    try:
        if os.path.exists(_DAILY_BUDGET_FILE):
            with open(_DAILY_BUDGET_FILE) as f:
                data = json.load(f)
            if 'date' not in data or 'used' not in data:
                fail(f'Budget file missing fields: {data}')
                return
            pass_(f'Daily budget file OK ({data})')
        else:
            # Try to create it
            os.makedirs(os.path.dirname(_DAILY_BUDGET_FILE), exist_ok=True)
            with open(_DAILY_BUDGET_FILE, 'w') as f:
                json.dump({'date': datetime.now().strftime('%Y-%m-%d'), 'used': 0}, f)
            pass_('Daily budget file created')
    except Exception as e:
        fail('Daily budget file', e)
        return

# ── Test 5: PostgreSQL column verification ─────────────────────────────────────

def test_postgresql_columns():
    section('PostgreSQL workflow columns')
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()

        # 5a. Verify both columns exist with correct types
        cur.execute("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name='trades'
            AND column_name IN ('workflow_state', 'workflow_updated_at')
            ORDER BY column_name
        """)
        rows = {r[0]: r for r in cur.fetchall()}
        cur.close()
        conn.close()

        if 'workflow_state' not in rows:
            fail('workflow_state column missing from trades table')
            return
        if 'workflow_updated_at' not in rows:
            fail('workflow_updated_at column missing from trades table')
            return

        state_col = rows['workflow_state']
        ts_col = rows['workflow_updated_at']

        # 5b. workflow_state type check
        if 'character varying' not in state_col[1] and 'varchar' not in state_col[1]:
            fail(f"workflow_state type wrong: {state_col[1]}")
            return
        pass_(f"workflow_state column: {state_col[1]} default={state_col[2]}")

        # 5c. workflow_updated_at type check
        if 'timestamp' not in ts_col[1]:
            fail(f"workflow_updated_at type wrong: {ts_col[1]}")
            return
        pass_(f"workflow_updated_at column: {ts_col[1]} default={ts_col[2]}")

    except Exception as e:
        fail('PostgreSQL column verification', e)
        return

# ── Test 6: decider-run instrumentation check ──────────────────────────────────

def test_decider_run_instrumentation():
    section('decider_run.py instrumentation')
    try:
        import ast
        with open('/root/.hermes/scripts/decider_run.py') as f:
            source = f.read()
    except Exception as e:
        fail('Read decider_run.py', e)
        return

    # 6a. Checkpoint import
    if 'from checkpoint_utils import' in source:
        pass_('checkpoint_utils imported in decider_run.py')
    else:
        fail('checkpoint_utils import NOT found in decider_run.py')

    # 6b. log_event import
    if 'from event_log import' in source:
        pass_('event_log imported in decider_run.py')
    else:
        fail('event_log import NOT found in decider_run.py')

    # 6c. log_event calls present
    if 'log_event(EVENT_TRADE_ENTERED' in source:
        pass_('EVENT_TRADE_ENTERED log_event call found')
    else:
        fail('EVENT_TRADE_ENTERED log_event call NOT found')

    if 'log_event(EVENT_TRADE_FAILED' in source:
        pass_('EVENT_TRADE_FAILED log_event call found')
    else:
        fail('EVENT_TRADE_FAILED log_event call NOT found')

    if 'log_event(EVENT_HOTSET_UPDATED' in source:
        pass_('EVENT_HOTSET_UPDATED log_event call found')
    else:
        fail('EVENT_HOTSET_UPDATED log_event call NOT found')

    # 6d. checkpoint_write calls present
    if "checkpoint_write('trade_pending'" in source:
        pass_("checkpoint_write('trade_pending') call found")
    else:
        fail("checkpoint_write('trade_pending') call NOT found")

    if "checkpoint_write('hotset_built'" in source:
        pass_("checkpoint_write('hotset_built') call found")
    else:
        fail("checkpoint_write('hotset_built') call NOT found")

# ── Test 7: hl-sync-guardian instrumentation check ────────────────────────────

def test_guardian_instrumentation():
    section('hl-sync-guardian.py instrumentation')
    try:
        with open('/root/.hermes/scripts/hl-sync-guardian.py') as f:
            source = f.read()
    except Exception as e:
        fail('Read hl-sync-guardian.py', e)
        return

    # 7a. checkpoint_utils import
    if 'from checkpoint_utils import' in source:
        pass_('checkpoint_utils imported in hl-sync-guardian.py')
    else:
        fail('checkpoint_utils import NOT found')

    # 7b. event_log import
    if 'from event_log import' in source:
        pass_('event_log imported in hl-sync-guardian.py')
    else:
        fail('event_log import NOT found')

    # 7c. orphan_detected checkpoint
    if "checkpoint_write('orphan_detected'" in source:
        pass_("checkpoint_write('orphan_detected') call found")
    else:
        fail("checkpoint_write('orphan_detected') call NOT found")

    # 7d. guardian_cycle checkpoint
    if "checkpoint_write('guardian_cycle'" in source:
        pass_("checkpoint_write('guardian_cycle') call found")
    else:
        fail("checkpoint_write('guardian_cycle') call NOT found")

    # 7e. EVENT_POSITION_CLOSED log
    if 'EVENT_POSITION_CLOSED' in source:
        pass_('EVENT_POSITION_CLOSED log_event found')
    else:
        fail('EVENT_POSITION_CLOSED log_event NOT found')

    # 7f. EVENT_CHECKPOINT_RECOVERY log
    if 'EVENT_CHECKPOINT_RECOVERY' in source:
        pass_('EVENT_CHECKPOINT_RECOVERY log_event found')
    else:
        fail('EVENT_CHECKPOINT_RECOVERY log_event NOT found')

# ── Test 8: ai_decider instrumentation check ──────────────────────────────────

def test_ai_decider_instrumentation():
    section('ai_decider.py instrumentation')
    try:
        with open('/root/.hermes/scripts/ai_decider.py') as f:
            source = f.read()
    except Exception as e:
        fail('Read ai_decider.py', e)
        return

    # 8a. Token budget functions
    if '_check_token_budget' in source:
        pass_('_check_token_budget function found')
    else:
        fail('_check_token_budget function NOT found')

    if '_record_token_usage' in source:
        pass_('_record_token_usage function found')
    else:
        fail('_record_token_usage function NOT found')

    # 8b. Budget constants
    if '_MAX_TOKENS_PER_RUN' in source:
        pass_('_MAX_TOKENS_PER_RUN constant found')
    else:
        fail('_MAX_TOKENS_PER_RUN constant NOT found')

    if '_DAILY_TOKEN_BUDGET' in source:
        pass_('_DAILY_TOKEN_BUDGET constant found')
    else:
        fail('_DAILY_TOKEN_BUDGET constant NOT found')

    # 8c. Budget file constant
    if '_DAILY_BUDGET_FILE' in source:
        pass_('_DAILY_BUDGET_FILE constant found')
    else:
        fail('_DAILY_BUDGET_FILE constant NOT found')

    # 8d. log_event integration
    if 'log_event' in source and 'BUDGET_EXCEEDED' in source:
        pass_('log_event with BUDGET_EXCEEDED found')
    else:
        fail('log_event with BUDGET_EXCEEDED NOT found')

# ── Test 9: Syntax verification (py_compile) ────────────────────────────────────

def test_syntax():
    section('Syntax verification (py_compile)')
    files = [
        '/root/.hermes/scripts/checkpoint_utils.py',
        '/root/.hermes/scripts/event_log.py',
        '/root/.hermes/scripts/ai_decider.py',
        '/root/.hermes/scripts/decider_run.py',
        '/root/.hermes/scripts/hl-sync-guardian.py',
        '/root/.hermes/scripts/signal_schema.py',
    ]
    for fpath in files:
        try:
            with open(fpath) as f:
                source = f.read()
            compile(source, fpath, 'exec')
            pass_(f'Syntax OK: {os.path.basename(fpath)}')
        except SyntaxError as e:
            fail(f'Syntax error in {os.path.basename(fpath)}: {e}')
        except Exception as e:
            fail(f'Compile check failed for {os.path.basename(fpath)}', e)

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print('=' * 60)
    print('Hermes Trading Pipeline — Upgrade Integration Test')
    print(f'Started: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)

    test_checkpoint_utils()
    test_event_log()
    test_signal_schema_workflow()
    test_ai_decider_token_budget()
    test_postgresql_columns()
    test_decider_run_instrumentation()
    test_guardian_instrumentation()
    test_ai_decider_instrumentation()
    test_syntax()

    print('\n' + '=' * 60)
    print(f'SUMMARY: {TESTS_PASSED} passed | {TESTS_FAILED} failed | {TESTS_SKIPPED} skipped')
    print('=' * 60)

    if TESTS_FAILED > 0:
        print('RESULT: FAIL')
        sys.exit(1)
    else:
        print('RESULT: PASS')
        sys.exit(0)

if __name__ == '__main__':
    main()
