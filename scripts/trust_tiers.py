#!/usr/bin/env python3
"""
Copy-trader TRUST TIERS — central access for the tier system.

T (2026-10-31): "shadow mode the traders, compile our own leaderboard, the
top top traders we mirror exactly — we have to find traders we trust."

Tiers (from HERMES_DATA/copy_trust.json, written by shadow_mirror.py):
  T1 — EXACT MIRROR: enter+exit exactly like the pro (our exit engines are
       skipped for their trades; only the catastrophic floor stays).
  T2 — STANDARD COPY: current behavior (our exits/engines govern).
  T3 — SHADOW ONLY: no real money; their fills are simulated in the shadow
       ledger until they earn promotion.

Fail-safe rules (this module is a money gate):
  - trust file missing/corrupt/stale > 6h → EVERYONE is T2 (old behavior,
    engines stay on) — never fail-open to T1, never fail-closed to T3.
  - COPY_TRUST_TIERS_ENABLED=False → everyone T2.
"""

import json
import os
import time

from paths import HERMES_DATA

TRUST_FILE = os.path.join(HERMES_DATA, 'copy_trust.json')
_TRUST_STALE_SEC = 20 * 3600         # older than this → ignore tiers (T2 default).
                                      # FIX: was 6h vs a once-daily 04:30 refresh — every day
                                      # from ~10:30 the whole board silently fell back to T2
                                      # (observed: T1 wallet 0x3ff54fd2's 09:38 signal stamped
                                      # T1, its 11:28 signal T2). Refresh is now 4×/day and the
                                      # window tolerates one missed cycle.

_cache = {'ts': 0.0, 'map': None}


def _load_trust_map() -> dict:
    """wallet(lower) -> tier string. Returns {} on any problem (all T2)."""
    now = time.time()
    if _cache['map'] is not None and now - _cache['ts'] < 60:
        return _cache['map']
    out = {}
    try:
        try:
            from hermes_constants import COPY_TRUST_TIERS_ENABLED
        except Exception:
            COPY_TRUST_TIERS_ENABLED = False
        if COPY_TRUST_TIERS_ENABLED:
            with open(TRUST_FILE) as f:
                data = json.load(f)
            if now - float(data.get('updated') or 0) <= _TRUST_STALE_SEC:
                wallets = data.get('wallets') or {}
                if isinstance(wallets, dict):
                    def _norm_tier(v):
                        # bug_hunter LOW: uppercase + whitelist — a stray 't3'
                        # would otherwise slip past both == 'T3' and == 'T1'
                        t = str(v.get('tier') or 'T2').upper()
                        return t if t in ('T1', 'T2', 'T3') else 'T2'
                    out = {str(w).lower(): _norm_tier(v)
                           for w, v in wallets.items()
                           if isinstance(v, dict)}
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError, TypeError, AttributeError, KeyError):
        out = {}  # fail to T2 — the safe middle
    _cache['ts'] = now
    _cache['map'] = out
    return out


def tier_for_wallet(wallet) -> str:
    """'T1' | 'T2' | 'T3' for a trader wallet. Unknown → 'T2'."""
    if not wallet:
        return 'T2'
    return _load_trust_map().get(str(wallet).lower(), 'T2')


def is_exact_mirror_trade(pos_or_meta) -> bool:
    """True when an OPEN trade must be exit-mirrored (T1) instead of
    engine-managed.

    Accepts: a trade row dict (needs `signal` + optional `signal_metadata`)
    or an already-parsed metadata dict (needs `trust_tier`).
    Only trades whose signal is the hl_copy namespace AND whose metadata
    carries trust_tier=T1 qualify — tier is stamped into metadata at SIGNAL
    TIME by hl_copy_signal (source strings are never modified: an exact
    source match exists at signal_schema for 'hl_copy_trader').
    """
    if isinstance(pos_or_meta, dict) and pos_or_meta.get('trust_tier'):
        return (pos_or_meta.get('trust_tier') == 'T1'
                and 'hl_copy' in str(pos_or_meta.get('source') or 'hl_copy'))
    if not isinstance(pos_or_meta, dict):
        return False
    signal = str(pos_or_meta.get('signal') or '')
    if 'hl_copy' not in signal:
        return False
    meta = pos_or_meta.get('signal_metadata') or pos_or_meta.get('_signal_metadata')
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except (ValueError, TypeError):
            meta = None
    if not isinstance(meta, dict):
        return False
    return meta.get('trust_tier') == 'T1'
