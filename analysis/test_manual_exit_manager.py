#!/usr/bin/env python3
"""Regression suite for manual_exit_manager — the CEO-trade exit brain.

Covers: phase boundaries (0.10% BE-lock / 0.40% trail), TIERED peak trail
(profit-monster tiers: 0.20/0.50/0.80/1.20% giveback at 0/1.5/3.0/5.0%
peaks), tier-boundary relaxation (own stops only), CEO-stop improve-only
guard, NaN/Inf guards, direction validation.

Run: python3 analysis/test_manual_exit_manager.py   (exit 0 = all pass)
Real-trade calibration: #16351 (winner, TP beats trail), #16353/#16358
(BE-lock scratches), #16377 (tiered trail booked +1.75% — SL must
reproduce the actual 79,441.50 fill).
"""
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
# #16377 replay: short 79721, peak 0.5506% (price 79283), dist 0.20% (tier 1)
sl_16377 = 79721 * (1 - (0.005506 - 0.002))
check('#16377 short trail reproduces actual 79441.50 fill',
      decide('SHORT', 79283, 79721, 79721, peak_frac=0.005506), sl_16377, 'TRAIL')
check('long tier-1 floor (peak 0.50% → +0.30%)', decide('LONG', 100.5, 100, 100), 100.30, 'TRAIL')
check('long tier-2 floor (peak 2.00% → +1.50%)', decide('LONG', 102.0, 100, 101.3, peak_frac=0.02), 101.50, 'TRAIL')
check('long tier-3 floor (peak 3.50% → +2.70%)', decide('LONG', 103.5, 100, 102.0, peak_frac=0.035), 102.70, 'TRAIL')
check('long tier-4 floor (peak 6.00% → +4.80%)', decide('LONG', 106.0, 100, 104.0, peak_frac=0.06), 104.80, 'TRAIL')
check('short tier-2 floor (peak 2.00% → 98.50)', decide('SHORT', 98.0, 100, 99.0, peak_frac=0.02), 98.50, 'TRAIL')
# tier-boundary relaxation (PM semantics): peak 1.51% → dist 0.50 → floor 1.01
# (a peak of 1.49 gave floor 1.29 — the boundary intentionally gives room back)
check('tier boundary relaxes own stop (peak 1.51 → floor 1.01)',
      decide('LONG', 101.51, 100, 101.29, peak_frac=0.0151), 101.01, 'TRAIL')
check('peak holds at stored value on giveback (peak 4.0, now 3.6 → floor 3.2)',
      decide('LONG', 103.6, 100, 103.0, peak_frac=0.04), 103.20, 'TRAIL')

# ── #16351 winner: TP beats trail ────────────────────────────────────────
# short 82532, peak 0.888% → floor 0.688% → trail SL 81963.7 — TP 81800
# fills FIRST (lower price for a short), so manual_tp_hit stays the exit.
r = decide('SHORT', 81900, 82532, 82200, peak_frac=0.00888)
check('#16351 trail stays above TP (81963.7 > 81800)', r, 82532 * (1 - 0.00688), 'TRAIL')
assert r is None or r[0] > 81800, 'trail must not undercut the TP'

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
