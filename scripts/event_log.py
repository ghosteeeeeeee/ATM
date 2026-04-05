"""
event_log.py — Hermes structured event logging system
Implements Claude Code primitive: System event logging separate from conversation logs.
Provides a structured, queryable audit trail for the trading pipeline.
"""
import json
import os
import gzip
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

EVENT_LOG_FILE = '/root/.hermes/data/event-log.jsonl'
MAX_LOG_SIZE_MB = 50
MAX_ARCHIVED_FILES = 10

# ── Event type constants ────────────────────────────────────────────────────
# Use these constants as event_type values for log_event() calls.

# Trade lifecycle
EVENT_TRADE_SUBMITTED   = 'TRADE_SUBMITTED'
EVENT_TRADE_ENTERED     = 'TRADE_ENTERED'
EVENT_TRADE_FAILED      = 'TRADE_FAILED'
EVENT_POSITION_OPEN     = 'POSITION_OPEN'
EVENT_POSITION_CLOSED  = 'POSITION_CLOSED'

# Pipeline lifecycle
EVENT_SIGNAL_APPROVED   = 'SIGNAL_APPROVED'
EVENT_SIGNAL_REJECTED   = 'SIGNAL_REJECTED'
EVENT_SIGNAL_COMPACTED  = 'SIGNAL_COMPACTED'
EVENT_HOTSET_UPDATED    = 'HOTSET_UPDATED'

# Safety / errors
EVENT_CIRCUIT_BREAKER_TRIPPED = 'CIRCUIT_BREAKER_TRIPPED'
EVENT_BUDGET_EXCEEDED    = 'BUDGET_EXCEEDED'
EVENT_API_CALL_FAILED    = 'API_CALL_FAILED'

# Infrastructure
EVENT_CHECKPOINT_WRITTEN  = 'CHECKPOINT_WRITTEN'
EVENT_CHECKPOINT_RECOVERY = 'CHECKPOINT_RECOVERY'

# Regime / state
EVENT_REGIME_CHANGE       = 'REGIME_CHANGE'
EVENT_WORKFLOW_STATE_CHANGE = 'WORKFLOW_STATE_CHANGE'


# ── Core logging function ───────────────────────────────────────────────────

def log_event(
    event_type: str,
    details: dict,
    level: str = 'INFO'
) -> bool:
    """
    Append a structured event to the event log file.

    Args:
        event_type: One of the EVENT_* constants above (e.g. 'TRADE_ENTERED')
        details:    Arbitrary key/value dict with event-specific data
        level:      INFO | WARN | ERROR | DEBUG

    Returns:
        True if written successfully, False otherwise.
        NEVER raises — logging failures must never block the pipeline.
    """
    try:
        _rotate_if_needed()

        entry = {
            'ts': datetime.utcnow().isoformat() + 'Z',
            'event': event_type,
            'level': level.upper(),
            **details
        }

        with open(EVENT_LOG_FILE, 'a') as f:
            f.write(json.dumps(entry) + '\n')

        return True
    except Exception:
        return False


# ── Rotation ───────────────────────────────────────────────────────────────

def _rotate_if_needed():
    """Compress and archive the event log if it exceeds MAX_LOG_SIZE_MB."""
    try:
        if not os.path.exists(EVENT_LOG_FILE):
            return

        size_bytes = os.path.getsize(EVENT_LOG_FILE)
        if size_bytes < MAX_LOG_SIZE_MB * 1024 * 1024:
            return

        # Archive with timestamp
        archive_path = f'{EVENT_LOG_FILE}.{int(time.time())}.gz'
        with open(EVENT_LOG_FILE, 'rb') as f_in:
            with gzip.open(archive_path, 'wb', compresslevel=6) as f_out:
                f_out.write(f_in.read())

        # Truncate original
        with open(EVENT_LOG_FILE, 'w') as f:
            f.write('')

        _prune_archives()
    except Exception:
        pass


def _prune_archives():
    """Remove oldest archives if more than MAX_ARCHIVED_FILES exist."""
    try:
        archives = sorted(
            Path(EVENT_LOG_FILE).parent.glob(f'{Path(EVENT_LOG_FILE).name}.*.gz'),
            key=lambda p: p.stat().st_mtime
        )
        while len(archives) > MAX_ARCHIVED_FILES:
            oldest = archives.pop(0)
            oldest.unlink()
    except Exception:
        pass


# ── Query helpers ───────────────────────────────────────────────────────────

def read_events(
    event_type: str | None = None,
    token: str | None = None,
    since_hours: float = 24,
    limit: int = 500
) -> list[dict]:
    """
    Read recent events, optionally filtered.

    Args:
        event_type: Filter by event type (e.g. 'TRADE_ENTERED')
        token:      Filter by token field in details
        since_hours: Only events within this many hours (default 24)
        limit:      Max events to return (default 500)
    """
    results = []
    cutoff = time.time() - (since_hours * 3600)

    try:
        if not os.path.exists(EVENT_LOG_FILE):
            return results

        # Also check archives
        all_paths = [Path(EVENT_LOG_FILE)]
        all_paths.extend(
            sorted(Path(EVENT_LOG_FILE).parent.glob(f'{Path(EVENT_LOG_FILE).name}.*.gz'))
        )

        for path in all_paths:
            try:
                if path.suffix == '.gz':
                    with gzip.open(path, 'rt') as f:
                        lines = f.readlines()
                else:
                    with open(path, 'r') as f:
                        lines = f.readlines()
            except Exception:
                continue

            for line in lines:
                try:
                    entry = json.loads(line.strip())
                except Exception:
                    continue

                # Parse timestamp
                try:
                    ts = datetime.fromisoformat(entry.get('ts', '').rstrip('Z')).timestamp()
                    if ts < cutoff:
                        continue
                except Exception:
                    continue

                # Apply filters
                if event_type and entry.get('event') != event_type:
                    continue
                if token and entry.get('token') != token and entry.get('details', {}).get('token') != token:
                    continue

                results.append(entry)

                if len(results) >= limit:
                    return results

    except Exception:
        pass

    return results


def event_summary(since_hours: float = 24) -> dict:
    """Return a summary count of events in the period."""
    events = read_events(since_hours=since_hours, limit=10000)
    counts: dict[str, int] = {}
    for e in events:
        t = e.get('event', 'UNKNOWN')
        counts[t] = counts.get(t, 0) + 1
    return counts


# ── Convenience wrappers ────────────────────────────────────────────────────

def log_trade_entered(token: str, direction: str, price: float,
                       confidence: float) -> bool:
    return log_event(EVENT_TRADE_ENTERED, {
        'token': token,
        'direction': direction,
        'price': price,
        'confidence': confidence,
    })


def log_trade_failed(token: str, reason: str) -> bool:
    return log_event(EVENT_TRADE_FAILED, {
        'token': token,
        'reason': reason[:200],
    }, level='ERROR')


def log_hotset_updated(count: int, token_count: int) -> bool:
    return log_event(EVENT_HOTSET_UPDATED, {
        'signal_count': count,
        'hotset_size': token_count,
    })


def log_budget_exceeded(estimated: int, daily_used: int,
                          daily_limit: int, run_limit: int | None = None) -> bool:
    details = {
        'estimated_tokens': estimated,
        'daily_used': daily_used,
        'daily_limit': daily_limit,
    }
    if run_limit is not None:
        details['run_limit'] = run_limit
    return log_event(EVENT_BUDGET_EXCEEDED, details, level='WARN')


def log_api_call(tokens_used: int, model: str = 'MiniMax-M2') -> bool:
    return log_event('API_CALL', {
        'tokens_used': tokens_used,
        'model': model,
    })


def log_checkpoint_recovery(label: str, recovered: bool,
                              details: str = '') -> bool:
    return log_event(EVENT_CHECKPOINT_RECOVERY, {
        'checkpoint_label': label,
        'recovered': recovered,
        'details': details,
    }, level='WARN' if not recovered else 'INFO')
