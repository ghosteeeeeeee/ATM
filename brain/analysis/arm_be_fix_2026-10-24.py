#!/usr/bin/env python3
"""Selfcheck for the ARM-BE shadow fix (brain_auditor run #127, 2026-10-24).

Root cause fixed: ARM-BE used a module-level _arm_be_shadow_armed set, but
position_manager runs as a fresh subprocess every pipeline pass, so the
arm->cross-entry sequence could never survive one process (0 runtime fires
2026-10-18..24 while sibling UGB-BE, built on DB highest/lowest_price,
logged 504). Fix: arm state = DB peak (highest/lowest_price), same
persistence basis as UGB-BE.

Asserts:
  1. Source: ARM-BE block reads highest_price/lowest_price (DB basis).
  2. Source: _arm_be_shadow_armed is fully removed (no dead references).
  3. Source: dedup set _arm_be_shadow_logged still guards re-logging.
  4. Logic truth table: LONG/SHORT fav + live_pnl conditions (hand-computable).
  5. position_manager.py compiles.
"""
import ast
import py_compile
import sys
from pathlib import Path

PM = Path("/root/.hermes/scripts/position_manager.py")


def _arm_be_block(src: str) -> str:
    start = src.index("7b-shadow3. ARM-BE-STOP SHADOW")
    end = src.index("7b-shadow4. UGB SHADOW")
    return src[start:end]


def fire(entry, peak, live, direction, regime="NORMAL", signal="x"):
    """Replica of the fixed ARM-BE condition (must mirror position_manager)."""
    if "volume-" in signal.lower() or regime == "EXTREME":
        return False
    if not (entry > 0 and peak > 0):
        return False
    arm_pct = 0.4  # PM_TRAIL_ACTIVATE_PCT * 100
    fav = (peak / entry - 1.0) * 100 if direction == "LONG" else (1.0 - peak / entry) * 100
    return fav >= arm_pct and live <= 0


def selfcheck() -> bool:
    src = PM.read_text()
    block = _arm_be_block(src)
    ok = True

    # 1. DB-state basis present
    if "highest_price" not in block or "lowest_price" not in block:
        print("FAIL 1: ARM-BE block does not read DB peak state")
        ok = False
    else:
        print("ok 1: ARM-BE reads DB highest/lowest_price")

    # 2. dead set removed from CODE (comment mentions in the fix note are fine)
    code_hits = [
        ln for ln in src.splitlines()
        if "_arm_be_shadow_armed" in ln and not ln.lstrip().startswith("#")
    ]
    if code_hits:
        print(f"FAIL 2: _arm_be_shadow_armed still in code: {code_hits[:2]}")
        ok = False
    else:
        print("ok 2: _arm_be_shadow_armed removed from code (comment-only mention ok)")

    # 3. dedup guard intact
    if "trade_id not in _arm_be_shadow_logged" not in block:
        print("FAIL 3: dedup guard missing from ARM-BE block")
        ok = False
    else:
        print("ok 3: _arm_be_shadow_logged dedup guard present")

    # 4. truth table (hand-computable)
    cases = [
        # (entry, peak, live, direction, regime, signal, expected)
        (100.0, 100.6, -0.05, "LONG", "NORMAL", "x", True),    # armed 0.6, round trip
        (100.0, 100.2, -0.05, "LONG", "NORMAL", "x", False),   # peak below 0.40 arm
        (100.0, 100.6, 0.30, "LONG", "NORMAL", "x", False),    # still positive
        (100.0, 100.6, 0.00, "LONG", "NORMAL", "x", True),     # exactly at entry fires
        (100.0, 99.5, -0.10, "SHORT", "NORMAL", "x", True),    # short armed (low)
        (100.0, 99.8, -0.10, "SHORT", "NORMAL", "x", False),   # short peak below arm
        (100.0, 100.6, -0.05, "LONG", "EXTREME", "x", False),  # scope: EXTREME excluded
        (100.0, 100.6, -0.05, "LONG", "NORMAL", "volume-buildup-", False),  # volume- excluded
        (0.0, 100.6, -0.05, "LONG", "NORMAL", "x", False),     # bad entry guard
    ]
    tab_ok = True
    for i, (en, pk, lv, d, rg, sg, exp) in enumerate(cases, 1):
        got = fire(en, pk, lv, d, rg, sg)
        if got != exp:
            print(f"FAIL 4.{i}: fire({en},{pk},{lv},{d},{rg},{sg}) = {got}, expected {exp}")
            tab_ok = False
            ok = False
    if tab_ok:
        print(f"ok 4: truth table {len(cases)}/{len(cases)}")

    # 5. compiles
    try:
        py_compile.compile(str(PM), doraise=True)
        print("ok 5: position_manager.py compiles")
    except py_compile.PyCompileError as e:
        print(f"FAIL 5: {e}")
        ok = False

    # AST sanity: file still parses (catches anything py_compile tolerated oddly)
    ast.parse(src)
    print("ok 6: AST parse PASS")
    print("SELFcheck:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(0 if selfcheck() else 1)
