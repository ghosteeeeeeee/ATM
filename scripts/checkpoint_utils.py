"""
checkpoint_utils.py — Hermes pipeline checkpoint system
Implements Claude Code primitive: Session persistence that survives crashes.
Snapshot pipeline state before each major step.
"""
import json
import os
import time
from pathlib import Path
from datetime import datetime

CHECKPOINT_DIR = '/root/.hermes/checkpoints'
MAX_SNAPSHOTS = 50

# ── Low-level checkpoint I/O ────────────────────────────────────────────────

def checkpoint_write(label: str, data: dict) -> str:
    """
    Write a named checkpoint snapshot.
    Returns the path. Prunes old snapshots if over MAX_SNAPSHOTS.
    NEVER raises — checkpoint failures must never block the pipeline.
    """
    try:
        os.makedirs(CHECKPOINT_DIR, exist_ok=True)
        ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        path = f'{CHECKPOINT_DIR}/{ts}_{label}.json'
        entry = {
            'ts': datetime.utcnow().isoformat() + 'Z',
            'label': label,
            **data
        }
        with open(path, 'w') as f:
            json.dump(entry, f, indent=2)
        _prune_checkpoints()
        return path
    except Exception:
        return ''


def checkpoint_read_last(label: str) -> dict | None:
    """Read the most recent checkpoint for a given label. Returns None if not found."""
    try:
        files = sorted(Path(CHECKPOINT_DIR).glob(f'*_{label}.json'))
        if not files:
            return None
        with open(files[-1]) as f:
            return json.load(f)
    except Exception:
        return None


def checkpoint_list(label: str | None = None, limit: int = 20) -> list[dict]:
    """List recent checkpoints, optionally filtered by label."""
    try:
        pattern = f'*{label}*.json' if label else '*.json'
        files = sorted(Path(CHECKPOINT_DIR).glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        results = []
        for f in files[:limit]:
            try:
                with open(f) as fp:
                    results.append(json.load(fp))
            except Exception:
                pass
        return results
    except Exception:
        return []


def _prune_checkpoints():
    """Keep only the last MAX_SNAPSHOTS. Safe to call after every write."""
    try:
        files = sorted(
            Path(CHECKPOINT_DIR).glob('*.json'),
            key=lambda p: p.stat().st_mtime
        )
        while len(files) > MAX_SNAPSHOTS:
            oldest = files.pop(0)
            oldest.unlink()
    except Exception:
        pass


# ── Crash recovery ─────────────────────────────────────────────────────────

def detect_incomplete_run(max_age_seconds: int = 180) -> dict | None:
    """
    On startup, check for a pipeline run that was interrupted mid-trade.
    Returns the incomplete checkpoint if:
      - workflow_state is TRADE_PENDING or SIGNAL_DETECTED
      - checkpoint is older than max_age_seconds
    Returns None if no incomplete run detected.
    """
    try:
        files = sorted(
            Path(CHECKPOINT_DIR).glob('*.json'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        if not files:
            return None

        with open(files[0]) as f:
            last = json.load(f)

        state = last.get('workflow_state', 'IDLE')
        ts_str = last.get('ts', '')

        try:
            ts_epoch = datetime.fromisoformat(ts_str.rstrip('Z')).timestamp()
        except Exception:
            return None

        age = time.time() - ts_epoch

        if state in ('TRADE_PENDING', 'SIGNAL_DETECTED') and age > max_age_seconds:
            return last
    except Exception:
        pass
    return None


def get_last_trade_checkpoint() -> dict | None:
    """Convenience: get the most recent trade_submitted checkpoint."""
    return checkpoint_read_last('trade_submitted')


def clear_workflow_state(label: str, new_state: str = 'IDLE') -> bool:
    """
    Write a checkpoint marking the workflow as cleared/new state.
    Used after successful recovery to reset the incomplete-run marker.
    """
    try:
        checkpoint_write('workflow_reset', {
            'workflow_state': new_state,
            'cleared_label': label,
            'cleared_at': datetime.utcnow().isoformat() + 'Z'
        })
        return True
    except Exception:
        return False


# ── Convenience wrappers for common checkpoint patterns ─────────────────────

def checkpoint_decider_cycle(entered: int = 0, skipped: int = 0,
                              open_count: int = 0) -> str:
    """Standard checkpoint at start/end of a decider-run cycle."""
    return checkpoint_write('decider_cycle', {
        'workflow_state': 'CYCLE_COMPLETE',
        'entered': entered,
        'skipped': skipped,
        'open_count': open_count,
    })


def checkpoint_trade_pending(token: str, direction: str,
                              trade_id: str = '') -> str:
    """Checkpoint written just after a trade is submitted to HL."""
    return checkpoint_write('trade_pending', {
        'workflow_state': 'TRADE_PENDING',
        'token': token,
        'direction': direction,
        'trade_id': trade_id,
    })


def checkpoint_guardian_cycle(open_trade_count: int = 0,
                               workflow_state: str = 'IDLE') -> str:
    """Standard checkpoint for hl-sync-guardian cycle start."""
    return checkpoint_write('guardian_cycle', {
        'workflow_state': workflow_state,
        'open_trade_count': open_trade_count,
    })


def checkpoint_orphan_detected(token: str, trade_id: int | None = None,
                                action: str = 'RECONCILING') -> str:
    """Checkpoint written when guardian finds an orphan HL position."""
    return checkpoint_write('orphan_detected', {
        'workflow_state': 'ERROR_RECOVERY',
        'token': token,
        'trade_id': trade_id,
        'action': action,
    })
