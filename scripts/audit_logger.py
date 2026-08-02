#!/usr/bin/env python3
"""
audit_logger.py — Centralized audit trail for the Hermes trading system.

Writes one JSON object per line to /var/www/hermes/data/audit.log.
Every trade lifecycle event is captured here — no exceptions.

Event types:
  TRADE_OPEN_ATTEMPT   — add_trade() called (before success/fail known)
  TRADE_OPEN_SUCCESS    — DB INSERT succeeded, HL confirmed
  TRADE_OPEN_FAILED     — DB INSERT failed (HL may or may not be rolled back)
  TRADE_CLOSE           — any close_paper_position() call
  TRADE_ORPHAN_DETECTED — guardian found HL position with no DB record
  TRADE_ORPHAN_CREATED  — guardian created orphan paper trade
  TRADE_ORPHAN_CLOSED   — guardian closed orphan HL position
  LOSS_COOLDOWN_SET     — set_loss_cooldown() called
  SIGNAL_BLOCKED        — signal suppressed (cooldown, regime, blacklist, etc.)
  ATR_SL_HIT           — ATR trailing SL triggered
  ATR_TP_HIT            — ATR trailing TP triggered
  ATR_CHECK             — ATR check performed (debug, every cycle)
  GUARDIAN_CYCLE        — guardian sync cycle summary
"""

import os, json, time
from datetime import datetime, timezone

AUDIT_LOG = '/var/www/hermes/data/audit.log'
os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)

# Global phase context — set by decider_run.py / guardian for correlation
_current_phase = None  # 'pipeline' | 'guardian' | 'position_manager'
_current_run_id = None  # monotonically increasing per-process run ID

def set_phase(phase: str, run_id: str = None):
    global _current_phase, _current_run_id
    _current_phase = phase
    if run_id:
        _current_run_id = run_id

def _now():
    return datetime.now(timezone.utc).isoformat()

def _base():
    return {
        'ts': _now(),
        'phase': _current_phase,
        'run_id': _current_run_id,
        'pid': os.getpid(),
    }

def log_event(event_type: str, **fields):
    """Write one JSON-Lines record to audit.log."""
    rec = {**fields, **(_base()), 'event': event_type}
    try:
        with open(AUDIT_LOG, 'a') as f:
            f.write(json.dumps(rec, default=str) + '\n')
    except Exception as e:
        # Never let audit logging crash the trading system
        import sys
        print(f'[AUDIT LOG ERROR] {e}', file=sys.stderr)

# ── Convenience wrappers ──────────────────────────────────────────────────────

def trade_open_attempt(token: str, direction: str, signal: str,
                        entry_price: float, amount_usdt: float,
                        source: str = 'decider'):
    log_event('TRADE_OPEN_ATTEMPT',
              token=token.upper(), direction=direction, signal=signal,
              entry_price=entry_price, amount_usdt=amount_usdt,
              source=source)

def trade_open_success(token: str, direction: str, trade_id: int,
                       hl_entry_price: float, signal: str,
                       source: str = 'decider'):
    log_event('TRADE_OPEN_SUCCESS',
              token=token.upper(), direction=direction, trade_id=trade_id,
              hl_entry_price=hl_entry_price, signal=signal,
              source=source)

def trade_open_failed(token: str, direction: str, reason: str,
                      hl_position_left_open: bool = False,
                      source: str = 'decider'):
    log_event('TRADE_OPEN_FAILED',
              token=token.upper(), direction=direction, reason=reason,
              hl_position_left_open=hl_position_left_open,
              source=source)

def trade_close(trade_id: int, token: str, direction: str,
                entry_price: float, exit_price: float,
                pnl_usdt: float, pnl_pct: float,
                close_reason: str, hype_realized_pnl_usdt: float = None,
                is_loss: bool = None, source: str = 'decider'):
    # Cast None-able types to survive pyright strictness
    log_event('TRADE_CLOSE',
              trade_id=int(trade_id), token=token.upper(), direction=direction,
              entry_price=float(entry_price), exit_price=float(exit_price),
              pnl_usdt=float(pnl_usdt), pnl_pct=float(pnl_pct),
              close_reason=str(close_reason),
              hype_realized_pnl_usdt=float(hype_realized_pnl_usdt) if hype_realized_pnl_usdt is not None else None,
              is_loss=bool(is_loss) if is_loss is not None else None,
              source=str(source))

def orphan_detected(token: str, direction: str,
                    entry_price: "float|None" = None, size: "float|None" = None,
                    reason: str = 'no_db_record'):
    log_event('TRADE_ORPHAN_DETECTED',
              token=token.upper(), direction=direction,
              entry_price=entry_price, size=size, reason=reason)

def orphan_created(trade_id: int, token: str, direction: str,
                   entry_price: float, amount_usdt: float):
    log_event('TRADE_ORPHAN_CREATED',
              trade_id=trade_id, token=token.upper(), direction=direction,
              entry_price=entry_price, amount_usdt=amount_usdt)

def orphan_closed(token: str, direction: str,
                  close_price: float, pnl_usdt: float = None,
                  close_reason: str = 'guardian_orphan'):
    log_event('TRADE_ORPHAN_CLOSED',
              token=token.upper(), direction=direction,
              close_price=close_price, pnl_usdt=pnl_usdt,
              close_reason=close_reason)

def loss_cooldown_set(token: str, direction: str,
                      streak: int, hours: float, reason: str = 'loss'):
    log_event('LOSS_COOLDOWN_SET',
              token=token.upper(), direction=direction,
              streak=streak, hours=hours, reason=reason)

def signal_blocked(token: str, direction: str, signal: str,
                   blocker: str, blocker_reason: str = ''):
    log_event('SIGNAL_BLOCKED',
              token=token.upper(), direction=direction, signal=signal,
              blocker=blocker, blocker_reason=blocker_reason)

def atr_check(trade_id: int, token: str, direction: str,
              current_price: float, sl_price: float, tp_price: float,
              in_profit: bool, phase: int, pnl_pct: float = None):
    log_event('ATR_CHECK',
              trade_id=trade_id, token=token.upper(), direction=direction,
              current_price=current_price, sl_price=sl_price, tp_price=tp_price,
              in_profit=in_profit, phase=phase, pnl_pct=pnl_pct)

def atr_sl_hit(trade_id: int, token: str, direction: str,
               entry_price: float, exit_price: float,
               pnl_usdt: float, pnl_pct: float, hold_time_secs: float,
               sl_price_before_hit: float = None):
    log_event('ATR_SL_HIT',
              trade_id=trade_id, token=token.upper(), direction=direction,
              entry_price=entry_price, exit_price=exit_price,
              pnl_usdt=pnl_usdt, pnl_pct=pnl_pct,
              hold_time_secs=hold_time_secs,
              sl_price_before_hit=sl_price_before_hit)

def atr_tp_hit(trade_id: int, token: str, direction: str,
               entry_price: float, exit_price: float,
               pnl_usdt: float, pnl_pct: float, hold_time_secs: float):
    log_event('ATR_TP_HIT',
              trade_id=trade_id, token=token.upper(), direction=direction,
              entry_price=entry_price, exit_price=exit_price,
              pnl_usdt=pnl_usdt, pnl_pct=pnl_pct,
              hold_time_secs=hold_time_secs)

def guardian_cycle(hl_count: int, db_count: int,
                    orphans: list, missing_db: list,
                    closed_count: int = 0, mirrored_count: int = 0):
    log_event('GUARDIAN_CYCLE',
              hl_count=hl_count, db_count=db_count,
              orphans=orphans, missing_db=missing_db,
              closed_count=closed_count, mirrored_count=mirrored_count)

def sentinel_alert(token: str, alert_type: str, detail: str):
    """Critical system alert — something went wrong despite guards."""
    log_event('SENTINEL_ALERT',
              token=token.upper(), alert_type=alert_type, detail=detail)