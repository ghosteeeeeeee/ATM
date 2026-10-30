#!/usr/bin/env python3
"""
Central directional-blacklist helper.

CEO 2026-10-30 (Option D): the JUP YOLO mirror needs a source-scoped
SHORT_BLACKLIST exemption. The blacklist is checked at SIX sites
(signal_schema, brain, decider_run, hl-sync-guardian x2, ai_trader_precheck)
— a signal-layer-only exemption creates zombie signals (approved, then
blocked at execution). EVERY site routes through this one helper so the
exemption can never disagree with itself.

Rules:
  - direction == 'SHORT' and token in SHORT_BLACKLIST:
        blocked UNLESS source contains 'jup_yolo_mirrored'
  - direction == 'LONG' and token in LONG_BLACKLIST:
        blocked (Option D exempts the SHORT list ONLY)
  - otherwise not blocked.

Guards the OTHER gates unchanged (this helper is not involved in):
  RSI floors, staleness, rep-gate, hot-set, conflict-penalty, oversold knife.
"""

from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST

# FIX (bug_hunter N2): match the whole 'jup_yolo' namespace, not just the
# full 'jup_yolo_mirrored' source string. The RSI-floor carve-outs match
# 'jup_yolo' (prefix) — if signal_type ('jup_yolo_short') ever flows as the
# source (decider's `signal_type or source` path), the full-string check
# would give floor-exemption WITHOUT blacklist-exemption → approved-then-
# blocked zombie churn, the exact failure Option D exists to prevent.
# The namespace is ours alone; nothing else starts with 'jup_yolo'.
JUP_YOLO_NS = 'jup_yolo'


def is_directional_blocked(token, direction, source=None) -> bool:
    """True when token+direction must be blocked by a directional blacklist.

    token/direction: whatever the calling site already compares (some sites
    pass hype_coin()-normalized symbols, others raw uppercase — this helper
    only .upper()s, preserving each site's existing normalization).
    source: the signal source string (or trade.signal / hotset source).
    None/empty source = no exemption (fail toward the conservative block).
    """
    tok = str(token).upper() if token is not None else ''
    dire = str(direction).upper() if direction is not None else ''
    src = str(source or '')
    if dire == 'SHORT':
        if tok in SHORT_BLACKLIST:
            return JUP_YOLO_NS not in src
    elif dire == 'LONG':
        if tok in LONG_BLACKLIST:
            return True
    return False


def directional_block_reason(token, direction) -> str:
    """Which list the block came from — for logging at call sites."""
    tok = str(token).upper() if token is not None else ''
    dire = str(direction).upper() if direction is not None else ''
    if dire == 'SHORT' and tok in SHORT_BLACKLIST:
        return 'SHORT_BLACKLIST'
    if dire == 'LONG' and tok in LONG_BLACKLIST:
        return 'LONG_BLACKLIST'
    return ''
