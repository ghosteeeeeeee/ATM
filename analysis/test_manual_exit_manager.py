#!/usr/bin/env python3
"""Regression suite for manual_exit_manager — the CEO-trade exit brain.

Covers: phase boundaries (0.10% BE-lock / 0.40% trail), TIERED peak trail
(MANUAL_TRAIL_TIERS: 0.50/0.70/1.00/1.40% giveback at 0/1.5/3.0/5.0% peaks —
CEO 2026-10-24 "survive slightly bigger pullbacks" directive), tier-boundary
relaxation (own stops only), CEO-stop improve-only guard, NaN/Inf guards,
state-file poison resilience (bug_hunter F-2), direction validation.

Run: python3 analysis/test_manual_exit_manager.py   (exit 0 = all pass)
Real-trade calibration: #16351 (winner, TP beats trail), #16353/#16358
(BE-lock scratches), #16381 (cascade +1.74% — 0.50% base tier must survive
the 0.46% bounce off its peak, bug_hunter-verified actuals).
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'scripts'))
import manual_exit_manager as M  # noqa: E402

# isolate the trail state file
_tmpdir = tempfile.mkdtemp(prefix='mxm_test_')
M._STATE_FILE = os.path.join(_tmpdir, 'state.json')

decide = M.decide_sl
PASS = 0
FAIL = 0


def check(desc, got, expect_sl=None, expect_phase=None, expect_none=False):
    global PASS, FAIL
    if expect_none:
        ok = got is None
    else:
        ok = (got is not None
              and (expect_sl is None or abs(got[0] - expect_sl) < 0.01)
              and (expect_phase is None or got[2].startswith(expect_phase)))
    print(('✓' if ok else '✗ FAIL'), desc, '→', got)
    PASS += ok
    FAIL += not ok


# ── BE-lock phase ─────────────────────────────────────────────────────────
check('#16353 short pre-BE untouched', decide('SHORT', 81122, 81139, 81760), expect_none=True)
check('#16353 short BE at +0.10%', decide('SHORT', 81057, 81139, 81760), 81139.0, 'BE-LOCK')
check('#16358 long BE at +0.10%', decide('LONG', 81954, 81872, 81380), 81872.0, 'BE-LOCK')
check('#16358 long BE wiggle stays', decide('LONG', 81888, 81872, 81872), expect_none=True)
check('bad direction never falls through', decide('long', 81954, 81872, 81380), expect_none=True)
check('zero price guarded', decide('LONG', 0, 81872, 81380), expect_none=True)
check('NaN current_price guarded (F-2)', decide('LONG', float('nan'), 81872, 81380), expect_none=True)
check('Inf current_price guarded (F-2)', decide('LONG', float('inf'), 81872, 81380), expect_none=True)

# ── Tiered trail: floor = entry ∓ (peak − tier_dist) ──────────────────────
# #16381 replay (bug_hunter actuals): short 79721, peak 0.60% (price 79244.5).
# New 0.50% base → floor 0.10% → SL 79641.3 — SURVIVES the 0.46% bounce
# (high 79583 < SL 79641.3) that killed the old 0.20% base at 79444.
r = decide('SHORT', 79244.5, 79721, 79721, peak_frac=0.006)
check('#16381 replay: floor +0.10% → SL 79641.3', r, 79721 * (1 - 0.001), 'TRAIL')
assert r is not None and r[0] > 79583, 'must survive the 79583 bounce'
check('long tier-1 floor (peak 0.90% → +0.40%)', decide('LONG', 100.9, 100, 100), 100.40, 'TRAIL')
check('long tier-2 floor (peak 2.00% → +1.30%)', decide('LONG', 102.0, 100, 101.0, peak_frac=0.02), 101.30, 'TRAIL')
check('long tier-3 floor (peak 3.50% → +2.50%)', decide('LONG', 103.5, 100, 102.0, peak_frac=0.035), 102.50, 'TRAIL')
check('long tier-4 floor (peak 6.00% → +4.60%)', decide('LONG', 106.0, 100, 104.0, peak_frac=0.06), 104.60, 'TRAIL')
check('short tier-2 floor (peak 2.00% → 98.70)', decide('SHORT', 98.0, 100, 99.0, peak_frac=0.02), 98.70, 'TRAIL')
check('zero-floor edge (peak 0.50 → floor 0 = BE)', decide('LONG', 100.5, 100, 100.0), 100.0, 'TRAIL')
# tier-boundary relaxation (PM semantics): 1.49 → floor 0.99; 1.51 → floor 0.81
check('tier boundary relaxes own stop (peak 1.49 → floor 0.99)',
      decide('LONG', 101.49, 100, 100.99, peak_frac=0.0149), 100.99, 'TRAIL')
check('tier boundary relaxes own stop (peak 1.51 → floor 0.81)',
      decide('LONG', 101.51, 100, 100.99, peak_frac=0.0151), 100.81, 'TRAIL')
check('peak holds at stored value on giveback (peak 4.0, now 3.6 → floor 3.0)',
      decide('LONG', 103.6, 100, 103.0, peak_frac=0.04), 103.00, 'TRAIL')

# ── #16351 winner: TP beats trail ────────────────────────────────────────
# short 82532, peak 0.888% → dist 0.50 → floor 0.388% → SL 82210.7;
# TP 81800 fills FIRST (lower price for a short) → manual_tp_hit stays.
r = decide('SHORT', 81900, 82532, 82200, peak_frac=0.00888)
check('#16351 trail stays above TP (82210.7 > 81800)', r, 82532 * (1 - 0.00388), 'TRAIL')
assert r is None or r[0] > 81800, 'trail must not undercut the TP'

# ── State file poison resilience (bug_hunter F-2) ────────────────────────
import time as _t
M._save_state({'good': {'peak_frac': 0.01, 'last_sl': 101.0, 'ts': _t.time()},
               'bad_string': 'garbage',
               'bad_junk': {'ts': 'not-a-number'},
               'bad_none': None})
reloaded = M._load_state()
ok = list(reloaded.keys()) == ['good']
print(('✓' if ok else '✗ FAIL'), 'state prune drops malformed siblings, keeps valid →', list(reloaded.keys()))
PASS += ok
FAIL += not ok

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
