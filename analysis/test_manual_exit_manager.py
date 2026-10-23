#!/usr/bin/env python3
"""Regression suite for manual_exit_manager.decide_sl — the CEO-trade exit brain.

Covers: phase boundaries (0.10% BE-lock / 0.40% trail), ratchet-only per
direction, BE→trail supersede sequences, CEO-edit protection, NaN/Inf guards
(bug_hunter 2026-10-23 F-2), direction validation.

Run: python3 scripts/test_manual_exit_manager.py   (exit 0 = all pass)
Real-trade calibration cases: #16351 (winner), #16353 / #16358 (max-hold exits
that the BE-lock would have turned into scratches).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import manual_exit_manager as M  # noqa: E402

decide = M.decide_sl
PASS = 0
FAIL = 0


def check(desc, got, expect):
    """expect: None | ('BE', sl) | 'TRAIL'"""
    global PASS, FAIL
    if expect is None:
        ok = got is None
    elif expect == 'TRAIL':
        ok = got is not None and got[2].startswith('TRAIL')
    elif expect[0] == 'BE':
        ok = got is not None and got[2] == 'BE-LOCK' and abs(got[0] - expect[1]) < 1e-9
    else:
        ok = False
    print(('✓' if ok else '✗ FAIL'), desc, '→', got)
    PASS += ok
    FAIL += not ok


# ── real trades ──────────────────────────────────────────────────────────
check('#16353 short pre-BE (0.05%) untouched', decide('SHORT', 81122, 81139, 81760), None)
check('#16353 short BE at +0.10%', decide('SHORT', 81057, 81139, 81760), ('BE', 81139.0))
check('#16353 short BE wiggle stays', decide('SHORT', 81200, 81139, 81139), None)
check('#16353 short trail at +0.41%', decide('SHORT', 80808, 81139, 81139), 'TRAIL')
check('#16358 long pre-BE untouched', decide('LONG', 81913, 81872, 81380), None)
check('#16358 long BE at +0.10%', decide('LONG', 81954, 81872, 81380), ('BE', 81872.0))
check('#16358 long BE wiggle stays', decide('LONG', 81888, 81872, 81872), None)
check('#16358 long trail at +0.41%', decide('LONG', 82210, 81872, 81872), 'TRAIL')
check('#16351 short BE then trail supersedes', decide('SHORT', 81939, 82532, 82532), 'TRAIL')

# ── ratchet: never backward ──────────────────────────────────────────────
check('LONG trail dip: no back-move', decide('LONG', 82100, 81872, 82035), None)
check('SHORT trail rally: no back-move', decide('SHORT', 81000, 81139, 80900), None)
check('LONG old SL above entry: BE must not lower', decide('LONG', 81954, 81872, 81900), None)
check('SHORT old SL better than entry: BE must not raise', decide('SHORT', 81057, 81139, 81000), None)

# ── boundaries ───────────────────────────────────────────────────────────
check('below BE boundary (0.09%)', decide('LONG', 81945, 81872, 81380), None)
check('above trail boundary (0.41%)', decide('LONG', 82210, 81872, 81872), 'TRAIL')

# ── validation & guards ──────────────────────────────────────────────────
check('bad direction never falls through', decide('long', 81954, 81872, 81380), None)
check('zero price guarded', decide('LONG', 0, 81872, 81380), None)
check('negative price guarded', decide('SHORT', -1, 81139, 81760), None)
check('NaN current_price guarded (F-2)', decide('LONG', float('nan'), 81872, 81380), None)
check('NaN entry guarded (F-2)', decide('LONG', 81954, float('nan'), 81380), None)
check('Inf current_price guarded (F-2)', decide('LONG', float('inf'), 81872, 81380), None)
check('NaN old_sl guarded (F-2)', decide('LONG', 81954, 81872, float('nan')), None)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
